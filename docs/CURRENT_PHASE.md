El documento maestro de requisitos esta en docs/requirements/PACMAN_MVS_ZOS_REQUISITOS_DESARROLLO_v4.docx. No releerlo completo en cada sesion;
consultar unicamente las secciones de la fase actual cuando CURRENT_PHASE.md lo indique (G4: sec. 25 fila G4 y sec. 26 MVS-G4).

MVS-G3 COMPLETE (tag mvs-g3, 2026-10-08, final build JOB 188): partial redraw (Write X'F1' + TPUT NOEDIT) and glyph animation with an idle
visual tick; options REDRAW(PARTIAL|FULL), ANIM(AUTO|YES|NO), METRICS(NO|YES). Final manual checklist PASS (AUTO, COLOR(YES) HILITE(YES),
ANIM(NO) REDRAW(FULL), COLOR(NO)). Design, results, known limitation: docs/G3-PARTIAL.md (D27, D28).
KNOWN LIMITATION (D28, investigation closed deliberately): in TK4-/MVS 3.8J + TSO + c3270, COLOR(AUTO) performs a capability Query Reply
that leaves the idle ticks held until the first AID; after the first input the animation works normally. COLOR(YES) HILITE(YES) skips the
query and the animation starts immediately (recommended on TK4-/c3270). Not a fault of the mechanics or of the G3 renderer.
Pending note (from G1, not G3 work): the ESTAE abend-restore exit in PACFSIO is implemented but not validated live.

NEXT (new session, NOT STARTED): MVS-G4 - advanced glyphs (master doc sec. 26): try the graphic/APL characters available, alternative
wall/corner tiles, charset profiles, document visual differences per emulator; acceptance: a look closer to the arcade without Programmed
Symbols. Fallback: G3. Capability matrix rows to use: "APL / graphic character set (GE order)" (QCode 85 announced, contents to decode).
Start by reading: CLAUDE.md, docs/CURRENT_PHASE.md, docs/DECISIONS.md (D22-D28), docs/G1-RENDERER.md, docs/G2-HIGHLIGHT.md,
docs/G3-PARTIAL.md, docs/CAPABILITIES.md. Regression to keep: tests/test_g3.py (oracle 1.0-MVS + TSO + 199 TSC streams),
tests/test_g2.py (on its listing), tests/test_core_frozen.py. Probe lesson (G1, G3): check every TPUT length (never `LA 0,n(0)`), trace at
the TPUT boundary, and verify on the terminal side (c3270 -trace, tools/c3270_*.py) before concluding anything from visuals.
1.0-MVS is the immutable functional baseline; z/OS out of scope.

MVS-G4 IN PROGRESS (2026-10-08): probe E9 CLOSED, PASS (JOB 190; docs/evidence/g4-probe-analysis.md): GE supported, LCID F1 =
charset 963 / CP310 APL, base 697 / CP037, no loadable PS, box-drawing maze rendered live in c3270. Design docs/G4-GLYPHS.md
APPROVED (all five points). Research/design checkpoint committed; implementation next (CLASSIC = G3 byte for byte, core frozen).
