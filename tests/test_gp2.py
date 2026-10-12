#!/usr/bin/env python3
"""MVS-GP2 acceptance (docs/GP2-PROGRESSION.md, D37): GP2.2 levels, progression, fruit and extra life under
RULES(ARCADE) - core, text output and the independent model.
Local:    the authorised core change only (docs/CORE_CHANGES.md, GP2.2); against mvs-gp1 the screen / input /
          platform side is untouched, PACARC and PACREQ grew append-only, the CLASSIC and GP1 lines of PACGAME /
          PACRT / PACMAIN / PACDISP are kept except the listed ones; every level-dependent value is in the one PACGAME
          table and equals the design; structural guards (PAC-ARC on every call, own 01, PACSCR a pure composer, the
          core architecture rules, CLIST columns); the model reaches every documented edge case and shows the designed
          rules (GP1 invariants rerun on the extended model).
Hercules: test_gp2.py GP2-LISTING (deck GP2 = the whole S1 deck, a marker step, then the ARCADE runs)
  - every step RC 0000, no compiler warnings;
  - everything before the marker passes tests/test_s1.py (CLASSIC: S1/RT/GX/... regression and the 1.0-MVS oracle);
  - every ARCADE run (BAT TURN, BAT REALTIME, TSO line mode; start level in PARM columns 22-23) = the model;
  - PARM column 21 not A with columns 22-23 present = CLASSIC (1.0-MVS oracle / RT model).
PACMAN_LATER_PHASE (set by a later phase that runs this file as a regression) skips ONLY the source-equality / diff-set
pins against mvs-gp1; every structural guard, model, listing and oracle check always runs.
"""
import difflib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tools'))
LATER = os.environ.get('PACMAN_LATER_PHASE')
os.environ['PACMAN_LATER_PHASE'] = LATER or 'GP2'
import ref_gp2 as L  # noqa: E402
import ref_arcade as A  # noqa: E402
import ref_rt  # noqa: E402
import search_gp2 as S  # noqa: E402
from make_deck import GP2_BAT, GP2_CLASSIC, GP2_MARK, GP2_RT, GP2_TSO, build  # noqa: E402
from test_g0 import BANNER, oracle  # noqa: E402

BASE = 'mvs-gp1'


def git_show(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:./{path}'], cwd=R, capture_output=True, text=True,
                          check=True).stdout.splitlines()


def src(path):
    return (R / path).read_text().splitlines()


def code(lines):
    return [l for l in lines if l[6:7] != '*']


def cards(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


def removed(path):
    return [d[2:] for d in difflib.ndiff(git_show(BASE, path), src(path)) if d[:2] == '- ']


# 1. sources -------------------------------------------------------------------------------------------------------
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
assert 'MVS-GP2 GP2.2 (D37' in (R / 'docs/CORE_CHANGES.md').read_text()
assert 'D37 (MVS-GP2)' in (R / 'docs/DECISIONS.md').read_text()
if not LATER:
    for f in ('src/copy/PACSTATE.cpy', 'src/copy/PACMREQ.cpy', 'maps/LEVEL1.txt', 'maps/ARCADE1.txt',
              'src/cobol/PACMAP.cob', 'src/cobol/PACAI.cob', 'src/cobol/PACSCR.cob', 'src/copy/PACPAL.cpy',
              'src/copy/PACDS.cpy', 'src/cobol/PACINPT.cob', 'src/cobol/PACPLAT.cob', 'src/cobol/PACQRY.cob',
              'src/asm/PACFSIO.asm', 'src/asm/PACTSO.asm'):
        assert git_show(BASE, f) == src(f), f
    REMOVED = {   # the only mvs-gp1 lines that changed (GP1 constants moved into the level table, wider counters)
        'src/cobol/PACGAME.cob': [
            '      * RULES : SEE DOCS/DECISIONS.MD D7, D9, D11, D14, D36.',
            '      * MVS-GP1 CONSTANTS (THE ONLY PLACE; GP2 MAKES THEM PER LEVEL).',
            '      * ROW 1 TURN (TURNS), ROW 2 REALTIME (QUANTA): FRIGHT LENGTH,',
            '      * WARNING WINDOW, EYES WAIT, REALTIME FRIGHT ACCUMULATOR STEP.',
            '       01  K-ARC-DATA            PIC X(22) VALUE', "           'T0200050102R0400100202'.",
            '               10  K-FR          PIC 999.', '               10  K-WARN        PIC 999.',
            '               PERFORM ARC-DEATH THRU ARC-DEATH-EXIT.', '           MOVE K-WARN (WS-KR) TO ARC-KWARN.',
            '           MOVE K-FR (WS-KR) TO ARC-FR.', '           MOVE K-WARN (WS-KR) TO ARC-KWARN.',
            '           ADD 1 TO ARC-EATEN.'],
        'src/cobol/PACRT.cob': [
            '       01  RT-ACC                PIC 9 VALUE 0.', '           ADD GH-NUM TO RT-ACC.',
            '           IF RT-ACC NOT < GH-DEN', '               SUBTRACT GH-DEN FROM RT-ACC',
            '           IF LIVES < WS-LIVES AND ARC-ON = 1',
            '           IF LIVES < WS-LIVES AND F-LOST = 0'],
        'src/cobol/PACMAIN.cob': [],
        'src/cobol/PACDISP.cob': ["           DISPLAY 'TURNS ' TICK-COUNT.", "               DISPLAY 'GHOSTS EATEN ' ARC-EATEN",
                                  '               ADD 1 TO M-LINES', '               ADD 16 TO M-CHARS.',
                                  '           ADD 1 TO M-LINES.', '           ADD 12 TO M-CHARS.'],
    }
    for f, want in REMOVED.items():
        assert sorted(removed(f)) == sorted(want), (f, removed(f))
    # CLASSIC: the TURNS line moved under ELSE, the old CLASSIC death test kept for ARC-ON = 0 (same arithmetic)
    assert "               DISPLAY 'TURNS ' TICK-COUNT." in src('src/cobol/PACDISP.cob')
    assert '           IF ARC-ON = 0 AND LIVES < WS-LIVES' in src('src/cobol/PACRT.cob')
# append-only copybooks (structural, always)
old, new = code(git_show(BASE, 'src/copy/PACARC.cpy')), code(src('src/copy/PACARC.cpy'))
assert new[:len(old)] == old, 'PACARC must grow append-only'
assert [l.split()[1].rstrip('.') for l in new[len(old):]] == [
    'ARC-LEVEL', 'ARC-AIB', 'ARC-KNUM', 'ARC-BV', 'ARC-BK', 'ARC-BX', 'ARC-BY', 'ARC-ITEMS', 'ARC-BN', 'ARC-BT',
    'ARC-XL', 'ARC-TURNS', 'ARC-EATN4', 'ARC-FRUITS', 'ARC-NDIE', 'ARC-EVF', 'ARC-EA', 'ARC-EF', 'ARC-EX', 'ARC-EC',
    'ARC-ED']
assert new[0] == '       01  PAC-ARC.' and not any('VALUE' in l for l in new)                  # D16, linkage-safe
old_req, new_req = git_show('mvs-s1', 'src/copy/PACREQ.cpy'), src('src/copy/PACREQ.cpy')
assert new_req[:len(old_req)] == old_req, 'PACREQ must grow append-only'
assert [l.split()[1] for l in code(new_req[len(old_req):])][:2] == ['REQ-RULES', 'REQ-START']
# every call of an ARCADE module passes the ARCADE state; PACSCR stays a pure composer
for name in ('PACMAIN', 'PACRT', 'PACDISP', 'PACGAME'):
    text = (R / f'src/cobol/{name}.cob').read_text()
    for callee, u, v in re.findall(r"CALL '(PACGAME|PACRT|PACDISP|PACSCR)' USING ([^\n]*)\n([^\n]*)", text):
        assert 'PAC-ARC' in u or v.strip() in ('PAC-ARC', 'PAC-ARC.'), (name, callee, u, v)
    assert all('PAC-ARC' in u for u in re.findall(r"CALL 'PACAI' USING ([^\n]*)", text))
scr = '\n'.join(code(src('src/cobol/PACSCR.cob')))
assert not re.search(r'\b(DISPLAY|ACCEPT|READ|OPEN|WRITE)\b', scr), 'PACSCR stays a pure composer'
# every level-dependent value lives in the one PACGAME table and equals the design (model)
game = (R / 'src/cobol/PACGAME.cob').read_text()
rows = re.findall(r"05  FILLER  PIC X\(20\) VALUE '(\d)(\d\d)(\d{3})(\d{3})(\d{3})(\d{3})([A-Z])(\d{4})'\.", game)
assert {i: tuple(int(x) if x.isdigit() else x for x in r) for i, r in enumerate(rows, 1)} == L.ROWS
assert re.search(r"K-ARC-DATA\s+PIC X\(16\) VALUE\s+'T(\d{3})(\d)(\d{3})R(\d{3})(\d)(\d{3})'", game).groups() == (
    '%03d' % L.EYES['T'], str(L.FINC), '%03d' % L.FRUIT_TIME['T'], '%03d' % L.EYES['R'], str(L.FINC),
    '%03d' % L.FRUIT_TIME['R'])
for name, v in (('K-BX', L.FRUIT_CELL[0]), ('K-BY', L.FRUIT_CELL[1]), ('K-B1', L.FRUIT_AT[0]), ('K-B2', L.FRUIT_AT[1]),
                ('K-XLIFE', L.XLIFE), ('K-LAST', L.LAST), ('K-NROW', 13)):
    assert re.search(r'01  ' + name + r'\s+PIC 9[^ ]* VALUE ' + str(v) + r'\.', game), name
assert re.search(r"CHAIN-DATA\s+PIC X\(16\) VALUE '0200040008001600'", game)
for name in ('PACMAIN', 'PACRT', 'PACDISP', 'PACAI', 'PACMAP', 'PACSCR'):
    t = (R / f'src/cobol/{name}.cob').read_text()
    assert not re.search(r'K-LVL|KL-|K-ARC|K-XLIFE|K-B[XY12T]\b', t), name
rt = '\n'.join(code(src('src/cobol/PACRT.cob')))
assert 'MOVE ARC-KNUM TO RT-NUM' in rt and "ARC-ED = 'D'" in rt and "ARC-EC = 'C'" in rt
assert re.search(r'01  GH-DEN10\s+PIC 99 VALUE 10\.', rt) and re.search(r'01  FRZ-INIT\s+PIC 99 VALUE 10\.', rt)
assert L.FREEZE == 10
# PARM columns 22-23 and the CLIST (normal play starts at LEVEL(1))
main = '\n'.join(code(src('src/cobol/PACMAIN.cob')))
assert 'MOVE 1 TO REQ-START.' in main and 'IF PARM-LEN = 22' in main and 'IF PARM-LEN = 23' in main
clist = (R / 'src/clist/PACMAN.clist').read_text()
assert 'RULES(CLASSIC) LEVEL(1)' in clist and '&V&Y&U&W&LEVEL)' in clist
for n, line in enumerate(clist.replace('@@PREFIX@@', 'HERC01.PACMAN').splitlines(), 1):
    assert len(line) <= 72, ('PACMAN.clist', n)
# GP1 as a regression: its structural guards and the (frozen) GP1 model checks; only its source pins are skipped
subprocess.run([sys.executable, str(R / 'tests/test_gp1.py')], check=True, stdout=subprocess.DEVNULL,
               env=dict(os.environ, PACMAN_LATER_PHASE=os.environ['PACMAN_LATER_PHASE']))
for t in ('test_mvs7', 'test_mvs8'):          # architecture rules (core has no terminal / host verbs) and the map
    subprocess.run([sys.executable, str(R / f'tests/{t}.py')], check=True, stdout=subprocess.DEVNULL)
subprocess.run([sys.executable, str(R / 'tools/validate_source.py')] + [str(p) for p in (R / 'src/cobol').glob('*.cob')]
               + [str(p) for p in (R / 'src/copy').glob('*.cpy')], check=True, stdout=subprocess.DEVNULL)


# 2. the model -----------------------------------------------------------------------------------------------------
def start_of(st):
    return L.parse_start(st)


def turn_log(cs, start):
    """[(log, game snapshot fields)] per TURN step, as the search saw it."""
    ai, n, rest = L.parse_config(cs)
    g, res = L.Level(ai, n, 'T', start), []
    g.start = start
    for c in rest:
        u = c[:1].upper()
        if u == 'Q':
            break
        if u not in ('U', 'D', 'L', 'R') or not u:
            continue
        lives = g.lives
        g.log = []
        g.turn('T', u)
        res.append((list(g.log), dict(lives0=lives, lives=g.lives, evf=g.evf, level=g.level, ascore=g.ascore,
                                       lost=g.lost, won=g.won, bt=g.bt, xl=g.xl)))
        if g.won or g.lost:
            break
    return res, g


starts = {c: st for d, c, st in GP2_BAT if d == 'gp2cases'}
for name, (pred, _) in S.PRED.items():
    st = start_of(starts[name])
    ai, n, rest = L.parse_config(cards('gp2cases', name))
    g = L.Level(ai, n, 'T', st)
    g.start = st
    hit = False
    for u in rest:
        if u == 'Q':
            break
        g.log = []
        g.turn('T', u)
        hit = hit or pred(g.log, g)
        if g.won or g.lost:
            break
    assert hit, name
# extra life: exactly once, at the step that reaches 10000, lives + 1 (with a death in the same step: unchanged)
for name in ('G2XP', 'G2XG', 'G2XF', 'G2XD', 'G2X20K'):
    steps, g = turn_log(cards('gp2cases', name), 13)
    xs = [i for i, (_, s) in enumerate(steps) if 'X' in s['evf']]
    assert len(xs) <= 1 and (xs or name == 'G2X20K'), name
    for i, (lg, s) in enumerate(steps):
        before = steps[i - 1][1]['ascore'] if i else 0
        assert ('X' in s['evf']) == (before < 10000 <= s['ascore']), (name, i)
        d = s['lives'] - s['lives0']
        assert d == ('X' in s['evf']) - ('D' in s['evf']), (name, i, d, s['evf'])
    if name == 'G2XD':
        assert any('X' in s['evf'] and 'D' in s['evf'] and s['lives'] == s['lives0'] for _, s in steps)
    if name == 'G2X20K':
        assert g.ascore >= 20000 and g.xl == 1 and len(xs) == 1
# level clear by the full-clear route (AI0): fruit at items 30 and 70, eaten / expired after exactly 30 turns,
# clear at T183 into level 2 (row 2: fright 17); the same route from level 99 = WON
steps, g = turn_log(cards('gp2cases', 'G2CLR'), 1)
ev = {i + 1: e[0] for i, (lg, _) in enumerate(steps) for e in lg if e[0] in ('fruit', 'fruiteat', 'fruitexp', 'clear')}
assert ev == {32: 'fruit', 52: 'fruiteat', 78: 'fruit', 108: 'fruitexp', 183: 'clear', }, ev
assert steps[182][1]['level'] == 2 and steps[182][1]['evf'] == '---C-' and g.level == 2 and g.fr == L.ROWS[2][2] - 5
out99 = L.simulate(cards('gp2cases', 'G2CLR'), start=99)
assert out99[-7:] == ['WIN', 'TURNS 0000183', 'SCORE %07d' % (96 * 10 + 4 * 50 + L.ROWS[13][7]), 'LIVES 3',
                      'GHOSTS EATEN 0000', 'FRUITS EATEN 001', 'LEVEL 099'], out99[-7:]
assert any(l.startswith('L LV=099') and l.endswith('EV=---C-') for l in out99)
# every row: G2ROW (AI1 1, power pellet on turn 2) shows the row's AI, fruit and fright length
for k in range(1, 14):
    out = L.simulate(cards('gp2cases', 'G2ROW'), start=k)
    r = L.ROWS[k]
    lv = [l for l in out if l.startswith('L ')]
    assert lv[0] == f'L LV={k:03d} AI={min(3, 1 + r[0])} IT=000 BN=0 BT=000 BK={r[6]} BV={r[7]:04d} XL=0 EV=-----'
    a2 = [l for l in out if l.startswith('A ')][2]
    assert f' FR={r[2]:03d} ' in a2 and 'EV=POWR' in a2, (k, a2)
assert L.Level(0, 3, 'T', 9).ai == 0 and L.Level(3, 3, 'T', 5).ai == 3 and L.Level(2, 1, 'T', 5).ai == 3
assert [L.parse_start(s) for s in ('', '  ', '00', 'ab', '5', '123', '99', '7 ', '05')] == [1, 1, 1, 1, 5, 1, 99, 1, 5]
assert [L.Level(1, n, 'T').left for n in (1, 2, 3)] == [100, 99, 98] and max(L.FRUIT_AT) < 98


# GP1 invariants rerun on the extended model (the frame checks of tests/test_gp1.py, with the level row)
def frames(out):
    res = []
    for i, l in enumerate(out):
        if re.match(r'T\d{3} ', l):
            pos = [tuple(map(int, re.search(r' G=(\d+),(\d+)', l).groups()))]
            if out[i + 3].startswith('G2='):
                pos += [tuple(map(int, m)) for m in re.findall(r'G\d=(\d+),(\d+)', out[i + 3])]
            a, lv = out[i + 1], out[i + 2]
            modes = re.findall(r'([NFE])(\d{3})', a[a.index(' M=') + 3:])
            res.append((l, a, lv, pos, modes))
    return res


def field(a, key, w):
    k = a.index(f' {key}=') + len(key) + 2 if f' {key}=' in a else a.index(f'{key}=') + len(key) + 1
    return a[k:k + w]


def num(a, key, w):
    return int(field(a, key, w))


turn_out = {(c, st): L.simulate(cards(d, c), start=start_of(st)) for d, c, st in GP2_BAT}
for (c, st), out in turn_out.items():
    fr = frames(out)
    assert len(fr) > 1, c
    for (l0, a0, v0, p0, m0), (l1, a1, v1, p1, m1) in zip(fr, fr[1:]):
        lev = num(v1, 'LV', 3)
        fmax = L.ROWS[min(lev, 13)][2]
        f0, f1, ft1 = num(a0, 'FR', 3), num(a1, 'FR', 3), num(a1, 'FT', 3)
        evg, evf = field(a1, 'EV', 4), field(v1, 'EV', 5)
        died, clear = 'D' in evf, 'C' in evf
        assert f1 <= fmax and (f1 == max(f0 - 1, 0) or evg == 'POWR' or died or clear), (c, l1, a1)
        for i, ((m_0, w0), (m_1, w1)) in enumerate(zip(m0, m1)):
            if died or clear:
                assert m_1 == 'N' and p1[i] == A.GSTARTS[i] or not clear, (c, l1)
                continue
            if m_0 == 'F' and m_1 == 'F' and p0[i] != p1[i]:
                assert ft1 > 0 and ft1 % 2 == 0 and evg != 'POWR', (c, l1, a1, i)
            if m_0 == 'E' and m_1 == 'E':
                assert p0[i] == p1[i] and (int(w1) == int(w0) - 1 or int(w0) == int(w1) == 1), (c, l1, i)
            if m_0 == 'F' and m_1 == 'E':
                assert p1[i] == A.GSTARTS[i] and int(w1) == L.EYES['T'] and evg == 'GHST', (c, l1, i)
            if m_0 == 'E' and m_1 == 'N':
                hx, hy = A.GSTARTS[i]
                assert abs(p1[i][0] - hx) + abs(p1[i][1] - hy) <= 1 and int(w0) == 1, (c, l1, i)
        s0, s1 = num(a0, 'S', 7), num(a1, 'S', 7)
        bt0, bt1 = num(v0, 'BT', 3), num(v1, 'BT', 3)
        assert bt1 <= L.FRUIT_TIME['T'] and (bt1 == max(bt0 - 1, 0) or 'A' in evf or 'F' in evf or died or clear)
        if not died and not clear:
            gain = (num(l0, 'L', 3) - num(l1, 'L', 3)) * 10 + (num(a0, 'PW', 1) - num(a1, 'PW', 1)) * 40 \
                + (num(v1, 'BV', 4) if 'F' in evf else 0)
            assert s1 - s0 == gain + (num(a1, 'P', 4) if evg == 'GHST' else 0) or evg == 'GHST', (c, l1, a1, v1)
        assert num(l1, 'V', 1) <= 4
# REALTIME: frightened accumulator unchanged (+2 due at >= 5); a death or a clear freezes 10 quanta; the normal
# ghosts follow the level's step of 10; pause stops every timer (G2RPAU = G2RB2 apart from the input column)
rt_out = {(c, st): L.rt_simulate(cards(d, c), start_of(st)) for d, c, st in GP2_RT}
for (c, st), out in rt_out.items():
    qs = [i for i, l in enumerate(out) if re.match(r'Q\d{7} ', l)]
    for i0, i1 in zip(qs, qs[1:]):
        a0, a1, v1 = out[i0 + 2], out[i1 + 2], out[i1 + 3]
        if ' K=F ' in out[i1] or num(a1, 'FR', 3) in (0, L.ROWS[min(num(v1, 'LV', 3), 13)][4]):
            continue
        assert num(a1, 'FA', 1) == (num(a0, 'FA', 1) + 2) % 5, (c, out[i1], a1)
    for k, i in enumerate(qs):
        evf = field(out[i + 3], 'EV', 5)
        if ('D' in evf or 'C' in evf) and ' K=F ' not in out[i] and ' ST=LOST' not in out[i] \
                and ' ST=WON' not in out[i] and k + 10 < len(qs):
            assert all(' K=F ' in out[qs[k + j]] for j in range(1, 11)) and ' K=F ' not in out[qs[k + 11]], (c, out[i])
strip = [re.sub(r' IN=.{8}', ' ', l) for l in rt_out[('G2RPAU', '')]]
assert strip == [re.sub(r' IN=.{8}', ' ', l) for l in rt_out[('G2RB2', '')]] and any(' IN=P.P' in l or ' IN=PLP ' in l for l in rt_out[('G2RPAU', '')])
assert any('EV=A' in l for l in rt_out[('G2RB2', '')]) and sum(l.endswith(('EV=A----', 'EV=A---D')) for l in rt_out[('G2RB2', '')]) >= 2
assert any(re.search(r'EV=..X.D', l) for l in rt_out[('G2RXD', '13')])
g = L.Level(1, 1, 'R', 5)
c = L.LevelRT(g)
c.rin('MOV', 'R', 'R')
due = []
for _ in range(20):
    c.rq()
    due.append(g.moven)
assert due == [0, 1, 1, 1, 1, 1, 1, 1, 1, 1] * 2, due                        # 9/10: acc 9, 18-10, 17-10, ...
tso_out = {}
for c, st in GP2_TSO:
    cs = cards('gpcases', c)
    ai, n, _ = L.parse_config(cs[:1])
    tso_out[(c, st)] = L.simulate(cs[1:], prompts=True, cfg=(ai, n), redraw=True, start=start_of(st))
print('local checks PASS:', len(S.PRED), 'searched + constructed edge cases;', len(GP2_BAT), 'TURN,', len(GP2_RT),
      'REALTIME,', len(GP2_TSO), 'TSO ARCADE model runs')

# 3. the Hercules listing ------------------------------------------------------------------------------------------
if len(sys.argv) == 2:
    lines = Path(sys.argv[1]).read_text().splitlines()
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', build('GP2', 'HERC01.PACMAN'), re.M))
    rcs = re.findall(r'PACBLGP2\s+(\w+)\s+(?:IEBGENER|IKFCBL00|IFOX00|IEWL|PACMAIN|PACQRYT|PACTSOT)\s+RC= (\d{4})',
                     '\n'.join(lines))
    assert len(rcs) == nsteps and all(r == '0000' for _, r in rcs), (nsteps, len(rcs), [x for x in rcs if x[1] != '0000'])
    assert not [l for l in lines if re.search(r'IKF\d{4}I-[WCE]', l)], 'compiler warnings'
    cut = lines.index(GP2_MARK)
    gp2_only = re.compile(r'(CPY6|GP2MARK|G2[BRTC]\d+)$')
    head = []
    for l in lines[:cut]:
        m = re.search(r'PACBLGP2\s+(\w+)\s+\S+\s+RC=', l)
        if m and gp2_only.match(m.group(1)):
            continue
        head.append(l.replace('PACBLGP2', 'PACBLDS1'))
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as tf:
        tf.write('\n'.join(head) + '\n')
    s1 = subprocess.run([sys.executable, str(R / 'tests/test_s1.py'), tf.name], capture_output=True, text=True)
    assert s1.returncode == 0, s1.stdout[-2000:] + s1.stderr[-3000:]
    tail = [l.rstrip() for l in lines[cut + 1:]]
    starts_at = [i for i, l in enumerate(tail) if l == BANNER]
    want = [turn_out[(c, st)] for _, c, st in GP2_BAT] + [rt_out[(c, st)] for _, c, st in GP2_RT] + \
        [tso_out[k] for k in GP2_TSO]
    want = [[l.rstrip() for l in w] for w in want]
    assert len(starts_at) == len(want) + len(GP2_CLASSIC), (len(starts_at), len(want) + len(GP2_CLASSIC))
    names = [f'{c}/{st!r}' for _, c, st in GP2_BAT] + [f'RT {c}/{st!r}' for _, c, st in GP2_RT] + \
        [f'TSO {c}/{st!r}' for c, st in GP2_TSO]
    for name, s, w in zip(names, starts_at, want):
        got = tail[s:s + len(w)]
        assert got == w, (name, next(((x, a, b) for x, (a, b) in enumerate(zip(got, w)) if a != b), (len(got), len(w))))
    batch_or, _ = oracle()
    for (kind, c, col, st), s in zip(GP2_CLASSIC, starts_at[len(want):]):
        w = batch_or[c] if kind == 'BAT' else [l.rstrip() for l in ref_rt.simulate(cards('rtcases', c))]
        assert tail[s:s + len(w)] == w, ('CLASSIC columns 21-23', repr(col + st), c)
        assert 'RULES ARCADE' not in tail[s:s + len(w)]
    print('MVS-GP2 GP2.2 PASS:', len(rcs), 'steps RC 0000; S1 regression:', s1.stdout.strip().splitlines()[-1][:60],
          '...;', len(want), 'ARCADE runs = model (', sum(len(w) for w in want), 'lines );', len(GP2_CLASSIC),
          'columns 21-23 CLASSIC runs = oracle/model')
