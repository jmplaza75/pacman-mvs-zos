# MVS-G3 partial redraw and character animation - design and result (2026-10-08, CLOSED: tag mvs-g3)
Master document (docs/requirements/..._v4.docx): sec. 25 row G3 "animation by characters: alternate glyphs/frames
(Pac-Man mouth, ghosts); dependency: fast enough partial redraw"; sec. 26 MVS-G3 "update only changed cells, avoid
clearing the screen, measure traffic and flicker, keep the full render as a diagnostic mode; acceptance: smoother, state
consistent"; MVS-G0 "separate visual tick from logical tick; animation must not alter collisions or logical speed".
Scope: presentation only, TSC mode only. PACGAME/PACMAP/PACAI untouched; no autonomous ghosts, no real time.

## Transport (probe E6, docs/evidence/g3-probe-analysis.md)
Partial update = explicit 3270 Write command X'F1' as first byte + TPUT NOEDIT (PACFSIO service SENP). TPUT ASIS erased the
rest of the screen (variant A, discarded). Full screens still use TPUT FULLSCR (G1/G2, unchanged).

## Options (all separate; defaults keep G2 behaviour for direct calls)
- CLIST `REDRAW(PARTIAL|FULL)` default PARTIAL -> PARM column 15 `P`/`F`; anything but `P` = full (diagnostic and reference).
- CLIST `ANIM(AUTO|YES|NO)` default AUTO -> PARM column 14 `A`/`Y`/`N`. AUTO = YES in TSC (the partial send is proven, there
  is nothing to detect); outside TSC always NO. ANIM works with FULL too (alternating glyphs, full screens, no idle ticks).
- Partial redraw is an internal optimisation independent of ANIM (REDRAW P with ANIM N sends partial screens, same glyphs).
- Fallback: a failing partial TPUT (RC <> 0) makes PACPLAT set REDRAW F and ANIM N, tell PACDISP (REQ-SENDST R) and the
  whole screen is sent instead; line mode fallback of G1 is unchanged.

## Modules
- PACSCR: with REDRAW P every screen is first composed as a virtual 24x80 image (char, colour, highlight per cell) by the SAME
  paragraphs that build the full stream (a mode switch redirects PUT-SBA/PUT-COLOUR/PUT-HILITE/PUT-TEXT/PUT-CELL into the image).
  Full screen when nothing is known (first screen) or the last input was a redraw request (empty ENTER, PA2); else only the
  cells that differ from the image on the terminal are sent. Ops PRMT, TICK, FULL.
- PACDISP: SCR-PRMT / SCR-TICK / SCR-RESEND. PACPLAT: SEND-PART, RECT idle polling, option resolution. PACFSIO: SENP, RECT.
- PACMAIN (driver) PARM columns 14-15 and IDLE-TICK; PACINPT: idle tick = REQ-KIND TCK (in TSD dry runs the card `+`).
- Copybooks: PACREQ (+REQ-ANIM, REQ-REDRAW, REQ-SENDST), PACDS (+DS-KIND F/P/T), PACPAL (glyphs C/O and G/W).

## Stream formats (TSD prints them; tests/ref_g3_screen.py builds them independently)
- Partial (DS-KIND P): WCC C3; runs of changed cells in address order (SBA at the start of a run and at the start of every
  row; SA colour / SA highlight only when they change, carried over between runs; blanks are colour 0 -> `28 42 00`); then the
  input field cell (row 18 col 15): SBA, IC, SA colour, [SA underscore], blank, [SA reset]; then `28 00 00`.
  TPUT adds X'F1' in front (not part of the DS, not printed by TSD).
- Tick (DS-KIND T): WCC C2 (no reset MDT, so a command being typed is not lost), changed cells only, `28 00 00`; nothing is
  sent if nothing changed.
## Animation and the visual tick
- Visual frame VIS alternates at every logical screen and every tick: frame 0 = `C`/`G`, frame 1 = `O`/`W` (Pac-Man mouth, ghost
  feet). The game state is never read differently: mapping `C`,`O` -> `P` and `W` -> `G` gives exactly the G2 image.
- Idle tick: with ANIM Y + REDRAW P, PACFSIO RECT polls the terminal every 0.5 s (TGET ASIS,NOWAIT: R15 0 input, 4 none, else error;
  R1 is not used when R15 = 4); while no key arrives PACMAIN asks PACDISP for
  a TICK (glyph frame only). No call reaches PACGAME: logical turns happen only when the user presses ENTER, so collisions and
  logical speed are untouched. After 5 minutes without input the old fallback applies.
## How "mechanics unchanged" is shown (tests/test_g3.py)
core frozen + the 25 oracle blocks of 1.0-MVS byte-identical + ANIM(NO)/FULL streams equal the G2 model + for the real output
the ANIM(YES)/FULL streams differ from ANIM(NO)/FULL only in glyph bytes (P->C/O, G->W) + the game model feeding ref_g3 is the same
independent model of all earlier phases.
## Results (Hercules JOB 169, final build JOB 188; 61 steps RC 0000; no compiler warnings)
199 TSC streams (full, partial, tick) identical to the independent model. Traffic, same moves, bytes sent:
MOVES 9005 full -> 1678 partial; MULTI 12155 -> 2700 (4.5x less); DIE1 16917 -> 2287. Idle ticks cost 35 bytes each (class).
Flicker: judged live (partial writes do not erase or repaint untouched cells).
## KNOWN LIMITATION (COLOR(AUTO) and the idle animation)
In this TK4-/MVS 3.8J + TSO + c3270 environment, COLOR(AUTO) performs a capability Query Reply that leaves the idle ticks held
until the first AID. After the first input the animation works normally. With COLOR(YES) HILITE(YES) the query is skipped and the
animation starts immediately. This is a known limitation of the TSO environment/protocol investigated, not a fault of the game
mechanics or of the G3 renderer.
Recommended on TK4-/c3270 for immediate idle animation: `EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'COLOR(YES) HILITE(YES)'`.
COLOR(AUTO) stays the default to keep the G1/G2 detection and its safe fallback to line mode.

## How it was found (details: docs/evidence/g3-tick-trace.md)
1. Live: no idle ticks at all -> RECT used `TGET ASIS` (default WAIT, blocking); fixed with `TGET ASIS,NOWAIT` (macro checked).
2. Live: ticks only after the first input. Probes: E7 is VOID (its tick TPUT length was 1, `LA 0,1(0)`); E6 (exact) is a positive control;
   E8 R0 = E6 byte for byte at the terminal, so E6/R0 visual differences were c3270/curses repaint, not MVS.
3. Real game, both sides traced (in-memory TICKTRACE/RECTRACE in PACPLAT + c3270 -trace + presentation-space sampler over -scriptport):
   PACSCR alternates, every tick is handed to SENP with the right 21 bytes and TPUT RC 0, but TSO delivers none of them to the terminal
   until the first AID, then releases the whole backlog; afterwards ticks arrive every ~0.52 s. COLOR(YES) (no query) -> ticks from the start.
4. Hypotheses tried and refuted, one build each: `TPUT ... BREAKIN` for ticks (JOB 183); `TCLEARQ INPUT` after the query (JOB 185);
   `FSOF` + `FSON` after the query (JOB 187). All withdrawn.
5. The investigation is CLOSED deliberately here: the residual behaviour belongs to TSO's internal state after the Query Reply and is not
   worth enlarging G3 further. The diagnostic instrumentation was removed; the final build (JOB 188) equals the JOB 184/186 state.
Verified in the presentation space: the input field keeps a typed character during ticks, the cursor does not move, no logical move
happens before ENTER, exactly one move after it.

## Compiler note (D27)
IKFCBL00 gives IKF4072I-W for any paragraph performed without THRU whose LAST sentence is an IF (even IF/ELSE). Such paragraphs end
with `MOVE 0 TO WS-NOP.` in PACSCR.
