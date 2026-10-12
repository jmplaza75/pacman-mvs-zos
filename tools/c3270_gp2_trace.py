#!/usr/bin/env python3
"""MVS-GP2 GP2.4 live acceptance: one RULES(ARCADE) game (REALTIME or TURN, 120x27) in a c3270 -trace file, from the
first host write with the ARCADE title after --from to the line-mode end. Nothing before the game start is read (no
logon); inbound records are used only by their AID (and, for ENTER, the one typed game command).
1. The game inputs are rebuilt from the AIDs between the host writes: REALTIME one card per quantum (arrows PF7/8/10/11
   = U D L R, PF9 = pause, PA2 = redraw, ENTER = its command; an AID right before a write may belong to the next one:
   both are tried, as tools/c3270_gp1_trace.py); TURN one card per ENTER (its command).
2. The cards are replayed through the independent GP2 model (tests/ref_gp2.py + the screen models; PARM config
   AI/GHOSTS, start level, SOUND bells from the counters as tests/test_gp2.py) and every live host write is compared
   with the model stream byte for byte (write 0 may carry the platform's first-screen clear prefix 11 40 40 3C 40 40 00,
   which the TSD dry run does not print).
3. On a match, the model state of every quantum / turn is what the terminal showed: the report lists the GP2 events
   (level, fruit shown / eaten / expired, power pellets with the fright length, extra life, deaths, level clear and
   the freeze, pause intervals with the fruit timer before / after, PA2 redraws, alarm writes) and the end lines.
Usage: c3270_gp2_trace.py TRACE --cfg 'AI0 1' [--start N] [--play R|T] [--from HHMMSS] [--sound Y|N]
       (the scenario of tools/gp2_live.py: --scenario A|B|C sets cfg / start / play)"""
import argparse
import itertools
import shutil
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tools'))
sys.path.insert(0, str(R / 'tests'))
from c3270_rt_trace import load, ms  # noqa: E402
from c3270_gp1_trace import TITLE, host, command, cards_for  # noqa: E402
import ref_gp2 as L  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
import ref_rt  # noqa: E402
from ref_snap import Log  # noqa: E402

PREFIX = bytes.fromhex('1140403c404000')
SCEN = {'A': ('AI0 1', 1, 'R'), 'B': ('AI0 1', 13, 'T'), 'C': ('AI2 1', 13, 'R')}


def bells(frames, log, sound):
    """The GP2 alarm rule (tests/test_gp2.py): start, deaths / extra life / level rose, the first WIN; one per write."""
    if sound != 'Y':
        return list(frames)
    st = {'last': None, 'won': False}

    def ring(snap):
        b = st['last'] is None or any(snap[i] > st['last'][i] for i in (2, 3, 4)) or (snap[1] and not st['won'])
        st['won'], st['last'] = st['won'] or snap[1], snap
        return b
    out = [bytes([f[0] | 0x04]) + f[1:] if ring(s) else f for f, s in zip(frames, log)]
    if ring(log.state()):
        out.append(bytes([0xC6, 0x28, 0x00, 0x00]))
    return out


def model(cfg, start, play, cards, sound):
    log = Log()
    if play == 'R':
        end, fs = ref_rt.tsd([cfg] + cards, 'W', snap=log, mk_game=lambda a, n: L.Level(a, n, 'R', start),
                             mk_ctl=L.LevelRT)
        return end, bells(fs, log, sound)
    tmp = Path(tempfile.mkdtemp(dir=R / 'build'))
    (tmp / 'LIVE.txt').write_text('\n'.join([cfg] + cards) + '\n')
    try:
        fs = gx.frames('LIVE', True, False, 'P', 'G', '4', 'W', snap=log, mk=lambda a, n: L.Level(a, n, 'T', start),
                       d=f'../build/{tmp.name}')
    finally:
        shutil.rmtree(tmp)
    return L.simulate([cfg] + cards, start=start), bells(fs, log, sound)


def same(p, q, k):
    return p == q or (k == 0 and p.replace(PREFIX, b'', 1) == q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('trace')
    ap.add_argument('--scenario', choices=sorted(SCEN))
    ap.add_argument('--cfg', default='AI1 1')
    ap.add_argument('--start', type=int, default=1)
    ap.add_argument('--play', default='R')
    ap.add_argument('--from', dest='frm', default='000000')
    ap.add_argument('--sound', default='Y')
    a = ap.parse_args()
    if a.scenario:
        a.cfg, a.start, a.play = SCEN[a.scenario]
    ev = [e for e in load(a.trace) if e[1] and ms(e[1]) >= ms(a.frm + '.000')]
    starts = [i for i, e in enumerate(ev) if e[0] == '<' and TITLE in e[2]]
    if not starts:
        raise SystemExit('no ARCADE game screen in the trace')
    ev = ev[starts[0]:]
    help_quit = 'Q QUIT '.encode('cp037')
    banners = [w.encode('cp037') for w in (' GAME OVER ', ' YOU WIN ', ' QUIT ', ' END OF INPUT ')]

    def is_end(b):
        return any(b.count(v) > (b.count(help_quit) if v == banners[2] else 0) for v in banners)
    gw, aids, lines, over = [], [], [], False
    for kind, t, x in ev:
        if kind == '<' and not over:
            b = host(x)
            if b[:1] in (b'\xf1', b'\x7e', b'\xf5'):
                gw.append((ms(t), b))
                over = is_end(b)
        elif kind == '<':
            text = host(x).decode('cp037', 'replace')
            lines.append(''.join(ch if ch.isprintable() else ' ' for ch in text).strip())
        elif kind == '>' and x and not over and gw:
            cmd = command(x)
            if cmd:
                aids.append((ms(t), cmd))
    live = [b[1:] for _, b in gw]
    if a.play == 'T':
        cards = [c for _, c in aids if c not in ('*', '.')]
        end, fs = model(a.cfg, a.start, 'T', cards, a.sound)
        n_same = sum(1 for k, (p, q) in enumerate(zip(live, fs)) if same(p, q, k))
    else:
        best = None
        near = [i for i, (t, _) in enumerate(aids) if any(0 <= tw - t < 60 for tw, _ in gw)]
        for combo in itertools.product((0, 1), repeat=min(len(near), 10)):
            shift = [0] * len(aids)
            for i, s in zip(near, combo):
                shift[i] = s
            cs = cards_for(gw, aids, shift)
            while cs and cs[-1] == '.':
                cs.pop()
            e, f = model(a.cfg, a.start, 'R', cs, a.sound)
            k_same = sum(1 for k, (p, q) in enumerate(zip(live, f)) if same(p, q, k))
            if best is None or k_same > best[0]:
                best = (k_same, cs, e, f)
            if k_same == len(live) == len(f):
                break
        n_same, cards, end, fs = best
    ok = n_same == len(live) == len(fs)
    print(f'game writes: live {len(live)}, model {len(fs)}, identical {n_same}' + (' | ALL IDENTICAL' if ok else ''))
    bad = [k for k, (p, q) in enumerate(zip(live, fs)) if not same(p, q, k)]
    print('first difference at write', bad[0] if bad else '-',
          '(write 0 carries the clear prefix)' if live and live[0] != fs[0] and same(live[0], fs[0], 0) else '')
    print('cards:', ' '.join(cards))
    print('end lines (model):', ' / '.join(end[-8:]))
    print('line-mode text after the game:', ' / '.join(l for l in lines if l)[:400])
    print("writes with the alarm bit (WCC X'04'):", [k for k, b in enumerate(live) if b[:1] and b[0] & 0x04])
    report(a, cards)
    return 0 if ok else 1


def report(a, cards):
    """The GP2 events of the replayed game (model state = what was on the screen)."""
    ai, n, _ = L.parse_config([a.cfg])
    g = L.Level(ai, n, a.play, a.start)
    print(f'start: LEVEL {g.level:02d} AI{g.ai} fruit {g.bk} {g.bv} lives {g.lives}')
    keep = ('power', 'fruit', 'fruiteat', 'fruitexp', 'xlife', 'death', 'clear', 'collide')

    def show(tag, extra=''):
        note = [e for e in g.log if e[0] in keep]
        if note or extra:
            print(f'{tag} P=({g.x:02d},{g.y:02d}) LV={g.level:02d} AI{g.ai} FR={g.fr:03d} BT={g.bt:03d} '
                  f'S={g.ascore:07d} V={g.lives} EV={g.evf} {extra}' + ' '.join(str(e) for e in note))
    if a.play == 'T':
        for k, u in enumerate(cards, 1):
            if u.upper() == 'Q':
                print(f'   Q after turn {k - 1}: QUIT')
                return
            g.log = []
            g.step(u.upper())
            show(f'T{k:03d}')
        return
    c = L.LevelRT(g)
    frz = 0
    for card in cards:
        for kind, d, ch in next(ref_rt.events([card])):
            if kind in ('MOV', 'PAU', 'RDR', 'INV'):
                c.rin(kind, d, ch)
            if kind == 'PAU':
                print(f'   input P -> {"PAUSE" if c.pause else "RESUME"} after quantum {c.q} (BT={g.bt:03d}, '
                      f'LV={g.level:02d}, S={g.ascore:07d})')
            if kind == 'RDR':
                print(f'   input PA2 -> full redraw of quantum {c.q + 1} (BT={g.bt:03d}, LV={g.level:02d})')
            if kind == 'QUI':
                print(f'   input Q after quantum {c.q}: QUIT')
                return
        if c.status() in ('PAUS', 'WAIT'):
            continue
        g.log = []
        c.rq()
        if c.kind == 'F':
            frz += 1
            continue
        if frz:
            print(f'   freeze: {frz} quanta (Q{c.q - frz:04d}-Q{c.q - 1:04d})')
            frz = 0
        show(f'Q{c.q:04d} K={c.kind}')


if __name__ == '__main__':
    sys.exit(main())
