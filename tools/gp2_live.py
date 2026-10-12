#!/usr/bin/env python3
"""MVS-GP2 GP2.4 live driver: plays one deterministic scenario (tests/gp2live/LIVE[ABC].txt) in the c3270 started by
tools/c3270_rt.sh (script port 4001), so no maze has to be cleared by hand. The terminal must be logged on and at
TSO READY; only the game / READY screens are read (never the logon). The analysis is done afterwards from the c3270
trace by tools/c3270_gp2_trace.py (replay through the independent model): this driver only sends keys.
REALTIME (A, C): the first card is sent on the start screen; then every card is sent right after the host write of
the previous quantum (x3270if 'KEY Wait(5,Output)' = the key, then the next write), so card k is the input of
quantum k as in the batch card rules (tests/ref_rt.py). '.' = PF1, U/D/L/R = PF7/8/10/11, P = PF9 (pause; the
driver then holds the pause --pause seconds before the resuming P), * = PA2, Q = Q + ENTER.
GP2.4 live run 1 (2026-10-12, docs/evidence/gp2-live.md): c3270's Wait(Output) blocks only after an AID; for an idle
card ('.', no key) it returned at once (median 7 ms), so the driver ran ahead of the quanta (scenario A: 201 cards in
100 quanta). Fix: an idle card sends PF1, an AID the game ignores in REALTIME (PACINPT RT-TSC: anything but PF7-PF11,
PA2 and ENTER = IGN, dropped by PACMAIN RT-EVENT before PACRT: no input, no frame change; the replay maps PF1 to '.'),
so every card is one AID and every Wait(Output) blocks for exactly one host write. The scenarios are unchanged.
TURN (B): every card is typed in the command field + ENTER, then the next write is awaited.
Usage: gp2_live.py A|B|C [--port 4001] [--prefix HERC01.PACMAN] [--pause 3] [--log FILE]"""
import argparse
import subprocess
import time
from pathlib import Path

R = Path(__file__).resolve().parent.parent
SCEN = {   # card file, CLIST keywords (defaults: COLOR/HILITE/GLYPHS/SCALE/CANVAS AUTO, SOUND AUTO)
    'A': ('LIVEA', 'RULES(ARCADE) AI(0) GHOSTS(1) PLAY(REALTIME)'),
    'B': ('LIVEB', 'RULES(ARCADE) AI(0) GHOSTS(1) LEVEL(13) PLAY(TURN) ANIM(NO)'),
    'C': ('LIVEC', 'RULES(ARCADE) AI(2) GHOSTS(1) LEVEL(13) PLAY(REALTIME)'),
}
KEY = {'U': 'PF(7)', 'D': 'PF(8)', 'L': 'PF(10)', 'R': 'PF(11)', 'P': 'PF(9)', '*': 'PA(2)', 'Q': 'String("Q") Enter()',
       '.': 'PF(1)'}

ap = argparse.ArgumentParser()
ap.add_argument('scenario', choices=sorted(SCEN))
ap.add_argument('--port', default='4001')
ap.add_argument('--prefix', default='HERC01.PACMAN')
ap.add_argument('--pause', type=float, default=3.0)
ap.add_argument('--log', default=str(Path.home() / 'gp2-live-driver.log'))
a = ap.parse_args()
name, words = SCEN[a.scenario]
cards = (R / f'tests/gp2live/{name}.txt').read_text().splitlines()[1:]
LOG = open(a.log, 'a')


def say(msg):
    LOG.write(f'{time.strftime("%H%M%S")}.{int(time.time() * 1000) % 1000:03d} {a.scenario} {msg}\n')
    LOG.flush()


def x(action, timeout=30):
    r = subprocess.run(['x3270if', '-t', a.port, action], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise SystemExit(f'x3270if {action}: {r.stderr.strip()}')
    return r.stdout


def screen():
    return [l.rstrip() for l in x('Ascii()').splitlines()]


def at_ready():
    rows = [l for l in screen() if l.strip()]
    return bool(rows) and rows[-1].strip() == 'READY'


if not at_ready():
    raise SystemExit('the terminal is not at TSO READY (log on first)')
x('TemporaryKeymap()')
say(f'start {name}: {words}')
x(f'String("EXEC \'{a.prefix}.CLIST(PACMAN)\' \'{words}\'")')
x('Enter()')
end = time.time() + 60
while not any('COMMAND ===>' in l for l in screen()):
    if time.time() > end:
        raise SystemExit('no game screen within 60 s')
    time.sleep(0.5)
time.sleep(1.0)                                  # let the first screen settle (keyboard restored)
print(f'{time.strftime("%H:%M:%S")} scenario {a.scenario} ({name}, {len(cards)} cards): {words}')
paused = False
for k, card in enumerate(cards):
    if card == 'Q':
        say(f'card {k} Q')
        x(KEY['Q'])
        break
    if a.scenario == 'B':                        # TURN: one command per screen
        x(f'String("{card}") Enter() Wait(5,Output)')
        say(f'card {k} {card}')
        continue
    x(KEY[card] + ' Wait(5,Output)')
    say(f'card {k} {card}')
    if card == 'P':
        paused = not paused
        if paused:
            print(f'{time.strftime("%H:%M:%S")} PAUSED (card {k}) - resuming in {a.pause:.0f} s')
            time.sleep(a.pause)
end = time.time() + 60
while not at_ready():
    if time.time() > end:
        raise SystemExit('not back at READY within 60 s')
    time.sleep(0.5)
say('READY')
print(f'{time.strftime("%H:%M:%S")} back at READY')
