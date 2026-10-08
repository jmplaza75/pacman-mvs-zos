# Terminal / platform capability matrix (requirements sec. 28) - first version, MVS-G0 (2026-10-07)
Environment: Hercules 4.00 (TK4- bundled build, plain TN3270 server; Homebrew 4.9.1 installed but not running), MVS 3.8J TK4-, CPU 3033 S/370, 16 MB, c3270/s3270 4.5ga6 (Homebrew,
curses-wide, iconv), local 3270 devices 00C0-00C6 (VTAM), TSO/VTAM line mode.
Status: CONFIRMED = proven on this installation (evidence named); PENDING = must be tested in the phase that needs it;
NOT EXPECTED = documented as unsupported by the emulator, to be confirmed by a probe before being ruled out.

| Capability | Status | Evidence / test | Renderer |
|---|---|---|---|
| 3270 model / screen size | CONFIRMED 80 x 24 | E5 Query Reply usable area (JOB 156) | All |
| TSO line-mode output + `STLINENO LINE=1` fresh screen | CONFIRMED | live c3270 validation (MVS-8, JOB 138 build; G0 metrics live: 4 frames, 3 clears) | G0 |
| TSO terminal macros TPUT/TGET/STFSMODE/STLINENO/TCLEARQ | CONFIRMED (assemble) | IFOX00 JOB 137, docs/evidence/g0-tso-macros-probe.txt (STFSMODE has usermod ZP60009) | G1+ |
| TSO full-screen (TPUT FULLSCR/TGET ASIS) | CONFIRMED | E2/E3 live: screen stays until ENTER, AIDs received, PA2 reshow works (twice), no `***` (JOBs 153-154) | G1+ |
| TPUT/TGET in batch TMP | CONFIRMED no-op | JOB 129, mvs8-tputprobe.txt: full-screen output cannot be regression-tested in batch | - |
| Extended colour (3279), 7 colours | CONFIRMED | E3/E4 live: SA X'2842F1'-'F7' shown blue, red, pink, green, turquoise, yellow, white; default green (JOBs 154-155) | G1 |
| Reshow keys | PA2 CONFIRMED, CLEAR NOT DELIVERED | E3: PA2 redraw twice; E4: CLEAR blanks the screen and never reaches TGET (handled by TSO); redraw after CLEAR = PA2 | G1+ |
| Highlighting (reverse, blink, underscore) | ANNOUNCED (QCode 87); CONFIRMED live (G2) | docs/G2-HIGHLIGHT.md; JOB 164 data streams equal the model; c3270 live check passed | G2 |
| Character attributes (SA order) | USED (colour SA X'42', highlight SA X'41') | G1 and G2 live | G2/G4 |
| APL / graphic character set (GE order) | PENDING | character sets reply (QCode 85) announced; contents to decode in G4 | G4 |
| Programmed Symbols | NOT EXPECTED | QCode 85 present; loadable-set flags not decoded yet; x3270 family documents no PS loading - confirm in G5 | G5/G6 |
| Triple-plane PS | NOT EXPECTED | depends on PS | G6 |
| Vector / host graphics (GDDM, GOCA) | NOT ANNOUNCED | E5 Query Reply has no graphics-related codes; x3270 documents no graphics | G7 |
| Capability detection (Read Partition Query) | CONFIRMED | E5: TPUT NOEDIT WSF, reply AID 88 at TGET ASIS without user action; codes 80 81 84 85 86 87 88 95 A1 A6 | G1, G9 |
| Colour renderer TSC (G1) | CONFIRMED | live c3270: clean full-screen colour game, moves, INVALID, PA2, Q (JOBs 157/161) | G1 |
| Audible alarm (WCC alarm bit) | PENDING | c3270 rings the terminal bell on the WCC alarm - S1 probe | S1 |
| Viable update rate | CONFIRMED (turn-based) | one frame per input in TSO; cost measured below | G3/G8 |

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
