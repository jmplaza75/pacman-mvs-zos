#!/usr/bin/env python3
"""ZOS-3 PACZ3HA check: the high-score test PDSs of one attempt (docs/zos3-design.md, tools/zowe/zos_target.py
z3ha_deck). Read-only.

Usage: zos_hs_setup_check.py SPOOLDIR [--catalog]
Spool (the job as tools/zowe/zos_submit.py saved it):
1. steps ALLOC, HSSEED1, HSSEED2, HSSEED3, HSFILL, HSLIST in this order; COND CODE 0000 each, HSFILL 0012;
   no abend / IEA995 / $HASP375 / S722 text; spool DDs = the JES files + SYSPRINT of HSSEED1..3 / HSFILL + SYSTSPRT of
   HSLIST; the only datasets named in JESYSMSG under the HLQ (besides the job's own JES datasets) are the two attempt PDSs;
2. HSFILL (IEBUPDTE) stowed exactly M01..M20 (IEB817I each), then IEB813I OUTPUT DIRECTORY FULL at M21 and nothing
   after it: the one directory block is genuinely full, as in oracle JOB 312;
3. HSLIST (TSO LISTDS): each PDS FB 80 80 PO; members HSTEST = BAD EMPTY HS9, HSFULL = M01..M20.
--catalog (read-only z/OSMF requests, these two datasets only): catalogued, dsntp PDS, dsorg PO, recfm FB, lrecl 80,
   blksz 80, not migrated; the same member lists; HS9 = the one record '9999999 PACHS001 099', BAD = its two records,
   EMPTY = no record.
Exit 0 only if everything passes.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from zos_equiv import zos_runs  # noqa: E402
from zos_target import HS_ATTEMPT, HS_SETS  # noqa: E402

HLQ = 'Z00000'
DSN = {n: f'{HLQ}.PACMAN.{n}.{HS_ATTEMPT}' for n, _ in HS_SETS}
STEPS = ['ALLOC', 'HSSEED1', 'HSSEED2', 'HSSEED3', 'HSFILL', 'HSLIST']
RC = dict.fromkeys(STEPS, '0000') | {'HSFILL': '0012'}
MEMBERS = {'HSTEST': ['BAD', 'EMPTY', 'HS9'], 'HSFULL': [f'M{i:02}' for i in range(1, 21)]}
CONTENT = {'HS9': ['9999999 PACHS001 099'], 'BAD': ['XYZZY NOT A SCORE', 'SECOND JUNK RECORD'], 'EMPTY': []}
SPOOL = {('HSSEED1', 'SYSPRINT'), ('HSSEED2', 'SYSPRINT'), ('HSSEED3', 'SYSPRINT'), ('HSFILL', 'SYSPRINT'),
         ('HSLIST', 'SYSTSPRT')}


def fill_ok(lines):
    """IEBUPDTE NEW MASTER log: IEB817I for M01..M20 in order, then IEB813I right after ADD NAME=M21, nothing stowed
    after it, highest condition code 12."""
    stowed = re.findall(r'IEB817I MEMBER NAME \((\w+)\s*\) NOT FOUND IN NM DIRECTORY\.\s+STOWED WITH TTR', '\n'.join(lines))
    full = [i for i, l in enumerate(lines) if 'IEB813I OUTPUT DIRECTORY FULL' in l]
    adds = [i for i, l in enumerate(lines) if './ ADD NAME=M21' in l]
    return (stowed == MEMBERS['HSFULL'] and len(full) == 1 and len(adds) == 1 and adds[0] < full[0]
            and not any('IEB817I' in l for l in lines[full[0]:])
            and any('IEB818I HIGHEST CONDITION CODE WAS 00000012' in l for l in lines))


def listds(lines):
    """{dsname: (recfm, lrecl, blksize, dsorg, [members])} from TSO LISTDS ... MEMBERS output."""
    out, cur, sect = {}, None, None
    for i, l in enumerate(lines):
        s = l.strip()
        if s in DSN.values():
            cur, sect = s, None
            out[cur] = [None, None, None, None, []]
        elif cur and s.startswith('--RECFM-LRECL-BLKSIZE-DSORG'):
            out[cur][:4] = lines[i + 1].split()[:4]
        elif cur and s.startswith('--MEMBERS--'):
            sect = 'M'
        elif cur and s.startswith('--'):
            sect = None
        elif cur and sect == 'M' and s and not s.startswith('READY') and not s.startswith('LISTDS'):
            out[cur][4].append(s.split()[0])
    return {k: tuple(v[:4]) + (v[4],) for k, v in out.items()}


def spool_check(d):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = json.loads((d / 'spool.json').read_text())
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    jes = ''.join(p.read_text() for p in d.glob('00*-JES2-*.txt'))
    _, steps, runs = zos_runs(d)
    res = []
    res.append(('steps ' + ' '.join(STEPS), steps == STEPS))
    for s in STEPS:
        res.append((f'{s} COND CODE {RC[s]}',
                    bool(re.search(rf'IEF142I {job["jobname"]} {s} - STEP WAS EXECUTED - COND CODE {RC[s]}', msg))))
    res.append(('no abend / IEA995 / $HASP375 / S722', not re.search(r'ABEND|IEA995|\$HASP375|S722', jes)))
    dd = {(f['stepname'], f['ddname']) for f in files if f['stepname'] != 'JES2'}
    res.append(('spool DDs = SYSPRINT of HSSEED1..3 / HSFILL + SYSTSPRT of HSLIST', dd == SPOOL))
    own = f'{HLQ}.{job["jobname"]}.{job["jobid"]}.'           # the job's own JES SYSIN / SYSOUT datasets
    named = {n.rstrip('.') for n in re.findall(rf'\b({HLQ}\.[\w.$#@]+)', msg) if not n.startswith(own)}
    res.append((f'datasets in JESYSMSG = {sorted(DSN.values())}', named == set(DSN.values())))
    fill = (d / next(f'{f["id"]:03d}-HSFILL-SYSPRINT.txt' for f in files
                     if (f['stepname'], f['ddname']) == ('HSFILL', 'SYSPRINT'))).read_text().splitlines()
    res.append(('HSFILL: M01..M20 stowed, IEB813I directory full at M21, highest CC 12', fill_ok(fill)))
    lst = (d / next(f'{f["id"]:03d}-HSLIST-SYSTSPRT.txt' for f in files
                    if (f['stepname'], f['ddname']) == ('HSLIST', 'SYSTSPRT'))).read_text().splitlines()
    got = listds(lst)
    for n, ds in DSN.items():
        res.append((f'LISTDS {ds}: FB 80 80 PO, members {" ".join(MEMBERS[n][:3])}{" ..." if n == "HSFULL" else ""}',
                    got.get(ds) == ('FB', '80', '80', 'PO', MEMBERS[n])))
    return job, res


def catalog_check():
    from zoslib import zowe
    res = []
    for n, ds in DSN.items():
        items = zowe('zos-files', 'list', 'data-set', ds, '-a', json_out=True)['data']['apiResponse']['items']
        a = items[0] if len(items) == 1 and items[0]['dsname'] == ds else {}
        want = {'dsntp': 'PDS', 'dsorg': 'PO', 'recfm': 'FB', 'lrecl': '80', 'blksz': '80', 'migr': 'NO'}
        res.append((f'catalog {ds}: ' + ', '.join(f'{k} {v}' for k, v in want.items())
                    + f' (vol {a.get("vol")}, {a.get("spacu")})', all(a.get(k) == v for k, v in want.items())))
        mem = zowe('zos-files', 'list', 'all-members', ds, json_out=True)['data']['apiResponse']['items']
        res.append((f'members {ds}', sorted(m['member'] for m in mem) == MEMBERS[n]))
    for m, want in CONTENT.items():
        r = zowe('zos-files', 'view', 'data-set', f"{DSN['HSTEST']}({m})")
        got = [l.rstrip() for l in r.stdout.splitlines() if l.strip()]
        res.append((f'{DSN["HSTEST"]}({m}) = {len(want)} record(s) as seeded', got == want))
    return res


def main():
    args = [a for a in sys.argv[1:] if a != '--catalog']
    job, res = spool_check(args[0])
    if '--catalog' in sys.argv:
        res += catalog_check()
    print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}')
    for k, v in res:
        print(f'  {"OK  " if v else "FAIL"} {k}')
    bad = sum(not v for _, v in res)
    print('HS SETUP CHECK ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
