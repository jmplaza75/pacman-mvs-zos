#!/usr/bin/env python3
"""Independent Python reference model of MVS-4 (ghost). Usage: ref_mvs4.py cmdfile | --gen-win0 | --gen-catch0
Optional first card AI0 (still ghost) / AI1 (random LCG ghost, default)."""
import sys
from collections import deque
from pathlib import Path
R = Path(__file__).resolve().parent.parent
MAP0 = (R / 'maps/LEVEL1.txt').read_text().splitlines()
START, GSTART, SEED0 = (2, 2), (19, 9), 12345
DIRS = [('U', 0, -1), ('D', 0, 1), ('L', -1, 0), ('R', 1, 0)]


def simulate(cards):
    cards = list(cards)
    ai = 1
    if cards and cards[0][:1] == 'A':
        ai = 0 if cards[0][2:3] == '0' else 1
        cards = cards[1:]
    grid = [list(r) for r in MAP0]
    x, y = START
    gx, gy = GSTART
    grid[y - 1][x - 1] = ' '
    grid[gy - 1][gx - 1] = ' '
    left = sum(r.count('.') for r in grid)
    seed = SEED0
    score = t = 0
    out = ['PACMAN MVS-4 BASIC GHOST']

    def status(tt, c, res):
        out.append(f'T{tt:03d} {c} {res} X={x:02d} Y={y:02d} S={score:04d} L={left:03d} G={gx:02d},{gy:02d}')
        for j, row in enumerate(grid, 1):
            line = list(row)
            if j == y:
                line[x - 1] = 'P'
            if j == gy:
                line[gx - 1] = 'G'
            out.append(''.join(line))
    status(0, ' ', 'START  ')
    end = 'EOF'
    won = caught = False
    for c in cards:
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
        if MAP0[ny - 1][nx - 1] != '#':
            x, y, res = nx, ny, 'MOVED  '
            if grid[y - 1][x - 1] == '.':
                grid[y - 1][x - 1] = ' '
                score += 10
                left -= 1
            won = left == 0
        if (gx, gy) == (x, y):
            caught, won = True, False
        if not won and not caught and ai == 1:
            cand = [(dx, dy) for _, dx, dy in DIRS if MAP0[gy + dy - 1][gx + dx - 1] != '#']
            if cand:
                seed = (seed * 75 + 74) % 65537
                dx, dy = cand[seed % len(cand)]
                gx, gy = gx + dx, gy + dy
            if (gx, gy) == (x, y):
                caught, won = True, False
        status(t, c, res)
        if caught or won:
            break
    end = 'CAUGHT' if caught else 'WIN' if won else end
    out += [end, f'TURNS {t:03d}', f'SCORE {score:04d}']
    return out


def bfs(src, dst):
    prev, q = {src: None}, deque([src])
    while q:
        p = q.popleft()
        if p == dst:
            break
        for k, dx, dy in DIRS:
            n = (p[0] + dx, p[1] + dy)
            if n not in prev and MAP0[n[1] - 1][n[0] - 1] != '#':
                prev[n] = (p, k)
                q.append(n)
    path, p = [], dst
    while prev[p]:
        p, k = prev[p]
        path.append(k)
    return path[::-1]


def gen_win0():
    """Full-clear route that never enters the (still) ghost cell; ends right after the last pellet."""
    seen = {START, GSTART}
    moves = []
    back = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}

    def dfs(p):
        for k, dx, dy in DIRS:
            n = (p[0] + dx, p[1] + dy)
            if n not in seen and MAP0[n[1] - 1][n[0] - 1] != '#':
                seen.add(n)
                moves.append(k)
                dfs(n)
                moves.append(back[k])
    dfs(START)
    pellets = {(i + 1, j + 1) for j, r in enumerate(MAP0) for i, ch in enumerate(r) if ch == '.'} - {START, GSTART}
    p, eaten = START, set()
    for i, k in enumerate(moves):
        d = {kk: (dx, dy) for kk, dx, dy in DIRS}[k]
        p = (p[0] + d[0], p[1] + d[1])
        eaten.add(p)
        if pellets <= eaten:
            return ['AI0'] + moves[:i + 1] + ['R']
    raise SystemExit('unreachable pellets')


if __name__ == '__main__':
    a = sys.argv[1]
    if a == '--gen-win0':
        print('\n'.join(gen_win0()))
    elif a == '--gen-catch0':
        print('\n'.join(['AI0'] + bfs(START, GSTART) + ['L']))
    else:
        print('\n'.join(simulate(Path(a).read_text().splitlines())))
