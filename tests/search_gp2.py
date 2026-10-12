#!/usr/bin/env python3
"""MVS-GP2 (D37, D12): search the GP2 model (tests/ref_gp2.py) for short card sequences that reach each documented
edge case; writes one case file per edge into tests/gp2cases (first card = AI<l> <n>; the start level of a case is
in tools/make_deck.py GP2_BAT / GP2_RT). Deterministic (fixed random seeds).
Usage: search_gp2.py [--write]        TURN cases
       search_gp2.py --rt [--write]   REALTIME cases (one card = one quantum: a direction or '.')"""
import random
import sys
from collections import deque
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
import ref_gp2 as L  # noqa: E402
from ref_mvs6 import MAP0  # noqa: E402

DIRS = {'U': (0, -1), 'D': (0, 1), 'L': (-1, 0), 'R': (1, 0)}


def ev(lg, kind):
    return [e for e in lg if e[0] == kind]


# predicate(log of one step, game after the step, xl before the step) -> bool; (start levels searched)
PRED = {
    'G2CLRD': (lambda lg, g: bool(ev(lg, 'clear')) and bool(ev(lg, 'death')) and not g.lost, (1,)),
    'G2CLRL': (lambda lg, g: any(e[3] for e in ev(lg, 'death')) and g.lost, (1,)),
    'G2CLRO': (lambda lg, g: bool(ev(lg, 'clear')) and bool(ev(lg, 'power')), (1,)),
    'G2CLRF': (lambda lg, g: any(e[3] and 'E' in e[4] for e in ev(lg, 'clear')), (1,)),
    'G2BUND': (lambda lg, g: any(e[2] for e in ev(lg, 'fruit')), (1,)),
    'G2BDIE': (lambda lg, g: bool(ev(lg, 'deathfruit')) and not g.lost, (1,)),
    'G2BGH': (lambda lg, g: g.bt > 0 and any(tuple(x[:2]) == L.FRUIT_CELL for x in g.gh), (1,)),
    'G2XP': (lambda lg, g: ('xlife', 'item') in lg, (13,)),
    'G2XG': (lambda lg, g: ('xlife', 'ghost') in lg, (13,)),
    'G2XF': (lambda lg, g: ('xlife', 'fruit') in lg, (13,)),
    'G2XD': (lambda lg, g: bool(ev(lg, 'xlife')) and bool(ev(lg, 'death')), (13,)),
    'G2X20K': (lambda lg, g: g.ascore >= 20000, (13,)),            # no second extra life
}


def legal(g):
    return [d for d, (dx, dy) in DIRS.items() if MAP0[g.y + dy - 1][g.x + dx - 1] != '#']


def nearest(g, want=None, cell=None, avoid=None):
    """First step of a shortest path to the nearest cell holding one of want (or to cell), never through avoid;
    None if none."""
    prev, q = {(g.x, g.y): None}, deque([(g.x, g.y)])
    while q:
        p = q.popleft()
        if p != (g.x, g.y) and (p == cell if cell else g.grid[p[1] - 1][p[0] - 1] in want):
            while prev[p][0] != (g.x, g.y):
                p = prev[p][0]
            return prev[p][1]
        for d, (dx, dy) in DIRS.items():
            n = (p[0] + dx, p[1] + dy)
            if n not in prev and MAP0[n[1] - 1][n[0] - 1] != '#' and n != avoid:
                prev[n] = (p, d)
                q.append(n)
    return None


def choose(rng, g, style, last):
    if style == 'avoid':            # the first fruit of the game only, then hunt and keep off the fruit cell
        av = L.FRUIT_CELL if g.bt > 0 and (g.fruits or g.level > g.start) else None
        if g.bt > 0 and not av:
            return nearest(g, cell=L.FRUIT_CELL) or rng.choice(legal(g))
        if g.fr > 0 and 'F' in g.mode[:g.n] and rng.random() < 0.85:
            _, tx, ty = min((abs(x - g.x) + abs(y - g.y), x, y) for i, (x, y, _) in enumerate(g.gh)
                            if g.mode[i] == 'F')
            d = 'R' if tx > g.x else 'L' if tx < g.x else 'D' if ty > g.y else 'U'
            n = (g.x + DIRS[d][0], g.y + DIRS[d][1])
            if d in legal(g) and n != av:
                return d
        d = nearest(g, '.o', avoid=av)
        if d:
            return d
        ok = [d for d in legal(g) if (g.x + DIRS[d][0], g.y + DIRS[d][1]) != av]
        return rng.choice(ok or legal(g))
    if style in ('fruit', 'hunt') and g.bt > 0 and rng.random() < 0.9:
        d = nearest(g, cell=L.FRUIT_CELL)
        if d:
            return d
    if style == 'hunt' and g.fr > 0 and 'F' in g.mode[:g.n] and rng.random() < 0.8:
        _, tx, ty = min((abs(x - g.x) + abs(y - g.y), x, y) for i, (x, y, _) in enumerate(g.gh) if g.mode[i] == 'F')
        d = 'R' if tx > g.x else 'L' if tx < g.x else 'D' if ty > g.y else 'U'
        if d in legal(g):
            return d
    if style in ('greedy', 'fruit', 'hunt') and rng.random() < 0.85:
        return nearest(g, '.o') or rng.choice(legal(g))
    return last if last in legal(g) and rng.random() < 0.7 else rng.choice(legal(g))


def play(rng, ai, n, style, start, limit=900):
    g = L.Level(ai, n, 'T', start)
    g.start = start
    cards, found, last = [f'AI{ai} {n}'], {}, rng.choice(legal(g))
    for _ in range(limit):
        d = choose(rng, g, style, last)
        last = d
        cards.append(d)
        g.log = []
        g.turn('T', d)
        for k, (p, starts) in PRED.items():
            if start in starts and k not in found and p(g.log, g):
                found[k] = list(cards)
        if g.won or g.lost:
            break
    return found


def search(tries=4000):
    rng, best = random.Random(20261012), {}
    for t in range(tries):
        start = (1, 13)[t % 2]
        ai, n = rng.choice((0, 1, 2, 3) if start == 13 else (1, 2, 3)), rng.choice((1, 2, 3))
        style = ('walk', 'greedy', 'fruit', 'hunt', 'avoid', 'avoid')[(t // 2) % 6]
        for k, cards in play(rng, ai, n, style, start).items():
            if k not in best or len(cards) < len(best[k]):
                best[k] = cards
    return best


# ---- REALTIME: the second fruit while the first is shown (timer restart; AI0, eat on, keep off the fruit cell);
# an extra life and a death in one quantum (level 13, chase the fruit, moving ghosts)
def rt_play(rng, ai, n, start, style, limit=500):
    g = L.Level(ai, n, 'R', start)
    g.start = start
    c = L.LevelRT(g)
    cards, found = [f'AI{ai} {n}'], {}
    for q in range(limit):
        d = None
        if style == 'eat':
            d = nearest(g, '.o', avoid=L.FRUIT_CELL if g.bt > 0 else None)
        elif q == 0 or rng.random() < 0.5:
            d = choose(rng, g, style, c.cur)
        if d and d != c.cur:
            c.rin('MOV', d, d)
        else:
            d = None
        cards.append(d or '.')
        g.log = []
        c.rq()
        if any(e[3] for e in ev(g.log, 'fruit')):
            found.setdefault('G2RB2', list(cards))
        if ev(g.log, 'xlife') and ev(g.log, 'death') and not g.lost:
            found.setdefault('G2RXD', list(cards))
        if g.won or g.lost:
            break
    return found


def rt_search(tries=3000):
    rng, best = random.Random(20261013), {}
    for t in range(tries):
        if t % 3 == 0:
            ai, n, start, style = 0, rng.choice((1, 2, 3)), 1, 'eat'
        else:
            ai, n, start, style = rng.choice((1, 2, 3)), rng.choice((1, 2, 3)), 13, ('fruit', 'hunt')[t % 2]
        for k, cards in rt_play(rng, ai, n, start, style).items():
            if k not in best or len(cards) < len(best[k]):
                best[k] = cards
    return best


if __name__ == '__main__':
    rt = '--rt' in sys.argv
    best = rt_search() if rt else search()
    names = ('G2RB2', 'G2RXD') if rt else sorted(PRED)
    for k in names:
        print(k, len(best[k]) - 1 if k in best else 'NOT FOUND', best.get(k, [''])[0])
    if '--write' in sys.argv:
        out = R / 'tests/gp2cases'
        out.mkdir(exist_ok=True)
        for k, cards in best.items():
            tail = ['.', '.', 'Q'] if rt else ['Q']
            (out / f'{k}.txt').write_text('\n'.join(cards + tail) + '\n')


# ---- constructed cases (design 7): the 1.0-MVS full-clear route WIN0 (AI0) in ARCADE = a level clear with both
# fruits (one eaten, one expiring); the same route as REALTIME cards (one direction per quantum); a short row probe
# (eat the power pellet at 2,4 on turn 2: the fright length of the row) used with every start level; a pause while
# a fruit is shown (G2RB2 with an idle quantum after the first spawn replaced by P . L . P: only the input column
# may differ; L is ignored while paused).
def constructed():
    win0 = (R / 'tests/cases/WIN0.txt').read_text().splitlines()
    route = win0[1:-1]
    out = {'G2CLR': win0[:1] + route + ['D', 'D', 'R', 'R', 'R', 'R', 'R', 'Q'],
           'G2RCLR': win0[:1] + route + ['.'] * 12 + ['D', '.', 'R', '.', '.', 'Q'],
           'G2ROW': ['AI1 1', 'D', 'D', 'R', 'R', 'R', 'R', 'R', 'R', 'R', 'R', 'R', 'R', 'R', 'R', 'Q']}
    rb2 = (R / 'tests/gp2cases/G2RB2.txt').read_text().splitlines()
    g = L.Level(*L.parse_config(rb2[:1])[:2], 'R', 1)
    c = L.LevelRT(g)
    for k, d in enumerate(rb2[1:], 1):
        if d in DIRS:
            c.rin('MOV', d, d)
        c.rq()
        if g.bt > 0:
            break
    j = next(i for i in range(k + 2, len(rb2)) if rb2[i] == '.')       # an idle quantum while the fruit is shown
    out['G2RPAU'] = rb2[:j] + ['P', '.', 'L', '.', 'P'] + rb2[j + 1:]
    return out


if __name__ == '__main__' and '--build' in sys.argv:
    for k, cards in constructed().items():
        (R / f'tests/gp2cases/{k}.txt').write_text('\n'.join(cards) + '\n')
        print(k, len(cards) - 1)
