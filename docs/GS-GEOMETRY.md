# MVS-GS geometry integration - design (APPROVED 2026-10-09, D32)
Part of MVS-GS (still open, uncommitted since checkpoint fbc52ab). Evidence: docs/evidence/gs-e12-geometry.md (probe E12,
runs A-D). Study model: tools/geometry_model.py (mock-ups + exact byte counts with the MVS-GS encoder). Nothing in
PACMAN is changed by this document.

## 1. What the live study established
| Canvas | How the user gets it | Physical window before connecting | Live |
|---|---|---|---|
| 80 x 24 | model 2, or any model c3270 cannot fit (silent downgrade) | any | PASS |
| 80 x 32 | `c3270 -model 3` | >= 36 rows | PASS |
| 80 x 43 | `c3270 -model 4` (c3270 default) | >= 46 rows | PASS |
| 132 x 27 | `c3270 -model 5` | >= 30 rows x 132 cols | PASS |
| 120 x 27 | `c3270 -model 2 -oversize auto` (IBM-DYNAMIC) | the usual 120 x 30 | PASS |
- The canvas is fixed when c3270 connects (terminal type + Query Reply); a resize never renegotiates it, and shrinking
  the window below it corrupts the curses display for the rest of the session (c3270 limit, run A).
- TK4- TSO already switches every session with a larger alternate size to it at logon (its own Query + Erase/Write
  Alternate): READY runs at 80x32 / 80x43 / 132x27 / 120x27. PACMAN's full screens go out as TPUT FULLSCR = a 3270
  Write, which keeps whatever size is active. Today that is harmless on 80-column canvases (the game sits at the top)
  and **corrupts the screen on 132x27 and 120x27** (80-column addresses in a wider buffer) - a latent defect of every
  TSC renderer (G1-GS), never seen live because all live checks ran on model 2 or 4.
- The maze stays 4x2 = 80 x 20 cells on every canvas: 4x2 is the only tile with square proportions on a 1:2 character
  cell (5x2 = 1.25x too wide, 6x2 = 1.5x; 6x3 would be square but needs 120 x 30 for the maze alone). With the same font
  the maze is therefore physically the same size everywhere; a larger canvas buys **centring and HUD space**, not a
  bigger maze. A physically larger maze (6x3, 120 x 30 + text) would need a taller oversize canvas (> 4095 cells:
  14-bit addressing) and about 3.5 KB streams - out of scope, noted for the future.

## 2. Comparison (exact bytes: start position, 3 ghosts, message = the largest full screen seen)
| Canvas | Maze position (rows x cols) | Maze share | HUD | Full screen | For the 120 x 30 window |
|---|---|---|---|---|---|
| 80 x 24 (current GS) | 1-20 x 1-80 | 83% | rows 21-23 only | 1684 | fits, but anchored top-left; 40 columns and 6 rows unused |
| 80 x 32 | 6-25 x 1-80 | 62% | rows 1-4 above, 27-30 below | 1705 | does not fit (needs >= 36 rows) |
| 80 x 43 | 12-31 x 1-80 (vertically centred) | 47% | rows 2-9 above, 34-41 below | 1720 | does not fit (needs >= 46 rows) |
| 132 x 27 | 4-23 x 27-106 (26 columns each side) | 45% | side panels + rows 25-27 | 1870 lean / 1995 rich | does not fit (needs 132 cols) |
| **120 x 27 IBM-DYNAMIC** | **4-23 x 21-100 (20 columns each side)** | 49% | side panels + rows 25-27 | **1870 lean** / 1995 rich | **exactly the usual window** |
Recommendation: **120 x 27 IBM-DYNAMIC as the primary large canvas** (matches the usual window, maze truly centred,
room for a real HUD), with the same "wide" layout serving 132 x 27 (wider margins); 80x32 / 80x43 get a "tall" layout
(maze vertically centred, HUD above/below); 80 x 24 = the current MVS-GS renderer, the fallback for everything else.

## 3. Proposed wide layout (120 x 27; 132 x 27 identical with the maze at columns 27-106)
```
01|                                                                  (SF protected at (1,1))
02|                                                     P A C - M A N
03|
04|                    ┌──────────────────────────────────────────────────────────────────────────────┐
05|  SCORE   0000      │  ┌────────────────────────────────┐      ┌────────────────────────────────┐  │  GHOSTS  AI3
06|                    │  │▄█▀  •   •   •   •   •   •   •  │      │ •   •   •   •   •   •   •  ▄°°▄│  │
07|  PELLETS 098       │  │▀█▄                             │      │                            █▀█▀│  │  ∩ 19,09
08|                    │  │ •  ┌──────┐ •  ┌──────────┐ •  │      │ •  ┌──────────┐ •  ┌──────┐ •  │  │  ∩ 02,09
09|  TURN    000       │  │    └──────┘    └──────────┘    └──────┘    └──────────┘    └──────┘    │  │  ∩ 19,02
10|                    │  │ •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •  │  │
11|  LAST    R MOVED   │  │                                                                        │  │
12|                    │  │ •  ┌──────┐ •  ┌──┐ •  ┌──────────────────────┐ •  ┌──┐ •  ┌──────┐ •  │  │
13|  STATE   READY     │  │    └──────┘    │  │    └───────┐      ┌───────┘    │  │    └──────┘    │  │
14|                    │  │ •   •   •   •  │  │ •   •   •  │      │ •   •   •  │  │ •   •   •   •  │  │
15|  LIVES   ⊂ ⊂ ⊂     │  │                │  │            │      │            │  │                │  │
16|                    │  │ •  ┌──────┐ •  │  └───────┐ •  │      │ •  ┌───────┘  │ •  ┌──────┐ •  │  │
17|                    │  │    └──────┘    └──────────┘    └──────┘    └──────────┘    └──────┘    │  │  U D L R ENTER
18|                    │  │ •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •  │  │  Q QUIT  PA2
19|                    │  │                                                                        │  │
20|                    │  │▄°°▄ •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •  ▄°°▄│  │
21|                    │  │█▀█▀                                                                █▀█▀│  │
22|                    │  └────────────────────────────────────────────────────────────────────────┘  │
23|                    └──────────────────────────────────────────────────────────────────────────────┘
24|
25|                    INVALID COMMAND X            (or the end banner YOU WIN / GAME OVER / QUIT / END OF INPUT)
26|                    COMMAND ===> _
27|
```
- Maze: rows 4-23, columns (W-80)/2+1 .. +79 = 21-100 (120) / 27-106 (132); same tiles, sprites, contours as MVS-GS.
- Left margin (columns 3-18): SCORE, PELLETS, TURN, LAST (command + result, which the G0 status line carried),
  STATE, LIVES as Pac-Man icons (CP310 X'9B'), one turquoise line each ("lean HUD").
- Right margin (columns W-17 ..): GHOSTS + AI level, one line per ghost in its colour (CP310 X'AA' + position), keys.
- Row 2: title. Row 25: message / end banner (blinking red message, reverse banner as MVS-GS). Row 26: command field
  (aligned with the maze). The G0 status line is dropped in the wide layout (all its fields are in the HUD).
- Tall layout (80 x 32 / 80 x 43): maze vertically centred (80x43 rows 12-31; 80x32 rows 6-25), score/pellets/turn/
  lives on one line above, G0 status line + message + command + help below (tools/geometry_model.py mock-ups).
- Byte budget: lean HUD 1849-1870 bytes (limit 2048, the MVS-GS size guard stays). The rich HUD (labels and values on
  separate lines, title row larger, G0 line kept) costs 1976-1995 bytes: only with a larger transport buffer (section
  6, optional E13).
- Partial updates and ticks: unchanged in size (the same 8 cells per changed logical cell + the changed HUD lines).

## 4. AUTO selection (no new or reordered capability query)
- New option `CANVAS(AUTO|DEFAULT)` (PARM column 18, absent = DEFAULT, CLIST default AUTO).
- The buffer size is decided ONCE, before the query, from the requested options only: COLOR(AUTO) and CANVAS(AUTO) ->
  the terminal's alternate size (whatever it is); anything else (CANVAS(DEFAULT), COLOR(YES), batch/TSD) -> 80 x 24.
- Its dimensions come ONLY from the Query Reply the game already requests with COLOR(AUTO): PACQRY (pure) is extended
  to also return the implicit-partition sizes (QCode X'A6', as decoded by E12; 80 x 24 when absent). No other change to
  the query, its order or its handling.
- Layout choice inside that buffer (after the existing SCALE/HILITE/GLYPHS resolution): scaled 4x2 and W >= 120,
  H >= 27 -> wide layout; scaled and W = 80, H >= 32 -> tall layout; every other case (80 x 24 buffer, SCALE(NO)/(3),
  no highlighting, size guard...) -> the existing 80 x 24 screens **placed at an origin centred in the buffer** (origin
  (1,1) when the buffer is 80 x 24). Every renderer addresses cells as (origin + row/column) in a W x H buffer, so the
  G1-G4 and 80 x 24 GS streams are byte-identical when W x H = 80 x 24.
- Buffers above 4095 cells (a very large oversize window) use 14-bit buffer addresses (announced by the reply, X'81'
  flags) instead of the 12-bit codes; all five live canvases are below 4095.
- TSD dry run (no query): column 18 = a simulated canvas (e.g. `W` 120x27, `X` 132x27, `T` 80x43, `M` 80x32) so every
  layout and every centred fallback is regression-tested byte for byte against an independent model.

## 5. Entering and leaving the alternate size safely (the D28 constraint)
D28: after the capability query TSO holds NOEDIT output until the first AID, so nothing may need a NOEDIT size switch
between the query and the user's first input. Sequence:
1. FSON.
2. Still **before the query**: one TPUT NOEDIT of `X'7E' + WCC` (Erase/Write Alternate, no data) when the buffer is to
   be the alternate size (section 4), else `X'F5' + WCC` (Erase/Write, 80 x 24). This sets the size deterministically,
   whatever TSO left (its own logon EWA, or the default after a CLEAR at READY). Model-2 sessions: alternate = 80 x 24.
3. Query + reply (COLOR(AUTO) only) -> buffer dimensions -> layout and origin (section 4). No further size switch.
4. First screen: TPUT FULLSCR (a Write) laid out for that buffer, with the D25 clear prefix (it nulls the whole buffer
   of any size) - exactly the transport used today.
5. Partial screens and ticks: Write X'F1' (SENP) unchanged; they keep the size.
6. Every later FULL screen (PA2 / empty ENTER redraw, resend after a failed partial, the end screen): TPUT NOEDIT with
   the same command as step 2 (`X'7E'` or `X'F5'`) + the stream. This re-establishes the size after a CLEAR (CLEAR
   resets the terminal to 80 x 24 and is not delivered to the program, E4; PA2 then repairs the screen, as today). They
   follow an AID, so D28 does not hold them.
7. Leaving: unchanged (end screen, 3 s pause, FSOF); TSO's next line-mode output sets its own size again (observed in
   every E12 run: TSO sends its own Erase/Write Alternate).

## 6. PACFSIO change required (decision for the user)
One new op, keeping SEND/SENP/RECV/RECT/QRY/FSON/FSOF untouched: `SENX` = TPUT NOEDIT of the caller's buffer as is, its
first byte being the 3270 command chosen by PACPLAT (X'7E' Erase/Write Alternate, X'F5' Erase/Write); used for the
2-byte mode switch (step 2) and for the later full screens (step 6). Same 2048-byte buffer (SENDBUF unchanged), same
length handling (AH, never `LA 0,n(0)`), same ESTAE. Optional, only if the rich HUD is wanted: a probe E13 first proves
that TSO/VTAM pass a 4096-byte TPUT (FULLSCR and NOEDIT; PACFSC already has a 4 KB buffer), then PAC-DS / PACFSIO grow
to 4096. Not needed for the lean HUD.

## 7. Model 3/4 sessions (TSO already in the alternate size at logon)
They become explicit: step 5.2 switches (again) to the alternate size, the reply announces 80x32 / 80x43 and the tall
layout is drawn for exactly that buffer (or, when not scaled, the 80 x 24 screen centred vertically). Nothing relies on
TSO's own logon behaviour any more.

## 8. The latent wide-buffer corruption (model 5 / IBM-DYNAMIC)
Fixed for every renderer by sections 4 and 5: no screen is ever sent into a buffer whose size and width the renderer
does not know. CANVAS(DEFAULT) (and every direct call without column 18) switches to 80 x 24 with `X'F5'` before the
first screen; CANVAS(AUTO) knows W x H from the reply and centres the 80 x 24 screens when they are used. The renderer
data streams for an 80 x 24 buffer are unchanged byte for byte (only the transport adds the 2-byte switch and the
command byte of later full screens), so the G1-G4 and GS regressions stay exact.

## 9. Fallback chain
CANVAS wide/tall -> 80 x 24 MVS-GS (4x2, centred in the buffer) -> G4 GRAPHIC -> BASE -> CLASSIC -> line mode.
Triggers: no reply / COLOR(YES) / CANVAS(DEFAULT) -> 80 x 24 buffer; a buffer too small or too narrow for the wide/tall
layouts -> the 80 x 24 screens centred in it; size guard overflow on a wide/tall screen -> the centred 80 x 24 GS screen
for the rest of the game; 80 x 24 overflow -> G4 (existing guard); any send error -> existing fallbacks.

## 10. Operational restriction (README, CLIST help)
Size the terminal window BEFORE connecting: c3270 fixes the canvas at connect time (and silently drops to 80 x 24 when
the window is too small for the requested model). Do not shrink the window below the negotiated canvas during the
session (the c3270 display corrupts and does not recover). For the 120 x 30 window: `c3270 -model 2 -oversize auto
localhost:3270`.

## 11. Points for approval
1. 120 x 27 IBM-DYNAMIC wide layout as the primary large canvas (maze rows 4-23, columns 21-100), same layout for
   132 x 27 (columns 27-106); tall layout for 80 x 32 / 80 x 43; 80 x 24 GS as fallback.
2. Lean HUD within the existing 2048-byte limit (G0 status line dropped in the wide layout) - or E13 first and the rich
   HUD with a 4 KB buffer.
3. `CANVAS(AUTO|DEFAULT)`, PARM column 18, absent = DEFAULT; buffer size decided before the query from the options,
   dimensions only from the existing Query Reply (PACQRY returns the X'A6' sizes); every renderer drawn at an origin in
   a W x H buffer (80 x 24 screens centred); TSD simulated canvases for testing.
4. The entry/leave sequence of section 5 (one size switch before the query; FULLSCR first screen; the same EWA/EW
   command for later full screens; partials unchanged).
5. PACFSIO: new op SENX only (section 6). This lifts the "PACFSIO untouched" rule for this one op.
6. The latent wide-buffer defect fixed for all renderers via the 80 x 24 `X'F5'` path (section 8).
7. Operational restriction documented (section 10).

## 12. Approval (user, 2026-10-09)
All seven points approved: 120 x 27 IBM-DYNAMIC primary (maze rows 4-23, columns 21-100, 20-column margins); 132 x 27
wide, 80 x 43 / 80 x 32 tall centred, 80 x 24 the universal GS fallback; compact side HUD (rich 1995-byte HUD NOT
implemented); CANVAS(AUTO|DEFAULT) in PARM column 18 (absent = today's behaviour, CLIST AUTO, only the established query
path); one size switch before the query (AUTO: Erase/Write Alternate; DEFAULT: Erase/Write); PACFSIO op SENX as the one
allowed extension (minimal; validated protocol code untouched; regression proving SEND/SENP unchanged); fallback chain
alternate canvas -> 80 x 24 GS -> G4 GRAPHIC -> BASE -> CLASSIC -> line mode, 2048-byte guard kept; operational rule in
README/CLIST; recommended launch `c3270 -model 2 -oversize auto localhost:3270`.
Additional requirements: core frozen; maze stays 80 x 20; full redraws re-establish the buffer size (deterministic PA2/
CLEAR recovery); partial redraws in the selected canvas' coordinates; end-screen pause in every geometry; 80 x 24 output
byte-identical on the DEFAULT/legacy path; tests for the model 2/3/4/5 and IBM-DYNAMIC Query Replies; explicit test that
an unsupported / too-small alternate geometry falls back safely to 80 x 24.
Future (NOT a GS dependency): probe E13 / 4 KB TPUT transport, as a graphics-ceiling investigation (richer HUD, 6x3 XL).

