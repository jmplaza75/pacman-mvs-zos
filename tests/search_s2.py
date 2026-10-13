#!/usr/bin/env python3
"""MVS-S2 (D41, D12): search the GP2 REALTIME model (tests/ref_gp2.py, start level 13) for short card sequences that
reach the extra-life pattern edges of docs/S2-PATTERNS.md section 6; writes tests/s2cases/<name>.txt (first card =
AI<l> <n>, one card = one quantum: a direction or '.'). Deterministic (fixed random seed).
  S2XL   an extra life alone, then at least 4 quiet quanta (its full pattern at NORMAL and FAST)
  S2XLD  a death one quantum after an extra life (the death replaces the running extra-life pattern)
  S2XLC  an extra life and a level clear in one quantum (the level clear, higher, is the write's event); start level
         12, still ghosts (AI0): the score crosses 10000 only on exact totals (items 1160 a level, ghosts in 200s,
         fruit in 100s), so it has its own search (seed 41, a bounded number of tries)
  S2PRM  (constructed) RTSTILL (CLASSIC) with an invalid input (X) and a PA2 redraw (*) on the quanta where the two
         death patterns ring their second bell: the step rides on the quantum's prompt-form write
The start level of each case is START_OF (tools/make_deck.py reads it). Tail: 8 idle quanta (the longest pattern,
3 bells at FAST, ends 6 quanta after its event) and Q.
Usage: search_s2.py [--write]   the searched cases;   search_s2.py --build   the constructed case"""
import random
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
import ref_gp2 as L  # noqa: E402
from search_gp2 import choose, ev, legal, nearest  # noqa: E402

START = 13
START_OF = {'S2XL': 13, 'S2XLD': 13, 'S2XLC': 12, 'S2PRM': 1}
TAIL = ['.'] * 8 + ['Q']


def rt_play(rng, ai, n, style, limit=1500):
    g = L.Level(ai, n, 'R', START)
    g.start = START
    c = L.LevelRT(g)
    cards, found, hist = [f'AI{ai} {n}'], {}, []
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
        xl, death, clear = bool(ev(g.log, 'xlife')), bool(ev(g.log, 'death')), bool(ev(g.log, 'clear'))
        hist.append((xl, death, clear))
        if xl and clear:
            found.setdefault('S2XLC', list(cards))
        if len(hist) > 1 and hist[-2][0] and not hist[-2][1] and not hist[-2][2] and death and not g.lost:
            found.setdefault('S2XLD', list(cards))
        if len(hist) > 4 and hist[-5] == (True, False, False) and not any(any(h) for h in hist[-4:]):
            found.setdefault('S2XL', list(cards))
        if g.won or g.lost or len(found) == 3:
            break
    return found


def rt_search(tries=6000):
    rng, best = random.Random(20261013), {}
    for t in range(tries):
        ai, n = rng.choice((0, 1, 2, 3)), rng.choice((1, 2, 3))
        style = ('fruit', 'hunt', 'avoid', 'greedy', 'eat')[t % 5]
        for k, cards in rt_play(rng, ai, n, style).items():
            if k not in best or len(cards) < len(best[k]):
                best[k] = cards
        if len(best) == 3 and t > 300:
            break
    return best


def xlc_play(rng, n, start, phunt, pfruit, limit):
    """AI0: eat the nearest item, the fruit with probability pfruit, hunt a frightened ghost with probability phunt."""
    g = L.Level(0, n, 'R', start)
    c = L.LevelRT(g)
    cards, fr_eat = [f'AI0 {n}'], None
    for _ in range(limit):
        d = None
        if g.bt > 0 and fr_eat is None:
            fr_eat = rng.random() < pfruit
        if g.bt == 0:
            fr_eat = None
        av = L.FRUIT_CELL if (g.bt > 0 and not fr_eat) else None
        if g.bt > 0 and fr_eat:
            d = nearest(g, cell=L.FRUIT_CELL)
        elif g.fr > 0 and 'F' in g.mode[:g.n] and rng.random() < phunt:
            tg = [(x, y) for i, (x, y, _) in enumerate(g.gh) if g.mode[i] == 'F']
            d = nearest(g, cell=rng.choice(tg), avoid=av)
        if not d:
            d = nearest(g, '.o', avoid=av)
        if not d:
            d = rng.choice(legal(g))
        if d != c.cur:
            c.rin('MOV', d, d)
            cards.append(d)
        else:
            cards.append('.')
        g.log = []
        c.rq()
        if ev(g.log, 'xlife') and ev(g.log, 'clear'):
            return cards
        if g.xl or g.won or g.lost:
            return None
    return None


def xlc_search(tries=4700):
    rng, best = random.Random(41), None
    for _ in range(tries):
        n, start = rng.choice((1, 2, 3)), rng.choice(range(1, 14))
        cards = xlc_play(rng, n, start, rng.random(), rng.random(), limit=len(best[0]) if best else 2500)
        if cards and (best is None or len(cards) < len(best[0])):
            best = (cards, start)
    assert best[1] == START_OF['S2XLC'], best[1]
    return best[0]


def constructed():
    """S2PRM: RTSTILL cards 29 and 74 (the second bell of each death pattern at NORMAL) -> X and *."""
    cs = (R / 'tests/rtcases/RTSTILL.txt').read_text().splitlines()
    assert cs[29] == '.' and cs[74] == '.'
    return {'S2PRM': cs[:29] + ['X'] + cs[30:74] + ['*'] + cs[75:]}


if __name__ == '__main__' and '--build' in sys.argv:
    for k, cards in constructed().items():
        (R / f'tests/s2cases/{k}.txt').write_text('\n'.join(cards) + '\n')
        print(k, len(cards) - 1)
    sys.exit(0)

if __name__ == '__main__':
    best = rt_search()
    best['S2XLC'] = xlc_search()
    for k in ('S2XL', 'S2XLD', 'S2XLC'):
        print(k, len(best[k]) - 1 if k in best else 'NOT FOUND', best.get(k, [''])[0])
    if '--write' in sys.argv:
        out = R / 'tests/s2cases'
        out.mkdir(exist_ok=True)
        for k, cards in best.items():
            (out / f'{k}.txt').write_text('\n'.join(cards + TAIL) + '\n')
