#!/usr/bin/env python3
"""ZOS-4 PACZ4INS step 6: install the z/OS CLIST (src/zos/PACMAN.clist rendered for Z00000.PACMAN) as
Z00000.PACMAN.CLIST(PACMAN) - only after the PACZ4INS job and its post-job state passed - then prove it byte for byte.

Usage: zos_clist_install.py SPOOLDIR_OF_PACZ4INS   (writes ONE member; nothing else)
1. re-checks, read-only, the PACZ4INS job (zos_ins_check job_check) and the state after it (PACSRCT = the template,
   CEEOPTS, PACMAIN attributes = PACZ2D, CLIST(PACMAN) still the template): any FAIL -> nothing is written;
2. uploads build/zos/PACMAN.zos.clist with IBM-037 into CLIST(PACMAN) and downloads it in binary: it must equal the
   local file encoded to IBM-037 and padded to fixed 80-byte records (tools/zowe/zos_upload.py, the ZOS-1 method);
3. re-checks CLIST(PACMAN) = rendered and CLIST(PACSRCT) = template (zos_ins_check --clist).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zos_ins_check as C  # noqa: E402
from zos_upload import upload_verify  # noqa: E402


def main():
    (d,) = sys.argv[1:]
    _, res = C.job_check(d)
    bad = C.show('PACZ4INS CHECK (before the CLIST)', res + C.state_after_job())
    if bad:
        sys.exit('STOP: the CLIST is not installed')
    ok, msg = upload_verify(C.rendered_clist(), 'CLIST', 'PACMAN', C.HLQ, C.R / 'build/zos4/dl')
    print(msg)
    if not ok:
        sys.exit('STOP: CLIST(PACMAN) is not the rendered member')
    sys.exit(1 if C.show('PACZ4INS CLIST CHECK', C.state_after_clist()) else 0)


if __name__ == '__main__':
    main()
