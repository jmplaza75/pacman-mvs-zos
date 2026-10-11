#!/usr/bin/env python3
"""Independent reference model of MVS-GP1 RULES(ARCADE) (docs/GP1-POWER.md, D36), written from the design, not from the
COBOL. Shared with the earlier models only: the LEVEL1 map, the start cells, the AI1-AI3 moves of a NORMAL ghost
(ref_mvs6), the REALTIME controller (ref_rt: TTL, 4/5 cadence, pause, freeze) and the card readers.
simulate(cards) -> BAT TURN lines; rt_simulate(cards) -> BAT REALTIME lines; tso(cards, parm_cfg) -> TSO line mode.
Usage: ref_arcade.py CARDFILE [--rt]"""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs6 import Game, parse_config, MAP0, START, GSTARTS, GDIR0, REV, DIRS  # noqa: E402
import ref_rt  # noqa: E402

POWER = [(2, 4), (19, 4), (2, 8), (19, 8)]
# design 3a: (fright, warning, eyes wait, REALTIME frightened accumulator step) per mode
K = {'T': (20, 5, 10, 2), 'R': (40, 10, 20, 2)}
CHAIN = [200, 400, 800, 1600]
BANNER, RULES = 'PACMAN MVS-6 SMART GHOSTS', 'RULES ARCADE'


class Arcade(Game):
    """One ARCADE game. play = 'T' (TURN) or 'R' (REALTIME). Ghost entries: [x, y, dir]; mode N/F/E, wait, rev."""

    def __init__(self, ai=1, n=1, play='T'):
        super().__init__(ai, n)
        assert all(MAP0[y - 1][x - 1] == '.' for x, y in POWER)
        for x, y in POWER:
            assert (x, y) != START and (x, y) not in GSTARTS[:n]
            self.grid[y - 1][x - 1] = 'o'
        self.left = sum(r.count('.') + r.count('o') for r in self.grid)
        self.arc, self.play, self.ascore, self.power, self.eaten = True, play, 0, 4, 0
        self.cmd, self.res, self.ticks = ' ', 'START  ', 0
        self.death_reset()
        self.evt, self.pts, self.moven = '    ', 0, 1
        self.log = []                                 # (event, ...) for the edge-case search (no effect on output)

    # ---- state helpers
    def death_reset(self):
        self.fr = self.fturn = self.facc = self.chain = 0
        self.movef = 0
        self.mode, self.wait, self.rev = ['N'] * 3, [0] * 3, [0] * 3

    def home(self, i):
        self.gh[i] = [GSTARTS[i][0], GSTARTS[i][1], GDIR0[i]]

    def k(self):
        return K['R' if self.play == 'R' else 'T']

    # ---- one fright tick (TURN: each move; REALTIME: each running quantum)
    def tick(self):
        self.evt, self.pts = '    ', 0
        if self.fr > 0:
            self.fr -= 1
            if self.fr == 0:
                self.fright_end()
            else:
                self.fturn += 1
        for i in range(self.n):
            if self.mode[i] != 'E':
                continue
            self.wait[i] -= 1
            if self.wait[i] > 0:
                continue
            if tuple(self.gh[i][:2]) == (self.x, self.y):
                self.wait[i] = 1                      # Pac-Man on the home cell: one more tick
                self.log.append(('defer', i))
                continue
            self.log.append(('revive', i, self.fr > 0))
            self.mode[i] = 'N'                        # NORMAL even if a fright is running
            self.home(i)

    def fright_end(self):
        self.log.append(('fend',))
        self.fr = self.fturn = self.facc = self.chain = 0
        for i in range(self.n):
            if self.mode[i] == 'F':
                self.mode[i], self.rev[i] = 'N', 0

    def fright_start(self):
        self.fr = self.k()[0]
        self.fturn = self.facc = self.chain = 0
        self.movef = 0                                # no frightened move in the step where it starts
        self.evt = 'POWR'
        self.log.append(('power', self.fr_was, tuple(self.mode[:self.n])))
        for i in range(self.n):
            if self.mode[i] != 'E':                   # eyes ignore a new power pellet
                self.mode[i], self.rev[i] = 'F', 1

    def warning(self):
        return 0 < self.fr <= self.k()[1]

    # ---- moves
    def flee(self, i):
        gx, gy, d = self.gh[i]
        opened = [k for k in (1, 2, 3, 4) if MAP0[gy + DIRS[k - 1][2] - 1][gx + DIRS[k - 1][1] - 1] != '#']
        if self.rev[i]:
            self.rev[i] = 0
            if REV[d] in opened:
                self.gh[i] = [gx + DIRS[REV[d] - 1][1], gy + DIRS[REV[d] - 1][2], REV[d]]
                self.log.append(('reversed', i))
                return
            self.log.append(('revblocked', i))
        cand = [k for k in opened if k != REV[d]] or ([REV[d]] if REV[d] in opened else [])
        if not cand:
            return

        def dist(k):
            return abs(gx + DIRS[k - 1][1] - self.x) + abs(gy + DIRS[k - 1][2] - self.y)
        best = max(dist(k) for k in cand)
        pick = next(k for k in cand if dist(k) == best)      # first maximum, U D L R
        self.log.append(('flee', i, sum(dist(k) == best for k in cand) > 1))
        self.gh[i] = [gx + DIRS[pick - 1][1], gy + DIRS[pick - 1][2], pick]

    def move_ghosts(self):
        for i in range(self.n):
            if self.mode[i] == 'N' and self.moven:
                self.move_ghost(self.gh[i])           # AI1-AI3 as 1.0-MVS (seed only here)
            elif self.mode[i] == 'F' and self.movef:
                self.flee(i)

    def collide(self, phase=1):
        """Design 4.4: index order; eyes nothing, frightened eaten (scored at once), normal = hit."""
        hit, ate = False, 0
        for i in range(self.n):
            if tuple(self.gh[i][:2]) != (self.x, self.y):
                continue
            if self.mode[i] == 'E':
                self.log.append(('oneyes', i))
            if self.mode[i] == 'N':
                hit = True
            elif self.mode[i] == 'F':
                ate += 1
                self.chain = min(self.chain + 1, 4)
                self.pts = CHAIN[self.chain - 1]
                self.ascore += self.pts
                self.eaten += 1
                self.evt = 'GHST'
                self.mode[i], self.wait[i], self.rev[i] = 'E', self.k()[2], 0
                self.home(i)
        if ate or hit:
            self.log.append(('collide', phase, ate, hit))
        return hit

    def turn(self, kind, d):
        """kind: T (TURN: tick + whole turn), B / P / G (REALTIME steps, the tick was done by the controller)."""
        if kind == 'T':
            self.tick()
            self.moven = 1
            self.movef = 1 if self.fr > 0 and self.fturn > 0 and self.fturn % 2 == 0 else 0
        if kind in 'TBP':
            self.ticks += 1
            self.cmd = d
            dx, dy = ref_rt.D[d]
            self.res = 'BLOCKED'
            if MAP0[self.y + dy - 1][self.x + dx - 1] != '#':
                self.x, self.y, self.res = self.x + dx, self.y + dy, 'MOVED  '
                c = self.grid[self.y - 1][self.x - 1]
                if c in '.o':
                    self.grid[self.y - 1][self.x - 1] = ' '
                    self.left -= 1
                    self.ascore += 10 if c == '.' else 50
                    if c == 'o':
                        self.power -= 1
                        self.fr_was = self.fr
                        self.fright_start()
                self.won = self.left == 0
        hit = self.collide()
        if not hit and not self.won and self.ai > 0 and kind != 'P':
            self.move_ghosts()
            hit = self.collide(2)
        if hit:
            self.log.append(('death', self.fr > 0, tuple(self.mode[:self.n]), self.left == 0))
            self.won = False
            self.lives -= 1
            self.death_reset()
            if self.lives == 0:
                self.lost, self.res = True, 'LOST   '
            else:
                self.res = 'DIED   '
                self.x, self.y = START
                for i in range(self.n):
                    self.home(i)
                self.won = self.left == 0
        self.state = 'LOST   ' if self.lost else 'WON    ' if self.won else 'RUNNING'
        self.t = self.ticks % 1000
        self.score = self.ascore % 10000

    def step(self, u):
        """The TURN interface of the screen models (ref_g4_screen / ref_gx_screen frames)."""
        self.turn('T', u)
        return self.res

    # ---- text
    def arc_line(self):
        return (f'A S={self.ascore:07d} PW={self.power} FR={self.fr:03d} FT={self.fturn:03d} FA={self.facc} '
                f'CH={self.chain} EV={self.evt:<4} P={self.pts:04d} N={self.eaten:03d} M=' +
                ' '.join(f'{self.mode[i]}{self.wait[i]:03d}' for i in range(self.n)))

    def frame(self, c, res):
        g = self
        out = [(f'T{g.t:03d} {c} {res} X={g.x:02d} Y={g.y:02d} S={g.score:04d} L={g.left:03d} '
                f'G={g.gh[0][0]:02d},{g.gh[0][1]:02d} V={g.lives} ST={g.state}').rstrip(), g.arc_line()]
        if g.n > 1:
            out.append('G2=%02d,%02d' % tuple(g.gh[1][:2]) + (' G3=%02d,%02d' % tuple(g.gh[2][:2]) if g.n > 2 else ''))
        out += g.board()
        return out

    def board(self):
        lines = []
        for j, row in enumerate(self.grid, 1):
            line = list(row)
            if j == self.y:
                line[self.x - 1] = 'P'
            for i in range(self.n):
                gx, gy, _ = self.gh[i]
                if j == gy:
                    line[gx - 1] = 'G' if self.mode[i] == 'N' else self.mode[i]
            lines.append(''.join(line))
        return lines

    def end_lines(self, end, quanta=None):
        out = [end, f'TURNS {self.t:03d}', f'SCORE {self.ascore:07d}', f'LIVES {self.lives}']
        if quanta is not None:
            out.append(f'QUANTA {quanta:07d}')
        return out + [f'GHOSTS EATEN {self.eaten:03d}']


def simulate(cards, prompts=False, cfg=None, redraw=False):
    """BAT TURN (cfg None: optional first config card) or TSO line mode (cfg from the PARM, prompts, blank = redraw)."""
    cards = list(cards)
    if cfg is None:
        ai, n, cards = parse_config(cards)
    else:
        ai, n = cfg
    g = Arcade(ai, n, 'T')
    out = [BANNER, RULES]
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


class ArcadeRT(ref_rt.Controller):
    """PACRT with design 3a/4.2/4.3: tick first, normal 4/5 accumulator, frightened +2 due at >= 5, ACC 0 at a death."""

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
            g.facc += g.k()[3]
            if g.facc >= 5:
                g.facc -= 5
                g.movef = 1
        self.acc += ref_rt.GH_NUM
        gdue = self.acc >= ref_rt.GH_DEN
        if gdue:
            self.acc -= ref_rt.GH_DEN
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
            lives = g.lives
            g.turn(self.kind, self.cur)
            if g.lives < lives:
                self.acc = 0
            if g.lives < lives and not g.lost:
                self.frz, self.cur, self.req, self.ttl = ref_rt.FREEZE, ' ', ' ', 0


def open_(g, d):
    dx, dy = ref_rt.D[d]
    return MAP0[g.y + dy - 1][g.x + dx - 1] != '#'


Arcade.open = open_


def rt_simulate(cards):
    """BAT REALTIME (one card = one quantum), the ref_rt.run driver without screens, plus the ARCADE lines."""
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
    g = Arcade(ai, n, 'R')
    c = ArcadeRT(g)
    out = [BANNER, RULES] + g.frame(' ', 'START  ')
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
        if g.won or g.lost:
            st['over'], st['end'] = True, 'LOST' if g.lost else 'WIN'
    end = 'LOST' if g.lost else 'WIN' if g.won else st['end']
    return out + g.end_lines(end, c.q)


if __name__ == '__main__':
    cards = Path(sys.argv[1]).read_text().splitlines()
    print('\n'.join(rt_simulate(cards) if '--rt' in sys.argv else simulate(cards)))
