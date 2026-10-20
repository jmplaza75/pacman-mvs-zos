#!/usr/bin/env python3
"""ZOS-7 ARCADE live scenarios (docs/zos7-design.md, decisions 2026-10-19): the REALTIME wall-stop plan of L2 (NORMAL)
and L3 (FAST) and its offline robustness proof; L1 = the MVS scenario B (tests/gp2live/LIVEB.txt, TURN, LEVEL 13).

The REALTIME plan is a list of (gameplay key, seconds after the previous key was sent). Every key is sent while
Pac-Man stands at a wall or after a respawn, so his path does not depend on the exact landing quantum:
  PF8   start: down column 2 over both power pellets (2,4) (2,8), stop at (2,9)
  PF11  right along row 9 into the AI(0) ghost at its home (19,9) while it is frightened: 200, eyes
  PF10  leave the home cell to (2,9)
  PF11  back into the revived ghost: death 1
  PF8   after a 34 s quiet run (the principal segment of the frozen ZOS-6 gates, >= 200 logical quanta), down again
  PF11  death 2
  PF8, PF11  death 3 = GAME OVER (the final-death sequence, decision D1)
The second key must land after Pac-Man reached (2,9) (card >= 8, else he turns into row 4 / 8) and early enough to
reach the ghost inside the LEVEL 2 fright (34 quanta NORMAL, 41 FAST): 2.1 s is inside that window at both speeds
with a +/- 5 quanta margin. The proof replays every combination of a -5 / 0 / +5 quanta shift of each key's landing
relative to the previous key (3^7 runs per speed) through the independent model (tests/ref_gp2.py rt_simulate) and
requires the intended outcome every time.
Usage: zos7_scen.py [--prove]     print the canonical cards / outcome per speed (and run the proof)"""
import itertools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests')]
import ref_gp2 as L  # noqa: E402
import ref_rt  # noqa: E402

CFG, START = 'AI0 1', 2
KEYS = [('PF8', 2.0), ('PF11', 2.1), ('PF10', 6.0), ('PF11', 5.0), ('PF8', 34.0), ('PF11', 3.0), ('PF8', 6.0),
        ('PF11', 3.0)]
CHAR = {'PF7': 'U', 'PF8': 'D', 'PF10': 'L', 'PF11': 'R'}
# the intended outcome: LOST after 3 deaths, one ghost eaten, SCORE 0000510 (decision D4)
EXPECT = {'end': 'LOST', 'score': 510, 'ghosts': 1, 'lives': 0}
TAIL = 120                                     # idle cards after the last key (the game ends before them)
SHIFTS = (-5, 0, 5)


def gaps(per):
    """Nominal landing distance (quanta) of each key after the previous one; the first key is the start (card 1)."""
    return [round(s * 1000 / per) for _, s in KEYS[1:]]


def cards(per, deltas=None):
    """The cards (one per quantum, card 1 = the start key) for landing shifts `deltas` (one per key after the first)."""
    deltas = deltas or [0] * (len(KEYS) - 1)
    pos = [1]
    for g, d in zip(gaps(per), deltas):
        pos.append(pos[-1] + g + d)
    out = ['.'] * (pos[-1] + TAIL)
    for p, (k, _) in zip(pos, KEYS):
        out[p - 1] = CHAR[k]
    return out


def outcome(lines):
    """-> dict(end, score, ghosts, lives, quanta) from the ARCADE REALTIME end lines."""
    e = lines[-8:]
    return {'end': e[0], 'score': int(e[2][6:]), 'lives': int(e[3][6:]), 'quanta': int(e[4][7:]),
            'ghosts': int(e[5][13:])}


def run(per, deltas=None):
    return outcome(L.rt_simulate([CFG] + cards(per, deltas), start=START, per=per))


def intended(o):
    return all(o[k] == v for k, v in EXPECT.items())


def prove(per):
    """-> (runs, failures): every key-landing shift combination keeps the intended outcome."""
    bad, n = [], 0
    for d in itertools.product(SHIFTS, repeat=len(KEYS) - 1):
        n += 1
        o = run(per, list(d))
        if not intended(o):
            bad.append((d, o))
    return n, bad


def liveb():
    """L1: the MVS scenario B cards (config card first)."""
    return (R / 'tests/gp2live/LIVEB.txt').read_text().splitlines()


def main():
    for per in (ref_rt.NORMAL, ref_rt.FAST):
        o = run(per)
        print(f'T {per}: gaps {gaps(per)} -> {o} intended {intended(o)}')
        if '--prove' in sys.argv:
            n, bad = prove(per)
            print(f'  proof: {n} shift combinations, {len(bad)} without the intended outcome')
            for d, x in bad[:5]:
                print(f'    {d}: {x}')
    lb = liveb()
    print(f'L1: {len(lb) - 1} TURN commands, end {L.simulate(lb, start=13)[-7:]}')


if __name__ == '__main__':
    main()
