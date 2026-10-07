#!/usr/bin/env python3
"""MVS-1 checks. Local: COBOL map literals == maps/LEVEL1.txt.
With a job listing argument: SYSOUT of the run step == tests/expected/MVS1.txt and all RC 0000."""
import re, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
src = (R / 'src/cobol/PACMAIN.cob').read_text()
lit = re.findall(r"FILLER\s+PIC X\(20\) VALUE '([^']*)'", src)
exp = (R / 'maps/LEVEL1.txt').read_text().splitlines()
assert lit == exp, 'COBOL map differs from maps/LEVEL1.txt'
assert len(exp) == 10 and all(len(r) == 20 for r in exp)
assert all(r[0] == r[-1] == '#' for r in exp) and set(exp[0]) == set(exp[-1]) == {'#'}
assert set(''.join(exp)) <= set('#. ')
print('local map checks PASS')
if len(sys.argv) > 1:
    t = open(sys.argv[1]).read()
    rcs = re.findall(r'(\w+)\s+(?:IEBGENER|IKFCBL00|IEWL|PACMAIN)\s+RC= (\d{4})', t)
    assert len(rcs) == 4 and all(r == '0000' for _, r in rcs), rcs
    want = (R / 'tests/expected/MVS1.txt').read_text()
    lines = t.splitlines()
    i = max(k for k, l in enumerate(lines) if l == 'PACMAN MVS-1 STATIC MAP 20X10')
    got = '\n'.join(lines[i:i + 12]) + '\n'
    assert got == want, 'runtime output differs:\n' + got
    print('MVS-1 runtime PASS', rcs)
