# PACMAN Mainframe - Local Environment (verified 2026-10-07; source: requirements v4 sec. 35-37)
- Host: macOS, Darwin 25.6.0, ARM64. Running emulator: TK4- bundled Hercules 4.00 (2016 build, x86_64 via Rosetta,
  ~/mainframe/tk4/hercules/darwin/bin/hercules, started by ./start_herc). Homebrew SDL Hyperion 4.9.1 is installed
  (/opt/homebrew/bin/hercules) but not used (found in MVS-G1, see docs/evidence/g1-probe-analysis.md).
- Guest: TK4- / MVS 3.8J, S/370, CPU 3033, 1 CPU, 16 MB, JES2.
- Config: ~/mainframe/tk4/conf/tk4-.cnf; start with ./start_herc in ~/mainframe/tk4.
- Console 3270 on localhost:3270 (c3270/s3270 4.5ga6). ASCII card reader: 127.0.0.1:3505.
- JES printer output: ~/mainframe/tk4/prt/prt00e.txt (shared; never clear it).
- COBOL: IKFCBL00 (CB545 V2 LVL78 01MAY72), linker IEWL, runtime SYS1.COBLIB.
  Conservative dialect: no inline EXIT, no `>=`/`<=` (use NOT < / NOT >), `01 name COPY member.`
- TSO user: HERC01. Datasets: HERC01.PACMAN.COBOL / .COPY / .LOAD.
- Credentials: TK4_USER/TK4_PASSWORD via environment or gitignored `.env`; never committed.
