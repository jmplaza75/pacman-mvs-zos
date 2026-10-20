#!/usr/bin/env python3
"""ZOS-7 ARCADE live input driver (docs/zos7-design.md). Sends the approved plan of ONE case (L1, L2 or L3) to a
running c3270 through its script port, exactly as tools/zowe/zos6_drive.py (frozen; its Driver is reused unchanged):
never logs on, never sends a userid or password, never starts or stops a trace, never starts another case, never
retries; every action waits Wait(5,Unlock) first; one JSON log entry per action.
Usage: zos7_drive.py --port N --case L1|L2|L3 --log <outside-repo-path> [--prefix Z00000.PACMAN]

Cases (decisions D3 / D4, 2026-10-19): every case ARCADE (the CLIST default) at LEVEL >= 2 (not eligible: the high
score is read, never written), SOUND(NO) (alarm = ZOS-8), PRESENT(COALESCED) explicit (never the EVERY default).
L1 TURN, LEVEL 13, ANIM(NO): the MVS scenario B (tests/gp2live/LIVEB.txt), one typed command + ENTER per screen.
L2 / L3 REALTIME NORMAL / FAST, LEVEL 2: the wall-stop plan of tools/zowe/zos7_scen.py; the game ends LOST (no Q).
"""
import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zos6_drive as Z6D  # noqa: E402
import zos7_scen as SC  # noqa: E402

# RULES(ARCADE) is the installed CLIST's default (D43, src/zos/PACMAN.clist PROC, unchanged since zos-6) and is not
# typed: the longest EXEC proven on the live ISPF Command Shell is R2's (113 characters); the ARCADE game itself is
# proven by the checker's ARCADE model / end lines. PRESENT(COALESCED) is always typed (never the EVERY default).
KW_RT = 'AI(0) LEVEL(2) PLAY(REALTIME) SOUND(NO) PRESENT(COALESCED)'
KW_TURN = 'AI(0) LEVEL(13) PLAY(TURN) ANIM(NO) SOUND(NO) PRESENT(COALESCED)'
HEAD = [('transition', 'EXEC'), ('expect', '***'), ('transition', 'ENTER'), ('expect', 'GAME')]
TAIL = [('expect', '***'), ('closure', 'ENTER'), ('expect', 'SHELL')]


def rt_steps():
    out = []
    for k, s in SC.KEYS:
        out += [('wait', s), ('gameplay', k)]
    return HEAD + out + TAIL


def turn_steps():
    return HEAD + [('gameplay', c) for c in SC.liveb()[1:]] + TAIL


PLANS = {
    'L1': {'T': None, 'play': 'T', 'start': 13, 'kw': KW_TURN, 'cfg': SC.CFG, 'steps': turn_steps()},
    'L2': {'T': 150, 'play': 'R', 'start': SC.START, 'present': 'C', 'kw': KW_RT, 'cfg': SC.CFG, 'steps': rt_steps()},
    'L3': {'T': 125, 'play': 'R', 'start': SC.START, 'present': 'C', 'kw': KW_RT + ' SPEED(FAST)', 'cfg': SC.CFG,
           'steps': rt_steps()},
}
# gameplay action -> TN3270E AID and the card character the model consumes (REALTIME: Z6D.EXPECT; TURN: typed text)
EXPECT = dict(Z6D.EXPECT)
for _c in 'UDLR':
    EXPECT[_c] = (0x7D, _c)
CALLS = dict(Z6D.CALLS)
for _c in 'UDLR':
    CALLS[_c] = [f'String("{_c}")', 'Enter()']


def command(case, prefix):
    return f"EXEC '{prefix}.CLIST(PACMAN)' '{PLANS[case]['kw']}'"


def planned(case, category=None):
    return [(c, a) for c, a in PLANS[case]['steps'] if c not in ('wait', 'expect') and category in (None, c)]


def run(case, port, log, prefix):
    d = Z6D.Driver(port, log)
    if Z6D.SHELL not in d.screen():
        raise Z6D.Stop('the ISPF Command Shell is not on the screen')
    for kind, v in PLANS[case]['steps']:
        if kind == 'wait':
            time.sleep(v)
        elif kind == 'expect':
            d.expect(v, {'GAME': 30, 'SHELL': 60, '***': 60}[v])
        elif v == 'EXEC':
            d.act(kind, 'EXEC', [f'String("{command(case, prefix)}")', 'Enter()'])
        else:
            d.act(kind, v, CALLS[v])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', required=True)
    ap.add_argument('--case', required=True, choices=sorted(PLANS))
    ap.add_argument('--log', required=True)
    ap.add_argument('--prefix', default='Z00000.PACMAN')
    a = ap.parse_args()
    with open(a.log, 'x') as log:                         # never overwrite a log
        try:
            run(a.case, a.port, log, a.prefix)
        except Z6D.Stop as e:
            print(f'ZOS-7 DRIVER STOP ({a.case}): {e}')
            sys.exit(1)
    print(f'ZOS-7 DRIVER {a.case}: plan sent completely; stop the trace now (Trace(Off)); no other case is started '
          'here')


if __name__ == '__main__':
    main()
