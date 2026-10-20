#!/usr/bin/env python3
"""ZOS-8 live input driver (docs/zos8-design.md, U1-U12). Sends the approved plan of ONE case to a running c3270
through its script port, on the frozen ZOS-6 Driver (tools/zowe/zos6_drive.py, imported unchanged): never logs on,
never sends a userid or password, never starts or stops a trace, never starts another case, never retries a case;
every action waits Wait(5,Unlock) first; one JSON log entry per action.

Usage: zos8_drive.py --port N --case CASE --log <outside-repo-path> [--prefix Z00000.PACMAN] [--resume-after LOG]
--resume-after LOG [LOG] (Stage D only): continue a case an earlier run stopped, at one of two points only: its EXEC
held at the initial `***` (continue with the hold's ENTER) or its complete test screen displayed (continue with the
abend ENTER); nothing is resent; the ordinals continue the earlier log(s).
Cases:
- Stage C (high score on test data, TURN, SOUND(NO)): HL1 HL2 HL3 HL4 (CLIST(PACZ8HT) -> HS8.T1), HL6 (PACZ8HU ->
  no dataset -> DUMMY), HL8 (PACZ8HF -> HSFULL.T1). Only HL8 may show IEC217I B14 (the failed STOW of HSFULL.T1);
  if TSO holds it with `***` before the end of the game, exactly one ENTER (category hold) is sent.
- Stage D (recovery, U12 micro-gates): E1 E2 E3 = EXEC CLIST(RPESTAE) CASE(Ex), the ISPF `***` hold every EXEC from the
  shell shows + one ENTER, ENTER on the test screen (the forced
  0C7), then the recovery: every `***` is answered by one ENTER (category recovery, at most 4) until the ISPF Command
  Shell is back; `LISTALC STATUS` (proof of a usable line-mode TSO); `FREE F(CEEOPTS)` only if LISTALC shows a
  CEEOPTS DD left by an interrupted CLIST (category cleanup); then the clean follow-up game GD (installed
  CLIST(PACMAN), CLASSIC TURN, the cards of tests/zos8live/GD.txt). LISTALC and FREE are held like every command
  from the shell (live 2026-10-20, E1 recovery): the ISPF initial hold (the shell screen, `===> <command>`, `***`),
  one ENTER, then the line-mode output pages (each ends with `***`, one ENTER each; LISTALC: 13 on that session, the
  first with the --DDNAME---DISP-- header; FREE: none), then the idle shell (held_command).
- Stage F (production first write, frozen 2026-10-20): SF = HL2's LIVEB cards through the installed CLIST(PACMAN)
  (ARCADE LEVEL 1 TURN, DATA(HISCORE) absent -> 980, NEW HIGH SCORE: PACHSIO REPL + STOW creates the member).
- Stage E (sound): S8A / S8B = the ZOS-7 L2 / L3 plan with SOUND(YES) (REALTIME, LEVEL 2: DATA read only); S8C =
  CLASSIC TURN WIN (tests/zos8live/S8C.txt) with SOUND(YES).
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zos6_drive as Z6D  # noqa: E402
import zos7_drive as Z7D  # noqa: E402
import zos7_scen as SC7  # noqa: E402
import zos8_scen as S  # noqa: E402

HEAD = [('transition', 'EXEC'), ('expect', '***'), ('transition', 'ENTER'), ('expect', 'GAME')]
TAIL = [('expect', '***END'), ('closure', 'ENTER'), ('expect', 'SHELL')]
RECOVERY_MAX = 4
PAGES_MAX = 30                # output pages of one held command (LISTALC 2026-10-20: 13); more = STOP
PAGE_TIMEOUT = 30             # s for each next screen of a held command
SHELL_TITLE = Z6D.SHELL
DD_DISP = re.compile(r'CEEOPTS\s+(KEEP|DELETE|CATLG|UNCATLG|PASS)')


def test_screen(case):
    """The exact lines of the RPESTAE test screen of a case (src/probe/PACRPE.cob BUILD-SCREEN; E1 live 2026-10-20)."""
    return [f'PACMAN RP.0 ESTAE LIVE TEST - CASE {case}', 'PACHSIO READ RC=0000 (E2 ONLY, ELSE 0)',
            'PRESS ENTER: THE PROGRAM FORCES A 0C7 ABEND.', 'PASS: LINE MODE, ABEND MESSAGE, THEN READY.',
            'E3 = CONTROL: LINE MODE FIRST (FSOF), THEN 0C7.']


def screen_buffer(s):
    """The 3270 screen buffer as one string: the Ascii() rows joined at the screen width (every row padded to the
    widest), so a field that continues past the end of a row stays contiguous (E1-T2 2026-10-20, 27 x 120: the E3
    line starts at row 5 column 81 and wraps). Nothing else is changed: no whitespace is removed or merged."""
    rows = s.splitlines()
    w = max((len(r) for r in rows), default=0)
    return ''.join(r.ljust(w) for r in rows)


def screen_state(s, case):
    """-> 'screen' when the screen buffer (screen_buffer) is exactly the case's test screen: each of its lines exactly
    once, in order, and nothing but blanks elsewhere; None while none of its lines is there (not yet); STOP when only
    some of them are there (altered, missing), a line repeats, the order differs, other text is on it, or any error
    text is outside the exact lines. The expected `ABEND` of the PRESS ENTER line is exempt only as that exact line
    (E1 2026-10-20: the generic detector stopped on it)."""
    buf = screen_buffer(s)
    lines = test_screen(case)
    rest = buf
    for line in lines:
        rest = rest.replace(line, ' ' * len(line))
    m = Z6D.BAD.search(rest)
    if m:
        raise Z6D.Stop(f'{m.group(0)} on the screen')
    found = [buf.count(line) for line in lines]
    if not any(found):
        return None
    if not all(found):
        raise Z6D.Stop(f'the {case} test screen is incomplete or altered: '
                       f'{[line for line, n in zip(lines, found) if not n]} missing')
    pos = [buf.index(line) for line in lines]
    if max(found) > 1 or pos != sorted(pos):
        raise Z6D.Stop(f'the {case} test screen has a repeated line or its lines out of order')
    if rest.strip():
        raise Z6D.Stop(f'the {case} test screen carries other text: {rest.split()[:6]}')
    return 'screen'


RECOVER_TIMEOUT = 90          # s: the shell must be back after the abend (else STOP: the user reconnects)
IEC_HOLD = re.compile(r'IEC217I B14-0C')


def turn_steps(name, head=HEAD):
    return head + [('gameplay', c) for c in S.live_cards(name)[1:]] + TAIL


def rt_steps():
    out = []
    for k, s in SC7.KEYS:
        out += [('wait', s), ('gameplay', k)]
    return HEAD + out + TAIL


PLANS = {}
for _n in S.HL_ORDER + ['S8C', 'SF']:
    PLANS[_n] = {'kind': 'TURN', 'game': _n, 'clist': S.clist_of(_n), 'kw': S.kw_of(_n), 'steps': turn_steps(_n),
                 'iec_hold': _n == 'HL8'}
for _n, _t in S.S8_RT.items():
    PLANS[_n] = {'kind': 'RT', 'T': _t, 'play': 'R', 'start': SC7.START, 'present': 'C', 'cfg': SC7.CFG,
                 'clist': 'PACMAN', 'kw': S.KW_S8 + (' SPEED(FAST)' if _t == 125 else ''), 'steps': rt_steps(),
                 'iec_hold': False}
GD_HEAD = [('transition', 'EXEC:GD')] + HEAD[1:]
for _e in ('E1', 'E2', 'E3'):
    PLANS[_e] = {'kind': 'ESTAE', 'case': _e, 'clist': 'RPESTAE', 'kw': f'CASE({_e})', 'iec_hold': False,
                 'steps': [('transition', 'EXEC'), ('expect', '***'), ('transition', 'ENTER'), ('expect', 'ESTAE'),
                           ('abend', 'ENTER'), ('recover', None),
                           ('check', 'LISTALC'), ('cleanup', None)] + turn_steps('GD', GD_HEAD)}
EXPECT = dict(Z7D.EXPECT)
CALLS = dict(Z7D.CALLS)
CALLS['ENTER'] = ['Enter()']


def command(case, action, prefix):
    p = PLANS[case]
    if action == 'EXEC':
        return f"EXEC '{prefix}.CLIST({p['clist']})' '{p['kw']}'"
    if action == 'EXEC:GD':
        return f"EXEC '{prefix}.CLIST(PACMAN)' '{S.kw_of('GD')}'"
    return {'LISTALC': 'LISTALC STATUS', 'FREE': 'FREE F(CEEOPTS)'}[action]


def shell_idle(s):
    """The idle ISPF Command Shell: the panel, no `***`, exactly one command line and it is empty."""
    cmd = [r.strip() for r in s.splitlines() if r.strip().startswith('===>')]
    return SHELL_TITLE in s and '***' not in s and cmd == ['===>']


def initial_hold(s, text):
    """The ISPF initial hold of a command typed on the shell: the panel with `===> <text>` and `***`."""
    cmd = [r.strip() for r in s.splitlines() if r.strip().startswith('===>')]
    return SHELL_TITLE in s and '***' in s and cmd == [f'===> {text}']


def output_page(s):
    """A line-mode output page: `***`, not the shell panel."""
    return '***' in s and SHELL_TITLE not in s


def page_lines(pages):
    """The output lines of the pages in order (blank lines and the `***` markers removed, stripped)."""
    return [r.strip() for s in pages for r in s.splitlines() if r.strip() and r.strip() != '***']


def ceeopts_of(lines, prefix):
    """The strict CEEOPTS DD rule (E1 recovery 2026-10-20) on LISTALC STATUS output lines: True only for exactly one
    DD line `CEEOPTS <disp>` right after the dataset line <prefix>.CEEOPTS; False when CEEOPTS appears nowhere;
    anything else (CEEOPTS elsewhere, twice, under another dataset) is ambiguous -> ValueError."""
    loose = [i for i, r in enumerate(lines) if re.search(r'\bCEEOPTS\b', r)]
    dd = [i for i, r in enumerate(lines) if DD_DISP.fullmatch(r.strip())]
    if not loose:
        return False
    if len(dd) == 1 and dd[0] > 0 and lines[dd[0] - 1].strip() == f'{prefix}.CEEOPTS' and \
            set(loose) == {dd[0] - 1, dd[0]}:
        return True
    raise ValueError(f'CEEOPTS listed ambiguously: {[lines[i] for i in loose]}')


def planned(case, category=None):
    """The fixed planned actions (the recovery ENTERs and the conditional cleanup are not fixed: see the checker)."""
    return [(c, a) for c, a in PLANS[case]['steps'] if c not in ('wait', 'expect', 'recover', 'cleanup') and
            category in (None, c)]


class Driver8(Z6D.Driver):
    """The frozen ZOS-6 Driver with the ZOS-8 screen states; Z6D.Driver.expect is used unchanged for the game."""

    def poll(self, timeout, done, allow_bad=False):
        end = time.time() + timeout
        while time.time() < end:
            s = self.screen()
            m = Z6D.BAD.search(s)
            if m and not allow_bad:
                raise Z6D.Stop(f'{m.group(0)} on the screen')
            r = done(s)
            if r:
                return r, s
            time.sleep(0.25)
        raise Z6D.Stop(f'expected screen not reached within {timeout} s')

    def held_command(self, category, action, text):
        """One command from the idle shell, held like every shell command: every screen is validated before its ENTER
        - first exactly the ISPF initial hold (the shell with `===> <text>` and `***`), then only line-mode output
        pages (`***`, no shell) until the idle shell; one ENTER (category, 'ENTER') per validated hold or page; any
        error text, any other screen, more than PAGES_MAX pages or PAGE_TIMEOUT s without a new screen: STOP.
        -> the output pages."""
        prev = self.screen()
        if not shell_idle(prev):
            raise Z6D.Stop(f'not at the idle ISPF Command Shell before {text}')
        self.act(category, action, [f'String("{text}")', 'Enter()'])
        hold, pages = False, []
        while True:
            end = time.time() + PAGE_TIMEOUT
            while True:
                if time.time() > end:
                    raise Z6D.Stop(f'{text}: no next screen within {PAGE_TIMEOUT} s')
                s = self.screen()
                m = Z6D.BAD.search(s)
                if m:
                    raise Z6D.Stop(f'{text}: {m.group(0)} on the screen')
                if s != prev and ('***' in s or shell_idle(s)):         # a new screen (the typed one is neither)
                    break
                time.sleep(0.25)
            if not hold:
                if not initial_hold(s, text):
                    raise Z6D.Stop(f'{text}: the first screen is not the ISPF initial hold')
                hold = True
            elif shell_idle(s):
                return pages
            elif output_page(s):
                pages.append(s)
                if len(pages) > PAGES_MAX:
                    raise Z6D.Stop(f'{text}: more than {PAGES_MAX} output pages')
            else:
                raise Z6D.Stop(f'{text}: a screen that is neither an output page nor the idle shell')
            prev = s
            self.act(category, 'ENTER', CALLS['ENTER'])


def resume_point(case, prefix, screen, done):
    """Stage D resume, only at the two points where a first E1 run stopped (2026-10-20), never anywhere else:
    - after the EXEC (the earlier log = exactly [EXEC ok]): the screen must be that EXEC's initial `***` hold (the
      command on the input line, `***`, no test screen) -> continue with the hold's ENTER;
    - after the hold's ENTER (the earlier logs = exactly [EXEC ok, hold ENTER ok], ordinals 1, 2): the screen must be
      the complete test screen of the case (screen_state) -> continue with the abend ENTER.
    -> the index of the next plan step."""
    p = PLANS[case]
    if p['kind'] != 'ESTAE':
        raise Z6D.Stop('resume is only defined for the Stage D cases')
    got = [(x.get('ordinal'), x.get('category'), x.get('action'), x.get('result')) for x in done]
    steps = p['steps']
    assert steps[:5] == [('transition', 'EXEC'), ('expect', '***'), ('transition', 'ENTER'), ('expect', 'ESTAE'),
                         ('abend', 'ENTER')]
    if got == [(1, 'transition', 'EXEC', 'ok')]:
        if '***' not in screen or command(case, 'EXEC', prefix) not in screen or 'ESTAE LIVE TEST' in screen:
            raise Z6D.Stop('the screen is not the initial *** hold of the pending EXEC')
        return 2
    if got == [(1, 'transition', 'EXEC', 'ok'), (2, 'transition', 'ENTER', 'ok')]:
        if screen_state(screen, case) != 'screen':
            raise Z6D.Stop(f'the screen is not the complete test screen of {case}')
        return 4
    raise Z6D.Stop(f'the earlier driver logs are not a resume point of {case}: {got}')


def run(case, port, log, prefix, done=None):
    """done: the earlier driver log entries (resume, Stage D only): the plan continues after the pending EXEC's hold,
    the ordinals continue that log."""
    p = PLANS[case]
    d = Driver8(port, log)
    s = d.screen()
    first = 0
    if done is not None:
        first = resume_point(case, prefix, s, done)
        d.n = len(done)
    elif Z6D.SHELL not in s:
        raise Z6D.Stop('the ISPF Command Shell is not on the screen')
    ceeopts = False
    for kind, v in p['steps'][first:]:
        if kind == 'wait':
            time.sleep(v)
        elif kind == 'expect' and v == '***END':
            holds = 0
            while True:
                if not p['iec_hold']:
                    d.expect('***', 60)
                    break
                # HL8 only: IEC217I B14-0C (the failed STOW on HSFULL.T1) may be on the screen; any other error stops
                _, s = d.poll(60, lambda s: '***' in s, allow_bad=True)
                found = Z6D.BAD.findall(s)
                if any(b != 'IEC217' for b in found) or ('IEC217' in found and not IEC_HOLD.search(s)):
                    raise Z6D.Stop(f'{found} on the screen (HL8 allows IEC217I B14-0C only)')
                if IEC_HOLD.search(s) and holds == 0 and 'HIGH SCORE' not in s:
                    holds += 1
                    d.act('hold', 'ENTER', CALLS['ENTER'])
                    continue
                break
        elif kind == 'expect' and v == 'ESTAE':
            d.poll(30, lambda s: screen_state(s, p['case']), allow_bad=True)
        elif kind == 'check' and v == 'LISTALC':
            pages = d.held_command('check', 'LISTALC', command(case, 'LISTALC', prefix))
            lines = page_lines(pages)
            if not lines or lines[0] != '--DDNAME---DISP--':
                raise Z6D.Stop('LISTALC STATUS: no output page, or its first line is not the --DDNAME---DISP-- header')
            try:
                ceeopts = ceeopts_of(lines, prefix)
            except ValueError as ex:
                raise Z6D.Stop(f'LISTALC STATUS: {ex}')
        elif kind == 'expect':
            d.expect(v, {'GAME': 30, 'SHELL': 60, '***': 60}[v])
        elif kind == 'recover':
            n, end = 0, time.time() + RECOVER_TIMEOUT
            while True:
                if time.time() > end:
                    raise Z6D.Stop('the ISPF Command Shell did not come back after the abend')
                s = d.screen()
                if '***' in s:
                    n += 1
                    if n > RECOVERY_MAX:
                        raise Z6D.Stop(f'more than {RECOVERY_MAX} recovery holds')
                    d.act('recovery', 'ENTER', CALLS['ENTER'])
                elif Z6D.SHELL in s:
                    break
                time.sleep(0.25)
        elif kind == 'cleanup':
            if ceeopts and d.held_command('cleanup', 'FREE', command(case, 'FREE', prefix)):
                raise Z6D.Stop('FREE F(CEEOPTS) wrote output (a successful FREE writes none)')
        elif v in ('EXEC', 'EXEC:GD'):
            d.act(kind, v, [f'String("{command(case, v, prefix)}")', 'Enter()'])
        else:
            d.act(kind, v, CALLS[v])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', required=True)
    ap.add_argument('--case', required=True, choices=sorted(PLANS))
    ap.add_argument('--log', required=True)
    ap.add_argument('--prefix', default='Z00000.PACMAN')
    ap.add_argument('--resume-after', nargs='+', help='Stage D only: the earlier driver log(s) of the case, in order')
    a = ap.parse_args()
    done = None
    if a.resume_after:
        done = [json.loads(x) for f in a.resume_after for x in Path(f).read_text().splitlines() if x.strip()]
    with open(a.log, 'x') as log:                         # never overwrite a log
        try:
            run(a.case, a.port, log, a.prefix, done)
        except Z6D.Stop as e:
            print(f'ZOS-8 DRIVER STOP ({a.case}): {e}')
            sys.exit(1)
    print(f'ZOS-8 DRIVER {a.case}: plan sent completely; stop the trace now (Trace(Off)); no other case is started '
          'here')


if __name__ == '__main__':
    main()
