#!/usr/bin/env python3
"""ZOS-6 protocol probe input controller (docs/zos6-protocol-probe.md). One probe run (one mode) per invocation.

Usage: zos6_probe_drive.py --port N --mode P0|PT|PN|PH|PB4|PR2|PR2I --log <outside-repo-path> [--loadlib Z00000.PACMAN.Z6PRB.LOAD]

Uses the zos6_drive.Driver adapter (the real `x3270if -t` contract). Starts only with `ISPF Command Shell` on the
screen; sends the CALL of the probe (transition), the ENTER at ISPF's `***` if one appears before the probe screen
(transition), then three timed PF attempts from the moment the probe screen is seen: PF4 at +5 s, PF5 at +10 s, PF6 at
+15 s (distinct AIDs F4 / F5 / F6), each after Wait(5,Unlock). A Wait(5,Unlock) that times out is an OBSERVATION here
(logged `not sent: keyboard locked 5 s`, the key is not sent, never retried; the next attempt follows its own
schedule); any other x3270if error is a STOP. Then the closure: `***` after the probe's summary, ENTER, the shell.
Never logs on, never starts or stops a trace, never repeats a key. One JSON line per action.
"""
import argparse
import json
import sys
import time

from zos6_drive import Driver, Stop, now, SHELL

TITLE = 'PACZ6P ZOS-6 PROTOCOL PROBE'
ATTEMPTS = [(5, 'PF4', 'PF(4)'), (10, 'PF5', 'PF(5)'), (15, 'PF6', 'PF(6)')]


def command(mode, loadlib):
    return f"CALL '{loadlib}(PACZ6P)' '{mode}'"


def log_line(d, category, action, req, ws=None, unl=None, sent=None, result='ok'):
    d.n += 1
    d.log.write(json.dumps({'ordinal': d.n, 'category': category, 'action': action, 'requested': req,
                            'wait_start': ws, 'unlocked': unl, 'sent': sent, 'result': result}) + '\n')
    d.log.flush()


def wait_for(d, words, timeout):
    end = time.time() + timeout
    while time.time() < end:
        s = d.screen()
        for w in words:
            if w in s:
                return w
        time.sleep(0.25)
    raise Stop(f'none of {words} on the screen within {timeout} s')


def attempt(d, action, call):
    req = ws = now()
    try:
        d.x('Wait(5,Unlock)', timeout=15)
    except Stop as ex:
        if 'Timed out' in str(ex) or 'timed out' in str(ex):
            log_line(d, 'probe', action, req, ws, None, None, 'not sent: keyboard locked 5 s')
            return
        log_line(d, 'probe', action, req, ws, None, None, f'error: {ex}')
        raise
    unl = now()
    try:
        d.x(call)
    except Stop as ex:
        log_line(d, 'probe', action, req, ws, unl, None, f'error: {ex}')
        raise
    log_line(d, 'probe', action, req, ws, unl, now())


def run(mode, port, log, loadlib):
    d = Driver(port, log)
    if SHELL not in d.screen():
        raise Stop('the ISPF Command Shell is not on the screen')
    d.act('transition', 'CALL', [f'String("{command(mode, loadlib)}")', 'Enter()'])
    if wait_for(d, [TITLE, '***'], 30) == '***':
        d.act('transition', 'ENTER', ['Enter()'])
        wait_for(d, [TITLE], 30)
    t0 = time.time()
    for at, action, call in ATTEMPTS:
        time.sleep(max(0.0, t0 + at - time.time()))
        attempt(d, action, call)
    wait_for(d, ['***'], 90)
    d.act('closure', 'ENTER', ['Enter()'])
    wait_for(d, [SHELL], 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', required=True)
    ap.add_argument('--mode', required=True, choices=['P0', 'PT', 'PN', 'PH', 'PB4', 'PR2', 'PR2I'])
    ap.add_argument('--log', required=True)
    ap.add_argument('--loadlib', default='Z00000.PACMAN.Z6PRB.LOAD')
    a = ap.parse_args()
    with open(a.log, 'x') as log:
        try:
            run(a.mode, a.port, log, a.loadlib)
        except Stop as e:
            print(f'ZOS-6 PROBE DRIVER STOP ({a.mode}): {e}')
            sys.exit(1)
    print(f'ZOS-6 PROBE DRIVER {a.mode}: done; stop the trace now (Trace(Off))')


if __name__ == '__main__':
    main()
