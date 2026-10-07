# Terminal / platform capability matrix (requirements sec. 28) - first version, MVS-G0 (2026-10-07)
Environment: Hercules 4.9.1 (SDL Hyperion), MVS 3.8J TK4-, CPU 3033 S/370, 16 MB, c3270/s3270 4.5ga6 (Homebrew,
curses-wide, iconv), local 3270 devices 00C0-00C6 (VTAM), TSO/VTAM line mode.
Status: CONFIRMED = proven on this installation (evidence named); PENDING = must be tested in the phase that needs it;
NOT EXPECTED = documented as unsupported by the emulator, to be confirmed by a probe before being ruled out.

| Capability | Status | Evidence / test | Renderer |
|---|---|---|---|
| 3270 model / screen size | PENDING | c3270 runs with its default model (no profile); rows used by TSO not yet measured. G1 probe: query `show` in c3270 and a TSO line-count test | All |
| TSO line-mode output + `STLINENO LINE=1` fresh screen | CONFIRMED | live c3270 validation (MVS-8, JOB 138 build; G0 metrics live: 4 frames, 3 clears) | G0 |
| TSO terminal macros TPUT/TGET/STFSMODE/STLINENO/TCLEARQ | CONFIRMED (assemble) | IFOX00 JOB 137, docs/evidence/g0-tso-macros-probe.txt (STFSMODE has usermod ZP60009) | G1+ |
| TPUT/TGET in batch TMP | CONFIRMED no-op | JOB 129, mvs8-tputprobe.txt: full-screen output cannot be regression-tested in batch | - |
| Extended colour (3279) | PENDING | c3270 is a colour 3279 emulator; host side needs a full-screen datastream (TPUT FULLSCR) - G1 probe | G1 |
| Highlighting (reverse, blink, underscore, intensity) | PENDING | field/character attributes via SF/SFE/SA orders - G1/G2 probe | G2 |
| Character attributes (SA order) | PENDING | G2 probe | G2/G4 |
| APL / graphic character set (GE order) | PENDING | c3270 maps APL characters to Unicode in wide-curses builds - G4 probe | G4 |
| Programmed Symbols | NOT EXPECTED | x3270 family does not implement PS loading (requirements sec. 29); confirm via Query Reply in G5 probe | G5/G6 |
| Triple-plane PS | NOT EXPECTED | depends on PS | G6 |
| Vector / host graphics (GDDM, GOCA) | NOT EXPECTED | x3270 documents no graphics support; GDDM not known on TK4- (check libraries in G7) | G7 |
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
