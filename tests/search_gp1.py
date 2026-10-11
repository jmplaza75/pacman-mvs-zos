#!/usr/bin/env python3
"""MVS-GP1 (D36, D12): search the ARCADE model (tests/ref_arcade.py) for short TURN card sequences that reach each
documented edge case; prints one case file per edge (first card = AI<l> <n>). Deterministic (fixed random seed).
Usage: search_gp1.py [OUTDIR]   (without OUTDIR: report only)"""
import random
import sys
from collections import deque
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
import ref_arcade as A  # noqa: E402

DIRS = {'U': (0, -1), 'D': (0, 1), 'L': (-1, 0), 'R': (1, 0)}
PRED = {
    'GPFWALK': lambda lg, g: any(e[0] == 'collide' and e[1] == 2 and e[2] > 0 for e in lg),   # F ghost walks into P
    'GPTWOF': lambda lg, g: any(e[0] == 'collide' and e[2] >= 2 for e in lg),                 # 200 + 400 in one check
    'GPFN': lambda lg, g: any(e[0] == 'collide' and e[2] >= 1 and e[3] for e in lg),          # F eaten, then N hit
    'GPREVB': lambda lg, g: any(e[0] == 'revblocked' for e in lg),                           # reversal blocked
    'GPTIE': lambda lg, g: any(e[0] == 'flee' and e[2] for e in lg),                          # flee tie U D L R
    'GPPOW2': lambda lg, g: any(e[0] == 'power' and e[1] > 0 and 'F' in e[2] for e in lg),     # 2nd o in a fright
    'GPPOWE': lambda lg, g: any(e[0] == 'power' and 'E' in e[2] for e in lg),                 # o while eyes wait
    'GPDEYE': lambda lg, g: any(e[0] == 'death' and 'E' in e[2] for e in lg),                 # death during eyes
    'GPDFR': lambda lg, g: any(e[0] == 'death' and e[1] for e in lg),                         # death in a fright
    'GPWALKF': lambda lg, g: any(e[0] == 'collide' and e[1] == 1 and e[2] > 0 for e in lg),   # P walks into F
}


def legal(g):
    return [d for d, (dx, dy) in DIRS.items() if A.MAP0[g.y + dy - 1][g.x + dx - 1] != '#']


def nearest(g, want):
    """First step of a shortest path to the nearest cell whose content is in want (None if none)."""
    prev, q = {(g.x, g.y): None}, deque([(g.x, g.y)])
    while q:
        p = q.popleft()
        if p != (g.x, g.y) and g.grid[p[1] - 1][p[0] - 1] in want:
            while prev[p][0] != (g.x, g.y):
                p = prev[p][0]
            return prev[p][1]
        for d, (dx, dy) in DIRS.items():
            n = (p[0] + dx, p[1] + dy)
            if n not in prev and A.MAP0[n[1] - 1][n[0] - 1] != '#':
                prev[n] = (p, d)
                q.append(n)
    return None


def play(rng, ai, n, style, limit=260):
    g = A.Arcade(ai, n, 'T')
    cards, found, last = [f'AI{ai} {n}'], {}, rng.choice(legal(g))
    for _ in range(limit):
        if style == 'greedy' and rng.random() < 0.85:
            d = nearest(g, '.o') or rng.choice(legal(g))
        elif style == 'hunt' and g.fr > 0 and rng.random() < 0.8:
            tgt = min((abs(x - g.x) + abs(y - g.y), x, y) for i, (x, y, _) in enumerate(g.gh) if g.mode[i] == 'F') \
                if 'F' in g.mode[:n] else None
            d = None
            if tgt:
                d = ('R' if tgt[1] > g.x else 'L' if tgt[1] < g.x else 'D' if tgt[2] > g.y else 'U')
                if d not in legal(g):
                    d = None
            d = d or nearest(g, 'o.') or rng.choice(legal(g))
        elif style == 'hunt':
            d = nearest(g, 'o') or nearest(g, '.') or rng.choice(legal(g))
        else:
            d = last if last in legal(g) and rng.random() < 0.7 else rng.choice(legal(g))
        last = d
        cards.append(d)
        g.log = []
        g.turn('T', d)
        for k, p in PRED.items():
            if k not in found and p(g.log, g):
                found[k] = list(cards)
        if g.won and any(e[0] == 'power' for e in g.log) and 'GPLASTO' not in found:
            found['GPLASTO'] = list(cards)
        if g.left == 0 and any(e[0] == 'death' for e in g.log) and 'GPLASTH' not in found:
            found['GPLASTH'] = list(cards)
        if g.won or g.lost:
            break
    return found


def search(tries=6000):
    rng, best = random.Random(20261011), {}
    for t in range(tries):
        ai, n = rng.choice((1, 2, 3)), rng.choice((1, 2, 3))
        style = ('walk', 'greedy', 'hunt')[t % 3]
        for k, cards in play(rng, ai, n, style).items():
            if k not in best or len(cards) < len(best[k]):
                best[k] = cards
    return best


if __name__ == "__main__" and "--rt" not in sys.argv:
    best = search()
    for k in sorted(set(PRED) | {'GPLASTO', 'GPLASTH'}):
        print(k, len(best[k]) - 1 if k in best else 'NOT FOUND', best.get(k, [''])[0])
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
        for k, cards in best.items():
            (out / f'{k}.txt').write_text('\n'.join(cards + ['Q']) + '\n')


# ---- REALTIME (one card = one quantum: a direction or '.'): eat -> revival in the fright (both cadences) -> fright end;
# and a death in a fright (normal accumulator reset, freeze)
def rt_play(rng, ai, n, limit=220):
    g = A.Arcade(ai, n, 'R')
    c = A.ArcadeRT(g)
    cards, seen, found = [f'AI{ai} {n}'], set(), {}
    for q in range(limit):
        d = None
        if q == 0:
            d = rng.choice(legal(g))
        elif rng.random() < 0.3:
            if g.fr > 0 and 'F' in g.mode[:n] and rng.random() < 0.7:
                f = [(abs(x - g.x) + abs(y - g.y), x, y) for i, (x, y, _) in enumerate(g.gh) if g.mode[i] == 'F']
                _, tx, ty = min(f)
                d = 'R' if tx > g.x else 'L' if tx < g.x else 'D' if ty > g.y else 'U'
            else:
                d = nearest(g, 'o') or nearest(g, '.') or rng.choice(legal(g))
        if d:
            c.rin('MOV', d, d)
        cards.append(d or '.')
        g.log = []
        c.rq()
        for e in g.log:
            if e[0] == 'collide' and e[2] > 0:
                seen.add('eat')
            if e[0] == 'revive' and e[2] and 'F' in g.mode[:n]:
                seen.add('mix')
            if e[0] == 'fend' and 'mix' in seen:
                seen.add('fend')
            if e[0] == 'death' and e[1]:
                found.setdefault('RTGPD', list(cards))
        if {'eat', 'mix', 'fend'} <= seen:
            found.setdefault('RTGPA', list(cards))
        if g.won or g.lost or len(found) == 2:
            break
    return found


def rt_search(tries=3000):
    rng, best = random.Random(20261012), {}
    for _ in range(tries):
        for k, cards in rt_play(rng, rng.choice((1, 2, 3)), rng.choice((2, 3))).items():
            if k not in best or len(cards) < len(best[k]):
                best[k] = cards
    return best


if __name__ == '__main__' and '--rt' in sys.argv:
    best = rt_search()
    for k, cards in best.items():
        print(k, len(cards) - 1, cards[0])
        (R / f'tests/gpcases/{k}.txt').write_text('\n'.join(cards + ['.', '.', 'Q']) + '\n')
