#!/usr/bin/env python3
"""Generate the DC statements of the MVS-G1 colour/highlight probe screen (3270 data stream, 12-bit addresses)
for src/probe/PACFS.asm. Usage: g1_probe_screen.py > build/demo_dc.asm"""
CODES = [0x40, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F,
         0x50, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E, 0x5F,
         0x60, 0x61, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F,
         0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F]
SA, COLOR, HILITE, RESET = 0x28, 0x42, 0x41, (0x28, 0x00, 0x00)
items = []


def sba(r, c):
    a = (r - 1) * 80 + (c - 1)
    items.append(('X', [0x11, CODES[a >> 6], CODES[a & 63]]))


def x(*b):
    items.append(('X', list(b)))


def c(t):
    items.append(('C', t))


x(0xC3)                                            # WCC: reset, keyboard restore, reset MDT (Erase/Write by TSO)
sba(1, 1); c('PACMAN G1 COLOUR PROBE - PRESS ENTER')
for i, (code, name) in enumerate([(0xF1, 'BLUE'), (0xF2, 'RED'), (0xF3, 'PINK'), (0xF4, 'GREEN'),
                                  (0xF5, 'TURQUOISE'), (0xF6, 'YELLOW'), (0xF7, 'WHITE')]):
    sba(3 + i, 2); x(SA, COLOR, code); c(f'{name} {code:02X}'); x(*RESET)
for i, (code, name) in enumerate([(0xF1, 'BLINK'), (0xF2, 'REVERSE'), (0xF4, 'UNDERSCORE')]):
    sba(11 + i, 2); x(SA, HILITE, code); c(name); x(*RESET)
sba(14, 1); x(0x1D, 0xE8); c('INTENSIFIED FIELD'); x(0x1D, 0x60)
sba(16, 2)
for ch, col in (('#', 0xF1), ('.', 0xF7), ('.', 0xF7), ('P', 0xF6), ('.', 0xF7), ('G', 0xF2), ('.', 0xF7), ('#', 0xF1)):
    x(SA, COLOR, col); c(ch)
x(*RESET)
sba(18, 1); c('ALL WHITE OR GREEN = NO EXTENDED COLOUR')
sba(20, 1); x(0x13)                                # insert cursor

out, first = [], True
for kind, v in items:
    parts = [v[k:k + 20] for k in range(0, len(v), 20)] if kind == 'X' else [v]
    for p in parts:
        operand = "X'" + ''.join(f'{b:02X}' for b in p) + "'" if kind == 'X' else f"C'{p}'"
        out.append(f"{'DEMO' if first else '':<8} DC    {operand}")
        first = False
out.append('DEMOEND  EQU   *')
print('\n'.join(out))
