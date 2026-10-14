#!/usr/bin/env python3
"""ZOS-2 ARCADE (MVS-GP2) check of a z/OS run job built from the GP2 deck (oracle JOB 310): spool health as in
tools/zowe/zos_classic_check.py, tools/zowe/zos_equiv.py --subset against tests/oracle20/310-PACBLGP2.json.gz, and the
independent model tests/ref_gp2.py exactly as tests/test_gp2.py applies it:
  G2B<i> (GP2_BAT[i]: directory, case, start text)  = ref_gp2.simulate(cards, start=parse_start(start text));
  G2T<i> (GP2_TSO[i]: case, start text)             = ref_gp2.simulate(cards[1:], prompts=True, cfg=config card,
                                                      redraw=True, start=parse_start(start text)).
Usage: zos_arcade_check.py SPOOLDIR [SPOOLDIR ...]   (read-only; exit 0 only if everything passes)
"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests'), str(R / 'tools')]
from zos_classic_check import health  # noqa: E402
from zos_equiv import compare  # noqa: E402
import ref_gp2 as L  # noqa: E402
from make_deck import GP2_BAT, GP2_TSO  # noqa: E402

ORACLE = R / 'tests/oracle20/310-PACBLGP2.json.gz'


def cards(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


def expected(step):
    i = int(step[3:]) - 1
    if step.startswith('G2B'):
        d, c, st = GP2_BAT[i]
        return f'{d}/{c} start {st!r}', L.simulate(cards(d, c), start=L.parse_start(st))
    if step.startswith('G2T'):
        c, st = GP2_TSO[i]
        cs = cards('gpcases', c)
        ai, n, _ = L.parse_config(cs[:1])
        return f'TSO gpcases/{c} start {st!r}', L.simulate(cs[1:], prompts=True, cfg=(ai, n), redraw=True,
                                                           start=L.parse_start(st))
    return None, None


def main():
    oracle = json.load(gzip.open(ORACLE))
    bad = 0
    for d in sys.argv[1:]:
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
            what, want = expected(s)
            if want is None:
                print(f'  model  FAIL {s}: no model mapping')
                bad += 1
                continue
            want = [l.rstrip() for l in want]
            got = runs[s]['lines']
            ok = got == want
            i = next((k for k, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
            print(f'  model  {"OK  " if ok else "FAIL"} {s} {what}: {len(got)} lines'
                  + ('' if ok else f' - first difference at line {i + 1}'))
            bad += not ok
    print('ARCADE CHECK ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
