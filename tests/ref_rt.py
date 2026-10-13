#!/usr/bin/env python3
"""Independent reference model of MVS-RT REALTIME (docs/RT-REALTIME.md, D33), written from the design, not from the COBOL.
Game rules: the ref_mvs6 model, split into a player step (P), a ghost step (G) and the whole turn (B). Screens: the
ref_gx_screen renderer. One card = one quantum: its characters up to the first blank are the inputs of that quantum
(U D L R any case, Q quit, P pause, * = PA2 redraw, . or + = nothing, anything else invalid); a first card starting with
A is the configuration (BAT). Before the start only a direction makes the game start (that card is quantum 1).
simulate(cards) -> BAT output lines; frames(cards, parm_cfg, canvas) -> (TSD streams, end lines).
Usage: ref_rt.py CARDFILE [--tsd CANVAS]"""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
from ref_mvs6 import Game, parse_config, MAP0, START, GSTARTS, GDIR0  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
import ref_gs_screen as gs  # noqa: E402
from ref_snap import Rec  # noqa: E402

gs.BANNERS.setdefault('PAUSE', (' PAUSED ', gs.HELP))   # RT3: while paused the message row shows this banner

TTL, FREEZE, GH_NUM, GH_DEN, ANIM_Q = 3, 10, 4, 5, 3
# MVS-RP RP.3 SPEED (docs/RP-POLISH.md 6): the quantum in ms (PARM column 24: F = FAST, anything else NORMAL). Every
# REALTIME duration is designed in quanta of 150 ms and converted to the selected quantum, rounded half up; the
# movement cadence stays per quantum. READY! = the last 4 designed freeze quanta, a popup lasts 5 quanta after its
# first frame, a death-animation frame is 150 ms.
NORMAL, FAST = 150, 125
READY_Q, POPUP_Q, DEATH_FRAME_MS = 4, 5, 150


def quanta(q, per=NORMAL):
    """q quanta of 150 ms -> the same length in quanta of per ms, rounded half up (per 150: q)."""
    return (q * 300 + per) // (2 * per)


def period(speed):
    """PARM column 24 -> the quantum (ms)."""
    return FAST if speed == 'F' else NORMAL
D = {'U': (0, -1), 'D': (0, 1), 'L': (-1, 0), 'R': (1, 0)}


class RTGame(Game):
    """ref_mvs6 Game with the REQ-STEP split. cmd / res = LAST-CMD / LAST-RESULT (HUD)."""

    def __init__(self, ai=1, n=1):
        super().__init__(ai, n)
        self.cmd, self.res, self.ticks = ' ', 'START  ', 0

    def open(self, d):
        dx, dy = D[d]
        return MAP0[self.y + dy - 1][self.x + dx - 1] != '#'

    def play(self, kind, d):
        if kind in 'BP':
            self.ticks += 1
            self.cmd = d
            dx, dy = D[d]
            self.res = 'BLOCKED'
            if MAP0[self.y + dy - 1][self.x + dx - 1] != '#':
                self.x, self.y, self.res = self.x + dx, self.y + dy, 'MOVED  '
                if self.grid[self.y - 1][self.x - 1] == '.':
                    self.grid[self.y - 1][self.x - 1] = ' '
                    self.score += 10
                    self.left -= 1
                self.won = self.left == 0
        hit = self.on_player() > 0
        if not hit and not self.won and self.ai > 0 and kind != 'P':
            for gh in self.gh:
                self.move_ghost(gh)
            hit = self.on_player() > 0
        if hit:
            self.won = False
            self.lives -= 1
            if self.lives == 0:
                self.lost, self.res = True, 'LOST   '
            else:
                self.res = 'DIED   '
                self.x, self.y = START
                self.gh = [[GSTARTS[i][0], GSTARTS[i][1], GDIR0[i]] for i in range(self.n)]
                self.won = self.left == 0
        self.state = 'LOST   ' if self.lost else 'WON    ' if self.won else 'RUNNING'
        self.t = self.ticks % 1000


class Controller:
    """PACRT: directions, TTL, 4/5 ghost cadence, pause, death freeze, counters."""

    def __init__(self, g, per=NORMAL):
        self.g, self.q, self.cur, self.req, self.ttl, self.acc = g, 0, ' ', ' ', 0, 0
        self.per, g.per = per, per                    # RP.3: the game converts its own REALTIME durations
        self.frt, self.rdy, self.puq = quanta(FREEZE, per), quanta(READY_Q, per), quanta(POPUP_Q, per)
        self.frz, self.pause, self.started, self.buf, self.vis, self.kind, self.rtin = 0, False, False, [], 0, '-', ''

    def status(self):
        if not self.started:
            return 'WAIT'
        if self.pause:
            return 'PAUS'
        return 'FRZ ' if self.frz else 'RUN '

    def rin(self, kind, d, ch):
        if len(self.buf) < 8:
            self.buf.append({'MOV': d, 'QUI': 'Q', 'PAU': 'P', 'RDR': '*', 'CFG': 'A'}.get(kind, ch))
        if kind == 'PAU' and self.started:
            self.pause = not self.pause
        if kind == 'MOV' and not self.pause and not self.frz:
            self.req, self.ttl, self.started = d, TTL, True

    def rq(self):
        g = self.g
        self.q += 1
        self.rtin, self.buf, self.kind = ''.join(self.buf), [], '-'
        self.vis = (self.q // ANIM_Q) % 2
        if self.frz:
            self.frz -= 1
            self.kind = 'F'
            return
        self.acc += GH_NUM
        gdue = self.acc >= GH_DEN
        if gdue:
            self.acc -= GH_DEN
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
            g.play(self.kind, self.cur)
            if g.lives < lives and not g.lost:
                self.frz, self.cur, self.req, self.ttl = self.frt, ' ', ' ', 0


def events(cards):
    """PACINPT RT card reader: one event list per card, None = end of input."""
    for card in cards:
        card = card.ljust(80)[:80]
        if card[0] == 'A':
            yield [('CFG', ' ', 'A')]
            continue
        evs = []
        for ch in card:
            if ch == ' ':
                break
            if ch in '.+':
                continue
            u = ch.upper()
            if ch in 'Pp':
                evs.append(('PAU', ' ', ch))
            elif ch == '*':
                evs.append(('RDR', ' ', ch))
            elif ch == 'A':
                evs.append(('INV', ' ', ch))
            elif u in D:
                evs.append(('MOV', u, ch))
            elif u == 'Q':
                evs.append(('QUI', ' ', ch))
            else:
                evs.append(('INV', ' ', ch))
        yield evs


def run(cards, tsd=None, cfg=None, snap=None, mk_game=None, mk_ctl=None, hs=None, per=NORMAL):
    """The PACMAIN RT-GAME driver. tsd = None (BAT) or a canvas letter (TSD); cfg = (ai, n) from the PARM (TSD).
    snap: optional ref_snap.Log ((lives, won) per screen sent, MVS-S1). mk_game / mk_ctl (MVS-GP1): the ARCADE game
    and controller of tests/ref_arcade.py (TSD screens only; its end lines come from the game)."""
    stream = []
    for evs in events(cards):
        stream += [e for e in evs] + [('NON', ' ', ' ')]
    stream.append(('EOF', ' ', ' '))
    pos = [0]

    def read():
        e = stream[min(pos[0], len(stream) - 1)]
        pos[0] += 1
        return e
    out, frames = [], Rec(snap, lambda: g.snap() if hasattr(g, 'snap') else (g.lives, g.won))
    first = read() if tsd is None else None
    ai, n = cfg or (1, 1)
    if tsd is None and first[0] == 'CFG':
        ai, n, _ = parse_config([cards[0]])
        first = read()
    g = (mk_game or RTGame)(ai, n)
    c = (mk_ctl or Controller)(g, per)
    st = {'prev': None, 'msg_on': None, 'msg_last': None, 'face': 'R', 'frame': ' ', 'over': False}
    from ref_rp import Tracker
    tr = Tracker(hs)

    def decor(rtstat=None, rtfrz=None, ends=False):
        """MVS-RP: the decorations of the screen composed now (PACRT published status, freeze count, death cell)."""
        return tr.frame(g, 'R', rtstat or c.status(), c.frz if rtfrz is None else rtfrz, c.q,
                        getattr(c, 'dth', None), ends, tm=(c.per, c.frt, c.rdy, c.puq))
    geo = None
    if tsd is not None:
        geo = gx.Geo(tsd, True, 4)
    else:
        out.append('PACMAN MVS-6 SMART GHOSTS')
        out += board(g)

    def face():
        if g.cmd in 'LR' and g.res != 'BLOCKED':
            st['face'] = g.cmd
        return st['face']

    def prmt(rdr, kind='N'):
        if geo is None:
            return
        paused = c.status() == 'PAUS'
        show = st['msg_on']
        cur = gx.image(geo, g, g.cmd, g.res, None if paused else show, True, c.vis, face(),
                       'PAUSE' if paused else None, decor())
        frames.append(gx.full(geo, cur) if st['prev'] is None or rdr else gx.partial(geo, cur, st['prev'], 'P'), kind)
        st['prev'], st['msg_last'], st['msg_on'] = cur, show, None

    def rtqf(rtstat=None, rtfrz=None):
        cur = gx.image(geo, g, g.cmd, g.res, st['msg_last'], True, c.vis, face(), None, decor(rtstat, rtfrz))
        p = gx.partial(geo, cur, st['prev'], 'T')
        frames.append(p if p is not None else bytes([0xC2, 0x28, 0x00, 0x00]), 'Q')
        st['prev'] = cur

    def event(e):
        kind, d, ch = e
        if kind in ('NON', 'IGN', 'CFG'):
            return
        if kind == 'EOF':
            st['over'], st['end'] = True, 'EOF'
            return
        c.rin(kind, d, ch)
        if kind == 'QUI':
            g.state = 'QUIT   '
            st['over'], st['end'] = True, 'QUIT'
            return
        if kind == 'INV':
            if geo is None:
                out.append('INVALID COMMAND ' + ch)
            else:
                st['msg_on'] = ch
            if st['frame'] == ' ':
                st['frame'] = 'P'
        if kind == 'RDR':
            st['frame'] = 'F'

    def pre_screen(kind='N'):
        prmt(st['frame'] == 'F', kind)
        st['frame'] = ' '

    prmt(False)
    e = first if tsd is None else read()
    while True:
        event(e)
        if st['over'] or c.started:
            break
        if e[0] != 'NON':                       # RT3: every input gets a screen (keyboard restore)
            pre_screen()
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
            if st['frame'] == ' ':
                st['frame'] = 'P'
            pre_screen()
            while c.status() == 'PAUS' and not st['over']:
                e = read()
                event(e)
                if not st['over'] and c.status() == 'PAUS' and e[0] != 'NON':
                    pre_screen()
            if st['over']:
                break
            collect()
        if st['over']:
            break
        c.rq()
        if geo is None:
            out.append(f'Q{c.q:07d} IN={c.rtin:<8} K={c.kind} C={c.cur} R={c.req} T={c.ttl} X={g.x:02d} Y={g.y:02d} '
                       f'S={g.score:04d} L={g.left:03d} V={g.lives} ST={g.state}')
            out.append('  G=' + ' '.join('%02d,%02d' % (gx_, gy) for gx_, gy, _ in g.gh))
        elif st['frame'] != ' ':
            pre_screen('P')                     # MVS-S2: the quantum's one write in prompt form
        else:
            rtqf()
        st['frame'] = ' '
        if g.won or g.lost:
            st['over'], st['end'] = True, 'LOST' if g.lost else 'WIN'
    end = 'LOST' if g.lost else 'WIN' if g.won else st.get('end', 'EOF')
    if geo is not None and getattr(g, 'arc', False) and g.lost:
        for k in range(c.frt, c.rdy, -1):     # MVS-RP: the final death frames (PACDISP, before the end screen)
            rtqf('FRZ ', k)
    if geo is not None and geo.fam != 'G':
        frames.append(gx.full(geo, gx.image(geo, g, g.cmd, g.res, None, True, c.vis, face(), end,
                                            decor(ends=True))), 'E')
    if hasattr(g, 'end_lines'):
        return out + g.end_lines(end, c.q), frames
    out += [end, f'TURNS {g.t:03d}', f'SCORE {g.score:04d}', f'LIVES {g.lives}', f'QUANTA {c.q:07d}']
    return out, frames


def board(g):
    """The BAT start frame (status line, extra ghosts, board) as PACDISP STAT prints it."""
    lines = [(f'T{g.t:03d}   START   X={g.x:02d} Y={g.y:02d} S={g.score:04d} L={g.left:03d} '
              f'G={g.gh[0][0]:02d},{g.gh[0][1]:02d} V={g.lives} ST={g.state}').rstrip()]
    if g.n > 1:
        lines.append('G2=%02d,%02d' % tuple(g.gh[1][:2]) + (' G3=%02d,%02d' % tuple(g.gh[2][:2]) if g.n > 2 else ''))
    for j, row in enumerate(g.grid, 1):
        line = list(row)
        if j == g.y:
            line[g.x - 1] = 'P'
        for x, y, _ in g.gh:
            if j == y:
                line[x - 1] = 'G'
        lines.append(''.join(line))
    return lines


def simulate(cards, per=NORMAL):
    return run(list(cards), per=per)[0]


def tsd(cards, canvas, snap=None, mk_game=None, mk_ctl=None, hs=None, per=NORMAL):
    """(parm config, cards) as the TSD deck runs them: the config card goes to the PARM."""
    ai, n, rest = parse_config(list(cards))
    return run(rest, tsd=canvas, cfg=(ai, n), snap=snap, mk_game=mk_game, mk_ctl=mk_ctl, hs=hs, per=per)


if __name__ == '__main__':
    cards = Path(sys.argv[1]).read_text().splitlines()
    if len(sys.argv) > 3 and sys.argv[2] == '--tsd':
        o, f = tsd(cards, sys.argv[3])
        print(len(f), 'streams;', o[-5:])
    else:
        print('\n'.join(simulate(cards)))
