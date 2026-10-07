#!/usr/bin/env python3
"""MVS-3 acceptance. Local: map sync + model sanity. With a job listing: all RC 0000 and the three
runs' SYSOUT equal the independent reference model output (tests/expected/MVS3-*.txt)."""
import re, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs3 import simulate  # noqa: E402

RUNS = ('MOVES', 'EOF', 'WIN')
lit = re.findall(r"FILLER\s+PIC X\(20\) VALUE '([^']*)'", (R / 'src/cobol/PACMAIN.cob').read_text())
assert lit == (R / 'maps/LEVEL1.txt').read_text().splitlines(), 'map mismatch'
for n in RUNS:
    exp = (R / f'tests/expected/MVS3-{n}.txt').read_text().splitlines()
    assert exp == simulate((R / f'tests/cases/{n}.txt').read_text().splitlines()), n
win = (R / 'tests/expected/MVS3-WIN.txt').read_text()
assert 'SCORE 1010' in win and 'WIN' in win.splitlines() and ' L=000' in win   # 101 pellets x 10
assert len(re.findall(r'^T\d{3} ', win, re.M)) == 186 and 'T186' not in win                          # trailing command ignored
mv = (R / 'tests/expected/MVS3-MOVES.txt').read_text()
assert 'T004 L MOVED   X=03 Y=02 S=0020 L=099' in mv     # revisiting an eaten cell scores nothing
assert 'T003 U BLOCKED X=04 Y=02 S=0020 L=099' in mv     # wall bump scores nothing
print('local checks PASS')
if len(sys.argv) > 1:
    t = open(sys.argv[1]).read()
    rcs = re.findall(r'(\w+)\s+(?:IEBGENER|IKFCBL00|IEWL|PACMAIN)\s+RC= (\d{4})', t)
    assert len(rcs) == 6 and all(r == '0000' for _, r in rcs), rcs
    lines = t.splitlines()
    starts = [i for i, l in enumerate(lines) if l == 'PACMAN MVS-3 PELLETS AND SCORE']
    assert len(starts) == 3, starts
    for s, n in zip(starts, RUNS):
        exp = (R / f'tests/expected/MVS3-{n}.txt').read_text().splitlines()
        assert lines[s:s + len(exp)] == exp, f'{n}: runtime output differs'
    print('MVS-3 runtime PASS', rcs)
