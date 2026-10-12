#!/usr/bin/env python3
"""Independent reference model of MVS-GP2 RULES(ARCADE) (docs/GP2-PROGRESSION.md, D37), written from the design, not
from the COBOL. It extends the GP1 model (tests/ref_arcade.py, D36, kept unchanged as the GP1 reference) with levels,
the per-level table, the maze refill, the fruit, the extra life, the event flags and the wide counters.
simulate(cards) -> BAT TURN lines; rt_simulate(cards) -> BAT REALTIME lines; TSO line mode = simulate(prompts, cfg).
Usage: ref_gp2.py CARDFILE [--rt] [--start N]"""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
import ref_arcade as A  # noqa: E402
import ref_rt  # noqa: E402
from ref_mvs6 import MAP0, START, GSTARTS, parse_config  # noqa: E402

# design 4.2: level -> (AI bump, REALTIME normal step of 10, fright T, warning T, fright R, warning R, fruit, points)
ROWS = {1: (0, 8, 20, 5, 40, 10, 'C', 100), 2: (0, 8, 17, 5, 34, 10, 'S', 300), 3: (1, 8, 14, 5, 27, 10, 'O', 500),
        4: (1, 9, 10, 4, 20, 7, 'O', 500), 5: (2, 9, 7, 3, 13, 7, 'A', 700), 6: (2, 9, 17, 5, 34, 10, 'A', 700),
        7: (2, 9, 7, 3, 13, 7, 'M', 1000), 8: (2, 9, 7, 3, 13, 7, 'M', 1000), 9: (2, 9, 4, 2, 7, 3, 'G', 2000),
        10: (2, 9, 17, 5, 34, 10, 'G', 2000), 11: (2, 9, 7, 3, 13, 7, 'B', 3000), 12: (2, 9, 4, 2, 7, 3, 'B', 3000),
        13: (2, 9, 4, 2, 7, 3, 'K', 5000)}
EYES = {'T': 10, 'R': 20}            # GP1, unchanged at every level
FINC = 2                             # GP1 frightened accumulator step (due at >= 5)
FRUIT_CELL = (10, 8)
FRUIT_AT = (30, 70)                  # items eaten in the level
FRUIT_TIME = {'T': 30, 'R': 60}
XLIFE = 10000
LAST = 99
FREEZE = 10


def parse_start(text):
    """PARM columns 22-23 (design 5): 1 or 2 digits up to the PARM end, 1-99; anything else = 1."""
    if len(text) in (1, 2) and text.isdigit() and 0 < int(text) < 100:
        return int(text)
    return 1


class Level(A.Arcade):
    def __init__(self, ai=1, n=1, play='T', start=1):
        self.level, self.aib = start, ai
        self.bt = 0
        super().__init__(ai, n, play)
        assert MAP0[FRUIT_CELL[1] - 1][FRUIT_CELL[0] - 1] == '.' and FRUIT_CELL != START
        assert FRUIT_CELL not in GSTARTS and FRUIT_CELL not in A.POWER
        self.xl, self.turns, self.fruits, self.ndie, self.evf = 0, 0, 0, 0, '-----'
        self.level_start()

    # ---- the row of the level
    def row(self):
        return ROWS[min(self.level, 13)]

    def k(self):
        r = self.row()
        if self.play == 'R':
            return (r[4], r[5], EYES['R'], FINC)
        return (r[2], r[3], EYES['T'], FINC)

    def level_start(self):
        r = self.row()
        self.ai = 0 if self.aib == 0 else min(3, self.aib + r[0])
        self.knum, self.bk, self.bv = r[1], r[6], r[7]
        self.items = self.bn = self.bt = 0
        self.death_reset()

    def flag(self, c):
        i = 'AFXCD'.index(c)
        self.evf = self.evf[:i] + c + self.evf[i + 1:]

    def add(self, pts, src):
        self.ascore += pts
        if not self.xl and self.ascore >= XLIFE:      # once, at the moment the points are added
            self.xl = 1
            self.lives += 1
            self.flag('X')
            self.log.append(('xlife', src))

    # ---- ticks: GP1 (fright, eyes) then the fruit timer
    def tick(self):
        super().tick()
        self.evf = '-----'
        if self.bt > 0:
            self.bt -= 1
            if self.bt == 0:
                self.log.append(('fruitexp',))

    def collide(self, phase=1):
        before = self.ascore
        hit = super().collide(phase)                  # GP1 scores eaten ghosts directly
        if self.ascore != before:
            gained = self.ascore - before
            self.ascore = before
            self.add(gained, 'ghost')                 # extra life before the hit is applied
        return hit

    def refill(self):
        self.grid = [list(r) for r in MAP0]
        self.grid[START[1] - 1][START[0] - 1] = ' '
        for i in range(self.n):
            gx, gy = GSTARTS[i]
            self.grid[gy - 1][gx - 1] = ' '
        for x, y in A.POWER:
            self.grid[y - 1][x - 1] = 'o'
        self.left = sum(r.count('.') + r.count('o') for r in self.grid)
        self.power = 4

    def level_clear(self):
        self.flag('C')
        self.log.append(('clear', self.level, self.lives, self.fr > 0, tuple(self.mode[:self.n])))
        if self.level >= LAST:
            return                                    # level 99 cleared: the game is won
        self.level += 1
        self.won = False
        self.res = 'CLEARED'
        self.x, self.y = START
        for i in range(self.n):
            self.home(i)
        self.refill()
        self.level_start()

    def turn(self, kind, d):
        if kind == 'T':
            self.tick()
            self.moven = 1
            self.movef = 1 if self.fr > 0 and self.fturn > 0 and self.fturn % 2 == 0 else 0
        if kind in 'TBP':
            self.turns += 1
            self.cmd = d
            dx, dy = ref_rt.D[d]
            self.res = 'BLOCKED'
            if MAP0[self.y + dy - 1][self.x + dx - 1] != '#':
                self.x, self.y, self.res = self.x + dx, self.y + dy, 'MOVED  '
                c = self.grid[self.y - 1][self.x - 1]
                if c in '.o':
                    self.grid[self.y - 1][self.x - 1] = ' '
                    self.left -= 1
                    if c == 'o':
                        self.power -= 1
                        self.fr_was = self.fr
                        self.fright_start()
                    self.add(10 if c == '.' else 50, 'item')
                    self.items += 1
                    if self.items in FRUIT_AT:
                        self.log.append(('fruit', self.items, (self.x, self.y) == FRUIT_CELL, self.bt > 0))
                        self.bn += 1
                        self.bt = FRUIT_TIME['R' if self.play == 'R' else 'T']
                        self.flag('A')
                if self.bt > 0 and (self.x, self.y) == FRUIT_CELL:
                    self.bt = 0
                    self.fruits += 1
                    self.flag('F')
                    self.log.append(('fruiteat',))
                    self.add(self.bv, 'fruit')
                self.won = self.left == 0
        hit = self.collide()
        if not hit and not self.won and self.ai > 0 and kind != 'P':
            self.move_ghosts()
            hit = self.collide(2)
        if hit:
            self.log.append(('death', self.fr > 0, tuple(self.mode[:self.n]), self.left == 0))
            if self.bt > 0:
                self.log.append(('deathfruit',))
            self.won = False
            self.lives -= 1
            self.death_reset()
            self.bt = 0
            self.flag('D')
            self.ndie += 1
            if self.lives == 0:
                self.lost, self.res = True, 'LOST   '
            else:
                self.res = 'DIED   '
                self.x, self.y = START
                for i in range(self.n):
                    self.home(i)
                self.won = self.left == 0
        if self.won and not self.lost:
            self.level_clear()
        self.state = 'LOST   ' if self.lost else 'WON    ' if self.won else 'RUNNING'
        self.t = self.turns % 1000
        self.score = self.ascore % 10000

    def snap(self):
        """Screen snapshot for the bell rule (MVS-GP2 / S1): lives, won, deaths, extra life, level."""
        return (self.lives, self.won, self.ndie, self.xl, self.level)

    def step(self, u):
        self.turn('T', u)
        return self.res

    # ---- text
    def lvl_line(self):
        return (f'L LV={self.level:03d} AI={self.ai} IT={self.items:03d} BN={self.bn} BT={self.bt:03d} BK={self.bk} '
                f'BV={self.bv:04d} XL={self.xl} EV={self.evf}')

    def arc_line(self):
        line = super().arc_line()
        k = line.index(' N=')
        return line[:k] + f' N={self.eaten % 1000:03d}' + line[k + 6:]

    def frame(self, c, res):
        out = super().frame(c, res)
        return out[:2] + [self.lvl_line()] + out[2:]

    def board(self):
        if self.bt > 0:
            row = self.grid[FRUIT_CELL[1] - 1]
            saved = row[FRUIT_CELL[0] - 1]
            row[FRUIT_CELL[0] - 1] = '%'               # under Pac-Man and the ghosts
            lines = super().board()
            row[FRUIT_CELL[0] - 1] = saved
            return lines
        return super().board()

    def end_lines(self, end, quanta=None):
        out = [end, f'TURNS {self.turns:07d}', f'SCORE {self.ascore:07d}', f'LIVES {self.lives}']
        if quanta is not None:
            out.append(f'QUANTA {quanta:07d}')
        return out + [f'GHOSTS EATEN {self.eaten:04d}', f'FRUITS EATEN {self.fruits:03d}', f'LEVEL {self.level:03d}']


def head(g):
    return [A.BANNER, A.RULES, f'LEVEL {g.level:03d}']


def simulate(cards, prompts=False, cfg=None, redraw=False, start=1):
    cards = list(cards)
    if cfg is None:
        ai, n, cards = parse_config(cards)
    else:
        ai, n = cfg
    g = Level(ai, n, 'T', start)
    out = head(g)
    last = g.frame(' ', 'START  ')
    out += last
    end = 'EOF'
    for c in cards:
        if prompts:
            out.append('CMD (U/D/L/R/Q)?')
        if redraw and not c.strip():
            out += last
            continue
        c = c[:1].ljust(1)
        u = c.upper()
        if u == 'Q':
            end = 'QUIT'
            break
        if u not in ('U', 'D', 'L', 'R'):
            out.append('INVALID COMMAND ' + c)
            continue
        g.turn('T', u)
        last = g.frame(c, g.res)
        out += last
        if g.lost or g.won:
            break
    else:
        if prompts:
            out.append('CMD (U/D/L/R/Q)?')
    end = 'LOST' if g.lost else 'WIN' if g.won else end
    return out + g.end_lines(end)


class LevelRT(ref_rt.Controller):
    """PACRT under D37: tick first, normal accumulator + the level's step due at >= 10, frightened + 2 due at >= 5;
    a death (flag D) or a level clear (flag C) resets the normal accumulator and freezes 10 quanta."""

    def rq(self):
        g = self.g
        self.q += 1
        self.rtin, self.buf, self.kind = ''.join(self.buf), [], '-'
        self.vis = (self.q // ref_rt.ANIM_Q) % 2
        if self.frz:
            self.frz -= 1
            self.kind = 'F'
            return
        g.tick()
        g.movef = 0
        if g.fr > 0:
            g.facc += FINC
            if g.facc >= 5:
                g.facc -= 5
                g.movef = 1
        self.acc += g.knum
        gdue = self.acc >= 10
        if gdue:
            self.acc -= 10
        g.moven = 1 if gdue else 0
        gdue = gdue or g.movef == 1
        if self.req != ' ':
            if g.open(self.req):
                self.cur, self.req, self.ttl = self.req, ' ', 0
            else:
                self.ttl -= 1
            if self.ttl == 0:
                self.req = ' '
        pmove = self.cur != ' ' and g.open(self.cur)
        self.kind = 'B' if pmove and gdue else 'P' if pmove else 'G' if gdue else '-'
        if self.kind != '-':
            g.turn(self.kind, self.cur)
            if 'D' in g.evf or 'C' in g.evf:
                self.acc = 0
                if not g.lost:
                    self.frz, self.cur, self.req, self.ttl = FREEZE, ' ', ' ', 0


def rt_simulate(cards, start=1):
    cards = list(cards)
    stream = []
    for evs in ref_rt.events(cards):
        stream += evs + [('NON', ' ', ' ')]
    stream.append(('EOF', ' ', ' '))
    pos = [0]

    def read():
        e = stream[min(pos[0], len(stream) - 1)]
        pos[0] += 1
        return e
    first = read()
    ai, n = 1, 1
    if first[0] == 'CFG':
        ai, n, _ = parse_config([cards[0]])
        first = read()
    g = Level(ai, n, 'R', start)
    c = LevelRT(g)
    out = head(g) + g.frame(' ', 'START  ')
    st = {'over': False, 'end': 'EOF'}

    def event(e):
        kind, d, ch = e
        if kind in ('NON', 'IGN', 'CFG'):
            return
        if kind == 'EOF':
            st['over'], st['end'] = True, 'EOF'
            return
        c.rin(kind, d, ch)
        if kind == 'QUI':
            st['over'], st['end'] = True, 'QUIT'
            return
        if kind == 'INV':
            out.append('INVALID COMMAND ' + ch)

    e = first
    while True:
        event(e)
        if st['over'] or c.started:
            break
        e = read()

    def collect():
        while True:
            e = read()
            event(e)
            if e[0] == 'NON' or st['over']:
                return
    while not st['over']:
        collect()
        while c.status() == 'PAUS' and not st['over']:
            while c.status() == 'PAUS' and not st['over']:
                event(read())
            if st['over']:
                break
            collect()
        if st['over']:
            break
        c.rq()
        out.append(f'Q{c.q:07d} IN={c.rtin:<8} K={c.kind} C={c.cur} R={c.req} T={c.ttl} X={g.x:02d} Y={g.y:02d} '
                   f'S={g.score:04d} L={g.left:03d} V={g.lives} ST={g.state}')
        out.append('  G=' + ' '.join('%02d,%02d' % (x, y) for x, y, _ in g.gh))
        out.append(g.arc_line())
        out.append(g.lvl_line())
        if g.won or g.lost:
            st['over'], st['end'] = True, 'LOST' if g.lost else 'WIN'
    end = 'LOST' if g.lost else 'WIN' if g.won else st['end']
    return out + g.end_lines(end, c.q)


Level.open = A.open_


if __name__ == '__main__':
    args = sys.argv[1:]
    st = int(args[args.index('--start') + 1]) if '--start' in args else 1
    cs = Path(args[0]).read_text().splitlines()
    print('\n'.join(rt_simulate(cs, st) if '--rt' in args else simulate(cs, start=st)))
