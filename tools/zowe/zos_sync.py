#!/usr/bin/env python3
"""Upload every release source with IBM-037 and verify each member byte for byte (ZOS-1).

Usage: zos_sync.py [--hlq HLQ] [--dry-run]
Inventory (2.0 release set, 23 members): src/cobol/*.cob -> COBOL, src/copy/*.cpy -> COPY, src/asm/*.asm -> ASM,
src/clist/*.clist -> CLIST (raw, @@PREFIX@@ kept: identity only, not an install). Subdirectories (src/cobol/alt,
src/probe) are not part of the set. Runs tools/validate_source.py first; stops at the first failure.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zoslib import R, hlq  # noqa: E402
from zos_upload import upload_verify  # noqa: E402

SETS = (('src/cobol', '*.cob', 'COBOL'), ('src/copy', '*.cpy', 'COPY'), ('src/asm', '*.asm', 'ASM'),
        ('src/clist', '*.clist', 'CLIST'))


def inventory():
    return [(p, lib) for d, pat, lib in SETS for p in sorted((R / d).glob(pat))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hlq')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out', type=Path, default=R / 'build/zos1/dl')
    a = ap.parse_args()
    inv = inventory()
    for p, lib in inv:
        print(f'{lib:<6} {p.stem.upper():<9} {p.relative_to(R)}')
    print(len(inv), 'members')
    if a.dry_run:
        return
    h = hlq(a.hlq)
    subprocess.run([sys.executable, str(R / 'tools/validate_source.py')] + [str(p) for p, _ in inv], check=True)
    for p, lib in inv:
        ok, msg = upload_verify(p, lib, None, h, a.out)
        print(msg)
        if not ok:
            sys.exit(1)
    print(f'ALL {len(inv)} MEMBERS IDENTICAL (IBM-037, fixed 80)')


if __name__ == '__main__':
    main()
