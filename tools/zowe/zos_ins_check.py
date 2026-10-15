#!/usr/bin/env python3
"""ZOS-4 PACZ4INS checks (tools/zowe/zos_target.py z4ins_deck; docs/zos4-pacz4ins-review.md). Read-only.

Usage: zos_ins_check.py --gate          before the job: LOAD(PACMAIN), <p>.CEEOPTS and CLIST(PACSRCT) absent; CLIST(PACMAN)
                                        present and exactly the frozen raw template (IBM-037, fixed 80); PACZ2D attributes
                                        as accepted
       zos_ins_check.py SPOOLDIR        after the job: spool (RC, DDs, IEBCOPY copy messages), the two smoke runs = their
                                        oracle 307 blocks and models, then the state: PACSRCT = the template, CEEOPTS one
                                        record, PACMAIN attributes = PACZ2D's, PACZ2D unchanged, CLIST(PACMAN) still the
                                        template (the z/OS CLIST is not installed by the job)
       zos_ins_check.py --clist         after the CLIST installation: CLIST(PACMAN) = the rendered src/zos/PACMAN.clist
                                        byte for byte, PACSRCT still the template
"""
import gzip
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path.insert(0, str(HERE))
from zoslib import fixed_records, zowe  # noqa: E402
from zos_equiv import compare, zos_runs  # noqa: E402
from zos_target import Z4INS_SMOKE, zos_clist_text  # noqa: E402

HLQ = 'Z00000'
P = f'{HLQ}.PACMAN'
STEPS = ['SAVETPL', 'CEEOPT', 'PROM1', 'PROM2'] + Z4INS_SMOKE
PACZ2D_ATTR = {'ac': '00', 'amode': '24', 'attr': 'RN RU', 'rmode': '24', 'size': '000200B0'}   # as listed 2026-10-15
TEMPLATE = R / 'src/clist/PACMAN.clist'
CEE_RECORD = 'ALL31(OFF),STACK(,,BELOW)'.ljust(80).encode('cp037')     # the one record, IBM-037, fixed 80
RENDERED = R / 'build/zos/PACMAN.zos.clist'


def rendered_clist():
    """The z/OS CLIST for Z00000.PACMAN as a local file (what is uploaded and compared)."""
    text = zos_clist_text(P)
    assert all(len(l) <= 72 for l in text.splitlines()), 'a CLIST line ends at column 72'
    RENDERED.parent.mkdir(parents=True, exist_ok=True)
    RENDERED.write_text(text, encoding='ascii')
    return RENDERED


def members(ds, attrs=False):
    d = zowe('zos-files', 'list', 'all-members', ds, *(['-a'] if attrs else []), json_out=True)
    return {m['member']: m for m in d['data']['apiResponse']['items']}


def exists(ds):
    return [i for i in zowe('zos-files', 'list', 'data-set', ds, '-a', json_out=True)['data']['apiResponse']['items']
            if i['dsname'] == ds]


def binary(dsn):
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / 'm.bin'
        zowe('zos-files', 'download', 'data-set', dsn, '--binary', '-f', str(f), json_out=True)
        return f.read_bytes()


def attrs_of(m):
    return {k: m.get(k) for k in PACZ2D_ATTR}


def gate():
    load, cl = members(f'{P}.LOAD', True), members(f'{P}.CLIST')
    return [('LOAD(PACMAIN) does not exist', 'PACMAIN' not in load),
            (f'{P}.CEEOPTS does not exist', not exists(f'{P}.CEEOPTS')),
            ('CLIST(PACSRCT) does not exist', 'PACSRCT' not in cl),
            ('CLIST(PACMAN) exists', 'PACMAN' in cl),
            ('CLIST(PACMAN) = the frozen raw template src/clist/PACMAN.clist (IBM-037, fixed 80)',
             'PACMAN' in cl and binary(f'{P}.CLIST(PACMAN)') == fixed_records(TEMPLATE)),
            (f'LOAD(PACZ2D) attributes as accepted {PACZ2D_ATTR}', attrs_of(load.get('PACZ2D', {})) == PACZ2D_ATTR)]


def job_check(d):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = json.loads((d / 'spool.json').read_text())
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    jes = ''.join(p.read_text() for p in d.glob('00*-JES2-*.txt'))
    _, steps, runs = zos_runs(d)
    res = [(f'steps {" ".join(STEPS)}', job['jobname'] == 'PACZ4INS' and steps == STEPS)]
    for s in STEPS:
        res.append((f'{s} COND CODE 0000',
                    bool(re.search(rf'IEF142I {job["jobname"]} {s} - STEP WAS EXECUTED - COND CODE 0000', msg))))
    res.append(('no ABEND / IEA995 / $HASP375 / S722 / CEE message',
                not re.search(r'ABEND|IEA995|\$HASP375|S722|CEE\d{4}', jes)))
    dd = {(f['stepname'], f['ddname']) for f in files if f['stepname'] != 'JES2'}
    res.append(('spool DDs: SYSPRINT of SAVETPL / CEEOPT / PROM1 / PROM2, SYSOUT of the two runs',
                dd == {(s, 'SYSPRINT') for s in STEPS[:4]} | {(s, 'SYSOUT') for s in Z4INS_SMOKE}))
    res.append(('STEPLIB Z00000.PACMAN.LOAD retained once per smoke run',
                len(re.findall(r'IGD104I Z00000\.PACMAN\.LOAD\s+RETAINED,\s+DDNAME=STEPLIB', msg)) == len(Z4INS_SMOKE)))
    own = f'{HLQ}.{job["jobname"]}.{job["jobid"]}.'
    named = {x.rstrip('.') for x in re.findall(rf'\b({HLQ}\.[\w.$#@]+)', msg) if not x.startswith(own)}
    res.append(('datasets in JESYSMSG only CLIST, CEEOPTS, LOAD', named <= {f'{P}.CLIST', f'{P}.CEEOPTS', f'{P}.LOAD'}))
    for s, want in (('PROM1', ('PACZ2D', 'PACMAIN')), ('PROM2', ('PACMAIN',))):
        f = next(f for f in files if (f['stepname'], f['ddname']) == (s, 'SYSPRINT'))
        text = (d / f'{f["id"]:03d}-{s}-SYSPRINT.txt').read_text()
        lines = [l for l in text.splitlines() if 'COPIED' in l.upper() and all(w in l for w in want)]
        res.append((f'{s}: IEBCOPY reports {" -> ".join(want)} copied', bool(lines)))
    sys.path.insert(0, str(R / 'tests'))
    from zos_classic_check import model
    oracle = json.load(gzip.open(R / 'tests/oracle20/307-PACREL20.json.gz'))
    smoke = {s: runs[s] for s in Z4INS_SMOKE}
    nb, msgs = compare(oracle, smoke, {'PACMAIN': 'PACMAIN'}, subset=True)
    for m in msgs:
        if not m.startswith('SUBSET'):
            res.append((f'oracle 307 {m[5:]}', m.startswith('OK')))
    for s in Z4INS_SMOKE:
        r = model(s, runs[s]['lines'])
        res.append((f'{s} = the independent model (tests/test_mvs8.py)' + (f' - {r}' if r else ''), r is None))
    return job, res


def state_after_job():
    load, cl = members(f'{P}.LOAD', True), members(f'{P}.CLIST')
    a = (exists(f'{P}.CEEOPTS') or [{}])[0]
    rec = [l.rstrip() for l in zowe('zos-files', 'view', 'data-set', f'{P}.CEEOPTS').stdout.splitlines() if l.strip()] \
        if a else []
    return [('CLIST(PACSRCT) = the frozen raw template', 'PACSRCT' in cl
             and binary(f'{P}.CLIST(PACSRCT)') == fixed_records(TEMPLATE)),
            ('CLIST(PACMAN) still the template (not installed by the job)',
             binary(f'{P}.CLIST(PACMAN)') == fixed_records(TEMPLATE)),
            (f'{P}.CEEOPTS: PS FB 80 80, one record ALL31(OFF),STACK(,,BELOW)',
             a.get('dsorg') == 'PS' and a.get('recfm') == 'FB' and a.get('lrecl') == '80' and a.get('blksz') == '80'
             and rec == ['ALL31(OFF),STACK(,,BELOW)']),
            (f'{P}.CEEOPTS content (binary): exactly one fixed 80-byte record = ALL31(OFF),STACK(,,BELOW) in IBM-037 + '
             'blank padding', bool(a) and binary(f'{P}.CEEOPTS') == CEE_RECORD),
            (f'LOAD(PACMAIN) attributes = PACZ2D\'s {PACZ2D_ATTR} (AMODE 24, RMODE 24, RENT REUS, same size)',
             attrs_of(load.get('PACMAIN', {})) == PACZ2D_ATTR),
            ('LOAD(PACZ2D) unchanged', attrs_of(load.get('PACZ2D', {})) == PACZ2D_ATTR)]


def state_after_clist():
    want = fixed_records(rendered_clist())
    return [('CLIST(PACMAN) = the rendered src/zos/PACMAN.clist (IBM-037, fixed 80) byte for byte',
             binary(f'{P}.CLIST(PACMAN)') == want),
            ('CLIST(PACSRCT) still the frozen raw template', binary(f'{P}.CLIST(PACSRCT)') == fixed_records(TEMPLATE))]


def show(title, res):
    for k, v in res:
        print(f'  {"OK  " if v else "FAIL"} {k}')
    bad = sum(not v for _, v in res)
    print(f'{title} ' + ('PASS' if not bad else f'FAIL ({bad})'))
    return bad


def main():
    a = sys.argv[1:]
    if a == ['--gate']:
        bad = show('PACZ4INS GATE', gate())
    elif a == ['--clist']:
        bad = show('PACZ4INS CLIST CHECK', state_after_clist())
    else:
        job, res = job_check(a[0])
        print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}')
        bad = show('PACZ4INS CHECK', res + state_after_job())
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
