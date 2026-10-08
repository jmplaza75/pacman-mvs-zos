#!/usr/bin/env python3
"""MVS-G3 acceptance (partial redraw + glyph animation in the TSC renderer; presentation only).
Local:    core frozen; model invariants (see below).
Hercules: test_g3.py G3-LISTING
  - every step RC 0000 (uploads, compiles, 2 assemblies, link, 19 batch, 6 TSO, 12 TSD dry runs);
  - the 25 batch/TSO output blocks are byte-identical to the 1.0-MVS release evidence (oracle, monochrome fallback);
  - every TSD data stream (full, partial and tick) equals tests/ref_g3_screen.py byte for byte, and each run ends with
    the same end lines as the model;
  - ANIM(NO)+FULL streams equal the G2 model (tests/ref_g2_screen.py): the mechanics and the screens are those of G2;
  - ANIM(YES)+FULL vs ANIM(NO)+FULL from the REAL output: same length, the only differing bytes are glyphs
    (P->C/O, G->W): animation changes how the same state is drawn, never the state;
  - traffic table (bytes sent): partial vs full.
"""
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
import ref_g2_screen as g2  # noqa: E402
from ref_g3_screen import frames, cells, GLYPHS  # noqa: E402
from ref_mvs6 import simulate, Game, parse_config  # noqa: E402
from test_g0 import blocks, oracle, BANNER  # noqa: E402  (also runs the G0 local checks)

# (case, hilite, anim, redraw) in the order of the TSD steps of the G3 deck (tools/make_deck.py)
TSD = (('MOVES', 1, 1, 'P'), ('TSORDR', 1, 1, 'P'), ('MULTI', 1, 1, 'P'), ('DIE1', 1, 1, 'P'), ('C3N2', 0, 1, 'P'),
       ('TICKS', 1, 1, 'P'), ('MOVES', 1, 0, 'P'), ('MOVES', 1, 1, 'F'), ('TICKS', 1, 1, 'F'), ('MOVES', 1, 0, 'F'),
       ('DIE1', 1, 0, 'F'), ('MULTI', 1, 0, 'F'))
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
ref = [frames(c, bool(h), bool(a), r) for c, h, a, r in TSD]
assert all(len(f) < 2048 for fs in ref for f in fs)
# model invariants -----------------------------------------------------------------------------------------------
assert ref[9] == g2.frames('MOVES', True) and ref[10] == g2.frames('DIE1', True)       # ANIM(NO) FULL = G2 screens
assert ref[11] == g2.frames('MULTI', True)
assert len(ref[8]) == len(frames('TICKS', True, False, 'F'))                           # ticks are inert unless ANIM+PARTIAL
# glyph-only property of the image: mapping the animated glyphs back gives the G2 image for every logical screen
ai, n, cards = parse_config((R / 'tests/cases/MULTI.txt').read_text().splitlines())
g = Game(ai, n)
for u in 'RDLRD':
    g.step(u)
    for gl in GLYPHS:
        a = cells(g, 'x', 'MOVED  ', None, True, gl)
        b = cells(g, 'x', 'MOVED  ', None, True, ('P', 'G'))
        back = [(('P' if c in 'CO' else 'G' if c == 'W' else c), col, h) if 240 <= q < 1040 else (c, col, h)
                for q, (c, col, h) in enumerate(a)]            # board = rows 4-13 only
        assert back == b
# traffic: partial is far smaller than full
assert sum(map(len, ref[0])) * 3 < sum(map(len, ref[9])) and sum(map(len, ref[2])) * 3 < sum(map(len, ref[11]))
assert sum(map(len, ref[3])) * 3 < sum(map(len, ref[10]))
# coverage (D12): blink message in a partial, redraw is a full screen, ticks, ticks inert under FULL
assert any(bytes([0x28, 0x41, 0xF1]) in f for f in ref[0])
assert len(ref[1]) == 4 and ref[1][2][0] == 0xC3 and len(ref[1][2]) > 500 and len(ref[1][1]) < 300          # empty ENTER = full redraw
assert sum(1 for f in ref[5] if f[0] == 0xC2) >= 6 and all(f[0] in (0xC3, 0xC2) for f in ref[5])
assert all(len(f) > 400 for f in ref[8])                                           # FULL: only full screens
print('local checks PASS:', [len(f) for f in ref], 'screens per run')

if len(sys.argv) == 2:
    lines = Path(sys.argv[1]).read_text().splitlines()
    rcs = re.findall(r'(\w+)\s+(?:IEBGENER|IKFCBL00|IFOX00|IEWL|PACMAIN)\s+RC= (\d{4})', '\n'.join(lines))
    assert len(rcs) == 5 + 8 + 8 + 2 + 1 + 19 + 6 + len(TSD) and all(r == '0000' for _, r in rcs), rcs
    batch_or, tso_or = oracle()
    assert blocks(lines, BANNER) == list(batch_or.values()) + list(tso_or.values()), 'oracle changed'
    # frames of all TSD runs are printed one after the other; split them by the model's frame counts
    streams = []
    j = 0
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
    # real-output property: animation never changes anything but glyphs (TSD8 MOVES anim FULL vs TSD10 MOVES plain FULL)
    pos, per_run = 0, []
    for fs in ref:
        per_run.append(streams[pos:pos + len(fs)])
        pos += len(fs)
    P, G = 'P'.encode('cp037')[0], 'G'.encode('cp037')[0]
    C, O, W = 'C'.encode('cp037')[0], 'O'.encode('cp037')[0], 'W'.encode('cp037')[0]
    allowed = {(P, C), (P, O), (G, G), (G, W)}
    for anim_run, plain_run in ((per_run[7], per_run[9]),):
        assert len(anim_run) == len(plain_run)
        for a, b in zip(anim_run, plain_run):
            assert len(a) == len(b)
            assert all((y, x) in allowed or x == y for x, y in zip(a, b)), 'animation changed more than glyphs'
    full_b, part_b = sum(map(len, per_run[11])), sum(map(len, per_run[2]))
    print('traffic (bytes, same moves): MULTI full', full_b, 'partial', part_b, f'({full_b / part_b:.1f}x less);',
          'MOVES full', sum(map(len, per_run[9])), 'partial', sum(map(len, per_run[0])),
          'DIE1 full', sum(map(len, per_run[10])), 'partial', sum(map(len, per_run[3])))
    print('MVS-G3 PASS:', len(rcs), 'steps RC 0000; oracle unchanged;', len(streams), 'TSC streams identical to the model')
