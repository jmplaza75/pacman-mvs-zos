#!/usr/bin/env python3
"""ZOS-7: deterministic synthetic c3270 traces (and driver logs) of the ARCADE live cases L1 / L2 / L3
(docs/zos7-design.md) for tools/zowe/zos7_live_check.py. The ZOS-6 fixture (tests/zos6_fixture.py, frozen) supplies the
trace renderer (BID per host record, RESPONSEs, kybd lines), the transition / closure records and the timing constants;
the game streams come from the independent models (ref_rt + ref_gp2 REALTIME, ref_gx_screen + ref_gp2 TURN).

REALTIME (L2 / L3): the ZOS-6 time simulation - polls on absolute deadlines, PRESENT(COALESCED) slots (start base,
then every 2nd / 3rd quantum), one post-write poll B, the driver's waits after each send + Wait(Unlock); the game ends
where the model's game ends (LOST, no Q); then the FINAL-DEATH writes one period apart (PACDISP CLOK / WDLN) and the
end screen; the ARCADE end lines + the high-score lines in line mode, ***, ENTER, the shell.
TURN (L1): one typed command + ENTER after each unlock, the next screen 20 ms after the host saw it.
build(case, **inject) -> (trace text, driver log lines). Injections: hiscore (the DATA state the host read; default
ABSENT), mutate / drop_write (write index), nonslot / replay (an extra restore-only / a repeated write before that
write index), fd_dup (one final-death write sent twice), fd_drop (one final-death write missing), fd_mid (a copy of
the first final-death frame inside the game), end_lines (replacement line-mode end lines), tso_c3 ('blocking' after
the start AID, 'unrelated', 'dup'), lose (a gameplay AID lost), frt (the host freezes that many quanta), scale (host
period factor), waits (override the plan's waits), kw (the EXEC operands typed)."""
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R / 'tests'), str(R / 'tools/zowe')]
import qry_cases as Q  # noqa: E402
import zos6_fixture as F6  # noqa: E402
import zos7_live_check as Z7  # noqa: E402
from zos7_drive import PLANS, EXPECT  # noqa: E402

UP, DOWN, BIDRTT = F6.UP, F6.DOWN, F6.BIDRTT
e = F6.e
CARD = {'PF7': 'U', 'PF8': 'D', 'PF9': 'P', 'PF10': 'L', 'PF11': 'R', 'PA2': '*', 'x': 'x', 'Q': 'Q'}


def aid_bytes(action):
    a = EXPECT[action][0]
    if a == 0x7D:
        return bytes([0x7D, 0x5B, 0x6F, 0x11, 0x5B, 0x60]) + e(action)
    return bytes([a, 0x5B, 0x6F])


def payload(i, f, full):
    if i == 0:
        return bytes([0xF1]) + f[:1] + F6.CLRPFX + f[1:]
    return bytes([0x7E if f in full else 0xF1]) + f


def build(case, hiscore='ABSENT', mutate=None, drop_write=None, nonslot=None, replay=None, fd_dup=None, fd_drop=None,
          fd_mid=False, end_lines=None, tso_c3=None, lose=None, frt=None, scale=1.0, waits=None, kw=None,
          prefix='Z00000.PACMAN'):
    plan = PLANS[case]
    steps = list(plan['steps'])
    if waits:
        k = 0
        for i, (kind, v) in enumerate(steps):
            if kind == 'wait':
                steps[i] = ('wait', waits[k] if k < len(waits) else v)
                k += 1
    recs, log = [], []
    t0 = 36_000_000

    def host(p, at):
        recs.append(['<', at, p, 'H'])

    def term(p, at):
        recs.append(['>', at, p, 'T'])

    def logged(cat, act, req, sent):
        log.append({'ordinal': len(log) + 1, 'category': cat, 'action': act, 'requested': req, 'wait_start': req,
                    'unlocked': sent, 'sent': sent, 'result': 'ok'})
    term(bytes([0x7D, 0x5B, 0x6F, 0x11, 0x5B, 0x60]) + e(f"EXEC '{prefix}.CLIST(PACMAN)' '{kw or plan['kw']}'"), t0)
    logged('transition', 'EXEC', t0, t0)
    host(F6.TRANS_STAR, t0 + 300)
    term(bytes([0x7D, 0xD9, 0xC5]), t0 + 1500)
    logged('transition', 'ENTER', t0 + 1500, t0 + 1500)
    host(F6.TRANS_CLR, t0 + 1700)
    hsw = t0 + 1800
    host(bytes([0x7E, 0xC3]), hsw + 170)
    host(F6.QUERY, hsw + 171)
    term(Q.rec('dyn'), hsw + 175)
    h_first = hsw + 250
    gameplay = [v for kind, v in steps if kind == 'gameplay']
    _, hs = Z7.hs_state(hiscore, plan['start'])
    lock, sends = [], []

    def unlock_after(r):
        for x, y in lock:
            if x <= r < y:
                return y + 1
        return r

    def write(h):
        lock.append((h + DOWN, h + DOWN + BIDRTT))
    if plan['play'] == 'T':
        mod = Z7.model_turn([EXPECT[a][1] for a in gameplay], 'W', plan['start'], hs, plan['cfg'])
        frames, full, out = mod['frames'], mod['full'], mod['out']
        assert len(frames) == len(gameplay) + 1, (len(frames), len(gameplay))
        hw = [h_first]
        write(h_first)
        cursor = h_first + DOWN + BIDRTT + 1
        for a in gameplay:
            sent = unlock_after(cursor + 300)
            sends.append((sent, a))
            logged('gameplay', a, cursor + 300, sent)
            hw.append(sent + UP + 20)
            write(hw[-1])
            cursor = hw[-1] + DOWN + BIDRTT + 1
        arrivals = [h + DOWN + BIDRTT for h in hw]
        fd_idx = []
    else:
        T = plan['T'] * scale
        wb, acc = [], 0
        for kind, v in steps[steps.index(('expect', 'GAME')) + 1:]:
            if kind == 'wait':
                acc += v * 1000
            elif kind == 'gameplay':
                wb.append(acc)
                acc = 0
        polls, pending, carry, pres = [], [], [], []
        ps = {'acc': 0}

        def slot(kind):
            if kind == 'base':
                ps['acc'] = 0
                return True
            ps['acc'] += plan['T']
            if ps['acc'] >= 300:
                ps['acc'] = 0
                return True
            return False

        def send(i, cursor):
            req = cursor + wb[i]
            sent = unlock_after(req)
            sends.append((sent, gameplay[i]))
            logged('gameplay', gameplay[i], req, sent)
            return sent
        cursor = h_first + DOWN + BIDRTT + 1
        cursor = send(0, cursor)
        arr = cursor + UP
        polls.append([arr, [gameplay[0]]])
        slot('base')
        pres.append(True)
        write(arr)
        base, k, i = arr, 1, 1
        while True:
            hk = base + k * T
            k += 1
            while i < len(gameplay) and cursor + wb[i] < hk + DOWN:
                cursor = send(i, cursor)
                pending.append([cursor + UP, gameplay[i]])
                i += 1
            took = carry + [x[1] for x in pending if x[0] <= hk]
            pending, carry = [x for x in pending if x[0] > hk], []
            polls.append([hk, took])
            pres.append(slot('q'))
            if pres[-1]:
                write(hk)
                b = next((x for x in pending if x[0] <= hk + 1), None)
                if b is not None:
                    pending.remove(b)
                    carry = [b[1]]
            if i == len(gameplay) and hk > cursor + 15000:
                break
        cards = [''.join(CARD[a] for a in took) or '.' for _, took in polls]
        mod = Z7.model_rt(cards, 'W', plan['T'], plan['start'], hs, 'C', frt, plan['cfg'])
        frames, full, out, qs, fc, kinds = (mod[x] for x in ('frames', 'full', 'out', 'qs', 'fc', 'kinds'))
        qi, fd_idx, je = Z7.classify(kinds, qs, out[0])
        ce = fc[-1]
        assert [fc[j] for j in qi] == [n + 1 for n, w in enumerate(pres[:ce]) if w], 'fixture slots != model slots'
        h_end = polls[ce - 1][0]
        hw = [h_first]
        for j in range(1, len(frames)):
            if j in qi:
                hw.append(polls[fc[j] - 1][0])
            elif j in fd_idx:
                hw.append(h_end + (fd_idx.index(j) + 1) * T)
            else:
                hw.append(h_end + len(fd_idx) * T + 5)
        arrivals = []
        for h in hw:
            a_ = h + DOWN + BIDRTT
            arrivals.append(max(a_, arrivals[-1] + 1) if arrivals else a_)
    prev = None
    for n, (f, at) in enumerate(zip(frames, arrivals)):
        p = payload(n, f, full)
        if mutate == n:
            p = p[:-1] + bytes([p[-1] ^ 0x01])
        if nonslot == n:
            host(bytes([0xF1, 0xC2, 0x28, 0x00, 0x00]), int(at) - 150)
        if replay == n:
            host(prev, int(at) - 150)
        if fd_mid and n == len(frames) // 3 and fd_idx:
            host(payload(1, frames[fd_idx[0]], full), int(at) - 150)
        prev = p
        if drop_write == n or (fd_drop is not None and fd_idx and n == fd_idx[fd_drop]):
            continue
        host(p, int(at))
        if fd_dup is not None and fd_idx and n == fd_idx[fd_dup]:
            host(p, int(at) + 20)
    if tso_c3:
        s0 = sends[0][0]
        if tso_c3 in ('blocking', 'dup'):
            host(b'\xf1\xc3', s0 + UP + 5)
            if tso_c3 == 'dup':
                host(b'\xf1\xc3', s0 + UP + 6)
        elif tso_c3 == 'unrelated':
            host(b'\xf1\xc3', int(arrivals[len(arrivals) // 2]) + 40)
    for n, (sent, action) in enumerate(sends):
        if lose == n:
            continue
        term(aid_bytes(action), sent)
    end_at = int(arrivals[-1]) + 3000
    lines = end_lines or list(out) + Z7.hs_lines(hiscore, out, plan['start'])
    host(bytes([0x7E, 0xC1]) + b''.join(bytes([0x11, 0x40 + i, 0x40]) + e(s) for i, s in enumerate(lines)), end_at)
    host(bytes.fromhex('F1C2115D7F1D4011D9401DC85C5C5C1D4013'), end_at + 110)
    term(bytes([0x7D, 0xC7, 0xE5]), end_at + 4000)
    logged('closure', 'ENTER', end_at + 4000, end_at + 4000)
    host(F6.SHELL_PANEL, end_at + 4200)
    return F6.render(recs, lock), [json.dumps(x) for x in log]


if __name__ == '__main__':
    for c in ('L1', 'L2', 'L3'):
        text, lg = build(c)
        print(c, len(text.splitlines()), 'trace lines,', len(lg), 'driver actions')
