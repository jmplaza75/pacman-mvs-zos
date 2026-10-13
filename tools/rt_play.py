#!/usr/bin/env python3
"""MVS-RT: start a REALTIME game in the c3270 started by tools/c3270_rt.sh (script port 4001) and switch the game keys
on only while it runs: the temporary keymap 'pacgame' (P / p -> PF9 = pause) is enabled when the game screen appears
and cleared when TSO is back at READY, so logon, password and TSO commands keep a normal 'p'.
The terminal must be logged on and at READY. Only the game / READY screen is read (never the logon).
MVS-RP D40 (RP.4 reproduction): --hold-ok expects a TSO '***' hold before the game: the script waits (it never
presses ENTER itself); the user presses ENTER and the full-screen game must follow.
Usage: rt_play.py [--port 4001] [--prefix HERC01.PACMAN] [--hold-ok] [CLIST keywords, default PLAY(REALTIME)]"""
import argparse
import subprocess
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument('--port', default='4001')
ap.add_argument('--prefix', default='HERC01.PACMAN')
ap.add_argument('--hold-ok', action='store_true')
ap.add_argument('keywords', nargs='*', default=['PLAY(REALTIME)'])
a = ap.parse_args()


def x(action):
    r = subprocess.run(['x3270if', '-t', a.port, action], capture_output=True, text=True, timeout=30)
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
x('Set(typeahead)') == 'false\n' or print('warning: c3270 typeahead is not false (use tools/c3270_rt.sh)')
words = ' '.join(a.keywords)
x(f'String("EXEC \'{a.prefix}.CLIST(PACMAN)\' \'{words}\'")')
x('Enter()')
end = time.time() + 60
held = False
while True:
    s = screen()
    if any('COMMAND ===>' in l for l in s):
        break
    bottom = [l.strip() for l in s if l.strip()][-1:]
    if bottom == ['***'] and a.hold_ok:
        if not held:
            print(f'{time.strftime("%H:%M:%S")} TSO *** hold seen (expected): press ENTER in the terminal')
            held, end = True, time.time() + 120
        time.sleep(0.5)
        continue
    if bottom == ['***'] or any('ASSUMED' in l or l.startswith(' IKJ') for l in s):
        raise SystemExit('TSO stopped before the game (*** or a TSO message on the screen): ' + ' | '.join(
            l.strip() for l in s[-6:] if l.strip()))
    if any('PACMAN MVS-6 SMART GHOSTS' in l for l in s):
        raise SystemExit('PACMAN started in LINE MODE (no colour full-screen): REALTIME not possible, TURN instead')
    if time.time() > end:
        raise SystemExit('no game screen within 60 s')
    time.sleep(0.5)
x('TemporaryKeymap(pacgame)')
print(f'{time.strftime("%H:%M:%S")} game started ({words}); game keys on: arrows = PF7/8/10/11, P = PF9 pause, '
      'PA2 redraw, Q + ENTER quit')
try:
    while True:
        time.sleep(1)
        if at_ready():
            break
finally:
    x('TemporaryKeymap()')
print(f'{time.strftime("%H:%M:%S")} back at READY; game keys off')
