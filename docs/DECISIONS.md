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
- D13 (MVS-6) IKFCBL00 rejects nested subscripts (`REV-D (GH-DIR (G))`, `MAP-CELL (GH-Y (G) GH-X (G))`,
  IKF4077I): copy table fields into scalars first. Table items (GHOST-TABLE OCCURS 3) are fine as plain subscripts.
- D14 (MVS-6) Ghost AI levels, config card `AI<l> [<n>]` (l 0 still, 1 random incl. reversal, 2 persistent,
  3 chase; n = 1-3 ghosts, default AI1, 1 ghost, so MVS-5 behaviour and output are unchanged byte for byte):
  * Levels 2/3 never reverse unless no other move exists (impossible on LEVEL1: no dead ends - asserted by test).
  * AI2 keeps going while exactly one non-reverse move exists (corridor/turn); at an intersection (>= 2) it draws
    from the shared LCG (same seed 12345, draws in ghost order).
  * AI3 picks the move minimising Manhattan distance to the player's position after the player's move; ties go to
    the first in order U,D,L,R; no random draw.
  * Ghost starts (19,9) dir L, (2,9) dir R, (19,2) dir L; only active ghosts' cells are cleared (100/99/98 pellets).
  * Ghosts move in index order after the player; any ghost on the player's cell is a hit; several ghosts on the
    cell in one tick cost ONE life. Extra ghosts print on an extra status line `G2=xx,yy[ G3=xx,yy]`.
  * Documented edges are all tested: double hit (MULTI), pellet counts, no-reverse, corridor/intersection, tie
    breaking (properties re-derived from the real SYSOUT by tests/test_mvs6.py).
- D15 (permanent) D13 (no nested subscripts; copy table fields to scalars first) and D14 (all AI levels stay
  deterministic and reproducible, including the U,D,L,R tie-break and shared-LCG draw order) bind every later phase.
- D16 (MVS-7) IKFCBL00 copy members must START with their own 01 record (`01  PAC-STATE.`) and are used as `01  PAC-STATE COPY PACSTATE.` (names must match); otherwise IKF2148I/IKF3001I.
- D17 (MVS-7) Refactor rule: observable behaviour must not change. The banner text stays `PACMAN MVS-6 SMART GHOSTS`
  (it names the behaviour version, not the build) and all 19 SYSOUT blocks are byte-identical to the pre-refactor
  MVS-6 evidence (docs/evidence/mvs6-ai.txt); PACMAIN-MVS-6 monolith is preserved in git (tag mvs-6).
- D18 (permanent) D16 (copy members start with their own 01 record), D17 (refactors must not change observable
  behaviour; before/after SYSOUT identity) and the MVS-7 layer separation bind every later phase: PACGAME, PACMAP and
  PACAI never reference terminal, 3270, TSO or platform facilities; those live only in PACINPT, PACDISP, PACPLAT.
- D19 (MVS-8) Interactive mode = CLIST with SYSIN/SYSOUT allocated to the terminal + `PARM='TSO AI<l> <n>'`. The mode
  (REQ-MODE) is read only by PACMAIN, PACPLAT, PACINPT and PACDISP; the core never mentions it (tested). TSO-only input
  rules: leading blanks skipped, empty line = redraw. No input is read after QUIT/WON/LOST in either mode. TPUT/TGET
  were discarded (no-ops under a batch TMP, untestable). Details: docs/INTERACTIVITY.md.
- D20 (MVS-8) TSO `***` paging is avoided by starting each frame (after the first) on a fresh screen with
  `STLINENO LINE=1`, issued by the assembler stub PACTSO via PACPLAT op CLS; PACTSO is a no-op unless ASCBTSB shows a TSO
  user. Assembler is limited to this terminal service (requirements sec. 1). Validated live in c3270 (JOB 138 build).
- D21 (MVS-9) Release 1.0-MVS: every dataset name derives from a prefix (make_deck.py --prefix, default HERC01.PACMAN;
  the CLIST is a template with @@PREFIX@@), so the release rebuilds from empty libraries under any prefix. Release
  acceptance = tools/release_check.sh (local checks + RELEASE deck + tests/test_mvs8.py), proven from scratch under
  HERC01.PACMAN.R10 (JOBs 139-142) and on HERC01.PACMAN (JOB 143). Deliverables in releases/1.0-MVS/.
- D22 (MVS-G0) Core freeze: PACGAME, PACMAP, PACAI, PACSTATE, PACMREQ and maps/LEVEL1.txt are pinned to 1.0-MVS by
  tests/core_baseline.json (tests/test_core_frozen.py). A change is allowed only through
  `tools/core_baseline.py --authorize "REASON" --by NAME`, which logs it in docs/CORE_CHANGES.md. PACREQ may grow
  (append-only). The regression oracle for every G phase is the 1.0-MVS release evidence (mvs9-release-build.txt):
  all 25 output blocks must stay byte-identical (tests/test_g0.py).
- D23 (MVS-G0) Presentation metrics are optional: PARM column 11 = 'M' (e.g. 'BAT       M', 'TSO AI3 3 M') makes
  PACDISP print one METRICS line (frames, lines, characters, clears) after the end lines; without it the output is
  unchanged. Replaceability of the display is proven by linking an alternative PACDISP (src/cobol/alt/PACDSPX.cob)
  over the existing LOAD(PACMAIN) into LOAD(PACALT): the core CSECTs are reused without recompilation.
- D24 (MVS-G1) Colour renderer TSC as designed in docs/G1-RENDERER.md, approved with: player yellow, ghosts red/pink/
  turquoise (by index), walls blue, pellets white, HUD turquoise, help/input green, error red. All colours and the
  screen layout live only in copybook PACPAL. Selection COLOR(AUTO|YES|NO) (PARM column 12, default N for direct calls,
  AUTO in the CLIST); AUTO needs QCode X'86'; any failure keeps/returns to TSO line mode. Line mode is restored by
  PACPLAT FSOF at the end, by FINI, on any TPUT/TGET error (fallback) and by an ESTAE exit in PACFSIO on abend.
  TSD = batch dry run printing each TSC data stream in hex, checked byte for byte against tests/ref_g1_screen.py.
- D25 (MVS-G1) TSC screens start from a clean buffer: PACFSIO SEND inserts SBA(1,1) + RA to (1,1) with X'00' right
  after the WCC and sends with TPUT FULLSCR (the transport seen working live). History: JOB 157 visible with TSO
  remnants; JOB 159 (NOEDIT + X'F5') and JOB 160 (FULLSCR + prefix) black because of a length bug (`LA 0,n(0)` = n);
  JOB 161 fixes the length (AH) and was validated live (clean colour screen, R, Q, READY). The ESTAE abend-restore exit
  is implemented but not validated live.
