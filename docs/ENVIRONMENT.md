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

## Host since the 2026-10-21 DASD recovery (MVS-10; docs/evidence/mvs10-release.md section 4)
- Never run two Hercules instances on the same DASD (that corrupted mvsdlb.248). Check first: `pgrep -fl hercules`.
- Active system volume: dasd/mvsres.148 from the pristine TK4- image (backup mvsres.148.post-recovery-mvs10-20261021);
  the old volume (mvsres.148.pre-pristine-test-20261021) IPLs into disabled wait 00020000 80000005 - retired, kept.
- Boot (manual console): `./start_herc` in ~/mainframe/tk4; console `c3270 -model 2 CONS@127.0.0.1:3270`; Hercules
  `ipl 148`; at IEA101A on the MVS console `R 00,CMD=02` (autopilot startup). `./mvs` is not used any more.
- Shutdown (TK4- manual): `f bsppilot,shutnow`, wait `$HASP099`; `$PJES2` -> `$HASP085`; `Z EOD` -> `IEE334I`;
  `QUIESCE` -> `HHC00809I disabled wait state 000A0000 00000CCC`; Hercules `stopall`, `sysclear`, `quit`. In this
  setup the 3215 console 01F (console ID 04) has nothing attached and collects messages: if `IEA404A WTO BUFFER
  SHORTAGE` appears and JES2 stops answering, `D C` then `K Q,L=04` frees the buffers (IEA406I).
- Hercules commands also through the HTTP console (http://127.0.0.1:8038, POST field `command`); MVS commands only on
  the MVS console (a `/` command is rejected there, HHC01600E).
