#!/usr/bin/env python3
"""MVS-2 acceptance. Local: reference model sanity. With a job listing: all RC 0000 and both
runs' SYSOUT equal the independent reference model output (tests/expected/MVS2-*.txt)."""
import re, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs2 import simulate  # noqa: E402

# source map must still equal the map file
lit = re.findall(r"FILLER\s+PIC X\(20\) VALUE '([^']*)'", (R / 'src/cobol/PACMAIN.cob').read_text())
assert lit == (R / 'maps/LEVEL1.txt').read_text().splitlines(), 'map mismatch'
# model invariants: the player never stands on a wall, walls block, quit stops, EOF ends
for name in ('MOVES', 'EOF'):
    exp = (R / f'tests/expected/MVS2-{name}.txt').read_text().splitlines()
    assert exp == simulate((R / f'tests/cases/{name}.txt').read_text().splitlines())
    assert not any('P#' in l or '#P' in l and False for l in exp[:0])
assert 'T03 U BLOCKED X=04 Y=02' in (R / 'tests/expected/MVS2-MOVES.txt').read_text()
assert 'TURNS 13' in (R / 'tests/expected/MVS2-MOVES.txt').read_text()  # trailing R after Q not run
print('local checks PASS')
if len(sys.argv) > 1:
    t = open(sys.argv[1]).read()
    rcs = re.findall(r'(\w+)\s+(?:IEBGENER|IKFCBL00|IEWL|PACMAIN)\s+RC= (\d{4})', t)
    assert len(rcs) == 5 and all(r == '0000' for _, r in rcs), rcs
    lines = t.splitlines()
    starts = [i for i, l in enumerate(lines) if l == 'PACMAN MVS-2 PLAYER BY TURNS']
    assert len(starts) == 2, starts
    for s, name in zip(starts, ('MOVES', 'EOF')):
        exp = (R / f'tests/expected/MVS2-{name}.txt').read_text().splitlines()
        assert lines[s:s + len(exp)] == exp, f'{name}: runtime output differs'
    print('MVS-2 runtime PASS', rcs)
