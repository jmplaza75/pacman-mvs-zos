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
MVS-S2 S2.4: scenarios S2A-S2E (tests/s2live, REALTIME; ended by the game or by Q).
MVS-G8 G8.4: scenario G8 = no CLIST operand at all (the 2.0 defaults).
Usage: gp2_live.py A|B|C|S2A..S2E|G8 [--port 4001] [--prefix HERC01.PACMAN] [--pause 3] [--log FILE] [--snap DIR]"""
import argparse
import subprocess
import time
from pathlib import Path

R = Path(__file__).resolve().parent.parent
SCEN = {   # card file, CLIST keywords (defaults: COLOR/HILITE/GLYPHS/SCALE/CANVAS AUTO, SOUND AUTO)
    'A': ('LIVEA', 'RULES(ARCADE) AI(0) GHOSTS(1) PLAY(REALTIME)'),
    'B': ('LIVEB', 'RULES(ARCADE) AI(0) GHOSTS(1) LEVEL(13) PLAY(TURN) ANIM(NO)'),
    'C': ('LIVEC', 'RULES(ARCADE) AI(2) GHOSTS(1) LEVEL(13) PLAY(REALTIME)'),
    # MVS-S2 S2.4 (docs/evidence/s2-live-checklist.md): tests/s2live/LIVE<X>.txt (tests/s2live/make_live.py)
    'S2A': ('../s2live/LIVEA', 'RULES(ARCADE) AI(3) GHOSTS(1)'),
    'S2B': ('../s2live/LIVEB', 'RULES(ARCADE) AI(0) GHOSTS(1) SPEED(FAST)'),
    'S2C': ('../s2live/LIVEC', 'RULES(CLASSIC) AI(0) GHOSTS(1)'),
    'S2D': ('../s2live/LIVED', 'RULES(ARCADE) AI(3) GHOSTS(1) ALARM(SINGLE)'),
    'S2E': ('../s2live/LIVEE', 'RULES(CLASSIC) AI(0) GHOSTS(1) SOUND(NO)'),
    # MVS-G8 G8.4: the installed release with NO CLIST operand (tests/s2live/LIVEG8.txt, make_live.py G8)
    'G8': ('../s2live/LIVEG8', ''),
}
# MVS-G8 G8.4: --snap DIR saves the emulator screen (c3270 PrintText: HTML with the 3270 colours + plain text; a local
# action, nothing reaches the host) after these host writes of the model (tests/s2live/make_live.py G8 + the RP model):
# write w is on the screen after card w-1 and its Wait(Output); write 0 = the start screen, the last = the end screen.
SNAPS = {'G8': {0: '01-ready', 20: '02-fright', 30: '03-popup', 100: '04-play', 149: '05-death', 154: '06-ready-death',
                179: '07-end'}}
KEY = {'U': 'PF(7)', 'D': 'PF(8)', 'L': 'PF(10)', 'R': 'PF(11)', 'P': 'PF(9)', '*': 'PA(2)', 'Q': 'String("Q") Enter()',
       '.': 'PF(1)'}

ap = argparse.ArgumentParser()
ap.add_argument('scenario', choices=sorted(SCEN))
ap.add_argument('--port', default='4001')
ap.add_argument('--prefix', default='HERC01.PACMAN')
ap.add_argument('--pause', type=float, default=3.0)
ap.add_argument('--log', default=str(Path.home() / 'gp2-live-driver.log'))
ap.add_argument('--snap', help='MVS-G8: directory for the screen captures (SNAPS)')
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


def snap(w):
    name = SNAPS.get(a.scenario, {}).get(w) if a.snap else None
    if name:
        base = str(Path(a.snap).resolve() / f'g8-{name}')
        x(f'PrintText(html,file,{base}.html)')
        x(f'PrintText(file,{base}.txt)')
        say(f'snap write {w} {name}')


def screen():
    return [l.rstrip() for l in x('Ascii()').splitlines()]


def at_ready():
    rows = [l for l in screen() if l.strip()]
    return bool(rows) and rows[-1].strip() == 'READY'


if not at_ready():
    raise SystemExit('the terminal is not at TSO READY (log on first)')
x('TemporaryKeymap()')
say(f'start {name}: {words}')
x(f'String("EXEC \'{a.prefix}.CLIST(PACMAN)\'' + (f' \'{words}\'' if words else '') + '")')
x('Enter()')
end = time.time() + 60
while not any('COMMAND ===>' in l for l in screen()):
    if time.time() > end:
        raise SystemExit('no game screen within 60 s')
    time.sleep(0.5)
time.sleep(1.0)                                  # let the first screen settle (keyboard restored)
snap(0)
print(f'{time.strftime("%H:%M:%S")} scenario {a.scenario} ({name}, {len(cards)} cards): {words}')
paused = False
for k, card in enumerate(cards):
    if card == 'Q':
        say(f'card {k} Q')
        if k + 1 in SNAPS.get(a.scenario, {}) and a.snap:
            x(KEY['Q'] + ' Wait(5,Output)')          # the end screen (3-s end pause), then its capture
            snap(k + 1)
        else:
            x(KEY['Q'])
        break
    if a.scenario == 'B':                        # TURN: one command per screen
        x(f'String("{card}") Enter() Wait(5,Output)')
        say(f'card {k} {card}')
        continue
    x(KEY[card] + ' Wait(5,Output)')
    say(f'card {k} {card}')
    snap(k + 1)
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
