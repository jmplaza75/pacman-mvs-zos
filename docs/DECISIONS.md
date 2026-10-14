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
- D28 (MVS-G3) Known limitation, investigation closed deliberately: In this TK4-/MVS 3.8J + TSO + c3270 environment, COLOR(AUTO) performs a capability Query Reply that leaves the idle ticks held
  until the first AID. After the first input the animation works normally. With COLOR(YES) HILITE(YES) the query is skipped and the
  animation starts immediately. This is a known limitation of the TSO environment/protocol investigated, not a fault of the game
  mechanics or of the G3 renderer.
  COLOR(AUTO) remains the default (G1/G2 detection + fallback); COLOR(YES) HILITE(YES) is the recommended option on TK4-/c3270 for
  immediate idle animation. Refuted fixes: TPUT BREAKIN, TCLEARQ INPUT after the query, FSOF+FSON after the query (docs/G3-PARTIAL.md).
- D27 (MVS-G3) Partial redraw = X'F1' Write + TPUT NOEDIT (probe E6, variant W; ASIS erases). Options REDRAW(PARTIAL|FULL) (PARM
  col 15) and ANIM(AUTO|YES|NO) (col 14), independent; full render stays the reference/diagnostic mode and the fallback after a
  failed partial send. Animation = alternating glyphs (PACPAL) with a visual tick separate from the logical one (idle polling,
  never a game call). Core untouched. Performed paragraphs that end in an IF get a final `MOVE 0 TO WS-NOP.` (IKF4072I-W).
  Details and results: docs/G3-PARTIAL.md.
- D26 (MVS-G2) Highlighting is a separate option of TSC (HILITE(AUTO|YES|NO), PARM column 13, default N for direct calls,
  AUTO in the CLIST; AUTO needs colour plus QCode X'87'). Reverse for P/G, blink for INVALID COMMAND, underscore for the
  input field; nothing else (docs/G2-HIGHLIGHT.md). Values only in PACPAL. Off = G1 screens. Compiler note: a paragraph
  must not end with a conditional PERFORM (IKF4072I-W with IKFCBL00); end it with a plain statement.
- D25 (MVS-G1) TSC screens start from a clean buffer: PACFSIO SEND inserts SBA(1,1) + RA to (1,1) with X'00' right
  after the WCC and sends with TPUT FULLSCR (the transport seen working live). History: JOB 157 visible with TSO
  remnants; JOB 159 (NOEDIT + X'F5') and JOB 160 (FULLSCR + prefix) black because of a length bug (`LA 0,n(0)` = n);
  JOB 161 fixes the length (AH) and was validated live (clean colour screen, R, Q, READY). The ESTAE abend-restore exit
  is implemented but not validated live.
- D29 (MVS-G4) Glyph profiles of the TSC renderer, design docs/G4-GLYPHS.md (approved 2026-10-08): GLYPHS(AUTO|GRAPHIC|BASE|CLASSIC),
  PARM column 16, default AUTO in the CLIST and CLASSIC (= the G3 screens byte for byte) for direct calls. GRAPHIC = CP310 glyphs
  sent per cell as GE X'08' + code (not SA X'43'): wall tiles by neighbour mask (N1 E2 S4 W8), pellet bullet, Pac-Man facing the last
  horizontal move that was not blocked (vertical moves, bumps, invalid input keep it), ghosts with two frames; BASE = + - | tiles and
  a middle dot. AUTO = GRAPHIC only if the Query Reply X'85' has the GE flag, CGCSGIDs and a code page 310 set; with COLOR(YES) there
  is no query, so the explicit TK4-/c3270 combination is COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC). The reply is parsed by the pure
  subprogram PACQRY (G1/G2 decisions moved there unchanged); query transport, PACFSIO and the G1-G3 protocol path are untouched.
  Values only in PACPAL; the virtual image carries a GE flag per cell. Probe E9: docs/evidence/g4-probe-analysis.md.
  REVISED after the live check (user, 2026-10-08): the neighbour-mask wall tiles were rejected (centre-line strokes, not
  barriers; docs/evidence/g4-wall-diagnosis.md). BASE and GRAPHIC draw each wall cell as a blank in the wall colour with
  reverse video (HI-WALL) when highlighting is on, `#` otherwise (reverse video is never forced against HILITE); pellets and
  sprites as above; CLASSIC unchanged. Arcade-style wall contours are deferred to a future scaled renderer (preferably 2 x 2).
  Maintenance: `make_deck.py COMPRESS` compresses the COBOL/COPY libraries (SE37 in JOB 193).
- D30 (MVS-G5) Programmed Symbols are not supported in the validated TK4-/MVS 3.8J + TSO + c3270 environment; G4 is the production
  character-set ceiling (capability limit, not an implementation failure). Isolated probe E10 (JOB 196, live 2026-10-08,
  docs/evidence/g5-probe-analysis.md): Query Reply X'85' offers no loadable sets (byte-identical to E9), c3270 traces the Load PS field
  as `WriteStructuredField unsupported ID 0x06`, nothing returns to the host, SA X'43' to the loaded LCID shows the base set while the
  APL control (F1) works. Matches x3270 source (sf.c/ctlr.c/telnet.c). G6 (multicolour/triple-plane PS) is BLOCKED / NOT APPLICABLE
  here, reason inherited. A PS-capable terminal/emulator may be explored in a separate future compatibility branch (not pursued, no
  dependency on Vista TN3270/PCOMM). Next visual step for this environment: the 2 x 2 scaled renderer.
- D31 (MVS-GS) Scaled renderer, design docs/GS-SCALED.md (approved 2026-10-08): 1 logical cell = 4x2 terminal cells (layout B,
  board 80x20 rows 1-20, text rows 21-24), SCALE(3) = 3x2 alternative, SCALE(NO) = G4. Walls are contours on the wall/corridor
  boundaries (corner rule on 2 neighbours + diagonal, outside = open: double outer border), static, computed once. Sprites = E11
  half-block pixel art (Pac-Man R/L/shut, ghosts frames A/B with reverse-video eyes), pellet top row 2nd column. Row 22 end/status
  banner. Option SCALE(AUTO|4|3|NO), PARM column 17; absent = NO (G4 byte-identical); AUTO only from the existing query results;
  needs COLOR + HILITE + GRAPHIC glyphs, else SCALED -> G4 GRAPHIC -> BASE -> CLASSIC -> line mode. Full-screen compression (RA,
  RA+GE, blank skips) lives in PACSCR; PACFSIO unchanged; renderer-side guard: no stream > 2048 bytes reaches PACFSIO. Probe E11
  (JOB 198) live: captures identical to the model. Physical proportions not yet visually confirmed.
  Implementation (JOB 200, test_gs PASS): end banner = one final scaled screen + 3 s pause (new PACTSO op WAIT, no input
  read, D19 kept), scaled only; SCALE(3) shares the layout-B text rows (board centred at column 11); 3x2 ghost eye in the
  middle cell; size guard falls back to G4 for the rest of the game (tested with SCALE T = 1000-byte limit).
- D32 (MVS-GS) Geometry (docs/GS-GEOMETRY.md, approved 2026-10-09; evidence docs/evidence/gs-e12-geometry.md, probe E12): the
  3270 canvas is fixed by c3270 at connect (window size then; silent downgrade when too small; resize never renegotiates,
  shrinking below it is unsupported). Live PASS: 80x32 (model 3), 80x43 (model 4), 132x27 (model 5), 120x27 (IBM-DYNAMIC,
  `-model 2 -oversize auto`). TK4- TSO itself enters the alternate size at logon, so PACMAN must set the buffer size itself:
  CANVAS(AUTO|DEFAULT) (PARM column 18), one EWA / EW before the query, FULLSCR first screen, later full screens with the same
  command (PACFSIO op SENX, the one allowed extension), partials unchanged. Primary layout 120x27 (maze rows 4-23, columns
  21-100, compact side HUD), 132x27 wide, 80x43/80x32 tall, 80x24 GS fallback. The maze stays 4x2 (80x20). 4 KB TPUT (E13)
  is a future investigation, not a dependency.
  Live (2026-10-09, JOB 207 build): 120x27 IBM-DYNAMIC PASS (centred maze, HUD, banners, CLEAR+PA2 recovery), 80x24 fallbacks
  PASS. Preferred canvas for the normal 120x30 macOS Terminal: 120x27 IBM-DYNAMIC; 80x24 the universal fallback. MVS-GS closed.
- D33 (MVS-RT) REALTIME design, docs/RT-REALTIME.md "RT1 frozen design" (approved 2026-10-10, from RT0 probe E14,
  docs/evidence/rt-e14-timing.md): T = 150 ms with absolute deadlines (175 ms fallback; not 100 ms); arrows -> PF7/8/10/11
  via the c3270 launcher keymap with typeahead OFF; U/D/L/R + ENTER fallback; drain all AIDs each quantum into one
  requested-direction slot (latest wins, TTL 3 player steps); ghosts 4/5 by integer accumulator; exactly one write per
  active quantum with keyboard restore, never conditional on an AID (CLEAR is swallowed by TSO; PA2 = redraw);
  press-to-start (D28 release); separate RT-LOOP, terminal-independent PACRT, PACGAME REQ-STEP B/P/G (TURN = B), PACFSIO
  POLL, PACTSO TIME / deadline wait; PLAY(TURN|REALTIME), TURN default and byte-identical. TICK-COUNT wraps harmlessly
  (display only, JOB 217): PACSTATE unchanged. RT0 has no valid physical 4-key burst; accepted as an RT3 control issue.
- D34 (MVS-RT) REALTIME is the PACMAN CLIST default (`PLAY(REALTIME)`), approved by the user after the RT3 live PASS
  (2026-10-11, docs/evidence/rt3-live.md); `PLAY(TURN)` is the compatibility mode and direct calls without PARM column
  19 stay TURN (D17). Pause = PF9 (P in the launcher's temporary keymap) or P + ENTER, with a PAUSED banner; RT3 live
  defects fixed: CLIST CALL line beyond column 72, PACTSO DLWT register (batch clock test PACTSOT added).

- D35 (MVS-S1) Sound = the 3270 alarm (probe E15, docs/evidence/s1-e15-alarm.md: audible through SENX, SEND and SENP;
  3 bells audible back to back and 0.5 s apart). `SOUND(AUTO|YES|NO)` (PARM column 20; absent = NO, so every earlier
  reference stays byte-identical; CLIST default AUTO). The alarm is base 3270: AUTO = YES in colour full-screen mode
  (TSC, and the TSD dry run), NO in line mode and batch. Display/platform only, core untouched: PACDISP SET-BELL reads
  the state before every screen sent - first screen (start), fewer lives than at the previous screen (death, the last
  one too), first screen after the win; one bell per screen (death + win in one move ring once). PACPLAT SET-ALARM sets
  WCC bit X'04' on that same stream (C3 -> C7, C2 -> C6): no extra write, except at the end of a game without an end
  screen (not scaled), where a pending bell goes on one restore-only write C6 28 00 00 before line mode. Tests:
  tests/test_s1.py (JOB 233: RT deck unchanged + 15 SOUND TSD runs = model with 38 bells + 3 silent runs = oracle).
  Live 1: a latent RT2 defect surfaced at every game end (PACTSO WAIT fell into DOTIME, wild store, 0C4-4); fixed in
  PACTSO (one `B DONE`), static check in tests/test_s1.py (batch cannot reach that path); docs/evidence/s1-live-0c4.md.
- D36 (MVS-GP1) Power pellets under `RULES(ARCADE)`, design docs/GP1-POWER.md (approved by the user 2026-10-11).
  `RULES` = PARM column 21 (`A` ARCADE, anything else/absent CLASSIC = 1.0-MVS byte for byte; CLIST default CLASSIC
  until G8). ARCADE state in the new copybook PACARC (own 01), passed explicitly to PACGAME/PACAI/PACRT/PACDISP/PACSCR;
  PACSTATE untouched, no CLASSIC field repurposed (SCORE only mirrors the low 4 digits of the 7-digit ARC-SCORE).
  Core change (authorised): PACMAP op LDA (power pellets `o` at (2,4) (19,4) (2,8) (19,8), existing corridor cells),
  EAT flag 2 on `o`, CNT counts `o`; PACGAME ATIK + ARCADE move/hit branches; PACAI flee + per-class cadence.
  Rules: `o` 50 points, ghosts 200/400/800/1600 by chain; a new `o` restarts the fright (no added time) and resets
  the chain; eyes are non-lethal and ignore new power pellets; an eaten ghost jumps home as eyes and waits, then
  revives NORMAL even during a fright (one more tick while Pac-Man stands on the home cell); a death resets fright,
  chain, accumulators and eyes; pause freezes every GP1 timer. Frightened move: pending reversal first, then the
  maximum Manhattan distance from Pac-Man, tie order U,D,L,R, no seed use; AI0 stays still. Cadence: TURN frightened
  1 move every 2 Pac-Man turns; REALTIME frightened accumulator + 2 due at >= 5 = 2/5 of the quanta (40 % of
  Pac-Man, half of the 4/5 normal-ghost rate) - two different discrete rules, neither called "half speed".
  Constants in one PACGAME table (TURN/REALTIME): fright 20 / 40 (6 s), warning 5 / 10 (1.5 s), eyes 10 / 20 (3 s).
  The collision order of GP1-POWER 4.4 is authoritative. No GP2 behaviour in GP1.
  GP1.2 (JOB 238, tests/test_gp1.py PASS): no frightened move in the step where a fright starts; GHOSTS EATEN is
  the last end line; LEVEL1 has no dead ends (dead-end flee unreachable, blocked pending reversal tested).
  GP1.3 screens (JOB 240, GP1-POWER section 10): ARCADE status line variant (61 columns, S= 7 digits, PW, FR),
  power pellet blinking, frightened ghosts blue / white (warning) not reversed outside the scaled sprites, eyes `"`
  drawn under Pac-Man and the other ghosts; CLASSIC streams byte-identical.
- D37 (MVS-GP2) Levels, progression and bonus fruit under `RULES(ARCADE)`, design docs/GP2-PROGRESSION.md (approved by
  the user 2026-10-12). CLASSIC = 1.0-MVS byte for byte. Levels 1-99: a level ends only when the maze is completely
  cleared (after the step's hits and life loss); the next level refills every item (96 + 4 power pellets with 1
  ghost), returns Pac-Man and the ghosts to their start cells, resets fright, warning, eyes, chain, accumulators,
  the fruit and both fruit thresholds, and applies its row; score, lives, the EXTRA-LIFE-AWARDED flag, the seed and
  the game totals persist. Clearing level 99 ends the game WON - an intentional MVS implementation limit, not the
  endless arcade progression. Per-level table (the one place of every level-dependent value, PACGAME K-LVL, 13 rows,
  levels 13-99 = row 13): AI = configured + bump (max AI3; AI0 stays AI0), REALTIME normal ghosts + 8 or 9 of 10
  (8/10 = the GP1 4/5 pattern), fright 20/17/14/10/7/17/7/7/4/17/7/4/4 turns (40 ... 7 quanta) with its warning
  window, fruit cherry 100, strawberry 300, orange 500, apple 700, melon 1000, galaxian 2000, bell 3000, key 5000.
  Fruit at (10,8) (verified corridor cell, no spawn / power overlap) after 30 and 70 items of the level, 30 turns /
  60 quanta; eaten when Pac-Man is on the cell at the end of his step (also when it appears under him); removed by
  a death and a level clear; pause stops its timer. Exactly one extra life when a scoring event takes the score to
  10000 or more, before any hit of the same check (ARC-XL, never twice). Deaths are signalled by the event flag D
  (never inferred from LIVES, which an extra life in the same step leaves unchanged); a death or a level clear in
  REALTIME freezes 10 quanta on the existing freeze. LIVES stays PIC 9 (max 4): "lives widened" closed as not needed.
  Wide ARCADE counters ARC-TURNS 9(7), ARC-EATN4 9(4), ARC-FRUITS 999 (TICK-COUNT / ARC-EATEN mirror their low
  digits). Start level: PARM columns 22-23 (1-2 digits to the PARM end, 1-99, anything else = 1), CLIST `LEVEL(n)`
  default 1, a fresh game at that level (no simulated earlier levels). Text: `LEVEL nnn` header, one `L` line per
  frame (level, AI, items, fruit, extra life, events), `%` fruit on the board, end lines TURNS 7 digits, GHOSTS EATEN 4
  digits, FRUITS EATEN, LEVEL. GP1 ARCADE reference output evolves (GP1 invariants rerun on the extended model).
  GP2.3 screens (JOB 246 + GP2 rerun JOB 247, GP2-PROGRESSION section 11): fruit `%` green (base set, every profile;
  scaled sprite 8) drawn under eyes, Pac-Man and ghosts and redrawn when they leave; status line variant with FR,
  level and fruit kind (PW dropped); wide / tall HUD level + fruit name and points; level transition = the refilled
  maze + CLEARED + new level (no new sequence; RP owns READY / intermission); ARCADE alarm from the counters (death,
  extra life, level clear, final win), one alarm per screen (events of one write coalesced), CLASSIC S1 rule unchanged.
  User (2026-10-12): GP2.3 approved; the level-clear alarm is kept (D37 section 8, one ordinary alarm, coalesced); the
  80x24 status line (LEVEL + fruit kind letter, no PW=, no fruit points) is an intentional compact-layout tradeoff.
- D38 (MVS-HS) Persistent ARCADE high score, design docs/HS-HISCORE.md (approved by the user 2026-10-12 with the D4
  amendment), probe E16 (docs/evidence/hs-e16-probe.md, JOB 254). One global ARCADE high score in
  `<prefix>.DATA(HISCORE)` (PDS FB 80/80, outside the build libraries; ALLOC deck + one-time DATA deck), record = 7-digit
  score, tag `PACHS001`, level reached by the run that set it. Only PACPLAT touches it, through the new assembler
  service PACHSIO (BLDL lookup with the PDS opened without the member, OPEN TYPE=J + JFCNWRIT; update in place by QSAM
  UPDAT; REPL = QSAM OUTPUT of one record; fresh-RDJFCB safety check before every QSAM OPEN; ESTAE retry turns any abend
  of its I/O into RC 16). GAME / MAP / AI / PACARC unchanged. CLASSIC: nothing. Eligible = ARCADE started at level 1,
  any end (LOST, WIN, QUIT, EOF); `LEVEL(n>1)` shows, never saves. Written only when strictly beaten (equal = no
  write, never decreases). Missing / empty / malformed = 0, healed by the next eligible save. In-memory high score =
  max(persistent, current). End lines `HIGH SCORE nnnnnnn LEVEL nnn` + `NEW HIGH SCORE` / `HIGH SCORE NOT SAVED`
  (write attempted and failed) / `START LEVEL nn: HIGH SCORE NOT RECORDED`, or `HIGH SCORE UNAVAILABLE` (DD present
  but unusable); no DD = not configured, silent (every earlier reference unchanged). CLIST: no keyword; ARCADE only;
  `&SYSDSN` pre-check, DATA missing = `ALLOC ... DUMMY` (unavailable). Never abends, never changes the game result, no
  new alarm, no screen change (HUD = RP).
  HS.2 (JOB 260, tests/test_hs.py): H1-H15 = the independent model tests/ref_hs.py; the ESTAE exit is deleted after
  a retry too (E16b). HS.3 live PASS (docs/evidence/hs-live.md); the live higher-score case ended with QUIT, LOST and
  the other end paths are covered by HS.2.
- D39 (MVS-RP) Presentation and gameplay polish, design docs/RP-POLISH.md (approved by the user 2026-10-12). Display,
  platform and test work only: GAME / MAP / AI / PACARC untouched, batch and line-mode SYSOUT byte-identical in both
  rule sets. ARCADE full-screen only (CLASSIC screens byte-identical): READY! over the central wall bar (y 5, x 8-13)
  before the first direction and in the last 4 quanta of a death / level-clear freeze; death animation (6 frames at
  the death cell, published by PACRT with the freeze count; final death played by PACDISP before GAME OVER); no
  level-clear flash; score popups for an eaten ghost and the eaten fruit (one 4x2 tile, 6 quanta, display state in
  PACSCR, no game freeze; drawn over Pac-Man, under ghosts); HUD high score = max(REQ-HISCORE, ARC-SCORE) when HS is R / Z; end screen with SCORE /
  HIGH SCORE / NEW HIGH SCORE. An RP decoration over DS-LIMIT is dropped for that frame, never the G4 fallback.
  `SPEED(NORMAL|FAST)` = 150 / 125 ms, PARM column 24, any REALTIME game; amended for RP.3 (user, 2026-10-12/13):
  FAST changes the movement cadence only. Every timed event keeps its wall-clock length through one conversion
  Q' = (Q x 300 + P) / (2 x P) of the quanta designed at 150 ms (P = REQ-RTPER, chosen only by PACMAIN): freezes,
  READY!, popups (PACRT), fright / warning / eyes / fruit (PACGAME, authorised core change 2026-10-13); the death
  frames are 150 ms each (docs/RP-POLISH.md 6). NORMAL = identity. ESTAE validated live by the test driver
  PACRPE (forced 0C7 in full-screen mode, also after a PACHSIO call), not by a hook in the game. Soak: 10-minute pause
  and 10-minute pre-start wait in one live session.
- D40 (APPROVED 2026-10-12, implemented in RP.2b; recorded from RP.0 live 1/2, docs/evidence/rp-estae-live1.md, rp-estae-live2.md) Startup
  hardening. When line-mode output is pending at game start (seen after a program that wrote line output and then
  abended), TSO shows `***` before PACPLAT's full-screen switch; the ENTER that releases it is queued as input and
  TRY-COLOUR's QRY read takes it as the Query Reply (no X'88' -> HAS-COLOUR 0 -> line-mode fallback; the real reply is
  then read as commands, `INVALID COMMAND A` / `X`). Not caused by the PACFSIO ESTAE exit (RP.0 PASS). Fix
  (docs/RP-POLISH.md 11): PACQRY accepts only a structurally valid Query Reply (AID X'88', exact chain of X'81'
  fields, Summary first); PACPLAT reads past anything else with PACFSIO RECT, at most 8 records / 6 empty reads,
  then the line-mode fallback after a drain; a valid first reply = no extra read (start unchanged); no re-query.
- D41 (MVS-S2, APPROVED and frozen 2026-10-13, docs/S2-PATTERNS.md; build JOB 290, installed JOB 297-299, live PASS docs/evidence/s2-live.md) Alarm patterns. No probe: E15 showed separate
  bells are not merged. `ALARM(PATTERN|SINGLE)` = PARM column 25 (`P`; absent/else SINGLE = S1/GP2 bytes and waits;
  CLIST default PATTERN); SOUND(NO) suppresses every alarm. No new sound event: start, death, extra life, level clear,
  game over (the last death, which already rang as a death) and win all rang before S2; under PATTERN they give 1 / 2
  / 2 / 3 / 3 / 4 bells at offsets 0, G, 2G ... quanta, G = 2 at 150 ms (NORMAL), 3 at 125 ms (FAST), exact, no clock
  reads in play. Steps ride on REALTIME quantum writes (plain or prompt-form frames); pre-start / pause screens and
  ticks neither ring nor advance; pause holds a pattern; TURN rings offset 0 only during play. Priority game over > win
  > level clear > death > extra life > start; higher or equal replaces, lower is absorbed (unreachable in play).
  Game end drops in-play steps; game-over / win steps left go as bell-only writes inside the existing 3-s end pause
  (CLOK at the end screen, WDLN pacing, new PACPLAT op DLWT to t0 + 3000 ms), never lengthening it; not scaled = S1.
  Display/platform only: GAME, MAP, AI, PACARC, PACRT unchanged.
- D42 (MVS-G7, APPROVED 2026-10-14) Host graphics: negative capability closure, not a failed implementation (paper phase, docs/evidence/g7-gddm-check.md). Terminal: the
  E5 Query Reply (QCodes 80 81 84 85 86 87 88 95 A1 A6) announces no graphics and c3270 documents none. Host: read-only
  check jcl/mvs/G7CHK.jcl (JOB 301, all RC 0000): one master catalog, 140 non-VSAM names and 26 aliases, the seven
  LNKLST00 libraries plus SYS1.LPALIB (4077 member / alias names) contain no GDDM (ADM*) or other graphics module
  (tools/g7_gddm_scan.py, self-checked on synthetic positives). GDDM is a licensed product, not added (requirements
  sec. 29). The existing 3270 scaled / glyph renderer (GS over G4) is the final MVS graphics solution;
  nothing of PACMAN changed (installed PACMAIN JOB 298, CLIST JOB 299). A graphics-capable terminal
  plus a licensed host stack is a possible separate branch, not pursued.
- D43 (MVS-G8 / 2.0-MVS-MAX, APPROVED and frozen 2026-10-14, docs/G8-RELEASE.md) Final MVS release. Release phase, no
  game / display / platform source change. Only the CLIST default flips RULES(CLASSIC) -> RULES(ARCADE); PACMAIN's
  absent-PARM behaviour unchanged (no RULES column = CLASSIC; batch stays the reference); no PROFILE keyword, the AUTO
  chain (COLOR/HILITE/GLYPHS/SCALE/CANVAS AUTO, REALTIME, SOUND AUTO, ALARM PATTERN) is the maximum mode with its
  fallbacks. Benchmarks: deterministic bytes per frame from Hercules TSD streams + live cadence reused from RP; no CPU.
  Small PNG screenshot set + text reconstructions from model streams; no live traces committed. Clean rebuild from
  newly allocated empty libraries HERC01.PACMAN.R20 (larger ALLOC space, deck REL20, JCL audited against the old
  libraries), the validated R20 PACMAIN copied (not relinked) into HERC01.PACMAN.LOAD as the installed 2.0 module
  (JOB 298 historical), final CLIST installed, minimal installed live smoke; folder releases/2.0-MVS-MAX, annotated
  tag 2.0-mvs-max.
- D44 (ZOS plan, APPROVED 2026-10-14, docs/ZOS-MIGRATION-PLAN.md sec. 17) z/OS port: 2.0-mvs-max is the immutable
  functional oracle (R0-R8). Release name `2.0-ZOS`, tag `2.0-zos` (supersedes only the `1.0-zOS` name of requirements v4
  sec. 13). Target IBM Z Xplore, prefix Z00000.PACMAN. High score starts empty (no MVS import). AMODE 24 preferred only if
  it runs the complete program without source changes; otherwise stop and report before AMODE 31 or any source change.
  Work on branch `zos` in worktree ~/Documents/Worktrees/Pacman-zOS. Job output left to site retention, never purged
  automatically. ZOS-0 discovery-only; the single IEFBR14 is authorised by the user after being shown in full.
- D45 (ZOS-1, APPROVED 2026-10-14, docs/zos-build.md) Initial z/OS port build profile A: Enterprise COBOL 6.5.0
  P260714 with `RENT,RMODE(24),DATA(24),NODYNAM,TRUNC(STD),NUMPROC(NOPFD)`; binder IEWBLINK `RENT,AMODE=24,RMODE=24`;
  LE `ALL31(OFF),STACK(,,BELOW)`; HLASM R6.0. Evidence J3 JOB08331 proves only the toolchain / probe viability in
  AMODE 24, NOT that the complete Pac-Man application is viable in AMODE 24. Profile B (AMODE 31, J4 JOB08335) is a
  documented fallback only, never adopted automatically: if a real Pac-Man module exposes an AMODE 24 limitation,
  stop and report before changing profile or source.
