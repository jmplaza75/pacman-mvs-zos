#!/usr/bin/env python3
"""MVS-S2 (D41, docs/S2-PATTERNS.md): the independent model of the alarm patterns, written from the design, not from the
COBOL. Input: the model streams of a TSD run and their ref_snap.Log with kinds (Q / P quantum write, plain / prompt
form; E end screen; N other write) and snapshots - CLASSIC (lives, won), ARCADE (lives, won, deaths, extra life, level). Output: the streams PACMAN
must send with SOUND Y and ALARM(PATTERN), the WCC alarm bit X'04' on the ringing writes, plus the bell-only writes
(C6 28 00 00) of the end pause, and the trace of the rings.

Events of one write (the S1 / GP2 detection, D35 / D37), highest one kept:
  START 1 (first write), EXTRA LIFE 2 (ARCADE extra-life flag rose), DEATH 3 (CLASSIC lives fell / ARCADE deaths rose),
  LEVEL CLEAR 4 (ARCADE level rose), WIN 5 (won first seen), GAME OVER 6 (a death that leaves 0 lives).
Bells 1 / 2 / 2 / 3 / 4 / 3 at offsets 0, G, 2G ... quanta; G = 2 at 150 ms, 3 at 125 ms (section 3.2).
Rules (section 4): one pattern at a time, an event of higher or equal priority replaces it (offset 0 rings on its own
write); a lower event while a pattern runs never happens (asserted). Only Q / P writes advance a pattern and carry its
steps. TURN: offset 0 only during play. End (section 5): with an end screen, the WIN / GAME OVER steps left go as
bell-only writes after it; without one, the S1 rule (one bell-only write for an event pending at the end)."""

START, XLIFE, DEATH, CLEAR, WIN, OVER = 1, 2, 3, 4, 5, 6
NAMES = {START: 'START', XLIFE: 'XLIFE', DEATH: 'DEATH', CLEAR: 'CLEAR', WIN: 'WIN', OVER: 'OVER'}
BELLS = {START: 1, XLIFE: 2, DEATH: 2, CLEAR: 3, WIN: 4, OVER: 3}
BELL_ONLY = bytes([0xC2, 0x28, 0x00, 0x00])


def gap(per):
    """D41 3.2: the spacing in quanta, exact: 2 at NORMAL (150 ms), 3 at FAST (125 ms)."""
    assert per in (150, 125), per
    return 2 if per == 150 else 3


def alarm(f):
    return bytes([f[0] | 0x04]) + f[1:]


def event(last, snap, won_seen):
    """The highest event of a write, 0 = none (last = the snapshot of the previous write, None for the first)."""
    if last is None:
        return START
    ev, died = 0, False
    if len(snap) == 5:                                   # ARCADE: from the counters
        if snap[3] > last[3]:
            ev = XLIFE
        if snap[2] > last[2]:
            ev, died = DEATH, True
        if snap[4] > last[4]:
            ev = CLEAR
    elif snap[0] < last[0]:                              # CLASSIC: lives fell
        ev, died = DEATH, True
    if snap[1] and not won_seen:
        ev = WIN
    if died and snap[0] == 0:
        ev = OVER
    return ev


def patterns(frames, log, sound, play, per):
    """-> (streams, trace); trace = [(write index, event name or 'STEP', bell number)] of every ring."""
    if sound != 'Y':
        return list(frames), []
    kinds = log.kinds
    assert kinds is not None and len(kinds) == len(frames) == len(log)
    g = gap(per)
    out, trace = [], []
    last, won_seen, act = None, False, None
    for k, (f, snap, kind) in enumerate(zip(frames, log, kinds)):
        ev = event(last, snap, won_seen)
        last, won_seen = snap, won_seen or bool(snap[1])
        ring = False
        if ev:
            assert act is None or ev >= act['pri'], ('lower event during a pattern', k, NAMES[ev], act)
            ring, act = True, None
            trace.append((k, NAMES[ev], 1))
            if BELLS[ev] > 1 and (play == 'R' or ev >= WIN):
                act = {'pri': ev, 'left': BELLS[ev] - 1, 'next': g, 'n': 1}
        elif act is not None and kind in ('Q', 'P'):
            act['next'] -= 1
            if act['next'] == 0:
                ring = True
                act['n'] += 1
                trace.append((k, 'STEP', act['n']))
                act['left'] -= 1
                act['next'] = g
                if act['left'] == 0:
                    act = None
        out.append(alarm(f) if ring else f)
    if kinds and kinds[-1] == 'E':
        if act is not None and act['pri'] >= WIN:
            for _ in range(act['left']):
                act['n'] += 1
                trace.append((len(out), 'STEP', act['n']))
                out.append(alarm(BELL_ONLY))
    else:
        ev = event(last, log.state(), won_seen)
        if ev:
            trace.append((len(out), NAMES[ev], 1))
            out.append(alarm(BELL_ONLY))
    return out, trace


def counts(trace):
    """{event name: bells rung for it} per occurrence, in order: [(name, bells)]."""
    out = []
    for _, name, n in trace:
        if name != 'STEP':
            out.append([name, 1])
        else:
            out[-1][1] = n
    return [tuple(x) for x in out]
