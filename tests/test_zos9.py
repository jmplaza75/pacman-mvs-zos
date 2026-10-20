#!/usr/bin/env python3
"""ZOS-9 local checks (docs/zos9-design.md; nothing submitted): the two approved gap-closing jobs PACZ9E1 / PACZ9E2.
1. frozen: production sources, the oracles and every reused ZOS-2..8 tool / model = tag zos-8;
2. tools/zowe/zos9_equiv.py selftest: every step anchored at its own oracle block, model render = oracle block for every
   step, application lines 2,167 / 2,628, deck audit, GAP paths = run configurations, injected faults detected;
3. the decks of record jcl/zos/PACZ9E1.jcl / PACZ9E2.jcl = the generated decks; exact step membership / order;
   PGM=PACZ6D only; no build / bind / promotion / PACHS / DATA / DELETE; historical PARM and cards;
4. every docs/zos9-design.md execution GAP row (G4, G6, G9, P7, P10) maps to job -> step -> oracle -> model;
5. the checker on simulated spools: the oracle blocks as SYSOUT PASS; a missing / extra / reordered / renamed step,
   another program, an RC, an extra spool DD, an unretained STEPLIB, one changed line, a wrong job name FAIL.
Usage: python3 tests/test_zos9.py
"""
import gzip
import json
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R / 'tools/zowe'), str(R / 'tests'), str(R / 'tools')]
import zos9_equiv as Z  # noqa: E402

# 1. frozen ---------------------------------------------------------------------------------------------------------
FROZEN = ['src', 'tests/oracle20', 'releases/2.0-MVS-MAX', 'tools/make_deck.py', 'tools/zowe/zos_target.py',
          'tools/zowe/zos_equiv.py', 'tools/zowe/zos_classic_check.py', 'tools/zowe/zos_listing.py',
          'tools/zowe/zos6_dry.py', 'tools/zowe/zos5_live_check.py', 'tools/zowe/zos6_live_check.py',
          'tools/zowe/zos7_live_check.py', 'tools/zowe/zos7_dry.py', 'tools/zowe/zos8_live_check.py',
          'tests/ref_gx_screen.py', 'tests/ref_gp2.py', 'tests/ref_rt.py', 'tests/ref_mvs6.py', 'tests/test_gp2.py',
          'tests/test_gx.py', 'tests/gpcases', 'tests/gp2cases', 'tests/rtcases', 'tests/cases']
for p in FROZEN:
    ex = [':(exclude)src/zos/PACMAN.clist'] if p == 'src' else []     # ZOS-10 Z6, checked exactly below
    r = subprocess.run(['git', 'diff', '--quiet', 'zos-8', '--', p] + ex, cwd=R)
    assert r.returncode == 0, f'{p} differs from zos-8'
import zos_c2  # noqa: E402
assert zos_c2.z6_strip((R / 'src/zos/PACMAN.clist').read_text()) == subprocess.run(
    ['git', 'show', 'zos-8:./src/zos/PACMAN.clist'], cwd=R, capture_output=True, text=True, check=True).stdout
print('frozen sources / oracles / reused tools and models = zos-8: PASS')

# 2. selftest ---------------------------------------------------------------------------------------------------------
ok, res, det = Z.selftest()
assert ok, [k for k, v in res.items() if not v] + [k for k, v in det.items() if not v]
print(f'zos9_equiv selftest: {len(res)} checks PASS, {len(det)} injected faults detected: PASS')

# 3. decks of record ---------------------------------------------------------------------------------------------------
WANT = {1: ('PACZ9E1', ['TSD2', 'TSD5', 'TSD14', 'TSD36', 'TSD41', 'TSD43', 'TSD50', 'TSD52', 'TSD55', 'TSD56',
                        'RTB2', 'RTB3', 'RTB4', 'RTB12'], 2167),
        2: ('PACZ9E2', ['G3T4', 'G3T5', 'G3T7', 'G3T8', 'G3T10', 'G3T14', 'G3T15', 'G3T26', 'G3T28', 'G3R3'], 2628)}
APPROVED = {1: {'TSD2', 'TSD5', 'TSD14', 'TSD41', 'TSD36', 'TSD43', 'TSD50', 'TSD52', 'TSD55', 'TSD56', 'RTB2', 'RTB3',
                'RTB4', 'RTB12'},
            2: {'G3T4', 'G3T5', 'G3T8', 'G3T26', 'G3T28', 'G3T7', 'G3T10', 'G3T15', 'G3T14', 'G3R3'}}
import zos_target as zt  # noqa: E402
for n, (job, steps, lines) in WANT.items():
    assert Z.JOBS[n][0] == job and Z.JOBS[n][4] == steps and set(steps) == APPROVED[n] and Z.APP_LINES[n] == lines
    text = (R / f'jcl/zos/{job}.jcl').read_text()
    assert text == Z.deck(n), f'{job}: the deck of record differs from the generated deck'
    assert list(zt.steps_of_deck(text)) == steps
    assert text.count('EXEC PGM=') == len(steps) == text.count('EXEC PGM=PACZ6D,COND=(0,NE)')
    for w in ('PACHS', '.DATA', 'DELETE', 'IEBCOPY', 'IEWBLINK', 'IGYCRCTL', 'ASMA90', 'PGM=PACMAIN', 'SYSLMOD'):
        assert w not in text, (job, w)
    assert Z.audit(n, text, '@@HLQ@@.PACMAN')
    assert sum(len(Z.oracle_block(n, s)) for s in steps) == lines
print('decks of record PACZ9E1 (14 steps, 2,167 lines) / PACZ9E2 (10 steps, 2,628 lines) = generated, PACZ6D only, '
      'historical PARM / cards, no PACHS / DATA / DELETE / build: PASS')

# 4. GAP -> job -> step -> oracle -> model -----------------------------------------------------------------------------
ROWS = {'G4': {'G3T4', 'G3T5', 'G3T8', 'G3R3'}, 'G6': {'G3T26', 'G3T28'}, 'G9': {'RTB2', 'RTB3', 'RTB4', 'RTB12'},
        'P7': {'TSD2', 'TSD5', 'TSD14', 'TSD36', 'TSD41', 'TSD43', 'TSD50', 'TSD52', 'TSD55', 'TSD56', 'G3T4', 'G3T5',
               'G3T7', 'G3T8', 'G3T10', 'G3T14', 'G3T15', 'G3T26', 'G3T28'},
        'P10': {'G3T4', 'G3R3'}}
for row, steps in ROWS.items():
    mapped = {s for s, g in Z.GAPS.items() if any(x.split()[0].strip('/') == row or f'/ {row} ' in x or
                                                  x.startswith(f'{row} ') for x in g)}
    assert mapped == steps, (row, sorted(mapped ^ steps))
PATHS = ['HILITE(NO)', 'GLYPHS(BASE)', 'GRAPHIC', 'CLASSIC glyphs', 'SCALE(3)', 'size guard', '132x27', '80x32',
         '100x25', '160x30', '80x24', 'RTCORNER', 'RTTTL', 'RTREV', 'RTEDGE0', 'GPTWOF', 'GPFN', 'GPTICK', 'G2BGHX',
         'G2BUND', 'RTGPP']
for p in PATHS:
    assert any(p in x for g in Z.GAPS.values() for x in g), p
design = (R / 'docs/zos9-design.md').read_text()
for n, (job, steps, _) in WANT.items():
    for s in steps:
        assert f'| {s} |' in design, f'{s} missing from the design mapping table'
print(f'GAP rows {sorted(ROWS)} -> {sum(len(v[1]) for v in WANT.values())} steps -> own oracle block -> frozen model; '
      f'{len(PATHS)} named paths each carried by a step; design table complete: PASS')


# 5. the checker on simulated spools -----------------------------------------------------------------------------------
def spool(d, job, steps, outputs, pgm=None, rc='0000', retain=True, extra=()):
    d.mkdir(parents=True)
    (d / 'job.json').write_text(json.dumps({'jobname': job, 'jobid': 'JOB09999', 'retcode': 'CC 0000'}))
    prog = pgm if isinstance(pgm, dict) else {}
    jcl = [f'        1 //{job} JOB 1,CLASS=7'] + [f'        2 //{s:<8} EXEC PGM={prog.get(s, "PACZ6D")}' for s in steps]
    msg = []
    for s in steps:
        msg.append(f' IEF142I {job} {s} - STEP WAS EXECUTED - COND CODE {rc if s == steps[0] else "0000"}')
        if retain:
            msg.append(' IGD104I Z00000.PACMAN.LOAD                           RETAINED,  DDNAME=STEPLIB')
    files = [{'id': 2, 'ddname': 'JESJCL', 'stepname': 'JES2', 'procstep': None, 'recfm': 'V'},
             {'id': 3, 'ddname': 'JESYSMSG', 'stepname': 'JES2', 'procstep': None, 'recfm': 'VA'}]
    (d / '002-JES2-JESJCL.txt').write_text('\n'.join(jcl) + '\n')
    (d / '003-JES2-JESYSMSG.txt').write_text('\n'.join(msg) + '\n')
    k = 100
    for s in steps:
        k += 1
        files.append({'id': k, 'ddname': 'SYSOUT', 'stepname': s, 'procstep': None, 'recfm': 'FBA', 'lrecl': 121})
        (d / f'{k:03d}-{s}-SYSOUT.txt').write_text(''.join(' ' + l.ljust(120) + '\n' for l in outputs[s]))
    for s, dd in extra:
        k += 1
        files.append({'id': k, 'ddname': dd, 'stepname': s, 'procstep': None, 'recfm': 'FBA'})
        (d / f'{k:03d}-{s}-{dd}.txt').write_text(' x\n')
    (d / 'spool.json').write_text(json.dumps(files))
    return d


neg = 0
with tempfile.TemporaryDirectory() as t:
    for n, (job, steps, _) in WANT.items():
        outs = {s: Z.oracle_block(n, s) for s in steps}
        ok, rep = Z.check(spool(Path(t) / f'ok{n}', job, steps, outs), n)
        assert ok and all(v['state'] == 'PASS' for v in rep['steps'].values()), rep
        s0, s1 = steps[0], steps[-1]
        changed = dict(outs)
        changed[s1] = outs[s1][:3] + [outs[s1][3] + 'X'] + outs[s1][4:]
        cases = {'missing step': (job, steps[:-1], outs, {}),
                 'extra step': (job, steps + ['TSD1' if n == 1 else 'G3T1'],
                                dict(outs, **{('TSD1' if n == 1 else 'G3T1'): Z.oracle_block(n, 'TSD1' if n == 1 else
                                                                                            'G3T1')}), {}),
                 'reordered steps': (job, [steps[1], steps[0]] + steps[2:], outs, {}),
                 'renamed job': ('PACZ9EX', steps, outs, {}),
                 'PACMAIN executed': (job, steps, outs, {'pgm': {s0: 'PACMAIN'}}),
                 'RC 0004': (job, steps, outs, {'rc': '0004'}),
                 'CEEDUMP spool': (job, steps, outs, {'extra': [(s0, 'CEEDUMP')]}),
                 'STEPLIB not retained': (job, steps, outs, {'retain': False}),
                 'one line changed': (job, steps, changed, {})}
        for i, (why, (jn, st, o, kw)) in enumerate(cases.items()):
            ok, rep = Z.check(spool(Path(t) / f'n{n}{i}', jn, st, o, **kw), n)
            assert not ok, (job, why)
            neg += 1
        ok, rep = Z.check(spool(Path(t) / f'c{n}', job, steps, changed), n)
        assert [s for s, v in rep['steps'].items() if v['state'] != 'PASS'] == [s1], rep   # only the changed step
print(f'checker on simulated spools: both jobs PASS on their oracle blocks; {neg} faults FAIL; a one-line change fails '
      'that step only: PASS')
print('ZOS-9 LOCAL CHECKS PASS')
