El documento maestro de requisitos esta en docs/requirements/PACMAN_MVS_ZOS_REQUISITOS_DESARROLLO_v4.docx. No releerlo completo en cada sesion;
consultar unicamente las secciones de la fase actual cuando CURRENT_PHASE.md lo indique (MVS-G8 / 2.0-MVS-MAX COMPLETA, etiqueta 2.0-mvs-max; la rama MVS esta TERMINADA. No hay fase activa; el port z/OS no esta iniciado).

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
MVS-RP COMPLETE (tag mvs-rp, 2026-10-13): presentation and gameplay polish (docs/RP-POLISH.md, D39, D40). Build of
record deck RP JOB 285, installed JOB 286 (PACMAIN) + JOB 287 (CLIST); live docs/evidence/rp3-fast-live.md and
docs/evidence/rp-live.md (two accepted coverage exceptions recorded there). Regression to keep: tests/test_rp.py
(`build/PACBLDRP-285.txt`), test_gp2 / test_hs with PACMAN_LATER_PHASE=RP, tests/test_core_frozen.py.
Next phase after RP: MVS-S2 (started 2026-10-13 on the user's go, see the MVS-S2 entry at the end).
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
  PASS (docs/evidence/rp2-build-tsd.txt).
- RP.2b D40 COMPLETE (2026-10-12, NOT installed): PACQRY validity + bounded selection, PACPLAT read loop + drain,
  PACQRYT sequence mode; deck RP JOB 275 (after COMPRESS JOB 274): 100 steps RC 0000, 60 TSD runs = model, 29 startup
  sequences = model; regression GP2 JOB 276, HS JOB 277 PASS (docs/evidence/rp2b-d40-build.txt).
- RP.3 SPEED BUILD GREEN (2026-10-13, NOT installed; PACMAIN and the CLIST not replaced): REQ-RTPER (PACMAIN, PARM
  column 24), PACPLAT period, RT-CONV in PACRT and PACGAME (authorised core change, docs/CORE_CHANGES.md), PACSCR /
  PACDISP timers from the converted quanta, CLIST SPEED + LEVEL padding. Deck RP JOB 285: 127 steps RC 0000, RP.2
  6265 streams unchanged, D40 29 sequences, RP3 12 TSD runs = 1495 streams + 9 BAT runs = model, CLIST PARM lines
  under the TMP; regression GP2 JOB 283 (after COMPRESS JOB 282), HS JOB 284 PASS (docs/evidence/rp3-speed-build.txt).
  Test: `python3 tests/test_rp.py build/PACBLDRP-285.txt`.
- RP.3 INSTALLED (2026-10-13, user approval): PACMAIN = deck RP JOB 286 (load PACMAIN, same sources as JOB 285; all
  RP / D40 / RP3 checks re-passed on the installed module), CLIST JOB 287 (only new default SPEED(NORMAL)). Next: ONE
  directed FAST live capture (docs/evidence/rp3-fast-live-checklist.md), analysed before the rest of RP.4.
- RP.3 FAST LIVE PASS (2026-10-13, docs/evidence/rp3-fast-live.md): 344/344 writes = FAST models, 343 writes in 343
  periods, gap median 125 / p95 133 ms, lateness median 7 / p95 13 ms, 2 isolated late writes (160 ms) recovered at
  once, drift +0.5 ms / 100 quanta; fright 5999 / 5997 ms, eyes 2998, freeze 1501 (NORMAL design 6000 / 3000 / 1500);
  D40 case (a) clean startup. SPEED(FAST) kept. Pause at FAST not taken: folded into the RP.4 soak.
- RP.4 PASS (2026-10-13, docs/evidence/rp-live.md): JWT=60 min (JOB 288, read-only); D40 case (b) live PASS; Part A
  262/262 and Part B 5357/5357 writes = models; 603 s pause soak, no catch-up; no host skip in 10.75 min of FAST play.
  Accepted exceptions: no 10-minute pre-start hold live (25.7 s); pause / PA2 inside a death freeze only on Hercules
  (RPLOST). MVS-RP CLOSED.
MVS-S2 (started 2026-10-13 on the user's go): alarm patterns and sound polish.
- Go on the S1 evidence (E15 screens 5/6: separate bells not merged); no probe step.
- S2.1 design docs/S2-PATTERNS.md: D41 APPROVED and frozen (2026-10-13, user decisions in its section 8): ALARM(PATTERN|SINGLE)
  column 25, exact spacing G = 2 / 3 quanta (NORMAL / FAST), no new sound event (all six already rang), 3-s end pause kept.
- S2.1 design checkpoint c340b99.
- S2.2 BUILD GREEN (2026-10-13, NOT installed; PACMAIN and the CLIST not replaced): PACREQ +REQ-ALARM, PACMAIN column
  25, PACPLAT op DLWT, PACDISP pattern player + end pause, CLIST ALARM(PATTERN); GAME/MAP/AI/PACARC/PACRT/PACSCR = mvs-rp.
  Model tests/ref_s2.py, cases tests/s2cases (tests/search_s2.py). COMPRESS JOB 289; deck S2 JOB 290 (load PACS2D): 60
  steps RC 0000 at the first submission, 25 TSD runs = 2986 model streams (108 alarm writes), 21 D41 edges reached, 4
  line-mode runs = oracle / models. SINGLE regression into PACS2D: RP JOB 291, GP2 JOB 293 (after COMPRESS 292), HS
  JOB 294 PASS. Evidence docs/evidence/s2-build-tsd.txt. Test: `python3 tests/test_s2.py build/PACBLDS2-290.txt`.
- S2.2 committed as checkpoint baea879.
- S2.3 INSTALLED (2026-10-13, user approval): PACMAIN = deck S2 into PACMAIN JOB 297 (all S2 checks re-passed) and deck
  RP into PACMAIN JOB 298 (SINGLE path, all RP checks; last link, same sources); CLIST JOB 299 (default ALARM(PATTERN)).
  JOB 296 = JCL error, not run (EXEC cards at column 72 with the longer load name; make_deck run_step fixed, other decks
  byte-identical). COMPRESS JOB 295. Evidence appended to docs/evidence/s2-build-tsd.txt.
- S2.4 prepared, NOT run: docs/evidence/s2-live-checklist.md, five deterministic scenarios tests/s2live (driver
  tools/gp2_live.py S2A-S2E), analyser tools/c3270_s2_trace.py (tested on synthetic traces).
- S2.4 session 1 (2026-10-13, docs/evidence/s2-live.md): S2A (twice), S2B, S2D, S2E = models byte for byte (run 2 of S2A
  with a stray DOWN arrow: exact with --aids); bell gaps 295-302 ms (NORMAL) / 371-374 ms (FAST), end pause 3.0 s,
  cadence at the period. S2C run after it: 188 / 188 writes = model, 4 bells (1 + 3 bell-only writes at +302 / +611
  / +911 ms), end pause 3011 ms; user: "4 distinct bells", no audible anomaly in S2A/S2B/S2D/S2E. S2.4 PASS.
MVS-S2 COMPLETE (tag mvs-s2, 2026-10-13): D41, docs/S2-PATTERNS.md; build deck S2 JOB 290, SINGLE regression RP 291 /
GP2 293 / HS 294 (docs/evidence/s2-build-tsd.txt); installed baseline PACMAIN = JOB 298 link (JOB 297 S2 checks, JOB 298
RP checks, same sources), CLIST JOB 299 (defaults ... SPEED(NORMAL) ALARM(PATTERN)); live docs/evidence/s2-live.md.
Regression to keep: tests/test_s2.py (`build/PACBLDS2-290.txt`), test_rp / test_gp2 / test_hs with
PACMAN_LATER_PHASE=S2, tests/test_core_frozen.py.
MVS-G7 CLOSED NEGATIVE (tag mvs-g7, 2026-10-14, closure approved by the user, D42): host graphics, paper phase; a
negative capability closure, not a failed implementation. Terminal: E5 Query Reply
announces no graphics, c3270 documents none. Host: read-only check jcl/mvs/G7CHK.jcl, JOB 301 (JOB 300 = first pass
without the full link list), all RC 0000: no GDDM (ADM*) or other graphics module in the master catalog (the only
catalog), the seven LNKLST00 libraries or SYS1.LPALIB (tools/g7_gddm_scan.py, self-checked on synthetic positives).
Evidence docs/evidence/g7-gddm-check.md. Nothing of PACMAN changed; installed baseline = S2 (PACMAIN JOB 298, CLIST
JOB 299). The existing 3270 scaled / glyph renderer (GS over G4) is the final MVS graphics solution;
adding GDDM is outside the requirements.
MVS-G8 / 2.0-MVS-MAX IN PROGRESS (started 2026-10-14 on the user's go; docs/ROADMAP-POST-RT.md row 8, final MVS release).
- G8.1 design docs/G8-RELEASE.md: D43 APPROVED and frozen (2026-10-14) with the release-integrity amendment
  (section 8a): the validated R20 artifact becomes the installed PACMAIN (JOB 298 = historical), JCL audit against
  the old libraries, RP live timing reused, minimal installed live smoke (section 9).
  Release phase: no game / display / platform source changes; CLIST default RULES(ARCADE) (rest of the AUTO chain
  unchanged), benchmarks, screenshots, fresh rebuild under HERC01.PACMAN.R20, README authenticity section, tag
  2.0-mvs-max.
- G8.2 BUILD GREEN (2026-10-14, NOT installed; HERC01.PACMAN.LOAD(PACMAIN) and CLIST untouched): CLIST default
  RULES(ARCADE) (final default set frozen in tests/test_g8.py), deck REL20, `make_deck.py --runonly`, ALLOC sized for
  2.0, tools/g8_jcl_audit.py, tools/g8_bench.py, tests/test_g8.py, `tools/release_check.sh 2.0`. COMPRESS JOB 302;
  REL20 into PACR20D JOB 303 (60 steps RC 0000, CLIST PARMs, 1.0 oracle PASS); S2 run-only on PACR20D JOB 304
  (2986 streams = model). Evidence docs/evidence/g8-build.txt.
- G8.3 COMPLETE (2026-10-14, user go; docs/evidence/g8-install.txt): R20 check JOB 305 (no R20 dataset), ALLOC JOB 306
  (new empty HERC01.PACMAN.R20.*), build of record REL20 JOB 307 into HERC01.PACMAN.R20.LOAD(PACMAIN) (60 steps RC
  0000, link: member did not exist), run-only on that member S2 308 / RP 309 / GP2 310 / GP23 311 / HS 312 all PASS,
  every deck and listing audited (no old-library reference), R20 CLIST JOB 313; promotion INST20 JOB 314 (IEBCOPY
  replace, no compile / link; AMASPZAP dumps of both members identical: 33 CSECT records, 4494 hex rows), installed
  checks JOB 315 (1.0 oracle = REL20 runs) and JOB 316 (S2 = model, = R20 output byte for byte), final CLIST JOB 317
  (default RULES(ARCADE)). INSTALLED 2.0: HERC01.PACMAN.LOAD(PACMAIN) = copy of the R20 build of record (JOB 307 / 314),
  CLIST JOB 317; JOB 298 historical. HISCORE untouched. Harness only: test_hs made run-only aware (no assemblies in a
  run-only deck) and prefix-aware (PACMAN_PREFIX) for the CLIST-block lines. Next: G8.4 (minimal live) on the user's go.
- G8.4 PASS (2026-10-14, docs/evidence/g8-live.md): installed release, CLIST with NO operand (scenario G8,
  tools/gp2_live.py, tests/s2live/LIVEG8.txt) played twice: 180/180 writes = model each (ARCADE, 120 x 27, GRAPHIC 4x2,
  REALTIME, PATTERN), clean QUIT -> READY, HISCORE not rewritten (1050 < 1430); 7 screen captures (c3270 PrintText).
- G8.5 release material prepared (NOT tagged): docs/BENCHMARKS.md, final docs/CAPABILITIES.md, README for 2.0,
  releases/2.0-MVS-MAX/ (RELEASE-NOTES, MANIFEST, DEFAULTS, CAPABILITIES, BENCHMARKS, SHA256SUMS, decks of record,
  screenshots). Release approved by the user (2026-10-14).
MVS-G8 COMPLETE: annotated tag `2.0-mvs-max` on commit 94fd6f6 (2026-10-14). Installed release verified after tagging
by the read-only JOB 318: AMASPZAP dumps of HERC01.PACMAN.LOAD(PACMAIN) = HERC01.PACMAN.R20.LOAD(PACMAIN) (build of
record REL20 JOB 307) = the JOB 314 promotion; HERC01.PACMAN.CLIST(PACMAN) = the tagged src/clist/PACMAN.clist
(RULES(ARCADE)). Nothing pushed (no remote configured).
Accepted as documented: tests/test_rt.py and tests/test_s1.py pin sources to their own phases and need
PACMAN_LATER_PHASE=G8 when run alone (as at mvs-s2); the guards are not weakened.

THE MVS BRANCH IS COMPLETE: 2.0-MVS-MAX is the final MVS release (roadmap decision 3). No active phase. The z/OS port
(ZOS-*) is NOT started and needs a separate roadmap and the user's go; S3/S4 companion audio is optional, client-side
and not started.

z/OS PORT (branch `zos`, worktree ~/Documents/Worktrees/Pacman-zOS; `main` keeps the MVS line unchanged).
Plan docs/ZOS-MIGRATION-PLAN.md APPROVED 2026-10-14 (D44): phases ZOS-0 .. ZOS-10, 2.0-mvs-max = functional oracle,
release 2.0-ZOS / tag 2.0-zos. Target IBM Z Xplore (shared, non-production), prefix Z00000.PACMAN.
ZOS-0 Discovery COMPLETE: PASS, no blockers (tag zos-0 on 1e5a9eb, 2026-10-14). Evidence
docs/evidence/zos0-discovery.md, summary docs/ZOS-ENVIRONMENT.md, oracle tests/oracle20 (tools/oracle_extract.py).
JOB08215 (IEFBR14, no DD, CC 0000, not purged) is the ZOS-0 submit/spool evidence. No Z00000.PACMAN.* dataset exists.
Open ZOS-1 questions (NOT settled facts): the Enterprise COBOL release actually used by the site compile procedure;
AMODE 24 viability; the HLASM / binder build procedure; the z/OS DISPLAY / SYSOUT format; the listing translator for
the existing tests; PDS viability for Z00000.PACMAN.DATA.
ZOS-2 candidate C1 (docs/ZOS-DIFFS.md): PACQRY paragraph VALIDATE, unchanged.
ZOS-1 Toolchain COMPLETE: PASS (tag zos-1, 2026-10-14). Enterprise COBOL 6.5.0 P260714, HLASM R6.0, IEWBLINK;
datasets Z00000.PACMAN.{COBOL,COPY,ASM,CLIST,OBJ,LOAD} PDSE + DATA PDS (JOB08252); 23 release sources + 2 probes
uploaded IBM-037, byte-identical; IGYWCL hello JOB08254; probes J3 JOB08331 (AMODE 24) and J4 JOB08335 (AMODE 31) PASS;
DISPLAY SYSOUT FBA 121 (safe line limit 120 = oracle maximum); tools/zowe listing translator working. Build profile A
= D45 (docs/zos-build.md): proven for the toolchain probe only, not for the full application; profile B fallback only.
Evidence docs/evidence/zos1-toolchain.md. No job purged.
Carried into ZOS-2: candidate C1 (PACQRY paragraph VALIDATE), AMODE 24 of the full module, full-size listing checks.

## ZOS-2 Portable core - IN PROGRESS
Approved (2026-10-14): local tooling and Z2-1 (PACZ2CMP, diagnostic compile inventory: no bind, no run, no source
change, no COND between modules); Z2-2 / Z2-3 / Z2-4 approved in architecture only, each needs the full rendered JCL
and its expected step/result matrix reviewed before submission. SSRANGE: optional diagnostic only, never automatic,
never in the release build. Out of ZOS-2: TSD / full screen, CLIST install, PACMAIN promotion, live 3270.
C1 (VALIDATE): no fix before the compiler confirms it; if it is the only issue the preferred resolution is a minimal
paragraph rename in the zos branch source (port compatibility delta) + MVS oracle/model regression, applied only after
the user approves it. main and the MVS release are not touched.
- Local tooling done: make_deck.py --target zos (tools/zowe/zos_target.py), zos_listing in-stream PROCs, zos_equiv,
  zos_compile_report, tests/test_zos_tools.py PASS, R3 gate (tools/zowe/r3_gate.py: 13 release decks = SHA256SUMS,
  94 MVS deck generations = zos-1) PASS.
- Z2-1 PACZ2CMP JOB08497 (docs/evidence/zos2-portable-core.md): C1 not confirmed (PACQRY RC 0); C2 = ANS-68
  `01 <name> COPY <member>` in 9 modules (RC 12, only cause); C3 = ASMA303W PACFSIO (benign); PACHSIO incomplete
  (job cancelled S722 at the ~5,000-line site output limit). STOPPED: waiting for the user's decisions. No source
  changed.
- Decisions (user, 2026-10-14): C1 disproved (no rename); C2 -> Z1 applied on branch zos (28 substitutions, guards
  tests/zos_c2.py, test_core_frozen / test_g8 explicit allowance, R3 gate split: generator + release decks on the
  2.0-mvs-max sources, z/OS tree differs only by Z1 lines) - local checks PASS; C3 accepted provisionally (sole
  ASMA303W, base R15) as technical debt for recovery work; PACHSIO: standalone compact assembly (deck ZHSA) to be
  shown before submission; no LINES=, no full GP2 battery in ZOS-2 (full regression = ZOS-9/10): Z2-2..Z2-4
  redesigned as small jobs (tools/zowe/zos_target.py CHUNKS, matrix tools/zowe/zos_plan.py, every job < 4,000
  estimated spool lines; zos_equiv --subset, PACTSOT clock by the RT3 rules).
- Z1 members uploaded and verified 9/9, other members 14/14 unchanged; PACZ2HSA JOB08810 RC 0, 266 records, END
  processed, no diagnostic, OBJ(PACHSIO) written: PASS.
- PACZ2BLD JOB08888 (binder LIST without MAP): 10 COBOL RC 0 clean, PACTSO / PACHSIO RC 0, PACFSIO RC 4 = C3 only,
  LINK RC 0, LOAD(PACZ2D) AMODE 24 / RMODE 24 / RENT, entry PACMAIN: build PASS (accepted as build of record).
- PACZ2C1 JOB08984: RUN1..RUN5 RC 0, = oracle 307 and models, 3,586 spool lines: PASS.
- PACZ2C2 JOB09000: RUN6..RUN8 RC 0, = oracle 307 and models, 3,532 spool lines: PASS.
- PACZ2C3 JOB09015: RUN9 RC 0, = oracle 307 and model, 839 spool lines: PASS.
- PACZ2C4 JOB09023: RUN10 EDGE3 RC 0, = oracle 307 and model (WIN / TURNS 319 / SCORE 1000 / LIVES 2), 3,578 spool
  lines: PASS.
- PACZ2C5 JOB09027, PACZ2C6 JOB09030, PACZ2C7 JOB09031 (batch approval): all runs RC 0, = oracle 307 and models.
  Combined CLASSIC validation (25 runs, order, models, MVS-7 before/after): PASS.
- PACZ2G1 JOB09069: 10 ARCADE runs RC 0, = oracle 310 (own blocks) and ref_gp2: PASS.
- PACZ2G2 JOB09114 (S1S2 removed): 8 REALTIME runs (5 CLASSIC, 3 ARCADE) RC 0, = oracle 310 own blocks, ref_rt and
  ref_gp2: PASS. NEXT: PACZ2G3 review (not submitted). CLIST install / interactive EXEC stay in the later z/OS platform/install phase.
- Tool fix 4ff8b4d (accepted): zos_equiv --subset anchors each step at its own oracle block.
- KNOWN ZOS-2 TOOLING ISSUE (open, not to be solved before an RP-specific design is approved): oracle 309 (RP) holds
  80 run datasets for 81 PACMAIN run steps (RPT1's TSD output follows the IEBUPDTE listing after one empty line, not
  the TK4- two-line separator), so no 309 step is anchorable and PACZ2RP would fail "cannot be anchored". Oracle 309
  is not modified, the anchoring rules are not weakened, no generic content-search fallback is added.
