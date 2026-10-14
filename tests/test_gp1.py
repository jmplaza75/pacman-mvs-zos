#!/usr/bin/env python3
"""MVS-GP1 acceptance (docs/GP1-POWER.md, D36): GP1.2 RULES(ARCADE) core and text output, GP1.3 ARCADE screens.
Local:    the authorised core change only (docs/CORE_CHANGES.md 2026-10-11); against mvs-s1 the CLASSIC code keeps every
          line except the listed signature / display lines; the screen side (PACSCR, PACPAL, PACDS, PACINPT, PACPLAT,
          PACQRY, PACFSIO, PACTSO) is untouched in GP1.2; constants in one place and equal to the design; the independent
          model (tests/ref_arcade.py) reaches every documented edge case and shows the designed timing.
Hercules: test_gp1.py GP1-LISTING (deck GP1 = the whole S1 deck, a marker step, then the ARCADE runs)
  - every step RC 0000, no compiler warnings;
  - everything before the marker passes tests/test_s1.py (CLASSIC: S1/RT/GX/... regression and the 1.0-MVS oracle);
  - every ARCADE run (BAT TURN, BAT REALTIME, TSO line mode) equals the model line for line;
  - PARM column 21 present but not A (C, blank, X) = CLASSIC: the 1.0-MVS oracle / the RT model.
GP1.3 (after the second marker): every ARCADE TSD stream (TURN and REALTIME, all glyph profiles, scaled families,
ticks, redraw, size guard, SOUND bells) equals the screen models (ref_g4/gs/gx_screen with ref_arcade) byte for byte,
with its end lines; locally the GP1.3 source changes against the GP1.2 checkpoint bc419f7 are pinned (PACPAL
append-only, PACSCR/PACDISP listed lines only, core / input / platform untouched).
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
# MVS-GP2: PACMAN_LATER_PHASE (set by a later phase's test, or by hand to run this file as a regression on later
# sources) skips ONLY the source-equality / diff-set pins against mvs-s1 and the GP1.2 checkpoint and the parse of
# the GP1 constants row (moved into the GP2 level table, authorised D37); every structural guard and every GP1 model
# check always runs. The listing part checks GP1 listings (PACBLGP1) only.
LATER = os.environ.get('PACMAN_LATER_PHASE')
os.environ['PACMAN_LATER_PHASE'] = LATER or 'GP1'
import ref_arcade as A  # noqa: E402
import ref_rt  # noqa: E402
import search_gp1 as S  # noqa: E402
from make_deck import GP1_BAT, GP1_CLASSIC, GP1_MARK, GP1_RT, GP1_TSO, GP13_MARK, GP13_RT, GP13_TURN, build  # noqa: E402
import ref_g4_screen as g4  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
from ref_snap import Log  # noqa: E402
from test_g0 import BANNER, blocks, oracle  # noqa: E402


def git_show(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:./{path}'], cwd=R, capture_output=True, text=True,
                          check=True).stdout.splitlines()


def cards(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


# 1. sources -------------------------------------------------------------------------------------------------------
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
assert 'MVS-GP1 GP1.2 (D36' in (R / 'docs/CORE_CHANGES.md').read_text()
for f in ('src/copy/PACSTATE.cpy', 'src/copy/PACMREQ.cpy', 'maps/LEVEL1.txt',
          'src/copy/PACDS.cpy', 'src/cobol/PACINPT.cob', 'src/cobol/PACPLAT.cob', 'src/cobol/PACQRY.cob',
          'src/asm/PACFSIO.asm', 'src/asm/PACTSO.asm'):
    assert LATER or git_show('mvs-s1', f) == (R / f).read_text().splitlines(), f
old_req, new_req = git_show('mvs-s1', 'src/copy/PACREQ.cpy'), (R / 'src/copy/PACREQ.cpy').read_text().splitlines()
assert new_req[:len(old_req)] == old_req, 'PACREQ must grow append-only'
added = [l.split()[1] for l in new_req[len(old_req):] if l[6:7] != '*']
assert added[:1] == ['REQ-RULES'] and (LATER or len(added) == 1), added
REMOVED = {   # the only mvs-s1 lines that changed (USING lists / CALL signatures, three ARCADE display points)
    'PACGAME': ["      * RULES : SEE DOCS/DECISIONS.MD D7, D9, D11, D14.", "       PROCEDURE DIVISION USING PAC-STATE PAC-REQ.",
                "               CALL 'PACAI' USING PAC-STATE"],
    'PACMAP': ["               MOVE 1 TO M-FLAG."],
    'PACAI': ["       PROCEDURE DIVISION USING PAC-STATE."],
    'PACRT': ["       PROCEDURE DIVISION USING PAC-STATE PAC-REQ.", "           CALL 'PACGAME' USING PAC-STATE PAC-REQ."],
    'PACDISP': ["       PROCEDURE DIVISION USING PAC-STATE PAC-REQ.", "           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS.",
                "           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS.",
                "           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS.", "           DISPLAY 'SCORE ' SCORE.",
                "               MOVE 'G' TO WS-LINE-CELL (WS-GX).",
                "           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS."],
}
# GP1.3 (screens) against the GP1.2 checkpoint: PACPAL append-only, PACSCR only the listed lines, PACDISP only the PACSCR
# calls (now with PAC-ARC); the core, PACMAIN, PACRT and the input / platform side unchanged since GP1.2
GP12 = 'bc419f7'
for f in ('src/cobol/PACGAME.cob', 'src/cobol/PACMAP.cob', 'src/cobol/PACAI.cob', 'src/copy/PACARC.cpy', 'maps/ARCADE1.txt',
          'src/cobol/PACMAIN.cob', 'src/cobol/PACRT.cob', 'src/copy/PACREQ.cpy', 'src/clist/PACMAN.clist'):
    assert LATER or git_show(GP12, f) == (R / f).read_text().splitlines(), f
old, new = git_show(GP12, 'src/copy/PACPAL.cpy'), (R / 'src/copy/PACPAL.cpy').read_text().splitlines()
assert new[:len(old)] == old, 'PACPAL must grow append-only'
added = [l.split()[1] for l in new[len(old):] if l[6:7] != '*']
assert added[:8] == ['PAL-POWER', 'HI-POWER', 'PAL-FRIGHT', 'PAL-WARN', 'PAL-EYES', 'GLY-EYES', 'SPR-4X', 'SPR-3X'] \
    and (LATER or len(added) == 8), added
pal = '\n'.join(new)
for name, v in (('PAL-POWER', g4.POWER), ('HI-POWER', 0xF1), ('PAL-FRIGHT', g4.FRIGHT), ('PAL-WARN', g4.WARN),
                ('PAL-EYES', g4.EYESC)):
    assert re.search(name + r'\s+PIC 999 VALUE ' + str(v) + r'\.', pal), name
assert "GLY-EYES              PIC X VALUE '\"'." in pal
assert "' BB  TT  ee     '" in pal and "' B  T  e    '" in pal        # power / eyes tiles of ref_gs_screen.arc_tile
old, new = git_show(GP12, 'src/cobol/PACSCR.cob'), (R / 'src/cobol/PACSCR.cob').read_text().splitlines()
assert LATER or [d[2:] for d in difflib.ndiff(old, new) if d[:2] == '- '] == [
    '           05  SPR-4-CH          PIC X OCCURS 40 TIMES.', '           05  SPR-3-CH          PIC X OCCURS 30 TIMES.',
    '       PROCEDURE DIVISION USING PAC-STATE PAC-REQ PAC-DS.', '           MOVE SPR-4 TO SPR-4-T.',
    '           MOVE SPR-3 TO SPR-3-T.', '           MOVE 0 TO WS-HP WS-HG WS-HE WS-HN WS-HW.',
    "           IF SPR-C = 'E'", "           IF SPR-C = 'T' OR SPR-C = 'B' OR SPR-C = 'E'"]
old, new = git_show(GP12, 'src/cobol/PACDISP.cob'), (R / 'src/cobol/PACDISP.cob').read_text().splitlines()
assert LATER or all(d[2:].strip() == "CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS." for d in difflib.ndiff(old, new)
                    if d[:2] == '- ')
scr = (R / 'src/cobol/PACSCR.cob').read_text()
calls = re.findall(r"CALL 'PACSCR' USING ([^\n]*)\n([^\n]*)", (R / 'src/cobol/PACDISP.cob').read_text())
assert len(calls) == 6 and all(v.strip() in ('PAC-ARC', 'PAC-ARC.') for _, v in calls), calls
assert not re.search(r'\b(DISPLAY|ACCEPT|READ|OPEN|WRITE)\b',
                     '\n'.join(l for l in scr.splitlines() if l[6:7] != '*')), 'PACSCR stays a pure composer'
for name in ('PACGAME', 'PACMAP', 'PACAI', 'PACRT', 'PACDISP', 'PACMAIN') if not LATER else ():
    old, new = git_show('mvs-s1', f'src/cobol/{name}.cob'), (R / f'src/cobol/{name}.cob').read_text().splitlines()
    removed = [d[2:] for d in difflib.ndiff(old, new) if d[:2] == '- ']
    if name == 'PACMAIN':    # every removed line is a PACGAME / PACRT / PACDISP call that now also passes PAC-ARC
        assert removed and all(re.fullmatch(r"\s+CALL '(PACGAME|PACRT|PACDISP)' USING PAC-STATE PAC-REQ\.", l)
                               for l in removed), removed
    else:
        assert sorted(removed) == sorted(REMOVED[name]), (name, removed)
for name in ('PACMAIN', 'PACRT', 'PACDISP', 'PACGAME'):   # nobody calls the ARCADE modules without the ARCADE state
    src = (R / f'src/cobol/{name}.cob').read_text()
    calls = re.findall(r"CALL '(PACGAME|PACRT|PACDISP)' USING ([^\n]*)\n([^\n]*)", src)
    assert (calls or name in ('PACDISP', 'PACGAME')) and all('PAC-ARC' in u or v.strip() in ('PAC-ARC', 'PAC-ARC.') for _, u, v in calls), (name, calls)
    assert all('PAC-ARC' in u for u in re.findall(r"CALL 'PACAI' USING ([^\n]*)", src))
arc = [l for l in (R / 'src/copy/PACARC.cpy').read_text().splitlines() if l[6:7] != '*']
assert arc[0] == '       01  PAC-ARC.' and not any('VALUE' in l for l in arc)               # D16, linkage-safe
game, mapsrc = (R / 'src/cobol/PACGAME.cob').read_text(), (R / 'src/cobol/PACMAP.cob').read_text()
if not LATER:
    k = re.search(r"K-ARC-DATA\s+PIC X\(22\) VALUE\s+'([^']*)'", game).group(1)
    assert {k[i]: (int(k[i + 1:i + 4]), int(k[i + 4:i + 7]), int(k[i + 7:i + 10]), int(k[i + 10])) for i in (0, 11)} == A.K
assert A.K == {'T': (20, 5, 10, 2), 'R': (40, 10, 20, 2)}                                     # design 3a (approved)
ch = re.search(r"CHAIN-DATA\s+PIC X\(16\) VALUE '(\d{16})'", game).group(1)
assert [int(ch[i:i + 4]) for i in range(0, 16, 4)] == A.CHAIN == [200, 400, 800, 1600]
pw = re.search(r"PWR-DATA\s+PIC X\(16\) VALUE '(\d{16})'", mapsrc).group(1)
assert [(int(pw[i:i + 2]), int(pw[i + 2:i + 4])) for i in range(0, 16, 4)] == A.POWER == [(2, 4), (19, 4), (2, 8), (19, 8)]
lvl = [list(r) for r in (R / 'maps/LEVEL1.txt').read_text().splitlines()]
for x, y in A.POWER:
    assert lvl[y - 1][x - 1] == '.'                    # existing corridor cells, topology unchanged
    lvl[y - 1][x - 1] = 'o'
assert [''.join(r) for r in lvl] == (R / 'maps/ARCADE1.txt').read_text().splitlines()
for name in ('PACMAIN', 'PACRT', 'PACDISP', 'PACAI', 'PACMAP'):   # constants only in PACGAME (GP2: per-level table)
    assert 'K-ARC' not in (R / f'src/cobol/{name}.cob').read_text(), name
rt = (R / 'src/cobol/PACRT.cob').read_text()
assert 'ADD ARC-KFINC TO ARC-FACC' in rt and 'MOVE 0 TO RT-ACC' in rt
clist = (R / 'src/clist/PACMAN.clist').read_text()
# MVS-G8 (D43): the CLIST default flips to RULES(ARCADE); tests/test_g8.py pins the final default set
assert ('RULES(CLASSIC)' in clist or 'RULES(ARCADE) LEVEL(1)' in clist) and ('&V&Y&U&W)' in clist or (LATER and '&V&Y&U&W' in clist)) and 'SET &W = &SUBSTR(1:1,&RULES)' in clist
for n, line in enumerate(clist.replace('@@PREFIX@@', 'HERC01.PACMAN').splitlines(), 1):
    assert len(line) <= 72, ('PACMAN.clist', n)
for t in ('test_mvs7', 'test_mvs8'):          # architecture rules (core has no terminal / host verbs) and the map
    subprocess.run([sys.executable, str(R / f'tests/{t}.py')], check=True, stdout=subprocess.DEVNULL)


# 2. the model: every edge case is reached, the designed timing holds ---------------------------------------------
def replay(cs):
    """(log of every turn, game) for a TURN case, as search_gp1 saw it."""
    ai, n, rest = A.parse_config(cs)
    g, logs = A.Arcade(ai, n, 'T'), []
    for c in rest:
        u = c[:1].upper()
        if u == 'Q':
            break
        if u not in 'UDLR' or not u:
            continue
        g.log = []
        g.turn('T', u)
        logs.append((list(g.log), g.won, g.left))
        if g.won or g.lost:
            break
    return logs, g


for name, pred in S.PRED.items():
    logs, g = replay(cards('gpcases', name))
    assert any(pred(lg, g) for lg, _, _ in logs), name
logs, _ = replay(cards('gpcases', 'GPLASTO'))
assert logs[-1][1] and any(e[0] == 'power' for e in logs[-1][0]), 'GPLASTO: the last item is a power pellet'
logs, _ = replay(cards('gpcases', 'GPLASTH'))
assert logs[-1][2] == 0 and any(e[0] == 'death' for e in logs[-1][0]), 'GPLASTH: last item and a hit in one turn'
# LEVEL1 has no dead ends (tests/test_mvs8.py), so the "reverse only when nothing else is open" flee rule cannot fire
# on it: documented as unreachable (as D13 did for AI2/AI3); the blocked pending reversal (GPREVB) is reachable.


def frames(out):
    """(T line, A line, ghost positions, modes) per TURN frame of a model / listing block."""
    res = []
    for i, l in enumerate(out):
        if re.match(r'T\d{3} ', l):
            pos = [tuple(map(int, re.search(r' G=(\d+),(\d+)', l).groups()))]
            if out[i + 2].startswith('G2='):
                pos += [tuple(map(int, m)) for m in re.findall(r'G\d=(\d+),(\d+)', out[i + 2])]
            a = out[i + 1]
            modes = re.findall(r'([NFE])(\d{3})', a[a.index(' M=') + 3:])
            res.append((l, a, pos, modes))
    return res


def field(a, key, w):
    return int(a[a.index(f' {key}=') + len(key) + 2:][:w]) if f' {key}=' in a else int(a[a.index(f'{key}=') + len(key) + 1:][:w])


turn_out = {c: A.simulate(cards(d, c)) for d, c in GP1_BAT}
for c, out in turn_out.items():
    fr = frames(out)
    assert len(fr) > 1, c
    for (l0, a0, p0, m0), (l1, a1, p1, m1) in zip(fr, fr[1:]):
        f0, f1, ft1 = field(a0, 'FR', 3), field(a1, 'FR', 3), field(a1, 'FT', 3)
        ev, died = a1[a1.index('EV=') + 3:][:4], ' DIED ' in l1 or ' LOST ' in l1
        assert f1 <= 20 and (f1 == max(f0 - 1, 0) or ev == 'POWR' or died or (f1 == 0 and f0 == 1)), (c, l1, a1)
        for i, ((m_0, w0), (m_1, w1)) in enumerate(zip(m0, m1)):
            if died:
                continue
            if m_0 == 'F' and m_1 == 'F' and p0[i] != p1[i]:          # TURN: frightened move only on even fright turns
                assert ft1 > 0 and ft1 % 2 == 0 and ev != 'POWR', (c, l1, a1, i)
            if m_0 == 'E' and m_1 == 'E':                              # eyes never move and count down (or wait at 1)
                assert p0[i] == p1[i] and (int(w1) == int(w0) - 1 or int(w0) == int(w1) == 1), (c, l1, i)
            if m_0 == 'F' and m_1 == 'E':                              # eaten: home at once, full wait
                assert p1[i] == A.GSTARTS[i] and int(w1) == 10 and ev == 'GHST', (c, l1, i)
            if m_0 == 'E' and m_1 == 'N':      # revival at home (tick first: it may take its normal step at once)
                hx, hy = A.GSTARTS[i]
                assert abs(p1[i][0] - hx) + abs(p1[i][1] - hy) <= 1 and int(w0) == 1, (c, l1, i)
        s0, s1 = field(a0, 'S', 7), field(a1, 'S', 7)
        if not died:
            assert s1 - s0 == (field(l0, 'L', 3) - field(l1, 'L', 3)) * 10 + (field(a0, 'PW', 1) - field(a1, 'PW', 1)) * 40 \
                + (field(a1, 'P', 4) if ev == 'GHST' else 0) or ev == 'GHST', (c, l1, a1)
# scripted cases (design 4.2-4.4)
fr = {l[:4]: (l, a, p, m) for l, a, p, m in frames(turn_out['GPAI0'])}
assert [field(fr[t][1], 'P', 4) for t in ('T007', 'T024', 'T031')] == [200, 400, 200]        # chain reset by a new o
assert all(field(fr[t][1], 'FR', 3) == 20 and 'EV=POWR' in fr[t][1] for t in ('T002', 'T006', 'T025', 'T029'))
assert fr['T025'][3][0][0] == 'E' and fr['T025'][3][1][0] == 'F'      # eyes ignore the pellet; revived N frightened
assert fr['T017'][3][1] == ('N', '000') and field(fr['T017'][1], 'FR', 3) > 0                 # revived N in a fright
assert field(fr['T048'][1], 'FR', 3) == 1 and field(fr['T049'][1], 'FR', 3) == 0 and 'F' not in str(fr['T049'][3])
assert all(p == [A.GSTARTS[0], A.GSTARTS[1], A.GSTARTS[2]] for _, _, p, _ in fr.values())       # AI0 never moves
assert turn_out['GPAI0'][-5:] == ['QUIT', 'TURNS 051', 'SCORE 0001310', 'LIVES 3', 'GHOSTS EATEN 003']
fr = {l[:4]: (l, a, p, m) for l, a, p, m in frames(turn_out['GPHOME'])}
assert fr['T007'][2][1] == (2, 9) == (field(fr['T007'][0], 'X', 2), field(fr['T007'][0], 'Y', 2))  # eyes on Pac-Man
assert fr['T017'][3][1] == ('E', '001') and fr['T018'][3][1] == ('E', '001')                   # revival deferred
assert ' DIED ' in fr['T019'][0] and field(fr['T019'][1], 'FR', 3) == 0 and fr['T019'][3] == [('N', '000')] * 2
# REALTIME: frightened accumulator +2 due at >= 5 (2/5), reset at fright start / end; pause freezes every timer
rt_out = {c: A.rt_simulate(cards(d, c)) for d, c in GP1_RT}
for c, out in rt_out.items():
    arcs = [l for l in out if l.startswith('A S=')][1:]
    qs = [l for l in out if re.match(r'Q\d{7} ', l)]
    for (q0, a0), (q1, a1) in zip(zip(qs, arcs), zip(qs[1:], arcs[1:])):
        if ' K=F ' in q1 or field(a1, 'FR', 3) in (0, 40):
            continue
        assert field(a1, 'FA', 1) == (field(a0, 'FA', 1) + 2) % 5, (c, q1, a1)
strip = [re.sub(r' IN=.{8}', ' ', l) for l in rt_out['RTGPP']]
assert strip == [re.sub(r' IN=.{8}', ' ', l) for l in rt_out['RTGPA']] and any(' IN=PP ' in l for l in rt_out['RTGPP'])
assert any('EV=GHST' in l for l in rt_out['RTGPA']) and any(' FR=040 ' in l and 'EV=GHST' in l for l in rt_out['RTGPD'])
tso_out = {}
for c in GP1_TSO:
    cs = cards('gpcases', c)
    ai, n, _ = A.parse_config(cs[:1])
    tso_out[c] = A.simulate(cs[1:], prompts=True, cfg=(ai, n), redraw=True)
t = [l for l in tso_out['GPTSO'] if re.match(r'T\d{3} ', l)]
assert len(t) == len(set(t)) + 1, 'GPTSO: one redraw repeats a frame'


# GP1.3 screen models -----------------------------------------------------------------------------------------------
def arc_turn(ai, n):
    return A.Arcade(ai, n, 'T')


def arc_rt(ai, n):
    return A.Arcade(ai, n, 'R')


def bells(frames, log, sound):
    """The S1 bell rule, unchanged (tests/test_s1.py): first screen, fewer lives than the previous screen, first screen
    after the win; a pending bell at the end of a game without an end screen goes on C6 28 00 00."""
    if sound != 'Y':
        return list(frames), []
    last, won, out, rung = None, False, [], []

    def ring(snap):
        nonlocal last, won
        lv, w = snap
        b = last is None or lv < last or (w and not won)
        won, last = won or w, lv
        return b
    for k, (f, snap) in enumerate(zip(frames, log)):
        b = ring(snap)
        out.append(bytes([f[0] | 0x04]) + f[1:] if b else f)
        if b:
            rung.append(k)
    if ring(log.state()):
        out.append(bytes([0xC6, 0x28, 0x00, 0x00]))
        rung.append(len(frames))
    return out, rung


scr_turn, scr_rt = [], []
for run in GP13_TURN:
    c, h, a, r, gl, sc, cv, snd = run
    log = Log()
    fs = gx.frames(c, h == 'Y', a == 'Y', r, gl, sc, cv, snap=log, mk=arc_turn, d='gpcases')
    scr_turn.append((run, bells(fs, log, snd), A.simulate([l for l in cards('gpcases', c)])[-5:]))
for run in GP13_RT:
    c, cv, snd = run
    log = Log()
    end, fs = ref_rt.tsd(cards('gpcases', c), cv, snap=log, mk_game=arc_rt, mk_ctl=A.ArcadeRT)
    scr_rt.append((run, bells(fs, log, snd), end[-6:]))
allf = [f for _, (fs, _), _ in scr_turn + scr_rt for f in fs]
assert max(len(f) for f in allf) <= 2048
blob = b''.join(allf)
assert bytes([0x28, 0x42, g4.FRIGHT]) in blob and bytes([0x28, 0x41, 0xF1]) in blob          # fright colour, blink
assert any(b'\x96' in f and b'\x28\x41\xf1' in f for _, (fs, _), _ in scr_turn[:1] for f in fs)  # o blinking (C)
assert any(e for _, (fs, _), _ in scr_turn[:5] for e in [b'\x7f' in f for f in fs]), 'eyes \" on the unscaled boards'
# frightened ghosts drawn white in the warning window (GPAI0 T021-T024): the model image proves it, PACSCR = model
cs = cards('gpcases', 'GPAI0')
ai, n, rest = A.parse_config(cs)
g = A.Arcade(ai, n, 'T')
for u in rest[:21]:
    g.step(u)
assert g.warning() and g4.fright_colour(g) == g4.WARN
img = g4.cells(g, rest[20], g.res, None, True, 'G', True, 0, 'R')
assert any(col == g4.WARN and b == g4.CP310['∩'] and h == 0 for b, col, h, ge in img)
assert [r[0][7] for r in scr_turn].count('Y') == 2 and all(len(rg) >= 1 for r, (_, rg), _ in scr_turn if r[7] == 'Y')
print('GP1.3 local checks PASS:', len(GP13_TURN), 'TURN and', len(GP13_RT), 'REALTIME ARCADE TSD runs,', len(allf),
      'model streams, largest', max(len(f) for f in allf), 'bytes')
print('local checks PASS:', len(S.PRED) + 2, 'edge cases reached;', len(GP1_BAT), 'TURN,', len(GP1_RT), 'REALTIME,',
      len(GP1_TSO), 'TSO ARCADE model runs')

# 3. the Hercules listing ------------------------------------------------------------------------------------------
if len(sys.argv) == 2:
    lines = Path(sys.argv[1]).read_text().splitlines()
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', build('GP1', 'HERC01.PACMAN'), re.M))
    rcs = re.findall(r'PACBLGP1\s+(\w+)\s+(?:IEBGENER|IKFCBL00|IFOX00|IEWL|PACMAIN|PACQRYT|PACTSOT)\s+RC= (\d{4})',
                     '\n'.join(lines))
    assert len(rcs) == nsteps and all(r == '0000' for _, r in rcs), (nsteps, len(rcs), [x for x in rcs if x[1] != '0000'])
    assert not [l for l in lines if re.search(r'IKF\d{4}I-[WCE]', l)], 'compiler warnings'
    cut = lines.index(GP1_MARK)
    gp1_only = re.compile(r'(CPY6|GP1MARK|GP13MARK|GP[BRTC]\d+|GQ[TR]\d+)$')
    head = []
    for l in lines[:cut]:
        m = re.search(r'PACBLGP1\s+(\w+)\s+\S+\s+RC=', l)
        if m and gp1_only.match(m.group(1)):
            continue
        head.append(l.replace('PACBLGP1', 'PACBLDS1'))
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as tf:
        tf.write('\n'.join(head) + '\n')
    s1 = subprocess.run([sys.executable, str(R / 'tests/test_s1.py'), tf.name], capture_output=True, text=True)
    assert s1.returncode == 0, s1.stdout[-2000:] + s1.stderr[-3000:]
    tail = [l.rstrip() for l in lines[cut + 1:]]
    starts = [i for i, l in enumerate(tail) if l == BANNER]
    want = [turn_out[c] for _, c in GP1_BAT] + [rt_out[c] for _, c in GP1_RT] + [tso_out[c] for c in GP1_TSO]
    want = [[l.rstrip() for l in w] for w in want]
    assert len(starts) == len(want) + len(GP1_CLASSIC), (len(starts), len(want) + len(GP1_CLASSIC))
    names = [c for _, c in GP1_BAT] + [c for _, c in GP1_RT] + ['TSO ' + c for c in GP1_TSO]
    for name, s, w in zip(names, starts, want):
        got = tail[s:s + len(w)]
        assert got == w, (name, next(((x, a, b) for x, (a, b) in enumerate(zip(got, w)) if a != b), (len(got), len(w))))
    batch_or, _ = oracle()
    cl = starts[len(want):]
    for (kind, c, col), s in zip(GP1_CLASSIC, cl):
        w = batch_or[c] if kind == 'BAT' else [l.rstrip() for l in ref_rt.simulate(cards('rtcases', c))]
        assert tail[s:s + len(w)] == w, ('CLASSIC column 21', repr(col), c)
        assert 'RULES ARCADE' not in tail[s:s + len(w)]
    # GP1.3: TSD streams after the second marker, run by run (end lines: 5 TURN / 6 REALTIME)
    cut2 = lines.index(GP13_MARK)
    t2, j, ns = lines[cut2 + 1:], 0, 0

    def tsd_run(nend):
        global j
        streams = []
        while t2[j].rstrip() not in ('WIN', 'LOST', 'QUIT', 'EOF'):
            m = re.match(r'TSD FRAME LEN(\d{4})$', t2[j])
            j += 1
            if not m:
                continue
            hexs = ''
            while t2[j].startswith('TSD ') and not t2[j].startswith('TSD FRAME'):
                hexs += t2[j][4:].strip()
                j += 1
            data = bytes.fromhex(hexs)
            assert len(data) == int(m.group(1))
            streams.append(data)
        ends = [l.rstrip() for l in t2[j:j + nend]]
        j += nend
        return streams, ends
    for run, (wstreams, _), wend in scr_turn + scr_rt:
        got, ends = tsd_run(len(wend))
        assert len(got) == len(wstreams), (run, len(got), len(wstreams))
        for x, (p, q) in enumerate(zip(got, wstreams)):
            assert p == q, (run, x, next((y for y in range(min(len(p), len(q))) if p[y] != q[y]), min(len(p), len(q))))
        assert ends == wend, (run, ends, wend)
        ns += len(got)
    print('MVS-GP1 GP1.3 PASS:', len(GP13_TURN) + len(GP13_RT), 'ARCADE TSD runs =', ns, 'model streams')
    print('MVS-GP1 GP1.2 PASS:', len(rcs), 'steps RC 0000; S1 regression:', s1.stdout.strip().splitlines()[-1][:60], '...;',
          len(want), 'ARCADE runs = model (', sum(len(w) for w in want), 'lines );', len(GP1_CLASSIC),
          'column-21 CLASSIC runs = oracle/model')
