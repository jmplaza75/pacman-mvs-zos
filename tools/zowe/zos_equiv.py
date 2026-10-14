#!/usr/bin/env python3
"""Run-by-run equivalence of a z/OS job with the frozen 2.0-MVS-MAX oracle (ZOS-2; plan sec. 13, level L3).

Usage: zos_equiv.py SPOOLDIR ORACLE.json.gz --map PACMAIN=PACZ2D [--map ...] [--skip STEP ...] [--subset]
                   [--clock STEP]
--subset: the job runs a deterministic subset of the oracle's run steps (ZOS-2 chunks): the oracle run steps absent
from the job are not compared (counted), every run step of the job must exist in the oracle, in oracle order. Each
step is compared with its OWN oracle block, located from the oracle's step identity (anchors(): the exact step name
and its ordinal among the oracle's run steps; program and deck PARM only as consistency checks), never by searching
the stream for matching content, so executions with identical output (e.g. oracle 310 G2B46..G2B49) are told apart;
a step that cannot be anchored uniquely fails; the block must also end where the oracle's next dataset begins.
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
    names = [s for s, _, _, _ in steps]
    for s in {n for n in names if names.count(n) > 1}:      # a step name must identify one execution
        out[s]['extra'].append('DUPLICATED STEP NAME')
    return job, names, out


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


# first line of a run dataset per (program, TSD or not): used only to tell run datasets from the compiler / utility
# listings that share the oracle stream and as a consistency check of the anchoring, never to match a z/OS output
HEADS = {('PACMAIN', ''): ('PACMAN',), ('PACMAIN', 'TSD'): ('TSX',), ('PACQRYT', ''): ('QRY ',),
         ('PACTSOT', ''): ('TSOT ',)}
DECKS = Path(__file__).resolve().parent.parent.parent / 'releases/2.0-MVS-MAX/decks'


# Known run-dataset boundaries without the TK4- two-line separator, bound to one frozen oracle stream (SHA-256 of
# '\n'.join(stream)). Oracle 309 (RP): RPT1's SYSOUT follows the RPSEED IEBUPDTE listing after ONE empty line. An entry
# is used only if the oracle stream has exactly this digest and every recorded fact holds (empty line before, the
# preceding text line, the run header, not already a separator boundary, the anchored step name); otherwise nothing of
# that oracle is anchored. Other oracles never consult the table.
KNOWN_BOUNDARIES = {
    'a549c3f181981b9d4b52cb6517f664469490d5e0e9b57539f5a360e636b25621': [
        {'line': 662, 'step': 'RPT1', 'prev': 'IEB819I END OF JOB IEBUPDTE.', 'head': 'TSX SWITCH '}],
}


def anchors(oracle, progs):
    """{oracle run step name: index of the first line of its own block in the stream}.
    Identity = the exact oracle step name and its ordinal among the oracle's run steps (oracle['steps'] order, the
    programs in progs): the k-th run step owns the k-th run dataset of the stream (a block after the TK4- separator
    whose first line is a run header). Program and deck PARM are consistency checks only: the block's header must be
    the one of the step's program / mode; the first inconsistent step and every later one are left unanchored. If the
    stream holds a different number of run datasets than there are run steps, nothing is anchored (the mapping would
    not be unique). Unanchored steps fail explicitly in compare(); there is no fallback to a content search."""
    import re
    s = oracle['stream']
    parm = {}
    for b in re.split(r'(?m)^(?=//\w+\s+EXEC )', (DECKS / oracle['deck']).read_text())[1:]:
        m = re.search(r"PARM='([^']*)", '\n'.join(b.split('\n', 2)[:2]))
        parm[re.match(r'//(\w+)', b).group(1)] = m.group(1) if m else ''
    names = [st for st, _, _ in oracle['steps']]
    dup = {st for st in names if names.count(st) > 1}          # a duplicated name is never anchored
    heads = tuple(h for (prog, _), hs in HEADS.items() if prog in progs for h in hs)
    steps = [(st, p) for st, p, _ in oracle['steps'] if p in progs]
    blocks = [p + 2 for p in range(len(s) - 2) if s[p] == '' and s[p + 1] == '' and s[p + 2] != ''
              and (p == 0 or s[p - 1] != '') and s[p + 2].startswith(heads)]
    out = {}
    import hashlib
    known = KNOWN_BOUNDARIES.get(hashlib.sha256('\n'.join(s).encode()).hexdigest(), [])
    known = [k for k in known if k['head'].startswith(heads)]      # only entries of the requested run classes
    for k in known:
        n = k['line']
        if not (2 <= n < len(s) and s[n - 1] == '' and s[n - 2] == k['prev'] and s[n].startswith(k['head'])
                and n not in blocks):
            return out                                       # a recorded fact does not hold: fail closed
        blocks.append(n)
    blocks.sort()
    if len(blocks) != len(steps):
        return out
    pos = dict(zip(blocks, [st for st, _ in steps]))
    if any(pos.get(k['line']) != k['step'] for k in known):
        return out                                           # the boundary is not the declared step's: fail closed
    for (st, prog), b in zip(steps, blocks):
        want = HEADS.get((prog, 'TSD' if parm.get(st, '')[:3] == 'TSD' else ''))
        if not want or not s[b].startswith(want):
            break
        if st not in dup:
            out[st] = b
    return out


def ends_ok(oracle, anc, step, e):
    """The block ending before stream line e must end exactly where the oracle's next dataset begins: the next oracle
    step's own block (when it is an anchored run), else a separator, a page eject (one empty line, then text) or the
    end of the stream."""
    s, names = oracle['stream'], [x[0] for x in oracle['steps']]
    i = names.index(step)
    nxt = names[i + 1] if i + 1 < len(names) else None
    if nxt in anc:
        return e + 2 == anc[nxt]
    return e == len(s) or s[e:e + 2] == SEP or (s[e] == '' and e + 1 < len(s) and s[e + 1] != '')


def compare(oracle, runs, pmap, skip=(), subset=False, clock=()):
    stream, msgs, bad = oracle['stream'], [], 0
    present = [s for s in runs if runs[s]['pgm'] in pmap.values()]
    known = [s for s, p, _ in oracle['steps'] if p in pmap]
    extra = [s for s in present if s not in known]
    if extra:
        msgs.append(f'FAIL run steps not in the oracle: {extra}')
        bad += 1
    nsub = 0
    anc = anchors(oracle, set(pmap)) if subset else {}
    order = [st for st, _, _ in oracle['steps'] if st in present]
    if subset and order != present:
        msgs.append(f'FAIL run steps not in oracle order: {present}')
        bad += 1
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
            if subset:
                cands = [anc[step] - 2] if step in anc else []
            else:
                cands = [p for p in range(cur, len(stream) - 1) if stream[p:p + 2] == SEP and stream[p + 2:p + 3]
                         and stream[p + 2].startswith('TSOT ')] if gap_ok else [cur]
            p = cands[0] if cands else None
            ok = p is not None and stream[p:p + 2] == SEP and clock_ok(block) and clock_ok(stream[p + 2:p + 2 + len(block)])
            ok = ok and (not subset or ends_ok(oracle, anc, step, p + 2 + len(block)))
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
        if subset:                     # the step's own oracle block (anchors), never a content search
            if step not in anc:
                msgs.append(f'FAIL {step}: its oracle block cannot be anchored from the oracle metadata')
                bad += 1
                continue
            cands = [anc[step] - 2]
        else:
            cands = [cur] if not gap_ok else [p for p in range(cur, len(stream) - len(want) + 1)
                                              if stream[p:p + 2] == SEP and stream[p + 2] == block[0]]
        hit = next((p for p in cands if stream[p:p + len(want)] == want), None)
        if hit is not None and subset and not ends_ok(oracle, anc, step, hit + len(want)):
            msgs.append(f'FAIL {step}: {len(block)} lines match the start of its oracle block (stream line {hit + 2}) '
                        f'but the oracle block does not end there')
            bad += 1
            continue
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
