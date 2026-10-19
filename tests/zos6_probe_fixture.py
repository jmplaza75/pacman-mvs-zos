#!/usr/bin/env python3
"""ZOS-6 protocol probe: deterministic synthetic c3270 traces and driver logs for tools/zowe/zos6_probe_check.py
(docs/zos6-protocol-probe.md). build(mode, delivered) -> (trace text, driver log lines).
P0-like: frames with REQUEST-FLAG 00 behind one BID per bracket, an empty SDI + KRI control every 14 frames (the R1-T3
pattern), the keyboard unlocked only after a control; PT-like: every frame with SDI (01) behind its own BID, the
keyboard unlocked after every frame. `delivered`: which of the three attempts (PF4 / PF5 / PF6) reach the wire.
PN-, PH-, PB4- and PR2-like: as P0 (PR2: frames on even quanta only) (the host-side poll order and HOLD are not visible in the record shapes)."""
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
import zos5_fixture as FX  # noqa: E402

TITLE = 'PACZ6P ZOS-6 PROTOCOL PROBE'


def e(s):
    return s.encode('cp037')


def build(mode, delivered=(True, True, True), quanta=133, swap=None, host_drop=None, lagstep=0, replay=None,
          odd_hit=False):
    t0 = 36_000_000
    host, term, kb = [], [], []                 # host: (ms, rq, dt, payload)
    shown_mode = 'PR2' if mode == 'PR2I' else mode                 # PR2I shows the PR2 title
    host.append((t0, 0x01, 0x00, bytes.fromhex('F5C3114040') + e(f'{TITLE}  MODE {shown_mode}')))
    even = mode in ('PR2', 'PR2I')
    aid_at = {5000: 'F4', 10000: 'F5', 15000: 'F6'}
    got, log = [], []
    log.append({'ordinal': 1, 'category': 'transition', 'action': 'CALL', 'requested': t0 - 2000,
                'wait_start': t0 - 2000, 'unlocked': t0 - 2000, 'sent': t0 - 2000, 'result': 'ok'})
    pending = list(zip(aid_at.items(), delivered))
    for q in range(1, quanta + 1):
        tq = t0 + 200 + q * 150 + ((q - 1) % 4) * lagstep     # injection: lag building up between PB4 barriers
        if mode == 'PT' or q % 14 == 1:
            host.append((tq - 110, 0x00, 0x09, b''))
            kb.append((tq - 110, True))
        shown = {swap[0]: swap[1], swap[1]: swap[0]}.get(q, q) if swap else q     # injection: two frames swapped
        frame = bytes.fromhex('F1C211C261') + e(f'QUANTUM {shown:04d}  AIDS RECEIVED {len(got):02d}')
        if even and q == replay:                    # injection: the skipped quantum q - 1 written late (a burst)
            host.append((tq - 1, 0x00, 0x00, bytes.fromhex('F1C211C261') + e(f'QUANTUM {q - 1:04d}  AIDS RECEIVED 00')))
        if not even or q % 2 == 0:                  # PR2 / PR2I: only even quanta write
            host.append((tq, 0x01 if mode == 'PT' else 0x00, 0x00, frame))
        if mode == 'PT':
            kb.append((tq, False))
        elif q % 14 == 0:
            host.append((tq + 20, 0x03, 0x00, b''))
            kb.append((tq + 20, False))
        while pending and tq - t0 >= pending[0][0][0]:
            (off, aid), ok = pending.pop(0)
            action = {'F4': 'PF4', 'F5': 'PF5', 'F6': 'PF6'}[aid]
            entry = {'ordinal': len(log) + 1, 'category': 'probe', 'action': action, 'requested': tq,
                     'wait_start': tq, 'unlocked': tq + 1 if ok else None, 'sent': tq + 2 if ok else None,
                     'result': 'ok' if ok else 'not sent: keyboard locked 5 s'}
            log.append(entry)
            if ok:
                term.append((tq + 2, bytes([int(aid, 16), 0x5B, 0x6F])))
                if mode == 'PR2I':                  # delivered on the next even (write) quantum >= q + 2, or with
                    d = q + 1 if odd_hit and (q + 1) % 2 else (q + 2 if q % 2 == 0 else q + 1)   # odd_hit: an odd one
                    d = d if odd_hit or d % 2 == 0 else d + 1
                    got.append((aid, d, (d - 1) * 150 + 1))
                else:
                    got.append((aid, q + 1, off + 160))
    end = t0 + 200 + quanta * 150 + 100
    lines = [f'PACZ6P MODE {mode} QUANTA {quanta:06d} ELAPSED-MS {quanta * 150:06d}',
             'PACZ6P LATE>75MS 000000 MAXLATE-MS 000003 MAXPUT-MS 000001',
             f'PACZ6P RCOUT 000000 RCIN 000000 AIDS {len(got):06d}',
             f"PACZ6P HOLDS {({'PH': quanta, 'PB4': quanta // 4}.get(mode, 0)):06d} MAXHOLD-MS "
             f"{({'PH': 509, 'PB4': 300}.get(mode, 0)):06d} MAXNOHOLD-MS {(0 if mode == 'PH' else 1):06d}",
             f"PACZ6P WRITES {(quanta // 2 if mode == 'PR2' else quanta):06d} "
             f"SKIPPED {(quanta - quanta // 2 if mode == 'PR2' else 0):06d}"]
    lines += [f'PACZ6P AID {a} QUANTUM {q:06d} MS {t:06d}' for k, (a, q, t) in enumerate(got)
              if k != host_drop]                # injection: one received AID missing from the host summary
    if mode == 'PR2I':
        lines += instr_lines(quanta, got)
    for k, s in enumerate(lines):
        host.append((end + k * 5, 0x00, 0x00, bytes([0xF1, 0xC1, 0x11, 0x40, 0x40]) + e(s)))
    host.append((end + 100, 0x00, 0x00, FX.TRANS_STAR if hasattr(FX, 'TRANS_STAR') else
                 bytes.fromhex('F1C2115D7F1D4011D9401DC85C5C5C1D4013')))
    log.append({'ordinal': len(log) + 1, 'category': 'closure', 'action': 'ENTER', 'requested': end + 2000,
                'wait_start': end + 2000, 'unlocked': end + 2000, 'sent': end + 2000, 'result': 'ok'})
    return render(host, term, kb), [json.dumps(x) for x in log]


def instr_lines(quanta, got):
    """The PR2I host table lines (S1 / S2 status, I detail for each AID quantum and the 3 before) for `got`."""
    hit = {q: a for a, q, _ in got}
    st = ''
    for q in range(1, quanta + 1):
        c = 'a' if q in hit else '.'
        st += (c.upper() if c != '.' else ':') if q % 2 == 0 else c
    out = [f'PACZ6P S1 {st[:67]}', f'PACZ6P S2 {st[67:]}']
    cnt = 0
    for a, q, _ in got[:3]:
        for p in range(max(1, q - 3), q + 1):
            w = p % 2 == 0
            before = cnt + sum(1 for _, x, _ in got if x < p) - cnt
            after = before + (1 if p in hit else 0)
            tp = f'{(p - 1) * 150:06d} {(p - 1) * 150:06d}' if w else '------ ------'
            out.append(f"PACZ6P I {p:03d} {int(w)} {'00' if p in hit else '04'} "
                       f"{'003' if p in hit else '---'} {hit.get(p, '00')} {before:02d}>{after:02d} {tp} "
                       f'{(p - 1) * 150:06d} {(p - 1) * 150 + 1:06d}')
    return out


def render(host, term, kb):
    items, seq = [], 0
    for tm, rq, dt, p in sorted(host, key=lambda x: x[0]):
        hdr = bytes([dt, rq, 0x02]) + seq.to_bytes(2, 'big')
        items.append((tm, '<', hdr + p))
        items.append((tm + 1, '>', bytes([0x02, 0, 0]) + seq.to_bytes(2, 'big') + b'\x00'))
        seq += 1
    for tm, p in term:
        items.append((tm, '>', bytes(5) + p))
    for tm, lk in kb:
        items.append((tm, 'K', lk))
    items.sort(key=lambda x: (x[0], {'<': 0, 'K': 1, '>': 2}[x[1]]))
    out = ['20261017.095959.000 infra  Trace started (synthetic ZOS-6 probe fixture)', ' TELNET state:',
           '< 0x0   fffa28030400020405fff0', ' Screen contents (TN3270E-3270) unformatted:']
    out += FX.dump('<', bytes(5) + e('ISPF Command Shell'))
    out.append(' Data stream:')
    for tm, d, b in items:
        if d == 'K':
            out.append(f'{FX.stamp(tm)} kybd   Keyboard lock(kybd_bid) none +BID -> BID' if b else
                       f'{FX.stamp(tm)} kybd   Keyboard unlock(kybd_send_data) BID -BID -> none')
            continue
        w = b.replace(b'\xff', b'\xff\xff') + b'\xff\xef'
        out.append(f'{FX.stamp(tm)} socket Host socket read complete nr={len(w)}' if d == '<' else
                   f'{FX.stamp(tm)} tn3270 SENT TN3270E(3270-DATA NO-RESPONSE 0)')
        out += FX.dump(d, w)
    return '\n'.join(out) + '\n'
