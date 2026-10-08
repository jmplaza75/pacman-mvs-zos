#!/usr/bin/env python3
"""Generates src/probe/PACFS7.asm (MVS-G3 probe E7) with the data streams of the independent model: the game's initial full
screen (case start, highlights on, animated glyph frame 0) and the two idle-tick streams (frame 0->1 and 1->0)."""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_g3_screen import cells, partial, GLYPHS  # noqa: E402
from ref_g2_screen import screen  # noqa: E402
from ref_mvs6 import Game  # noqa: E402

g = Game(1, 1)
full = screen(g, ' ', 'START  ', None, True, GLYPHS[0])
c0, c1 = (cells(g, ' ', 'START  ', None, True, gl) for gl in GLYPHS)
tick1, tick2 = partial(c1, c0, 'T', True), partial(c0, c1, 'T', True)
# variant I: the same glyph change in the format of the game's (visible) logical partial: WCC C3 + cells + input field with IC
tick1i, tick2i = partial(c1, c0, 'P', True), partial(c0, c1, 'P', True)
# variant F: the same initial screen without 3270 fields: every SF order (1D + attribute) becomes one blank (same positions)
fullf, i = bytearray(), 0
while i < len(full):
    if full[i] == 0x1D:
        fullf.append(0x40)
        i += 2
    else:
        fullf.append(full[i])
        i += 1
fullf = bytes(fullf)
assert full.count(0x1D) == 3 and 0x1D not in fullf and len(fullf) == len(full) - 3


def dc(label, data):
    out = f'{label:<9}DS    0H\n'
    for i in range(0, len(data), 24):
        out += "         DC    X'" + data[i:i + 24].hex().upper() + "'\n"
    return out + f'{label}L{" " * (8 - len(label) - 1)}EQU   *-{label}\n'


tpl = (R / 'tools/probe_e7.asm.tpl').read_text()
(R / 'src/probe/PACFS7.asm').write_text(tpl.replace('@@DATA@@', dc('FULLS', full) + dc('FULLF', fullf) + dc('TICK1', tick1) + dc('TICK2', tick2)
                                                    + dc('TICK1I', tick1i) + dc('TICK2I', tick2i)))
print(len(full), len(fullf), len(tick1), len(tick2), len(tick1i), len(tick2i))
