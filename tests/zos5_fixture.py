#!/usr/bin/env python3
"""ZOS-5: a synthetic c3270 trace of the designed live session (docs/zos5-design.md) for tools/zowe/zos5_live_check.py:
run from the ISPF Command Shell (option 6: each game ends with the end lines, ISPF's ***, ENTER and the shell panel);
games A (MOVES, 120 x 27 from the IBM-DYNAMIC reply), B (TSORDR, CLEAR + PA2 redraw), C (TSORDR, COLOR(YES), 80 x 24),
the game writes = tests/ref_gx_screen.py for the cards (with idle ticks), every record framed as TN3270E 3270-DATA
(5-byte header, IAC doubling, IAC EOR) and written as c3270 trace lines (`< 0x..` / `> 0x..`, 32 bytes per line, large
host records split over two socket reads, the switch and the query in one read).
  python3 tests/zos5_fixture.py            writes tests/fixtures/zos5/session.trace
session(**opts) returns the records [(direction, ms, header, payload)]; render(records) the trace text; the test
mutates the records."""
import os
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
import qry_cases as Q  # noqa: E402
import ref_gx_screen as gx  # noqa: E402

CLRPFX = bytes.fromhex('1140403C404000')
TSO_CLEAR = bytes.fromhex('7EC111F2E71D4011404013')
QUERY = bytes.fromhex('F3000501FF02')
OUT = R / 'tests/fixtures/zos5/session.trace'
CARDS_A = ['+', '+', 'R', 'R', 'U', '+', 'L', 'L', 'L', 'D', 'D', 'R', 'X', 'r', 'R', 'R', '+', 'D', 'Q']
CARDS_BC = ['R', '', 'D', 'Q']
EXEC = "EXEC 'Z00000.PACMAN.CLIST(PACMAN)' '{}'"
KW_AB = 'RULES(CLASSIC) PLAY(TURN) SOUND(NO)'
KW_C = 'COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC) RULES(CLASSIC) PLAY(TURN) SOUND(NO)'
SHELL_PANEL = (bytes([0x7E, 0xC3, 0x11, 0x40, 0x40]) + 'Menu  List  Mode  Functions  Utilities  Help'.encode('cp037')
               + bytes([0x11, 0xC1, 0x5D]) + 'ISPF Command Shell'.encode('cp037') + bytes([0x11, 0xC2, 0x60])
               + 'Enter TSO or Workstation commands below:'.encode('cp037') + bytes([0x11, 0x4A, 0x40]) + b'\x7e\x7e\x7e\x6e')


def e(s):
    return s.encode('cp037')


def enter(text):
    return bytes([0x7D, 0x5B, 0x6F]) + (bytes([0x11, 0x5B, 0x60]) + e(text) if text else b'')


def frames(cards, canvas, prof=(1, 1, 1)):
    with tempfile.TemporaryDirectory() as t:
        (Path(t) / 'FX.txt').write_text('\n'.join(cards) + '\n')
        return gx.frames('FX', prof[1] == 1, True, 'P', 'G' if prof[2] else 'C', '4', canvas,
                         d=os.path.relpath(t, R / 'tests'))


def line(text):
    return bytes([0xF1, 0xC3, 0x11, 0x40, 0x40]) + e(text)


def session(reply=None, canvas='W', cards_a=None, b_redraw='CLEAR+PA2', c_redraw='ENTER', games='ABC', tso_clear=False):
    reply = reply if reply is not None else Q.rec('dyn')
    recs, t = [], [36000000]

    def host(p, dt=40):
        t[0] += dt
        recs.append(['<', t[0], 'H', p])

    def term(p, dt=900):
        t[0] += dt
        recs.append(['>', t[0], 'T', p])

    def play(kw, cmd, cards, canv, redraw):
        term(enter(EXEC.format(kw)), 2000)
        host(bytes([cmd, 0xC3]))
        if cmd == 0x7E:
            host(QUERY, 1)
            term(reply, 30)
        fs = frames(cards, canv)
        host(bytes([0xF1]) + fs[0][:1] + CLRPFX + fs[0][1:], 60)
        full = 0x7E if cmd == 0x7E else 0xF5
        for f, c in zip(fs[1:], cards):
            if c == '+':
                host(bytes([0xF1]) + f, 500)
                continue
            if c == '':
                if redraw == 'CLEAR+PA2':
                    term(b'\x6D')
                    if tso_clear:
                        host(TSO_CLEAR)                                 # z/OS TSO / VTAM answer to CLEAR (live T2)
                    term(b'\x6E')
                elif redraw == 'PA2':
                    term(b'\x6E')
                else:
                    term(enter(''))
            else:
                term(enter(c))
            host(bytes([full if c == '' or c.upper() == 'Q' else 0xF1]) + f)
        host(line('QUIT'), 3000)
        end = {'MOVES': ['TURNS 013', 'SCORE 0080'], 'TSORDR': ['TURNS 002', 'SCORE 0010']}
        for s in end['MOVES' if len(cards) > 6 else 'TSORDR'] + ['LIVES 3', '***']:
            host(line(s), 5)
        term(enter(''), 1500)                                         # ENTER at ISPF's ***
        host(SHELL_PANEL, 60)                                         # back in the ISPF Command Shell (option 6)

    if 'A' in games:
        play(KW_AB, 0x7E, cards_a or CARDS_A, canvas, None)
    if 'B' in games:
        play(KW_AB, 0x7E, CARDS_BC, canvas, b_redraw)
    if 'C' in games:
        play(KW_C, 0xF5, CARDS_BC, 'D', c_redraw)
    seq = 0
    for r in recs:
        if r[0] == '<':
            r[2] = bytes([0, 0, 0]) + seq.to_bytes(2, 'big')
            seq = (seq + 1) % 65536
        else:
            r[2] = bytes(5)
    return recs


def wire(r):
    return (r[2] + r[3]).replace(b'\xff', b'\xff\xff') + b'\xff\xef'


def stamp(ms):
    s, m = divmod(ms, 1000)
    return f'20261017.{s // 3600:02d}{s // 60 % 60:02d}{s % 60:02d}.{m:03d}'


def dump(d, b):
    return [f'{d} 0x{k:<4x}{b[k:k + 32].hex()}' for k in range(0, len(b), 32)]


def render(recs, raw=None, funcs=None):
    """Trace text; raw: optional list of (direction, ms, bytes) blocks used instead of the framed records; funcs: the
    TN3270E functions to show as negotiated (FUNCTIONS IS) in the TELNET state replay (default: none, as before)."""
    out = ['20261017.095959.000 infra  Trace started (synthetic ZOS-5 fixture)', ' TELNET state:',
           '< 0x0   fffd28fffa2802044942' + '4d2d44594e414d4943fff0']
    if funcs is not None:
        out.append('< 0x0   fffa280304' + bytes(funcs).hex() + 'fff0')
    out.append(' Screen contents (TN3270E-3270) unformatted:')
    out += dump('<', bytes(5) + b'\x05\x02' + e('ISPF Command Shell') + bytes(40))
    out.append(' Data stream:')
    blocks = raw
    if blocks is None:
        blocks, k = [], 0
        while k < len(recs):
            d, ms, w = recs[k][0], recs[k][1], wire(recs[k])
            if d == '<' and recs[k][3][:1] in (b'\x7e', b'\xf5') and len(recs[k][3]) == 2 and k + 1 < len(recs) \
                    and recs[k + 1][3] == QUERY:
                blocks.append((d, ms, w + wire(recs[k + 1])))          # switch + query in one socket read
                k += 2
                continue
            if d == '<' and len(w) > 1000:
                blocks += [(d, ms, w[:700]), (d, ms + 1, w[700:])]     # one record over two reads
            else:
                blocks.append((d, ms, w))
            k += 1
    for d, ms, b in blocks:
        out.append(f'{stamp(ms)} socket Host socket read complete nr={len(b)}' if d == '<' else
                   f'{stamp(ms)} tn3270 SENT TN3270E(3270-DATA NO-RESPONSE 0)')
        out += dump(d, b)
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(session()))
    print(f'{OUT.relative_to(R)} written')
