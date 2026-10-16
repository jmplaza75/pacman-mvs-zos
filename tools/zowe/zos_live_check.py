#!/usr/bin/env python3
"""ZOS-4 live acceptance postcheck (docs/zos4-live-acceptance.md): compare the c3270 clipboard captures E1..E10 with the
expected milestone screens taken from the frozen models (tests/expected/MVS6-DIE1.txt, MVS6-LOST0.txt). Local, read-only.

Usage: zos_live_check.py DIR      (DIR holds E1.txt .. E10.txt, plain text copied from the c3270 window)
Rule (user, 2026-10-16): each expected line is compared exactly through its last nonblank character; a capture line
may lack trailing blanks or carry trailing blanks; internal spaces, case, values, line order and frame content must be
exact; no other normalisation. Each expected milestone block must appear in its capture as consecutive lines (the
screen may hold other lines around it: the typed input, ISPF lines). A `***` between a frame's T line and its prompt /
end lines is a FAIL; a `***` after the program has ended is allowed. Any PACMAN:, IKJnnnnn, CEEnnnn, IECnnnI or ABEND
text in a capture is a FAIL.
"""
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
P = 'CMD (U/D/L/R/Q)?'


def model(case):
    return (R / f'tests/expected/MVS6-{case}.txt').read_text().splitlines()


def frame(exp, k):
    t = [i for i, l in enumerate(exp) if re.match(r'T\d{3} ', l)]
    return exp[t[k]:t[k] + 11]


def expected():
    d, lo = model('DIE1'), model('LOST0')
    return {
        'E2': [d[0]] + frame(d, 0) + [P],
        'E3': frame(d, 24) + [P],
        'E4': frame(d, 28) + [P, 'Q'] + d[-4:],
        'E6': [lo[0]] + frame(lo, 0) + [P],
        'E7': frame(lo, 24) + [P],
        'E8': frame(lo, 48) + [P],
        'E9': frame(lo, 72) + lo[-4:],
    }


def contains(cap, want):
    cap = [l.rstrip() for l in cap]
    want = [l.rstrip() for l in want]
    return any(cap[i:i + len(want)] == want for i in range(len(cap) - len(want) + 1))


BAD = re.compile(r'PACMAN:|IKJ\d{5}|CEE\d{4}|IEC\d{3}I|ABEND')


def main():
    d = Path(sys.argv[1])
    bad = 0
    for n in [f'E{i}' for i in range(1, 11)]:
        f = d / f'{n}.txt'
        if not f.exists():
            print(f'  FAIL {n}: capture missing')
            bad += 1
            continue
        cap = f.read_text(errors='replace').splitlines()
        msgs = [l.strip() for l in cap if BAD.search(l)]
        ok = not msgs
        what = 'no PACMAN: / IKJ / CEE / IEC / ABEND text' + (f' - found {msgs}' if msgs else '')
        if n in expected():
            ok = ok and contains(cap, expected()[n])
            what = 'milestone screen exact (trailing blanks ignored) and ' + what
        print(f'  {"OK  " if ok else "FAIL"} {n}: {what}')
        bad += not ok
    print('ZOS-4 LIVE CHECK ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
