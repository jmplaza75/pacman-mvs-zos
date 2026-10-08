#!/usr/bin/env python3
"""MVS-G4 acceptance (glyph profiles of the TSC renderer; presentation only). Design: docs/G4-GLYPHS.md.
Local:    core frozen; model invariants (CLASSIC = G3 model, reverse mapping, tables, facing, edge-case coverage).
Hercules: test_g4.py G4-LISTING
  - every step RC 0000 (uploads, compiles, 2 assemblies, 2 links, 19 batch, 6 TSO, 26 TSD dry runs, 1 QRY run);
  - the 25 batch/TSO output blocks are byte-identical to the 1.0-MVS release evidence (oracle);
  - every TSD data stream equals tests/ref_g4_screen.py byte for byte (the 12 G3 runs = the G3 model, i.e. CLASSIC is
    the G3 renderer unchanged; 14 runs with profiles G, B, C and A) and each run ends with the model's end line;
  - PACQRY on the recorded Query Replies (tests/qry_cases.py) gives exactly the expected colour/highlight/GE flags.
"""
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tools'))
import ref_g3_screen as g3  # noqa: E402
from ref_g4_screen import frames, cells, CP310  # noqa: E402
import ref_g2_screen as g2  # noqa: E402
from ref_mvs6 import simulate, Game, parse_config  # noqa: E402
from qry_cases import cases, expect  # noqa: E402
from make_deck import TSD as DECK_TSD, build  # noqa: E402
from test_g0 import blocks, oracle, BANNER  # noqa: E402  (also runs the G0 local checks)

TSD = [(c[0], *(x == 'Y' for x in c[1:3]), c[3], c[4] if len(c) > 4 else 'C') for c in DECK_TSD['G4']]
RESOLVED = {'G': 'G', 'B': 'B', 'C': 'C', 'A': 'C'}           # TSD: no query, so AUTO = CLASSIC
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
ref = [frames(c, h, a, r, RESOLVED[p]) for c, h, a, r, p in TSD]
assert all(len(f) < 2048 for fs in ref for f in fs)

# 1. CLASSIC is the G3 renderer: the first 12 runs are the G3 deck's runs and equal the G3 model
for (c, h, a, r, p), fs in zip(TSD[:12], ref[:12]):
    assert p == 'C' and fs == g3.frames(c, h, a, r), c
assert ref[24] == g3.frames('MOVES', True, True, 'P') and ref[25] == ref[24]          # explicit C and TSD AUTO = G3

# 2. reverse mapping: every G / B image maps back to the G3 image (only the presentation changes); walls: a filled
#    block (blank, wall colour, reverse) with highlighting, '#' without
BACK = {CP310[k]: v for k, v in (('⊂', 'C'), ('⊃', 'C'), ('○', 'O'), ('∩', 'G'), ('⍝', 'W'), ('•', '.'))}
BBACK = {0xB3: '.'}
ai, n, cards = parse_config((R / 'tests/cases/MULTI.txt').read_text().splitlines())
g = Game(ai, n)
for u in 'RDLRDR':
    res = g.step(u)
    for hi, anim, vis in ((True, False, 0), (True, True, 0), (True, True, 1), (False, True, 1)):
        want = g3.cells(g, u, res, None, hi, g3.GLYPHS[vis] if anim else ('P', 'G'))
        for prof, table in (('G', {**BACK, **({} if anim else {CP310['⊂']: 'P', CP310['⊃']: 'P'})}), ('B', BBACK)):
            img = cells(g, u, res, None, hi, prof, anim, vis, 'L' if u == 'L' else 'R')
            got = []
            for q, (b, col, h, ge) in enumerate(img):
                board = 240 <= q < 1040 and 30 <= q % 80 < 50
                if board and col == g2.WALL and b == 0x40 and h == g2.REVERSE:
                    got.append(('#', col, 0))
                    continue
                assert ge == (1 if prof == 'G' and board and b in table else 0)
                got.append((table[b] if board and b in table else bytes([b]).decode('cp037'), col, h))
            assert got == want, (prof, u, hi, anim, vis)

# 3. static: PACPAL holds the profile values the model uses (no wall tiles any more: D29 revision)
pal = (R / 'src/copy/PACPAL.cpy').read_text()
vals = {k: int(v) for k, v in re.findall(r'05  (HI-WALL|PEL-G|PEL-B|GPL-RIGHT|GPL-LEFT|GPL-CLOSED|GGH-1|GGH-2)\s+PIC 999 VALUE (\d+)', pal)}
assert vals == {'HI-WALL': g2.REVERSE, 'PEL-G': CP310['•'], 'PEL-B': 0xB3, 'GPL-RIGHT': CP310['⊂'], 'GPL-LEFT': CP310['⊃'],
                'GPL-CLOSED': CP310['○'], 'GGH-1': CP310['∩'], 'GGH-2': CP310['⍝']}, vals
assert 'TILE-' not in pal and 'MASK' not in (R / 'src/cobol/PACSCR.cob').read_text()

# 3b. wall occupancy (model): for every profile and highlight setting the set of occupied wall cells is exactly the
#     CLASSIC '#' set of LEVEL1 (98 cells), each one visibly occupied: '#' or a reverse-video block in the wall colour
level1 = Game(1, 1).grid
WALLS = {(j, i) for j in range(10) for i in range(20) if level1[j][i] == '#'}
assert len(WALLS) == 98


def wall_cells(img, hi_on, prof):
    occ = set()
    for j in range(10):
        for i in range(20):
            b, col, h, ge = img[(3 + j) * 80 + 30 + i]
            filled = col == g2.WALL and b == 0x40 and h == g2.REVERSE and ge == 0
            hashed = col == g2.WALL and b == ord('#'.encode('cp037')) and h == 0 and ge == 0
            assert not (filled and (prof == 'C' or not hi_on)) and not (hashed and prof != 'C' and hi_on)
            if filled or hashed:
                occ.add((j, i))
    return occ


g = Game(1, 1)
for prof in 'CBG':
    for hi_on in (True, False):
        assert wall_cells(cells(g, ' ', 'START  ', None, hi_on, prof, True, 0, 'R'), hi_on, prof) == WALLS, (prof, hi_on)

# 4. facing (FACE case): L blocked at start keeps R; L/R moves set it; vertical moves, bumps (also lowercase r/l),
#    invalid input, redraw and ticks keep it; it survives a death while moving left
faces = []
frames('FACE', True, True, 'P', 'G', faces)
assert ''.join(faces) == 'RRRRRLRRRRRRRRLLLLLLRLLLLR', ''.join(faces)
ai, n, cards = parse_config((R / 'tests/cases/FACE.txt').read_text().splitlines())
g, seen = Game(ai, n), []
for c in cards:
    u = c.strip()[:1].upper()
    if u and u in 'UDLR':
        seen.append((c.strip(), g.step(u).strip()))
assert ('L', 'BLOCKED') == seen[0] and ('L', 'DIED') in seen and ('r', 'BLOCKED') in seen and ('l', 'BLOCKED') in seen

# 5. coverage (D12) of the stream shapes
G_RUNS = range(12, 21)
assert all(f.count(0x08) >= 2 for k in G_RUNS for f in ref[k] if f[0] == 0xC3 and len(f) > 600)   # GE in full screens
assert any(f[0] == 0xC2 and 0x08 in f for f in ref[16])                                    # GE ticks (TICKS, G)
assert any(bytes([0x28, 0x42, 0x00, 0x40]) in f for f in ref[12][1:])                       # eaten pellet -> plain blank
assert len(ref[13]) == 4 and len(ref[13][2]) > 600                                          # empty ENTER = full redraw (G)
assert all(0x08 not in f for k in (21, 22, 23) for f in ref[k])                            # BASE: no GE at all
assert max(len(f) for fs in ref for f in fs) < 2048
print('local checks PASS:', [len(f) for f in ref], 'screens per run; first G screen', len(ref[12][0]), 'bytes')

if len(sys.argv) == 2:
    lines = Path(sys.argv[1]).read_text().splitlines()
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', build('G4', 'HERC01.PACMAN'), re.M))
    rcs = re.findall(r'PACBLDG4\s+(\w+)\s+(?:IEBGENER|IKFCBL00|IFOX00|IEWL|PACMAIN|PACQRYT)\s+RC= (\d{4})', '\n'.join(lines))
    assert len(rcs) == nsteps and all(r == '0000' for _, r in rcs), (nsteps, len(rcs), [x for x in rcs if x[1] != '0000'])
    assert not [l for l in lines if re.search(r'IKF\d{4}I-[WCE]', l)], 'compiler warnings'
    batch_or, tso_or = oracle()
    assert blocks(lines, BANNER) == list(batch_or.values()) + list(tso_or.values()), 'oracle changed'
    streams, j = [], 0
    while j < len(lines):
        m2 = re.match(r'TSD FRAME LEN(\d{4})$', lines[j])
        if not m2:
            j += 1
            continue
        n, hexs, j = int(m2.group(1)), '', j + 1
        while j < len(lines) and lines[j].startswith('TSD ') and not lines[j].startswith('TSD FRAME'):
            hexs += lines[j][4:].strip()
            j += 1
        data = bytes.fromhex(hexs)
        assert len(data) == n, (n, len(data))
        streams.append(data)
    want = [f for fs in ref for f in fs]
    assert len(streams) == len(want), (len(streams), len(want))
    for q, (a, b) in enumerate(zip(streams, want)):
        assert a == b, f'stream {q}: first difference at byte {next((x for x in range(min(len(a), len(b))) if a[x] != b[x]), min(len(a), len(b)))}'
    ends = [l for l in lines if l in ('QUIT', 'EOF', 'LOST', 'WIN')][-len(TSD):]
    assert ends == [simulate((R / f'tests/cases/{c}.txt').read_text().splitlines())[-4] for c, *_ in TSD], ends
    qry = [l for l in lines if l.startswith('QRY ') and 'LEN=' in l]
    exp = [f'QRY {name:<8} LEN={len(b):04d} C={c} H={h} GE={ge}' for name, b in cases() for c, h, ge in [expect(b)]]
    assert qry == exp, (qry, exp)
    pos, per_run = 0, []
    for fs in ref:
        per_run.append(streams[pos:pos + len(fs)])
        pos += len(fs)
    # wall occupancy on the REAL streams: replay every run on a terminal image (full screens reset it, partial screens
    # and ticks overwrite cells) and check after every stream that the occupied wall cells are exactly LEVEL1's 98
    def apply(img, ds):
        if ds[1:6] == bytes([0x11, 0x40, 0x40, 0x1D, 0x60]):
            img[:] = [(0x40, 0, 0, 0)] * 1920
        q, co, hh, k = 0, 0, 0, 1
        while k < len(ds):
            b = ds[k]
            if b == 0x11:
                q, k = g2.CODES.index(ds[k + 1]) * 64 + g2.CODES.index(ds[k + 2]), k + 3
            elif b == 0x28:
                if ds[k + 1] == 0x42:
                    co = ds[k + 2]
                elif ds[k + 1] == 0x41:
                    hh = ds[k + 2]
                else:
                    co = hh = 0
                k += 3
            elif b == 0x1D:
                img[q], q, k = (0x1D, 0, 0, 0), q + 1, k + 2
            elif b == 0x13:
                k += 1
            elif b == 0x08:
                img[q], q, k = (ds[k + 1], co, hh, 1), q + 1, k + 2
            else:
                img[q], q, k = (b, co, hh, 0), q + 1, k + 1
    checked = 0
    for (c, h, a, r, prof), run in zip(TSD, per_run):
        img = [(0x40, 0, 0, 0)] * 1920
        for ds in run:
            apply(img, ds)
            assert wall_cells(img, h, RESOLVED[prof]) == WALLS, (c, prof, h)
            checked += 1
    print('traffic (bytes): MOVES anim partial CLASSIC', sum(map(len, per_run[0])), 'GRAPHIC', sum(map(len, per_run[12])),
          '| MULTI CLASSIC', sum(map(len, per_run[2])), 'GRAPHIC', sum(map(len, per_run[14])), 'BASE', sum(map(len, per_run[21])))
    print('MVS-G4 PASS:', len(rcs), 'steps RC 0000; oracle unchanged;', len(streams), 'TSC streams identical to the model;',
          len(qry), 'PACQRY cases as expected;', checked, 'replayed screens with the 98 LEVEL1 wall cells occupied')
