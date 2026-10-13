#!/usr/bin/env python3
"""MVS-RP acceptance (D39, docs/RP-POLISH.md): presentation polish under RULES(ARCADE), display / platform only.
Local:    GAME / MAP / AI / PACARC untouched since mvs-hs (core frozen); PACREQ and PACPAL grew append-only; the RP code
          of PACSCR is ARCADE-only (RP-STATE leaves at once for CLASSIC); every documented RP edge case (section 9) is
          reached by a deck run on the independent models (tests/search_rp.py), and by the run configuration where it
          is not a screen state (families W / T / B / G, SCALE 3, the size guard, P before the start, a practice start,
          the unavailable high score); every model stream fits 2048 bytes.
Hercules: test_rp.py RP-LISTING (deck RP, load member PACRPD): every step RC 0000 (the high-score runs included), no
          compiler warnings; every TSD run after the marker = the models byte for byte (streams, alarms in the WCC,
          end lines and high-score lines).
RP.3 SPEED (section 6): the one conversion Q' = (Q x 300 + P) / (2 x P) (PACGAME = PACRT, the authorised core change
          only), the quantum chosen only in PACMAIN, NORMAL = every reference (identity on every table row), FAST
          values / wall-clock lengths / warning <= fright on every row, the FAST TSD and BAT runs = the models with the
          125 ms quantum, a pause freezes every converted timer, TURN / NORMAL / invalid SPEED = the references.
"""
import os
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tools'))
os.environ.setdefault('PACMAN_LATER_PHASE', 'RP')
import ref_gp2 as L  # noqa: E402
import ref_rt  # noqa: E402
import ref_hs as H  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
import search_rp as S  # noqa: E402
from ref_rp import bells  # noqa: E402
from ref_snap import Log  # noqa: E402
from make_deck import RP_MARK, RP_RT, RP_SEED, RP_TURN, RP3_BAT, RP3_CLIST, RP3_MARK, RP3_TSD, build  # noqa: E402
import ref_rp  # noqa: E402
import subprocess  # noqa: E402


def git_show(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:./{path}'], cwd=R, capture_output=True, text=True,
                          check=True).stdout.splitlines()


def src(path):
    return (R / path).read_text().splitlines()


# 1. sources -----------------------------------------------------------------------------------------------------------
BASE = 'mvs-hs'
for f in ('src/cobol/PACMAP.cob', 'src/cobol/PACAI.cob', 'src/copy/PACARC.cpy',
          'src/copy/PACSTATE.cpy', 'src/copy/PACMREQ.cpy', 'src/copy/PACDS.cpy', 'src/cobol/PACINPT.cob',
          'src/asm/PACFSIO.asm', 'src/asm/PACHSIO.asm', 'maps/LEVEL1.txt', 'maps/ARCADE1.txt'):
    assert git_show(BASE, f) == src(f), f
for f in ('src/copy/PACREQ.cpy', 'src/copy/PACPAL.cpy'):
    old, new = git_show(BASE, f), src(f)
    assert new[:len(old)] == old, f + ' must grow append-only'
scr = (R / 'src/cobol/PACSCR.cob').read_text()
st = scr[scr.index('       RP-STATE.'):scr.index('       RP-STATE-EXIT.')]
assert '           IF ARC-ON = 0\n               GO TO RP-STATE-EXIT.' in st, 'RP-STATE must leave at once for CLASSIC'
assert st.index('GO TO RP-STATE-EXIT') < st.index('PU-START'), 'nothing before the CLASSIC exit'
disp = (R / 'src/cobol/PACDISP.cob').read_text()
assert '           IF ARC-ON = 1 AND F-LOST = 1 AND REQ-PLAY = \'R\'\n               PERFORM FINAL-DEATH.' in disp
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
# RP.2b D40 (section 11): PACPLAT reads again only while QS-ACT = R (a test-before PERFORM: a valid first reply
# = no extra read), drains only after F, and takes the capabilities only from an accepted reply; PACFSIO unchanged
plat = (R / 'src/cobol/PACPLAT.cob').read_text()
tc = plat[plat.index('       TRY-COLOUR.'):plat.index('       TRY-COLOUR-EXIT.')]
assert '''               PERFORM QRY-MORE THRU QRY-MORE-EXIT
                   UNTIL QS-ACT NOT = 'R'.''' in tc and "IF FS-RC = 0 AND QS-ACT = 'F'\n               PERFORM QRY-DRAIN." in tc
assert "IF QS-ACT NOT = 'A'\n               MOVE 4 TO FS-RC." in tc
assert tc.index("MOVE 4 TO FS-RC.") < tc.index('MOVE QO-COLOUR TO HAS-COLOUR')
assert plat.count("MOVE 'RECT' TO FS-OP") == 3      # the TURN idle tick (G3) + QRY-MORE + QRY-DRAIN-ONE
# RP.3: PACGAME = mvs-hs plus only the authorised conversion (docs/CORE_CHANGES.md 2026-10-13)
old, new = git_show(BASE, 'src/cobol/PACGAME.cob'), src('src/cobol/PACGAME.cob')
old = [l.replace('MOVE KL-WRT (WS-LR) TO ARC-KWARN.', 'MOVE KL-WRT (WS-LR) TO ARC-KWARN') for l in old]
it, extra = iter(new), []
for l in old:
    for m in it:
        if m == l:
            break
        extra.append(m)
    else:
        raise AssertionError('PACGAME lost a line: ' + l)
extra += list(it)
rp3_ok = re.compile(r'^      \*|^       RT-CONV(-EXIT)?\.$|^           EXIT\.$|^       01  WS-C[QND] |WS-CQ|RT-CONV|REQ-RTPER|'
                    r'^           ELSE$|^           IF WS-KR = 2$')
assert extra and all(rp3_ok.search(l) for l in extra), [l for l in extra if not rp3_ok.search(l)]


def para(text, name):
    body = text[text.index(f'       {name}.\n'):text.index(f'       {name}-EXIT.\n')]
    return [l for l in body.splitlines()[1:] if not l.startswith('      *')]


game, rt = (R / 'src/cobol/PACGAME.cob').read_text(), (R / 'src/cobol/PACRT.cob').read_text()
conv = para(game, 'RT-CONV')
assert conv == para(rt, 'RT-CONV') and '           COMPUTE WS-CN = WS-CQ * 300 + REQ-RTPER.' in conv and \
    '           DIVIDE WS-CN BY WS-CD GIVING WS-CQ.' in conv, 'one conversion, the same in PACGAME and PACRT'
assert game.count('PERFORM RT-CONV THRU RT-CONV-EXIT') == 5 and rt.count('PERFORM RT-CONV THRU RT-CONV-EXIT') == 3
for name, v in (('FRZ-INIT', 10), ('RDY-INIT', 4), ('PUQ-INIT', 5)):
    assert re.search(r'01  ' + name + r'\s+PIC 99 VALUE ' + str(v) + r'\.', rt), name
assert 'MOVE RT-FRT TO RT-FRZ' in rt and 'MOVE FRZ-INIT TO RT-FRZ' not in rt
# the quantum is chosen in PACMAIN only: no other 125 in the game sources (except the ENTER AID X'7D' = 125)
for f in sorted((R / 'src').rglob('*')):
    if f.suffix in ('.cob', '.cpy', '.clist', '.asm') and f.name != 'PACMAIN.cob' and 'probe' not in f.parts:
        code_ = [l for l in f.read_text().splitlines() if not l.startswith('      *') and not l.lstrip().startswith('/*')]
        assert not [l for l in code_ if re.search(r'\b125\b', l) and l.strip() != 'IF WS-V NOT = 125'], f
main = (R / 'src/cobol/PACMAIN.cob').read_text()
assert "IF PARM-LEN > 23 AND PARM-SPEED = 'F'\n               MOVE 125 TO REQ-RTPER." in main and \
    'MOVE 150 TO REQ-RTPER.' in main and main.index('MOVE 150 TO REQ-RTPER.') < main.index("MOVE 'RSET' TO REQ-OP")
# a digit in column 24 = the old 3-digit start level (D37: = 1), so every pre-RP.3 PARM keeps its meaning (GP2 G2ROW)
assert 'IF PARM-LEN > 23 AND PARM-SPEED NUMERIC\n               MOVE 1 TO REQ-START.' in main
# absolute deadlines, no catch-up: DO-WDLN = mvs-hs plus only the period taken from REQ-RTPER
wd_old, wd_new = (t[t.index('       DO-WDLN.'):t.index('       COPY-TEXT.')] for t in
                  ('\n'.join(git_show(BASE, 'src/cobol/PACPLAT.cob')) + '\n', plat))
assert wd_new == wd_old.replace('           COMPUTE RT-NEXT', '           MOVE REQ-RTPER TO RT-PERIOD.\n'
                                '           COMPUTE RT-NEXT', 1)
assert 'COMPUTE RP-DTH = 11 - REQ-RTFRZ' not in scr and re.search(r'01  RP-DTHMS\s+PIC 999 VALUE 150\.', scr)
assert 'PERFORM FD-FRAME VARYING FD-K FROM REQ-RTFRT BY -1\n               UNTIL FD-K NOT > REQ-RTRDY.' in disp
clist = (R / 'src/clist/PACMAN.clist').read_text()
assert 'LEVEL(1) SPEED(NORMAL)' in clist and 'SET &F = &SUBSTR(1:1,&SPEED)' in clist and '&W&L&F)' in clist
assert all(len(l) <= 72 for l in clist.replace('@@PREFIX@@', 'HERC01.PACMAN').splitlines())
print('RP sources PASS (core frozen + authorised RP.3 conversion, append-only copies, ARCADE-only RP code, D40 read',
      'loop, one quantum / one conversion)')


# 2. the models --------------------------------------------------------------------------------------------------------
def cards(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


def hs_of(dd, start):
    if not dd:
        return None, None
    if dd == 'DUMMY':
        return ('E', 0, start), 'DUMMY'
    m = dd[2:]
    if m in RP_SEED:
        return ('R', RP_SEED[m], start), ('M', m)
    return ('Z', 0, start), ('M', m)


runs, cov = [], set()
store = H.Pds({m: [H.record(v, 1)] for m, v in RP_SEED.items()})
for run in RP_TURN:
    d, c, h, a, r, gl, sc, cv, snd, st_, dd = run
    start = L.parse_start(st_)
    hs, hdd = hs_of(dd, start)
    log = Log()
    fs = gx.frames(c, h == 'Y', a == 'Y', r, gl, sc, cv, snap=log,
                   mk=lambda ai, n, s=start: L.Level(ai, n, 'T', s), d=d, hs=hs)
    out = L.simulate(cards(d, c), start=start)
    wend = out[-7:] + (H.end_lines(store, hdd, *H.final(out), start) if hdd else [])
    runs.append((run, bells(fs, log, snd), wend))
    cov |= S.cover('T', d, c, cv, hs, start, sc, gl)
for run in RP_RT:
    d, c, cv, snd, st_, dd = run
    start = L.parse_start(st_)
    hs, hdd = hs_of(dd, start)
    log = Log()
    end, fs = ref_rt.tsd(cards(d, c), cv, snap=log, mk_game=lambda ai, n, s=start: L.Level(ai, n, 'R', s),
                         mk_ctl=L.LevelRT, hs=hs)
    wend = end[-8:] + (H.end_lines(store, hdd, *H.final(end), start) if hdd else [])
    runs.append((run, bells(fs, log, snd), wend))
    cov |= S.cover('R', d, c, cv, hs, start)
missing = [e for e in S.EDGES if e not in cov]
assert not missing, missing
cfg = {'W': any(r[7] == 'W' and r[6] == '4' for r in RP_TURN), 'T': any(r[7] == 'T' and r[6] == '4' for r in RP_TURN),
       'B': any(r[7] == 'D' and r[6] == '4' for r in RP_TURN), 'G': any(r[6] == 'N' for r in RP_TURN),
       '3': any(r[6] == '3' for r in RP_TURN), 'guard': any(r[6] == 'T' for r in RP_TURN),
       'P before start': cards('rpcases', 'RPPAUSE')[1] == 'P' and cards('rpcases', 'RPLOST')[1] == 'P',
       'practice': any(r[9] not in ('', '1', '01') and r[10] for r in RP_TURN),
       'unavailable': any(r[10] == 'DUMMY' for r in RP_TURN)}
assert all(cfg.values()), cfg
allf = [f for _, (fs, _), _ in runs for f in fs]
assert max(len(f) for f in allf) <= 2048
print('RP local checks PASS:', len(RP_TURN), 'TURN and', len(RP_RT), 'REALTIME TSD runs,', len(allf),
      'model streams, largest', max(len(f) for f in allf), 'bytes; edges', len(S.EDGES), '+ config', len(cfg))


# 2b. RP.3 SPEED (docs/RP-POLISH.md 6) ---------------------------------------------------------------------------------
T = ref_rt
rows = [L.ROWS[k] for k in range(1, 14)]
# NORMAL: the conversion is the identity on every designed value (every pre-RP.3 quantum count, every row)
for q in [r[4] for r in rows] + [r[5] for r in rows] + [L.EYES['R'], L.FRUIT_TIME['R'], T.FREEZE, T.READY_Q, T.POPUP_Q]:
    assert T.quanta(q, T.NORMAL) == q, q
# FAST: every fright / warning row (design section 6), each within half a quantum of its NORMAL length, warning <= fright
FAST_FR = [48, 41, 32, 24, 16, 41, 16, 16, 8, 41, 16, 8, 8]
FAST_WR = [12, 12, 12, 8, 8, 12, 8, 8, 4, 12, 8, 4, 4]
assert [T.quanta(r[4], T.FAST) for r in rows] == FAST_FR and [T.quanta(r[5], T.FAST) for r in rows] == FAST_WR
for r, f, w in zip(rows, FAST_FR, FAST_WR):
    assert abs(f * T.FAST - r[4] * T.NORMAL) * 2 <= T.FAST and abs(w * T.FAST - r[5] * T.NORMAL) * 2 <= T.FAST
    assert w <= f
assert [T.quanta(q, T.FAST) for q in (L.FRUIT_TIME['R'], L.EYES['R'], T.FREEZE, T.READY_Q, T.POPUP_Q)] == \
    [72, 24, 12, 5, 6]
assert (T.period('F'), T.period('N'), T.period('X'), T.period(' ')) == (125, 150, 150, 150)
for lv in range(1, 14):                          # the model game loads the converted values; TURN ignores SPEED
    gr, gt = L.Level(1, 1, 'R', lv), L.Level(1, 1, 'T', lv)
    gr.per = gt.per = T.FAST
    assert gr.k()[:3] == (FAST_FR[lv - 1], FAST_WR[lv - 1], 24) and gt.k()[:3] == rows[lv - 1][2:4] + (L.EYES['T'],)


def bat_rows(lines):
    """BAT REALTIME ARCADE lines -> [(quantum, inputs, positions, fr, evt, modes, bt, flags)]."""
    out = []
    for k, l in enumerate(lines):
        m = re.match(r'Q(\d{7}) IN=(.{8}) (.*)$', l)
        if m:
            a, lv = lines[k + 2], lines[k + 3]
            out.append((int(m.group(1)), m.group(2), m.group(3) + lines[k + 1], int(a[a.index('FR=') + 3:][:3]),
                        a[a.index('EV=') + 3:][:4], a[a.index(' M=') + 3:], int(lv[lv.index('BT=') + 3:][:3]),
                        lv[lv.index('EV=') + 3:]))
    return out


def timer_events(rows_):
    """(eyes wait, fruit time, fright length, warning quanta) measured on a BAT REALTIME trace."""
    ev = {}
    for k, (q, _, _, fr, evt, modes, bt, flg) in enumerate(rows_):
        if evt == 'POWR':
            ev['pow'] = q
        if fr == 0 and k and rows_[k - 1][3] == 1:
            ev.setdefault('fright', q - ev['pow'])
        if evt == 'GHST':
            ev['ghst'] = q
        if k and 'E' in rows_[k - 1][5] and 'E' not in modes and 'D' not in flg:
            ev.setdefault('eyes', q - ev['ghst'])
        if 'A' in flg:
            ev['spawn'] = q
        if k and rows_[k - 1][6] == 1 and bt == 0 and 'F' not in flg:
            ev.setdefault('fruit', q - ev['spawn'])
    return ev


tim = {per: L.rt_simulate(cards('rpcases', 'RP3TIM'), 1, per=per) for per in (T.NORMAL, T.FAST)}
fast, norm = bat_rows(tim[T.FAST]), bat_rows(tim[T.NORMAL])
assert timer_events(fast) == {'pow': 30, 'ghst': 29, 'spawn': 32, 'fright': 48, 'eyes': 24, 'fruit': 72}, \
    timer_events(fast)
assert {k: v for k, v in timer_events(norm).items() if k in ('fright', 'eyes')} == {'fright': 40, 'eyes': 20}
# the movement cadence is not rescaled: FAST = NORMAL quantum for quantum until a converted timer first runs out at
# NORMAL (the eyes revive after 20 quanta); CLASSIC without a death: the whole run is the same
first = next(k for k, (a, b) in enumerate(zip(fast, norm)) if a[2] != b[2])
assert fast[first][0] >= 29 + 20 and all(a[2] == b[2] for a, b in zip(fast[:first], norm[:first])), first
assert T.simulate(cards('rtcases', 'RTWIN'), T.FAST) == T.simulate(cards('rtcases', 'RTWIN'))
# a pause freezes every converted timer: RP3PAU = RP3TIM quantum for quantum (only the recorded inputs differ)
pau = bat_rows(L.rt_simulate(cards('rpcases', 'RP3PAU'), 1, per=T.FAST))
assert [r[2:] for r in pau] == [r[2:] for r in fast] and [r[1] for r in pau] != [r[1] for r in fast]
k0 = next(k for k, r in enumerate(pau) if 'P' in r[1])
assert pau[k0 - 1][3] > 0 and pau[k0 - 1][6] > 0 and 'E' in pau[k0 - 1][5], 'paused while fright, fruit, eyes run'


def decor_log(run_):
    """The decorations of every screen of a model run (ref_rp.Tracker wrapped): [(rtq, rtfrz, rp)]."""
    got, orig = [], ref_rp.Tracker

    class Rec(orig):
        def frame(self, g, play='T', rtstat=None, rtfrz=0, rtq=0, dth=None, ends=False, **kw):
            rp = super().frame(g, play, rtstat, rtfrz, rtq, dth, ends, **kw)
            got.append((rtq, rtstat, rtfrz, rp))
            return rp
    ref_rp.Tracker = Rec
    try:
        run_()
    finally:
        ref_rp.Tracker = orig
    return got


def mk_rt(start):
    return lambda ai, n: L.Level(ai, n, 'R', start)


# death animation / READY! at FAST: frames 1 1 2 3 4 5 6 (freeze quanta 12..6: elapsed 0..750 ms, 150 ms a frame),
# READY! in the last 5 (quanta 5..1 = 625 ms, the conversion of 4), the final death the same 7 frames
dl = decor_log(lambda: ref_rt.tsd(cards('rpcases', 'RPLOST'), 'W', mk_game=mk_rt(1), mk_ctl=L.LevelRT, per=T.FAST))
frz = {}
for q, stt, f, rp in dl:
    if stt == 'FRZ ':
        frz.setdefault(f, set()).add((rp['dth'][0] if rp['dth'] else 0, rp['ready']))
assert frz == {12: {(1, False)}, 11: {(1, False)}, 10: {(2, False)}, 9: {(3, False)}, 8: {(4, False)},
               7: {(5, False)}, 6: {(6, False)}, 5: {(0, True)}, 4: {(0, True)}, 3: {(0, True)}, 2: {(0, True)},
               1: {(0, True)}}, frz
dl_n = decor_log(lambda: ref_rt.tsd(cards('rpcases', 'RPLOST'), 'W', mk_game=mk_rt(1), mk_ctl=L.LevelRT))
assert {f: rp['dth'][0] for _, s_, f, rp in dl_n if s_ == 'FRZ ' and rp['dth']} == {10: 1, 9: 2, 8: 3, 7: 4, 6: 5, 5: 6}
# popups at FAST: shown in the quanta t0 .. t0 + 6 (the conversion of 5) unless a death / clear removes them
for d, c in (('rpcases', 'RPPAUSE'), ('gp2cases', 'G2RCLR'), ('rpcases', 'RP3TIM')):
    dl = decor_log(lambda: ref_rt.tsd(cards(d, c), 'W', mk_game=mk_rt(1), mk_ctl=L.LevelRT, per=T.FAST))
    shown = {}
    for q, stt, f, rp in dl:
        if rp and rp['pu']:
            shown.setdefault(rp['pu']['t0'], set()).add(q)
    assert shown and all(qs == set(range(t0, t0 + 7)) or max(qs) < t0 + 6 for t0, qs in shown.items()), (c, shown)
    assert any(qs == set(range(t0, t0 + 7)) for t0, qs in shown.items()), c

# the FAST / speed-variant deck runs on the models
rp3_tsd, rp3_bat = [], []
for run in RP3_TSD:
    play, d, c, cv, snd, st_, sp, rules = run
    start, per, log, cs = L.parse_start(st_), T.period(sp), Log(), cards(d, c)
    if play == 'T':                             # TURN ignores SPEED: the NORMAL TURN model
        fs = gx.frames(c, True, True, 'P', 'G', '4', cv, snap=log, mk=lambda ai, n, s=start: L.Level(ai, n, 'T', s),
                       d=d)
        wend = L.simulate(cs, start=start)[-7:]
    elif rules == 'A':
        end, fs = ref_rt.tsd(cs, cv, snap=log, mk_game=mk_rt(start), mk_ctl=L.LevelRT, per=per)
        wend = end[-8:]
    else:
        end, fs = ref_rt.tsd(cs, cv, snap=log, per=per)
        wend = end[-5:]
    rp3_tsd.append((run, bells(fs, log, snd), wend))
from test_g0 import BANNER, oracle  # noqa: E402
for run in RP3_BAT:
    play, d, c, rules, st_, sp = run
    start, per, cs = L.parse_start(st_), T.period(sp), cards(d, c)
    if rules == 'C':
        w = oracle()[0][c] if play == 'T' else T.simulate(cs, per=per)
    else:
        w = L.rt_simulate(cs, start, per=per) if play == 'R' else L.simulate(cs, start=start)
    rp3_bat.append((run, [l.rstrip() for l in w]))
n3 = sum(len(f) for _, (fs, _), _ in rp3_tsd for f in [fs])


def clist_parm(kw):
    """The PARM the CLIST builds (design 6: first letters, LEVEL zero-padded to 2 characters, else 01, SPEED in 24)."""
    d = dict(AI='1', GHOSTS='1', COLOR='AUTO', HILITE='AUTO', ANIM='AUTO', REDRAW='PARTIAL', METRICS='NO',
             GLYPHS='AUTO', SCALE='AUTO', CANVAS='AUTO', PLAY='REALTIME', SOUND='AUTO', RULES='CLASSIC', LEVEL='1',
             SPEED='NORMAL')
    d.update(re.findall(r'(\w+)\((\w*)\)', kw))
    lv = '0' + d['LEVEL'] if len(d['LEVEL']) == 1 else d['LEVEL']
    lv = lv if len(lv) == 2 else '01'
    return (f"TSO AI{d['AI']} {d['GHOSTS']} " + ('M' if d['METRICS'] == 'YES' else 'N') + ''.join(
        d[k][0] for k in ('COLOR', 'HILITE', 'ANIM', 'REDRAW', 'GLYPHS', 'SCALE', 'CANVAS', 'PLAY', 'SOUND', 'RULES'))
        + lv + d['SPEED'][0])


CL_WANT = [clist_parm(k) for k in RP3_CLIST]
assert all(len(p_) == 24 for p_ in CL_WANT)
assert [(p_[21:23], T.period(p_[23])) for p_ in CL_WANT] == [('01', 150), ('01', 125), ('07', 125), ('13', 150),
                                                             ('01', 150), ('00', 150), ('01', 125)]
assert L.parse_start('00') == 1 and L.parse_start('07') == 7
assert max(len(f) for _, (fs, _), _ in rp3_tsd for f in fs) <= 2048
print('RP.3 local checks PASS: identity at 150 ms on', len(rows), 'rows; FAST fright', FAST_FR, 'warning', FAST_WR,
      '(<= fright), fruit 72, eyes 24, freeze 12, READY! 5, popup 6; RP3TIM timers 48/24/72 = 6.0/3.0/9.0 s;',
      'cadence per quantum; pause freezes the timers;', len(RP3_TSD), 'TSD runs (', n3, 'streams ) +', len(RP3_BAT),
      'BAT runs')


# 3. the Hercules listing ----------------------------------------------------------------------------------------------
def listing_check(path):
    lines = Path(path).read_text().splitlines()
    deck = build('RP', 'HERC01.PACMAN')
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', deck, re.M))
    rcs = re.findall(r'PACBLDRP\s+(\w+)\s+(?:IEBGENER|IEBUPDTE|IEFBR14|IKFCBL00|IFOX00|IEWL|PACRPD|PACQRYT|IKJEFT01)\s+RC= (\d{4})',
                     '\n'.join(lines))
    assert len(rcs) == nsteps and all(rc == '0000' for _, rc in rcs), \
        (nsteps, len(rcs), [x for x in rcs if x[1] != '0000'])
    assert not [l for l in lines if re.search(r'IKF\d{4}I-[WCE]', l)], 'compiler warnings'
    t2, j, ns = lines[lines.index(RP_MARK) + 1:], 0, 0
    for run, (wstreams, _), wend in runs:
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
        ends = [l.rstrip() for l in t2[j:j + len(wend)]]
        j += len(wend)
        assert len(streams) == len(wstreams), (run, len(streams), len(wstreams))
        for x, (p, q) in enumerate(zip(streams, wstreams)):
            assert p == q, (run, x, len(p), len(q),
                            next((y for y in range(min(len(p), len(q))) if p[y] != q[y]), min(len(p), len(q))))
        assert ends == wend, (run, ends, wend)
        ns += len(streams)
    print('MVS-RP RP.2 PASS:', len(rcs), 'steps RC 0000;', len(runs), 'ARCADE TSD runs =', ns, 'model streams')


def d40_check(path):
    from qry_cases import seq_lines
    got = [l.rstrip() for l in Path(path).read_text().splitlines() if l.startswith('QSL ')]
    assert got == seq_lines(), [(a, b) for a, b in zip(got, seq_lines()) if a != b] or (len(got), len(seq_lines()))
    print('MVS-RP RP.2b D40 PASS:', len(got), 'startup sequences = model (valid first, ENTER / junk / AIDs /',
          'malformed then valid, empty reads, fallback by records and by time, single-record validity)')


def rp3_check(path):
    lines = Path(path).read_text().splitlines()
    t2, j, ns = lines[lines.index(RP3_MARK) + 1:], 0, 0
    for run, (wstreams, _), wend in rp3_tsd:
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
            streams.append(bytes.fromhex(hexs))
            assert len(streams[-1]) == int(m.group(1))
        ends = [l.rstrip() for l in t2[j:j + len(wend)]]
        j += len(wend)
        assert len(streams) == len(wstreams), (run, len(streams), len(wstreams))
        for x, (p, q) in enumerate(zip(streams, wstreams)):
            assert p == q, (run, x, len(p), len(q),
                            next((y for y in range(min(len(p), len(q))) if p[y] != q[y]), min(len(p), len(q))))
        assert ends == wend, (run, ends, wend)
        ns += len(streams)
    tail = [l.rstrip() for l in t2[j:]]
    starts = [i for i, l in enumerate(tail) if l == BANNER]
    assert len(starts) == len(rp3_bat), (len(starts), len(rp3_bat))
    nl = 0
    for (run, w), s0 in zip(rp3_bat, starts):
        got = tail[s0:s0 + len(w)]
        assert got == w, (run, next(((x, a, b) for x, (a, b) in enumerate(zip(got, w)) if a != b), (len(got), len(w))))
        nl += len(w)
    cl = [l.rstrip() for l in lines if l.startswith('RP3PARM=')]
    assert cl == ['RP3PARM=' + p_ + '=' for p_ in CL_WANT], (cl, CL_WANT)
    print('MVS-RP RP.3 PASS:', len(rp3_tsd), 'TSD runs =', ns, 'model streams (FAST ARCADE / CLASSIC, NORMAL, invalid,',
          'TURN);', len(rp3_bat), 'BAT runs =', nl, 'model lines; CLIST PARM', len(cl), 'keyword sets (TMP)')


if ARGS:
    listing_check(ARGS[0])
    d40_check(ARGS[0])
    rp3_check(ARGS[0])
