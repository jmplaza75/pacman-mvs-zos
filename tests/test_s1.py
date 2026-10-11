#!/usr/bin/env python3
"""MVS-S1 acceptance: SOUND(AUTO|YES|NO), the 3270 alarm on start, death and win (probe E15,
docs/evidence/s1-e15-alarm.md).
Local:    only the display/platform side changed since mvs-rt (PACMAIN PARM column 20, PACDISP SET-BELL, PACPLAT
          SET-ALARM, PACREQ +2 fields, CLIST SOUND); the core, PACRT, PACSCR, PACINPT, PACFSIO and PACTSO are untouched.
          The bell rule below (independent of the COBOL) applied to the screen models (ref_snap hooks).
Hercules: test_s1.py S1-LISTING (deck S1 = the whole RT deck, a marker step, then the SOUND runs)
  - every step RC 0000, no compiler warnings;
  - everything before the marker passes tests/test_rt.py unchanged (SOUND absent = N: TURN/GX/RT regression, oracle);
  - every SOUND run equals the model with the bells: the same streams, the WCC alarm bit X'04' on exactly the
    expected ones, plus one bell-only write (C6 28 00 00) when a game ends without an end screen;
  - BAT TURN, BAT REALTIME and TSO line mode with SOUND Y equal the 1.0-MVS oracle / the model (no sound there).
Bell rule: the first screen (start); any screen sent with fewer lives than the previous one (death, the last too);
the first screen sent after the win. One alarm per screen (a death and the win in one move ring once).
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
import ref_gx_screen as gx  # noqa: E402
import ref_rt  # noqa: E402
from make_deck import S1_MARK, S1_RT, S1_SILENT, S1_TURN, build  # noqa: E402
from ref_snap import Log  # noqa: E402
from test_g0 import BANNER, blocks, oracle  # noqa: E402

BELL_ONLY = bytes([0xC2, 0x28, 0x00, 0x00])
S1_ONLY = re.compile(r'S1(MARK|T\d+|R\d+|S\d+)$')


def git_show(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:./{path}'], cwd=R, capture_output=True, text=True,
                          check=True).stdout.splitlines()


def alarm(f):
    return bytes([f[0] | 0x04]) + f[1:]


def with_bells(frames, log, sound):
    """The streams PACMAN must send with SOUND sound, from the model streams and their (lives, won) snapshots."""
    if sound == 'N':
        return list(frames), []
    st = {'last': None, 'won': False}

    def ring(snap):
        lives, won = snap
        b = st['last'] is None or lives < st['last'] or (won and not st['won'])
        st['won'] = st['won'] or won
        st['last'] = lives
        return b
    out, rung = [], []
    assert len(frames) == len(log)
    for k, (f, snap) in enumerate(zip(frames, log)):
        if ring(snap):
            out.append(alarm(f))
            rung.append(k)
        else:
            out.append(f)
    if ring(log.state()):                          # the end of a game without an end screen
        out.append(alarm(BELL_ONLY))
        rung.append(len(frames))
    return out, rung


def turn_model(run):
    c, h, a, r, gl, sc, cv, snd = run
    log = Log()
    fs = gx.frames(c, h == 'Y', a == 'Y', r, gl, sc, cv, snap=log)
    return with_bells(fs, log, snd)


def rt_model(run):
    c, cv, snd = run
    log = Log()
    end, fs = ref_rt.tsd((R / f'tests/rtcases/{c}.txt').read_text().splitlines(), cv, snap=log)
    return end, with_bells(fs, log, snd)


# 1. only the display/platform side changed
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
# MVS-GP1: PACMAN_LATER_PHASE (set by a later phase's test that runs this file as a regression) skips ONLY the
# source-equality / diff-set pins against mvs-rt, which authorised later changes make intentionally false; the later
# test checks its own diff set. Structural guards (PACTSO fall-through, PACREQ append-only) and every behaviour,
# listing and oracle check below always run.
LATER = os.environ.get('PACMAN_LATER_PHASE')
if not LATER:
    for f in ('src/cobol/PACGAME.cob', 'src/cobol/PACMAP.cob', 'src/cobol/PACAI.cob', 'src/cobol/PACRT.cob',
              'src/cobol/PACSCR.cob', 'src/cobol/PACINPT.cob', 'src/cobol/PACQRY.cob', 'src/copy/PACSTATE.cpy',
              'src/copy/PACMREQ.cpy', 'src/copy/PACPAL.cpy', 'src/copy/PACDS.cpy', 'src/asm/PACFSIO.asm'):
        assert git_show('mvs-rt', f) == (R / f).read_text().splitlines(), f
# PACTSO: mvs-rt + ONE line. S1 live 0C4 (reason 4) at the end of every scaled game: since RT2 the WAIT path (PAUSE)
# fell through into DOTIME, which took a third parameter from 8(R1) (garbage after STIMER, WAIT has two) and stored
# the clock there. Batch cannot reach PAUSE (not TSO: WAIT ends before it), so the check is static.
old, new = git_show('mvs-rt', 'src/asm/PACTSO.asm'), (R / 'src/asm/PACTSO.asm').read_text().splitlines()
added = [d[2:] for d in difflib.ndiff(old, new) if d[:2] == '+ ']
if not LATER:
    assert [d for d in difflib.ndiff(old, new) if d[:2] == '- '] == [] and len(added) == 1 and added[0].split()[:2] == ['B', 'DONE']
code = [l for l in new if l.strip() and not l.startswith('*')]
k = next(i for i, l in enumerate(code) if l.startswith('PAUSE '))
assert code[k + 1].split()[0] == 'STIMER' and code[k + 2].split()[:2] == ['SR', '4,4'] and \
    code[k + 3].split()[:2] == ['B', 'DONE'], code[k:k + 4]
# every PACTSO block that ends at a label other than its intended successor ends with an unconditional branch
for i, l in enumerate(code[1:], 1):
    if l[:1] != ' ' and l.split()[0] in ('DOTIME', 'DODLWT', 'LATE', 'DONE', 'NOWMS', 'SAVE'):
        prev = code[i - 1].split()
        assert prev[0] in ('B', 'BR') or (prev[0] == 'DS' and l.split()[0] == 'SAVE') or code[i - 1][:1] != ' ' \
            or l.split()[0] == 'HAVET0', (l, code[i - 1])
old_req, new_req = git_show('mvs-rt', 'src/copy/PACREQ.cpy'), (R / 'src/copy/PACREQ.cpy').read_text().splitlines()
assert new_req[:len(old_req)] == old_req, 'PACREQ must grow append-only'
fields = [l.split()[1] for l in new_req[len(old_req):] if l[6:7] != '*']
assert fields[:2] == ['REQ-SOUND', 'REQ-BELL'] and (LATER or len(fields) == 2), fields
if not LATER:
    for name in ('PACMAIN', 'PACDISP', 'PACPLAT'):       # added lines only, nothing removed
        old, new = git_show('mvs-rt', f'src/cobol/{name}.cob'), (R / f'src/cobol/{name}.cob').read_text().splitlines()
        removed = [d for d in difflib.ndiff(old, new) if d[:2] == '- ']
        allowed = {'PACDISP': 4, 'PACMAIN': 0, 'PACPLAT': 0}[name]  # PACDISP: one comment re-wrapped, SCR-ENDS reshaped
        assert len(removed) <= allowed, (name, removed)
disp = (R / 'src/cobol/PACDISP.cob').read_text()
sb = disp[disp.index('       SET-BELL.'):]
sb = sb[:sb.index('\n       ', 20) if re.search(r'\n       [A-Z]', sb[20:]) else len(sb)]
assert set(re.findall(r'TO (\S+?)\.?\s', sb)) <= {'REQ-BELL', 'SB-WON', 'SB-SENT', 'SB-LIVES'}, sb
for n, line in enumerate((R / 'src/clist/PACMAN.clist').read_text().replace('@@PREFIX@@', 'HERC01.PACMAN')
                         .splitlines(), 1):
    assert len(line) <= 72 or line.lstrip().startswith('/*'), ('PACMAN.clist', n, len(line))
clist = (R / 'src/clist/PACMAN.clist').read_text()
assert 'SOUND(AUTO)' in clist and ('&V&Y&U)' in clist or LATER)   # the PARM order is pinned by the later test

# 2. the model with the bells
turn = [turn_model(x) for x in S1_TURN]
rt = [rt_model(x) for x in S1_RT]
rungs = {x: r for x, (_, r) in zip(S1_TURN, turn)}
n = {x: len(f) for x, (f, _) in zip(S1_TURN, turn)}
d1, l0, w0, e3, d1n, l0n, w0n, e1n, d1a, d1no = S1_TURN
assert rungs[d1][0] == 0 and len(rungs[d1]) == 2                      # start + one death (then QUIT: silent end screen)
assert len(rungs[l0]) == 4 and rungs[l0][-1] == n[l0] - 1             # start + 3 deaths, the last on the LOST screen
assert rungs[w0] == [0, n[w0] - 1]                                    # start + the WIN end screen
assert rungs[e3] == [0, n[e3] - 1]                                    # last pellet + hit in one move: ONE bell
assert len(rungs[d1n]) == 2 and turn[4][0][-1] != alarm(BELL_ONLY)    # not scaled, QUIT: no bell-only write
assert turn[5][0][-1] == alarm(BELL_ONLY) and len(rungs[l0n]) == 4    # not scaled, LOST: bell-only write at the end
assert turn[6][0][-1] == alarm(BELL_ONLY) and rungs[w0n] == [0, n[w0n] - 1]
assert turn[7][0][-1] == alarm(BELL_ONLY) and rungs[e1n][-1] == n[e1n] - 1
assert turn[8] == turn[0] and turn[9][1] == [] and turn[9][0] == gx.frames('DIE1', True, True, 'P', 'G', '4', 'W')
assert all(f[0] in (0xC6, 0xC7) for fs, r in turn + [x for _, x in rt] for k, f in enumerate(fs) if k in r)
rt_rung = {x[0]: r for x, (_, (_, r)) in zip(S1_RT, rt)}
rt_n = {x[0]: len(f) for x, (_, (f, _)) in zip(S1_RT, rt)}
assert len(rt_rung['RTSTILL']) == 4 and len(rt_rung['RTEDGE0']) == 4 and rt_rung['RTEDGE0'][-1] == rt_n['RTEDGE0'] - 2
# RTEDGE: a death, then the last pellet and a hit in the same quantum (WIN, 1 life): ONE bell on that frame
assert len(rt_rung['RTEDGE']) == 3 and rt_rung['RTEDGE'][-1] == rt_n['RTEDGE'] - 2
assert len(rt_rung['RTWIN']) == 2 and rt_rung['RTPAUSE'] == [0]
print('local checks PASS:', len(S1_TURN), 'TURN and', len(S1_RT), 'REALTIME SOUND runs,',
      sum(len(r) for _, r in turn) + sum(len(r) for _, (_, r) in rt), 'bells in',
      sum(len(f) for f, _ in turn) + sum(len(f) for _, (f, _) in rt), 'model streams')

if len(sys.argv) == 2:
    lines = Path(sys.argv[1]).read_text().splitlines()
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', build('S1', 'HERC01.PACMAN'), re.M))
    rcs = re.findall(r'PACBLDS1\s+(\w+)\s+(?:IEBGENER|IKFCBL00|IFOX00|IEWL|PACMAIN|PACQRYT|PACTSOT)\s+RC= (\d{4})',
                     '\n'.join(lines))
    assert len(rcs) == nsteps and all(r == '0000' for _, r in rcs), (nsteps, len(rcs), [x for x in rcs if x[1] != '0000'])
    assert not [l for l in lines if re.search(r'IKF\d{4}I-[WCE]', l)], 'compiler warnings'
    cut = lines.index(S1_MARK)
    head = []
    for l in lines[:cut]:
        m = re.search(r'PACBLDS1\s+(\w+)\s+\S+\s+RC=', l)
        if m and S1_ONLY.match(m.group(1)):
            continue
        head.append(l.replace('PACBLDS1', 'PACBLDRT'))
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as tf:
        tf.write('\n'.join(head) + '\n')
    rtt = subprocess.run([sys.executable, str(R / 'tests/test_rt.py'), tf.name], capture_output=True, text=True)
    assert rtt.returncode == 0, rtt.stdout[-2000:] + rtt.stderr[-3000:]
    tail, j = lines[cut + 1:], 0

    def tsd_run(quanta):
        global j
        streams = []
        while tail[j] not in ('WIN', 'LOST', 'QUIT', 'EOF'):
            m = re.match(r'TSD FRAME LEN(\d{4})$', tail[j])
            j += 1
            if not m:
                continue
            hexs = ''
            while tail[j].startswith('TSD ') and not tail[j].startswith('TSD FRAME'):
                hexs += tail[j][4:].strip()
                j += 1
            data = bytes.fromhex(hexs)
            assert len(data) == int(m.group(1))
            streams.append(data)
        ends = [l.rstrip() for l in tail[j:j + (5 if quanta else 4)]]
        j += 5 if quanta else 4
        return streams, ends

    def same(case, got, want):
        assert len(got) == len(want), (case, len(got), len(want))
        for x, (a, b) in enumerate(zip(got, want)):
            assert a == b, (case, x, next((y for y in range(min(len(a), len(b))) if a[y] != b[y]), min(len(a), len(b))))

    nb = ns = 0
    for run, (want, rung) in zip(S1_TURN, turn):
        got, ends = tsd_run(False)
        same(run, got, want)
        from ref_mvs6 import simulate
        assert ends == simulate((R / f'tests/cases/{run[0]}.txt').read_text().splitlines())[-4:], (run, ends)
        nb, ns = nb + len(rung), ns + len(got)
    for run, (end, (want, rung)) in zip(S1_RT, rt):
        got, ends = tsd_run(True)
        same(run, got, want)
        assert ends == end[-5:], (run, ends, end[-5:])
        nb, ns = nb + len(rung), ns + len(got)
    batch_or, tso_or = oracle()
    rest = [l.rstrip() for l in tail[j:]]
    blk = blocks(rest, BANNER)
    assert len(blk) == 3, len(blk)
    assert blk[0] == batch_or['LOST0'], 'BAT TURN with SOUND Y differs from the 1.0-MVS oracle'
    rtb = [l.rstrip() for l in ref_rt.simulate((R / 'tests/rtcases/RTSTILL.txt').read_text().splitlines())]
    k = rest.index(BANNER, rest.index(BANNER) + 1)
    assert rest[k:k + len(rtb)] == rtb, 'BAT REALTIME with SOUND Y differs from the model'
    assert blk[2] == tso_or['DIE1'], 'TSO line mode with SOUND Y differs from the 1.0-MVS oracle'
    assert not any(l.startswith('TSD ') for l in rest), 'a silent run sent a screen'
    print('MVS-S1 PASS:', len(rcs), 'steps RC 0000; RT regression:', rtt.stdout.strip().splitlines()[-1][:50], '...;',
          len(S1_TURN) + len(S1_RT), 'SOUND runs =', ns, 'model streams with', nb, 'bells;',
          len(S1_SILENT), 'silent runs = oracle/model')
