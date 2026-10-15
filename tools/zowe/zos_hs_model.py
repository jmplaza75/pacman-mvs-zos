#!/usr/bin/env python3
"""ZOS-3 HS reference: the independent model of tests/test_hs.py (sections 1-2: source checks, then model_runs with
tests/ref_hs.py + tests/ref_gp2.py), executed verbatim from the frozen file with PACMAN_LATER_PHASE=G8 exactly as
tests/test_g8.py ran it for the 2.0-MVS-MAX HS oracle (JOB 312). Nothing of test_hs.py is copied or edited: its text is
cut at the '# 3. the Hercules listings' header (section 3 needs a Hercules listing) and run in a namespace.

model() -> namespace with RUNS [(step, kind, base, hs lines)], PDS (ref_hs.Pds after every run, HTSO included),
           rp_streams(kind), tsd_run(lines, j, nend), HS_RUNS, HS_TSO, HS_PRINT, H (ref_hs), L (ref_gp2).
expected_text(step) -> the exact SYSOUT lines of a text run (BAT / REALTIME / CLASSIC / HTSO): base + HS lines.
states() -> [(step, {member: records} of HSTEST before, after), ...] and the HSFULL member set, step by step.
"""
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
_NS = {}


def model():
    if _NS:
        return _NS
    src = (R / 'tests/test_hs.py').read_text()
    cut = src.index('# 3. the Hercules listings')
    old_env, old_argv = os.environ.get('PACMAN_LATER_PHASE'), sys.argv
    os.environ['PACMAN_LATER_PHASE'] = 'G8'
    sys.argv = [str(R / 'tests/test_hs.py')]
    for p in (str(R / 'tests'), str(R / 'tools')):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        ns = {'__file__': str(R / 'tests/test_hs.py'), '__name__': 'test_hs_model'}
        exec(compile(src[:cut], str(R / 'tests/test_hs.py'), 'exec'), ns)
    finally:
        sys.argv = old_argv
        if old_env is None:
            os.environ.pop('PACMAN_LATER_PHASE', None)
        else:
            os.environ['PACMAN_LATER_PHASE'] = old_env
    _NS.update(ns)
    return _NS


def expected_text(step):
    ns = model()
    for st, kind, base, hs in ns['RUNS']:
        if st == step:
            assert base is not None, f'{step} is a TSD run'
            return [l.rstrip() for l in base] + hs
    raise KeyError(step)


def states(skip=()):
    """Replay ref_hs step by step: (step, HSTEST before, HSTEST after, HSFULL after, hs lines). Steps in skip (the
    deferred HA6) are not run; each must leave both PDSs unchanged in the full replay, else the skip is refused."""
    if skip:
        full_run = {st: (b, a) for st, b, a, _, _ in states()}
        assert all(full_run[s][0] == full_run[s][1] for s in skip), f'{skip}: a skipped step changes the state'
    ns = model()
    H, L = ns['H'], ns['L']
    pds = H.Pds({'HS9': [H.record(9999999, 99)], 'BAD': ['XYZZY NOT A SCORE', 'SECOND JUNK RECORD'], 'EMPTY': []})
    full = H.Pds(full=True)
    out = []
    finals = {st: (kind, base) for st, kind, base, _ in ns['RUNS']}
    for step, kind, d, c, st, ddk in ns['HS_RUNS']:
        if step in skip:
            continue
        before = {k: list(v) for k, v in pds.members.items()}
        start = L.parse_start(st)
        base = finals[step][1]
        if kind == 'C':
            hs = H.end_lines(pds, ('M', ddk[2:]), 0, 0, 1, arcade=False)
        else:
            score, level = H.final(base) if base else ns['TSD_FINAL'][kind]
            store = full if ddk.startswith('F:') else pds
            dd = ('M', ddk[2:]) if ddk[:2] in ('M:', 'F:') else ddk
            hs = H.end_lines(store, dd, score, level, start)
        out.append((step, before, {k: list(v) for k, v in pds.members.items()}, sorted(full.members), hs))
    for i, (c, st, m) in enumerate(ns['HS_TSO'], 1):
        before = {k: list(v) for k, v in pds.members.items()}
        base = finals[f'HTSO{i}'][1]
        hs = H.end_lines(pds, ('M', m), *H.final(base), L.parse_start(st))
        out.append((f'HTSO{i}', before, {k: list(v) for k, v in pds.members.items()}, sorted(full.members), hs))
    assert pds.members == ns['PDS'].members, 'replay differs from test_hs model_runs'
    return out


if __name__ == '__main__':
    for step, before, after, full, hs in states():
        ch = {k: after[k][0][:20] for k in after if before.get(k) != after[k]}
        print(f'{step:<6} {" / ".join(hs) or "(no HS line)":<60} {ch or "no change"}')
