#!/usr/bin/env python3
"""MVS-S2 S2.4: the deterministic live scenarios (played by tools/gp2_live.py through the c3270 script port), built
from Hercules-tested cases and cut at the game end (no key reaches TSO after it), each checked on the independent models
(tests/ref_s2.py): the alarm writes and the bells per event. Writes tests/s2live/LIVE<X>.txt and prints the expected
table for docs/evidence/s2-live-checklist.md.
  A  RTSTILL cards, RULES(ARCADE) AI(3) GHOSTS(1), NORMAL: start 1, death 2, death 2, game over 3 (in play, final
     death frames)
  B  G2RCLR cards, RULES(ARCADE) AI(0) GHOSTS(1) SPEED(FAST): start 1, level clear 3 (G = 3 quanta = 375 ms)
  C  RTWIN cards, RULES(CLASSIC) AI(0) GHOSTS(1), NORMAL: start 1, win 4 (1 + 3 bell-only writes in the end pause)
  D  = A with ALARM(SINGLE): one bell per event (S1 / GP2)
  E  = C with SOUND(NO): silent, end pause 3 s
Usage: make_live.py [--write]"""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(R / 'tests'))
import ref_gp2 as L  # noqa: E402
import ref_rt  # noqa: E402
import ref_s2 as S  # noqa: E402
from ref_rp import bells as gp2_bells  # noqa: E402
from ref_snap import Log  # noqa: E402

# name: (source case, config card, rules, speed, sound, alarm, CLIST keywords)
SCEN = {
    'A': ('rtcases/RTSTILL', 'AI3 1', 'A', 'N', 'Y', 'P', 'RULES(ARCADE) AI(3) GHOSTS(1)'),
    'B': ('gp2cases/G2RCLR', 'AI0 1', 'A', 'F', 'Y', 'P', 'RULES(ARCADE) AI(0) GHOSTS(1) SPEED(FAST)'),
    'C': ('rtcases/RTWIN', 'AI0 1', 'C', 'N', 'Y', 'P', 'RULES(CLASSIC) AI(0) GHOSTS(1)'),
    'D': ('rtcases/RTSTILL', 'AI3 1', 'A', 'N', 'Y', 'S', 'RULES(ARCADE) AI(3) GHOSTS(1) ALARM(SINGLE)'),
    'E': ('rtcases/RTWIN', 'AI0 1', 'C', 'N', 'N', 'P', 'RULES(CLASSIC) AI(0) GHOSTS(1) SOUND(NO)'),
}


def run(rules, cards, per, hs=None):
    log = Log()
    log.kinds = []
    if rules == 'A':
        end, fs = ref_rt.tsd(cards, 'W', snap=log, mk_game=lambda a, n: L.Level(a, n, 'R', 1), mk_ctl=L.LevelRT,
                             per=per, hs=hs)
    else:
        end, fs = ref_rt.tsd(cards, 'W', snap=log, per=per)
    return end, fs, log


def single(rules, fs, log):
    """The S1 / GP2 single-bell streams (ALARM(SINGLE))."""
    if rules == 'A':
        return gp2_bells(fs, log, 'Y')[0]
    out, last, won = [], None, False
    for f, (lives, w) in zip(fs, log):
        out.append(S.alarm(f) if last is None or lives < last or (w and not won) else f)
        last, won = lives, won or w
    return out


def cut(src, cfg, rules, per):
    """The shortest prefix of the source cards (after its config card) whose game ends WIN / LOST / QUIT (an ended
    game stays ended, so a binary search)."""
    cs = (R / f'tests/{src}.txt').read_text().splitlines()[1:]

    def ended(n):
        return run(rules, [cfg] + cs[:n], per)[0][0] in ('WIN', 'LOST', 'QUIT')
    lo, hi = 1, len(cs)
    assert ended(hi), src
    while lo < hi:
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if ended(mid) else (mid + 1, hi)
    return cs[:lo]


def expected(name):
    src, cfg, rules, sp, snd, al, words = SCEN[name]
    per = ref_rt.period(sp)
    cs = cut(src, cfg, rules, per)
    end, fs, log = run(rules, [cfg] + cs, per)
    if snd != 'Y':
        out, trace = list(fs), []
    elif al == 'P':
        out, trace = S.patterns(fs, log, 'Y', 'R', per)
    else:
        out = single(rules, fs, log)
        trace = [(k, 'BELL', 1) for k, f in enumerate(out) if f[0] & 0x04]
    return cs, end, out, trace, len(fs)


if __name__ == '__main__':
    for name in SCEN:
        cs, end, out, trace, nf = expected(name)
        print(f'{name}: {len(cs)} cards, end {end[0]}, {len(out)} writes ({len(out) - nf} after the end screen);',
              'events', S.counts(trace) if SCEN[name][5] == 'P' else len(trace), '; alarm writes',
              [k for k, _, _ in trace])
        if '--write' in sys.argv:
            (R / f'tests/s2live/LIVE{name}.txt').write_text('\n'.join([SCEN[name][1]] + cs) + '\n')
