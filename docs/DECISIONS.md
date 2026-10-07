# Decisions (IKFCBL00 / platform)
- D1 (MVS-0) Pipeline: IEBGENER upload -> IKFCBL00 (LOAD,LIB,SUPMAP) -> IEWL with SYS1.COBLIB; jobs submitted
  through the ASCII reader 3505 with HERC01 credentials injected in memory from `.env` (never committed).
- D2 (MVS-0) Dialect from the Z-HEIST project: no inline EXIT; no `>=`/`<=` (use NOT < / NOT >); copybooks as
  `01 name COPY member.`; SYSIN read via `ASSIGN TO UT-S-SYSIN`.
- D3 (MVS-2) Reference modification `X(1:1)` is rejected (IKF1083I/IKF4082I, RC 12). Use a REDEFINES/group
  item (e.g. `CMD-CHAR` over the first byte of the record) instead.
- D4 (MVS-2) A performed paragraph ending in a conditional gives IKF4072I-W (RC 4). End it with an EXIT
  paragraph and call `PERFORM x THRU x-EXIT`.
- D5 (MVS-2) Tests compare SYSOUT with expected output produced by an independent Python reference model.
- D6 (MVS-3) COBOL text must end by column 72 (an overlong line gave IKF4091I, RC 12); tools/validate_source.py
  now enforces it. Counters that can exceed 99 (turns up to 185 in the full-clear run) are PIC 999.
- D7 (MVS-3) Rules: pellet = 10 points; the start cell is cleared at init without scoring; blocked moves and
  revisits score nothing; the game ends WIN when PELLETS-LEFT = 0 and later commands are ignored.
