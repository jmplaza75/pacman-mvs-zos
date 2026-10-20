#!/usr/bin/env python3
"""ZOS-7 PACZ7DR1 / PACZ7DR2: the ARCADE batch / TSD dry runs on the installed ZOS-6 test member PACZ6D (no rebuild;
docs/zos7-design.md section F, decision D5) - the decks and their fail-closed comparator. Read-only on z/OS (the jobs
only run PGM=PACZ6D; no PACHS DD: the high score is never read or written by a dry run).

Usage: zos7_dry.py --job N --deck OUT.jcl        write job N's deck (prefix @@HLQ@@.PACMAN)
       zos7_dry.py --selftest                    expectations vs the frozen oracle 311 block + injected faults
       zos7_dry.py --job N SPOOLDIR [--report F] compare job N's SYSOUT step by step; exit 0 PASS, 1 FAIL
The TSD parser / comparator / renderer are the frozen ZOS-6 ones (tools/zowe/zos6_dry.py parse_tsd, compare_tsd,
render_tsd, compare_lines), reused unchanged.
Steps (TSD, wide 120 x 27 unless noted; SOUND N; ALARM S):
- E3: oracle 311 G3R7 = GP23 run 7 (G2RPAU, ARCADE REALTIME, pause), PRESENT(EVERY) - its PARM exactly (no columns
  22-26): the oracle block line for line and the EVERY model byte for byte (Z4 left ARCADE EVERY output unchanged on
  z/OS);
- N6 / F6 RPLOST (final death), N7 RPDCLR (deaths + level clear) / F7 S2XLC (level clear + extra life, LEVEL 12),
  N8 G2RXD (LEVEL 13, deaths + extra life) / F8 S2XLD (LEVEL 13, death + extra life), N9 / F9 RTGPA (ghost chain),
  NL2 / FL2 the L2 / L3 live scenario (LEVEL 2, canonical placement): ARCADE REALTIME PRESENT(COALESCED) at NORMAL /
  FAST = tests/ref_rt.py present='C' + tests/ref_gp2.py; the final-death writes of a LOST game (decision D1:
  6 NORMAL / 7 FAST) counted as a fact;
- T1: the L1 scenario (tests/gp2live/LIVEB.txt, ARCADE TURN, LEVEL 13, ANIM N, PRESENT(COALESCED)) = the
  ref_gx_screen TURN model.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests'), str(R / 'tools')]
import ref_rt  # noqa: E402
import ref_gp2 as L  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
from ref_snap import Log  # noqa: E402
import zos6_dry as D6  # noqa: E402
import zos7_scen as SC  # noqa: E402

LOAD = 'PACZ6D'
NORMAL, FAST = 150, 125
FINAL_DEATH = {NORMAL: 6, FAST: 7}
ORACLE311 = R / 'tests/oracle20/311-PACBLG23.json.gz'


def cards_of(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


def parm(cfg, cv, play, prof, level, speed, present):
    """PARM: 1-11 'TSD <cfg>', 12-17 profile (COLOR HILITE ANIM REDRAW GLYPHS SCALE), 18 canvas, 19 play, 20 SOUND N,
    21 RULES A, 22-23 start level, 24 SPEED, 25 ALARM S, 26 PRESENT."""
    p = ('TSD ' + cfg).ljust(11) + prof + cv + play + 'N' + 'A' + level + speed + 'S' + present
    assert len(p) == 26
    return p


def _steps():
    cfg7, c7 = D6.split_cfg(cards_of('gp2cases', 'G2RPAU'))
    out = [dict(step='E3', kind='TSD', play='R', parm=('TSD ' + cfg7).ljust(11) + 'NYYPG4' + 'W' + 'R' + 'N' + 'A',
                cards=c7, cfg=cfg7, canvas='W', per=NORMAL, start=1, present=None, oracle=('311', 'G3R7'))]
    # NORMAL: RPDCLR (deaths + a level clear), G2RXD (deaths + the extra life). Their cards are NORMAL-timed (at FAST
    # both end LOST before the event), so FAST uses the FAST-designed S2 cases of the same events (oracle 308 S2_TSD):
    # S2XLC (level clear + extra life, start 12) and S2XLD (death + extra life, start 13).
    rt = {'N': [('6', 'rpcases', 'RPLOST', 1), ('7', 'rpcases', 'RPDCLR', 1), ('8', 'gp2cases', 'G2RXD', 13),
                ('9', 'gpcases', 'RTGPA', 1)],
          'F': [('6', 'rpcases', 'RPLOST', 1), ('7', 's2cases', 'S2XLC', 12), ('8', 's2cases', 'S2XLD', 13),
                ('9', 'gpcases', 'RTGPA', 1)]}
    for sp, per, tag in (('N', NORMAL, 'N'), ('F', FAST, 'F')):
        for k, d, c, lv in rt[sp]:
            cfg, cs = D6.split_cfg(cards_of(d, c))
            out.append(dict(step=f'{tag}{k}', kind='TSD', play='R', parm=parm(cfg, 'W', 'R', 'NYYPG4', f'{lv:02d}', sp,
                                                                              'C'),
                            cards=cs, cfg=cfg, canvas='W', per=per, start=lv, present='C'))
        out.append(dict(step=f'{tag}L2', kind='TSD', play='R', parm=parm(SC.CFG, 'W', 'R', 'NYYPG4', '02', sp, 'C'),
                        cards=SC.cards(per), cfg=SC.CFG, canvas='W', per=per, start=SC.START, present='C',
                        scenario=True))
    lb = SC.liveb()
    out.append(dict(step='T1', kind='TSD', play='T', parm=parm(SC.CFG, 'W', 'T', 'NYNPG4', '13', 'N', 'C'),
                    cards=lb[1:], cfg=lb[0], canvas='W', per=NORMAL, start=13, present='C'))
    return out


STEPS = _steps()
JOBS = {1: ['E3', 'N6', 'F6', 'N7', 'F7'], 2: ['N8', 'F8', 'N9', 'F9', 'NL2', 'FL2', 'T1']}
assert sorted(sum(JOBS.values(), [])) == sorted(s['step'] for s in STEPS)


def job_steps(n):
    by = {s['step']: s for s in STEPS}
    return [by[x] for x in JOBS[n]]


def oracle_block(which, name):
    import zos_equiv as ZE
    o = json.load(gzip.open(ORACLE311 if which == '311' else R / f'tests/oracle20/{which}.json.gz'))
    anc = ZE.anchors(o, {'PACMAIN'})
    s, b = o['stream'], anc[name]
    x = s[b:min([v for v in anc.values() if v > b], default=len(s))]
    while x and x[-1] == '':
        x.pop()
    return [l.rstrip() for l in x]


def model(st):
    """-> dict(frames, plain, full, out (end lines), qs, kinds, skips) as zos6_dry.model."""
    full, real = set(), gx.full

    def tagged(*a, **kw):
        b = real(*a, **kw)
        full.add(b)
        return b
    log = Log()
    log.kinds = []
    gx.full = tagged
    try:
        if st['play'] == 'T':
            fs = gx.frames('LIVEB', True, False, 'P', 'G', '4', st['canvas'], snap=log,
                           mk=lambda ai, n: L.Level(ai, n, 'T', st['start']), d='gp2live', hs=None)
            out = L.simulate([st['cfg']] + st['cards'], start=st['start'])[-7:]
            frames = list(fs)
            qs, skips = [None] * len(frames), [0] * len(frames)
        else:
            out, fr = ref_rt.tsd([st['cfg']] + st['cards'], st['canvas'], snap=log, per=st['per'],
                                 present=st['present'], mk_game=lambda ai, n: L.Level(ai, n, 'R', st['start']),
                                 mk_ctl=L.LevelRT, hs=None)
            frames, qs, skips = list(fr), list(fr.qs), list(fr.skips)
    finally:
        gx.full = real
    return {'frames': frames, 'plain': list(frames), 'full': full, 'out': out, 'qs': qs, 'kinds': log.kinds,
            'skips': skips}


def events(st):
    """The ARCADE events of a REALTIME step from the model game (event flags D death, C level clear, X extra life, and
    ghosts eaten) -> set of {'D', 'C', 'X', 'G'}."""
    seen = set()

    class G(L.Level):
        def turn(self, *a, **kw):
            eat = self.eaten
            r = super().turn(*a, **kw)
            seen.update(f for f in 'DCX' if f in self.evf)
            if self.eaten != eat:
                seen.add('G')
            return r
    ref_rt.tsd([st['cfg']] + st['cards'], st['canvas'], per=st['per'], present=st['present'],
               mk_game=lambda ai, n: G(ai, n, 'R', st['start']), mk_ctl=L.LevelRT, hs=None)
    return seen


def facts(st, m):
    f = {'frames': len(m['frames']), 'end': m['out'][0]}
    if st['play'] == 'T':
        return f
    qi = [j for j, k in enumerate(m['kinds']) if k in ('Q', 'P') and m['qs'][j] is not None]
    fd = [j for j, k in enumerate(m['kinds']) if k in ('Q', 'P') and m['qs'][j] is None]
    f['quantum_frames'] = len(qi)
    f['strides'] = sorted({m['qs'][b] - m['qs'][a] for a, b in zip(qi, qi[1:]) if b == a + 1})
    f['strictly_increasing'] = all(m['qs'][a] < m['qs'][b] for a, b in zip(qi, qi[1:]))
    f['skipped_quanta'] = sum(m['skips'])
    f['final_death_writes'] = len(fd)
    f['final_death_before_end_screen'] = bool(fd) and fd == list(range(fd[0], fd[-1] + 1)) and \
        fd[-1] == len(m['kinds']) - 2 and m['kinds'][-1] == 'E'
    return f


def deck(n, pfx='@@HLQ@@.PACMAN'):
    import make_deck as md
    import zos_target as zt
    if not zt._md:
        zt.apply(md, pfx)
    zt.JOBNAME = None
    out = zt.job_card(f'PACZ7DR{n}', f'PACMAN ZOS7 DRY{n}')
    for st in job_steps(n):
        out += zt.run_step(st['step'], pfx, LOAD, '\n'.join(st['cards']) + '\n', parm=st['parm'])
    assert out.count(f'PGM={LOAD}') == len(JOBS[n]) and 'PGM=PACMAIN' not in out and 'DELETE' not in out
    assert 'PACHS' not in out and '.DATA' not in out
    return out


def estimate(j):
    return sum(len(D6.render_tsd(model(st), st['canvas'])) for st in job_steps(j))


def check(spool, n):
    import zos_equiv as ZE
    job, names, runs = ZE.zos_runs(spool)
    rep, ok = {'job': job.get('jobid'), 'retcode': job.get('retcode'), 'steps': {}}, True
    if names != JOBS[n]:
        return False, dict(rep, why=f'steps {names} != {JOBS[n]}')
    for st in job_steps(n):
        r = runs[st['step']]
        res = {'pgm': r['pgm'], 'rc': r['rc'], 'extra': r['extra'], 'lines': len(r['lines'])}
        good = r['pgm'] == LOAD and r['rc'] == '0000' and not r['extra']
        if not good:
            res['why'] = ['step: program / RC / extra output']
        m = model(st)
        g, w = D6.compare_tsd(r['lines'], st, m)
        res['model'] = 'exact' if g else w
        good &= g
        if st.get('oracle'):
            g2, w2 = D6.compare_lines(r['lines'], oracle_block(*st['oracle']))
            res['oracle' + st['oracle'][0]] = 'exact' if g2 else w2
            good &= g2
        f = res['facts'] = facts(st, m)
        if st['play'] == 'R' and st['present'] == 'C':
            want = FINAL_DEATH[st['per']] if f['end'] == 'LOST' else 0
            good &= f['final_death_writes'] == want and (not want or f['final_death_before_end_screen'])
        res['state'] = 'PASS' if good else 'FAIL'
        ok &= good
        rep['steps'][st['step']] = res
    rep['state'] = 'PASS' if ok else 'FAIL'
    return ok, rep


def selftest():
    res, det = {}, {}
    e3 = STEPS[0]
    o = oracle_block(*e3['oracle'])
    m3 = model(e3)
    res['E3 oracle 311 G3R7 = the EVERY ARCADE model (frames, TSX, end lines)'] = D6.compare_tsd(o, e3, m3)[0]
    res['E3 render(model) = oracle text'] = D6.render_tsd(m3, 'W') == o
    k = next(i for i, l in enumerate(o) if l.startswith('TSD ') and not l.startswith('TSD FRAME') and len(l) > 20)
    bad = {'one hex digit changed': o[:k] + [o[k][:10] + ('0' if o[k][10] != '0' else '1') + o[k][11:]] + o[k + 1:],
           'one hex line dropped': o[:k] + o[k + 1:], 'end line changed': o[:-1] + ['LEVEL 002'],
           'end lines missing': o[:-8]}
    for why, ls in bad.items():
        det[why] = not D6.compare_tsd(ls, e3, m3)[0]
    for st in STEPS[1:]:
        m = model(st)
        f = facts(st, m)
        rb = D6.render_tsd(m, st['canvas'])
        res[f'{st["step"]} model render parses back exactly'] = D6.compare_tsd(rb, st, m)[0]
        if st['play'] == 'R':
            g = 2 if st['per'] == NORMAL else 3
            res[f'{st["step"]} grid'] = f['strictly_increasing'] and set(f['strides']) <= {1, g} and g in f['strides']
            want = FINAL_DEATH[st['per']] if f['end'] == 'LOST' else 0
            res[f'{st["step"]} final-death writes {want}'] = f['final_death_writes'] == want and \
                (not want or f['final_death_before_end_screen'])
            if want:                              # D1 faults in the final-death sequence are detected
                fl = [i for i, l in enumerate(rb) if l.startswith('TSD FRAME')]
                j = fl[-2]
                nxt = fl[-1]
                det[f'{st["step"]} last final-death frame dropped'] = not D6.compare_tsd(rb[:j] + rb[nxt:], st, m)[0]
                det[f'{st["step"]} last final-death frame duplicated'] = \
                    not D6.compare_tsd(rb[:nxt] + rb[j:nxt] + rb[nxt:], st, m)[0]
        if st.get('scenario'):
            res[f'{st["step"]} scenario outcome = intended'] = SC.intended(SC.outcome(m['out']))
    for per in (NORMAL, FAST):                    # D5: every event at both speeds under COALESCED, + the final death
        cov = set()
        for st in STEPS:
            if st['play'] == 'R' and st['present'] == 'C' and st['per'] == per:
                cov |= events(st)
                if facts(st, model(st))['final_death_writes']:
                    cov.add('FD')
        res[f'T {per}: COALESCED coverage death / level clear / extra life / ghost / final death'] = \
            cov >= {'D', 'C', 'X', 'G', 'FD'}
    res['all injected faults detected'] = all(det.values())
    res['decks: PGM=PACZ6D only, no PACHS / DATA / DELETE'] = all(deck(n) for n in JOBS)
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
        print(f'{a.deck}: {len(JOBS[a.job])} steps, estimated SYSOUT lines {estimate(a.job)}')
        return
    if a.selftest:
        ok, res, det = selftest()
        for k, v in res.items():
            print(f'{"PASS" if v else "FAIL"}  {k}')
        for k, v in det.items():
            print(f'  {"detected" if v else "MISSED  "}  {k}')
        print('COMPARATOR SELFTEST ' + ('PASS' if ok else 'FAIL'))
        sys.exit(0 if ok else 1)
    ok, rep = check(a.spool, a.job)
    text = json.dumps(rep, indent=1, default=str)
    if a.report:
        Path(a.report).write_text(text + '\n')
    print(text)
    print(f'PACZ7DR{a.job} ' + rep['state'])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
