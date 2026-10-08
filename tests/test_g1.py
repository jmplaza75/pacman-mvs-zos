#!/usr/bin/env python3
"""MVS-G1 acceptance (colour renderer TSC).
Local:    core frozen; reference renderer sanity (palette, one screen per read).
Hercules: test_g1.py G1-LISTING
  - every step RC 0000 (uploads, compiles, 2 assemblies, link, 19 batch, 6 TSO, 5 TSD dry runs);
  - the 25 batch/TSO output blocks are byte-identical to the 1.0-MVS release evidence (oracle, monochrome fallback);
  - every TSD screen (the TSC data stream printed in hex) equals tests/ref_g1_screen.py byte for byte,
    and each TSD run ends with the same end lines as the model.
"""
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_g1_screen import frames, screen, PLAYER, GHOSTS, WALL, PELLET  # noqa: E402
from ref_mvs6 import simulate  # noqa: E402
from test_g0 import blocks, oracle, BANNER  # noqa: E402  (also runs the G0 local checks)

TSD = ('MOVES', 'TSORDR', 'MULTI', 'C3N2', 'DIE1')
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
assert (PLAYER, GHOSTS, WALL, PELLET) == (0xF6, (0xF2, 0xF3, 0xF5), 0xF1, 0xF7)
ref = {c: frames(c) for c in TSD}
assert len(ref['TSORDR']) == 4 and ref['TSORDR'][1] == ref['TSORDR'][2]     # empty line = identical redraw
assert all(len(f) < 2048 for fs in ref.values() for f in fs)
print('local checks PASS:', {c: len(f) for c, f in ref.items()}, 'screens')

if len(sys.argv) == 2:
    lines = Path(sys.argv[1]).read_text().splitlines()
    rcs = re.findall(r'(\w+)\s+(?:IEBGENER|IKFCBL00|IFOX00|IEWL|PACMAIN)\s+RC= (\d{4})', '\n'.join(lines))
    assert len(rcs) == 5 + 8 + 8 + 2 + 1 + 19 + 6 + 5 and all(r == '0000' for _, r in rcs), rcs
    batch_or, tso_or = oracle()
    assert blocks(lines, BANNER) == list(batch_or.values()) + list(tso_or.values()), 'oracle changed'
    got, i = [], 0
    while i < len(lines):
        m = re.match(r'TSD FRAME LEN(\d{4})$', lines[i])
        if not m:
            i += 1
            continue
        n, hexs, i = int(m.group(1)), '', i + 1
        while i < len(lines) and lines[i].startswith('TSD ') and not lines[i].startswith('TSD FRAME'):
            hexs += lines[i][4:].strip()
            i += 1
        data = bytes.fromhex(hexs)
        assert len(data) == n, (n, len(data))
        got.append(data)
    want = [f for c in TSD for f in ref[c]]
    assert len(got) == len(want), (len(got), len(want))
    for k, (a, b) in enumerate(zip(got, want)):
        assert a == b, f'screen {k}: first difference at byte {next(j for j in range(min(len(a), len(b))) if a[j] != b[j]) if a[:min(len(a), len(b))] != b[:min(len(a), len(b))] else min(len(a), len(b))}'
    ends = [l for l in lines if l in ('QUIT', 'EOF', 'LOST', 'WIN')][-len(TSD):]
    assert ends == [simulate((R / f'tests/cases/{c}.txt').read_text().splitlines())[-4] for c in TSD], ends
    print('MVS-G1 PASS:', len(rcs), 'steps RC 0000; oracle unchanged;', len(got), 'TSC screens identical to the model')
