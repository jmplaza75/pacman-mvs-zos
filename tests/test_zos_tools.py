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
