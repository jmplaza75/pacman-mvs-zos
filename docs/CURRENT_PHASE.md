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
MVS-GP2 COMPLETE (tag mvs-gp2, 2026-10-12): levels, progression and bonus fruit under RULES(ARCADE) (D37,
docs/GP2-PROGRESSION.md).
- GP2.2 core + text + model (JOB 244, checkpoint 93a4811): levels 1-99 (level 99 cleared = WON, intentional MVS
  limit), refill on a full clear, 13-row level table (AI bump, REALTIME step, fright), fruit at (10,8) after 30 / 70
  items, one extra life at 10000, death flag, wide counters, LEVEL(n) = PARM columns 22-23.
- GP2.3 screens (JOB 246 deck GP23 + JOB 247 deck GP2, checkpoint 3c7cf59): fruit in every profile / scale, level and
  fruit in the HUD (compact 80x24 status line: LEVEL + kind letter), alarm on death / extra life / level clear (one
  per write). CLIST JOB 248: defaults RULES(CLASSIC) LEVEL(1).
- GP2.4 live PASS (docs/evidence/gp2-live.md): scripted scenarios (tools/gp2_live.py, tests/gp2live) replayed by
  tools/c3270_gp2_trace.py = model byte for byte; B run 1, A and C run 2 after a driver sync fix (idle card = PF1).
- Regression to keep: tests/test_gp2.py (`build/PACBLGP2-247.txt build/PACBLG23-246.txt`; runs test_gp1 with
  PACMAN_LATER_PHASE, test_s1 -> test_rt -> test_gx on the listing) + test_gs, test_g4, test_core_frozen.
MVS-HS IN PROGRESS (started 2026-10-12 on the user's go): persistent ARCADE high score in HERC01.PACMAN.DATA(HISCORE).
- HS.0 probe E16 PASS (JOB 254, docs/evidence/hs-e16-probe.md): isolated src/probe/PACHSA.asm + PACHSP.cob, deck `HSP`.
  No abend for no DD / missing dataset / DD without member / missing, empty or garbage member; rewrite in place (same
  TTR, no space used); first write creates the member; batch = TSO (IKJEFT01). Fixed on the way: BPAM OPEN 013-18 on a
  missing member (OPEN TYPE=J without the member, JFCNWRIT), S800 on the BPAM update write (QSAM UPDAT instead). A
  failed ALLOC ends a CLIST: the CLIST must guard it with &SYSDSN (works on MVS 3.8).
- HS.1 design docs/HS-HISCORE.md: D38 APPROVED and frozen (2026-10-12; D1-D3, D5, D6 as proposed, D4 amended: empty /
  malformed data self-heals on the next eligible save, NOT SAVED only for a failed attempted write, tested by a full
  PDS directory). HS.0/HS.1 checkpoint ef2e591; HS.2 commit f6ef97a.
- HS.2 COMPLETE (2026-10-12): probe E16b PASS (JOB 258: REPL heal, DUMMY, ESTAE guard on a genuine full directory,
  the exit deleted after a retry too). src/asm/PACHSIO.asm, PACREQ (+7), PACPLAT HSRD/HSWR, PACMAIN, PACDISP end
  lines, CLIST (&SYSDSN, DUMMY fallback, ARCADE only), decks DATA / HS / `RUN --hiscore`, PACHSIO linked into every
  current deck. Deck HS JOB 260 PASS (tests/test_hs.py: 21 runs = model, H1-H15, prints, CLIST block); regression
  COMPRESS 261, GP2 262 (237 steps), GP23 263 PASS. Installed: DATA JOB 264, CLIST JOB 265. Core untouched.
  Test: `python3 tests/test_hs.py build/PACBLDHS-260.txt build/PACBLG23-263.txt build/PACBLGP2-262.txt`.
- HS.3 live PASS (2026-10-12, docs/evidence/hs-live.md): L1-L7 (created, read back, updated, LEVEL(5) not recorded,
  CLASSIC silent, renamed dataset = UNAVAILABLE + clean READY, member `0001430 PACHS001 001`). The live higher-score case
  ended with QUIT, not LOST; LOST / EOF / practice WIN / failure paths are covered by HS.2 (JOB 260).
MVS-HS COMPLETE (tag mvs-hs, 2026-10-12). Regression to keep: tests/test_hs.py (`build/PACBLDHS-260.txt
build/PACBLG23-263.txt build/PACBLGP2-262.txt`; runs test_gp2 with PACMAN_LATER_PHASE=HS) + test_gs, test_g4,
test_core_frozen. Install note: the high-score dataset <prefix>.DATA (deck DATA once, or ALLOC on a fresh install) is
outside the build libraries; COMPRESS and rebuilds never touch it.
MVS-RP IN PROGRESS (started 2026-10-12 on the user's go): presentation and gameplay polish (docs/RP-POLISH.md).
- RP.1 design D39 APPROVED and frozen (2026-10-12): ARCADE-only visuals, fruit popup in, no level-clear flash, SPEED
  for any REALTIME game, ESTAE via the test driver PACRPE. S2 not started.
- RP.0 build PASS (deck RPE JOB 266: src/probe/PACRPE.cob + RPESTAE.clist, production PACFSIO/PACHSIO unchanged,
  no warnings, both batch runs end S0C7 = trigger proven; docs/evidence/rp-estae-build.txt). Live checklist
  docs/evidence/rp-estae-checklist.md.
- RP.0 live 1 (docs/evidence/rp-estae-live1.md) and live 2 (docs/evidence/rp-estae-live2.md): ESTAE recovery PASS
  (E1; E2 twice, each followed by a clean full-screen game; E3 control twice). RP.0 CLOSED. The startup `***` follows
  every E3 and no E2: it comes from line output written by an abended program, not from the exit -> D40 (open).
- D40 startup hardening (inside RP as step RP.2b, before RP.4; design PROPOSED in docs/RP-POLISH.md section 11): TSO `***` before the full-screen switch makes the capability query read
  the user's ENTER as the reply -> line-mode fallback (stray `A` / `X` commands). Design APPROVED (2026-10-12), step
  RP.2b, after RP.2.
- RP.2 COMPLETE (2026-10-12, NOT installed): PACRT (freeze count + death cell), PACREQ / PACPAL appended, PACSCR (READY!,
  death frames, popups, HUD high score, end line, decoration-drop size rule), PACDISP (final death frames); models
  tests/ref_rp.py (+ gs/gx/g4/rt hooks), cases tests/rpcases, tests/search_rp.py, tests/test_rp.py. Deck RP JOB 270
  (load member PACRPD): 95 steps RC 0000, 60 ARCADE TSD runs = 6265 model streams; regression GP2 JOB 271, HS JOB 272
  PASS (docs/evidence/rp2-build-tsd.txt). Installed PACMAIN unchanged until RP.2b is green.
