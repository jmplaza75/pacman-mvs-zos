#!/usr/bin/env python3
"""ZOS-3 PACZ3TD1..4 check: the minimum ALARM(PATTERN) TSD set (S2T runs of oracle JOB 308, tools/zowe/zos_target.py
CHUNKS Z3TSD1..4). Read-only.

Usage: zos_tsd_check.py SPOOLDIR --job N        (exit 0 only if everything passes)
1. spool health as tools/zowe/zos_classic_check.py (PACZ2D, COND CODE 0000, only SYSOUT, STEPLIB once per step, no
   CEE / abend / IEA995 / $HASP375 text); the steps are exactly the chunk's;
2. oracle: every step against its own oracle 308 block (zos_equiv --subset: step identity + ordinal; exact text, the
   hexadecimal stream lines included - only the ASA column and the record padding are removed);
3. model: the TSD streams parsed from the SYSOUT (tests/test_s2.py tsd_streams: 'TSD FRAME LENnnnn' + hex records,
   length checked) = the tests/ref_s2.py pattern streams of tests/test_s2.py model() byte for byte - every WCC, every
   alarm bit X'04', every bell-only write C6 28 00 00 - then the end lines = the model's, and nothing after them.
"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path.insert(0, str(HERE))
from zos_classic_check import health  # noqa: E402
from zos_equiv import compare  # noqa: E402
import zos_s2_model as SM  # noqa: E402
from zos_target import CHUNKS  # noqa: E402

ORACLE = R / 'tests/oracle20/308-PACBLDS2.json.gz'


def model_check(step, lines):
    """(ok, text) of one S2T step's SYSOUT against the model."""
    ns = SM.model()
    pat, end, _ = SM.expected(step)
    try:
        streams, j = ns['tsd_streams'](lines, 0)
    except (AssertionError, IndexError, ValueError) as e:
        return False, f'{step}: TSD stream not parseable ({e.__class__.__name__})'
    ends = lines[j:j + len(end)]
    ok = streams == pat and ends == end and j + len(end) == len(lines)
    nal = sum(1 for f in streams if f[0] & 0x04)
    nend = len(streams) - len(ns['model'](SM.expected(step)[2])[3].kinds)   # writes after the last modelled screen
    first = next((k for k, (a, b) in enumerate(zip(streams, pat)) if a != b), None)
    return ok, (f'{step}: {len(streams)} / {len(pat)} streams = ref_s2 pattern model byte for byte '
                f'({nal} with the alarm bit, {nend} end bell-only writes), end lines {ends == end}'
                + ('' if ok else f' - first differing stream {first}, nothing after the end: {j + len(end) == len(lines)}'))


def main():
    a = sys.argv[1:]
    d, n = a[0], int(a[a.index('--job') + 1])
    job_name, _, steps_want, _, _ = CHUNKS[f'Z3TSD{n}']
    job, steps, runs, hb, lines = health(d)
    print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}: {len(steps)} steps, {lines} spool lines')
    bad = len(hb)
    for b in hb:
        print('  FAIL', b)
    ok = steps == steps_want and job['jobname'] == job_name
    print(f'  {"OK  " if ok else "FAIL"} steps {" ".join(steps_want)}')
    bad += not ok
    nb, msgs = compare(json.load(gzip.open(ORACLE)), runs, {'PACMAIN': 'PACZ2D'}, subset=True)
    for m in msgs:
        if not m.startswith('SUBSET'):
            print('  oracle 308', m)
    bad += nb
    for s in steps:
        ok, text = model_check(s, runs[s]['lines'])
        print(f'  model  {"OK  " if ok else "FAIL"} {text}')
        bad += not ok
    print(f'PACZ3TD{n} CHECK ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
