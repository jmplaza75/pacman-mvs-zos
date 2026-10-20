#!/usr/bin/env python3
"""ZOS-8 live postcheck (docs/zos8-design.md, U1-U12). Local, read-only; one case per trace.

Usage: zos8_live_check.py --case CASE --trace TRACE --drive-log LOG [--before ABSENT|'<record>'|n/a]
       [--prefix Z00000.PACMAN]
       exit 0 PASS, 1 FUNCTIONAL FAIL, 2 ENVIRONMENT/TIMING BLOCKED, 3 COVERAGE INCOMPLETE (never PASS)
--before = the read-only precheck of the case's store before the case (HS8.T1 / HSFULL.T1 member HISCORE): the
checker models the game from it (independent of the planned chain) and also reports whether it is the chain's state.

The frozen ZOS-6 / ZOS-5 checkers (TN3270E parse with the KRI and narrow F1 C3 rules, write equality lcp, texts,
typed) and the accepted ZOS-7 checker (zos7_live_check.check: the whole REALTIME ARCADE acceptance, D1, the frozen
gates) are imported unchanged. What ZOS-8 adds:
- TURN games (HL*, S8C, the Stage D follow-up GD): every write = the TURN TSD model (ref_gx_screen; ARCADE ref_gp2
  with the HUD high score of the store state, or CLASSIC), one screen per command, end lines = the model's + the
  ref_hs high-score lines of the store state (CLASSIC: none); the EXEC names the plan's CLIST member exactly;
- HL8 only: IEC217I B14-0C for <prefix>.HSFULL.T1(HISCORE) may appear (at most one message, anywhere after the last
  command and before the shell), with at most one TSO hold (`***` + one ENTER, category hold) before the end screen;
  any other IEC / IKJ / CEE / ABEND text, or an IEC in any other case, fails;
- sound (S8A / S8B through zos7_live_check.check with the model's frames rung by tests/ref_s2.py patterns on the
  skipped quanta; S8C TURN): every write incl. the WCC alarm bit and the bell-only writes = model; the bells per
  event = the plan's (else COVERAGE INCOMPLETE); bell-step gaps reported (no gate);
- recovery E1 / E2 / E3 (micro-gates): the RPESTAE test screen of the case, one ENTER, then an abend indication
  (ABEND / ENDED DUE TO ERROR / COMPLETION CODE / CEE3nnnS) - E3: after `RPE E3 LINE MODE RESTORED, FORCING 0C7` - the
  test screen never again, only ENTERs (one per `***`) until the ISPF Command Shell; LISTALC STATUS and FREE held as
  observed live (2026-10-20): the ISPF initial hold, then the output pages (each ends with `***`), one ENTER each, then
  the shell (held_trace); FREE F(CEEOPTS) exactly when the LISTALC pages list a CEEOPTS DD (the strict DD rule,
  zos8_drive.ceeopts_of), with no output; then the follow-up game GD PASS (the only game start of the trace). The LE
  text and the abend code are recorded, not gated. Before the test screen: EXEC, exactly one ISPF `***` hold, exactly
  one ENTER (every EXEC from the shell is held; E1 2026-10-20). A resumed case is checked from its two trace segments
  (--trace2 / --drive-log2) joined losslessly (join_traces).
"""
import argparse
import hashlib
import json
import re
import sys
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests')]
import zos6_live_check as Z6  # noqa: E402
import zos7_live_check as Z7  # noqa: E402
import ref_rt  # noqa: E402
import ref_gp2 as L  # noqa: E402
import ref_hs as H  # noqa: E402
import ref_s2  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
from ref_snap import Log  # noqa: E402
import zos8_scen as S  # noqa: E402
import zos8_drive as DV  # noqa: E402

Z5 = Z6.Z5
Fail = Z6.Fail
ms, typed = Z6.ms, Z6.typed
PASS, BLOCKED, FAILED, INCOMPLETE = Z6.PASS, Z6.BLOCKED, Z6.FAILED, Z7.INCOMPLETE
ABEND_SIGN = re.compile(r'ABEND|ENDED DUE TO ERROR|COMPLETION CODE|CEE3\d{3}S')
IEC_B14 = re.compile(r'IEC217I B14-0C,[^,]*,[^,]*,[^,]*,PACHS,')
E3_LINE = 'RPE E3 LINE MODE RESTORED, FORCING 0C7'
START = (0x7E, 0xF5)


def is_start(e):
    return e[1] == '<' and len(e[3]) == 2 and e[3][0] in START and e[3][1] == 0xC3


def txt(e):
    return Z5.texts(e[3]) if e[1] == '<' else []


def check_log(log_lines, case):
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
    return log


# ---- models ------------------------------------------------------------------------------------------------------
@contextmanager
def persisted(saved):
    """The end-screen NEW HIGH SCORE label follows the persistence outcome (PACSCR: RP-HI = 1 AND REQ-HSNEW = 'Y';
    D38: NEW only when the save succeeded). tests/ref_rp.py Tracker (unchanged) decides it from the score alone
    (eligible and beaten): wrapped here, its end frame keeps the label only if ref_hs saved the record. saved None =
    the Tracker unchanged. Every other decoration is the Tracker's own."""
    import ref_rp
    real = ref_rp.Tracker
    if saved is None:
        yield
        return

    class Tracker(real):
        def frame(self, *a, **kw):
            rp = super().frame(*a, **kw)
            if rp is not None and rp.get('end'):
                rp['new'] = bool(rp['new'] and saved)
            return rp
    ref_rp.Tracker = Tracker
    try:
        yield
    finally:
        ref_rp.Tracker = real


def turn_model(name, hs, sound, saved=None):
    """The TURN TSD model of a ZOS-8 game (tests/zos8live/<name>.txt) -> dict(frames, full, kinds, bells). saved: the
    ref_hs persistence outcome of the game (True = NEW HIGH SCORE saved) for the end-screen label (see persisted)."""
    full, real, tagged = Z7._tagging()
    lg = Log()
    lg.kinds = []
    gx.full = tagged
    try:
        with persisted(saved):
            frames = S.model_frames(name, hs=hs, snap=lg)
    finally:
        gx.full = real
    bells = []
    if sound:
        frames, bells = ref_s2.patterns(frames, lg, 'Y', 'T', 150)
        full = full | {ref_s2.alarm(f) for f in full}
    return {'frames': frames, 'full': full, 'kinds': list(lg.kinds), 'bells': bells}


def model_rt_sound(cards, canvas, per, start, hs, present='C', frt=None, cfg=Z7.SC.CFG):
    """zos7_live_check.model_rt (same game, controller and output) with SOUND Y / ALARM(PATTERN): the frames rung by
    tests/ref_s2.py patterns on the COALESCED skipped quanta; a rung full screen is still a full screen."""
    full, real, tagged = Z7._tagging()
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
    rung, trace = ref_s2.patterns(list(frames), lg, 'Y', 'R', per, skips=frames.skips)
    kinds = list(lg.kinds) + ['B'] * (len(rung) - len(lg.kinds))
    c = ctl['c']
    return {'out': out, 'frames': rung, 'kinds': kinds, 'full': full | {ref_s2.alarm(f) for f in full}, 'rqs': rqs,
            'rins': rins, 'qs': list(frames.qs) + [None] * (len(rung) - len(lg.kinds)),
            'fc': list(frames.cards) + [frames.cards[-1]] * (len(rung) - len(lg.kinds)), 'frt': c.frt, 'rdy': c.rdy,
            'bells': trace}


ALARM = 0x04                                  # the 3270 WCC sound-alarm bit
_PARSE6 = Z6.parse6                           # the frozen ZOS-6 parse, unchanged (parse8 adds to it, never replaces it)


def c3_alarm_equiv(wcc):
    """WCC X'C3', with or without the alarm bit only: C3 or C7, nothing else (no other bit is ignored)."""
    return wcc & ~ALARM & 0xFF == 0xC3


def sound_c3_controls(ev, tso):
    """ZOS-8 sound (Stage E S1, 2026-10-20): the frozen narrow TSO blocking-read CONTROL rule of zos6_live_check.parse6
    (an exact 2-byte host Write F1 C3 right after an inbound AID, that AID the last kept event, the last host record
    before the AID a WCC C3 screen, at most one per AID) with one predicate widened: the WCC of that last host record
    may also carry the alarm bit (C7 = the SOUND(YES) start / PAUSED screen ringing its bell). Applied to the events
    parse6 kept; an AID that already has a control gets no second one. -> (kept events, all controls by time)."""
    have = {c['aid_ms'] for c in tso}
    add, kept = [], []
    for k, e in enumerate(ev):
        if e[1] == '<' and e[3] == Z6.TSO_C3 and k > 0 and ev[k - 1][1] == '>' and ev[k - 1][3][:1] != b'' \
                and kept and ev[k - 1] is kept[-1] and ms(ev[k - 1][2]) not in have:
            last_host = next((x for x in reversed(kept[:-1]) if x[1] == '<'), None)
            if last_host is not None and len(last_host[3]) > 1 and c3_alarm_equiv(last_host[3][1]):
                add.append({'ms': ms(e[2]), 'ts': e[2], 'aid_ms': ms(ev[k - 1][2]), 'aid': f'{ev[k - 1][3][0]:02X}',
                            'alarm_context': True})
                have.add(ms(ev[k - 1][2]))
                continue
        kept.append(e)
    return kept, sorted(list(tso) + add, key=lambda c: c['ms'])


def parse8(text):
    """zos6_live_check.parse6 + sound_c3_controls (ZOS-8 sound cases only); the game starts recomputed on the kept
    events with parse6's own predicate."""
    t = _PARSE6(text)
    ev, tso = sound_c3_controls(t['ev'], t['tso_controls'])
    starts = [k for k, e in enumerate(ev) if e[1] == '<' and len(e[3]) == 2 and e[3][0] in (0x7E, 0xF5) and
              e[3][1] == 0xC3]
    return dict(t, ev=ev, starts=starts, tso_controls=tso)


@contextmanager
def sound_parse():
    """The frozen ZOS-7 check (and ZOS-6 helpers it calls) parse through parse8 inside this context only."""
    real = Z6.parse6
    Z6.parse6 = parse8
    try:
        yield
    finally:
        Z6.parse6 = real


@contextmanager
def sound_model():
    real = Z7.model_rt
    Z7.model_rt = model_rt_sound
    try:
        yield
    finally:
        Z7.model_rt = real


def store_pds(name, before):
    """The ref_hs PDS and DD of the case's store before the case (from --before)."""
    st = S.store_of(name)
    if st == 'NONE':
        return H.Pds(), 'DUMMY'
    mem = {} if before == 'ABSENT' else {'HISCORE': [before.ljust(80)]}
    return H.Pds(mem, full=(st == 'FULL')), ('M', 'HISCORE')


def expected_lines(name, before):
    cards = S.live_cards(name)
    out = S.end_lines(name, cards)
    if S.GAMES[name][3] == 'C':
        return out, []
    pds, dd = store_pds(name, before)
    return out, H.end_lines(pds, dd, *H.final(out), S.GAMES[name][2])


def saved_of(hsl):
    """The persistence outcome of a game from its ref_hs high-score lines: saved = NEW HIGH SCORE."""
    return 'NEW HIGH SCORE' in hsl


# ---- one TURN game -------------------------------------------------------------------------------------------------
def turn_game(G, name, cmd, before, allow_iec, sound, prefix):
    """G = the events from the game's EXEC to the end of the trace. -> report dict or raises Fail."""
    rep = {'game': name}
    pre_in = [k for k, e in enumerate(G) if e[1] == '>']
    s0 = next((k for k, e in enumerate(G) if is_start(e)), None)
    if s0 is None:
        raise Fail(f'{name}: no game start after the EXEC')
    pre = [G[k] for k in pre_in if k < s0]
    if len(pre) != 2 or typed(pre[0][3]) != cmd or pre[1][3][0] != 0x7D or typed(pre[1][3]):
        raise Fail(f'{name}: transition inputs {[typed(e[3]) for e in pre]} are not EXEC {cmd!r} + ENTER')
    E = G[s0:]
    host = [e for e in E if e[1] == '<']
    if host[1][3] != Z5.QUERY:
        raise Fail(f'{name}: no Read Partition Query after the switch')
    k1, k2 = E.index(host[1]), E.index(host[2])
    inb = [e for e in E[k1:k2] if e[1] == '>']
    if len(inb) != 1 or inb[0][3][:1] != b'\x88' or not Z5.Q.valid(inb[0][3]):
        raise Fail(f'{name}: not exactly one valid Query Reply before the first screen')
    prof, size = Z5.Q.expect(inb[0][3]), Z5.Q.expect_size(inb[0][3])
    canvas = Z5.SIZES.get(size)
    if prof != (1, 1, 1) or canvas != 'W':
        raise Fail(f'{name}: profile {prof} / canvas {size}: not the accepted 120 x 27 full-screen profile')
    fcmd = 0x7E
    i0 = E.index(host[2])
    # HL8: IEC217I B14 (the failed STOW of HSFULL.T1) and at most one TSO hold (*** + ENTER) are not game records
    iec, hold, drop = [], [], set()
    for k in range(i0 + 1, len(E)):
        e = E[k]
        if e[1] == '<' and any(re.search(r'IEC\d{3}I', s) for s in txt(e)):
            iec.append(k)
    if iec and not allow_iec:
        raise Fail(f'{name}: IEC message {[s for s in txt(E[iec[0]]) if "IEC" in s]} (only HL8 may show IEC217I B14)')
    if len(iec) > 1:
        raise Fail(f'{name}: {len(iec)} IEC messages (at most one IEC217I B14-0C)')
    if iec:
        k = iec[0]
        t = ' '.join(txt(E[k])) + ' ' + ' '.join(txt(next((x for x in E[k + 1:] if x[1] == '<'), E[k])))
        if not IEC_B14.search(t) or f'{prefix}.HSFULL.T1(HISCORE)' not in t:
            raise Fail(f'{name}: the IEC message is not IEC217I B14-0C for {prefix}.HSFULL.T1(HISCORE): {t[:160]}')
        drop.add(k)
        nxt = next((j for j in range(k + 1, len(E)) if E[j][1] == '<'), None)
        if nxt is not None and not any(s.startswith('IEC') for s in txt(E[nxt])) and \
                any(f'{prefix}.HSFULL.T1(HISCORE)' in s for s in txt(E[nxt])):
            drop.add(nxt)                                    # the message continuation record
        # a hold = the next host record is a TSO `***` that comes before the game's line-mode closure, answered by
        # one empty ENTER that also comes before it (the end screen follows the hold)
        close = next((j for j in range(i0 + 1, len(E)) if E[j][1] == '<' and j not in drop and
                      E[j][3][1:2] == b'\xc1'), len(E))
        st = next((j for j in range(k + 1, len(E)) if E[j][1] == '<' and j not in drop), None)
        ent = None if st is None else next((j for j in range(st + 1, len(E)) if E[j][1] == '>'), None)
        if st is not None and st < close and '***' in ' '.join(txt(E[st])) and ent is not None and ent < close \
                and E[ent][3][0] == 0x7D and not typed(E[ent][3]):
            drop |= {st, ent}
            hold = [st, ent]
    rep['iec'] = [' '.join(txt(E[k])) for k in iec]
    rep['hold'] = bool(hold)
    E2 = [e for k, e in enumerate(E) if k not in drop]
    i0 = E2.index(host[2])
    gend = next((k for k in range(i0 + 1, len(E2)) if E2[k][1] == '<' and E2[k][3][1:2] == b'\xc1'), None)
    if gend is None:
        raise Fail(f'{name}: no line-mode closure after the game')
    writes = [e for e in E2[i0:gend] if e[1] == '<']
    aids = [e for e in E2[i0:gend] if e[1] == '>']
    acts = [Z7.act7(e[3]) for e in aids]
    cards = S.live_cards(name)
    if acts != cards[1:]:
        raise Fail(f'{name}: the typed commands ({len(acts)}) are not the cards of tests/{S.LIVE_DIR}/{name}.txt')
    hs = S.hs_tuple(name, before) if S.GAMES[name][3] == 'A' else None
    out, hsl = expected_lines(name, before)
    mod = turn_model(name, hs, sound, saved=saved_of(hsl) if hs else None)
    live = [e[3] for e in writes]
    k = Z6.lcp(live, mod['frames'], mod['full'], fcmd)
    if k != len(live) or len(mod['frames']) != len(live):
        raise Fail(f'{name}: game write {k} differs from the TURN model (live {len(live)}, model '
                   f'{len(mod["frames"])})')
    pos = [E2.index(e) for e in aids]
    per_cmd = [sum(1 for e in E2[a + 1:b] if e[1] == '<') for a, b in zip(pos, pos[1:] + [gend])]
    first = sum(1 for e in E2[i0:pos[0]] if e[1] == '<') if pos else len(live)
    if first != 1 or any(n != 1 for n in per_cmd[:-1]):
        raise Fail(f'{name}: not one screen per command (before the first {first}, per command '
                   f'{sorted(set(per_cmd[:-1]))})')
    exp = list(out) + hsl
    kk, star, shell, closure_in = 0, False, False, []
    for e in E2[gend:]:
        if e[1] == '>':
            closure_in.append(e)
            continue
        for s in txt(e):
            mt = Z5.BAD_TEXT.search(s)
            if mt and mt.group(0) == '***' and kk < len(exp):
                raise Fail(f'{name}: end lines {exp} not complete before ***')
            if mt and mt.group(0) != '***':
                raise Fail(f'{name}: {mt.group(0)} after the game')
            if mt:
                star = True
            if kk < len(exp) and s == exp[kk]:
                kk += 1
        if kk == len(exp) and any(Z5.SHELL in s for s in txt(e)):
            shell = True
            break
    if kk != len(exp):
        raise Fail(f'{name}: end lines {exp} not found in line mode')
    if not shell:
        raise Fail(f'{name}: no return to the {Z5.SHELL}')
    if len(closure_in) != 1 or closure_in[0][3][0] != 0x7D or typed(closure_in[0][3]):
        raise Fail(f'{name}: closure inputs {[Z7.act7(e[3]) for e in closure_in]} are not one ENTER')
    rep.update(writes=len(live), commands=len(acts), end_lines=exp, star=star, profile=prof, size=size,
               kinds={x: mod['kinds'].count(x) for x in sorted(set(mod['kinds']))},
               bells=[list(x) for x in ref_s2.counts(mod['bells'])] if sound else [],
               bell_writes=[w for w, _, _ in mod['bells']],
               bell_times=[ms(writes[w][2]) for w, _, _ in mod['bells'] if w < len(writes)])
    rep['bell_gaps'] = [b - a for a, b in zip(rep['bell_times'], rep['bell_times'][1:])]
    rep['end'] = gend
    return rep


def game_cmd(name, prefix, clist=None):
    return f"EXEC '{prefix}.CLIST({clist or S.clist_of(name)})' '{S.kw_of(name)}'"


def check_turn(text, log_lines, case, before, prefix):
    p = DV.PLANS[case]
    t = parse8(text) if 'SOUND(YES)' in p['kw'].split() else Z6.parse6(text)
    ev = t['ev']
    rep = {'case': case, 'before': before, 'funcs': t['funcs'], 'tso_controls': t['tso_controls']}
    if Z5.CR not in t['funcs']:
        raise Fail(f'{case}: CONTENTION-RESOLUTION not negotiated (the accepted ZOS-5 profile)')
    if len(t['starts']) != 1:
        raise Fail(f'{case}: {len(t["starts"])} games in the trace (exactly one expected)')
    if t['tso_controls']:
        raise Fail(f'{case}: TSO F1 C3 records in a TURN game {t["tso_controls"]} (not expected)')
    log = check_log(log_lines, case)
    acts = [(x['category'], x['action']) for x in log]
    plan = DV.planned(case)
    holds = [i for i, a in enumerate(acts) if a == ('hold', 'ENTER')]
    if holds and not (p['iec_hold'] and len(holds) == 1 and holds[0] == len(plan) - 1):
        raise Fail(f'{case}: hold ENTER {holds} not allowed (HL8 only, once, before the closure ENTER)')
    if [a for i, a in enumerate(acts) if i not in holds] != plan:
        raise Fail(f'{case}: driver log != plan')
    cmd = DV.command(case, 'EXEC', prefix)
    i_exec = next((k for k, e in enumerate(ev) if e[1] == '>' and typed(e[3]) == cmd), None)
    if i_exec is None:
        raise Fail(f'{case}: no EXEC {cmd!r} in the trace')
    Z5.outside_errors(ev[:i_exec])
    g = turn_game(ev[i_exec:], p['game'], cmd, before, p['iec_hold'], 'SOUND(YES)' in p['kw'].split(), prefix)
    if len(holds) != int(g['hold']):
        raise Fail(f'{case}: driver hold ENTERs {len(holds)} != trace holds {int(g["hold"])}')
    rep.update(g)
    if case in S.HL_ORDER:
        chain = {c: b for c, _, b, _, _ in S.hl_chain()}
        rep['chain_before'] = chain[case]
        rep['state_gate'] = S.store_of(case) == 'NONE' or chain[case] == before.rstrip()
        if not rep['state_gate']:
            raise Fail(f'{case}: store state {before!r} != the planned chain {chain[case]!r} (STOP the stage)')
    rep['coverage'] = {'ok': True}
    if case == 'SF':                                  # Stage F: the frozen production first write (fail closed)
        if before != 'ABSENT':
            raise Fail(f'SF: DATA(HISCORE) before the game is {before!r}, not ABSENT (no first write)')
        if expected_lines('SF', 'ABSENT')[1] != S.SF_LINES:
            raise Fail('SF: the model no longer gives the frozen Stage F high-score lines')
        hsl = rep['end_lines'][-len(S.SF_LINES):]
        if hsl != S.SF_LINES or any(x in ' '.join(rep['end_lines']) for x in ('NOT SAVED', 'UNAVAILABLE')):
            raise Fail(f'SF: high-score lines {hsl} != {S.SF_LINES}')
        rep['sf_lines'] = hsl
    if case == 'S8C':
        rep['coverage'] = {'expected': S.S8_BELLS[case], 'actual': g['bells'], 'ok': g['bells'] == S.S8_BELLS[case]}
    rep['state'] = PASS if rep['coverage']['ok'] else INCOMPLETE
    return rep


# ---- REALTIME with sound (S8A / S8B) -------------------------------------------------------------------------------
def rt_writes(text):
    """The game writes and their trace times, segmented exactly as zos7_live_check.check does."""
    t = parse8(text)
    G = t['ev'][t['starts'][0]:]
    host = [e for e in G if e[1] == '<']
    i0 = G.index(host[2])
    gend = next(k for k in range(i0 + 1, len(G)) if G[k][1] == '<' and G[k][3][1:2] == b'\xc1')
    return [e for e in G[i0:gend] if e[1] == '<']


def check_rt(text, log_lines, case, hiscore, prefix):
    p = DV.PLANS[case]
    with sound_model(), sound_parse():
        rep = Z7.check(text, log_lines, case, hiscore, prefix, plan=p)
        T = p['T']
        writes = rt_writes(text)
        m = Z6.STRIDE[T] * rep['writes'] + 10
        cards = Z6.cards_for(m, [d['card'] for d in rep['directional']],
                             [DV.EXPECT[d['action']][1] for d in rep['directional']])
        _, hs = Z7.hs_state(hiscore, p['start'])
        mod = model_rt_sound(cards, rep['canvas'], T, p['start'], hs, 'C', None, p['cfg'])
    if len(mod['frames']) != len(writes):
        raise Fail(f'{case}: final model {len(mod["frames"])} writes != live {len(writes)}')
    bells = [list(x) for x in ref_s2.counts(mod['bells'])]
    times = [ms(writes[w][2]) for w, _, _ in mod['bells']]
    steps, cur = [], []
    for (w, name, n), tm in zip(mod['bells'], times):
        if name != 'STEP':
            cur = [tm]
            steps.append(cur)
        else:
            cur.append(tm)
    rep.update(bells=bells, bell_writes=[w for w, _, _ in mod['bells']],
               bell_alarm_bits=sum(1 for w in writes if w[3][1:2] and w[3][1] & 0x04),
               pattern_step_gaps=[[b - a for a, b in zip(s, s[1:])] for s in steps if len(s) > 1])
    want = S.S8_BELLS[case]
    rep['sound_coverage'] = {'expected': want, 'actual': bells, 'ok': bells == want}
    if rep['state'] == PASS and not rep['sound_coverage']['ok']:
        rep['state'] = INCOMPLETE
    return rep


# ---- recovery (E1 / E2 / E3) ---------------------------------------------------------------------------------------
def seqs(text):
    """TN3270E SEQ-NUMBERs of a trace: every host record (data, BID, control) and every terminal 3270-DATA record."""
    recs = Z6.raw_records(text)
    return ([int.from_bytes(r[3][3:5], 'big') for r in recs if r[1] == '<'],
            [int.from_bytes(r[3][3:5], 'big') for r in recs if r[1] == '>' and r[3][:1] == b'\x00'])


CUTS = {('hold',), ('hold', 'screen'), ('screen',)}


def join_traces(*texts, case=None, cuts=None):
    """One logical execution from 2 or 3 trace segments of a resumed Stage D case (E1 2026-10-20), cut only at the
    defined resume points, in this order: 'hold' = the EXEC's initial `***` hold (the segment ends with the `***` host
    record), 'screen' = the complete test screen of the case (the segment ends with that screen). cuts = the boundary
    kinds in order; by default ('hold',) for 2 segments, ('hold', 'screen') for 3; the single cut at the screen
    (('screen',), E1-T2 2026-10-20: the driver stopped on the wrapped test screen) only when the caller names it
    (the segment then ends with exactly the test screen record). Every boundary: the next segment starts with exactly
    one empty ENTER (no host write before it); host and terminal SEQ-NUMBERs continue exactly +1 (no record lost,
    added or repeated); the same negotiated functions; times strictly increase. Anything
    else (a missing, repeated, modified or reordered segment) raises Fail. -> the parse6 dict of the joined events."""
    if len(texts) not in (2, 3):
        raise Fail(f'segments: {len(texts)} segments (a resumed case has 2 or 3)')
    cuts = tuple(cuts) if cuts is not None else (('hold',) if len(texts) == 2 else ('hold', 'screen'))
    if cuts not in CUTS or len(cuts) != len(texts) - 1:
        raise Fail(f'segments: cut points {cuts} for {len(texts)} segments are not a defined resume')
    ts = [Z6.parse6(x) for x in texts]
    sq = [seqs(x) for x in texts]

    def cont(a, b):          # +1 across the boundary; or the all-zero numbering the ZOS-5 rule accepts, in both
        return bool(a and b) and (b[0] == a[-1] + 1 or not any(a + b))
    for n in range(len(texts) - 1):
        a, b = ts[n], ts[n + 1]
        if a['funcs'] != b['funcs']:
            raise Fail(f'segments {n + 1}/{n + 2}: negotiated functions differ {a["funcs"]} / {b["funcs"]}')
        if not cont(sq[n][0], sq[n + 1][0]) or not cont(sq[n][1], sq[n + 1][1]):
            raise Fail(f'segments {n + 1}/{n + 2}: SEQ-NUMBERs do not continue across the boundary (host '
                       f'{sq[n][0][-1:]} -> {sq[n + 1][0][:1]}, terminal {sq[n][1][-1:]} -> {sq[n + 1][1][:1]})')
        e1, e2 = a['ev'], b['ev']
        last = ' '.join(txt(e1[-1])) if e1 and e1[-1][1] == '<' else None
        if last is None:
            raise Fail(f'segment {n + 1} does not end with a host record')
        if cuts[n] == 'hold' and '***' not in last:
            raise Fail(f'segment {n + 1} does not end with the *** hold')
        if cuts[n] == 'screen' and not (case and txt(e1[-1]) == DV.test_screen(case)):
            raise Fail(f'segment {n + 1} does not end with the exact test screen')
        if not e2 or e2[0][1] != '>' or e2[0][3][0] != 0x7D or typed(e2[0][3]):
            raise Fail(f'segment {n + 2} does not start with the one ENTER that continues the case')
        if ms(e2[0][2]) <= ms(e1[-1][2]):
            raise Fail(f'segments {n + 1}/{n + 2}: times do not increase across the boundary')
    ev = [e for x in ts for e in x['ev']]
    return {'ev': ev, 'funcs': ts[0]['funcs'], 'starts': [k for k, e in enumerate(ev) if is_start(e)],
            'tso_controls': [c for x in ts for c in x['tso_controls']],
            'controls': [c for x in ts for c in x['controls']]}


ERR_TEXT = re.compile(r'IKJ\d{5}|IEC\d{3}|IGZ\d{4}|CEE\d{4}|ABEND')


def held_trace(ev, i_cmd, case, what):
    """The answer to a command typed on the shell at ev[i_cmd], as observed live (LISTALC / FREE, 2026-10-20): the
    ISPF initial hold (host records whose only text is `***`), then 0..PAGES_MAX output pages (the host records
    between two ENTERs; exactly one of them carries `***`, as the last text of the last record), every hold and page
    answered by exactly one empty ENTER, then the shell panel (no `***`). An ENTER with nothing before it, a page
    without `***` or with text after it, a page repeated, an error text, a second command typed, too many pages or no
    return to the shell: Fail. -> (pages as lists of output lines, index of the shell panel record, ENTERs)."""
    groups, cur, enters = [], [], 0
    for i in range(i_cmd + 1, len(ev)):
        e = ev[i]
        if e[1] == '<':
            if any(Z5.SHELL in x for x in txt(e)):
                if not groups or any('***' in x for r in cur for x in txt(r)):
                    raise Fail(f'{case}: {what}: the shell came back before the hold was answered')
                if cur and any(txt(r) for r in cur):
                    raise Fail(f'{case}: {what}: output without `***` before the shell')
                pages = groups[1:]
                if len(pages) > DV.PAGES_MAX:
                    raise Fail(f'{case}: {what}: {len(pages)} output pages (more than {DV.PAGES_MAX})')
                return pages, i, enters
            cur.append(e)
            continue
        if e[3][0] != 0x7D or typed(e[3]):
            raise Fail(f'{case}: {what}: an input other than one empty ENTER before the shell')
        lines = [x.strip() for r in cur for x in txt(r) if x.strip()]
        if not cur or not lines or lines[-1] != '***' or lines.count('***') != 1 or \
                not any('***' in x for x in txt(cur[-1])):
            raise Fail(f'{case}: {what}: ENTER {enters + 1} does not answer one `***` hold / page '
                       f'({len(cur)} host records)')
        body = lines[:-1]
        if not groups and body:
            raise Fail(f'{case}: {what}: the initial hold carries text {body[:3]}')
        if groups and not body:
            raise Fail(f'{case}: {what}: an empty output page')
        if any(ERR_TEXT.search(x) for x in body):
            raise Fail(f'{case}: {what}: an error text on output page {len(groups)}')
        if len(groups) > 1 and body == groups[-1]:
            raise Fail(f'{case}: {what}: output page {len(groups)} repeats the previous page')
        groups.append(body)
        cur, enters = [], enters + 1
    raise Fail(f'{case}: {what}: no return to the {Z5.SHELL}')


LOG_CUT = {'hold': (('transition', 'EXEC'), ('transition', 'ENTER')),
           'screen': (('transition', 'ENTER'), ('abend', 'ENTER'))}


def check_segments(texts, logs, case, cuts):
    """A resumed case per segment: one driver log per trace segment; at every cut the earlier log ends with the action
    before the cut and the later one starts with the action that continues it (hold: EXEC | hold ENTER; screen: hold
    ENTER | abend ENTER); in every segment the terminal inputs (query replies 0x88 aside) = that log's actions, one
    each (nothing missing, duplicated or sent outside the driver)."""
    if len(logs) != len(texts):
        raise Fail(f'{case}: {len(texts)} trace segments, {len(logs)} driver logs')
    acts = [[(json.loads(x)['category'], json.loads(x)['action']) for x in lg if x.strip()] for lg in logs]
    for n, c in enumerate(cuts):
        if not acts[n] or not acts[n + 1] or (acts[n][-1], acts[n + 1][0]) != LOG_CUT[c]:
            raise Fail(f'{case}: driver logs {n + 1} / {n + 2} are not split at the {c} '
                       f'({acts[n][-1:]} | {acts[n + 1][:1]})')
    for n, (tx, a) in enumerate(zip(texts, acts)):
        ins = [e for e in Z6.parse6(tx)['ev'] if e[1] == '>' and e[3][:1] != b'\x88']
        if len(ins) != len(a):
            raise Fail(f'{case}: segment {n + 1}: {len(ins)} terminal inputs, {len(a)} driver actions')


def check_estae(text, log_lines, case, prefix, cuts=None):
    t = join_traces(*text, case=case, cuts=cuts) if isinstance(text, tuple) else Z6.parse6(text)
    ev = t['ev']
    rep = {'case': case, 'funcs': t['funcs'], 'segments': len(text) if isinstance(text, tuple) else 1}
    log = check_log(log_lines, case)
    acts = [(x['category'], x['action']) for x in log]
    head = [('transition', 'EXEC'), ('transition', 'ENTER'), ('abend', 'ENTER')]
    k = 3
    nrec = 0
    while k < len(acts) and acts[k] == ('recovery', 'ENTER'):
        nrec, k = nrec + 1, k + 1
    if acts[:3] != head or nrec > DV.RECOVERY_MAX or acts[k:k + 1] != [('check', 'LISTALC')]:
        raise Fail(f'{case}: driver log {acts[:k + 1]} is not EXEC, hold ENTER, ENTER, recovery ENTERs, LISTALC')
    k += 1
    nls = 0
    while k < len(acts) and acts[k] == ('check', 'ENTER'):
        nls, k = nls + 1, k + 1
    if nls < 2:
        raise Fail(f'{case}: driver log: {nls} LISTALC ENTERs (the initial hold + at least one output page)')
    cleanup = []
    while k < len(acts) and acts[k][0] == 'cleanup':
        cleanup.append(acts[k])
        k += 1
    if cleanup not in ([], [('cleanup', 'FREE'), ('cleanup', 'ENTER')]):
        raise Fail(f'{case}: cleanup actions {cleanup} (FREE + the ENTER of its hold, or nothing)')
    plan = DV.planned(case)
    if acts[k:] != plan[plan.index(('transition', 'EXEC:GD')):]:
        raise Fail(f'{case}: the follow-up game actions differ from the plan')
    inb = [(i, e) for i, e in enumerate(ev) if e[1] == '>']
    cmd = DV.command(case, 'EXEC', prefix)
    i_exec = next((i for i, e in inb if typed(e[3]) == cmd), None)
    if i_exec is None:
        raise Fail(f'{case}: no EXEC {cmd!r} in the trace')
    Z5.outside_errors(ev[:i_exec])
    screen = f'PACMAN RP.0 ESTAE LIVE TEST - CASE {case}'
    i_scr = next((i for i in range(i_exec, len(ev)) if any(screen in s for s in txt(ev[i]))), None)
    if i_scr is None:
        raise Fail(f'{case}: the RPESTAE test screen of {case} was not sent')
    # EXEC -> the ISPF / TSO `***` hold (exactly one, the last host record before the ENTER) -> exactly one empty
    # ENTER -> the test screen (no `***` and no text record in between)
    between = [(i, ev[i]) for i in range(i_exec + 1, i_scr)]
    ins = [i for i, e in between if e[1] == '>']
    if len(ins) != 1 or ev[ins[0]][3][0] != 0x7D or typed(ev[ins[0]][3]):
        raise Fail(f'{case}: not exactly one ENTER between the EXEC and the test screen ({len(ins)} inputs)')
    i_hold = ins[0]
    stars = [i for i, e in between if e[1] == '<' and any('***' in s for s in txt(e))]
    last_host = max((i for i, e in between if e[1] == '<' and i < i_hold), default=None)
    if len(stars) != 1 or stars[0] != last_host:
        raise Fail(f'{case}: the EXEC is not held by exactly one *** right before its ENTER ({len(stars)} *** records)')
    if any(txt(e) for i, e in between if i > i_hold):
        raise Fail(f'{case}: text written between the hold ENTER and the test screen')
    if txt(ev[i_scr]) != DV.test_screen(case):
        raise Fail(f'{case}: the test screen is not exactly the approved one ({txt(ev[i_scr])})')
    i_ab = next((i for i in range(i_scr + 1, len(ev)) if ev[i][1] == '>'), None)
    if i_ab is None or ev[i_ab][3][0] != 0x7D or typed(ev[i_ab][3]):
        raise Fail(f'{case}: the test screen was not answered by one ENTER')
    i_ls = next((i for i, e in inb if i > i_ab and typed(e[3]) == 'LISTALC STATUS'), None)
    if i_ls is None:
        raise Fail(f'{case}: no LISTALC STATUS after the abend')
    span = ev[i_ab + 1:i_ls]
    if any(e[1] == '>' and (e[3][0] != 0x7D or typed(e[3])) for e in span):
        raise Fail(f'{case}: an input other than ENTER during the recovery')
    if sum(e[1] == '>' for e in span) != nrec:
        raise Fail(f'{case}: {sum(e[1] == ">" for e in span)} recovery ENTERs in the trace, {nrec} in the driver log')
    if any(is_start(e) for e in span) or any(screen in s for e in span for s in txt(e)):
        raise Fail(f'{case}: the test screen / a full-screen start after the abend: line mode not restored')
    lines = [s for e in span for s in txt(e)]
    sign = [i for i, s in enumerate(lines) if ABEND_SIGN.search(s)]
    if not sign:
        raise Fail(f'{case}: no abend indication after the ENTER (expected the forced 0C7)')
    if case == 'E3' and E3_LINE not in lines[:sign[0]]:
        raise Fail(f'{case}: the line {E3_LINE!r} does not precede the abend indication')
    if case != 'E3' and E3_LINE in lines:
        raise Fail(f'{case}: the E3 line in {case}')
    if not any(Z5.SHELL in s for s in lines[sign[-1]:]):
        raise Fail(f'{case}: no return to the {Z5.SHELL} after the abend')
    m = re.search(r'(?:ABEND|COMPLETION CODE)[ =]*(?:CODE)?[ =]*(S?[0-9A-F]{3}|U\d{4})', ' '.join(lines))
    rep.update(recovery_enters=nrec, abend_text=lines[:40], abend_code=m.group(1) if m else None,
               le_messages=sorted({x for s in lines for x in re.findall(r'CEE\d{4}[A-Z]', s)}))
    # LISTALC: the initial hold, its output pages, the shell; the leftover allocations of an interrupted CLIST
    pages, i_sh, nent = held_trace(ev, i_ls, case, 'LISTALC STATUS')
    if nent != nls:
        raise Fail(f'{case}: LISTALC STATUS: {nent} ENTERs in the trace, {nls} in the driver log')
    ltext = [x for p in pages for x in p]
    if not pages or ltext[0] != '--DDNAME---DISP--':
        raise Fail(f'{case}: LISTALC STATUS: no output page, or the first line is not the --DDNAME---DISP-- header')
    try:
        ceeopts = DV.ceeopts_of(ltext, prefix)
    except ValueError as ex:
        raise Fail(f'{case}: LISTALC STATUS: {ex}')
    rep.update(listalc=ltext[:40], listalc_pages=len(pages), ceeopts_left=ceeopts)
    after = next((i for i, e in inb if i > i_sh), None)
    free = after is not None and typed(ev[after][3]) == 'FREE F(CEEOPTS)'
    if free != ceeopts or free != bool(cleanup):
        raise Fail(f'{case}: FREE F(CEEOPTS) {"sent" if free else "not sent"} but CEEOPTS '
                   f'{"listed" if ceeopts else "not listed"} (driver cleanup {cleanup})')
    if free:
        fpages, i_sh, fent = held_trace(ev, after, case, 'FREE F(CEEOPTS)')
        if fpages or fent != 1:
            raise Fail(f'{case}: FREE F(CEEOPTS) answered by output {fpages[:1]}')
        after = next((i for i, e in inb if i > i_sh), None)
    rep['cleanup'] = cleanup
    # the clean follow-up game: the only game start of the trace
    if len(t['starts']) != 1:
        raise Fail(f'{case}: {len(t["starts"])} game starts in the trace (only the follow-up game)')
    gcmd = DV.command(case, 'EXEC:GD', prefix)
    i_g = after if after is not None and typed(ev[after][3]) == gcmd else None
    if i_g is None:
        raise Fail(f'{case}: the next input after the cleanup is not the follow-up game EXEC {gcmd!r}')
    rep['followup'] = turn_game(ev[i_g:], 'GD', gcmd, 'n/a', False, False, prefix)
    rep['state'] = PASS
    return rep


def check_sf_store(pre, post, rec_bytes, expected_bytes):
    """Stage F production state (read-only zos8_batch.state('DATA') before / after the game, the member's bytes as
    downloaded in binary, the expected FB 80 record bytes): before no member at all; after exactly one member HISCORE
    with exactly one record = S.SF_RECORD (text view and the 80 bytes); the dataset attributes unchanged. -> the
    list of failures (empty = PASS)."""
    bad = []
    if pre.get('members') != []:
        bad.append(f'DATA members before {pre.get("members")} (expected none)')
    if post.get('members') != ['HISCORE']:
        bad.append(f'DATA members after {post.get("members")} (expected exactly HISCORE)')
    if post.get('HISCORE') != [S.SF_RECORD.rstrip()]:
        bad.append(f'DATA(HISCORE) records {post.get("HISCORE")} (expected exactly {S.SF_RECORD.rstrip()!r})')
    if len(expected_bytes) != 80 or rec_bytes != expected_bytes:
        bad.append(f'DATA(HISCORE) bytes: {len(rec_bytes)} bytes, equal to the expected FB 80 record: '
                   f'{rec_bytes == expected_bytes}')
    if pre.get('attrs') != post.get('attrs'):
        bad.append(f'DATA attributes changed {pre.get("attrs")} -> {post.get("attrs")}')
    return bad


def check(text, log_lines, case, before='ABSENT', prefix='Z00000.PACMAN', cuts=None):
    kind = DV.PLANS[case]['kind']
    if kind == 'ESTAE':
        return check_estae(text, log_lines, case, prefix, cuts)
    if kind == 'RT':
        return check_rt(text, log_lines, case, before, prefix)
    return check_turn(text, log_lines, case, before, prefix)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True, choices=sorted(DV.PLANS))
    ap.add_argument('--trace', required=True)
    ap.add_argument('--drive-log', required=True)
    ap.add_argument('--trace2', nargs='+', help='Stage D resume: the later trace segment(s), in order')
    ap.add_argument('--drive-log2', nargs='+', help='Stage D resume: the driver log(s) of the resumed run(s)')
    ap.add_argument('--cuts', nargs='+', choices=['hold', 'screen'],
                    help="Stage D resume: the cut points in order (default hold, or hold screen); 'screen' alone "
                         'only when named; with --cuts every trace / log needs a matching <file>.sha256')
    ap.add_argument('--sf-store', nargs=4, metavar=('PRE_JSON', 'POST_JSON', 'MEMBER_BIN', 'EXPECTED_BIN'),
                    help='Stage F: the read-only DATA state before / after and the member / expected record bytes')
    ap.add_argument('--before', default=None, help="the case's store before the case: ABSENT, the record, or n/a")
    ap.add_argument('--prefix', default='Z00000.PACMAN')
    a = ap.parse_args()
    kind = DV.PLANS[a.case]['kind']
    if a.before is None and kind != 'ESTAE' and S.store_of(a.case) not in (None, 'NONE'):
        ap.error('--before (the read-only precheck of the store) is required for this case')
    before = a.before or ('ABSENT' if kind == 'RT' else 'n/a')
    if (a.case == 'SF') != bool(a.sf_store) or (a.case == 'SF' and a.before != 'ABSENT'):
        ap.error('SF needs --before ABSENT and --sf-store; --sf-store is for SF only')
    if bool(a.trace2) != bool(a.drive_log2) or (a.trace2 and kind != 'ESTAE'):
        ap.error('--trace2 and --drive-log2 go together, Stage D only')
    if a.cuts and not a.trace2:
        ap.error('--cuts needs --trace2 / --drive-log2')
    if a.cuts:                                       # every segment and log checksum-verified on its own
        for f in [a.trace, a.drive_log] + a.trace2 + a.drive_log2:
            side = Path(f + '.sha256')
            got = hashlib.sha256(Path(f).read_bytes()).hexdigest()
            want = side.read_text().split()[0] if side.exists() else None
            if want != got:
                print(f'{a.case}: {FAILED}: {f}: SHA-256 {got} does not match {side} ({want})')
                sys.exit(1)
            print(f'{a.case}: {Path(f).name} SHA-256 = {side.name}')
    raw, lg = Path(a.trace).read_bytes(), Path(a.drive_log).read_bytes()
    print(f'{a.case} trace SHA-256 {hashlib.sha256(raw).hexdigest()} ({len(raw)} bytes); driver log SHA-256 '
          f'{hashlib.sha256(lg).hexdigest()}; before {before!r}')
    text, lines = raw.decode('utf-8', 'replace'), lg.decode().splitlines()
    if a.trace2:
        if len(a.trace2) != len(a.drive_log2):
            ap.error('one driver log per later trace segment')
        segs, seglogs = [text], [list(lines)]
        for n, (tf, lf) in enumerate(zip(a.trace2, a.drive_log2), 2):
            raw2, lg2 = Path(tf).read_bytes(), Path(lf).read_bytes()
            print(f'{a.case} trace segment {n} SHA-256 {hashlib.sha256(raw2).hexdigest()} ({len(raw2)} bytes); '
                  f'driver log {n} SHA-256 {hashlib.sha256(lg2).hexdigest()}')
            segs.append(raw2.decode('utf-8', 'replace'))
            seglogs.append(lg2.decode().splitlines())
            lines += lg2.decode().splitlines()
        text = tuple(segs)
    try:
        if a.cuts:
            check_segments(text, seglogs, a.case, tuple(a.cuts))
        rep = check(text, lines, a.case, before, a.prefix, tuple(a.cuts) if a.cuts else None)
    except Fail as e:
        print(f'{a.case}: {FAILED}: {e}')
        sys.exit(1)
    if a.sf_store:
        pre, post = (json.loads(Path(f).read_text()) for f in a.sf_store[:2])
        bad = check_sf_store(pre, post, Path(a.sf_store[2]).read_bytes(), Path(a.sf_store[3]).read_bytes())
        rep['sf_store'] = {'members_before': pre.get('members'), 'members_after': post.get('members'),
                           'HISCORE': post.get('HISCORE'), 'failures': bad}
        if bad:
            print(json.dumps(rep['sf_store'], indent=1))
            print(f'{a.case}: {FAILED}: production state {bad}')
            sys.exit(1)
    show = {k: v for k, v in rep.items() if k not in ('directional', 'funcs')}
    print(json.dumps(show, indent=1, default=str)[:20000])
    print(f'{a.case}: {rep["state"]}' + (f' - {"; ".join(rep.get("blocked", []))}' if rep.get('blocked') else ''))
    sys.exit({PASS: 0, BLOCKED: 2, INCOMPLETE: 3}[rep['state']])


if __name__ == '__main__':
    main()
