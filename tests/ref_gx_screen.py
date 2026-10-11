#!/usr/bin/env python3
"""Independent reference renderer for the MVS-GS geometry integration (docs/GS-GEOMETRY.md, D32), written from the
design, not from the COBOL. frames(case, hi, anim, redraw, glyphs, scale, canvas) returns every TSD data stream.
Buffer: canvas W x H (TSD simulated: W 120x27, X 132x27, T 80x43, M 80x32, U 100x25, L 160x30; anything else 80x24).
Above 4095 cells only the first floor(4094/W) rows are used. Families: W (4x2, W >= 120 and rows >= 27: wide, side HUD),
T (4x2, rows >= 32: tall), B (scaled: the 80 x 24 GS screens centred), G (not scaled: the G4 screens centred).
Size guard (2048; scale T: 1000): W/T -> B -> G for the rest of the game.
- G: the ref_g4_screen streams with every buffer address relocated to the origin (every row of those streams starts
  with an SBA, so relocation is exact). No end screen.
- B: the ref_gs_screen images placed at the origin; full / partial encoded on the W x H buffer; end screen.
- W / T: images built here; same encoders; end screen."""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs6 import Game, parse_config  # noqa: E402
from ref_g2_screen import (e, sa, sh, status, HUD, ERROR, HELP, PLAYER, GHOSTS, REVERSE, BLINK, UNDERSCORE,  # noqa: E402
                           CODES)
import ref_g4_screen as g4  # noqa: E402
import ref_gs_screen as gs  # noqa: E402
from ref_snap import Rec  # noqa: E402

CANVASES = {'W': (120, 27), 'X': (132, 27), 'T': (80, 43), 'M': (80, 32), 'U': (100, 25), 'L': (160, 30)}
LIFE, GHOST_ICON = 0x9B, 0xAA
BLANK = (0x40, 0, 0, 0)


class Geo:
    def __init__(self, canvas, scaled, sc_w):
        self.w, self.h = CANVASES.get(canvas, (80, 24))
        self.cells = self.w * self.h
        self.rows = self.h if self.cells <= 4095 else 4094 // self.w
        self.n = self.w * self.rows
        self.sc_w = sc_w
        if scaled and sc_w == 4 and self.w > 119 and self.rows > 26:
            self.fam = 'W'
        elif scaled and sc_w == 4 and self.rows > 31:
            self.fam = 'T'
        else:
            self.fam = 'B' if scaled else 'G'
        self.org = ((self.rows - 24) // 2 + 1, (self.w - 80) // 2 + 1)
        self.c0 = (self.w - 80) // 2 + 1
        self.b0 = (self.rows - 27) // 2 + 4 if self.fam == 'W' else (self.rows - 20) // 2 + 1

    def down(self):
        self.fam = 'B' if self.fam in 'WT' else 'G'

    def a(self, row, col):                         # 0-based buffer address of an absolute (row, col)
        return (row - 1) * self.w + col - 1

    def sf_field(self):
        """(protected SF address, unprotected SF address of the command field), 0-based."""
        if self.fam in 'BG':
            r0, c0 = self.org
            return self.a(r0 + 20, c0), self.a(r0 + 22, c0 + 13)
        if self.fam == 'W':
            return 0, self.a(self.b0 + 22, self.c0 + 12)
        return 0, self.a(self.b0 + 24, self.c0 + 13)


def blank_image(geo):
    return [BLANK] * geo.n


def put(img, geo, row, col, text, colour, high=0, keep=False):
    for k, c in enumerate(text):
        img[geo.a(row, col + k)] = (e(c)[0], colour, high, 0) if c != ' ' or keep else BLANK


def image(geo, g, cmd, res, msg, anim, vis, face, banner=None):
    if geo.fam == 'B':
        base = gs.image(g, cmd, res, msg, geo.sc_w, anim, vis, face, banner)
        img = blank_image(geo)
        r0, c0 = geo.org
        for q in range(1920):
            img[geo.a(r0 + q // 80, c0 + q % 80)] = base[q]
        return img
    base = gs.image(g, cmd, res, None, 4, anim, vis, face)          # the maze tiles (rows 1-20 of layout B)
    img = blank_image(geo)
    b0, c0 = geo.b0, geo.c0
    for j in range(20):
        for i in range(80):
            img[geo.a(b0 + j, c0 + i)] = base[j * 80 + i]
    if geo.fam == 'W':
        put(img, geo, b0 - 2, c0 + 33, 'P A C - M A N', PLAYER)
        left = c0 - 18
        lines = [('SCORE', '%04d' % g.score), ('PELLETS', '%03d' % g.left), ('TURN', '%03d' % g.t),
                 ('LAST', f'{cmd} {res}'), ('STATE', g.state), ('LIVES', '')]
        for k, (label, value) in enumerate(lines):
            put(img, geo, b0 + 1 + 2 * k, left, label.ljust(8) + value.ljust(9), HUD)
        for k in range(g.lives):
            img[geo.a(b0 + 11, c0 - 10 + 2 * k)] = (LIFE, PLAYER, 0, 1)
        right = c0 + 82
        put(img, geo, b0 + 1, right, 'GHOSTS  AI%d' % g.ai, HUD)
        for k, (gx, gy, _) in enumerate(g.gh):
            img[geo.a(b0 + 3 + k, right)] = (GHOST_ICON, GHOSTS[k], 0, 1)
            put(img, geo, b0 + 3 + k, right + 2, '%02d,%02d' % (gx, gy), GHOSTS[k])
        put(img, geo, b0 + 13, right, 'U D L R ENTER', HELP)
        put(img, geo, b0 + 14, right, 'Q QUIT  PA2', HELP)
        mrow, mcol, crow, ccol = b0 + 21, c0, b0 + 22, c0
    else:
        put(img, geo, b0 - 4, c0 + 33, 'P A C - M A N', PLAYER)
        put(img, geo, b0 - 2, c0 + 1, 'SCORE %04d   PELLETS %03d   TURN %03d   LIVES ' % (g.score, g.left, g.t), HUD)
        for k in range(g.lives):
            img[geo.a(b0 - 2, c0 + 45 + 2 * k)] = (LIFE, PLAYER, 0, 1)
        put(img, geo, b0 + 21, c0 + 1, status(g, cmd, res).ljust(61), HUD)
        if g.n > 1:
            put(img, geo, b0 + 21, c0 + 63, 'G2=%02d,%02d' % tuple(g.gh[1][:2])
                + (' G3=%02d,%02d' % tuple(g.gh[2][:2]) if g.n > 2 else ''), HUD)
        mrow, mcol, crow, ccol = b0 + 22, c0 + 1, b0 + 24, c0 + 1
        put(img, geo, crow, c0 + 19, gs.HELP_S, HELP)
    if msg is not None:
        put(img, geo, mrow, mcol, 'INVALID COMMAND ' + msg, ERROR, BLINK)
    if banner is not None:
        text, colour = gs.BANNERS[banner]
        put(img, geo, mrow, mcol, text, colour, REVERSE, keep=True)
    put(img, geo, crow, ccol, 'COMMAND ===>', HELP)
    return img


def addr(geo, q):
    q %= geo.cells
    return [CODES[q >> 6], CODES[q & 63]]


def full(geo, img):
    sp1, spf = geo.sf_field()
    out = [0xC3]
    pos, co, hi, a = None, 0, 0, 0
    while a < geo.n:
        if a in (sp1, spf):
            if pos != a:
                out += [0x11] + addr(geo, a)
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
        while b < geo.n and b not in (sp1, spf) and img[b] == cell:
            b += 1
        n = b - a
        ch, c, h, ge = cell
        blank = ch == 0x40 and h == 0 and ge == 0
        if blank and n >= 4:
            a = b
            continue
        if pos != a:
            out += [0x11] + addr(geo, a)
        if not blank and c != co:
            out += sa(c) if c else [0x28, 0x42, 0x00]
            co = c
        if h != hi:
            out += sh(h)
            hi = h
        size = 2 if ge else 1
        one = ([0x08] if ge else []) + [ch]
        out += [0x3C] + addr(geo, b) + one if n * size > 3 + size else one * n
        pos = a = b
    if hi:
        out += sh(0)
    return bytes(out + [0x28, 0x00, 0x00])


def partial(geo, cur, prev, kind):
    out = [0xC3 if kind == 'P' else 0xC2]
    co = hh = 0
    inrun, changed = False, 0
    for i in range(geo.n):
        if cur[i] == prev[i]:
            inrun = False
            continue
        changed += 1
        if not inrun or i % geo.w == 0:
            out += [0x11] + addr(geo, i)
        inrun = True
        b, c, h, ge = cur[i]
        if c != co:
            out += sa(c) if c else [0x28, 0x42, 0x00]
            co = c
        if h != hh:
            out += sh(h)
            hh = h
        out += [0x08, b] if ge else [b]
    if kind == 'T' and not changed:
        return None
    if kind == 'P':
        out += [0x11] + addr(geo, geo.sf_field()[1] + 1) + [0x13] + sa(HELP) + sh(UNDERSCORE) + e(' ') + sh(0)
    return bytes(out + [0x28, 0x00, 0x00])


def relocate(geo, ds):
    """An 80 x 24 G1-G4 stream moved to the origin of the W x H buffer (SBA / RA addresses only)."""
    r0, c0 = geo.org
    out, k = bytearray(ds[:1]), 1
    while k < len(ds):
        b = ds[k]
        if b in (0x11, 0x3C):
            q = CODES.index(ds[k + 1]) * 64 + CODES.index(ds[k + 2])
            out += bytes([b] + addr(geo, geo.a(r0 + q // 80, c0 + q % 80)))
            k += 3
            if b == 0x3C:
                out += ds[k:k + 1]
                k += 1
        elif b in (0x28,):
            out += ds[k:k + 3]
            k += 3
        elif b in (0x1D, 0x08):
            out += ds[k:k + 2]
            k += 2
        else:
            out.append(b)
            k += 1
    return bytes(out)


def frames(case, hi=True, anim=True, redraw='P', glyphs='G', scale='4', canvas='D', snap=None):
    """The whole TSD run. Resolution as PACPLAT in TSD: glyph AUTO = CLASSIC; scale A = 4; scaled only with
    highlight and GRAPHIC glyphs. snap: optional ref_snap.Log ((lives, won) per screen sent, MVS-S1)."""
    prof = {'G': 'G', 'B': 'B', 'C': 'C', 'A': 'C'}[glyphs]
    s = '4' if scale == 'A' else scale
    if s not in '43T' or not hi or prof != 'G':
        s = 'N'
    geo = Geo(canvas, s != 'N', 3 if s == '3' else 4)
    limit = 1000 if s == 'T' else 2048
    if s == 'N':
        return [relocate(geo, f) for f in g4.frames(case, hi, anim, redraw, prof, snap=snap)]
    # the size guard can only trip at the first screen in practice (scale T): find the family that fits it
    ai, n, cards = parse_config((R / f'tests/cases/{case}.txt').read_text().splitlines())
    while geo.fam != 'G':
        first = full(geo, image(geo, Game(ai, n), ' ', 'START  ', None, anim, 0 if anim else 1, 'R'))
        if len(first) <= limit:
            break
        geo.down()
    if geo.fam == 'G':
        return [relocate(geo, f) for f in g4.frames(case, True, anim, redraw, 'G', snap=snap)]
    g = Game(ai, n)
    st = {'vis': 1, 'prev': None, 'last': None, 'face': 'R'}
    out = Rec(snap, lambda: (g.lives, g.won))

    def img(cmd, res, msg, banner=None):
        return image(geo, g, cmd, res, msg, anim, st['vis'], st['face'], banner)

    def prompt(cmd, res, msg, rdr):
        if anim:
            st['vis'] ^= 1
        cur = img(cmd, res, msg)
        if redraw == 'P' and st['prev'] is not None and not rdr:
            out.append(partial(geo, cur, st['prev'], 'P'))
        else:
            out.append(full(geo, cur))
        if redraw == 'P':
            st['prev'] = cur
        st['last'] = (cmd, res, msg)

    def tick():
        if not (anim and redraw == 'P' and st['prev'] is not None):
            return
        st['vis'] ^= 1
        cmd, res, msg = st['last']
        cur = img(cmd, res, msg)
        p = partial(geo, cur, st['prev'], 'T')
        if p is not None:
            out.append(p)
        st['prev'] = cur

    def end(kind, cmd, res):
        if kind == 'QUIT':
            g.state = 'QUIT   '
        out.append(full(geo, img(cmd, res, None, kind)))
        return out

    cmd, res = ' ', 'START  '
    prompt(cmd, res, None, False)
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


def unicode(geo, img):
    names = {0xA2: '─', 0x85: '│', 0xC5: '┌', 0xD5: '┐', 0xC4: '└', 0xD4: '┘', 0x93: '▀', 0x94: '▄', 0xA1: '°',
             0xA3: '•', 0x9B: '⊂', 0xAA: '∩'}
    rows = []
    for r in range(geo.rows):
        s = ''
        for q in range(r * geo.w, (r + 1) * geo.w):
            ch, c, h, ge = img[q]
            s += names.get(ch, '?') if ge else ('█' if ch == 0x40 and h else bytes([ch]).decode('cp037'))
        rows.append(s.rstrip())
    return rows


if __name__ == '__main__':
    canvas = sys.argv[1] if len(sys.argv) > 1 else 'W'
    geo = Geo(canvas, True, 4)
    ai, n, cards = parse_config((R / 'tests/cases/MULTI.txt').read_text().splitlines())
    im = image(geo, Game(ai, n), ' ', 'START  ', 'X', True, 0, 'R')
    print(f'{geo.w}x{geo.h} family {geo.fam} origin {geo.org} b0 {geo.b0} c0 {geo.c0}: full {len(full(geo, im))} bytes')
    print('\n'.join(f'{k + 1:02d}|{l}' for k, l in enumerate(unicode(geo, im))))
