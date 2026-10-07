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
- D8 (permanent rules from MVS-3) Every COBOL source ends by column 72 (enforced by tools/validate_source.py,
  run by make_deck/submit); counters that may exceed 99 are sized PIC 999 or larger; validate_source.py stays
  the preventive format gate. Conditional-ending performed paragraphs use THRU ...-EXIT (D4).
- D9 (MVS-4) Ghost rules: one ghost starts at (19,9), cell cleared (no pellet). AI1 (default) = random among
  non-wall neighbours (order U,D,L,R) using a deterministic LCG seed' = (seed*75+74) mod 65537, seed 12345,
  one draw per ghost move, no draw if no neighbour. AI0 = still ghost (test mode; optional first SYSIN card
  `AI0`/`AI1`). Order per turn: player move/eat -> hit check -> (if not over) ghost move -> hit check; a hit
  ends the run with CAUGHT (lives arrive in MVS-5) and beats WIN. Every U/D/L/R command, even blocked, is a tick.
- D10 (permanent rules from MVS-4) Tests are deterministic and checked against an independent Python model.
  AI must be reproducible with a fixed seed; a controlled/deterministic mode (AI0 still ghost, fixed LCG seed)
  is always kept so AI, collision and regression scenarios replay exactly. Any future AI improvement must be
  testable reproducibly even if normal play uses pseudo-random behaviour.
- D11 (MVS-5) Lives and cycle: 3 lives. A hit costs one life; if lives remain, player (2,2) and ghost (19,9) are
  reset (eaten pellets and score persist, ghost seed continues, ghost does not move that tick) and the result is
  DIED; at 0 lives the run ends LOST (board shows the collision). States: READY (before the first tick) ->
  RUNNING -> WON | LOST | QUIT (shown as ST= in each status line); EOF ends in the last state. End lines:
  WIN|LOST|QUIT|EOF, TURNS, SCORE, LIVES. A hit beats a simultaneous last pellet; if lives remain and no pellets
  are left after the reset the game is WON. That edge is covered by cases EDGE3/EDGE2/EDGE1 (tests/search_edge.py engineers them: last pellet eaten in the same tick as the hit, with 2/1/0 lives remaining after it).
  JES trims trailing blanks, so tests compare right-stripped lines.
- D12 (permanent rule) No documented edge case may remain without a test before a phase is closed.
