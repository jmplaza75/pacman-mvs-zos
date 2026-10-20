#!/usr/bin/env python3
"""MVS-10 (D46, docs/MVS10-PF12.md section 6) live driver of the PF12 gate: plays tests/mvs10live/LIVE10.txt in the
c3270 started by tools/c3270_rt.sh (script port 4001), terminal logged on and at TSO READY; only the game / READY
screens are read (never the logon). Successor of tools/gp2_live.py for the 2.1 key map (that file stays as it was).
Each AID token is one key + Wait(5,Output) (one host write per quantum, as gp2_live.py): PF<n> -> PF(n), PA2 -> PA(2);
after the first PF9 of a pair the pause is held --pause seconds. TYPEQ: Wait(5,Unlock), then String("Q") only - no AID,
nothing reaches the host - and a --hold seconds wait while the game keeps running; ENTER: Enter() (the typed Q +
ENTER = QUIT), then back to READY. One JSON line per token in --log: token, k, t (ms of the day, the trace clock).
The analysis is tools/mvs10_trace.py TRACE --log LOG. Never logs on, never retries; any x3270if error stops.
Usage: mvs10_live.py --log FILE [--port 4001] [--prefix HERC01.PACMAN] [--pause 3] [--hold 3]"""
import argparse
import datetime
import json
import subprocess
import time
from pathlib import Path

R = Path(__file__).resolve().parent.parent
WORDS = 'RULES(CLASSIC) AI(0) GHOSTS(1) SOUND(NO)'


def key(tok):
    if tok == 'PA2':
        return 'PA(2)'
    assert tok.startswith('PF') and 1 <= int(tok[2:]) <= 24, tok
    return f'PF({int(tok[2:])})'


def now_ms():
    d = datetime.datetime.now()
    return ((d.hour * 60 + d.minute) * 60 + d.second) * 1000 + d.microsecond // 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', required=True)
    ap.add_argument('--port', default='4001')
    ap.add_argument('--prefix', default='HERC01.PACMAN')
    ap.add_argument('--pause', type=float, default=3.0)
    ap.add_argument('--hold', type=float, default=3.0)
    a = ap.parse_args()
    tokens = (R / 'tests/mvs10live/LIVE10.txt').read_text().split()
    assert ' '.join(tokens[:2]) == 'AI0 1', tokens[:2]
    tokens = tokens[2:]
    log = open(a.log, 'x')                                   # never overwrite a log

    def x(action, timeout=30):
        r = subprocess.run(['x3270if', '-t', a.port, action], capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            raise SystemExit(f'STOP: x3270if {action}: {r.stderr.strip()}')
        return r.stdout

    def say(tok, k):
        log.write(json.dumps({'token': tok, 'k': k, 't': now_ms()}) + '\n')
        log.flush()

    def screen():
        return [l.rstrip() for l in x('Ascii()').splitlines()]

    def at_ready():
        rows = [l for l in screen() if l.strip()]
        return bool(rows) and rows[-1].strip() == 'READY'

    if not at_ready():
        raise SystemExit('STOP: the terminal is not at TSO READY (log on first)')
    x('TemporaryKeymap()')
    say('EXEC', -1)
    x(f'String("EXEC \'{a.prefix}.CLIST(PACMAN)\' \'{WORDS}\'")')
    x('Enter()')
    end = time.time() + 60
    while not any('COMMAND ===>' in l for l in screen()):
        if time.time() > end:
            raise SystemExit('STOP: no game screen within 60 s')
        time.sleep(0.5)
    time.sleep(1.0)                                          # the first screen settles (keyboard restored)
    paused = False
    for k, tok in enumerate(tokens):
        if tok == 'TYPEQ':
            x('Wait(5,Unlock)')
            say(tok, k)
            x('String("Q")')                                 # typed into the command field: no AID
            time.sleep(a.hold)
            continue
        if tok == 'ENTER':
            x('Wait(5,Unlock)')
            say(tok, k)
            x('Enter()')
            break
        say(tok, k)
        x(key(tok) + ' Wait(5,Output)')
        if tok == 'PF9':
            paused = not paused
            if paused:
                time.sleep(a.pause)
    end = time.time() + 60
    while not at_ready():
        if time.time() > end:
            raise SystemExit('STOP: not back at READY within 60 s')
        time.sleep(0.5)
    say('READY', len(tokens))
    print(f'{time.strftime("%H:%M:%S")} MVS-10 scenario sent ({len(tokens)} tokens), back at READY; '
          f'check: tools/mvs10_trace.py TRACE --log {a.log}')


if __name__ == '__main__':
    main()
