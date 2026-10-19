#!/usr/bin/env python3
"""ZOS-6 live input driver (docs/zos6-design.md section 7). Sends the approved plan of ONE case (R1 or R2) to a running
c3270 through its script port, after the operator has logged on, entered ISPF option 6 and started the trace.

Usage: zos6_drive.py --port N --case R1|R2 --log <outside-repo-path> [--prefix Z00000.PACMAN]

Never logs on, never sends a userid or password, never starts or stops a trace, never runs R2 by itself, never retries.
Starts only with `ISPF Command Shell` on the screen (Ascii()). Every action: Wait(5,Unlock), then the action; one JSON
log line per action: ordinal, category (transition | gameplay | closure), planned action, requested / Wait start /
unlock / send timestamps (ms since the epoch), result or error. Expect steps poll the screen (Ascii()) for the state the
plan needs next. STOP (exit 1, nothing more sent) on: keyboard locked > 5 s, any x3270if error or timeout, IKJ / IEC /
IGZ / CEE / ABEND / PACMAN: on the screen, the game in line mode, no game screen within 30 s, no shell within 60 s.
Actions used (checked against the installed x3270 4.5ga6): PF(7) PF(8) PF(9) PF(10) PF(11) PA(2) Enter() String("..")
Wait(5,Unlock) Ascii().
"""
import argparse
import json
import re
import subprocess
import sys
import time

# The approved plans (docs/zos6-design.md section 2). Steps: (category, action) actions; ('wait', seconds);
# ('expect', what). Gameplay actions: PF7 PF8 PF9 PF10 PF11 PA2 x Q (x and Q = String + Enter).
# ZOS-6 production design (docs/zos6-production-design.md, ZV-D33): R1 / R2 run with PRESENT(COALESCED) explicitly
# ('present': 'C'); absent PRESENT would be EVERY (the D33 loop).
KW = 'AI(0) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO) PRESENT(COALESCED)'
PLANS = {
    'R1': {'T': 150, 'present': 'C', 'kw': KW, 'steps': [
        ('transition', 'EXEC'), ('expect', '***'), ('transition', 'ENTER'), ('expect', 'GAME'),
        ('wait', 5), ('gameplay', 'PF8'), ('wait', 60), ('gameplay', 'PF9'), ('wait', 60), ('gameplay', 'PF9'),
        ('wait', 10), ('gameplay', 'x'), ('wait', 3), ('gameplay', 'PA2'), ('wait', 3), ('gameplay', 'PF11'),
        ('wait', 10), ('gameplay', 'Q'), ('expect', '***'), ('closure', 'ENTER'), ('expect', 'SHELL')]},
    'R2': {'T': 125, 'present': 'C', 'kw': KW + ' SPEED(FAST)', 'steps': [
        ('transition', 'EXEC'), ('expect', '***'), ('transition', 'ENTER'), ('expect', 'GAME'),
        ('wait', 2), ('gameplay', 'PF11'), ('wait', 5), ('gameplay', 'PF8'), ('wait', 2), ('gameplay', 'PF7'),
        ('wait', 2), ('gameplay', 'PF10'), ('wait', 30), ('gameplay', 'Q'), ('expect', '***'), ('closure', 'ENTER'),
        ('expect', 'SHELL')]},
}
# gameplay action -> (TN3270E AID, the card character the REALTIME model consumes)
EXPECT = {'PF7': (0xF7, 'U'), 'PF8': (0xF8, 'D'), 'PF9': (0xF9, 'P'), 'PF10': (0x7A, 'L'), 'PF11': (0x7B, 'R'),
          'PA2': (0x6E, '*'), 'x': (0x7D, 'x'), 'Q': (0x7D, 'Q')}
CALLS = {'PF7': ['PF(7)'], 'PF8': ['PF(8)'], 'PF9': ['PF(9)'], 'PF10': ['PF(10)'], 'PF11': ['PF(11)'],
         'PA2': ['PA(2)'], 'x': ['String("x")', 'Enter()'], 'Q': ['String("Q")', 'Enter()'], 'ENTER': ['Enter()']}
SHELL = 'ISPF Command Shell'
TITLE = 'P A C - M A N'
BAD = re.compile(r'IKJ\d{5}|IEC\d{3}|IGZ\d{4}|CEE\d{4}|ABEND|PACMAN:')


def command(case, prefix):
    return f"EXEC '{prefix}.CLIST(PACMAN)' '{PLANS[case]['kw']}'"


def planned(case, category=None):
    """The planned actions of a case, in order: [(category, action)] (optionally one category only)."""
    return [(c, a) for c, a in PLANS[case]['steps'] if c not in ('wait', 'expect') and category in (None, c)]


class Stop(Exception):
    pass


def now():
    return int(time.time() * 1000)


class Driver:
    def __init__(self, port, log):
        self.port, self.log, self.n = port, log, 0

    def x(self, action, timeout=10):
        """One action through `x3270if -t PORT ACTION` (the real CLI contract, checked live on the idle ISPF shell
        2026-10-16): exit status 0 = the action succeeded, anything else = failure; stdout is the action's raw text
        (Ascii(): the screen rows; most actions: nothing). No `data:` prefix and no `ok` line exist on this interface
        (those belong to s3270's own stdin protocol). A timeout is a failure."""
        try:
            r = subprocess.run(['x3270if', '-t', str(self.port), action], capture_output=True, text=True,
                               timeout=timeout)
        except subprocess.TimeoutExpired:
            raise Stop(f'x3270if {action}: no answer within {timeout} s')
        if r.returncode:
            raise Stop(f'x3270if {action}: rc {r.returncode} {r.stdout.strip()[-200:]} {r.stderr.strip()[-200:]}')
        return r.stdout

    def screen(self):
        return self.x('Ascii()')

    def act(self, category, action, calls):
        self.n += 1
        e = {'ordinal': self.n, 'category': category, 'action': action, 'requested': now()}
        try:
            e['wait_start'] = now()
            self.x('Wait(5,Unlock)', timeout=15)
            e['unlocked'] = now()
            for c in calls:
                self.x(c)
            e['sent'], e['result'] = now(), 'ok'
        except Stop as ex:
            e['result'] = f'error: {ex}'
            raise Stop(e['result'])
        finally:
            self.log.write(json.dumps(e) + '\n')
            self.log.flush()

    def expect(self, what, timeout):
        end = time.time() + timeout
        while time.time() < end:
            s = self.screen()
            m = BAD.search(s)
            if m:
                raise Stop(f'{m.group(0)} on the screen')
            if what == 'GAME' and TITLE in s:
                return
            if what == 'GAME' and re.search(r'^ ?T000 ', s, re.M):
                raise Stop('the game started in line mode')
            if what == 'SHELL' and SHELL in s:
                return
            if what == '***' and '***' in s:
                return
            time.sleep(0.25)
        raise Stop(f'{what} not on the screen within {timeout} s')


def run(case, port, log, prefix):
    d = Driver(port, log)
    if SHELL not in d.screen():
        raise Stop('the ISPF Command Shell is not on the screen')
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
        except Stop as e:
            print(f'ZOS-6 DRIVER STOP ({a.case}): {e}')
            sys.exit(1)
    print(f'ZOS-6 DRIVER {a.case}: plan sent completely; stop the trace now (Trace(Off)); R2 is never started here')


if __name__ == '__main__':
    main()
