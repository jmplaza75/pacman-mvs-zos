#!/usr/bin/env python3
"""Extracts the host->terminal 3270 records from a c3270 -trace file: (line, timestamp, bytes)."""
import re
import sys


def records(path):
    out, cur, ts, start = [], None, '', 0
    for n, line in enumerate(open(path, errors='replace'), 1):
        m = re.match(r'^(\d{8}\.\d{6}\.\d{3}) ', line)
        if m:
            ts = m.group(1)
        m = re.match(r'^< 0x([0-9a-f]+)\s+([0-9a-f]+)', line)
        if not m:
            if cur is not None:
                out.append((start, ts, bytes(cur)))
                cur = None
            continue
        if int(m.group(1), 16) == 0:
            if cur is not None:
                out.append((start, ts, bytes(cur)))
            cur, start = bytearray(), n
        cur += bytes.fromhex(m.group(2))
    if cur is not None:
        out.append((start, ts, bytes(cur)))
    return out


if __name__ == '__main__':
    for start, ts, b in records(sys.argv[1]):
        print(start, ts, len(b), b[:24].hex(' '))
