#!/usr/bin/env python3
"""Dev tool: engineer AI1 command lists where the LAST pellet is eaten in the very tick the ghost is on that cell.
Phase A: chase the ghost until `lives` remain; B: eat every pellet but one (greedy); C: wait with wall bumps,
then walk onto the last pellet so arrival coincides with the ghost. Usage: search_edge.py LIVES_BEFORE OUTFILE"""
import sys
from collections import deque
sys.path.insert(0, 'tests')
from ref_mvs5 import Game, MAP0, DIRS


def first_step(g, goal):
    """BFS shortest first move from the player to goal(cell) -> (move, path_cells) or None."""
    src = (g.x, g.y)
    prev, q = {src: None}, deque([src])
    while q:
        p = q.popleft()
        if goal(p):
            path = []
            while prev[p]:
                p, k = prev[p]
                path.append(k)
            return path[::-1]
        for k, dx, dy in DIRS:
            n = (p[0] + dx, p[1] + dy)
            if n not in prev and MAP0[n[1] - 1][n[0] - 1] != '#':
                prev[n] = (p, k)
                q.append(n)
    return None


def bump(g):
    for k, dx, dy in DIRS:
        if MAP0[g.y + dy - 1][g.x + dx - 1] == '#':
            return k


def build(lives_before):
    g, cmds = Game(1), []
    while g.lives > lives_before:                       # phase A
        if len(cmds) > 600:
            return None
        k = first_step(g, lambda p: p == (g.gx, g.gy))[0]
        cmds.append(k)
        g.step(k)
    for pad in range(0, 40):                            # shift the ghost phase before eating
        r = attempt(g, cmds, lives_before, pad)
        if r:
            return r
    return None


def attempt(g0, cmds, lives_before, pad):
    g, cmds = g0.copy(), list(cmds)
    for _ in range(pad):
        k = bump(g)
        cmds.append(k)
        g.step(k)
    if g.lives != lives_before:
        return None
    pellets = [(i + 1, j + 1) for j, r in enumerate(g.grid) for i, ch in enumerate(r) if ch == '.']
    for c in pellets:                                   # candidate last pellet
        h, hc = g.copy(), list(cmds)
        ok = True
        while h.left > 1 and ok:                        # phase B
            path = first_step(h, lambda p: h.grid[p[1] - 1][p[0] - 1] == '.' and p != c)
            if not path:
                ok = False
                break
            hc.append(path[0])
            h.step(path[0])
            ok = h.lives == lives_before
        if not ok or h.left != 1 or h.grid[c[1] - 1][c[0] - 1] != '.':
            continue
        for w in range(0, 400):                         # phase C
            f, fc = h.copy(), list(hc)
            for _ in range(w):
                k = bump(f)
                fc.append(k)
                f.step(k)
            if f.lives != lives_before:
                break
            path = first_step(f, lambda p: p == c)
            for k in path[:-1]:
                fc.append(k)
                f.step(k)
            if f.lives != lives_before:
                continue
            fc.append(path[-1])
            res = f.step(path[-1])
            if f.left == 0 and res in ('DIED   ', 'LOST   ') and f.lives == lives_before - 1:
                return fc
    return None


if __name__ == '__main__':
    r = build(int(sys.argv[1]))
    if not r:
        sys.exit('not found')
    open(sys.argv[2], 'w').write('\n'.join(r + ['R']) + '\n')
    print(len(r), 'commands')
