#!/usr/bin/env python3
"""Independent reference renderer for the MVS-G4 glyph profiles (written from docs/G4-GLYPHS.md and the E9 evidence,
not from the COBOL). frames(case, hi, anim, redraw, prof) returns every data stream PACSCR must build, as in
ref_g3_screen, with the profile applied to the board: C = the G3 screens; B and G = filled walls (a blank in the wall
colour with reverse video) when highlighting is on, '#' when it is off; B = base pellet; G = CP310 pellet and sprites,
each preceded by the GE order X'08'. Image cells are (byte, colour, highlight, ge). (The rejected neighbour-mask wall
tiles of the first G4 build are documented in docs/evidence/g4-wall-diagnosis.md.)"""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs6 import Game, parse_config  # noqa: E402
from ref_snap import Rec  # noqa: E402
from ref_g2_screen import (e, sba, sa, sh, status, WALL, PELLET, PLAYER, GHOSTS, HUD, ERROR, HELP,  # noqa: E402
                           HELP_TEXT, REVERSE, BLINK, UNDERSCORE)

GE = 0x08
# MVS-GP1 ARCADE (docs/GP1-POWER.md 6): power pellet 'o' white (blink with highlighting), frightened ghosts blue / white
# in the warning window without reverse, eyes '"' white without reverse, drawn under Pac-Man and the other ghosts
POWER, FRIGHT, WARN, EYESC = 0xF7, 0xF1, 0xF7, 0xF7
# MVS-GP2 (docs/GP2-PROGRESSION.md 11): the fruit '%' green, no blink, base set (never GE), under eyes / actors
FRUITC = 0xF4


def fruit_at(g):
    """(x, y) of a shown fruit, else None."""
    return (10, 8) if getattr(g, 'bt', 0) > 0 else None


def fright_colour(g):
    return WARN if 0 < g.fr <= g.k()[1] else FRIGHT
# CP310 code points as observed live in c3270 (docs/evidence/g4-probe-analysis.md, rows AX/9X/DX)
CP310 = {'•': 0xA3, '⊂': 0x9B, '⊃': 0x9A, '○': 0x9D, '∩': 0xAA, '⍝': 0xDF}


def cells(g, cmd, res, msg, hi, prof, anim, vis, face, rp=None):
    """rp (MVS-RP, ref_rp.Tracker): death frame and READY! on the board, the popup on the message row (no invalid
    command message), the high score on row 20."""
    img = [(0x40, 0, 0, 0)] * 1920
    dth = rp['dth'] if rp else None

    def put(row, col, text, colour, high=0):
        for k, c in enumerate(text):
            img[(row - 1) * 80 + col - 1 + k] = (e(c)[0], colour, high, 0) if c != ' ' else (0x40, 0, 0, 0)

    put(1, 2, status(g, cmd, res).ljust(61), HUD)
    if g.n > 1:
        put(2, 2, 'G2=%02d,%02d' % tuple(g.gh[1][:2]) + (' G3=%02d,%02d' % tuple(g.gh[2][:2]) if g.n > 2 else ''), HUD)
    second = anim and vis == 1
    if prof == 'G':
        pl = CP310['○'] if second else CP310['⊃' if face == 'L' else '⊂']
        gh = CP310['⍝' if second else '∩']
    else:
        pl = e('O' if second else 'C' if anim else 'P')[0]
        gh = e('W' if second else 'G')[0]
    for j in range(10):
        row = []
        for i, c in enumerate(g.grid[j]):
            if c == '#':
                filled = prof != 'C' and hi
                row.append([0x40 if filled else e('#')[0], WALL, REVERSE if filled else 0, 'wall'])
            elif c == '.':
                row.append([e('.')[0] if prof == 'C' else CP310['•'] if prof == 'G' else 0xB3, PELLET, 0, 'glyph'])
            elif c == 'o':
                row.append([e('o')[0], POWER, BLINK if hi else 0, 'base'])
            else:
                row.append([0x40, 0, 0, 'open'])
        arc = getattr(g, 'arc', False)
        fr = fruit_at(g)
        if fr and fr[1] == j + 1:
            row[fr[0] - 1] = [e('%')[0], FRUITC, 0, 'base']
        for k, (gx, gy, _) in enumerate(g.gh if dth is None else []):
            if arc and g.mode[k] == 'E' and gy == j + 1:
                row[gx - 1] = [e('"')[0], EYESC, 0, 'base']
        if dth is None and g.y == j + 1:
            row[g.x - 1] = [pl, PLAYER, REVERSE if hi else 0, 'glyph']
        if dth is not None and dth[2] == j + 1:          # MVS-RP death frames: glyph, c o . *, nothing
            from ref_rp import DEATH_GLYPHS
            f = dth[0]
            row[dth[1] - 1] = ([pl, PLAYER, REVERSE if hi else 0, 'glyph'] if f == 1 else [0x40, 0, 0, 'open']
                               if f == 6 else [e(DEATH_GLYPHS[f - 2])[0], PLAYER, 0, 'base'])
        if rp and rp['ready'] and j + 1 == 5:
            from ref_rp import READY_X, READY_TEXT
            for k, c in enumerate(READY_TEXT):
                row[READY_X - 1 + k] = [e(c)[0], PLAYER, 0, 'base']
        for k, (gx, gy, _) in enumerate(g.gh if dth is None else []):
            if gy == j + 1 and arc and g.mode[k] == 'F':
                row[gx - 1] = [gh, fright_colour(g), 0, 'glyph']
            elif gy == j + 1 and not (arc and g.mode[k] == 'E'):
                row[gx - 1] = [gh, GHOSTS[k], REVERSE if hi else 0, 'glyph']
        for i, (b, col, h, kind) in enumerate(row):
            ge = 1 if prof == 'G' and kind == 'glyph' else 0
            img[(3 + j) * 80 + 30 + i] = (0x40, 0, 0, 0) if kind == 'open' else (b, col, h, ge)
    if msg is not None:
        put(16, 2, 'INVALID COMMAND ' + msg, ERROR, BLINK if hi else 0)
    elif rp and rp['pu']:
        put(16, 2, rp['pu']['msg'], rp['pu']['col'])
    if rp and rp['hi'] is not None:
        put(20, 2, 'HIGH SCORE %07d' % rp['hi'], HUD)
    put(18, 2, 'COMMAND ===>', HELP)
    put(23, 2, HELP_TEXT, HELP)
    return img


def cell_bytes(b, ge):
    return [GE, b] if ge else [b]


def screen(img, g, msg, hi, rp=None):
    """Full screen: the G2 layout; board cells taken from the image (colour order only for visible colour changes)."""
    out = [0xC3] + sba(1, 1) + [0x1D, 0x60] + sba(1, 2) + sa(HUD) + [b for b, *_ in img[1:62]]
    if g.n > 1:
        n = 8 if g.n == 2 else 17
        out += sba(2, 2) + sa(HUD) + [b for b, *_ in img[81:81 + n]]
    for j in range(10):
        out += sba(4 + j, 31)
        cur = hcur = 0
        for b, col, h, ge in img[(3 + j) * 80 + 30:(3 + j) * 80 + 50]:
            if col and col != cur:
                out += sa(col)
                cur = col
            if h != hcur:
                out += sh(h)
                hcur = h
            out += cell_bytes(b, ge)
        if hcur:
            out += sh(0)
    if msg is not None:
        out += sba(16, 2) + sa(ERROR) + (sh(BLINK) if hi else []) + e('INVALID COMMAND ' + msg) + (sh(0) if hi else [])
    elif rp and rp['pu']:
        out += sba(16, 2) + sa(rp['pu']['col']) + e(rp['pu']['msg'])
    if rp and rp['hi'] is not None:
        out += sba(20, 2) + sa(HUD) + e('HIGH SCORE %07d' % rp['hi'])
    out += sba(18, 2) + sa(HELP) + e('COMMAND ===>') + [0x1D, 0x40] + (sh(UNDERSCORE) if hi else []) + [0x13, 0x40] \
        + (sh(0) if hi else []) + [0x1D, 0x60]
    out += sba(23, 2) + sa(HELP) + e(HELP_TEXT) + [0x28, 0x00, 0x00]
    return bytes(out)


def partial(cur, prev, kind, hi):
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
        out += cell_bytes(b, ge)
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


def frames(case, hi=False, anim=False, redraw='F', prof='C', faces=None, snap=None, mk=Game, d='cases', hs=None,
           plain_first=False):
    """faces: optional list that receives the Pac-Man facing used for every logical screen (for the tests).
    snap: optional ref_snap.Log that receives (lives, won) for every screen sent (MVS-S1).
    mk / d (MVS-GP1): the game class (ref_arcade.Arcade for RULES(ARCADE)) and the case directory under tests/."""
    ai, n, cards = parse_config((R / f'tests/{d}/{case}.txt').read_text().splitlines())
    g = mk(ai, n)
    st = {'vis': 1, 'prev': None, 'last': None, 'face': 'R', 'plain': plain_first}
    out = Rec(snap, lambda: g.snap() if hasattr(g, 'snap') else (g.lives, g.won))
    from ref_rp import Tracker, drop
    tr = Tracker(hs)

    def decor():
        rp = tr.frame(g, 'T')
        if st['plain']:                     # MVS-RP size guard: the first screen rebuilt without decorations
            st['plain'] = False
            rp = drop(rp)
        return rp

    def image(cmd, res, msg, rp=None):
        return cells(g, cmd, res, msg, hi, prof, anim, st['vis'], st['face'], rp)

    def prompt(cmd, res, msg, rdr):
        if anim:
            st['vis'] ^= 1
        rp = decor()
        cur = image(cmd, res, msg, rp)
        if faces is not None:
            faces.append(st['face'])
        if redraw == 'P' and st['prev'] is not None and not rdr:
            out.append(partial(cur, st['prev'], 'P', hi))
        else:
            out.append(screen(cur, g, msg, hi, rp))
        if redraw == 'P':
            st['prev'] = cur
        st['last'] = (cmd, res, msg)

    def tick():
        if not (anim and redraw == 'P' and st['prev'] is not None):
            return
        st['vis'] ^= 1
        cmd, res, msg = st['last']
        cur = image(cmd, res, msg, decor())
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
            continue
        u = stripped.upper()
        if u == 'Q':
            return out
        if u in ('U', 'D', 'L', 'R'):
            cmd, res = stripped, g.step(u)
            if g.lost or g.won:
                return out
            if u in 'LR' and res != 'BLOCKED':
                st['face'] = u
            prompt(cmd, res, None, False)
        else:
            prompt(cmd, res, stripped, False)
    return out


if __name__ == '__main__':
    for f in frames(sys.argv[1], True, True, 'P', sys.argv[2] if len(sys.argv) > 2 else 'G'):
        print(len(f), f.hex().upper())
