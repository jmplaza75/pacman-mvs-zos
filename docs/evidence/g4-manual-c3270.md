# MVS-G4 manual validation in c3270 (reported by the user, 2026-10-08; builds JOB 191 and JOB 195, CLIST JOB 192) - G4 CLOSED
## Part 1 - PASS
Confirmed live with `GLYPHS(GRAPHIC)` in the real game: CP310/APL box walls drawn correctly; graphic pellets correct;
Pac-Man and the ghost use the new glyphs; colour + highlighting + GE work together; after moves (`T002`, score updated)
the board stays correct; partial redraw with GE cells works live (the open point of the design, section 4); eaten
pellets disappear; no corruption, shifted cells or garbage characters; `COLOR(NO)` returns to the monochrome line mode.

## Part 2 - functional checklist PASS (user, 2026-10-08)
All six items pass: immediate animation `⊂ <-> ○` / `∩ <-> ⍝` with COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC); facing L `⊃`, R `⊂`,
U/D keep it; default CLIST selects GRAPHIC (AUTO); BASE `+ - |` walls and base pellets; CLASSIC = the G3 look; `X` INVALID
and PA2 full redraw.

## Status
- Protocol / renderer mechanics (GE transport, partial redraw, animation, AUTO, fallback): PASS.
- G4 visual fidelity of wall geometry (BASE and GRAPHIC): FAIL - maze hard to read, internal walls not faithful to CLASSIC;
  investigation: docs/evidence/g4-wall-diagnosis.md.
- G4 remains OPEN; no commit, no tag.
- Fix A (filled walls; `#` with HILITE(NO)) built in JOB 195 - live check: Part 3.

## Part 3 - filled walls (build JOB 195): PASS (user, 2026-10-08)
- `COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC)`: solid walls - OK
- `COLOR(YES) HILITE(NO) GLYPHS(GRAPHIC)`: `#` walls - OK
- `COLOR(YES) HILITE(YES) GLYPHS(BASE)`: solid walls - OK
- `COLOR(YES) HILITE(NO) GLYPHS(BASE)`: `#` walls - OK
- default CLIST (AUTO): GRAPHIC with solid walls - OK
Inner walls and the border read correctly; the 2-cell-wide blocks stay solid; no gaps or corruption after moves; GRAPHIC
keeps its pellets, sprites and animation; BASE keeps its glyphs; HILITE(NO) falls back to `#`; AUTO selects GRAPHIC with
solid walls.

## Final status: G4 CLOSED (2026-10-08)
- GRAPHIC, BASE, CLASSIC and AUTO validated live in c3270.
- Partial redraw with GE cells passed live in Part 1; the filled walls passed live in Part 3.
- The centre-line wall shaping of the first build (JOB 191) was rejected live and replaced by filled walls (D29 revision);
  docs/evidence/g4-wall-diagnosis.md is kept as the historical evidence.
- True arcade wall contours are deferred deliberately to a future scaled renderer (preferably 2 x 2).
- Core (PACGAME, PACMAP, PACAI, PACSTATE, PACMREQ, LEVEL1) frozen and unchanged (tests/test_core_frozen.py PASS);
  PACFSIO identical to tag mvs-g3.

Not covered (not G4 work): the ESTAE abend-restore exit in PACFSIO remains implemented but not validated live.
