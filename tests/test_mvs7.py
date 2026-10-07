#!/usr/bin/env python3
"""MVS-7 acceptance (portability refactor: behaviour identical to MVS-6). Local: model regression vs MVS-5, map properties, behaviour properties of the model output.
With a job listing: all RC 0000, every run's SYSOUT equals the independent model, and the same behaviour
properties are re-derived from the REAL output (positions, directions, Manhattan choices, lives)."""
import re, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs6 import simulate, Game, MAP0, GSTARTS, GDIR0, REV, DIRS  # noqa: E402

OLD = ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1')
NEW = ('P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')
RUNS = OLD + NEW
lit = re.findall(r"FILLER\s+PIC X\(20\) VALUE '([^']*)'", (R / 'src/cobol/PACMAP.cob').read_text())
assert lit == MAP0, 'map mismatch'
OPEN = lambda x, y: MAP0[y - 1][x - 1] != '#'
NB = {k: (dx, dy) for k, (_, dx, dy) in enumerate(DIRS, 1)}        # 1=U 2=D 3=L 4=R
# LEVEL1 has no dead ends, so the "reverse only when nothing else" rule can never fire on it (documented, D13)
assert all(sum(OPEN(x + dx, y + dy) for dx, dy in NB.values()) >= 2
           for y in range(1, 11) for x in range(1, 21) if OPEN(x, y))


def cfg_of(case):
    first = (R / f'tests/cases/{case}.txt').read_text().splitlines()[0]
    if first[:1] != 'A':
        return 1, 1
    return int(first[2:3]), int(first[4:5]) if first[4:5] in '123' and first[4:5] else 1


def behaviour(lines, ai, n):
    """Re-derive ghost rules from the printed output only."""
    st = [i for i, l in enumerate(lines) if re.match(r'T\d{3} ', l)]
    stats = {'ticks': 0, 'multi_ok': 0}

    def ghosts(i):
        l = lines[i]
        pos = [tuple(map(int, re.search(r' G=(\d+),(\d+)', l).groups()))]
        if n > 1:
            pos += [tuple(map(int, m)) for m in re.findall(r'G\d=(\d+),(\d+)', lines[i + 1])]
        return pos
    start = [tuple(p) for p in GSTARTS[:n]]
    assert ghosts(st[0]) == start
    pos, dirs, lives = start, list(GDIR0[:n]), 3
    for i in st[1:]:
        l = lines[i]
        px, py = map(int, re.search(r'X=(\d+) Y=(\d+)', l).groups())
        newlives = int(re.search(r' V=(\d)', l).group(1))
        cur = ghosts(i)
        assert all(OPEN(*p) for p in cur), 'ghost inside a wall'
        if ' DIED ' in l or ' LOST ' in l:
            assert newlives == lives - 1, 'one life per hit tick'
            pos, dirs, lives = start, list(GDIR0[:n]), newlives
            if ' LOST ' in l:
                break
            assert cur == start and (px, py) == (2, 2)
            continue
        assert newlives == lives
        stats['ticks'] += 1
        for k in range(n):
            d = (cur[k][0] - pos[k][0], cur[k][1] - pos[k][1])
            if ai == 0:
                assert d == (0, 0)
                continue
            assert abs(d[0]) + abs(d[1]) == 1, 'ghost must move exactly one step'
            nd = next(j for j, v in NB.items() if v == d)
            if ai >= 2:
                opens = [j for j, v in NB.items() if OPEN(pos[k][0] + v[0], pos[k][1] + v[1]) and j != REV[dirs[k]]]
                assert nd in opens, 'reversed or entered wall'
                if ai == 2 and len(opens) == 1:
                    assert nd == opens[0]                      # corridor: forced / keeps going
                if ai == 3:
                    dist = lambda j: abs(pos[k][0] + NB[j][0] - px) + abs(pos[k][1] + NB[j][1] - py)
                    assert nd == min(opens, key=lambda j: (dist(j), j)), 'chase must take the first minimum'
            dirs[k] = nd
        pos = cur
    return stats


exp = {n: (R / f'tests/expected/MVS6-{n}.txt').read_text().splitlines() for n in RUNS}
for n in RUNS:
    assert exp[n] == simulate((R / f'tests/cases/{n}.txt').read_text().splitlines()), n
for n in OLD:                                  # regression: identical to the accepted MVS-5 output
    old = (R / f'tests/expected/MVS5-{n}.txt').read_text().splitlines()
    assert exp[n][1:] == old[1:] and exp[n][0] == 'PACMAN MVS-6 SMART GHOSTS', n
counts = {}
for n in RUNS:
    ai, k = cfg_of(n)
    behaviour(exp[n], ai, k)
    counts[n] = (ai, k)
# ghost start cells are cleared only for active ghosts: pellets at START = 100 / 99 / 98 for 1 / 2 / 3 ghosts
for n, left in (('P2', 100), ('R1N2', 99), ('P2N3', 98)):
    assert f' L={left:03d} ' in exp[n][1], (n, exp[n][1])
assert exp['C3'][-4:] == ['LOST', 'TURNS 084', 'SCORE 0000', 'LIVES 0']     # a waiting player is hunted down
assert exp['C3N2'][-4:] == ['LOST', 'TURNS 021', 'SCORE 0000', 'LIVES 0']   # second chaser is faster
# two ghosts on the player's cell in the same tick cost ONE life (D13)
g = Game(3, 3)
cmds = (R / 'tests/cases/MULTI.txt').read_text().splitlines()[1:]
double = False
for c in cmds:
    before = g.lives
    g.step(c)
    if g.last_hits >= 2:
        double = True
        assert before - g.lives == 1
assert double, 'MULTI must contain a double hit'
assert exp['MULTI'][-1] == 'LIVES 2'
# --- portability architecture (requirements sec. 3): core modules contain no terminal/host verbs
import glob
core = ('PACGAME', 'PACMAP', 'PACAI')
for m in core:
    code = [l[6:72] for l in (R / f'src/cobol/{m}.cob').read_text().splitlines() if len(l) > 6 and l[6] != '*']
    text = '\n'.join(code).upper()
    for bad in ('DISPLAY', 'ACCEPT', ' READ ', 'WRITE', 'OPEN ', 'SELECT', 'UT-S', 'SYSIN', 'TSO', 'ISPF', 'ZOWE',
                'HERCULES', 'UPON CONSOLE', 'STOP RUN'):
        assert bad not in text, (m, bad)
    assert 'CALL ' not in text or m != 'PACMAP'                      # MAP is a leaf service
for m in ('PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACDISP', 'PACPLAT'):
    assert 'SELECT' not in (R / f'src/cobol/{m}.cob').read_text()   # only PACINPT touches the card file
assert 'DISPLAY' not in (R / 'src/cobol/PACMAIN.cob').read_text()   # driver prints nothing itself
assert (R / 'src/cobol/PACINPT.cob').read_text().count('SELECT COMMAND-FILE') == 1
print('local checks PASS')
if len(sys.argv) > 1:
    lines = open(sys.argv[1]).read().splitlines()
    rcs = re.findall(r'(\w+)\s+(?:IEBGENER|IKFCBL00|IEWL|PACMAIN)\s+RC= (\d{4})', '\n'.join(lines))
    assert len(rcs) == 10 + 7 + 1 + len(RUNS) and all(r == '0000' for _, r in rcs), rcs
    starts = [i for i, l in enumerate(lines) if l == 'PACMAN MVS-6 SMART GHOSTS']
    assert len(starts) == len(RUNS), starts
    for s, n in zip(starts, RUNS):
        got = lines[s:s + len(exp[n])]
        assert got == exp[n], f'{n}: runtime output differs'
        behaviour(got, *counts[n])
    # BEFORE/AFTER: the accepted MVS-6 evidence (pre-refactor) and this run produce identical SYSOUT blocks
    before = (R / 'docs/evidence/mvs6-ai.txt').read_text().splitlines()
    bst = [i for i, l in enumerate(before) if l == 'PACMAN MVS-6 SMART GHOSTS']
    assert len(bst) == len(RUNS)
    for bs, s, n in zip(bst, starts, RUNS):
        assert before[bs:bs + len(exp[n])] == lines[s:s + len(exp[n])], f'{n}: differs from pre-refactor MVS-6'
    print('(identical to pre-refactor MVS-6 on', len(RUNS), 'runs)', len(rcs), 'steps RC 0000')
