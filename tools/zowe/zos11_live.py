#!/usr/bin/env python3
"""ZOS-11 (2.1-zos, D46; docs/zos11-design.md) live gate of REALTIME Right on PF12: plan, driver and checker.

Successor of the frozen ZOS-6 live tools for the 2.1 key map: tools/zowe/zos6_drive.py and zos6_live_check.py are
imported and used unchanged (their Driver class, check(), parse6, the COALESCED model, the timing rules); the 2.1 map
is supplied in this process only, as tools/zowe/zos10_release.py did for S10. Nothing here touches z/OS by itself:
the driver acts only through the c3270 script port of a session the user logged on.

Plan Z11 (installed CLIST, no PLAY / PRESENT: the REALTIME default COALESCED; RULES(CLASSIC): no high-score path):
PF8, PF10, PF11 (2.0: Right; 2.1: nothing), PF12 (Right), PF7, PF9 pause / PF9 resume, PA2, the PF1-PF24 sweep
(PF1-PF6, PF11, PF13-PF24: nothing), PF12, a 40 s idle stretch (the principal timing segment), then TYPEQ (`Q` typed
into the command field, no AID) with a 3 s hold, then ENTER. Categories: gameplay = consumed by the game; ignored =
an AID the 2.1 game must ignore; hold = TYPEQ (no AID). The ENTER after the hold: if the typed Q is still in the field
it is gameplay `Q` (Q + ENTER quits); if a host write erased it, it is gameplay `ENTER()` (a blank ENTER = redraw) and
the driver then sends a fresh `Q` + ENTER (gameplay `Q`). The driver records which; the checker uses the driver log.
The Q decision reads the game's input field itself (q_field: the text after `COMMAND ===>` on a full Ascii() of the
screen), never the cursor: attempt 1 (2026-10-21) showed that the game's writes move the cursor (Q at row 25 column
33, cursor 25 / 35), so a cursor-relative probe mistook a surviving Q for an erased one.

Checker (`--check`): the frozen check() on the trace with the ignored AIDs removed from the game input (each one
proven separately: AID-only record, the game wrote on after it), the 2.1 map (PF12 X'7C' = R) and case name Z11 (the
R1-only death rules do not apply; every other functional and timing rule does). Gate:
  every live write = the COALESCED model with the 2.1 map (check() state PASS; BLOCKED = environment / timing);
  controls - the same trace FAILS check() with the 2.0 map (PF11 R, PF12 ignored), with PF12 ignored and with PF11 as
  Right (so PF12 moved right and PF11 did not);
  PF12 / PF11 / every swept PF key reached the host as an AID-only record and the game wrote on after each;
  TYPEQ -> ENTER: no inbound record and >= 5 game writes in between (Q alone does not quit);
  the end: model end lines QUIT after the last ENTER (Q + ENTER quits), `***`, the ISPF Command Shell.
Usage: zos11_live.py --drive PORT LOG [--prefix P]     zos11_live.py --check TRACE LOG [--prefix P]"""
import argparse
import copy
import datetime
import hashlib
import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zos6_drive as D  # noqa: E402
import zos6_live_check as C  # noqa: E402

CASE = 'Z11'
KW = 'AI(0) RULES(CLASSIC) SOUND(NO)'
PF_AID = {**{f'PF{n}': 0xF0 + n for n in range(1, 10)}, 'PF10': 0x7A, 'PF11': 0x7B, 'PF12': 0x7C,
          **{f'PF{n}': 0xC1 + n - 13 for n in range(13, 22)}, 'PF22': 0x4A, 'PF23': 0x4B, 'PF24': 0x4C}
SWEEP = ['PF1', 'PF2', 'PF3', 'PF4', 'PF5', 'PF6', 'PF11'] + [f'PF{n}' for n in range(13, 25)]
STEPS = ([('transition', 'EXEC'), ('expect', '***'), ('transition', 'ENTER'), ('expect', 'GAME'), ('wait', 5),
          ('gameplay', 'PF8'), ('wait', 1.5), ('gameplay', 'PF10'), ('wait', 1.5), ('ignored', 'PF11'), ('wait', 1.5),
          ('gameplay', 'PF12'), ('wait', 1.5), ('gameplay', 'PF7'), ('wait', 1.5), ('gameplay', 'PF9'), ('wait', 3),
          ('gameplay', 'PF9'), ('wait', 2), ('gameplay', 'PA2'), ('wait', 2)]
         + [x for k in SWEEP for x in (('ignored', k), ('wait', 0.5))]
         + [('gameplay', 'PF12'), ('wait', 40), ('hold', 'TYPEQ'), ('wait', 3), ('gameplay', 'QENTER'),
            ('expect', '***'), ('closure', 'ENTER'), ('expect', 'SHELL')])
PLAN = {'T': 150, 'present': 'C', 'kw': KW, 'cfg': 'AI0 1', 'steps': STEPS}
MAP21 = {'PF12': 'R'}                        # 2.1: PF12 = Right, PF11 = ignored (PF7 PF8 PF9 PF10 PA2 as 2.0)


def plan_from_log(log, plan=PLAN):
    """The plan of this run: QENTER resolved by the driver log (variant A `Q`, or B `ENTER()` + fresh `Q`); None when
    the log does not end that way (the run is then not the Z11 plan: no model replay, the gate fails)."""
    acts = [x['action'] for x in log if x['category'] == 'gameplay']
    tail = acts[len([a for k, a in plan['steps'] if k == 'gameplay']) - 1:]
    if tail not in (['Q'], ['ENTER()', 'Q']):
        return None
    steps = []
    for k, v in plan['steps']:
        steps += [(k, a) for a in tail] if v == 'QENTER' else [(k, v)]
    return dict(plan, steps=steps)


@contextmanager
def keymap(rights=('PF12',)):
    """The checker's key map for one run: `rights` = the PF keys that move Right (2.1: PF12; the controls: PF11 = 2.0,
    none = PF12 ignored, PF11 + PF12); every other PF key except PF7 PF8 PF9 PF10 is removed from the game input.
    Restores the frozen tables afterwards."""
    ignored = {k for k in PF_AID if k not in ('PF7', 'PF8', 'PF9', 'PF10') + tuple(rights)}
    ign_aids = {PF_AID[k] for k in ignored}
    saved = (dict(D.EXPECT), dict(C.AID_ACTION), C.DIRS, C.parse6)
    orig_parse6 = C.parse6

    def parse_ign(text):
        t = orig_parse6(text)
        if t['starts']:
            s0 = t['starts'][0]
            keep = [e for k, e in enumerate(t['ev'])
                    if not (k > s0 and e[1] == '>' and e[3][:1] and e[3][0] in ign_aids)]
            t = dict(t, ev=keep, starts=[k for k, e in enumerate(keep) if e is t['ev'][s0]] + [
                k for k, e in enumerate(keep) if any(e is t['ev'][s] for s in t['starts'][1:])])
        return t
    try:
        for k, a in PF_AID.items():
            C.AID_ACTION[a] = k
        D.EXPECT.pop('PF11', None)
        for k in rights:
            D.EXPECT[k] = (PF_AID[k], 'R')
        D.EXPECT['ENTER()'] = (0x7D, '*')        # a blank ENTER = RT-ENTER RDR = the model's redraw card
        C.DIRS = ('PF7', 'PF8', 'PF10') + tuple(rights)
        C.parse6 = parse_ign
        yield ignored
    finally:
        D.EXPECT.clear()
        D.EXPECT.update(saved[0])
        C.AID_ACTION.clear()
        C.AID_ACTION.update(saved[1])
        C.DIRS, C.parse6 = saved[2], saved[3]


def checker_plan(plan, ignored):
    """The plan as the frozen check() sees it: keys removed from the input become category `ignored` (not gameplay)."""
    return dict(plan, steps=[('ignored' if (k in ('gameplay', 'ignored') and v in ignored) else
                              'gameplay' if k == 'ignored' else k, v) for k, v in plan['steps']])


def relog(log, ignored):
    out = copy.deepcopy(log)
    for x in out:
        if x['category'] in ('gameplay', 'ignored') and x['action'] in ignored:
            x['category'] = 'ignored'
        elif x['category'] == 'ignored':
            x['category'] = 'gameplay'
    return out


def run_check(text, log, plan, rights=('PF12',), prefix='Z00000.PACMAN'):
    """-> (report or None, error or None) of the frozen check() under one key map."""
    with keymap(rights) as ign:
        try:
            lines = [json.dumps(x) for x in relog(log, ign)]
            return C.check(text, lines, CASE, prefix, plan=checker_plan(plan, ign)), None
        except C.Fail as e:
            return None, str(e)


def tod_ms(epoch_ms):
    d = datetime.datetime.fromtimestamp(epoch_ms / 1000)
    return ((d.hour * 60 + d.minute) * 60 + d.second) * 1000 + d.microsecond // 1000


def gate(text, log_lines, prefix='Z00000.PACMAN', epoch=True):
    """-> (ok, results, report): the ZOS-11 acceptance on one trace and its driver log. epoch: the driver log times
    are epoch ms (live); False: they are already the trace's time-of-day ms (synthetic tests)."""
    log = [json.loads(x) for x in log_lines if x.strip()]
    plan = plan_from_log(log)
    if plan is None:                              # not the Z11 plan: no replay, every model / control criterion fails
        rep, err, c20, c_no12, c_11r = None, 'the driver log does not end with Q or ENTER() + Q', None, None, None
    else:
        rep, err = run_check(text, log, plan, prefix=prefix)
        c20 = run_check(text, log, plan, rights=('PF11',))[1]
        c_no12 = run_check(text, log, plan, rights=())[1]
        c_11r = run_check(text, log, plan, rights=('PF11', 'PF12'))[1]
    t = C.parse6(text)
    ev, s0 = t['ev'], t['starts'][0] if t['starts'] else 0
    gend = next((k for k in range(s0 + 1, len(ev)) if ev[k][1] == '<' and ev[k][3][1:2] == b'\xc1'), len(ev))
    game = ev[s0:gend]
    writes = [C.ms(e[2]) for e in game if e[1] == '<']
    inb = [(C.ms(e[2]), e[3]) for e in game if e[1] == '>']
    rev = {a: k for k, a in PF_AID.items()}
    pf = [(tm, rev[p[0]], p) for tm, p in inb if p[:1] and p[0] in rev]
    conv = tod_ms if epoch else (lambda x: x)
    tq = next((conv(x['sent']) for x in log if x['action'] == 'TYPEQ'), None)
    ten = next((conv(x['sent']) for x in log if x['category'] == 'gameplay' and x['action'] in ('Q', 'ENTER()')
                and tq is not None and conv(x['sent']) > tq), None)
    variant = ('A (typed Q survived, ENTER quit)' if not any(x['action'] == 'ENTER()' for x in log) else
               'B (typed Q erased, blank ENTER redraw, fresh Q + ENTER quit)')
    res = {
        'every live write = the COALESCED model with the 2.1 map (check() PASS)':
            rep is not None and rep['state'] == C.PASS,
        'control: the 2.0 map (PF11 R, PF12 ignored) fails': c20 is not None,
        'control: PF12 ignored fails (PF12 moved Right)': c_no12 is not None,
        'control: PF11 as Right fails (PF11 did not move)': c_11r is not None,
        'PF12 reached the host as AID-only records (no ENTER)': any(n == 'PF12' for _, n, _ in pf) and
            all(len(p) == 3 for _, n, p in pf if n == 'PF12'),
        'PF11 and the PF1-PF24 sweep reached the host as AID-only records': {n for _, n, _ in pf} >= set(SWEEP) and
            all(len(p) == 3 for _, n, p in pf),
        'the game wrote on after every PF AID (no PF key quits)': bool(pf) and
            all(sum(1 for w in writes if w > tm) >= 2 for tm, _, _ in pf),
        'TYPEQ -> ENTER: no inbound record, >= 5 game writes (Q alone does not quit)': tq is not None and
            ten is not None and not any(tq <= tm < ten for tm, _ in inb) and
            sum(1 for w in writes if tq <= w < ten) >= 5,
        'end: QUIT end lines after the last ENTER (Q + ENTER quits)':
            rep is not None and rep['end_lines'][:1] == ['QUIT'],
    }
    blocked = rep is not None and rep['state'] != C.PASS
    detail = {'state': rep['state'] if rep else C.FAILED, 'error': err, 'blocked': rep['blocked'] if rep else [],
              'controls': {'2.0 map': c20, 'PF12 ignored': c_no12, 'PF11 as Right': c_11r},
              'variant': variant, 'pf_aids': [n for _, n, _ in pf],
              'writes TYPEQ->ENTER': sum(1 for w in writes if tq is not None and ten is not None and tq <= w < ten)}
    return all(res.values()), res, detail, blocked, rep


FIELD_MARK = 'COMMAND ===>'


def q_field(screen):
    """Full Ascii() screen -> the content of the game's input field: the text after the single `COMMAND ===>` row's
    marker (the next column is the field attribute, shown blank), stripped. No cursor is involved. Raises D.Stop when
    the marker row is not exactly one (not the game screen) - the driver never guesses."""
    rows = [r for r in screen.split('\n') if FIELD_MARK in r]
    if len(rows) != 1:
        raise D.Stop(f'{len(rows)} rows with {FIELD_MARK!r} on the screen (exactly 1 required)')
    return rows[0].split(FIELD_MARK, 1)[1].strip()


def q_decision(screen):
    """'enter' when the typed Q is still in the field (send ENTER: it carries the Q), 'fallback' when the field is
    empty (a host write erased it: the designed blank ENTER, then a fresh Q + ENTER); any other content -> D.Stop."""
    content = q_field(screen)
    if content == 'Q':
        return 'enter'
    if content == '':
        return 'fallback'
    raise D.Stop(f'unexpected input-field content {content!r} after the Q hold')


def drive(port, log_path, prefix='Z00000.PACMAN'):
    """The Z11 plan once through the c3270 script port (logged-on ISPF Command Shell; never logs on, never retries)."""
    calls = {**{k: [f'PF({int(k[2:])})'] for k in PF_AID}, 'PA2': ['PA(2)'], 'TYPEQ': ['String("Q")'],
             'ENTER': ['Enter()']}
    with open(log_path, 'x') as log:
        d = D.Driver(port, log)
        if D.SHELL not in d.screen():
            raise D.Stop('the ISPF Command Shell is not on the screen')
        for kind, v in STEPS:
            if kind == 'wait':
                time.sleep(v)
            elif kind == 'expect':
                d.expect(v, {'GAME': 30, 'SHELL': 60, '***': 60}[v])
            elif v == 'EXEC':
                d.act(kind, 'EXEC', [f'String("EXEC \'{prefix}.CLIST(PACMAN)\' \'{KW}\'")', 'Enter()'])
            elif v == 'QENTER':
                d.x('Wait(5,Unlock)', timeout=15)
                still = q_decision(d.screen()) == 'enter'      # the field itself, not the cursor
                d.act('gameplay', 'Q' if still else 'ENTER()', ['Enter()'])
                if not still:                    # variant B: the blank ENTER redraws; a fresh Q + ENTER quits
                    time.sleep(3)
                    d.act('gameplay', 'Q', ['String("Q")', 'Enter()'])
            else:
                d.act(kind, v, calls[v])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--drive', nargs=2, metavar=('PORT', 'LOG'))
    ap.add_argument('--check', nargs=2, metavar=('TRACE', 'LOG'))
    ap.add_argument('--prefix', default='Z00000.PACMAN')
    a = ap.parse_args()
    if a.drive:
        try:
            drive(a.drive[0], a.drive[1], a.prefix)
        except D.Stop as e:
            print(f'ZOS-11 DRIVER STOP: {e}')
            sys.exit(1)
        print('ZOS-11 DRIVER: plan sent completely; stop the trace now (Trace(Off))')
        return
    raw, lg = Path(a.check[0]).read_bytes(), Path(a.check[1]).read_bytes()
    print(f'trace SHA-256 {hashlib.sha256(raw).hexdigest()} ({len(raw)} bytes); driver log SHA-256 '
          f'{hashlib.sha256(lg).hexdigest()}')
    ok, res, det, blocked, rep = gate(raw.decode('utf-8', 'replace'), lg.decode().splitlines(), a.prefix)
    for k, v in res.items():
        print(f'{"PASS" if v else "FAIL"}  {k}')
    for k, v in det.items():
        print(f'  {k}: {v}')
    if rep:
        print(f'  principal segment: {json.dumps(rep.get("principal"))}')
        print(f'  input reaction: {json.dumps(rep.get("reaction"))}')
    state = 'PASS' if ok else ('ENVIRONMENT/TIMING BLOCKED' if blocked and all(
        v for k, v in res.items() if not k.startswith('every live write')) else 'FAIL')
    print(f'ZOS-11 LIVE GATE {state}')
    sys.exit(0 if ok else (2 if state.startswith('ENV') else 1))


if __name__ == '__main__':
    main()
