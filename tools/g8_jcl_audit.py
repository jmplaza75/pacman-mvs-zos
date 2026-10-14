#!/usr/bin/env python3
"""MVS-G8 (D43, docs/G8-RELEASE.md section 5): release-integrity audit of the 2.0 rebuild under a fresh prefix.
Decks (before submission): every dataset name under HERC01 must be under PREFIX + '.' (no project DD, STEPLIB, TSO
ALLOC / EXEC / CALL / DELETE or CLIST text may resolve to the old HERC01.PACMAN libraries); every other DSN must be a
permitted system library or a temporary (&&); no JOBLIB; every STEPLIB = PREFIX.LOAD; cards within 80 columns and
JCL statements within column 71.
Listings (--listing, after the job): every HERC01 dataset name the system printed (allocation / disposition
messages, echoed JCL) is under PREFIX + '.'.
Usage: g8_jcl_audit.py [--prefix HERC01.PACMAN.R20] [--listing] FILE..."""
import argparse
import re
import sys

SYSTEM = {'SYS1.MACLIB', 'SYS1.AMODGEN', 'SYS1.COBLIB'}
NAME = re.compile(r"(?<![A-Z0-9@#$.])HERC01(?:\.[A-Z0-9@#$]{1,8})*")


def audit_deck(text, prefix):
    errs = []
    for n, line in enumerate(text.splitlines(), 1):
        if len(line) > 80:
            errs.append(f'{n}: card longer than 80 columns')
        if line.startswith('//') and not line.startswith('//*') and len(line.rstrip()) > 71:
            errs.append(f'{n}: JCL statement past column 71')
        if re.match(r'//JOBLIB\s', line):
            errs.append(f'{n}: JOBLIB')
        m = re.match(r'//STEPLIB\s+DD\s+DSN=([^,\s]+)', line)
        if m and m.group(1) != f'{prefix}.LOAD':
            errs.append(f'{n}: STEPLIB {m.group(1)}')
        for d in re.findall(r'DSN=([^,\s)(]+)', line):
            if not (d.startswith('&&') or d in SYSTEM or d.startswith(prefix + '.')):
                errs.append(f'{n}: DSN {d}')
        for d in NAME.findall(line.upper()):
            if d != prefix and not d.startswith(prefix + '.'):      # the prefix itself: the //* PREFIX comment
                errs.append(f'{n}: dataset name {d}')
    return errs


def audit_listing(text, prefix):
    errs = []
    for n, line in enumerate(text.splitlines(), 1):
        for d in NAME.findall(line.upper()):
            if d.count('.') and d != prefix and not d.startswith(prefix + '.'):
                errs.append(f'{n}: {d}: {line.strip()[:100]}')
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefix', default='HERC01.PACMAN.R20')
    ap.add_argument('--listing', action='store_true')
    ap.add_argument('files', nargs='+')
    a = ap.parse_args()
    bad = 0
    for f in a.files:
        text = open(f, encoding='ascii', errors='replace').read()
        errs = (audit_listing if a.listing else audit_deck)(text, a.prefix)
        names = sorted(set(d for d in NAME.findall(text.upper()) if '.' in d))
        print(f"{f}: {'FAIL' if errs else 'PASS'} ({len(names)} HERC01 names, all under {a.prefix}.)"
              if not errs else f'{f}: FAIL')
        for e in errs[:20]:
            print('  ', e)
        bad += bool(errs)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
