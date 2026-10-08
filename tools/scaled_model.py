#!/usr/bin/env python3
"""Scaled-renderer study model (feasibility/design only; nothing here is used by PACMAN, core untouched).
1 logical cell = SX x SY terminal cells. Candidate scales: 2x2 (requested), 3x2, 4x2.

Walls are contours: each wall cell is split into SX x SY sub-cells and every sub-cell gets a CP310 box glyph decided
ONLY by the static map (the wall cell and its 8 neighbours). Contours therefore never change during a game; corridor
cells carry pellet / sprite / blank. Rule for a corner sub-cell, e.g. top-left, from N, W, NW ('open' = not a wall;
outside the map counts as open, giving the arcade double outer border):
    N open,  W open            -> outer corner   ┌
    N open,  W wall            -> ─  (edge along the top)
    N wall,  W open            -> │  (edge down the left)
    N wall,  W wall, NW open   -> inner corner   ┘
    N wall,  W wall, NW wall   -> blank (inside a wall block)
The other three corners are mirror images (TR: N,E,NE ┐ └; BL: S,W,SW └ ┐; BR: S,E,SE ┘ ┌). Non-corner sub-cells on the
top/bottom row (SX > 2) get ─ when N/S is open; with SY = 2 there are no middle rows. A one-cell-thick wall therefore
becomes two parallel lines closed by corners (a double-sided arcade wall).

Sprites are pixel art on half blocks: each terminal cell = 2 vertical pixels (▀ top, ▄ bottom, full = blank in reverse
video, which needs highlighting); a tile has SX x 2*SY pixels.

The encoder produces the exact 3270 bytes a renderer would hand to PACFSIO (WCC first; PACFSIO SEND adds the 7-byte clear
prefix itself, D25): SBA only when the address jumps, SA colour/reverse only on change, GE X'08' before CP310 codes, RA
(X'3C' addr [08] char) for runs where it is shorter, SBA skips over runs of >= 4 blanks (SEND nulls the buffer first).
Usage: scaled_model.py   prints the three layouts (Unicode), exact sizes, partial-update costs and the 2048-byte check."""
from pathlib import Path

R = Path(__file__).resolve().parent.parent
MAP = [l.rstrip('\n') for l in (R / 'maps/LEVEL1.txt').read_text().splitlines() if l.strip()]
H, W = len(MAP), len(MAP[0])
# CP310 code points, all seen live in E9 (docs/evidence/g4-probe-analysis.md)
CP310 = {'─': 0xA2, '│': 0x85, '┌': 0xC5, '┐': 0xD5, '└': 0xC4, '┘': 0xD4, '•': 0xA3,
         '▌': 0x91, '▐': 0x92, '▀': 0x93, '▄': 0x94, '■': 0x95, '°': 0xA1, '○': 0x9D}
BLUE, RED, PINK, GREEN, TURQ, YELLOW, WHITE = 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7
FULL = '█'                       # blank in reverse video
CODES = [0x40, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F,
         0x50, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E, 0x5F,
         0x60, 0x61, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F,
         0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F]
SEND_MAX = 2048                  # PACFSIO BUF X(2048) / SENDBUF CL2060 incl. the 7-byte prefix: unchanged


def wall(x, y):
    return 0 <= x < W and 0 <= y < H and MAP[y][x] == '#'


def contour(x, y, sx, sy):
    def corner(v, h, d, outer, inner):
        if not v and not h:
            return outer
        if not v:
            return '─'
        if not h:
            return '│'
        return inner if not d else ' '
    n, s, w, e = wall(x, y - 1), wall(x, y + 1), wall(x - 1, y), wall(x + 1, y)
    nw, ne, sw, se = wall(x - 1, y - 1), wall(x + 1, y - 1), wall(x - 1, y + 1), wall(x + 1, y + 1)
    rows = []
    for j in range(sy):
        top, bot = j == 0, j == sy - 1
        row = []
        for i in range(sx):
            left, right = i == 0, i == sx - 1
            if top and left:
                g = corner(n, w, nw, '┌', '┘')
            elif top and right:
                g = corner(n, e, ne, '┐', '└')
            elif bot and left:
                g = corner(s, w, sw, '└', '┐')
            elif bot and right:
                g = corner(s, e, se, '┘', '┌')
            elif top:
                g = '─' if not n else ' '
            elif bot:
                g = '─' if not s else ' '
            else:
                g = '│' if (left and not w) or (right and not e) else ' '
            row.append(g)
        rows.append(row)
    return rows


def px_cells(px):
    out = []
    for j in range(0, len(px), 2):
        out.append([{('#', '#'): FULL, ('#', '.'): '▀', ('.', '#'): '▄'}.get((a, b), ' ')
                    for a, b in zip(px[j], px[j + 1])])
    return out


SPRITES = {
    (2, 2): {'P_R': ['##', '#.', '#.', '##'], 'P_L': ['##', '.#', '.#', '##'], 'P_C': ['##', '##', '##', '##'],
             'G_A': ['##', '##', '##', '#.'], 'G_B': ['##', '##', '##', '.#'], 'POWER': ['..', '##', '##', '..']},
    (3, 2): {'P_R': ['.#.', '##.', '##.', '.#.'], 'P_L': ['.#.', '.##', '.##', '.#.'],
             'P_C': ['.#.', '###', '###', '.#.'],
             'G_A': ['.#.', '###', '###', '#.#'], 'G_B': ['.#.', '###', '###', '.#.'],
             'POWER': ['...', '.#.', '.#.', '...']},
    (4, 2): {'P_R': ['.##.', '##..', '##..', '.##.'], 'P_L': ['.##.', '..##', '..##', '.##.'],
             'P_C': ['.##.', '####', '####', '.##.'],
             'G_A': ['.##.', '####', '####', '#.#.'], 'G_B': ['.##.', '####', '####', '.#.#'],
             'POWER': ['....', '.##.', '.##.', '....']},
}
EYES = {(2, 2): [0, 1], (3, 2): [0, 2], (4, 2): [1, 2]}       # top-row cells that show ° in reverse (eyes)
PELLET_AT = {(2, 2): (0, 0), (3, 2): (0, 1), (4, 2): (0, 1)}
GHOST_COL = {'ghost1': RED, 'ghost2': PINK, 'ghost3': TURQ}


def tile(kind, sx, sy, frame='A', face='R'):
    """sy rows of (glyph, colour, reverse) for a corridor cell content."""
    if kind == 'pellet':
        r, c = PELLET_AT[(sx, sy)]
        return [[('•', WHITE, 0) if (j, i) == (r, c) else (' ', 0, 0) for i in range(sx)] for j in range(sy)]
    if kind == 'empty':
        return [[(' ', 0, 0)] * sx for _ in range(sy)]
    sp = SPRITES[(sx, sy)]
    if kind == 'pac':
        cells = px_cells(sp['P_C'] if frame == 'B' else sp['P_' + face])
        return [[(g, YELLOW, int(g == FULL)) if g != ' ' else (' ', 0, 0) for g in row] for row in cells]
    if kind in GHOST_COL:
        col = GHOST_COL[kind]
        cells = px_cells(sp['G_' + frame])
        out = [[(g, col, int(g == FULL)) if g != ' ' else (' ', 0, 0) for g in row] for row in cells]
        for i in EYES[(sx, sy)]:
            if out[0][i][0] == FULL:
                out[0][i] = ('°', col, 1)
        return out
    if kind == 'power':
        cells = px_cells(sp['POWER'])
        return [[(g, WHITE, int(g == FULL)) if g != ' ' else (' ', 0, 0) for g in row] for row in cells]
    raise ValueError(kind)


def board(sx, sy, sprites, frame='A', face='R'):
    out = [[None] * (W * sx) for _ in range(H * sy)]
    for y in range(H):
        for x in range(W):
            if MAP[y][x] == '#':
                t = [[(g, BLUE, 0) if g != ' ' else (' ', 0, 0) for g in row] for row in contour(x, y, sx, sy)]
            else:
                t = tile(sprites.get((x, y), 'pellet'), sx, sy, frame, face)
            for j in range(sy):
                for i in range(sx):
                    out[y * sy + j][x * sx + i] = t[j][i]
    return out


# ---------------------------------------------------------------- screens
class Screen:
    """24 x 80 buffer of None | ('c', glyph, colour, reverse) | ('sf', attr); ic = cursor address."""
    def __init__(self):
        self.cells = [None] * 1920
        self.ic = None

    def put(self, row, col, text, colour=GREEN, rev=0):
        for k, ch in enumerate(text):
            self.cells[(row - 1) * 80 + col - 1 + k] = ('c', ch, colour if ch != ' ' or rev else 0, rev)

    def sf(self, row, col, attr):
        self.cells[(row - 1) * 80 + col - 1] = ('sf', attr)

    def place(self, row, col, b):
        for j, r in enumerate(b):
            for i, (g, c, v) in enumerate(r):
                self.cells[(row - 1 + j) * 80 + col - 1 + i] = ('c', g, c, v)

    def input_field(self, row, col, label='COMMAND ===>'):
        """Label, then SF unprotected, the 1-byte field (cursor), SF protected - as G1 (docs/G1-RENDERER.md)."""
        self.put(row, col, label, GREEN)
        p = col + len(label)
        self.sf(row, p, 0x40)
        self.cells[(row - 1) * 80 + p] = ('c', ' ', 0, 0)
        self.ic = (row - 1) * 80 + p
        self.sf(row, p + 2, 0x60)

    def unicode(self):
        rows = []
        for r in range(24):
            s = ''
            for c in self.cells[r * 80:(r + 1) * 80]:
                s += ' ' if c is None or c[0] == 'sf' else c[1]
            rows.append(s.rstrip())
        return rows


def sba(a):
    return [0x11, CODES[a >> 6], CODES[a & 63]]


def char_bytes(g):
    if g == FULL:
        return [0x40]
    if g in CP310:
        return [0x08, CP310[g]]
    return list(g.encode('cp037'))


def encode(scr, wcc=0xC3, cells=None, full=True):
    """Exact 3270 stream. full=True: whole screen after a null-clear (blank runs >= 4 skipped);
    full=False: partial - only the addresses in `cells` (a set) are written, blanks written explicitly."""
    out = [wcc]
    pos, colour, rev, i = None, 0, 0, 0
    addrs = range(1920) if full else sorted(cells)
    addrs = list(addrs)
    k = 0
    while k < len(addrs):
        a = addrs[k]
        c = scr.cells[a]
        if c is None and full:
            k += 1
            continue
        if c is not None and c[0] == 'sf':
            if pos != a:
                out += sba(a)
            if rev:
                out += [0x28, 0x41, 0x00]
                rev = 0
            out += [0x1D, c[1]]
            pos = a + 1
            k += 1
            continue
        g, col, v = ('c', ' ', 0, 0)[1:] if c is None else c[1:]
        # run of identical cells at consecutive addresses
        m = k + 1
        while m < len(addrs) and addrs[m] == addrs[m - 1] + 1 and scr.cells[addrs[m]] == c:
            m += 1
        L = m - k
        blank = g == ' ' and not v
        if full and blank and L >= 4:
            k = m
            continue
        if pos != a:
            out += sba(a)
        if not blank and col != colour:
            out += [0x28, 0x42, col]
            colour = col
        if v != rev:
            out += [0x28, 0x41, 0xF2 if v else 0x00]
            rev = v
        cb = char_bytes(g)
        end = a + L
        if L * len(cb) > 3 + len(cb):
            out += [0x3C] + sba(end % 1920)[1:] + cb
        else:
            out += cb * L
        pos = end
        k = m
    if rev:
        out += [0x28, 0x41, 0x00]
    if scr.ic is not None:
        out += sba(scr.ic) + [0x13]                  # cursor back into the input field (full and partial)
    return bytes(out + [0x28, 0x00, 0x00])


# ---------------------------------------------------------------- candidate layouts
START = {(1, 1): 'pac', (18, 8): 'ghost1'}          # oracle T000: X=02 Y=02, G=19,09 (1-based)
DEMO = {(1, 1): 'pac', (18, 8): 'ghost1', (9, 3): 'ghost2', (10, 7): 'ghost3', (4, 1): 'empty'}
LAYOUTS = {
    'A': {'scale': (2, 2), 'board_at': (3, 2), 'desc': '2x2: board 40x20 rows 3-22 cols 2-41, side panel cols 45-80'},
    'B': {'scale': (4, 2), 'board_at': (1, 1), 'desc': '4x2: board 80x20 rows 1-20 (full width), text rows 21-24'},
    'C': {'scale': (3, 2), 'board_at': (2, 1), 'desc': '3x2: board 60x20 rows 2-21 cols 1-60, side panel cols 62-80'},
}
STATUS = 'T000 START X=02 Y=02 S=0000 L=100 G=19,09 V=3 ST=READY'    # the G0 status text (61 max)


def layout(name, sprites=DEMO, frame='A', face='R', msg='INVALID COMMAND X', label=None):
    lay = LAYOUTS[name]
    sx, sy = lay['scale']
    scr = Screen()
    r0, c0 = lay['board_at']
    scr.place(r0, c0, board(sx, sy, sprites, frame, face))
    if name == 'A':
        p = 45
        scr.sf(1, 1, 0x60)
        scr.put(1, 2, label or 'PAC-MAN  MVS 3.8J  TK4-', TURQ)
        for r, t in ((3, 'TURN    000   START'), (4, 'SCORE   0000'), (5, 'PELLETS 100'), (6, 'LIVES   3'),
                     (7, 'GHOSTS  3   AI3'), (9, 'STATE   READY')):
            scr.put(r, p, t, TURQ)
        scr.input_field(12, p)
        if msg:
            scr.put(14, p, msg, RED)
        scr.put(20, p, 'U D L R + ENTER', GREEN)
        scr.put(21, p, 'Q QUIT   PA2 REDRAW', GREEN)
    elif name == 'C':
        p = 62
        scr.sf(1, 1, 0x60)
        scr.put(1, 2, label or 'PAC-MAN  MVS 3.8J  TK4-', TURQ)
        for r, t in ((3, 'TURN  000 START'), (4, 'SCORE 0000'), (5, 'PELLETS 100'), (6, 'LIVES 3'),
                     (7, 'GHOSTS 3 AI3'), (9, 'STATE READY')):
            scr.put(r, p, t, TURQ)
        scr.input_field(12, p, 'CMD ===>')
        if msg:
            scr.put(14, p, msg[:18], RED)
        scr.put(19, p, 'U D L R + ENTER', GREEN)
        scr.put(20, p, 'Q QUIT', GREEN)
        scr.put(21, p, 'PA2 REDRAW', GREEN)
    else:
        scr.sf(21, 1, 0x60)
        scr.put(21, 2, STATUS, TURQ)
        if msg:
            scr.put(22, 2, msg, RED)
        scr.input_field(23, 2)
        scr.put(23, 20, 'U D L R + ENTER   Q QUIT   PA2 REDRAW', GREEN)
        if label:
            scr.put(24, 2, label, TURQ)
    return scr


def logical_cells(name, x, y):
    """Terminal addresses covered by logical cell (x, y): the ONLY cells to invalidate when it changes."""
    sx, sy = LAYOUTS[name]['scale']
    r0, c0 = LAYOUTS[name]['board_at']
    return {(r0 - 1 + y * sy + j) * 80 + c0 - 1 + x * sx + i for j in range(sy) for i in range(sx)}


def partial(name, before, after, cells_xy, frame_b='A', frame_a='A', face='R'):
    a = layout(name, after, frame_a, face, msg=None)
    dirty = set()
    for x, y in cells_xy:
        dirty |= logical_cells(name, x, y)
    return encode(a, 0xC2, dirty, full=False)


def report():
    res = {}
    for name in LAYOUTS:
        sx, sy = LAYOUTS[name]['scale']
        full = encode(layout(name))
        start = encode(layout(name, START, msg=None))
        move = partial(name, START, {(2, 1): 'pac', (18, 8): 'ghost1'}, [(1, 1), (2, 1)])
        gmove = partial(name, START, {(1, 1): 'pac', (17, 8): 'ghost1'}, [(18, 8), (17, 8)])
        tick_p = partial(name, START, START, [(1, 1)], frame_a='B')
        tick_g = partial(name, START, START, [(18, 8)], frame_a='B')
        res[name] = dict(scale=f'{sx}x{sy}', board_cells=sx * sy * W * H, share=round(sx * sy * W * H / 1920, 3),
                         full_demo=len(full), full_start=len(start), fits=len(full) <= SEND_MAX,
                         player_move=len(move), ghost_move=len(gmove), tick_pac=len(tick_p), tick_ghost=len(tick_g))
    return res


if __name__ == '__main__':
    for name in LAYOUTS:
        scr = layout(name)
        print(f'=== Layout {name}: {LAYOUTS[name]["desc"]}: {len(encode(scr))} bytes (3 ghosts + message)')
        for k, l in enumerate(scr.unicode(), 1):
            print(f'{k:02d}|{l}')
    print()
    print('layout scale board share  full(3G+msg) full(start)  fits2048  move(P) move(G)  tick(P) tick(G)')
    for n, r in report().items():
        print(f'{n:6} {r["scale"]:5} {r["board_cells"]:5} {r["share"]:5}  {r["full_demo"]:12} {r["full_start"]:11}  '
              f'{str(r["fits"]):8}  {r["player_move"]:7} {r["ghost_move"]:7}  {r["tick_pac"]:7} {r["tick_ghost"]:7}')
