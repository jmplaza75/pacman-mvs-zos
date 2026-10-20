#!/usr/bin/env python3
"""MVS-10 (D46, docs/MVS10-PF12.md section 6) live acceptance of the PF12 change: the LIVE10 game
(tests/mvs10live/make_live10.py, RULES(CLASSIC) AI(0) GHOSTS(1) SOUND(NO)) in a c3270 -trace file, from the first game
write after --from to the line-mode end, with the driver log of tools/mvs10_live.py. Nothing before the game start is
read (no logon); inbound records are used only by their AID (and, for ENTER, the typed command field).
Successor of tools/c3270_s2_trace.py for the 2.1 key map: the frozen helpers are imported, never changed.
1. The game inputs are rebuilt from the AIDs that reached the host (one card per write; an AID just before a write may
   belong to the next quantum, decided greedily as tools/c3270_s2_trace.py --aids) with the 2.1 map of PACINPT RT-TSC:
   PF7 U, PF8 D, PF10 L, PF12 R, PF9 P, PA2 redraw, ENTER = the typed command (blank = redraw, as RT-ENTER); every
   other AID (PF11 included) = no input. Replayed through the independent models, every live write must equal the
   model byte for byte.
2. Control: the same AIDs replayed with the 2.0 map (PF11 R, PF12 nothing) must NOT reproduce the live writes.
3. Gate: PF12 and PF11 reached the host as AID-only records (no ENTER, no field); after every PF AID the game went on
   (a later game write); the game ended only after an ENTER whose field is Q (end banner QUIT, model end lines QUIT);
   between the driver's TYPEQ and ENTER no inbound record reached the host and the game kept writing.
Usage: mvs10_trace.py TRACE --log DRIVERLOG [--from HHMMSS]"""
import argparse
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tools'))
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tests/s2live'))
sys.path.insert(0, str(R / 'tests/mvs10live'))
from c3270_rt_trace import load, ms  # noqa: E402
from c3270_gp1_trace import host, cards_for  # noqa: E402
from c3270_s2_trace import TITLE, is_end, same  # noqa: E402
import make_live10 as S  # noqa: E402

AIDS = {0xF1 + i: f'PF{i + 1}' for i in range(9)} | {0x7A: 'PF10', 0x7B: 'PF11', 0x7C: 'PF12'} | \
    {0xC1 + i: f'PF{13 + i}' for i in range(9)} | {0x4A: 'PF22', 0x4B: 'PF23', 0x4C: 'PF24'} | \
    {0x7D: 'ENTER', 0x6E: 'PA2', 0x6C: 'PA1', 0x6D: 'CLEAR'}
MAP21 = {0xF7: 'U', 0xF8: 'D', 0x7A: 'L', 0x7C: 'R', 0xF9: 'P', 0x6E: '*'}
MAP20 = {0xF7: 'U', 0xF8: 'D', 0x7A: 'L', 0x7B: 'R', 0xF9: 'P', 0x6E: '*'}
NO_PF12 = {k: v for k, v in MAP21.items() if k != 0x7C}                  # control: PF12 ignored
PF11_TOO = MAP21 | {0x7B: 'R'}                                             # control: PF11 still Right


def body(inb):
    return inb[:-2] if inb.endswith(b'\xff\xef') else inb


def field(inb):
    """The typed command field of an ENTER record (AID, cursor 2, SBA X'11' + address 2, data)."""
    inb = body(inb)
    data = inb[6:] if len(inb) > 6 and inb[3] == 0x11 else b''
    return data.decode('cp037', 'replace').strip()


def command(inb, mp):
    """The game card of one inbound record under a key map; None = no input (IGN)."""
    aid = inb[0]
    if aid == 0x7D:
        return field(inb)[:1].upper() or '*'
    return mp.get(aid)


def parse(trace, frm='000000'):
    ev = [e for e in load(trace) if e[1] and ms(e[1]) >= ms(frm + '.000')]
    starts = [i for i, e in enumerate(ev) if e[0] == '<' and TITLE in e[2]]
    if not starts:
        raise SystemExit('no game screen in the trace after --from')
    writes, inbound, over, end_k, after = [], [], False, None, []
    for kind, t, x in ev[starts[0]:]:
        if kind == '<':
            b = host(x)
            if not over and b[:1] in (b'\xf1', b'\x7e', b'\xf5'):
                writes.append((ms(t), b[1:]))
                if is_end(b):
                    over, end_k = True, len(writes) - 1
            elif over:
                after.append(b.decode('cp037', 'replace'))
        elif kind == '>' and x and not over and writes:
            inbound.append((ms(t), bytes(x)))
    return writes, inbound, end_k, after


def replay(writes, inbound, mp):
    """Greedy AID placement (as c3270_s2_trace.py --aids) -> (identical writes, model writes, end lines, cards)."""
    live = [w for _, w in writes]
    aid_t = [(t, c) for t, x in inbound for c in [command(x, mp)] if c]

    def attempt(sh):
        cs = cards_for(writes, aid_t, sh)
        end, fs = S.run(cs)
        pre = next((k for k, (p, q) in enumerate(zip(live, fs)) if not same(p, q, k)), min(len(live), len(fs)))
        return (pre, sum(1 for k, (p, q) in enumerate(zip(live, fs)) if same(p, q, k))), (fs, end, cs)
    shift = [0] * len(aid_t)
    score, best = attempt(shift)
    for i in [i for i, (t, _) in enumerate(aid_t) if any(0 <= tw - t < 60 for tw, _ in writes)]:
        for sh in (1, 2):
            if score[1] == len(live) == len(best[0]):
                break
            trial = list(shift)
            trial[i] = sh
            sc, res = attempt(trial)
            if sc > score:
                shift, score, best = trial, sc, res
    return score[1], best[0], best[1], best[2]


def gate(writes, inbound, end_k, log):
    """-> (ok, results) of the MVS-10 acceptance on one parsed trace and the driver log entries."""
    live = [w for _, w in writes]
    n21, f21, end21, c21 = replay(writes, inbound, MAP21)
    reproduces = lambda mp: (lambda r: r[0] == len(live) == len(r[1]))(replay(writes, inbound, mp))  # noqa: E731
    n20 = replay(writes, inbound, MAP20)[0]
    names = [(t, AIDS.get(x[0], f'{x[0]:02X}'), x) for t, x in inbound]
    pf = [(t, n, x) for t, n, x in names if n.startswith('PF')]
    run = writes[:end_k] if end_k is not None else writes                 # the game writes before the end screen
    later = lambda t: any(tw > t for tw, _ in run)                          # noqa: E731
    tq = next((e['t'] for e in log if e['token'] == 'TYPEQ'), None)
    te = next((e['t'] for e in log if e['token'] == 'ENTER'), None)
    res = {
        'every live write = the model with the 2.1 map (PF12 R, PF11 no input)': n21 == len(live) == len(f21),
        'control: the 2.0 map (PF11 R, PF12 nothing) does not reproduce the live writes': not reproduces(MAP20),
        'control: PF12 ignored does not reproduce the live writes (PF12 moved Right)': not reproduces(NO_PF12),
        'control: PF11 as Right does not reproduce the live writes (PF11 did not move)': not reproduces(PF11_TOO),
        'PF12 reached the host as an AID-only record (no ENTER, no field)': any(n == 'PF12' and len(body(x)) == 3
                                                                               for _, n, x in pf),
        'PF11 reached the host as an AID-only record': any(n == 'PF11' and len(body(x)) == 3 for _, n, x in pf),
        'the game went on after every PF AID (no PF key quits)': bool(pf) and all(later(t) for t, _, _ in pf),
        'end: QUIT banner, model end lines QUIT':
            end_k is not None and end_k == len(live) - 1 and end21[:1] == ['QUIT'],
        'the last inbound record before the end is ENTER with field Q (QUIT = Q + ENTER only)':
            bool(names) and names[-1][1] == 'ENTER' and field(names[-1][2]).upper() == 'Q' and
            names[-1][0] <= writes[-1][0],
        'TYPEQ -> ENTER: no inbound record, the game kept writing (Q alone does not quit)':
            tq is not None and te is not None and tq < te and
            not any(tq <= t < te for t, _ in inbound) and sum(1 for tw, _ in writes if tq <= tw < te) >= 5,
    }
    detail = {'live writes': len(live), 'model writes 2.1': len(f21), 'identical 2.1': n21, 'identical 2.0': n20,
              'end lines': end21, 'cards': ' '.join(c21[1:]),
              'AIDs': [n for _, n, _ in names], 'writes between TYPEQ and ENTER':
              sum(1 for tw, _ in writes if tq is not None and te is not None and tq <= tw < te)}
    return all(res.values()), res, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('trace')
    ap.add_argument('--log', required=True)
    ap.add_argument('--from', dest='frm', default='000000')
    a = ap.parse_args()
    writes, inbound, end_k, after = parse(a.trace, a.frm)
    log = [json.loads(l) for l in open(a.log) if l.strip()]
    ok, res, det = gate(writes, inbound, end_k, log)
    for k, v in res.items():
        print(f'{"PASS" if v else "FAIL"}  {k}')
    for k, v in det.items():
        print(f'  {k}: {v}')
    print('line-mode text after the game:', ' / '.join(s.strip() for s in after if s.strip())[:300])
    print('MVS-10 LIVE GATE ' + ('PASS' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
