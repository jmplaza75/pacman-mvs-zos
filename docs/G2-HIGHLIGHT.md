# MVS-G2 highlighting - design and result (2026-10-08)
Requirement (master doc sec. 25-26, MVS-G2): reverse / blink / underscore / intensity only where they improve
readability, as an option of the TSC renderer; G1 colour and TSO monochrome stay as fallbacks. Basis: Query Reply QCode
X'87' (highlighting) announced by the terminal (E5, docs/CAPABILITIES.md).

## Selection (separate from colour; G1 output is the "off" state)
- CLIST keyword `HILITE(AUTO|YES|NO)`, default AUTO, passed in PARM column 13 (`A`/`Y`/`N`; column 12 stays COLOR).
- PACPLAT INIT resolves REQ-HILITE to `Y` or `N`: `Y` stays `Y` in TSC; `A` becomes `Y` only if the Query Reply of the
  AUTO colour detection also contains QCode X'87'; with COLOR(YES) there is no query, so `A` means `N`. Outside TSC
  (BAT, TSO monochrome, fallback after an error) it is always `N`. TSD (dry run) honours `Y` so it can be tested.
- Direct calls without the PARM column behave as before (`N`): G1 byte for byte, only the help line says `G2`.

## What is highlighted (all values in copybook PACPAL, 0 disables an element)
| Element | Highlight (SA X'41') | Why |
|---|---|---|
| `P` Pac-Man and `G` ghosts | reverse video F2 (a solid block in the element's colour) | moving characters stand out from the `#`/`.` background |
| `INVALID COMMAND x` | blink F1 | the only transient message; it disappears on the next screen |
| 1-byte command input field | underscore F4 | shows where to type |
| walls, pellets, HUD, help | none | static text: colour is enough; highlighting everything would remove the contrast |
Intensity is a field attribute (not an SA order) and is not used: no readability gain over colour.
Data stream: after the colour order of a cell, `28 41 vv` only when the highlight of the cell changes (adjacent
highlighted cells share one run, blank/other cells end it with `28 41 00`); every run is closed at the end of its text
or board row; the final `28 00 00` resets all character attributes as in G1.

## Tests
- tests/ref_g2_screen.py: independent Python renderer (hilite flag). tests/test_g2.py: core frozen; highlight orders
  appear exactly when asked, one underscore per screen; highlight off = the G1 screens (help text aside); coverage:
  INVALID blink (MOVES), adjacent highlighted cells (MULTI, DIE1, C3N2, P2N3...), redraw (TSORDR).
- Hercules (deck G2, job PACBLDG2): 56 steps RC 0000 (25 oracle runs + 7 TSD dry runs, 5 with highlights, 2 without);
  the 25 batch/TSO blocks byte-identical to 1.0-MVS; 132 TSC screens byte-identical to the model.
- Live c3270 validation (user, 2026-10-08): all effects as designed, HILITE(NO) = G1 look, COLOR(NO) = monochrome
  (docs/evidence/g2-manual-c3270.md). G2 closed.
