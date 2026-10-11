#!/usr/bin/env python3
"""Independent reference renderer for the MVS-G2 TSC colour+highlight screens (written from docs/G1-RENDERER.md and docs/G2-HIGHLIGHT.md, not from the
COBOL). frames(case) replays a case with the game model and returns the expected 3270 data stream of every screen
sent (one per read), exactly as PACSCR must build it. Text is EBCDIC (cp037)."""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs6 import Game, parse_config  # noqa: E402

CODES = [0x40, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F,
         0x50, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E, 0x5F,
         0x60, 0x61, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F,
         0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F]
# palette approved for G1 (user, 2026-10-07)
BLUE, RED, PINK, GREEN, TURQ, YELLOW, WHITE = 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7
WALL, PELLET, PLAYER, GHOSTS, HUD, ERROR, HELP = BLUE, WHITE, YELLOW, (RED, PINK, TURQ), TURQ, RED, GREEN
# highlight (G2): extended-highlight SA X'41' values; reverse F2, blink F1, underscore F4
REVERSE, BLINK, UNDERSCORE = 0xF2, 0xF1, 0xF4
HELP_TEXT = 'PACMAN G2  U D L R + ENTER   Q QUIT   PA2 REDRAW'


def e(text):
    return list(text.encode('cp037'))


def sba(row, col):
    a = (row - 1) * 80 + col - 1
    return [0x11, CODES[a >> 6], CODES[a & 63]]


def sa(colour):
    return [0x28, 0x42, colour]


def sh(v):
    return [0x28, 0x41, v]


def status(g, cmd, res):
    if getattr(g, 'arc', False):          # MVS-GP1 ARCADE status line (docs/GP1-POWER.md 6): 7-digit score, PW, FR
        return (f'T{g.t:03d} {cmd} {res} S={g.ascore:07d} L={g.left:03d} V={g.lives} ST={g.state} '
                f'PW={g.power} FR={g.fr:03d}')
    return (f'T{g.t:03d} {cmd} {res} X={g.x:02d} Y={g.y:02d} S={g.score:04d} L={g.left:03d} '
            f'G={g.gh[0][0]:02d},{g.gh[0][1]:02d} V={g.lives} ST={g.state}')


def screen(g, cmd, res, msg, hi=False, glyphs=('P', 'G')):
    out = [0xC3] + sba(1, 1) + [0x1D, 0x60] + sba(1, 2) + sa(HUD) + e(status(g, cmd, res).ljust(61))
    if g.n > 1:
        text = 'G2=%02d,%02d' % tuple(g.gh[1][:2]) + (' G3=%02d,%02d' % tuple(g.gh[2][:2]) if g.n > 2 else '')
        out += sba(2, 2) + sa(HUD) + e(text)
    for j in range(1, 11):
        chars = list(''.join(g.grid[j - 1]))
        cols = [WALL if c == '#' else PELLET if c == '.' else 0 for c in chars]
        his = [0] * 20
        if g.y == j:
            chars[g.x - 1], cols[g.x - 1], his[g.x - 1] = glyphs[0], PLAYER, REVERSE if hi else 0
        for k, (gx, gy, _) in enumerate(g.gh):
            if gy == j:
                chars[gx - 1], cols[gx - 1], his[gx - 1] = glyphs[1], GHOSTS[k], REVERSE if hi else 0
        out += sba(3 + j, 31)
        cur = hcur = 0
        for c, col, h in zip(chars, cols, his):
            if col and col != cur:
                out += sa(col)
                cur = col
            if h != hcur:
                out += sh(h)
                hcur = h
            out += e(c)
        if hcur:
            out += sh(0)
    if msg is not None:
        out += sba(16, 2) + sa(ERROR) + (sh(BLINK) if hi else []) + e('INVALID COMMAND ' + msg) + (sh(0) if hi else [])
    out += sba(18, 2) + sa(HELP) + e('COMMAND ===>') + [0x1D, 0x40] + (sh(UNDERSCORE) if hi else []) + [0x13, 0x40] \
        + (sh(0) if hi else []) + [0x1D, 0x60]
    out += sba(23, 2) + sa(HELP) + e(HELP_TEXT) + [0x28, 0x00, 0x00]
    return bytes(out)


def frames(case, hi=False):
    """Screens of the interactive flow: config from the PARM, one screen before every read, none after the end."""
    ai, n, cards = parse_config((R / f'tests/cases/{case}.txt').read_text().splitlines())
    g = Game(ai, n)
    cmd, res, msg = ' ', 'START  ', None
    out = [screen(g, cmd, res, msg, hi)]
    for card in cards:
        stripped = card.lstrip()[:1] if card[:8].strip() else ''
        if stripped == '':                     # empty line: redraw, no turn
            out.append(screen(g, cmd, res, None, hi))
            continue
        u = stripped.upper()
        if u == 'Q':
            return out
        if u in ('U', 'D', 'L', 'R'):
            cmd, res = stripped, g.step(u)
            if g.lost or g.won:
                return out
            out.append(screen(g, cmd, res, None, hi))
        else:
            out.append(screen(g, cmd, res, stripped, hi))
    return out


if __name__ == '__main__':
    for f in frames(sys.argv[1], len(sys.argv) > 2):
        print(len(f), f.hex().upper())
