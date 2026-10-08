#!/usr/bin/env python3
"""Timeline of a PACMAN TSC run in a c3270 -trace file, from the game's first full screen (F1/F5 + C3 + SBA(1,1) + RA clear prefix)
on: host->terminal records (time, length, WCC, kind: TICK = WCC C2, PART = C3 short, FULL = with the clear prefix) and terminal->host
records shown ONLY by their AID byte (no typed data, nothing from before the game, so nothing of the logon)."""
import re
import sys

CLEAR = bytes.fromhex('114040' '3c404000')


def events(path):
    ev, cur, ts, d = [], None, '', None
    for line in open(path, errors='replace'):
        m = re.match(r'^(\d{8}\.\d{6}\.\d{3}) ', line)
        if m:
            ts = m.group(1)[9:]
        m = re.match(r'^([<>]) 0x([0-9a-f]+)\s+([0-9a-f]+)', line)
        if m:
            if int(m.group(2), 16) == 0:
                if cur is not None:
                    ev.append((d, start_ts, bytes(cur)))
                cur, d, start_ts = bytearray(), m.group(1), ts
            cur += bytes.fromhex(m.group(3))
            continue
        if cur is not None:
            ev.append((d, start_ts, bytes(cur)))
            cur = None
    return ev


ev = events(sys.argv[1])
GAME = bytes.fromhex('c3') + CLEAR + bytes.fromhex('1140401d60')
i0 = next(i for i, (d, _, b) in enumerate(ev) if d == '<' and b[1:1 + len(GAME)] == GAME)
for d, ts, b in ev[i0:]:
    b = b[:-2] if b.endswith(b'\xff\xef') else b
    if d == '>':
        print(f'{ts}  IN   AID={b[0]:02X}')
        continue
    kind = 'FULL' if b[2:9] == CLEAR else 'TICK' if b[1] == 0xC2 else 'PART' if b[1] == 0xC3 else '----'
    print(f'{ts}  OUT  {kind} len {len(b):4} {b[:14].hex(" ")}')
    if kind == '----' and b[0] == 0xF5:
        break
