# MVS build procedure (MVS-0)
1. Hercules/TK4- running; `.env` (gitignored, mode 600) holds `HERC01_PASSWORD`.
2. First use only: `./tools/submit.sh jcl/mvs/ALLOC.jcl` (creates HERC01.PACMAN.COBOL/COPY/LOAD; not idempotent).
3. `python3 tools/make_deck.py PACHELLO && ./tools/submit.sh build/PACHELLO.jcl`
4. `./tools/job_output.py PACBLD00 > build/PACBLD00.txt && ./tools/check_hello.py build/PACBLD00.txt`
Pipeline: IEBGENER upload -> IKFCBL00 -> IEWL (SYS1.COBLIB) -> execute -> SYSOUT.
Environment notes: socket jobs need HERC01 credentials (injected in memory by send_deck.py, redacted in output);
printer output in ~/mainframe/tk4/prt/prt00e.txt.
## MVS-0 result (2026-10-07)
ALLOC JOB 111 RC 0000. PACBLD00 JOB 112: SRC1/COB1/LINK/RUN1 all RC 0000, banner printed;
rerun reproduced the same result. Evidence: docs/evidence/mvs0-pachello.txt.
