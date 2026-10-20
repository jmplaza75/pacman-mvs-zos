#!/usr/bin/env python3
"""ZOS-9 PACZ9E1 / PACZ9E2 (docs/zos9-design.md, decisions DEC-1..4 of 2026-10-20): the two approved gap-closing batch
jobs - their decks and their fail-closed per-step checker. Read-only on z/OS: every step is EXEC PGM=PACZ6D (the build
installed as PACMAIN by PACZ6INS JOB09499) from <prefix>.LOAD; no build, bind or promotion step; no PACHS DD; no DATA
reference; no DELETE; spool output only.

Each step is taken verbatim from the z/OS rendering (tools/zowe/zos_target.py, as every chunk deck) of the MVS deck that
produced its oracle - GP2 (oracle JOB 310) for PACZ9E1, GP23 (oracle JOB 311) for PACZ9E2 - so its PARM and cards are
the historical ones (checked against releases/2.0-MVS-MAX/decks). Steps are in deck = oracle order (the anchoring rule).

Each step is checked on its own, twice:
1. oracle: its own frozen 2.0 block (zos_equiv --subset: step identity + ordinal anchoring, exact text; only the ASA
   column and the record padding are removed - the approved normalisation, unchanged);
2. model: the frozen independent model of that run, rendered as the SYSOUT the program prints:
   TSD<n>  (make_deck TSD['GX'][n-1], the test_gx run list)  tests/ref_gx_screen.frames + the 1.0 end lines (ref_mvs6);
   RTB<n>  (make_deck RT_BAT[n-1])                            tests/ref_rt.simulate (as tests/test_rt.py);
   G3T<n>  (make_deck GP23_TURN[n-1])                         ref_gx_screen.frames on ref_gp2.Level + ref_gp2 end lines
                                                              (as tests/test_gp2.py GP2.3);
   G3R<n>  (make_deck GP23_RT[n-1])                           ref_rt.tsd on ref_gp2.Level / LevelRT (as test_gp2.py).
   The TSD text form (TSX switch, TSX FULL, 'TSD FRAME LENnnnn' + 64-hex lines) is parsed back with the frozen
   fail-closed parser of tools/zowe/zos6_dry.py; frames, transport lines and end lines must all equal the model.
No new model, no copy of expected output: the selftest proves model render = oracle block for every step.

Usage: zos9_equiv.py --job N --deck OUT.jcl          write job N's deck (prefix @@HLQ@@.PACMAN)
       zos9_equiv.py --selftest                      mapping, decks, oracle = model for every step, injected faults
       zos9_equiv.py --job N SPOOLDIR [--report F]   check job N; exit 0 only if every step passes
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests'), str(R / 'tools')]
import ref_gp2 as L  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
import ref_rt  # noqa: E402
from ref_mvs6 import simulate as classic_simulate  # noqa: E402
from ref_snap import Log  # noqa: E402

LOAD = 'PACZ6D'
# job -> (job name, MVS deck, oracle job, oracle file, steps in deck order)
JOBS = {
    1: ('PACZ9E1', 'GP2', '310', '310-PACBLGP2.json.gz',
        ['TSD2', 'TSD5', 'TSD14', 'TSD36', 'TSD41', 'TSD43', 'TSD50', 'TSD52', 'TSD55', 'TSD56',
         'RTB2', 'RTB3', 'RTB4', 'RTB12']),
    2: ('PACZ9E2', 'GP23', '311', '311-PACBLG23.json.gz',
        ['G3T4', 'G3T5', 'G3T7', 'G3T8', 'G3T10', 'G3T14', 'G3T15', 'G3T26', 'G3T28', 'G3R3']),
}
RELEASE_DECK = {'GP2': 'R20-GP2.jcl', 'GP23': 'R20-GP23.jcl'}
APP_LINES = {1: 2167, 2: 2628}          # docs/zos9-design.md 7.3: the sum of the frozen oracle blocks
# step -> the docs/zos9-design.md GAP rows / paths it closes (every listed path is reached by that step's run config
# or by its case's documented edge; asserted by the selftest against the step's PARM and case name)
GAPS = {
    'TSD2': ['P7 CLASSIC glyphs, partial redraw, not scaled (G3 profile)'],
    'TSD5': ['P7 HILITE(NO) colour-only profile (CLASSIC)'],
    'TSD14': ['P7 GRAPHIC glyphs not scaled (G4 renderer, CLASSIC)'],
    'TSD36': ['P7 SCALE(3) 3x2 renderer (CLASSIC)'],
    'TSD41': ['P7 GLYPHS(BASE) (CLASSIC; scale requested, refused -> G4 BASE)'],
    'TSD43': ['P7 SCALE T = size guard (CLASSIC)'],
    'TSD50': ['P7 canvas X 132x27 (CLASSIC)'],
    'TSD52': ['P7 canvas M 80x32 (CLASSIC)'],
    'TSD55': ['P7 canvas U 100x25, too small (CLASSIC)'],
    'TSD56': ['P7 canvas L 160x30, > 4095 cells (CLASSIC)'],
    'RTB2': ['G9 REALTIME edge RTCORNER'],
    'RTB3': ['G9 REALTIME edge RTTTL'],
    'RTB4': ['G9 REALTIME edge RTREV'],
    'RTB12': ['G9 REALTIME edge RTEDGE0'],
    'G3T4': ['P7 HILITE(NO) (ARCADE)', 'G4 GPTWOF two frightened ghosts eaten in one collision check (200 + 400)',
             'P10 RP popup-two-ghosts'],
    'G3T5': ['P7 GRAPHIC not scaled 80x24 (ARCADE)', 'G4 GPTICK idle tick'],
    'G3T7': ['P7 ARCADE scale 4 on 80x24 (compact HUD)'],
    'G3T8': ['P7 SCALE(3) 3x2 (ARCADE)', 'G4 GPFN frightened ghost eaten, then normal-ghost hit'],
    'G3T10': ['P7 canvas X 132x27 (ARCADE)'],
    'G3T14': ['P7 SCALE T = size guard (ARCADE)'],
    'G3T15': ['P7 canvas M 80x32 (ARCADE)'],
    'G3T26': ['P7 CLASSIC glyphs not scaled (ARCADE)', 'G6 G2BGHX ghost on the fruit cell'],
    'G3T28': ['P7 GLYPHS(BASE) (ARCADE)', 'G6 G2BUND fruit left uneaten'],
    'G3R3': ['P10 / G4 RTGPP pause during a fright (ARCADE REALTIME)'],
}
SWITCH_CMD = {'D': 'F5'}


def cards(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


def oracle(n):
    return json.load(gzip.open(R / 'tests/oracle20' / JOBS[n][3]))


def oracle_block(n, step):
    """The step's own frozen block (zos_equiv anchoring, no content search), right-stripped, trailing blanks dropped."""
    import zos_equiv as ZE
    o = oracle(n)
    anc = ZE.anchors(o, {'PACMAIN'})
    s, b = o['stream'], anc[step]
    x = s[b:min([v for v in anc.values() if v > b], default=len(s))]
    while x and x[-1] == '':
        x.pop()
    return [l.rstrip() for l in x]


# ---- the frozen run definitions of each step (make_deck lists) -------------------------------------------------------
def run_of(step):
    import make_deck as md
    k = int(re.search(r'(\d+)$', step).group(1)) - 1
    if step.startswith('TSD'):
        return md.TSD['GX'][k]
    if step.startswith('RTB'):
        return md.RT_BAT[k]
    if step.startswith('G3T'):
        return md.GP23_TURN[k]
    if step.startswith('G3R'):
        return md.GP23_RT[k]
    raise KeyError(step)


def gx_params(run):
    """tests/test_gx.py params(): (case, hilite, anim, redraw, glyphs[, scale[, canvas]]) with the deck defaults."""
    run = tuple(run) + ('C',) * (5 - len(run)) if len(run) < 5 else tuple(run)
    c, h, a, r, gl = run[:5]
    return c, h == 'Y', a == 'Y', r, gl, run[5] if len(run) > 5 else 'N', run[6] if len(run) > 6 else 'D'


_BELLS = []


def gp23_bells():
    """tests/test_gp2.py bells() (the GP2.3 single-bell screen model), executed verbatim from the frozen file."""
    if not _BELLS:
        src = (R / 'tests/test_gp2.py').read_text()
        code = src[src.index('def bells(frames, log, sound):'):src.index('def mk_turn(st):')]
        ns = {}
        exec(compile(code, str(R / 'tests/test_gp2.py'), 'exec'), ns)
        _BELLS.append(ns['bells'])
    return _BELLS[0]


def model(step):
    """-> dict(kind 'TSD', canvas, frames (as sent, bells included), plain (without bells), out = end lines) or
    dict(kind 'BAT', lines)."""
    run = run_of(step)
    if step.startswith('RTB'):
        return {'kind': 'BAT', 'lines': [l.rstrip() for l in ref_rt.simulate(cards('rtcases', run))]}
    if step.startswith('TSD'):
        c, h, a, r, gl, sc, cv = gx_params(run)
        fs = gx.frames(c, h, a, r, gl, sc, cv)
        end = classic_simulate(cards('cases', c))
        out = end[len(end) - next(i for i, l in enumerate(reversed(end), 1) if l.rstrip() in
                                  ('WIN', 'LOST', 'QUIT', 'EOF')):]
        return {'kind': 'TSD', 'canvas': cv, 'frames': list(fs), 'plain': list(fs), 'out': [l.rstrip() for l in out]}
    if step.startswith('G3T'):
        d, c, h, a, r, gl, sc, cv, snd, st = run
        start, log = L.parse_start(st), Log()
        fs = gx.frames(c, h == 'Y', a == 'Y', r, gl, sc, cv, snap=log, mk=lambda ai, n: L.Level(ai, n, 'T', start), d=d)
        frames, _ = gp23_bells()(fs, log, snd)
        out = L.simulate(cards(d, c), start=start)[-7:]
        return {'kind': 'TSD', 'canvas': cv, 'frames': frames, 'plain': list(fs), 'out': [l.rstrip() for l in out]}
    d, c, cv, snd, st = run
    start, log = L.parse_start(st), Log()
    end, fr = ref_rt.tsd(cards(d, c), cv, snap=log, mk_game=lambda ai, n: L.Level(ai, n, 'R', start), mk_ctl=L.LevelRT)
    frames, _ = gp23_bells()(list(fr), log, snd)
    return {'kind': 'TSD', 'canvas': cv, 'frames': frames, 'plain': list(fr), 'out': [l.rstrip() for l in end[-8:]]}


def switch_line(cv):
    w, h = gx.CANVASES.get(cv, (80, 24))
    return f'TSX SWITCH {"7E" if cv in gx.CANVASES else "F5"} {w:03d}X{h:03d}'


def expected_tsx(m):
    """[(frame index, TSX line)]: the size switch first, then FULL FIRST / FULL <cmd> before every full-screen frame."""
    cmd = '7E' if m['canvas'] in gx.CANVASES else 'F5'
    out, first = [(0, switch_line(m['canvas']))], True
    for k, f in enumerate(m['plain']):
        if 0x1D in f:                    # tests/test_gx.py transport rule: a full screen carries SF orders
            out.append((k, 'TSX FULL FIRST' if first else f'TSX FULL {cmd}'))
            first = False
    return out


def render(m):
    """The SYSOUT text of a model (selftest: = the oracle block; the checker compares parsed parts, not this text)."""
    if m['kind'] == 'BAT':
        return list(m['lines'])
    tsx, lines = dict(), []
    for k, t in expected_tsx(m):
        tsx.setdefault(k, []).append(t)
    for k, f in enumerate(m['frames']):
        lines += tsx.get(k, [])
        lines.append(f'TSD FRAME LEN{len(f):04d}')
        h = f.hex().upper()
        lines += ['TSD ' + h[i:i + 64] for i in range(0, len(h), 64)]
    return lines + list(m['out'])


def compare_model(lines, m):
    """-> (ok, findings): BAT exact lines; TSD parsed with the frozen zos6_dry parser (fail closed), then frames,
    transport lines and end lines each equal to the model."""
    import zos6_dry as D6
    if m['kind'] == 'BAT':
        return D6.compare_lines(lines, m['lines'])
    try:
        tsx, frames, end = D6.parse_tsd([l.rstrip() for l in lines])
    except D6.Bad as ex:
        return False, [f'PARSE: {ex}']
    msgs = []
    if len(frames) != len(m['frames']):
        msgs.append(f'frames: {len(frames)} on z/OS, {len(m["frames"])} in the model')
    k = next((j for j, (a, b) in enumerate(zip(frames, m['frames'])) if a != b), None)
    if k is not None:
        msgs.append(f'frame {k} differs')
    if tsx != expected_tsx(m):
        msgs.append(f'TSX lines differ: {tsx[:3]} / {expected_tsx(m)[:3]}')
    if end != m['out']:
        msgs.append(f'end lines {end} != {m["out"]}')
    return not msgs, msgs


# ---- decks -----------------------------------------------------------------------------------------------------------
FORBIDDEN = ('PACHS', '.DATA', 'DELETE', 'IEBCOPY', 'IEWBLINK', 'IGYCRCTL', 'ASMA90', 'SYSLMOD', 'PACMAIN',
             'PACZ2D', 'IEFBR14', 'IKJEFT01', 'DISP=NEW', 'DISP=(NEW', 'DISP=OLD', 'DISP=MOD')


def deck(n, pfx='@@HLQ@@.PACMAN'):
    import make_deck as md
    import zos_target as zt
    if not zt._md:
        zt.apply(md, pfx)
    zt.JOBNAME = None
    job, base, _, _, steps = JOBS[n]
    full = zt.steps_of_deck(md.build(base, pfx, LOAD))
    order = [s for s in full if s in steps]
    assert order == steps, f'{job}: steps not in deck order: {order}'
    out = zt.job_card(job, f'PACMAN ZOS9 {job}')
    for s in steps:
        t = full[s].replace('\n//\n', '\n') if full[s].endswith('\n//\n') else full[s]
        assert re.match(rf'//{s}\s+EXEC PGM={LOAD},COND=\(0,NE\)', t), s
        out += t
    audit(n, out, pfx)
    return out


def release_step(n, step):
    """(PARM, SYSIN cards) of a step in the frozen 2.0 release deck of record."""
    import zos_target as zt
    t = zt.steps_of_deck((R / 'releases/2.0-MVS-MAX/decks' / RELEASE_DECK[JOBS[n][1]]).read_text())[step]
    return step_parts(t)


def step_parts(t):
    m = re.search(r"PARM='([^']*)'", t)
    cs = re.search(r'//SYSIN\s+DD \*\n(.*?)\n/\*', t, re.S)
    return (m.group(1) if m else None), (cs.group(1).split('\n') if cs else None)


def audit(n, text, pfx):
    """Fail closed: only the approved steps, each EXEC PGM=PACZ6D, STEPLIB <prefix>.LOAD SHR, the historical PARM and
    cards, CEEOPTS = profile A, SYSOUT only; nothing that builds, binds, promotes, deletes or touches DATA / PACHS."""
    import zos_target as zt
    job, _, _, _, steps = JOBS[n]
    assert text.startswith(f'//{job} ') and text.count(' JOB ') == 1, 'job card'
    parts = zt.steps_of_deck(text)
    assert list(parts) == steps, f'step membership / order {list(parts)}'
    assert text.count('EXEC PGM=') == len(steps) == text.count(f'EXEC PGM={LOAD},'), 'programs'
    head = text.split('\n//' + steps[0], 1)[0]
    for w in FORBIDDEN:
        assert w not in text.replace(head, ''), f'forbidden {w!r} in a step'
    dsns = set(re.findall(r'DSN=([^,\s]+)', text))
    assert dsns == {f'{pfx}.LOAD'}, f'datasets {dsns}'
    for s, t in parts.items():
        assert t.count(f'//STEPLIB  DD DSN={pfx}.LOAD,DISP=SHR\n') == 1, s
        assert '//CEEOPTS  DD *\nALL31(OFF),STACK(,,BELOW)\n/*\n' in t, s
        dds = re.findall(r'^//(\w+)\s+DD ', t, re.M)
        assert dds == ['STEPLIB', 'CEEOPTS', 'SYSIN', 'SYSOUT', 'CEEDUMP', 'SYSUDUMP'], (s, dds)
        assert step_parts(t) == release_step(n, s), f'{s}: PARM / cards differ from the 2.0 deck of record'
    return True


# ---- check of a downloaded spool -------------------------------------------------------------------------------------
def check(spool, n):
    import zos_equiv as ZE
    from zos_classic_check import health
    job_name, _, oname, _, steps = JOBS[n]
    job, names, runs, hb, nlines = health(spool, (LOAD,))
    rep = {'job': job.get('jobname'), 'jobid': job.get('jobid'), 'retcode': job.get('retcode'), 'spool_lines': nlines,
           'health': hb or 'OK', 'steps': {}}
    ok = not hb and job.get('jobname') == job_name and names == steps
    if names != steps:
        rep['why'] = f'steps {names} != {steps}'
    nb, msgs = ZE.compare(oracle(n), runs, {'PACMAIN': LOAD}, subset=True)
    rep['oracle_compare'] = [m for m in msgs if not m.startswith('SUBSET')]
    ok &= nb == 0
    per = {m.split()[1].rstrip(':'): m.startswith('OK') for m in rep['oracle_compare'] if m[:4] in ('OK  ', 'FAIL')}
    for s in steps:
        r = runs.get(s)
        res = {'gaps': GAPS[s]}
        if r is None:
            res.update(state='FAIL', why='missing')
            ok = False
            rep['steps'][s] = res
            continue
        res.update(pgm=r['pgm'], rc=r['rc'], lines=len(r['lines']))
        g1 = r['pgm'] == LOAD and r['rc'] == '0000' and not r['extra']
        g2 = per.get(s, False)
        import zos6_dry as D6
        g3, w3 = D6.compare_lines(r['lines'], oracle_block(n, s))
        g4, w4 = compare_model(r['lines'], model(s))
        res.update(step_ok=g1, oracle_anchor=g2, oracle_block='exact' if g3 else w3, model='exact' if g4 else w4)
        res['state'] = 'PASS' if g1 and g2 and g3 and g4 else 'FAIL'
        ok &= res['state'] == 'PASS'
        rep['steps'][s] = res
    rep['state'] = 'PASS' if ok else 'FAIL'
    return ok, rep


# ---- selftest --------------------------------------------------------------------------------------------------------
def selftest():
    res, det = {}, {}
    import zos_equiv as ZE
    for n, (job, base, oname, _, steps) in JOBS.items():
        o = oracle(n)
        anc = ZE.anchors(o, {'PACMAIN'})
        res[f'{job}: every step anchored at its own oracle {oname} block'] = all(s in anc for s in steps)
        total = 0
        for s in steps:
            ob = oracle_block(n, s)
            total += len(ob)
            m = model(s)
            res[f'{job} {s}: model render = oracle block ({len(ob)} lines)'] = render(m) == ob
            res[f'{job} {s}: checker model compare accepts the oracle block'] = compare_model(ob, m)[0]
            res[f'{job} {s}: mapped to GAP rows'] = bool(GAPS.get(s))
        res[f'{job}: application lines = {APP_LINES[n]}'] = total == APP_LINES[n]
        res[f'{job}: deck audit (PACZ6D only, historical PARM / cards, no build / PACHS / DATA / DELETE)'] = \
            bool(deck(n))
    res['GAP map covers exactly the job steps'] = sorted(GAPS) == sorted(sum((j[4] for j in JOBS.values()), []))
    # the paths named in GAPS follow from the frozen run configuration of the step
    prof = {'TSD2': lambda p: p[1:5] == (True, True, 'P', 'C') and p[5] == 'N',
            'TSD5': lambda p: not p[1], 'TSD14': lambda p: p[4] == 'G' and p[5] == 'N',
            'TSD36': lambda p: p[5] == '3', 'TSD41': lambda p: p[4] == 'B', 'TSD43': lambda p: p[5] == 'T',
            'TSD50': lambda p: p[6] == 'X', 'TSD52': lambda p: p[6] == 'M', 'TSD55': lambda p: p[6] == 'U',
            'TSD56': lambda p: p[6] == 'L'}
    for s, f in prof.items():
        res[f'{s}: run configuration = its GAP path'] = f(gx_params(run_of(s)))
    rt = {'RTB2': 'RTCORNER', 'RTB3': 'RTTTL', 'RTB4': 'RTREV', 'RTB12': 'RTEDGE0'}
    for s, c in rt.items():
        res[f'{s}: case {c}'] = run_of(s) == c
    g3 = {'G3T4': ('GPTWOF', 'N', 'G', 'N', 'D'), 'G3T5': ('GPTICK', 'Y', 'G', 'N', 'D'),
          'G3T7': (None, 'Y', 'G', '4', 'D'), 'G3T8': ('GPFN', 'Y', 'G', '3', 'D'), 'G3T10': (None, 'Y', 'G', '4', 'X'),
          'G3T14': (None, 'Y', 'G', 'T', 'W'), 'G3T15': (None, 'Y', 'G', '4', 'M'),
          'G3T26': ('G2BGHX', 'Y', 'C', 'N', 'D'), 'G3T28': ('G2BUND', 'Y', 'B', 'N', 'D')}
    for s, (c, h, gl, sc, cv) in g3.items():
        d_, c_, h_, a_, r_, gl_, sc_, cv_, snd_, st_ = run_of(s)
        res[f'{s}: case / HILITE / GLYPHS / SCALE / canvas = its GAP path'] = \
            (c is None or c_ == c) and (h_, gl_, sc_, cv_) == (h, gl, sc, cv)
    res['G3R3: case RTGPP (pause during a fright)'] = run_of('G3R3')[:2] == ('gpcases', 'RTGPP')
    # injected faults: the comparisons fail closed
    n, s = 2, 'G3T4'
    ob, m = oracle_block(n, s), model(s)
    k = next(i for i, l in enumerate(ob) if l.startswith('TSD ') and not l.startswith('TSD FRAME') and len(l) > 20)
    flip = ob[k][:10] + ('0' if ob[k][10] != '0' else '1') + ob[k][11:]
    bad = {'one hex digit changed': ob[:k] + [flip] + ob[k + 1:],
           'one hex line dropped': ob[:k] + ob[k + 1:], 'end line changed': ob[:-1] + ['LEVEL 002'],
           'end lines missing': ob[:-7], 'TSX switch changed': [ob[0].replace('F5', '7E')] + ob[1:],
           'a frame duplicated': ob[:k - 1] + ob[k - 1:k + 3] + ob[k - 1:]}
    for why, ls in bad.items():
        det[f'{s} {why}'] = not compare_model(ls, m)[0]
    b2 = oracle_block(1, 'RTB12')
    det['RTB12 one line changed'] = not compare_model(b2[:5] + [b2[5] + 'X'] + b2[6:], model('RTB12'))[0]
    det['TSD56 model of another canvas rejected'] = not compare_model(oracle_block(1, 'TSD56'), model('TSD55'))[0]
    import make_deck as md
    import zos_target as zt
    d1 = deck(1)
    mutants = {'extra step': d1 + zt.steps_of_deck(md.build('GP2', '@@HLQ@@.PACMAN', LOAD))['TSD1'],
               'missing step': d1.replace(zt.steps_of_deck(d1)['RTB4'], ''),
               'PACHS DD': d1.replace('//SYSOUT   DD SYSOUT=A\n', '//PACHS    DD DUMMY\n//SYSOUT   DD SYSOUT=A\n', 1),
               'DATA reference': d1.replace('DSN=@@HLQ@@.PACMAN.LOAD,DISP=SHR', 'DSN=@@HLQ@@.PACMAN.DATA,DISP=SHR', 1),
               'PACMAIN executed': d1.replace(f'EXEC PGM={LOAD},', 'EXEC PGM=PACMAIN,', 1),
               'card changed': d1.replace('//SYSIN    DD *\nR\n', '//SYSIN    DD *\nL\n', 1),
               'PARM changed': d1.replace("PARM='TSD AI1 1  NYYP'", "PARM='TSD AI1 1  NYYF'", 1),
               'DELETE added': d1 + '//DEL      EXEC PGM=IEFBR14\n//D DD DSN=X,DISP=(OLD,DELETE)\n'}
    for why, t in mutants.items():
        try:
            audit(1, t, '@@HLQ@@.PACMAN')
            det[f'deck {why}'] = False
        except (AssertionError, KeyError):
            det[f'deck {why}'] = True
    res['all injected faults detected'] = all(det.values())
    return all(res.values()), res, det


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spool', nargs='?')
    ap.add_argument('--deck')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--report')
    ap.add_argument('--job', type=int, choices=(1, 2))
    a = ap.parse_args()
    if a.deck:
        Path(a.deck).write_text(deck(a.job))
        print(f'{a.deck}: {len(JOBS[a.job][4])} steps, application SYSOUT lines {APP_LINES[a.job]}')
        return
    if a.selftest:
        ok, res, det = selftest()
        for k, v in res.items():
            print(f'{"PASS" if v else "FAIL"}  {k}')
        for k, v in det.items():
            print(f'  {"detected" if v else "MISSED  "}  {k}')
        print('ZOS-9 SELFTEST ' + ('PASS' if ok else 'FAIL'))
        sys.exit(0 if ok else 1)
    ok, rep = check(a.spool, a.job)
    text = json.dumps(rep, indent=1, default=str)
    if a.report:
        Path(a.report).write_text(text + '\n')
    print(text)
    print(f'{JOBS[a.job][0]} ' + rep['state'])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
