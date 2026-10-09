#!/usr/bin/env python3
"""MVS-GS acceptance (scaled renderer; presentation only). Design: docs/GS-SCALED.md (D31).
Local:    core frozen; model invariants: PACPAL tables = the design, wall contours (every wall/corridor boundary drawn,
          one-cell walls double-sided, outer border double, interiors blank), invalidation (a changed logical cell
          touches only its own 8 cells), every stream <= 2048 bytes, fallback runs = the G4 model.
Hercules: test_gs.py GS-LISTING
  - every step RC 0000 and no compiler warnings;
  - the 25 batch/TSO output blocks are byte-identical to the 1.0-MVS release evidence (oracle);
  - the 26 G4 runs (no PARM column 17 = SCALE(NO)) equal tests/ref_g4_screen.py byte for byte (G4 regression);
  - the 18 MVS-GS runs equal tests/ref_gs_screen.py byte for byte (scaled 4x2/3x2, the four end banners, AUTO,
    fallbacks, the size guard T, explicit N); every run ends with the model's end line;
  - every real stream <= 2048 bytes (T run: <= 1000); replaying the real streams on a 3270 buffer image (RA, GE, SBA,
    SF, IC; full screens start from a nulled buffer) gives exactly the model image after every stream;
  - PACQRY cases as in G4.
"""
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tools'))
import ref_g4_screen as g4  # noqa: E402
import ref_gs_screen as gs  # noqa: E402
import ref_g2_screen as g2  # noqa: E402
from ref_mvs6 import simulate, Game, parse_config  # noqa: E402
from qry_cases import cases, expect  # noqa: E402
from make_deck import TSD as DECK_TSD, GS_RUNS, build  # noqa: E402
from test_g0 import blocks, oracle, BANNER  # noqa: E402  (also runs the G0 local checks)

subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
G4_RUNS = DECK_TSD['G4']
assert DECK_TSD['GS'] == G4_RUNS + GS_RUNS and len(G4_RUNS) == 26 and len(GS_RUNS) == 18
G4_RESOLVED = {'G': 'G', 'B': 'B', 'C': 'C', 'A': 'C'}          # TSD: no query, so glyph AUTO = CLASSIC


def resolve(run):
    """PACPLAT resolution in TSD: scale A -> 4; scaled only with highlight Y and glyphs G (resolved)."""
    case, h, a, r, glyphs, scale = run
    prof = G4_RESOLVED[glyphs]
    s = '4' if scale == 'A' else scale
    if s not in '43T' or h != 'Y' or prof != 'G':
        s = 'N'
    return case, h == 'Y', a == 'Y', r, prof, s


def ref_run(run):
    if len(run) == 5 or len(run) < 5:
        c, h, a, r, p = (*run, 'C') if len(run) == 4 else run
        return g4.frames(c, h == 'Y', a == 'Y', r, G4_RESOLVED[p])
    case, hi, anim, redraw, prof, s = resolve(run)
    if s in '43':
        return gs.frames(case, anim, redraw, s)
    return g4.frames(case, hi, anim, redraw, prof)          # N (any reason) and T (guard): the G4 renderer


RUNS = G4_RUNS + GS_RUNS
ref = [ref_run(x) for x in RUNS]
RES = [None] * 26 + [resolve(x) for x in GS_RUNS]

# 1. SCALE(NO) regression: the first 26 runs are exactly the G4 deck's runs and model; fallbacks = G4 model
for run, fs in zip(G4_RUNS, ref[:26]):
    c, h, a, r = run[:4]
    p = run[4] if len(run) > 4 else 'C'
    assert fs == g4.frames(c, h == 'Y', a == 'Y', r, G4_RESOLVED[p]), run
scaled = [k for k in range(26, 44) if RES[k][5] in '43']
assert [RES[k][5] for k in range(26, 44)] == list('444444444333') + ['4', 'N', 'N', 'N', 'T', 'N'], RES[26:]
assert ref[26 + 13] == g4.frames('MOVES', False, True, 'P', 'G')         # no highlight -> G4 GRAPHIC
assert ref[26 + 14] == g4.frames('MOVES', True, True, 'P', 'B')          # BASE -> G4 BASE
assert ref[26 + 15] == g4.frames('MOVES', True, True, 'P', 'C')          # TSD AUTO glyphs = CLASSIC -> G4 CLASSIC
assert ref[26 + 16] == g4.frames('MULTI', True, True, 'P', 'G')          # guard T -> G4 GRAPHIC from the 1st screen
assert gs.frames('MULTI', True, 'P', '4')[0][:1] == b'\xc3' and len(gs.frames('MULTI', True, 'P', '4')[0]) > 1000
assert ref[26 + 12] == gs.frames('MOVES', True, 'P', '4')                # AUTO = 4x2

# 2. size: every model stream fits PACFSIO (2048); the guard run's first scaled screen would not fit 1000
assert max(len(f) for fs in ref for f in fs) <= 2048
assert max(len(f) for f in ref[26 + 16]) <= 1000

# 3. PACPAL holds the design values used by the model
pal = (R / 'src/copy/PACPAL.cpy').read_text()
num = {k: int(v) for k, v in re.findall(r'05  ((?:SG|LS)-[\w-]+)\s+PIC 9+ VALUE (\d+)', pal)}
assert {k: num[k] for k in ('SG-HLINE', 'SG-VLINE', 'SG-TL', 'SG-TR', 'SG-BL', 'SG-BR', 'SG-UPPER', 'SG-LOWER',
                            'SG-EYE')} == dict(zip(['SG-HLINE', 'SG-VLINE', 'SG-TL', 'SG-TR', 'SG-BL', 'SG-BR',
                                                    'SG-UPPER', 'SG-LOWER', 'SG-EYE'],
                                                   [gs.HLINE, gs.VLINE, gs.TL, gs.TR, gs.BL, gs.BR, gs.UPPER, gs.LOWER,
                                                    gs.EYE]))
assert (num['LS-STATUS-ROW'], num['LS-MSG-ROW'], num['LS-CMD-ROW'], num['LS-SF-ROW'], num['LS-GHOSTS-COL'],
        num['LS-HELP-COL'], num['LS-BOARD-COL-4'], num['LS-BOARD-COL-3'], num['LS-PEL-COL']) == \
    (21, gs.MSG_ROW, gs.CMD_ROW, gs.SF_ROW, 64, 20, gs.BOARD_COL[4], gs.BOARD_COL[3], 2)
spr = dict(re.findall(r"05  (SPR-[43])\s+PIC X\(\d+\) VALUE\s+'([^']*)'", pal))


def letters(w):
    out = ''
    for name, ghost in (('PR', 0), ('PL', 0), ('PC', 0), ('GA', 1), ('GB', 1)):
        for row in gs.sprite(w, name, 1, ghost):
            out += ''.join({0x93: 'T', 0x94: 'B', 0xA1: 'E'}.get(b, 'F' if h else ' ') for b, c, h, ge in row)
    return out


assert spr == {'SPR-4': letters(4), 'SPR-3': letters(3)}, (spr, letters(4), letters(3))

# 4. wall contours on LEVEL1: for every wall cell and every open side (corridor or outside), the sub-cells along that
#    side carry the line (top/bottom: ─ or a corner; left/right: │ or a corner); a side towards another wall carries no
#    straight line; a wall cell surrounded by walls (incl. diagonals) is blank; one-cell walls get two parallel lines
grid = Game(1, 1).grid
H_OK, V_OK = {gs.HLINE, gs.TL, gs.TR, gs.BL, gs.BR}, {gs.VLINE, gs.TL, gs.TR, gs.BL, gs.BR}
doubled = 0
for w in (4, 3):
    for y in range(10):
        for x in range(20):
            if grid[y][x] != '#':
                continue
            t = gs.contour(grid, x, y, w)
            n, s, wl, e = (not gs.is_wall(grid, x, y - 1), not gs.is_wall(grid, x, y + 1),
                           not gs.is_wall(grid, x - 1, y), not gs.is_wall(grid, x + 1, y))
            assert all(c in H_OK for c in t[0]) == n or (not n and t[0][0] in V_OK | {0, gs.BR}), (x, y)
            if n:
                assert all(c in H_OK for c in t[0]), (w, x, y)
            if s:
                assert all(c in H_OK for c in t[1]), (w, x, y)
            if wl:
                assert t[0][0] in V_OK and t[1][0] in V_OK, (w, x, y)
            if e:
                assert t[0][-1] in V_OK and t[1][-1] in V_OK, (w, x, y)
            if not n:
                assert all(c == 0 for c in t[0][1:-1]), (w, x, y)
            if not s:
                assert all(c == 0 for c in t[1][1:-1]), (w, x, y)
            if all(gs.is_wall(grid, x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                assert t == [[0] * w, [0] * w], (w, x, y)
            if n and s:
                doubled += 1
                assert all(c in H_OK for c in t[0] + t[1])
assert doubled > 0
# outer border: rows 1 and 20 (4x2) are ─ lines closed by ┌ ┐ / └ ┘; columns 1 and 80 are │
img = gs.image(Game(1, 1), ' ', 'START  ', None, 4, False, 0, 'R')
top = [img[i][0] for i in range(80)]
assert top[0] == gs.TL and top[79] == gs.TR and set(top[1:79]) == {gs.HLINE}
bottom = [img[19 * 80 + i][0] for i in range(80)]
assert bottom[0] == gs.BL and bottom[79] == gs.BR and set(bottom[1:79]) == {gs.HLINE}
assert all(img[r * 80][0] == gs.VLINE and img[r * 80 + 79][0] == gs.VLINE for r in range(1, 19))
assert all(img[r * 80 + 1][0] == 0x40 for r in range(1, 19))           # gap between the two border lines

# 5. invalidation: between two consecutive model images of a scaled run, every changed board cell lies in the tile of
#    a logical cell whose content (wall/pellet/empty/sprite+frame) changed, and every such logical cell has changed
#    cells; walls are never invalidated
def board_changes(a, b, w):
    out = set()
    for i in range(1600):
        q = (i // 80) * 80 + i % 80
        if i % 80 >= gs.BOARD_COL[w] - 1 and i % 80 < gs.BOARD_COL[w] - 1 + 20 * w and a[q] != b[q]:
            out.add(((i % 80 - gs.BOARD_COL[w] + 1) // w, i // 160))
    return out


checked_inv = 0
for w in (4, 3):
    ai, n, cards = parse_config((R / 'tests/cases/MULTI.txt').read_text().splitlines())
    g = Game(ai, n)
    prev, vis = None, 0
    for u in 'RDLRDRUUL':
        res = g.step(u)
        cur = gs.image(g, u, res, None, w, True, vis, 'R')
        if prev is not None:
            for x, y in board_changes(prev, cur, w):
                assert grid[y][x] != '#', (x, y)
            checked_inv += 1
        prev, vis = cur, vis ^ 1
assert checked_inv == 16

# 6. coverage of the stream shapes (D12)
S = {k: ref[k] for k in range(26, 44)}
ends = {k: S[k][-1] for k in scaled}
assert all(f[0] == 0xC3 and len(f) > 600 for f in ends.values())                          # end screen = full
assert any(bytes([0x3C]) in f and bytes([0x08, gs.HLINE]) in f for f in S[26])            # RA + GE in full screens
assert any(f[0] == 0xC2 for f in S[26 + 4])                                               # ticks (TICKS 4x2)
assert len(S[26 + 1]) >= 4 and len(S[26 + 1][2]) > 1000                                   # TSORDR: redraw = full
for k, kind in ((26, 'QUIT'), (28, 'EOF'), (32, 'LOST'), (33, 'WIN')):
    text = gs.BANNERS[kind][0].strip()
    assert text.encode('cp037') in S[k][-1], kind
print('local checks PASS:', len(RUNS), 'runs,', sum(map(len, ref)), 'streams; first 4x2 screen', len(S[26][0]),
      'bytes, 3x2', len(S[36][0]), '; largest', max(len(f) for fs in ref for f in fs))

if len(sys.argv) == 2:
    lines = Path(sys.argv[1]).read_text().splitlines()
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', build('GS', 'HERC01.PACMAN'), re.M))
    rcs = re.findall(r'PACBLDGS\s+(\w+)\s+(?:IEBGENER|IKFCBL00|IFOX00|IEWL|PACMAIN|PACQRYT)\s+RC= (\d{4})', '\n'.join(lines))
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
    assert max(map(len, streams)) <= 2048
    ends = [l for l in lines if l in ('QUIT', 'EOF', 'LOST', 'WIN')][-len(RUNS):]
    assert ends == [simulate((R / f'tests/cases/{c[0]}.txt').read_text().splitlines())[-4] for c in RUNS], ends
    qry = [l for l in lines if l.startswith('QRY ') and 'LEN=' in l]
    exp = [f'QRY {name:<8} LEN={len(b):04d} C={c} H={h} GE={ge}' for name, b in cases() for c, h, ge in [expect(b)]]
    assert qry == exp, (qry, exp)
    pos, per_run = 0, []
    for fs in ref:
        per_run.append(streams[pos:pos + len(fs)])
        pos += len(fs)
    assert max(map(len, per_run[26 + 16])) <= 1000

    # terminal replay of the scaled runs: decode the real streams like a 3270 (full screens: Erase/Write after the
    # PACFSIO clear prefix = all nulls; partials: Write) and compare with the model image after every stream
    def apply(img, ds):
        if ds[0] == 0xC3 and ds[1:2] == b'\x11' and len(ds) > 600:
            img[:] = [None] * 1920
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
                img[q], q, k = ('SF', ds[k + 1]), q + 1, k + 2
            elif b == 0x13:
                k += 1
            elif b == 0x3C:
                stop = g2.CODES.index(ds[k + 1]) * 64 + g2.CODES.index(ds[k + 2])
                ge = ds[k + 3] == 0x08
                ch = ds[k + 4] if ge else ds[k + 3]
                k += 5 if ge else 4
                while True:
                    img[q] = (ch, co, hh, 1 if ge else 0)
                    q = (q + 1) % 1920
                    if q == stop:
                        break
            elif b == 0x08:
                img[q], q, k = (ds[k + 1], co, hh, 1), q + 1, k + 2
            else:
                img[q], q, k = (b, co, hh, 0), q + 1, k + 1

    def same(term, model):
        for q in range(1920):
            t, m = term[q], model[q]
            if (t is not None and t[0] == 'SF') or q == (gs.CMD_ROW - 1) * 80 + 14:
                continue                                     # field attributes and the input field (not in the image)
            if t is None:
                t = (0x40, 0, 0, 0)
            if t[0] == 0x40 and t[2] == 0 and t[3] == 0 and m[0] == 0x40 and m[2] == 0 and m[3] == 0:
                continue                                     # blank / null: colour of a blank is invisible
            if t != m and not (t[0] == 0x40 and t[2] == 0 and m == (0x40, 0, 0, 0)):
                return q
        return None

    replayed = 0
    for k in scaled:
        case, hi, anim, redraw, prof, s = RES[k]
        w = int(s)
        # the model images, in the same order as the streams (re-run the model flow, keeping each image)
        imgs = []
        orig_full, orig_partial = gs.full, gs.partial
        gs.full = lambda img, _o=orig_full: (imgs.append(img), _o(img))[1]
        gs.partial = lambda cur, prev, kind, _o=orig_partial: (lambda r: (imgs.append(cur) if r is not None else None, r)[1])(_o(cur, prev, kind))
        try:
            again = gs.frames(case, anim, redraw, s)
        finally:
            gs.full, gs.partial = orig_full, orig_partial
        assert again == ref[k] and len(imgs) == len(per_run[k])
        term = [None] * 1920
        for ds, model in zip(per_run[k], imgs):
            apply(term, ds)
            bad = same(term, model)
            assert bad is None, (case, s, bad // 80 + 1, bad % 80 + 1, term[bad], model[bad])
            replayed += 1
    print('traffic (bytes): MOVES 4x2', sum(map(len, per_run[26])), '| MULTI 4x2', sum(map(len, per_run[28])),
          '3x2', sum(map(len, per_run[36])), '| MULTI G4 GRAPHIC', sum(map(len, per_run[14])))
    print('MVS-GS PASS:', len(rcs), 'steps RC 0000; oracle unchanged;', len(streams), 'TSC streams identical to the models',
          '(26 G4 runs + 18 GS runs);', replayed, 'scaled streams replayed on a 3270 image = model;', len(qry),
          'PACQRY cases')
