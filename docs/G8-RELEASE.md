# MVS-G8 / 2.0-MVS-MAX: final MVS release - COMPLETE (tag 2.0-mvs-max) - design (D43, APPROVED and frozen 2026-10-14 with the
release-integrity amendment; user decisions in section 8)
Source: docs/ROADMAP-POST-RT.md row 8 ("Final capability matrix, CLIST default `RULES(ARCADE)` + best profile (GS,
REALTIME, SOUND if S1 passes), benchmarks (bytes/frame, frame jitter), screenshots, README "what runs on MVS vs the
client", rebuild from empty libraries under a new prefix, tag `2.0-mvs-max`"), requirements v4 sec. 25 (G8 visual
optimisation, G9 maximum mode = automatic selection of the best supported profile), sec. 26 (MVS-G8 acceptance: "the
project uses the maximum viable presentation without breaking compatibility"), sec. 27 (authenticity rule), sec. 28
(capability matrix). Roadmap decision 2 (2026-10-11): after GP1 and GP2 are live-validated (done), the CLIST defaults to
`RULES(ARCADE)`.

## 0. What G8 is (and is not)
- A **release phase**, not a feature phase. Every capability it ships is already built and live-validated (G1-G4, GS,
  RT, S1, GP1, GP2, HS, RP, S2); the ceilings are known (G5/G6 negative D30, G7 negative D42).
- **No change to GAME / MAP / AI / PACARC / PACRT / PACSCR / PACDISP / PACPLAT / PACMAIN / assembler sources.** The
  2.0 program is built from the S2 sources (installed JOB 298 link) in empty R20 libraries (section 5); the validated
  R20 load module, not JOB 298, becomes the installed final PACMAIN (JOB 298 stays historical evidence).
  tests/core_baseline.json unchanged.
- Changes: the CLIST defaults (section 2), the ALLOC deck space for a fresh install (section 5), a release deck, test /
  benchmark / screenshot tooling, documentation, the release folder and the tag.
- No probe: no capability is unproven. Out of scope (unchanged): ZOS-*, Zowe, S3/S4 companion audio (after 2.0).

## 1. Steps
| Step | Content | Exit |
|---|---|---|
| G8.1 | this design | user approval, D43 frozen |
| G8.2 (BUILD GREEN 2026-10-14, JOBs 302-304; docs/evidence/g8-build.txt) | CLIST defaults, ALLOC space, deck `REL20`, tests/test_g8.py, tools/g8_bench.py (deterministic bytes/frame), CLIST-dependent checks of earlier decks adapted | build green on Hercules under `HERC01.PACMAN` (not installed) |
| G8.3 (COMPLETE 2026-10-14, JOBs 305-317; docs/evidence/g8-install.txt) | on the user's approval: fresh build from empty libraries under `HERC01.PACMAN.R20` (ALLOC, REL20, CLIST, DATA, regression decks with `--prefix`, JCL audit), then install: the validated R20 PACMAIN copied into `HERC01.PACMAN.LOAD` and the final CLIST, with installed checks | all checks PASS on R20 and on the installed copy; install jobs |
| G8.4 (PASS 2026-10-14; docs/evidence/g8-live.md) | minimal live smoke of the installed release (section 9) + the screenshot set | docs/evidence/g8-live.md |
| G8.5 (COMPLETE 2026-10-14, tag 2.0-mvs-max on 94fd6f6; post-tag check JOB 318) | final capability matrix, benchmarks page, README (incl. "what runs on MVS vs the client"), releases/2.0-MVS-MAX (decks + SHA256SUMS), CURRENT_PHASE, roadmap | tag `2.0-mvs-max` |

## 2. Default profile = maximum mode (D43.1)
The CLIST `PROC` defaults become the maximum viable profile; the only value that changes is `RULES(CLASSIC)` ->
`RULES(ARCADE)` (roadmap decision 2). Every other default already selects the maximum automatically:
| Keyword | 2.0 default | Selection (no new code) |
|---|---|---|
| COLOR | AUTO | Read Partition Query (D40-hardened); colour -> full-screen TSC, else monochrome line mode |
| HILITE | AUTO | QCode 87 |
| GLYPHS | AUTO | GRAPHIC when the reply announces GE + the APL set (E9: c3270 does) |
| SCALE | AUTO | 4x2 when colour + highlight + GRAPHIC are active, else the G4 glyph look |
| CANVAS | AUTO | largest validated alternate size (120x27 / 132x27 / 80x32 / 80x43), else 80x24 |
| REDRAW / ANIM | PARTIAL / AUTO | G3 partial redraw + animation |
| PLAY | REALTIME | needs colour full-screen, else TURN |
| SOUND / ALARM | AUTO / PATTERN | 3270 alarm, D41 patterns |
| RULES | **ARCADE** (was CLASSIC) | power pellets, levels, fruit, high score, READY!, popups |
| SPEED / LEVEL / AI / GHOSTS / METRICS | NORMAL / 1 / 1 / 1 / NO | unchanged |

- **No new keyword** (no `PROFILE(MAX)`): the AUTO chain *is* G9 "maximum mode", and it degrades on its own
  (requirement G9 + "without breaking compatibility"). `COLOR(AUTO)` stays the default (not `YES`): it is the only
  setting that falls back correctly on a monochrome terminal. D28 (idle ticks held after the query) does not affect
  REALTIME, which waits for the first arrow anyway (RT0: D28 released by the first AID).
- **Compatibility is explicit**: `RULES(CLASSIC)` = the 1.0-MVS game (byte-identical batch / line mode; CLASSIC
  screens unchanged since S2); `PLAY(TURN)`, `CANVAS(DEFAULT)`, `SCALE(NO)`, `GLYPHS(CLASSIC)`, `COLOR(NO)`,
  `SOUND(NO)`, `ALARM(SINGLE)` keep every earlier look. Batch (cards) stays the reference (D18): the PARM default of
  PACMAIN is not changed, so a batch run without the RULES column is still CLASSIC.
- With ARCADE the default, the CLIST high-score block (`&SYSDSN` + ALLOC PACHS or DUMMY) runs on every default game.

## 3. Benchmarks (D43.2)
Two kinds, kept apart:
1. **Deterministic cost per frame** (bytes per write), from Hercules TSD dry-run streams (the same streams the models
   check) - reproducible, no client involved. tools/g8_bench.py reads build listings and reports, per profile, the
   bytes of the first full screen, median / p95 / max bytes per quantum write, alarm writes, end screen. Profiles:
   line mode (CLASSIC, G0 baseline above), G1 full redraw, G3 partial, G4 GRAPHIC, GS 4x2 80x24, GS 4x2 120x27 wide,
   ARCADE GS 120x27 (the 2.0 default). Sources: the REL20 regression listings (no new runs where an existing deck
   already covers the profile; one small bench step set in REL20 for any missing profile).
2. **Live timing** (frame jitter), from c3270 `-trace` files analysed by tools/c3270_rt_game.py: gap median / p95 /
   max, lateness, drift, skipped periods, for the default profile at NORMAL (150 ms) and FAST (125 ms). Accepted
   values are reported, not targets. **Reused, not re-measured** (amendment): the valid RP live analyses (RP.3 FAST
   docs/evidence/rp3-fast-live.md, RP.4 NORMAL / FAST docs/evidence/rp-live.md) and the S2 live runs; the program
   loop is unchanged since then, so no long live session is repeated. The G8.4 smoke trace adds one short sample.
   Host CPU utilisation: not part of the release.

## 4. Screenshots (D43.3)
- **Real screenshots**: PNG captures of the macOS Terminal window taken by the user during G8.4 (the only way to show
  the actual client rendering, fonts and colours). Set: READY! (120x27), ARCADE in play with a frightened ghost, the
  score popup, the end screen with the high score, RULES(CLASSIC) 4x2, 80x24 fallback, line mode (COLOR(NO)).
  Small set, stored in releases/2.0-MVS-MAX/screenshots/ (PNG; no logon screen, no password, no session data).
- **Reproducible text captures**: the same screens as UTF-8 text rebuilt from the deterministic model streams (the
  ones Hercules matched byte for byte), so anyone can regenerate them; the live traces themselves are never committed
  (they hold terminal / session information).

## 5. Fresh rebuild under a new prefix (D43.4)
- Prefix **`HERC01.PACMAN.R20`** (the 1.0-MVS precedent was `HERC01.PACMAN.R10`). Only HERC01.PACMAN.* is touched.
  The R20 project libraries are newly allocated and empty before REL20 (ALLOC fails rather than reuse: DISP=NEW;
  a pre-existing R20 dataset is a stop condition, never scratched silently).
- **JCL audit** (tools/g8_jcl_audit.py, run on every generated R20 deck before submission and on the listings after):
  every project DSN (DD, PARM, CLIST text, ALLOC in TMP input) must start with `HERC01.PACMAN.R20.`; allowed others
  are system libraries (SYS1.*, the compiler / TMP libraries named in docs/mvs-build.md) and temporaries (&&); any
  `HERC01.PACMAN.` name without `.R20.` fails the audit. No JOBLIB / STEPLIB to the old libraries.
- The ALLOC deck's 1.0 space (COBOL 15,5 tracks, LOAD 15,5) is too small for 2.0 (7048 source lines; the working
  install needed COMPRESS several times): the ALLOC primary / secondary space is raised so a fresh install builds and
  regresses without COMPRESS. Existing installs are not touched (ALLOC is first-use only).
- New deck `REL20` (job `PACREL20`): uploads every copybook and source, compiles, assembles PACTSO / PACFSIO / PACHSIO,
  links `<prefix>.LOAD(PACMAIN)`, then a compact regression: the 1.0-MVS oracle cases (CLASSIC batch = 1.0 bytes) and
  a selection of TSD runs per renderer. The build of record is REL20 plus the existing regression decks rerun with
  `--prefix HERC01.PACMAN.R20` (S2, RP, GP2, GP23, HS; tests unchanged), all PASS, then a final REL20 link so the
  R20 PACMAIN is the REL20 link of record. `tools/release_check.sh` is extended to run the 2.0 sequence (the 1.0 path
  kept).
- **Install = the validated artifact** (amendment): IEBCOPY of `HERC01.PACMAN.R20.LOAD(PACMAIN)` into
  `HERC01.PACMAN.LOAD(PACMAIN)` (replace), no relink; the same job runs a short batch / TSD check set against the
  installed copy (= models) and a byte compare of the two members (IEBCOMPR or a listing of both). The final CLIST
  (section 2) is installed in `HERC01.PACMAN.CLIST(PACMAN)` and also in R20. The release manifest records the R20
  link job, the copy job and the CLIST jobs.

## 6. Documentation (D43.5)
- docs/CAPABILITIES.md: final matrix, every row CONFIRMED / NOT SUPPORTED / NOT AVAILABLE with its evidence, and a
  "2.0 profile per terminal" table (what AUTO selects for each answer of the query).
- docs/BENCHMARKS.md: section 3 results.
- README rewritten for 2.0-MVS-MAX: quick start with the default profile, options table, compatibility modes, and the
  sec. 27 authenticity section **"What runs on MVS and what runs on the client"**: everything (game, rules, AI,
  timing, screens, 3270 data stream, alarm, high score file) runs in MVS 3.8J; the Mac side is only the c3270 terminal
  (rendering, fonts, bell setting, keymap `tools/c3270_rt.sh`) and the optional Python helpers that type the EXEC
  (`tools/rt_play.py`) or analyse traces - none of them takes part in the game. No companion audio in 2.0.
- releases/2.0-MVS-MAX/: ALLOC, REL20, CLIST, DATA decks for the default prefix, SHA256SUMS of the sources.

## 7. Tests and edge cases (D9, D10, D12)
- test_g8: CLIST PROC defaults as section 2; the PARM built by the CLIST for the default call and for
  `RULES(CLASSIC)` (TMP run of the CLIST block, as HS / RP3 do); CLASSIC batch = 1.0 oracle; core baseline unchanged;
  sources linked by REL20 = the installed S2 sources (SHA256).
- Edge cases to cover (Hercules where possible, else live): default call with DATA missing (DUMMY, `HIGH SCORE
  UNAVAILABLE`); default call on a monochrome / no-reply terminal (line mode, TURN; Hercules TSD-less = covered by
  the D40 sequences); 80x24 terminal (GS 80x24); window too small for the scaled maze (G4 fallback, GX size guard);
  `RULES(CLASSIC)` explicit (CLASSIC screens = S2 references); batch without the RULES column = CLASSIC.
- Every earlier regression stays: test_s2, test_rp, test_gp2, test_hs (PACMAN_LATER_PHASE=G8), test_core_frozen,
  test_mvs8 (1.0 oracle).

## 8. Decisions for the user (proposed; see 8a for the approved form)
1. Default profile = section 2 (only RULES flips to ARCADE; COLOR stays AUTO; no PROFILE keyword).
2. Benchmarks = section 3 (deterministic bytes from Hercules + live jitter NORMAL and FAST; host CPU optional).
3. Screenshots = section 4 (PNG taken by the user in G8.4 + text captures from the trace).
4. Fresh rebuild = section 5 (`HERC01.PACMAN.R20`, larger ALLOC space, deck REL20 + existing regression decks).
5. Tag `2.0-mvs-max` and folder releases/2.0-MVS-MAX after G8.4 PASS; G8 is the last MVS phase (S3/S4 optional after).

## 8a. User decisions (2026-10-14, D43 APPROVED with a release-integrity amendment)
1. Only the CLIST default changes, `RULES(CLASSIC)` -> `RULES(ARCADE)`. PACMAIN / direct-call absent-PARM behaviour is
   not changed (absent RULES column = CLASSIC). No `PROFILE(MAX)`. AUTO capability fallback preserved. The complete
   final CLIST default set (section 2 table) is frozen and documented in the README and the release folder.
2. Benchmarks as section 3; NORMAL / FAST cadence and jitter reused from the valid RP live traces; no long live session
   repeated; host CPU not required.
3. A small final screenshot set plus reproducible text reconstructions; no credentials / logon information in
   screenshots or repository artifacts.
4. Clean rebuild under `HERC01.PACMAN.R20`: newly allocated empty project libraries; release JCL audited so no project
   DD resolves to the old `HERC01.PACMAN.*` libraries (system libraries allowed); allocation and directory sizes
   raised so the rebuild does not depend on COMPRESS. After the R20 build and regressions pass, the validated R20
   artifact becomes the installed final PACMAIN (copied, section 5) and the final CLIST is installed, followed by a
   short installed smoke. JOB 298 remains historical evidence, not the 2.0 module.
5. Release directory `releases/2.0-MVS-MAX/` and the authoritative annotated tag `2.0-mvs-max`. The folder holds what
   identifies and reproduces the release: commit / build manifest, build-of-record JOBs, capability matrix, benchmark
   summary, release notes, final defaults, screenshots / reference text. Live traces with terminal / session
   information are never committed.

## 9. Final live requirement (minimal, after the installed release)
- `EXEC '<prefix>.CLIST(PACMAN)'` with no RULES: ARCADE is the default (power pellets / READY! / ARCADE HUD shown).
- Preferred 120x27 full-screen rendering (c3270 `-model 2 -oversize auto`, GS 4x2 wide layout).
- A short representative ARCADE sequence (moves, a pellet, a power pellet if reached), then a clean QUIT -> READY.
- Nothing else: no feature work, no soak. Existing GP / RP / S2 live evidence stays valid.
