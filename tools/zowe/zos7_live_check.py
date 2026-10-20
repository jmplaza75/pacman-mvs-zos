#!/usr/bin/env python3
"""ZOS-7 ARCADE live postcheck (docs/zos7-design.md, decisions D1-D5 of 2026-10-19). Local, read-only. One case per
trace: L1 (TURN, LEVEL 13), L2 (REALTIME NORMAL) or L3 (REALTIME FAST), all RULES(ARCADE) PRESENT(COALESCED) SOUND(NO).

Usage: zos7_live_check.py --case L1|L2|L3 --trace TRACE --drive-log LOG --hiscore ABSENT|'<80-byte record>'
       [--prefix Z00000.PACMAN]
       exit 0 PASS, 1 FUNCTIONAL FAIL, 2 ENVIRONMENT/TIMING BLOCKED, 3 COVERAGE INCOMPLETE (writes = model, but the
       game did not show the intended events - never PASS)

The frozen ZOS-6 checker (tools/zowe/zos6_live_check.py) and through it the frozen ZOS-5 checker are imported and
reused unchanged: the TN3270E parse with the KRI and the narrow TSO `F1 C3` CONTROL rule (parse6), the BID times,
the AID windows (window), write equality (lcp: write 0 with the clear prefix, full screens 7E / partial F1), the
timing / gates / principal segment / reaction / diagnostics (timing, GATES, STRIDE) and the lateness envelope
diagnostic-only rule under COALESCED. Nothing of ZOS-6 is retuned.
What ZOS-7 adds:
- the ARCADE model: tests/ref_rt.py driven by the GP2 game / controller (tests/ref_gp2.py Level, LevelRT) at the
  start level of the plan, the RP decorations with the high score read from the live DATA state (--hiscore, from the
  read-only precheck: ABSENT = REQ-HSST Z, value 0; a valid record = R) and the end lines = the ARCADE lines + the
  high-score lines of tests/ref_hs.py (LEVEL >= 2: `START LEVEL nn: HIGH SCORE NOT RECORDED` when beaten - nothing is
  ever written, decision D3);
- every game write is one of four classes, each checked on its own (no broad exemption):
  1. COALESCED gameplay writes: quantum writes tied to their logical quantum, strictly increasing, exactly STRIDE
     (2 NORMAL / 3 FAST) apart inside a segment - the ZOS-6 rules unchanged;
  2. the FINAL-DEATH exception (D1): only after the game is logically LOST, only the final death animation, exactly
     6 (NORMAL) / 7 (FAST) writes, consecutive, in the model's order and bytes, right before the end screen, after the
     last gameplay write; outside the stride rule; their timing is reported separately (no gate);
  3. the end screen: exactly one, the last game write;
  4. transport / control records: KRI controls and the narrow TSO F1 C3 records (parse6), never game writes;
- L1 (TURN): one typed command + ENTER per screen (the cards = tests/gp2live/LIVEB.txt exactly), every write = the
  ARCADE TURN TSD model (ref_gx_screen frames with the GP2 TURN game, ANIM N) byte for byte, one write per command;
  no timing gate;
- coverage: the intended outcome of the scenario (L2 / L3: LOST, SCORE 0000510, one ghost eaten, LIVES 0 -
  tools/zowe/zos7_scen.py; L1: QUIT, SCORE 0010780, LIVES 4 (extra life), two fruits) - else COVERAGE INCOMPLETE.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests')]
import zos6_live_check as Z6  # noqa: E402
import ref_rt  # noqa: E402
import ref_gp2 as L  # noqa: E402
import ref_hs as HS  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
from ref_snap import Log  # noqa: E402
import zos7_scen as SC  # noqa: E402
from zos7_drive import PLANS, EXPECT  # noqa: E402

Z5 = Z6.Z5
Fail = Z6.Fail
ms, typed, stats = Z6.ms, Z6.typed, Z6.stats
PASS, BLOCKED, FAILED, INCOMPLETE = Z6.PASS, Z6.BLOCKED, Z6.FAILED, 'COVERAGE INCOMPLETE'
FINAL_DEATH = {150: 6, 125: 7}          # decision D1: the final-death writes of a lost ARCADE REALTIME game
EXPECT_L1 = {'end': 'QUIT', 'score': 10780, 'lives': 4, 'fruits': 2}
DIRS = Z6.DIRS


def hs_state(hiscore, start):
    """--hiscore (the read-only precheck of <prefix>.DATA(HISCORE)) -> (Pds model, Tracker hs tuple)."""
    pds = HS.Pds() if hiscore == 'ABSENT' else HS.Pds({'HISCORE': [hiscore.ljust(80)]})
    st, val, _ = pds.read(('M', 'HISCORE'))
    return pds, (st, val, start)


def hs_lines(hiscore, out, start):
    """The high-score end lines of the game (ref_hs; LEVEL >= 2 never saves) for the ARCADE end lines `out`."""
    pds, _ = hs_state(hiscore, start)
    score, level = HS.final(out)
    return HS.end_lines(pds, ('M', 'HISCORE'), score, level, start)


def act7(p):
    """The gameplay action of an inbound record: a PF / PA key, or the typed text of an ENTER (x, Q, U, D, L, R)."""
    if p[0] == 0x7D:
        t = typed(p)
        return t if t in ('x', 'Q', 'U', 'D', 'L', 'R') else f'ENTER({t})'
    return Z6.AID_ACTION.get(p[0], f'AID {p[0]:02X}')


def _tagging():
    full, real = set(), gx.full

    def tagged(*a, **kw):
        b = real(*a, **kw)
        full.add(b)
        return b
    return full, real, tagged


def model_rt(cards, canvas, per, start, hs, present='C', frt=None, cfg=SC.CFG):
    """The ARCADE REALTIME TSD model (ref_rt + ref_gp2) -> dict as zos6_live_check.model (out = the 8 ARCADE end lines,
    frames, kinds, full, rqs, rins, qs, fc) plus frt / rdy (the converted freeze / READY! quanta)."""
    full, real, tagged = _tagging()
    rqs, rins, ctl = [], [], {}

    class Ctl(L.LevelRT):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            ctl['c'] = self

        def rq(self):
            super().rq()
            rqs.append((self.kind, self.frz))

        def rin(self, kind, d, ch):
            rins.append((kind, d, ch))
            super().rin(kind, d, ch)
    lg = Log()
    lg.kinds = []
    gx.full = tagged
    try:
        out, frames = ref_rt.tsd([cfg] + cards, canvas, snap=lg, mk_game=lambda ai, n: L.Level(ai, n, 'R', start),
                                 mk_ctl=Ctl, hs=hs, per=per, present=present, frt=frt)
    finally:
        gx.full = real
    c = ctl['c']
    return {'out': out, 'frames': list(frames), 'kinds': lg.kinds, 'full': full, 'rqs': rqs, 'rins': rins,
            'qs': list(frames.qs), 'fc': list(frames.cards), 'frt': c.frt, 'rdy': c.rdy}


def model_turn(cards, canvas, start, hs, cfg=SC.CFG):
    """The ARCADE TURN TSD model of L1 (ANIM N, the scaled GRAPHIC profile) -> dict(out, frames, kinds, full)."""
    if [cfg] + cards != SC.liveb():
        raise Fail('L1: the typed commands are not the cards of tests/gp2live/LIVEB.txt')
    full, real, tagged = _tagging()
    lg = Log()
    lg.kinds = []
    gx.full = tagged
    try:
        fs = gx.frames('LIVEB', True, False, 'P', 'G', '4', canvas, snap=lg,
                       mk=lambda ai, n: L.Level(ai, n, 'T', start), d='gp2live', hs=hs)
    finally:
        gx.full = real
    out = L.simulate([cfg] + cards, start=start)[-7:]
    return {'out': out, 'frames': list(fs), 'kinds': lg.kinds, 'full': full}


def place(live, aids, chars, wt, bid_t, bid_lat, T, canvas, fcmd, m, run_model, frt=None, case='', final=None):
    """zos6_live_check.place (the bounded, backtracking AID placement inside the ZOS-6 windows, unchanged rules) on the
    ARCADE model `run_model(cards, frt)`; COALESCED only. -> (slots, windows, final model) or raises Fail."""
    memo, worst = {}, [(-1, None)]

    def run(cards):
        key = tuple(cards)
        if key not in memo:
            memo[key] = run_model(cards, frt)
        return memo[key]

    def rec(n, slots, wins, mod):
        if n == len(aids):
            k = Z6.lcp(live, mod['frames'], mod['full'], fcmd)
            writes_ok = k == len(live) and len(mod['frames']) == len(live)
            ok = writes_ok and (final is None or final(mod))
            if not ok and n >= worst[0][0]:
                worst[0] = (n, f'{case}: end lines not found in line mode' if writes_ok else
                            f'{case}: game write {k} differs from the model (live {len(live)} writes, model '
                            f'{len(mod["frames"])})')
            return (slots, wins, mod) if ok else None
        lo, hi = Z6.window(ms(aids[n][2]), wt, bid_t, bid_lat, T, slots[-1] if slots else 1, m, mod['fc'], 'C',
                           mod['kinds'])
        if lo > hi:
            if n >= worst[0][0]:
                worst[0] = (n, f'{case}: gameplay AID {n + 1} has no permitted quantum (order / window)')
            return None
        for j in range(lo, hi + 1):
            cand = run(Z6.cards_for(m, slots + [j], chars[:n + 1]))
            k = Z6.lcp(live, cand['frames'], cand['full'], fcmd)
            if n + 1 < len(aids):
                nlo = Z6.window(ms(aids[n + 1][2]), wt, bid_t, bid_lat, T, j, m, cand['fc'], 'C', cand['kinds'])[0]
                want = min(len(live), next((w for w, c in enumerate(cand['fc']) if c >= nlo), len(cand['frames'])))
            else:
                want = len(live)
            if k >= want:
                r = rec(n + 1, slots + [j], wins + [(lo, hi)], cand)
                if r:
                    return r
        if n >= worst[0][0]:
            worst[0] = (n, f'{case}: gameplay AID {n + 1} does not match the model at any permitted quantum '
                           f'{lo}..{hi} (it is not moved further)')
        return None
    r = rec(0, [], [], run(['.'] * m))
    if r is None:
        raise Fail(worst[0][1] or f'{case}: game writes differ from the model at every permitted placement')
    return r


def classify(kinds, qs, end):
    """-> (gameplay quantum writes, final-death writes, end-screen index) of a model run, or raises Fail. The
    final-death writes are the model's quantum frames without a logical quantum (PACDISP FINAL-DEATH): allowed only in
    a LOST game, consecutive, after every gameplay write and immediately before the one end screen, which is the last
    write."""
    qi = [j for j, k in enumerate(kinds) if k in ('Q', 'P') and qs[j] is not None]
    fd = [j for j, k in enumerate(kinds) if k in ('Q', 'P') and qs[j] is None]
    ends = [j for j, k in enumerate(kinds) if k == 'E']
    if len(ends) != 1 or ends[0] != len(kinds) - 1:
        raise Fail(f'end screen: {len(ends)} end writes, not exactly one last write')
    if fd:
        if end != 'LOST':
            raise Fail(f'{len(fd)} quantum frames without a logical quantum in a game that ended {end} (only the final '
                       'death of a LOST game may have them)')
        if fd != list(range(fd[0], fd[-1] + 1)) or fd[-1] != ends[0] - 1 or (qi and qi[-1] > fd[0]):
            raise Fail(f'final-death writes {fd} not consecutive right before the end screen {ends[0]}')
    return qi, fd, ends[0]


def check(text, log_lines, case, hiscore, prefix='Z00000.PACMAN', plan=None):
    """-> report dict (state PASS / BLOCKED / COVERAGE INCOMPLETE) or raises Fail (FUNCTIONAL FAIL)."""
    plan = plan or PLANS[case]
    T, start, cfg = plan['T'], plan['start'], plan['cfg']
    turn = plan['play'] == 'T'

    def planned(category=None):
        return [(c, a) for c, a in plan['steps'] if c not in ('wait', 'expect') and category in (None, c)]
    rep = {'case': case, 'T': T, 'blocked': [], 'stop': False, 'present': plan.get('present', 'C'), 'start': start,
           'hiscore': hiscore}
    if 'PRESENT(COALESCED)' not in plan['kw'].split():
        raise Fail(f'{case}: the plan does not request PRESENT(COALESCED) explicitly')
    t = Z6.parse6(text)
    ev, starts = t['ev'], t['starts']
    rep.update(controls=t['controls'], tso_controls=t['tso_controls'], funcs=t['funcs'])
    if len(starts) != 1:
        raise Fail(f'{case}: {len(starts)} games in the trace (exactly one expected)')
    if Z5.CR not in t['funcs']:
        raise Fail(f'{case}: CONTENTION-RESOLUTION not negotiated (the accepted ZOS-5 profile)')
    s0 = starts[0]
    log = [json.loads(x) for x in log_lines if x.strip()]
    bad = [x for x in log if x.get('result') != 'ok']
    if bad:
        raise Fail(f'{case}: driver action not successful: {bad[0]}')
    for x in log:
        if not (x.get('wait_start', 0) <= x.get('unlocked', -1) <= x.get('sent', -1)) or \
                x.get('requested', 1e18) > x['sent']:
            raise Fail(f'{case}: driver log entry {x.get("ordinal")} has inconsistent timestamps')
    if [x.get('ordinal') for x in log] != list(range(1, len(log) + 1)) or \
            any(a['sent'] > b['sent'] for a, b in zip(log, log[1:])):
        raise Fail(f'{case}: driver log ordinals / send order inconsistent')
    if [(x['category'], x['action']) for x in log] != planned():
        raise Fail(f'{case}: driver log != plan')
    pre = [e for e in ev[:s0] if e[1] == '>']
    if len(pre) != 2 or typed(pre[0][3]) != f"EXEC '{prefix}.CLIST(PACMAN)' '{plan['kw']}'" or \
            pre[1][3][0] != 0x7D or typed(pre[1][3]):
        raise Fail(f'{case}: transition inputs {[act7(e[3]) for e in pre]} are not EXEC + ENTER')
    G = ev[s0:]
    host = [e for e in G if e[1] == '<']
    if host[1][3] != Z5.QUERY:
        raise Fail(f'{case}: no Read Partition Query after the switch')
    k1, k2 = G.index(host[1]), G.index(host[2])
    inb = [e for e in G[k1:k2] if e[1] == '>']
    if len(inb) != 1 or inb[0][3][:1] != b'\x88' or not Z5.Q.valid(inb[0][3]):
        raise Fail(f'{case}: not exactly one valid Query Reply before the first screen')
    reply = inb[0][3]
    prof, size = Z5.Q.expect(reply), Z5.Q.expect_size(reply)
    canvas = Z5.SIZES.get(size)
    if prof != (1, 1, 1) or canvas is None:
        raise Fail(f'{case}: profile {prof} / canvas {size}: not the full-screen profile')
    fcmd = 0x7E if canvas != 'D' else 0xF5
    rep.update(profile=prof, size=size, canvas=canvas, reply_is_dyn=reply == Z5.Q.rec('dyn'))
    i0 = G.index(host[2])
    gend = next((k for k in range(i0 + 1, len(G)) if G[k][1] == '<' and G[k][3][1:2] == b'\xc1'), None)
    if gend is None:
        raise Fail(f'{case}: no line-mode closure after the game')
    writes = [e for e in G[i0:gend] if e[1] == '<']
    aids = [e for e in G[i0:gend] if e[1] == '>']
    live = [e[3] for e in writes]
    wt = [ms(e[2]) for e in writes]
    acts = [act7(e[3]) for e in aids]
    plan_g = [a for _, a in planned('gameplay')]
    log_g = [x['action'] for x in log if x['category'] == 'gameplay']
    if not (plan_g == log_g == acts):
        raise Fail(f'{case}: gameplay plan / driver log / TN3270E AIDs differ ({len(plan_g)} / {len(log_g)} / '
                   f'{len(acts)})')
    for e, a in zip(aids, acts):
        if e[3][0] != EXPECT[a][0]:
            raise Fail(f'{case}: {a} arrived as AID {e[3][0]:02X}')
    _, hs = hs_state(hiscore, start)
    tail_txt = [x for e in G[gend:] if e[1] == '<' for x in Z5.texts(e[3])]

    def closing(out):
        return list(out) + hs_lines(hiscore, out, start)

    def final(md):
        it = iter(tail_txt)
        return all(any(x == want for x in it) for want in closing(md['out']))
    if turn:
        mod = model_turn([EXPECT[a][1] for a in acts], canvas, start, hs, cfg)
        k = Z6.lcp(live, mod['frames'], mod['full'], fcmd)
        if k != len(live) or len(mod['frames']) != len(live):
            raise Fail(f'{case}: game write {k} differs from the TURN model (live {len(live)}, model '
                       f'{len(mod["frames"])})')
        pos = [G.index(e) for e in aids]
        per_cmd = [sum(1 for e in G[a + 1:b] if e[1] == '<') for a, b in zip(pos, pos[1:] + [gend])]
        first = sum(1 for e in G[i0:pos[0]] if e[1] == '<') if pos else len(live)
        if first != 1 or any(n != 1 for n in per_cmd[:-1]):
            raise Fail(f'{case}: not one screen per command (before the first {first}, per command '
                       f'{sorted(set(per_cmd[:-1]))})')
        for c in rep['tso_controls']:         # TURN: every command is read by a blocking TGET (the narrow rule holds)
            n = next((i for i, e in enumerate(aids) if ms(e[2]) == c['aid_ms']), None)
            if n is None:
                raise Fail(f'{case}: F1 C3 at {c["ts"]} does not follow a gameplay AID')
            c['card'] = n + 1
        out, kinds = mod['out'], mod['kinds']
        rep.update(writes=len(live), commands=len(acts), kinds={x: kinds.count(x) for x in sorted(set(kinds))})
        o = {'end': out[0], 'score': int(out[2][6:]), 'lives': int(out[3][6:]), 'fruits': int(out[5][13:])}
        rep['coverage'] = {'expected': EXPECT_L1, 'actual': o, 'ok': all(o[x] == v for x, v in EXPECT_L1.items())}
        slots = wins = None
    else:
        present = 'C'
        chars = [EXPECT[a][1] for a in acts]
        m = Z6.STRIDE[T] * len(live) + 10
        bid_t, bid_lat = Z6.bid_times(text, ev, writes, {x['ts'] for x in t['tso_controls']})

        def run_model(cards, frt):
            return model_rt(cards, canvas, T, start, hs, present, frt, cfg)
        slots, wins, mod = place(live, aids, chars, wt, bid_t, bid_lat, T, canvas, fcmd, m, run_model, case=case,
                                 final=final)
        cards = Z6.cards_for(m, slots, chars)
        out, kinds, rqs, rins, qs, fc = (mod[x] for x in ('out', 'kinds', 'rqs', 'rins', 'qs', 'fc'))
        consumed = [d if kind == 'MOV' else Z6.EVENT_CHAR.get(kind) or ch for kind, d, ch in rins]
        if consumed != chars:
            raise Fail(f'{case}: the model consumed {consumed}, the AIDs carry {chars}')
        qi, fd, je = classify(kinds, qs, out[0])
        if any(qs[a] >= qs[b] for a, b in zip(qi, qi[1:])):
            raise Fail(f'{case}: quantum writes not in strictly increasing logical order (replay)')
        for a, b in zip(qi, qi[1:]):
            if b == a + 1 and qs[b] - qs[a] != Z6.STRIDE[T]:
                raise Fail(f'{case}: writes {a} / {b} present quanta {qs[a]} / {qs[b]}: not {Z6.STRIDE[T]} apart')
        want_fd = FINAL_DEATH[T] if out[0] == 'LOST' else 0
        model_fd = mod['frt'] - mod['rdy'] if out[0] == 'LOST' else 0
        if len(fd) != want_fd or model_fd != want_fd:
            raise Fail(f'{case}: {len(fd)} final-death writes (model {model_fd}), {want_fd} required (decision D1)')
        for c in rep['tso_controls']:         # CONTROL only after an AID consumed by a blocking read (ZOS-6 rule)
            n = next((i for i, e in enumerate(aids) if ms(e[2]) == c['aid_ms']), None)
            prev = None if n is None else max((w for w, cc in enumerate(fc) if cc < slots[n]), default=None)
            if prev is None or kinds[prev] != 'N':
                raise Fail(f'{case}: F1 C3 at {c["ts"]} follows an AID that was not read by a blocking read')
            c['card'] = slots[n]
        runs, cur = [], 0
        for kind, frz in rqs + [('-', 0)]:
            if kind == 'F':
                cur += 1
            elif cur:
                runs.append(cur)
                cur = 0
        want_frz = ref_rt.quanta(ref_rt.FREEZE, T)
        if any(r != want_frz for r in runs):
            raise Fail(f'{case}: freeze runs {runs}, {want_frz} quanta required')
        rep['freeze_mutants'] = {}
        for d in (-1, 1):
            if not runs:
                break
            try:
                _, _, mm = place(live, aids, chars, wt, bid_t, bid_lat, T, canvas, fcmd, m, run_model, want_frz + d,
                                 case, final)
                ok = Z6.lcp(live, mm['frames'], mm['full'], fcmd) == len(live) and len(mm['frames']) == len(live)
            except Fail:
                ok = False
            rep['freeze_mutants'][want_frz + d] = 'matches' if ok else 'rejected'
        rep['live_freeze_discrimination'] = None if not runs else 'NOT OBSERVABLE' if 'matches' in \
            rep['freeze_mutants'].values() else 'DISCRIMINATED'
        rep.update(writes=len(live), quanta=len(rqs), death_runs=runs, frame_quanta=[qs[j] for j in qi],
                   gameplay_writes=len(qi), final_death_writes=fd, end_screen=je,
                   directional=[{'action': a, 'sent': ms(e[2]), 'aid': f'{e[3][0]:02X}', 'card': s, 'window': w,
                                 'model': c} for a, e, s, w, c in zip(acts, aids, slots, wins, consumed)])
        o = SC.outcome(out)
        rep['coverage'] = {'expected': SC.EXPECT, 'actual': o, 'ok': SC.intended(o)}
        # the ZOS-6 timing on the gameplay writes only (the final-death writes are not quantum writes of the grid)
        k2 = ['D' if j in fd else k for j, k in enumerate(kinds)]
        Z6.timing(rep, wt, k2, qs, fc, cards, slots, aids, acts, rqs, text, T)
        fdt = [wt[j] for j in fd]
        rep['final_death_timing'] = {
            'writes': len(fd), 'from_last_gameplay_write': (fdt[0] - wt[qi[-1]]) if fd and qi else None,
            'gaps': [b - a for a, b in zip(fdt, fdt[1:])], 'to_end_screen': (wt[je] - fdt[-1]) if fd else None,
            'span': (fdt[-1] - fdt[0]) if fd else None, 'nominal_gap': T}
        spans = []
        byq = {qs[j]: j for j in qi}
        ks = [kd for kd, _ in rqs]
        for d0 in [k_ for k_ in range(len(ks)) if ks[k_] == 'F' and (k_ == 0 or ks[k_ - 1] != 'F')]:
            pair = next(((byq[q1], byq[q1 + want_frz]) for q1 in range(d0, d0 + Z6.STRIDE[T])
                         if q1 in byq and q1 + want_frz in byq), None)
            spans.append(None if pair is None else wt[pair[1]] - wt[pair[0]])
        rep['freeze_span_proxy_ms'] = spans          # timing information only (no ZOS-7 gate)
    exp = closing(out)
    tail = G[gend:]
    k, star, shell, closure_in = 0, False, False, []
    for e in tail:
        if e[1] == '>':
            closure_in.append(e)
            continue
        segs = Z5.texts(e[3])
        for s in segs:
            mt = Z5.BAD_TEXT.search(s)
            if mt and mt.group(0) == '***' and k < len(exp):
                raise Fail(f'{case}: end lines {exp} not complete before ***')
            if mt and mt.group(0) != '***':
                raise Fail(f'{case}: {mt.group(0)} after the game')
            if mt:
                star = True
            if k < len(exp) and s == exp[k]:
                k += 1
        if k == len(exp) and any(Z5.SHELL in s for s in segs):
            shell = True
            break
    if k != len(exp):
        raise Fail(f'{case}: end lines {exp} not found in line mode')
    if not shell:
        raise Fail(f'{case}: no return to the {Z5.SHELL}')
    if len(closure_in) != 1 or closure_in[0][3][0] != 0x7D or typed(closure_in[0][3]):
        raise Fail(f'{case}: closure inputs {[act7(e[3]) for e in closure_in]} are not one ENTER')
    Z5.outside_errors(ev)
    rep.update(end_lines=exp, star=star)
    rep['state'] = BLOCKED if rep['blocked'] else PASS if rep['coverage']['ok'] else INCOMPLETE
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True, choices=sorted(PLANS))
    ap.add_argument('--trace', required=True)
    ap.add_argument('--drive-log', required=True)
    ap.add_argument('--hiscore', required=True, help="ABSENT or the 80-byte HISCORE record (read-only precheck)")
    ap.add_argument('--prefix', default='Z00000.PACMAN')
    a = ap.parse_args()
    raw, lg = Path(a.trace).read_bytes(), Path(a.drive_log).read_bytes()
    print(f'{a.case} trace SHA-256 {hashlib.sha256(raw).hexdigest()} ({len(raw)} bytes); driver log SHA-256 '
          f'{hashlib.sha256(lg).hexdigest()}; hiscore {a.hiscore!r}')
    try:
        rep = check(raw.decode('utf-8', 'replace'), lg.decode().splitlines(), a.case, a.hiscore, a.prefix)
    except Fail as e:
        print(f'{a.case}: {FAILED}: {e}')
        sys.exit(1)
    print(f'{a.case}: T {rep["T"]}; profile {rep["profile"]} canvas {rep["size"]}; {rep["writes"]} game writes = '
          'model; '
          f'end lines {rep["end_lines"]}; *** {rep["star"]}; shell yes')
    print(f'  coverage: {json.dumps(rep["coverage"])}')
    if rep['T']:
        print(f'  writes: {rep["gameplay_writes"]} COALESCED gameplay, {len(rep["final_death_writes"])} final-death '
              f'(D1), end screen {rep["end_screen"]}; {rep["quanta"]} logical quanta; freeze runs {rep["death_runs"]}')
        for d in rep['directional']:
            print(f'  {d["action"]}: sent {d["sent"]}, AID {d["aid"]}, card {d["card"]} in {d["window"]}, '
                  f'model {d["model"]}')
        print(f'  final-death timing (reported only, no gate): {json.dumps(rep["final_death_timing"])}')
        print(f'  freeze-span proxy per in-game death (information only): {rep["freeze_span_proxy_ms"]} ms')
        print(f'  freeze mutants {rep["freeze_mutants"]}; live freeze discrimination '
              f'{rep["live_freeze_discrimination"]}')
        print(f'  principal segment: {json.dumps(rep["principal"])}')
        print(f'  input reaction: {json.dumps(rep["reaction"])}')
        print(f'  frozen ZOS-6 gates: {json.dumps(rep.get("gates"))}')
        print(f'  diagnostics: {json.dumps(rep.get("diag", {}))}')
    else:
        print(f'  TURN: {rep["commands"]} commands, one screen each; write kinds {rep["kinds"]}')
    print(f'  TSO blocking-read CONTROL records (F1 C3): {len(rep["tso_controls"])} '
          f'{[(c["aid"], c.get("card")) for c in rep["tso_controls"]]}')
    for n_ in rep.get('diag_notes', []):
        print(f'  diagnostic: {n_}')
    print(f'{a.case}: {rep["state"]}' + (f' - {"; ".join(rep["blocked"])}' if rep['blocked'] else ''))
    sys.exit({PASS: 0, BLOCKED: 2, INCOMPLETE: 3}[rep['state']])


if __name__ == '__main__':
    main()
