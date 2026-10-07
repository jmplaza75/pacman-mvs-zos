#!/usr/bin/env python3
"""Independent Python reference model of MVS-3 (pellets/score/win). Usage: ref_mvs3.py cmdfile
   ref_mvs3.py --gen-win  prints a command sequence that eats every pellet, plus one trailing command."""
import sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
MAP0 = (R / 'maps/LEVEL1.txt').read_text().splitlines()
START = (2, 2)


def render(grid, x, y):
    return [(''.join(r)[:x - 1] + 'P' + ''.join(r)[x:]) if j == y else ''.join(r) for j, r in enumerate(grid, 1)]


def simulate(cmds):
    grid = [list(r) for r in MAP0]
    x, y = START
    grid[y - 1][x - 1] = ' '
    left = sum(r.count('.') for r in grid)
    score = t = 0
    out = ['PACMAN MVS-3 PELLETS AND SCORE']

    def status(tt, c, res):
        out.append(f'T{tt:03d} {c} {res} X={x:02d} Y={y:02d} S={score:04d} L={left:03d}')
        out.extend(render(grid, x, y))
    status(0, ' ', 'START  ')
    end = 'EOF'
    for c in cmds:
        c = c[:1].ljust(1)
        u = c.upper()
        if u == 'Q':
            end = 'QUIT'
            break
        if u not in ('U', 'D', 'L', 'R'):
            out.append('INVALID COMMAND ' + c)
            continue
        t += 1
        nx, ny = x + (u == 'R') - (u == 'L'), y + (u == 'D') - (u == 'U')
        res = 'BLOCKED'
        if 1 <= nx <= 20 and 1 <= ny <= 10 and grid[ny - 1][nx - 1] != '#':
            x, y, res = nx, ny, 'MOVED  '
            if grid[y - 1][x - 1] == '.':
                grid[y - 1][x - 1] = ' '
                score += 10
                left -= 1
        status(t, c, res)
        if left == 0:
            end = 'WIN'
            break
    out += [end, f'TURNS {t:03d}', f'SCORE {score:04d}']
    return out


def gen_win():
    grid = [list(r) for r in MAP0]
    grid[START[1] - 1][START[0] - 1] = ' '
    todo = sum(r.count('.') for r in grid)
    seen = {START}
    moves = []
    d = {'U': (0, -1), 'D': (0, 1), 'L': (-1, 0), 'R': (1, 0)}
    back = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}

    def dfs(x, y):
        for k, (dx, dy) in d.items():
            n = (x + dx, y + dy)
            if n not in seen and MAP0[n[1] - 1][n[0] - 1] != '#':
                seen.add(n)
                moves.append(k)
                dfs(*n)
                moves.append(back[k])
    dfs(*START)
    # truncate after the last pellet is eaten
    g = [list(r) for r in grid]
    x, y = START
    left = todo
    for i, k in enumerate(moves):
        x, y = x + d[k][0], y + d[k][1]
        if g[y - 1][x - 1] == '.':
            g[y - 1][x - 1] = ' '
            left -= 1
            if left == 0:
                return moves[:i + 1] + ['R']
    raise SystemExit('unreachable pellets')


if __name__ == '__main__':
    if sys.argv[1] == '--gen-win':
        print('\n'.join(gen_win()))
    else:
        print('\n'.join(simulate(Path(sys.argv[1]).read_text().splitlines())))
