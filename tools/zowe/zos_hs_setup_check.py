#!/usr/bin/env python3
"""ZOS-3 PACZ3HA check: the high-score test PDSs of one attempt (docs/zos3-design.md, tools/zowe/zos_target.py
z3ha_deck). Read-only.

Usage: zos_hs_setup_check.py SPOOLDIR [--catalog]
       zos_hs_setup_check.py --gate      (read-only: the --catalog checks alone, before PACZ3HS is submitted)
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


ECHO = re.compile(r"^  LISTDS '([A-Z0-9$#@.]+)' MEMBERS$")
ATTR = re.compile(r'^  (\S+) +(\d+) +(\d+) +(\S+)$')
VOL = re.compile(r'^  [A-Z0-9$#@]{1,6}$')
MEMBER = re.compile(r'^  ([A-Z$#@][A-Z0-9$#@]{0,7})$')


def listds(lines):
    """{dsname: (recfm, lrecl, blksize, dsorg, [members])} from the SYSTSPRT of IKJEFT01 running LISTDS ... MEMBERS
    (VBA: column 1 is the ASA control character; record padding removed). The exact shape of JOB02091:
      READY                                   TMP prompt (first record, ASA '1')
        LISTDS '<dsn>' MEMBERS                the command echo starts one extent
      <dsn>
      --RECFM-LRECL-BLKSIZE-DSORG
        <recfm> <lrecl> <blksize> <dsorg>
      --VOLUMES--
        <volser>                              one or more
      --MEMBERS--
        <member>                              zero or more, indented 2 (a member named END is '  END')
      READY                                   unindented: ends the extent
      END                                     unindented, only as the very last record: end of SYSTSIN
    Anything else (another line inside an extent, a missing READY, a second echo before READY, END elsewhere, a
    duplicated dataset) returns None: the output is not interpreted at all (fail closed)."""
    body = [l.rstrip() for l in lines]
    while body and body[-1] == '':
        body.pop()
    if not body or any(l[:1] not in (' ', '1', '0', '-', '+') for l in body):
        return None
    body = [l[1:] for l in body]
    if body[0] != 'READY' or body[-1] != 'END':
        return None
    out, i, n = {}, 1, len(body) - 1        # body[n] is the final END: never inside an extent
    while i < n:
        m = ECHO.match(body[i])
        if not m or m.group(1) in out:
            return None
        ds = m.group(1)
        try:
            j = body.index('READY', i + 1)
        except ValueError:
            return None
        ext = body[i + 1:j]
        if j >= n or any(ECHO.match(l) for l in ext):
            return None
        if len(ext) < 7 or ext[0] != ds or ext[1] != '--RECFM-LRECL-BLKSIZE-DSORG' or not ATTR.match(ext[2]) \
                or ext[3] != '--VOLUMES--' or '--MEMBERS--' not in ext:
            return None
        k = ext.index('--MEMBERS--')
        if k < 5 or not all(VOL.match(l) for l in ext[4:k]) or not all(MEMBER.match(l) for l in ext[k + 1:]):
            return None
        out[ds] = ATTR.match(ext[2]).groups() + ([MEMBER.match(l).group(1) for l in ext[k + 1:]],)
        i = j + 1
    return out


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
    res.append(('HSLIST: LISTDS output parsed within each command extent (echo .. READY, final END)', got is not None))
    got = got or {}
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
        names = sorted(m['member'] for m in mem)
        res.append((f'members {ds} = {" ".join(MEMBERS[n]) if n == "HSTEST" else "M01..M20"}', names == MEMBERS[n]))
        if n == 'HSFULL':
            gone = ['HISCORE'] + [f'M{i}' for i in range(21, 31)]
            res.append((f'{ds}: HISCORE and M21..M30 absent', not set(gone) & set(names)))
    for m, want in CONTENT.items():
        r = zowe('zos-files', 'view', 'data-set', f"{DSN['HSTEST']}({m})")
        got = [l.rstrip() for l in r.stdout.splitlines() if l.strip()]
        res.append((f'{DSN["HSTEST"]}({m}) = {len(want)} record(s) as seeded', got == want))
    return res


def main():
    if sys.argv[1:] == ['--gate']:            # ZOS-3 PACZ3HS pre-submit gate: the accepted PACZ3HA state, read-only
        res = catalog_check()
        for k, v in res:
            print(f'  {"OK  " if v else "FAIL"} {k}')
        bad = sum(not v for _, v in res)
        print('HS T1 STATE GATE ' + ('PASS: the accepted PACZ3HA state' if not bad else f'FAIL ({bad}): STOP, do not submit'))
        sys.exit(1 if bad else 0)
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
