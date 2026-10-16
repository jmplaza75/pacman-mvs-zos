#!/usr/bin/env python3
"""ZOS-5 live full-screen acceptance postcheck (docs/zos5-design.md, docs/zos5-live-session.md). Local, read-only.

Usage: zos5_live_check.py TRACE [--reply-out FILE]                    one trace holding games A, B and C
       zos5_live_check.py --a LABEL=TRACE --bc LABEL=TRACE [--reply-out FILE]
                          composite acceptance (ZOS-5 final, docs/evidence/zos5-fullscreen.md): A from the --a trace
                          (exactly one game), B and C from the --bc A / B / C session (CONTENTION-RESOLUTION
                          negotiated); the first game of the --bc trace is never counted as A
TRACE = the c3270 trace started in the ISPF Command Shell (option 6; x3270if Trace(On,...)) and stopped there after
game C. Nothing earlier exists in it; inbound typed text is used only inside the games (the game commands).

1. Framing (fail closed): the host->terminal and terminal->host bytes of the `< 0x..` / `> 0x..` hex lines are
   reassembled per direction into telnet records (IAC EOR ends a record, IAC IAC = one X'FF'). Between records only
   the keep-alive IAC DO / WILL / WONT TIMING-MARK and IAC NOP are accepted (reported); any other telnet command, a
   record split by one, bytes after the last EOR, or bytes before the first record = FAIL.
   Every record carries the 5-byte TN3270E header (RFC 2355): DATA-TYPE, REQUEST-FLAG, RESPONSE-FLAG, SEQ-NUMBER.
   In RFC 2355 core, REQUEST-FLAG has meaning only for DATA-TYPE REQUEST (8.1.2: ignored otherwise, senders SHOULD set
   X'00'). The TN3270E CONTENTION-RESOLUTION function (05) redefines it as a bit mask: on host 3270-DATA X'01' SDI,
   X'02' KRI; on BID X'04' SIGNAL. ZOS-5 validates the negotiated subset actually observed (live trace T2, z/OS
   FUNCTIONS IS 00 02 04 05), nothing more. The negotiated functions are read from the ' TELNET state:' replay at the
   start of the trace (the last FUNCTIONS IS).
   Host: DATA-TYPE X'00' (3270-DATA): RESPONSE-FLAG X'00' / X'01' / X'02', a non-empty payload; with
   CONTENTION-RESOLUTION negotiated REQUEST-FLAG only X'00' / X'01' SDI / X'02' KRI / X'03' SDI + KRI (any other bit =
   FAIL), without it REQUEST-FLAG ignored (RFC 2355 core). DATA-TYPE X'09' (BID, a TN3270E control record, never
   3270 data): only with CONTENTION-RESOLUTION negotiated and exactly REQUEST-FLAG X'00' (SIGNAL BID X'04' not
   accepted: not observed), RESPONSE-FLAG X'02', no payload; it must be answered by exactly X'02' X'00' X'00' + its
   SEQ-NUMBER + payload X'00'. Any other host DATA-TYPE = FAIL. Host SEQ-NUMBER all zero or +1 per record (mod
   65536), BIDs included. Terminal: 3270-DATA (REQUEST-FLAG X'00', RESPONSE-FLAG X'00', SEQ-NUMBER all zero or +1 per
   record) or RESPONSE (X'02', RESPONSE-FLAG X'00' with payload X'00' = positive, answering an outstanding host record
   that asked for a response; X'01' negative = FAIL); every host record with ALWAYS-RESPONSE (X'02') must be answered.
   Shorter than 5 bytes, any other value = FAIL. Only then the 3270 payload is passed on.
2. Games: a game starts at the host record `7E C3` or `F5 C3` (PACPLAT's data-free size switch) and ends at the next one
   / the end of the trace. Exactly three, in order: A and B `7E C3` then the Read Partition Query `F3 00 05 01 FF 02`
   then exactly one inbound record before the first screen: the Query Reply (AID X'88', tests/qry_cases.valid); C
   `F5 C3` and no query. The reply gives the profile (qry_cases.expect: colour, highlight, GE) and the canvas
   (qry_cases.expect_size), resolved as PACPLAT does (HILITE / GLYPHS / SCALE AUTO); nothing is assumed.
3. Cards: after the first screen every host write is either an idle tick (X'F1' + WCC X'C2': card `+`) or the answer
   to the oldest pending AID: ENTER = its typed command (empty = redraw), PA2 = redraw; CLEAR is not delivered to the
   program (recorded; B's redraw must be CLEAR then PA2, C's an empty ENTER); any other AID = FAIL. z/OS TSO / VTAM
   answers CLEAR itself with one write (live trace T2: `7E C1 11 F2 E7 1D 40 11 40 40 13`, Erase/Write Alternate,
   WCC C1, SBA(27,120), SF, SBA(1,1), IC): exactly that record, at most once, only in game B between its CLEAR and
   the following PA2, is classified as external CLEAR handling - not a PACMAN write, no card, no model frame; zero is
   also valid; anywhere else, twice or any other bytes = the usual FAIL. The cards without
   `+` and redraws must equal the frozen case (MOVES / TSORDR / TSORDR) up to its Q, the redraws where the case has them.
4. Model: tests/ref_gx_screen.py frames for the rebuilt cards and the resolved profile (= oracle 310 TSD45 / TSD48 /
   TSD28 when no tick was seen); write 0 = X'F1' or X'F5' + WCC + PACFSIO's clear prefix + the rest; a redraw and the
   end screen = the canvas command (X'7E' A / B, X'F5' C) + frame; moves / invalid / ticks = X'F1' + frame; byte for
   byte. Then line mode: the frozen block's end lines in order, then the ISPF Command Shell panel (the shell boundary,
   docs/zos5-live-session.md: the games run from ISPF option 6, as in ZOS-4). `***` is accepted only after the end
   lines (ISPF's own prompt once the program has ended), never in the game stream or before the end lines; IKJ / IEC /
   IGZ / CEE / ABEND / PACMAN: text in any host record of the data stream = FAIL.
5. Report: SHA-256 of the trace, framing summary, per game the reply (also written with --reply-out), the profile and
   canvas, writes / ticks / AIDs, D28 (ticks before the first AID or not), the end pause (end screen -> first
   line-mode record), and an audit: no LOGON / PASSWORD text in the trace's host records, and inbound records outside
   the games shown by AID and length only.
Verdict: PASS (as designed: profile (1, 1, 1), canvas 120 x 27 for A / B), MODEL-IDENTICAL-OTHER-PROFILE (exit 2: the
writes equal the model of another profile / canvas; the wide-layout acceptance stays open for review) or FAIL (exit 1).
"""
import argparse
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(R / 'tests'))
import qry_cases as Q  # noqa: E402
import ref_gx_screen as gx  # noqa: E402

IAC, EOR, SB, SE, NOP = 0xFF, 0xEF, 0xFA, 0xF0, 0xF1
DO, DONT, WILL, WONT, TM = 0xFD, 0xFE, 0xFB, 0xFC, 0x06
QUERY = bytes.fromhex('F3000501FF02')
CLRPFX = bytes.fromhex('1140403C404000')
SIZES = {v: k for k, v in gx.CANVASES.items()}
SIZES[(80, 24)] = 'D'
GAMES = [('A', 'MOVES', 0x7E, 'TSD45'), ('B', 'TSORDR', 0x7E, 'TSD48'), ('C', 'TSORDR', 0xF5, 'TSD28')]
END_LINES = {'MOVES': ['QUIT', 'TURNS 013', 'SCORE 0080', 'LIVES 3'],
             'TSORDR': ['QUIT', 'TURNS 002', 'SCORE 0010', 'LIVES 3']}     # oracle 310 TSD45 / TSD48 / TSD28
BAD_TEXT = re.compile(r'IKJ\d{5}|IEC\d{3}|IGZ\d{4}|CEE\d{4}|ABEND|PACMAN:|\*\*\*')
SHELL = 'ISPF Command Shell'           # the option 6 panel title: the boundary after each game
TSO_CLEAR = bytes.fromhex('7EC111F2E71D4011404013')   # z/OS TSO / VTAM write answering CLEAR (live trace T2)
AIDN = {0x7D: 'ENTER', 0x6E: 'PA2', 0x6D: 'CLEAR', 0x6C: 'PA1', 0x88: 'QREPLY'}


class Fail(Exception):
    pass


def blocks(text):
    """(direction, time, bytes) per trace data block, and the text of the start-of-trace dumps.
    A Trace(On) during a session (c3270 / s3270 4.5, seen on a local fake TN3270E host 2026-10-16) first writes
    ' TELNET state:' and ' Screen contents (...):' with synthetic `<` dumps (no TN3270E framing, no EOR), then
    ' Data stream:'. Only blocks after that marker are data: a host block must directly follow
    'Host socket read complete nr=N' with exactly N bytes; terminal blocks are the `> 0x..` dumps of what was sent."""
    out, ts, started, prev, snap = [], '', False, '', bytearray()
    for line in text.splitlines():
        if line.strip() == 'Data stream:':
            started = True
            continue
        m = re.match(r'^(\d{8}\.\d{6}\.\d{3}) ', line)
        if m:
            ts = m.group(1)
        h = re.match(r'^([<>]) 0x([0-9a-f]+)\s+([0-9a-f]+)\s*$', line)
        if not h:
            if line.strip():
                prev = line
            continue
        b = bytes.fromhex(h.group(3))
        if not started:
            snap += b
            continue
        if int(h.group(2), 16) == 0:
            if h.group(1) == '<':
                nr = re.search(r'Host socket read complete nr=(\d+)$', prev)
                if not nr:
                    raise Fail(f'host data block without a socket read line ({ts})')
                out.append(['<', ts, bytearray(), int(nr.group(1))])
            else:
                out.append(['>', ts, bytearray(), None])
        elif not out or out[-1][0] != h.group(1):
            raise Fail(f'continuation line without its block ({ts})')
        out[-1][2] += b
    if not started:
        raise Fail("no ' Data stream:' marker: the trace was not started with Trace(On) during the session")
    for d, t, b, nr in out:
        if nr is not None and nr != len(b):
            raise Fail(f'host block of {len(b)} bytes, socket read nr={nr} ({t})')
    return [(d, t, bytes(b)) for d, t, b, _ in out], bytes(snap)


def telnet(bl):
    """Records per direction: [(order, direction, time, record bytes)], keep-alives counted; fail closed."""
    state = {'<': bytearray(), '>': bytearray()}
    recs, keep = [], 0
    for n, (d, ts, b) in enumerate(bl):
        cur, i = state[d], 0
        while i < len(b):
            c = b[i]
            if c != IAC:
                cur.append(c)
                i += 1
                continue
            if i + 1 >= len(b):
                raise Fail(f'IAC at the end of a trace block ({d} {ts})')
            c2 = b[i + 1]
            if c2 == IAC:
                cur.append(IAC)
                i += 2
            elif c2 == EOR:
                recs.append((n, d, ts, bytes(cur)))
                cur.clear()
                i += 2
            elif c2 in (DO, DONT, WILL, WONT) and i + 2 < len(b) and b[i + 2] == TM and not cur:
                keep += 1
                i += 3
            elif c2 == NOP and not cur:
                keep += 1
                i += 2
            else:
                raise Fail(f'unexpected telnet command IAC {c2:02X} ({d} {ts})')
    for d, cur in state.items():
        if cur:
            raise Fail(f'{len(cur)} bytes after the last EOR ({d}): truncated record')
    return recs, keep


def seq_ok(seqs):
    return all(s == 0 for s in seqs) or all(b == (a + 1) % 65536 for a, b in zip(seqs, seqs[1:]))


def functions(text):
    """The TN3270E functions negotiated (the last FUNCTIONS IS in the ' TELNET state:' replay), as a set of codes."""
    if ' TELNET state:' not in text or ' Screen contents' not in text:
        return set()
    part = text[text.index(' TELNET state:'):text.index(' Screen contents')]
    b = bytes.fromhex(''.join(re.findall(r'^< 0x[0-9a-f]+\s+([0-9a-f]+)\s*$', part, re.M)))
    fis = re.findall(rb'\xff\xfa\x28\x03\x04(.*?)\xff\xf0', b, re.S)
    return set(fis[-1]) if fis else set()


CR = 0x05                                # TN3270E function CONTENTION-RESOLUTION


def tn3270e(recs, funcs=frozenset()):
    """Validate the TN3270E headers; [(order, direction, time, payload)] of the 3270-DATA records."""
    out, hseq, iseq, pending = [], [], [], {}
    cr = CR in funcs
    for n, d, ts, r in recs:
        if len(r) < 5:
            raise Fail(f'record of {len(r)} bytes: no TN3270E header ({d} {ts})')
        dt, rq, rs, sq, p = r[0], r[1], r[2], int.from_bytes(r[3:5], 'big'), r[5:]
        if d == '<' and dt == 0x09:
            if not cr or rq != 0x00 or rs != 0x02 or p:
                raise Fail(f'host BID {r.hex()} not a normal BID under negotiated CONTENTION-RESOLUTION ({ts})')
            hseq.append(sq)
            pending[sq] = 'BID'
        elif d == '<':
            if dt != 0x00 or rs not in (0x00, 0x01, 0x02) or not p or (cr and rq & ~0x03):
                raise Fail(f'host record header {r[:5].hex()} not 3270-DATA with valid flags ({ts})')
            hseq.append(sq)
            if rs:
                pending[sq] = rs
            out.append((n, d, ts, p))
        elif dt == 0x00:
            if rq or rs or not p:
                raise Fail(f'terminal record header {r[:5].hex()} not plain 3270-DATA ({ts})')
            iseq.append(sq)
            out.append((n, d, ts, p))
        elif dt == 0x02:
            if rs != 0x00 or p != b'\x00' or sq not in pending or (pending[sq] == 'BID' and rq):
                raise Fail(f'terminal RESPONSE {r.hex()} not a positive answer to an outstanding request ({ts})')
            del pending[sq]
        else:
            raise Fail(f'terminal record DATA-TYPE {dt:02X} ({ts})')
    if not seq_ok(hseq) or not seq_ok(iseq):
        raise Fail('SEQ-NUMBER neither all zero nor +1 per record')
    if any(v in (0x02, 'BID') for v in pending.values()):
        raise Fail('host record with ALWAYS-RESPONSE (or a BID) never answered')
    return out, ('+1' if any(hseq) else 'zero')


def texts(p):
    """EBCDIC text segments of a 3270 write (orders removed)."""
    seg, out, i = bytearray(), [], 2
    skip = {0x11: 3, 0x1D: 2, 0x28: 3, 0x3C: 4, 0x12: 3, 0x13: 1, 0x05: 1, 0x08: 2}
    while i < len(p):
        c = p[i]
        if c in skip or c == 0x29:
            if seg:
                out.append(seg.decode('cp037', 'replace'))
            seg = bytearray()
            i += 2 + 2 * p[i + 1] if c == 0x29 and i + 1 < len(p) else skip[c] if c in skip else 2
            continue
        seg.append(c)
        i += 1
    if seg:
        out.append(seg.decode('cp037', 'replace'))
    return [s.strip() for s in out if s.strip()]


def typed(p):
    data = p[6:] if len(p) > 6 and p[3] == 0x11 else b''
    return data.decode('cp037', 'replace').strip()


def frozen_cards(case):
    lines = (R / f'tests/cases/{case}.txt').read_text().splitlines()
    _, _, cards = gx.parse_config(lines)
    out = []
    for c in cards:
        out.append(c.strip())
        if c.strip()[:1].upper() == 'Q':
            break
    return out


def model(cards, prof, canvas):
    with tempfile.TemporaryDirectory(dir=R / 'build' if (R / 'build').is_dir() else None) as t:
        (Path(t) / 'LIVE.txt').write_text('\n'.join(cards) + '\n')
        d = os.path.relpath(t, R / 'tests')
        c, h, g = prof
        return gx.frames('LIVE', h == 1, True, 'P', 'G' if g else 'C', '4', canvas, d=d)


def game(name, case, cmd, ev, res):
    """Check one game; returns (profile, size) or raises Fail."""
    host = [e for e in ev if e[1] == '<']
    if host[0][3] != bytes([cmd, 0xC3]):
        raise Fail(f'{name}: first record {host[0][3][:2].hex()} is not the size switch {cmd:02X} C3')
    i = 1
    reply = None
    if cmd == 0x7E:
        if host[1][3] != QUERY:
            raise Fail(f'{name}: no Read Partition Query after the switch')
        k1, k2 = ev.index(host[1]), ev.index(host[2])
        inb = [e for e in ev[k1:k2] if e[1] == '>']
        if len(inb) != 1 or inb[0][3][:1] != b'\x88':
            raise Fail(f'{name}: {len(inb)} inbound records between the query and the first screen (one reply expected)')
        reply = inb[0][3]
        if not Q.valid(reply):
            raise Fail(f'{name}: the Query Reply is not structurally valid (PACQRY D40 rule)')
        prof, size = Q.expect(reply), Q.expect_size(reply)
        if prof[0] != 1:
            raise Fail(f'{name}: the reply announces no colour: the game falls back to line mode')
        if size[0] > 170:
            raise Fail(f'{name}: buffer {size} wider than 170: line-mode fallback')
        i = 2
    else:
        if any(e[3] == QUERY for e in host) or any(e[3][:1] == b'\x88' for e in ev if e[1] == '>'):
            raise Fail(f'{name}: a query / reply in the forced COLOR(YES) game')
        prof, size = (1, 1, 1), (80, 24)
    canvas = SIZES.get(size)
    if canvas is None:
        raise Fail(f'{name}: canvas {size} has no model layout')
    first = ev.index(host[i])
    writes, pend, cards, kinds, aids, clear_before, ticks_before_aid = [], [], [], [], [], False, None
    n_first, tso_clear = None, 0
    for e in ev[first:]:
        if e[1] == '>':
            aid = e[3][0]
            aids.append(AIDN.get(aid, f'{aid:02X}'))
            if aid == 0x6D:
                clear_before = True
            elif aid in (0x7D, 0x6E):
                pend.append(('' if aid == 0x6E else typed(e[3]), aid, clear_before))
                clear_before = False
                if ticks_before_aid is None:
                    ticks_before_aid = cards.count('+')
            else:
                raise Fail(f'{name}: unexpected AID {aid:02X}')
            continue
        if name == 'B' and clear_before and e[3] == TSO_CLEAR and not tso_clear:
            tso_clear += 1                               # external CLEAR handling (CLEAR -> PA2 in B only)
            continue
        writes.append(e)
        if n_first is None:
            n_first = e
            continue
        p = e[3]
        if p[0] == 0xF1 and len(p) > 1 and p[1] == 0xC2:
            cards.append('+')
            kinds.append(('tick', None, False))
            continue
        if not pend:
            raise Fail(f'{name}: a host write with no pending input')
        text, aid, clr = pend.pop(0)
        cards.append(text)
        kinds.append(('redraw' if text == '' else 'cmd', aid, clr))
        if text[:1].upper() == 'Q':
            break                                        # the end screen; line mode follows
    game_w = writes
    plain = [c for c in cards if c != '+']
    want = frozen_cards(case)
    if [c for c in plain] != want:
        raise Fail(f'{name}: typed cards {plain} are not the frozen {case} cards {want}')
    for (k, aid, clr), c in zip(kinds, cards):
        if k == 'redraw' and name == 'B' and not (aid == 0x6E and clr):
            raise Fail('B: the redraw was not CLEAR then PA2')
        if k == 'redraw' and name == 'C' and aid != 0x7D:
            raise Fail('C: the redraw was not an empty ENTER')
    fs = model(cards, prof, canvas)
    if len(fs) != len(game_w):
        raise Fail(f'{name}: {len(game_w)} game writes, model {len(fs)}')
    full_cmd = 0x7E if cmd == 0x7E else 0xF5
    for j, (w, f) in enumerate(zip(game_w, fs)):
        p = w[3]
        if j == 0:
            ok = p[0] in (0xF1, 0xF5) and p[1:] == f[:1] + CLRPFX + f[1:]
        else:
            k = kinds[j - 1][0]
            last = j == len(fs) - 1
            need = full_cmd if (k == 'redraw' or last) else 0xF1
            ok = p[0] == need and p[1:] == f
        if not ok:
            raise Fail(f'{name}: write {j} differs from the model ({len(p) - 1} / {len(f)} bytes)')
    end_t = game_w[-1][2]
    rest = ev[ev.index(game_w[-1]) + 1:]
    for e in ev[:ev.index(game_w[-1]) + 1]:
        m = e[1] == '<' and BAD_TEXT.search(' '.join(texts(e[3])))
        if m:
            raise Fail(f'{name}: error / *** text in the game stream: {m.group(0)}')
    exp, k, shell = END_LINES[case], 0, False
    for e in rest:
        if e[1] != '<':
            continue
        segs = texts(e[3])
        for s in segs:
            m = BAD_TEXT.search(s)
            if m and not (m.group(0) == '***' and k == len(exp)):
                raise Fail(f'{name}: error / *** text after the end screen: {m.group(0)}')
            if k < len(exp) and s == exp[k]:
                k += 1
        if k == len(exp) and any(SHELL in s for s in segs):
            shell = True
            break
    if not shell:
        raise Fail(f'{name}: end lines {exp} + the {SHELL} panel not found in line mode after the end screen')
    line_t = next((e[2] for e in rest if e[1] == '<'), '')
    res.update(name=name, profile=prof, size=size, canvas=canvas, writes=len(game_w), ticks=cards.count('+'),
               aids=aids, d28=('ticks before the first input' if ticks_before_aid else
                               'no tick before the first input (held or none)'),
               pause=ms(line_t) - ms(end_t) if line_t else None, reply=reply, tso_clear=tso_clear,
               cards=len([c for c in cards if c != '+']))
    return prof, size


def ms(ts):
    h, m, s = int(ts[9:11]), int(ts[11:13]), float(ts[13:])
    return round((h * 3600 + m * 60 + s) * 1000)


def parse(text):
    """Framing, negotiated functions, game starts and the audit of one trace (fail closed)."""
    bl, snap = blocks(text)
    recs, keep = telnet(bl)
    funcs = functions(text)
    ev, rule = tn3270e(recs, funcs)
    starts = [k for k, e in enumerate(ev) if e[1] == '<' and len(e[3]) == 2 and e[3][0] in (0x7E, 0xF5) and e[3][1] == 0xC3]
    if any(re.search(r'LOGON|PASSW', ' '.join(texts(e[3]))) for e in ev if e[1] == '<'):
        raise Fail('audit: LOGON / PASSWORD text in a host record of the data stream')
    words = re.findall(r'[A-Z0-9#@$.]{4,}', snap.replace(b'\x00', b'\x40').decode('cp037', 'replace'))
    snap_flags = sorted({w for w in words if re.search(r'LOGON|PASSW|IKJ567', w)})
    return {'records': len(recs), 'keepalive': keep, 'seq': rule, 'funcs': sorted(funcs), 'ev': ev, 'starts': starts,
            'snapshot': len(snap), 'snap_flags': snap_flags}


def outside_errors(ev):
    for e in ev:                                         # shell traffic outside the games: errors still fail
        m = e[1] == '<' and BAD_TEXT.search(' '.join(texts(e[3])))
        if m and m.group(0) != '***':
            raise Fail(f'error text in a host record outside the game stream: {m.group(0)}')


def designed(r):
    return r['cmd'] != 0x7E or (r['profile'] == (1, 1, 1) and r['size'] == (120, 27))


def run_game(g, ev, a, b, source):
    name, case, cmd, block = g
    r = {'block': block, 'source': source, 'cmd': cmd}
    game(name, case, cmd, ev[a:b], r)
    return r


def check(text):
    t = parse(text)
    ev, starts = t['ev'], t['starts']
    if len(starts) != 3:
        raise Fail(f'{len(starts)} games found (A, B, C expected)')
    outside = [(AIDN.get(e[3][0], f'{e[3][0]:02X}'), len(e[3])) for e in ev[:starts[0]] if e[1] == '>']
    results = [run_game(g, ev, a, b, 'trace') for g, a, b in zip(GAMES, starts, starts[1:] + [len(ev)])]
    outside_errors(ev)
    return {'records': t['records'], 'keepalive': t['keepalive'], 'seq': t['seq'], 'games': results, 'outside': outside,
            'snapshot': t['snapshot'], 'snap_flags': t['snap_flags'],
            'verdict': 'PASS' if all(designed(r) for r in results) else 'MODEL-IDENTICAL-OTHER-PROFILE'}


def check_composite(text_a, text_bc, la='A source', lbc='B/C source'):
    """Composite acceptance (ZOS-5 final): game A from a trace holding exactly one game (A, frozen MOVES / TSD45, closed
    through the ISPF Command Shell); games B and C from one trace holding the whole A / B / C session with
    CONTENTION-RESOLUTION negotiated - B the second game (TSD48, the scoped TSO CLEAR write), C the third (TSD28). The
    first game of the B/C source is NOT validated and never counts as A."""
    ta = parse(text_a)
    if len(ta['starts']) != 1:
        raise Fail(f'{la}: {len(ta["starts"])} games found (exactly one A game expected)')
    ra = run_game(GAMES[0], ta['ev'], ta['starts'][0], len(ta['ev']), la)
    outside_errors(ta['ev'])
    tb = parse(text_bc)
    if CR not in tb['funcs']:
        raise Fail(f'{lbc}: CONTENTION-RESOLUTION not negotiated')
    if len(tb['starts']) != 3:
        raise Fail(f'{lbc}: {len(tb["starts"])} games found (the A / B / C session expected)')
    s = tb['starts']
    rb = run_game(GAMES[1], tb['ev'], s[1], s[2], lbc)
    rc = run_game(GAMES[2], tb['ev'], s[2], len(tb['ev']), lbc)
    outside_errors(tb['ev'])
    res = [ra, rb, rc]
    return {'sources': {la: ta, lbc: tb}, 'games': res,
            'verdict': 'PASS' if all(designed(r) for r in res) else 'MODEL-IDENTICAL-OTHER-PROFILE'}


def reply_hex(rp):
    """A recorded Query Reply as stored in tests/qreply_*.hex: upper-case hexadecimal, one line, final newline."""
    return rp.hex().upper() + '\n'


def game_line(g):
    rp = g['reply']
    return (f'game {g["name"]} ({g["block"]}) from {g["source"]}: profile colour/highlight/GE {g["profile"]}, canvas '
            f'{g["size"]} ({g["canvas"]}), {g["writes"]} writes = model, {g["ticks"]} ticks, {g["cards"]} commands, AIDs '
            f'{g["aids"]}, TSO CLEAR writes {g["tso_clear"]}, D28: {g["d28"]}, end pause {g["pause"]} ms'
            + (f', reply {len(rp)} bytes{" = tests/qreply_dyn.hex" if rp == Q.rec("dyn") else " (differs from qreply_dyn)"}'
               if rp else ', no query (forced)'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('trace', nargs='?')
    ap.add_argument('--a', metavar='LABEL=TRACE', help='composite: the trace holding the accepted game A')
    ap.add_argument('--bc', metavar='LABEL=TRACE', help='composite: the A / B / C session trace for B and C')
    ap.add_argument('--reply-out')
    a = ap.parse_args()
    if a.trace and not (a.a or a.bc):
        raw = Path(a.trace).read_bytes()
        print(f'trace {a.trace} SHA-256 {hashlib.sha256(raw).hexdigest()} ({len(raw)} bytes)')
        try:
            rep = check(raw.decode('utf-8', 'replace'))
        except Fail as e:
            print(f'ZOS-5 LIVE CHECK FAIL: {e}')
            sys.exit(1)
        print(f'framing: {rep["records"]} TN3270E records, SEQ-NUMBER {rep["seq"]}, keep-alives {rep["keepalive"]}; '
              f'inbound before game A: {rep["outside"]}')
        print(f'audit: start-of-trace dumps {rep["snapshot"]} bytes (not data), words to review there: '
              f'{rep["snap_flags"] or "none"}; the raw trace is never committed')
        for g in rep['games']:
            print(game_line(g))
    elif a.a and a.bc and not a.trace:
        (la, pa), (lb, pb) = (x.split('=', 1) for x in (a.a, a.bc))
        raws = {la: Path(pa).read_bytes(), lb: Path(pb).read_bytes()}
        for lab, role in ((la, 'A'), (lb, 'B and C')):
            print(f'{lab} (source of {role}): SHA-256 {hashlib.sha256(raws[lab]).hexdigest()} ({len(raws[lab])} bytes)')
        try:
            rep = check_composite(raws[la].decode('utf-8', 'replace'), raws[lb].decode('utf-8', 'replace'), la, lb)
        except Fail as e:
            print(f'ZOS-5 LIVE CHECK FAIL: {e}')
            sys.exit(1)
        names = {0: 'BIND-IMAGE', 2: 'RESPONSES', 4: 'SYSREQ', 5: 'CONTENTION-RESOLUTION'}
        for lab, s in rep['sources'].items():
            print(f'{lab} framing: {s["records"]} TN3270E records, host SEQ-NUMBER {s["seq"]}, keep-alives '
                  f'{s["keepalive"]}, functions ' + ', '.join(f'{f:02X} {names.get(f, "?")}' for f in s['funcs'])
                  + f'; {len(s["starts"])} game(s); start-of-trace dump {s["snapshot"]} bytes, words to review: '
                  f'{s["snap_flags"] or "none"}')
        print(f'{lb}: its first game is not validated here and is not acceptance evidence for A')
        for g in rep['games']:
            print(game_line(g))
    else:
        ap.error('either TRACE, or --a LABEL=TRACE and --bc LABEL=TRACE')
    if a.reply_out:
        rp = next(g['reply'] for g in rep['games'] if g['reply'])
        Path(a.reply_out).write_text(reply_hex(rp))
        print(f'reply of game A written to {a.reply_out} (SHA-256 {hashlib.sha256(Path(a.reply_out).read_bytes()).hexdigest()})')
    print(f'ZOS-5 LIVE CHECK {rep["verdict"]}')
    sys.exit(0 if rep['verdict'] == 'PASS' else 2)


if __name__ == '__main__':
    main()
