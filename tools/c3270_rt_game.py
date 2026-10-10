#!/usr/bin/env python3
"""MVS-RT RT3 live acceptance: a REALTIME game in a c3270 -trace file, from the LAST game start (first host record
containing the EBCDIC title 'P A C - M A N' after --from) to the line-mode end. Nothing of the logon is read; inbound
records are shown only by their AID. Reports: output cadence while running (gap statistics, bursts, gaps > 1.5 x 150 ms
outside pauses), every AID (PF7/8/10/11 arrows, PF9 pause, PA2, ENTER, CLEAR), pause intervals (PAUSED banner on the
screen, frames stopped, first frame after the resume), keyboard lock per AID, restore-only writes (F1 C2 28 00 00),
full screens (PA2 redraws), the end banner.
Usage: c3270_rt_game.py TRACE [--from HHMMSS] [--events]"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c3270_rt_trace import load, ms  # noqa: E402

TITLE = 'P A C - M A N'.encode('cp037')
PAUSED = ' PAUSED '.encode('cp037')
BANNERS = {k: k.encode('cp037') for k in (' GAME OVER ', ' YOU WIN ', ' QUIT ', ' END OF INPUT ')}
AIDN = {0xF7: 'UP/PF7', 0xF8: 'DOWN/PF8', 0x7A: 'LEFT/PF10', 0x7B: 'RIGHT/PF11', 0xF9: 'PAUSE/PF9', 0x6E: 'PA2',
        0x7D: 'ENTER', 0x6D: 'CLEAR', 0x6C: 'PA1', 0xF3: 'PF3'}


def stats(v):
    v = sorted(v)
    if not v:
        return '-'
    return f'n={len(v)} min={v[0]} med={v[len(v) // 2]} p95={v[int(.95 * (len(v) - 1))]} max={v[-1]}'


ap = argparse.ArgumentParser()
ap.add_argument('trace')
ap.add_argument('--from', dest='frm', default='000000')
ap.add_argument('--events', action='store_true')
a = ap.parse_args()
ev = [e for e in load(a.trace) if e[1] and ms(e[1]) >= ms(a.frm + '.000')]
starts = [i for i, e in enumerate(ev) if e[0] == '<' and TITLE in e[2]]
if not starts:
    raise SystemExit('no game screen in the trace')
i0 = starts[0]
ev = ev[i0:]
end = next((i for i, e in enumerate(ev) if e[0] == '<' and any(b in e[2] for b in BANNERS.values())), len(ev) - 1)
banner = next((k for k, b in BANNERS.items() if b in ev[end][2]), None) if end < len(ev) - 1 else None
ev = ev[:end + 1]
rows, outs, aids, locks, lock_t = [], [], [], [], None
paused, pauses, first_aid = None, [], None
for k, t, x in ev:
    if k == '<':
        b = x[:-2] if x.endswith(b'\xff\xef') else x
        kind = 'FULL' if b[0] in (0xF5, 0x7E) or (len(b) > 2 and b[2:4] == b'\x11\x40') else 'PART'
        if b[:4] == bytes([0xF1, 0xC2, 0x28, 0x00]) and len(b) == 5 or b == bytes([0xF1, 0xC2, 0x28, 0x00, 0x00]):
            kind = 'RESTORE'
        has_p = PAUSED in b
        outs.append((ms(t), kind, len(b), has_p))
        rows.append(f'{t} OUT {kind:7} len {len(b):4}' + (' PAUSED' if has_p else ''))
        if has_p and paused is None:
            paused = ms(t)
        elif paused is not None and not has_p and kind != 'FULL':
            pauses.append((paused, ms(t)))
            paused = None
    elif k == '>' and x:
        name = AIDN.get(x[0], f'{x[0]:02X}')
        aids.append((ms(t), name))
        first_aid = first_aid or ms(t)
        rows.append(f'{t} IN  {name}')
    elif k == 'kb':
        if 'lock(key_AID)' in x:
            lock_t = ms(t)
        elif '-OIA_LOCKED' in x and lock_t is not None:
            locks.append(ms(t) - lock_t)
            lock_t = None
if a.events:
    print('\n'.join(rows))
in_pause = lambda t0: any(p0 <= t0 <= p1 for p0, p1 in pauses)  # noqa: E731
run = [o for o in outs if first_aid and o[0] > first_aid]
gaps = [y[0] - x[0] for x, y in zip(run, run[1:]) if not in_pause(x[0]) and not in_pause(y[0])]
print('game start', ev[0][1], '| first AID', ev[[e[0] for e in ev].index('>')][1] if aids else '-', '| end', ev[-1][1],
      '| banner', banner)
print('outputs', len(outs), {k: sum(1 for o in outs if o[1] == k) for k in ('FULL', 'PART', 'RESTORE')})
print('running output gaps ms', stats(gaps), '| < 20 ms:', sum(g < 20 for g in gaps), '| > 225 ms:',
      sum(g > 225 for g in gaps))
print('before the first AID: outputs delivered', sum(1 for o in outs if first_aid and o[0] < first_aid))
print('AIDs', len(aids), {n: sum(1 for _, x in aids if x == n) for n in sorted({x for _, x in aids})})
print('keyboard lock per AID ms', stats(locks))
for p0, p1 in pauses:
    after = [o for o in outs if o[0] > p1][:4]
    print(f'pause {p1 - p0} ms; after resume: first frames at +' + ', +'.join(str(o[0] - p1) for o in after) + ' ms')
