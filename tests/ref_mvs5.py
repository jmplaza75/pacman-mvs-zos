#!/usr/bin/env python3
"""Independent Python reference model of MVS-5 (lives, game cycle). Usage: ref_mvs5.py cmdfile | --gen-win0 | --gen-catch0
Optional first card AI0 (still ghost) / AI1 (random LCG ghost, default)."""
import sys
from collections import deque
from pathlib import Path
R = Path(__file__).resolve().parent.parent
MAP0 = (R / 'maps/LEVEL1.txt').read_text().splitlines()
START, GSTART, SEED0 = (2, 2), (19, 9), 12345
DIRS = [('U', 0, -1), ('D', 0, 1), ('L', -1, 0), ('R', 1, 0)]


class Game:
    """One game; step(cmd) performs one U/D/L/R tick and returns the result word."""

    def __init__(self, ai=1):
        self.ai, self.seed, self.lives, self.state = ai, SEED0, 3, 'READY  '
        self.grid = [list(r) for r in MAP0]
        self.x, self.y = START
        self.gx, self.gy = GSTART
        self.grid[self.y - 1][self.x - 1] = ' '
        self.grid[self.gy - 1][self.gx - 1] = ' '
        self.left = sum(r.count('.') for r in self.grid)
        self.score = self.t = 0
        self.won = self.lost = False

    def copy(self):
        g = Game.__new__(Game)
        g.__dict__.update(self.__dict__)
        g.grid = [row[:] for row in self.grid]
        return g

    def step(self, u):
        self.t += 1
        nx, ny = self.x + (u == 'R') - (u == 'L'), self.y + (u == 'D') - (u == 'U')
        res = 'BLOCKED'
        if MAP0[ny - 1][nx - 1] != '#':
            self.x, self.y, res = nx, ny, 'MOVED  '
            if self.grid[self.y - 1][self.x - 1] == '.':
                self.grid[self.y - 1][self.x - 1] = ' '
                self.score += 10
                self.left -= 1
            self.won = self.left == 0
        hit = (self.gx, self.gy) == (self.x, self.y)
        if not hit and not self.won and self.ai == 1:
            cand = [(dx, dy) for _, dx, dy in DIRS if MAP0[self.gy + dy - 1][self.gx + dx - 1] != '#']
            if cand:
                self.seed = (self.seed * 75 + 74) % 65537
                dx, dy = cand[self.seed % len(cand)]
                self.gx, self.gy = self.gx + dx, self.gy + dy
            hit = (self.gx, self.gy) == (self.x, self.y)
        if hit:
            self.won = False
            self.lives -= 1
            if self.lives == 0:
                self.lost, res = True, 'LOST   '
            else:
                res = 'DIED   '
                self.x, self.y = START
                self.gx, self.gy = GSTART
                self.won = self.left == 0
        self.state = 'LOST   ' if self.lost else 'WON    ' if self.won else 'RUNNING'
        return res


def simulate(cards):
    cards = list(cards)
    ai = 1
    if cards and cards[0][:1] == 'A':
        ai = 0 if cards[0][2:3] == '0' else 1
        cards = cards[1:]
    g = Game(ai)
    out = ['PACMAN MVS-5 LIVES AND CYCLE']

    def status(c, res):
        out.append((f'T{g.t:03d} {c} {res} X={g.x:02d} Y={g.y:02d} S={g.score:04d} L={g.left:03d} '
                    f'G={g.gx:02d},{g.gy:02d} V={g.lives} ST={g.state}').rstrip())  # JES trims blanks
        for j, row in enumerate(g.grid, 1):
            line = list(row)
            if j == g.y:
                line[g.x - 1] = 'P'
            if j == g.gy:
                line[g.gx - 1] = 'G'
            out.append(''.join(line))
    status(' ', 'START  ')
    end = 'EOF'
    for c in cards:
        c = c[:1].ljust(1)
        u = c.upper()
        if u == 'Q':
            end = 'QUIT'
            break
        if u not in ('U', 'D', 'L', 'R'):
            out.append('INVALID COMMAND ' + c)
            continue
        res = g.step(u)
        status(c, res)
        if g.lost or g.won:
            break
    end = 'LOST' if g.lost else 'WIN' if g.won else end
    out += [end, f'TURNS {g.t:03d}', f'SCORE {g.score:04d}', f'LIVES {g.lives}']
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
