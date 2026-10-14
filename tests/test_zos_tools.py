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
