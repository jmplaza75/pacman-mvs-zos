#!/usr/bin/env python3
"""ZOS-4 Z3 (docs/zos4-sysin-fix.md): replace the installed Z2 CLIST(PACMAN) by the Z3 CLIST (src/zos/PACMAN.clist =
2.0 + Z3 SYSIN lines + Z2) rendered for Z00000.PACMAN. One member written; nothing else.

Usage: zos_z3_install.py --gate        read-only: CLIST(PACMAN) = exactly the installed Z2 member (the 8724464 source
                                       rendered, SHA-256 of the 107 x 80 bytes as recorded by PACZ4INS), PACSRCT = the
                                       template, CEEOPTS / PACMAIN / PACZ2D as after PACZ4INS (zos_ins_check)
       zos_z3_install.py --install     the gate again; any FAIL -> nothing written; then the upload with IBM-037 and the
                                       binary download (zos_upload, the ZOS-1 method) and zos_ins_check --clist
                                       (CLIST(PACMAN) = rendered src/zos byte for byte, PACSRCT = template)
"""
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zos_ins_check as C  # noqa: E402
from zoslib import fixed_records  # noqa: E402
from zos_upload import upload_verify  # noqa: E402

Z2_REF = '8724464'                     # the src/zos/PACMAN.clist PACZ4INS installed (JOB03939 + zos_clist_install)
Z2_SHA = '2e9895dc6f7c16a4ef159966aa6dc36cd957b11ea9e51adf3c7a3d917f6f7f33'   # docs/evidence/zos4-classic.md


def z2_installed_bytes():
    src = subprocess.run(['git', 'show', f'{Z2_REF}:./src/zos/PACMAN.clist'], cwd=C.R, capture_output=True,
                         check=True).stdout.decode('ascii')
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / 'z2.clist'
        f.write_text(src.replace('@@PREFIX@@', C.P), encoding='ascii')
        b = fixed_records(f)
    assert hashlib.sha256(b).hexdigest() == Z2_SHA, 'the Z2 reference does not render to the recorded member'
    return b


def gate():
    z2 = z2_installed_bytes()
    z3 = fixed_records(C.rendered_clist())
    cur = C.binary(f'{C.P}.CLIST(PACMAN)')
    res = [(f'CLIST(PACMAN) = the installed Z2 member (SHA-256 {Z2_SHA[:8]}..., {len(z2) // 80} x 80)', cur == z2),
           ('rendered Z3 member differs from it (something to install)', z3 != z2)]
    return res + [r for r in C.state_after_job() if 'not installed by the job' not in r[0]]


def main():
    a = sys.argv[1:]
    if a == ['--gate']:
        sys.exit(1 if C.show('Z3 INSTALL GATE', gate()) else 0)
    if a != ['--install']:
        sys.exit(__doc__)
    if C.show('Z3 INSTALL GATE', gate()):
        sys.exit('STOP: the Z3 CLIST is not installed')
    ok, msg = upload_verify(C.rendered_clist(), 'CLIST', 'PACMAN', C.HLQ, C.R / 'build/zos4/dl-z3')
    print(msg)
    if not ok:
        sys.exit('STOP: CLIST(PACMAN) is not the rendered member')
    sys.exit(1 if C.show('Z3 CLIST CHECK', C.state_after_clist()) else 0)


if __name__ == '__main__':
    main()
