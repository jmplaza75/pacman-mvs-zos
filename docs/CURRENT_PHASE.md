El documento maestro de requisitos esta en docs/requirements/PACMAN_MVS_ZOS_REQUISITOS_DESARROLLO_v4.docx. No releerlo completo en cada sesion;
consultar unicamente las secciones de la fase actual cuando CURRENT_PHASE.md lo indique (MVS-GS cerrada; siguiente fase: pendiente de decision del usuario).

MVS-G3 COMPLETE (tag mvs-g3, 2026-10-08, final build JOB 188): partial redraw (Write X'F1' + TPUT NOEDIT) and glyph animation with an idle
visual tick; options REDRAW(PARTIAL|FULL), ANIM(AUTO|YES|NO), METRICS(NO|YES). Final manual checklist PASS (AUTO, COLOR(YES) HILITE(YES),
ANIM(NO) REDRAW(FULL), COLOR(NO)). Design, results, known limitation: docs/G3-PARTIAL.md (D27, D28).
KNOWN LIMITATION (D28, investigation closed deliberately): in TK4-/MVS 3.8J + TSO + c3270, COLOR(AUTO) performs a capability Query Reply
that leaves the idle ticks held until the first AID; after the first input the animation works normally. COLOR(YES) HILITE(YES) skips the
query and the animation starts immediately (recommended on TK4-/c3270). Not a fault of the mechanics or of the G3 renderer.
Pending note (from G1, not G3 work): the ESTAE abend-restore exit in PACFSIO is implemented but not validated live.

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

MVS-RT (real-time gameplay) STARTED 2026-10-09, plan approved: docs/RT-REALTIME.md (baseline mvs-gs, 62ab854).
- RT0 CLOSED 2026-10-10: isolated probe E14 (src/probe/PACRTP.cob + PACRTA.asm, CLIST RTPROBE, build JOB 211, logs JOBs
  213-216). Evidence and conclusions: docs/evidence/rt-e14-timing.md. PACMAN and the frozen core unchanged.
- RT1 APPROVED 2026-10-10: frozen design D33 in docs/RT-REALTIME.md (T = 150 ms, PF7/8/10/11, typeahead OFF, PACRT,
  PACGAME REQ-STEP, PACFSIO POLL, PACTSO TIME/deadline wait, PLAY(TURN|REALTIME)). TICK-COUNT > 999 wraps harmlessly
  (JOB 217): PACSTATE unchanged. No further probes.
- RT2 DONE 2026-10-10 (Hercules JOB 222, tests/test_rt.py PASS, docs/evidence/rt2-build.txt): PACRT, PACGAME REQ-STEP
  (authorised), RT-GAME loop, PACINPT/PACPLAT/PACDISP/PACSCR RT ops, PACFSIO POLL, PACTSO TIME/DLWT, PLAY(TURN|REALTIME)
  (CLIST default TURN), tests/ref_rt.py + tests/rtcases. TURN regression unchanged.
- NEXT: RT3 (live TSC integration on c3270 with tools/c3270_rt.sh) - WAITING FOR USER GO.
