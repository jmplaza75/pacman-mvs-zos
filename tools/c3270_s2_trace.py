#!/usr/bin/env python3
"""MVS-S2 S2.4 live acceptance (D41, docs/S2-PATTERNS.md): one scenario of tools/gp2_live.py (S2A-S2E,
tests/s2live/LIVE<X>.txt) in a c3270 -trace file, from the first game write after --from to the line-mode end. Nothing
before the game start is read (no logon); inbound records are used only by their AID.
1. The game writes are every host Write / Erase-Write up to the end banner, plus the bell-only writes the end pause
   may send after it (exactly F1 + C6 28 00 00); the line-mode output that follows is only timed.
2. The scenario cards (the driver sends card k as the input of quantum k) are replayed through the independent models
   (tests/ref_rt.py / ref_gp2.py screens + tests/ref_s2.py patterns, or the S1 / GP2 single bell for ALARM(SINGLE), or
   no bell for SOUND(NO)); every live write is compared with the model stream byte for byte (write 0 may carry the
   first-screen clear prefix). The AIDs between the writes must be the scenario cards (PF1 = '.').
3. Report: every alarm write with its event and time, the gaps between the bells of each pattern (ms; in play they
   are G quanta of the period), the end pause (end screen -> each bell-only write -> the first line-mode record, about
   3 s), and the cadence of the running writes (median / p95 gap, late writes > 1.5 periods).
--aids: replay the cards rebuilt from the AIDs that actually reached the host (one card per write after the first; an
AID just before a write may belong to the next quantum, decided greedily as tools/c3270_gp2_trace.py), for a run whose
inputs differ from the scenario (a key pressed by hand, a dropped idle PF1).
MVS-G8 G8.4: --scenario G8 (the no-operand release smoke, tests/s2live/LIVEG8.txt).
Usage: c3270_s2_trace.py TRACE --scenario S2A|S2B|S2C|S2D|S2E|G8 [--from HHMMSS] [--aids]"""
import argparse
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tools'))
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tests/s2live'))
from c3270_rt_trace import load, ms  # noqa: E402
from c3270_gp1_trace import host, command, cards_for  # noqa: E402
import make_live as M  # noqa: E402
import ref_rt  # noqa: E402
import ref_s2 as S  # noqa: E402

TITLE = 'P A C - M A N'.encode('cp037')
PREFIX = bytes.fromhex('1140403c404000')
BELL_ONLY = (bytes.fromhex('c6280000'), bytes.fromhex('c2280000'))
BANNERS = [w.encode('cp037') for w in (' GAME OVER ', ' YOU WIN ', ' QUIT ', ' END OF INPUT ')]
HELP_QUIT = 'Q QUIT '.encode('cp037')


def is_end(b):
    return any(b.count(v) > (b.count(HELP_QUIT) if v == BANNERS[2] else 0) for v in BANNERS)


def same(p, q, k):
    return p == q or (k == 0 and p.replace(PREFIX, b'', 1) == q)


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(round(p * (len(v) - 1))))] if v else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('trace')
    ap.add_argument('--scenario', required=True, choices=['S2' + k for k in M.SCEN if len(k) == 1] + ['G8'])
    ap.add_argument('--from', dest='frm', default='000000')
    ap.add_argument('--aids', action='store_true')
    a = ap.parse_args()
    name = a.scenario[2:] if a.scenario.startswith('S2') else a.scenario     # MVS-G8: scenario G8
    src, cfg, rules, sp, snd, al, words = M.SCEN[name]
    per = ref_rt.period(sp)
    cards = (R / f'tests/s2live/LIVE{name}.txt').read_text().splitlines()
    ev = [e for e in load(a.trace) if e[1] and ms(e[1]) >= ms(a.frm + '.000')]
    starts = [i for i, e in enumerate(ev) if e[0] == '<' and TITLE in e[2]]
    if not starts:
        raise SystemExit('no game screen in the trace after --from')
    ev = ev[starts[0]:]
    writes, aids, after, over, end_k, tail, aid_t = [], [], [], False, None, None, []
    for kind, t, x in ev:
        if kind == '<':
            b = host(x)
            if not over and b[:1] in (b'\xf1', b'\x7e', b'\xf5'):
                writes.append((ms(t), b[1:]))
                if is_end(b):
                    over, end_k = True, len(writes) - 1
            elif over and tail is None and b[:1] == b'\xf1' and b[1:] in BELL_ONLY:
                writes.append((ms(t), b[1:]))
            elif over and tail is None:
                tail = ms(t)                              # the first line-mode record after the game
                after.append(b.decode('cp037', 'replace'))
            elif over:
                after.append(b.decode('cp037', 'replace'))
        elif kind == '>' and not over and writes:
            cmd = command(x)
            aids.append(cmd if cmd else ('.' if x[:1] == b'\xf1' else '?'))
            aid_t.append((ms(t), aids[-1]))
    live = [w for _, w in writes]
    # the models, with the HUD high score of the first write (ARCADE: the CLIST allocates the high-score member)
    first = live[0].decode('cp037', 'replace') if live else ''
    m = re.search(r'HIGH[^0-9]{0,8}(\d{7})', first) or re.search(r'HI (\d{7})', first)
    hs = ('R', int(m.group(1)), 1) if (m and rules == 'A') else None

    def replay(cs):
        end, fs, log = M.run(rules, cs, per, hs)
        if snd != 'Y':
            want, trace = list(fs), []
        elif al == 'P':
            want, trace = S.patterns(fs, log, 'Y', 'R', per)
        else:
            want = M.single(rules, fs, log)
            trace = [(k, 'BELL', 1) for k, f in enumerate(want) if f[0] & 0x04]
        pre = next((k for k, (p, q) in enumerate(zip(live, want)) if not same(p, q, k)), min(len(live), len(want)))
        return (pre, sum(1 for k, (p, q) in enumerate(zip(live, want)) if same(p, q, k))), (end, want, trace, cs)
    score, (end, want, trace, used) = replay(cards)
    if a.aids:
        game = writes[:end_k + 1] if end_k is not None else writes
        shift = [0] * len(aid_t)
        score, best = replay([cfg] + cards_for(game, aid_t, shift))
        for i in [i for i, (t, _) in enumerate(aid_t) if any(0 <= tw - t < 60 for tw, _ in game)]:
            for sh in (1, 2):
                if score[1] == len(live) == len(best[1]):
                    break
                trial = list(shift)
                trial[i] = sh
                sc, res = replay([cfg] + cards_for(game, aid_t, trial))
                if sc > score:
                    shift, score, best = trial, sc, res
        end, want, trace, used = best
        print('cards rebuilt from the AIDs:', ' '.join(used[1:]))
        print('first card differing from the scenario:',
              next((i + 1 for i, (x, y) in enumerate(zip(used[1:], cards[1:])) if x != y), '-'))
    n_same = score[1]
    ok = n_same == len(live) == len(want)
    print(f'scenario {a.scenario}: {words} | speed {"FAST" if per != 150 else "NORMAL"} ({per} ms) | HUD high score',
          m.group(1) if m else 'none')
    print(f'writes: live {len(live)}, model {len(want)}, identical {n_same}' + (' | ALL IDENTICAL' if ok else ''))
    bad = [k for k, (p, q) in enumerate(zip(live, want)) if not same(p, q, k)]
    print('first difference at write', bad[0] if bad else '-')
    want_aids = [c for c in cards[1:]]
    print('AIDs = scenario cards:', aids == want_aids, f'({len(aids)} AIDs, {len(want_aids)} cards)')
    rung = [k for k, w in enumerate(live) if w[:1] and w[0] & 0x04]
    print("live writes with the alarm bit (WCC X'04'):", rung, '| model:', [k for k, f in enumerate(want)
                                                                             if f[0] & 0x04])
    t0 = writes[0][0] if writes else 0
    names = {k: e for k, e, _ in trace}
    print('alarms (write, ms from the first write, event):')
    last_ev, gaps, groups = None, [], []
    for k in rung:
        e = names.get(k, '?')
        print(f'  {k:4d} {writes[k][0] - t0:7d} ms  {e}')
        if e != 'STEP':
            groups.append([k])
        elif groups:
            gaps.append((groups[-1][0], writes[k][0] - writes[groups[-1][-1]][0]))
            groups[-1].append(k)
        last_ev = e
    print('bells per event:', [(names.get(g[0], '?'), len(g)) for g in groups])
    print('gaps between the bells of a pattern (ms):', [g for _, g in gaps], f'(G = {S.gap(per)} quanta = '
          f'{S.gap(per) * per} ms in play)')
    if end_k is not None:
        te = writes[end_k][0]
        extra = [writes[k][0] - te for k in range(end_k + 1, len(writes))]
        print('end screen = write', end_k, '| bell-only writes after it (ms):', extra,
              '| first line-mode record after', (tail - te) if tail else '-', 'ms (design: 3000 + the line-mode switch)')
    run_gaps = [writes[k + 1][0] - writes[k][0] for k in range(1, (end_k or len(writes)) - 1)]
    late = [g for g in run_gaps if g > 1.5 * per]
    print(f'cadence of the game writes: median {pct(run_gaps, 0.5)} ms, p95 {pct(run_gaps, 0.95)} ms, '
          f'{len(late)} gaps > {1.5 * per:.0f} ms', late[:10])
    print('line-mode text after the game:', ' / '.join(s.strip() for s in after if s.strip())[:300])
    print('model end lines:', ' / '.join(end[-8:]))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
