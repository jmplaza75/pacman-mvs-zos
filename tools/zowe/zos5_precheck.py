#!/usr/bin/env python3
"""ZOS-5 read-only precheck (docs/zos5-live-session.md): the installed z/OS state is still the zos-4 closure - CLIST(PACMAN)
= the rendered src/zos (Z3 + Z2, SHA-256 f8989cfa...), CLIST(PACSRCT) = the template, CEEOPTS exact (attributes +
binary), LOAD(PACMAIN) attributes = PACZ2D's, PACZ2D unchanged. Zowe reads only; nothing is written.
Usage: zos5_precheck.py"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zos_ins_check as C  # noqa: E402

ZOS4_CLIST = 'f8989cfada7a862992af1c079572792eb72752aadb50e45281a81dd7447620cc'   # docs/evidence/zos4-closure-check.txt


def main():
    b = C.binary(f'{C.P}.CLIST(PACMAN)')
    res = [(f'CLIST(PACMAN) SHA-256 = the zos-4 member {ZOS4_CLIST[:8]}... ({len(b) // 80} x 80)',
            hashlib.sha256(b).hexdigest() == ZOS4_CLIST)]
    res += C.state_after_clist()
    res += [r for r in C.state_after_job() if 'CLIST(PACMAN)' not in r[0] and 'PACSRCT' not in r[0]]
    sys.exit(1 if C.show('ZOS-5 PRECHECK', res) else 0)


if __name__ == '__main__':
    main()
