#!/usr/bin/env python3
"""MVS-GP2 GP2.4: builds the live scenario card files tests/gp2live/LIVE[ABC].txt from the GP2 edge cases and checks
them against the independent model (tests/ref_gp2.py). A REALTIME direction card is dropped ('.') when the model shows
it is redundant (the same as Pac-Man's current direction with no request pending), so the live driver sends a key
only when it matters; the game must stay identical. A: G2RCLR (level 1 -> 2) + a pause and a PA2 while the second
fruit is shown and a PA2 on level 2; B: G2XF (TURN, LEVEL 13); C: G2RXD (REALTIME, LEVEL 13).
Usage: make_live.py"""
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(R / 'tests'))
import ref_gp2 as L  # noqa: E402
import ref_rt  # noqa: E402


def strip(lines):
    return [re.sub(r' IN=.{8}', ' ', l) for l in lines]


def lean(cards, start):
    """Drop the direction cards that change nothing (model controller state before each quantum)."""
    ai, n, rest = L.parse_config(cards)
    g = L.Level(ai, n, 'R', start)
    c = L.LevelRT(g)
    out = []
    for card in rest:
        keep = card
        if len(card) == 1 and card in 'UDLR' and c.started and c.cur == card and c.req == ' ' and not c.frz:
            keep = '.'
        out.append(keep)
        for kind, d, ch in next(ref_rt.events([card])):
            if kind in ('MOV', 'PAU', 'RDR', 'INV'):
                c.rin(kind, d, ch)
            if kind == 'QUI':
                return cards[:1] + out
        if c.status() in ('PAUS', 'WAIT'):
            continue
        c.rq()
    return cards[:1] + out


def build():
    a = (R / 'tests/gp2cases/G2RCLR.txt').read_text().splitlines()
    la = lean(a, 1)
    assert strip(L.rt_simulate(la, 1)) == strip(L.rt_simulate(a, 1))
    body = la[1:]
    idle = [i for i, x in enumerate(body) if x == '.']
    p = next(i for i in idle if i + 1 >= 108)              # body[i] = the input of quantum i + 1
    body[p:p + 1] = ['P', 'P']
    r1 = next(i for i, x in enumerate(body) if x == '.' and i >= 120)
    body[r1] = '*'
    r2 = next(i for i, x in enumerate(body) if x == '.' and i >= 197)
    body[r2] = '*'
    A = la[:1] + body
    assert strip(L.rt_simulate(A, 1)) == strip(L.rt_simulate(a, 1)), 'pause / PA2 must change nothing in the game'
    c = (R / 'tests/gp2cases/G2RXD.txt').read_text().splitlines()
    C = lean(c, 13)
    assert strip(L.rt_simulate(C, 13)) == strip(L.rt_simulate(c, 13))
    B = (R / 'tests/gp2cases/G2XF.txt').read_text().splitlines()
    return {'LIVEA': A, 'LIVEB': B, 'LIVEC': C}


if __name__ == '__main__':
    for k, cs in build().items():
        (R / f'tests/gp2live/{k}.txt').write_text('\n'.join(cs) + '\n')
        print(k, cs[0], len(cs) - 1, 'cards,', sum(1 for x in cs[1:] if x != '.'), 'key actions')
