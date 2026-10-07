#!/usr/bin/env python3
"""Check ASCII-only, <=80 column, tab-free sources/JCL. Returns list of errors."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def validate(path):
    path = Path(path)
    errors = []
    for n, line in enumerate(path.read_bytes().decode('latin-1').splitlines(), 1):
        if any(ord(c) > 126 or (ord(c) < 32) for c in line):
            errors.append(f'{path}:{n}: non-ASCII or control character')
        if path.suffix in ('.cob', '.cpy') and len(line.rstrip()) > 72:
            errors.append(f'{path}:{n}: COBOL text beyond column 72')
        if path.suffix == '.asm' and len(line.rstrip()) > 71:
            errors.append(f'{path}:{n}: assembler text beyond column 71 (72 is the continuation column)')
        if len(line) > 80:
            errors.append(f'{path}:{n}: longer than 80 columns')
        if path.suffix in ('.cob', '.cpy') and len(line) > 6 and line[6] not in ' *-/D':
            errors.append(f'{path}:{n}: bad indicator column')
    return errors


if __name__ == '__main__':
    errs = [e for p in sys.argv[1:] for e in validate(p)]
    print('\n'.join(errs) or 'OK')
    sys.exit(1 if errs else 0)
