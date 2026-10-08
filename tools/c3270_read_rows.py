#!/usr/bin/env python3
"""MVS-G4: reads rows of the presentation space of a running c3270 started with `-scriptport PORT` (x3270if Ascii) and
prints them as the terminal renders them (UTF-8). Use it ONLY while a probe/game screen is shown (nothing of the logon).
Usage: c3270_read_rows.py [--port 4001] [--rows 1-23] [--out FILE]"""
import argparse
import subprocess

ap = argparse.ArgumentParser()
ap.add_argument('--port', default='4001')
ap.add_argument('--rows', default='1-23', help='1-based inclusive range')
ap.add_argument('--out')
a = ap.parse_args()
r1, r2 = (int(x) for x in a.rows.split('-'))
out = subprocess.run(['x3270if', '-t', a.port, f'Ascii({r1 - 1},0,{r2 - r1 + 1},80)'],
                     capture_output=True, text=True, timeout=10)
if out.returncode != 0:
    raise SystemExit(f'x3270if failed: {out.stderr.strip()}')
lines = [f'{r1 + i:02d}|{t.rstrip()}' for i, t in enumerate(out.stdout.splitlines())]
text = '\n'.join(lines) + '\n'
print(text, end='')
if a.out:
    open(a.out, 'w', encoding='utf-8').write(text)
