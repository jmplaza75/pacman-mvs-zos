#!/usr/bin/env python3
"""Independent Python reference model of MVS-6 (ghost AI levels, several ghosts). Usage: ref_mvs6.py cmdfile | --gen-win0 | --gen-catch0
Optional first card "AI<0-3>[ <1-3>]": ghost level (0 still, 1 random, 2 persistent, 3 chase) and ghost count."""
import sys
from collections import deque
from pathlib import Path
R = Path(__file__).resolve().parent.parent
MAP0 = (R / 'maps/LEVEL1.txt').read_text().splitlines()
START, GSTART, SEED0 = (2, 2), (19, 9), 12345
GSTARTS = [(19, 9), (2, 9), (19, 2)]      # ghost start cells; initial direction index (1=U 2=D 3=L 4=R)
GDIR0 = [3, 4, 3]
REV = {1: 2, 2: 1, 3: 4, 4: 3}
DIRS = [('U', 0, -1), ('D', 0, 1), ('L', -1, 0), ('R', 1, 0)]


class Game:
    """One game; step(cmd) performs one U/D/L/R tick and returns the result word.
    ai: 0 still, 1 random (may reverse), 2 persistent direction, 3 chase (Manhattan). n: number of ghosts."""

    def __init__(self, ai=1, n=1):
        self.ai, self.n, self.seed, self.lives, self.state = ai, n, SEED0, 3, 'READY  '
        self.grid = [list(r) for r in MAP0]
        self.x, self.y = START
        self.grid[self.y - 1][self.x - 1] = ' '
        self.gh = [[GSTARTS[i][0], GSTARTS[i][1], GDIR0[i]] for i in range(n)]
        for gx, gy, _ in self.gh:
            self.grid[gy - 1][gx - 1] = ' '
        self.left = sum(r.count('.') for r in self.grid)
        self.score = self.t = 0
        self.won = self.lost = False

    def copy(self):
        g = Game.__new__(Game)
        g.__dict__.update(self.__dict__)
        g.grid = [row[:] for row in self.grid]
        g.gh = [r[:] for r in self.gh]
        return g

    def draw(self, n):
        self.seed = (self.seed * 75 + 74) % 65537
        return self.seed % n

    def move_ghost(self, gh):
        gx, gy, d = gh
        opened = [k for k in (1, 2, 3, 4)
                  if MAP0[gy + DIRS[k - 1][2] - 1][gx + DIRS[k - 1][1] - 1] != '#']
        if self.ai == 1:
            cand = opened
        else:
            cand = [k for k in opened if k != REV[d]]
            if not cand:
                cand = [REV[d]] if REV[d] in opened else []
        if not cand:
            return
        if self.ai == 3:
            def dist(k):
                return abs(gx + DIRS[k - 1][1] - self.x) + abs(gy + DIRS[k - 1][2] - self.y)
            pick = min(cand, key=lambda k: (dist(k), k))
        elif self.ai == 2 and len(cand) == 1:
            pick = cand[0]
        else:
            pick = cand[self.draw(len(cand))]
        gh[0], gh[1], gh[2] = gx + DIRS[pick - 1][1], gy + DIRS[pick - 1][2], pick

    def on_player(self):
        return sum(1 for gx, gy, _ in self.gh if (gx, gy) == (self.x, self.y))

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
        hit = self.on_player() > 0
        if not hit and not self.won and self.ai > 0:
            for gh in self.gh:
                self.move_ghost(gh)
            hit = self.on_player() > 0
        self.last_hits = self.on_player()
        if hit:
            self.won = False
            self.lives -= 1
            if self.lives == 0:
                self.lost, res = True, 'LOST   '
            else:
                res = 'DIED   '
                self.x, self.y = START
                self.gh = [[GSTARTS[i][0], GSTARTS[i][1], GDIR0[i]] for i in range(self.n)]
                self.won = self.left == 0
        self.state = 'LOST   ' if self.lost else 'WON    ' if self.won else 'RUNNING'
        return res


def parse_config(cards):
    ai, n = 1, 1
    if cards and cards[0][:1] == 'A':
        c = cards[0]
        ai = int(c[2:3]) if c[2:3] in ('0', '1', '2', '3') else 1
        n = int(c[4:5]) if c[4:5] in ('1', '2', '3') else 1
        cards = cards[1:]
    return ai, n, cards


def simulate(cards):
    ai, n, cards = parse_config(list(cards))
    g = Game(ai, n)
    out = ['PACMAN MVS-6 SMART GHOSTS']

    def status(c, res):
        out.append((f'T{g.t:03d} {c} {res} X={g.x:02d} Y={g.y:02d} S={g.score:04d} L={g.left:03d} '
                    f'G={g.gh[0][0]:02d},{g.gh[0][1]:02d} V={g.lives} ST={g.state}').rstrip())
        if n > 1:
            out.append('G2=%02d,%02d' % tuple(g.gh[1][:2]) + (' G3=%02d,%02d' % tuple(g.gh[2][:2]) if n > 2 else ''))
        for j, row in enumerate(g.grid, 1):
            line = list(row)
            if j == g.y:
                line[g.x - 1] = 'P'
            for gx, gy, _ in g.gh:
                if j == gy:
                    line[gx - 1] = 'G'
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
