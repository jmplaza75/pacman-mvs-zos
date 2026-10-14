#!/usr/bin/env python3
"""Run-by-run equivalence of a z/OS job with the frozen 2.0-MVS-MAX oracle (ZOS-2; plan sec. 13, level L3).

Usage: zos_equiv.py SPOOLDIR ORACLE.json.gz --map PACMAIN=PACZ2D [--map ...] [--skip STEP ...]

Run steps are the oracle steps whose program is a --map key (the MVS load member); each must exist in the z/OS job
with the same step name, the mapped program and the same RC, unless named with --skip (reported as not compared).
The z/OS side of a run is its SYSOUT spool file: ASA column removed, trailing blanks removed (= the fixed-record
padding; the oracle lines are right-stripped the same way, D11). Nothing else is normalized: spaces inside a line,
case, numbers, line order, blank lines and the record split of a line longer than 120 characters all stay as printed.
Any other spool file of a run step (CEEDUMP, an LE message file, ...) is a failure.

The oracle stream is not attributed to steps (TK4- printed every SYSOUT dataset in one stream). The only framing it
holds between program outputs is the TK4- separator: exactly two empty lines before each non-empty SYSOUT dataset
(verified on the oracle jobs). So the z/OS runs are matched in step order: each non-empty run must equal the oracle
lines right after an exact two-line separator; consecutive run steps must be adjacent; oracle lines are skipped only
where the oracle has non-run steps (compile / link / utility listings) between two runs, before the first run or
after the last one. Exit 0 only if every run matches.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zos_listing import asa, steps_of  # noqa: E402

SEP = ['', '']


def zos_runs(d):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = sorted(json.loads((d / 'spool.json').read_text()), key=lambda f: f['id'])
    steps = steps_of(d, job['jobname'])
    out = {}
    for s, ps, pgm, rc in steps:
        mine = [f for f in files if f['stepname'] == s and (f.get('procstep') or None) == ps]
        lines, extra = None, []
        for f in mine:
            step = f['stepname'] + (f'.{f["procstep"]}' if f.get('procstep') else '')
            raw = (d / f'{f["id"]:03d}-{step}-{f["ddname"]}.txt').read_text().splitlines()
            if f['ddname'] == 'SYSOUT' and lines is None:
                lines = asa(raw) if 'A' in (f.get('recfm') or '') else [l.rstrip() for l in raw]
                long = [len(l) for l in raw if len(l.rstrip()) > ('A' in (f.get('recfm') or '')) + 119]
                if long:
                    print(f'  {s}: {len(long)} record(s) filled to column 120 (a longer line would be split)',
                          file=sys.stderr)
            else:
                extra.append(f['ddname'])
        out[s] = {'pgm': pgm, 'rc': rc, 'lines': lines or [], 'extra': extra}
    return job, [s for s, _, _, _ in steps], out


def first_diff(a, b):
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else '<missing>'
        y = b[i] if i < len(b) else '<missing>'
        if x != y:
            return i, x, y
    return None


def compare(oracle, runs, pmap, skip=()):
    stream, msgs, bad = oracle['stream'], [], 0
    cur, gap_ok = 0, True               # gap_ok: oracle lines may be skipped (non-run steps since the last run)
    for step, opgm, orc in oracle['steps']:
        if opgm not in pmap:
            gap_ok = True
            continue
        if step in skip:
            msgs.append(f'SKIP {step}: not compared (--skip)')
            gap_ok = True
            continue
        z = runs.get(step)
        if z is None:
            msgs.append(f'FAIL {step}: missing in the z/OS job')
            bad += 1
            continue
        if z['pgm'] != pmap[opgm] or z['rc'] != orc or z['extra']:
            msgs.append(f'FAIL {step}: z/OS {z["pgm"]} RC {z["rc"]} extra {z["extra"]} / oracle {opgm} RC {orc}')
            bad += 1
        block = z['lines']
        if not block:
            msgs.append(f'FAIL {step}: no SYSOUT output (every oracle run prints)')
            bad += 1
            gap_ok = True
            continue
        want = SEP + block
        cands = [cur] if not gap_ok else [p for p in range(cur, len(stream) - len(want) + 1)
                                          if stream[p:p + 2] == SEP and stream[p + 2] == block[0]]
        hit = next((p for p in cands if stream[p:p + len(want)] == want), None)
        if hit is None:
            p = cands[0] if cands else cur
            d = first_diff(want, stream[p:p + len(want)])
            msgs.append(f'FAIL {step}: {len(block)} lines; vs oracle at stream line {p}: first difference at block '
                        f'line {d[0] - 2}: z/OS {d[1]!r} / oracle {d[2]!r}')
            bad += 1
            gap_ok = True              # resynchronise on the next run
            continue
        msgs.append(f'OK   {step}: {len(block)} lines identical (oracle stream lines {hit + 2}-{hit + len(want) - 1})')
        cur, gap_ok = hit + len(want), False
    if not gap_ok and cur != len(stream):
        msgs.append(f'FAIL tail: {len(stream) - cur} oracle lines after the last run and no step to own them')
        bad += 1
    return bad, msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spool', type=Path)
    ap.add_argument('oracle', type=Path)
    ap.add_argument('--map', action='append', required=True, help='MVSPGM=ZOSPGM')
    ap.add_argument('--skip', action='append', default=[])
    a = ap.parse_args()
    pmap = dict(m.split('=', 1) for m in a.map)
    oracle = json.load(gzip.open(a.oracle))
    job, _, runs = zos_runs(a.spool)
    bad, msgs = compare(oracle, runs, pmap, set(a.skip))
    print('\n'.join(msgs))
    n = sum(m.startswith('OK') for m in msgs)
    print(f'{job["jobname"]} {job["jobid"]} vs oracle JOB {oracle["job"]}: {n} runs identical, {bad} failures -> '
          + ('PASS' if not bad else 'FAIL'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
