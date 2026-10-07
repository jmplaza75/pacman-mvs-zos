#!/usr/bin/env python3
"""MVS-G0 acceptance (stable visual baseline).
Local:   core frozen (tests/core_baseline.json) + every earlier local check.
Hercules: test_g0.py G0-LISTING G0X-LISTING
  G0  (build from source + 19 batch runs + 6 TSO-mode replays): all checks of tests/test_mvs8.py, and every output block
      byte-identical to the 1.0-MVS release evidence (docs/evidence/mvs9-release-build.txt) = the regression oracle.
  G0X (installed load module): optional METRICS lines are correct and leave the normal output untouched; an alternative
      PACDISP linked over LOAD(PACMAIN) (core not recompiled) plays the same games (status lines identical), and the
      linker maps show the core CSECTs (PACGAME, PACMAP, PACAI) with identical lengths.
"""
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
BANNER = 'PACMAN MVS-6 SMART GHOSTS'
ALT_BANNER = 'PACMAN ALT DISPLAY'
PROMPT = 'CMD (U/D/L/R/Q)?'
BATCH = ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1',
         'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')
TSO = ('MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR')
CORE = ('PACGAME', 'PACMAP', 'PACAI')


def spans(lines, banner):
    out = []
    for i, l in enumerate(lines):
        if l == banner:
            out.append((i, next(j for j in range(i, len(lines)) if lines[j].startswith('LIVES ')) + 1))
    return out


def blocks(lines, banner):
    return [lines[i:j] for i, j in spans(lines, banner)]


def oracle():
    b = blocks((R / 'docs/evidence/mvs9-release-build.txt').read_text().splitlines(), BANNER)
    assert len(b) == len(BATCH) + len(TSO)
    return dict(zip(BATCH, b[:len(BATCH)])), dict(zip(TSO, b[len(BATCH):]))


def width(line):
    if re.match(r'T\d{3} ', line):
        return 61
    if line.startswith('G2='):
        return 17 if ' G3=' in line else 8
    if len(line) == 20 and line[0] == '#':
        return 20
    fixed = {BANNER: 25, PROMPT: 16, 'LOST': 4, 'QUIT': 4, 'WIN': 3, 'EOF': 3}
    if line in fixed:
        return fixed[line]
    if line.startswith('INVALID COMMAND'):
        return 17
    return {'TURNS': 9, 'SCORE': 10, 'LIVES': 7}[line[:5]]


def metrics_expected(block, tso):
    status = [l for l in block if re.match(r'T\d{3} ', l)]
    clears = sum(' START ' not in l for l in status) if tso else 0
    return (f'METRICS FRAMES={len(status):04d} LINES={len(block):05d} '
            f'CHARS={sum(width(l) for l in block):07d} CLEARS={clears:04d}')


def csects(lines, after):
    """CSECT lengths from the first cross-reference table after line index `after`."""
    i = next(k for k in range(after, len(lines)) if 'CROSS REFERENCE TABLE' in lines[k])
    table = {}
    for l in lines[i:i + 30]:
        m = re.match(r'\s+(PAC\w+)\s+([0-9A-F]+)\s+([0-9A-F]+)', l)
        if m:
            table[m.group(1)] = m.group(3)
    return table


for t in ('test_core_frozen', 'test_map', 'test_mvs2', 'test_mvs3', 'test_mvs4', 'test_mvs5', 'test_mvs6',
          'test_mvs7', 'test_mvs8'):
    subprocess.run([sys.executable, str(R / f'tests/{t}.py')], check=True, stdout=subprocess.DEVNULL)
batch_or, tso_or = oracle()
print('local checks PASS (core frozen, oracle loaded)')

if len(sys.argv) == 3:
    g0 = Path(sys.argv[1]).read_text().splitlines()
    g0x = Path(sys.argv[2]).read_text().splitlines()
    # --- G0: the full 1.0-MVS checks plus byte identity with the release evidence
    print(subprocess.run([sys.executable, str(R / 'tests/test_mvs8.py'), sys.argv[1]], check=True,
                         capture_output=True, text=True).stdout.strip().splitlines()[-1])
    got = blocks(g0, BANNER)
    assert got == list(batch_or.values()) + list(tso_or.values()), 'G0 output differs from the 1.0-MVS oracle'
    # --- G0X: return codes
    rcs = re.findall(r'(MET\d|SRCX|COBX|LINKALT|ALT\d)\s+\S+\s+RC= (\d{4})', '\n'.join(g0x))
    assert len(rcs) == 10 and all(r == '0000' for _, r in rcs), rcs
    # --- metrics: normal output unchanged, METRICS line correct
    met = spans(g0x, BANNER)
    for (i, j), (case, mode) in zip(met, (('MOVES', 'BAT'), ('P2N3', 'BAT'), ('MULTI', 'TSO'), ('TSORDR', 'TSO'))):
        ref = (tso_or if mode == 'TSO' else batch_or)[case]
        assert g0x[i:j] == ref, f'{case}: metrics run changed the normal output'
        nxt = g0x[j]
        assert nxt == metrics_expected(ref, mode == 'TSO'), (case, nxt, metrics_expected(ref, mode == 'TSO'))
        print(f'{case:7} {mode}: {nxt}')
    assert len(met) == 4
    # --- alternative display: same game, only status lines; core CSECTs identical
    alt = blocks(g0x, ALT_BANNER)
    assert len(alt) == 3
    for blk, (case, mode) in zip(alt, (('MOVES', 'BAT'), ('MULTI', 'BAT'), ('TSORDR', 'TSO'))):
        ref = (tso_or if mode == 'TSO' else batch_or)[case]
        keep = [l for l in ref[1:] if not (len(l) == 20 and l[0] == '#') and not l.startswith('G2=')]
        assert blk == [ALT_BANNER] + keep, f'{case}: alternative display does not show the same game'
    main_map = csects(g0, next(i for i, l in enumerate(g0) if re.search(r'//LINK\s+EXEC PGM=IEWL', l)))
    alt_map = csects(g0x, next(i for i, l in enumerate(g0x) if 'LINKALT' in l and 'IEWL' in l))
    for c in CORE + ('PACINPT', 'PACPLAT', 'PACTSO'):
        assert main_map[c] == alt_map[c], (c, main_map[c], alt_map[c])
    print('core CSECT lengths in PACALT = PACMAIN:', {c: alt_map[c] for c in CORE})
    print('MVS-G0 PASS')
