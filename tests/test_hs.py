#!/usr/bin/env python3
"""MVS-HS acceptance (docs/HS-HISCORE.md, D38): the persistent ARCADE high score.
Local:    the core and every module outside the HS change are unchanged since mvs-gp2; PACREQ grew append-only by the
          D38 fields; only PACPLAT calls PACHSIO; GAME / MAP / AI never see the file; PACPLAT never receives the game
          state (so the end type cannot influence a save: an eligible WIN, which needs 99 level clears, is covered by
          this structure plus the LOST / QUIT / EOF runs); PACHSIO keeps the E16 guards; CLIST block and columns;
          the independent model tests/ref_hs.py.
Hercules: test_hs.py HS-LISTING [GP23-LISTING [GP2-LISTING]]
  - deck HS: every step RC 0000 except HSFILL (IEBUPDTE, directory full, RC 0012); no compiler warnings, assemblies
    severity 0;
  - every run (BAT TURN / REALTIME / CLASSIC, TSO line mode through IKJEFT01) = the GP2 model (CLASSIC: the 1.0-MVS
    oracle) followed by the HS lines of ref_hs, the member state carried from run to run;
  - the two TSD dry runs: streams and end lines = the same runs of the GP23 deck (GP23-LISTING), then the HS lines;
  - member prints, member list (no member created by a 0 score) and the CLIST block (DATA present / missing);
  - with GP2-LISTING: tests/test_gp2.py GP2 GP23 (the whole regression) with PACMAN_LATER_PHASE=HS.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tools'))
LATER = os.environ.get('PACMAN_LATER_PHASE', 'HS') != 'HS'
os.environ.setdefault('PACMAN_LATER_PHASE', 'HS')
import ref_gp2 as L  # noqa: E402
import ref_hs as H  # noqa: E402
from make_deck import (GP23_MARK, GP23_RT, GP23_TURN, HS_MARK, HS_PRINT, HS_RUNS, HS_TSD_RT, HS_TSD_TURN,  # noqa: E402
                       HS_TSO, build, clist_text, hs_clist_block)
from test_g0 import BANNER, oracle  # noqa: E402

BASE = 'mvs-gp2'


def git_show(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:./{path}'], cwd=R, capture_output=True, text=True,
                          check=True).stdout.splitlines()


def src(path):
    return (R / path).read_text().splitlines()


def code(lines):
    return [l for l in lines if l[6:7] != '*']


def cards(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


# 1. sources -------------------------------------------------------------------------------------------------------
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
subprocess.run([sys.executable, str(R / 'tests/ref_hs.py')], check=True, stdout=subprocess.DEVNULL)
assert 'D38 (MVS-HS)' in (R / 'docs/DECISIONS.md').read_text()
for f in ('src/cobol/PACGAME.cob', 'src/cobol/PACMAP.cob', 'src/cobol/PACAI.cob', 'src/copy/PACARC.cpy',
          'src/copy/PACSTATE.cpy', 'src/copy/PACMREQ.cpy', 'src/cobol/PACSCR.cob', 'src/cobol/PACRT.cob',
          'src/cobol/PACINPT.cob', 'src/cobol/PACQRY.cob', 'src/copy/PACPAL.cpy', 'src/copy/PACDS.cpy',
          'src/asm/PACFSIO.asm', 'src/asm/PACTSO.asm', 'maps/LEVEL1.txt', 'maps/ARCADE1.txt'):
    if LATER:           # a later phase (RP) changes the screens: only the source-equality pins are skipped
        continue
    assert git_show(BASE, f) == src(f), f
old_req, new_req = git_show(BASE, 'src/copy/PACREQ.cpy'), src('src/copy/PACREQ.cpy')
assert new_req[:len(old_req)] == old_req
HS_REQ = ['REQ-HSST', 'REQ-HISCORE', 'REQ-HSLVL', 'REQ-HSSCORE', 'REQ-HSGLVL', 'REQ-HSELIG', 'REQ-HSNEW']
added = [l.split()[1] for l in code(new_req[len(old_req):])]
assert added[:len(HS_REQ)] == HS_REQ and (LATER or added == HS_REQ), added
callers = [p.name for p in (R / 'src/cobol').glob('*.cob') if "'PACHSIO'" in p.read_text()]
assert callers == ['PACPLAT.cob'], callers
for m in ('PACGAME', 'PACMAP', 'PACAI', 'PACRT', 'PACSCR'):
    t = (R / f'src/cobol/{m}.cob').read_text()
    if m == 'PACSCR' and LATER:     # MVS-RP (D39): the HUD / end screen READ the high-score values, never the file
        assert 'PACHS' not in t and 'PACHSIO' not in t, m
        continue
    assert 'PACHS' not in t and 'HISCORE' not in t and 'REQ-HS' not in t, m
plat = (R / 'src/cobol/PACPLAT.cob').read_text()
assert 'PACSTATE' not in plat and 'PACARC' not in plat and 'F-WON' not in plat and 'F-LOST' not in plat
main = code(src('src/cobol/PACMAIN.cob'))
assert sum("'HSRD'" in l for l in main) == 1 and sum("'HSWR'" in l for l in main) == 1
asm = [l for l in src('src/asm/PACHSIO.asm') if not l.startswith('*')]
for need in ('OPEN  (PODCB,(INPUT)),TYPE=J', "OI    JFCB+X'34',X'08'", 'BLDL  PODCB,BLDLL', 'ESTAE ESTEXIT,CT',
             'ESTAE 0', 'OPEN  (QUDCB,(UPDAT))', 'OPEN  (PSDCB,(OUTPUT))', 'BAL   14,SAMEMEM'):
    assert any(need in l for l in asm), need
assert sum('ESTAE 0' in l for l in asm) == 1 and sum('BAL   14,SAMEMEM' in l for l in asm) == 2
clist = clist_text('HERC01.PACMAN')
assert all(len(l) <= 72 for l in clist.splitlines())
block = hs_clist_block('HERC01.PACMAN')
assert block[0] == 'IF &W = A THEN DO' and "&SYSDSN('HERC01.PACMAN.DATA') = OK" in block[1] and \
    'DUMMY' in block[3] and block[-1] == 'END' and 'IF &W = A THEN FREE F(PACHS)' in clist.splitlines()
alloc = subprocess.run([sys.executable, str(R / 'tools/make_deck.py'), 'ALLOC', '--out', '/dev/stdout'],
                       capture_output=True, text=True, check=True).stdout
assert 'HERC01.PACMAN.DATA,DISP=(NEW,CATLG,DELETE)' in alloc and 'BLKSIZE=80' in alloc
print('HS local checks PASS')


# 2. expected outputs ----------------------------------------------------------------------------------------------
def model_runs():
    """[(step, base output or None for TSD, hs lines)] in listing order, and the final model PDS."""
    pds = H.Pds({'HS9': [H.record(9999999, 99)], 'BAD': ['XYZZY NOT A SCORE', 'SECOND JUNK RECORD'], 'EMPTY': []})
    full = H.Pds(full=True)
    res = []
    for step, kind, d, c, st, ddk in HS_RUNS:
        start = L.parse_start(st)
        cs = cards(d, c)
        if kind == 'B':
            base = L.simulate(cs, start=start)
        elif kind == 'R':
            base = L.rt_simulate(cs, start)
        elif kind == 'C':
            base = oracle()[0][c]
        else:
            base = None
        if kind == 'C':
            hs = H.end_lines(pds, ('M', ddk[2:]), 0, 0, 1, arcade=False)
        else:
            score, level = H.final(base) if base else TSD_FINAL[kind]
            store = full if ddk.startswith('F:') else pds
            dd = ('M', ddk[2:]) if ddk[:2] in ('M:', 'F:') else ddk
            hs = H.end_lines(store, dd, score, level, start)
        res.append((step, kind, base, hs))
    for i, (c, st, m) in enumerate(HS_TSO, 1):
        cs = cards('gpcases', c)
        ai, n, _ = L.parse_config(cs[:1])
        base = L.simulate(cs[1:], prompts=True, cfg=(ai, n), redraw=True, start=L.parse_start(st))
        res.append((f'HTSO{i}', 'S', base, H.end_lines(pds, ('M', m), *H.final(base), L.parse_start(st))))
    return res, pds


TSD_FINAL = {'T': H.final(L.simulate(cards(*HS_TSD_TURN[:2]), start=1)),
             'Q': H.final(L.rt_simulate(cards(*HS_TSD_RT[:2]), 1))}
RUNS, PDS = model_runs()


def rp_streams(kind):
    """MVS-RP: the TSD streams of HG2 (T) / HG3 (Q) from the models; their members are fresh (missing): Z."""
    import ref_gx_screen as gx
    import ref_rt
    from ref_rp import bells
    from ref_snap import Log
    mem = [r[5][2:] for r in HS_RUNS if r[1] == kind][0]
    assert all(r[5] != 'M:' + mem for r in HS_RUNS if r[1] != kind), mem      # nothing else touches it first
    log = Log()
    if kind == 'T':
        d, c, h, a, r, gl, sc, cv, snd, st = HS_TSD_TURN
        fs = gx.frames(c, h == 'Y', a == 'Y', r, gl, sc, cv, snap=log, mk=lambda ai, n: L.Level(ai, n, 'T', 1), d=d,
                       hs=('Z', 0, 1))
    else:
        d, c, cv, snd, st = HS_TSD_RT
        _, fs = ref_rt.tsd(cards(d, c), cv, snap=log, mk_game=lambda ai, n: L.Level(ai, n, 'R', 1),
                           mk_ctl=L.LevelRT, hs=('Z', 0, 1))
    return bells(fs, log, snd)[0]


def tsd_run(t, j, nend):
    """One TSD dry run from line j: (streams, end lines, next j) - the parsing of tests/test_gp2.py tsd_check."""
    streams = []
    while t[j].rstrip() not in ('WIN', 'LOST', 'QUIT', 'EOF'):
        m = re.match(r'TSD FRAME LEN(\d{4})$', t[j])
        j += 1
        if not m:
            continue
        hexs = ''
        while t[j].startswith('TSD ') and not t[j].startswith('TSD FRAME'):
            hexs += t[j][4:].strip()
            j += 1
        data = bytes.fromhex(hexs)
        assert len(data) == int(m.group(1))
        streams.append(data)
    return streams, [l.rstrip() for l in t[j:j + nend]], j + nend


# 3. the Hercules listings -----------------------------------------------------------------------------------------
if not ARGS:
    sys.exit(0)
lines = Path(ARGS[0]).read_text().splitlines()
deck = build('HS', 'HERC01.PACMAN')
nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', deck, re.M))
rcs = re.findall(r'PACBLDHS\s+(\w+)\s+\S+\s+RC= (\d{4})', '\n'.join(lines))
assert len(rcs) == nsteps, (nsteps, len(rcs))
assert [s for s, r in rcs if r != '0000'] == ['HSFILL'] and dict(rcs)['HSFILL'] == '0012', [x for x in rcs if x[1] != '0000']
assert not [l for l in lines if re.search(r'IKF\d{4}I-[WCE]', l)], 'compiler warnings'
# MVS-G8 (D43): a run-only deck (PACMAN_RUNONLY=1) assembles nothing; the three assemblies are in the REL20 listing
assert sum(l.strip() == 'HIGHEST SEVERITY WAS    0' for l in lines) == (0 if os.environ.get('PACMAN_RUNONLY') == '1' else 3)
assert any('IEB813I OUTPUT DIRECTORY FULL' in l for l in lines)
t = [l.rstrip() for l in lines[lines.index(HS_MARK) + 1:]]
gp23 = None
if len(ARGS) > 1:
    g = [l.rstrip() for l in Path(ARGS[1]).read_text().splitlines()]
    g = g[g.index(GP23_MARK) + 1:]
    j, gp23 = 0, {}
    for run in GP23_TURN + GP23_RT:
        streams, ends, j = tsd_run(g, j, 7 if run in GP23_TURN else 8)
        gp23[run] = (streams, ends)
j, nlines, nstreams = 0, 0, 0
for step, kind, base, hs in RUNS:
    if kind in ('T', 'Q'):
        streams, ends, j = tsd_run(t, j, (7 if kind == 'T' else 8) + len(hs))
        if gp23 is not None and os.environ['PACMAN_LATER_PHASE'] != 'HS':
            # MVS-RP (D39) and later: the ARCADE screens carry the RP decorations and the HUD high score, so the
            # streams come from the models with this run's high-score state (a fresh member: Z) instead of GP23
            ws = rp_streams(kind)
            we = gp23[HS_TSD_TURN if kind == 'T' else HS_TSD_RT][1]
            assert streams == ws and ends == we + hs, (step, len(streams), len(ws), ends, we + hs)
        elif gp23 is not None:
            ws, we = gp23[HS_TSD_TURN if kind == 'T' else HS_TSD_RT]
            assert streams == ws and ends == we + hs, (step, len(streams), len(ws), ends, we + hs)
        else:
            assert ends[-len(hs):] == hs, (step, ends, hs)
        nstreams += len(streams)
        continue
    j = t.index(BANNER, j)
    w = [l.rstrip() for l in base] + hs
    got = t[j:j + len(w)]
    assert got == w, (step, next(((x, a, b) for x, (a, b) in enumerate(zip(got, w)) if a != b), (len(got), len(w))))
    nxt = t[j + len(w)] if j + len(w) < len(t) else ''
    assert not nxt.startswith(('HIGH SCORE', 'NEW HIGH', 'START LEVEL')), (step, nxt)
    j += len(w)
    nlines += len(w)
# member prints (HS_PRINT order), after the runs: exactly one record each, = the model
# (the record follows the IEBGENER message after a form feed, so it is a line of its own here)
prints = [l for l in t[j:] if re.fullmatch(r'\d{7} PACHS001 \d{3}', l)]
assert prints == [PDS.members[m][0].rstrip() for m in HS_PRINT], prints
assert all(len(PDS.members[m]) == 1 for m in HS_PRINT)
assert not any('SECOND JUNK' in l or 'XYZZY' in l for l in t), 'the malformed member was not healed'
mem = t.index('--MEMBERS--', j)
listed = []
for l in t[mem + 1:]:
    if not re.fullmatch(r'  [A-Z@#$][A-Z0-9@#$]{0,7}', l):
        break
    listed.append(l.strip())
assert sorted(listed) == sorted(set(PDS.members) | {'HSCLY', 'HSCLN'}), listed
assert 'HS8' not in listed
# the CLIST block: DATA present -> the member allocated SHR; DATA missing -> DUMMY (NULLFILE); the CLIST goes on
PFX = os.environ.get('PACMAN_PREFIX', 'HERC01.PACMAN')       # MVS-G8 (D43): the R20 rebuild runs under its own prefix
cl = t[t.index(f"  EXEC '{PFX}.HSTEST(HSCLY)'", j):mem]
i1 = cl.index(f'{PFX}.HSCL.DATA(HISCORE)')
assert cl[i1 + 1].split() == ['PACHS', 'KEEP'] and cl.count('HSCL END') == 2
assert any(l.startswith(f'IDC0550I ENTRY (A) {PFX}.HSCL.DATA DELETED') for l in cl)
assert cl.index('NULLFILE  PACHS') > i1 and not any('IKJ56' in l for l in cl), cl
print('MVS-HS HS.2 PASS:', len(rcs), 'steps (HSFILL RC 0012, the rest RC 0000);', len(RUNS), 'runs = model + HS lines (',
      nlines, 'text lines,', nstreams, 'TSD streams', ('= RP models)' if LATER else '= GP23)') if gp23 is not None else 'not compared)', ';',
      len(prints), 'member prints = model; CLIST block both paths')
if len(ARGS) > 2:
    r = subprocess.run([sys.executable, str(R / 'tests/test_gp2.py'), ARGS[2], ARGS[1]], capture_output=True, text=True,
                       env=dict(os.environ, PACMAN_LATER_PHASE='HS'))
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    print('GP2 regression (test_gp2 GP2 + GP23, PACMAN_LATER_PHASE=HS):', r.stdout.strip().splitlines()[-1][:120])
