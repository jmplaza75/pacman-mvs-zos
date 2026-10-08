# MVS-G1 colour renderer - design (2026-10-07, for approval; nothing implemented yet)
Requirement (master doc sec. 26, MVS-G1): detect colour; palette for walls, pellets, Pac-Man, ghosts and HUD;
reverse/highlight/blink only where they help readability (not used in G1); keep monochrome. Acceptance: the game works
correctly with and without colour. Basis: capabilities confirmed by probes E1-E5 (docs/CAPABILITIES.md).

## 1. Modes and selection (the renderer is separate and can be switched off)
| Mode | Input | Output | Status |
|---|---|---|---|
| BAT | SYSIN cards | SYSOUT text | unchanged: 1.0-MVS oracle |
| TSO | terminal line mode | text frames, `STLINENO` fresh screen | unchanged: **monochrome fallback** (G0) |
| TSC (new) | full-screen input field, TGET ASIS | 3270 colour screen, TPUT FULLSCR | G1 renderer |
- CLIST keyword `COLOR(AUTO|YES|NO)`, default AUTO, passed in PARM column 12 (`A`/`Y`/`N`); column 11 stays METRICS.
- PACPLAT INIT (TSO only): AUTO enters full-screen, sends the Read Partition Query and switches to TSC only if the reply
  has QCode X'86' (colour); YES skips the query; NO, a missing reply, or any TPUT/TGET error leaves the mode at TSO.
- Batch and all existing tests never enter TSC.

## 2. Modules (core PACGAME/PACMAP/PACAI and their copybooks untouched; PACREQ grows append-only)
- **PACFSIO** (assembler, PLATFORM, called only by PACPLAT): the validated E2/E3/E5 protocol as services FSON
  (TCLEARQ, STFSMODE ON,INITIAL=YES, STTMPMD ON), QRY (TPUT NOEDIT WSF + TGET ASIS), SEND (TPUT FULLSCR),
  RECV (TGET ASIS, retry on empty read), FSOF (STTMPMD OFF, STFSMODE OFF, STLINENO LINE=1). No-op outside TSO.
- **PACPLAT**: new ops FSON/QRY/SEND/RECV/FSOF wrapping PACFSIO; decides TSC vs TSO.
- **PACSCR** (new COBOL, DISPLAY layer): builds the whole 80x24 screen datastream from PAC-STATE (read-only).
- **PACDISP**: in TSC mode STAT/INVL/PRMT collect into PACSCR and one SEND per turn (on PRMT); END leaves full-screen
  (FSOF) and prints the usual end lines in line mode, so every mode ends with the same QUIT/TURNS/SCORE/LIVES lines.
- **PACINPT**: in TSC mode READ asks PACPLAT RECV and parses the inbound: AID ENTER X'7D' -> first non-blank byte of
  the input field, classified exactly as today (U/D/L/R/Q, case-insensitive); PA2 X'6E' (and any other AID) -> RDR
  (redraw, no turn). CLEAR is not delivered by TSO (E4): the screen comes back with PA2.

## 3. Screen layout (80 x 24, confirmed by E5) and palette (7 colours confirmed by E4)
| Rows | Content | Colour (SA X'2842..') |
|---|---|---|
| 1 | the G0 status line, unchanged text (`Txxx cmd result X= Y= S= L= G= V= ST=`) | turquoise F5 |
| 2 | `G2=..[ G3=..]` when 2-3 ghosts | turquoise F5 |
| 4-13 | board, 20 columns at column 31 | `#` blue F1, `.` white F7, `P` yellow F6, `G` red F2 |
| 16 | `INVALID COMMAND x` when needed | red F2 |
| 18 | `COMMAND ===>` + 1-byte unprotected input field, cursor inside | green F4 / default |
| 23 | `U D L R + ENTER   Q QUIT   PA2 REDRAW` | green F4 |
- Formatted screen (protected fields + one unprotected input field) so Read Modified returns only the typed command.
- One SA order per colour run (consecutive equal cells share one order); reset X'280000' at row ends.
- All ghosts are red in G1 (one rule, readable); per-ghost colours are a candidate for G2.

## 4. Tests (deterministic; batch remains the reference)
1. Oracle: BAT and TSO outputs byte-identical to 1.0-MVS (tests/test_g0.py), core frozen.
2. Dry-run renderer: mode TSD (batch, PARM) builds the same TSC screens but PACPLAT prints each datastream in hex
   instead of sending it; tests/ref_g1_screen.py, an independent Python renderer fed with the oracle frames, must produce
   the identical bytes (layout, palette, SA run-length, field and cursor orders) for several cases (1-3 ghosts, invalid
   command, death, win).
3. Live c3270 checklist: AUTO selects colour; walls/pellets/P/G/HUD in their colours; a few moves; invalid command
   message; PA2 redraw; Q ends with the usual end lines and READY; `COLOR(NO)` gives the G0 monochrome mode.

## 5. Metrics
METRICS keeps working: in TSC one frame = one TPUT; CHARS counts datastream bytes per frame (baseline vs G0 in
docs/CAPABILITIES.md).

## Out of G1 scope
Highlighting (G2), animation (G3), partial redraw (G3/G8), PF-key controls, charsets/PS (G4-G6), sound (S1+).
