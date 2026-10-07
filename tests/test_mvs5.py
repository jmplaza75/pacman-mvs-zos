#!/usr/bin/env python3
"""MVS-5 acceptance. Local: map sync + model checks. With a job listing: all RC 0000, every run's SYSOUT
equals the independent model (tests/expected/MVS5-*.txt) and lives/ghost invariants hold in the real output."""
import re, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs5 import simulate, MAP0  # noqa: E402

RUNS = ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1')
lit = re.findall(r"FILLER\s+PIC X\(20\) VALUE '([^']*)'", (R / 'src/cobol/PACMAIN.cob').read_text())
assert lit == MAP0, 'map mismatch'


def invariants(lines, still):
    st = [l for l in lines if re.match(r'T\d{3} ', l)]
    g = [tuple(map(int, re.search(r'G=(\d+),(\d+)', l).groups())) for l in st]
    lv = [int(re.search(r' V=(\d)', l).group(1)) for l in st]
    for i in range(1, len(st)):
        died = ' DIED ' in st[i] or ' LOST ' in st[i]
        assert lv[i] == lv[i - 1] - (1 if died else 0), (i, 'lives')
        if not died:
            d = abs(g[i][0] - g[i - 1][0]) + abs(g[i][1] - g[i - 1][1])
            assert d <= (0 if still else 1), (i, 'ghost step')
        else:
            assert g[i] == (19, 9) or ' LOST ' in st[i], (i, 'ghost respawn')
            if ' DIED ' in st[i]:
                assert ' X=02 Y=02 ' in st[i], 'player respawn'
    assert all(MAP0[y - 1][x - 1] != '#' for x, y in g), 'ghost inside a wall'
    assert 'ST=READY' in st[0] and lv[0] == 3


exp = {n: (R / f'tests/expected/MVS5-{n}.txt').read_text().splitlines() for n in RUNS}
for n in RUNS:
    assert exp[n] == simulate((R / f'tests/cases/{n}.txt').read_text().splitlines()), n
    invariants(exp[n], n in ('WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER'))
end = {n: exp[n][-4:] for n in RUNS}
assert end['WIN0'] == ['WIN', 'TURNS 183', 'SCORE 1000', 'LIVES 3']
assert end['DIE1'][0] == 'QUIT' and end['DIE1'][3] == 'LIVES 2' and end['DIE1'][1] == 'TURNS 028'
assert end['LOST0'] == ['LOST', 'TURNS 072', 'SCORE 0230', 'LIVES 0']       # trailing R ignored
assert end['LOST1'][0] == 'LOST' and end['WINAFTER'][0] == 'WIN' and end['WINAFTER'][3] == 'LIVES 2'
assert end['CATCH0'][0] == 'EOF' and end['CATCH0'][3] == 'LIVES 2'          # play continues after a death
# D11 edge: last pellet eaten in the same tick as the ghost hit (engineered by tests/search_edge.py)
for n, lives_after, final in (('EDGE3', 2, 'WIN'), ('EDGE2', 1, 'WIN'), ('EDGE1', 0, 'LOST')):
    e = exp[n]
    last = [l for l in e if re.match(r'T\d{3} ', l)][-1]
    assert ' L=000 ' in last and f' V={lives_after} ' in last and ' S=1000 ' in last, (n, last)
    assert e[-4] == final and e[-1] == f'LIVES {lives_after}', n
    assert ('DIED' in last and 'ST=WON' in last) if final == 'WIN' else ('LOST' in last and 'ST=LOST' in last)
print('local checks PASS')
if len(sys.argv) > 1:
    lines = open(sys.argv[1]).read().splitlines()
    rcs = re.findall(r'(\w+)\s+(?:IEBGENER|IKFCBL00|IEWL|PACMAIN)\s+RC= (\d{4})', '\n'.join(lines))
    assert len(rcs) == 15 and all(r == '0000' for _, r in rcs), rcs
    starts = [i for i, l in enumerate(lines) if l == 'PACMAN MVS-5 LIVES AND CYCLE']
    assert len(starts) == 12, starts
    for s, n in zip(starts, RUNS):
        got = lines[s:s + len(exp[n])]
        assert got == exp[n], f'{n}: runtime output differs'
        invariants(got, n in ('WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER'))
    print('MVS-5 runtime PASS', len(rcs), 'steps RC 0000')
