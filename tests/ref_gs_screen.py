#!/usr/bin/env python3
"""Independent reference renderer for MVS-GS (scaled renderer, docs/GS-SCALED.md, D31), written from the design, not from
the COBOL. frames(case, anim, redraw, scale) returns every data stream PACSCR must build in the TSD dry run.
scale '4' / '3': the scaled screens (highlighting and GRAPHIC glyphs are prerequisites, so hi = on, profile G);
scale 'T': 4x2 with a 1000-byte limit -> the first screen overflows, so the whole run is the G4 GRAPHIC run;
scale 'N': the G4 renderer (ref_g4_screen) unchanged.
Image cells are (byte, colour, highlight, ge) for the 1920 buffer positions, as in ref_g4_screen.

Layout B (rows 1-20 board, 4x2 at column 1 / 3x2 at column 11; row 21 SF + status + ghosts at column 64; row 22 message
or end banner; row 23 command field + help at column 20). Walls: contour glyphs from the static map (outside = open).
Sprites: half-block pixel art, full cells = blank in reverse video, ghost eyes = CP310 X'A1' in reverse.
Full screen encoding: WCC C3; buffer order; SBA only on an address jump; SF X'60' at (21,1); at (23,14) the command field
(SF X'40', underscore on, IC, blank, underscore off, SF X'60'); colour SA only for visible cells (not plain blank) when it
changes; highlight SA whenever it changes (also before an SF: switched off); GE + code for CP310 cells; a run of equal
cells uses RA (3C addr [08] c) when L * size > 3 + size; runs of >= 4 plain blanks are skipped; highlight off at the end;
tail 28 00 00. Partial / tick: the G3 diff of the images (blanks written), field at (23,15). End: one full screen with the
banner (scaled only)."""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs6 import Game, parse_config  # noqa: E402
from ref_g2_screen import (e, sba, sa, sh, status, WALL, PELLET, PLAYER, GHOSTS, HUD, ERROR, HELP,  # noqa: E402
                           REVERSE, BLINK, UNDERSCORE, CODES)
import ref_g4_screen as g4  # noqa: E402

GE = 0x08
HLINE, VLINE, TL, TR, BL, BR = 0xA2, 0x85, 0xC5, 0xD5, 0xC4, 0xD4      # ─ │ ┌ ┐ └ ┘ (CP310, E9)
UPPER, LOWER, EYE, BULLET = 0x93, 0x94, 0xA1, 0xA3                    # ▀ ▄ ° •
HELP_S = 'PACMAN GS  U D L R + ENTER   Q QUIT   PA2 REDRAW'
# pixel art (2*2 pixel rows per tile, '#' on): Pac-Man right / left / shut, ghost frame A / B
PIX = {4: {'PR': ['.##.', '##..', '##..', '.##.'], 'PL': ['.##.', '..##', '..##', '.##.'],
           'PC': ['.##.', '####', '####', '.##.'], 'GA': ['.##.', '####', '####', '#.#.'],
           'GB': ['.##.', '####', '####', '.#.#']},
       3: {'PR': ['.#.', '##.', '##.', '.#.'], 'PL': ['.#.', '.##', '.##', '.#.'], 'PC': ['.#.', '###', '###', '.#.'],
           'GA': ['.#.', '###', '###', '#.#'], 'GB': ['.#.', '###', '###', '.#.']}}
EYES = {4: (1, 2), 3: (1,)}                 # top-row cells of a ghost that carry an eye (they are full cells)
BOARD_COL = {4: 1, 3: 11}
SF_ROW, MSG_ROW, CMD_ROW = 21, 22, 23
BANNERS = {'LOST': (' GAME OVER ', ERROR), 'WIN': (' YOU WIN ', PLAYER), 'QUIT': (' QUIT ', HELP),
           'EOF': (' END OF INPUT ', HELP)}


def is_wall(grid, x, y):
    return 0 <= y < 10 and 0 <= x < 20 and grid[y][x] == '#'


def contour(grid, x, y, w):
    """2 rows of w codes (0 = blank) for the wall cell (x, y), 0-based."""
    def corner(v, h, d, outer, inner):
        if not v and not h:
            return outer
        if not v:
            return HLINE
        if not h:
            return VLINE
        return 0 if d else inner
    W = lambda dx, dy: is_wall(grid, x + dx, y + dy)  # noqa: E731
    top = [corner(W(0, -1), W(-1, 0), W(-1, -1), TL, BR)] + [0 if W(0, -1) else HLINE] * (w - 2) \
        + [corner(W(0, -1), W(1, 0), W(1, -1), TR, BL)]
    bot = [corner(W(0, 1), W(-1, 0), W(-1, 1), BL, TR)] + [0 if W(0, 1) else HLINE] * (w - 2) \
        + [corner(W(0, 1), W(1, 0), W(1, 1), BR, TL)]
    return [top, bot]


def sprite(w, name, colour, ghost, fright=False):
    """fright (MVS-GP1): a frightened ghost's eye cells are not in reverse video."""
    px = PIX[w][name]
    rows = []
    for j in (0, 2):
        row = []
        for i in range(w):
            a, b = px[j][i] == '#', px[j + 1][i] == '#'
            if a and b:
                cell = (0x40, colour, REVERSE, 0)
                if ghost and j == 0 and i in EYES[w]:
                    cell = (EYE, colour, 0 if fright else REVERSE, 1)
            elif a:
                cell = (UPPER, colour, 0, 1)
            elif b:
                cell = (LOWER, colour, 0, 1)
            else:
                cell = (0x40, 0, 0, 0)
            row.append(cell)
        rows.append(row)
    return rows


def arc_tile(w, kind):
    """MVS-GP1 extra tiles: power pellet (pixels .##. in the middle rows: lower halves over upper halves, white,
    blinking) and eyes (the ghost's eye cells only, white, not reversed)."""
    tile = [[(0x40, 0, 0, 0)] * w for _ in range(2)]
    mid = (1, 2) if w == 4 else (1,)
    if kind == '%':                 # MVS-GP2 fruit: 4 wide .##. / #### / .##. / ...., 3 wide .#. / ### / .#. / ...
        top = 'BFFB' if w == 4 else 'BFB'
        bot = ' TT ' if w == 4 else ' T '
        for r, codes in enumerate((top, bot)):
            for i, ch in enumerate(codes):
                if ch == 'F':
                    tile[r][i] = (0x40, g4.FRUITC, REVERSE, 0)
                elif ch == 'B':
                    tile[r][i] = (LOWER, g4.FRUITC, 0, 1)
                elif ch == 'T':
                    tile[r][i] = (UPPER, g4.FRUITC, 0, 1)
    elif kind == 'o':
        for i in mid:
            tile[0][i] = (LOWER, g4.POWER, BLINK, 1)
            tile[1][i] = (UPPER, g4.POWER, BLINK, 1)
    else:
        for i in EYES[w]:
            tile[0][i] = (EYE, g4.EYESC, 0, 1)
    return tile


def image(g, cmd, res, msg, w, anim, vis, face, banner=None):
    img = [(0x40, 0, 0, 0)] * 1920

    def put(row, col, text, colour, high=0, keep_blanks=False):
        for k, c in enumerate(text):
            img[(row - 1) * 80 + col - 1 + k] = ((e(c)[0], colour, high, 0) if c != ' ' or keep_blanks
                                                else (0x40, 0, 0, 0))

    put(21, 2, status(g, cmd, res).ljust(61), HUD)
    if g.n > 1:
        put(21, 64, 'G2=%02d,%02d' % tuple(g.gh[1][:2]) + (' G3=%02d,%02d' % tuple(g.gh[2][:2]) if g.n > 2 else ''),
            HUD)
    second = anim and vis == 1
    pac = sprite(w, 'PC' if second else 'PL' if face == 'L' else 'PR', PLAYER, False)
    col0 = BOARD_COL[w]
    for y in range(10):
        for x in range(20):
            c = g.grid[y][x]
            tile = None
            arc = getattr(g, 'arc', False)
            for k, (gx, gy, _) in enumerate(g.gh):
                if (gx - 1, gy - 1) == (x, y) and arc and g.mode[k] == 'F':
                    tile = sprite(w, 'GB' if second else 'GA', g4.fright_colour(g), True, True)
                elif (gx - 1, gy - 1) == (x, y) and not (arc and g.mode[k] == 'E'):
                    tile = sprite(w, 'GB' if second else 'GA', GHOSTS[k], True)
            if tile is None and (g.x - 1, g.y - 1) == (x, y):
                tile = pac
            if tile is None and arc and any(g.mode[k] == 'E' and (gx - 1, gy - 1) == (x, y)
                                            for k, (gx, gy, _) in enumerate(g.gh)):
                tile = arc_tile(w, 'E')
            if tile is None and g4.fruit_at(g) == (x + 1, y + 1):
                tile = arc_tile(w, '%')
            if tile is None and c == 'o':
                tile = arc_tile(w, 'o')
            if tile is None and c == '#':
                tile = [[(code, WALL, 0, 1) if code else (0x40, 0, 0, 0) for code in row]
                        for row in contour(g.grid, x, y, w)]
            if tile is None:
                tile = [[(0x40, 0, 0, 0)] * w for _ in range(2)]
                if c == '.':
                    tile[0][1] = (BULLET, PELLET, 0, 1)
            for j in range(2):
                for i in range(w):
                    img[(2 * y + j) * 80 + col0 - 1 + w * x + i] = tile[j][i]
    if msg is not None:
        put(MSG_ROW, 2, 'INVALID COMMAND ' + msg, ERROR, BLINK)
    if banner is not None:
        text, colour = BANNERS[banner]
        put(MSG_ROW, 2, text, colour, REVERSE, keep_blanks=True)
    put(CMD_ROW, 2, 'COMMAND ===>', HELP)
    put(CMD_ROW, 20, HELP_S, HELP)
    return img


def addr(a):
    return [CODES[(a % 1920) >> 6], CODES[(a % 1920) & 63]]


def full(img):
    out = [0xC3]
    sp1, spf = (SF_ROW - 1) * 80, (CMD_ROW - 1) * 80 + 13
    pos, co, hi, a = None, 0, 0, 0
    while a < 1920:
        if a in (sp1, spf):
            if pos != a:
                out += [0x11] + addr(a)
            if hi:
                out += sh(0)
                hi = 0
            if a == sp1:
                out += [0x1D, 0x60]
                a += 1
            else:
                out += [0x1D, 0x40] + sh(UNDERSCORE) + [0x13, 0x40] + sh(0) + [0x1D, 0x60]
                a += 3
            pos = a
            continue
        cell = img[a]
        b = a + 1
        while b < 1920 and b not in (sp1, spf) and img[b] == cell:
            b += 1
        n = b - a
        ch, c, h, ge = cell
        blank = ch == 0x40 and h == 0 and ge == 0
        if blank and n >= 4:
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
        one = ([GE] if ge else []) + [ch]
        out += [0x3C] + addr(b) + one if n * size > 3 + size else one * n
        pos = a = b
    if hi:
        out += sh(0)
    return bytes(out + [0x28, 0x00, 0x00])


def partial(cur, prev, kind):
    """The G3/G4 diff (ref_g4_screen.partial) with the command field of layout B."""
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
        b, c, h, ge = cur[i]
        if c != co:
            out += sa(c) if c else [0x28, 0x42, 0x00]
            co = c
        if h != hh:
            out += sh(h)
            hh = h
        out += [GE, b] if ge else [b]
    if kind == 'T' and not changed:
        return None
    if kind == 'P':
        out += sba(CMD_ROW, 15) + [0x13] + sa(HELP) + sh(UNDERSCORE) + e(' ') + sh(0)
    return bytes(out + [0x28, 0x00, 0x00])


def frames(case, anim=True, redraw='P', scale='4', faces=None):
    if scale == 'T':
        return g4.frames(case, True, anim, redraw, 'G', faces)
    if scale == 'N':
        return g4.frames(case, True, anim, redraw, 'G', faces)
    w = int(scale)
    ai, n, cards = parse_config((R / f'tests/cases/{case}.txt').read_text().splitlines())
    g = Game(ai, n)
    st = {'vis': 1, 'prev': None, 'last': None, 'face': 'R'}
    out = []

    def img(cmd, res, msg, banner=None):
        return image(g, cmd, res, msg, w, anim, st['vis'], st['face'], banner)

    def prompt(cmd, res, msg, rdr):
        if anim:
            st['vis'] ^= 1
        cur = img(cmd, res, msg)
        if faces is not None:
            faces.append(st['face'])
        if redraw == 'P' and st['prev'] is not None and not rdr:
            out.append(partial(cur, st['prev'], 'P'))
        else:
            out.append(full(cur))
        if redraw == 'P':
            st['prev'] = cur
        st['last'] = (cmd, res, msg)

    def tick():
        if not (anim and redraw == 'P' and st['prev'] is not None):
            return
        st['vis'] ^= 1
        cmd, res, msg = st['last']
        cur = img(cmd, res, msg)
        s = partial(cur, st['prev'], 'T')
        if s is not None:
            out.append(s)
        st['prev'] = cur

    def end(kind, cmd, res):
        if kind == 'QUIT':
            g.state = 'QUIT   '
        out.append(full(img(cmd, res, None, kind)))
        return out

    cmd, res, msg = ' ', 'START  ', None
    prompt(cmd, res, msg, False)
    for card in cards:
        stripped = card.lstrip()[:1] if card[:8].strip() else ''
        if stripped == '+':
            tick()
            continue
        if stripped == '':
            prompt(cmd, res, None, True)
            continue
        u = stripped.upper()
        if u == 'Q':
            return end('QUIT', cmd, res)
        if u in ('U', 'D', 'L', 'R'):
            cmd, res = stripped, g.step(u)
            if u in 'LR' and res != 'BLOCKED':
                st['face'] = u
            if g.lost or g.won:
                return end('LOST' if g.lost else 'WIN', cmd, res)
            prompt(cmd, res, None, False)
        else:
            prompt(cmd, res, stripped, False)
    return end('EOF', cmd, res)


if __name__ == '__main__':
    case = sys.argv[1] if len(sys.argv) > 1 else 'MOVES'
    fs = frames(case, True, 'P', sys.argv[2] if len(sys.argv) > 2 else '4')
    print([len(f) for f in fs])
