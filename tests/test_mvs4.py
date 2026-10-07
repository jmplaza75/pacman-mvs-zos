#!/usr/bin/env python3
"""MVS-4 acceptance. Local: map sync + model checks. With a job listing: all RC 0000, every run's SYSOUT
equals the independent model (tests/expected/MVS4-*.txt) and ghost invariants hold in the real output."""
import re, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs4 import simulate, MAP0  # noqa: E402

RUNS = ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0')
lit = re.findall(r"FILLER\s+PIC X\(20\) VALUE '([^']*)'", (R / 'src/cobol/PACMAIN.cob').read_text())
assert lit == MAP0, 'map mismatch'


def ghost_invariants(lines, still):
    st = [l for l in lines if re.match(r'T\d{3} ', l)]
    pos = [tuple(map(int, re.search(r'G=(\d+),(\d+)', l).groups())) for l in st]
    for a, b in zip(pos, pos[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) <= (0 if still else 1), (a, b)
    assert all(MAP0[y - 1][x - 1] != '#' for x, y in pos), 'ghost inside a wall'
    return len(set(pos))


exp = {n: (R / f'tests/expected/MVS4-{n}.txt').read_text().splitlines() for n in RUNS}
for n in RUNS:
    assert exp[n] == simulate((R / f'tests/cases/{n}.txt').read_text().splitlines()), n
assert exp['WIN0'][-3:] == ['WIN', 'TURNS 183', 'SCORE 1000'] and any(' L=000 ' in l for l in exp['WIN0'])
assert exp['CATCH0'][-3].startswith('CAUGHT') and exp['CATCH0'][-2] == 'TURNS 024'   # trailing L ignored
assert exp['CATCH1'][-3] == 'CAUGHT' and exp['RAND'][-3] == 'EOF'
assert ghost_invariants(exp['RAND'], False) > 5          # the random ghost really roams
assert ghost_invariants(exp['WIN0'], True) == 1          # AI0 ghost never moves
print('local checks PASS')
if len(sys.argv) > 1:
    lines = open(sys.argv[1]).read().splitlines()
    rcs = re.findall(r'(\w+)\s+(?:IEBGENER|IKFCBL00|IEWL|PACMAIN)\s+RC= (\d{4})', '\n'.join(lines))
    assert len(rcs) == 8 and all(r == '0000' for _, r in rcs), rcs
    starts = [i for i, l in enumerate(lines) if l == 'PACMAN MVS-4 BASIC GHOST']
    assert len(starts) == 5, starts
    for s, n in zip(starts, RUNS):
        got = lines[s:s + len(exp[n])]
        assert got == exp[n], f'{n}: runtime output differs'
        ghost_invariants(got, n in ('WIN0', 'CATCH0'))
    print('MVS-4 runtime PASS', rcs)
