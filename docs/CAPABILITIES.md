# Terminal / platform capability matrix (requirements sec. 28) - FINAL for 2.0-MVS-MAX (MVS-G8, 2026-10-14)
First version MVS-G0 (2026-10-07); every row below is now closed: CONFIRMED (used by 2.0), NOT SUPPORTED / NOT
AVAILABLE (closed negative with evidence) or NOT TESTED (other emulators, outside the validated environment).
Environment: Hercules 4.00 (TK4- bundled build, plain TN3270 server; Homebrew 4.9.1 installed but not running), MVS 3.8J TK4-, CPU 3033 S/370, 16 MB, c3270/s3270 4.5ga6 (Homebrew,
curses-wide, iconv), local 3270 devices 00C0-00C6 (VTAM), TSO/VTAM line mode.
Status: CONFIRMED = proven on this installation (evidence named). No row is PENDING at 2.0.

| Capability | Status | Evidence / test | Renderer |
|---|---|---|---|
| 3270 model / screen size | CONFIRMED 80 x 24 | E5 Query Reply usable area (JOB 156) | All |
| Alternate screen size (Erase/Write Alternate) | CONFIRMED 80x32 (model 3), 80x43 (model 4), 132x27 (model 5), 120x27 (IBM-DYNAMIC, `-oversize auto`) | E12 live (JOBs 202/203, docs/evidence/gs-e12-geometry.md); game live on 120x27 (JOB 207 build) | GS |
| Canvas negotiation | CONFIRMED fixed at connect | c3270 picks the model from the window at startup (silent downgrade to model 2 if too small); resize never renegotiates; shrinking below the canvas corrupts the c3270 display (unsupported) | GS |
| TSO line mode in the alternate size | CONFIRMED | TK4- TSO issues its own Erase/Write Alternate at logon; PACMAN now sets the size itself before the query (D32) | GS |
| TSO line-mode output + `STLINENO LINE=1` fresh screen | CONFIRMED | live c3270 validation (MVS-8, JOB 138 build; G0 metrics live: 4 frames, 3 clears) | G0 |
| TSO terminal macros TPUT/TGET/STFSMODE/STLINENO/TCLEARQ | CONFIRMED (assemble) | IFOX00 JOB 137, docs/evidence/g0-tso-macros-probe.txt (STFSMODE has usermod ZP60009) | G1+ |
| TSO full-screen (TPUT FULLSCR/TGET ASIS) | CONFIRMED | E2/E3 live: screen stays until ENTER, AIDs received, PA2 reshow works (twice), no `***` (JOBs 153-154) | G1+ |
| TPUT/TGET in batch TMP | CONFIRMED no-op | JOB 129, mvs8-tputprobe.txt: full-screen output cannot be regression-tested in batch | - |
| Extended colour (3279), 7 colours | CONFIRMED | E3/E4 live: SA X'2842F1'-'F7' shown blue, red, pink, green, turquoise, yellow, white; default green (JOBs 154-155) | G1 |
| Reshow keys | PA2 CONFIRMED, CLEAR NOT DELIVERED | E3: PA2 redraw twice; E4: CLEAR blanks the screen and never reaches TGET (handled by TSO); redraw after CLEAR = PA2 | G1+ |
| Highlighting (reverse, blink, underscore) | ANNOUNCED (QCode 87); CONFIRMED live (G2) | docs/G2-HIGHLIGHT.md; JOB 164 data streams equal the model; c3270 live check passed | G2 |
| Character attributes (SA order) | USED (colour SA X'42', highlight SA X'41') | G1 and G2 live | G2/G4 |
| APL / graphic character set (GE order) | CONFIRMED (E9 live; used by G4) | QCode 85: GE flag, base 697/CP037, LCID F1 = 963/CP310; GE X'08' and SA X'43' F1 equivalent in c3270; box-drawing maze rendered (docs/evidence/g4-probe-analysis.md) | G4 |
| Programmed Symbols | NOT SUPPORTED (c3270) | E10 live (JOB 196, D30): QCode 85 load bytes 00000000; Load PS traced `unsupported ID 0x06`, no inbound; SA 43 to the loaded LCID = base set (docs/evidence/g5-probe-analysis.md) | G5 closed negative |
| Triple-plane PS | NOT APPLICABLE | depends on PS (G5 negative, D30) | G6 blocked |
| Vector / host graphics (GDDM, GOCA) | NOT AVAILABLE (G7 closed negative, D42) | E5 Query Reply has no graphics-related codes; c3270 documents no graphics; no GDDM on TK4- (JOB 301: catalog + LNKLST00 + LPALIB, docs/evidence/g7-gddm-check.md) | G7 closed |
| Capability detection (Read Partition Query) | CONFIRMED | E5: TPUT NOEDIT WSF, reply AID 88 at TGET ASIS without user action; codes 80 81 84 85 86 87 88 95 A1 A6 | G1, G9 |
| Colour renderer TSC (G1) | CONFIRMED | live c3270: clean full-screen colour game, moves, INVALID, PA2, Q (JOBs 157/161) | G1 |
| Audible alarm (WCC alarm bit) | CONFIRMED (E15 live) | X'04' in the WCC reaches c3270 through SENX, SEND and SENP and rings the Mac terminal bell (Terminal "Audible bell" on); 3 bells audible back to back and 0.5 s apart; docs/evidence/s1-e15-alarm.md | S1 |
| Partial screen update (Write X'F1' + TPUT NOEDIT) | CONFIRMED (probe E6, live) | docs/evidence/g3-probe-analysis.md; ASIS variant erases the screen | G3+ |
| Idle animation (visual tick between inputs) | CONFIRMED with COLOR(YES); with COLOR(AUTO) only after the first input (TSO holds NOEDIT output after the capability Query Reply; investigation closed, D28) | docs/G3-PARTIAL.md, docs/evidence/g3-game-timeline*.txt | G3 |
| Viable update rate | CONFIRMED: REALTIME one write per 150 ms quantum (125 ms with SPEED(FAST)) on an absolute grid, no skipped period, lateness median 5-7 ms; 2.0 default median 86 bytes per quantum write (partial redraw, G3) | docs/BENCHMARKS.md, docs/evidence/rp-live.md, rp3-fast-live.md, g8-live.md; G3: docs/G3-PARTIAL.md | G3/RT/G8 |
| Real-time input (PF7/8/10/12 arrows since MVS-10 - PF11 until 2.0-MVS-MAX, D46; PF9 pause, keyboard restore per write) | CONFIRMED | probe E14, docs/evidence/rt3-live.md, rp-live.md | RT |
| Alarm patterns (separate bells, timed by quanta) | CONFIRMED (S2) | docs/evidence/s2-live.md: 1-4 bells per event, 296-302 ms apart, heard as separate | S2 |
| Automatic maximum profile (G9) | CONFIRMED (G8.4): the CLIST with no operand selects colour full-screen, highlighting, GRAPHIC glyphs, 4x2 scale, partial redraw, 120 x 27 wide layout, REALTIME, ARCADE, PATTERN; 180/180 live writes = model | docs/evidence/g8-live.md, docs/G8-RELEASE.md (D43) | G8/G9 |

## Presentation cost baseline (G0 renderer, measured on Hercules, JOB 146, docs/evidence/g0-metrics-altdisplay.txt)
Per frame: 1 status line (61 chars) + 10 board rows (200 chars) [+ 1 ghost line: 8 chars with 2 ghosts, 17 with 3].
TSO adds 1 prompt line (16 chars) per read and 1 screen clear per frame after the first.

| Run | Frames | Lines | Characters | Clears | Lines / frame |
|---|---|---|---|---|---|
| MOVES, batch, 1 ghost | 14 | 160 | 3 726 | 0 | 11.4 |
| P2N3, batch, 3 ghosts | 65 | 785 | 18 124 | 0 | 12.1 |
| MULTI, TSO, 3 ghosts | 19 | 252 | 5 640 | 18 | 13.3 |
| TSORDR, TSO, 1 ghost (with one redraw) | 4 | 53 | 1 163 | 3 | 13.3 |
Totals include the banner and the four end lines. Every frame is redrawn completely (no partial redraw yet: G3).

## Visual differences per emulator (MVS-G4 glyph profiles, docs/G4-GLYPHS.md section 7)
| Emulator | GRAPHIC result | Status |
|---|---|---|
| c3270 4.5ga6, UTF-8 terminal (macOS) | CP310 mapped to Unicode; continuous box lines (font-dependent) | CONFIRMED live (E9) |
| s3270 / x3270if `Ascii()` | same Unicode text | CONFIRMED (E9 capture) |
| c3270 without Unicode / ASCII line-drawing mode | boxes become `+ - \|` (x3270 source, table `apla2uc`); APL symbols may be blank | NOT TESTED |
| x3270, wc3270, commercial emulators, real 3279 with APL | GE expected where the GE flag is announced; AUTO = CLASSIC otherwise | NOT TESTED |

## 2.0-MVS-MAX: what the defaults select (D43; no PROFILE keyword - the AUTO chain is the maximum mode)
| What the terminal answers (Read Partition Query) | Selected by the 2.0 defaults | Validated |
|---|---|---|
| colour + highlighting + GE / APL set, alternate size 120 x 27 or 132 x 27 (c3270 `-model 2 -oversize auto` / `-model 5`) | full-screen colour, GRAPHIC glyphs, 4x2 maze centred with side panels, partial redraw, REALTIME, ARCADE, PATTERN alarm | live G8.4 (120 x 27), GS live (132 x 27) |
| the same, alternate size 80 x 32 / 80 x 43 | 4x2 maze centred vertically | GS live (E12) |
| the same, 80 x 24 only | 4x2 maze 80 x 20 + compact status line | Hercules TSD (JOBs 308-312), GS live |
| colour + highlighting, no GE / APL set | GLYPHS(AUTO) = CLASSIC: the G3 colour look (`#` walls, `.` pellets, highlighted sprites), not scaled, partial redraw, REALTIME | Hercules TSD, G4 PACQRY cases (reply with ALT cleared -> C) |
| colour + GE, no highlighting | GRAPHIC sprites with `#` walls (no reverse video), not scaled | Hercules TSD |
| no colour / no valid Query Reply (D40: a pending `***`, a monochrome terminal) | monochrome line mode, TURN play | Hercules (PACQRYT sequences, JOB 309), D40 live (rp-live.md) |
| a screen too big for the 2048-byte TPUT budget | size guard: G4 glyph look for that screen set | Hercules TSD (scale T runs) |
Explicit compatibility modes keep every earlier look: `RULES(CLASSIC)` (1.0-MVS game), `PLAY(TURN)`, `CANVAS(DEFAULT)`,
`SCALE(NO|3)`, `GLYPHS(CLASSIC|BASE)`, `COLOR(NO)`, `SOUND(NO)`, `ALARM(SINGLE)`. Batch (cards) is the reference and
fallback; a PARM without the RULES column is CLASSIC (PACMAIN unchanged).

## Ceilings of the validated environment (closed negative)
- Programmed Symbols / triple-plane PS: not supported by c3270 (G5 D30, G6 blocked).
- Host graphics (GDDM / GOCA): not in the Query Reply, not in c3270, no GDDM on TK4- (G7 D42).
- Music / PCM audio: not in the 3270 data stream; only the alarm (S1/S2). A client companion (S3/S4) is optional and
  not part of 2.0.
