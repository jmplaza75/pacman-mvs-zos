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
from make_deck import RP_MARK, RP_RT, RP_SEED, RP_TURN, build  # noqa: E402
import subprocess  # noqa: E402


def git_show(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:./{path}'], cwd=R, capture_output=True, text=True,
                          check=True).stdout.splitlines()


def src(path):
    return (R / path).read_text().splitlines()


# 1. sources -----------------------------------------------------------------------------------------------------------
BASE = 'mvs-hs'
for f in ('src/cobol/PACGAME.cob', 'src/cobol/PACMAP.cob', 'src/cobol/PACAI.cob', 'src/copy/PACARC.cpy',
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
print('RP sources PASS (core frozen, append-only copies, ARCADE-only RP code, D40 read loop)')


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


# 3. the Hercules listing ----------------------------------------------------------------------------------------------
def listing_check(path):
    lines = Path(path).read_text().splitlines()
    deck = build('RP', 'HERC01.PACMAN')
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', deck, re.M))
    rcs = re.findall(r'PACBLDRP\s+(\w+)\s+(?:IEBGENER|IEBUPDTE|IEFBR14|IKFCBL00|IFOX00|IEWL|PACRPD|PACQRYT)\s+RC= (\d{4})',
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


if ARGS:
    listing_check(ARGS[0])
    d40_check(ARGS[0])
