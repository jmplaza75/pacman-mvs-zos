#!/usr/bin/env python3
"""ZOS-6: deterministic synthetic c3270 traces (and driver logs) of the approved REALTIME cases R1 / R2
(docs/zos6-design.md) for tools/zowe/zos6_live_check.py.

A small time simulation: the host polls once per quantum on absolute deadlines (h_k = h_1 + (k - 1) x T, re-based at a
resume), every host 3270-DATA record goes out behind a TN3270E BID answered by the terminal (CONTENTION-RESOLUTION,
functions 00 02 04 05 as negotiated on z/OS), the data arrives 170 ms after its host time and the keyboard is locked
from the BID (+60 ms) to the data; the driver waits for the unlock before each key (Wait(5,Unlock)); an AID reaches the
host 50 ms after it was sent and is consumed by the first poll at or after that. The cards that result are replayed
through tests/ref_rt.py (no new oracle): its streams are the PACMAN writes, the end lines are its end lines.
build(case, **inject) -> (trace text, driver log lines). Injections: scale (period factor), gaps (per-quantum host gap
pattern, ms offsets), skip_at (one skipped period after that quantum), delay ({write index: extra network ms}),
resume_burst (host writes after the resume ahead of their deadlines), lose / dup / subst (gameplay AIDs on the wire),
late ({gameplay index: extra ms before the host sees that AID}), midc1 (a TSO line-mode record mid-game), log_drop,
log_mismatch, mutate (write index), drop_write (write index), extra_write ('start' | 'pause'), end_lines (replacement
end lines), no_shell, dt0a (a BID with DATA-TYPE 0A), waits (override plan waits, for short functional tests).
ZOS-6 production design (ZV-D33): present (default: the plan's, R1 / R2 C = PRESENT(COALESCED); E = EVERY, the D33
loop) - with C the host polls every quantum but writes only at the PSLT slots (start / resume base, then every 2nd
NORMAL / 3rd FAST quantum; a pause screen and the end screen as before) and, after each quantum write, does exactly one
post-write poll B whose AID belongs to the next card; visibility ('arrival' or 'write': an AID becomes readable only
after the host's next write, the PR2I-C2 pattern); nonslot (an extra restore-only write before that write index),
replay (the previous frame sent again before that write index), frt (the host freezes that many quanta: a wrong
PACRT), plan (a test-only plan: steps, T, present, kw, cfg = the game configuration, default AI0 1; a plan without Q
ends where the model's game ends - WIN / LOST, possibly on a coalesced quantum)."""
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R / 'tests'), str(R / 'tools/zowe')]
import ref_rt  # noqa: E402
import qry_cases as Q  # noqa: E402
import zos5_fixture as FX  # noqa: E402
from zos6_drive import PLANS, EXPECT  # noqa: E402

UP, DOWN, BIDRTT = 50, 60, 110          # ms: AID terminal -> host; BID host -> terminal; BID response -> data
CRS = [0x00, 0x02, 0x04, 0x05]
QUERY, CLRPFX = FX.QUERY, FX.CLRPFX
SHELL_PANEL = FX.SHELL_PANEL
TRANS_STAR = bytes.fromhex('F1C2115D7F1D4011D9401DC85C5C5C1D4013')      # ISPF / TSO `***` before the game (ZOS-5)
TRANS_CLR = bytes.fromhex('F5C1115D7F1D4011404013')
CARD = {'PF7': 'U', 'PF8': 'D', 'PF9': 'P', 'PF10': 'L', 'PF11': 'R', 'PA2': '*', 'x': 'x', 'Q': 'Q'}


def e(s):
    return s.encode('cp037')


def aid_bytes(action):
    a = EXPECT[action][0]
    if a == 0x7D:
        return bytes([0x7D, 0x5B, 0x6F, 0x11, 0x5B, 0x60]) + e(action)
    return bytes([a, 0x5B, 0x6F])


def build(case, scale=1.0, gaps=None, skip_at=None, delay=None, resume_burst=False, lose=None, dup=None, subst=None,
          log_mismatch=False, mutate=None, drop_write=None, extra_write=None, end_lines=None, no_shell=False,
          dt0a=False, waits=None, prefix='Z00000.PACMAN', late=None, midc1=False, log_drop=None, kri=None,
          kri_rq=0x03, kri_short=False, present=None, visibility='arrival', nonslot=None, replay=None, frt=None,
          plan=None, tso_c3=None):
    plan = plan or PLANS[case]
    present = present or plan.get('present', 'E')
    T = plan['T'] * scale
    steps = list(plan['steps'])
    if waits:
        k = 0
        for i, (kind, v) in enumerate(steps):
            if kind == 'wait':
                steps[i] = ('wait', waits[k] if k < len(waits) else v)
                k += 1
    recs, log = [], []                       # recs: [direction, terminal ms, payload, kind]; kind 'H' host data
    t = [36_000_000]

    def host(p, at):
        recs.append(['<', at, p, 'H'])

    def term(p, at):
        recs.append(['>', at, p, 'T'])

    def logged(cat, act, req, sent):
        log.append({'ordinal': len(log) + 1, 'category': cat, 'action': act, 'requested': req, 'wait_start': req,
                    'unlocked': sent, 'sent': sent, 'result': 'ok'})

    # --- transition: EXEC, ISPF *** handshake, ENTER, then the game start (switch, query, reply, first screen)
    t0 = t[0]
    term(bytes([0x7D, 0x5B, 0x6F, 0x11, 0x5B, 0x60]) + e(f"EXEC '{prefix}.CLIST(PACMAN)' '{plan['kw']}'"), t0)
    logged('transition', 'EXEC', t0, t0)
    host(TRANS_STAR, t0 + 300)
    term(bytes([0x7D, 0xD9, 0xC5]), t0 + 1500)
    logged('transition', 'ENTER', t0 + 1500, t0 + 1500)
    host(TRANS_CLR, t0 + 1700)
    hs = t0 + 1800                           # host time of the size switch
    host(bytes([0x7E, 0xC3]), hs + 170)
    host(QUERY, hs + 171)
    term(Q.rec('dyn'), hs + 175)
    h_first = hs + 250
    # --- the time simulation of the game: polls with host times; gameplay actions with send times
    gameplay = [v for kind, v in steps if kind == 'gameplay']
    wb, acc = [], 0
    for kind, v in steps[steps.index(('expect', 'GAME')) + 1:]:
        if kind == 'wait':
            acc += v * 1000
        elif kind == 'gameplay':
            wb.append(acc)
            acc = 0
    tail_wait = acc                          # the wait after the last gameplay action (a plan without Q: the game ends)
    polls = []                               # [host ms, [actions], kind]  kind: q (quantum), pause, resume, end
    sends = []                               # (terminal send ms, action)
    lock = []                                # terminal keyboard-locked intervals (from, to)
    pattern = gaps or [0]

    def unlock_after(r):
        for x, y in lock:
            if x <= r < y:
                return y + 1
        return r

    def write(h):
        lock.append((h + DOWN, h + DOWN + BIDRTT))
        for x in pending:                    # visibility 'write': readable from the host's next write on
            if x[0] <= h:
                x[2] = True
    ps = {'acc': 0}

    def slot(kind):
        """PACPLAT PSLT for a running poll ('q' start / resume = base)."""
        if present != 'C' or kind in ('base', 'pause', 'end'):
            ps['acc'] = 0
            return True
        ps['acc'] += plan['T']
        if ps['acc'] >= 300:
            ps['acc'] = 0
            return True
        return False

    def visible(x, h):
        return x[0] <= h and (visibility == 'arrival' or x[2])

    def send(i, cursor):
        req = cursor + wb[i]
        sent = unlock_after(req)
        sends.append((sent, gameplay[i]))
        logged('gameplay', gameplay[i], req, sent)
        return sent
    cursor = h_first + DOWN + BIDRTT + 1     # terminal time the first screen is usable
    i, state, base, k, pending, carry, pres = 0, 'pre', 0, 0, [], [], []
    while True:
        if state in ('pre', 'paused'):       # blocking read: the next action is read when it arrives
            cursor = send(i, cursor)
            arr = cursor + UP
            i += 1
            if state == 'pre':
                polls.append([arr, [gameplay[i - 1]], 'q'])
            else:                            # the resume card is also the first quantum after it (CLOK, rq)
                polls.append([arr, [gameplay[i - 1]], 'resume'])
            slot('base')
            pres.append(True)
            write(arr)
            base, k = arr, 1
            state = 'run'
            continue
        hk = base + k * T + pattern[len(polls) % len(pattern)]
        if skip_at is not None and len(polls) > skip_at:
            hk += T
        if resume_burst and any(p[2] == 'resume' for p in polls[-3:]):
            hk = base + 5 * k
        k += 1
        while i < len(gameplay) and cursor + wb[i] < hk + DOWN:
            cursor = send(i, cursor)
            pending.append([cursor + UP + (late or {}).get(i, 0), gameplay[i], False])
            i += 1
        took = carry + [x[1] for x in pending if visible(x, hk)]
        pending, carry = [x for x in pending if not visible(x, hk)], []
        kind = 'end' if 'Q' in took else 'pause' if 'PF9' in took else 'q'
        polls.append([hk, took, kind])
        pres.append(slot(kind))
        if pres[-1]:
            write(hk)
        if pres[-1] and kind == 'q' and present == 'C':      # phase B: exactly one post-write poll (one AID at most)
            b = next((x for x in pending if visible(x, hk + 1)), None)
            if b is not None:
                pending.remove(b)
                carry = [b[1]]
        if kind == 'end':
            break
        if i == len(gameplay) and 'Q' not in gameplay and hk > cursor + tail_wait:
            break                            # no Q in the plan: the model decides where the game ended (below)
        if kind == 'pause':
            state = 'paused'
            cursor = max(cursor, hk + DOWN + BIDRTT + 1)
    # --- cards for the model: one per poll; the pause poll's card holds P, the resume read is its own card
    cards = []
    for hk, took, kind in polls:
        cards.append(''.join(CARD[a] for a in took) or '.')
    full = set()
    import ref_gx_screen as gx
    real_full = gx.full

    def tagged(*a, **kw):
        b = real_full(*a, **kw)
        full.add(b)
        return b
    gx.full = tagged
    try:
        out, frames = ref_rt.tsd([plan.get('cfg', 'AI0 1')] + cards, 'W', per=plan['T'], present=present, frt=frt)
    finally:
        gx.full = real_full
    fc = list(frames.cards)
    if out[-5] in ('LOST', 'WIN'):           # the game ended at card fc[-1]: the polls after it never happened
        ce = fc[-1]
        polls, cards, pres = polls[:ce], cards[:ce], pres[:ce]
        assert fc[1:] == [n + 1 for n, w in enumerate(pres) if w] + [ce], 'fixture slots != model slots (end)'
    else:
        assert fc[1:] == [n + 1 for n, w in enumerate(pres) if w], 'fixture slots != model slots'
    writes_host = [h_first] + [polls[c - 1][0] for c in fc[1:]]
    assert len(frames) == len(writes_host), (len(frames), len(writes_host))
    # --- host records: BID, then the data; terminal: the BID response, the data response
    arrivals = []
    for i, (hk, f) in enumerate(zip(writes_host, frames)):
        arr = hk + DOWN + BIDRTT + (delay or {}).get(i, 0)
        if arrivals and arr <= arrivals[-1]:
            arr = arrivals[-1] + 1
        arrivals.append(arr)
        if i == 0:
            p = bytes([0xF1]) + f[:1] + CLRPFX + f[1:]
        elif f in full:
            p = bytes([0x7E]) + f
        else:
            p = bytes([0xF1]) + f
        if mutate == i:
            p = p[:-1] + bytes([p[-1] ^ 0x01])
        if drop_write == i:
            continue
        if tso_c3 == 'replace' and i == len(writes_host) // 2:
            p = b'\xf1\xc3'
        if nonslot == i:                     # an extra write at a coalesced (non-slot) quantum before write i
            host(bytes([0xF1, 0xC2, 0x28, 0x00, 0x00]), int(arr) - 150)
        if replay == i:                      # the previous (stale) frame sent again before write i
            host(prev_p, int(arr) - 150)
        prev_p = p
        host(p, int(arr))
    if kri:                                  # empty 3270-DATA SEND-DATA / KEYBOARD-RESTORE controls (z/OS, R1-T3)
        for i in range(kri, len(arrivals) - 1, kri):
            recs.append(['<', int(arrivals[i]) + 20, b'', 'C', kri_rq, kri_short])
    if midc1:                                # an unexpected TSO line-mode record in the middle of the game
        host(bytes([0xF1, 0xC1, 0x11, 0x40, 0x40]) + e('LINE OUTPUT'), int(arrivals[len(arrivals) // 2]) + 5)
    # TSO blocking-read control (`F1 C3`): tso_c3 = 'blocking' (after the start and the resume AID, as R1-T4),
    # 'unrelated' (in the running loop), 'dup' (two after the start), 'other2' (F1 C2 after the start), 'replace'
    # (a real quantum write replaced by F1 C3)
    if tso_c3:
        blk = [s for s, a in sends][:1] + [s for (s, a) in sends if a == 'PF9'][1::2]
        if tso_c3 in ('blocking', 'dup', 'other2'):
            for at in (blk if tso_c3 == 'blocking' else blk[:1]):
                host(b'\xf1\xc2' if tso_c3 == 'other2' else b'\xf1\xc3', at + UP + 5)
                if tso_c3 == 'dup':
                    host(b'\xf1\xc3', at + UP + 6)
        elif tso_c3 == 'unrelated':
            host(b'\xf1\xc3', int(arrivals[len(arrivals) // 2]) + 40)
    if extra_write == 'start':
        host(bytes([0xF1, 0xC2, 0x28, 0x00, 0x00]), int(arrivals[0]) + 500)
    if extra_write == 'pause':
        ip = [p[2] for p in polls].index('pause') + 1
        host(bytes([0xF1, 0xC2, 0x28, 0x00, 0x00]), int(arrivals[ip]) + 5000)
    for n, (sent, action) in enumerate(sends):
        if lose == n:
            continue
        b = aid_bytes(action)
        if subst == n:
            b = aid_bytes({'PF7': 'PF8', 'PF8': 'PF7', 'PF10': 'PF11', 'PF11': 'PF10'}.get(action, 'PF8'))
        term(b, sent)
        if dup == n:
            term(b, sent + 2)
    end_at = int(arrivals[-1]) + 3000
    lines = end_lines or out[-5:]
    host(bytes([0x7E, 0xC1]) + b''.join(bytes([0x11, 0x40 + i, 0x40]) + e(s) for i, s in enumerate(lines)), end_at)
    host(bytes.fromhex('F1C2115D7F1D4011D9401DC85C5C5C1D4013'), end_at + 110)
    term(bytes([0x7D, 0xC7, 0xE5]), end_at + 4000)
    logged('closure', 'ENTER', end_at + 4000, end_at + 4000)
    if not no_shell:
        host(SHELL_PANEL, end_at + 4200)
    if log_drop is not None:
        del log[log_drop]
        for n, x in enumerate(log, 1):
            x['ordinal'] = n
    if log_mismatch:
        g = [x for x in log if x['category'] == 'gameplay']
        g[1]['action'] = 'PF7' if g[1]['action'] != 'PF7' else 'PF8'
    return render(recs, lock, dt0a), [json.dumps(x) for x in log]


def render(recs, lock, dt0a=False):
    """Every host 3270-DATA record behind a BID; terminal RESPONSEs; c3270-style trace lines with kybd lock lines."""
    items = []
    seq, last = 0, 0
    for rec in sorted(recs, key=lambda r: r[1]):
        d, at, p, kind = rec[:4]
        if d == '<' and kind == 'C':                     # a control record: no BID, explicit REQUEST-FLAG, no data
            at = max(at, last + 1)
            last = at
            hdr = bytes([0x00, rec[4], 0x02]) + seq.to_bytes(2, 'big')
            items.append((at, '<', hdr[:3] if rec[5] else hdr))
            items.append((at + 1, '>', bytes([0x02, 0, 0]) + seq.to_bytes(2, 'big') + b'\x00'))
            items.append((at, 'K', 'unlock'))
            seq += 1
            continue
        if d == '<':                         # the server sends the next BID only after the previous data record
            bid_at = max(at - BIDRTT, last + 1)
            at = max(at, bid_at + 2)
            last = at
            hdr_bid = bytes([0x0A if dt0a and seq == 20 else 0x09, 0x00, 0x02]) + seq.to_bytes(2, 'big')
            items.append((bid_at, '<', hdr_bid))
            items.append((bid_at + 1, '>', bytes([0x02, 0, 0]) + seq.to_bytes(2, 'big') + b'\x00'))
            items.append((bid_at, 'K', 'lock'))
            seq += 1
            items.append((at, '<', bytes([0x00, 0x03, 0x02]) + seq.to_bytes(2, 'big') + p))
            items.append((at + 1, '>', bytes([0x02, 0, 0]) + seq.to_bytes(2, 'big') + b'\x00'))
            items.append((at, 'K', 'unlock'))
            seq += 1
        else:
            items.append((at, '>', bytes(5) + p))
    items.sort(key=lambda x: (x[0], {'<': 0, 'K': 1, '>': 2}[x[1]]))
    out = ['20261017.095959.000 infra  Trace started (synthetic ZOS-6 fixture)', ' TELNET state:',
           '< 0x0   fffd28fffa2802044942' + '4d2d44594e414d4943fff0', '< 0x0   fffa280304' + bytes(CRS).hex() + 'fff0',
           ' Screen contents (TN3270E-3270) unformatted:']
    out += FX.dump('<', bytes(5) + b'\x05\x02' + e('ISPF Command Shell') + bytes(40))
    out.append(' Data stream:')
    for at, d, b in items:
        at = int(at)
        if d == 'K':
            out.append(f'{FX.stamp(at)} kybd   Keyboard lock(kybd_bid) none +BID -> BID' if b == 'lock' else
                       f'{FX.stamp(at)} kybd   Keyboard unlock(kybd_send_data) BID -BID -> none')
            continue
        w = b.replace(b'\xff', b'\xff\xff') + b'\xff\xef'
        out.append(f'{FX.stamp(at)} socket Host socket read complete nr={len(w)}' if d == '<' else
                   f'{FX.stamp(at)} tn3270 SENT TN3270E(3270-DATA NO-RESPONSE 0)')
        out += FX.dump(d, w)
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    for c in ('R1', 'R2'):
        text, lg = build(c)
        print(c, len(text.splitlines()), 'trace lines,', len(lg), 'driver actions')
