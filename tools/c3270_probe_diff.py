#!/usr/bin/env python3
"""Compares the 3270 writes received by c3270 in two trace files, from the probe's first full screen (the E6 screen:
WCC C3 then SBA row 2 col 2 'G3 PROBE E6') to its last partial (SBA row 7 col 10). Usage: c3270_probe_diff.py A.txt B.txt"""
import sys
from c3270_trace import records

START = bytes.fromhex("c311c1d1")                                  # WCC C3 + SBA(2,2)
PART = bytes.fromhex('c311c7e9')                                # WCC C3 + SBA(7,10)


def probe_window(path):
    recs = [(s, ts, b[:-2] if b.endswith(b'\xff\xef') else b) for s, ts, b in records(path)]
    first = next(i for i, (_, _, b) in enumerate(recs) if b[1:5] == START)
    last = max(i for i, (_, _, b) in enumerate(recs) if b[1:5] == PART)
    return recs[first:last + 1]


a, b = probe_window(sys.argv[1]), probe_window(sys.argv[2])
print(f'A: {len(a)} records, B: {len(b)} records')
for k in range(max(len(a), len(b))):
    ra, rb = (a[k] if k < len(a) else None), (b[k] if k < len(b) else None)
    if ra and rb and ra[2] == rb[2]:
        print(f'{k:2} same  len {len(ra[2]):4}  A {ra[1]}  B {rb[1]}  {ra[2][:12].hex(" ")}')
        continue
    print(f'{k:2} DIFF  A: {ra and (ra[1], len(ra[2]), ra[2][:40].hex(" "))}\n          B: {rb and (rb[1], len(rb[2]), rb[2][:40].hex(" "))}')
    if ra and rb:
        x, y = ra[2], rb[2]
        j = next((i for i in range(min(len(x), len(y))) if x[i] != y[i]), min(len(x), len(y)))
        print(f'          first different byte at offset {j}')
    break
