#!/usr/bin/env python3
"""MVS-RT probe E14 run A: scripted AIDs through the c3270 script port, timed from the c3270 trace (read only after
the probe's first 'E14 ' frame). Detects the input segment I (after the last 'E14 S P=250' frame: five consecutive
output gaps of 180-220 ms) and the restore-only segment R (frame tagged 'E14 R'). Every injected action is logged
with its local time. Screen snapshots (rows of the probe/game screen only) go to --snap.
I + 32 s: PA(2), Clear, PF(1), Enter, String("X") Enter, burst 'PF(7) PF(8) PF(10) PF(11)' (one macro), 1.5 s apart.
R + 3 s: snapshot, burst 'PF(10) PF(11) PF(7) PF(8)', snapshot, PA(2), snapshot, Clear, snapshot.
Usage: e14_inject.py TRACE --log FILE --snap FILE [--port 4001]"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c3270_rt_trace import E14, load, ms  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('trace')
ap.add_argument('--log', required=True)
ap.add_argument('--snap', required=True)
ap.add_argument('--port', default='4001')
a = ap.parse_args()
LOG = open(a.log, 'a')


def say(msg):
    LOG.write(f'{time.strftime("%H%M%S")}.{int(time.time() * 1000) % 1000:03d} {msg}\n')
    LOG.flush()


def act(action):
    r = subprocess.run(['x3270if', '-t', a.port, action], capture_output=True, text=True, timeout=30)
    say(f'ACTION {action} rc={r.returncode} {r.stdout.strip()[:60]} {r.stderr.strip()[:60]}')


def snap(label):
    r = subprocess.run(['x3270if', '-t', a.port, 'Ascii()'], capture_output=True, text=True, timeout=10)
    c = subprocess.run(['x3270if', '-t', a.port, 'Query(Cursor1)'], capture_output=True, text=True, timeout=10)
    with open(a.snap, 'a', encoding='utf-8') as f:
        f.write(f'=== {label} {time.strftime("%H:%M:%S")} cursor {c.stdout.strip()}\n')
        f.write('\n'.join(f'{i + 1:02d}|{t.rstrip()}' for i, t in enumerate(r.stdout.splitlines())) + '\n')
    say(f'SNAP {label}')


def probe_events():
    try:
        ev = load(a.trace)
        i0 = next(i for i, e in enumerate(ev) if e[0] == '<' and E14 in e[2])
    except (StopIteration, FileNotFoundError):
        return []
    return [(ms(t), b) for k, t, b in ev[i0:] if k == '<' and t]


say('waiting for the I segment')
state = 'S250'
while True:
    outs = probe_events()
    tag250 = [i for i, (_, b) in enumerate(outs) if 'E14 S P=250'.encode('cp037') in b]
    if state == 'S250' and tag250:
        tail = outs[tag250[-1]:]
        gaps = [y[0] - x[0] for x, y in zip(tail, tail[1:])]
        for j in range(len(gaps) - 4):
            if all(180 <= g <= 220 for g in gaps[j:j + 5]):
                state = 'I'
                say(f'I segment detected (trace t={tail[j][0]} ms)')
                break
    if state == 'I':
        break
    time.sleep(1)
time.sleep(30)
for x in ('PA(2)', 'Clear', 'PF(1)', 'Enter', 'String("X") Enter', 'PF(7) PF(8) PF(10) PF(11)'):
    act(x)
    time.sleep(1.5)
say('waiting for the R segment')
while not any('E14 R'.encode('cp037') in b for _, b in probe_events()):
    time.sleep(0.5)
time.sleep(3)
snap('R+3 before burst')
act('PF(10) PF(11) PF(7) PF(8)')
time.sleep(1)
snap('R after burst')
act('PA(2)')
time.sleep(1)
snap('R after PA2')
act('Clear')
time.sleep(1)
snap('R after CLEAR')
say('done')
