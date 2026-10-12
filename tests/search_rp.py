#!/usr/bin/env python3
"""MVS-RP (D39, D12): which documented RP edge cases (docs/RP-POLISH.md section 9) a TSD run reaches, measured on the
independent models (ref_rp.Tracker wrapped). cover(kind, d, case, ...) -> set of edge names. Usage: search_rp.py
prints the coverage of the RP deck runs (tools/make_deck.py RP_TURN / RP_RT) and the edges still missing."""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tools'))
import ref_rp  # noqa: E402
import ref_gp2 as L  # noqa: E402
import ref_rt  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
from ref_mvs6 import parse_config, START  # noqa: E402

EDGES = ['ready-start', 'ready-death', 'ready-clear', 'death-anim', 'death-start-cell', 'death-fruit-cell',
         'death-xlife', 'death-clear', 'final-death', 'popup-ghost', 'popup-fruit', 'popup-two-ghosts',
         'popup-under-ghost', 'popup-expire', 'popup-death', 'popup-clear', 'pause-popup', 'pause-freeze',
         'redraw-freeze', 'hi-R', 'hi-Z', 'end-new', 'end-not-new']
# reached by the run configuration, not by a screen state: families W / T / B / G, SCALE 3, the size guard (SCALE T),
# a P before the first direction (ignored: READY! stays), a practice start (LEVEL(n>1): high score shown, never new)


def cards(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


class Probe(ref_rp.Tracker):
    def __init__(self, hs, seen, st=None):
        super().__init__(hs)
        self.seen, self.last, self.st = seen, None, st if st is not None else []

    def frame(self, g, play='T', rtstat=None, rtfrz=0, rtq=0, dth=None, ends=False):
        eat0 = self.eat
        self.st.append((rtq, rtstat, rtfrz))
        rp = super().frame(g, play, rtstat, rtfrz, rtq, dth, ends)
        if rp is None:
            return rp
        s = self.seen
        if rp['ready']:
            s.add('ready-start' if (rtstat == 'WAIT' or (play != 'R' and g.turns == 0)) else
                  'ready-death' if 'D' in g.evf else 'ready-clear')
        if rp['dth']:
            s.add('death-anim')
            if 'C' in g.evf:
                s.add('death-clear')
            if (rp['dth'][1], rp['dth'][2]) == START:
                s.add('death-start-cell')
            if (rp['dth'][1], rp['dth'][2]) == ref_rp.FRUIT_CELL:
                s.add('death-fruit-cell')
            if 'X' in g.evf:
                s.add('death-xlife')
            if g.lost:
                s.add('final-death')
        if g.eaten - eat0 > 1:
            s.add('popup-two-ghosts')
        pu = rp['pu']
        if pu is not None:
            s.add('popup-fruit' if pu['msg'].startswith('FRUIT') else 'popup-ghost')
            if any(tuple(q[:2]) == (pu['x'], pu['y']) and g.mode[k] != 'E' for k, q in enumerate(g.gh)):
                s.add('popup-under-ghost')
            if rtstat == 'PAUS':
                s.add('pause-popup')
        if self.last is not None and pu is None and self.last['pu'] is not None:
            s.add('popup-death' if 'D' in g.evf else 'popup-clear' if 'C' in g.evf else 'popup-expire'
                  if not ends else 'popup-end')
        if rtstat == 'PAUS' and ('D' in g.evf or 'C' in g.evf) and rtfrz > 0:
            s.add('pause-freeze')
        if rp['hi'] is not None:
            s.add('hi-' + self.hs[0])
        if ends and rp['hi'] is not None:
            s.add('end-new' if rp['new'] else 'end-not-new')
        self.last = rp
        return rp


def cover(kind, d, c, canvas='W', hs=None, start=1, scale='4', glyphs='G'):
    seen, st = set(), []
    orig = ref_rp.Tracker
    ref_rp.Tracker = lambda h=None: Probe(h, seen, st)
    try:
        if kind == 'T':
            gx.frames(c, True, True, 'P', glyphs, scale, canvas, mk=lambda ai, n: L.Level(ai, n, 'T', start), d=d,
                      hs=hs)
        else:
            _, fs = ref_rt.tsd(cards(d, c), canvas, mk_game=lambda ai, n: L.Level(ai, n, 'R', start),
                               mk_ctl=L.LevelRT, hs=hs)
            # one tracker call per stream: a full screen (PA2) composed inside a freeze
            if any(s_ == 'FRZ ' and f[0] == 0xC3 and len(f) > 1000 for (_, s_, _), f in zip(st[:-1], fs[:-1])):
                seen.add('redraw-freeze')
    finally:
        ref_rp.Tracker = orig
    return seen


# ---- REALTIME cases (one card = one quantum; P = pause toggle, * = PA2 redraw) ---------------------------------------
DIRS = {'U': (0, -1), 'D': (0, 1), 'L': (-1, 0), 'R': (1, 0)}


def rt_trace(cards_):
    """Quantum by quantum on the model: [(card index, game, controller)] after each quantum (no pause handling)."""
    ai, n, rest = parse_config(list(cards_))
    g = L.Level(ai, n, 'R', 1)
    c = L.LevelRT(g)
    out = []
    for k, cd in enumerate(rest, 1):
        u = cd[:1].upper()
        if u in DIRS:
            c.rin('MOV', u, u)
        if u == 'Q':
            break
        c.rq()
        out.append((k, g.eaten, g.fruits, c.frz, 'D' in g.evf or 'C' in g.evf, g.lost))
        if g.lost or g.won:
            break
    return out


def first_freeze(cs):
    """The quantum of the first death / clear freeze of a card list on the TSD driver model."""
    seen, st = set(), []
    orig = ref_rp.Tracker
    ref_rp.Tracker = lambda h=None: Probe(h, seen, st)
    try:
        ref_rt.tsd(cs, 'W', mk_game=lambda ai, n: L.Level(ai, n, 'R', 1), mk_ctl=L.LevelRT)
    finally:
        ref_rp.Tracker = orig
    return next(q for q, s_, f in st if s_ == 'FRZ ')


def constructed():
    out = {}
    # RPLOST: AI3 3, a blocked first direction (U at the start cell starts the game, Pac-Man stays): every death on
    # the start cell, the last one = the final death (frames played before the end screen)
    lost = ['AI3 3', 'P', 'U'] + ['.'] * 160
    q0 = first_freeze(lost)                 # card q + 1 = quantum q (the pre-start P is not a quantum)
    out['RPLOST'] = lost[:q0 + 2] + ['*', 'P', '.', 'P'] + lost[q0 + 2:]
    # RPPAUSE: RTGPA with a pause in the quantum after the first eaten ghost (popup shown), a pause and a PA2 redraw
    # inside the first death freeze; P before the first direction is ignored (READY! stays)
    base = cards('gpcases', 'RTGPA')
    tr = rt_trace(base)
    ate = next(k for k, eat, *_ in tr if eat > 0)
    rest = base[1:]
    rest = rest[:ate] + ['P', '.', 'P'] + rest[ate:]
    out['RPPAUSE'] = base[:1] + ['P'] + rest
    return out


def rt_search(tries=4000, want=('death-clear', 'popup-under-ghost', 'popup-clear')):
    import random
    import search_gp2 as S2
    rng, best = random.Random(20261012), {}
    for t in range(tries):
        ai, n = rng.choice((1, 2, 3)), rng.choice((1, 2, 3))
        style = ('greedy', 'hunt', 'fruit', 'walk')[t % 4]
        g = L.Level(ai, n, 'R', 1)
        g.start = 1
        c = L.LevelRT(g)
        seen = set()
        pr = Probe(None, seen)
        cards_ = [f'AI{ai} {n}']
        for q in range(700):
            d = S2.choose(rng, g, style, c.cur) if q == 0 or rng.random() < 0.6 else None
            if d and d != c.cur and not c.frz:
                c.rin('MOV', d, d)
            else:
                d = None
            cards_.append(d or '.')
            c.rq()
            pr.frame(g, 'R', c.status(), c.frz, c.q, getattr(c, 'dth', None))
            for w in want:
                if w in seen and (w not in best or len(cards_) < len(best[w])):
                    best[w] = list(cards_)
            if g.won or g.lost or all(w in seen for w in want):
                break
    return best


if __name__ == '__main__' and '--write' in sys.argv:
    cases = constructed()
    found = rt_search()
    for w, name in (('death-clear', 'RPDCLR'), ('popup-under-ghost', 'RPUNDER'), ('popup-clear', 'RPCLRPU')):
        if w in found:
            cases[name] = found[w] + ['.'] * 12 + ['Q']
        print(name, len(found[w]) - 1 if w in found else 'NOT FOUND')
    (R / 'tests/rpcases').mkdir(exist_ok=True)
    for k, cs in cases.items():
        (R / f'tests/rpcases/{k}.txt').write_text('\n'.join(cs) + '\n')
        print('wrote', k, len(cs) - 1)

if __name__ == '__main__' and '--write' not in sys.argv:
    from make_deck import RP_TURN, RP_RT
    total = set()
    for kind, runs in (('T', RP_TURN), ('R', RP_RT)):
        for r in runs:
            got = cover(kind, *r)
            total |= got
            print(kind, r[:3], sorted(got))
    print('missing:', [e for e in EDGES if e not in total])
