#!/usr/bin/env python3
"""MVS-G8 (D43, docs/G8-RELEASE.md section 3.1): deterministic presentation cost per frame, from Hercules TSD dry-run
streams in build listings (the streams the tests match byte for byte against the independent models).
Each TSD run starts with its 'TSX FULL FIRST' line; runs are paired in order with the PARM='TSD...' cards echoed in
the same listing (the count must match). A frame after a 'TSX FULL ..' line is a full screen (Erase/Write), any
other frame an update (partial redraw, quantum write, keyboard restore or bell-only write). Profile = glyphs, scale,
redraw, canvas (the TSX SWITCH size, else 80x24), play, rules; runs are grouped by profile. '-' = PARM column absent
(the program default); a code not listed is printed raw.
Usage: g8_bench.py LISTING... [--md OUT.md]"""
import argparse
import re
import statistics
from collections import defaultdict
from pathlib import Path

GLY = {'G': 'GRAPHIC', 'B': 'BASE', 'C': 'CLASSIC', 'A': 'AUTO'}


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]


def runs_of(path):
    lines = Path(path).read_text(errors='replace').splitlines()
    parms = []
    for l in lines:
        m = re.search(r"PARM='(TSD[^']*)'", l)
        if m:
            parms.append(m.group(1))
    runs, cur = [], None
    for l in lines:
        if l.startswith('TSX FULL FIRST'):
            cur = {'size': '80x24', 'frames': [], 'full_next': True}
            runs.append(cur)
        elif cur is None:
            continue
        elif l.startswith('TSX SWITCH'):
            w, h = l.split()[3].split('X')
            cur['size'] = f'{int(w)}x{int(h)}'
        elif l.startswith('TSX FULL'):
            cur['full_next'] = True
        else:
            m = re.match(r'TSD FRAME LEN(\d{4})$', l)
            if m:
                cur['frames'].append((int(m.group(1)), cur['full_next']))
                cur['full_next'] = False
    assert len(parms) == len(runs), (path, len(parms), len(runs))
    for r, p in zip(runs, parms):
        p = p.ljust(25)
        r['profile'] = (GLY.get(p[15], p[15].strip() or '-'),
                        {'4': '4x2', '3': '3x2', 'N': 'no scale', 'A': 'AUTO', ' ': '-'}.get(p[16], p[16]),
                        {'P': 'partial', 'F': 'full'}.get(p[14], p[14]), r['size'],
                        {'R': 'REALTIME', 'T': 'TURN'}.get(p[18], 'TURN'), 'ARCADE' if p[20] == 'A' else 'CLASSIC')
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('listings', nargs='+')
    ap.add_argument('--md')
    a = ap.parse_args()
    groups = defaultdict(list)
    for f in a.listings:
        for r in runs_of(f):
            groups[r['profile']].append(r)
    hdr = ('| Glyphs | Scale | Redraw | Canvas | Play | Rules | Runs | Full screens: median / max bytes | '
           'Updates | Update bytes: median / p95 / max |')
    out = [hdr, '|' + '---|' * 10]
    for prof in sorted(groups):
        rs = groups[prof]
        full = [n for r in rs for n, f in r['frames'] if f]
        upd = [n for r in rs for n, f in r['frames'] if not f]
        u = f'{statistics.median(upd):.0f} / {pct(upd, 95)} / {max(upd)}' if upd else '-'
        out.append('| ' + ' | '.join(prof) + f' | {len(rs)} | {statistics.median(full):.0f} / {max(full)} | '
                   f'{len(upd)} | {u} |')
    text = '\n'.join(out) + '\n'
    print(text, end='')
    if a.md:
        Path(a.md).write_text(text)


if __name__ == '__main__':
    main()
