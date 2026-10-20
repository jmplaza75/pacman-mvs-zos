#!/usr/bin/env python3
"""ZOS-2 local checks of the z/OS tooling (no z/OS access):
1. tools/zowe/zos_listing.py: in-stream PROC definitions are not steps; '++' expansions give <step> <procstep>.
2. tools/zowe/zos_equiv.py: a simulated z/OS job built from the independent models (tests/expected/MVS6-*) passes
   against oracle JOB 315; every single mutation of the application output (a space, case, a digit, line order, a
   dropped blank line, a line split at 120 characters, an LE message, a wrong RC) fails.
3. make_deck.py --target zos: jcl/zos/PACZ2CMP.jcl is the generated Z2-1 deck; in the z/OS REL20 deck every run step
   keeps the MVS EXEC / PARM / cards / DDs (only CEEOPTS, CEEDUMP and SYSUDUMP DUMMY added); no slash in any PARM.
"""
import gzip
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tools/zowe'))
from zos_listing import steps_of  # noqa: E402
from zos_equiv import compare, zos_runs  # noqa: E402

JOB = 'PACZTEST'


def spool(d, steps, outputs, extra=()):
    """A spool directory as tools/zowe/zos_submit.py saves it: steps [(step, procstep, pgm, rc)]."""
    d.mkdir(parents=True, exist_ok=True)
    (d / 'job.json').write_text(json.dumps({'jobname': JOB, 'jobid': 'JOB00001'}))
    jcl = [f'        1 //{JOB} JOB 1,CLASS=7']
    msg = []
    for s, ps, pgm, rc in steps:
        jcl.append(f'        2 //{s:<8} EXEC PGM={pgm}' if ps is None else f'          ++{ps:<8} EXEC PGM={pgm}')
        msg.append(f' IEF142I {JOB} {s}{" " + ps if ps else ""} - STEP WAS EXECUTED - COND CODE {rc}')
    files = [{'id': 2, 'ddname': 'JESJCL', 'stepname': 'JES2', 'procstep': None, 'recfm': 'V'},
             {'id': 3, 'ddname': 'JESYSMSG', 'stepname': 'JES2', 'procstep': None, 'recfm': 'VA'}]
    (d / '002-JES2-JESJCL.txt').write_text('\n'.join(jcl) + '\n')
    (d / '003-JES2-JESYSMSG.txt').write_text('\n'.join(msg) + '\n')
    n = 100
    for s, lines in outputs.items():
        n += 1
        files.append({'id': n, 'ddname': 'SYSOUT', 'stepname': s, 'procstep': None, 'recfm': 'FBA', 'lrecl': 121})
        recs = []
        for l in lines:                        # FBA LRECL 121: a longer line becomes more records (ZOS-1 J3)
            while True:
                recs.append(' ' + l[:120].ljust(120))
                l = l[120:]
                if not l:
                    break
        (d / f'{n:03d}-{s}-SYSOUT.txt').write_text('\n'.join(recs) + '\n')
    for s, dd in extra:
        n += 1
        files.append({'id': n, 'ddname': dd, 'stepname': s, 'procstep': None, 'recfm': 'FBA'})
        (d / f'{n:03d}-{s}-{dd}.txt').write_text(' CEE3204S THE SYSTEM DETECTED A PROTECTION EXCEPTION\n')
    (d / 'spool.json').write_text(json.dumps(files))
    return d


# 1. zos_listing with an in-stream PROC
with tempfile.TemporaryDirectory() as t:
    d = Path(t) / 'p'
    spool(d, [], {})
    (d / '002-JES2-JESJCL.txt').write_text('\n'.join([
        f'        1 //{JOB} JOB 1,CLASS=7', '        2 //CBL      PROC M=', '        3 //C        EXEC PGM=IGYCRCTL',
        '        4 //SYSIN    DD DSN=X.COBOL(&M),DISP=SHR', '        5 //         PEND',
        '        6 //ASM      PROC M=', '        7 //A        EXEC PGM=ASMA90', '        8 //         PEND',
        '        9 //PACMAIN  EXEC CBL,M=PACMAIN', '       10 ++C        EXEC PGM=IGYCRCTL',
        '       11 //PACQRY   EXEC CBL,M=PACQRY', '       12 ++C        EXEC PGM=IGYCRCTL',
        '       13 //PACTSO   EXEC ASM,M=PACTSO', '       14 ++A        EXEC PGM=ASMA90',
        '       15 //RUN1     EXEC PGM=PACZ2D']) + '\n')
    (d / '003-JES2-JESYSMSG.txt').write_text(
        f' IEF142I {JOB} PACMAIN C - STEP WAS EXECUTED - COND CODE 0000\n'
        f' IEF142I {JOB} PACQRY C - STEP WAS EXECUTED - COND CODE 0012\n'
        f' IEF142I {JOB} PACTSO A - STEP WAS EXECUTED - COND CODE 0000\n')
    got = steps_of(d, JOB)
    assert got == [('PACMAIN', 'C', 'IGYCRCTL', '0000'), ('PACQRY', 'C', 'IGYCRCTL', '0012'),
                   ('PACTSO', 'A', 'ASMA90', '0000'), ('RUN1', None, 'PACZ2D', 'FLSH')], got
print('zos_listing in-stream PROC: PASS')

# 2. zos_equiv on a simulated z/OS run of the 1.0 oracle (JOB 315, INST-ORACLE: 19 RUN + 6 TSO)
oracle = json.load(gzip.open(R / 'tests/oracle20/315-PACREL10.json.gz'))
CASES = ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1',
         'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')
st = oracle['stream']
starts = [i for i, l in enumerate(st) if l == 'PACMAN MVS-6 SMART GHOSTS']
out = {f'RUN{i}': (R / f'tests/expected/MVS6-{c}.txt').read_text().splitlines() for i, c in enumerate(CASES, 1)}
for k, s in enumerate(starts[len(CASES):], 1):         # TSO transcripts: banner .. LIVES (as tests/test_mvs8.py)
    e = next(i for i in range(s, len(st)) if st[i].startswith('LIVES '))
    out[f'TSO{k}'] = st[s:e + 1]
assert len(out) == 25
runsteps = [(s, None, 'PACZ2D', '0000') for s in out]
pmap = {'PACMAIN': 'PACZ2D'}


def check(outputs, steps=runsteps, extra=()):
    with tempfile.TemporaryDirectory() as t:
        _, _, runs = zos_runs(spool(Path(t) / 's', [('LINK', None, 'IEWBLINK', '0000')] + steps, outputs, extra))
        return compare(oracle, runs, pmap)


bad, msgs = check(out)
assert bad == 0, msgs
assert sum(m.startswith('OK') for m in msgs) == 25


def mutated(step, fn):
    o = {k: list(v) for k, v in out.items()}
    o[step] = fn(o[step])
    return o


i = next(n for n, l in enumerate(out['RUN7']) if '  ' in l)
MUT = {
    'space': mutated('RUN7', lambda b: b[:i] + [b[i].replace('  ', ' ', 1)] + b[i + 1:]),
    'case': mutated('RUN3', lambda b: [b[0].lower()] + b[1:]),
    'digit': mutated('TSO2', lambda b: [l.replace('SCORE 0', 'SCORE 1') for l in b]),
    'order': mutated('RUN12', lambda b: b[:3] + [b[4], b[3]] + b[5:]),
    'blank line': mutated('RUN19', lambda b: b + ['']),
    'split at 120': mutated('RUN1', lambda b: [b[0] + ' ' * (121 - len(b[0])) + 'X'] + b[1:]),
    'missing run': {k: v for k, v in out.items() if k != 'RUN5'},
}
for name, o in MUT.items():
    bad, msgs = check(o)
    assert bad > 0, f'mutation not detected: {name}'
bad, _ = check(out, extra=[('RUN4', 'CEEDUMP')])
assert bad == 1, 'an extra spool file of a run step must fail'
bad, _ = check(out, steps=[(s, p, g, '0004' if s == 'TSO6' else rc) for s, p, g, rc in runsteps])
assert bad == 1, 'a different RC must fail'
print(f'zos_equiv: 25 simulated runs = oracle 315; {len(MUT) + 2} mutations detected: PASS')


def check_sub(names, outputs=None):
    o = outputs or {k: out[k] for k in names}
    with tempfile.TemporaryDirectory() as t:
        _, _, runs = zos_runs(spool(Path(t) / 's', [(k, None, 'PACZ2D', '0000') for k in o], o))
        return compare(oracle, runs, pmap, subset=True)


for names in (['RUN1', 'RUN2', 'RUN3', 'RUN4', 'RUN5'], ['RUN10'], ['RUN9', 'RUN11', 'TSO6'], ['RUN17', 'TSO1', 'TSO6']):
    bad, msgs = check_sub(names)
    assert bad == 0 and sum(m.startswith('OK') for m in msgs) == len(names), msgs
assert check_sub(None, {'RUN6': out['RUN7'], 'RUN7': out['RUN6']})[0] > 0, 'swapped outputs'
assert check_sub(None, {'RUN6': out['RUN6'], 'RUN99': out['RUN7']})[0] > 0, 'step not in the oracle'
assert check_sub(None, {'RUN11': out['RUN11'][:-1] + [out['RUN11'][-1] + ' ']})[0] == 0  # trailing blank = padding
assert '=' in out['RUN11'][1]
assert check_sub(None, {'RUN11': out['RUN11'][:1] + [out['RUN11'][1].replace('=', ':', 1)] + out['RUN11'][2:]})[0] > 0
print('zos_equiv --subset: 4 chunks PASS; swapped outputs, unknown step, changed character detected: PASS')

# 3. make_deck.py --target zos
with tempfile.TemporaryDirectory() as t:
    t = Path(t)

    def md(*args):
        subprocess.run([sys.executable, str(R / 'tools/make_deck.py'), *args], check=True, capture_output=True)

    md('--target', 'zos', 'ZCMP', '--out', str(t / 'z.jcl'))
    assert (t / 'z.jcl').read_text() == (R / 'jcl/zos/PACZ2CMP.jcl').read_text(), 'PACZ2CMP.jcl is not generated'
    md('--target', 'zos', 'REL20', '--load', 'PACZ2D', '--job', 'PACZ2BLD', '--out', str(t / 'zr.jcl'))
    md('REL20', '--load', 'PACZ2D', '--prefix', '@@HLQ@@.PACMAN', '--out', str(t / 'mr.jcl'))

    def run_steps(text):
        blocks = re.split(r'(?m)^(?=//\w+\s+EXEC )', text)
        return {re.match(r'//(\w+)', b).group(1): b for b in blocks[1:] if 'PGM=PACZ2D' in b.split('\n')[0]}
    zr, mr = run_steps((t / 'zr.jcl').read_text()), run_steps((t / 'mr.jcl').read_text())
    assert list(zr) == list(mr) and len(zr) == 25, (list(zr), list(mr))
    for s in zr:
        z = re.sub(r'//CEEOPTS  DD \*\n.*\n/\*\n', '', zr[s]).replace(
            '//CEEDUMP  DD SYSOUT=A\n//SYSUDUMP DD DUMMY\n', '//SYSUDUMP DD SYSOUT=A\n')
        end = re.compile(r'//\n$')            # the z/OS deck ends after TSO6 (no CLIST steps in ZOS-2)
        assert end.sub('', z) == end.sub('', mr[s]), s
        assert 'ALL31(OFF),STACK(,,BELOW)' in zr[s]
    assert '/' not in ''.join(re.findall(r"PARM='([^']*)'", (t / 'zr.jcl').read_text()))
print('make_deck --target zos: PACZ2CMP generated, 25 run steps = MVS cards/PARM/DDs: PASS')

# 4. PACZ2BLD: the deck of record is generated, and every object the binder includes is written by an earlier step of
#    the same job (no stale object from another job can be bound); LINK runs only if no earlier step gave RC > 4
with tempfile.TemporaryDirectory() as t:
    subprocess.run([sys.executable, str(R / 'tools/make_deck.py'), '--target', 'zos', 'Z2BLD', '--out',
                    str(Path(t) / 'b.jcl')], check=True, capture_output=True)
    bld = (Path(t) / 'b.jcl').read_text()
assert bld == (R / 'jcl/zos/PACZ2BLD.jcl').read_text(), 'jcl/zos/PACZ2BLD.jcl is not the generated deck'
steps = re.split(r'(?m)^(?=//\w+\s+EXEC )', bld)[1:]
written = [m.group(1) for s in steps[:-1] for m in [re.search(r'//SYSLIN   DD DSN=@@HLQ@@\.PACMAN\.OBJ\((\w+)\)', s)]]
inc = re.findall(r'INCLUDE OBJ\((\w+)\)', steps[-1])
assert steps[-1].startswith('//LINK     EXEC PGM=IEWBLINK,COND=(4,LT)') and len(inc) == 13 and sorted(inc) == sorted(written)
assert '  ENTRY PACMAIN\n  NAME PACZ2D(R)\n' in steps[-1] and all('COND=(4,LT)' in s.split('\n')[0] for s in steps)
assert 'DELETE' not in bld and 'PGM=PACZ2D' not in bld
print('PACZ2BLD: 13 objects regenerated in the job before the bind, LOAD(PACZ2D), no run, no DELETE: PASS')

# 5. every ZOS-2 run-chunk deck of record in jcl/zos is the generated deck (step text verbatim from the MVS deck)
sys.path.insert(0, str(R / 'tools/zowe'))
import zos_target  # noqa: E402
n = 0
for name, (job, *_rest) in zos_target.CHUNKS.items():
    rec = R / f'jcl/zos/{job}.jcl'
    if rec.exists() and name != 'Z2BLD':
        with tempfile.TemporaryDirectory() as t:
            subprocess.run([sys.executable, str(R / 'tools/make_deck.py'), '--target', 'zos', name, '--out',
                            str(Path(t) / 'c.jcl')], check=True, capture_output=True)
            assert (Path(t) / 'c.jcl').read_text() == rec.read_text(), f'{rec.name} is not the generated deck'
        n += 1
print(f'run-chunk decks of record = generated: {n}: PASS')

# 6. zos_equiv --subset anchors every step at its OWN oracle block (oracle step metadata), not at the first block with
#    the same content: oracle 310 G2B46..G2B49 (start '', '  ', '00', 'ab': all level 1) print identical blocks
sys.path[:0] = [str(R / 'tests'), str(R / 'tools')]
import ref_gp2 as GP2  # noqa: E402
from make_deck import GP2_BAT  # noqa: E402
from zos_equiv import anchors  # noqa: E402
o310 = json.load(gzip.open(R / 'tests/oracle20/310-PACBLGP2.json.gz'))
anc = anchors(o310, {'PACMAIN'})


def g2b(i):
    d, c, st = GP2_BAT[i - 1]
    return [l.rstrip() for l in GP2.simulate((R / f'tests/{d}/{c}.txt').read_text().splitlines(),
                                             start=GP2.parse_start(st))]


same = {f'G2B{i}': g2b(i) for i in (46, 47, 48, 49)}
assert all(v == same['G2B46'] for v in same.values()), 'G2B46..G2B49 should print identical output'
# own blocks derived structurally: G2B45..G2B49 are consecutive oracle steps of 205 lines each, so G2B46 starts one
# block (205 + the 2-line separator) after G2B45 and G2B49 three blocks after G2B46 (= stream line 104321, evidence)
assert anc['G2B46'] == anc['G2B45'] + 207 and anc['G2B49'] == anc['G2B46'] + 3 * 207 == 104321, anc['G2B49']
assert len({anc[k] for k in same}) == 4, 'four distinct own blocks'


def check310(outputs, order=None):
    steps = [(k, None, 'PACZ2D', '0000') for k in (order or outputs)]
    with tempfile.TemporaryDirectory() as t:
        _, _, runs = zos_runs(spool(Path(t) / 's', steps, outputs))
        return compare(o310, runs, {'PACMAIN': 'PACZ2D'}, subset=True)


bad, msgs = check310(same)
assert bad == 0, msgs
for k in same:                                    # each reported at its own block
    assert any(m.startswith(f'OK   {k}:') and f'stream lines {anc[k]}-{anc[k] + len(same[k]) - 1})' in m for m in msgs), k
bad, msgs = check310({'G2B49': same['G2B49']})        # alone: still its own block, not G2B46's (the first identical)
assert bad == 0 and msgs[0].startswith('OK   G2B49') and 'stream lines 104321-104525' in msgs[0], msgs
mut = list(same['G2B48'])
mut[1] = mut[1].replace('A', 'a', 1) if 'A' in mut[1] else mut[1] + 'X'
bad, msgs = check310({'G2B47': same['G2B47'], 'G2B48': mut})
assert bad == 1 and any(m.startswith('OK   G2B47') for m in msgs) and any(m.startswith('FAIL G2B48') for m in msgs), msgs
bad, msgs = check310({'G2B49': same['G2B49'][:-1]})          # truncated: the own block does not end there
assert bad == 1 and 'does not end there' in msgs[0], msgs
bad, msgs = check310({'G2B47': same['G2B47'], 'G2B49': same['G2B49']}, order=['G2B49', 'G2B47'])
assert bad >= 1 and any('not in oracle order' in m for m in msgs), msgs
bad, msgs = check310({'G2B45': g2b(49)})                     # level-13 step given the level-1 output
assert bad == 1 and msgs[0].startswith('FAIL G2B45'), msgs
# not anchorable: a duplicated oracle step name, and an oracle whose run datasets cannot be delimited one per step
dupo = dict(o310, steps=[['G2B49'] + x[1:] if x[0] == 'G2B48' else x for x in o310['steps']])   # same step count
ad = anchors(dupo, {'PACMAIN'})
assert 'G2B49' not in ad and 'G2B48' not in ad and ad['G2B47'] == anc['G2B47'] and ad['G2B55'] == anc['G2B55']
with tempfile.TemporaryDirectory() as t:
    _, _, runs = zos_runs(spool(Path(t) / 's', [('G2B49', None, 'PACZ2D', '0000')], {'G2B49': same['G2B49']}))
    bad, msgs = compare(dupo, runs, {'PACMAIN': 'PACZ2D'}, subset=True)
assert bad >= 1 and any(m.startswith('FAIL G2B49: its oracle block cannot be anchored') for m in msgs), msgs
assert not any(m.startswith('OK') for m in msgs), msgs                         # no fallback to a content search
o309 = json.load(gzip.open(R / 'tests/oracle20/309-PACBLDRP.json.gz'))
o309x = dict(o309, stream=o309['stream'][:-1] + [o309['stream'][-1] + ' '])    # same structure, other digest
assert anchors(o309x, {'PACMAIN'}) == {}, '80 run datasets for 81 run steps and no known boundary -> nothing anchored'
# a duplicated z/OS step name fails in every mode
with tempfile.TemporaryDirectory() as t:
    _, _, runs = zos_runs(spool(Path(t) / 's', [('G2B49', None, 'PACZ2D', '0000'), ('G2B49', None, 'PACZ2D', '0000')],
                                {'G2B49': same['G2B49']}))
    bad, msgs = compare(o310, runs, {'PACMAIN': 'PACZ2D'}, subset=True)
assert bad >= 1 and 'DUPLICATED STEP NAME' in ' '.join(msgs), msgs
print('zos_equiv --subset anchoring: G2B46..G2B49 (identical output) each at its own block (G2B49 = 104321-104525), '
      'mutation / truncation / order / wrong-level output detected, duplicated or undelimitable steps not anchorable: '
      'PASS')

# 7. LE storage-initialization tests: ST0 / STF carry exactly their STORAGE option, every other deck exactly the profile A
#    CEEOPTS; the ST0 / STF cross-check of tools/zowe/zos_arcade_check.py fails on any SYSOUT difference
BASE = 'ALL31(OFF),STACK(,,BELOW)'
WANT = {'PACZ2ST0': BASE + ',STORAGE(00,NONE,00)', 'PACZ2STF': BASE + ',STORAGE(FF,NONE,FF)'}
for f in sorted((R / 'jcl/zos').glob('PACZ2*.jcl')):
    vals = re.findall(r'//CEEOPTS  DD \*\n(.*)\n/\*', f.read_text())
    assert set(vals) <= {WANT.get(f.stem, BASE)}, (f.name, set(vals))
    assert f.stem not in WANT or (vals and set(vals) == {WANT[f.stem]}), f.name
import zos_arcade_check as ZAC  # noqa: E402


def two_jobs(a, b):
    with tempfile.TemporaryDirectory() as t:
        da = spool(Path(t) / 'a', [(k, None, 'PACZ2D', '0000') for k in a], a)
        db = spool(Path(t) / 'b', [(k, None, 'PACZ2D', '0000') for k in b], b)
        return ZAC.cross_check(da, db)


st = {'G2B21': [l.rstrip() for l in ZAC.expected('G2B21')[1]], 'G2R7': [l.rstrip() for l in ZAC.expected('G2R7')[1]]}
assert two_jobs(st, st) == (True, 2)
diff = {k: list(v) for k, v in st.items()}
diff['G2R7'][5] = diff['G2R7'][5].replace('0', '1', 1)
assert two_jobs(st, diff) == (False, 2)
assert two_jobs(st, {'G2R7': st['G2R7'], 'G2B21': st['G2B21']})[0] is False        # different step order
assert two_jobs(st, {'G2B21': st['G2B21']})[0] is False                             # a step missing
print('ST0 / STF: exact STORAGE CEEOPTS on ST0 / STF only, profile A CEEOPTS on every other deck; cross-check passes on '
      'identical SYSOUT and fails on a one-character difference: PASS')


# 8. oracle 309 (RP): the one known boundary without the two-line separator (RPT1 after the RPSEED IEBUPDTE listing),
#    bound to the frozen stream digest; generic anchoring of every other oracle unchanged; every deviation fails closed
import zos_equiv as ZE  # noqa: E402
import ref_rt  # noqa: E402
from test_g0 import oracle as oracle10  # noqa: E402
from make_deck import RP3_BAT  # noqa: E402
a309 = anchors(o309, {'PACMAIN'})
assert len(a309) == sum(1 for x in o309['steps'] if x[1] == 'PACMAIN') == 81 and a309['RPT1'] == 662, len(a309)
s9 = o309['stream']
seps = [p + 2 for p in range(len(s9) - 2) if s9[p] == '' and s9[p + 1] == '' and s9[p + 2] != ''
        and (p == 0 or s9[p - 1] != '')]
text = [p for p in seps if s9[p].startswith('PACMAN ')]          # independent: the 9 text runs are R3B1..R3B9
assert [a309[f'R3B{i}'] for i in range(1, 10)] == text, 'R3B anchors'
assert all(a309[st] in seps for st in a309 if st != 'RPT1'), 'every other step at a separator boundary'
saved = dict(ZE.KNOWN_BOUNDARIES)
for name in ('307-PACREL20', '308-PACBLDS2', '310-PACBLGP2', '315-PACREL10'):    # the table never touches them
    o = json.load(gzip.open(R / f'tests/oracle20/{name}.json.gz'))
    for progs in ({'PACMAIN'}, {'PACMAIN', 'PACQRYT', 'PACTSOT'}):
        with_t = anchors(o, progs)
        ZE.KNOWN_BOUNDARIES.clear()
        without_t = anchors(o, progs)
        ZE.KNOWN_BOUNDARIES.update(saved)
        assert with_t == without_t and with_t, name
digest = next(iter(saved))
for bad in ({'line': 661}, {'line': 663}, {'step': 'RPT2'}, {'prev': 'IEB818I HIGHEST CONDITION CODE WAS 00000000'},
            {'head': 'PACMAN '}):
    ZE.KNOWN_BOUNDARIES[digest] = [dict(saved[digest][0], **bad)]
    got = anchors(o309, {'PACMAIN'})
    ZE.KNOWN_BOUNDARIES.update(saved)
    assert got == {} or (bad == {'head': 'PACMAN '} and got == {}), (bad, len(got))
assert anchors(o309, {'PACQRYT'}) == anchors(o309x, {'PACQRYT'}), 'an entry of another class is ignored'


def rp3_model(step):
    play, d, c, rules, st_, sp = RP3_BAT[int(step[3:]) - 1]
    cs = (R / f'tests/{d}/{c}.txt').read_text().splitlines()
    start, per = GP2.parse_start(st_), ref_rt.period(sp)
    if rules == 'C':
        w = oracle10()[0][c] if play == 'T' else ref_rt.simulate(cs, per=per)
    else:
        w = GP2.rt_simulate(cs, start, per=per) if play == 'R' else GP2.simulate(cs, start=start)
    return [l.rstrip() for l in w]


rp = {f'R3B{i}': rp3_model(f'R3B{i}') for i in (1, 2, 4, 5, 6, 7, 9)}
for k, w in rp.items():
    assert s9[a309[k]:a309[k] + len(w)] == w, k
with tempfile.TemporaryDirectory() as t:
    _, _, runs = zos_runs(spool(Path(t) / 's', [(k, None, 'PACZ2D', '0000') for k in rp], rp))
    bad, msgs = compare(o309, runs, {'PACMAIN': 'PACZ2D'}, subset=True)
assert bad == 0 and sum(m.startswith('OK') for m in msgs) == 7, msgs
mut = dict(rp, R3B5=rp['R3B5'][:3] + [rp['R3B5'][3] + 'X'] + rp['R3B5'][4:])
with tempfile.TemporaryDirectory() as t:
    _, _, runs = zos_runs(spool(Path(t) / 's', [(k, None, 'PACZ2D', '0000') for k in mut], mut))
    bad, msgs = compare(o309x, runs, {'PACMAIN': 'PACZ2D'}, subset=True)
assert bad == 7 and all('cannot be anchored' in m for m in msgs if m.startswith('FAIL G') or 'R3B' in m), msgs
with tempfile.TemporaryDirectory() as t:
    _, _, runs = zos_runs(spool(Path(t) / 's', [(k, None, 'PACZ2D', '0000') for k in mut], mut))
    bad, msgs = compare(o309, runs, {'PACMAIN': 'PACZ2D'}, subset=True)
assert bad == 1 and [m.split(':')[0] for m in msgs if m.startswith('FAIL')] == ['FAIL R3B5'], msgs
print('oracle 309 RP anchoring: 81/81 with the digest-bound RPT1 boundary (R3B = the 9 text blocks), other oracles '
      'unchanged, wrong line / step / preceding line / header / digest fail closed, 7 RP3 BAT models = own blocks, '
      'a mutation fails R3B5 only: PASS')

# 9. ZOS-3 PACZ3FS (PACFSIO batch contract): S1S3 / S2L4 come verbatim from their own MVS decks (GP2 / S2), PARM column 12
#    is COLOR A on a TSO PARM (PACPLAT TRY-COLOUR -> CALL 'PACFSIO' FSON); each anchors at its own block of its own
#    oracle (310 / 308) and equals the 1.0-MVS TSO DIE1 run; the real z/OS COLOR(N) run of DIE1 (PACZ2C7 TSO2, JOB09031)
#    passes every check for both steps; a mutation fails that step only; the bind of record includes PACFSIO
import zos_fs_check as FS  # noqa: E402
import make_deck as md  # noqa: E402  (last section: apply() swaps its builders for this process)
fs = (R / 'jcl/zos/PACZ3FS.jcl').read_text()
fst = zos_target.steps_of_deck(fs)
assert list(fst) == ['S1S3', 'S2L4'] and 'DELETE' not in fs and fs.count('//STEPLIB  DD DSN=@@HLQ@@.PACMAN.LOAD,') == 2
zos_target.apply(md, zos_target.PREFIX)
for s, (base, _) in zos_target.SOURCES['Z3FS'].items():
    own = zos_target.steps_of_deck(md.build(base, zos_target.PREFIX, zos_target.LOAD))[s]
    assert fst[s] == (own[:-3] if own.endswith('\n//\n') else own), s     # S2L4 ends the S2 deck: null statement off
    parm = re.search(r"PARM='([^']*)'", fst[s].split('\n', 1)[0]).group(1)
    assert parm[:3] == 'TSO' and parm[11] == 'A' and parm[18] == 'A' and (len(parm) < 21 or parm[20] == 'C'), parm
    assert '//CEEOPTS  DD *\nALL31(OFF),STACK(,,BELOW)\n/*\n' in fst[s] and 'PACHS' not in fst[s]
c7 = zos_runs(R / 'build/zos/PACZ2C7-JOB09031')[2]['TSO2']
with tempfile.TemporaryDirectory() as t:
    runs = zos_runs(spool(Path(t) / 's', [(k, None, 'PACZ2D', '0000') for k in FS.STEPS],
                          {k: c7['lines'] for k in FS.STEPS}))[2]
    bad, msgs = FS.check_runs(runs)
assert bad == 0 and sum(m.startswith(('oracle 310 OK', 'oracle 308 OK')) for m in msgs) == 2, msgs
mut = c7['lines'][:40] + [c7['lines'][40] + 'X'] + c7['lines'][41:]
with tempfile.TemporaryDirectory() as t:
    runs = zos_runs(spool(Path(t) / 's', [(k, None, 'PACZ2D', '0000') for k in FS.STEPS],
                          {'S1S3': c7['lines'], 'S2L4': mut}))[2]
    bad, msgs = FS.check_runs(runs)
assert bad >= 3 and all('S2L4' in m for m in msgs if 'FAIL' in m), msgs
assert FS.linkage()[0]
print('PACZ3FS: S1S3 / S2L4 verbatim from GP2 / S2, TSO + COLOR A PARM, own oracle blocks (310 / 308) = 1.0-MVS DIE1 = '
      'test_mvs8 model, the real z/OS COLOR(N) DIE1 run passes as both, a mutation fails S2L4 only, PACFSIO bound: PASS')

# 10. ZOS-3 PACZ3HA (HS test PDSs, attempt T1): the deck of record is the generated one; it names only the two attempt
#     PDSs (never <HLQ>.PACMAN.DATA), no DELETE, no game run; real PDSs (DSNTYPE=PDS) FB 80/80 with BLKSIZE coded;
#     HSSEED1..3 / HSFILL are the frozen MVS HS steps verbatim apart from the dataset names; the HSFILL rule accepts
#     the oracle 312 IEBUPDTE log (M01..M20 stowed, IEB813I at M21) and rejects a 21st member or a missing IEB813I
import zos_hs_setup_check as HSC  # noqa: E402
ha = (R / 'jcl/zos/PACZ3HA.jcl').read_text()
with tempfile.TemporaryDirectory() as t:
    subprocess.run([sys.executable, str(R / 'tools/make_deck.py'), '--target', 'zos', 'Z3HA', '--out',
                    str(Path(t) / 'h.jcl')], check=True, capture_output=True)
    assert (Path(t) / 'h.jcl').read_text() == ha, 'PACZ3HA.jcl is not the generated deck'
has = zos_target.steps_of_deck(ha)
assert list(has) == HSC.STEPS and 'DELETE' not in ha and 'PACMAN.DATA' not in ha and 'PACZ2D' not in ha
assert set(re.findall(r'DSN=([\w@.]+)', ha)) == {'@@HLQ@@.PACMAN.HSTEST.T1', '@@HLQ@@.PACMAN.HSFULL.T1'}
assert ha.count('DISP=(NEW,CATLG,CATLG),\n//            DSNTYPE=PDS,DSORG=PO,RECFM=FB,LRECL=80,BLKSIZE=80,') == 2
mvs_hs = zos_target.steps_of_deck(md.hs_steps('@@HLQ@@.PACMAN', 'PACZ2D'))
for s in ('HSSEED1', 'HSSEED2', 'HSSEED3', 'HSFILL'):
    assert has[s].replace('.HSTEST.T1', '.HSTEST').replace('.HSFULL.T1', '.HSFULL') == mvs_hs[s], s
from zoslib import audit_deck, render  # noqa: E402
assert audit_deck(render(ha, 'Z00000'), 'Z00000') == []
o312 = json.load(gzip.open(R / 'tests/oracle20/312-PACBLDHS.json.gz'))['stream']
log = o312[o312.index('       ./ ADD NAME=M01') - 3:o312.index('IEB819I END OF JOB IEBUPDTE.') + 1]
assert HSC.fill_ok(log)
assert not HSC.fill_ok([l for l in log if 'IEB813I' not in l])
assert not HSC.fill_ok(log[:-3] + ['IEB817I MEMBER NAME (M21     ) NOT FOUND IN NM DIRECTORY.  STOWED WITH TTR.']
                       + log[-3:])
# the LISTDS parser on the real SYSTSPRT of PACZ3HA JOB02091 (fixture = the raw spool file, SHA-256 recorded in
# docs/evidence/zos3-pacz3ha-JOB02091-raw.sha256): the first checker run took the final IKJEFT01 END as a 21st
# HSFULL member (the member list was not closed at READY); each extent now runs from its LISTDS echo to its READY
import hashlib  # noqa: E402
fx = R / 'tests/fixtures/zos/JOB02091-109-HSLIST-SYSTSPRT.txt'
assert hashlib.sha256(fx.read_bytes()).hexdigest() == \
    '5a53d7a2cd633d0999660c0f8c441d467c6c0a88480b06022d8c2c30de4f6210', 'fixture is not the JOB02091 raw file'
raw = fx.read_text().splitlines()
got = HSC.listds(raw)
assert got == {'Z00000.PACMAN.HSTEST.T1': ('FB', '80', '80', 'PO', ['BAD', 'EMPTY', 'HS9']),
               'Z00000.PACMAN.HSFULL.T1': ('FB', '80', '80', 'PO', [f'M{i:02}' for i in range(1, 21)])}, got
assert all('END' not in v[4] for v in got.values()) and raw[-2:] == [' READY', ' END']
k20 = raw.index('   M20')
legit = raw[:k20 + 1] + ['   END'] + raw[k20 + 1:]          # a real member named END is indented: kept as a member
assert HSC.listds(legit)['Z00000.PACMAN.HSFULL.T1'][4][-1] == 'END'
k1 = raw.index(" Z00000.PACMAN.HSFULL.T1")
bad_shapes = {
    'no READY after HSFULL': raw[:-2] + [' END'],
    'no final END': raw[:-1],
    'END inside the HSFULL extent': raw[:k20] + [' END'] + raw[k20:],
    'unexpected line among the members': raw[:k20] + ['   M20 EXTRA'] + raw[k20:],
    'second echo before READY': raw[:k20] + ["   LISTDS 'Z00000.PACMAN.HSTEST.T1' MEMBERS"] + raw[k20:],
    'dataset line differs from the echo': raw[:k1] + [' Z00000.PACMAN.HSFULL.T2'] + raw[k1 + 1:],
    'no MEMBERS header': [l for l in raw if l != ' --MEMBERS--'],
    'no TMP prompt first': raw[1:],
    'duplicated extent': raw[:-1] + raw[1:raw.index(' READY', 2) + 1] + [' END'],
    'no ASA column': [l[1:] for l in raw],
}
for why, shape in bad_shapes.items():
    assert HSC.listds(shape) is None, why
print('PACZ3HA: generated deck, only HSTEST.T1 / HSFULL.T1 (no DATA, no DELETE, no run), DSNTYPE=PDS FB 80/80, '
      'seed / fill steps = frozen MVS HS steps, full-directory rule on the oracle 312 log; LISTDS parser on the real '
      f'JOB02091 output (final END not a member, a member named END kept, {len(bad_shapes)} malformed shapes fail '
      'closed): PASS')

# 11. oracle 312 (HS): the known boundary of HA1 (after the HSFILL IEBUPDTE listing, ONE empty line), bound to the
#     frozen stream digest: 19/19 PACMAIN run steps anchored by ordinal; without the entry, with another digest or with
#     any recorded fact changed nothing is anchored; every other oracle anchors exactly as without the entry; each
#     anchored block = the frozen test_hs model (ref_hs + ref_gp2, PACMAN_LATER_PHASE=G8 as test_g8 ran it)
import zos_hs_model as HSM  # noqa: E402
o312 = json.load(gzip.open(R / 'tests/oracle20/312-PACBLDHS.json.gz'))
s12 = o312['stream']
d312 = hashlib.sha256('\n'.join(s12).encode()).hexdigest()
assert d312 == '46fdb3368babf2eb1f220dbe03f5af8f0fd7ac27b53c090634a2756390d0b9ca' and d312 in ZE.KNOWN_BOUNDARIES
a312 = anchors(o312, {'PACMAIN'})
runs312 = [x[0] for x in o312['steps'] if x[1] == 'PACMAIN']
assert len(runs312) == 19 and list(a312) == runs312 and a312['HA1'] == 149, a312
seps12 = [p + 2 for p in range(len(s12) - 2) if s12[p] == '' and s12[p + 1] == '' and s12[p + 2] != ''
          and (p == 0 or s12[p - 1] != '')]
assert all(a312[st] in seps12 for st in runs312[1:]) and 149 not in seps12
o312x = dict(o312, stream=s12[:-1] + [s12[-1] + ' '])
assert anchors(o312x, {'PACMAIN'}) == {}, 'other digest: 18 run datasets for 19 run steps -> nothing anchored'
saved = dict(ZE.KNOWN_BOUNDARIES)
ZE.KNOWN_BOUNDARIES.pop(d312)
assert anchors(o312, {'PACMAIN'}) == {}, 'without the entry nothing of 312 is anchored'
others = {}
for name in ('307-PACREL20', '308-PACBLDS2', '309-PACBLDRP', '310-PACBLGP2', '311-PACBLG23', '315-PACREL10',
             '316-PACBLDS2'):
    o = json.load(gzip.open(R / f'tests/oracle20/{name}.json.gz'))
    others[name] = (o, {k: anchors(o, k) for k in ({'PACMAIN'}, {'PACMAIN', 'PACQRYT', 'PACTSOT'})} if False else
                    [anchors(o, p) for p in ({'PACMAIN'}, {'PACMAIN', 'PACQRYT', 'PACTSOT'})])
ZE.KNOWN_BOUNDARIES.update(saved)
for name, (o, before) in others.items():
    assert [anchors(o, p) for p in ({'PACMAIN'}, {'PACMAIN', 'PACQRYT', 'PACTSOT'})] == before, name
for bad in ({'line': 148}, {'line': 150}, {'step': 'HA2'}, {'prev': 'IEB818I HIGHEST CONDITION CODE WAS 00000012'},
            {'head': 'PACMAN MVS-6 SMART GHOSTX'}, {'head': 'TSX SWITCH '}):
    ZE.KNOWN_BOUNDARIES[d312] = [dict(saved[d312][0], **bad)]
    got = anchors(o312, {'PACMAIN'})
    ZE.KNOWN_BOUNDARIES.update(saved)
    assert got == {}, (bad, len(got))
ns = HSM.model()
for st, kind, base, hs in ns['RUNS']:
    if st.startswith('HTSO'):
        continue
    b = a312[st]
    if base is not None:
        w = HSM.expected_text(st)
        assert s12[b:b + len(w)] == w and ZE.ends_ok(o312, a312, st, b + len(w)), st
    else:
        streams, ends, j = ns['tsd_run'](s12, b, (7 if kind == 'T' else 8) + len(hs))
        assert streams == ns['rp_streams'](kind) and ends[-len(hs):] == hs and ZE.ends_ok(o312, a312, st, j), st
with tempfile.TemporaryDirectory() as t:
    ha = {st: HSM.expected_text(st) for st in ('HA1', 'HA2')}
    _, _, runs = zos_runs(spool(Path(t) / 's', [(k, None, 'PACZ2D', '0000') for k in ha], ha))
    bad, msgs = compare(o312, runs, {'PACMAIN': 'PACZ2D'}, subset=True)
    assert bad == 0 and sum(m.startswith('OK') for m in msgs) == 2, msgs
    mut = dict(ha, HA1=ha['HA1'][:-1] + [ha['HA1'][-1] + 'X'])
    _, _, runs = zos_runs(spool(Path(t) / 'm', [(k, None, 'PACZ2D', '0000') for k in mut], mut))
    bad, msgs = compare(o312, runs, {'PACMAIN': 'PACZ2D'}, subset=True)
    assert bad == 1 and [m.split(':')[0] for m in msgs if m.startswith('FAIL')] == ['FAIL HA1'], msgs
# the 309 known boundary through compare() too (RPT1 was not in PACZ2RP): its own oracle block as the z/OS output
names9 = [x[0] for x in o309['steps']]
e9 = a309[names9[names9.index('RPT1') + 1]] - 2
rpt1 = {'RPT1': s9[a309['RPT1']:e9]}
with tempfile.TemporaryDirectory() as t:
    _, _, runs = zos_runs(spool(Path(t) / 's', [('RPT1', None, 'PACZ2D', '0000')], rpt1))
    bad, msgs = compare(o309, runs, {'PACMAIN': 'PACZ2D'}, subset=True)
assert bad == 0 and msgs[0].startswith('OK   RPT1') and 'stream lines 662-' in msgs[0], msgs
print('oracle 312 HS anchoring: 19/19 with the digest-bound HA1 boundary, nothing without it / with another digest / '
      'with any fact changed, 7 other oracles unchanged, 19 blocks = test_hs model (17 text, 2 TSD), compare: '
      'HA1/HA2 PASS, a mutation fails HA1 only; 309 RPT1 compared at its known boundary: PASS')

# 12. ZOS-3 PACZ3HS1..8 (option A): the frozen HS runs in the frozen order without HA6, each job's steps = the z/OS
#     rendering of the frozen MVS HS steps with only the approved deltas (T1 names, COND=(0,NE), profile A CEEOPTS /
#     CEEDUMP / SYSUDUMP DUMMY in the IKJEFT01 steps); only LOAD + the two T1 PDSs; no DELETE / DATA / CLIST / HSP;
#     estimates under 4,000; HTSO1/2 model = the fixed oracle 312 ranges (frozen digest); the state chain starts at the
#     accepted PACZ3HA state and ends at test_hs's final PDS; HA6 changes nothing
import zos_hs_check as HSK  # noqa: E402
order = [s for steps in zos_target.HS_JOBS.values() for s in steps]
assert order == [r[0] for r in ns['HS_RUNS'] if r[0] not in zos_target.HS_DEFERRED] + ['HTSO1', 'HTSO2']
assert zos_target.HS_DEFERRED == ['HA6']
mvs_hs = zos_target.steps_of_deck(md.hs_steps('@@HLQ@@.PACMAN', 'PACZ2D'))
cee = '//CEEOPTS  DD *\nALL31(OFF),STACK(,,BELOW)\n/*\n'
est = {}
for n, (name, steps) in enumerate(zos_target.HS_JOBS.items(), 1):
    deck = (R / f'jcl/zos/PACZ3HS{n}.jcl').read_text()
    with tempfile.TemporaryDirectory() as t:
        subprocess.run([sys.executable, str(R / 'tools/make_deck.py'), '--target', 'zos', name, '--out',
                        str(Path(t) / 'h.jcl')], check=True, capture_output=True)
        assert (Path(t) / 'h.jcl').read_text() == deck, f'PACZ3HS{n}.jcl is not the generated deck'
    st = zos_target.steps_of_deck(deck)
    assert list(st) == steps, (n, list(st))
    assert 'DELETE' not in deck and 'PACMAN.DATA' not in deck and 'HSCL' not in deck and '//HSP' not in deck
    assert set(re.findall(r"(?:DSN=|DA\(')([\w@.]+)", deck)) <= {'@@HLQ@@.PACMAN.LOAD', '@@HLQ@@.PACMAN.HSTEST.T1',
                                                                 '@@HLQ@@.PACMAN.HSFULL.T1'}, n
    assert audit_deck(render(deck, 'Z00000'), 'Z00000') == []
    lines = 60
    for s in steps:
        assert re.match(rf'//{s}\s+EXEC PGM=(PACZ2D|IKJEFT01),COND=\(0,NE\)', st[s]) and st[s].count(cee) == 1, s
        back = st[s].replace('.HSTEST.T1', '.HSTEST').replace('.HSFULL.T1', '.HSFULL').replace(
            'COND=(0,NE)', 'COND=(0,NE,LINK)')
        if s.startswith('HTSO'):
            back = back.replace(cee + '//CEEDUMP  DD SYSOUT=A\n//SYSUDUMP DD DUMMY\n', '')
        own = mvs_hs[s]
        assert back == own, s
        kind = next((r[1] for r in ns['HS_RUNS'] if r[0] == s), 'S')
        if kind in ('T', 'Q'):
            lines += a312[order[order.index(s) + 1]] - 2 - a312[s] if s != 'HG3' else 941
        else:
            lines += len(HSM.expected_text(s)) + (12 if s.startswith('HTSO') else 0)
        lines += 30
    est[n] = lines
    assert lines < 4000, (n, lines)
for i, at in ((1, 25366), (2, 25744)):          # HTSO model = the fixed oracle 312 ranges of the frozen digest
    w = HSM.expected_text(f'HTSO{i}')
    assert d312 == '46fdb3368babf2eb1f220dbe03f5af8f0fd7ac27b53c090634a2756390d0b9ca'
    assert s12[at:at + len(w)] == w and s12[at - 2:at] == ['END', ''], i
    assert s12[at + len(w)] in ('', ) and s12[at + len(w) + 1] != 'HIGH SCORE', i
sts = HSK.expected_states()
assert len(sts) == 9 and sts[0] == {'HS9': ['9999999 PACHS001 099'], 'BAD': ['XYZZY NOT A SCORE', 'SECOND JUNK RECORD'],
                                    'EMPTY': []}
assert sts[-1] == {k: [r.rstrip() for r in v] for k, v in ns['PDS'].members.items()} and 'HS8' not in sts[-1]
assert sts[3] == sts[4], 'PACZ3HS4 (HA7, HA8) changes nothing'
full = {s: (b, a) for s, b, a, _, _ in HSM.states()}
assert full['HA6'][0] == full['HA6'][1], 'HA6 is state-neutral'


def hs8(t, iec=True, rc='0000', hh1=None):
    outs = {s: HSM.expected_text(s) for s in ('HH1', 'HTSO1', 'HTSO2')}
    if hh1:
        outs['HH1'] = hh1
    d = spool(Path(t), [('HH1', None, 'PACZ2D', rc), ('HTSO1', None, 'IKJEFT01', '0000'),
                        ('HTSO2', None, 'IKJEFT01', '0000')], outs, [('HTSO1', 'SYSTSPRT'), ('HTSO2', 'SYSTSPRT')])
    for f in d.glob('*-SYSTSPRT.txt'):
        f.write_text('1READY\n   ALLOC F(PACHS) DA(...) SHR REUSE\n READY\n END\n')
    m = d / '003-JES2-JESYSMSG.txt'
    m.write_text(m.read_text() + ' IGD104I Z00000.PACMAN.LOAD                           RETAINED,  DDNAME=STEPLIB\n'
                 + (f' IEC217I B14-0C,IGG0201Z,{JOB},HH1,PACHS,0D38,ZXPL01,\n Z00000.PACMAN.HSFULL.T1(HISCORE)\n'
                    if iec else ''))
    return d


with tempfile.TemporaryDirectory() as t:
    _, res = HSK.spool_check(hs8(Path(t) / 'ok'), 8)
    assert all(v for _, v in res), [k for k, v in res if not v]
    _, res = HSK.spool_check(hs8(Path(t) / 'noiec', iec=False), 8)
    assert [k for k, v in res if not v] == [k for k, _ in res if k.startswith('HH1: exactly one IEC event')], res
    _, res = HSK.spool_check(hs8(Path(t) / 'rc', rc='0016'), 8)
    assert [k for k, v in res if not v] == ['HH1 COND CODE 0000', 'oracle 312 HH1: z/OS PACZ2D RC 0016 extra [] / '
                                           'oracle PACMAIN RC 0000'], res
    w = HSM.expected_text('HH1')
    _, res = HSK.spool_check(hs8(Path(t) / 'saved', hh1=w[:-1] + ['NEW HIGH SCORE']), 8)
    assert {k.split(':')[0] for k, v in res if not v} == {'oracle 312 HH1', 'HH1 SYSOUT = model (740 lines, ends '
                                                          "'HIGH SCORE NOT SAVED')"}, [k for k, v in res if not v]
# the real JESYSMSG of PACZ3HS8 JOB02433 (fixture = the raw file, SHA-256 in docs/evidence/
# zos3-pacz3hs8-JOB02433-raw.sha256): the first checker run expected the MVS form (a second 'IEC217I <dsname>' line);
# z/OS continues the message on the next record without a message id, with the member
fx = R / 'tests/fixtures/zos/JOB02433-004-JES2-JESYSMSG.txt'
assert hashlib.sha256(fx.read_bytes()).hexdigest() == \
    'c21900d8b5cb40ed39a3c4714637c831792bf424d0b86b13946a939e70c0c37a', 'fixture is not the JOB02433 raw file'
real = fx.read_text().splitlines()
assert HSK.hh1_b14('\n'.join(real), 'PACZ3HS8')
k = next(i for i, l in enumerate(real) if 'IEC217I' in l)
first, cont = real[k], real[k + 1]
assert cont == ' Z00000.PACMAN.HSFULL.T1(HISCORE)'
neg = {
    'no continuation': real[:k + 1] + real[k + 2:],
    'continuation not next': real[:k + 1] + [real[k + 2]] + [cont] + real[k + 3:],
    'other dataset': real[:k + 1] + [' Z00000.PACMAN.HSTEST.T1(HISCORE)'] + real[k + 2:],
    'other member': real[:k + 1] + [' Z00000.PACMAN.HSFULL.T1(M01)'] + real[k + 2:],
    'no member': real[:k + 1] + [' Z00000.PACMAN.HSFULL.T1'] + real[k + 2:],
    'other step': real[:k] + [first.replace(',HH1,', ',HA1,')] + real[k + 1:],
    'other DD': real[:k] + [first.replace(',PACHS,', ',SYSUT2,')] + real[k + 1:],
    'other code': real[:k] + [first.replace('B14-0C', 'B37-04')] + real[k + 1:],
    'other job': real[:k] + [first.replace(',PACZ3HS8,', ',PACZ3HS7,')] + real[k + 1:],
    'MVS continuation form': real[:k + 1] + [' IEC217I Z00000.PACMAN.HSFULL.T1(HISCORE)'] + real[k + 2:],
    'a second IEC message': real + [' IEC161I 056-084,IGG0CLF2,PACZ3HS8,HTSO1,PACHS'],
    'the event twice': real[:k + 2] + [first, cont] + real[k + 2:],
}
for why, shape in neg.items():
    assert not HSK.hh1_b14('\n'.join(shape), 'PACZ3HS8'), why
print('PACZ3HS8 checker on a synthetic spool: PASS with B14-0C + RC 0 + NOT SAVED; missing B14, step RC 16, a '
      '"NEW HIGH SCORE" HH1 each fail exactly their criteria; the real JOB02433 IEC217I (z/OS continuation form) '
      f'accepted, {len(neg)} malformed / other events fail closed: PASS')
print('PACZ3HS1..8: generated decks, frozen order without HA6, steps = MVS HS steps + the approved deltas only, '
      f'LOAD + T1 only, spool estimates {est} (< 4,000), HTSO model = oracle 312 lines 25366 / 25744, state chain '
      'PACZ3HA -> test_hs final PDS, HA6 state-neutral: PASS')

# 13. ZOS-3 PACZ3TD1..4 (minimum ALARM(PATTERN) TSD set): the 12 selected S2T runs reach all 21 D41 edges of test_s2
#     (frozen coverage code, run per run); the 9 that are the only run of an edge are all in, the other 3 are the
#     cheapest completion (fewest oracle lines); no selected run can be dropped; every one is ALARM P (PARM column 25),
#     unlike HG2 / HG3 (no column 25: SINGLE); each oracle 308 block = the model byte for byte; the checker fails a
#     single flipped alarm bit in one hex record, in that step only (no normalisation of WCC bytes)
import itertools  # noqa: E402
import zos_s2_model as S2M  # noqa: E402
import zos_tsd_check as TDK  # noqa: E402
cov2 = S2M.coverage()
sel = [s for n in range(1, 5) for s in zos_target.CHUNKS[f'Z3TSD{n}'][2]]
edges = set(S2M.model()['EDGES'])
assert set().union(*cov2.values()) == edges and len(edges) == 21
assert set().union(*[cov2[s] for s in sel]) == edges, 'the selection reaches every edge'
only2 = {e: [s for s in cov2 if e in cov2[s]] for e in edges}
mand2 = {v[0] for v in only2.values() if len(v) == 1}
assert mand2 <= set(sel) and len(mand2) == 9
o308 = json.load(gzip.open(R / 'tests/oracle20/308-PACBLDS2.json.gz'))
s8, a308 = o308['stream'], anchors(o308, {'PACMAIN'})
n8 = [x[0] for x in o308['steps'] if x[0] in a308]
blk8 = {k: [l.rstrip() for l in s8[a308[k]:a308[n8[n8.index(k) + 1]] - 2]] for k in cov2}
left = edges - set().union(*[cov2[s] for s in mand2])
cands2 = [s for s in cov2 if s not in mand2 and cov2[s] & left]
best2 = min((sum(len(blk8[s]) for s in c), sorted(c)) for r in range(1, 4) for c in itertools.combinations(cands2, r)
            if set().union(*[cov2[s] for s in c]) >= left)
assert sorted(set(sel) - mand2) == best2[1], best2
for s in sel:
    assert set().union(*[cov2[x] for x in sel if x != s]) != edges, f'{s} could be dropped'
deck2 = {}
for n in range(1, 5):
    deck2.update(zos_target.steps_of_deck((R / f'jcl/zos/{zos_target.CHUNKS[f"Z3TSD{n}"][0]}.jcl').read_text()))
for s in sel:
    parm = re.search(r"PARM='([^']*)'", deck2[s]).group(1)
    assert parm[:3] == 'TSD' and len(parm) == 25 and parm[24] == 'P', (s, parm)
    pat, end, _ = S2M.expected(s)
    st_, j = S2M.model()['tsd_streams'](blk8[s], 0)
    assert st_ == pat and blk8[s][j:] == end and ZE.ends_ok(o308, a308, s, a308[s] + len(blk8[s])), s
    assert max(len(l) for l in blk8[s]) <= 120, s          # one SYSOUT record per line: no hex record split
hs7 = zos_target.steps_of_deck((R / 'jcl/zos/PACZ3HS7.jcl').read_text())
for s in ('HG2', 'HG3'):
    assert len(re.search(r"PARM='([^']*)'", hs7[s]).group(1)) == 21, 'HG2 / HG3 ran ALARM SINGLE (no column 25)'
td3 = {s: blk8[s] for s in zos_target.CHUNKS['Z3TSD3'][2]}
with tempfile.TemporaryDirectory() as t:
    runs = zos_runs(spool(Path(t) / 'ok', [(k, None, 'PACZ2D', '0000') for k in td3], td3))[2]
    assert compare(o308, runs, {'PACMAIN': 'PACZ2D'}, subset=True)[0] == 0
    assert all(TDK.model_check(s, runs[s]['lines'])[0] for s in td3)
    k = next(i for i, l in enumerate(td3['S2T13']) if l.startswith('TSD ') and not l.startswith('TSD FRAME')
             and l[4:6] in ('C6', 'C2'))
    w = td3['S2T13'][k]
    flip = w[:4] + ('C2' if w[4:6] == 'C6' else 'C6') + w[6:]          # the WCC alarm bit X'04' toggled
    mut = dict(td3, S2T13=td3['S2T13'][:k] + [flip] + td3['S2T13'][k + 1:])
    runs = zos_runs(spool(Path(t) / 'm', [(k2, None, 'PACZ2D', '0000') for k2 in mut], mut))[2]
    nb, msgs = compare(o308, runs, {'PACMAIN': 'PACZ2D'}, subset=True)
    assert nb == 1 and [m.split(':')[0] for m in msgs if m.startswith('FAIL')] == ['FAIL S2T13'], msgs
    assert [s for s in mut if not TDK.model_check(s, runs[s]['lines'])[0]] == ['S2T13']
print(f'PACZ3TD1..4: {len(sel)} S2T runs reach all 21 D41 edges (9 sole runs + the cheapest completion '
      f'{best2[1]}, none removable), ALARM P on each (HG2 / HG3 SINGLE), oracle 308 blocks = ref_s2 model byte for '
      'byte, a flipped alarm bit fails its step only: PASS')

# 14. ZOS-4 PACZ4CL: the generated deck; only the work PDS and the present-path DATA are named / written (never
#     <HLQ>.PACMAN.DATA, no DELETE, no run of PACMAIN); G8CLS / HSCLS1 / HSCLS2 carry exactly the MVS test CLISTs (the
#     HS block with the two attempt prefixes instead of one prefix deleted in between); the TMP-output rules accept
#     the oracle 307 / 312 shapes and fail closed on a wrong PARM, a swapped path, a missing HSCL END or an IKJ56 message
import zos_clist_check as CLK  # noqa: E402
cl = (R / 'jcl/zos/PACZ4CL.jcl').read_text()
# PACZ4CL (attempt T1) is frozen as submitted (JOB03750): the deck of record = the deck the job ran (the Z2 lines have
# since been refined for attempt T2, PACZ4Z2, section 16)
sub = R / 'build/zos/PACZ4CL-JOB03750/deck.jcl'
if sub.exists():
    assert render(cl, 'Z00000') == sub.read_text(), 'PACZ4CL.jcl is not the deck JOB03750 ran'
cst = zos_target.steps_of_deck(cl)
assert list(cst) == CLK.STEPS and 'DELETE' not in cl and 'PACMAN.DATA' not in cl and 'PACMAIN' not in cl
assert set(re.findall(r'DSN=([\w@.]+)', cl)) == {'@@HLQ@@.PACMAN.Z4CL.T1', '@@HLQ@@.PACMAN.Z4HSY.DATA',
                                               '@@HLQ@@.PACMAN.Z4CEY.CEEOPTS'}
# Z2: src/zos/PACMAN.clist = the frozen 2.0 CLIST + the Z2 lines around the CALL only; the PARM lines (G8 check)
# unchanged; each Z2 test member carries the Z2 lines verbatim (CALL -> marker)
sys.path.insert(0, str(R / 'tests'))
import zos_c2  # noqa: E402
c20 = (R / 'src/clist/PACMAN.clist').read_text().splitlines()
cz = zos_c2.z3_strip(zos_c2.z5_strip((R / 'src/zos/PACMAN.clist').read_text())).splitlines()   # Z5 (ZOS-6, section
#                                                                       22) and Z3 (section 18) put back: Z2 only
zi, zc = cz.index(next(l for l in cz if l.startswith('/* Z2 (ZOS-4)'))), cz.index("CALL '@@PREFIX@@.LOAD(PACMAIN)' '&P'")
assert cz[:zi] == c20[:zi] and cz[zc] == c20[zi] and cz[zc + 1] == 'FREE F(CEEOPTS)' and cz[zc + 2:] == c20[zi + 1:]
assert all(len(l.replace('@@PREFIX@@', 'Z00000.PACMAN')) <= 72 for l in cz) and len(cz) - len(c20) == 32
for s, pz in (('Z2CLS1', 'Z4CEY'), ('Z2CLS2', 'Z4CEN')):          # T1: the Z2 lines as they were (JOB03750)
    body = cst[s].split('DLM=ZZ\n')[1]
    assert not any(x.startswith('CALL ') for x in body.splitlines()) and \
        'WRITE Z2 CALL REACHED\nLISTALC STATUS\nFREE F(CEEOPTS)' in body and f"&SYSDSN('@@HLQ@@.PACMAN.{pz}.CEEOPTS')" in body
assert audit_deck(render(cl, 'Z00000'), 'Z00000') == []
mg8 = zos_target.steps_of_deck(zos_target._mvs['g8_clist_steps']('@@HLQ@@.PACMAN'))['G8CLS']
assert cst['G8CLS'].split('//SYSUT1   DD DATA,DLM=ZZ\n')[1] == mg8.split('//SYSUT1   DD DATA,DLM=ZZ\n')[1]
mhs = zos_target.steps_of_deck(md.hs_steps('@@HLQ@@.PACMAN.R20', 'PACZ2D'))
for s, p in (('HSCLS1', 'Z4HSY'), ('HSCLS2', 'Z4HSN')):
    a_ = cst[s].split('DLM=ZZ\n')[1]
    b_ = mhs[s].split('DLM=ZZ\n')[1].replace('@@HLQ@@.PACMAN.R20.HSCL', f'@@HLQ@@.PACMAN.{p}')
    assert a_ == b_, s
assert CLK.g8_want() == ['TSO AI1 1 NAAAPAAARAA01NP', 'TSO AI1 1 NAAAPAAARAC01NP', 'TSO AI1 1 NAAAPAAARAA01FS',
                         'TSO AI1 1 NAAAPAAATAX05NP']
W, Y = CLK.WORK, CLK.YES
good = ['READY', f"  EXEC '{W}(PARMS)'"] + [f'G8PARM={p}=' for p in CLK.g8_want()] + [
    f"  EXEC '{W}(HSCLY)'", '--DDNAME---DISP--', f'{Y}(HISCORE)', '  PACHS    KEEP', 'HSCL END',
    f"  EXEC '{W}(HSCLN)'", '--DDNAME---DISP--', 'NULLFILE  PACHS', 'HSCL END', 'READY',
    f"  EXEC '{W}(Z2RUN)' 'Z2Y'", 'Z2 CALL REACHED', '--DDNAME---DISP--', 'NULLFILE  SYSIN', CLK.CEY,
    '  CEEOPTS  KEEP', '--DDNAME---DISP--', 'NULLFILE  SYSIN', 'Z2 END', 'Z2RC=0', 'READY',
    f"  EXEC '{W}(Z2RUN)' 'Z2N'", CLK.MSG_MISSING, 'Z2RC=8', 'READY',
    f"  ALLOC F(CEEOPTS) DA('{W}(PARMS)') SHR", 'READY', f"  EXEC '{W}(Z2RUN)' 'Z2Y'",
    'IKJ56861I  FILE CEEOPTS NOT ALLOCATED, FILE IN USE', CLK.MSG_EXISTS, 'Z2RC=8', 'READY', '  LISTALC STATUS',
    '--DDNAME---DISP--', f'{W}(PARMS)', '  CEEOPTS  KEEP', 'READY', '  FREE F(CEEOPTS)', 'READY', 'END']
assert all(v for _, v in CLK.tmp_check(good)), CLK.tmp_check(good)
bad_tmp = {
    'wrong PARM': [l.replace('A01FS', 'A01NS') for l in good],
    'present path DUMMY': [l if l != f'{Y}(HISCORE)' else 'NULLFILE  PACHS' for l in good],
    'missing path allocated': [l if l != 'NULLFILE  PACHS' else f'{CLK.NO}(HISCORE)' for l in good],
    'no HSCL END': good[:good.index('HSCL END')] + good[good.index('HSCL END') + 1:],
    'IKJ56 message': good[:-1] + ['IKJ56228I DATA SET NOT IN CATALOG'] + good[-1:],
    'order swapped': [l.replace('(HSCLY)', '(TMPX)').replace('(HSCLN)', '(HSCLY)').replace('(TMPX)', '(HSCLN)')
                      for l in good],
    'Z2 case 1: CEEOPTS left after the FREE': good[:good.index('Z2 END')] + [CLK.CEY, '  CEEOPTS  KEEP']
    + good[good.index('Z2 END'):],
    'Z2 case 2: RC 0': [l if l != 'Z2RC=8' else 'Z2RC=0' for l in good],
    'Z2 case 2: CALL reached': good[:good.index(CLK.MSG_MISSING)] + ['Z2 CALL REACHED']
    + good[good.index(CLK.MSG_MISSING):],
    'Z2 case 3: CALL reached': good[:good.index(CLK.MSG_EXISTS)] + ['Z2 CALL REACHED'] + good[good.index(CLK.MSG_EXISTS):],
    'Z2 case 3: DD replaced by the project dataset': [l if l != f'{W}(PARMS)' else CLK.CEY for l in good],
    'Z2 case 3: DD lost': [l for l in good if l != f'{W}(PARMS)' and l != '  CEEOPTS  KEEP' or good.index(l) < 40],
    'IKJ56 outside case 3': good[:good.index('Z2RC=0')] + ['IKJ56228I DATA SET NOT IN CATALOG']
    + good[good.index('Z2RC=0'):],
    'unrelated IKJ in case 3': good[:good.index(CLK.MSG_EXISTS)] + ['IKJ56228I DATA SET Z00000.X NOT IN CATALOG']
    + good[good.index(CLK.MSG_EXISTS):],
    'cleanup FREE failed': good[:-1] + ['IKJ56247I FILE CEEOPTS NOT FREED, IS NOT ALLOCATED'] + good[-1:],
}
for why, ls in bad_tmp.items():
    assert not all(v for _, v in CLK.tmp_check(ls)), why
print('PACZ4CL: generated deck, only Z4CL.T1 / Z4HSY.DATA / Z4CEY.CEEOPTS (no DATA, no DELETE, no PACMAIN), MVS test '
      'CLISTs exactly (two prefixes instead of a DELETE), Z2 = the only change to the 2.0 CLIST and verbatim in its 3 '
      'cases, G8PARM = oracle 307, TMP-output rules pass the expected shape and fail '
      f'{len(bad_tmp)} wrong shapes: PASS')

# 15. ZOS-4 PACZ4LE (LE runtime-option diagnostic, ZOS-1 probes only): the generated deck (no Pac-Man, no write, STEPLIB
#     only); the step rules accept the designed outcomes and fail on the other side of each decision (a CEEOPTS win in
#     D3, installation values in D2, the arguments/options split reversed)
import zos_le_check as LEK  # noqa: E402
le = (R / 'jcl/zos/PACZ4LE.jcl').read_text()
with tempfile.TemporaryDirectory() as t:
    subprocess.run([sys.executable, str(R / 'tools/make_deck.py'), '--target', 'zos', 'Z4LE', '--out',
                    str(Path(t) / 'l.jcl')], check=True, capture_output=True)
    assert (Path(t) / 'l.jcl').read_text() == le, 'PACZ4LE.jcl is not the generated deck'
assert set(re.findall(r'DSN=([\w@.]+)', le)) == {'@@HLQ@@.PACMAN.LOAD'} and 'PACZ2D' not in le and 'PACMAIN' not in le
assert re.findall(r'PGM=(\w+)', le) == ['ZHELLO31', 'ZHELLO24', 'ZHELLO31']
assert audit_deck(render(le, 'Z00000'), 'Z00000') == []


def le_out(arg, tam, where, opts):
    z = ['ZH PARMLEN=%03d' % len(arg), 'ZH PARM=' + arg, f'ZH TAM   =000000000{tam}', f'ZH BSM   =000000000{tam}',
         f'ZH PARM1 =0000299520 {where[0]}', 'ZH CSECT =0000036416 BELOW', f'ZH SAVEA =0000155696 {where[1]}']
    return z + ['', 'LAST WHERE SET              OPTION'] + [f'{s:<28}{o}' for s, o in opts]


inst, inv, cee = 'Installation default', 'Invocation command', 'DD:CEEOPTS'
d1 = le_out('ZHARG', 1, ('ABOVE', 'ABOVE'), [(inst, 'ALL31(ON)'), (inst, 'CBLOPTS(ON)'), (inv, 'RPTOPTS(ON)'),
                                            (inst, 'STACK(128K,128K,ANYWHERE,KEEP,512K,128K)')])
d2 = le_out('ZHARG', 0, ('BELOW', 'BELOW'), [(cee, 'ALL31(OFF)'), (inst, 'CBLOPTS(ON)'), (inv, 'RPTOPTS(ON)'),
                                            (cee, 'STACK(128K,128K,BELOW,KEEP,512K,128K)')])
d3 = le_out('ZHARG', 1, ('ABOVE', 'ABOVE'), [(cee, 'ALL31(ON)'), (inst, 'CBLOPTS(ON)'), (inv, 'RPTOPTS(ON)'),
                                            (inv, 'STACK(128K,128K,ANYWHERE,KEEP,512K,128K)')])
for s, o in (('D1', d1), ('D2', d2), ('D3', d3)):
    assert all(v for _, v in LEK.step_check(s, o)), (s, LEK.step_check(s, o))
assert not all(v for _, v in LEK.step_check('D3', [l.replace(inv + ' ' * 10 + 'STACK', 'x') for l in d3]
                                            [:-1] + [f'{cee:<28}STACK(128K,128K,BELOW,KEEP,512K,128K)']))
assert all(v for _, v in LEK.step_check('D3', [l.replace('SAVEA =0000155696 ABOVE', 'SAVEA =0000155696 BELOW')
                                              for l in d3])), 'D3: SAVEA is information only'
assert all(v for _, v in LEK.step_check('D1', [l.replace('SAVEA =0000155696 ABOVE', 'SAVEA =0000155696 BELOW')
                                              for l in d1])), 'D1 with ANYWHERE: SAVEA is information only'
assert not all(v for _, v in LEK.step_check('D3', [l.replace('ZH PARM=ZHARG', 'ZH PARM=ZHARGX') for l in d3]))
assert not all(v for _, v in LEK.step_check('D2', [l.replace('SAVEA =0000155696 BELOW', 'SAVEA =0458174512 ABOVE')
                                                   for l in d2])), 'D2 stays strict on SAVEA'
assert not all(v for _, v in LEK.step_check('D2', [l.replace(cee, inst) for l in d2]))
assert not all(v for _, v in LEK.step_check('D1', [l.replace('ZH PARM=ZHARG', 'ZH PARM=RPTOPTS(ON)')
                                                   .replace('PARMLEN=005', 'PARMLEN=011') for l in d1]))
# the real D1 SYSOUT of PACZ4LE JOB03693 (fixture = the raw file, SHA-256 in docs/evidence/
# zos4-pacz4le-JOB03693-raw.sha256): this system reports the no-override origin as 'IBM-supplied default' (the first
# check assumed 'Installation ...' and gave a false FAIL); CEEOPTS / invocation / any other origin still fails D1
from zos_listing import asa  # noqa: E402
fx = R / 'tests/fixtures/zos/JOB03693-103-D1-SYSOUT.txt'
assert hashlib.sha256(fx.read_bytes()).hexdigest() == \
    'b91fba786e5cef54fbe80c908f3016ea20096a4f0e2cb7d9550d5369c2c88df9', 'fixture is not the JOB03693 raw file'
real1 = asa(fx.read_text().splitlines())
assert all(v for _, v in LEK.step_check('D1', real1)), LEK.step_check('D1', real1)
zh1, rep1 = LEK.readings(real1)
assert rep1['ALL31'] == ('IBM-supplied default', 'ON') and rep1['STACK'][0] == 'IBM-supplied default'
for opt in ('ALL31', 'STACK'):
    for other in ('DD:CEEOPTS', 'Invocation command', 'Programmer default', 'IBM-supplied defaultX'):
        k = next(i for i, l in enumerate(real1) if LEK.OPT.match(l) and LEK.OPT.match(l).group(2) == opt
                 and LEK.OPT.match(l).group(1).strip() == 'IBM-supplied default' and i > 30)
        bad1 = real1[:k] + [real1[k].replace('IBM-supplied default', other.ljust(20))] + real1[k + 1:]
        assert not all(v for _, v in LEK.step_check('D1', bad1)), (opt, other)
print('PACZ4LE: generated deck (ZHELLO31 / ZHELLO24 / ZHELLO31, STEPLIB only, no Pac-Man), step rules accept the '
      'designed outcomes and fail a CEEOPTS win in D3, installation values in D2, a reversed arguments/options split; '
      'real JOB03693 D1 (IBM-supplied default) accepted, CEEOPTS / invocation / other origins fail: PASS')

# 16. ZOS-4 Z2-only attempts. PACZ4Z2 (T2, JOB03829) frozen as submitted; its real TMP output (fixture = the raw file)
#     passes cases 1-2 and fails exactly the controlled-error criteria of case 3 (the handler did not regain control).
#     PACZ4Z3 (T3): the generated deck with the current Z2 (CONTROL NOFLUSH / FLUSH around the ERROR routine + ALLOC)
#     verbatim, T3 names, CONTROL LIST, DYNAMNBR=200; the T3 rules accept the designed outcome and fail each required
#     negative (handler not firing, no message, no Z2RC, SYSIN / SYSOUT left, original DD changed / lost, CALL reached)
import zos_z2_check as Z2K  # noqa: E402
z2rec = (R / 'jcl/zos/PACZ4Z2.jcl').read_text()
sub2 = R / 'build/zos/PACZ4Z2-JOB03829/deck.jcl'
if sub2.exists():
    assert render(z2rec, 'Z00000') == sub2.read_text(), 'PACZ4Z2.jcl is not the deck JOB03829 ran'
fx = R / 'tests/fixtures/zos/JOB03829-CLT-SYSTSPRT.txt'
assert hashlib.sha256(fx.read_bytes()).hexdigest() == \
    'db07714427816c4e20d34fb74e540397c5b8dda2d9f3afb798e00a015690b112', 'fixture is not the JOB03829 raw file'
r2 = Z2K.tmp_check([l[1:].rstrip() for l in fx.read_text().splitlines()], 'T2')
failed2 = [k for k, v in r2 if not v]
assert failed2 == ['case 3: the ERROR routine regained control (ALREADY ALLOCATED message after the refusal)',
                   'case 3: Z2RC=8 after the message',
                   'case 3: SYSIN and SYSOUT not allocated after the controlled failure'], failed2
z3d = (R / 'jcl/zos/PACZ4Z3.jcl').read_text()
with tempfile.TemporaryDirectory() as t:
    subprocess.run([sys.executable, str(R / 'tools/make_deck.py'), '--target', 'zos', 'Z4Z3', '--out',
                    str(Path(t) / 'z.jcl')], check=True, capture_output=True)
    assert (Path(t) / 'z.jcl').read_text() == z3d, 'PACZ4Z3.jcl is not the generated deck'
z3s = zos_target.steps_of_deck(z3d)
assert list(z3s) == Z2K.STEPS and 'DELETE' not in z3d and 'PACMAN.DATA' not in z3d and 'PACMAIN' not in z3d
assert set(re.findall(r'DSN=([\w@.]+)', z3d)) == {'@@HLQ@@.PACMAN.Z4CL.T3', '@@HLQ@@.PACMAN.Z4CY3.CEEOPTS'}
assert '//CLT      EXEC PGM=IKJEFT01,COND=(0,NE),DYNAMNBR=200' in z3d and audit_deck(render(z3d, 'Z00000'), 'Z00000') == []
assert 'G8PARM' not in z3d and 'HSCL' not in z3d
for s, pz in (('Z2CLS1', 'Z4CY3'), ('Z2CLS2', 'Z4CN3')):
    body = z3s[s].split('DLM=ZZ\n')[1]
    blk = [l.replace('@@PREFIX@@', f'@@HLQ@@.PACMAN.{pz}') for l in cz[zi:zc]]
    assert body.startswith('PROC 0\nCONTROL LIST\n') and '\n'.join(blk) in body
    assert 'CONTROL NOFLUSH\nERROR DO' in body and 'ERROR OFF\nCONTROL FLUSH\n' in body
    assert not any(x.startswith('CALL ') for x in body.splitlines())
_, W3, CY3, CN3 = Z2K.names('T3')
LA = '  LISTALC STATUS'
g3 = [f"  EXEC '{W3}(Z2RUN)' 'Z2Y'", 'ALLOC F(SYSIN) DUMMY REUSE', 'ALLOC F(SYSOUT) DUMMY REUSE',
      f"ALLOC F(CEEOPTS) DA('{CY3}') SHR", 'Z2 CALL REACHED', 'LISTALC STATUS', '--DDNAME---DISP--', 'NULLFILE  SYSIN',
      'NULLFILE  SYSOUT', CY3, '  CEEOPTS  KEEP', 'FREE F(CEEOPTS)', 'LISTALC STATUS', '--DDNAME---DISP--',
      'NULLFILE  SYSIN', 'NULLFILE  SYSOUT', 'FREE F(SYSIN SYSOUT)', 'Z2 END', 'Z2RC=0', 'READY',
      f"  EXEC '{W3}(Z2RUN)' 'Z2N'", 'ALLOC F(SYSIN) DUMMY REUSE', 'ALLOC F(SYSOUT) DUMMY REUSE',
      f'PACMAN: {CN3} MISSING, GAME NOT STARTED', 'FREE F(SYSIN SYSOUT)', 'Z2RC=8', 'READY',
      f"  ALLOC F(CEEOPTS) DA('{W3}(Z2N)') SHR", 'READY', LA, '--DDNAME---DISP--', 'Z00000.PACZ4Z3.JOB1.D1.?',
      '  SYSTSPRT DELETE', f'{W3}(Z2N)', '  CEEOPTS  KEEP', 'READY',
      f"  EXEC '{W3}(Z2RUN)' 'Z2Y'", 'ALLOC F(SYSIN) DUMMY REUSE', 'ALLOC F(SYSOUT) DUMMY REUSE',
      f"ALLOC F(CEEOPTS) DA('{CY3}') SHR", f'IKJ56246I DATA SET {CY3} NOT ALLOCATED, FILE IN USE', Z2K.MSG_EXISTS,
      'FREE F(SYSIN SYSOUT)', 'Z2RC=8', 'READY', LA, '--DDNAME---DISP--', 'Z00000.PACZ4Z3.JOB1.D1.?',
      '  SYSTSPRT DELETE', f'{W3}(Z2N)', '  CEEOPTS  KEEP', 'READY', '  FREE F(CEEOPTS)', 'READY', 'END']
assert all(v for _, v in Z2K.tmp_check(g3, 'T3')), [k for k, v in Z2K.tmp_check(g3, 'T3') if not v]
k3 = max(i for i, l in enumerate(g3) if l == f"  EXEC '{W3}(Z2RUN)' 'Z2Y'")
m3 = g3.index(Z2K.MSG_EXISTS)
post3 = max(i for i, l in enumerate(g3) if l == LA)
neg3 = {
    'handler not firing (JOB03829 shape)': g3[:m3] + ['READY'] + g3[g3.index('READY', m3) + 1:],
    'no ALREADY ALLOCATED message': g3[:m3] + g3[m3 + 1:],
    'no Z2RC': g3[:m3 + 2] + g3[m3 + 3:],
    'SYSIN / SYSOUT left allocated': g3[:post3 + 6] + ['NULLFILE  SYSIN', 'NULLFILE  SYSOUT'] + g3[post3 + 6:],
    'original CEEOPTS changed': g3[:post3 + 4] + [CY3] + g3[post3 + 5:],
    'original CEEOPTS lost': g3[:post3 + 4] + g3[post3 + 6:],
    'CALL reached on case 3': g3[:m3] + ['Z2 CALL REACHED'] + g3[m3:],
    'refusal not FILE IN USE': [l if not l.startswith('IKJ56246I') else 'IKJ56228I DATA SET X NOT IN CATALOG' for l in g3],
    'ALLOC not reached': [l for i, l in enumerate(g3) if not (i > k3 and l.startswith('ALLOC F(CEEOPTS)'))],
}
for why, ls in neg3.items():
    assert not all(v for _, v in Z2K.tmp_check(ls, 'T3')), why
print('Z2 attempts: PACZ4Z2 frozen as JOB03829 ran; its real output fails exactly the 3 controlled-error criteria of '
      'case 3; PACZ4Z3 generated (current Z2 with CONTROL NOFLUSH / FLUSH verbatim, T3 names, CONTROL LIST, DYNAMNBR=200, '
      f'no G8 / HS / DATA / DELETE / PACMAIN); T3 rules accept the designed outcome and fail {len(neg3)} negatives: PASS')

# 17. ZOS-4 PACZ4INS (first promotion, for review): the generated deck writes only CLIST(PACSRCT), the new CEEOPTS and
#     LOAD(PACMAIN) (via a temporary PDSE: IEBCOPY rename, no binder, no DELETE, PACZ2D read only); the two smoke steps
#     are the REL20 RUN1 / TSO2 steps verbatim with PGM=PACMAIN; the rendered z/OS CLIST = src/zos for Z00000.PACMAN,
#     lines <= 72; the smoke rules accept the real z/OS outputs of RUN1 (C1) and TSO2 (C7) and fail a mutation
import zos_ins_check as INS  # noqa: E402
ins = (R / 'jcl/zos/PACZ4INS.jcl').read_text()
with tempfile.TemporaryDirectory() as t:
    subprocess.run([sys.executable, str(R / 'tools/make_deck.py'), '--target', 'zos', 'Z4INS', '--out',
                    str(Path(t) / 'i.jcl')], check=True, capture_output=True)
    assert (Path(t) / 'i.jcl').read_text() == ins, 'PACZ4INS.jcl is not the generated deck'
ist = zos_target.steps_of_deck(ins)
assert list(ist) == INS.STEPS and 'DELETE' not in ins and 'PACMAN.DATA' not in ins
assert 'IEWBLINK' not in ins and 'PGM=PACZ2D' not in ins and 'NAME ' not in ins           # no rebind, PACZ2D not run
assert set(re.findall(r'DSN=([^,\s]+)', ins)) == {'@@HLQ@@.PACMAN.CLIST(PACMAN)', '@@HLQ@@.PACMAN.CLIST(PACSRCT)',
                                                   '@@HLQ@@.PACMAN.CEEOPTS', '@@HLQ@@.PACMAN.LOAD', '&&PROMO'}
assert 'SELECT MEMBER=((PACZ2D,PACMAIN))' in ist['PROM1'] and 'SELECT MEMBER=PACMAIN\n' in ist['PROM2']
assert 'DSN=&&PROMO,DISP=(NEW,PASS),DSNTYPE=LIBRARY' in ist['PROM1'] and 'DSN=&&PROMO,DISP=(OLD,PASS)' in ist['PROM2']
assert '\nALL31(OFF),STACK(,,BELOW)\n' in ist['CEEOPT'] and 'DISP=(NEW,CATLG,CATLG)' in ist['CEEOPT']
assert audit_deck(render(ins, 'Z00000'), 'Z00000') == []
rel_main = zos_target.steps_of_deck(md.build('REL20', '@@HLQ@@.PACMAN', 'PACMAIN'))
for s in zos_target.Z4INS_SMOKE:
    assert ist[s] == rel_main[s] and f'//{s:<8} EXEC PGM=PACMAIN,COND=(0,NE)' in ist[s], s
    assert ist[s].replace('PGM=PACMAIN', 'PGM=PACZ2D') == zos_target.steps_of_deck(
        md.build('REL20', '@@HLQ@@.PACMAN', 'PACZ2D'))[s], s                               # = the accepted ZOS-2 step
rc = zos_target.zos_clist_text('Z00000.PACMAN')
assert '@@PREFIX@@' not in rc and all(len(l) <= 72 for l in rc.splitlines())
assert rc == (R / 'src/zos/PACMAN.clist').read_text().replace('@@PREFIX@@', 'Z00000.PACMAN')
from zos_classic_check import model as cmodel  # noqa: E402
o307 = json.load(gzip.open(R / 'tests/oracle20/307-PACREL20.json.gz'))
real = {'RUN1': zos_runs(R / 'build/zos/PACZ2C1-JOB08984')[2]['RUN1'],
        'TSO2': zos_runs(R / 'build/zos/PACZ2C7-JOB09031')[2]['TSO2']}
smk = {s: dict(real[s], pgm='PACMAIN') for s in real}
nb, msgs = compare(o307, smk, {'PACMAIN': 'PACMAIN'}, subset=True)
assert nb == 0 and all(cmodel(s, smk[s]['lines']) is None for s in smk), msgs
mut = dict(smk, TSO2=dict(smk['TSO2'], lines=smk['TSO2']['lines'][:-1] + ['LIVES 9']))
assert compare(o307, mut, {'PACMAIN': 'PACMAIN'}, subset=True)[0] == 1 and cmodel('TSO2', mut['TSO2']['lines'])
print('PACZ4INS: generated deck (PACSRCT copy, new CEEOPTS, PACZ2D -> PACMAIN by IEBCOPY through a temporary PDSE, no '
      'binder / DELETE / DATA), smoke steps = REL20 RUN1 / TSO2 with PGM=PACMAIN, rendered z/OS CLIST = src/zos; '
      'smoke rules pass the real z/OS RUN1 / TSO2 outputs and fail a mutation: PASS')


# 18. ZOS-4 Z3 (proposed, not installed): src/zos/PACMAN.clist = the installed Z2 source (8724464, rendered = the member
#     PACZ4INS installed, SHA-256 2e9895dc...) with only the 2.0 SYSIN line replaced by the frozen Z3 block (ATTRIB +
#     USING, SYSOUT / Z2 / CEEOPTS untouched); an independent model of the block's control flow: every outcome of
#     ATTRIB / ALLOC / FREE ATTRLIST either continues with SYSIN allocated and no attribute list left, or ends RC 8 before
#     any CALL, freeing only what this CLIST created (a list it did not create is never freed)
import difflib  # noqa: E402
import zos_z3_install as Z3I  # noqa: E402
z3src = zos_c2.z5_strip((R / 'src/zos/PACMAN.clist').read_text())      # the Z5 lines (ZOS-6, section 22) put back
z2src = subprocess.run(['git', 'show', f'{Z3I.Z2_REF}:./src/zos/PACMAN.clist'], cwd=R, capture_output=True,
                       check=True).stdout.decode()
assert zos_c2.z3_strip(z3src) == z2src, 'Z3 changes more than the SYSIN line'
assert hashlib.sha256(Z3I.z2_installed_bytes()).hexdigest() == Z3I.Z2_SHA
d = [l for l in difflib.unified_diff(z2src.splitlines(), z3src.splitlines(), lineterm='', n=0)
     if l[:1] in '+-' and l[:3] not in ('---', '+++')]
assert d == ['-' + zos_c2.Z3_OLD] + ['+' + l for l in zos_c2.Z3_BLOCK], d
assert all(len(l.replace('@@PREFIX@@', 'Z00000.PACMAN')) <= 72 for l in z3src.splitlines())
assert 'ALLOC F(SYSOUT) DA(*) REUSE' in z3src.splitlines() and z3src.count('Z3SIATTR') == 3
assert 'LRECL' not in ''.join(l for l in z3src.splitlines() if l.startswith('ALLOC') or l.startswith('  ALLOC'))
ddn = set(re.findall(r'\bF\(([A-Z0-9@#$ ]+)\)', z3src)) | {'STEPLIB', 'SYSTSPRT', 'SYSTSIN', 'SYSPRINT'}
assert not any('Z3SIATTR' in x.split() for x in ddn) and not 'Z3SIATTR'.startswith('PAC')
zb = zos_c2.Z3_BLOCK


def run_z3(rc):
    """Interpret the Z3 block (exactly its statement forms) with command return codes rc {ATTRIB, ALLOC, FREEA, FREES}
    (missing = 0); returns (commands issued, exit code or None = falls through to SYSOUT / Z2 / CALL)."""
    v, out, prog, i, handler, flush = {}, [], zb, 0, None, True

    def val(x):
        return v[x] if x.startswith('&') else x

    def cond(c):
        terms = c.split(' AND ')
        return all((val(a) == val(b)) if op == '=' else (val(a) != val(b))
                   for a, op, b in (t.split() for t in terms))

    def cmd(c):
        out.append(c)
        k = {'ATTRIB': 'ATTRIB', 'ALLOC': 'ALLOC'}.get(c.split()[0]) or ('FREEA' if 'ATTRLIST' in c else
                                                                         'FREES' if c.startswith('FREE') else None)
        r = rc.get(k, 0) if k else 0
        if r and handler:
            v['&LASTCC'] = str(r)
            for h in handler:
                stmt(h)

    def stmt(s):
        s = s.strip()
        m, f = re.match(r'SET (&\w+) = (\S+)$', s), re.match(r'IF (.+) THEN (?!DO$)(.+)$', s)
        if m:
            v[m.group(1)] = val(m.group(2))
        elif f:
            if cond(f.group(1)):
                stmt(f.group(2))
        elif s in ('RETURN',) or s.startswith('/*') or s.startswith('CONTROL'):
            pass
        elif s.startswith('EXIT CODE('):
            raise SystemExit(int(s[10:-1]))
        else:
            cmd(s)

    while i < len(prog):
        s = prog[i].strip()
        if s == 'ERROR DO':
            j = prog.index('END', i)
            handler, i = prog[i + 1:j], j + 1
            continue
        if s == 'ERROR OFF':
            handler, i = None, i + 1
            continue
        m = re.match(r'IF (.+) THEN (.+)$', s)
        if m:
            if m.group(2) == 'DO':
                j = prog.index('END', i)
                body, i = prog[i + 1:j], j + 1
            else:
                body, i = [m.group(2)], i + 1
            if cond(m.group(1)):
                try:
                    for b in body:
                        stmt(b)
                except SystemExit as e:
                    return out, e.code
            continue
        stmt(s)
        i += 1
    return out, None


ATTR = 'ATTRIB Z3SIATTR RECFM(F) LRECL(80) BLKSIZE(80)'
ALLO = 'ALLOC F(SYSIN) DA(*) REUSE USING(Z3SIATTR)'
FRA, FRS = 'FREE ATTRLIST(Z3SIATTR)', 'FREE F(SYSIN)'
MSG = 'WRITE PACMAN: SYSIN NOT ALLOCATED (Z3, RC &Z), GAME NOT STARTED'
z3cases = {     # outcome -> (commands issued, exit)
    'all succeed: SYSIN fixed 80, list freed, continue': ({}, [ATTR, ALLO, FRA], None),
    'ATTRIB fails (e.g. the name in use): nothing freed, RC 8': ({'ATTRIB': 12}, [ATTR, MSG], 8),
    'ALLOC fails: only the list freed, RC 8': ({'ALLOC': 12}, [ATTR, ALLO, FRA, MSG], 8),
    'FREE ATTRLIST fails: SYSIN freed, RC 8': ({'FREEA': 12}, [ATTR, ALLO, FRA, MSG, FRS], 8),
    'ALLOC and FREE ATTRLIST fail: RC 8, SYSIN not freed': ({'ALLOC': 12, 'FREEA': 12}, [ATTR, ALLO, FRA, MSG], 8),
}
for why, (rcs, want, ex) in z3cases.items():
    got = run_z3(rcs)
    assert got == (want, ex), (why, got)
    assert (FRA in got[0]) == ('ATTRIB' not in rcs), why                   # the list freed iff this CLIST created it
assert ''.join(zb[:3]).count('/*') == 3 and z3src.index('\n'.join(zb)) < z3src.index('ALLOC F(SYSOUT) DA(*) REUSE') \
    < z3src.index('/* Z2 (ZOS-4)') < z3src.index("CALL '")
print(f'Z3: src/zos = installed Z2 source (8724464 / 2e9895dc) with only the SYSIN line -> the frozen ATTRIB + USING '
      f'block; SYSOUT / Z2 untouched; control-flow model: {len(z3cases)} outcomes, list freed only if created, RC 8 '
      'before SYSOUT / Z2 / CALL on any failure: PASS')

# 19. ZOS-5 live postcheck tools/zowe/zos5_live_check.py (before the session): the model = the frozen oracle 310 blocks
#     TSD45 / TSD48 / TSD28 for the frozen cards; the synthetic session trace (tests/zos5_fixture.py, committed fixture
#     regenerated byte for byte) passes; TN3270E framing fails closed (data type, flags, truncated, SEQ-NUMBER,
#     responses, telnet commands, bytes after the last EOR); game-level negatives (model byte, cards, redraw keys,
#     extra startup read, no colour, error / *** text, no READY, audit); another reply size = model-identical, not PASS
import zos5_live_check as Z5  # noqa: E402
import zos5_fixture as FX  # noqa: E402
o310 = json.load(gzip.open(R / 'tests/oracle20/310-PACBLGP2.json.gz'))['stream']
sw310 = [i for i, l in enumerate(o310) if l.startswith('TSX SWITCH')]


def tsd_block(k):
    j, fr = sw310[k], []
    while o310[j].rstrip() not in ('WIN', 'LOST', 'QUIT', 'EOF'):
        m = re.match(r'TSD FRAME LEN(\d{4})$', o310[j])
        j += 1
        if m:
            h = ''
            while o310[j].startswith('TSD ') and not o310[j].startswith('TSD FRAME'):
                h += o310[j][4:].strip()
                j += 1
            fr.append(bytes.fromhex(h))
    return o310[sw310[k]], fr, o310[j:j + 4]


for k, (name, case, cmd, blk) in zip((44, 47, 27), Z5.GAMES):
    sx, fr, endl = tsd_block(k)
    assert sx == ('TSX SWITCH 7E 120X027' if cmd == 0x7E else 'TSX SWITCH F5 080X024'), (blk, sx)
    assert Z5.model(Z5.frozen_cards(case), (1, 1, 1), 'W' if cmd == 0x7E else 'D') == fr, blk
    assert endl == Z5.END_LINES[case], (blk, endl)
fxt = FX.render(FX.session())
assert fxt == (R / 'tests/fixtures/zos5/session.trace').read_text(), 'fixture not regenerated identically'
rep = Z5.check(fxt)
assert rep['verdict'] == 'PASS' and [g['ticks'] for g in rep['games']] == [4, 0, 0] and rep['seq'] == '+1'
assert sum(r[3] == FX.line('***') for r in FX.session()) == 3      # ISPF's *** after the end lines: accepted
assert rep['games'][0]['reply'] == Z5.Q.rec('dyn') and rep['games'][2]['reply'] is None


def z5(recs=None, text=None):
    try:
        return Z5.check(text if text is not None else FX.render(recs))['verdict']
    except Z5.Fail as ex:
        return 'FAIL: ' + str(ex)


def mut(f):
    r = [list(x) for x in FX.session()]
    f(r)
    return r


def hidx(r, pred, n=0):
    return [i for i, x in enumerate(r) if pred(x)][n]


neg5 = {
    'host DATA-TYPE SSCP-LU (07)': (mut(lambda r: r[hidx(r, lambda x: x[0] == '<', 5)].__setitem__(
        2, bytes([7, 0, 0]) + r[hidx(r, lambda x: x[0] == '<', 5)][2][3:])), 'not 3270-DATA'),
    'host RESPONSE-FLAG 03': (mut(lambda r: r[hidx(r, lambda x: x[0] == '<', 3)].__setitem__(
        2, bytes([0, 0, 3]) + r[hidx(r, lambda x: x[0] == '<', 3)][2][3:])), 'not 3270-DATA'),
    'record shorter than the header': (mut(lambda r: r[hidx(r, lambda x: x[0] == '<', 4)].__setitem__(
        slice(2, 4), [b'\x00\x00', b'\xf1'])), 'no TN3270E header'),
    'empty 3270-DATA payload': (mut(lambda r: r[hidx(r, lambda x: x[0] == '<', 4)].__setitem__(3, b'')),
                                'not 3270-DATA'),
    'SEQ-NUMBER gap': (mut(lambda r: r[hidx(r, lambda x: x[0] == '<', 9)].__setitem__(
        2, b'\x00\x00\x00\x03\x00')), 'SEQ-NUMBER'),
    'ALWAYS-RESPONSE never answered': (mut(lambda r: r[hidx(r, lambda x: x[0] == '<', 6)].__setitem__(
        2, b'\x00\x00\x02' + r[hidx(r, lambda x: x[0] == '<', 6)][2][3:])), 'never answered'),
    'model byte changed in a partial': (mut(lambda r: r[hidx(r, lambda x: x[0] == '<', 8)].__setitem__(
        3, r[hidx(r, lambda x: x[0] == '<', 8)][3][:-1] + b'\x40')), 'differs from the model'),
    'typed L for the first R': (mut(lambda r: r[hidx(r, lambda x: x[0] == '>' and x[3][6:] == b'\xd9')].__setitem__(
        3, FX.enter('L'))), 'not the frozen MOVES cards'),
    'extra startup read before the first screen': (mut(lambda r: r.insert(hidx(r, lambda x: x[3][:1] == b'\x88') + 1,
                                                                          ['>', 0, bytes(5), FX.enter('')])),
                                                   'inbound records between the query'),
    '*** before the end lines': (mut(lambda r: r.insert(hidx(r, lambda x: x[3] == FX.line('QUIT')),
                                                        ['<', 0, bytes(5), FX.line('***')])), 'after the end screen'),
    'IKJ message after the end lines': (mut(lambda r: r.insert(hidx(r, lambda x: x[3] == FX.line('***')),
                                                               ['<', 0, bytes(5), FX.line('IKJ56500I COMMAND NOT FOUND')])),
                                        'after the end screen'),
    'IKJ message in the shell between games': (mut(lambda r: r.insert(hidx(r, lambda x: x[3] == FX.SHELL_PANEL) + 1,
                                                                      ['<', 0, bytes(5), FX.line('IKJ56500I X')])),
                                               'outside the game stream'),
    'no ISPF Command Shell after game A': (mut(lambda r: r.__delitem__(hidx(r, lambda x: x[3] == FX.SHELL_PANEL))),
                                           'ISPF Command Shell panel not found'),
    'LOGON text (audit)': (mut(lambda r: r.insert(1, ['<', 0, bytes(5), FX.line('LOGON Z00000')])), 'audit'),
}
for why, (recs, want) in neg5.items():
    for k, x in enumerate(r for r in recs if r[0] == '<'):           # keep SEQ-NUMBER +1 except where it is the point
        if why not in ('SEQ-NUMBER gap', 'record shorter than the header') and len(x[2]) == 5:
            x[2] = x[2][:3] + k.to_bytes(2, 'big')
    got = z5(recs)
    assert got.startswith('FAIL') and want in got, (why, got)
for why, kw, want in (('B redraw by PA2 without CLEAR', dict(b_redraw='PA2'), 'CLEAR then PA2'),
                      ('C redraw by PA2', dict(c_redraw='PA2'), 'empty ENTER'),
                      ('reply with no colour', dict(reply=Z5.Q.sf_cut(Z5.Q.rec('dyn'), Z5.Q.rec('dyn').find(b'\x81\x86') - 2)),
                       'no colour')):
    got = z5(FX.session(**kw))
    assert got.startswith('FAIL') and want in got, (why, got)
# framing at byte level: IAC IAC = X'FF'; timing marks accepted between records only; other telnet commands, bytes
# after the last EOR and a negative / unsolicited RESPONSE fail
blk = [('<', '', bytes.fromhex('0000000000f1c3ffff40ffef'))]
assert Z5.telnet(blk)[0][0][3] == bytes.fromhex('0000000000f1c3ff40')
assert Z5.telnet([('<', '', bytes.fromhex('fffd06') + blk[0][2])])[1] == 1
for bad in ('fffb00', '0000ff', '00000000'):
    try:
        Z5.telnet([('<', '', blk[0][2] + bytes.fromhex(bad))])
        raise AssertionError(bad)
    except Z5.Fail:
        pass
ok_resp = mut(lambda r: (r[hidx(r, lambda x: x[0] == '<', 6)].__setitem__(
    2, b'\x00\x00\x02' + r[hidx(r, lambda x: x[0] == '<', 6)][2][3:]),
    r.insert(hidx(r, lambda x: x[0] == '<', 6) + 1, ['>', 0, b'\x02\x00\x00' + bytes([0, 6]), b'\x00'])))
assert z5(ok_resp) == 'PASS', z5(ok_resp)
# RFC 2355 8.1.2: REQUEST-FLAG is ignored outside DATA-TYPE REQUEST - the exact header z/OS sent (live trace T2),
# 00 01 02 00 1e on a host 3270-DATA record with a payload, answered by a positive RESPONSE: accepted
rq_ok = Z5.tn3270e([(0, '<', 't', bytes.fromhex('000102001e') + bytes.fromhex('f1c3114040')),
                    (1, '>', 't', bytes.fromhex('020100001e') + b'\x00')])
assert rq_ok[0] == [(0, '<', 't', bytes.fromhex('f1c3114040'))], rq_ok
for bad_rq in (bytes.fromhex('020100001e') + b'\x01', bytes.fromhex('020101001e') + b'\x00',
               bytes.fromhex('020100001f') + b'\x00'):                        # negative / flag / wrong SEQ: still FAIL
    try:
        Z5.tn3270e([(0, '<', 't', bytes.fromhex('000102001e') + b'\xf1\xc3'), (1, '>', 't', bad_rq)])
        raise AssertionError(bad_rq.hex())
    except Z5.Fail:
        pass
# negotiated CONTENTION-RESOLUTION (05, as z/OS in live trace T2): REQUEST-FLAG on host 3270-DATA = SDI (01) / KRI
# (02) only; normal BID 09 / 00 / 02, no payload, answered by exactly 02 00 00 SEQ 00; nothing else accepted
CRF = {0x00, 0x02, 0x04, 0x05}
D = bytes.fromhex('f1c3114040')


def tn(rs_, f=CRF):
    try:
        return Z5.tn3270e([(k, d_, 't', b) for k, (d_, b) in enumerate(rs_)], f)
    except Z5.Fail as ex:
        return 'FAIL: ' + str(ex)


def H(dt, rq, rsf, sq, p=D):
    return ('<', bytes([dt, rq, rsf]) + sq.to_bytes(2, 'big') + p)


def A(sq, rq=0, rsf=0, p=b'\x00'):
    return ('>', bytes([2, rq, rsf]) + sq.to_bytes(2, 'big') + p)


assert not isinstance(tn([H(0, 1, 2, 0x1e), A(0x1e)]), str)                      # SDI
assert not isinstance(tn([H(0, 3, 2, 0x1e), A(0x1e)]), str)                      # SDI + KRI
assert 'not 3270-DATA' in tn([H(0, 4, 2, 0x1e), A(0x1e)])                       # bit 04 on 3270-DATA
bid_ok = tn([H(0, 3, 2, 0x22), A(0x22), H(9, 0, 2, 0x23, b''), A(0x23), H(0, 3, 2, 0x24), A(0x24)])
assert not isinstance(bid_ok, str) and [x[3] for x in bid_ok[0]] == [D, D] and bid_ok[1] == '+1', bid_ok
for why, rs_, want in (
        ('BID with payload', [H(9, 0, 2, 0x23, b'\x00'), A(0x23)], 'BID'),
        ('BID RESPONSE-FLAG 01', [H(9, 0, 1, 0x23, b''), A(0x23)], 'BID'),
        ('BID RESPONSE-FLAG 00', [H(9, 0, 0, 0x23, b'')], 'BID'),
        ('SIGNAL BID (04)', [H(9, 4, 2, 0x23, b''), A(0x23)], 'BID'),
        ('BID never answered', [H(9, 0, 2, 0x23, b'')], 'never answered'),
        ('BID answered with another SEQ', [H(9, 0, 2, 0x23, b''), A(0x24)], 'RESPONSE'),
        ('BID answered negatively', [H(9, 0, 2, 0x23, b''), A(0x23, rsf=1, p=b'\x01')], 'RESPONSE'),
        ('BID answered with REQUEST-FLAG 01', [H(9, 0, 2, 0x23, b''), A(0x23, rq=1)], 'RESPONSE'),
        ('BID without CONTENTION-RESOLUTION', [H(9, 0, 2, 0x23, b''), A(0x23)], 'BID'),
        ('unknown host DATA-TYPE 01', [H(1, 0, 2, 0x23), A(0x23)], 'not 3270-DATA'),
        ('unknown host DATA-TYPE 0A', [H(0x0A, 0, 2, 0x23, b''), A(0x23)], 'not 3270-DATA'),
        ('BID out of the +1 host sequence', [H(0, 3, 2, 0x22), A(0x22), H(9, 0, 2, 0x25, b''), A(0x25),
                                             H(0, 3, 2, 0x23), A(0x23)], 'SEQ-NUMBER'),
        ('terminal 3270-DATA REQUEST-FLAG 01', [('>', bytes([0, 1, 0, 0, 0]) + b'\x7d')], 'plain 3270-DATA')):
    got = tn(rs_, CRF - {0x05} if why == 'BID without CONTENTION-RESOLUTION' else CRF)
    assert isinstance(got, str) and want in got, (why, got)
# z/OS TSO / VTAM answers CLEAR with one external write (live trace T2): accepted only exactly, once, in B between
# CLEAR and PA2; it is no PACMAN write (B still = TSD48 / the model); zero stays valid; everything else fails
def renum(r):
    k = 0
    for x in r:
        if x[0] == '<':
            x[2] = bytes(3) + k.to_bytes(2, 'big')
            k += 1
    return r


def put(at, rec=None, n=1):
    r = [list(x) for x in FX.session()]
    i = at(r)
    for _ in range(n):
        r.insert(i, ['<', 0, bytes(5), rec or Z5.TSO_CLEAR])
    return renum(r)


clr_i = lambda r: hidx(r, lambda x: x[3] == b'\x6d')                        # noqa: E731  B's CLEAR
pa2_i = lambda r: hidx(r, lambda x: x[3] == b'\x6e')                        # noqa: E731  B's PA2
ok_clr = Z5.check(FX.render(put(lambda r: clr_i(r) + 1)))
assert ok_clr['verdict'] == 'PASS' and ok_clr['games'][1]['tso_clear'] == 1, ok_clr['verdict']
assert ok_clr['games'][1]['writes'] == rep['games'][1]['writes'] and rep['games'][1]['tso_clear'] == 0
for why, recs, want in (
        ('before the CLEAR', put(clr_i), 'no pending input'),
        ('after the PA2', put(lambda r: pa2_i(r) + 1), 'no pending input'),     # takes PA2's place
        ('in game A', put(lambda r: hidx(r, lambda x: x[0] == '>' and x[3][6:] == b'\xd9') + 1), 'no pending input'),
        ('in game C', put(lambda r: hidx(r, lambda x: x[0] == '>' and x[3][6:] == b'\xd9', 2) + 1), 'no pending input'),
        ('twice', put(lambda r: clr_i(r) + 1, n=2), 'no pending input'),
        ('WCC C3', put(lambda r: clr_i(r) + 1, bytes.fromhex('7EC311F2E71D4011404013')), 'no pending input'),
        ('another address', put(lambda r: clr_i(r) + 1, bytes.fromhex('7EC111F2E81D4011404013')), 'no pending input'),
        ('orders reordered', put(lambda r: clr_i(r) + 1, bytes.fromhex('7EC11D4011F2E711404013')), 'no pending input'),
        ('Erase/Write instead', put(lambda r: clr_i(r) + 1, bytes.fromhex('F5C111F2E71D4011404013')), 'no pending input'),
        ('unrelated write after CLEAR', put(lambda r: clr_i(r) + 1, bytes.fromhex('F1C3114040')), 'no pending input')):
    got = z5(recs)
    assert got.startswith('FAIL') and want in got, (why, got)
# composite acceptance (ZOS-5 final: A from one trace, B / C from the A / B / C session trace with
# CONTENTION-RESOLUTION): the synthetic T5-like (A only) + T2-like (A / B / C, CR, TSO CLEAR in B) evidence passes;
# a wrong or missing A source, a wrong B / C source, swapped roles and no CR fail; the first game of the B / C source
# never counts as A (a B / C source whose A misses an L still passes, an A source with that A fails)
CRS = [0x00, 0x02, 0x04, 0x05]
ta = FX.render(FX.session(games='A'), funcs=CRS)
tbc = FX.render(FX.session(tso_clear=True), funcs=CRS)
two_l = ['+', 'R', 'R', 'U', 'L', 'L', 'D', 'D', 'R', 'X', 'r', 'R', 'R', 'D', 'Q']


def zc(a_, bc_):
    try:
        return Z5.check_composite(a_, bc_, 'TA', 'TBC')
    except Z5.Fail as ex:
        return 'FAIL: ' + str(ex)


cp = zc(ta, tbc)
assert cp['verdict'] == 'PASS' and [(g['name'], g['source']) for g in cp['games']] == [('A', 'TA'), ('B', 'TBC'),
                                                                                         ('C', 'TBC')], cp
assert [g['tso_clear'] for g in cp['games']] == [0, 1, 0] and cp['games'][0]['cards'] == 15
assert zc(ta, FX.render(FX.session(tso_clear=True, cards_a=two_l), funcs=CRS))['verdict'] == 'PASS'   # T2-like A
for why, a_, bc_, want in (
        ('A source = the A / B / C session', tbc, tbc, 'exactly one A game'),
        ('A source with two L', FX.render(FX.session(games='A', cards_a=two_l), funcs=CRS), tbc, 'not the frozen MOVES'),
        ('A source empty of games', FX.render(FX.session(games=''), funcs=CRS), tbc, 'exactly one A game'),
        ('A source holds C only', FX.render(FX.session(games='C'), funcs=CRS), tbc, 'size switch'),
        ('B / C source with B redraw by PA2 only', ta, FX.render(FX.session(b_redraw='PA2'), funcs=CRS), 'CLEAR then PA2'),
        ('B / C source with C redraw by PA2', ta, FX.render(FX.session(c_redraw='PA2'), funcs=CRS), 'empty ENTER'),
        ('B / C source without CONTENTION-RESOLUTION', ta, FX.render(FX.session(tso_clear=True)), 'not negotiated'),
        ('B / C source = A only', ta, ta, 'games found'),
        ('roles swapped', tbc, ta, 'exactly one A game')):
    got = zc(a_, bc_)
    assert isinstance(got, str) and want in got, (why, got)
# --reply-out serialisation = the tests/qreply_*.hex convention (upper-case hex, one line, final newline): the dyn
# reply serialised by the checker is the file tests/qreply_dyn.hex byte for byte
assert Z5.reply_hex(Z5.Q.rec('dyn')).encode() == (R / 'tests/qreply_dyn.hex').read_bytes()
# the negotiated functions come from the TELNET state replay (T2: FUNCTIONS IS 00 02 04 05); the synthetic fixture and
# the local x3270 run negotiated none
tstate = ('x\n TELNET state:\n< 0x0   fffa28030400020405fff0\n Screen contents (TN3270E-3270) formatted:\n')
assert Z5.functions(tstate) == {0, 2, 4, 5} and Z5.functions(fxt) == set()
assert Z5.functions((R / 'tests/fixtures/zos5/x3270-midsession.trace').read_text()) == set()
neg_resp = [list(x) for x in ok_resp]
neg_resp[hidx(neg_resp, lambda x: x[2][:1] == b'\x02')][2] = b'\x02\x00\x01\x00\x06'
assert z5(neg_resp).startswith('FAIL') and 'RESPONSE' in z5(neg_resp)
txt = FX.render(FX.session())
assert z5(text=txt[:txt.rindex('ffef')]).startswith('FAIL'), 'truncated final record'
hd, tl = txt.split(' Data stream:\n')
assert z5(text=hd + ' Data stream:\n' + tl.replace('< 0x0   ', '< 0x0   fffb00', 1)).startswith('FAIL')   # IAC WILL BINARY
assert 'Data stream' in z5(text=hd.replace(' Data stream:', '') + tl)                   # no marker: not a mid-session trace
nr1 = re.search(r'nr=(\d+)', tl).group(1)
assert 'socket read nr=' in z5(text=hd + ' Data stream:\n' + tl.replace(f'nr={nr1}', f'nr={int(nr1) + 1}', 1))
assert 'without a socket read' in z5(text=hd + ' Data stream:\n' + tl.replace('socket Host socket read complete', 'x', 1))
rsnap = Z5.check(txt.replace('c9e2d7c640', 'd3d6c7d6d5', 1))    # 'ISPF ' -> 'LOGON' in the start dump only
assert rsnap['verdict'] == 'PASS' and any('LOGON' in w for w in rsnap['snap_flags']), rsnap['snap_flags']
# the real x3270 4.5 output of a mid-session Trace(On) (s3270 against the local fake TN3270E host
# tests/fixtures/zos5/fake_tn3270e.py, 2026-10-16): start dumps skipped, records framed and validated, the reply = the
# TK4- IBM-DYNAMIC reply byte for byte
xt = (R / 'tests/fixtures/zos5/x3270-midsession.trace').read_bytes()
assert hashlib.sha256(xt).hexdigest() == 'ac62ea51b371c81140522bc69a8a249c5ca4307053aa51d88bb99ae02702c223'
xb, xsnap = Z5.blocks(xt.decode())
xev, xrule = Z5.tn3270e(Z5.telnet(xb)[0])
assert [(d, p[:2].hex()) for _, d, _, p in xev] == [('<', '7ec3'), ('<', 'f300'), ('>', '8800'), ('<', 'f1c3'),
                                                     ('>', '7d40'), ('<', 'f1c3'), ('<', 'f1c3')] and xrule == '+1'
assert xev[1][3] == Z5.QUERY and xev[2][3] == Z5.Q.rec('dyn') and len(xsnap) == 1970
# another reply size: the writes equal the model of that canvas, the verdict is not PASS
other = FX.session(reply=Z5.Q.rec('m5'), canvas='X')
assert z5(other) == 'MODEL-IDENTICAL-OTHER-PROFILE', z5(other)
print(f'ZOS-5 live postcheck: model = oracle 310 TSD45 / TSD48 / TSD28 (frozen cards, end lines); synthetic session '
      f'PASS (fixture regenerated identically); {len(neg5) + 3} game / framing negatives fail closed, byte-level '
      'framing rules (IAC IAC, timing mark, other commands, trailing bytes, responses), 132 x 27 reply = '
      'MODEL-IDENTICAL-OTHER-PROFILE: PASS')

# 20. ZOS-6 REALTIME live postcheck (docs/zos6-design.md; nothing executed live). tools/zowe/zos6_live_check.py on
#     synthetic traces of the approved R1 / R2 plans (tests/zos6_fixture.py: a host / network / BID time simulation,
#     the PACMAN writes = tests/ref_rt.py); the model anchored to the frozen oracle 310 RTB1-12 / RTT1-6 blocks; valid R1
#     / R2 PASS with PF7 / PF8 / PF10 / PF11 mapped through all four layers; every FUNCTIONAL FAIL rule and every
#     ENVIRONMENT / TIMING BLOCKED class; BLOCKED is neither PASS nor FAIL; R2 only after an R1 PASS
import zos6_fixture as F6  # noqa: E402
import zos6_live_check as C6  # noqa: E402
import zos_equiv as ZE6  # noqa: E402
from make_deck import RT_BAT, RT_TSD, rt_parm_and_cards  # noqa: E402
import ref_rt  # noqa: E402
o310b = json.load(gzip.open(R / 'tests/oracle20/310-PACBLGP2.json.gz'))
anc6 = ZE6.anchors(o310b, {'PACMAIN'})
s310, ord6 = o310b['stream'], sorted(anc6.values())


def blk6(st):
    b = anc6[st]
    x = s310[b:min([v for v in ord6 if v > b], default=len(s310))]
    while x and x[-1] == '':
        x.pop()
    return x


for i, c in enumerate(RT_BAT, 1):                       # RTB1-12: the batch REALTIME output = ref_rt.simulate
    assert blk6(f'RTB{i}') == [x.rstrip() for x in ref_rt.simulate((R / f'tests/rtcases/{c}.txt').read_text()
                                                                     .splitlines())], c    # oracle lines right-stripped
for i, (c, cv) in enumerate(RT_TSD, 1):                 # RTT1-6: the TSD REALTIME streams + end lines = ref_rt.tsd
    bl, fr, j = blk6(f'RTT{i}'), [], 0
    while j < len(bl):
        m = re.match(r'TSD FRAME LEN(\d{4})$', bl[j])
        j += 1
        if m:
            h = ''
            while j < len(bl) and bl[j].startswith('TSD ') and not bl[j].startswith('TSD FRAME'):
                h += bl[j][4:].strip()
                j += 1
            fr.append(bytes.fromhex(h))
    parm, cards6 = rt_parm_and_cards(c)
    cfg = (R / f'tests/rtcases/{c}.txt').read_text().splitlines()[0]
    cfg = cfg if cfg[:1] == 'A' else 'AI1 1'
    out6, fr6 = ref_rt.tsd([cfg] + cards6.splitlines(), cv)
    e6 = next(k for k in range(len(bl)) if bl[k] in ('QUIT', 'LOST', 'WIN', 'EOF') and k > 0
              and bl[k - 1].startswith('TSD '))
    assert list(fr6) == fr and bl[e6:e6 + 5] == out6[-5:], c


def run6(case, present='E', plan=None, **kw):
    """The D33 checker rules (EVERY: one write per quantum) keep their regression here; PRESENT(COALESCED), the R1 / R2
    mode, is section 22."""
    text, lg = F6.build(case, present=present, plan=plan, **kw)
    try:
        return C6.check(text, lg, case, present=present, plan=plan)
    except C6.Fail as ex:
        return {'state': C6.FAILED, 'why': str(ex)}


r1 = run6('R1')       # the approved R1 plan: AI(0), still ghost, Pac-Man stationary after the respawn - the freeze
assert r1['state'] == C6.PASS, r1.get('blocked', r1.get('why'))        # length leaves no trace: NOT OBSERVABLE, which
assert r1['live_freeze_discrimination'] == 'NOT OBSERVABLE' and r1['freeze_mutants'] == {9: 'matches', 11: 'matches'}
assert r1['death_runs'] == [10] and r1['death_ms'] == 1500 and r1['principal']['quanta'] >= 200
assert r1['writes'] == r1['quanta'] + 3 and r1['diag']['bids'] > 0       # BIDs / RESPONSEs are no game writes
r2 = run6('R2')
assert r2['state'] == C6.PASS and r2['death_runs'] == [] and r2['principal']['quanta'] >= 200, r2.get('why')
assert [(d['action'], d['aid'], d['model']) for d in r2['directional']] == [
    ('PF11', '7B', 'R'), ('PF8', 'F8', 'D'), ('PF7', 'F7', 'U'), ('PF10', '7A', 'L')]
assert [(d['action'], d['aid'], d['model']) for d in r1['directional']] == [('PF8', 'F8', 'D'), ('PF11', '7B', 'R')]
assert r2['principal']['first'] > max(d['sent'] for d in r2['directional'])   # the R2 timing segment follows PF10
SH1 = [1, 3, 2, 2, 1, 1, 6]                              # R1 with short waits (functional negatives)
SH2 = [1, 1, 1, 1, 2]
rs1 = run6('R1', waits=SH1)                             # the short plan itself is functionally exact (only too short)
assert rs1['state'] == C6.BLOCKED and any('< 200' in b for b in rs1['blocked']), rs1.get('blocked', rs1.get('why'))
fails6 = {
    'game write before the start': ('R1', dict(waits=SH1, extra_write='start'),
                                   ('differs from the model', 'permitted quantum')),
    'game write while PAUSED': ('R1', dict(waits=SH1, extra_write='pause'),
                               ('differs from the model', 'permitted quantum')),
    'lost AID': ('R1', dict(waits=SH1, lose=2), 'differ'),
    'duplicated AID': ('R1', dict(waits=SH1, dup=3), 'differ'),
    'substituted directional AID': ('R2', dict(waits=SH2, subst=2), 'differ'),
    'driver log != trace': ('R2', dict(waits=SH2, log_mismatch=True), 'plan'),
    'model byte changed': ('R1', dict(waits=SH1, mutate=6), ('differs from the model', 'permitted quantum')),
    'death stop one quantum short': ('R1', dict(waits=SH1, drop_write=rs1['death_writes'][0] + 3),
                                     ('differs from the model', 'permitted quantum')),
    'wrong QUANTA': ('R2', dict(waits=SH2, end_lines=['QUIT', 'TURNS 007', 'SCORE 0070', 'LIVES 3', 'QUANTA 9999999']),
                     'end lines'),
    'wrong closure (score)': ('R2', dict(waits=SH2, end_lines=['QUIT', 'TURNS 007', 'SCORE 0000', 'LIVES 3',
                                                                 'QUANTA 0000001']), 'end lines'),
    'missing shell': ('R2', dict(waits=SH2, no_shell=True), 'ISPF Command Shell'),
    'unknown DATA-TYPE': ('R2', dict(waits=SH2, dt0a=True), 'not 3270-DATA'),
    'cadence faster than 0.99 T': ('R2', dict(scale=0.97), 'earliest deadline'),
    'host burst after the resume (causality)': ('R1', dict(waits=SH1, resume_burst=True), 'earliest deadline'),
    'AID matching only beyond its permitted window': ('R2', dict(waits=SH2, late={1: 420}), 'permitted quantum'),
    'unexpected TSO line-mode (C1) record mid-game': ('R2', dict(waits=SH2, midc1=True), 'differ'),
    'driver-log action missing': ('R2', dict(waits=SH2, log_drop=4), 'driver log'),
}
for why, (c, kw, want) in fails6.items():
    r = run6(c, **kw)
    assert r['state'] == C6.FAILED and any(w in r['why'] for w in ((want,) if isinstance(want, str) else want)), \
        (why, r.get('why'), r['state'])
dw = r1['death_writes'][1]
blocked6 = {
    'mean 1.05 T': ('R2', dict(scale=1.05), '> 1.02 T', False),
    'mean 1.15 T (STOP)': ('R2', dict(scale=1.15), '> 1.10 T', True),
    'median outside T +/- 10 ms': ('R2', dict(gaps=[0, 15, 30]), 'median gap', False),
    'probable skipped period': ('R2', dict(skip_at=120), 'skipped period', False),
    'death stop outside 1350..1650 ms': ('R1', dict(delay={dw: 300}), 'death stop', False),
}
for why, (c, kw, want, stop) in blocked6.items():
    r = run6(c, **kw)
    assert r['state'] == C6.BLOCKED and any(want in b for b in r['blocked']) and r['stop'] == stop, \
        (why, r.get('blocked'), r.get('why'))
    assert r['state'] not in (C6.PASS, C6.FAILED)
rr = r1['post_resume'][0]['writes'][0]                  # the resume quantum write
r = run6('R1', delay={rr + 1: 250, rr + 2: 150})        # bunched after the resume, causality respected
assert r['state'] == C6.BLOCKED and any('post-resume' in b for b in r['blocked']), r.get('blocked', r.get('why'))
text6, lg6 = F6.build('R2', waits=SH2)                  # a well-formed but hand-edited driver log (send before unlock)
x6 = json.loads(lg6[3])
x6['sent'] = x6['unlocked'] - 1
try:
    C6.check(text6, lg6[:3] + [json.dumps(x6)] + lg6[4:], 'R2')
    raise AssertionError('edited driver log accepted')
except C6.Fail as ex:
    assert 'inconsistent timestamps' in str(ex), ex
assert all(w[1] - w[0] <= 2 for _, _, w in r1['placements'] + r2['placements'])     # bounded placement windows
assert [s - w[0] for _, s, w in r2['placements']] == [0, 1, 1, 1, 1]                # start at lo, in-run AIDs at lo + 1
assert C6.r2_eligible(C6.PASS) and not C6.r2_eligible(C6.BLOCKED) and not C6.r2_eligible(C6.FAILED)
import zos6_drive as D6  # noqa: E402
assert [a for _, a in D6.planned('R1', 'gameplay')] == ['PF8', 'PF9', 'PF9', 'x', 'PA2', 'PF11', 'Q']
assert [a for _, a in D6.planned('R2', 'gameplay')] == ['PF11', 'PF8', 'PF7', 'PF10', 'Q']
assert [a for _, a in D6.planned('R1')][:2] == ['EXEC', 'ENTER'] and D6.planned('R2', 'closure') == [('closure', 'ENTER')]
assert {c for cs in D6.CALLS.values() for c in cs} <= {'PF(7)', 'PF(8)', 'PF(9)', 'PF(10)', 'PF(11)', 'PA(2)',
                                                     'Enter()',
                                                     'String("x")', 'String("Q")'}
assert D6.command('R2', 'Z00000.PACMAN') == ("EXEC 'Z00000.PACMAN.CLIST(PACMAN)' "
                                             "'AI(0) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO) PRESENT(COALESCED) "
                                             "SPEED(FAST)'")
assert D6.PLANS['R1']['present'] == D6.PLANS['R2']['present'] == 'C'      # R1 / R2 request COALESCED explicitly
assert [w for k, w in D6.PLANS['R2']['steps'] if k == 'wait'][-1] == 30
assert D6.PLANS['R1']['steps'][7] == ('gameplay', 'PF9')
# empty 3270-DATA SEND-DATA / KEYBOARD-RESTORE control records (REQUEST-FLAG X'03', z/OS TN3270E with
# CONTENTION-RESOLUTION, live R1-T3): validated, never game writes, never compared with the model, visible in the
# send-state diagnostics; any other empty 3270-DATA (REQUEST-FLAG 00 / 01 / 02) or a truncated record fails
rk = run6('R2', kri=12)
assert rk['state'] == C6.PASS and rk['writes'] == r2['writes'] and len(rk['controls']) > 0, rk.get('why')
assert rk['diag']['kri_controls'] > 0 and rk['diag']['kri_max_gap'] is not None and r2['controls'] == []
for why, kw, want in (('empty 3270-DATA, REQUEST-FLAG 00', dict(kri_rq=0x00), 'not 3270-DATA'),
                      ('empty 3270-DATA, SEND-DATA only (01)', dict(kri_rq=0x01), 'not 3270-DATA'),
                      ('empty 3270-DATA, KRI only (02)', dict(kri_rq=0x02), 'not 3270-DATA'),
                      ('truncated control record', dict(kri_short=True), 'no TN3270E header')):
    r = run6('R2', waits=SH2, kri=6, **kw)
    assert r['state'] == C6.FAILED and want in r['why'], (why, r.get('why'))
# the driver against the REAL `x3270if -t PORT ACTION` contract (observed live on the idle ISPF shell, 2026-10-16):
# exit status 0 = success, stdout = raw text (Ascii(): the screen rows; Wait / PF / PA / Enter / String: nothing);
# no `data:` prefix, no `ok` line; nonzero status or a timeout = STOP. A fake x3270if replaces subprocess.run.
import subprocess as SP6  # noqa: E402
import io as IO6  # noqa: E402
REAL_RUN6 = SP6.run
SCREEN6 = ('   Menu  List  Mode  Functions  Utilities  Help\n' + ' ' + '\u2500' * 78 + '\n'
           '                             ISPF Command Shell\n Enter TSO commands below:\n\n ===>\n'
           + '\n' * 16 + '  F1=Help      F2=Split     F3=Exit\n F10=Actions  F12=Cancel\n')
GAME6 = SCREEN6.replace('ISPF Command Shell', 'P A C - M A N  ***')       # the pre-game ***, the game, the closing ***
SEQ6 = [SCREEN6, GAME6, GAME6, GAME6, SCREEN6]      # Ascii() answers: startup, ***, game, ***, back in the shell


class FakeX:
    def __init__(self, screens, fail=None, hang=None):
        self.screens, self.fail, self.hang, self.calls = list(screens), fail, hang, []

    def __call__(self, cmd, capture_output, text, timeout):
        action = cmd[3]
        self.calls.append(action)
        if self.hang and action.startswith(self.hang):
            raise SP6.TimeoutExpired(cmd, timeout)
        if self.fail and action.startswith(self.fail):
            return SP6.CompletedProcess(cmd, 1, '', 'x3270if: error')
        out = (self.screens.pop(0) if len(self.screens) > 1 else self.screens[0]) if action == 'Ascii()' else ''
        return SP6.CompletedProcess(cmd, 0, out, '')


def drive6(fake, case='R2'):
    real_run, real_sleep = REAL_RUN6, D6.time.sleep
    D6.subprocess.run, D6.time.sleep = fake, lambda s: None
    log = IO6.StringIO()
    try:
        D6.run(case, 4005, log, 'Z00000.PACMAN')
        return 'ok', log.getvalue().splitlines()
    except D6.Stop as ex:
        return f'STOP: {ex}', log.getvalue().splitlines()
    finally:
        D6.subprocess.run, D6.time.sleep = real_run, real_sleep


dx = D6.Driver(4005, IO6.StringIO())
D6.subprocess.run = FakeX([SCREEN6])
try:
    assert dx.screen() == SCREEN6 and 'ISPF Command Shell' in dx.screen()       # raw multiline screen, complete
    assert dx.x('Wait(5,Unlock)') == '' and dx.x('PF(8)') == '' and dx.x('Enter()') == '' and dx.x('String("x")') == ''
    D6.subprocess.run = FakeX([SCREEN6], fail='PF(')
    try:
        dx.x('PF(8)')
        raise AssertionError('nonzero rc accepted')
    except D6.Stop as ex:
        assert 'rc 1' in str(ex)
    D6.subprocess.run = FakeX([SCREEN6], hang='Wait(')
    try:
        dx.x('Wait(5,Unlock)', timeout=15)
        raise AssertionError('timeout accepted')
    except D6.Stop as ex:
        assert 'no answer within 15 s' in str(ex)
finally:
    D6.subprocess.run = REAL_RUN6
res, lines = drive6(FakeX(SEQ6), 'R2')       # startup sees the shell; every planned action sent, logged ok
assert res == 'ok' and [(json.loads(x)['category'], json.loads(x)['action']) for x in lines] == D6.planned('R2')
assert all(json.loads(x)['result'] == 'ok' for x in lines)
res, lines = drive6(FakeX([SCREEN6.replace('ISPF Command Shell', 'ISPF Primary Option Menu')]), 'R1')
assert res.startswith('STOP') and 'not on the screen' in res and lines == []         # no shell: nothing sent
fk = FakeX(SEQ6, fail='PF(7)')
res, lines = drive6(fk, 'R2')                                    # a failing action: STOP, logged as error, nothing after
assert res.startswith('STOP') and json.loads(lines[-1])['action'] == 'PF7' and 'error' in json.loads(lines[-1])['result']
assert fk.calls[-1] == 'PF(7)'
res, lines = drive6(FakeX(SEQ6, hang='Wait('), 'R1')
assert res.startswith('STOP') and 'no answer' in res and len(lines) == 1 and 'error' in json.loads(lines[0])['result']
print(f'ZOS-6 live postcheck (EVERY rules): ref_rt = oracle 310 RTB1-12 / RTT1-6; synthetic R1 PASS (live freeze '
      'discrimination NOT OBSERVABLE, reported), R2 PASS (PF7 / PF8 / PF10 / PF11 -> '
      f'F7 / F8 / 7A / 7B -> U / D / L / R); {len(fails6)} FUNCTIONAL FAIL rules, {len(blocked6) + 2} BLOCKED classes '
      '(BLOCKED != PASS / FAIL); R2 only after an R1 PASS: PASS')

# 21. ZOS-6 protocol probe (docs/zos6-protocol-probe.md; local / static only, nothing uploaded or run): the assembler
#     probe src/probe/zos/PACZ6P.asm (P0 = TPUT NOEDIT, PT = TPG NOEDIT,WAIT,NOHOLD, then TGET ASIS,NOWAIT on an
#     absolute 150 ms schedule; no ATTACH / STAX / ESTAE / LE; AMODE / RMODE 24; TPG buffer address / size in R2 / R3,
#     never R0 / R1: IHB300, JOB04217), the generated build deck (ASM + LKED into the existing probe PDSE DISP=SHR, no
#     allocation, no DELETE), the analyzer on synthetic P0 / PT traces (inventory, order, AIDs wire vs driver vs host),
#     the input controller on a fake x3270if (a 5 s keyboard-locked wait is an observation, not a retry, not a STOP);
#     PN = the P0 loop with the TGET ASIS,NOWAIT before the TPUT NOEDIT (no TPG, no TGET WAIT, no subtask);
#     PH = the P0 loop with TPUT NOEDIT,WAIT,HOLD (output written before control returns); PB4 = the P0 loop with
#     the PH HOLD output on every 4th quantum only (a periodic output barrier); PR2 = 150 ms logical quanta with a
#     poll each, but a NOHOLD write of the current state only on even quanta (66 of 133), never replayed; PR2I =
#     PR2 plus a host table (one record per quantum: clock reads and stores only, printed after ENDLOOP)
import zos6_probe_check as PC  # noqa: E402
import zos6_probe_fixture as PF  # noqa: E402
import zos6_probe_drive as PD  # noqa: E402
psrc = (R / 'src/probe/zos/PACZ6P.asm').read_text().splitlines()
pcode = [x for x in psrc if x[:1] != '*']
assert all(len(x) <= 71 for x in psrc) and not any(x.startswith(('/*', '//')) for x in psrc)
assert [x.split()[0:2] for x in pcode if ' TPG ' in x] == [['TPG', '(2),(3),NOEDIT,WAIT,NOHOLD']]
ktpg = next(i for i, x in enumerate(pcode) if ' TPG ' in x)
assert [x.split()[:2] for x in pcode[ktpg - 2:ktpg]] == [['LA', '2,FRAME'], ['LA', '3,FRAMEL']]
assert [x.split()[1] for x in pcode if x.split()[:1] == ['TPUT'] and 'NOEDIT' in x] == [
    '(1),(0),NOEDIT', '(1),(0),NOEDIT', '(1),(0),NOEDIT,WAIT,HOLD'] and sum(' TGET ' in x for x in pcode) == 1
assert any('TGET  (1),(0),ASIS,NOWAIT' in x for x in pcode) and 'PACZ6P   AMODE 24' in psrc and 'PACZ6P   RMODE 24' in psrc
pops = [(x.split()[0] if x[:1] == ' ' else x.split()[1]) for x in pcode if x.strip()]      # the operation field
assert not {'ATTACH', 'DETACH', 'STAX', 'ESTAE', 'ESPIE', 'SPIE', 'CALL', 'LINK', 'XCTL', 'LOAD'} & set(pops), pops
# PN (poll before output): accepted PARM; the one TGET (NOWAIT, never WAIT) lives in POLL; in the loop PN calls POLL
# before the TPUT NOEDIT and skips the post-output POLL, which P0 / PT keep after the output
assert [x.split()[:2] for x in pcode if '=C\'P' in x and 'CLC' in x] == [['CLC', "2(2,2),=C'P0'"],
                                                                     ['CLC', "2(2,2),=C'PT'"], ['CLC', "2(2,2),=C'PN'"],
                                                                     ['CLC', "2(2,2),=C'PH'"], ['CLC', "2(2,2),=C'PB'"],
                                                                     ['CLC', "2(2,2),=C'PR'"]]
tgets = [x.split()[1] for x in pcode if x.split()[:1] == ['TGET'] or ' TGET ' in x]
assert tgets == ['(1),(0),ASIS,NOWAIT'] and not any('WAIT' in x.split()[1].replace('NOWAIT', '') for x in pcode
                                                    if ' TGET ' in x)
ops = [' '.join(x.split()[:2]) if x[:1] == ' ' else ' '.join(x.split()[:3]) for x in pcode if x.strip()]
lp, el, pl = ops.index('LOOP DS 0H'), ops.index('ENDLOOP DS 0H'), ops.index('POLL DS 0H')
body = ops[lp:el]
k1, kt, k2 = body.index('BAL 11,POLL'), body.index('TPUT (1),(0),NOEDIT'), len(body) - 1 - body[::-1].index('BAL 11,POLL')
assert body[k1 - 2:k1] == ["CLI MODE,C'N'", 'BNE FRAMEB'] and k1 < kt < k2 and body.count('BAL 11,POLL') == 2
assert body[k2 - 2:k2] == ["CLI MODE,C'N'", 'BE NOAID'] and ops.index('TGET (1),(0),ASIS,NOWAIT') > pl > el
assert not any(x.startswith(('WAIT ', 'TGET')) and 'NOWAIT' not in x for x in body)    # nothing blocks on input
# PH (TPUT HOLD): the only change from P0 is the output call: one HOLD TPUT, reached only for MODE H, then the common
# OUTDONE; PH polls AFTER the output (the P0 order: only MODE N skips the post-output POLL)
kh = body.index('USEHOLD DS 0H')
assert body[kh + 1:kh + 4] == ['MVI HOLDQ,1', 'TPUT (1),(0),NOEDIT,WAIT,HOLD', 'B OUTDONE']
assert body.count("CLI MODE,C'H'") == 1
assert body[body.index("CLI MODE,C'H'") + 1] == 'BE USEHOLD'
assert body.index('USEHOLD DS 0H') < body.index('OUTDONE DS 0H')
assert body.index("CLI MODE,C'H'") < body.index('TPUT (1),(0),NOEDIT') < kh and "CLI MODE,C'H'" not in ops[el:]
# PB4 (periodic HOLD barrier): PARM 'PB4' (3 characters, length checked); in the output selection MODE B takes the
# PH HOLD call when q mod 4 = 0 (R4 = R8 AND 3, R4 used nowhere else) and the P0 NOHOLD TPUT otherwise; the poll
# stays after the output (only MODE N skips it); HOLDQ marks a HOLD quantum for HOLDS / MAXHOLD / MAXNOHOLD
kb = ops.index("CLC 2(2,2),=C'PB'")
assert ops[kb + 1:kb + 9] == ['BNE PARMR', "CLC 0(2,2),=H'3'", 'BL EXIT', "CLI 4(2),C'4'", 'BNE EXIT',
                             "MVI FMODE+2,C'4'", "MVI S1MODE+2,C'4'", 'B PARMOK']
kr = ops.index('PARMR DS 0H')
assert ops[kr + 1:kr + 17] == ["CLC 2(2,2),=C'PR'", 'BNE EXIT', "CLC 0(2,2),=H'3'", 'BL EXIT', "CLI 4(2),C'2'",
                              'BNE EXIT', "MVI FMODE+2,C'2'", "MVI S1MODE+2,C'2'", "CLC 0(2,2),=H'4'", 'BL PARMOK',
                              "CLI 5(2),C'I'", 'BNE EXIT', 'MVI INSTR,1', "MVI S1MODE+3,C'I'", 'PARMOK DS 0H',
                              "MVC MODE,3(2)"]                 # PR2I = MODE R (PR2) + INSTR; FMODE (title) as PR2
kc = body.index("CLI MODE,C'B'")
assert body[kc:kc + 7] == ["CLI MODE,C'B'", 'BNE USENOH', 'LR 4,8', "N 4,=F'3'", 'BZ USEHOLD', 'USENOH DS 0H',
                          'TPUT (1),(0),NOEDIT'] and body.index("CLI MODE,C'H'") < kc < kh
assert [o for o in body if re.search(r'(^|\s)4,|,4\)', o)] == ['LR 4,8', "N 4,=F'1'", 'LR 4,8', "N 4,=F'3'"]
# PR2 (render every 2nd logical quantum): the quantum itself is unchanged (133 x 150 ms: NQUANTA, PERIOD, the lateness
# and deadline code run for every q before / after the branch); at FRAMEB MODE R with an odd q counts a skip and jumps
# to PUTOK, i.e. no frame is built, no TPUT, but the same POLL and the same absolute deadline; even q builds the frame
# from the CURRENT q / AIDCNT and writes it with the P0 NOHOLD TPUT; nothing is kept for a later write
kf = body.index('FRAMEB DS 0H')
assert body[kf:kf + 11] == ['FRAMEB DS 0H', "CLI MODE,C'R'", 'BNE FRAMEC', 'LR 4,8', "N 4,=F'1'", 'BZ FRAMEC',
                            'L 2,SKIPCNT', 'LA 2,1(2)', 'ST 2,SKIPCNT', 'B PUTOK', 'FRAMEC DS 0H']
assert body[kf + 11:kf + 13] == ['CVD 8,DW', 'UNPK FQ(4),DW']                        # the frame shows the current q
assert body.index('LOOP DS 0H') < body.index('ST 1,TISSUE') < kf < body.index('PUTOK DS 0H') < body.index('NOAID DS 0H')
kn = body.index('NOAID DS 0H')
assert body[kn + 1:kn + 3] == ['LR 0,8', 'MH 0,PERIOD'] and 'BL LOOP' in body[kn:]
assert any("NQUANTA DC F'133'" in ' '.join(x.split()[:3]) for x in pcode)
assert any("PERIOD DC H'150'" == ' '.join(x.split()[:3]) for x in pcode)
ko = body.index('OUTDONE DS 0H')
assert body[ko + 4:ko + 7] == ['L 2,WRCNT', 'LA 2,1(2)', 'ST 2,WRCNT']                # counted after RC 0 only
pr2_writes = [q for q in range(1, 134) if q % 2 == 0]
assert len(pr2_writes) == 66 and pr2_writes[0] == 2 and pr2_writes[-1] == 132 and 133 - len(pr2_writes) == 67
assert any("C'PACZ6P WRITES '" in x for x in pcode) and any("C' SKIPPED '" in x for x in pcode)
# PR2I (instrumentation only): every added step in the loop and in POLL sits in a block `CLI INSTR,1` / `BNE NOINSn`
# (skipped by every other mode, PR2 included) and uses only the clock (BAL 14,NOWMS) and stores into the record at
# 0(R6) (R6 used nowhere else); no SVC / macro / I/O inside; one record per quantum, (q - 1) x 32 from ITAB, initialised
# from IINIT at the top of the quantum; the table (133 x 32) is printed by IDUMP, called only at SUMEND (after
# ENDLOOP's STTMPMD / STFSMODE OFF / STLINENO and the summary), with line-mode TPUTs
allowed = re.compile(r"^(CLI INSTR,1|BNE NOINS\d|BNZ NOINS\d|BZ NOINS\d|BAL 14,NOWMS|LR 6,8|BCTR 6,0|SLL 6,5|"
                     r"LA 6,ITAB\(6\)|MVC 0\(32,6\),IINIT|STH 8,0\(6\)|ST 1,(12|16|20|24)\(6\)|MVI 2\(6\),1|"
                     r"L 2,AIDCNT|STH 2,(8|10)\(6\)|LR 5,1|STC 15,3\(6\)|LTR 15,15|STH 5,4\(6\)|LTR 5,5|"
                     r"MVC 6\(1,6\),INBUF|LR 1,5|NOINS\d DS 0H)$")
blocks = []
for k, o in enumerate(ops):
    if o == 'CLI INSTR,1' and ops[k + 1].startswith('BNE NOINS'):
        end = ops.index(ops[k + 1].split()[1] + ' DS 0H', k)
        blocks.append((k, end))
        assert all(allowed.match(x) for x in ops[k:end + 1]), ops[k:end + 1]
assert len(blocks) == 6 and [b for b in blocks if lp < b[0] < el].__len__() == 3 and all(b[0] > pl for b in blocks[3:])
ki = blocks[0][0]
assert ops[ki - 1] == 'LA 8,1(8)' and ops[ki - 2] == 'LOOP DS 0H' and ops[ki + 2:ki + 8] == [
    'LR 6,8', 'BCTR 6,0', 'SLL 6,5', 'LA 6,ITAB(6)', 'MVC 0(32,6),IINIT', 'STH 8,0(6)']
r6 = [o for o in ops[:ops.index('IDUMP DS 0H')] if re.search(r'(^|\s)6,|\(6\)', o)]
assert all(allowed.match(o) for o in r6), r6                                       # R6: the record pointer only
assert "ITAB DS 0F" in ops and 'DS 133XL32' in ops and ops.index('LTORG') < ops.index('ITAB DS 0F')
assert ops.count('BAL 11,IDUMP') == 1 and ops.index('BAL 11,IDUMP') > ops.index('STFSMODE OFF') > el
ks = ops.index('SUMEND DS 0H')
assert ops[ks + 1:ks + 5] == ['CLI INSTR,1', 'BNE SUMX', 'BAL 11,IDUMP', 'SUMX DS 0H']
idump = ops[ops.index('IDUMP DS 0H'):ops.index('DEC6 DS 0H')]
assert [o for o in idump if o.startswith(('TPUT', 'TGET', 'TPG', 'STIMER', 'WTO'))] == ['TPUT (1),(0)'] * 3
loop_io = [o for o in body if o.split()[0] in ('TPUT', 'TPG', 'TGET', 'WTO', 'STIMER')]
assert loop_io == ['TPUT (1),(0),NOEDIT', 'TPUT (1),(0),NOEDIT,WAIT,HOLD', 'TPG (2),(3),NOEDIT,WAIT,NOHOLD',
                   'STIMER WAIT,MICVL=MICDW']                                        # unchanged by PR2I
assert [o for o in ops[pl:ops.index('NOWMS DS 0H')] if o.split()[0] in ('TPUT', 'TPG', 'TGET', 'WTO')] == [
    'TGET (1),(0),ASIS,NOWAIT']                                                    # POLL: still the one TGET
assert any(' '.join(x.split()[:2]) == "IINIT DC" and "X'FF',X'FFFF'" in x for x in pcode)
assert body.index('MVI HOLDQ,0') < body.index("CLI MODE,C'T'") and 'MVI HOLDQ,1' in body
kq = body.index('CLI HOLDQ,1')
assert body[kq:kq + 5] == ['CLI HOLDQ,1', 'BNE PUTNH', 'L 2,HOLDCNT', 'LA 2,1(2)', 'ST 2,HOLDCNT']
assert body.index('OUTDONE DS 0H') < kq < body.index('PUTALL DS 0H') < body.index('PUTOK DS 0H')
assert [q for q in range(1, 134) if q & 3 == 0][:2] == [4, 8] and sum(q & 3 == 0 for q in range(1, 134)) == 33
assert any("C'PACZ6P HOLDS '" in x for x in pcode) and any("C' MAXNOHOLD-MS '" in x for x in pcode)
assert not any(re.search(r'PACMAIN|PACFSIO|PACTSO|CLIST|DATA\(', x) for x in pcode)
assert subprocess.run([sys.executable, str(R / 'tools/zowe/zos6_probe_deck.py'), '--check']).returncode == 0
pdeck = (R / 'jcl/zos/PACZ6PRB.jcl').read_text()
assert audit_deck(render(pdeck, 'Z00000'), 'Z00000') == [] and 'DELETE' not in pdeck
assert re.findall(r'DSN=(@@HLQ@@[\w.()]+)', pdeck) == ['@@HLQ@@.PACMAN.Z6PRB.LOAD(PACZ6P)']
assert '\n'.join(psrc) + '\n' in pdeck and "PARM='LIST,AMODE=24,RMODE=24'" in pdeck
assert 'IEFBR14' not in pdeck and 'CATLG' not in pdeck and re.findall(r'^//(\w+) +EXEC', pdeck, re.M) == ['ASM', 'LKED']
assert '//SYSLMOD  DD DSN=@@HLQ@@.PACMAN.Z6PRB.LOAD(PACZ6P),DISP=SHR\n' in pdeck
assert not re.search(r'PACMAN\.(LOAD|ASM|OBJ|CLIST|DATA|COBOL|CEEOPTS)\b', pdeck)
pt = PC.analyse(*PF.build('PT'), 'PT')
assert pt['frames'] == 133 and pt['quanta_in_order'] and pt['frames_sdi'] == 133 and pt['bids'] == 133
assert pt['after_sdi'] == {'BID': 132} and pt['driver_sent_match_wire'] and pt['host_received_match_wire']
assert [a for _, a in pt['wire_aids']] == ['F4', 'F5', 'F6'] and pt['host_summary']['QUANTA'] == '000133'
p0 = PC.analyse(*PF.build('P0', (False, True, False)), 'P0')
assert p0['frames_sdi'] == 0 and p0['empty_controls'] == {'03': 9} and p0['bids'] == 10
assert [r for _, r in p0['driver_attempts']].count('not sent: keyboard locked 5 s') == 2
assert p0['driver_sent_match_wire'] and p0['host_received_match_wire'] and [a for _, a in p0['wire_aids']] == ['F5']
tx, lgx = PF.build('PT')
assert PC.analyse(*PF.build('PT', swap=(10, 11)), 'PT')['quanta_in_order'] is False       # output order checked
bad_host = PC.analyse(tx, lgx, 'PT')
bad_host['host_aids'][1] = ('F7', 67, 10160)
assert [a for a, _, _ in bad_host['host_aids']] != [a for _, a in bad_host['wire_aids']]
lg_mis = [json.dumps(dict(json.loads(x), action='PF6')) if json.loads(x).get('action') == 'PF5' else x for x in lgx]
assert not PC.analyse(tx, lg_mis, 'PT')['driver_sent_match_wire']
pn = PC.analyse(*PF.build('PN'), 'PN')          # PN: 133 frames, the three AIDs on the wire and received by the host
assert pn['frames'] == 133 and pn['quanta_in_order'] and pn['driver_sent_match_wire'] and pn['host_received_match_wire']
assert [a for _, a in pn['wire_aids']] == ['F4', 'F5', 'F6'] == [a for a, _, _ in pn['host_aids']]
assert pn['host_summary']['MODE'] == 'PN' and pn['host_summary']['AIDS'] == '000003' and pn['mean_period'] == 150.0
assert pn['lag_vs_first_frame_schedule']['max'] == 0 and pn['arrival_gaps']['median'] == 150
pn_miss = PC.analyse(*PF.build('PN', host_drop=1), 'PN')                          # one host AID missing: reported
assert [a for a, _, _ in pn_miss['host_aids']] == ['F4', 'F6'] and not pn_miss['host_received_match_wire']
assert pn_miss['driver_sent_match_wire']                                          # ... independently of the driver
tn, lgn = PF.build('PN')
lgn_mis = [json.dumps(dict(json.loads(x), action='PF4')) if json.loads(x).get('action') == 'PF6' else x for x in lgn]
pn_dm = PC.analyse(tn, lgn_mis, 'PN')                                             # driver / wire mismatch: reported
assert not pn_dm['driver_sent_match_wire'] and pn_dm['host_received_match_wire']
assert PC.analyse(*PF.build('PN', swap=(40, 41)), 'PN')['quanta_in_order'] is False
assert PC.analyse(*PF.build('PN', quanta=100), 'PN')['frames'] == 100              # a short run is visible
assert pn['aid_test_exercised'] and (pn['aids_planned'], pn['aids_attempted'], pn['aids_sent']) == (3, 3, 3)
# an experiment in which no planned AID was sent proves nothing about delivery, although both equalities hold on
# empty lists: (a) every attempt timed out; (b) no attempt at all (the PN-T2 shape: the driver stopped at the
# transition ENTER, the probe ran its 133 quanta)
nx = PC.analyse(*PF.build('PN', delivered=(False, False, False)), 'PN')
assert nx['driver_sent_match_wire'] and nx['host_received_match_wire'] and nx['wire_aids'] == nx['host_aids'] == []
assert nx['aid_test_exercised'] is False and (nx['aids_attempted'], nx['aids_sent']) == (3, 0)
tn0, lg0 = PF.build('PN', delivered=(False, False, False))
lg0 = [x for x in lg0 if json.loads(x)['category'] != 'probe']
n0 = PC.analyse(tn0, lg0, 'PN')
assert n0['driver_attempts'] == [] and n0['wire_aids'] == [] and n0['host_aids'] == [] and n0['frames'] == 133
assert n0['driver_sent_match_wire'] and n0['host_received_match_wire'] and n0['aid_test_exercised'] is False
ph = PC.analyse(*PF.build('PH'), 'PH')            # PH: the same diagnostic report shape
assert ph['host_summary']['HOLDS'] == '000133' and ph['host_summary']['MAXHOLD-MS'] == '000509'
assert ph['lag_by_q_mod4'] is None and len(ph['lag_by_third']) == 3
pb = PC.analyse(*PF.build('PB4', lagstep=40), 'PB4')   # PB4: lag building up between barriers, drained at them
assert pb['frames'] == 133 and pb['quanta_in_order'] and pb['host_summary']['MODE'] == 'PB4'
assert pb['host_summary']['HOLDS'] == '000033' and pb['host_summary']['MAXNOHOLD-MS'] == '000001'
assert {k: v['max'] for k, v in pb['lag_by_q_mod4'].items()} == {'1': 0, '2': 40, '3': 80, '0': 120}
assert [t['max'] for t in pb['lag_by_third']] == [120, 120, 120]                 # bounded, not growing
assert pb['aid_test_exercised'] and pb['driver_sent_match_wire'] and pb['host_received_match_wire']
assert (pb['aids_planned'], pb['aids_attempted'], pb['aids_sent']) == (3, 3, 3)
pr = PC.analyse(*PF.build('PR2'), 'PR2')         # PR2: 66 writes of the even quanta, 133 logical quanta
assert pr['frames'] == pr['frames_on_wire'] == 66 and pr['frame_step'] == 2 and pr['quanta_in_order']
assert (pr['logical_quanta'], pr['physical_writes'], pr['skipped_writes']) == (133, 66, 67)
assert pr['mean_period'] == 300.0 and pr['lag_vs_first_frame_schedule']['max'] == 0     # vs the logical schedule
assert pr['aid_test_exercised'] and pr['driver_sent_match_wire'] and pr['host_received_match_wire']
assert [t['max'] for t in pr['lag_by_third']] == [0, 0, 0] and pr['lag_by_q_mod4'] is None
prr = PC.analyse(*PF.build('PR2', replay=40), 'PR2')    # a skipped quantum written late (burst): detected
assert prr['frames'] == 67 and not prr['quanta_in_order']
assert PC.analyse(*PF.build('P0'), 'P0')['frame_step'] == 1                       # the other modes: step 1
assert PC.analyse(*PF.build('P0'), 'P0')['physical_writes'] == 133
pi = PC.analyse(*PF.build('PR2I'), 'PR2I')          # PR2I: the PR2 wire shape + the host table
assert pi['frames'] == 66 and pi['quanta_in_order'] and pi['frame_step'] == 2 and pi['host_received_match_wire']
assert pi['instr']['quanta'] == 133 and pi['instr']['writes_even_only'] and pi['instr']['odd_hits'] == []
assert pi['instr']['host_pattern'] == 'write-poll-only' and len(pi['instr']['detail']) == 12
d0 = pi['instr']['deliveries'][0]
assert d0['write'] and any(c == '.' for _, c in d0['before'])                       # odd no-data, then the write poll
assert [x['tput'] for x in pi['instr']['detail'] if not x['write']][0] == [None, None]
po = PC.analyse(*PF.build('PR2I', odd_hit=True), 'PR2I')                         # an odd no-write poll succeeds
assert po['instr']['odd_hits'] and po['instr']['host_pattern'] == 'odd-poll-success'
assert pr['instr'] is None and PC.analyse(*PF.build('P0'), 'P0')['instr'] is None    # other modes: no table
pbx = PC.analyse(*PF.build('PB4', delivered=(True, False, True), host_drop=0), 'PB4')
assert pbx['aid_test_exercised'] and pbx['driver_sent_match_wire'] and not pbx['host_received_match_wire']
assert [a for _, a in pbx['wire_aids']] == ['F4', 'F6'] and [a for a, _, _ in pbx['host_aids']] == ['F6']
assert ph['host_summary']['MODE'] == 'PH' and ph['aid_test_exercised'] and ph['host_received_match_wire']


class FakeP:
    def __init__(self, screens, timeout_waits=(), fail=None):
        self.screens, self.tw, self.fail, self.calls, self.nw = list(screens), set(timeout_waits), fail, [], 0

    def __call__(self, cmd, capture_output, text, timeout):
        a = cmd[3]
        self.calls.append(a)
        if a.startswith('Wait('):
            self.nw += 1
            if self.nw in self.tw:
                return SP6.CompletedProcess(cmd, 1, '', 'Wait(unlock): Timed out')
        if self.fail and a.startswith(self.fail):
            return SP6.CompletedProcess(cmd, 1, '', 'x3270if: error')
        out = (self.screens.pop(0) if len(self.screens) > 1 else self.screens[0]) if a == 'Ascii()' else ''
        return SP6.CompletedProcess(cmd, 0, out, '')


PTITLE = SCREEN6.replace('ISPF Command Shell', PD.TITLE)
STAR6 = SCREEN6.replace('ISPF Command Shell', '***')


def pdrive(fake, mode='PT'):
    real_sleep = PD.time.sleep
    D6.subprocess.run, PD.time.sleep = fake, lambda s: None
    log = IO6.StringIO()
    try:
        PD.run(mode, 4005, log, 'Z00000.PACMAN.Z6PRB.LOAD')
        return 'ok', [json.loads(x) for x in log.getvalue().splitlines()]
    except D6.Stop as ex:
        return f'STOP: {ex}', [json.loads(x) for x in log.getvalue().splitlines()]
    finally:
        D6.subprocess.run, PD.time.sleep = REAL_RUN6, real_sleep


fk = FakeP([SCREEN6, STAR6, PTITLE, STAR6, SCREEN6], timeout_waits={3, 5})   # waits: CALL, ENTER, PF4, PF5, PF6, ...
res, lg = pdrive(fk, 'P0')
assert res == 'ok' and [(x['category'], x['action']) for x in lg] == [
    ('transition', 'CALL'), ('transition', 'ENTER'), ('probe', 'PF4'), ('probe', 'PF5'), ('probe', 'PF6'),
    ('closure', 'ENTER')], lg
assert [x['result'] for x in lg if x['category'] == 'probe'] == ['not sent: keyboard locked 5 s', 'ok',
                                                                  'not sent: keyboard locked 5 s']
assert 'PF(4)' not in fk.calls and fk.calls.count('PF(5)') == 1 and 'PF(6)' not in fk.calls       # never retried
assert "String(\"CALL 'Z00000.PACMAN.Z6PRB.LOAD(PACZ6P)' 'P0'\")" in fk.calls
res, lg = pdrive(FakeP([SCREEN6, PTITLE, STAR6, SCREEN6]), 'PT')     # no *** before the probe screen: no ENTER
assert res == 'ok' and [x['action'] for x in lg] == ['CALL', 'PF4', 'PF5', 'PF6', 'ENTER']
res, lg = pdrive(FakeP([SCREEN6, PTITLE, STAR6, SCREEN6], fail='PF(5)'), 'PT')   # any other error: STOP
assert res.startswith('STOP') and lg[-1]['action'] == 'PF5' and lg[-1]['result'].startswith('error')
res, lg = pdrive(FakeP([STAR6]), 'PT')
assert res.startswith('STOP') and lg == []
fk = FakeP([SCREEN6, PTITLE, STAR6, SCREEN6])
res, lg = pdrive(fk, 'PN')                       # PN: same CALL form, same three timed attempts, no other key
assert res == 'ok' and [x['action'] for x in lg] == ['CALL', 'PF4', 'PF5', 'PF6', 'ENTER']
assert "String(\"CALL 'Z00000.PACMAN.Z6PRB.LOAD(PACZ6P)' 'PN'\")" in fk.calls
fk = FakeP([SCREEN6, PTITLE, STAR6, SCREEN6])
res, lg = pdrive(fk, 'PH')
assert res == 'ok' and "String(\"CALL 'Z00000.PACMAN.Z6PRB.LOAD(PACZ6P)' 'PH'\")" in fk.calls
fk = FakeP([SCREEN6, PTITLE, STAR6, SCREEN6])
res, lg = pdrive(fk, 'PB4')
assert res == 'ok' and "String(\"CALL 'Z00000.PACMAN.Z6PRB.LOAD(PACZ6P)' 'PB4'\")" in fk.calls
assert [x['action'] for x in lg] == ['CALL', 'PF4', 'PF5', 'PF6', 'ENTER']
fk = FakeP([SCREEN6, PTITLE, STAR6, SCREEN6])
res, lg = pdrive(fk, 'PR2')
assert res == 'ok' and "String(\"CALL 'Z00000.PACMAN.Z6PRB.LOAD(PACZ6P)' 'PR2'\")" in fk.calls
fk = FakeP([SCREEN6, PTITLE, STAR6, SCREEN6])
res, lg = pdrive(fk, 'PR2I')                     # same plan; only the CALL operand differs
assert res == 'ok' and "String(\"CALL 'Z00000.PACMAN.Z6PRB.LOAD(PACZ6P)' 'PR2I'\")" in fk.calls
assert [x['action'] for x in lg] == ['CALL', 'PF4', 'PF5', 'PF6', 'ENTER']
print('ZOS-6 protocol probe (local): PACZ6P source (P0 TPUT NOEDIT / PT TPG NOEDIT,WAIT,NOHOLD + TGET ASIS,NOWAIT / PN TGET ASIS,NOWAIT before TPUT / PH TPUT NOEDIT,WAIT,HOLD / PB4 HOLD every 4th quantum / PR2 write every 2nd quantum / PR2I + host table, '
      'AMODE / RMODE 24, no ATTACH / STAX / ESTAE / LE), generated deck (ASM + LKED into the existing Z6PRB.LOAD, no allocation, no DELETE), analyzer on '
      'synthetic P0 / PT / PN / PH / PB4 / PR2 traces (aid_test_exercised, lag by phase, write coalescing, PR2I table), input controller on a fake x3270if: PASS')

# 22. ZOS-6 production implementation (docs/zos6-production-design.md, ZV-D33; local only: nothing built, uploaded or
#     run live). PRESENT(EVERY|COALESCED): the CLIST PARM (EVERY = the 2.0 PARM byte for byte), the COBOL control flow
#     (PACMAIN phases A S D R W B T, PACPLAT PSLT interpreted from its source, PACDISP / PACSCR RTQS), the filtered model
#     (tests/ref_rt.py present='C': grid, no replay / catch-up, logical identity with EVERY, the image invariant, the
#     skipped-quantum display state, the S2 pattern clock) and the checker (logical quanta vs physical frames, the
#     9 / 10 / 11-quantum freeze discrimination, trace-clock input reaction, the predeclared candidate gates)
import copy  # noqa: E402
import ref_rt  # noqa: E402
import zos6_fixture as F6  # noqa: E402
import zos6_live_check as C6  # noqa: E402
import zos6_drive as D6  # noqa: E402
from make_deck import RT_TSD  # noqa: E402
import ref_rp as RP22  # noqa: E402
import ref_s2 as S22  # noqa: E402
import ref_gp2 as L22  # noqa: E402
from ref_snap import Log as Log22  # noqa: E402
TAG22 = zos_c2.TAG


def tag22(rel):
    return zos_c2.at_tag(rel)


# --- 26 / 27 / 28: PACFSIO and zos5_live_check.py byte-identical; the portable game modules = their Z1 text only
assert (R / 'src/asm/PACFSIO.asm').read_text() == tag22('src/asm/PACFSIO.asm')
assert (R / 'src/asm/PACTSO.asm').read_text() == tag22('src/asm/PACTSO.asm')
assert subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'tools/zowe/zos5_live_check.py'], cwd=R).returncode == 0
assert subprocess.run(['git', 'ls-files', '--error-unmatch', 'tools/zowe/zos5_live_check.py'], cwd=R,
                      capture_output=True).returncode == 0
for rel in ('src/cobol/PACRT.cob', 'src/cobol/PACGAME.cob', 'src/cobol/PACMAP.cob', 'src/cobol/PACAI.cob',
            'src/cobol/PACINPT.cob', 'src/copy/PACSTATE.cpy', 'src/copy/PACARC.cpy', 'src/copy/PACDS.cpy'):
    assert (R / rel).read_text() == zos_c2.z1_text(rel), rel
zos_c2.guard()
assert sorted(zos_c2.z4_table()) == sorted(zos_c2.Z4_FILES) and 'src/asm/PACFSIO.asm' not in zos_c2.Z4_FILES
for rel in zos_c2.Z4_FILES:                               # Z4 is pure addition except two replaced lines (listed)
    for i1, i2, old, new in zos_c2.z4_table()[rel]:
        assert len(old) <= 1 and len(new) >= len(old), (rel, i1, old)
old22 = tag22('src/copy/PACREQ.cpy').split('\n')
new22 = (R / 'src/copy/PACREQ.cpy').read_text().split('\n')
assert new22[:len(old22) - 1] == old22[:-1] and [l for l in new22[len(old22) - 1:] if l.strip() and l[6] != '*'] == [
    '           05  REQ-PMODE             PIC X.', '           05  REQ-PRES              PIC X.']   # appended: no offset moves


# --- 1 / 2: the z/OS CLIST PARM (an independent evaluator of the PARM statements) - absent PRESENT == EVERY == the 2.0
#     PARM byte for byte; COALESCED adds column 26 = C; the MVS CLIST untouched
def clist_parm22(text, kw):
    lines = text.split('\n')
    proc = ' '.join(l.rstrip('+ ') for l in lines[:lines.index(next(l for l in lines if l.startswith('/*')))])
    v = {k: d for k, d in re.findall(r'(\w+)\((\w*)\)', proc)}
    v.update(re.findall(r'(\w+)\((\w*)\)', kw))
    env = {'&' + k: x for k, x in v.items()}

    def val(x):
        x = x.strip()
        m = re.fullmatch(r'&SUBSTR\(1:1,(&\w+)\)', x)
        if m:
            return env[m.group(1)][:1]
        m = re.fullmatch(r'&STR\((.*)\)', x)
        if m:
            return re.sub(r'&\w+', lambda g: env[g.group(0)], m.group(1)) if m.group(1) else ''
        m = re.fullmatch(r'&LENGTH\(&STR\((&\w+)\)\)', x)
        if m:
            return str(len(env[m.group(1)]))
        return env[x] if x.startswith('&') else x
    after = False                             # after the 2.0 PARM line only &E / &P statements (Z2 lines ignored)
    for l in lines:
        m = re.fullmatch(r'SET (&[A-Z]) = (.*)', l)
        f = re.fullmatch(r'IF (.+?) (=|NE) (\S+) THEN SET (&[A-Z]) = (.*)', l)
        skip = ('&Z', '&T', '&I') if not after else tuple('&' + c for c in 'ABCDFGHIJKLMNOQRSTUVWXYZ')
        after = after or l.startswith('SET &P =')
        if m and m.group(1) not in skip:
            env[m.group(1)] = val(m.group(2))
        elif f and f.group(4) not in skip:
            a, b = val(f.group(1)), val(f.group(3))
            if (a == b) == (f.group(2) == '='):
                env[f.group(4)] = val(f.group(5))
        if l.startswith("CALL '"):
            return env['&P']


zcl = (R / 'src/zos/PACMAN.clist').read_text()
mcl = tag22('src/clist/PACMAN.clist')
assert (R / 'src/clist/PACMAN.clist').read_text() == mcl                               # MVS CLIST untouched
for kw in ('', 'AI(0) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO)', 'AI(0) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO) '
           'SPEED(FAST)', 'AI(3) GHOSTS(2) COLOR(NO) LEVEL(7)', 'METRICS(YES) ALARM(SINGLE) LEVEL(12)'):
    legacy = clist_parm22(mcl, kw)
    assert len(legacy) == 25 and clist_parm22(zcl, kw) == legacy and clist_parm22(zcl, kw + ' PRESENT(EVERY)') == legacy
    assert clist_parm22(zcl, kw + ' PRESENT(COALESCED)') == legacy + 'C', kw
assert clist_parm22(zcl, 'AI(0) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO) PRESENT(COALESCED)') == \
    'TSO AI0 1 NAAAPAAARNC01NPC'
assert zos_c2.z5_strip(zcl).count('PRESENT') == 0 and '  ALARM(PATTERN) PRESENT(EVERY)' in zcl.split('\n')
assert zos_c2.Z5_SET_AFTER in zcl.split('\n') and zos_c2.Z5_SET_AFTER in mcl.split('\n')   # the 2.0 PARM line as is
# the Z5 statements reuse only forms the 2.0 CLIST already runs (no null SET: the one &STR() in the repository is a
# comparison, src/probe/RTPROBE.clist): SET &v = &SUBSTR(1:1,&kw), IF &v = literal THEN SET ..., &STR(.. &v&w ..)
assert zos_c2.Z5_SET[2:] == ['SET &E = &SUBSTR(1:1,&PRESENT)', 'IF &E = C THEN SET &P = &STR(&P&E)']
assert 'SET &K = &SUBSTR(1:1,&ALARM)' in mcl and 'IF &METRICS = YES THEN SET &M = M' in mcl and '&F&K)' in mcl
assert not re.search(r'SET &\w+ = (&STR\(\))?$', zcl, re.M)


# --- the COBOL sources: a minimal interpreter for the PSLT / pattern-clock paragraphs (MOVE / ADD / SUBTRACT / GO TO
#     / IF with = / NOT = / NOT < / > joined by AND; CALL ignored), so the slot rule is checked on the source itself
def para22(rel, name):
    ls = (R / rel).read_text().split('\n')
    i = ls.index(f'       {name}.')
    out = []
    for l in ls[i + 1:]:
        if re.fullmatch(r'       [A-Z0-9-]+\.', l):
            break
        if len(l) > 6 and l[6] == '*':
            continue
        out.append(l[7:72].strip())
    return out


def cobol22(lines, env):
    text = ' '.join(lines)
    sents = [x.strip() for x in re.split(r"\.(?=\s|$)", text) if x.strip()]
    verbs = ('MOVE', 'ADD', 'SUBTRACT', 'GO', 'CALL', 'PERFORM')

    def val(t):
        return t[1:-1] if t.startswith("'") else int(t) if t.isdigit() else env[t]

    def cond(ts):
        for c in ' '.join(ts).split(' AND '):
            c = c.split()
            a, op, b = c[0], ' '.join(c[1:-1]), c[-1]
            x, y = val(a), val(b)
            ok = {'=': x == y, 'NOT =': x != y, 'NOT <': x >= y, '>': x > y}[op]
            if not ok:
                return False
        return True

    def stmts(ts):
        k = 0
        while k < len(ts):
            j = next((n for n in range(k + 1, len(ts)) if ts[n] in verbs), len(ts))
            st = ts[k:j]
            k = j
            if st[0] == 'MOVE':
                env[st[3]] = val(st[1])
            elif st[0] == 'ADD':
                env[st[3]] = env[st[3]] + val(st[1])
            elif st[0] == 'SUBTRACT':
                env[st[3]] = env[st[3]] - val(st[1])
            elif st[0] == 'GO':
                return 'exit'
    for se in sents:
        ts = re.findall(r"'[^']*'|\S+", se)
        if ts[0] == 'IF':
            j = next(n for n in range(1, len(ts)) if ts[n] in verbs)
            if cond(ts[1:j]) and stmts(ts[j:]) == 'exit':
                return env
        elif stmts(ts) == 'exit':
            return env
    return env


PSLT22 = para22('src/cobol/PACPLAT.cob', 'DO-PSLT')
PSTP22 = int(re.search(r'01  PS-TP\s+PIC 9\(4\) VALUE (\d+)\.', (R / 'src/cobol/PACPLAT.cob').read_text()).group(1))
assert PSTP22 == ref_rt.PRES_TP == 300


def cobol_slots22(pmode, mode, per, seq):
    """Drive the COBOL DO-PSLT over seq ('B' base / 'Q' quantum) -> the Y / N answers."""
    env, out = {'PS-ACC': 0, 'PS-TP': PSTP22, 'REQ-PMODE': pmode, 'REQ-MODE': mode, 'REQ-RTPER': per}, ''
    for x in seq:
        env['REQ-PRES'] = x
        out += cobol22(PSLT22, env)['REQ-PRES']
    return out


SEQ22 = 'B' + 'Q' * 11 + 'B' + 'Q' * 5 + 'B' + 'Q' * 400
for per, stride in ((150, 2), (125, 3)):                  # 4 / 5 / 7 / 8: the slot grid, anchored at every base
    cy = cobol_slots22('C', 'TSC', per, SEQ22)
    assert cy == cobol_slots22('C', 'TSD', per, SEQ22)
    exp, acc = '', 0
    for x in SEQ22:
        if x == 'B':
            exp, acc = exp + 'Y', 0
            continue
        acc += 1
        exp += 'Y' if acc % stride == 0 else 'N'
    assert cy == exp, (per, cy[:40])
    assert all(SEQ22[i + 1] == 'B' for i in range(len(cy) - 1) if cy[i:i + 2] == 'YY')   # two in a row: a base only
    assert cy.count('Y') == SEQ22.count('B') + sum(len(r) // stride for r in SEQ22.split('B') if r)
for pmode, mode in ((' ', 'TSC'), (' ', 'TSD'), ('C', 'BAT'), ('C', 'TSO'), ('X', 'TSC')):   # 3: EVERY / non-screen
    assert set(cobol_slots22(pmode, mode, 150, SEQ22)) == {'Y'}, (pmode, mode)


# --- 3 / 9 / 10 / 11: PACMAIN phase order and the EVERY path (no post-write poll, RT-FRAME cleared every quantum)
RTQ22 = para22('src/cobol/PACMAIN.cob', 'RT-QUANTUM')
J22 = ' | '.join(RTQ22)
order22 = [J22.rindex(x) for x in ('PERFORM RT-COLLECT', "MOVE 'RQ  ' TO REQ-OP", "MOVE 'PSLT' TO REQ-OP",
                                   "MOVE 'RTQF' TO REQ-OP", 'IF F-WON = 1', 'PERFORM RT-POST-READ',
                                   'IF RT-OVER = 1 | GO TO RT-QUANTUM-EXIT', "MOVE 'WDLN' TO REQ-OP")]
assert order22 == sorted(order22), order22                 # A S D R (W inside R) B T
assert "IF REQ-PMODE = 'C' AND REQ-PRES = 'Y' | AND REQ-MODE = 'TSC' | PERFORM RT-POST-READ THRU RT-POST-READ-EXIT" \
    in J22                                                   # B: COALESCED, presented, live terminal only
assert "IF REQ-PRES = 'Y' | MOVE SPACE TO RT-FRAME" in J22  # a prompt frame waits for the next presented quantum
assert para22('src/cobol/PACMAIN.cob', 'RT-POST-READ') == ['PERFORM RT-READ.', 'PERFORM RT-EVENT THRU RT-EVENT-EXIT.']
assert para22('src/cobol/PACMAIN.cob', 'RT-READ') == ['MOVE SPACE TO REQ-INKEY.', "MOVE 'RTRD' TO REQ-OP.",
                                                       "CALL 'PACINPT' USING PAC-REQ."]
rtsc22 = ' '.join(para22('src/cobol/PACINPT.cob', 'RT-TSC'))  # one RTRD = one PACPLAT POLL = one PACFSIO POLL = 1 TGET
assert rtsc22.count("CALL 'PACPLAT'") == 1 and ' '.join(para22('src/cobol/PACPLAT.cob', 'DO-POLL')).count(
    "CALL 'PACFSIO'") == 1
assert re.findall(r'TGET .*', ' '.join(l for l in (R / 'src/asm/PACFSIO.asm').read_text().split('\n')
                                       if 'POLL' in l or 'TGET' in l)).count('TGET  (1),(0),ASIS,NOWAIT') <= 2
mm22 = ' | '.join(para22('src/cobol/PACMAIN.cob', 'MAIN-PARA'))
assert "MOVE SPACE TO REQ-PMODE. | IF PARM-LEN > 25 AND PARM-PRES = 'C' | MOVE 'C' TO REQ-PMODE. | MOVE 'Y' TO " \
    "REQ-PRES." in mm22
assert "MOVE 1 TO RT-PBASE." in ' | '.join(para22('src/cobol/PACMAIN.cob', 'RT-GAME')) and \
    ' | '.join(para22('src/cobol/PACMAIN.cob', 'RT-PAUSED')).index('MOVE 1 TO RT-PBASE.') < \
    ' | '.join(para22('src/cobol/PACMAIN.cob', 'RT-PAUSED')).index('PERFORM RT-COLLECT')       # 8: resume = base
assert "MOVE 'Q' TO REQ-PRES. | IF RT-PBASE = 1 | MOVE 'B' TO REQ-PRES. | MOVE 0 TO RT-PBASE." in J22
assert C6.cards_for(6, [3, 3], ['L', 'R']) == ['.', '.', 'LR', '.', '.', '.']          # 10: B(k) before A(k + 1)

# --- 12 / 13 / 14 / 15: RTQS = display state of logical time only; the pattern clock; the diff baseline untouched
assert para22('src/cobol/PACSCR.cob', 'DO-RTQS') == ['MOVE 0 TO DS-LEN.', 'PERFORM RP-STATE THRU RP-STATE-EXIT.',
                                                     'PERFORM SET-FACE.', "IF REQ-ANIM = 'Y'", 'MOVE REQ-VIS TO VIS.']
assert "IF REQ-ANIM = 'Y' MOVE REQ-VIS TO VIS." in ' '.join(para22('src/cobol/PACSCR.cob', 'DO-RTQF')) or \
    'MOVE REQ-VIS TO VIS.' in ' '.join(para22('src/cobol/PACSCR.cob', 'DO-RTQF'))      # the same update as DO-RTQF
assert 'VIS' not in ' '.join(para22('src/cobol/PACSCR.cob', 'DO-ENDS')) and \
    'SET-FACE' in ' '.join(para22('src/cobol/PACSCR.cob', 'DO-ENDS'))     # DO-ENDS draws the saved VIS (unchanged)
scr22 = (R / 'src/cobol/PACSCR.cob').read_text()


def closure22(rel, names):
    seen, todo = set(), list(names)
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        for l in para22(rel, n):
            todo += [x for x in re.findall(r'PERFORM ([A-Z0-9-]+)', l)]
    return seen


touch22 = closure22('src/cobol/PACSCR.cob', ['RP-STATE', 'SET-FACE'])
body22 = ' '.join(' '.join(para22('src/cobol/PACSCR.cob', n)) for n in touch22)
assert 'WS-FACE' in body22 and 'PU-T0' in body22 and 'PU-X' in body22                      # 12 / 13
for bad in ('VS-PREV', 'PREV-OK', 'VS-CUR', 'KEEP-VS', 'DIFF-', 'PUT-BYTE', 'PUT-TAIL', 'DS-BUF', 'MSG-ON', 'MSG-LAST'):
    assert bad not in body22, bad                                                         # 15 (and the message)
assert para22('src/cobol/PACDISP.cob', 'SCR-RTQS') == [
    "MOVE 'RTQS' TO REQ-OP.", "CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS", 'PAC-ARC.', "MOVE 'RTQF' TO REQ-OP.",
    'IF PT-ON = 1 AND PT-NEXT > 1', 'SUBTRACT 1 FROM PT-NEXT.']                       # 14: no SEND / BELL / SB / metric
assert "ELSE IF REQ-OP = 'RTQF' AND REQ-PRES = 'N' | PERFORM SCR-RTQS | ELSE IF REQ-OP = 'RTQF'" in \
    ' | '.join(para22('src/cobol/PACDISP.cob', 'SCREEN-OP'))
for nxt, on, want in ((3, 1, 2), (2, 1, 1), (1, 1, 1), (3, 0, 3)):                    # the COBOL rule = ref_s2 skips
    e22 = cobol22(para22('src/cobol/PACDISP.cob', 'SCR-RTQS'), {'PT-ON': on, 'PT-NEXT': nxt, 'REQ-OP': 'RTQF'})
    assert e22['PT-NEXT'] == want and e22['REQ-OP'] == 'RTQF'

# --- 16 / 17 / 18: the model. Default / EVERY = the frozen oracle streams (section 20 anchors ref_rt to 310); every
#     RT TSD case at both speeds: the filtered model runs every quantum (same end lines, rqs, consumed events), presents
#     the grid, never replays, and each presented image = the unfiltered model's image of that quantum
def tsd22(cards, cv, per, present, **kw):
    log = Log22()
    log.kinds = []
    out, fr = ref_rt.tsd(cards, cv, snap=log, per=per, present=present, **kw)
    return out, fr, log


INV22 = 'INVALID'.encode('cp037')


def img_eq22(a, b, gw, stat):
    """The image invariant with its one listed exemption (physical presentation state, design section 16): the
    invalid-input message is a one-shot latch (PACSCR MSG-ON) shown by the next presented prompt frame; when EVERY shows
    and clears it inside one coalesced interval the two images may differ on the message row only, with INVALID there
    on one side."""
    if a == b:
        return True
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    rows = {i // gw for i in diff}
    if len(a) != len(b) or len(rows) != 1:
        return False
    r = rows.pop()
    txt = [bytes(c[0] for c in im[r * gw:(r + 1) * gw]) for im in (a, b)]
    ok = any(INV22 in t for t in txt)
    stat['msg'] += ok
    return ok


def grid22(fr, kinds, stride):
    qi = [j for j, k in enumerate(kinds) if k in ('Q', 'P')]
    assert all(fr.qs[a] < fr.qs[b] for a, b in zip(qi, qi[1:]))                           # 6: no replay
    for a, b in zip(qi, qi[1:]):
        if b == a + 1:
            assert fr.qs[b] - fr.qs[a] == stride, (fr.qs[a], fr.qs[b])                    # 7: no catch-up burst
    return qi


ncase22, st22, vis_diff22 = 0, {'msg': 0}, 0
for c, cv in RT_TSD + [('RTLONG', 'W'), ('RTWIN', 'W'), ('RTEDGE', 'W'), ('RTTTL', 'W'), ('RTREV', 'W')]:
    raw = (R / f'tests/rtcases/{c}.txt').read_text().splitlines()
    cards = ([raw[0]] if raw[0][:1] == 'A' else ['AI1 1']) + [x for x in (raw[1:] if raw[0][:1] == 'A' else raw)]
    for per, stride in ((150, 2), (125, 3)):
        oe, fe, le = tsd22(cards, cv, per, None)
        oE, fE, _ = tsd22(cards, cv, per, 'E')
        assert list(fe) == list(fE) and oe == oE and fe.qs == fE.qs                        # 16: default == EVERY
        oc, fc22, lc = tsd22(cards, cv, per, 'C')
        assert oc == oe, c                                                                 # same logical game
        qi = grid22(fc22, lc.kinds, stride)
        ev = {q: im for q, im in zip(fe.qs, fe.imgs) if q is not None}
        gw = len(fe.imgs[0]) // (27 if cv == 'W' else 24)
        assert all(img_eq22(ev[q], im, gw, st22) for q, im in zip(fc22.qs, fc22.imgs) if q is not None), c
        if lc.kinds[-1] == 'E':          # the end screen: the final logical state (VIS too, RTQS), = EVERY's
            assert le.kinds[-1] == 'E' and fc22.imgs[-1] == fe.imgs[-1] and list(fc22)[-1] == list(fe)[-1], c
            qp = [q for q in fc22.qs if q is not None]
            qf = int(oc[-1].split()[1])
            vis_diff22 += ((qp[-1] // ref_rt.ANIM_Q) % 2) != ((qf // ref_rt.ANIM_Q) % 2)
        assert len(qi) < len([q for q in fe.qs if q is not None]) or len(qi) <= 2
        ncase22 += 1
assert C6.STRIDE == {150: 2, 125: 3}
assert vis_diff22 >= 1, vis_diff22      # runs whose last presented VIS differs from the final one (the PACZ6DR1 defect)
# the old defect, caught on real z/OS output: PACZ6DR1 JOB09418 (PACZ6D before the RTQS VIS fix) - N2 / N3 differ from
# the model only in the end screen (the sprite of the last presented VIS); with the comparator fix N1 matches
import zos6_dry as DRY22  # noqa: E402
sp22 = R / 'build/zos/PACZ6DR1-JOB09418'
if sp22.exists():
    ok22, rep22 = DRY22.check(sp22, 1)
    st22r = {k: v['state'] for k, v in rep22['steps'].items()}
    assert not ok22 and st22r == {'E1': 'PASS', 'E2': 'PASS', 'N1': 'PASS', 'N2': 'FAIL', 'N3': 'FAIL', 'N4': 'PASS'}, st22r
    for k in ('N2', 'N3'):
        st_ = next(s for s in DRY22.STEPS if s['step'] == k)
        _, frz, _ = DRY22.parse_tsd(__import__('zos_equiv').zos_runs(sp22)[2][k]['lines'])
        mz = DRY22.model(st_)
        assert frz[:-1] == mz['frames'][:-1] and frz[-1] != mz['frames'][-1] and mz['kinds'][-1] == 'E', k

# ARCADE (RULES(ARCADE): popups, death frames, READY!, facing) - every RP / GP2 REALTIME case, both speeds
pu22 = []
real_start22 = RP22.Tracker.start


def rec_start22(self, cell, pts, col, kind, now):
    pu22.append(now)
    return real_start22(self, cell, pts, col, kind, now)


from make_deck import RP_RT as RPRT22, RP_SEED as SEED22  # noqa: E402
RP22.Tracker.start = rec_start22
try:
    narc22, skipped_pu22 = 0, 0
    for d, c, cv, snd, st_, dd in RPRT22:
        start = L22.parse_start(st_)
        hs = None if not dd else ('E', 0, start) if dd == 'DUMMY' else             ('R', SEED22[dd[2:]], start) if dd[2:] in SEED22 else ('Z', 0, start)
        cards = (R / f'tests/{d}/{c}.txt').read_text().splitlines()
        for per in (150, 125):
            mk = (lambda ai, n, s=start: L22.Level(ai, n, 'R', s))
            pu22.clear()
            oe, fe = ref_rt.tsd(cards, cv, mk_game=mk, mk_ctl=L22.LevelRT, hs=hs, per=per)
            eat_q = list(pu22)
            pu22.clear()
            oc, fcz = ref_rt.tsd(cards, cv, mk_game=mk, mk_ctl=L22.LevelRT, hs=hs, per=per, present='C')
            assert oc == oe, (c, per)
            ev = {q: im for q, im in zip(fe.qs, fe.imgs) if q is not None}
            assert all(im == ev[q] for q, im in zip(fcz.qs, fcz.imgs) if q is not None), (c, per)    # 12 / 13
            slots = {q for q in fcz.qs if q is not None}
            skipped_pu22 += sum(1 for q in eat_q if q not in slots)
            assert sorted(pu22) == sorted(eat_q), (c, per, pu22, eat_q)       # PU-T0 = the event quantum (RTQS)
            narc22 += 1
finally:
    RP22.Tracker.start = real_start22
assert narc22 >= 10 and skipped_pu22 >= 1, (narc22, skipped_pu22)

# 12: the facing - L lands on a skipped quantum, U on the next (presented) one: the presented frame faces left as in
# EVERY (SET-FACE ran on the skipped quantum)
face22 = None
for k in range(2, 40):
    cs = ['AI0 1', 'R'] + ['.'] * k + ['L', 'U'] + ['.'] * 6 + ['Q']
    oe, fe = ref_rt.tsd(cs, 'W')
    oc, fcf = ref_rt.tsd(cs, 'W', present='C')
    ev = {q: im for q, im in zip(fe.qs, fe.imgs) if q is not None}
    assert all(im == ev[q] for q, im in zip(fcf.qs, fcf.imgs) if q is not None)
    lq = k + 2                                               # the L card's quantum
    if lq not in set(fcf.qs) and lq in ev and ev[lq] != ev.get(lq - 1):
        face22 = cs
        break
assert face22 is not None                                    # such a case exists and passed the invariant

# 14: the S2 pattern clock on skipped quanta (ref_s2 skips = PACDISP SCR-RTQS): CLASSIC death with SOUND Y, ALARM P
for per in (150, 125):
    cs = (R / 'tests/rtcases/RTSTILL.txt').read_text().splitlines()
    cs = cs if cs[0][:1] == 'A' else ['AI1 1'] + cs
    _, fe, le = tsd22(cs, 'W', per, None)
    _, fc14, lc14 = tsd22(cs, 'W', per, 'C')
    _, tre = S22.patterns(list(fe), le, 'Y', 'R', per)
    _, trc = S22.patterns(list(fc14), lc14, 'Y', 'R', per, skips=fc14.skips)
    tre = [x for x in tre if x[0] < len(fe) and fe.qs[x[0]] is not None]          # rings on quantum writes
    trc = [x for x in trc if x[0] < len(fc14) and fc14.qs[x[0]] is not None]
    qe = [fe.qs[k] for k, _, _ in tre]
    qc = [fc14.qs[k] for k, _, _ in trc]
    assert [n for _, n, _ in tre] == [n for _, n, _ in trc] and all(a >= b for a, b in zip(qc, qe)), (qe, qc)
    steps = [q for (k, n, _), q in zip(trc, qc) if n == 'STEP']
    assert steps and all(q - qc[i - 1] == S22.gap(per) for i, ((k, n, _), q) in enumerate(zip(trc, qc))
                         if n == 'STEP'), qc                     # every step G LOGICAL quanta after the ring before it
    _, trn = S22.patterns(list(fc14), lc14, 'Y', 'R', per)                       # without the skips: wrong spacing
    assert [fc14.qs[k] for k, n, _ in trn if n == 'STEP' and k < len(fc14)] != steps and steps, (per, steps)
assert sum(fc14.skips) > 0

# --- 19 .. 25: the checker on COALESCED synthetic traces (tests/zos6_fixture.py simulates a coalesced host: polls
#     every quantum, writes at the PSLT slots, one post-write poll B)
PLAN22 = copy.deepcopy(D6.PLANS['R1'])
PLAN22['cfg'] = 'AI1 1'          # test-only: a moving ghost, so the frames depend on the freeze length


def run22(case, plan=None, **kw):
    text, lg = F6.build(case, plan=plan, **kw)
    try:
        return C6.check(text, lg, case, plan=plan)
    except C6.Fail as ex:
        return {'state': C6.FAILED, 'why': str(ex)}


rm = run22('R1', PLAN22)                                     # 23: the exact 10-quantum freeze, both mutants rejected
assert rm['state'] == C6.PASS and rm['present'] == 'C' and rm['death_runs'] == [10], rm.get('blocked', rm.get('why'))
assert rm['freeze_mutants'] == {9: 'rejected', 11: 'rejected'} and rm['death_ms'] == 1500
assert rm['death_pair_quanta'][1] - rm['death_pair_quanta'][0] == 10 and rm['writes'] < rm['quanta']
for frt, n in ((9, '21'), (11, '22')):                       # a host freezing 9 / 11 quanta: FUNCTIONAL FAIL
    r = run22('R1', PLAN22, frt=frt)
    assert r['state'] == C6.FAILED and 'does not match the model' in r['why'], (n, r.get('why'))
r1c = run22('R1')                         # the approved R1 plan (AI(0)): 9 / 10 / 11 observationally identical -
assert r1c['state'] == C6.PASS and r1c['live_freeze_discrimination'] == 'NOT OBSERVABLE', r1c.get('blocked',
                                                                                                 r1c.get('why'))
assert r1c['freeze_mutants'] == {9: 'matches', 11: 'matches'} and r1c['death_runs'] == [10] and \
    1350 <= r1c['death_ms'] <= 1650 and 'PACRT unchanged' in r1c['logical_freeze_proof']   # reported, not a PASS of it
assert rm['live_freeze_discrimination'] == 'DISCRIMINATED'
# the logical freeze proof for R1 (offline): PACRT unchanged (above, Z1 text) and RTSTILL - the model's freeze is
# exactly quanta(10) at both speeds (oracle 310 RTB7 / RTT2 anchor RTSTILL in section 20)
for per22 in (150, 125):
    cs22 = (R / 'tests/rtcases/RTSTILL.txt').read_text().splitlines()
    m22 = C6.model(cs22[1:] if cs22[0][:1] == 'A' else cs22, 'W', per22, 'C',
                   cfg=cs22[0] if cs22[0][:1] == 'A' else 'AI1 1')
    runs22, cur = [], 0
    for kd, _ in m22['rqs'] + [('-', 0)]:
        cur = cur + 1 if kd == 'F' else (runs22.append(cur) or 0) if cur else 0
    assert runs22 and set(runs22) == {ref_rt.quanta(10, per22)}, (per22, runs22)
assert 'FRZ-INIT              PIC 99 VALUE 10.' in (R / 'src/cobol/PACRT.cob').read_text()
r2c = run22('R2')
assert r2c['state'] == C6.PASS and r2c['present'] == 'C' and r2c['principal']['quanta'] >= 200, r2c.get('why')
assert set(b - a for a, b in zip(r2c['frame_quanta'], r2c['frame_quanta'][1:])) <= {3, 1} and \
    r2c['gates']['physical']['median'] == 375
assert [(d['action'], d['aid'], d['model']) for d in r2c['directional']] == [
    ('PF11', '7B', 'R'), ('PF8', 'F8', 'D'), ('PF7', 'F7', 'U'), ('PF10', '7A', 'L')]
for w, why in ((40, 'non-slot write'), (60, 'replay')):                                  # 19 / 20
    r = run22('R2', **({'nonslot': w} if why == 'non-slot write' else {'replay': w}))
    assert r['state'] == C6.FAILED and ('differs from the model' in r['why'] or 'permitted quantum' in r['why']), \
        (why, r.get('why'))
# 9 / 11: delivery only after a write (PR2I-C2): every running AID is read by B and placed on the card after a write
for case, plan in (('R1', PLAN22), ('R2', None)):
    r = run22(case, plan, visibility='write')
    assert r['state'] == C6.PASS, (case, r.get('blocked', r.get('why')))
    pf9 = [n for n, (a, _, _) in enumerate(r['placements']) if a == 'PF9']
    run_aids = [s for n, (a, s, _) in enumerate(r['placements']) if n > 0 and n not in pf9[1::2]]   # not blocking
    assert run_aids and all(s - 1 in r['frame_cards'] for s in run_aids), (case, run_aids)   # card after a write
    assert len(r['placements']) == len(r['reaction'])
# 24: input reaction in the trace clock only - the driver log timestamps (shifted by 10 s, still consistent) change
#     nothing; and the measure is wire AID -> arrival of the first write answering the card or later
t24, lg24 = F6.build('R2')
sh24 = []
for x in lg24:
    y = json.loads(x)
    for k in ('requested', 'wait_start', 'unlocked', 'sent'):
        y[k] += 10000
    sh24.append(json.dumps(y))
ra, rb = C6.check(t24, lg24, 'R2'), C6.check(t24, sh24, 'R2')
assert ra['reaction'] == rb['reaction'] and all(x['ms'] is not None and x['ms'] > 0 for x in ra['reaction'])
assert C6.reaction(1000, [0, 1, 3, 5, 7], [0, 900, 1200, 1500, 1800], 4) == (3, 500)
assert C6.reaction(1000, [0, 1, 3], [0, 900, 1200], 9) == (None, None)
# 25: the predeclared candidate gates (BLOCKED, never FAIL) - NORMAL / FAST values as approved
assert C6.GATES[150] == {'median': (280, 320), 'p95': 450, 'max': 1000, 'backlog': 100, 'react': 1000,
                         'react_median': 750}
assert C6.GATES[125] == {'median': (345, 405), 'p95': 525, 'max': 1000, 'backlog': 100, 'react': 1075,
                         'react_median': 825}
nw25 = r2c['writes']
gates25 = {
    'physical median': dict(scale=1.1),
    'physical p95': dict(delay={i: 200 for i in range(30, nw25 - 5, 8)}),
    'physical max': dict(delay={50: 700}),
    'backlog delta': dict(delay={i: 160 for i in range(55, nw25)}),
    'input reaction': dict(delay={r2c['reaction'][2]['write']: 900}),        # PF7's answering frame 0.9 s late
}
for why, kw in gates25.items():
    r = run22('R2', **kw)
    assert r['state'] == C6.BLOCKED and any(b.startswith(why) for b in r['blocked']), (why, r.get('blocked'),
                                                                                       r.get('why'))
# a game that ends (LOST) on a COALESCED quantum: no write for the deciding quantum, the end screen follows at once;
# a host that writes the deciding quantum anyway fails
for T in (150, 125):
    pg = {'T': T, 'present': 'C', 'cfg': 'AI2 3', 'kw': 'AI(2) GHOSTS(3) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO) '
          'PRESENT(COALESCED)' + (' SPEED(FAST)' if T == 125 else ''),
          'steps': [('transition', 'EXEC'), ('expect', '***'), ('transition', 'ENTER'), ('expect', 'GAME'),
                    ('wait', 2), ('gameplay', 'PF8'), ('wait', 60), ('expect', '***'), ('closure', 'ENTER'),
                    ('expect', 'SHELL')]}
    rg = run22('R2', pg)
    qend = int(rg['end_lines'][4].split()[1])
    assert rg['state'] == C6.PASS and rg['end_lines'][0] == 'LOST' and qend not in rg['frame_quanta'], \
        (T, rg.get('blocked', rg.get('why')))
    assert rg['frame_quanta'][-1] < qend and rg['live_freeze_discrimination'] == 'DISCRIMINATED', \
        (T, rg['frame_quanta'][-3:], qend)
    rx = run22('R2', pg, nonslot=rg['writes'] - 1)           # an extra write before the end screen
    assert rx['state'] == C6.FAILED, (T, rx.get('why'))
# R1-T4 decisions (2026-10-19). (1) The TSO blocking-read CONTROL record `F1 C3`: accepted (counted, never a game write)
# only right after an AID read by a blocking TGET (start / resume); an unrelated, duplicated, different or substituted
# record fails. (2) The historical lateness-envelope rule: diagnostic under COALESCED, a BLOCKED rule under EVERY.
for case, n_ in (('R1', 2), ('R2', 1)):
    r = run22(case, tso_c3='blocking')
    assert r['state'] == C6.PASS and len(r['tso_controls']) == n_ and r['writes'] == run22(case)['writes'], \
        (case, r.get('why'), r.get('tso_controls'))
    assert {c['aid'] for c in r['tso_controls']} <= {'F8', 'F9', '7B'} and all('card' in c for c in r['tso_controls'])
for case in ('R1', 'R2'):
    for bad in ('unrelated', 'dup', 'other2', 'replace'):
        r = run22(case, tso_c3=bad)
        assert r['state'] == C6.FAILED, (case, bad, r.get('state'), r.get('blocked'))
rs = run22('R2', skip_at=120)                                # COALESCED: the envelope rise is a diagnostic only
assert rs['state'] == C6.PASS and any('probable skipped period' in x for x in rs.get('diag_notes', [])), \
    (rs.get('blocked'), rs.get('why'))
re_ = run6('R2', skip_at=120)                                # EVERY: the historical D33 rule still BLOCKS
assert re_['state'] == C6.BLOCKED and any('skipped period' in b for b in re_['blocked']), re_.get('blocked')
# 4: the NORMAL / FAST gates, the stride and the presentation interval are FROZEN as approved (2026-10-19); they are
# never tuned from live results
assert (C6.GATES, C6.STRIDE, ref_rt.PRES_TP, PSTP22) == (
    {150: {'median': (280, 320), 'p95': 450, 'max': 1000, 'backlog': 100, 'react': 1000, 'react_median': 750},
     125: {'median': (345, 405), 'p95': 525, 'max': 1000, 'backlog': 100, 'react': 1075, 'react_median': 825}},
    {150: 2, 125: 3}, 300, 300)
GATES_SHA22 = '13d815edc1c73fc0913b6c14549d85f13cd201c20ab073628ec4743a538c11e9'      # frozen 2026-10-19
assert hashlib.sha256(repr(sorted((k, sorted(v.items())) for k, v in C6.GATES.items())).encode()).hexdigest() == \
    GATES_SHA22
print(f'ZOS-6 production (ZV-D33, local): PRESENT absent = EVERY = the 2.0 PARM, COALESCED = column 26 C; PACFSIO / '
      f'PACTSO / zos5_live_check / PACRT / PACGAME / PACMAP / PACAI / PACINPT unchanged, Z4 = {len(zos_c2.Z4_FILES)} '
      f'sources; COBOL PSLT (interpreted) = 2 / 3-quantum grid, base at start / resume, no burst, EVERY / BAT / TSO = '
      f'every quantum; phases A S D R W B T, B = one RTRD = one TGET; RTQS = RP-STATE + SET-FACE, no image / diff; '
      f'model: {ncase22} RT + {narc22} ARCADE runs, image invariant ({st22["msg"]} message-row exemptions), '
      f'{skipped_pu22} popups started on skipped quanta, end screens = EVERY ({vis_diff22} with the last presented VIS '
      f'!= the final one; JOB09418 old defect caught), '
      f'S2 pattern clock; checker: moving-ghost freeze 10 PASS (DISCRIMINATED) / 9 / 11 FAIL, approved R1 plan PASS '
      f'with live freeze discrimination NOT OBSERVABLE (logical proof: PACRT unchanged + RTSTILL), R2 PASS, game over '
      f'on a coalesced quantum PASS, non-slot / replay FAIL, delivery after a write PASS, trace-clock reaction, '
      f'{len(gates25)} frozen candidate gates BLOCKED: PASS')


# 23. ZOS-6 production build deck PACZ6BLD (jcl/zos/PACZ6BLD.jcl = tools/zowe/zos_target.py z6bld_deck): the compiler
#     work-file override is explicit and local to this deck (JOB09327: COB8 PACSCR SYSUT11 B37-04 with TRK,(5,5)); the
#     historical default TRK,(5,5) of every other deck is unchanged
import zos_target as ZT23  # noqa: E402
import make_deck as MD23  # noqa: E402
if not ZT23._md:                  # an earlier section may already have swapped the step builders (apply is not idempotent)
    ZT23.apply(MD23, '@@HLQ@@.PACMAN')
assert ZT23.COB_WORK == [ZT23.COB_WORK_DEFAULT] == ['TRK,(5,5)'] and ZT23.Z6BLD_SPACE == 'CYL,(1,1)'
assert ZT23.cobol_work() == ''.join(f'//{f"SYSUT{i}":<9}DD UNIT=SYSALLDA,SPACE=(TRK,(5,5))\n' for i in range(1, 16)) + \
    '//SYSMDECK DD UNIT=SYSALLDA,SPACE=(TRK,(5,5))\n'                                   # 1: the default, byte for byte
z23 = ZT23.deck('Z6BLD', '@@HLQ@@.PACMAN')
assert ZT23.COB_WORK == ['TRK,(5,5)']                                                   # the override is not left set
assert z23 == (R / 'jcl/zos/PACZ6BLD.jcl').read_text()                                  # the deck of record
for name in ('Z2BLD', 'ZCMP', 'Z2DRV'):                                                  # 1: existing decks keep TRK
    t = ZT23.deck(name, '@@HLQ@@.PACMAN')
    assert 'CYL,(1,1)' not in t and t.count('SPACE=(TRK,(5,5))') >= 16, name
assert (R / 'jcl/zos/PACZ2CMP.jcl').read_text() == ZT23.deck('ZCMP', '@@HLQ@@.PACMAN')
st23 = ZT23.steps_of_deck(z23)
cob23 = [s for s in st23 if s != 'LINK']
assert list(st23) == cob23 + ['LINK'] and all('PGM=IGYCRCTL' in st23[s] for s in cob23)
assert [re.search(r'COBOL\((\w+)\)', st23[s]).group(1) for s in cob23] == ZT23.Z6BLD_UNITS == [
    'PACMAIN', 'PACGAME', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACRT']           # 4: the seven PACREQ users
for s in cob23:                                                                         # 2: CYL,(1,1) on the 16 files
    ws = re.findall(r'^//(SYSUT\d+|SYSMDECK)\s+DD UNIT=SYSALLDA,SPACE=\((.*)\)$', st23[s], re.M)
    assert sorted(w for w, _ in ws) == sorted([f'SYSUT{i}' for i in range(1, 16)] + ['SYSMDECK']) and \
        {sp for _, sp in ws} == {'CYL,(1,1)'}, s
    assert "PARM=('RENT,RMODE(24),DATA(24),NODYNAM'," in st23[s] and 'REGION=0M' in st23[s]
assert 'ASMA90' not in z23 and 'ASM(' not in z23                                         # 3 / 7: no assembly
assert 'COBOL(PACFSIO)' not in z23 and 'OBJ(PACFSIO),DISP' not in z23                   # 7: PACFSIO not rebuilt
assert sorted(re.findall(r'INCLUDE OBJ\((\w+)\)', st23['LINK'])) == sorted(ZT23.Z6BLD_UNITS + ZT23.Z6BLD_REUSED)
assert ZT23.Z6BLD_REUSED == ['PACMAP', 'PACAI', 'PACQRY', 'PACTSO', 'PACFSIO', 'PACHSIO']  # 6: reused objects
assert re.findall(r'NAME (\w+)\(R\)', z23) == ['PACZ6D'] and 'PACZ2D' not in z23 and 'LOAD(PACMAIN)' not in z23  # 5
assert "PARM='LIST,AMODE=24,RMODE=24,RENT'" in st23['LINK']
old23 = ZT23.steps_of_deck(ZT23.deck('Z2BLD', '@@HLQ@@.PACMAN'))                        # only the override differs
for s in cob23:
    assert st23[s].replace('CYL,(1,1)', 'TRK,(5,5)') == old23[s], s
assert st23['LINK'] == old23['LINK'].replace('NAME PACZ2D(R)', 'NAME PACZ6D(R)')
assert audit_deck(render(z23, 'Z00000'), 'Z00000') == []
print('PACZ6BLD: default compiler work files TRK,(5,5) unchanged (existing decks byte-identical), override CYL,(1,1) '
      'on SYSUT1-15 + SYSMDECK of the 7 PACREQ compiles only, no assembly, 13 INCLUDEs (6 reused, PACFSIO not rebuilt), '
      'NAME PACZ6D(R), audit clean: PASS')

# 24. ZOS-7 ARCADE (docs/zos7-design.md, decisions D1-D5 2026-10-19; local only: nothing built, uploaded or run).
#     Validation only: no source change; the ZOS-6 acceptance tools stay frozen; the live cases L1 (TURN) / L2 / L3
#     (REALTIME NORMAL / FAST) and the dry runs PACZ7DR1 / PACZ7DR2 on PACZ6D.
import subprocess as SP24  # noqa: E402
import zos7_scen as SC24  # noqa: E402
import zos7_drive as DV24  # noqa: E402
import zos7_live_check as Z724  # noqa: E402
import zos7_fixture as F724  # noqa: E402
import zos7_dry as DR24  # noqa: E402
import ref_hs as HS24  # noqa: E402
# --- frozen: no production source, CLIST or ZOS-6 / ZOS-5 acceptance tool differs from the zos-6 tag
for p24 in ['src', 'jcl/zos/PACZ6BLD.jcl', 'tools/zowe/zos6_live_check.py', 'tools/zowe/zos6_drive.py',
            'tools/zowe/zos6_dry.py', 'tests/zos6_fixture.py', 'tools/zowe/zos5_live_check.py']:
    r24 = SP24.run(['git', 'diff', '--quiet', 'zos-6', '--', p24], cwd=R)
    assert r24.returncode == 0, f'{p24} differs from zos-6'
# --- the plans (D3 / D4): ARCADE, LEVEL >= 2, SOUND(NO), PRESENT(COALESCED) explicit, never PACMAIN's EVERY default
for c24, pl in DV24.PLANS.items():
    w = pl['kw'].split()
    assert {'SOUND(NO)', 'PRESENT(COALESCED)', 'AI(0)'} <= set(w) and not any(x.startswith('RULES(') for x in w), c24
    lv = int(next(x for x in w if x.startswith('LEVEL('))[6:-1])
    assert lv >= 2 and lv == pl['start'], c24
    assert len(DV24.command(c24, 'Z00000.PACMAN')) <= 113, c24                  # <= R2's EXEC, proven live
assert 'RULES(ARCADE)' in (R / 'src/zos/PACMAN.clist').read_text().split('/*')[0]     # ARCADE = the CLIST default
assert [a for c, a in DV24.PLANS['L1']['steps'] if c == 'gameplay'] == SC24.liveb()[1:] and \
    DV24.PLANS['L1']['kw'].split()[2:5] == ['PLAY(TURN)', 'ANIM(NO)', 'SOUND(NO)']
for c24, T24 in (('L2', 150), ('L3', 125)):
    pl = DV24.PLANS[c24]
    assert pl['T'] == T24 and ('SPEED(FAST)' in pl['kw']) == (T24 == 125)
    assert [(k, v) for k, v in pl['steps'] if k in ('wait', 'gameplay')] == \
        [x for k, s in SC24.KEYS for x in (('wait', s), ('gameplay', k))]
    assert 'Q' not in [a for c, a in pl['steps'] if c == 'gameplay']                 # the game ends LOST
# --- the scenario: canonical outcome and the landing-shift proof (3^7 combinations per speed)
for T24 in (150, 125):
    assert SC24.intended(SC24.run(T24)) and SC24.prove(T24)[1] == []
    assert SC24.gaps(T24)[3] >= 200 + 2 * max(SC24.SHIFTS)                          # the principal segment (frozen gate)
# --- the high-score boundary (D3): LEVEL >= 2 never saves; the end lines for an absent / a present HISCORE
assert Z724.hs_lines('ABSENT', ['LOST', 'T', 'SCORE 0000510', 'L', 'Q', 'G', 'F', 'LEVEL 002'], 2) == \
    ['HIGH SCORE 0000510 LEVEL 002', 'START LEVEL 02: HIGH SCORE NOT RECORDED']
rec24 = HS24.record(20000, 5)
assert Z724.hs_lines(rec24, ['QUIT', 'T', 'SCORE 0010780', 'L', 'G', 'F', 'LEVEL 013'], 13) == \
    ['HIGH SCORE 0020000 LEVEL 005']
pds24 = HS24.Pds()
HS24.end_lines(pds24, ('M', 'HISCORE'), 99999, 9, 2)
assert pds24.members == {}                                                          # nothing written at LEVEL 2
src24 = (R / 'src/cobol/PACPLAT.cob').read_text()
assert re.search(r"MOVE 'P' TO REQ-HSNEW\.\n\s+IF REQ-HSELIG NOT = 'Y'\n\s+GO TO DO-HSWR-EXIT\.", src24) and \
    src24.index("IF REQ-HSELIG NOT = 'Y'") < src24.index("CALL 'PACHSIO' USING HS-OP HS-RC HS-DDN HS-REC.\n           MOVE 'F'")
# --- the checker: classification units (D1 is narrow)
assert Z724.classify(['N', 'Q', 'Q', 'Q', 'Q', 'E'], [None, 1, 3, None, None, None], 'LOST')[1:] == ([3, 4], 5)
for k24, q24, end24 in ((['N', 'Q', 'Q', 'E'], [None, 1, None, None], 'QUIT'),          # final death only if LOST
                        (['N', 'Q', 'Q', 'Q', 'E'], [None, None, 3, None, None], 'LOST'),  # not after the gameplay
                        (['N', 'Q', 'Q', 'E', 'Q'], [None, 1, None, None, None], 'LOST'),  # not before the end screen
                        (['N', 'Q', 'E', 'E'], [None, 1, None, None], 'QUIT')):          # one end screen
    try:
        Z724.classify(k24, q24, end24)
        raise AssertionError((k24, q24, end24))
    except Z724.Fail:
        pass
assert Z724.FINAL_DEATH == {150: 6, 125: 7}


def run24(case, hiscore='ABSENT', check_hs=None, **kw):
    t, lg = F724.build(case, hiscore=hiscore, **kw)
    try:
        return Z724.check(t, lg, case, check_hs or hiscore)
    except Z724.Fail as ex:
        return str(ex)


# --- positives: L1 / L2 / L3 PASS on the synthetic traces
r24 = {c: run24(c) for c in ('L1', 'L2', 'L3')}
assert all(isinstance(v, dict) and v['state'] == 'PASS' for v in r24.values()), r24
assert r24['L1']['writes'] == 78 and r24['L1']['coverage']['actual'] == Z724.EXPECT_L1
assert r24['L1']['end_lines'][-2:] == ['HIGH SCORE 0010780 LEVEL 013', 'START LEVEL 13: HIGH SCORE NOT RECORDED']
for c24, T24 in (('L2', 150), ('L3', 125)):
    v = r24[c24]
    assert len(v['final_death_writes']) == Z724.FINAL_DEATH[T24] and v['death_runs'] == [ref_rt.quanta(10, T24)] * 2
    assert v['final_death_timing']['gaps'] == [T24] * (Z724.FINAL_DEATH[T24] - 1)
    assert v['end_screen'] == v['writes'] - 1 and v['coverage']['ok'] and v['principal']['quanta'] >= 200
    assert v['end_lines'][-2:] == ['HIGH SCORE 0000510 LEVEL 002', 'START LEVEL 02: HIGH SCORE NOT RECORDED']
    assert {x - y for x, y in zip(v['frame_quanta'][1:], v['frame_quanta'])} == {Z724.Z6.STRIDE[T24]}  # no pause
# a present high-score record (R): read, shown, not beaten, nothing saved
v24 = run24('L1', hiscore=rec24)
assert v24['state'] == 'PASS' and v24['end_lines'][-1] == 'HIGH SCORE 0020000 LEVEL 005'
# --- negatives: every class fails closed (FUNCTIONAL FAIL), coverage / timing are never PASS
neg24 = {'L2 mutated write': dict(mutate=40), 'L2 dropped write': dict(drop_write=40),
         'L2 non-slot write': dict(nonslot=40), 'L2 replayed write': dict(replay=40),
         'L2 final-death write duplicated': dict(fd_dup=0), 'L2 final-death write dropped': dict(fd_drop=2),
         'L2 final-death frame inside the game': dict(fd_mid=True), 'L3 final-death write duplicated': dict(fd_dup=3),
         'L2 high-score line missing': dict(end_lines=None), 'L2 F1 C3 unrelated': dict(tso_c3='unrelated'),
         'L2 F1 C3 duplicated': dict(tso_c3='dup'), 'L2 gameplay AID lost': dict(lose=1),
         'L2 host freeze 11': dict(frt=11), 'L2 EXEC without PRESENT(COALESCED)':
         dict(kw=DV24.KW_RT.replace(' PRESENT(COALESCED)', '')), 'L1 mutated write': dict(mutate=30),
         'L1 dropped write': dict(drop_write=30), 'L1 F1 C3 duplicated': dict(tso_c3='dup')}
for why, kw in neg24.items():
    c24 = why[:2]
    if why == 'L2 high-score line missing':
        out24 = r24['L2']['end_lines'][:-1]
        kw = dict(end_lines=out24)
    res = run24(c24, **kw)
    assert isinstance(res, str), (why, res if isinstance(res, str) else res['state'])
assert isinstance(run24('L2', check_hs=rec24), str)                                  # the wrong DATA state
# --- the narrow F1 C3 CONTROL rule is unchanged: after the start AID (blocking read) = counted, PASS
for c24 in ('L2', 'L1'):
    v = run24(c24, tso_c3='blocking')
    assert v['state'] == 'PASS' and len(v['tso_controls']) == 1, c24
# --- coverage and timing are never PASS. Every landing shift that still ends the game LOST gives the intended outcome
#     (the proof above; a late key leaves the game running: no closure = FAIL), so the state is tested by requiring an
#     outcome the trace does not show; and a slow host (the frozen gates)
sv24 = dict(SC24.EXPECT)
try:
    SC24.EXPECT['ghosts'] = 2
    v = run24('L2')
    assert v['state'] == Z724.INCOMPLETE and not v['coverage']['ok'], v['state']
finally:
    SC24.EXPECT.clear()
    SC24.EXPECT.update(sv24)
v = run24('L2', scale=1.2)
assert isinstance(v, str) or v['state'] != 'PASS'
# --- the driver on the fake x3270if of section 20 (the frozen ZOS-6 Driver, the ZOS-7 plans): every planned action
#     sent and logged ok, the EXEC typed with PRESENT(COALESCED), TURN commands typed + ENTER, the plan's waits; no
#     shell = nothing sent; a failing action = STOP
def drive24(fake, case):
    real_run, real_sleep, slept = REAL_RUN6, DV24.time.sleep, []
    DV24.Z6D.subprocess.run, DV24.time.sleep = fake, slept.append
    log = IO6.StringIO()
    try:
        DV24.run(case, 4005, log, 'Z00000.PACMAN')
        return 'ok', log.getvalue().splitlines(), slept
    except DV24.Z6D.Stop as ex:
        return f'STOP: {ex}', log.getvalue().splitlines(), slept
    finally:
        DV24.Z6D.subprocess.run, DV24.time.sleep = real_run, real_sleep


for c24 in ('L1', 'L2', 'L3'):
    fk = FakeX(SEQ6)
    res, lines, slept = drive24(fk, c24)
    assert res == 'ok' and [(json.loads(x)['category'], json.loads(x)['action']) for x in lines] == DV24.planned(c24)
    assert fk.calls[2] == f'String("{DV24.command(c24, "Z00000.PACMAN")}")' and 'PRESENT(COALESCED)' in fk.calls[2]
    assert slept == [s for k, s in DV24.PLANS[c24]['steps'] if k == 'wait']
    if c24 == 'L1':
        assert fk.calls.count('String("U")') == 16 and fk.calls.count('String("Q")') == 1 and slept == []
    else:
        assert [c for c in fk.calls if c.startswith('PF(')] == [f'PF({k[2:]})' for k, _ in SC24.KEYS]
res, lines, _ = drive24(FakeX([SCREEN6.replace('ISPF Command Shell', 'ISPF Primary Option Menu')]), 'L2')
assert res.startswith('STOP') and lines == []
res, lines, _ = drive24(FakeX(SEQ6, fail='PF(11)'), 'L3')
assert res.startswith('STOP') and json.loads(lines[-1])['action'] == 'PF11' and 'error' in json.loads(lines[-1])['result']
# --- the dry runs: comparator self-test (oracle 311 G3R7, D1 faults, coverage at both speeds), decks of record
ok24, res24, det24 = DR24.selftest()
assert ok24 and all(det24.values()), [k for k, v in res24.items() if not v]
for n24 in (1, 2):
    d24 = DR24.deck(n24)
    assert d24 == (R / f'jcl/zos/PACZ7DR{n24}.jcl').read_text()
    assert audit_deck(render(d24, 'Z00000'), 'Z00000') == []
    assert re.findall(r'^//(\w+)\s+EXEC PGM=(\w+)', d24, re.M) == [(s, 'PACZ6D') for s in DR24.JOBS[n24]]
    assert DR24.estimate(n24) < 3500
print('ZOS-7 ARCADE (local): src / CLIST / ZOS-6 tools = zos-6; plans ARCADE LEVEL >= 2 SOUND(NO) PRESENT(COALESCED); '
      'L2 / L3 wall-stop scenario LOST / 510 / 1 ghost in 2187 x 2 landing shifts; HS read-only (LEVEL >= 2 never '
      'saves); checker L1 / L2 / L3 PASS (final death 6 / 7 writes, D1 narrow), '
      f'{len(neg24) + 1} negatives FAIL, F1 C3 rule unchanged, coverage / timing never PASS; driver on the fake x3270if; '
      'PACZ7DR1 / DR2 decks of '
      'record, comparator self-test PASS: PASS')


# 25. ZOS-8 Services (docs/zos8-design.md, decisions U1-U12 2026-10-20; Stage A local only: nothing allocated,
#     uploaded, built, submitted or run; no production source change). PACHSIO / PACFSIO / production CLIST frozen;
#     the ZOS-7 tools frozen (U9) and imported; B1 PACZ8HB / B2 PACZ8RPE decks of record; test CLISTs (U3); the z/OS
#     RPESTAE test CLIST (U4); live plans / checker for Stage C (HL), D (E1-E3 + GD), E (S8A / S8B / S8C).
import subprocess as SP25  # noqa: E402
import zos8_scen as S25  # noqa: E402
import zos8_drive as DV25  # noqa: E402
import zos8_live_check as Z825  # noqa: E402
import zos8_batch as B25  # noqa: E402
import zos8_fixture as F825  # noqa: E402
import zos7_fixture as F725  # noqa: E402
import zos_hs_model as HM25  # noqa: E402
# --- frozen: production source, CLIST, PACHSIO / PACFSIO, the ZOS-5 / 6 / 7 acceptance tools = zos-7; the only new
#     file under src/ is the test CLIST src/probe/zos/RPESTAE.clist
FROZEN25 = ['src/cobol', 'src/copy', 'src/asm', 'src/clist', 'src/zos', 'jcl/zos/PACZ6BLD.jcl', 'jcl/zos/PACZ7DR1.jcl',
            'jcl/zos/PACZ7DR2.jcl', 'tools/zowe/zos7_scen.py', 'tools/zowe/zos7_drive.py',
            'tools/zowe/zos7_live_check.py', 'tools/zowe/zos7_dry.py', 'tests/zos7_fixture.py',
            'tools/zowe/zos6_live_check.py', 'tools/zowe/zos6_drive.py', 'tools/zowe/zos6_dry.py',
            'tests/zos6_fixture.py', 'tools/zowe/zos5_live_check.py', 'tools/zowe/zos_target.py', 'tools/make_deck.py']
for p25 in FROZEN25:
    assert SP25.run(['git', 'diff', '--quiet', 'zos-7', '--', p25], cwd=R).returncode == 0, f'{p25} differs from zos-7'
    assert not SP25.run(['git', 'ls-files', '--others', '--exclude-standard', '--', p25], cwd=R,
                        capture_output=True, text=True).stdout.strip(), f'{p25}: untracked file'
new25 = set(SP25.run(['git', 'diff', '--name-only', 'zos-7', '--', 'src'], cwd=R, capture_output=True,
                     text=True).stdout.split()) | set(SP25.run(['git', 'ls-files', '--others', '--exclude-standard',
                                                                '--', 'src'], cwd=R, capture_output=True,
                                                               text=True).stdout.split())
assert new25 <= {'src/probe/zos/RPESTAE.clist'}, new25
# --- the scenario: card files = the commands each model game consumes; the Stage C state chain (ref_hs)
for n25 in S25.GAMES:
    assert S25.live_cards(n25) == S25.consumed(n25), n25
    assert S25.live_cards(n25)[-1] in ('Q', 'U', 'D', 'L', 'R') and 'EOF' not in S25.end_lines(n25, S25.live_cards(n25))
chain25 = S25.hl_chain()
assert [(c, b, h[-1], a) for c, _, b, h, a in chain25] == [
    ('HL1', '0000720 PACHS001 001', 'START LEVEL 05: HIGH SCORE NOT RECORDED', '0000720 PACHS001 001'),
    ('HL2', '0000720 PACHS001 001', 'NEW HIGH SCORE', '0000980 PACHS001 001'),
    ('HL3', '0000980 PACHS001 001', 'HIGH SCORE 0000980 LEVEL 001', '0000980 PACHS001 001'),
    ('HL4', '0000980 PACHS001 001', 'NEW HIGH SCORE', '0001310 PACHS001 001'),
    ('HL6', 'n/a', 'HIGH SCORE UNAVAILABLE', 'n/a'), ('HL8', 'ABSENT', 'HIGH SCORE NOT SAVED', 'ABSENT')]
# B1: the batch model = the frozen oracle 312 for the GPREVB game (HA2 base output); create / tie / update / lower
base25 = HM25.expected_text('HA2')
assert base25[:len(base25) - 1] == [l.rstrip() for l in GP2.simulate(S25.cards_of('gpcases', 'GPREVB'), start=1)]
assert [x[1][-1] for x in S25.b1_model()] == ['NEW HIGH SCORE', 'HIGH SCORE 0000370 LEVEL 001', 'NEW HIGH SCORE',
                                               'HIGH SCORE 0000720 LEVEL 001']
# --- the plans: every live EXEC <= 113 characters (proven live), PRESENT(COALESCED) explicit, Stage C / D silent,
#     Stage E sound; HL on the test CLISTs only; S8A / S8B = the ZOS-7 L2 / L3 gameplay with SOUND(YES), LEVEL 2
for c25, p25 in DV25.PLANS.items():
    acts = [a for k, a in p25['steps'] if k == 'transition' and a.startswith('EXEC')]
    for a in acts:
        cmd = DV25.command(c25, a, 'Z00000.PACMAN')
        assert len(cmd) <= S25.EXEC_MAX and 'PACMAN.DATA' not in cmd, (c25, cmd)
    if p25['kind'] != 'ESTAE':
        w = p25['kw'].split()
        assert 'PRESENT(COALESCED)' in w and ('SOUND(YES)' in w) == c25.startswith('S8'), c25
for c25 in S25.HL_ORDER:
    assert DV25.PLANS[c25]['clist'] in S25.TEST_CLISTS and 'ANIM(NO)' in DV25.PLANS[c25]['kw'], c25
for c25, l25 in (('S8A', 'L2'), ('S8B', 'L3')):
    assert DV25.PLANS[c25]['steps'] == DV24.PLANS[l25]['steps'][:-3] + DV25.TAIL[:1] + DV24.PLANS[l25]['steps'][-2:]
    assert DV25.PLANS[c25]['kw'] == DV24.PLANS[l25]['kw'].replace('SOUND(NO)', 'SOUND(YES)')
assert 'RULES(CLASSIC)' in DV25.PLANS['S8C']['kw'] and 'RULES(CLASSIC)' in S25.kw_of('GD')
# --- batch: decks of record, audits, B1 geometry = DATA (PACZALLO), test CLISTs = installed CLIST but the DATA lines,
#     the z/OS RPESTAE (Z2 core verbatim, E2 on HS8.T1), estimates
ok25, res25 = B25.selftest()
assert ok25, [k for k, v in res25.items() if not v]
for k25, f25 in (('B1', B25.b1_deck), ('B2', B25.b2_deck)):
    assert audit_deck(render(f25(), 'Z00000'), 'Z00000') == [] and B25.audit(f25(), k25) == []
alloc25 = (R / 'jcl/zos/PACZALLO.jcl').read_text()
assert all(x in alloc25 for x in B25.DATA_DD) and alloc25.count('SPACE=(TRK,(1,1,5))') == 1
assert re.findall(r'EXEC PGM=(\w+)', B25.b2_deck())[2:] == ['PACRPE', 'PACRPE'] and 'NAME PACRPE(R)' in B25.b2_deck()
# --- batch checkers on synthetic spools: PASS, and every injected fault fails closed
for k25 in ('B1', 'B2'):
    r25, _ = F825.spool_check(k25)
    assert all(v for _, v in r25), (k25, [x for x, v in r25 if not v])
for k25, f25 in (('B1', 'H2 rc'), ('B1', 'H3 line'), ('B1', 'print'), ('B1', 'members'), ('B1', 'data'),
                 ('B1', 'iec'), ('B2', 'COB rc'), ('B2', 'E1 noabend'), ('B2', 'E2 lines'), ('B2', 'rmode'),
                 ('B2', 'data')):
    r25, _ = F825.spool_check(k25, (f25,))
    assert not all(v for _, v in r25), (k25, f25)


# --- live checker: positives
def run25(case, before=None, **kw):
    t, lg = F825.build(case, before=before, **kw)
    chain = {c: b for c, _, b, _, _ in S25.hl_chain()}
    try:
        return Z825.check(t, lg, case, before or chain.get(case, 'ABSENT'))
    except Z825.Fail as ex:
        return str(ex)


pos25 = {c: run25(c) for c in DV25.PLANS}
assert all(isinstance(v, dict) and v['state'] == 'PASS' for v in pos25.values()), \
    {c: (v if isinstance(v, str) else v['state']) for c, v in pos25.items()}
assert pos25['HL8']['end_lines'][-1] == 'HIGH SCORE NOT SAVED' and pos25['HL6']['end_lines'][-1] == \
    'HIGH SCORE UNAVAILABLE'
assert pos25['S8C']['bells'] == [['START', 1], ['WIN', 4]] and pos25['S8C']['bell_gaps'][1:] == [300, 300, 300]
assert pos25['S8A']['pattern_step_gaps'] == [[300], [300], [300, 300]] and \
    pos25['S8B']['pattern_step_gaps'] == [[375], [375], [375, 375]]
assert all(pos25[e]['abend_code'] == '0C7' and pos25[e]['followup']['end_lines'][0] == 'QUIT' for e in ('E1', 'E2',
                                                                                                        'E3'))
for v25 in ('hold', 'tail'):                                    # HL8: the IEC217I B14 message, with or without a hold
    r25 = run25('HL8', iec=v25)
    assert isinstance(r25, dict) and r25['state'] == 'PASS' and len(r25['iec']) == 1 and r25['hold'] == (v25 == 'hold')
r25 = run25('E1', leftover=False)                               # the CLIST freed CEEOPTS itself: no FREE
assert r25['state'] == 'PASS' and not r25['ceeopts_left'] and r25['cleanup'] == []
assert run25('E2', recovery=2)['recovery_enters'] == 2
# --- live checker: negatives fail closed
neg25 = {'HL2 mutated write': ('HL2', dict(mutate=20)), 'HL4 dropped write': ('HL4', dict(drop_write=10)),
         'HL2 NEW line missing': ('HL2', dict(end_lines=S25.end_lines('HL2', S25.live_cards('HL2')) +
                                               ['HIGH SCORE 0000980 LEVEL 001'])),
         'HL3 wrong store state': ('HL3', dict(before='0000720 PACHS001 001')),
         'HL2 the installed CLIST instead of PACZ8HT': ('HL2', dict(member='PACMAN')),
         'HL2 an IEC message': ('HL2', dict(iec='hold')), 'HL8 another IEC message': ('HL8', dict(iec='bad')),
         'HL8 NOT SAVED missing': ('HL8', dict(end_lines=S25.end_lines('HL8', S25.live_cards('HL8')) +
                                               ['HIGH SCORE 0000510 LEVEL 001', 'NEW HIGH SCORE'])),
         'HL6 UNAVAILABLE missing': ('HL6', dict(end_lines=S25.end_lines('HL6', S25.live_cards('HL6')))),
         'S8C bell-only write dropped': ('S8C', dict(drop_write=186)),
         'S8C first write mutated': ('S8C', dict(mutate=0)),
         'S8A mutated write': ('S8A', dict(mutate=40)), 'S8B dropped write': ('S8B', dict(drop_write=30)),
         'S8A EXEC with SOUND(NO)': ('S8A', dict(kw=DV24.KW_RT)),
         'E1 no abend': ('E1', dict(no_abend=True)), 'E1 test screen again': ('E1', dict(rescreen=True)),
         'E3 line after the abend': ('E3', dict(e3_late=True)), 'E2 typed input in the recovery': ('E2',
                                                                                              dict(extra_input=True)),
         'E1 CEEOPTS left, not freed': ('E1', dict(no_free=True)),
         'E2 FREE without a leftover': ('E2', dict(leftover=False, free_anyway=True)),
         'E3 follow-up game differs': ('E3', dict(gd=dict(mutate=5)))}
for why, (c25, kw25) in neg25.items():
    r25 = run25(c25, **kw25)
    assert isinstance(r25, str), (why, r25 if isinstance(r25, str) else r25['state'])
# --- the end-screen NEW HIGH SCORE label follows the persistence outcome (HL8 live, 2026-10-20: PACSCR shows it only
#     when REQ-HSNEW = 'Y'; ref_rp.Tracker, unchanged, shows it whenever the score beats the record). The correction
#     changes no frame of a saved / practice / unavailable game and, for the failed save, only the end screen and only
#     by the label; both wrong pairings and any other screen difference fail
chain25b = {c: b for c, _, b, _, _ in S25.hl_chain()}
for c25 in S25.HL_ORDER:
    hs25 = S25.hs_tuple(c25, chain25b[c25])
    sv25b = Z825.saved_of(Z825.expected_lines(c25, chain25b[c25])[1])
    a25 = Z825.turn_model(c25, hs25, False)['frames']
    b25 = Z825.turn_model(c25, hs25, False, saved=sv25b)['frames']
    d25 = [i for i, (x, y) in enumerate(zip(a25, b25)) if x != y]
    assert len(a25) == len(b25) and sv25b == (c25 in ('HL2', 'HL4')), c25
    if c25 == 'HL8':
        assert d25 == [len(a25) - 1], d25
        ta25, tb25 = (Z5.texts(bytes([0x7E]) + f[-1]) for f in (a25, b25))
        from collections import Counter as C25
        assert C25(ta25) - C25(tb25) == C25(['NEW', 'HIGH', 'SCORE']) and not C25(tb25) - C25(ta25), (ta25, tb25)
    else:
        assert d25 == [], (c25, d25)
neg25b = {'HL8 unsaved score with the NEW HIGH SCORE label': ('HL8', dict(end_label='saved')),
          'HL2 saved new high score without the label': ('HL2', dict(end_label='unsaved')),
          'HL4 saved new high score without the label': ('HL4', dict(end_label='unsaved')),
          'HL8 end screen otherwise changed': ('HL8', dict(mutate=29)),
          'HL8 game screen changed': ('HL8', dict(mutate=12))}
for why, (c25, kw25) in neg25b.items():
    r25 = run25(c25, **kw25)
    assert isinstance(r25, str) and 'differs from the TURN model' in r25, (why, r25)
sv25 = list(S25.S8_BELLS['S8C'])
try:                                                            # coverage is never PASS when the bells differ
    S25.S8_BELLS['S8C'] = [['START', 1], ['WIN', 3]]
    assert run25('S8C')['state'] == Z825.INCOMPLETE
finally:
    S25.S8_BELLS['S8C'] = sv25


# --- the driver on the fake x3270if of section 20: every planned action sent and logged ok; the conditional ones
def drive25(fake, case, done=None):
    real_run, real_sleep = REAL_RUN6, DV25.time.sleep
    DV25.Z6D.subprocess.run, DV25.time.sleep = fake, lambda s: None
    log = IO6.StringIO()
    try:
        DV25.run(case, 4005, log, 'Z00000.PACMAN', done)
        return 'ok', [json.loads(x) for x in log.getvalue().splitlines()]
    except DV25.Z6D.Stop as ex:
        return f'STOP: {ex}', [json.loads(x) for x in log.getvalue().splitlines()]
    finally:
        DV25.Z6D.subprocess.run, DV25.time.sleep = real_run, real_sleep


for c25 in ('HL1', 'HL4', 'S8A', 'S8C'):
    fk = FakeX(SEQ6)
    res, lines = drive25(fk, c25)
    assert res == 'ok' and [(x['category'], x['action']) for x in lines] == DV25.planned(c25), (c25, res)
    assert fk.calls[2] == f'String("{DV25.command(c25, "EXEC", "Z00000.PACMAN")}")'
IEC25 = SCREEN6.replace('ISPF Command Shell', 'IEC217I B14-0C,IGG0201Z,Z00000 ***')
res, lines = drive25(FakeX([SCREEN6, GAME6, GAME6, IEC25, GAME6, SCREEN6]), 'HL8')
assert res == 'ok' and [(x['category'], x['action']) for x in lines] == \
    DV25.planned('HL8')[:-1] + [('hold', 'ENTER'), ('closure', 'ENTER')]
res, lines = drive25(FakeX([SCREEN6, GAME6, GAME6, IEC25, GAME6, SCREEN6]), 'HL2')
assert res.startswith('STOP') and 'IEC' in res                     # an IEC message outside HL8 stops the case
res, lines = drive25(FakeX([SCREEN6, GAME6, GAME6, IEC25.replace('IEC217I B14-0C', 'IEC020I 001-4'), SCREEN6]),
                     'HL8')
assert res.startswith('STOP')
def tscreen25(rows, w, pos, lines=None):
    """A test screen as Ascii() returns it: rows x w, every row padded to w, the lines written into the buffer at
    (row, column) - a line longer than the rest of its row continues on the next row, as on the 3270."""
    buf = [' '] * (rows * w)
    for (r, c), line in zip(pos, lines or DV25.test_screen('E1')):
        buf[r * w + c:r * w + c + len(line)] = line
    b = ''.join(buf)
    return ''.join(b[i:i + w] + '\n' for i in range(0, rows * w, w))


# the two real E1 test screens, rebuilt from their line positions = the preserved Ascii() files byte for byte:
# E1 2026-10-20 (24 x 80, unwrapped; ~/zos8-live/stageD/zos8-E1-resume-final-screen.txt) and E1-T2 (27 x 120: the
# first line at column 81, the E3 line at row 5 column 81 wrapping onto row 6; stageD-E1-T2/zos8-E1-T2-final-screen)
POS80, POS120 = [(1, 1), (3, 1), (5, 1), (6, 1), (7, 1)], [(0, 81), (2, 1), (3, 41), (4, 1), (4, 81)]
ESTAE25 = tscreen25(24, 80, POS80)
WRAP25 = tscreen25(27, 120, POS120)
assert hashlib.sha256(ESTAE25.encode()).hexdigest() == \
    'cde67794a40071e8d461637881a6a2f3dedc90f9a9153e6909db04b990868fe5'
assert hashlib.sha256(WRAP25.encode()).hexdigest() == \
    '2634a8ff1f63bd66b765bab27d1bb9f2a3a454591dbedc394668fc9dd99513bc'
ABEND25 = SCREEN6.replace('ISPF Command Shell', 'CEE3207S ABEND 0C7 ENDED DUE TO ERROR ***')
HOLD25 = SCREEN6.replace(' ===>', f" ===> {DV25.command('E1', 'EXEC', 'Z00000.PACMAN')}") + ' ***\n'


def held25(text):                                       # the ISPF initial hold of a shell command (live 2026-10-20)
    return SCREEN6.replace(' ===>', f' ===> {text}') + ' ***\n'


def page25(lines):                                      # a line-mode output page (no shell panel), ending with ***
    return ' ' + '\n '.join(lines) + '\n ***\n'


def pages25(leftover=True, size=12):
    ls = F825.listalc_lines('Z00000.PACMAN', leftover)
    return [page25(ls[i:i + size]) for i in range(0, len(ls), size)]


def tail25(freed, pages=None):                          # the Ascii() answers after the recovery's return to the shell
    pg = pages25(freed) if pages is None else pages
    return ([SCREEN6, held25('LISTALC STATUS')] + pg + [SCREEN6] +
            ([SCREEN6, held25('FREE F(CEEOPTS)'), SCREEN6] if freed else []) + [GAME6, GAME6, GAME6, SCREEN6])


for freed in (True, False):
    fk = FakeX([SCREEN6, HOLD25, ESTAE25, ABEND25, SCREEN6] + tail25(freed))
    res, lines = drive25(fk, 'E1')
    acts25 = [(x['category'], x['action']) for x in lines]
    assert res == 'ok' and acts25[:5] == [('transition', 'EXEC'), ('transition', 'ENTER'), ('abend', 'ENTER'),
                                          ('recovery', 'ENTER'), ('check', 'LISTALC')], (res, acts25[:6])
    assert (('cleanup', 'FREE') in acts25) == freed and acts25[-1] == ('closure', 'ENTER')
    assert ('String("FREE F(CEEOPTS)")' in fk.calls) == freed and \
        f'String("{DV25.command("E1", "EXEC:GD", "Z00000.PACMAN")}")' in fk.calls
    assert acts25.count(('check', 'ENTER')) == 1 + len(pages25(freed)) and \
        [a for a in acts25 if a[0] == 'cleanup'] == ([('cleanup', 'FREE'), ('cleanup', 'ENTER')] if freed else [])
sv25 = DV25.RECOVER_TIMEOUT
try:                                                            # the exit never restored line mode: STOP, nothing more
    DV25.RECOVER_TIMEOUT = 0.5
    res, lines = drive25(FakeX([SCREEN6, HOLD25, ESTAE25]), 'E1')
    assert res.startswith('STOP') and [x['category'] for x in lines] == ['transition', 'transition', 'abend']
finally:
    DV25.RECOVER_TIMEOUT = sv25
# --- the EXEC's initial ISPF `***` hold (E1 2026-10-20: every EXEC from the shell is held; the first E plans waited
#     for the test screen at once): the plans, the checker (exactly EXEC -> one *** -> one ENTER -> the screen)
for e25 in ('E1', 'E2', 'E3'):
    assert DV25.PLANS[e25]['steps'][:4] == [('transition', 'EXEC'), ('expect', '***'), ('transition', 'ENTER'),
                                            ('expect', 'ESTAE')]
for h25, why25 in (('missing', 'driver log'), ('dup', 'not exactly one ENTER'), ('order', 'not held by exactly one')):
    r25 = run25('E1', hold=h25)
    assert isinstance(r25, str) and why25 in r25, (h25, r25)
# --- a resumed case: its two trace segments joined losslessly (SEQ-NUMBERs continue, segment 1 ends with the hold,
#     segment 2 starts with its ENTER); a lost / stray record at the boundary, swapped or missing segments fail
t25, l25 = F825.build('E1')
(a25, b25), la25, lb25 = F825.split_at_hold(t25, l25)
r25 = Z825.check((a25, b25), la25 + lb25, 'E1')
assert r25['state'] == 'PASS' and r25['segments'] == 2 and r25['followup']['end_lines'][0] == 'QUIT'
assert r25['ceeopts_left'] == run25('E1')['ceeopts_left']
for why25, kw25, swap25 in (('lost *** record', dict(drop_last=True), False),
                            ('stray host write', dict(extra_first=True), False), ('swapped', {}, True)):
    (a25, b25), la25, lb25 = F825.split_at_hold(t25, l25, **kw25)
    try:
        Z825.check((b25, a25) if swap25 else (a25, b25), la25 + lb25, 'E1')
        raise AssertionError(why25)
    except Z825.Fail:
        pass
(a25, b25), la25, lb25 = F825.split_at_hold(t25, l25)
for seg25 in (a25, b25):
    try:
        Z825.check(seg25, la25 + lb25, 'E1')
        raise AssertionError('one segment accepted')
    except Z825.Fail:
        pass
# --- the driver resumes only the held EXEC of a Stage D case: nothing resent, ordinals continue the earlier log
done25 = [{'ordinal': 1, 'category': 'transition', 'action': 'EXEC', 'result': 'ok'}]
fk = FakeX([HOLD25, ESTAE25, ABEND25, SCREEN6] + tail25(True))
res, lines = drive25(fk, 'E1', done25)
assert res == 'ok' and lines[0]['ordinal'] == 2 and (lines[0]['category'], lines[0]['action']) == \
    ('transition', 'ENTER') and not any('EXEC' in c and 'RPESTAE' in c for c in fk.calls)
assert [(x['category'], x['action']) for x in lines][-1] == ('closure', 'ENTER')
for scr25, d25, c25 in ((SCREEN6, done25, 'E1'), (HOLD25, done25 * 2, 'E1'), (HOLD25, done25, 'HL2'),
                        (HOLD25.replace('CASE(E1)', 'CASE(E2)'), done25, 'E1')):
    res, lines = drive25(FakeX([scr25]), c25, d25)
    assert res.startswith('STOP') and lines == [], (c25, res)
# --- the RPESTAE test screen (E1 2026-10-20: its own PRESS ENTER line contains ABEND, which the generic detector
#     took for an error): recognised only complete and exact; the expected ABEND is exempt only as that exact line
assert DV25.Z6D.BAD.search(ESTAE25).group(0) == 'ABEND'          # the original false positive, reproduced
assert DV25.screen_state(ESTAE25, 'E1') == 'screen'
try:                                                            # an altered PRESS ENTER line: its ABEND is an error
    DV25.screen_state(ESTAE25.replace('PRESS ENTER', 'PRESS'), 'E1')
    raise AssertionError('altered PRESS ENTER line accepted')
except DV25.Z6D.Stop:
    pass
assert DV25.screen_state(HOLD25, 'E1') is None and DV25.screen_state(SCREEN6, 'E1') is None   # not (yet) the screen
for bad25 in ('CEE3207S DATA EXCEPTION', 'IEA995I ABEND 0C7', 'IKJ56247I'):
    try:
        DV25.screen_state(ESTAE25 + bad25, 'E1')
        raise AssertionError(bad25)
    except DV25.Z6D.Stop:
        pass
res, lines = drive25(FakeX([SCREEN6, HOLD25, ESTAE25.replace('PRESS ENTER', 'PRESS') + 'CEE3207S']), 'E1')
assert res.startswith('STOP') and [x['action'] for x in lines] == ['EXEC', 'ENTER']   # altered screen: no abend ENTER
# --- resume at the displayed test screen: the earlier logs = [EXEC, hold ENTER]; nothing resent; next = abend ENTER
done25b = done25 + [{'ordinal': 2, 'category': 'transition', 'action': 'ENTER', 'result': 'ok'}]
fk = FakeX([ESTAE25, ABEND25, SCREEN6] + tail25(True))
res, lines = drive25(fk, 'E1', done25b)
assert res == 'ok' and lines[0]['ordinal'] == 3 and (lines[0]['category'], lines[0]['action']) == ('abend', 'ENTER')
assert not any('RPESTAE' in c for c in fk.calls) and fk.calls.count('Enter()') >= 1
for scr25, d25 in ((HOLD25, done25b), (ESTAE25.replace('PASS: LINE MODE', 'PASS'), done25b), (ESTAE25, done25),
                   (ESTAE25, [done25b[1], done25b[0]]), (ESTAE25, done25b + done25b[1:])):
    res, lines = drive25(FakeX([scr25]), 'E1', d25)
    assert res.startswith('STOP') and lines == [], res
# --- the three segments of the resumed E1: EXEC -> *** | ENTER -> test screen | abend ENTER -> the rest; joined only
#     losslessly at those two points; missing, repeated, modified, reordered segments and boundary faults fail
segs25, logs25 = F825.split_segments(t25, l25, ('hold', 'screen'))
r25 = Z825.check(tuple(segs25), sum(logs25, []), 'E1')
assert r25['state'] == 'PASS' and r25['segments'] == 3 and r25 == {**r25, 'segments': 3}
mod25 = segs25[1].replace('d7c1c3d4c1d540d9d7', 'd7c1c3d4c1d540d9d8', 1)
assert mod25 != segs25[1]
for why25, sg25 in (('missing segment 2', (segs25[0], segs25[2])), ('segment 2 twice', (segs25[0], segs25[1],
                                                                                       segs25[1])),
                    ('four segments', (segs25[0], segs25[1], segs25[1], segs25[2])),
                    ('reordered 1 / 2', (segs25[1], segs25[0], segs25[2])),
                    ('reordered 2 / 3', (segs25[0], segs25[2], segs25[1])),
                    ('modified segment 2', (segs25[0], mod25, segs25[2])),
                    ('cut at the screen only', tuple(F825.split_segments(t25, l25, ('screen',))[0])),
                    ('lost boundary record', tuple(F825.split_segments(t25, l25, ('hold', 'screen'),
                                                                       drop_last=True)[0])),
                    ('stray host write', tuple(F825.split_segments(t25, l25, ('hold', 'screen'),
                                                                   extra_first=True)[0]))):
    try:
        Z825.check(sg25, sum(logs25, []), 'E1')
        raise AssertionError(why25)
    except Z825.Fail:
        pass
for scr25 in (DV25.test_screen('E1')[:4], DV25.test_screen('E1') + ['CEE3207S X'], DV25.test_screen('E2')):
    assert isinstance(run25('E1', screen=scr25), str), scr25                        # an altered test screen
# --- Stage D LISTALC / FREE as observed live (E1 recovery 2026-10-20: every shell command is held by ISPF first;
#     LISTALC answered the hold + 13 output pages, FREE the hold only; the first E plans expected one *** and looked for
#     CEEOPTS on the hold screen only). The page count is not fixed (bounded by PAGES_MAX); every hold / page is
#     validated before its ENTER; CEEOPTS only by the strict DD rule over all pages
P25 = 'Z00000.PACMAN'
ls25 = F825.listalc_lines(P25)
assert DV25.ceeopts_of(ls25, P25) is True and DV25.ceeopts_of(F825.listalc_lines(P25, False), P25) is False
k25 = ls25.index(f'{P25}.CEEOPTS')
for bad25 in (ls25[:k25 + 1] + ls25[k25 + 2:],                                      # dataset without its DD line
              ls25[:k25] + ['Z00000.OTHER.PARMS'] + ls25[k25 + 1:],                 # the DD on another dataset
              ls25[:k25 + 1] + ['ISPLOG  KEEP'] + ls25[k25 + 2:],                   # the dataset under another DD
              ls25 + [f'{P25}.CEEOPTS', 'CEEOPTS  KEEP'],                           # listed twice
              ls25[:k25] + ['CEEOPTS  KEEP'] + ls25[k25 + 2:]):                     # a DD line without the dataset
    try:
        DV25.ceeopts_of(bad25, P25)
        raise AssertionError(bad25[k25 - 1:k25 + 3])
    except ValueError:
        pass
# checker: page sizes (CEEOPTS pair split across two pages), the live split page record, no leftover
for kw25 in (dict(page=k25 + 1), dict(page=5), dict(page=len(ls25)), dict(pagefault='split'), dict(leftover=False)):
    r25 = run25('E1', **kw25)
    assert isinstance(r25, dict) and r25['state'] == 'PASS' and r25['ceeopts_left'] == kw25.get('leftover', True), \
        (kw25, r25)
    assert r25['listalc_pages'] == -(-len(F825.listalc_lines(P25, kw25.get('leftover', True))) // kw25.get('page', 12))
negp25 = {'no initial hold': dict(pagefault='no_hold'), 'hold with text': dict(pagefault='hold_text'),
          'page missing': dict(pagefault='missing'), 'page ENTER not logged': dict(pagefault='missing_log'),
          'page duplicated': dict(pagefault='dup'), 'pages reordered': dict(pagefault='reorder'),
          'page without ***': dict(pagefault='no_star'), 'text after ***': dict(pagefault='after_star'),
          'two ENTERs on a page': dict(pagefault='two_enters'), 'error text on a page': dict(pagefault='error'),
          'more than PAGES_MAX pages': dict(pagefault='too_many'),
          'no header': dict(listalc=ls25[1:]), 'CEEOPTS ambiguous': dict(listalc=ls25[:k25 + 1] + ls25[k25 + 2:]),
          'FREE with output': dict(free_output=True), 'FREE not held': dict(free_fault='no_hold'),
          'FREE hold answered twice': dict(free_fault='hold_twice'),
          'LISTALC hold answered twice': dict(pagefault='hold_twice')}
for why25, kw25 in negp25.items():
    r25 = run25('E1', **kw25)
    assert isinstance(r25, str), (why25, r25 if isinstance(r25, str) else r25['state'])
# driver: every screen validated before its ENTER; bounded pages and time; nothing sent after a bad screen
sv25 = DV25.PAGE_TIMEOUT, DV25.PAGES_MAX
pre25 = [SCREEN6, HOLD25, ESTAE25, ABEND25, SCREEN6, SCREEN6]
try:
    DV25.PAGE_TIMEOUT = 0.3
    for size25 in (3, 12, 40):                                  # any page count within the bound
        res, lines = drive25(FakeX(pre25[:-1] + tail25(True, pages25(True, size25))), 'E1')
        assert res == 'ok' and [(x['category'], x['action']) for x in lines].count(('check', 'ENTER')) == \
            1 + len(pages25(True, size25)), (size25, res)
    lh25 = held25('LISTALC STATUS')
    pg25 = pages25()
    n25 = len(pg25)
    negd25 = {'no initial hold (a page first)': ([pg25[0]], 0), 'hold of another command': ([held25('LISTALC')], 0),
              'the idle shell, never held': ([SCREEN6], 0),
              'error text on a page': ([lh25, pg25[0], page25(['IKJ56231I DATA SET NOT ALLOCATED'])], 2),
              'a shell screen with *** after the hold': ([lh25, pg25[0], held25('X')], 2),
              'page never changes (timeout)': ([lh25, pg25[0]], 2),
              'no --DDNAME---DISP-- header': ([lh25] + pg25[1:] + [SCREEN6], n25),
              'CEEOPTS ambiguous': ([lh25, page25(ls25[:k25 + 1] + ls25[k25 + 2:]), SCREEN6], 2),
              'FREE with output': ([lh25] + pg25 + [SCREEN6, SCREEN6, held25('FREE F(CEEOPTS)'), page25(['X']),
                                                    SCREEN6], n25 + 1 + 2)}
    for why25, (scr25, ent25) in negd25.items():
        res, lines = drive25(FakeX(pre25 + scr25), 'E1')
        acts25 = [(x['category'], x['action']) for x in lines]
        assert res.startswith('STOP') and ('transition', 'EXEC:GD') not in acts25, (why25, res)
        assert sum(a[1] == 'ENTER' and a[0] in ('check', 'cleanup') for a in acts25) == ent25, (why25, acts25)
    DV25.PAGES_MAX = n25 - 1                                    # one page more than the bound: STOP, no ENTER on it
    res, lines = drive25(FakeX(pre25 + [lh25] + pg25 + [SCREEN6]), 'E1')
    assert res.startswith('STOP') and f'more than {n25 - 1}' in res and \
        [(x['category'], x['action']) for x in lines].count(('check', 'ENTER')) == n25, res
finally:
    DV25.PAGE_TIMEOUT, DV25.PAGES_MAX = sv25
# --- the test screen on a 120-column terminal (E1-T2 2026-10-20: the E3 line wraps at the row end; the first driver
#     matched per row and timed out on the real screen): exact lines in the joined screen buffer, each once, in order,
#     nothing else on the screen; the ABEND exemption only for the exact PRESS ENTER line
assert '(FSOF), THEN 0C7.' not in WRAP25 and DV25.screen_state(WRAP25, 'E1') == 'screen'
assert DV25.screen_state(ESTAE25, 'E1') == 'screen'                                   # unwrapped (80 columns)
L25 = DV25.test_screen('E1')
badscr25 = {'altered character (wrapped line)': WRAP25.replace('(FSOF)', '(FS0F)'),
            'altered character (row 1)': WRAP25.replace('CASE E1', 'CASE E7'),
            'missing line': tscreen25(27, 120, POS120[:4], L25[:4]),
            'duplicated line': tscreen25(27, 120, POS120 + [(8, 1)], L25 + [L25[1]]),
            'reordered lines': tscreen25(27, 120, POS120, [L25[0], L25[2], L25[1], L25[3], L25[4]]),
            'other text on the screen': WRAP25[:-2] + 'X\n',
            'other case': tscreen25(27, 120, POS120, DV25.test_screen('E2')),
            'error text': tscreen25(27, 120, POS120 + [(9, 1)], L25 + ['CEE3207S DATA EXCEPTION']),
            'error text in the wrapped line': WRAP25.replace('\nHEN 0C7.', '\nHENABEND'),
            'IKJ message': tscreen25(27, 120, POS120 + [(20, 1)], L25 + ['IKJ56247I FILE NOT FREED']),
            'altered PRESS ENTER line (its ABEND)': WRAP25.replace('PRESS ENTER:', 'PRESS ENTER;')}
for why25, scr25 in badscr25.items():
    assert scr25 != WRAP25, why25
    try:
        DV25.screen_state(scr25, 'E1')
        raise AssertionError(why25)
    except DV25.Z6D.Stop:
        pass
for why25 in ('altered character (wrapped line)', 'missing line', 'duplicated line', 'reordered lines'):
    try:
        DV25.screen_state(badscr25[why25].replace('PRESS ENTER: THE PROGRAM FORCES A 0C7 ABEND.', ' ' * 44), 'E1')
        raise AssertionError(why25)
    except DV25.Z6D.Stop:
        pass
assert DV25.screen_state(WRAP25.replace('CASE E1', 'CASE E2'), 'E2') == 'screen'
for scr25 in (WRAP25, ESTAE25):                                 # the whole E1 plan on the real screen shapes
    res, lines = drive25(FakeX([SCREEN6, HOLD25, scr25, ABEND25, SCREEN6] + tail25(True)), 'E1')
    assert res == 'ok' and [x['action'] for x in lines][:3] == ['EXEC', 'ENTER', 'ENTER'], res
for scr25 in (badscr25['altered character (wrapped line)'], badscr25['error text']):
    res, lines = drive25(FakeX([SCREEN6, HOLD25, scr25]), 'E1')
    assert res.startswith('STOP') and [x['action'] for x in lines] == ['EXEC', 'ENTER'], res   # no abend ENTER
d2 = [{'ordinal': 1, 'category': 'transition', 'action': 'EXEC', 'result': 'ok'},
      {'ordinal': 2, 'category': 'transition', 'action': 'ENTER', 'result': 'ok'}]
fk = FakeX([WRAP25, ABEND25, SCREEN6] + tail25(True))           # E1-T2 resume: the wrapped screen, then abend
res, lines = drive25(fk, 'E1', d2)
assert res == 'ok' and (lines[0]['ordinal'], lines[0]['category']) == (3, 'abend') and \
    not any('RPESTAE' in c for c in fk.calls)
res, lines = drive25(FakeX([badscr25['other text on the screen']]), 'E1', d2)
assert res.startswith('STOP') and lines == []
# --- the checker joins a case cut once at the test screen only when that cut is named (E1-T2): segment 1 ends with
#     exactly the test screen record, segment 2 starts with the abend ENTER; logs split there; per segment the terminal
#     inputs = the driver actions; every trace / log checksum-verified by the CLI
t25, l25 = F825.build('E1')
sg25, lg25 = F825.split_segments(t25, l25, ('screen',))
Z825.check_segments(sg25, lg25, 'E1', ('screen',))
r25 = Z825.check(tuple(sg25), sum(lg25, []), 'E1', cuts=('screen',))
assert r25['state'] == 'PASS' and r25['segments'] == 2 and r25['ceeopts_left'] and \
    r25['followup']['end_lines'][0] == 'QUIT'
tg25, lgg25 = F825.build('E1', gd=dict(mutate=5))
sgm25, _ = F825.split_segments(tg25, lgg25, ('screen',))
sgh25, lgh25 = F825.split_segments(t25, l25, ('hold',))
negc25 = {'screen cut not named': (tuple(sg25), None), 'named as the hold cut': (tuple(sg25), ('hold',)),
          'undefined cut': (tuple(sg25), ('game',)), 'hold split declared as screen': (tuple(sgh25), ('screen',)),
          'lost test-screen record': (tuple(F825.split_segments(t25, l25, ('screen',), drop_last=True)[0]),
                                      ('screen',)),
          'stray host write before the ENTER': (tuple(F825.split_segments(t25, l25, ('screen',),
                                                                          extra_first=True)[0]), ('screen',)),
          'swapped segments': ((sg25[1], sg25[0]), ('screen',)), 'segment 2 missing': ((sg25[0],), ('screen',)),
          'segment 2 twice': ((sg25[0], sg25[1], sg25[1]), ('screen',)),
          'altered write in segment 2': ((sg25[0], sgm25[1]), ('screen',))}
for why25, (sg, cu) in negc25.items():
    try:
        Z825.check(sg, sum(lg25, []), 'E1', cuts=cu)
        raise AssertionError(why25)
    except Z825.Fail:
        pass
negl25 = {'abend ENTER in log 1': [lg25[0] + lg25[1][:1], lg25[1][1:]], 'hold ENTER in log 2': [lg25[0][:1],
                                                                                              lg25[0][1:] + lg25[1]],
          'log 2 entry duplicated': [lg25[0], lg25[1][:1] + lg25[1]], 'log 2 entry missing': [lg25[0], lg25[1][1:]],
          'logs swapped': [lg25[1], lg25[0]], 'one log only': [lg25[0] + lg25[1]]}
for why25, lgs in negl25.items():
    try:
        Z825.check_segments(sg25, lgs, 'E1', ('screen',))
        raise AssertionError(why25)
    except Z825.Fail:
        pass
with tempfile.TemporaryDirectory() as td25:                     # the CLI: --cuts screen, independent checksums
    fs25 = []
    for n, (tx, lg) in enumerate(zip(sg25, lg25), 1):
        for name, data in ((f's{n}.trace', tx), (f's{n}.jsonl', '\n'.join(lg) + '\n')):
            f = Path(td25) / name
            f.write_text(data)
            (Path(td25) / f'{name}.sha256').write_text(f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {name}\n')
            fs25.append(str(f))
    cli25 = [sys.executable, str(R / 'tools/zowe/zos8_live_check.py'), '--case', 'E1', '--trace', fs25[0],
             '--drive-log', fs25[1], '--trace2', fs25[2], '--drive-log2', fs25[3]]
    assert SP25.run(cli25 + ['--cuts', 'screen'], capture_output=True).returncode == 0
    assert SP25.run(cli25, capture_output=True).returncode == 1                       # not named: refused
    (Path(td25) / 's2.jsonl.sha256').write_text('0' * 64 + '  s2.jsonl\n')
    out25 = SP25.run(cli25 + ['--cuts', 'screen'], capture_output=True, text=True)
    assert out25.returncode == 1 and 'does not match' in out25.stdout
    (Path(td25) / 's2.jsonl.sha256').unlink()
    assert SP25.run(cli25 + ['--cuts', 'screen'], capture_output=True).returncode == 1  # checksum file missing
# --- Stage E S1 (2026-10-20): with SOUND(YES) the screen before the first AID rings (WCC C7 = C3 + alarm), and the
#     frozen parse6 rule (previous WCC exactly C3) left TSO's F1 C3 blocking-read control as a game write. ZOS-8 only:
#     sound_c3_controls accepts C3 or C7 (alarm bit only), everything else of the rule unchanged; sound cases only
def ev25(*items):                                       # synthetic parse6 events (order, dir, ts, payload)
    return [(i, d, f'20261020.1000{t // 1000:02d}.{t % 1000:03d}', pl) for i, (d, t, pl) in enumerate(items)]


AID25, C3R25 = bytes([0xF8, 0x6F, 0xD9]), b'\xf1\xc3'


def ctl25(wcc=0xC7, rec=C3R25, gap=False, dup=False, tso=()):
    items = [('<', 0, bytes([0xF1, wcc]) + b'\x11\x40\x40ABC'), ('>', 100, AID25)]
    if gap:
        items.append(('<', 150, b'\xf1\xc2\x11\x40\x40X'))
    items.append(('<', 200, rec))
    if dup:
        items.append(('<', 210, C3R25))
    kept, ctl = Z825.sound_c3_controls(ev25(*items), list(tso))
    return len(ctl) - len(tso), [e[3] for e in kept]


assert [w for w in range(256) if Z825.c3_alarm_equiv(w)] == [0xC3, 0xC7]
assert ctl25(0xC3)[0] == 1 and ctl25(0xC7)[0] == 1                                     # 1, 2
assert ctl25(0xC7, rec=b'\xf1\xc2')[0] == 0 and ctl25(0xC7, rec=b'\xf1\xc7')[0] == 0    # 4 wrong bytes
assert ctl25(0xC7, rec=b'\xf1\xc3\x00')[0] == 0 and ctl25(0xC7, rec=b'\xf1')[0] == 0     # 5 wrong length
n25, kept25 = ctl25(0xC7, dup=True)                                                     # 6 duplicate: one only
assert n25 == 1 and kept25.count(C3R25) == 1
assert ctl25(0xC7, gap=True)[0] == 0                                                   # 7 not right after the AID
assert Z825.sound_c3_controls(ev25(('<', 0, b'\xf1\xc7\x11\x40\x40A'), ('<', 200, C3R25)), [])[0][-1][3] == C3R25
for w25 in [0xC3 ^ (1 << b) for b in range(8) if b != 2] + [0xC0 + i for i in range(16) if 0xC0 + i not in (0xC3,
                                                                                                            0xC7)]:
    assert ctl25(w25)[0] == 0, hex(w25)                                                # 8 any other WCC
assert ctl25(0xC7, tso=[{'ms': 1, 'ts': 'x', 'aid_ms': Z825.ms(ev25(('<', 0, b''), ('>', 100, b''))[1][2]),
                         'aid': 'F8'}])[0] == 0                                         # the AID already has one
for short25 in (b'\x7e\xc3', b'\xf1\xc7', b'\xf5\xc3', b'\xf1\xc3\x11'):                 # 10 other short writes
    assert ctl25(0xC7, rec=short25)[0] == 0, short25
# end to end on the frozen ZOS-7 fixture through the ZOS-8 sound model: the live S1 shape (rung screen, AID, F1 C3)
for c25 in ('S8A', 'S8B'):
    t25, l25 = F825.build(c25, tso_c3='blocking')
    pe25 = Z825.parse8(t25)
    c0 = pe25['tso_controls']
    assert len(c0) == 1 and c0[0].get('alarm_context')
    k25 = next(k for k, e in enumerate(Z825._PARSE6(t25)['ev']) if e[1] == '>' and e[3][:1] == b'\xf8')
    prev25 = next(e for e in reversed(Z825._PARSE6(t25)['ev'][:k25]) if e[1] == '<')
    assert prev25[3][1] == 0xC7 and not Z825._PARSE6(t25)['tso_controls']               # 3: the old rule missed it
    r25 = Z825.check(t25, l25, c25, 'ABSENT')                                           # 3: now PASS
    assert r25['state'] == 'PASS' and r25['bells'] == S25.S8_BELLS[c25] and r25['bell_alarm_bits'] == 8, (c25, r25)
    for why25, kw25 in (('duplicate', dict(tso_c3='dup')), ('outside the AID context', dict(tso_c3='unrelated'))):
        assert isinstance(run25(c25, **kw25), str), (c25, why25)
t25, l25 = F825.build('S8A', tso_c3='blocking')                                         # 9: replaces a real write
ev8 = Z825.parse8(t25)['ev']
g25 = ev8[Z825.parse8(t25)['starts'][0]:]
host8 = [e for e in g25 if e[1] == '<']
i8 = g25.index(host8[2])
w8 = [e for e in g25[i8:] if e[1] == '<']
first_aid8 = next(e for e in g25[i8:] if e[1] == '>')
after8 = next(n for n, e in enumerate(w8) if Z825.ms(e[2]) > Z825.ms(first_aid8[2]))
assert isinstance(run25('S8A', tso_c3='blocking', drop_write=after8), str)
assert run25('S8C')['state'] == 'PASS' and Z825.parse8(F825.build('HL2')[0])['tso_controls'] == []  # TURN unchanged
L2t25 = F725.build('L2', tso_c3='blocking')[0]                                           # SOUND(NO): = parse6 (C3)
assert Z825.parse8(L2t25)['tso_controls'] == Z825._PARSE6(L2t25)['tso_controls'] and \
    len(Z825._PARSE6(L2t25)['tso_controls']) == 1
# --- Stage F (frozen 2026-10-20, option A): SF = HL2's LIVEB cards through the installed CLIST(PACMAN), ARCADE LEVEL 1
#     TURN, DATA(HISCORE) absent -> 980, NEW HIGH SCORE; one FB 80 record 0000980 PACHS001 001; no other member
assert S25.GAMES['SF'] == S25.GAMES['HL2'] == ('gp2live', 'LIVEB', 1, 'A') and S25.live_cards('SF') == \
    S25.live_cards('HL2') and len(S25.live_cards('SF')) - 1 == 77 and S25.kw_of('SF') == S25.kw_of('HL2')
assert DV25.command('SF', 'EXEC', 'Z00000.PACMAN') == \
    "EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) PLAY(TURN) ANIM(NO) SOUND(NO) PRESENT(COALESCED)'"
assert S25.SF_LINES == ['HIGH SCORE 0000980 LEVEL 001', 'NEW HIGH SCORE'] == Z825.expected_lines('SF', 'ABSENT')[1]
assert S25.SF_RECORD == '0000980 PACHS001 001'.ljust(80) and not (R / 'tests/zos8live/SF.txt').exists()
rsf = run25('SF')
assert isinstance(rsf, dict) and rsf['state'] == 'PASS' and rsf['sf_lines'] == S25.SF_LINES, rsf
out25 = S25.end_lines('SF', S25.live_cards('SF'))
negsf = {'different score': list(out25[:2]) + ['SCORE 0000990'] + list(out25[3:]) +
         ['HIGH SCORE 0000990 LEVEL 001', 'NEW HIGH SCORE'],
         'different level': list(out25) + ['HIGH SCORE 0000980 LEVEL 002', 'NEW HIGH SCORE'],
         'NEW HIGH SCORE missing': list(out25) + ['HIGH SCORE 0000980 LEVEL 001'],
         'HIGH SCORE NOT SAVED': list(out25) + ['HIGH SCORE 0000980 LEVEL 001', 'HIGH SCORE NOT SAVED'],
         'UNAVAILABLE': list(out25) + ['HIGH SCORE UNAVAILABLE']}
for why25, el25 in negsf.items():
    assert isinstance(run25('SF', end_lines=el25), str), why25
for why25, kw25 in (('HISCORE present before', dict(before='0000720 PACHS001 001')),
                    ('wrong card (a write differs)', dict(mutate=30)), ('a game write missing', dict(drop_write=40)),
                    ('another game (GPAI0 keywords)', dict(kw=S25.kw_of('HL4'))),
                    ('a test CLIST instead of the installed one', dict(member='PACZ8HT'))):
    assert isinstance(run25('SF', **kw25), str), why25
try:                                                # the model drifting from the frozen lines is itself a failure
    real25 = S25.SF_LINES
    S25.SF_LINES = ['HIGH SCORE 0000990 LEVEL 001', 'NEW HIGH SCORE']
    assert isinstance(run25('SF'), str)
finally:
    S25.SF_LINES = real25
ATTR25 = {'dsntp': 'PDS', 'dsorg': 'PO', 'recfm': 'FB', 'lrecl': '80', 'blksz': '80'}
EXP25 = S25.SF_RECORD.encode('cp037')
PRE25 = {'members': [], 'HISCORE': None, 'attrs': dict(ATTR25)}
POST25 = {'members': ['HISCORE'], 'HISCORE': [S25.SF_RECORD.rstrip()], 'attrs': dict(ATTR25)}
assert Z825.check_sf_store(PRE25, POST25, EXP25, EXP25) == []
negst = {'HISCORE present before': (dict(PRE25, members=['HISCORE']), POST25, EXP25),
         'HISCORE missing after': (PRE25, dict(POST25, members=[], HISCORE=None), b''),
         'extra DATA member': (PRE25, dict(POST25, members=['HISCORE', 'X']), EXP25),
         'two records': (PRE25, dict(POST25, HISCORE=[S25.SF_RECORD.rstrip()] * 2), EXP25 * 2),
         'wrong score': (PRE25, dict(POST25, HISCORE=['0000990 PACHS001 001']),
                         '0000990 PACHS001 001'.ljust(80).encode('cp037')),
         'wrong level': (PRE25, dict(POST25, HISCORE=['0000980 PACHS001 002']),
                         '0000980 PACHS001 002'.ljust(80).encode('cp037')),
         'wrong tag': (PRE25, dict(POST25, HISCORE=['0000980 PACHS002 001']), EXP25),
         'record bytes differ (padding)': (PRE25, POST25, EXP25[:-1] + b'\x00'),
         'record bytes short': (PRE25, POST25, EXP25[:79]),
         'attributes changed': (PRE25, dict(POST25, attrs=dict(ATTR25, recfm='FBA')), EXP25)}
for why25, (pr, po, by) in negst.items():
    assert Z825.check_sf_store(pr, po, by, EXP25), why25
print(f'ZOS-8 Stage F (frozen LIVEB / HL2 cards, installed CLIST, DATA absent -> 0000980 PACHS001 001): positive PASS, '
      f'{len(negsf) + 6} game faults and {len(negst)} production-state faults FAIL: PASS')
print('ZOS-8 sound F1 C3 control (C3 / C7 only): unit rules (exact record, context, once per AID, WCC C3 / C7 only, '
      'no other short write), S8A / S8B live shape PASS with bells 1/2/2/3, duplicate / unrelated / replaced write '
      'FAIL, TURN and SOUND(NO) unchanged: PASS')
print(f'ZOS-8 Stage D test screen / E1-T2 resume: wrapped (27 x 120) and unwrapped (24 x 80) real screens recognised, '
      f'{len(badscr25)} altered / missing / repeated / reordered / error screens STOP; screen cut only when named, '
      f'{len(negc25)} boundary / segment and {len(negl25)} log faults FAIL, CLI checksums: PASS')
print('ZOS-8 Stage D LISTALC / FREE: the live pagination (initial hold + output pages, one ENTER each) modelled in '
      f'driver / checker / fixture; strict CEEOPTS DD rule; {len(negp25)} checker and {len(negd25) + 1} driver faults '
      'FAIL / STOP: PASS')
print('ZOS-8 Services (Stage A, local): src / CLIST / PACHSIO / PACFSIO / ZOS-5..7 tools = zos-7 (+ the RPESTAE test '
      'CLIST); live cards = model games; Stage C chain HL1-HL8 (ref_hs); B1 model = oracle 312 (GPREVB); decks PACZ8HB '
      '/ PACZ8RPE audited, B1 geometry = DATA; test CLISTs = installed CLIST except the DATA lines; '
      'batch checkers PASS '
      f'+ 11 faults FAIL; live checker {len(pos25)} positives PASS (+ HL8 IEC variants, E leftovers), '
      f'{len(neg25) + len(neg25b)} negatives FAIL (end-screen label = the persistence outcome), sound coverage never '
      'PASS when bells differ; driver on the fake x3270if (hold, IEC stop, '
      'recovery, cleanup): PASS')
