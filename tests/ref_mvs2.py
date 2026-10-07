#!/usr/bin/env python3
"""Independent Python reference model of MVS-2; prints expected SYSOUT for a command file."""
import sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
MAP = (R / 'maps/LEVEL1.txt').read_text().splitlines()


def board(x, y):
    out = []
    for j, row in enumerate(MAP, 1):
        out.append(row[:x - 1] + 'P' + row[x:] if j == y else row)
    return out


def simulate(cmds):
    x = y = 2
    t = 0
    out = ['PACMAN MVS-2 PLAYER BY TURNS', 'T00   START   X=02 Y=02'] + board(x, y)
    quit_ = False
    for c in cmds:
        c = c[:1].ljust(1)
        u = c.upper()
        if u == 'Q':
            quit_ = True
            break
        if u not in 'UDLR' or u == ' ':
            out.append('INVALID COMMAND ' + c)
            continue
        t += 1
        nx, ny = x + (u == 'R') - (u == 'L'), y + (u == 'D') - (u == 'U')
        res = 'BLOCKED'
        if 1 <= nx <= 20 and 1 <= ny <= 10 and MAP[ny - 1][nx - 1] != '#':
            x, y, res = nx, ny, 'MOVED  '
        out.append(f'T{t:02d} {c} {res} X={x:02d} Y={y:02d}')
        out += board(x, y)
    out += ['QUIT' if quit_ else 'EOF', f'TURNS {t:02d}']
    return out


if __name__ == '__main__':
    print('\n'.join(simulate(Path(sys.argv[1]).read_text().splitlines())))
