#!/usr/bin/env python3
"""ZOS-2 CLASSIC oracle check of one or more z/OS run jobs (PACZ2C1..C7: the 19 batch runs and 6 TSO line-mode
replays of the 1.0-MVS oracle, steps RUN1..RUN19 / TSO1..TSO6 of oracle JOB 307).

Usage: zos_classic_check.py SPOOLDIR [SPOOLDIR ...] [--all]
Per job (tools/zowe/zos_submit.py spool directory):
1. spool health: every step executed (IEF142I) with COND CODE 0000, program PACZ2D, STEPLIB Z00000.PACMAN.LOAD
   retained (IGD104I) once per step, no CEE / abend / $HASP375 / IEA995 text in the JES files, and no spool file other
   than the JES files and one SYSOUT per step;
2. oracle: tools/zowe/zos_equiv.py --subset against tests/oracle20/307-PACREL20.json.gz (exact, ASA + padding only);
3. independent models, the runtime checks of tests/test_mvs8.py (imported: its local checks run first): a batch run
   equals tests/expected/MVS6-<case> and satisfies the behaviour rules re-derived from the output; a TSO run, read up
   to its LIVES line, has no DBG line, equals the batch reference without prompts, shows the board before the first
   prompt and has one prompt per read.
--all: the given jobs must cover the 25 CLASSIC runs exactly once, in oracle order across the jobs (the combined
validation; the MVS-7 before/after comparison of tests/test_mvs8.py is applied to the 19 batch runs as well).
Exit 0 only if everything passes. Read-only.
"""
import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(R / 'tests'))
from zos_equiv import compare, zos_runs  # noqa: E402

_argv, sys.argv = sys.argv, sys.argv[:1]
import test_mvs8 as T  # noqa: E402  (module-level local checks run here and must pass)
sys.argv = _argv

LOAD = 'Z00000.PACMAN.LOAD'
ORACLE = R / 'tests/oracle20/307-PACREL20.json.gz'
CASE = dict([(f'RUN{i}', n) for i, n in enumerate(T.RUNS, 1)] + [(f'TSO{i}', n) for i, n in enumerate(T.TSO, 1)])


def health(d):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = json.loads((d / 'spool.json').read_text())
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    jes = ''.join(p.read_text() for p in d.glob('00*-JES2-*.txt'))
    bad = []
    if re.search(r'CEE\d{4}|ABEND|\$HASP375|IEA995|IEF472I', jes):
        bad.append('CEE / abend / output-limit text in the JES files')
    _, steps, runs = zos_runs(d)
    for s in steps:
        if not re.search(rf'IEF142I {job["jobname"]} {s} - STEP WAS EXECUTED - COND CODE 0000', msg):
            bad.append(f'{s}: not executed with COND CODE 0000')
        if runs[s]['pgm'] != 'PACZ2D' or runs[s]['extra']:
            bad.append(f'{s}: program {runs[s]["pgm"]}, extra spool {runs[s]["extra"]}')
    if len(re.findall(rf'IGD104I {re.escape(LOAD)}\s+RETAINED,\s+DDNAME=STEPLIB', msg)) != len(steps):
        bad.append('STEPLIB Z00000.PACMAN.LOAD not retained once per step')
    others = [f['ddname'] for f in files if f['stepname'] != 'JES2' and f['ddname'] != 'SYSOUT']
    if others:
        bad.append(f'unexpected spool DD {others}')
    lines = sum(len(p.read_text().splitlines()) for p in d.glob('[0-9]*.txt'))
    return job, steps, runs, bad, lines


def model(step, got):
    n = CASE[step]
    if step.startswith('RUN'):
        if got != T.exp[n]:
            i = next((k for k, (a, b) in enumerate(zip(got, T.exp[n])) if a != b), min(len(got), len(T.exp[n])))
            return f'differs from MVS6-{n} at line {i + 1}'
        T.behaviour(got, *T.counts[n])
        return None
    end = next((i for i, l in enumerate(got) if l.startswith('LIVES ')), None)
    if end is None or end != len(got) - 1:
        return 'TSO transcript does not end at its LIVES line'
    if any(l.startswith('DBG ') for l in got):
        return 'diagnostic line in the TSO transcript'
    plain = [l for l in got if l != T.PROMPT]
    if plain != T.tso_exp[n]:
        return 'TSO transcript without prompts differs from the batch reference'
    if got.index(T.PROMPT) <= got.index(next(l for l in got if l.startswith('T000 '))) + 10:
        return 'prompt before the board'
    reads = (sum(1 for l in plain if re.match(r'T\d{3} ', l)) - 1 + sum('INVALID COMMAND' in l for l in plain)
             + (plain[-4] in ('QUIT', 'EOF')))
    if got.count(T.PROMPT) != reads:
        return f'{got.count(T.PROMPT)} prompts for {reads} reads'
    if n in T.counts:
        T.behaviour(plain, *T.counts[n])
    return None


def main():
    args = [a for a in sys.argv[1:] if a != '--all']
    oracle = json.load(gzip.open(ORACLE))
    bad, seen = 0, []
    for d in args:
        job, steps, runs, hb, lines = health(d)
        print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}: {len(steps)} steps, {lines} spool lines')
        for b in hb:
            print('  FAIL', b)
        nb, msgs = compare(oracle, runs, {'PACMAIN': 'PACZ2D'}, subset=True)
        for m in msgs:
            if not m.startswith('SUBSET'):
                print('  oracle', m)
        bad += len(hb) + nb
        for s in steps:
            r = model(s, runs[s]['lines'])
            print(f'  model  {"OK  " if r is None else "FAIL"} {s} {CASE[s]}: {len(runs[s]["lines"])} lines'
                  + (f' - {r}' if r else ''))
            bad += r is not None
            seen.append(s)
    if '--all' in sys.argv:
        want = [f'RUN{i}' for i in range(1, 20)] + [f'TSO{i}' for i in range(1, 7)]
        ok = seen == want
        print(f'combined: {len(seen)} CLASSIC runs, order and coverage = oracle 307: {ok}')
        bad += not ok
        before = (R / 'docs/evidence/mvs7-refactor.txt').read_text().splitlines()
        bst = [i for i, l in enumerate(before) if l == 'PACMAN MVS-6 SMART GHOSTS']
        if ok and len(bst) == 19:
            allruns = {}
            for d in args:
                allruns.update(zos_runs(d)[2])
            same = all(before[b:b + len(T.exp[n])] == allruns[f'RUN{i}']['lines']
                       for i, (b, n) in enumerate(zip(bst, T.RUNS), 1))
            print(f'combined: 19 batch runs identical to the MVS-7 before/after evidence: {same}')
            bad += not same
    print('CLASSIC CHECK ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
