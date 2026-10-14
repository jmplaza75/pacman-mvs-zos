#!/usr/bin/env python3
"""Run-by-run equivalence of a z/OS job with the frozen 2.0-MVS-MAX oracle (ZOS-2; plan sec. 13, level L3).

Usage: zos_equiv.py SPOOLDIR ORACLE.json.gz --map PACMAIN=PACZ2D [--map ...] [--skip STEP ...] [--subset]
                   [--clock STEP]
--subset: the job runs a deterministic subset of the oracle's run steps (ZOS-2 chunks): the oracle run steps absent
from the job are not compared (counted), every run step of the job must exist in the oracle, in oracle order.
--clock STEP: that step is the PACTSOT clock driver; its lines carry real elapsed times, so it is checked with the
rules of tests/test_rt.py (21 TSOT lines, RC 0 and 0..30 ms late for the 20 deadlines, 120..180 ms apart, last line LA
RC 4 at most 30 ms later) instead of an exact comparison.

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


def clock_ok(lines):
    """tests/test_rt.py RT3 rules for the PACTSOT driver output."""
    import re
    m = [re.match(r'TSOT (\S\S) DL= *(-?\d+) NOW= *(-?\d+) RC= *(-?\d+)', l) for l in lines if l.startswith('TSOT ')]
    if len(m) != 21 or not all(m) or len(lines) != 21:
        return False
    rows = [(x.group(1), int(x.group(2)), int(x.group(3)), int(x.group(4))) for x in m]
    return (all(rc == 0 and 0 <= now - dl <= 30 for _, dl, now, rc in rows[:20])
            and all(120 <= b[2] - a[2] <= 180 for a, b in zip(rows, rows[1:20]))
            and rows[20][0] == 'LA' and rows[20][3] == 4 and rows[20][2] - rows[19][2] <= 30)


def compare(oracle, runs, pmap, skip=(), subset=False, clock=()):
    stream, msgs, bad = oracle['stream'], [], 0
    present = [s for s in runs if runs[s]['pgm'] in pmap.values()]
    known = [s for s, p, _ in oracle['steps'] if p in pmap]
    extra = [s for s in present if s not in known]
    if extra:
        msgs.append(f'FAIL run steps not in the oracle: {extra}')
        bad += 1
    nsub = 0
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
        if z is None and subset:
            nsub += 1
            gap_ok = True
            continue
        if z is None:
            msgs.append(f'FAIL {step}: missing in the z/OS job')
            bad += 1
            continue
        if z['pgm'] != pmap[opgm] or z['rc'] != orc or z['extra']:
            msgs.append(f'FAIL {step}: z/OS {z["pgm"]} RC {z["rc"]} extra {z["extra"]} / oracle {opgm} RC {orc}')
            bad += 1
        block = z['lines']
        if step in clock:
            # the clock lines: same position rule, content checked by the RT3 rules (real elapsed times)
            cands = [p for p in range(cur, len(stream) - 1) if stream[p:p + 2] == SEP and stream[p + 2:p + 3]
                     and stream[p + 2].startswith('TSOT ')] if gap_ok else [cur]
            p = cands[0] if cands else None
            ok = p is not None and stream[p:p + 2] == SEP and clock_ok(block) and clock_ok(stream[p + 2:p + 2 + len(block)])
            msgs.append(f'{"OK  " if ok else "FAIL"} {step}: clock driver, {len(block)} lines, RT3 timing rules')
            bad += not ok
            if ok:
                cur, gap_ok = p + 2 + len(block), False
            continue
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
    if subset:
        msgs.append(f'SUBSET {nsub} oracle run steps not in this job (not compared)')
    elif not gap_ok and cur != len(stream):
        msgs.append(f'FAIL tail: {len(stream) - cur} oracle lines after the last run and no step to own them')
        bad += 1
    return bad, msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spool', type=Path)
    ap.add_argument('oracle', type=Path)
    ap.add_argument('--map', action='append', required=True, help='MVSPGM=ZOSPGM')
    ap.add_argument('--skip', action='append', default=[])
    ap.add_argument('--subset', action='store_true')
    ap.add_argument('--clock', action='append', default=[])
    a = ap.parse_args()
    pmap = dict(m.split('=', 1) for m in a.map)
    oracle = json.load(gzip.open(a.oracle))
    job, _, runs = zos_runs(a.spool)
    bad, msgs = compare(oracle, runs, pmap, set(a.skip), a.subset, set(a.clock))
    print('\n'.join(msgs))
    n = sum(m.startswith('OK') for m in msgs)
    print(f'{job["jobname"]} {job["jobid"]} vs oracle JOB {oracle["job"]}: {n} runs identical, {bad} failures -> '
          + ('PASS' if not bad else 'FAIL'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
