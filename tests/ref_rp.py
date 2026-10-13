#!/usr/bin/env python3
"""MVS-RP (D39, docs/RP-POLISH.md sections 2-5): the independent model of what an ARCADE screen decorates, written from
the design, not from the COBOL. Tracker.frame() is called for every screen the display composes (prompt, tick, quantum
frame, end screen) and returns None for CLASSIC, else a dict:
  ready  READY! over the central wall bar (row 5, cells 8-13)
  dth    None or (frame 1-6, x, y): the death animation (REALTIME freeze quanta 10..5 after a death)
  pu     None or the popup: dict(x, y, t4, t3, col, msg)
  hi     None or the HUD high score (max(persistent, current)) when the high-score state is R / Z
  end    True on the end screen (score / high score / NEW HIGH SCORE after the banner)
  new    REQ-HSNEW = Y (end screen)
The renderers (ref_gs_screen, ref_gx_screen, ref_g4_screen) draw it; drop() gives the same screen without them (the
size-guard rule: an oversized decorated screen is first rebuilt plain, full, in the same layout)."""

READY_Y, READY_X, READY_TEXT = 5, 8, 'READY!'
POPUP_GHOST = 0xF5                    # PAL-POPUP (turquoise)
DEATH_GLYPHS = 'co.*'                 # unscaled frames 2-5
# scaled death frames 2-5 as pixel art (4 pixel rows per tile, '#' on), rendered like the other sprites
DEATH_PIX = {4: [['....', '####', '####', '.##.'], ['....', '....', '####', '.##.'], ['....', '....', '.##.', '....'],
                 ['....', '....', '....', '.##.']],
             3: [['...', '###', '###', '.#.'], ['...', '...', '###', '.#.'], ['...', '...', '.#.', '...'],
                 ['...', '...', '...', '.#.']]}
FRUIT_CELL = (10, 8)


def texts(pts):
    """(4-wide text, 3-wide text) of a popup."""
    if pts < 1000:
        return '%03d ' % pts, '%03d' % pts
    d = '%04d' % pts
    return d, d[0] + 'K' + (' ' if d[1] == '0' else d[1])


class Tracker:
    def __init__(self, hs=None):
        """hs: None (no high-score DD: REQ-HSST N) or (hsst R / Z / E, persistent score, start level). NEW HIGH SCORE
        (REQ-HSNEW Y) = a level-1 start whose final score is strictly higher (the save succeeds in the test decks)."""
        self.pu, self.eat, self.frt, self.hs = None, 0, 0, hs

    def frame(self, g, play='T', rtstat=None, rtfrz=0, rtq=0, dth=None, ends=False, tm=(150, 10, 4, 5)):
        """tm (REALTIME, RP.3): (quantum ms, freeze quanta, READY! quanta, popup quanta) of the selected SPEED."""
        per, frt, rdy, puq = tm
        if not getattr(g, 'arc', False) or not hasattr(g, 'evf'):
            return None                  # CLASSIC, or the superseded GP1-only model (no GP2 counters)
        now = rtq if play == 'R' else g.turns
        from ref_g4_screen import FRUITC
        if g.fruits != self.frt:
            self.frt = g.fruits
            self.start(FRUIT_CELL, g.bv, FRUITC, 'FRUIT', now)
        if g.eaten != self.eat:
            self.eat = g.eaten
            self.start((g.x, g.y), g.pts, POPUP_GHOST, 'GHOST', now)
        if self.pu is not None and ((play == 'R' and now > self.pu['t0'] + puq) or
                                    (play != 'R' and now != self.pu['t0'])):
            self.pu = None
        if 'D' in g.evf or 'C' in g.evf:
            self.pu = None
        hi = None
        if self.hs is not None and self.hs[0] in 'RZ':
            hi = max(self.hs[1], g.ascore)
        ready, d = False, None
        if play == 'R':
            ready = rtstat == 'WAIT' or (rtstat == 'FRZ ' and 0 < rtfrz <= rdy)
            if rtstat == 'FRZ ' and rtfrz > rdy and 'D' in g.evf:
                # the frame of the elapsed freeze time (the death quantum = 0 ms), 150 ms each, at most 6
                d = (min(6, (frt - rtfrz) * per // 150 + 1), dth[0], dth[1])
        else:
            ready = g.turns == 0 or 'D' in g.evf or 'C' in g.evf
        if g.lost or g.won:
            ready = False
        rp = {'ready': ready, 'dth': d, 'pu': self.pu, 'hi': hi, 'end': False, 'new': False}
        if ends:
            self.pu = None
            new = hi is not None and self.hs[2] == 1 and g.ascore > self.hs[1]
            rp.update(ready=False, dth=None, pu=None, end=True, new=new)
        return rp

    def start(self, cell, pts, col, kind, now):
        t4, t3 = texts(pts)
        self.pu = {'x': cell[0], 'y': cell[1], 't4': t4, 't3': t3, 'col': col, 'msg': '%s %04d' % (kind, pts),
                   't0': now}


def decorated(rp):
    return rp is not None and (rp['ready'] or rp['dth'] or rp['pu'] or rp['hi'] is not None or rp['end'])


def drop(rp):
    return None if rp is None else {'ready': False, 'dth': None, 'pu': None, 'hi': None, 'end': False, 'new': False}


def bells(frames, log, sound):
    """GP2.3 rule (test_gp2): one alarm per screen when a counter rose (death, extra life, level) or the first
    screen / the win; the last state rings on a restore-only write when there is no end screen."""
    if sound != 'Y':
        return list(frames), []
    stt = {'last': None, 'won': False}

    def ring(snap):
        b = stt['last'] is None or (snap[2] > stt['last'][2] or snap[3] > stt['last'][3]
                                    or snap[4] > stt['last'][4]) or (snap[1] and not stt['won'])
        stt['won'], stt['last'] = stt['won'] or snap[1], snap
        return b
    out, rung = [], []
    for k, (f, snap) in enumerate(zip(frames, log)):
        b = ring(snap)
        out.append(bytes([f[0] | 0x04]) + f[1:] if b else f)
        if b:
            rung.append(k)
    if ring(log.state()):
        out.append(bytes([0xC6, 0x28, 0x00, 0x00]))
        rung.append(len(frames))
    return out, rung
