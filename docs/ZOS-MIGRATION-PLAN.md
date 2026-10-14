# z/OS migration plan: 2.0-MVS-MAX -> z/OS (PROPOSED, awaiting approval)
Status: APPROVED 2026-10-14 by the user (decisions in sec. 17, D44). Nothing has been run on z/OS yet: no z/OS
connection, no z/OS dataset, no source change. Once approved, this document is the source of truth for the second half of the project (it replaces the
`zos-migration.md` placeholder of requirements v4 sec. 16 and refines requirements sec. 12-15, see section 15).
Phases start one at a time, on the user's go, exactly as the MVS phases did (CLAUDE.md, requirements sec. 17).

Inputs: tag `2.0-mvs-max` (94fd6f6), requirements v4 (sec. 3, 12-17, 23-24), docs/ARCHITECTURE.md, ENVIRONMENT.md,
DECISIONS.md (D1-D43), CURRENT_PHASE.md, CAPABILITIES.md, BENCHMARKS.md, mvs-build.md, releases/2.0-MVS-MAX/, the
module sources (src/), the deck generator (tools/make_deck.py) and the test/model harness (tests/).

---------------------------------------------------------------------------------------------------------------------

## 1. Central rule and derived rules
**R0 - Functional oracle.** `2.0-mvs-max` is the immutable functional reference. During the port no gameplay, scoring,
timing, AI, presentation, sound, PARM / CLIST interface or defaults change, unless z/OS technically forces it; every
such case is recorded as a numbered entry (Z1, Z2, ...) in docs/ZOS-DIFFS.md with cause, evidence and user approval
before it is merged. No new gameplay feature, option or screen is added during the port.

Derived rules (binding in every ZOS phase):
- **R1 Shared source.** One source tree. The shared sources (src/cobol, src/copy, src/asm, src/clist) stay byte-identical
  to `2.0-mvs-max`; the gate is `git diff 2.0-mvs-max -- src/cobol src/copy src/asm src/clist` = empty, plus SHA-256 of
  each file against releases/2.0-MVS-MAX/MANIFEST.md. A module that z/OS forces to differ gets a **z/OS override** in
  `src/zos/<same name>` (requirements sec. 16: only platform-dependent artefacts are duplicated), approved per Z-entry.
  The MVS copy is never edited for z/OS.
- **R2 Core never forks.** PACGAME, PACMAP, PACAI, PACRT, PACSTATE, PACMREQ, PACARC (and maps) may not get a z/OS
  override. If one fails on z/OS, the phase stops and the user decides (a fix would be a shared-source change, i.e. an
  MVS change, which needs its own MVS regression and a new MVS tag; see section 2).
- **R3 MVS stays reproducible.** Harness changes must leave the MVS output unchanged: `make_deck.py` regenerates every
  deck in releases/2.0-MVS-MAX/decks byte for byte (SHA256SUMS), and all MVS tests pass. z/OS generation is a separate
  target (`--target zos`), never a change of the MVS default.
- **R4 Batch is the reference.** Batch card mode and the TSD mode (the 3270 data stream written to SYSOUT) are the
  first thing proven on every layer; live 3270 only validates what batch cannot reach (D18).
- **R5 Determinism.** Seed 12345, tie order U,D,L,R, AI0 and the controlled modes keep working unchanged (D9, D10, D14).
- **R6 Dialect.** The conservative IKFCBL00 dialect stays the rule for shared COBOL (no ref-mod, no inline EXIT, no
  `>=`/`<=`, no nested subscripts, copy members start with their own 01, column 72; D2-D4, D8, D13, D16). Enterprise
  COBOL features may appear only in a z/OS override and only when forced.
- **R7 Namespace and secrets.** Only `<HLQ>.PACMAN.*` is created or written on z/OS; the HLQ is a parameter, never a
  literal in the repository (requirements sec. 14). Zowe profiles / passwords / tokens / certificates never enter git
  (requirements sec. 15). MVS datasets HERC01.PACMAN.* are not touched by any ZOS phase.
- **R8 Evidence.** A ZOS phase closes only with an executed test on z/OS, evidence in docs/evidence/zos-*, README and
  CURRENT_PHASE updated, every documented edge case tested (D12), and a git tag.

## 2. Baseline, branch and rollback
- **Functional baseline:** tag `2.0-mvs-max` (94fd6f6) + the installed MVS release (HERC01.PACMAN.LOAD(PACMAIN) = copy
  of HERC01.PACMAN.R20.LOAD(PACMAIN), CLIST JOB 317). It is never modified by this plan.
- **Branch and folder:** branch `zos` created 2026-10-14 from `main` 0b7d154 (= tag `2.0-mvs-max` 94fd6f6 plus three
  post-tag documentation files; src/ identical to the tag), checked out as a git worktree outside the repository
  tree: `~/Documents/Worktrees/Pacman-zOS` (the git root is `~/Documents/Projects`, so the project lives in
  `~/Documents/Worktrees/Pacman-zOS/Pacman MVS and zOS`). The MVS checkout (its `build/` listings, `.env`, Hercules
  tooling) is never touched by z/OS work; `main`, `2.0-mvs-max` and releases/2.0-MVS-MAX stay unchanged. A defect found on z/OS
  that is a real defect of the shared source is fixed on `main` first (MVS phase, full MVS regression, new MVS tag) and
  then merged into `zos`; never fixed only on `zos`.
- **Oracle archive (made in ZOS-0, local only):** `build/` is gitignored, so the 2.0 listings of record are frozen
  into `tests/oracle20/` (per-run SYSOUT extracted and normalised, gzip, SHA-256 index): JOB 307 (REL20, 60 steps, 1.0
  oracle + CLIST PARMs), 308 (S2, 2986 streams), 309 (RP: 6265 + RP3 1495 streams, 29 D40 sequences, 9 BAT runs),
  310 (GP2), 311 (GP23), 312 (HS, 21 runs), 315 (installed 1.0 oracle), 316 (installed S2). The live traces of
  record (g8-live, rp-live, rp3-fast-live, s2-live, gp2-live) are already under docs/evidence/.
- **z/OS rollback:** every promotion on z/OS copies the current `<HLQ>.PACMAN.LOAD(PACMAIN)` and CLIST to
  `<HLQ>.PACMAN.PRV.*` first (IEBCOPY); rollback = copy back. Each phase tag (`zos-N`) is the git rollback point.

## 3. Starting architecture (2.0-MVS-MAX, as built)
One statically linked load module PACMAIN; shared state passed by reference; static `CALL 'X'`.
Call graph: PACMAIN -> PACINPT, PACGAME, PACRT, PACDISP, PACPLAT; PACGAME -> PACMAP; PACAI -> PACMAP; PACRT ->
PACGAME, PACMAP; PACDISP -> PACSCR, PACPLAT; PACPLAT -> PACTSO, PACFSIO, PACHSIO, PACQRY. Only PACPLAT calls assembler.
Interfaces: PACSTATE, PACREQ, PACMREQ, PACDS, PACPAL, PACARC (copybooks). PARM: fixed columns 1-25 (mode, AI, ghosts,
then one column per option: METRICS 11 ... ALARM 25), built by the CLIST. Test-only programs: PACTSOT (clock),
PACQRYT (query-reply sequences), probe PACRPE (forced abend for ESTAE).

## 4. Module portability matrix
LOC = lines in 2.0. "Host facility" = what the module touches outside COBOL computation.

| Module | Layer | LOC | Host facility used | Expectation | Action | Validated in |
|---|---|---|---|---|---|---|
| PACGAME | core | 603 | none | portable | recompile only; no override allowed (R2) | ZOS-2 |
| PACMAP | core | 90 | none | portable | recompile only (R2) | ZOS-2 |
| PACAI | core | 205 | none | portable | recompile only (R2) | ZOS-2 |
| PACRT | core (REALTIME steps) | 325 | none (timing via PACREQ only) | portable | recompile only (R2); timing behaviour validated with the platform | ZOS-2 (batch), ZOS-6 |
| PACARC / PACSTATE / PACMREQ | core copybooks | 53/27/7 | none | portable | unchanged | ZOS-2 |
| PACREQ / PACDS / PACPAL | interface copybooks | 98/6/139 | binary COMP fields shared with assembler | portable | unchanged; COMP/TRUNC checked (sec. 8) | ZOS-2/3 |
| PACMAIN | driver | 473 | PARM (LE PARM passing) | portable, LE PARM risk | recompile; PARM test incl. empty PARM | ZOS-2 |
| PACINPT | input | 289 | SYSIN QSAM (`UT-S-SYSIN`, `LABEL RECORDS ARE OMITTED`) | portable, dialect warnings | recompile; batch + TSO terminal input | ZOS-2, ZOS-4 |
| PACSCR | display (3270 composer) | 2242 | none (builds bytes) | mostly portable; EBCDIC literals | recompile; TSD streams = models | ZOS-5 |
| PACQRY | display (Query Reply parser) | 277 | none | portable | recompile; z/OS emulator replies as new test inputs | ZOS-5 |
| PACDISP | display | 774 | DISPLAY to SYSOUT, calls PACPLAT | partly platform-dependent (DISPLAY record format) | recompile; SYSOUT format checked | ZOS-2, ZOS-4 |
| PACPLAT | platform | 594 | RETURN-CODE, all host services via assembler | port (expected unchanged COBOL) | recompile; override only if a service contract changes | ZOS-3 |
| PACTSO | platform asm | 109 | ASCB/TSB test, STLINENO, STIMER (BINTVL, MICVL), STCK | port (likely assemble-as-is) | HLASM; clock + deadline probes | ZOS-3, ZOS-6 |
| PACFSIO | platform asm | 216 | TCLEARQ, STFSMODE, STTMPMD, TPUT FULLSCR/NOEDIT, TGET ASIS/NOWAIT, ESTAE, STIMER | port / possibly reimplement (24-bit TPUT/TGET, LE) | HLASM; addressing-mode decision (sec. 9) | ZOS-3, ZOS-5, ZOS-6 |
| PACHSIO | platform asm | 266 | RDJFCB, OPEN TYPE=J, BLDL, FIND, BPAM READ, QSAM UPDAT/OUTPUT, STOW at CLOSE, ESTAE | port / possibly reimplement (PDS vs PDSE, SMS) | HLASM; HS cases H1-H15 | ZOS-3, ZOS-8 |
| PACTSOT, PACQRYT | test drivers | 53/190 | as above | portable | recompile | ZOS-3, ZOS-5 |
| PACRPE (probe) | ESTAE test driver | 150 | forced S0C7 | behaviour changes under LE | rebuild; re-baseline expected abend path | ZOS-8 |
| PACHELLO | toolchain hello | 12 | `DISPLAY ... UPON CONSOLE` | portable (may need console authority) | ZOS-1 smoke (z/OS variant to SYSOUT if CONSOLE is refused) | ZOS-1 |
| JCL / decks | build | - | IEBGENER in-stream upload, IKFCBL00, IFOX00, IEWL+SYS1.COBLIB, IKJEFT01, IEBCOPY, IEBUPDTE, AMASPZAP | replace | `make_deck.py --target zos` + jcl/zos/ (sec. 7) | ZOS-1 onward |
| CLIST PACMAN | launcher | 75 | ALLOC DA(*), &SYSDSN, CALL 'dsn(member)' | adapt/test (expected as-is) | prefix substitution; run from READY and from ISPF 6 | ZOS-4 |
| tools (submit, run_deck, job_output, release_check) | harness | - | Hercules socket reader, JES printer file | replace for z/OS | tools/zowe/ (sec. 7) | ZOS-1 |
| c3270 tools (trace, rt_play, *_trace) | live harness | - | c3270 trace of localhost:3270 | adapt (host, TLS, port) | parameters only | ZOS-5 |

## 5. Phase structure (summary)
The 2.0 source is complete; the port does not re-add features one by one. Every phase builds the same 2.0 PACMAIN
and widens the set of 2.0 regressions and live checks that must pass on z/OS. "Allowed to change" lists what the
phase may create or edit; everything else is frozen.

| Phase | Objective | Touches z/OS | Main gate |
|---|---|---|---|
| ZOS-0 Discovery | Inventory z/OS, toolchain, TSO/3270, datasets, permissions, Zowe; freeze the MVS oracle; no Pac-Man | read-only + one trivial job | discovery report complete, all blockers classified |
| ZOS-1 Toolchain | Zowe automation; hello COBOL + hello HLASM; compile-link-run; dataset layout; build profile | `<HLQ>.PACMAN.*` created | hello COBOL+ASM RC 0, upload byte identity, edit-upload-build-spool loop |
| ZOS-2 Portable core | Build the full 2.0 PACMAIN; batch CLASSIC = 1.0-MVS oracle; core decks = models | yes | 1.0 oracle + core model runs byte-identical |
| ZOS-3 Platform layer | PACTSO / PACFSIO / PACHSIO / PACPLAT services in batch and TSO batch (IKJEFT01) | yes | service probes + TSD decks green, no override unless forced |
| ZOS-4 CLASSIC | First complete game on z/OS: batch + TSO line mode, CLIST, RULES(CLASSIC) PLAY(TURN) | yes + live TSO | oracle + live TSO line-mode game |
| ZOS-5 Full-screen / graphics | Colour, highlighting, GE/APL glyphs, 4x2 renderer, geometry, Query Reply, D40 | yes + live 3270 | TSD streams = models; live replay = model byte for byte |
| ZOS-6 REALTIME | 150 / 125 ms loop, PF keys, deadlines, keyboard restore, pause, PA2 | yes + live 3270 | RT decks = models; live timing criteria |
| ZOS-7 ARCADE | GP1/GP2/RP rules: power, fright, eyes, fruit, levels, extra life, popups | yes + live 3270 | GP1/GP2/GP23/RP decks = models; scenario replays |
| ZOS-8 Services | High score, ESTAE recovery, alarm (S1) and patterns (S2) | yes + live 3270 | HS H1-H15, ESTAE E1-E3, S2 live |
| ZOS-9 Equivalence | Full MVS <-> z/OS regression against 2.0-mvs-max; every difference explained | yes | zero unexplained differences |
| ZOS-10 Release | Clean rebuild into empty libraries, promotion, final live, docs, tag | yes | release check green, tag |

## 6. Phases in detail

### ZOS-0 Discovery (read-only)
- **Objective:** know exactly what the target system offers before any design choice; freeze the MVS oracle. No
  Pac-Man source or dataset on z/OS.
- **Allowed to change:** docs/ZOS-ENVIRONMENT.md (new), docs/ZOS-DIFFS.md (new, empty register), tests/oracle20/ +
  tools/oracle_extract.py (local oracle freeze), tools/zowe/ discovery scripts (read-only commands), README pointer.
- **Frozen:** all of src/, jcl/mvs/, tools/make_deck.py MVS output, every MVS dataset.
- **Required z/OS capabilities to establish (each answered YES / NO / RESTRICTED with evidence):**
  1. System: z/OS release, sysplex/LPAR or zD&T/ZDT/Wazi/hosted (Z Xplore-type) system, JES2 or JES3, SMS rules for
     the HLQ (PDS allowed? PDSE forced? DSNTYPE defaults), space quota, RACF profile on `<HLQ>.*`.
  2. Zowe: CLI profile (z/OSMF or zFTP), `zowe files list`, upload / download (text with explicit encoding and
     binary), `zowe jobs submit --wait-for-output`, spool download; job class / MSGCLASS / output retention.
  3. COBOL: Enterprise COBOL version and PTF level (`IGYCRCTL`), site PROCs (IGYWCL / IGYWCLG), default options
     (TRUNC, NUMPROC, ARITH, DATA, RMODE, SSRANGE, codepage CODEPAGE()), LE release, SCEELKED / SCEERUN names, site
     CEEOPTS / CEEDOPT defaults (TRAP, STORAGE, MSGFILE).
  4. Assembler: HLASM (ASMA90) level, SYS1.MACLIB / SYS1.MODGEN availability; binder IEWBLINK level.
  5. TSO/3270: interactive TSO/E logon available? via TN3270 (host, port, TLS), VTAM logmodes offered (model 2-5,
     IBM-DYNAMIC / query-capable), is TSO READY reachable without ISPF, can c3270 connect (TLS options), does the
     TN3270 server pass the Read Partition Query reply to the application, ISPF option 6 behaviour.
     If there is no 3270 access at all (TSO only through z/OSMF / REST / SSH), phases ZOS-5/6 and the live parts of
     ZOS-4/7/8 cannot run: that is a blocker to report, not to work around.
  6. Utilities: IEBCOPY, IEBGENER, IEBUPDTE, IKJEFT01 in batch, AMBLIST / AMASPZAP for identity checks.
  7. Codepage: the EBCDIC table Hercules' ASCII reader applied to the MVS sources (measured on every character used
     in src/), versus the Zowe upload encoding (IBM-037 / IBM-1047). Sources use `[ ] ! | @ # $` outside comments,
     the characters that differ between CP037 and CP1047.
  8. One trivial job: `IEFBR14` (or a LISTCAT of the user's own HLQ) to prove submit + spool retrieval. Nothing else.
- **Build/install:** none.
- **Tests / oracles reused:** all MVS local tests re-run on the `zos` branch (proves the branch = 2.0); oracle freeze
  verified (each extracted run = the corresponding model, using the existing tests on the archived listings).
- **Live acceptance:** none (connection only).
- **Evidence:** docs/evidence/zos0-discovery.md (command transcripts, credentials redacted), docs/ZOS-ENVIRONMENT.md.
- **Exit criteria:** every item 1-8 answered; blockers classified (blocking / degrading / none); the build profile
  questions for ZOS-1 written down; oracle archive committed with SHA-256; the user approves the environment.
- **Checkpoint:** commit + tag `zos-0`.

### ZOS-1 Toolchain
- **Objective:** a repeatable edit -> upload -> compile -> link -> run -> spool loop (requirements sec. 13 ZOS-1,
  ZOS-2, ZOS-3 and ZOS-6 automation), and the build profile used by every later phase.
- **Allowed to change:** tools/zowe/ (upload one member, sync all, submit, wait, fetch spool, normalised listing
  adapter, encoding check), tools/make_deck.py (`--target zos` only, R3), jcl/zos/ (ALLOC, BUILD, LINK, RUN
  skeletons with the HLQ as a symbol), src/zos/PACHELLO variant only if `UPON CONSOLE` is refused, docs/zos-build.md.
- **Frozen:** shared src/, MVS decks (byte-identical regeneration checked).
- **Required capabilities:** ZOS-0 items 1-4, 6, 7.
- **Build/install actions:**
  1. ALLOC `<HLQ>.PACMAN.{COBOL,COPY,ASM,CLIST,JCL}` (PDS or PDSE, FB 80), `<HLQ>.PACMAN.LOAD` (PDSE: Enterprise
     COBOL >= 5 executables are program objects), `<HLQ>.PACMAN.DATA` (PDS, FB 80, see sec. 10), `<HLQ>.PACMAN.OBJ`.
  2. Upload with an explicit encoding; download binary and compare with the local file converted through the
     Hercules table (byte identity per member; no truncation past column 72/80).
  3. Hello COBOL (PACHELLO) and hello HLASM (a minimal CSECT called from COBOL, parameters + RC): compile, bind, run.
  4. Build-profile probe (decides sec. 9 question 1): the same hello pair bound (a) AMODE 24 / RMODE 24 with COBOL
     RMODE(24) DATA(24) and (b) AMODE 31 with the assembler below the line; a TPUT/TGET-free CALL chain, and a PARM
     with the PACMAIN column layout echoed back (LE PARM handling, sec. 8).
- **Tests reused:** tools/validate_source.py on every upload; R3 deck regeneration check.
- **Live acceptance:** none.
- **Evidence:** docs/evidence/zos1-toolchain.md (+ normalised listings).
- **Exit criteria:** hello COBOL and hello ASM RC 0000 with no IGY/ASMA warnings above informational (or each one
  explained); upload byte identity proven for all of src/; the loop runs from one command; build profile chosen and
  recorded as a D-number.
- **Checkpoint:** commit + tag `zos-1`.

### ZOS-2 Portable core
- **Objective:** compile the complete 2.0 source set unchanged (all COBOL + all assembler, so the module links) and
  prove the core is equivalent: batch CLASSIC = the 1.0-MVS oracle, batch ARCADE / TURN core runs = models.
- **Allowed to change:** z/OS decks (generated), tools/zowe, docs. A compile failure in shared source stops the phase
  (R1/R2); a z/OS override is allowed only for PACPLAT/PACTSO/PACFSIO/PACHSIO and only if the failure is
  platform-specific.
- **Frozen:** all shared sources; core without exception (R2).
- **Required capabilities:** ZOS-1 profile.
- **Build/install:** deck REL20 (`--target zos`) into `<HLQ>.PACMAN.LOAD(PACZ2D)` (not PACMAIN yet), no promotion.
- **Tests / oracles reused:** 1.0 oracle steps of REL20 (= JOB 307 / 315 SYSOUT byte for byte, right-stripped);
  tests/test_core_frozen.py (source pin); test_map, test_mvs2-8 on the z/OS listing; BAT runs of RP3 and S2;
  diagnostic runs (not release): regression with LE `STORAGE(00,..)` and again with `STORAGE(FF,..)` (identical
  output proves no dependence on uninitialised WORKING-STORAGE), and one with SSRANGE (no range error).
- **Live acceptance:** none.
- **Evidence:** docs/evidence/zos2-core.md, compile listings summary (IGY messages by severity).
- **Exit criteria:** every step RC 0000; zero IGY W/E/S without an entry in sec. 8 table; all batch runs = MVS oracle
  and models; STORAGE 00/FF identical; no shared source changed.
- **Checkpoint:** tag `zos-2`.

### ZOS-3 Platform layer
- **Objective:** every host service behind PACPLAT works on z/OS with the same contract (RC values, lengths, units):
  PACTSO CLS/WAIT/TIME/DLWT, PACFSIO in batch (RC 4 = not TSO, nothing issued) and in TSO batch (IKJEFT01), PACHSIO
  READ/REPL/WRIT on a test PDS, TSD output.
- **Allowed to change:** src/zos/PACTSO|PACFSIO|PACHSIO.asm and src/zos/PACPLAT.cob ONLY if forced (each a Z-entry);
  probe programs under src/probe/zos/; decks, tools, docs.
- **Frozen:** core, PACSCR, PACQRY, PACDISP, PACINPT, PACMAIN, copybooks, CLIST.
- **Required capabilities:** IKJEFT01 batch, STIMER/STCK, RDJFCB, a PDS for DATA (or the documented PDSE fallback).
- **Build/install:** decks RT (batch clock test PACTSOT), HS (batch part), RPE build; still into a test member.
- **Tests / oracles reused:** PACTSOT clock checks (monotonic ms, DLWT RC 4 when late); HS batch cases H1-H15
  (tests/test_hs.py, prefix-aware); TSD runs of the GS/GX/G4 decks (tests/test_gx.py, test_gs.py, test_g4.py) since
  TSD exercises PACPLAT end to end without a terminal; PACQRYT 29 D40 sequences.
- **Live acceptance:** none (live begins in ZOS-4).
- **Evidence:** docs/evidence/zos3-platform.md.
- **Exit criteria:** all listed decks = models / oracle; each service's RC contract proven including error paths
  (missing DD, missing member, empty / garbage member, full directory or its documented substitute); every override
  justified by a Z-entry or none needed.
- **Checkpoint:** tag `zos-3`.

### ZOS-4 CLASSIC (first complete Pac-Man on z/OS)
- **Objective:** a playable game through the most conservative path: batch cards, then TSO line mode via the CLIST
  with `RULES(CLASSIC) PLAY(TURN) COLOR(NO)`.
- **Allowed to change:** CLIST only by prefix substitution (already generated); src/zos/PACMAN.clist only if a TSO/E
  difference forces it (Z-entry); install decks.
- **Frozen:** everything else.
- **Required capabilities:** interactive TSO/E (READY), terminal SYSIN/SYSOUT (ALLOC DA(*)), CALL of a PDSE member.
- **Build/install:** first promotion: `<HLQ>.PACMAN.LOAD(PACMAIN)` + `<HLQ>.PACMAN.CLIST(PACMAN)` (installed z/OS
  baseline, rollback copy per sec. 2).
- **Tests / oracles reused:** RELEASE / MVS8 decks (1.0 oracle, TSO input rules D19, `***` avoidance D20 via
  STLINENO), CLIST PARM lines (test_g8 CLIST block check with the z/OS prefix).
- **Live acceptance:** TSO line-mode game from READY: moves, blocked move, empty-ENTER redraw, Q -> READY; one game to
  LOST; repeated from ISPF option 6 (compatibility note only). No `***` mid-frame.
- **Evidence:** docs/evidence/zos4-classic.md (+ terminal transcript).
- **Exit criteria:** oracle green on the installed module; live checklist PASS; CLIST defaults unchanged from 2.0.
- **Checkpoint:** tag `zos-4`.

### ZOS-5 Full-screen / graphics
- **Objective:** the full-screen colour ladder on z/OS: TSC colour, highlighting, GE/APL glyphs, 4x2 scaled renderer,
  partial redraw, geometry (80x24 and the alternate sizes the logmode offers), capability detection, D40 startup.
- **Allowed to change:** src/zos/PACFSIO.asm if the addressing / TPUT path forces it (sec. 9); tools c3270 scripts
  (host, port, TLS parameters only); tests/qreply_zos_*.hex (new recorded replies).
- **Frozen:** PACSCR, PACQRY, PACDISP, PACPAL, core.
- **Required capabilities:** 3270 TN3270(E) path with Read Partition Query reaching TSO; extended colour; GE.
- **Build/install:** decks G4, GS, GX, GP23 (TSD) on z/OS; promotion only after the live PASS.
- **Tests / oracles reused:** tests/test_g4.py, test_gs.py, test_gx.py (TSD streams = models, 395 scaled / 931
  streams), PACQRY cases + the new z/OS replies fed through PACQRYT (expected profile computed by tests/qry_cases.py
  before going live), D40 29 sequences.
- **Live acceptance:** probe-style capture first: the real Query Reply of the z/OS path recorded (E5-equivalent),
  then the game in COLOR(YES) HILITE(YES) and COLOR(AUTO) at 80x24 and the largest offered alternate size; PA2 reshow,
  CLEAR behaviour; c3270 trace replayed = model byte for byte (tools/c3270_trace.py family).
- **Evidence:** docs/evidence/zos5-fullscreen.md, the recorded reply hex, traces.
- **Exit criteria:** TSD decks = models; live replay = model; capability table row-by-row (CAPABILITIES.md format)
  for z/OS: CONFIRMED / NOT SUPPORTED with evidence; any degradation goes to the existing fallback chain, never to new
  code.
- **Checkpoint:** tag `zos-5`.

### ZOS-6 REALTIME
- **Objective:** PLAY(REALTIME) at T = 150 ms (NORMAL) and 125 ms (FAST) on the absolute-deadline loop; PF7/8/10/11
  arrows, PF9 pause, PA2 during play, keyboard restore per write, no catch-up after a pause.
- **Allowed to change:** src/zos/PACTSO.asm / PACFSIO.asm only if STIMER / POLL semantics differ (Z-entry).
- **Frozen:** PACRT, PACGAME (REQ-STEP), PACPLAT period logic (RT-CONV), timers in PACSCR/PACDISP.
- **Required capabilities:** TGET ASIS,NOWAIT; STIMER MICVL resolution; acceptable network jitter.
- **Tests / oracles reused:** tests/test_rt.py (12 batch + 182 TSD REALTIME streams), RP3 (1495 FAST streams),
  tools/c3270_rt_game.py and c3270_rt_trace.py for live timing.
- **Live acceptance (same measures as RT3 / RP.3 / RP.4):** host side: one write per quantum, no skipped period, no
  burst after a pause, drift < 1 ms / 100 quanta, fright / eyes / freeze durations within one quantum of 6000 / 3000
  / 1500 ms (NORMAL); client side (c3270 trace): gap median within +-10 ms of T, p95 recorded and compared with
  docs/BENCHMARKS.md; a 10-minute pause soak. A WAN-induced client-side jitter that the host does not cause is
  recorded as an environment note (Z-entry), not fixed by changing T.
- **Evidence:** docs/evidence/zos6-realtime.md.
- **Exit criteria:** decks = models; live criteria met at NORMAL and FAST; keyboard never left locked.
- **Checkpoint:** tag `zos-6`.

### ZOS-7 ARCADE
- **Objective:** the 2.0 game rules under RULES(ARCADE): power pellets, frightened ghosts, 200/400/800/1600, eyes /
  return home, fruit, levels 1-99, refill, extra life at 10000, READY!/GAME OVER, death frames, popups.
- **Allowed to change:** nothing in src/ (all ARCADE code is core / display, R2); tests and tools only.
- **Frozen:** everything in src/.
- **Tests / oracles reused:** tests/test_gp1.py, test_gp2.py (GP2 + GP23 listings), test_rp.py (6265 streams),
  search_* edge generators re-run to confirm every edge (D12) is reached on z/OS.
- **Live acceptance:** scripted scenarios tests/gp2live (A, B, C) and RP scenarios via tools/gp2_live.py, replayed by
  tools/c3270_gp2_trace.py = model byte for byte.
- **Evidence:** docs/evidence/zos7-arcade.md.
- **Exit criteria:** all ARCADE decks = models and = oracle archive; live scenarios byte-identical.
- **Checkpoint:** tag `zos-7`.

### ZOS-8 Services
- **Objective:** persistent high score, abend recovery, alarm and alarm patterns.
- **Allowed to change:** src/zos/PACHSIO.asm, PACFSIO.asm if forced; probe PACRPE rebuild; CLIST data-set guard only
  through prefix substitution.
- **Frozen:** core, display, PACDISP pattern player (S2), PACPLAT.
- **Required capabilities:** writable `<HLQ>.PACMAN.DATA`; WCC alarm reaching the user's terminal bell.
- **Tests / oracles reused:** tests/test_hs.py (21 runs, H1-H15, CLIST block), test_s1.py, test_s2.py (2986 streams,
  21 D41 edges), RP.0 ESTAE checklist (E1-E3) with the re-baselined LE abend path (sec. 11).
- **Live acceptance:** HS L1-L7 (create, read back, update, LEVEL(5) not recorded, CLASSIC silent, renamed dataset =
  UNAVAILABLE + clean READY); ESTAE E1-E3 (line mode restored, next game clean); S2 scenarios S2A-S2E with bell
  timing 2 / 3 quanta and the 3-s end pause.
- **Evidence:** docs/evidence/zos8-services.md.
- **Exit criteria:** all PASS or each gap recorded as an approved Z-entry (e.g. no audible bell on the user's z/OS
  emulator path).
- **Checkpoint:** tag `zos-8`.

### ZOS-9 Equivalence
- **Objective:** the exact regression of sec. 13 on one z/OS build, every difference investigated to a cause.
- **Allowed to change:** nothing in src/; Z-entries closed or justified.
- **Tests:** levels L1-L4 of sec. 13 in full; tools/zowe/zos_equiv.py produces the run-by-run report.
- **Live acceptance:** the G8.4 scenario (CLIST with no operand, tests/s2live/LIVEG8.txt) twice: 180/180 writes =
  model, clean QUIT -> READY.
- **Evidence:** docs/evidence/zos9-equivalence.md (counts per deck, diff register).
- **Exit criteria:** zero unexplained differences; every Z-entry approved; capability matrix z/OS column complete.
- **Checkpoint:** tag `zos-9`.

### ZOS-10 Release
- **Objective:** reproducible z/OS release from empty libraries (sec. 14).
- **Allowed to change:** README (z/OS section, authenticity rule requirements sec. 24), releases/<z/OS release>/,
  docs/zos-build.md, CURRENT_PHASE.
- **Exit criteria / checkpoint:** release check green, final live smoke on the installed release, annotated tag (name
  to be approved, sec. 17).

## 7. MVS -> z/OS mapping

### Datasets (prefix = `<HLQ>.PACMAN`, HLQ from config, never literal)
| MVS (TK4-) | z/OS | Notes |
|---|---|---|
| HERC01.PACMAN.COBOL | `<HLQ>.PACMAN.COBOL` PDS/PDSE FB 80 | uploaded by Zowe, not in-stream |
| HERC01.PACMAN.COPY | `<HLQ>.PACMAN.COPY` FB 80 | SYSLIB of IGYCRCTL |
| (in-stream asm) | `<HLQ>.PACMAN.ASM` FB 80 | SYSIN of ASMA90 |
| HERC01.PACMAN.LOAD (PDS load modules) | `<HLQ>.PACMAN.LOAD` **PDSE** (program objects) | required by Enterprise COBOL >= 5 |
| (none) | `<HLQ>.PACMAN.OBJ` FB 80 | object decks between compile and bind |
| HERC01.PACMAN.CLIST | `<HLQ>.PACMAN.CLIST` FB 80 | prefix substituted at generation |
| HERC01.PACMAN.DATA(HISCORE) | `<HLQ>.PACMAN.DATA(HISCORE)` **PDS** FB 80/80 | see sec. 10 |
| HERC01.PACMAN.R20.* (build of record) | `<HLQ>.PACMAN.RZ.*` | clean-rebuild prefix (sec. 14) |
| - | `<HLQ>.PACMAN.PRV.*` | rollback copies |

### Toolchain
| Step | MVS 3.8J (TK4-) | z/OS |
|---|---|---|
| source transfer | IEBGENER in-stream through the 3505 reader | `zowe files upload` per member, explicit encoding, binary verify |
| COBOL | IKFCBL00 `LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K` | IGYCRCTL, options fixed in ZOS-1 (start: `NODYNAM,TRUNC(STD),NUMPROC(NOPFD),ARITH(COMPAT)`, RMODE/DATA from the profile probe) |
| assembler | IFOX00 `OBJECT,NODECK,NOXREF` | ASMA90 with SYS1.MACLIB + SYS1.MODGEN |
| link | IEWL `LIST,XREF` + SYS1.COBLIB | binder IEWBLINK, SYSLIB SCEELKED, AMODE/RMODE per profile, entry PACMAIN |
| runtime | SYS1.COBLIB (static) | Language Environment (SCEERUN in LNKLST or STEPLIB) |
| TSO batch | IKJEFT01 | IKJEFT01 |
| copy / promote | IEBCOPY | IEBCOPY (PDSE program objects: COPYGRP / COPYMOD as required) |
| identity | AMASPZAP dumps | AMBLIST LISTLOAD + binder map, or IEBCOPY unload hash |
| submit / wait / listing | tools/submit.sh + run_deck.py + JES printer file | tools/zowe/submit (zowe jobs submit --wait-for-output, download spool) |
| listing parse | TK4- step summary lines (`job step pgm RC= nnnn`) | tools/zowe/zos_listing.py normalises IEF142I / IEF272I and spool DDs into the shape the tests already parse; IKFnnnnI checks mapped to IGYnnnnn-W/E/S |

### Decks
`make_deck.py --target zos` generates the same deck set (REL20, S2, RP, GP2, GP23, HS, RT, GS, GX, G4, RELEASE, ALLOC,
DATA, CLIST, INST) with z/OS steps; the MVS generation is unchanged (R3). Rules of the MVS decks that remain: column
72 on EXEC/DD continuation, prefix-derived names, `COND=(0,NE)` chaining, run-only mode, JCL audit (g8_jcl_audit.py
gets a z/OS rule set: no HERC01, no TK4- library, only `<HLQ>.PACMAN.*` written).

## 8. COBOL dialect migration risks (IKFCBL00 1972 -> Enterprise COBOL)
Inventory of the 2.0 sources (non-comment code): no EXAMINE, TRANSFORM, NOTE, REMARKS, READY TRACE, EXHIBIT, ALTER,
CURRENT-DATE, TIME-OF-DAY, COMP-3, STRING/UNSTRING/INSPECT, SEARCH, GO TO DEPENDING; 24 binary `COMP` items; 53 OCCURS;
`STOP RUN` 4, `GOBACK` 9; one `UPON CONSOLE` (PACHELLO only).

| Risk | Where | Detection | Mitigation |
|---|---|---|---|
| `ASSIGN TO UT-S-SYSIN` form | PACINPT, PACQRYT | ZOS-1/2 compile + batch read | Enterprise COBOL accepts the `class-S-ddname` form; if not, z/OS override is NOT allowed for PACINPT without a Z-entry -> prefer a compile option or JCL DD of the derived name |
| `LABEL RECORDS ARE OMITTED` (obsolete) | PACINPT, PACQRYT | IGY informational/warning | accepted as documented warning (sec. 6 ZOS-2 exit) |
| Binary truncation (`PIC S9(4) COMP` lengths, `PIC 9(4) COMP` HEXN byte tricks) | PACPLAT, PACDISP, PACINPT, PACQRY, PACSCR, PACDS, PACREQ | TSD stream equality, HEX dumps | TRUNC(STD) = IKFCBL00 truncation semantics; never TRUNC(BIN) unless proven equal |
| Uninitialised WORKING-STORAGE (PACSTATE has no VALUE clauses) | all | STORAGE(00) vs STORAGE(FF) runs identical | if they differ: real latent defect -> MVS-side fix on main (sec. 2) |
| New reserved words in Enterprise COBOL used as data names | all | compile (IGY-S) + a local scan tool against the Enterprise COBOL reserved list in ZOS-0 | if hit: blocks R1 -> decision (rename = shared-source change on main) |
| Sign / NUMPROC differences on zoned fields | counters, score | oracle equality | NUMPROC(NOPFD) |
| DISPLAY record format (SYSOUT LRECL / carriage control) and line split > 120 | PACDISP, PACPLAT TSD lines | right-stripped line compare with oracle | DCB on the SYSOUT DD in z/OS decks; never change DISPLAY statements |
| LE PARM parsing (`/` separates runtime options) | PACMAIN | ZOS-1 PARM echo, empty-PARM run | PARM never contains `/` (CLIST builds letters/digits only); test kept |
| RETURN-CODE propagation, STOP RUN vs GOBACK under LE | PACPLAT, PACMAIN | step RC in listings | expected identical; checked by every deck |
| Static CALL / NODYNAM | all CALLs | binder map | NODYNAM, one module, same as MVS |
| Compiler diagnostics differ (IKF -> IGY) | tests | listing adapter | tests check "no W/E/S" through a mapped pattern; informational allowed list in docs/zos-build.md |

## 9. Assembler / platform-service risks
| # | Risk | Modules | Detection | Mitigation |
|---|---|---|---|---|
| 1 | Addressing mode: Enterprise COBOL passes 31-bit addresses; TPUT/TGET register forms carry option flags in the high byte of R1 (24-bit buffers) | PACFSIO, PACTSO | ZOS-1 profile probe, ZOS-3 service probe | profile A: whole module AMODE 24 / RMODE 24, COBOL RMODE(24) DATA(24) (no source change); profile B: AMODE 31 with a z/OS PACFSIO that copies buffers below the line (override + Z-entry). Prefer A if it binds and runs |
| 2 | ASCB/TSB test (`ASCBTSB` at X'3C') to detect TSO | PACTSO, PACFSIO | batch RC 4 + TSO RC 0 | offsets are architected; verify by IHAASCB mapping in ZOS-3 |
| 3 | STFSMODE / STTMPMD / STLINENO / TCLEARQ: TK4- has STFSMODE via usermod ZP60009 | PACFSIO, PACTSO | assemble (MNOTEs) + ZOS-3 | standard TSO/E macros on z/OS; expansions may differ, contract tested |
| 4 | ESTAE inside an LE enclave (LE TRAP(ON) has its own ESPIE/ESTAE) | PACFSIO, PACHSIO | ZOS-3 HS full-directory guard, ZOS-8 E1-E3 | sec. 11 |
| 5 | BPAM/QSAM tricks: OPEN TYPE=J with JFCNWRIT, BLDL/FIND, QSAM UPDAT, STOW at CLOSE; PDSE semantics differ (no directory blocks, no B14 on a full directory) | PACHSIO | HS H1-H15 | DATA stays a PDS (sec. 10); if SMS forces PDSE, the full-directory case becomes a Z-entry with a substitute failure test |
| 6 | STIMER MICVL / BINTVL, STCK (TOD), clock wrap of "ms since first TIME call" | PACTSO | PACTSOT | unchanged contract; real hardware clock is finer than Hercules |
| 7 | HLASM stricter than IFOX00 (literal pools, USING warnings) | all asm | ASMA90 RC | warnings fixed only via z/OS override if they matter; otherwise documented |
| 8 | Save-area / linkage conventions with LE caller | all asm | every CALL | standard 72-byte save area chaining, non-LE leaf routines; unchanged |

## 10. High-score persistence mapping (D38)
- `HERC01.PACMAN.DATA(HISCORE)` -> `<HLQ>.PACMAN.DATA(HISCORE)`, DSORG PO, **DSNTYPE PDS** (not PDSE), RECFM FB,
  LRECL 80, BLKSIZE 80 (PACHSIO checks LRECL 80 / BLKSIZE 80 / RECFM F before any I/O).
- Record format unchanged: `0001430 PACHS001 001` (score 7 digits, tag, version). Only games started at LEVEL(1)
  under ARCADE are eligible; CLASSIC never reads or writes.
- The z/OS high score starts empty (self-heals on the first eligible save, D38 D4); the MVS value is not migrated
  (proposed; see sec. 17).
- CLIST guard unchanged: `&SYSDSN('<prefix>.DATA') = OK` else `ALLOC F(PACHS) DUMMY`.
- Failure semantics unchanged: missing dataset / member / garbage = 0 + UNAVAILABLE or self-heal, NOT SAVED only for
  a failed attempted write; no abend reaches the player.
- Test isolation: batch HS decks use their own test members and `<HLQ>.PACMAN.HSFULL`; the installed DATA is never
  written by a deck (as on MVS).

## 11. Recovery / ESTAE strategy
- Keep the 2.0 design: PACFSIO FSON establishes ESTAE (restore line mode: STTMPMD/STFSMODE OFF, STLINENO 1, then
  percolate); PACHSIO guards its I/O with ESTAE and deletes it before every return.
- LE interaction to establish in ZOS-3/ZOS-8 (decision recorded as a D-number): with the default TRAP(ON), a program
  check (S0C7 from PACRPE) is first handled by LE (CEE3207S), which then ends the enclave with an abend (U4038 /
  ABEND(ON) setting); the PACFSIO ESTAE must still get control on that abend and restore line mode. LE messages
  (MSGFILE, CEEDUMP) may be written to the terminal while it is still in full-screen mode: this is the D40 situation;
  the expected path is "line mode restored, next game starts clean" (E2), not a particular message text.
- Runtime options are fixed per deck/CLIST (CEEOPTS DD or the site default), never in the PARM.
- Tests: E1 (normal game), E2 (forced abend in the test build PACRPE, then a clean game), E3 (control) live in ZOS-8;
  batch: HS full-directory / I/O failure guard returns RC 16 without abend.

## 12. Capability-query strategy
- Unchanged code path: COLOR(AUTO) -> PACFSIO QRY (Read Partition Query via TPUT NOEDIT WSF) -> TGET ASIS -> PACQRY
  validity + bounded selection (D40) -> profile (colour, highlight, GE/APL, alternate size) -> AUTO chain of D43.
- New inputs, not new code: the reply of every z/OS emulator / logmode used is captured once (ZOS-5 probe capture),
  stored as tests/qreply_zos_<name>.hex and run through PACQRYT in batch; the expected profile is computed by
  tests/qry_cases.py; only after it matches is the live game run.
- Watch points: TN3270E server or VTAM doing its own query; logmode not query-capable (fixed model 2 -> 80x24, which
  2.0 already handles); D28 (held output after the query) may disappear or change; `***` before the switch (D40).
- If the z/OS path gives no valid reply: the existing fallback (monochrome line mode, TURN) is the documented result;
  COLOR(YES) HILITE(YES) remains the explicit override, exactly as on TK4-.

## 13. Regression strategy against 2.0-mvs-max
Levels, all required for ZOS-9 and the subset listed per phase earlier:
- **L0 Source identity:** shared sources = `2.0-mvs-max` (git diff empty, SHA-256 per file); overrides listed with
  their Z-entries; uploaded members = local bytes (binary download compare).
- **L1 Build:** every deck step RC 0000; compiler/assembler/binder messages within the allowed list.
- **L2 Models:** every run's SYSOUT / TSD stream = the independent Python models (ref_*.py), using the existing tests
  unchanged on the normalised z/OS listing: test_mvs2-8, test_map, test_core_frozen, test_g4, test_gs, test_gx,
  test_rt, test_s1, test_gp1, test_gp2, test_hs, test_rp, test_s2, test_g8 (with PACMAN_LATER_PHASE / PACMAN_PREFIX as
  at 2.0).
- **L3 Oracle:** every run's SYSOUT on z/OS = the archived 2.0 MVS SYSOUT of the same run (tests/oracle20), compared
  per step, right-stripped lines (D11), after removing only listing chrome (job headers, job numbers, dates, system
  messages). Inventory: REL20 60 steps; S2 25 TSD runs = 2986 streams + 4 line-mode; RP 60 TSD runs = 6265 streams,
  RP3 12 TSD runs = 1495 streams + 9 BAT, D40 29 sequences; GP2 / GP23 decks; HS 21 runs; 1.0 oracle.
- **L4 Live:** c3270 traces of the scripted scenarios (G8, GP2 A-C, S2A-S2E, RT) replayed = model byte for byte;
  timing figures compared with docs/BENCHMARKS.md.
- **Difference policy:** any L0-L4 difference is a defect until explained. Explained differences are Z-entries in
  docs/ZOS-DIFFS.md (cause, evidence, user approval, test that pins it). A difference in the core is never accepted as
  "platform" without proof.

## 14. Final clean-rebuild / release procedure (ZOS-10)
1. Local: `tools/release_check.sh zos` (new mode): validate_source, all local tests, R3 MVS deck identity, z/OS JCL
   audit.
2. Allocate empty `<HLQ>.PACMAN.RZ.*` (check first that none exists, as G8.3 JOB 305).
3. Upload the tagged sources into RZ (binary identity check), build of record REL20 `--target zos` into
   `RZ.LOAD(PACMAIN)`; run-only S2 / RP / GP2 / GP23 / HS on that member; L1-L3 on every listing.
4. Promotion: IEBCOPY RZ -> `<HLQ>.PACMAN.LOAD(PACMAIN)` (no compile/link), identity by AMBLIST/binder map hash;
   installed checks (1.0 oracle, S2 = model and = RZ output); CLIST install; rollback copy kept in PRV.
5. Minimal installed live smoke: CLIST with no operand, scenario G8 twice, clean QUIT -> READY, HISCORE untouched.
6. Release material: releases/<z/OS release>/ (RELEASE-NOTES, MANIFEST with source SHA-256 = 2.0 + overrides,
   DEFAULTS, CAPABILITIES z/OS column, BENCHMARKS, decks of record, SHA256SUMS, screenshots), README z/OS section
   (what runs on z/OS vs the client, requirements sec. 24), docs/zos-build.md.
7. Annotated tag on the release commit; post-tag read-only identity job (as JOB 318). The MVS release stays
   independent (requirements sec. 13 ZOS-7, sec. 23).

## 15. Relation to requirements v4 sec. 12-13
| Requirements ZOS step | Covered by |
|---|---|
| sec. 12 freeze MVS release, inventories, datasets, text sources via Zowe, recompile first | done (2.0-mvs-max) + ZOS-0, ZOS-1, sec. 8 |
| ZOS-0 connectivity | ZOS-0 |
| ZOS-1 datasets | ZOS-1 |
| ZOS-2 transfer (encoding, no truncation) | ZOS-1 (binary identity) |
| ZOS-3 compilation | ZOS-1 (hello) + ZOS-2 (full build) |
| ZOS-4 functional run, turns first, fix only PLATFORM/INPUT/DISPLAY | ZOS-2, ZOS-4 (+ R1/R2) |
| ZOS-5 z/OS interface | ZOS-5, ZOS-6 |
| ZOS-6 Zowe automation | ZOS-1 (built first, used by every phase) |
| ZOS-7 release | ZOS-9, ZOS-10 |
Requirements sec. 24 ("repeat the same capability ladder on z/OS") is covered by ZOS-5..ZOS-8.

## 16. Target environment (declared by the user, 2026-10-14; verified in ZOS-0)
- IBM Z Xplore: hosted, **shared, non-production** z/OS training system. Userid / HLQ `Z00000`; project prefix
  `Z00000.PACMAN`. Host 198.51.100.200.
- Zowe profiles (local config, credentials in the Zowe secure store, never in git): `zosmf` (z/OSMF, port 10443, TLS
  certificate validation disabled locally: `rejectUnauthorized: false`), `tso` (account FB3, logon proc IZUFPROC,
  codepage 1047), `ssh` (22), `rse` (HTTPS 6800, `rseapi`), `zftp` (21, secure FTP). `cicsZXP` exists but CICS is
  outside this plan and is not used.
- Interactive 3270 / TSO: 198.51.100.200:623 (c3270 options, TLS and logmode established in ZOS-0).
- Site rules (binding, added to R7): only `Z00000.*` datasets (the project uses only `Z00000.PACMAN.*`); no disruptive
  or high-volume workload; no third-party software installed on z/OS; no service exposed externally; no effect on other
  users.
- Consequences for the plan:
  - Volume: the 2.0 regression decks are large (GP2 listing 4.9 MB, RP 3.4 MB, S2 2986 streams). On Z Xplore decks are
    submitted strictly one at a time, never in parallel, and large decks may be split into run-only parts; the full set
    runs only at ZOS-9 and ZOS-10. Spool output is downloaded and then left to the system's retention unless the user
    authorises purging the project's own jobs.
  - Clean rebuild (ZOS-10) uses a new prefix (`Z00000.PACMAN.RZ`) instead of deleting libraries; any dataset deletion is
    done only with the user's explicit approval.
  - Codepage: the TSO profile says 1047; the MVS oracle bytes come from the Hercules reader table (CP037-like). `[`,
    `]`, `^` differ between CP037 and CP1047. The upload encoding is chosen in ZOS-1 so that the uploaded bytes equal
    the MVS bytes (proved by binary download), whatever the TSO profile codepage is.
  - REALTIME runs over the internet, not localhost: client-side jitter is expected and handled as in ZOS-6 (host-side
    criteria binding, client-side figures recorded).
  - Logon proc IZUFPROC normally starts ISPF: ZOS-4 checks that TSO READY is reachable (ISPF exit or option 6).

## 17. Decisions (approved by the user 2026-10-14, recorded as D44)
1. Target system: IBM Z Xplore (sec. 16), TN3270 available.
2. Release name `2.0-ZOS`, final tag `2.0-zos`. Supersedes only the `1.0-zOS` release name of requirements v4 sec. 13
   (ZOS-7); every other requirement stands.
3. Prefix `Z00000.PACMAN`; whether DATA may be a PDS (SMS) is checked in ZOS-0.
4. The z/OS high score starts clean / empty; the MVS value is not imported.
5. AMODE 24 is a compatibility preference, not a requirement: adopted only if the z/OS compiler / binder / runtime
   run the complete program correctly without source changes. If AMODE 24 is not viable, stop and report before
   adopting AMODE 31 or changing any source.
6. Branch `zos` in the worktree `~/Documents/Worktrees/Pacman-zOS` (sec. 2).
7. Job output is left to the site's normal retention; jobs are never purged automatically.
8. ZOS-0 is discovery-only: read-only queries wherever possible, no source upload, no Pac-Man dataset, no installs, no
   CICS, nothing outside `Z00000.*`, no deletions. The single IEFBR14 job is shown in full (dataset name, DISP,
   SPACE/DCB) and authorised by the user before it is submitted.
