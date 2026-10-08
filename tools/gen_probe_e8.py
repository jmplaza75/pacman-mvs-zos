#!/usr/bin/env python3
"""Generates src/probe/PACFS8.asm (MVS-G3 probe E8, protocol bisect ladder from the working probe E6).
Rung 0 = E6 exactly (screen and partial frames parsed byte for byte from src/probe/PACFS3.asm, variant W protocol);
each next rung adds ONE factor, cumulatively, towards the game:
 1 + Read Partition Query   2 + clear prefix in FULLSCR   3 + 3270 fields (SF) in the initial screen
 4 - 2 s wait before the first partial   5 partial WCC C3 -> C2   6 partial in the exact G3 tick format
 7 + TGET NOWAIT between partials   8 the game's own initial screen and tick streams (independent model)."""
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_g3_screen import cells, partial, GLYPHS  # noqa: E402
from ref_g2_screen import screen, sba  # noqa: E402
from ref_mvs6 import Game  # noqa: E402


def e6_segments():
    segs, cur, name = {}, None, None
    for line in (R / 'src/probe/PACFS3.asm').read_text().splitlines():
        lab = line[:9].strip()
        if lab in ('SCREEN', 'FRMOB', 'FRMCB'):
            name, cur = lab, bytearray()
        if re.match(r'^(SCREENL|FRMOL|FRMCL)\s+EQU', line):
            segs[name], name = bytes(cur), None
            continue
        if name is None:
            continue
        m = re.search(r"DC\s+X'([0-9A-F]+)'", line)
        if m:
            cur += bytes.fromhex(m.group(1))
        m = re.search(r"DC\s+C'(.*)'", line)
        if m:
            cur += m.group(1).replace("''", "'").encode('cp037')
    return segs['SCREEN'], segs['FRMOB'], segs['FRMCB']


scr0, p0o, p0c = e6_segments()
assert scr0[0] == 0xC3 and scr0[-4:] == bytes([0x28, 0, 0, 0x13]) and p0o[0] == 0xC3
e = lambda s: s.encode('cp037')
scr3 = scr0[:1] + bytes(sba(1, 1)) + bytes([0x1D, 0x60]) + scr0[1:-4] + bytes(sba(18, 2)) + bytes([0x28, 0x42, 0xF4]) \
    + e('COMMAND ===>') + bytes([0x1D, 0x40, 0x13, 0x40, 0x1D, 0x60, 0x28, 0, 0])
p5o, p5c = b'\xC2' + p0o[1:], b'\xC2' + p0c[1:]


def g3tick(pc, gc):
    return (b'\xC2' + bytes(sba(7, 10)) + bytes([0x28, 0x42, 0xF6, 0x28, 0x41, 0xF2]) + e(pc)
            + bytes(sba(7, 20)) + bytes([0x28, 0x42, 0xF2]) + e(gc) + bytes([0x28, 0, 0]))


p6o, p6c = g3tick('C', 'G'), g3tick('O', 'W')
g = Game(1, 1)
scrg = screen(g, ' ', 'START  ', None, True, GLYPHS[0])
c0, c1 = (cells(g, ' ', 'START  ', None, True, gl) for gl in GLYPHS)
tk1, tk2 = partial(c1, c0, 'T', True), partial(c0, c1, 'T', True)


def dc(label, data):
    out = f'{label:<9}DS    0H\n'
    for i in range(0, len(data), 24):
        out += "         DC    X'" + data[i:i + 24].hex().upper() + "'\n"
    return out + f'{label + "L":<9}EQU   *-{label}\n'


data = ''.join(dc(n, d) for n, d in (('SCR0', scr0), ('SCR3', scr3), ('SCRG', scrg), ('P0O', p0o), ('P0C', p0c),
                                      ('P5O', p5o), ('P5C', p5c), ('P6O', p6o), ('P6C', p6c), ('TK1', tk1), ('TK2', tk2)))
tpl = (R / 'tools/probe_e8.asm.tpl').read_text()
(R / 'src/probe/PACFS8.asm').write_text(tpl.replace('@@DATA@@\n', data))
print({n: len(d) for n, d in (('SCR0', scr0), ('SCR3', scr3), ('SCRG', scrg), ('P0O', p0o), ('P5O', p5o), ('P6O', p6o),
                              ('TK1', tk1))})
