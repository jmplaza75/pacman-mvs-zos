#!/usr/bin/env python3
"""MVS-GS geometry acceptance (docs/GS-GEOMETRY.md, D32; presentation and transport only).
Local:    core frozen; PACFSIO differs from the approved checkpoint (7f56300) only by inserted SENX lines (SEND / SENP /
          QRY / RECV / RECT / FSON / FSOF code byte-identical); the geometry model reduces to the GS / G4 models on 80x24;
          families / origins of the simulated canvases; every stream <= 2048 (guard run <= 1000); PACQRY geometry cases.
Hercules: test_gx.py GX-LISTING
  - every step RC 0000, no compiler warnings, the 1.0-MVS oracle byte-identical;
  - the 44 GS runs (no PARM column 18 = CANVAS DEFAULT) equal the GS / G4 models byte for byte (legacy regression);
  - the 17 geometry runs equal tests/ref_gx_screen.py byte for byte; every run ends with the model's end line;
  - TSX lines: per run one size switch (F5 080X024 for DEFAULT, 7E + the simulated size otherwise), the first full screen
    FIRST (FULLSCR), every later full screen with the run's command;
  - the scaled geometry streams replayed on a W x H 3270 buffer equal the model image after every stream;
  - PACQRY: the 20 recorded/derived replies give the expected capabilities and alternate size.
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
import ref_gx_screen as gx  # noqa: E402
import ref_g2_screen as g2  # noqa: E402
from ref_mvs6 import simulate  # noqa: E402
from qry_cases import cases, expect, expect_size  # noqa: E402
from make_deck import TSD as DECK_TSD, GX_RUNS, build  # noqa: E402
from test_g0 import blocks, oracle, BANNER  # noqa: E402

subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)

# 1. PACFSIO: the approved checkpoint's lines are all present, in order, and the only additions are the SENX lines
old = subprocess.run(['git', 'show', '7f56300:./src/asm/PACFSIO.asm'], cwd=R, capture_output=True, text=True,
                     check=True).stdout.splitlines()
new = (R / 'src/asm/PACFSIO.asm').read_text().splitlines()
# MVS-RT (D33): the POLL service (3 comment lines, 2 dispatch lines, the DOPOLL block) is checked by tests/test_rt.py
if 'DOPOLL   DS    0H' in new:
    a, b = new.index('DOPOLL   DS    0H'), new.index('RECTGOT  DS    0H')
    new = [l for k, l in enumerate(new) if not a <= k < b]
    new = [l for l in new if 'POLL' not in l and 'PROBE E14' not in l and 'WAIT: INPUT = LEN > 0' not in l]
k, added = 0, []
for line in new:
    if k < len(old) and line == old[k]:
        k += 1
    else:
        added.append(line)
assert k == len(old), 'a PACFSIO line was changed or removed'
assert len(added) == 12 and all('SENX' in l or l.startswith('*') or l.split()[0] in ('LR', 'LH', 'TPUT', 'B')
                                 for l in added), added
assert sum('TPUT' in l for l in added if not l.startswith('*')) == 1 and any('NOEDIT' in l for l in added)

RUNS = DECK_TSD['GX']
assert RUNS == DECK_TSD['GS'] + GX_RUNS and len(GX_RUNS) == 17 and len(DECK_TSD['GS']) == 44


def params(run):
    run = tuple(run) + ('C',) * (5 - len(run)) if len(run) < 5 else tuple(run)
    c, h, a, r, gl = run[:5]
    sc = run[5] if len(run) > 5 else 'N'
    cv = run[6] if len(run) > 6 else 'D'
    return c, h == 'Y', a == 'Y', r, gl, sc, cv


ref = [gx.frames(*params(x)) for x in RUNS]

# 2. legacy regression: on 80x24 the geometry model IS the GS / G4 model
G4_RESOLVED = {'G': 'G', 'B': 'B', 'C': 'C', 'A': 'C'}
for run, fs in zip(RUNS[:44], ref[:44]):
    c, h, a, r, gl, sc, cv = params(run)
    s = '4' if sc == 'A' else sc
    if s in '43' and h and G4_RESOLVED[gl] == 'G':
        assert fs == gs.frames(c, a, r, s), run
    else:
        assert fs == g4.frames(c, h, a, r, G4_RESOLVED[gl]), run
assert ref[44 + 15] == gs.frames('MOVES', True, 'P', '4')                        # explicit CANVAS D = 80x24 GS

# 3. geometry: families and origins as designed
fam = {}
for i, run in enumerate(GX_RUNS):
    c, h, a, r, gl, sc, cv = params(run)
    geo = gx.Geo(cv, sc in '43T' and h and gl == 'G', 3 if sc == '3' else 4)
    fam[i] = (geo.fam, geo.org, geo.w, geo.h)
assert fam[0][0] == 'W' and gx.Geo('W', True, 4).c0 == 21 and gx.Geo('W', True, 4).b0 == 4
assert fam[5][0] == 'W' and gx.Geo('X', True, 4).c0 == 27
assert fam[6][0] == 'T' and gx.Geo('T', True, 4).b0 == 12 and fam[7][0] == 'T' and gx.Geo('M', True, 4).b0 == 7
assert fam[10] == ('B', (1, 11), 100, 25)                                         # too small: 80x24 GS centred
assert fam[11] == ('B', (1, 41), 160, 30) and gx.Geo('L', True, 4).n == 4000      # > 4095 cells: 25 rows used
assert fam[12][0] == 'B' and fam[13][0] == 'G' and fam[16][0] == 'G'             # 3x2, not scaled, no highlight
assert ref[44 + 14] == [gx.relocate(gx.Geo('W', False, 4), f) for f in g4.frames('MULTI', True, True, 'P', 'G')]
assert ref[44 + 13] == [gx.relocate(gx.Geo('W', False, 4), f) for f in g4.frames('MOVES', True, True, 'P', 'G')]

# 4. sizes
assert max(len(f) for fs in ref for f in fs) <= 2048
assert max(len(f) for f in ref[44 + 14]) <= 1000
for i in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9):                                          # wide/tall runs: end screen + banner
    assert ref[44 + i][-1][0] == 0xC3 and 0x1D in ref[44 + i][-1]

# 5. PACQRY geometry expectations
SIZE = {name: expect_size(b) for name, b in cases()}
assert SIZE['C3270'] == (80, 24) and SIZE['M3'] == (80, 32) and SIZE['M4'] == (80, 43) and SIZE['M5'] == (132, 27)
assert SIZE['DYN'] == (120, 27) and SIZE['NOA6'] == (120, 27) and SIZE['NOA6UA'] == (80, 24)
print('local checks PASS:', len(RUNS), 'runs,', sum(map(len, ref)), 'streams; largest', max(len(f) for fs in ref for f in fs),
      '; first 120x27 screen', len(ref[44][0]), 'bytes')

if len(sys.argv) == 2:
    lines = Path(sys.argv[1]).read_text().splitlines()
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', build('GX', 'HERC01.PACMAN'), re.M))
    rcs = re.findall(r'PACBLDGX\s+(\w+)\s+(?:IEBGENER|IKFCBL00|IFOX00|IEWL|PACMAIN|PACQRYT)\s+RC= (\d{4})', '\n'.join(lines))
    assert len(rcs) == nsteps and all(r == '0000' for _, r in rcs), (nsteps, len(rcs), [x for x in rcs if x[1] != '0000'])
    assert not [l for l in lines if re.search(r'IKF\d{4}I-[WCE]', l)], 'compiler warnings'
    batch_or, tso_or = oracle()
    assert blocks(lines, BANNER) == list(batch_or.values()) + list(tso_or.values()), 'oracle changed'
    streams, tsx, j = [], [], 0
    while j < len(lines):
        if lines[j].startswith('TSX '):
            tsx.append((len(streams), lines[j].strip()))
            j += 1
            continue
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
    exp = [f'QRY {name:<8} LEN={len(b):04d} C={c} H={h} GE={ge} AW={w:03d} AH={hh:03d}'
           for name, b in cases() for (c, h, ge), (w, hh) in [(expect(b), expect_size(b))]]
    assert qry == exp, (qry, exp)
    # TSX: one switch per run, then FIRST for the first full screen and the run's command for every later one
    switches = [t for _, t in tsx if t.startswith('TSX SWITCH')]
    assert len(switches) == len(RUNS), len(switches)
    pos, per_run, sw_i = 0, [], 0
    fulls = [(p, t) for p, t in tsx if t.startswith('TSX FULL')]
    for run, fs in zip(RUNS, ref):
        cv = params(run)[6]
        w, h = gx.CANVASES.get(cv, (80, 24))
        cmd = '7E' if cv in gx.CANVASES else 'F5'
        assert switches[sw_i] == f'TSX SWITCH {cmd} {w:03d}X{h:03d}', (run, switches[sw_i])
        sw_i += 1
        mine = [t for p, t in fulls if pos <= p < pos + len(fs)]
        nfull = sum(1 for f in fs if 0x1D in f)
        assert len(mine) == nfull and (not mine or mine[0] == 'TSX FULL FIRST') and \
            all(t == f'TSX FULL {cmd}' for t in mine[1:]), (run, mine, nfull)
        per_run.append(streams[pos:pos + len(fs)])
        pos += len(fs)
    assert max(map(len, per_run[44 + 14])) <= 1000

    # replay of the scaled geometry runs on their W x H buffer vs the model images
    def apply(img, ds, geo):
        if 0x1D in ds:
            img[:] = [None] * geo.cells
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
                img[q], q, k = ('SF',), q + 1, k + 2
            elif b == 0x13:
                k += 1
            elif b == 0x3C:
                stop = g2.CODES.index(ds[k + 1]) * 64 + g2.CODES.index(ds[k + 2])
                ge = ds[k + 3] == 0x08
                ch = ds[k + 4] if ge else ds[k + 3]
                k += 5 if ge else 4
                while True:
                    img[q] = (ch, co, hh, 1 if ge else 0)
                    q = (q + 1) % geo.cells
                    if q == stop:
                        break
            elif b == 0x08:
                img[q], q, k = (ds[k + 1], co, hh, 1), q + 1, k + 2
            else:
                img[q], q, k = (b, co, hh, 0), q + 1, k + 1

    replayed = 0
    for i, run in enumerate(GX_RUNS):
        c, h, a, r, gl, sc, cv = params(run)
        geo = gx.Geo(cv, sc in '43T' and h and gl == 'G', 3 if sc == '3' else 4)
        if geo.fam == 'G' or sc == 'T':
            continue
        imgs = []
        of, op = gx.full, gx.partial
        gx.full = lambda g_, img, _o=of: (imgs.append(img), _o(g_, img))[1]
        gx.partial = lambda g_, cur, prev, kind, _o=op: (lambda rr: (imgs.append(cur) if rr is not None else None, rr)[1])(_o(g_, cur, prev, kind))
        try:
            again = gx.frames(c, h, a, r, gl, sc, cv)
        finally:
            gx.full, gx.partial = of, op
        imgs = imgs[len(imgs) - len(again):]                     # drop the family probe images (first-screen fit)
        assert again == ref[44 + i] and len(imgs) == len(per_run[44 + i])
        term = [None] * geo.cells
        sp1, spf = geo.sf_field()
        for ds, model in zip(per_run[44 + i], imgs):
            apply(term, ds, geo)
            for q in range(geo.n):
                t, m = term[q], model[q]
                if q in (sp1, spf, spf + 1, spf + 2) or (t is not None and t[0] == 'SF'):
                    continue
                t = t or (0x40, 0, 0, 0)
                blank_t = t[0] == 0x40 and t[2] == 0 and t[3] == 0
                blank_m = m[0] == 0x40 and m[2] == 0 and m[3] == 0
                assert (blank_t and blank_m) or t == m, (run, q // geo.w + 1, q % geo.w + 1, t, m)
            replayed += 1
    print('MVS-GS GEOMETRY PASS:', len(rcs), 'steps RC 0000; oracle unchanged;', len(streams),
          'TSC streams identical to the models (44 GS runs + 17 geometry runs);', len(switches), 'size switches and',
          len(fulls), 'full-screen transports as designed;', replayed, 'geometry streams replayed on W x H = model;',
          len(qry), 'PACQRY cases')
