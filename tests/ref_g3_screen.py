#!/usr/bin/env python3
"""Independent reference renderer for the MVS-G3 TSC screens (written from docs/G3-PARTIAL.md, not from the COBOL).
frames(case, hi, anim, redraw) replays a case with the game model and returns every data stream PACSCR must build
(and PACPLAT print in the TSD dry run): full screens (as in G2, with the animated glyphs when anim), partial screens
(only the cells that differ from the image already on the terminal, plus the empty input field) and visual ticks
(glyph frame only). Cards: '+' = idle tick (TSD only), empty line = redraw request (full screen)."""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs6 import Game, parse_config  # noqa: E402
from ref_g2_screen import (e, sba, sa, sh, status, screen, WALL, PELLET, PLAYER, GHOSTS, HUD, ERROR, HELP,  # noqa: E402
                           HELP_TEXT, REVERSE, BLINK, UNDERSCORE)

GLYPHS = (('C', 'G'), ('O', 'W'))          # visual frame 0 / 1: (Pac-Man, ghost)


def cells(g, cmd, res, msg, hi, glyphs):
    """The 24 x 80 image of a screen: list of (char, colour, highlight); blanks are (' ', 0, 0)."""
    img = [(' ', 0, 0)] * 1920

    def put(row, col, text, colour, high=0):
        for k, c in enumerate(text):
            img[(row - 1) * 80 + col - 1 + k] = (c, colour, high) if c != ' ' else (' ', 0, 0)

    put(1, 2, status(g, cmd, res).ljust(61), HUD)
    if g.n > 1:
        put(2, 2, 'G2=%02d,%02d' % tuple(g.gh[1][:2]) + (' G3=%02d,%02d' % tuple(g.gh[2][:2]) if g.n > 2 else ''), HUD)
    for j in range(1, 11):
        chars = list(''.join(g.grid[j - 1]))
        cols = [WALL if c == '#' else PELLET if c == '.' else 0 for c in chars]
        his = [0] * 20
        if g.y == j:
            chars[g.x - 1], cols[g.x - 1], his[g.x - 1] = glyphs[0], PLAYER, REVERSE if hi else 0
        for k, (gx, gy, _) in enumerate(g.gh):
            if gy == j:
                chars[gx - 1], cols[gx - 1], his[gx - 1] = glyphs[1], GHOSTS[k], REVERSE if hi else 0
        for k in range(20):
            img[(3 + j - 1) * 80 + 30 + k] = (chars[k], cols[k], his[k]) if chars[k] != ' ' else (' ', 0, 0)
    if msg is not None:
        put(16, 2, 'INVALID COMMAND ' + msg, ERROR, BLINK if hi else 0)
    put(18, 2, 'COMMAND ===>', HELP)
    put(23, 2, HELP_TEXT, HELP)
    return img


def partial(cur, prev, kind, hi):
    """Changed cells in address order; a run ends at the end of its row; attributes carry over between runs."""
    out = [0xC3 if kind == 'P' else 0xC2]
    co = hh = 0
    inrun, changed = False, 0
    for i in range(1920):
        if cur[i] == prev[i]:
            inrun = False
            continue
        changed += 1
        row, col = i // 80 + 1, i % 80 + 1
        if not inrun or col == 1:
            out += sba(row, col)
        inrun = True
        ch, c, h = cur[i]
        if c != co:
            out += sa(c) if c else [0x28, 0x42, 0x00]
            co = c
        if h != hh:
            out += sh(h)
            hh = h
        out += e(ch)
    if kind == 'T' and not changed:
        return None
    if kind == 'P':
        out += sba(18, 15) + [0x13] + sa(HELP)
        if hi:
            out += sh(UNDERSCORE)
        elif hh:
            out += sh(0)
        out += e(' ')
        if hi:
            out += sh(0)
    return bytes(out + [0x28, 0x00, 0x00])


def frames(case, hi=False, anim=False, redraw='F'):
    ai, n, cards = parse_config((R / f'tests/cases/{case}.txt').read_text().splitlines())
    g = Game(ai, n)
    st = {'vis': 1, 'prev': None, 'last': None}
    out = []

    def glyphs():
        return GLYPHS[st['vis']] if anim else ('P', 'G')

    def prompt(cmd, res, msg, rdr):
        if anim:
            st['vis'] ^= 1
        gl = glyphs()
        if redraw == 'P':
            cur = cells(g, cmd, res, msg, hi, gl)
            if st['prev'] is None or rdr:
                out.append(screen(g, cmd, res, msg, hi, gl))
            else:
                out.append(partial(cur, st['prev'], 'P', hi))
            st['prev'] = cur
        else:
            out.append(screen(g, cmd, res, msg, hi, gl))
        st['last'] = (cmd, res, msg)

    def tick():
        if not (anim and redraw == 'P' and st['prev'] is not None):
            return
        st['vis'] ^= 1
        cmd, res, msg = st['last']
        cur = cells(g, cmd, res, msg, hi, glyphs())
        s = partial(cur, st['prev'], 'T', hi)
        if s is not None:
            out.append(s)
        st['prev'] = cur

    cmd, res, msg, rdr = ' ', 'START  ', None, False
    prompt(cmd, res, msg, rdr)
    for card in cards:
        stripped = card.lstrip()[:1] if card[:8].strip() else ''
        if stripped == '+':
            tick()
            continue
        if stripped == '':
            prompt(cmd, res, None, True)
            rdr = True
            continue
        rdr = False
        u = stripped.upper()
        if u == 'Q':
            return out
        if u in ('U', 'D', 'L', 'R'):
            cmd, res = stripped, g.step(u)
            if g.lost or g.won:
                return out
            prompt(cmd, res, None, False)
        else:
            prompt(cmd, res, stripped, False)
    return out


if __name__ == '__main__':
    for f in frames(sys.argv[1], True, True, 'P'):
        print(len(f), f.hex().upper())
