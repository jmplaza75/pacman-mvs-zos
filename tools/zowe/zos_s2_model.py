#!/usr/bin/env python3
"""ZOS-3 S2 reference: the independent alarm-pattern model of tests/test_s2.py (tests/ref_s2.py over the screen models),
executed verbatim from the frozen file: its import header and its section 2 ('# 2. the model' up to section 3), which
builds the model of every S2T run and asserts the D41 rules and the 21 documented edges (D12). Section 1 (source pins
against tag mvs-rp) is not run: on branch zos the Z1 COPY delta is a known, guarded difference (tests/zos_c2.py);
section 3 needs a Hercules listing. Nothing of test_s2.py is copied or edited.

model() -> namespace: runs [(run, pattern streams, end lines)] in S2_TSD order, model(run), tsd_streams(lines, j),
           EDGES, S (ref_s2), S2_TSD.
coverage() -> {S2T<i>: set of edges} - the edges each run reaches, by the frozen coverage code run on that run alone.
"""
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
_NS = {}
_COV = {}


def _parts():
    src = (R / 'tests/test_s2.py').read_text()
    head = src[:src.index('# 1. sources')] + src[src.index('# 2. the model'):src.index('runs, cov = [], set()')]
    loop = src[src.index('runs, cov = [], set()'):src.index('missing = [e for e in EDGES')]
    rest = src[src.index('missing = [e for e in EDGES'):src.index('# 3. the Hercules listing')]
    tail = src[src.index('# 3. the Hercules listing'):src.index('def listing_check(')]
    return head, loop, rest, tail


def _exec(code, ns, name):
    old_argv = sys.argv
    sys.argv = [str(R / 'tests/test_s2.py')]
    for p in (str(R / 'tests'), str(R / 'tools')):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        exec(compile(code, name, 'exec'), ns)
    finally:
        sys.argv = old_argv


def model():
    if _NS:
        return _NS
    head, loop, rest, tail = _parts()
    old = os.environ.get('PACMAN_LATER_PHASE')
    ns = {'__file__': str(R / 'tests/test_s2.py'), '__name__': 'test_s2_model'}
    _exec(head + loop + rest + tail, ns, str(R / 'tests/test_s2.py'))
    if old is None:
        os.environ.pop('PACMAN_LATER_PHASE', None)
    _NS.update(ns)
    return _NS


def coverage():
    if _COV:
        return _COV
    ns = model()
    _, loop, _, _ = _parts()
    for i, run in enumerate(ns['S2_TSD'], 1):
        n = dict(ns)
        n['S2_TSD'] = [run]
        _exec(loop, n, 'test_s2 coverage loop')
        _COV[f'S2T{i}'] = set(n['cov'])
    return _COV


def expected(step):
    """(pattern streams, end lines, run) of S2T<i>."""
    ns = model()
    run, pat, end = ns['runs'][int(step[3:]) - 1]
    return pat, end, run


if __name__ == '__main__':
    for k, v in coverage().items():
        print(k, sorted(v))
