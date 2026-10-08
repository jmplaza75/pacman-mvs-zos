El documento maestro de requisitos esta en docs/requirements/PACMAN_MVS_ZOS_REQUISITOS_DESARROLLO_v4.docx. No releerlo completo en cada sesion;
consultar unicamente las secciones de la fase actual cuando CURRENT_PHASE.md lo indique (G5 cerrada; renderer escalado 2x2: ver NEXT).

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

NEXT (NOT STARTED, needs the user's go): scaled renderer, preferably 2x2 (arcade-style wall contours deferred from G4), the next
meaningful visual improvement for the real environment. Start by reading: CLAUDE.md, this file, docs/DECISIONS.md (D24-D30),
docs/G4-GLYPHS.md (sec. on deferred contours), docs/G3-PARTIAL.md, docs/CAPABILITIES.md. Probe lessons (G1-G5): check every TPUT
length (never `LA 0,n(0)`); any inbound (Query Reply too) locks the keyboard until a write with keyboard restore; ENTER on an
unformatted screen sends the whole screen text (size TGET buffers or expect queued remainders); verify on the terminal side
(c3270 -trace, tools/c3270_*.py) before concluding anything from visuals.
