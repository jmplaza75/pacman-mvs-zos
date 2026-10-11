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

MVS-S1 IN PROGRESS (sound, D35): probe E15 live PASS (docs/evidence/s1-e15-alarm.md: the WCC alarm is audible through SENX,
SEND and SENP). SOUND(AUTO|YES|NO) built and tested on Hercules: JOB 233 (tests/test_s1.py PASS: RT/GX/TURN regression and
1.0-MVS oracle unchanged, 15 SOUND TSD runs = model with 38 bells, line/batch modes silent), CLIST SOUND(AUTO) JOB 234.
Evidence docs/evidence/s1-build-tsd.txt. Live 1 (2026-10-11): bells PASS (AUTO and NO), BUT every game end abended 0C4-4:
latent RT2 defect in PACTSO (WAIT fell into DOTIME: wild store), fixed with one `B DONE` (docs/evidence/s1-live-0c4.md);
rebuild JOB 236 PASS. Live 2 (docs/evidence/s1-live.md): PASS for AUTO and NO, both traced games ended LOST cleanly (end
lines, READY, no error); a QUIT end is not in the trace (same end path). PENDING: user decision to close (tag mvs-s1).
Do not start GP1 or S2 until S1 is closed and the user says go. E15 data for S2: 3 bells audible back to back and 0.5 s apart.
Maintenance: `make_deck.py COMPRESS` now also compresses LOAD (JOB 231 SE37 in LINK).
