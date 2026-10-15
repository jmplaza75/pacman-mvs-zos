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
with tempfile.TemporaryDirectory() as t:
    subprocess.run([sys.executable, str(R / 'tools/make_deck.py'), '--target', 'zos', 'Z4CL', '--out',
                    str(Path(t) / 'c.jcl')], check=True, capture_output=True)
    assert (Path(t) / 'c.jcl').read_text() == cl, 'PACZ4CL.jcl is not the generated deck'
cst = zos_target.steps_of_deck(cl)
assert list(cst) == CLK.STEPS and 'DELETE' not in cl and 'PACMAN.DATA' not in cl and 'PACMAIN' not in cl
assert set(re.findall(r'DSN=([\w@.]+)', cl)) == {'@@HLQ@@.PACMAN.Z4CL.T1', '@@HLQ@@.PACMAN.Z4HSY.DATA'}
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
    f"  EXEC '{W}(HSCLN)'", '--DDNAME---DISP--', 'NULLFILE  PACHS', 'HSCL END', 'READY', 'END']
assert all(v for _, v in CLK.tmp_check(good)), CLK.tmp_check(good)
bad_tmp = {
    'wrong PARM': [l.replace('A01FS', 'A01NS') for l in good],
    'present path DUMMY': [l if l != f'{Y}(HISCORE)' else 'NULLFILE  PACHS' for l in good],
    'missing path allocated': [l if l != 'NULLFILE  PACHS' else f'{CLK.NO}(HISCORE)' for l in good],
    'no HSCL END': good[:good.index('HSCL END')] + good[good.index('HSCL END') + 1:],
    'IKJ56 message': good[:-1] + ['IKJ56228I DATA SET NOT IN CATALOG'] + good[-1:],
    'order swapped': [l.replace('(HSCLY)', '(TMPX)').replace('(HSCLN)', '(HSCLY)').replace('(TMPX)', '(HSCLN)')
                      for l in good],
}
for why, ls in bad_tmp.items():
    assert not all(v for _, v in CLK.tmp_check(ls)), why
print('PACZ4CL: generated deck, only Z4CL.T1 / Z4HSY.DATA (no DATA, no DELETE, no PACMAIN), MVS test CLISTs exactly '
      '(two prefixes instead of a DELETE), G8PARM = oracle 307, TMP-output rules pass the expected shape and fail '
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
