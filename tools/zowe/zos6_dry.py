#!/usr/bin/env python3
"""ZOS-6 PACZ6DRY: the batch / TSD dry runs of the ZOS-6 build PACZ6D (docs/zos6-production-design.md) - the deck and
its fail-closed comparator. One step list (STEPS) drives both. Read-only on z/OS (the job only runs PGM=PACZ6D).

Usage: zos6_dry.py --job N --deck OUT.jcl        write job N's deck (prefix @@HLQ@@.PACMAN)
       zos6_dry.py --selftest                    the comparator against the frozen oracle 310 blocks + injected faults
       zos6_dry.py --job N SPOOLDIR [--report F] compare job N's SYSOUT step by step; exit 0 PASS, 1 FAIL
Two jobs (user decision 2026-10-19, only to stay below the site S722 output limit): PACZ6DR1 = EVERY + NORMAL
COALESCED; PACZ6DR2 = RPCLRPU at both speeds + FAST COALESCED + the FAST batch freeze.

Expected output (never derived from the run):
- EVERY steps (no PARM column 26): the frozen oracle 310 block of the same run (RTB7 batch, RTT2 TSD), line for line
  (right-stripped), and - TSD - the ref_rt frames byte for byte;
- COALESCED steps (column 26 C): tests/ref_rt.py with present='C' (and, SOUND Y + ALARM(PATTERN), tests/ref_s2.py
  patterns with the skipped quanta); BAT steps: ref_rt.simulate.
TSD SYSOUT is parsed fail-closed: every `TSD FRAME LENnnnn` must be followed by hex lines holding exactly nnnn bytes,
every line must be a known TSX / TSD form or an end line, nothing may be missing, extra or malformed. A TSD step
passes only when frames (count, order, bytes), the TSX transport lines and the end lines all equal the expectation.
"""
import argparse
import gzip
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests'), str(R / 'tools')]
import ref_rt  # noqa: E402
import ref_s2  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
from ref_snap import Log  # noqa: E402

LOAD = 'PACZ6D'
NORMAL, FAST = 150, 125
GOVER = ['D'] + ['.'] * 299                     # AI2 3: the game is lost on a coalesced quantum (tests section 22)


def cards_of(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


def split_cfg(lines):
    return (lines[0].rstrip()[:5], lines[1:]) if lines and lines[0][:1] == 'A' else ('AI1 1', lines)


def tsd_parm(cfg, cv, sound, rules, speed, alarm, present):
    """PARM columns: 1-11 'TSD <cfg>', 12-17 NYYPG4 (COLOR N, HILITE Y, ANIM Y, REDRAW P, GLYPHS G, SCALE 4), 18 canvas,
    19 R (REALTIME), 20 SOUND, 21 RULES, 22-23 level 01, 24 SPEED, 25 ALARM, 26 PRESENT."""
    p = ('TSD ' + cfg).ljust(11) + 'NYYPG4' + cv + 'R' + sound + rules + '01' + speed + alarm + present
    assert len(p) == 26
    return p


def bat_parm(rules, speed, present):
    p = 'BAT'.ljust(18) + 'R' + ' ' + rules + '01' + speed + 'S' + present
    assert len(p) == 26
    return p


def _steps():
    still_cfg, still = split_cfg(cards_of('rtcases', 'RTSTILL'))
    out = [
        # EVERY regression: the very RTB7 / RTT2 steps of the GP2 deck (oracle 310)
        dict(step='E1', kind='BAT', parm='BAT'.ljust(18) + 'R', cards=cards_of('rtcases', 'RTSTILL'), oracle='RTB7',
             per=NORMAL, freeze=10),
        dict(step='E2', kind='TSD', parm=('TSD ' + still_cfg).ljust(11) + 'NYYPG4WR', cards=still, cfg=still_cfg,
             canvas='W', oracle='RTT2', per=NORMAL, present=None),
    ]
    for sp, per, tag in (('N', NORMAL, 'N'), ('F', FAST, 'F')):
        out.append(dict(step=f'{tag}1', kind='TSD', parm=tsd_parm(still_cfg, 'W', 'Y', 'C', sp, 'P', 'C'),
                        cards=still, cfg=still_cfg, canvas='W', per=per, present='C', bells=True))
        for k, case in ((2, 'RTPAUSE'), (3, 'RTPRE')):
            cfg, cs = split_cfg(cards_of('rtcases', case))
            out.append(dict(step=f'{tag}{k}', kind='TSD', parm=tsd_parm(cfg, 'W', 'N', 'C', sp, 'S', 'C'), cards=cs,
                            cfg=cfg, canvas='W', per=per, present='C'))
        out.append(dict(step=f'{tag}4', kind='TSD', parm=tsd_parm('AI2 3', 'W', 'N', 'C', sp, 'S', 'C'), cards=GOVER,
                        cfg='AI2 3', canvas='W', per=per, present='C', lost_on_skip=True))
        rcfg, rcs = split_cfg(cards_of('rpcases', 'RPCLRPU'))
        out.append(dict(step=f'{tag}5', kind='TSD', parm=tsd_parm(rcfg, 'T', 'N', 'A', sp, 'S', 'C'), cards=rcs,
                        cfg=rcfg, canvas='T', per=per, present='C', arcade=True))
    out.append(dict(step='Z1', kind='BAT', parm=bat_parm('C', 'F', 'C'), cards=cards_of('rtcases', 'RTSTILL'),
                    per=FAST, freeze=12))
    return out


STEPS = _steps()
JOBS = {1: ['E1', 'E2', 'N1', 'N2', 'N3', 'N4'], 2: ['N5', 'F5', 'F1', 'F2', 'F3', 'F4', 'Z1']}
assert sorted(sum(JOBS.values(), [])) == sorted(s['step'] for s in STEPS)


def job_steps(n):
    by = {s['step']: s for s in STEPS}
    return [by[x] for x in JOBS[n]]


# --- expectations ------------------------------------------------------------------------------------------------
def oracle_block(name):
    import zos_equiv as ZE
    o = json.load(gzip.open(R / 'tests/oracle20/310-PACBLGP2.json.gz'))
    anc = ZE.anchors(o, {'PACMAIN'})
    s, b = o['stream'], anc[name]
    x = s[b:min([v for v in anc.values() if v > b], default=len(s))]
    while x and x[-1] == '':
        x.pop()
    return [l.rstrip() for l in x]


def model(st):
    """-> dict(frames, full set, out (end lines), qs, kinds) or for BAT dict(lines)."""
    if st['kind'] == 'BAT':
        return {'lines': [l.rstrip() for l in ref_rt.simulate(st['cards'], per=st['per'])]}
    full = set()
    real = gx.full

    def tagged(*a, **kw):
        b = real(*a, **kw)
        full.add(b)
        return b
    log = Log()
    log.kinds = []
    kw = {}
    if st.get('arcade'):
        import ref_gp2 as L
        kw = dict(mk_game=lambda ai, n: L.Level(ai, n, 'R', 1), mk_ctl=L.LevelRT, hs=None)
    gx.full = tagged
    try:
        out, fr = ref_rt.tsd([st['cfg']] + st['cards'], st['canvas'], snap=log, per=st['per'],
                             present=st.get('present'), **kw)
    finally:
        gx.full = real
    frames = list(fr)
    if st.get('bells'):
        frames, _ = ref_s2.patterns(frames, log, 'Y', 'R', st['per'], skips=fr.skips)
    return {'frames': frames, 'plain': list(fr), 'full': full, 'out': out, 'qs': list(fr.qs), 'kinds': log.kinds,
            'skips': list(fr.skips)}


SWITCH = {'W': 'TSX SWITCH 7E 120X027', 'T': 'TSX SWITCH 7E 080X043', 'D': 'TSX SWITCH F5 080X024'}


def full_at(m):
    """Indices of the full-screen writes, from the UNMODIFIED model frames (a bell sets the WCC alarm bit of a frame,
    which changes its bytes but not its transport; bell-only writes appended by ref_s2 are never full)."""
    return {k for k, f in enumerate(m['plain']) if f in m['full']}


def render_tsd(m, canvas):
    """The SYSOUT PACPLAT TSD would print for a model (used by the self-test and the line estimate)."""
    lines, first, fa = [SWITCH[canvas]], True, full_at(m)
    cmd = '7E' if canvas != 'D' else 'F5'
    for k, f in enumerate(m['frames']):
        if k in fa:
            lines.append('TSX FULL FIRST' if first else f'TSX FULL {cmd}')
            first = False
        lines.append(f'TSD FRAME LEN{len(f):04d}')
        h = f.hex().upper()
        lines += ['TSD ' + h[i:i + 64] for i in range(0, len(h), 64)]
    return lines + list(m['out'])


# --- the fail-closed parser ----------------------------------------------------------------------------------------
class Bad(Exception):
    pass


def parse_tsd(lines):
    """-> (tsx lines in order with the frame index they precede, frames, end lines). Raises Bad on any malformation."""
    tsx, frames, end, i = [], [], [], 0
    while i < len(lines):
        l = lines[i].rstrip()
        if l.startswith('TSX '):
            if end:
                raise Bad(f'line {i + 1}: TSX after the end lines')
            if not re.fullmatch(r'TSX (SWITCH (7E|F5) \d{3}X\d{3}|FULL (FIRST|7E|F5))', l):
                raise Bad(f'line {i + 1}: unknown TSX form {l!r}')
            tsx.append((len(frames), l))
            i += 1
            continue
        m = re.fullmatch(r'TSD FRAME LEN(\d{4})', l)
        if m:
            if end:
                raise Bad(f'line {i + 1}: a frame after the end lines')
            n, h = int(m.group(1)), ''
            i += 1
            while i < len(lines) and lines[i].startswith('TSD ') and not lines[i].startswith('TSD FRAME'):
                x = lines[i].rstrip()[4:]
                if not re.fullmatch(r'[0-9A-F]{2,64}', x) or len(x) % 2:
                    raise Bad(f'line {i + 1}: malformed hex {x!r}')
                h += x
                i += 1
            if len(h) != 2 * n:
                raise Bad(f'frame {len(frames)}: LEN{n:04d} but {len(h) // 2} bytes of hex')
            frames.append(bytes.fromhex(h))
            continue
        if l.startswith('TSD') or l.startswith('TSX'):
            raise Bad(f'line {i + 1}: unknown TSD form {l!r}')
        end.append(l)
        i += 1
    while end and end[-1] == '':
        end.pop()
    return tsx, frames, end


def expected_tsx(m, canvas):
    out, first, fa = [(0, SWITCH[canvas])], True, full_at(m)
    cmd = '7E' if canvas != 'D' else 'F5'
    for k, f in enumerate(m['frames']):
        if k in fa:
            out.append((k, 'TSX FULL FIRST' if first else f'TSX FULL {cmd}'))
            first = False
    return out


def compare_tsd(lines, st, m):
    """-> (ok, findings)."""
    msgs = []
    try:
        tsx, frames, end = parse_tsd(lines)
    except Bad as ex:
        return False, [f'PARSE: {ex}']
    if len(frames) != len(m['frames']):
        msgs.append(f'frames: {len(frames)} on z/OS, {len(m["frames"])} in the model')
    k = next((j for j, (a, b) in enumerate(zip(frames, m['frames'])) if a != b), None)
    if k is not None:
        msgs.append(f'frame {k} differs (z/OS {len(frames[k])} bytes, model {len(m["frames"][k])})')
    if tsx != expected_tsx(m, st['canvas']):
        msgs.append(f'TSX lines {tsx[:4]} != {expected_tsx(m, st["canvas"])[:4]}')
    if end != [x.rstrip() for x in m['out']]:
        msgs.append(f'end lines {end} != {m["out"]}')
    return not msgs, msgs


def compare_lines(got, want):
    got = [l.rstrip() for l in got]
    while got and got[-1] == '':
        got.pop()
    if got == want:
        return True, []
    k = next((j for j, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
    return False, [f'line {k + 1}: z/OS {got[k] if k < len(got) else "<missing>"!r} / expected '
                   f'{want[k] if k < len(want) else "<missing>"!r} ({len(got)} / {len(want)} lines)']


def freeze_runs(lines):
    runs, cur = [], 0
    for l in lines + ['Q']:
        m = re.match(r'Q\d{7} IN=.{8} K=(.)', l)
        if m and m.group(1) == 'F':
            cur += 1
        elif m or l == 'Q':
            if cur:
                runs.append(cur)
            cur = 0
    return runs


def facts(st, m):
    """The coverage facts a step demonstrates (from the expectation it matched)."""
    f = {}
    if st['kind'] == 'BAT':
        return f
    qi = [j for j, k in enumerate(m['kinds']) if k in ('Q', 'P')]
    qs = [m['qs'][j] for j in qi]
    f['quantum_frames'] = len(qs)
    f['strides'] = sorted({m['qs'][b] - m['qs'][a] for a, b in zip(qi, qi[1:]) if b == a + 1})   # inside a segment
    f['segments'] = 1 + sum(1 for a, b in zip(qi, qi[1:]) if b != a + 1)
    f['strictly_increasing'] = all(a < b for a, b in zip(qs, qs[1:]))
    f['skipped_quanta'] = sum(m['skips'])
    if st.get('lost_on_skip'):
        last = int(m['out'][-1].split()[1])
        f['end'] = m['out'][0]
        f['deciding_quantum'] = last
        f['deciding_quantum_presented'] = last in qs
    if st.get('bells'):
        f['alarm_frames'] = sum(1 for a, b in zip(m['frames'], m['plain'] + [b''] * 99) if a[:1] != b[:1])
        f['bell_only_writes'] = len(m['frames']) - len(m['plain'])
    return f


# --- the deck -----------------------------------------------------------------------------------------------------
def deck(n, pfx='@@HLQ@@.PACMAN'):
    import make_deck as md
    import zos_target as zt
    if not zt._md:
        zt.apply(md, pfx)
    zt.JOBNAME = None
    out = zt.job_card(f'PACZ6DR{n}', f'PACMAN ZOS6 DRY{n}')
    for st in job_steps(n):
        out += zt.run_step(st['step'], pfx, LOAD, '\n'.join(st['cards']) + '\n', parm=st['parm'])
    assert out.count(f'PGM={LOAD}') == len(JOBS[n]) and 'PGM=PACMAIN' not in out and 'DELETE' not in out
    return out


def estimate(j):
    n = 0
    for st in job_steps(j):
        m = model(st)
        n += len(m['lines']) if st['kind'] == 'BAT' else len(render_tsd(m, st['canvas']))
    return n


# --- check of a real job --------------------------------------------------------------------------------------------
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
        if st['kind'] == 'BAT':
            m = model(st)
            g1, w1 = compare_lines(r['lines'], m['lines'])
            res['model'] = 'exact' if g1 else w1
            good &= g1
            if st.get('oracle'):
                g2, w2 = compare_lines(r['lines'], oracle_block(st['oracle']))
                res['oracle310'] = 'exact' if g2 else w2
                good &= g2
            fr = freeze_runs(r['lines'])
            res['freeze_runs'] = fr
            good &= bool(fr) and set(fr) == {st['freeze']}
        else:
            m = model(st)
            g, w = compare_tsd(r['lines'], st, m)
            res['model'] = 'exact' if g else w
            good &= g
            if st.get('oracle'):
                g2, w2 = compare_lines(r['lines'], oracle_block(st['oracle']))
                res['oracle310'] = 'exact' if g2 else w2
                good &= g2
            res['facts'] = facts(st, m)
        res['state'] = 'PASS' if good else 'FAIL'
        ok &= good
        rep['steps'][st['step']] = res
    rep['state'] = 'PASS' if ok else 'FAIL'
    return ok, rep


# --- self-test against the frozen oracle and injected faults ------------------------------------------------------------
def selftest():
    e1, e2 = STEPS[0], STEPS[1]
    o7, o2 = oracle_block('RTB7'), oracle_block('RTT2')
    m1, m2 = model(e1), model(e2)
    res = {}
    res['RTB7 oracle = BAT model'] = compare_lines(o7, m1['lines'])[0]
    res['RTB7 freeze runs all exactly 10 (RTSTILL: 2 freezes, the last death ends the game)'] = freeze_runs(o7) == [10, 10]
    res['RTT2 oracle parses, = model frames / TSX / end lines'] = compare_tsd(o2, e2, m2)[0]
    tsx, frames, end = parse_tsd(o2)
    res['RTT2 frame boundaries'] = (len(frames) == len(m2['frames']) and
                                    sum(1 for l in o2 if l.startswith('TSD FRAME')) == len(frames))
    res['RTT2 render(model) = oracle text'] = render_tsd(m2, 'W') == o2
    # injected faults: each must be detected
    bad = {}
    k = next(i for i, l in enumerate(o2) if l.startswith('TSD ') and not l.startswith('TSD FRAME') and len(l) > 20)
    flip = o2[:k] + [o2[k][:10] + ('0' if o2[k][10] != '0' else '1') + o2[k][11:]] + o2[k + 1:]
    bad['one hex digit changed'] = flip
    bad['one hex line dropped'] = o2[:k] + o2[k + 1:]
    j = [i for i, l in enumerate(o2) if l.startswith('TSD FRAME')][5]
    nxt = next(i for i in range(j + 1, len(o2)) if not o2[i].startswith('TSD ') or o2[i].startswith('TSD FRAME'))
    bad['one whole frame dropped'] = o2[:j] + o2[nxt:]
    bad['one frame duplicated'] = o2[:nxt] + o2[j:nxt] + o2[nxt:]
    bad['malformed hex'] = o2[:k] + ['TSD ' + 'G' * 64] + o2[k + 1:]
    bad['unknown TSD form'] = o2[:k] + ['TSD SOMETHING'] + o2[k:]
    bad['TSX line missing'] = [l for l in o2 if l != 'TSX FULL FIRST']
    bad['end line changed'] = o2[:-1] + ['QUANTA 0000118']
    bad['end lines missing'] = o2[:-5]
    bad['frame after the end lines'] = o2 + o2[j:nxt]
    det = {}
    for why, ls in bad.items():
        det[why] = not compare_tsd(ls, e2, m2)[0]
    res['all injected TSD faults detected'] = all(det.values())
    lb = o7[:20] + [o7[20] + 'X'] + o7[21:]
    res['BAT line change detected'] = not compare_lines(lb, m1['lines'])[0]
    res['BAT truncation detected'] = not compare_lines(o7[:-3], m1['lines'])[0]
    # bell case (N1): the full-screen transport comes from the unmodified frames; alarm-bit / transport faults detected
    n1 = next(s for s in STEPS if s['step'] == 'N1')
    mb = model(n1)
    tx = expected_tsx(mb, 'W')
    res['N1 transport: FULL FIRST before frame 0 (an alarm frame), FULL 7E before the end screen'] = \
        tx[:2] == [(0, 'TSX SWITCH 7E 120X027'), (0, 'TSX FULL FIRST')] and mb['frames'][0][:1] != mb['plain'][0][:1] \
        and len(tx) == 1 + len(full_at(mb))
    rb = render_tsd(mb, 'W')
    ka = next(k for k, (a, b) in enumerate(zip(mb['frames'], mb['plain'])) if a != b and k > 0)
    fl = [i for i, l in enumerate(rb) if l.startswith('TSD FRAME')]
    hb = rb[fl[ka] + 1]
    wcc = '%02X' % (int(hb[4:6], 16) & ~0x04)
    belf = {'N1 alarm bit removed from one frame': rb[:fl[ka] + 1] + ['TSD ' + wcc + hb[6:]] + rb[fl[ka] + 2:],
            'N1 TSX FULL FIRST missing': [l for l in rb if l != 'TSX FULL FIRST'],
            'N1 TSX FULL moved one frame': [l for l in rb if l != 'TSX FULL 7E'][:fl[-1]] + ['TSX FULL 7E'] + \
            [l for l in rb if l != 'TSX FULL 7E'][fl[-1]:],
            'N1 bell-only write dropped': rb[:fl[-1]] + rb[fl[-1] + 2:]}
    for why, ls in belf.items():
        det[why] = not compare_tsd(ls, n1, mb)[0]
    res['all injected bell-case faults detected'] = all(det[w] for w in belf)
    # the COALESCED expectations render / parse round trip (the comparator does not depend on EVERY shapes)
    for st in STEPS[2:]:
        m = model(st)
        if st['kind'] == 'TSD':
            res[f'{st["step"]} model render parses back exactly'] = compare_tsd(render_tsd(m, st['canvas']), st, m)[0]
            f = facts(st, m)
            res[f'{st["step"]} grid'] = f['strictly_increasing'] and set(f['strides']) <= \
                {1, 2 if st['per'] == NORMAL else 3} and (2 if st['per'] == NORMAL else 3) in f['strides']
            if st.get('lost_on_skip'):
                res[f'{st["step"]} LOST on a skipped quantum'] = f['end'] == 'LOST' and not \
                    f['deciding_quantum_presented']
        else:
            res[f'{st["step"]} BAT freeze runs {st["freeze"]}'] = set(freeze_runs(m['lines'])) == {st['freeze']}
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
    print(f'PACZ6DR{a.job} ' + rep['state'])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
