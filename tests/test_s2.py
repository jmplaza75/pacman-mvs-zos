#!/usr/bin/env python3
"""MVS-S2 acceptance (D41, docs/S2-PATTERNS.md): alarm patterns, display / platform only.
Local:    GAME / MAP / AI / PACARC / PACRT (and PACSCR, PACINPT, PACQRY, the assembler modules, the other copies) equal
          tag mvs-rp; PACREQ appended REQ-ALARM only; PACMAIN / PACPLAT only added lines; PACDISP keeps SET-BELL and
          ARC-BELL byte for byte and calls SET-BELL only through BELL-SET (and the S1 SCR-END-BELL); CLIST ALARM(PATTERN)
          in column 25. The independent pattern model (tests/ref_s2.py) on the deck runs: its event detection = the
          S1 / GP2 bell rule of every write, the D41 pattern rules hold, and every documented edge case of section 6
          is reached by a run (D12).
Hercules: test_s2.py S2-LISTING (deck S2, load member PACS2D): every step RC 0000, no compiler warnings; every TSD run
          after the marker = the model streams byte for byte (alarm bits and end-pause bell-only writes) and the end
          lines; BAT / TSO line mode with column 25 = the 1.0-MVS oracle / the models (no screen sent).
Regression (SINGLE path, run separately on decks rebuilt into PACS2D, listings normalised PACS2D -> PACMAIN or PACRPD):
          PACMAN_LATER_PHASE=S2 tests/test_rp.py RP-LISTING, tests/test_hs.py HS GP23 GP2 listings.
"""
import difflib
import os
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tools'))
os.environ.setdefault('PACMAN_LATER_PHASE', 'S2')
import ref_gp2 as L  # noqa: E402
import ref_rt  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
import ref_s2 as S  # noqa: E402
from ref_rp import bells as gp2_bells  # noqa: E402
from ref_snap import Log  # noqa: E402
from make_deck import S2_LINE, S2_MARK, S2_TSD, build  # noqa: E402
from search_s2 import START_OF  # noqa: E402

BASE = 'mvs-rp'


def git_show(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:./{path}'], cwd=R, capture_output=True, text=True,
                          check=True).stdout.splitlines()


def src(path):
    return (R / path).read_text().splitlines()


def para(text, name, end):
    return text[text.index(f'       {name}.\n'):text.index(f'       {end}.\n')]


# 1. sources -----------------------------------------------------------------------------------------------------------
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
for f in ('src/cobol/PACGAME.cob', 'src/cobol/PACMAP.cob', 'src/cobol/PACAI.cob', 'src/cobol/PACRT.cob',
          'src/cobol/PACSCR.cob', 'src/cobol/PACINPT.cob', 'src/cobol/PACQRY.cob', 'src/cobol/PACQRYT.cob',
          'src/copy/PACARC.cpy', 'src/copy/PACSTATE.cpy', 'src/copy/PACMREQ.cpy', 'src/copy/PACPAL.cpy',
          'src/copy/PACDS.cpy', 'src/asm/PACFSIO.asm', 'src/asm/PACTSO.asm', 'src/asm/PACHSIO.asm',
          'maps/LEVEL1.txt', 'maps/ARCADE1.txt'):
    assert git_show(BASE, f) == src(f), f
old, new = git_show(BASE, 'src/copy/PACREQ.cpy'), src('src/copy/PACREQ.cpy')
assert new[:len(old)] == old, 'PACREQ must grow append-only'
assert [l.split()[1] for l in new[len(old):] if l[6:7] != '*'] == ['REQ-ALARM']
for name in ('PACMAIN', 'PACPLAT'):                     # added lines only
    old, new = git_show(BASE, f'src/cobol/{name}.cob'), src(f'src/cobol/{name}.cob')
    assert not [d for d in difflib.ndiff(old, new) if d[:2] == '- '], name
main = (R / 'src/cobol/PACMAIN.cob').read_text()
assert "           MOVE 'S' TO REQ-ALARM.\n           IF PARM-LEN > 24 AND PARM-ALARM = 'P'\n" \
       "               MOVE 'P' TO REQ-ALARM." in main
assert main.index('PARM-SPEED        PIC X.') < main.index('PARM-ALARM        PIC X.')
plat = (R / 'src/cobol/PACPLAT.cob').read_text()
assert "           ELSE IF REQ-OP = 'DLWT' AND REQ-MODE = 'TSC'\n" \
       "               CALL 'PACTSO' USING TSO-DLWT TSO-RC REQ-TIME\n" in plat
disp, disp0 = (R / 'src/cobol/PACDISP.cob').read_text(), '\n'.join(git_show(BASE, 'src/cobol/PACDISP.cob')) + '\n'
for a, b in (('SET-BELL', 'SCR-TICK'), ('ARC-BELL', 'ARC-BELL')):
    t, t0 = (x[x.index(f'       {a}.\n'):] for x in (disp, disp0))
    if a == b:                                          # ARC-BELL is the last paragraph
        assert t == t0, a
    else:
        assert t[:t.index(f'       {b}.\n')] == t0[:t0.index(f'       {b}.\n')], a
# SET-BELL is reached only through BELL-SET and the S1 not-scaled end (SCR-END-BELL)
assert disp.count('PERFORM SET-BELL.') == 2 and 'PERFORM SET-BELL.' in para(disp, 'BELL-SET', 'PAT-CLASS') and \
    'PERFORM SET-BELL.' in para(disp, 'SCR-END-BELL', 'BELL-WRITE')
assert disp.count('PERFORM BELL-SET') == 4                       # SCR-PRMT, SCR-ENDS-SEND, SCR-TICK, SCR-RTQF
bs = para(disp, 'BELL-SET', 'PAT-CLASS')
assert bs.count("IF REQ-ALARM = 'P' AND REQ-SOUND = 'Y'") == 2, 'the pattern code runs only with PATTERN and SOUND Y'
# the end pause: no pattern left = the S1 WAIT; else WDLN-paced bell-only writes, then DLWT to t0 + 3000 (never longer)
ep = para(disp, 'END-PAUSE', 'END-PAUSE-EXIT')
assert "IF PT-ON = 0\n               MOVE 'WAIT' TO REQ-OP" in ep and 'COMPUTE REQ-TIME = PT-T0 + 3000' in ep
assert 'PERFORM END-WDLN PT-G TIMES.' in para(disp, 'END-STEP', 'END-STEP-EXIT')
# G: 2 at 150 ms, 3 below (125 ms is the only other quantum, chosen in PACMAIN only); bells per event 1 2 2 3 4 3
assert "MOVE 2 TO PT-G.\n           IF REQ-RTPER < 150\n               MOVE 3 TO PT-G." in disp
assert "PT-TAB                PIC X(6) VALUE '122343'." in disp
assert [S.BELLS[k] for k in range(1, 7)] == [1, 2, 2, 3, 4, 3] and (S.gap(150), S.gap(125)) == (2, 3)
# the PT- state changes only inside the S2 paragraphs (and the S2 lines of SCR-ENDS / SCR-RTQF)
code = [l for l in disp.splitlines() if not l.startswith('      *')]
cur, owners = None, {}
for l in code:
    m = re.match(r'^       ([A-Z0-9-]+)\.$', l)
    if m:
        cur = m.group(1)
    for f in re.findall(r'(?:TO|FROM) (PT-[A-Z0-9]+)', l) + re.findall(r'COMPUTE (PT-[A-Z0-9]+)', l):
        owners.setdefault(f, set()).add(cur)
assert set().union(*owners.values()) <= {'BELL-SET', 'PAT-CLASS', 'PAT-PLAY', 'PAT-STEP', 'END-PAUSE', 'END-STEP',
                                         'SCR-ENDS', 'SCR-RTQF'}, owners
clist = (R / 'src/clist/PACMAN.clist').read_text()
assert 'SPEED(NORMAL) +\n  ALARM(PATTERN)\n' in clist and 'SET &K = &SUBSTR(1:1,&ALARM)' in clist and \
    '&W&L&F&K)' in clist
assert all(len(l) <= 72 for l in clist.replace('@@PREFIX@@', 'HERC01.PACMAN').splitlines())
print('S2 sources PASS (core and PACRT as mvs-rp, PACREQ +REQ-ALARM, PACMAIN / PACPLAT added lines only, SET-BELL /',
      'ARC-BELL unchanged, pattern code only with PATTERN + SOUND Y, end pause bounded by t0 + 3000, CLIST column 25)')


# 2. the model ---------------------------------------------------------------------------------------------------------
def cards(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


def start_of(d, c, st):
    return START_OF.get(c, 1) if d == 's2cases' else L.parse_start(st)


def model(run):
    """(single-rule streams, pattern streams, trace, log, end lines, period) of one S2 TSD run."""
    play, d, c, prof, cv, snd, rules, st, sp, al = run
    start, per, log = start_of(d, c, st), ref_rt.period(sp), Log()
    log.kinds = []
    h, a, r, gl, sc = prof[1] == 'Y', prof[2] == 'Y', prof[3], prof[4], prof[5]
    if play == 'T':
        mk = (lambda ai, n, s=start: L.Level(ai, n, 'T', s)) if rules == 'A' else gx.Game
        fs = gx.frames(c, h, a, r, gl, sc, cv, snap=log, mk=mk, d=d)
        if rules == 'A':
            end = L.simulate(cards(d, c), start=start)[-7:]
        else:
            from ref_mvs6 import simulate
            end = simulate(cards(d, c))[-4:]
    elif rules == 'A':
        e, fs = ref_rt.tsd(cards(d, c), cv, snap=log, mk_game=lambda ai, n, s=start: L.Level(ai, n, 'R', s),
                           mk_ctl=L.LevelRT, per=per)
        end = e[-8:]
    else:
        e, fs = ref_rt.tsd(cards(d, c), cv, snap=log, per=per)
        end = e[-5:]
    pat, trace = S.patterns(fs, log, snd, play, per)
    return fs, pat, trace, log, end, per


def all_events(last, snap, won_seen):
    """Every event of one write (not only the highest): for the coverage of the coalescing edges."""
    if last is None:
        return {'START'}
    ev = set()
    if len(snap) == 5:
        ev |= {'XLIFE'} if snap[3] > last[3] else set()
        ev |= {'DEATH'} if snap[2] > last[2] else set()
        ev |= {'CLEAR'} if snap[4] > last[4] else set()
    elif snap[0] < last[0]:
        ev.add('DEATH')
    if snap[1] and not won_seen:
        ev.add('WIN')
    return ev


def single_rings(fs, log, rules):
    """The S1 / GP2 single-bell rings (write indices; len(fs) = the end bell-only write): ARCADE ref_rp.bells, CLASSIC
    the S1 rule (first write, lives fell, first write after the win)."""
    if rules == 'A':
        return gp2_bells(fs, log, 'Y')[1]
    out, last, won = [], None, False
    for k, (lives, w) in enumerate(list(log) + [log.state()]):
        if last is None or lives < last or (w and not won):
            out.append(k)
        last, won = lives, won or w
    if log.kinds[-1] == 'E' and out and out[-1] == len(fs):
        out.pop()                                       # the end state = the end screen's: no bell-only write
    return out


EDGES = ['pattern-death-normal', 'pattern-death-fast', 'pattern-xlife-normal', 'pattern-xlife-fast',
         'pattern-clear-normal', 'pattern-clear-fast', 'over-on-final-death-frames', 'end-pause-over', 'end-pause-win',
         'replaced-xlife-by-death', 'one-write-death-xlife->death', 'one-write-clear-xlife->clear',
         'one-write-clear-death->clear', 'one-write-death-win->win', 'pause-holds-pattern', 'step-on-prompt-write',
         'prestart-no-ring', 'quit-drops-pattern', 'turn-single', 'not-scaled-end', 'sound-no']

runs, cov = [], set()
for run in S2_TSD:
    play, d, c, prof, cv, snd, rules, st, sp, al = run
    fs, pat, trace, log, end, per = model(run)
    g, kinds = S.gap(per), log.kinds
    runs.append((run, pat, end))
    assert max(len(f) for f in pat) <= 2048
    if snd != 'Y':
        assert pat == fs and trace == [], run           # SOUND(NO): every write as without sound
        cov.add('sound-no')
        continue
    # detection = the S1 / GP2 single-bell rule: the events sit exactly on the SINGLE rings
    evw = [k for k, e, _ in trace if e != 'STEP']
    assert evw == single_rings(fs, log, rules), (run, evw, single_rings(fs, log, rules))
    assert all(f[0] & 0x04 for k, f in enumerate(pat) if k in {x for x, _, _ in trace})
    assert not any(f[0] & 0x04 for k, f in enumerate(pat) if k not in {x for x, _, _ in trace})
    ends_e = kinds[-1] == 'E'
    for i, (k, e, _) in enumerate(trace):
        if e == 'STEP':
            continue
        steps = []
        for k2, e2, _ in trace[i + 1:]:
            if e2 != 'STEP':
                break
            steps.append(k2)
        prev = k
        for k2 in steps:
            if k2 >= len(kinds):                       # a bell-only write of the end pause, after the end screen
                assert ends_e and e in ('WIN', 'OVER') and pat[k2] == bytes([0xC6, 0x28, 0x00, 0x00]), (run, k2, e)
                cov.add('end-pause-' + e.lower())
                continue
            q = sum(1 for x in kinds[prev + 1:k2 + 1] if x in 'QP')
            assert q == g and kinds[k2] in 'QP', (run, e, prev, k2, q)     # exactly G quantum writes apart
            if kinds[k2] == 'P':
                cov.add('step-on-prompt-write')
            if 'N' in kinds[prev + 1:k2]:
                cov.add('pause-holds-pattern')
            if e == 'OVER' and rules == 'A' and play == 'R':
                cov.add('over-on-final-death-frames')
            prev = k2
        n, want = 1 + len(steps), S.BELLS[getattr(S, e)]
        if play == 'T' and e not in ('WIN', 'OVER'):
            assert n == 1, (run, e)
            cov.add('turn-single')
        elif n < want:
            nxt = next((x for x in trace if x[0] > k and x[1] != 'STEP'), None)
            if nxt is not None and nxt[0] < len(kinds):
                assert S.__dict__[nxt[1]] >= S.__dict__[e], (run, e, nxt)
                cov.add('replaced-' + e.lower() + '-by-' + nxt[1].lower())
            elif not ends_e and e in ('WIN', 'OVER'):
                assert n == 1 and k == len(fs), (run, e)   # not scaled: no end pause, the S1 bell-only write only
            else:
                assert end[0] in ('QUIT', 'EOF') and e not in ('WIN', 'OVER'), (run, e, end)
                cov.add('quit-drops-pattern')
        else:
            assert n == want, (run, e, n)
            if e not in ('WIN', 'OVER', 'START'):
                cov.add(f'pattern-{e.lower()}-{"fast" if per == 125 else "normal"}')
    last, won = None, False                             # several events in one write -> the highest one
    for k, snap in enumerate(log):
        evs = all_events(last, snap, won)
        last, won = snap, won or bool(snap[1])
        if len(evs) > 1:
            name = next(x for kk, x, _ in trace if kk == k)
            cov.add('one-write-' + '-'.join(sorted(evs)).lower() + '->' + name.lower())
    if play == 'R' and len(kinds) > 1 and kinds[1] == 'N':
        assert 1 not in {k for k, _, _ in trace}, run   # pre-start screens after the first never ring
        cov.add('prestart-no-ring')
    if not ends_e:
        assert play == 'T' and pat[-1] == bytes([0xC6, 0x28, 0x00, 0x00]) and trace[-1][1] != 'STEP', run
        cov.add('not-scaled-end')
missing = [e for e in EDGES if e not in cov]
assert not missing, (missing, sorted(cov))
n_streams = sum(len(p_) for _, p_, _ in runs)
print('S2 local checks PASS:', len(S2_TSD), 'TSD runs,', n_streams, 'model streams; events = the S1 / GP2 single rings;',
      'steps exactly G quantum writes apart; edges', len(EDGES), '(extra', sorted(cov - set(EDGES)), ')')


# 3. the Hercules listing ----------------------------------------------------------------------------------------------
def tsd_streams(t2, j):
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
    return streams, j


def listing_check(path):
    from test_g0 import BANNER, blocks, oracle
    lines = Path(path).read_text().splitlines()
    deck = build('S2', 'HERC01.PACMAN')
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', deck, re.M))
    rcs = re.findall(r'PACBLDS2\s+(\w+)\s+(?:IEBGENER|IKFCBL00|IFOX00|IEWL|PACS2D)\s+RC= (\d{4})', '\n'.join(lines))
    assert len(rcs) == nsteps and all(rc == '0000' for _, rc in rcs), \
        (nsteps, len(rcs), [x for x in rcs if x[1] != '0000'])
    assert not [l for l in lines if re.search(r'IKF\d{4}I-[WCE]', l)], 'compiler warnings'
    t2, j, ns, nb = lines[lines.index(S2_MARK) + 1:], 0, 0, 0
    for run, want, wend in runs:
        got, j = tsd_streams(t2, j)
        ends = [l.rstrip() for l in t2[j:j + len(wend)]]
        j += len(wend)
        assert len(got) == len(want), (run, len(got), len(want))
        for x, (p_, q) in enumerate(zip(got, want)):
            assert p_ == q, (run, x, len(p_), len(q),
                             next((y for y in range(min(len(p_), len(q))) if p_[y] != q[y]), min(len(p_), len(q))))
        assert ends == wend, (run, ends, wend)
        ns, nb = ns + len(got), nb + sum(1 for f in got if f[0] & 0x04)
    rest = [l.rstrip() for l in t2[j:]]
    assert not any(l.startswith('TSD ') for l in rest), 'a line-mode run sent a screen'
    batch_or, tso_or = oracle()
    starts = [i for i, l in enumerate(rest) if l == BANNER]
    assert len(starts) == len(S2_LINE), (len(starts), len(S2_LINE))
    for (kind, play, d, c, rules), s0 in zip(S2_LINE, starts):
        if kind == 'TSO':
            w = tso_or[c]
        elif rules == 'C':
            w = batch_or[c] if play == 'T' else [l.rstrip() for l in ref_rt.simulate(cards(d, c))]
        else:
            w = [l.rstrip() for l in L.simulate(cards(d, c), start=1)]
        assert rest[s0:s0 + len(w)] == w, (kind, c)
    print('MVS-S2 PASS:', len(rcs), 'steps RC 0000;', len(runs), 'TSD runs =', ns, 'model streams (', nb,
          'with the alarm bit );', len(S2_LINE), 'BAT / TSO line-mode runs = oracle / models')


if ARGS:
    listing_check(ARGS[0])
