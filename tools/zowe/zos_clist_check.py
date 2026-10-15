#!/usr/bin/env python3
"""ZOS-4 PACZ4CL check (tools/zowe/zos_target.py z4cl_deck): the CLIST PARM lines and the HS CLIST block under the TMP
in batch. Read-only.

Usage: zos_clist_check.py --gate              before the submission: none of the attempt names exists
       zos_clist_check.py SPOOLDIR            after it: spool, the TMP output, then the datasets (read-only)
References (frozen, no new model): the 4 `G8PARM=` lines of oracle JOB 307 (MVS G8CLT, the same 4 keyword sets of
make_deck G8_CLIST); the HS-block assertions of tests/test_hs.py section 3 on oracle JOB 312 (present: the DATA member
line followed by `PACHS KEEP`; missing: `NULLFILE  PACHS`; `HSCL END` after each; no IKJ56xxx message).
"""
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path.insert(0, str(HERE))
from zos_equiv import zos_runs  # noqa: E402
from zos_target import Z4_ATTEMPT, Z4_SETS  # noqa: E402

HLQ = 'Z00000'
WORK = f'{HLQ}.PACMAN.{Z4_SETS["work"][0]}.{Z4_ATTEMPT}'
YES = f'{HLQ}.PACMAN.{Z4_SETS["present"][0]}.DATA'
NO = f'{HLQ}.PACMAN.{Z4_SETS["missing"][0]}.DATA'
STEPS = ['ALLOC', 'G8CLS', 'HSCLS1', 'HSCLS2', 'CLT']


def g8_want():
    s = json.load(gzip.open(R / 'tests/oracle20/307-PACREL20.json.gz'))['stream']
    return [m.group(1) for m in (re.match(r'G8PARM=(.*)=$', l.rstrip()) for l in s) if m]


def tmp_check(lines):
    """[(criterion, ok)] of the CLT SYSTSPRT (ASA column already removed, padding stripped)."""
    res = []
    got = [m.group(1) for m in (re.match(r'G8PARM=(.*)=$', l) for l in lines) if m]
    want = g8_want()
    res.append((f'G8PARM lines = oracle 307 ({len(want)}: {", ".join(want)})', got == want and len(want) == 4))
    ey = next((i for i, l in enumerate(lines) if l.strip() == f"EXEC '{WORK}(HSCLY)'"), None)
    en = next((i for i, l in enumerate(lines) if l.strip() == f"EXEC '{WORK}(HSCLN)'"), None)
    ok = ey is not None and en is not None and ey < en
    res.append(('both HS-block CLISTs run, present first', ok))
    if ok:
        py, pn = lines[ey:en], lines[en:]
        i = next((k for k, l in enumerate(py) if l.strip() == f'{YES}(HISCORE)'), None)
        res.append(('present path: DATA(HISCORE) allocated to PACHS (KEEP), then HSCL END',
                    i is not None and i + 1 < len(py) and py[i + 1].split() == ['PACHS', 'KEEP']
                    and sum(l.strip() == 'HSCL END' for l in py) == 1 and not any('NULLFILE' in l for l in py)))
        res.append(('missing path: NULLFILE PACHS (DUMMY), then HSCL END, the missing DATA never allocated',
                    any(l.split() == ['NULLFILE', 'PACHS'] for l in pn) and sum(l.strip() == 'HSCL END' for l in pn) == 1
                    and not any(NO in l for l in pn)))
    res.append(('no IKJ56xxx message', not any(re.search(r'IKJ56\d{3}', l) for l in lines)))
    return res


def spool_check(d):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = json.loads((d / 'spool.json').read_text())
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    jes = ''.join(p.read_text() for p in d.glob('00*-JES2-*.txt'))
    _, steps, _ = zos_runs(d)
    res = [(f'steps {" ".join(STEPS)}', steps == STEPS)]
    for s in STEPS:
        res.append((f'{s} COND CODE 0000',
                    bool(re.search(rf'IEF142I {job["jobname"]} {s} - STEP WAS EXECUTED - COND CODE 0000', msg))))
    res.append(('no ABEND / IEA995 / $HASP375 / S722 / CEE message', not re.search(r'ABEND|IEA995|\$HASP375|S722|CEE\d{4}', jes)))
    dd = {(f['stepname'], f['ddname']) for f in files if f['stepname'] != 'JES2'}
    res.append(('spool DDs: SYSPRINT of G8CLS / HSCLS1 / HSCLS2, SYSTSPRT of CLT',
                dd == {('G8CLS', 'SYSPRINT'), ('HSCLS1', 'SYSPRINT'), ('HSCLS2', 'SYSPRINT'), ('CLT', 'SYSTSPRT')}))
    own = f'{HLQ}.{job["jobname"]}.{job["jobid"]}.'
    named = {x.rstrip('.') for x in re.findall(rf'\b({HLQ}\.[\w.$#@]+)', msg) if not x.startswith(own)}
    res.append((f'datasets in JESYSMSG only {WORK} and {YES}', named <= {WORK, YES}))
    f = next(f for f in files if (f['stepname'], f['ddname']) == ('CLT', 'SYSTSPRT'))
    raw = (d / f'{f["id"]:03d}-CLT-SYSTSPRT.txt').read_text().splitlines()
    res += tmp_check([l[1:].rstrip() for l in raw])
    return job, res


def catalog(after):
    from zoslib import zowe

    def exists(ds):
        items = zowe('zos-files', 'list', 'data-set', ds, '-a', json_out=True)['data']['apiResponse']['items']
        return [i for i in items if i['dsname'] == ds]
    res = []
    if not after:
        for ds in (WORK, YES, NO):
            res.append((f'{ds} does not exist', not exists(ds)))
        return res
    for ds, want in ((WORK, ['HSCLN', 'HSCLY', 'PARMS']), (YES, [])):
        a = (exists(ds) or [{}])[0]
        res.append((f'{ds}: PDS PO FB 80 80', all(a.get(k) == v for k, v in
                                                 {'dsntp': 'PDS', 'dsorg': 'PO', 'recfm': 'FB', 'lrecl': '80', 'blksz': '80'}.items())))
        mem = sorted(m['member'] for m in
                     zowe('zos-files', 'list', 'all-members', ds, json_out=True)['data']['apiResponse']['items'])
        res.append((f'{ds} members exactly {" ".join(want) or "(none: ALLOC SHR created no HISCORE)"}', mem == want))
    res.append((f'{NO} still does not exist', not exists(NO)))
    return res


def main():
    a = sys.argv[1:]
    if a == ['--gate']:
        res, title = catalog(False), 'PACZ4CL GATE'
    else:
        job, res = spool_check(a[0])
        print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}')
        res += catalog(True)
        title = 'PACZ4CL CHECK'
    for k, v in res:
        print(f'  {"OK  " if v else "FAIL"} {k}')
    bad = sum(not v for _, v in res)
    print(f'{title} ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
