#!/usr/bin/env python3
"""MVS-G3 diagnostic: reads ONLY the given cells (default: the two probe cells, row 7 col 10 and row 7 col 20, 1-based) from the
presentation space of a running c3270 started with `-scriptport PORT`, every 0.25 s, and prints them with a timestamp. Nothing
else of the session is read. Game start cells (AI1, 1 ghost): Pac-Man 5,32 and ghost 12,49 -> --cells 5,32 12,49
Usage: sample_probe_cells.py [--port 4001] [--seconds 20] [--cells R,C ...]"""
import argparse
import subprocess
import time

ap = argparse.ArgumentParser()
ap.add_argument('--port', default='4001')
ap.add_argument('--seconds', type=float, default=20)
ap.add_argument('--cells', nargs='+', default=['7,10', '7,20'], help='1-based row,col')
ap.add_argument('--cursor', action='store_true', help='also read the cursor position (Query(Cursor), 0-based row col)')
a = ap.parse_args()
CELLS = tuple((int(r) - 1, int(c) - 1) for r, c in (x.split(',') for x in a.cells))   # Ascii() is 0-origin


def cell(r, c):
    out = subprocess.run(['x3270if', '-t', a.port, f'Ascii({r},{c},1)'], capture_output=True, text=True, timeout=5)
    return out.stdout.strip() if out.returncode == 0 else f'ERR({out.stderr.strip()[:40]})'


t0, prev = time.time(), None
while time.time() - t0 < a.seconds:
    now = tuple(cell(r, c) for r, c in CELLS)
    if a.cursor:
        q = subprocess.run(['x3270if', '-t', a.port, 'Query(Cursor)'], capture_output=True, text=True, timeout=5)
        now += (q.stdout.strip() if q.returncode == 0 else 'ERR',)
    mark = '' if now == prev else '  <- change'
    cells = ' '.join(f'r{r + 1}c{c + 1}={v!r}' for (r, c), v in zip(CELLS, now))
    if a.cursor:
        cells += f' cursor0={now[-1]!r}'
    print(f'{time.time() - t0:6.2f}s  {cells}{mark}', flush=True)
    prev = now
    time.sleep(0.25)
