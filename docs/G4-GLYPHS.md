# MVS-G4 advanced glyphs - design (2026-10-08, APPROVED by the user on all five points; implementation in progress)
Requirement (master doc sec. 25 row G4, sec. 26 MVS-G4): try the graphic/APL characters available, alternative wall and
corner tiles, charset profiles, document visual differences per emulator. Acceptance: a look closer to the arcade without
Programmed Symbols. Dependency G3; fallback G3. Basis: probe E9 (docs/evidence/g4-probe-analysis.md): GE supported, second
set LCID X'F1' = charset 963 / CP310 APL, box drawing rendered live in c3270, no loadable PS.

## 1. Profiles (option of the TSC renderer only; BAT and TSO line mode never change)
| Profile | Walls | Pellet | Pac-Man frames | Ghost frames | Needs |
|---|---|---|---|---|---|
| CLASSIC `C` | `#` | `.` | `C` / `O` | `G` / `W` | nothing: exactly the G3 screens (reference, fallback) |
| BASE `B` | tiles `+ - \|` by neighbours | `·` X'B3' (CP037) | `C` / `O` | `G` / `W` | base set only (any 3270) |
| GRAPHIC `G` | box tiles `┌ ┐ └ ┘ ─ │ ├ ┤ ┬ ┴ ┼` by neighbours | `•` | `⊂` or `⊃` (facing) / `○` | `∩` / `⍝` | GE + CP310 (E9) |
- CLIST keyword `GLYPHS(AUTO|GRAPHIC|BASE|CLASSIC)`, default AUTO, passed in PARM column 16 (`A`/`G`/`B`/`C`; the first
  letters do not clash). PACREQ grows append-only (REQ-GLYPHS). A direct call without column 16 = `C` = G3 byte for byte.
- AUTO (resolved once in PACPLAT INIT, like HILITE, D26): `G` only if the COLOR(AUTO) Query Reply contains QCode X'85'
  with the ALT flag (X'80' in flags 1) AND a set descriptor with code page X'0136' (310); otherwise `C`. With COLOR(YES)
  there is no query, so AUTO = `C`. Outside TSC always `C`. TSD (dry run) honours `G`/`B` so they can be tested.
- Recommended on TK4-/c3270 (D28 + this phase): `EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC)'`.
  This is the explicit combination for immediate idle animation AND the GRAPHIC look: COLOR(YES) skips the capability query
  (so the D28 limitation does not apply), which also means AUTO cannot see GE and would choose CLASSIC.

Preview on LEVEL1 (from the model; colours as G1: walls blue, pellets white, Pac-Man yellow, ghosts red/pink/turquoise):
```
CLASSIC (C)            BASE (B)               GRAPHIC (G)
####################   +--------++--------+   ┌────────┬┬────────┐
#C.......##........#   |C·······++········|   │⊂•••••••├┤••••••••│
#.##.###.##.###.##.#   |·--·---·++·---·--·|   │•──•───•└┘•───•──•│
#..................#   |··················|   │••••••••••••••••••│
#.##.#.######.#.##.#   |·--·|·--++--·|·--·|   │•──•│•──┬┬──•│•──•│
#....#...##...#....#   |····|···++···|····|   │••••│•••├┤•••│••••│
#.##.###.##.###.##.#   |·--·+--·++·--+·--·|   │•──•└──•└┘•──┘•──•│
#..................#   |··················|   │••••••••••••••••••│
#.................G#   |·················G|   │•••••••••••••••••∩│
####################   +------------------+   └──────────────────┘
```

## 2. Wall tiles (presentation only, derived from the map read-only)
Mask of the four orthogonal wall neighbours (N=1, E=2, S=4, W=8; outside the board = no wall) -> 16-entry tile table per
profile in PACPAL. Walls never change at run time, so the masks can be computed once per screen composition (or once at
start) by PACSCR from MAP-CELL; nothing is written back to PAC-STATE.
| Mask | 0 | 1 N | 2 E | 3 NE | 4 S | 5 NS | 6 ES | 7 NES | 8 W | 9 NW | 10 EW | 11 NEW | 12 SW | 13 NSW | 14 ESW | 15 all |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GRAPHIC (CP310) | ■ 95 | │ 85 | ─ A2 | └ C4 | │ 85 | │ 85 | ┌ C5 | ├ C6 | ─ A2 | ┘ D4 | ─ A2 | ┴ C7 | ┐ D5 | ┤ D6 | ┬ D7 | ┼ D3 |
| BASE (CP037) | + | \| | - | + | \| | \| | + | + | - | + | - | + | + | + | + | + |
LEVEL1 uses masks 2-10, 12-14 (0, 1, 11, 15 never occur; their table entries are checked statically, see 6).
The 2-cell-thick inner walls come out as small closed boxes (`┬┬ / ├┤ / └┘`), close to the arcade's double-line walls.

## 3. Sprites and animation (G3 mechanics unchanged)
- Pac-Man: open frame faces the last horizontal command (`L` -> `⊃`, `R` -> `⊂`; U/D/bumps/invalid keep the facing; start
  facing right); closed frame `○`. Facing is display state kept in PACSCR from LAST-CMD (read-only), never a game value.
  Up/down facing (`∪`/`∩`) is deliberately not used: `∩` is the ghost and would be ambiguous.
- Ghosts: `∩` / `⍝` (the "eye" frame). Colours, reverse highlight (G2), visual tick and partial redraw (G3) as today.
- Mapping every G4 glyph back (`⊂ ⊃ ○` -> P, `∩ ⍝` -> G, tiles -> `#`, `•`/`·` -> `.`) gives exactly the G3/G2 image:
  the proof that only the presentation changed (same method as G3).

## 4. Data stream: GE per cell (not SA X'43')
- A GRAPHIC cell is sent as `08 cc` (GE + CP310 code); the virtual image (G3) gets one more byte per cell, CU-CS / PV-CS
  (0 base, 1 GE), compared in the diff like colour and highlight. No attribute state is carried between partial runs.
- SA X'43' X'F1' was equivalent in c3270 (E9) but would be a third run-state (set, carry, reset at row ends) for no gain;
  it stays documented as an alternative, not used.
- Size: the first full screen grows from 600 to 800 bytes (one GE byte for each of the 200 board cells: 98 walls,
  pellets, Pac-Man, ghost); DS buffer
  stays 2048; METRICS CHARS counts the GE bytes. Partial screens and ticks: +1 byte per changed GE cell.
- Transport unchanged: FULLSCR for full screens (GE proven live by E9), Write X'F1' + NOEDIT for partials/ticks (to be
  confirmed live with GE in the checklist, item 7).

## 5. Modules (core PACGAME/PACMAP/PACAI, PACSTATE, PACMREQ, LEVEL1 untouched, D22; no new core calls)
- PACPAL: profile tables (tiles, pellet, sprite frames per profile), GE flag per glyph. Values only here (as D24/D26).
- PACSCR: tile mask, facing, GE emission, CU-CS in the virtual image; CLASSIC path = current code path.
- PACPLAT: AUTO resolution from the Query Reply (parsing of X'85'); PACMAIN: PARM column 16; CLIST: GLYPHS keyword.
- New small subprogram PACQRY (pure function: reply bytes -> colour/highlight/GE flags) used by PACPLAT, so the AUTO
  decision can be tested in batch with recorded replies (driver PACQRYT reading the reply in hex from cards). The G1/G2
  colour/highlight decisions move into it unchanged (their behaviour is covered by the same test).

## 6. Tests (deterministic; batch remains the reference; D9-D12, D17-D18)
1. Core frozen + the 25 oracle blocks of 1.0-MVS byte-identical (tests/test_g0.py).
2. Regression: every G3 TSD stream (profile C) identical to tests/ref_g3_screen.py - the G3 checks on the same listing.
3. New TSD dry runs with profiles G and B (full/partial, anim yes/no, hilite yes/no, 1-3 ghosts, death, PA2 redraw, ticks)
   byte-identical to an independent tests/ref_g4_screen.py (masks computed by the model, not read from PACPAL).
4. Reverse mapping of every G/B stream = the G3 image (mechanics unchanged).
5. Static: PACPAL tile/glyph tables equal the model's tables (covers masks 0, 1, 11, 15 absent from LEVEL1).
6. Edge cases (all must have a case): border/corner cells; each LEVEL1 mask; pellet eaten (GE cell -> blank without GE);
   ghost leaving a pellet cell (back to `•`); Pac-Man facing after L, R, U, D, bump, invalid, redraw, death/respawn;
   tick toggling GE sprites; PA2 full redraw; AUTO with the recorded c3270 reply (-> G), same reply with ALT cleared (-> C),
   reply without X'85' (-> C), CP310 missing (-> C), COLOR(YES) (-> C), COLOR(NO) (line mode); largest full screen < 2048.
7. Live c3270 checklist: GLYPHS(GRAPHIC) with COLOR(YES) HILITE(YES): maze, moves both directions (facing), ghosts, ticks
   (GE partials visible), INVALID, PA2, Q, READY; AUTO with COLOR(AUTO) -> GRAPHIC; BASE; CLASSIC = G3 look; COLOR(NO).

## 7. Visual differences per emulator (to keep in docs/CAPABILITIES.md)
| Emulator | GRAPHIC result | Status |
|---|---|---|
| c3270 4.5ga6, UTF-8 terminal (macOS) | CP310 mapped to Unicode; continuous box lines (font-dependent) | CONFIRMED live (E9) |
| s3270 / x3270if `Ascii()` | same Unicode text (used for the captures) | CONFIRMED (E9 capture) |
| c3270 without Unicode / ASCII line-drawing mode | x3270 source maps CP310 boxes to `+ - \|` (table `apla2uc`), APL symbols may be blank | from source, NOT TESTED |
| x3270 (X11, own 3270 fonts with APL) | expected native APL glyphs | NOT AVAILABLE here, NOT TESTED |
| wc3270, commercial emulators, real 3279 with APL feature | GE expected where ALT is announced; AUTO stays C otherwise | NOT TESTED |
| terminal without GE (no ALT flag) | AUTO -> CLASSIC; forcing GRAPHIC is at the user's risk (wrong glyphs; restart with CLASSIC) | by design |
Glyph shapes (e.g. `⍝`, `∩`, line weight and gaps between `─` cells) depend on the font of the terminal window.

## 8. Out of scope
Programmed Symbols (G5/G6: E9 shows none loadable), new maps, power pellets, game changes, z/OS.

## Approval (user, 2026-10-08): all five points approved, with these precisions
1. Profiles C/B/G with the glyphs above; CLIST GLYPHS(AUTO|GRAPHIC|BASE|CLASSIC), PARM column 16, default AUTO in the CLIST
   and C for direct calls.
2. AUTO rule (ALT flag + CP310 in the X'85' reply; COLOR(YES) -> C); the explicit GRAPHIC combination is documented in 1.
3. GE per cell (not SA X'43').
4. Pac-Man facing left/right only; vertical moves keep the last horizontal facing; ghosts `∩`/`⍝`.
5. PACQRY extracted ONLY as pure capability parsing/selection (moves the G1/G2 decisions without changing them). Query
   transport, ordering, PACFSIO, TGET/TPUT, full-screen mode sequencing and the whole G1-G3 protocol path stay untouched.
