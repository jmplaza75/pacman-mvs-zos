#!/usr/bin/env python3
"""ZOS-2 ARCADE (MVS-GP2) check of a z/OS run job built from the GP2 deck (oracle JOB 310): spool health as in
tools/zowe/zos_classic_check.py, tools/zowe/zos_equiv.py --subset against tests/oracle20/310-PACBLGP2.json.gz, and the
independent model tests/ref_gp2.py exactly as tests/test_gp2.py applies it:
  G2B<i> (GP2_BAT[i]: directory, case, start text)  = ref_gp2.simulate(cards, start=parse_start(start text));
  G2T<i> (GP2_TSO[i]: case, start text)             = ref_gp2.simulate(cards[1:], prompts=True, cfg=config card,
                                                      redraw=True, start=parse_start(start text));
  G2R<i> (GP2_RT[i]: directory, case, start text)   = ref_gp2.rt_simulate(cards, parse_start(start text));
  RTB<i> (RT_BAT[i], CLASSIC REALTIME)              = ref_rt.simulate(cards)              (tests/test_rt.py);
  S1S<i> (S1_SILENT[i]: BAT / RTB / TSO, SOUND Y)   = the 1.0-MVS oracle run / ref_rt.simulate (tests/test_s1.py);
  QRY1 (PACQRYT driver of PACQRY)                   = one QRY line per recorded reply (qry_cases.expect,
                                                      expect_size: tests/test_g4.py, test_gs.py), the QSL startup
                                                      sequences (qry_cases.seq_lines: tests/test_rp.py), QRY TEST END;
  RUN<i> / TSO<i> (the 1.0-MVS oracle runs of the GP2 deck) = tests/test_mvs8.py models (zos_classic_check.model);
  TSOT1 (PACTSOT driver of the PACTSO clock)        = real elapsed times: checked with the RT3 rules of tests/test_rt.py
                                                      (zos_equiv --clock) instead of an exact comparison.
  R3B<i> (RP3_BAT[i], the RP deck, oracle JOB 309)  = tests/test_rp.py: CLASSIC TURN = the 1.0-MVS oracle run,
                                                      CLASSIC REALTIME = ref_rt.simulate(cards, per=period(speed)),
                                                      ARCADE = ref_gp2.rt_simulate / simulate with the start level and
                                                      period (anchoring: zos_equiv.anchors, its KNOWN_BOUNDARIES entry).
Usage: zos_arcade_check.py [--oracle 309] SPOOLDIR [SPOOLDIR ...]   (default oracle 310; read-only; exit 0 only if
       everything passes)
"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests'), str(R / 'tools')]
from zos_classic_check import BUILD, health  # noqa: E402
from zos_equiv import compare  # noqa: E402
import ref_gp2 as L  # noqa: E402
import ref_rt  # noqa: E402
from make_deck import GP2_BAT, GP2_RT, GP2_TSO, RP3_BAT, RT_BAT, S1_SILENT  # noqa: E402
from zos_equiv import clock_ok  # noqa: E402

CLOCK = {'TSOT1'}
PMAP = {'PACMAIN': 'PACZ2D', 'PACQRYT': 'PACQRYT', 'PACTSOT': 'PACTSOT'}

ORACLES = {'310': R / 'tests/oracle20/310-PACBLGP2.json.gz', '309': R / 'tests/oracle20/309-PACBLDRP.json.gz'}


def cards(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


def expected(step):
    if step == 'QRY1':
        from qry_cases import cases, expect, expect_size, seq_lines
        out = []
        for name, b in cases():
            c, h, g = expect(b)
            aw, ah = expect_size(b)
            out.append(f'QRY {name:<8} LEN={len(b):04d} C={c} H={h} GE={g} AW={aw:03d} AH={ah:03d}')
        return 'PACQRYT recorded replies + startup sequences', out + seq_lines() + ['QRY TEST END']
    if step in CLOCK:
        return 'PACTSOT clock (RT3 timing rules)', None
    if step.startswith('R3B'):                 # tests/test_rp.py, the RP3 BAT runs
        play, d, c, rules, st, sp = RP3_BAT[int(step[3:]) - 1]
        cs, start, per = cards(d, c), L.parse_start(st), ref_rt.period(sp)
        if rules == 'C':
            if play == 'T':
                from test_g0 import oracle
                return f'CLASSIC TURN {d}/{c} = 1.0-MVS oracle', oracle()[0][c]
            return f'CLASSIC REALTIME {d}/{c} per {per}', ref_rt.simulate(cs, per=per)
        if play == 'R':
            return f'ARCADE REALTIME {d}/{c} per {per}', L.rt_simulate(cs, start, per=per)
        return f'ARCADE TURN {d}/{c}', L.simulate(cs, start=start)
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
    if step.startswith('G2R'):
        d, c, st = GP2_RT[i]
        return f'REALTIME {d}/{c} start {st!r}', L.rt_simulate(cards(d, c), L.parse_start(st))
    if step.startswith('RTB'):
        c = RT_BAT[i]
        return f'CLASSIC REALTIME rtcases/{c}', ref_rt.simulate(cards('rtcases', c))
    if step.startswith('S1S'):
        kind, c = S1_SILENT[i]
        if kind == 'RTB':
            return f'CLASSIC REALTIME rtcases/{c} SOUND Y', ref_rt.simulate(cards('rtcases', c))
    return None, None


def cross_check(d1, d2):
    """PACZ2ST0 / PACZ2STF: the same steps in the same order, and every step's application SYSOUT identical (ASA column
    and record padding removed as everywhere, nothing else). Returns (identical, number of steps)."""
    from zos_equiv import zos_runs
    r1, r2 = zos_runs(d1)[2], zos_runs(d2)[2]
    return list(r1) == list(r2) and all(r1[k]['lines'] == r2[k]['lines'] for k in r1), len(r1)


def main():
    if sys.argv[1:2] == ['--oracle']:
        oname = sys.argv[2]
        del sys.argv[1:3]
    else:
        oname = '310'
    oracle = json.load(gzip.open(ORACLES[oname]))
    bad = 0
    for d in sys.argv[1:]:
        job, steps, runs, hb, lines = health(d, tuple(PMAP.values()))
        print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}: {len(steps)} steps, {lines} spool lines')
        for b in hb:
            print('  FAIL', b)
        nb, msgs = compare(oracle, runs, PMAP, subset=True, clock=CLOCK)
        for m in msgs:
            if not m.startswith('SUBSET'):
                print('  oracle', m)
        bad += len(hb) + nb
        for s in steps:
            if runs[s]['pgm'] in BUILD:
                continue                       # build steps: health above + zos_compile_report
            if s[:3] in ('RUN', 'TSO') and s[3:].isdigit():
                from zos_classic_check import CASE, model
                r = model(s, runs[s]['lines'])
                print(f'  model  {"OK  " if r is None else "FAIL"} {s} CLASSIC {CASE[s]}: {len(runs[s]["lines"])} lines'
                      + (f' - {r}' if r else ''))
                bad += r is not None
                continue
            what, want = expected(s)
            if s in CLOCK:
                ok = clock_ok(runs[s]['lines'])
                print(f'  model  {"OK  " if ok else "FAIL"} {s} {what}: {len(runs[s]["lines"])} lines')
                bad += not ok
                continue
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
    if len(sys.argv) == 3:                     # two jobs of the same steps (PACZ2ST0 / PACZ2STF): identical output
        same, n = cross_check(*sys.argv[1:])
        print(f'cross-check: {n} steps, every SYSOUT identical between the two jobs: {same}')
        bad += not same
    print('ARCADE CHECK ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
