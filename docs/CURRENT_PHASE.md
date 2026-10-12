El documento maestro de requisitos esta en docs/requirements/PACMAN_MVS_ZOS_REQUISITOS_DESARROLLO_v4.docx. No releerlo completo en cada sesion;
consultar unicamente las secciones de la fase actual cuando CURRENT_PHASE.md lo indique (MVS-GS cerrada; siguiente fase: pendiente de decision del usuario).

MVS-G3 COMPLETE (tag mvs-g3, 2026-10-08, final build JOB 188): partial redraw (Write X'F1' + TPUT NOEDIT) and glyph animation with an idle
visual tick; options REDRAW(PARTIAL|FULL), ANIM(AUTO|YES|NO), METRICS(NO|YES). Final manual checklist PASS (AUTO, COLOR(YES) HILITE(YES),
ANIM(NO) REDRAW(FULL), COLOR(NO)). Design, results, known limitation: docs/G3-PARTIAL.md (D27, D28).
KNOWN LIMITATION (D28, investigation closed deliberately): in TK4-/MVS 3.8J + TSO + c3270, COLOR(AUTO) performs a capability Query Reply
that leaves the idle ticks held until the first AID; after the first input the animation works normally. COLOR(YES) HILITE(YES) skips the
query and the animation starts immediately (recommended on TK4-/c3270). Not a fault of the mechanics or of the G3 renderer.
Pending note (from G1, not G3 work): the ESTAE abend-restore exit in PACFSIO is implemented but not validated live. S1 live 1 (unplanned 0C4 in full-screen mode) came back to READY in line mode, consistent with the exit working; the controlled test stays in RP.

1.0-MVS is the immutable functional baseline; z/OS out of scope.

MVS-G4 COMPLETE (tag mvs-g4, 2026-10-08, final build JOB 195): glyph profiles GLYPHS(AUTO|GRAPHIC|BASE|CLASSIC) (D29,
docs/G4-GLYPHS.md). Probe E9 (JOB 190) confirmed GE + CP310 APL, no loadable PS. GRAPHIC = CP310 pellets/sprites via GE, Pac-Man
facing left/right; BASE = base pellet; both draw walls as filled blocks (reverse video) with highlighting, `#` without; CLASSIC =
G3 byte for byte. The first centre-line wall tiles (JOB 191) were rejected live and replaced (docs/evidence/g4-wall-diagnosis.md,
historical). Live c3270 PASS (docs/evidence/g4-manual-c3270.md). Core frozen, PACFSIO unchanged. True arcade wall contours are
deferred to a future scaled renderer (preferably 2x2). Maintenance: `make_deck.py COMPRESS` if a build ends with SE37.
Regression to keep: tests/test_g4.py (oracle + 460 TSC streams + PACQRY + wall occupancy), tests/test_core_frozen.py.

MVS-G5 CLOSED NEGATIVE (tag mvs-g5, 2026-10-08, probe JOB 196, D30): Programmed Symbols are not supported in the validated
TK4-/MVS 3.8J + TSO + c3270 environment; G4 is the production character-set ceiling. Capability limit, not an implementation failure.
Isolated probe E10 (src/probe/PACFSA.asm via tools/gen_probe_e10.py, PACG5P, CLIST G5PROBE; game untouched): Query Reply = E9, no
loadable sets; c3270 traces Load PS as `unsupported ID 0x06`, nothing returns to the host; SA 43 to the loaded set = base set, APL
control works. LOADRC=0000 = host TPUT accepted the send only; ILEN=0053 = tail of the screen-1 ENTER record (not a response).
Evidence: docs/evidence/g5-probe-analysis.md, g5-c3270-e10-window.txt, g5-probe-build.txt.
MVS-G6 (multicolour/triple-plane PS): BLOCKED / NOT APPLICABLE in this environment (depends on PS, reason inherited from G5).
Future option, not pursued: a PS-capable terminal/emulator in a separate compatibility branch (E10 reusable; no Vista/PCOMM dependency).

MVS-GS COMPLETE (tag mvs-gs, 2026-10-09): scaled renderer + geometry integration.
- 4x2 scaled renderer (D31, docs/GS-SCALED.md): maze 80 x 20, arcade contour walls, half-block sprites, end banner with a
  3 s pause, SCALE(AUTO|4|3|NO); build JOB 200; 4x2 proportions confirmed live.
- Geometry (D32, docs/GS-GEOMETRY.md; probe E12: 80x32, 80x43, 132x27, 120x27 IBM-DYNAMIC live PASS): CANVAS(AUTO|DEFAULT),
  one size switch before the query, PACFSIO op SENX (the one extension), wide / tall / centred layouts, size guard
  W/T -> 80x24 GS -> G4; build JOB 207 (tests/test_gx.py), CLIST JOB 208; live PASS (docs/evidence/gs-manual-c3270.md).
- Preferred canvas for the normal 120 x 30 macOS Terminal: 120 x 27 IBM-DYNAMIC (`c3270 -model 2 -oversize auto
  localhost:3270`); 80 x 24 is the universal fallback. Larger canvases improve centring / HUD space, not the maze scale
  (80 x 20 at 4x2 everywhere).
- Operational rule: size the terminal window before connecting; never shrink it below the negotiated canvas while
  connected (c3270 cannot recover the display).
- Regression to keep: tests/test_gx.py (+ test_gs.py, test_g4.py, test_core_frozen.py). Future, not a dependency: probe E13
  (4 KB TPUT transport) for a richer HUD or a 6x3 maze.

MVS-RT COMPLETE (tag mvs-rt, 2026-10-11): real-time gameplay (D33, D34; docs/RT-REALTIME.md).
- RT0 probe E14 (docs/evidence/rt-e14-timing.md): T = 150 ms, PF7/8/10/11, typeahead off, D28 released by the first AID.
- RT2 (JOB 222) and final build JOB 226: PACRT, PACGAME REQ-STEP (authorised), RT-GAME loop, PACFSIO POLL, PACTSO
  TIME/DLWT (+ batch clock test PACTSOT), PF9 pause + PAUSED; tests/test_rt.py PASS (TURN/GX regression and 1.0-MVS
  oracle unchanged, 12 batch + 182 TSD REALTIME streams = tests/ref_rt.py).
- RT3 live PASS (docs/evidence/rt3-live.md); CLIST default PLAY(REALTIME), PLAY(TURN) compatibility (JOB 227).
- Play: `TYPEAHEAD=false tools/c3270_rt.sh` (120x30 window), log on, then `python3 tools/rt_play.py`.
- Regression to keep: tests/test_rt.py (+ test_gx.py, test_gs.py, test_g4.py, test_core_frozen.py).

Post-RT roadmap APPROVED with amendments (2026-10-11): docs/ROADMAP-POST-RT.md, order S1 -> GP1 -> GP2 -> HS -> RP -> S2 -> G7
-> G8 / 2.0-MVS-MAX (final MVS release). GP1/GP2 may change the core only under RULES(ARCADE); CLASSIC stays 1.0-MVS.

MVS-S1 COMPLETE (tag mvs-s1, 2026-10-11): sound = the 3270 alarm (D35).
- Probe E15 live PASS (docs/evidence/s1-e15-alarm.md): WCC bit X'04' audible through SENX, SEND and SENP; for S2:
  3 bells audible back to back and 0.5 s apart.
- SOUND(AUTO|YES|NO) (PARM column 20, absent = NO; CLIST default AUTO): bell on start, each death and the win, colour
  full-screen only; display/platform only (PACDISP SET-BELL, PACPLAT SET-ALARM), core untouched. Final build JOB 236,
  tests/test_s1.py PASS (docs/evidence/s1-build-tsd.txt).
- Live 1 found an 0C4-4 at every game end: latent RT2 defect in PACTSO (WAIT fell into DOTIME, wild store), fixed by
  one `B DONE` (docs/evidence/s1-live-0c4.md). Live 2/3 PASS: LOST and QUIT ends clean, AUTO rings, NO silent
  (docs/evidence/s1-live.md).
- Regression to keep: tests/test_s1.py (+ test_rt, test_gx, test_gs, test_g4, test_core_frozen).

MVS-GP1 IN PROGRESS (started 2026-10-11 on the user's go): power pellets under RULES(ARCADE).
- GP1.1 design docs/GP1-POWER.md: D36 APPROVED and frozen (2026-10-11, user decisions in its section 8).
- GP1.2 COMPLETE (2026-10-11): core change authorised (docs/CORE_CHANGES.md), PACARC, PARM column 21, ARCADE text
  lines; deck GP1 JOB 238: 192 steps RC 0000, S1/CLASSIC regression PASS, 26 ARCADE runs = tests/ref_arcade.py;
  evidence docs/evidence/gp1-build-text.txt. Test: `python3 tests/test_gp1.py build/PACBLGP1-238.txt`.
- GP1.2 committed as checkpoint bc419f7 (no tag).
- GP1.3 COMPLETE (2026-10-11): ARCADE screens in PACSCR/PACPAL (all glyph profiles, scaled families, partial redraw,
  ticks, REALTIME); deck GP1 JOB 240: 214 steps RC 0000, S1/CLASSIC regression PASS, 21 ARCADE TSD runs = 939 model
  streams; evidence docs/evidence/gp1-screens-tsd.txt; design section 10.
- GP1.4 live PASS (2026-10-11/12, docs/evidence/gp1-live.md): CLIST JOB 241 (default RULES(CLASSIC)); 2 games
  replayed by tools/c3270_gp1_trace.py = model byte for byte; pause / PA2 during a fright covered by RTGPP / GQR3.
MVS-GP1 COMPLETE (tag mvs-gp1, 2026-10-12). Regression to keep: tests/test_gp1.py (+ test_s1, test_rt, test_gx,
test_gs, test_g4, test_core_frozen).
MVS-GP2 IN PROGRESS (started 2026-10-12 on the user's go): levels, progression and bonus fruit under RULES(ARCADE).
- GP2.1 design docs/GP2-PROGRESSION.md: D37 APPROVED and frozen (2026-10-12, user decisions in its section 9;
  fruit cell (10,8) verified before coding).
- GP2.2 COMPLETE (2026-10-12): core change authorised (docs/CORE_CHANGES.md), PACARC appended, PACRT / PACMAIN /
  PACDISP / PACREQ / CLIST source; model tests/ref_gp2.py, cases tests/gp2cases (tests/search_gp2.py); deck GP2 JOB
  244: 236 steps RC 0000, S1/CLASSIC regression PASS, 71 ARCADE runs = model; evidence docs/evidence/gp2-build-text.txt.
  Test: `python3 tests/test_gp2.py build/PACBLGP2-244.txt` (runs test_gp1.py as a regression with
  PACMAN_LATER_PHASE). Committed as checkpoint 93a4811 (no tag).
- GP2.3 COMPLETE (2026-10-12, build green; live not started): PACPAL (append-only), PACSCR (fruit, sprite 8, status
  variant, wide / tall HUD level + fruit), PACDISP (ARC-BELL: alarm from death / extra life / level clear counters,
  coalesced); deck GP23 JOB 246: 73 steps RC 0000, 43 ARCADE TSD runs = 3697 model streams (largest 1968 bytes); GP2
  deck rerun JOB 247 PASS (text, S1/CLASSIC, 1.0-MVS oracle); CLIST installed JOB 248 (RULES(CLASSIC) LEVEL(1)
  defaults). Evidence docs/evidence/gp2-screens-tsd.txt; design section 11. Test:
  `python3 tests/test_gp2.py build/PACBLGP2-247.txt build/PACBLG23-246.txt`.
  GP2.3 approved by the user (level-clear alarm kept, compact 80x24 HUD accepted); committed as a checkpoint.
  GP2.4 live c3270 acceptance: checklist APPROVED (docs/evidence/gp2-live-checklist.md); scenarios A/B/C
  (tests/gp2live, tools/gp2_live.py driver, tools/c3270_gp2_trace.py replay analyser) committed before the live run;
  Scenarios frozen. Live run 1: B PASS (78/78 writes = model, alarms [0, 76]); A and C every write = model but
  the route desynchronised by a documented driver defect (Wait(Output) does not block without an AID), fixed (idle
  card = PF1, ignored by the game); A and C to be rerun (docs/evidence/gp2-live.md). No mvs-gp2 tag.
Maintenance: `make_deck.py COMPRESS` now also compresses LOAD (JOB 231 SE37 in LINK).
