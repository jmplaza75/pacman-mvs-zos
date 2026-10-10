#!/usr/bin/env python3
"""MVS-RT RT2 acceptance (docs/RT-REALTIME.md, D33).
Local:    the core differs from mvs-gs only by the authorised REQ-STEP selector; PACFSIO = mvs-gs + the POLL service only;
          PACTSO keeps CLS / WAIT byte-identical; the independent model (tests/ref_rt.py) shows every required REALTIME
          behaviour on the cases in tests/rtcases.
Hercules: test_rt.py RT-LISTING (deck RT = the whole GX deck + PACRT + 12 batch and 6 TSD REALTIME runs)
  - every step RC 0000, no compiler warnings;
  - the GX part (TURN regression, 1.0-MVS oracle, 61 GS/GX TSD runs, PACQRY) passes tests/test_gx.py unchanged;
  - every batch REALTIME run equals ref_rt.simulate line for line;
  - every TSD REALTIME run equals ref_rt streams byte for byte and its end lines; every quantum sends exactly one
    stream with WCC restore, including quanta where nothing changed (C2 28 00 00).
"""
import difflib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tools'))
import ref_rt  # noqa: E402
from make_deck import RT_BAT, RT_TSD, build  # noqa: E402
from test_g0 import BANNER  # noqa: E402


def git_show(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:./{path}'], cwd=R, capture_output=True, text=True,
                          check=True).stdout.splitlines()


def cards(case):
    return (R / f'tests/rtcases/{case}.txt').read_text().splitlines()


# 1. core: only the REQ-STEP selector was added to PACGAME (authorised in docs/CORE_CHANGES.md)
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
old, new = git_show('mvs-gs', 'src/cobol/PACGAME.cob'), (R / 'src/cobol/PACGAME.cob').read_text().splitlines()
diff = [d for d in difflib.ndiff(old, new) if d[:2] in ('+ ', '- ')]
assert all(d[0] == '+' for d in diff) and len(diff) == 9, diff
for f in ('src/cobol/PACMAP.cob', 'src/cobol/PACAI.cob', 'src/copy/PACSTATE.cpy', 'src/copy/PACMREQ.cpy'):
    assert git_show('mvs-gs', f) == (R / f).read_text().splitlines(), f
old_req = git_show('mvs-gs', 'src/copy/PACREQ.cpy')
assert (R / 'src/copy/PACREQ.cpy').read_text().splitlines()[:len(old_req)] == old_req, 'PACREQ must grow append-only'

# 2. PACFSIO: mvs-gs + POLL only; PACTSO: CLS / WAIT unchanged
old, new = git_show('mvs-gs', 'src/asm/PACFSIO.asm'), (R / 'src/asm/PACFSIO.asm').read_text().splitlines()
k, extra = 0, []
for line in new:
    if k < len(old) and line == old[k]:
        k += 1
    else:
        extra.append(line)
assert k == len(old), 'a PACFSIO line was changed or removed'
code = [l for l in extra if not l.startswith('*')]
assert sum('TGET' in l for l in code) == 1 and any('NOWAIT' in l for l in code) and not any('STIMER' in l for l in code)
assert not any('TPUT' in l for l in code) and len(code) == 15, code
old, new = git_show('mvs-gs', 'src/asm/PACTSO.asm'), (R / 'src/asm/PACTSO.asm').read_text().splitlines()
assert [l for l in old if l not in new and not l.startswith('*')] == [], 'a PACTSO code line was removed'

# PACRT is terminal independent (the GAME/MAP/AI rules of tests/test_mvs7.py)
src = '\n'.join(l for l in (R / 'src/cobol/PACRT.cob').read_text().splitlines() if l[6:7] != '*')
assert not re.search(r'\b(DISPLAY|ACCEPT|READ|OPEN|SELECT|WRITE|SYSIN|SYSOUT|TSO|ISPF|ZOWE|HERCULES|PACPLAT|PACFSIO|'
                     r'PACTSO|PACDISP|PACSCR|PACINPT)\b', src), 'PACRT must not touch terminal or host'

# 3. the model shows every required REALTIME behaviour
def q(lines, n):
    return next(l for l in lines if l.startswith(f'Q{n:07d} '))


out = {c: ref_rt.simulate(cards(c)) for c in RT_BAT}
o = out['RTLINE']
ks = [l[23] for l in o if re.match(r'Q\d{7} ', l)]
assert ks[:7] == list('PBBBBPB') and 'X=09' in q(o, 7) and 'X=09' in q(o, 12) and set(ks[7:]) <= {'G', '-'}
assert 'R=D T=2' in q(out['RTCORNER'], 3) and 'C=D' in q(out['RTCORNER'], 4) and 'Y=03' in q(out['RTCORNER'], 4)
assert 'R=U T=2' in q(out['RTTTL'], 2) and 'R=U T=1' in q(out['RTTTL'], 3) and 'R=  T=0' in q(out['RTTTL'], 4)
assert 'C=L' in q(out['RTREV'], 4) and 'X=04' in q(out['RTREV'], 4)
assert 'IN=DL ' in q(out['RTMULTI'], 2) and 'C=L' in q(out['RTMULTI'], 2) and 'IN=UDLR ' in q(out['RTMULTI'], 5) \
    and 'C=R' in q(out['RTMULTI'], 5)
o = out['RTSTILL']
death = next(l for l in o if re.match(r'Q\d{7} ', l) and 'V=2' in l)
assert ' K=G C=  ' in death and ' X=02 Y=02 ' in death
nd = int(death[1:8])
assert all(' K=F ' in q(o, nd + i) for i in range(1, 11)) and ' K=F ' not in q(o, nd + 11) and o[-5] == 'LOST'
o = out['RTPAUSE']
assert 'IN=PxP ' in q(o, 4) and 'INVALID COMMAND x' in o and 'IN=PP ' in q(o, 9) and 'IN=* ' in q(o, 7) and o[-5] == 'QUIT'
assert out['RTPRE'][-5] == 'QUIT' and 'IN=X*PR ' in q(out['RTPRE'], 1)
assert out['RTLONG'][-4:] == ['TURNS 102', 'SCORE 0020', 'LIVES 3', 'QUANTA 0001102']
assert out['RTWIN'][-5:-1] == ['WIN', 'TURNS 183', 'SCORE 1000', 'LIVES 3']
for case, end, lives in (('RTEDGE', 'WIN', '1'), ('RTEDGE0', 'LOST', '0')):
    o = out[case]
    last = [l for l in o if re.match(r'Q\d{7} ', l)][-2:]
    assert o[-5] == end and o[-2] == f'LIVES {lives}' and ' L=000 ' in last[1] and ' L=001 ' in last[0] \
        and int(last[1][last[1].index(' V=') + 3]) < int(last[0][last[0].index(' V=') + 3]), (case, last)
tsd = {(c, cv): ref_rt.tsd(cards(c), cv) for c, cv in RT_TSD}
minimal = sum(f == bytes([0xC2, 0x28, 0x00, 0x00]) for _, fs in tsd.values() for f in fs)
assert minimal > 0 and all(f[0] in (0xC2, 0xC3) for _, fs in tsd.values() for f in fs)
assert max(len(f) for _, fs in tsd.values() for f in fs) <= 2048
# RT3: every installed CLIST line (prefix substituted) must end by column 72 (73-80 = sequence numbers in TSO;
# a 73-column CALL line lost its closing quote: ENDING QUOTE ASSUMED, live 2026-10-10)
for clist in [R / 'src/clist/PACMAN.clist'] + sorted((R / 'src/probe').glob('RT*.clist')):
    for n, line in enumerate(clist.read_text().replace('@@PREFIX@@', 'HERC01.PACMAN').splitlines(), 1):
        assert len(line) <= 72 or line.lstrip().startswith('/*'), (clist.name, n, len(line))

# RT3 pause: PF9 (X'F9' = 249) is a pause AID; the PAUSED banner is on every pause screen and gone after the resume
inp = (R / 'src/cobol/PACINPT.cob').read_text()
assert re.search(r"IF WS-V = 249\n\s+MOVE 'P' TO RT-C\n\s+PERFORM RT-CHAR\.", inp), 'PF9 must map to pause'
launcher = (R / 'tools/c3270_rt.sh').read_text()
assert '<Key>UP: PF(7)' in launcher and '<Key>DOWN: PF(8)' in launcher and '<Key>LEFT: PF(10)' in launcher \
    and '<Key>RIGHT: PF(11)' in launcher and 'c3270.keymap.pacgame' in launcher and '<Key>p: PF(9)' in launcher
paused = ' PAUSED '.encode('cp037')
ps = tsd[('RTPAUSE', 'W')][1]
idx = [k for k, f in enumerate(ps) if paused in f]
assert len(idx) >= 2 and all(ps[k][0] == 0xC3 for k in idx) and paused not in ps[idx[-1] + 1] and \
    ps[idx[-1] + 1][0] == 0xC2, idx
print('local checks PASS:', len(RT_BAT), 'batch cases,', len(RT_TSD), 'TSD runs,',
      sum(len(fs) for _, fs in tsd.values()), 'model streams,', minimal, 'restore-only streams')

if len(sys.argv) == 2:
    lines = Path(sys.argv[1]).read_text().splitlines()
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', build('RT', 'HERC01.PACMAN'), re.M))
    rcs = re.findall(r'PACBLDRT\s+(\w+)\s+(?:IEBGENER|IKFCBL00|IFOX00|IEWL|PACMAIN|PACQRYT)\s+RC= (\d{4})', '\n'.join(lines))
    assert len(rcs) == nsteps and all(r == '0000' for _, r in rcs), (nsteps, len(rcs), [x for x in rcs if x[1] != '0000'])
    assert not [l for l in lines if re.search(r'IKF\d{4}I-[WCE]', l)], 'compiler warnings'
    # the GX part: everything up to the first banner after the PACQRY lines, with the RT-only steps removed
    lastq = max(i for i, l in enumerate(lines) if l.startswith('QRY ') and 'LEN=' in l)
    cut = next(i for i in range(lastq, len(lines)) if lines[i] == BANNER)
    rt_only = {'SRC10', 'COB10'} | {f'RTB{i}' for i in range(1, len(RT_BAT) + 1)} | \
        {f'RTT{i}' for i in range(1, len(RT_TSD) + 1)}
    head = []
    for l in lines[:cut]:
        m = re.search(r'PACBLDRT\s+(\w+)\s+\S+\s+RC=', l)
        if m and m.group(1) in rt_only:
            continue
        head.append(l.replace('PACBLDRT', 'PACBLDGX'))
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as tf:
        tf.write('\n'.join(head) + '\n')
    gx = subprocess.run([sys.executable, str(R / 'tests/test_gx.py'), tf.name], capture_output=True, text=True)
    assert gx.returncode == 0, gx.stdout[-2000:] + gx.stderr[-3000:]
    tail = lines[cut:]
    # batch REALTIME blocks: banner .. QUANTA
    starts = [i for i, l in enumerate(tail) if l == BANNER]
    assert len(starts) == len(RT_BAT), len(starts)
    for case, s in zip(RT_BAT, starts):
        e = next(j for j in range(s, len(tail)) if tail[j].startswith('QUANTA '))
        got = [l.rstrip() for l in tail[s:e + 1]]
        want = [l.rstrip() for l in out[case]]
        assert got == want, (case, next((x, a, b) for x, (a, b) in enumerate(zip(got, want)) if a != b) if
                             any(a != b for a, b in zip(got, want)) else (len(got), len(want)))
    # TSD REALTIME runs: streams then end lines, run by run
    j = next(j for j in range(starts[-1], len(tail)) if tail[j].startswith('QUANTA ')) + 1
    nstreams = 0
    for case, cv in RT_TSD:
        streams = []
        while not tail[j].startswith('QUANTA '):
            m = re.match(r'TSD FRAME LEN(\d{4})$', tail[j])
            if not m:
                j += 1
                continue
            n, hexs, j = int(m.group(1)), '', j + 1
            while tail[j].startswith('TSD ') and not tail[j].startswith('TSD FRAME'):
                hexs += tail[j][4:].strip()
                j += 1
            data = bytes.fromhex(hexs)
            assert len(data) == n
            streams.append(data)
        ends = [l.rstrip() for l in tail[j - 4:j + 1]]
        want_end, want = tsd[(case, cv)]
        assert ends == want_end[-5:], (case, ends, want_end[-5:])
        assert len(streams) == len(want), (case, len(streams), len(want))
        for x, (a, b) in enumerate(zip(streams, want)):
            assert a == b, (case, x, next((y for y in range(min(len(a), len(b))) if a[y] != b[y]), min(len(a), len(b))))
        nstreams += len(streams)
        j += 1
    print('MVS-RT RT2 PASS:', len(rcs), 'steps RC 0000; GX regression:', gx.stdout.strip().splitlines()[-1][:60], '...;',
          len(RT_BAT), 'batch REALTIME runs = model;', nstreams, 'TSD REALTIME streams = model')
