#!/usr/bin/env python3
"""MVS-GS geometry study (design only; nothing here is used by PACMAN). Renders the scaled 4x2 game screen on the five
live-proven canvases (docs/evidence/gs-e12-geometry.md) - 80x24 (current MVS-GS), 80x32, 80x43, 132x27, 120x27
(IBM-DYNAMIC) - as Unicode mock-ups and counts the exact compressed full-screen stream (the MVS-GS encoder of
tests/ref_gs_screen.py generalised to a W x H buffer: SBA on jumps, SA on change, GE, RA, blank skips, field orders).
The maze stays 4x2 (80 x 20) everywhere: 4x2 is the tile with square proportions on a 1:2 character cell, so a larger
canvas buys centring and HUD space, not a bigger maze (5x2 = 100 x 20 would stretch it 1.25x horizontally).
Usage: geometry_model.py [--state start|demo]"""
import argparse
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
import ref_gs_screen as gs  # noqa: E402
from ref_g2_screen import e, status, sa, sh, HUD, ERROR, HELP, PLAYER, GHOSTS, REVERSE, BLINK, UNDERSCORE, CODES  # noqa: E402
from ref_mvs6 import Game, parse_config  # noqa: E402

BULLETS = {gs.HLINE: '─', gs.VLINE: '│', gs.TL: '┌', gs.TR: '┐', gs.BL: '└', gs.BR: '┘', gs.UPPER: '▀',
           gs.LOWER: '▄', gs.EYE: '°', gs.BULLET: '•', 0x9B: '⊂', 0xAA: '∩'}


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = [(0x40, 0, 0, 0)] * (w * h)
        self.sf = {}                     # address -> attribute (field orders)
        self.field = None                # address of the 1-byte input field

    def put(self, row, col, text, colour, high=0, keep=False):
        for k, c in enumerate(text):
            self.img[(row - 1) * self.w + col - 1 + k] = ((e(c)[0], colour, high, 0) if c != ' ' or keep
                                                          else (0x40, 0, 0, 0))

    def ge(self, row, col, code, colour, high=0):
        self.img[(row - 1) * self.w + col - 1] = (code, colour, high, 1)

    def board(self, g, row, col, vis=0, face='R', anim=True):
        b = gs.image(g, ' ', 'START  ', None, 4, anim, vis, face)
        for j in range(20):
            for i in range(80):
                self.img[(row - 1 + j) * self.w + col - 1 + i] = b[j * 80 + i]

    def command(self, row, col):
        self.put(row, col, 'COMMAND ===>', HELP)
        a = (row - 1) * self.w + col - 1 + 12
        self.sf[a] = 0x40
        self.field = a + 1
        self.sf[a + 2] = 0x60

    def encode(self):
        """The MVS-GS full-screen encoding on a W x H buffer (12-bit addresses: W * H <= 4095)."""
        n = self.w * self.h
        assert n <= 4095

        def addr(a):
            return [CODES[(a % n) >> 6], CODES[(a % n) & 63]]
        out = [0xC3]
        pos, co, hi, a = None, 0, 0, 0
        while a < n:
            if a in self.sf:
                if pos != a:
                    out += [0x11] + addr(a)
                if hi:
                    out += sh(0)
                    hi = 0
                out += [0x1D, self.sf[a]]
                if self.sf[a] == 0x40:
                    out += sh(UNDERSCORE) + [0x13, 0x40] + sh(0)
                    a += 1
                a += 1
                pos = a
                continue
            cell = self.img[a]
            b = a + 1
            while b < n and b not in self.sf and self.img[b] == cell:
                b += 1
            k = b - a
            ch, c, h, ge = cell
            blank = ch == 0x40 and h == 0 and ge == 0
            if blank and k >= 4:
                a = b
                continue
            if pos != a:
                out += [0x11] + addr(a)
            if not blank and c != co:
                out += sa(c) if c else [0x28, 0x42, 0x00]
                co = c
            if h != hi:
                out += sh(h)
                hi = h
            size = 2 if ge else 1
            one = ([0x08] if ge else []) + [ch]
            out += [0x3C] + addr(b) + one if k * size > 3 + size else one * k
            pos = a = b
        if hi:
            out += sh(0)
        return bytes(out + [0x28, 0x00, 0x00])

    def unicode(self):
        rows = []
        for r in range(self.h):
            s = ''
            for q in range(r * self.w, (r + 1) * self.w):
                if q in self.sf:
                    s += ' '
                    continue
                ch, c, h, ge = self.img[q]
                if ge:
                    s += BULLETS.get(ch, '?')
                elif ch == 0x40 and h:
                    s += '█'
                else:
                    s += bytes([ch]).decode('cp037')
            rows.append(s.rstrip())
        return rows


def side_panels(cv, g, left, right, top):
    """HUD in the margins: left = score, pellets, lives (Pac-Man icons), turn, state; right = ghosts, AI, keys."""
    cv.put(top, left, 'SCORE', HUD)
    cv.put(top + 1, left, '%04d' % g.score, PLAYER)
    cv.put(top + 3, left, 'PELLETS', HUD)
    cv.put(top + 4, left, '%03d' % g.left, PLAYER)
    cv.put(top + 6, left, 'LIVES', HUD)
    for k in range(g.lives):
        cv.ge(top + 7, left + 2 * k, 0x9B, PLAYER)
    cv.put(top + 9, left, 'TURN', HUD)
    cv.put(top + 10, left, '%03d' % g.t, PLAYER)
    cv.put(top + 12, left, 'STATE', HUD)
    cv.put(top + 13, left, g.state.strip(), PLAYER)
    cv.put(top, right, 'GHOSTS  AI%d' % g.ai, HUD)
    for k, (gx, gy, _) in enumerate(g.gh):
        cv.ge(top + 2 + k, right, 0xAA, GHOSTS[k])
        cv.put(top + 2 + k, right + 2, '%02d,%02d' % (gx, gy), GHOSTS[k])
    cv.put(top + 12, right, 'U D L R', HELP)
    cv.put(top + 13, right, '+ ENTER', HELP)
    cv.put(top + 14, right, 'Q   QUIT', HELP)
    cv.put(top + 15, right, 'PA2 REDRAW', HELP)


def layout(name, g, msg='INVALID COMMAND X'):
    st = status(g, ' ', 'START  ')
    if name == '80x24':                                    # current MVS-GS layout B
        cv = Canvas(80, 24)
        cv.board(g, 1, 1)
        cv.sf[20 * 80] = 0x60
        cv.put(21, 2, st, HUD)
        if g.n > 1:
            cv.put(21, 64, 'G2=%02d,%02d G3=%02d,%02d' % (*g.gh[1][:2], *g.gh[2][:2]) if g.n > 2 else '', HUD)
        cv.put(22, 2, msg, ERROR, BLINK)
        cv.command(23, 2)
        cv.put(23, 20, gs.HELP_S, HELP)
        return cv
    if name == '80x32':                                    # board rows 6-25; HUD above, text below
        cv = Canvas(80, 32)
        cv.sf[0] = 0x60
        cv.put(2, 2, 'PAC-MAN', HUD)
        cv.put(2, 14, 'SCORE %04d   PELLETS %03d   TURN %03d' % (g.score, g.left, g.t), PLAYER)
        for k in range(g.lives):
            cv.ge(2, 60 + 2 * k, 0x9B, PLAYER)
        cv.put(3, 14, 'GHOSTS %d  AI%d  STATE %s' % (g.n, g.ai, g.state.strip()), HUD)
        cv.board(g, 6, 1)
        cv.put(27, 2, st, HUD)
        cv.put(28, 2, msg, ERROR, BLINK)
        cv.command(30, 2)
        cv.put(30, 20, gs.HELP_S, HELP)
        return cv
    if name == '80x43':                                    # board centred vertically: rows 12-31
        cv = Canvas(80, 43)
        cv.sf[0] = 0x60
        cv.put(3, 34, 'P A C - M A N', PLAYER)
        cv.put(6, 2, 'SCORE %04d' % g.score, PLAYER)
        cv.put(6, 24, 'PELLETS %03d' % g.left, PLAYER)
        cv.put(6, 46, 'TURN %03d' % g.t, PLAYER)
        cv.put(6, 62, 'LIVES', HUD)
        for k in range(g.lives):
            cv.ge(6, 68 + 2 * k, 0x9B, PLAYER)
        cv.put(8, 2, 'GHOSTS %d  AI%d  STATE %s' % (g.n, g.ai, g.state.strip()), HUD)
        cv.board(g, 12, 1)
        cv.put(34, 2, st, HUD)
        cv.put(36, 2, msg, ERROR, BLINK)
        cv.command(39, 2)
        cv.put(41, 2, gs.HELP_S, HELP)
        return cv
    w = {'120x27': 120, '132x27': 132}[name]
    cv = Canvas(w, 27)                                     # board centred: rows 4-23, columns (w-80)/2+1 ..
    c0 = (w - 80) // 2 + 1
    cv.sf[0] = 0x60
    cv.put(2, c0 + 33, 'P A C - M A N', PLAYER)
    cv.board(g, 4, c0)
    side_panels(cv, g, 3, c0 + 82, 5)
    cv.put(25, c0 + 9, st, HUD)
    cv.put(26, c0, msg, ERROR, BLINK)
    cv.command(27, c0)
    cv.put(27, c0 + 18, 'U D L R + ENTER   Q QUIT   PA2 REDRAW', HELP)
    return cv


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', default='demo', choices=['start', 'demo'])
    a = ap.parse_args()
    ai, n, cards = parse_config((R / 'tests/cases/MULTI.txt').read_text().splitlines())
    g = Game(ai, n)
    if a.state == 'demo':
        for u in 'RDRR':
            g.step(u)
    rows = []
    for name in ('80x24', '80x32', '80x43', '120x27', '132x27'):
        cv = layout(name, g)
        ds = cv.encode()
        board_share = 1600 / (cv.w * cv.h)
        rows.append((name, len(ds), board_share))
        print(f'=== {name}: full screen {len(ds)} bytes (limit 2048), maze 80x20 = {board_share:.0%} of the canvas')
        for k, l in enumerate(cv.unicode(), 1):
            print(f'{k:02d}|{l}')
    print('\n'.join(f'{n:7} {b:5} bytes  maze share {s:.0%}' for n, b, s in rows))
