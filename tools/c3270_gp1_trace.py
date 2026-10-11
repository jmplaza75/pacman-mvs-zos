#!/usr/bin/env python3
"""MVS-GP1 GP1.4 live acceptance: an ARCADE REALTIME game (120x27, RULES(ARCADE)) in a c3270 -trace file, from the
game start (the first host record with the EBCDIC title 'P A C - M A N   A R C A D E' after --from) to the line-mode end.
Nothing before the game start is read (no logon); inbound records are used only by their AID (and, for ENTER, the
one typed game command).
1. The inputs of every quantum are rebuilt from the AIDs between the host writes (arrows PF7/8/10/11 = U D L R, PF9 =
   pause, PA2 = redraw, ENTER = its command) as one card per quantum (tests/ref_rt.py card rules); an AID that arrived
   just before a write may belong to the next quantum: both assignments are tried.
2. The cards are replayed through the independent ARCADE model (tests/ref_arcade.py + the screen models, PARM config
   AI/GHOSTS, SOUND bells as S1) and every live host write is compared with the model stream byte for byte.
3. On a match, the model state of every quantum is what the terminal showed: the report lists the ARCADE events
   (power pellets, fright start / warning / end with running quanta, frightened and normal ghost moves per quantum,
   ghosts eaten with points, eyes and revival, pause intervals with the fright timer before / after, PA2 redraws,
   alarm writes) and the end lines.
Usage: c3270_gp1_trace.py TRACE --cfg 'AI0 2' [--from HHMMSS] [--sound Y|N]"""
import argparse
import itertools
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tools'))
sys.path.insert(0, str(R / 'tests'))
from c3270_rt_trace import load, ms  # noqa: E402
import ref_arcade as A  # noqa: E402
import ref_rt  # noqa: E402
from ref_snap import Log  # noqa: E402

TITLE = 'P A C - M A N   A R C A D E'.encode('cp037')
ARROW = {0xF7: 'U', 0xF8: 'D', 0x7A: 'L', 0x7B: 'R'}
END_WORDS = ('WIN', 'LOST', 'QUIT', 'EOF')


def host(b):
    b = b[:-2] if b.endswith(b'\xff\xef') else b
    return b.replace(b'\xff\xff', b'\xff')


def bells(frames, log, sound):
    """The S1 bell rule (tests/test_s1.py), as in tests/test_gp1.py."""
    if sound != 'Y':
        return list(frames)
    last, won, out = None, False, []

    def ring(snap):
        nonlocal last, won
        lv, w = snap
        b = last is None or lv < last or (w and not won)
        won, last = won or w, lv
        return b
    for f, snap in zip(frames, log):
        out.append(bytes([f[0] | 0x04]) + f[1:] if ring(snap) else f)
    if ring(log.state()):
        out.append(bytes([0xC6, 0x28, 0x00, 0x00]))
    return out


def command(inb):
    """The game command of an inbound record (AID + cursor [+ SBA + typed field])."""
    aid = inb[0]
    if aid in ARROW:
        return ARROW[aid]
    if aid == 0xF9:
        return 'P'
    if aid == 0x6E:
        return '*'
    if aid == 0x7D:
        data = inb[6:] if len(inb) > 6 and inb[3] == 0x11 else b''
        text = data.decode('cp037', 'replace').strip()
        return text[:1] if text else '.'
    return None


def cards_for(writes, aids, shift):
    """One card per write after the first screen; AID i goes to the write after it, or (shift[i]) to the next one."""
    slots = {}
    for i, (t, cmd) in enumerate(aids):
        k = next(j for j, (tw, _) in enumerate(writes) if tw >= t)
        slots.setdefault(min(k + shift[i], len(writes) - 1), []).append(cmd)
    return [''.join(slots.get(k, [])) or '.' for k in range(1, len(writes))]


def model(cfg, cards, sound):
    log = Log()
    end, fs = ref_rt.tsd([cfg] + cards, 'W', snap=log, mk_game=lambda a, n: A.Arcade(a, n, 'R'),
                         mk_ctl=A.ArcadeRT)
    return end, bells(fs, log, sound)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('trace')
    ap.add_argument('--cfg', default='AI1 1')
    ap.add_argument('--from', dest='frm', default='000000')
    ap.add_argument('--sound', default='Y')
    a = ap.parse_args()
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
    # the game writes: the first screen .. the end banner / bell-only write (line mode follows)
    best = None
    near = [i for i, (t, _) in enumerate(aids)
            if any(0 <= tw - t < 60 for tw, _ in gw)]
    for combo in itertools.product((0, 1), repeat=min(len(near), 10)):
        shift = [0] * len(aids)
        for i, s in zip(near, combo):
            shift[i] = s
        cards = cards_for(gw, aids, shift)
        while cards and cards[-1] == '.':
            cards.pop()
        end, fs = model(a.cfg, cards, a.sound)
        live = [b[1:] for _, b in gw]
        same = sum(1 for p, q in zip(live, fs) if p == q)
        if best is None or same > best[0]:
            best = (same, cards, end, fs, live)
        if same == len(live) == len(fs):
            break
    same, cards, end, fs, live = best
    print(f'game writes: live {len(live)}, model {len(fs)}, identical {same}')
    print('cards (one per quantum after the first screen):', ' '.join(cards))
    bad = [k for k, (p, q) in enumerate(zip(live, fs)) if p != q]
    print('first difference at write', bad[0] if bad else '-', '| ALL IDENTICAL' if same == len(live) == len(fs) else '')
    print('end lines (model):', ' / '.join(end[-6:]))
    print('line-mode text after the game:', ' / '.join(l for l in lines if l)[:400])
    alarms = [k for k, b in enumerate(live) if b[0] & 0x04]
    print('writes with the alarm bit (WCC X\'04\'):', alarms)
    report(a.cfg, cards)


def report(cfg, cards):
    """The ARCADE events of the replayed game, quantum by quantum (model state = what was on the screen)."""
    ai, n, _ = A.parse_config([cfg])
    g = A.Arcade(ai, n, 'R')
    c = A.ArcadeRT(g)
    prev = None
    q_frz = 0
    for card in cards:
        evs = next(ref_rt.events([card]))
        for kind, d, ch in evs:
            if kind in ('MOV', 'PAU', 'RDR', 'INV'):
                c.rin(kind, d, ch)
            if kind == 'PAU':
                print(f'   input P -> {"PAUSE" if c.pause else "RESUME"} (quantum {c.q}, FR={g.fr:03d})')
            if kind == 'RDR':
                print(f'   input PA2 -> full redraw of quantum {c.q + 1}')
            if kind == 'QUI':
                print(f'   input Q at quantum {c.q}: QUIT')
                return
        if c.status() in ('PAUS', 'WAIT'):
            continue
        pos0 = [tuple(x[:2]) for x in g.gh]
        modes0 = list(g.mode[:n])
        g.log = []
        c.rq()
        moved = ''.join('M' if tuple(g.gh[i][:2]) != pos0[i] and modes0[i] == g.mode[i] else '.' for i in range(n))
        st = (g.fr, tuple(g.mode[:n]))
        note = [e for e in g.log if e[0] in ('power', 'collide', 'revive', 'defer', 'fend', 'death')]
        if note or st != prev or c.kind == 'F' and q_frz == 0:
            print(f'Q{c.q:04d} K={c.kind} P=({g.x:02d},{g.y:02d}) FR={g.fr:03d}{" WARN" if g.warning() else "     "} '
                  f'FA={g.facc} modes={"".join(g.mode[:n])} moved={moved} S={g.ascore:07d} V={g.lives} '
                  + ' '.join(str(e) for e in note))
        elif g.fr and 'F' in g.mode[:n]:
            print(f'Q{c.q:04d}   FR={g.fr:03d} FA={g.facc} moved={moved}')
        q_frz = 1 if c.kind == 'F' else 0
        prev = st


if __name__ == '__main__':
    main()
