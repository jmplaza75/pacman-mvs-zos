#!/usr/bin/env python3
"""ZOS-3 PACZ3FS check: the PACFSIO batch contract (docs/zos3-design.md), steps S1S3 (MVS deck GP2, oracle JOB 310) and
S2L4 (MVS deck S2, oracle JOB 308): TSO line mode with PARM column 12 COLOR A(UTO), so PACPLAT INIT performs TRY-COLOUR,
whose first statement is CALL 'PACFSIO' (FSON); in a batch address space ASCBTSB is zero, PACFSIO returns RC 4 before
any service is issued and PACPLAT stays in TSO line mode.

Usage: zos_fs_check.py SPOOLDIR [--classic SPOOLDIR_OF_PACZ2C7]   (read-only; exit 0 only if everything passes)
1. spool health as tools/zowe/zos_classic_check.py (program PACZ2D, COND CODE 0000, only SYSOUT, STEPLIB once per step,
   no CEE / abend / output-limit text): the steps are exactly S1S3, S2L4;
2. oracle: each step against its own deck's oracle job with tools/zowe/zos_equiv.py --subset (step identity + ordinal
   anchoring, exact, ASA column + record padding only);
3. models: the 1.0-MVS oracle TSO run DIE1 (tests/test_g0.py, as tests/test_s1.py and tests/test_s2.py check these two
   runs) and the independent TSO line-mode model of tests/test_mvs8.py for DIE1 (zos_classic_check.model, step TSO2);
4. line-mode fallback: no data-stream line (TSD / TSX), and with --classic, each step identical to the z/OS run of the
   same game without COLOR (PACZ2C7 TSO2, JOB09031): the COLOR(AUTO) request leaves no trace in the transcript;
5. linkage of the module that ran: the PACZ2D bind of PACZ2BLD JOB08888 includes OBJ(PACFSIO), RC 0, no unresolved
   reference (NODYNAM: CALL 'PACFSIO' is a static V-constant resolved to that CSECT).
"""
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests'), str(R / 'tools')]
from zos_classic_check import health, model  # noqa: E402
from zos_equiv import compare, zos_runs  # noqa: E402
from zos_target import SOURCES  # noqa: E402

STEPS = SOURCES['Z3FS']
ORACLES = {310: R / 'tests/oracle20/310-PACBLGP2.json.gz', 308: R / 'tests/oracle20/308-PACBLDS2.json.gz'}
BLD = R / 'build/zos/PACZ2BLD-JOB08888/115-LINK-SYSPRINT.txt'


def check_runs(runs, oracles=None):
    """Oracle + model + fallback checks of {step: zos_runs entry}; returns (failures, messages)."""
    from test_g0 import oracle as o10
    oracles = oracles or {j: json.load(gzip.open(p)) for j, p in ORACLES.items()}
    want = [l.rstrip() for l in o10()[1]['DIE1']]
    bad, out = 0, []
    if list(runs) != list(STEPS):
        return 1, [f'FAIL steps {list(runs)} != {list(STEPS)}']
    for s, (_, ojob) in STEPS.items():
        nb, msgs = compare(oracles[ojob], {s: runs[s]}, {'PACMAIN': 'PACZ2D'}, subset=True)
        out += [f'oracle {ojob} {m}' for m in msgs if not m.startswith('SUBSET')]
        bad += nb
        got = runs[s]['lines']
        ok = got == want
        out.append(f'model  {"OK  " if ok else "FAIL"} {s}: 1.0-MVS oracle TSO DIE1 ({len(got)} / {len(want)} lines)')
        r = model('TSO2', got)
        out.append(f'model  {"OK  " if r is None else "FAIL"} {s}: test_mvs8 TSO line-mode model DIE1'
                   + (f' - {r}' if r else ''))
        stream = [l for l in got if l.startswith(('TSD ', 'TSX'))]
        out.append(f'fallbk {"OK  " if not stream else "FAIL"} {s}: no data-stream line (TSO line mode)')
        bad += (not ok) + (r is not None) + bool(stream)
    return bad, out


def linkage():
    t = BLD.read_text()
    inc = re.findall(r'INCLUDE OBJ\((\w+)\)', t)
    ok = ('PACFSIO' in inc and 'PACPLAT' in inc and 'NAME PACZ2D(R)' in t and
          'PROCESSING COMPLETED.  RETURN CODE =  0.' in t and not re.search(r'IEW2454W|IEW2456E|UNRESOLVED', t))
    return ok, f'PACZ2BLD JOB08888 bind of PACZ2D: OBJ(PACPLAT) + OBJ(PACFSIO) included, RC 0, nothing unresolved'


def main():
    args = sys.argv[1:]
    classic = None
    if '--classic' in args:
        i = args.index('--classic')
        classic = args[i + 1]
        del args[i:i + 2]
    (d,) = args
    job, steps, runs, hb, lines = health(d)
    print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}: {len(steps)} steps, {lines} spool lines')
    for b in hb:
        print('  FAIL', b)
    bad, msgs = check_runs(runs)
    bad += len(hb)
    for m in msgs:
        print(' ', m)
    if classic:
        ref = zos_runs(classic)[2]['TSO2']['lines']
        for s in STEPS:
            ok = runs[s]['lines'] == ref
            print(f'  fallbk {"OK  " if ok else "FAIL"} {s}: identical to the z/OS COLOR(N) run of DIE1 '
                  f'({Path(classic).name} TSO2)')
            bad += not ok
    ok, m = linkage()
    print(f'  link   {"OK  " if ok else "FAIL"} {m}')
    bad += not ok
    print('PACFSIO BATCH CONTRACT CHECK ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
