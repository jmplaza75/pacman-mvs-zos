#!/usr/bin/env python3
"""ZOS-3 PACZ3HS1..8: the stateful HS sequence (tools/zowe/zos_target.py HS_JOBS; HA6 deferred) - state gates and
job checks. Read-only.

Usage: zos_hs_check.py --gate N                 before submitting PACZ3HS<N>: the T1 PDSs must hold exactly the state
                                                the accepted jobs 1..N-1 produce (N=1: the accepted PACZ3HA state)
       zos_hs_check.py SPOOLDIR --job N         after PACZ3HS<N>: spool + oracle + model checks, then the state the
                                                job must leave (read-only catalog / member / content queries)
       zos_hs_check.py --plan                   print every job's steps, expected HS lines and the state after it
State = ref_hs (tools/zowe/zos_hs_model.py: the frozen test_hs model, PACMAN_LATER_PHASE=G8) replayed in the frozen
order without HA6: HSTEST.T1 members and their exact records; HSFULL.T1 always exactly M01..M20 (no HISCORE); both
PDS / PO / FB / 80 / 80, catalogued, not migrated.
Job checks: every step COND CODE 0000; no ABEND / IEA995 / $HASP375 / S722 / CEE text; spool DDs = SYSOUT per PACZ2D
step, SYSTSPRT + SYSOUT per IKJEFT01 step; STEPLIB Z00000.PACMAN.LOAD retained once per PACZ2D step; datasets in
JESYSMSG only the load library and the two T1 PDSs (besides the job's own JES datasets); no IEC message except in
PACZ3HS8, and there exactly one: IEC217I B14-0C on HH1 / PACHS continued by Z00000.PACMAN.HSFULL.T1(HISCORE) (hh1_b14); PACZ2D steps = their own oracle 312 block (zos_equiv --subset,
the digest-bound HA1 boundary) and = the model (text: base + HS lines; TSD: rp_streams + end lines); HTSO<i> SYSOUT =
the model exactly (tests prove model = oracle 312 lines 25366 / 25744 for the frozen digest; no runtime search) and
SYSTSPRT without any IKJ message.
"""
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path.insert(0, str(HERE))
import zos_hs_model as M  # noqa: E402
from zos_equiv import compare, zos_runs  # noqa: E402
from zos_target import HS_DEFERRED, HS_JOBS  # noqa: E402
from zos_hs_setup_check import DSN, MEMBERS  # noqa: E402

HLQ = 'Z00000'
LOAD = f'{HLQ}.PACMAN.LOAD'
ORACLE = R / 'tests/oracle20/312-PACBLDHS.json.gz'
JOBS = list(HS_JOBS.values())


def expected_states():
    """[state before job 1, after job 1, ..., after job 8]: {member: [records rstripped]} of HSTEST.T1."""
    st = {s: (b, a) for s, b, a, _, _ in M.states(skip=tuple(HS_DEFERRED))}
    norm = lambda m: {k: [r.rstrip() for r in v] for k, v in m.items()}   # noqa: E731
    out = [norm(st[JOBS[0][0]][0])]
    for steps in JOBS:
        out.append(norm(st[steps[-1]][1]))
    return out


def hs_lines():
    return {s: hs for s, _, _, _, hs in M.states(skip=tuple(HS_DEFERRED))}


def catalog_state(want):
    """Read-only z/OSMF queries of the two T1 PDSs only: (name, ok) results against the HSTEST state want."""
    from zoslib import zowe
    res = []
    for n, ds in DSN.items():
        items = zowe('zos-files', 'list', 'data-set', ds, '-a', json_out=True)['data']['apiResponse']['items']
        a = items[0] if len(items) == 1 and items[0]['dsname'] == ds else {}
        attrs = {'dsntp': 'PDS', 'dsorg': 'PO', 'recfm': 'FB', 'lrecl': '80', 'blksz': '80', 'migr': 'NO'}
        res.append((f'catalog {ds}: PDS PO FB 80 80, not migrated', all(a.get(k) == v for k, v in attrs.items())))
        names = sorted(m['member'] for m in
                       zowe('zos-files', 'list', 'all-members', ds, json_out=True)['data']['apiResponse']['items'])
        if n == 'HSFULL':
            res.append((f'{ds} members exactly M01..M20, HISCORE absent', names == MEMBERS['HSFULL']))
        else:
            res.append((f'{ds} members exactly {" ".join(sorted(want))}', names == sorted(want)))
            for m in sorted(want):
                got = [l.rstrip() for l in zowe('zos-files', 'view', 'data-set', f'{ds}({m})').stdout.splitlines()
                       if l.strip()]
                res.append((f'{ds}({m}) = {want[m] if want[m] else "no record"}', got == want[m]))
    return res


def hh1_b14(msg, jobname):
    """The z/OS form of the HH1 failure in JESYSMSG (JOB02433): one IEC message in the whole job log,
      IEC217I B14-0C,<module>,<job>,HH1,PACHS,<device>,<volser>,
      <HLQ>.PACMAN.HSFULL.T1(HISCORE)
    the continuation being the very next record, without a message id (MVS repeated 'IEC217I' on it: JOB 312). Any other
    shape - no continuation, another dataset / member, another step / DD / code, a second IEC message - is False."""
    lines = [l.strip() for l in msg.splitlines()]
    at = [i for i, l in enumerate(lines) if re.search(r'IEC\d{3}I', l)]
    if len(at) != 1:
        return False
    i = at[0]
    return (bool(re.fullmatch(rf'IEC217I B14-0C,[A-Z0-9]+,{re.escape(jobname)},HH1,PACHS,[0-9A-F]{{3,4}},[A-Z0-9$#@]{{1,6}},',
                              lines[i]))
            and i + 1 < len(lines) and lines[i + 1] == f'{DSN["HSFULL"]}(HISCORE)')


def spool_check(d, n):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = json.loads((d / 'spool.json').read_text())
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    jes = ''.join(p.read_text() for p in d.glob('00*-JES2-*.txt'))
    _, steps, runs = zos_runs(d)
    want_steps = JOBS[n - 1]
    res = [(f'steps {" ".join(want_steps)}', steps == want_steps)]
    for s in want_steps:
        res.append((f'{s} COND CODE 0000',
                    bool(re.search(rf'IEF142I {job["jobname"]} {s} - STEP WAS EXECUTED - COND CODE 0000', msg))))
    res.append(('no ABEND / IEA995 / $HASP375 / S722 / CEE message', not re.search(r'ABEND|IEA995|\$HASP375|S722|CEE\d{4}', jes)))
    want_dd = set()
    for s in want_steps:
        want_dd |= {(s, 'SYSTSPRT'), (s, 'SYSOUT')} if s.startswith('HTSO') else {(s, 'SYSOUT')}
    got_dd = {(f['stepname'], f['ddname']) for f in files if f['stepname'] != 'JES2'}
    res.append(('spool DDs: SYSOUT per run, SYSTSPRT + SYSOUT per IKJEFT01 step', got_dd == want_dd))
    nrun = sum(not s.startswith('HTSO') for s in want_steps)
    res.append(('STEPLIB Z00000.PACMAN.LOAD retained once per PACZ2D step',
                len(re.findall(rf'IGD104I {re.escape(LOAD)}\s+RETAINED,\s+DDNAME=STEPLIB', msg)) == nrun))
    own = f'{HLQ}.{job["jobname"]}.{job["jobid"]}.'
    named = {x.rstrip('.') for x in re.findall(rf'\b({HLQ}\.[\w.$#@]+)', msg) if not x.startswith(own)}
    res.append(('datasets in JESYSMSG only the load library and the T1 PDSs',
                named <= {LOAD} | set(DSN.values())))
    iec = [l.strip() for l in msg.splitlines() if re.search(r'IEC\d{3}I', l)]
    if 'HH1' in want_steps:
        res.append(('HH1: exactly one IEC event, IEC217I B14-0C on HH1 / PACHS (directory full), continued by '
                    f'{DSN["HSFULL"]}(HISCORE)', hh1_b14(msg, job['jobname'])))
    else:
        res.append(('no IEC message (no data-management failure)', not iec))
    oracle = json.load(gzip.open(ORACLE))
    pz = {s: r for s, r in runs.items() if r['pgm'] == 'PACZ2D'}
    nb, msgs = compare(oracle, pz, {'PACMAIN': 'PACZ2D'}, subset=True)
    for m in msgs:
        if not m.startswith('SUBSET'):
            res.append((f'oracle 312 {m[5:]}', m.startswith('OK')))
    if nb and not any(m.startswith('FAIL') for m in msgs):
        res.append(('oracle 312 compare', False))
    ns = M.model()
    kinds = {st: kind for st, kind, *_ in ns['HS_RUNS']}
    hs = hs_lines()
    for s in want_steps:
        got = runs[s]['lines']
        if s.startswith('HTSO') or kinds[s] not in ('T', 'Q'):
            w = M.expected_text(s)
            res.append((f'{s} SYSOUT = model ({len(w)} lines, ends {hs[s][-1] if hs[s] else "no HS line"!r})',
                        got == w))
        else:
            k = kinds[s]
            streams, ends, j = ns['tsd_run'](got, 0, (7 if k == 'T' else 8) + len(hs[s]))
            res.append((f'{s} TSD streams = rp_streams model, end lines with {hs[s]}, nothing after',
                        streams == ns['rp_streams'](k) and ends[-len(hs[s]):] == hs[s] and j == len(got)))
        if s.startswith('HTSO'):
            tp = (d / next(f'{f["id"]:03d}-{s}-SYSTSPRT.txt' for f in files
                           if (f['stepname'], f['ddname']) == (s, 'SYSTSPRT'))).read_text()
            res.append((f'{s} SYSTSPRT: no IKJ message', not re.search(r'IKJ\d{5}', tp)))
    return job, res


def show(res):
    for k, v in res:
        print(f'  {"OK  " if v else "FAIL"} {k}')
    return sum(not v for _, v in res)


def main():
    a = sys.argv[1:]
    states = expected_states()
    if a[:1] == ['--plan']:
        hs = hs_lines()
        for n, steps in enumerate(JOBS, 1):
            print(f'PACZ3HS{n}: ' + ', '.join(f'{s} [{" / ".join(hs[s]) or "no HS line"}]' for s in steps))
            print('   after: ' + ' '.join(f'{m}={v[0][:7] if v else "-"}' for m, v in sorted(states[n].items())))
        return
    if a[:1] == ['--gate']:
        n = int(a[1])
        print(f'gate before PACZ3HS{n}: HSTEST.T1 = state after '
              + ('the accepted PACZ3HA' if n == 1 else f'PACZ3HS{n - 1}'))
        bad = show(catalog_state(states[n - 1]))
        print(f'HS STATE GATE {n} ' + ('PASS: submit allowed' if not bad else f'FAIL ({bad}): STOP, do not submit'))
        sys.exit(1 if bad else 0)
    d, n = a[0], int(a[a.index('--job') + 1])
    job, res = spool_check(d, n)
    print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")} (PACZ3HS{n})')
    bad = show(res)
    print(f'state after PACZ3HS{n} (read-only):')
    bad += show(catalog_state(states[n]))
    print(f'PACZ3HS{n} CHECK ' + ('PASS' if not bad else f'FAIL ({bad}): STOP the sequence'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
