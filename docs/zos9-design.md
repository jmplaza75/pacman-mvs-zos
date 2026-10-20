# ZOS-9 Final equivalence - design (Z9-A, Z9-B, Z9-C) - APPROVED 2026-10-20; Z9-D prepared locally

Status: discovery / design APPROVED by the user (2026-10-20) with decisions DEC-1..DEC-4 (section 0). Z9-D local
preparation done (section 11): decks PACZ9E1 / PACZ9E2, checker tools/zowe/zos9_equiv.py, tests/test_zos9.py. Host
execution NOT yet authorised: waiting for the final pre-host review. Nothing was run on z/OS: no c3270, no upload, no
job, no dataset access, no build, no source change, no commit / tag / push.

## 0. Decisions (user, 2026-10-20)
- **DEC-1 APPROVED - full battery superseded.** OLD (plan sec. 6 ZOS-9, sec. 13 "levels L1-L4 in full", the "full
  battery -> ZOS-9/10" deferrals): run the full batteries. FINAL: every in-scope requirement and relevant path must be
  CLOSED in the equivalence matrix; any behaviour not already closed by accepted evidence receives focused direct or
  composed proof. The equivalence matrix, not the number of rerun cases, is the coverage authority. Not a reduction of
  acceptance quality: the batteries' output is enormous, five single runs exceed the site limit, most behaviours already
  have accepted z/OS evidence, and repeating them would add redundant evidence, not close a gap.
- **DEC-2 - PRESENT release policy FROZEN (implementation = ZOS-10).** For the final z/OS release, REALTIME launched
  through the installed PACMAN CLIST defaults to PRESENT(COALESCED); PRESENT(EVERY) stays an explicitly selectable
  legacy / compatibility mode. Program level unchanged: a PARM without column 26 keeps meaning EVERY (byte-stable 2.0
  PARM); the user-facing CLIST selects COALESCED unless PRESENT(EVERY) is requested. No CLIST change in ZOS-9.
  ZOS-9 equivalence: NOT a remaining gap. ZOS-10 release configuration: REQUIRED action, verifying at least: the
  ordinary / default REALTIME invocation selects COALESCED; explicit PRESENT(EVERY) remains selectable; TURN behaviour
  unchanged; the invocation obeys the CLIST / PARM size and compatibility constraints; the installed release smoke uses
  the final default path.
- **TSO line mode on the post-ZOS-6 build: VALID BY NON-INTERFERENCE** (section 2): the ZOS-6 behavioural change is
  gated by PRESENT(COALESCED) (column 26 = C), which line mode never sets; the added PACREQ fields are append-only and
  set before use; post-ZOS-6 TURN / batch / live runs (E1, E2, Z1, E3, B1, GD, S8C, L1, HL*, SF) show the rebuilt
  program oracle-compatible outside the coalesced path. No ZOS-9 rerun. Carried to ZOS-10: after the clean final
  rebuild, the installed-release checks exercise the required line-mode / 1.0-oracle path.
- **DEC-3 APPROVED - option A.** PACZ9E1 and PACZ9E2 (frozen content, section 7.3 / 11) are the only approved ZOS-9 host
  executions; not to be replaced by composition.
- **HA6: CLOSED BY COMPOSED EVIDENCE** (section 7.4; not "skipped"; no LINES=, no output dataset, no split).
- **DEC-4 - METRICS(YES): APPROVED OUT OF SCOPE - DIAGNOSTIC / NO FROZEN 2.0 EQUIVALENCE ORACLE.** Not PASS, not proven
  on z/OS. Controlling-source check: requirements v4 MVS-G0 / MVS-G3 ask to *measure* screen updates per turn / tick
  and traffic / flicker (phase activities, met on MVS by the G0 metrics and docs/BENCHMARKS.md); D23 makes the METRICS
  line explicitly optional; no requirement makes METRICS(YES) mandatory release behaviour and no 2.0 oracle run uses it
  (no PARM column 11 = M in any releases/2.0-MVS-MAX deck). No oracle is invented.
- **Capability column: documentation-only gap**, closed in the ZOS-9 documentation from accepted evidence only (each
  entry -> evidence or an accepted platform decision; nothing inferred; no host test).
- **Errata**: the three documentation errata of section 6 are corrected during ZOS-9 (at its closure, with the
  evidence report), recorded as post-closure documentation errata; historical outcomes not rewritten; the zos-8
  commit / tag not amended.
- **Production DATA**: `Z00000.PACMAN.DATA(HISCORE)` = `0000980 PACHS001 001`; PACZ9E1 / PACZ9E2 never reference it;
  Stage F never rerun; no ZOS-9 test resets DATA.
- **No other host execution** is approved (no ZOS-5..8 live rerun, Stage F, HA6, CLIST no-operand live, TSO line-mode
  rerun, full batteries). A newly discovered genuine gap is brought back for approval.
Baseline verified locally: branch `zos`, HEAD = tag `zos-8` = 32d99f21e2fa0d3f6dcda31c28212736a52a8109 (annotated),
`zos-7` = 75b3fd5, `2.0-mvs-max` = 94fd6f6, working tree clean, no remote.
Carried production state: `Z00000.PACMAN.DATA(HISCORE)` = one FB 80 record `0000980 PACHS001 001` (legitimate; never
deleted / reset / overwritten for test convenience).

Method: requirement -> MVS reference -> accepted z/OS evidence -> validity -> genuine gaps -> minimum executions.
Local analysis only: the frozen oracles (tests/oracle20), the frozen models (tests/ref_*.py, tests/search_*.py) replayed
on the cards that were actually executed on z/OS, `git diff` between the tags, and the documents listed in section 1.
Scratch analysis scripts lived in the session scratchpad (not in git); no repository tool was added or changed.

---------------------------------------------------------------------------------------------------------------------

## 1. Z9-A - Authoritative inputs (inventory)
| # | Input | Role in ZOS-9 |
|---|---|---|
| I1 | docs/requirements/PACMAN_MVS_ZOS_REQUISITOS_DESARROLLO_v4.docx (sec. 2-5, 7, 8, 11-15, 17, 18, 22-29) | primary requirements (RQ-*) |
| I2 | docs/ZOS-MIGRATION-PLAN.md (R0-R8, sec. 5-17) | z/OS acceptance criteria (PL-*); reconciled in section 8 |
| I3 | docs/DECISIONS.md D1-D43 (MVS), D44, D45, ZV-D33, ZOS-7 D1-D5, ZOS-8 U1-U12 | approved behaviour and variances |
| I4 | docs/ZOS-DIFFS.md Z1-Z5, C1-C3 | product differences of record |
| I5 | docs/ARCHITECTURE.md, CLAUDE.md (D9-D18 permanent rules) | layer / determinism / fallback rules |
| I6 | tests/oracle20 (JOBs 307-312, 315, 316; SHA256SUMS) + releases/2.0-MVS-MAX/decks | frozen MVS oracle (never modified) |
| I7 | tests/ref_*.py models, tests/search_*.py (D12 edge predicates), tests/*cases | independent models, edge definitions |
| I8 | docs/evidence/zos0-discovery.md, zos1-toolchain.md, zos2-portable-core.md (+ zos2-*check.txt, zos2-spool), zos3-platform-layer.md, zos3-coverage-summary.md (+ zos3-*check.txt, zos3-spool), zos4-classic.md, zos4-live.md, zos5-fullscreen.md, zos6-realtime.md, zos7-arcade.md, zos8-services.md | accepted z/OS evidence |
| I9 | docs/zos3..zos8 design / review documents, docs/zos6-production-design.md, zos6-io-architecture-memo.md | decisions and deferrals in context |
| I10 | docs/CURRENT_PHASE.md (ZOS-0..8 entries) | phase history and carried items |

## 2. Z9-A - Production-change timeline (2.0-mvs-max -> zos-8)
`git diff --stat <prev> <tag> -- src`, classified (A COBOL / copybook, B assembler, C installed CLIST, D tooling /
tests,
E docs, F production dataset state). D and E changed in every phase and are not listed per phase.
| Milestone | A COBOL / copy | B asm | C CLIST | F state | Load module under test afterwards |
|---|---|---|---|---|---|
| zos-0 | - | - | - | none | - |
| zos-1 | - (probes ZHELLOA/C only) | - | - | datasets allocated | probes |
| zos-2 | **Z1**: 28 `COPY` statements in 9 modules (syntax only; record layouts = 2.0) | - | - | - | LOAD(PACZ2D) JOB08888 |
| zos-3 | - | - | - | HS test PDSs T1 | PACZ2D |
| zos-4 | - | - | **Z2 + Z3** (src/zos/PACMAN.clist, installed) | CEEOPTS; PACMAIN := PACZ2D | PACMAIN = PACZ2D |
| zos-5 | - | - | - | - | PACZ2D |
| zos-6 | **Z4**: PACREQ (+2 fields appended), PACMAIN, PACPLAT, PACDISP, PACSCR | - (probe PACZ6P only) | **Z5** PRESENT keyword (installed) | PACMAIN := PACZ6D (JOB09460 / JOB09499) | PACMAIN = PACZ6D |
| zos-7 | - | - | - | - | PACZ6D |
| zos-8 | - (probe CLIST RPESTAE only) | - | - | **DATA(HISCORE) = 0000980** (Stage F); test datasets | PACZ6D |

**zos-7 -> zos-8 production delta (exact):** `git diff zos-7 zos-8 -- src` = one new file src/probe/zos/RPESTAE.clist
(test CLIST, not production). No COBOL, copybook, assembler, PACFSIO, PACHSIO or src/zos/PACMAN.clist change; no build,
no promotion. Production delta = state only (F): DATA(HISCORE) created. **Conclusion: ZOS-8 invalidates no earlier
gameplay, REALTIME, ARCADE or full-screen evidence.**

**The one real cross-build boundary is zos-6 (Z4), not zos-8.** ZOS-2..5 evidence ran on PACZ2D; the installed product
is the ZOS-6 program (PACZ6D = PACMAIN). Analysis of Z4 (the exact hunks of `git diff zos-5 zos-6`):
- requirement concerned: every ZOS-2..5 equivalence claim made on PACZ2D (CLASSIC / ARCADE batch, TSD alarm, HS batch,
  line-mode TSO, full-screen TURN);
- production dependency: PACMAIN, PACPLAT, PACDISP, PACSCR were recompiled; PACREQ grew by 2 trailing bytes;
- later change: Z4 adds (1) three statements at PARM decode (REQ-PMODE / REQ-PRES), (2) in RT-QUANTUM a PSLT call
  that returns `Y` unless REQ-PMODE = C and mode TSC / TSD, and RT-FRAME is cleared on `Y` exactly as before,
  (3) a PACDISP branch, PACSCR op RTQS and RT-POST-READ reachable only with REQ-PRES = N / REQ-PMODE = C;
- why it does NOT invalidate: on every path without PARM column 26 = C (all batch, all TURN, all line mode, all
  PRESENT(EVERY)) the new code is either not reached or returns the pre-Z4 value; the PACREQ fields are appended (no
  offset moves) and set before use. Post-Z4 anchors on the new binary: PACZ6DR1 E1 (EVERY batch = oracle 310 RTB7),
  E2 (EVERY TSD = oracle 310 RTT2), Z1 (FAST batch), PACZ7DR1 E3 (ARCADE EVERY TSD = oracle 311 G3R7), PACZ8HB B1
  (BAT ARCADE TURN + PACHSIO), live CLASSIC / ARCADE TURN full screen (GD, S8C, L1, HL*, SF).
- verdict: ZOS-2..5 evidence **VALID (cross-build, Z4 path-neutral)**. Residual: the line-mode TSO path has not been
  executed on the post-Z4 binary (LOW; the release binary of ZOS-10 is a new build anyway and its installed checks
  re-run the 1.0 oracle, plan sec. 14 step 4).

## 3. Z9-A - Validity of every accepted evidence item
| Evidence | Binary | Status | Reason |
|---|---|---|---|
| ZOS-0 discovery, oracle freeze | - | VALID | environment facts; oracle SHA256SUMS unchanged |
| ZOS-1 toolchain, upload identity, profile A/B probes, SYSOUT FBA 121 | probes | VALID | no toolchain change since |
| ZOS-2 C1-C7 CLASSIC 25 runs = oracle 307 | PACZ2D | VALID (cross-build) | Z4 inert on BAT / TSO TURN |
| ZOS-2 G1-G3 ARCADE BAT / TSO = oracle 310 | PACZ2D | VALID (cross-build) | idem; post-Z4 anchor B1, E3 |
| ZOS-2 G2 REALTIME BAT, RP3 FAST BAT, ST0 / STF, DRV (QRY1, TSOT1) | PACZ2D | VALID (cross-build) | Z4: PSLT `Y` in BAT; anchors E1 / Z1 |
| ZOS-3 PACZ3FS, HA, HS1..8 (18/19 HS runs), TD1..4 (12 S2T, 21 D41 edges) | PACZ2D | VALID (cross-build) | TSD TURN/RT without column 26; anchor E2, E3 |
| ZOS-4 Z2 / Z3 CLIST, PACZ4INS, live line mode (attestation) | PACZ2D | VALID; line mode OBSERVATIONAL | CLIST Z2 / Z3 lines unchanged by Z5 (z5_strip guard) |
| ZOS-5 live A / B / C full screen, Query Reply | PACZ2D | VALID (cross-build) | TURN, no column 26 |
| ZOS-6 build, dry runs, R1-T4 / R2 | PACZ6D / PACMAIN | VALID | current binary |
| ZOS-7 dry runs, L1 / L2 / L3 | PACZ6D / PACMAIN | VALID | current binary; frozen checkers |
| ZOS-8 B1, B2, HL1-HL8, E1-E3, S1-S3, SF | PACZ6D / PACMAIN | VALID | current binary; S1 / HL8 by the approved corrected checkers |
No item is INVALIDATED or PARTIALLY INVALIDATED. Tooling corrections (zos_equiv anchoring, IEC217I form, HL8 model,
SOUND C3 / C7 context, F1 C3, 120-column wrap, segment join) changed checkers only and never the product or an oracle.

---------------------------------------------------------------------------------------------------------------------

## 4. Z9-B - Requirement-by-requirement equivalence matrix
Equivalence classes: EX exact (oracle bytes after the approved normalisation), SEM semantic, MB model / batch,
LV live terminal, OBS observational. Status: CLOSED EXACT / SEMANTIC / MODEL-BATCH / LIVE / OBSERVATIONAL /
PLATFORM-SPECIFIC, GAP, DECISION (closure needs an explicit user decision, no execution), OUT (approved out of scope).
"Bin" = binary of the evidence: 2D = PACZ2D, 6D = PACZ6D / installed PACMAIN. Evidence ids: C1-C7, G1-G3, RP, ST, DRV
(ZOS-2 jobs), FS, HA, HS1-8, TD1-4 (ZOS-3), Z2/Z3/INS/L4 (ZOS-4), A/B/C (ZOS-5), DR1/DR2/R1/R2 (ZOS-6), 7DR1/7DR2/L1-L3
(ZOS-7), B1/B2/HL*/E1-E3/S1-S3/SF (ZOS-8).

### 4.1 Architecture, build, platform
| ID | Requirement (source) | MVS ref | Class | z/OS evidence (bin) | Valid | Approved diff | Residual | Status | Action |
|---|---|---|---|---|---|---|---|---|---|
| A1 | Core GAME/MAP/AI terminal-independent, never forked (RQ 3, 18; PL R2; D18) | 2.0 src | EX | test_core_frozen + zos_c2 guards; core = 2.0 except Z1 syntax | yes | Z1 | none | CLOSED EXACT | - |
| A2 | Shared source, platform-only deltas registered (RQ 12, 23; PL R1, R0) | 2.0 src | EX | Z1-Z5 guarded hunks (tests/zos_c2.py, zos_z4.json); R3 gate | yes | Z1-Z5 | register incomplete for checker-level diffs (see 6) | CLOSED EXACT | doc: section 6 list into the ZOS-9 report |
| A3 | MVS stays reproducible (PL R3) | SHA256SUMS | EX | r3_gate PASS at every phase close | yes | - | - | CLOSED EXACT | - |
| A4 | Recompile on z/OS, build reproducible by JCL (RQ 4, 12, 13 ZOS-3) | REL20 | MB | PACZ2BLD JOB08888, PACZ6BLD JOB09460 RC 0 (C3 only) | yes | - | clean rebuild = ZOS-10 | CLOSED MODEL-BATCH | ZOS-10 |
| A5 | Profile A: AMODE 24 / RMODE 24 / RENT, LE ALL31(OFF) STACK BELOW (D45, PL 9) | - | PS | J3; PACZ2D / PACZ6D attributes; CEEOPTS (Z2); every run | yes | Z2 | - | CLOSED PLATFORM-SPECIFIC | - |
| A6 | No dependence on uninitialised storage (PL ZOS-2) | - | EX | ST0 / STF identical (2D) | yes | - | new Z4 fields have VALUE / are set before use | CLOSED EXACT | - |
| A7 | Dialect / compiler diagnostics within the allowed list (PL 8) | IKF clean | MB | all IGY RC 0; C3 ASMA303W only | yes | C3 closed (ZOS-8) | ZOS-DIFFS C3 text stale | CLOSED MODEL-BATCH | doc |
| A8 | Text sources via Zowe, encoding, no truncation (RQ 12, 13 ZOS-2, 15) | local bytes | EX | ZOS-1 23/23, Z1 9/9, Z4 uploads byte-verified | yes | - | - | CLOSED EXACT | - |
| A9 | Zowe automation edit -> upload -> build -> spool (RQ 13 ZOS-6, 15) | - | MB | tools/zowe (upload, submit, spool, translator) used every phase | yes | - | - | CLOSED MODEL-BATCH | - |
| A10 | HLQ parameterised, only <HLQ>.PACMAN.*, no secrets (RQ 14, 15, 17; PL R7) | - | PS | JCL audits, @@HLQ@@ decks, secret audits per phase | yes | - | - | CLOSED PLATFORM-SPECIFIC | - |
| A11 | PACHELLO console hello (PL ZOS-1) | MVS-0 | - | compile + bind only (UPON CONSOLE not run) | yes | - | not a game requirement | OUT (ZOS-1 closure) | - |

### 4.2 Game rules (CLASSIC = 1.0-MVS, ARCADE = 2.0)
| ID | Requirement (source) | MVS ref | Class | z/OS evidence (bin) | Valid | Approved diff | Residual | Status | Action |
|---|---|---|---|---|---|---|---|---|---|
| G1 | CLASSIC game = 1.0-MVS (RQ 2, 7, 11 test list; D11 edge) | 307 RUN1-19, TSO1-6 | EX | C1-C7 25/25 identical (2D) | yes | - | - | CLOSED EXACT | - |
| G2 | AI levels deterministic, seed 12345, tie U D L R, AI0-3 (RQ 8; D9, D10, D14) | 307, 310 | EX | C1-C7, G1 (GPTIE), ST0/STF | yes | - | - | CLOSED EXACT | - |
| G3 | Ghost never enters a wall; collisions; lives; WON / LOST / QUIT (RQ 11) | 307 | EX | C1-C7 (EDGE1-3, LOST0/1, WIN0, DIE1) | yes | - | - | CLOSED EXACT | - |
| G4 | Power pellets, fright, eyes / revival, 200-1600 chain (D36) | 310 GP1 | EX | G1 (GPAI0, GPHOME, GPPOW2, GPTIE), G2 (RTGPA), 7DR (N9/F9), L2/L3 | yes | - | none: GPTWOF (G3T4), GPTICK (G3T5), GPFN (G3T8), RTGPP (G3R3) PASS in PACZ9E2 JOB04418 (6D) | CLOSED EXACT (Z9-D) | - |
| G5 | Levels 1-99, table rows, refill, level 99 = WON (D37) | 310 GP2 | EX | G1 G2ROW 01/13/ab, G3 G2B19, HA7 (start 99 WIN), L1 (13) | yes | - | rows > 13 = row 13 via HA7 | CLOSED EXACT | - |
| G6 | Fruit at 30 / 70 items, eaten / expired, under ghost (D37) | 310 | EX | G3 G2B19, G2 G2R7, S2T*, L1 | yes | - | none: G2BGHX (G3T26), G2BUND (G3T28) PASS in PACZ9E2 JOB04418 (6D) | CLOSED EXACT (Z9-D) | - |
| G7 | One extra life at 10000, none at 20000 (D37) | 310 G2X* | SEM | award executed via fruit (L1, 7DR N8/F7/F8, TD S2XL*); XLIFE is one shared paragraph called from ARC-EAT / EAT-GHOST / FRUIT-EAT, every call site and both branches executed on z/OS | yes | - | G2XP / G2XG / G2X20K oracle runs not executed (G2B28 5,806 and G2B29 5,260 lines exceed any job) | CLOSED SEMANTIC (composition) | none |
| G8 | Level-clear interactions (clear+power, clear+eyes, last item+hit) (D37, D36 GPLASTO/H) | 310 | SEM | level clear (G2R7, G2B19, N7/F7, TD), death+clear (S2T3, N7: RP edge death-clear), FRIGHT-START / RESET paths executed | yes | - | edges G2CLRO, G2CLRF, GPLASTO, GPLASTH not executed (1.0-1.9 k lines each) | CLOSED SEMANTIC (composition) | none (optional carriers listed in 7.3) |
| G9 | REALTIME logical rules: one RQ per quantum, buffered direction, TTL, reversal, freeze (D33, D34) | 310 RTB / RTT | EX | G2 RTB1/7/8/10/11, G2R1/5/7, DR1/DR2, R1/R2 | yes | ZV-D33 (presentation only) | none: RTB2 / RTB3 / RTB4 / RTB12 PASS in PACZ9E1 JOB04412 (6D); RTLONG closed by composition | CLOSED EXACT (Z9-D) | - |
| G10 | SPEED FAST conversion (RP.3) | 309 R3B | EX | RP R3B1-9 (2D), DR2, 7DR F*, R2, L3 | yes | - | - | CLOSED EXACT | - |
| G11 | Death freeze 10 / 12 quanta (D39) | 310 RTB7, 309 | EX+LV | E1 [10,10], Z1 [12,12] (6D); L2/L3 DISCRIMINATED | yes | freeze observability (R1 NOT OBSERVABLE) | - | CLOSED EXACT | - |
| G12 | ARCADE final-death sequence (RP) | 309 | EX | 7DR N6/NL2 6 writes, F6/FL2 7; L2/L3 live | yes | D1 6 / 7 writes | - | CLOSED PLATFORM-SPECIFIC | - |

### 4.3 Input, modes, presentation
| ID | Requirement (source) | MVS ref | Class | z/OS evidence (bin) | Valid | Approved diff | Residual | Status | Action |
|---|---|---|---|---|---|---|---|---|---|
| P1 | Turn mode A always available; batch cards = reference and fallback (RQ 5, MVS-8; D18) | 307 | EX | C1-C7 BAT (2D); B1, E1 (6D) | yes | - | - | CLOSED EXACT | - |
| P2 | TSO line mode via CLIST, D19 input rules, D20 no `***` mid-frame (PL ZOS-4) | 307 TSO1-6 | EX+OBS | C7 TSO1-6 batch replay (2D); L4 session 2 DIE1 / LOST0 (user attestation, 2D) | VALID BY NON-INTERFERENCE (DEC section 0) | ISPF option 6 boundary; Z3 SYSIN | live not traced (accepted) | CLOSED OBSERVATIONAL | ZOS-10: installed-release checks exercise line mode / 1.0 oracle after the clean rebuild |
| P3 | Input mapping U/D/L/R/Q, invalid input, empty-ENTER redraw, lowercase (RQ 5; D19) | 307, 310 | EX+LV | C1-C7; A (invalid X, lowercase r, blocked); R1 (x INVALID) | yes | - | - | CLOSED LIVE | - |
| P4 | PF7/8/10/11, PF9 pause / resume, PA2, no catch-up (D33) | 310 RTB8 | LV | R1-T4 (PF9 x2, PA2, x), RTB8 batch, DR N2/F2 | yes | ZV-D33; contention / BID timing | - | CLOSED LIVE | - |
| P5 | One write per logical quantum (D33) | 310 RTT | SEM | E2 EVERY TSD exact; live REALTIME = COALESCED | yes | **ZV-D33**: NORMAL 150 ms / stride 2 (~300 ms), FAST 125 ms / stride 3 (~375 ms); RTQS state-only advance (WS-FACE, PU-*, VIS, bell); no stale replay; START / RESUME re-anchor; post-write nonblocking read | EVERY live is PROTOCOL-BLOCKED on this TSO / TN3270E path (R1-T3) | CLOSED PLATFORM-SPECIFIC | see DEC-2 |
| P6 | Colour / highlight / GE glyphs via capability query, D40 bounded selection (D27-D32, D40) | 310 TSD45/48, QRY1 | EX+LV | A/B/C live = model; QRY1 29 sequences; real reply = qreply_dyn | yes | D28 behaviour recorded; CLEAR record | - | CLOSED LIVE | - |
| P7 | Every graphic tier can be switched off; all profiles / scales / canvases (RQ 24, 25; D29, D31, D32) | 310 TSD1-61, 311 G3T / G3R | EX | executed on z/OS only: GRAPHIC scale 4 on W / T / D, CLASSIC-glyph not-scaled FULL (S2T23), ANIM N | yes | - | none: every listed family PASS on PACZ6D - CLASSIC: TSD2 / 5 / 14 / 36 / 41 / 43 / 50 / 52 / 55 / 56 (PACZ9E1 JOB04412); ARCADE: G3T4 / 5 / 7 / 8 / 10 / 14 / 15 / 26 / 28 (PACZ9E2 JOB04418) | CLOSED EXACT (Z9-D) | - |
| P8 | Partial redraw = model, full redraw diagnostic (D27) | 310 | EX | A/B/C, TD (partial), S2T23 (full, not scaled) | yes | - | scaled FULL: the full-image composer runs on every first / PA2 frame | CLOSED EXACT | - |
| P9 | Geometry: 120x27 IBM-DYNAMIC, 80x24 fallback (D32) | E12 | LV | A/B (120x27), C (80x24) | yes | model 3/4/5 not offered on this system | - | CLOSED LIVE | - |
| P10 | RP presentation: READY!, death frames, popups, HUD high score, end line (D39) | 309 (23 edges) | EX | 20 / 23 RP edges reached by executed z/OS runs (EVERY or COALESCED model-exact) | yes | COALESCED presentation | none: popup-two-ghosts (G3T4) and pause in a fright (G3R3) PASS in PACZ9E2 JOB04418; pause-popup by composition; popup-clear COALESCED model-exact (N5/F5) | CLOSED EXACT (Z9-D) | - |
| P11 | METRICS(YES) diagnostic option (D23, optional) | no 2.0 oracle run | - | none | - | - | no frozen 2.0 reference exists; not mandatory (DEC-4 source check) | APPROVED OUT OF SCOPE - DIAGNOSTIC / NO FROZEN 2.0 EQUIVALENCE ORACLE | none (not PASS) |

### 4.4 Services
| ID | Requirement (source) | MVS ref | Class | z/OS evidence (bin) | Valid | Approved diff | Residual | Status | Action |
|---|---|---|---|---|---|---|---|---|---|
| S1 | Alarm on start / death / win / level / extra life (D35) | 308 | EX+LV | TD1-4, DR N1/F1, S1-S3 audible | yes | C7 = C3+alarm context | - | CLOSED LIVE | - |
| S2 | Alarm patterns, 2 / 3-quantum spacing, 3 s end pause (D41) | 308 21 edges | EX+LV | TD1-4 all 21 edges; S1-S3 live end pause / bell-only writes | yes | bells coalesced into presented writes | other 13 S2T / S2L1-3: redundant for coverage | CLOSED LIVE | - |
| H1 | HS read / create / update / tie / lower (D38) | 312 | EX+LV | HS1-8, B1 (6D), HL2-HL4, HL7 | yes | - | - | CLOSED LIVE | - |
| H2 | Practice start (LEVEL > 1) never recorded (D38) | 312 HA6 / HA7 | EX+LV | HA7 (99 > stored, not recorded), HL1 (5 > stored 720, live, store unchanged), L1-L3 | yes | - | HA6 not run: see section 7.4 | CLOSED EXACT (composition for HA6) | none |
| H3 | Unavailable / not saved / malformed / empty / 9999999 / no DD / DUMMY (D38) | 312 | EX+LV | HE1/2, HD1, HF1/2, HH1 (B14 under LE), HL6, HL8 | yes | z/OS IEC217I continuation form | - | CLOSED LIVE | - |
| H4 | CLASSIC never reads / writes the high score (D38) | 312 HA8 | EX | HA8, GD, S8C | yes | - | - | CLOSED EXACT | - |
| H5 | Production first write, DATA PDS FB 80/80 (PL 10; D44.4) | - | LV | SF (6D, installed CLIST) | yes | - | - | CLOSED LIVE | never repeat |
| H6 | HSP1..9 member prints (312) | 312 | MB | replaced by read-only state checks = ref_hs.Pds (ZOS-3 accepted) | yes | - | print format only | CLOSED MODEL-BATCH | - |
| R1 | ESTAE: line mode restored, next game clean (D40 context; PL 11) | RP.0 live | LV | B2, E1-E3 + GD each | yes | LE 0C7 / TSO 0C4 vs 0C7 not gated | cause not established (documentation only) | CLOSED LIVE | - |
| R2 | PACHSIO I/O guard RC 16 without abend | 312 HH1 | EX | HH1 (2D), HL8 (6D) | yes | - | - | CLOSED EXACT | - |

### 4.5 Installation, CLIST, release
| ID | Requirement (source) | MVS ref | Class | z/OS evidence (bin) | Valid | Approved diff | Residual | Status | Action |
|---|---|---|---|---|---|---|---|---|---|
| I1 | CLIST defaults and PARM lines unchanged from 2.0 except Z2 / Z3 / Z5 (PL ZOS-4) | test_g8 | EX | INS, PACZ6CL JOB09382, byte-verified installs | yes | Z2, Z3, Z5 | - | CLOSED EXACT | - |
| I2 | CLIST HS block (&SYSDSN guard, DUMMY fallback, ARCADE only) | 312 HSCL* | LV | HL6 (PACZ8HU), SF (installed, DATA OK), every CLASSIC game | yes | - | - | CLOSED LIVE | - |
| I3 | CEEOPTS errors: missing / check failed / already allocated -> RC 8, no CALL (Z2) | - | PS | PACZ4Z3 26/26; E1 leftover CEEOPTS refused | yes | - | - | CLOSED PLATFORM-SPECIFIC | - |
| I4 | CLIST with no operand plays (plan ZOS-9 live: G8 scenario twice) | G8.4 | LV | none | - | EVERY known blocked for interactive REALTIME on this path (R1-T3) | none for equivalence: release policy frozen (DEC-2) | NOT AN EQUIVALENCE GAP - ZOS-10 REQUIRED ACTION | ZOS-10: CLIST REALTIME default -> COALESCED + verification list (DEC-2) |
| I5 | z/OS capability matrix column (RQ 28; PL ZOS-5 / ZOS-9 exit) | CAPABILITIES.md | doc | docs/evidence/zos9-equivalence.md section 15 (every row -> accepted evidence or an approved decision) | yes | - | none | CLOSED DOCUMENTATION | - |
| I6 | README z/OS, authenticity rule, release from empty libraries, tag 2.0-zos (RQ 13 ZOS-7, 24, 27; PL ZOS-10) | G8 release | - | - | - | - | - | OUT of ZOS-9 (ZOS-10) | ZOS-10 |
| I7 | Full regression of every oracle run (RQ 13 ZOS-7; PL 13 L2/L3 "in full") | 268k oracle lines | EX | the matrix + sections 4-5 + PACZ9E1 / PACZ9E2 | - | - | superseded by DEC-1 (the matrix is the coverage authority) | CLOSED by DEC-1 (its GAP rows closed by Z9-D) | - |

FINAL counts (ZOS-9 closure; PACZ9E1 JOB04412 PASS 14/14, PACZ9E2 JOB04418 PASS 10/10, I5 written): CLOSED EXACT 22,
CLOSED SEMANTIC 2, CLOSED MODEL-BATCH 4, CLOSED LIVE 11, CLOSED OBSERVATIONAL 1, CLOSED PLATFORM-SPECIFIC 5, CLOSED by
DEC-1 1 (I7), CLOSED DOCUMENTATION 1 (I5), NOT AN EQUIVALENCE GAP / ZOS-10 REQUIRED ACTION 1 (I4), OUT OF SCOPE 3
(A11, I6, P11) = 51. **GAP = 0, DECISION = 0.**
Before Z9-D (51 rows, after the 2026-10-20 decisions): CLOSED EXACT 17, CLOSED SEMANTIC 2, CLOSED MODEL-BATCH 4, CLOSED
LIVE 11, CLOSED OBSERVATIONAL 1, CLOSED PLATFORM-SPECIFIC 5, CLOSED by DEC-1 1 (I7), GAP 6 (G4, G6, G9, P7, P10 ->
PACZ9E1 / PACZ9E2; I5 documentation only), NOT AN EQUIVALENCE GAP / ZOS-10 required 1 (I4), OUT 3 (A11, I6, P11). A
row with a split verdict is counted once, under its open part.

---------------------------------------------------------------------------------------------------------------------

## 5. Edge coverage on z/OS (D12: "no documented edge case stays untested")
Measured locally by replaying, through the frozen models, the exact cards of every run executed on z/OS (ZOS-2 BAT /
TSO, ZOS-3 HS / TD, ZOS-6 / 7 dry runs, ZOS-5..8 live) and evaluating the frozen predicates:
| Family | Edges | Reached on z/OS | Not reached |
|---|---|---|---|
| CLASSIC 1.0 (307 cases) | 25 runs | 25 | - |
| S2 alarm (search_s2, D41) | 21 | 21 | - |
| HS (H1-H15, 19 runs) | 19 | 18 + HA6 by composition | - |
| GP1 (search_gp1 + GPLASTO / GPLASTH) | 12 | 8 | GPTWOF, GPFN, GPLASTO, GPLASTH |
| GP2 (search_gp2) | 12 | 6 | G2CLRO, G2CLRF, G2BUND, G2XP, G2XG, G2X20K |
| RP (search_rp EDGES) | 23 | 20 (3 only under COALESCED) | popup-two-ghosts, pause-popup (popup-clear: COALESCED only) |
| RT cases (rtcases) | 12 | 7 | RTCORNER, RTTTL, RTREV, RTLONG, RTEDGE0 |
| Renderer families (profile x scale x canvas) | 15 | 6 | see P7 |
Closure rule applied in section 7: an item whose code path has been executed on z/OS (each statement / branch reached,
only the combination is new) is CLOSED SEMANTIC by composition when its only carrier is unaffordable or its interaction
is pure core arithmetic already proven; an item whose **code path no z/OS binary has ever executed** (renderer tables /
layouts / scales, specific RT branches) is a genuine GAP, because Enterprise COBOL semantics (TRUNC(STD) binary fields,
table indexing, buffer addressing; plan sec. 8) are unproven there.

## 6. Approved z/OS differences (to be listed explicitly in the ZOS-9 report; not regressions)
| # | Difference | Authority | Pinned by |
|---|---|---|---|
| AD1 | Z1 `COPY` syntax | ZOS-DIFFS Z1 | tests/zos_c2.py |
| AD2 | Z2 CLIST CEEOPTS (profile A) | Z2 | zos_c2 z2_guard, PACZ4Z3 |
| AD3 | Z3 terminal SYSIN fixed 80 | Z3 | zos_c2, L4 |
| AD4 | PRESENT(COALESCED): logical 150 / 125 ms, physical stride 2 (~300 ms) / 3 (~375 ms); not one TPUT per quantum | ZV-D33, Z4, Z5 | zos_z4.json, R1 / R2 gates |
| AD5 | RTQS state-only advance on skipped quanta (WS-FACE, PU-*, VIS, logical bell); diff baseline advances only on writes | ZV-D33 | DR1 / DR2, ref_rt present='C' |
| AD6 | No stale replay; START / RESUME re-anchor presentation | ZV-D33 | R1-T4 |
| AD7 | Post-write nonblocking read feeding the next quantum | ZV-D33 | Z4 RT-POST-READ |
| AD8 | TN3270E BID / CONTENTION-RESOLUTION / keyboard direction timing | ZOS-5, ZV-D33 | live gates |
| AD9 | Contextual TSO CONTROL record exactly `F1 C3` (never "ignore short records") | ZV-D33 decision 1 | fixtures section 20 |
| AD10 | SOUND context: previous WCC C3 or C7 (C7 = C3 + alarm bit only) | ZOS-8 | zos8_live_check.sound_c3_controls |
| AD11 | D1 final death: 6 (NORMAL) / 7 (FAST) consecutive exact writes | ZOS-7 D1 | 7DR, L2 / L3 |
| AD12 | Freeze 10 / 12 quanta; stationary live cases NOT OBSERVABLE, moving cases DISCRIMINATED | ZV-D33 split, ZOS-7 | E1 / Z1, L2 / L3 |
| AD13 | Final screen follows logical state, not the last physical frame | ZV-D33 (VIS fix) | DR1 JOB09466 |
| AD14 | Bells logical, coalesced into permitted presentations | ZOS-8 | S1-S3 |
| AD15 | Recovery: LE 0C7 / TSO 0C4 (E1 / E2), 0C7 / 0C7 (E3); acceptance = usable session + clean next game | ZOS-8 | E1-E3 |
| AD16 | ISPF option 6 Command Shell boundary instead of native READY; TSO / VTAM CLEAR record | ZOS-5 decisions | zos5_live_check |
| AD17 | z/OS IEC217I continuation form; DISPLAY SYSOUT FBA 121 | ZOS-3, ZOS-1 | zos_hs_check, zos_equiv |
Documentation errata to fix at ZOS-9 closure (doc only, with approval): ZOS-DIFFS C3 still says "not resolved" (closed
in ZOS-8); ZOS-DIFFS Z4 / Z5 headings still say "NOT built / NOT installed" (status lines below them are current);
docs/evidence/zos8-services.md line 6 says the installed CLIST(PACMAN) "changed" - it means **unchanged** (the same
document's production-source conclusion and every byte check say unchanged).

## 7. Z9-C - Genuine gaps, decisions and closures

### 7.1 Consolidated deferred / pending items found in the documents
| # | Item (source) | Resolution |
|---|---|---|
| 1 | C1 VALIDATE (ZOS-0) | disproved ZOS-2 - closed |
| 2 | C3 ASMA303W / PACFSIO ESTAE (ZOS-2..7) | CLOSED ZOS-8 (E1-E3), doc erratum only |
| 3 | S2 alarm deferred from ZOS-2 | closed ZOS-3 TD1-4 (+ ZOS-8 live) |
| 4 | Oracle 309 RPT1 / 312 HA1 boundaries | resolved (digest-bound KNOWN_BOUNDARIES) |
| 5 | HA6 (ZOS-3 -> ZOS-9/10) | CLOSED by composition (7.4) |
| 6 | HSP1..9 prints (ZOS-3 -> ZOS-9/10) | CLOSED MODEL-BATCH (state checks = ref_hs.Pds) |
| 7 | HS CLIST block HSCLS1/2, HSCLT (ZOS-3 -> ZOS-4 -> ZOS-8) | CLOSED LIVE (HL6, SF, CLASSIC games) |
| 8 | Other 13 S2T + S2L1..3 (ZOS-3) | CLOSED (21/21 edges; S2L blocks byte-covered by ZOS-2 PASS cases) |
| 9 | "Rest of the frozen batteries / full GP1 GP2 GP23 RP batteries" (ZOS-2, 3, 6, 7 -> ZOS-9/10) | DEC-1 + gaps Z9-G1 / Z9-G2 |
| 10 | Live TPUT / TGET / bell / timing unproved (ZOS-3) | closed ZOS-5..8 |
| 11 | Dry-run end-pause spacing not exercised (ZOS-3) | closed live S1-S3 |
| 12 | Live freeze discrimination (ZOS-6) | closed ZOS-7 (DISCRIMINATED) |
| 13 | 10-minute pause soak (plan ZOS-6) | superseded: 60 s approved (ZOS-6 design) |
| 14 | Release default of PRESENT (ZOS-6, 7, 8) | DEC-2 |
| 15 | Other canvases model 3/4/5 live (ZOS-5) | OUT: not offered on this system; TSD canvases in Z9-G1 / G2 |
| 16 | ZOS-4 live session 2 not traced (attestation) | accepted by the user; CLOSED OBSERVATIONAL |
| 17 | Line mode on the post-Z4 binary | LOW residual; ZOS-10 installed checks |
| 18 | LE / TSO abend code difference (ZOS-8) | documentation only, AD15 |
| 19 | DATA `used 100` room (ZOS-7) | closed B1 / SF |
| 20 | METRICS(YES) never run on z/OS (no 2.0 oracle run) | DEC-4 |
| 21 | z/OS capability matrix column (plan) | Z9-DOC |
| 22 | Doc errata (section 6) | Z9-DOC |
| 23 | P2 pending TGET subtask (probe design) | deferred design alternative, not a requirement - closed as not needed (ZV-D33) |

### 7.2 Decisions (proposed here; taken by the user 2026-10-20, see section 0)
- **DEC-1 Full-battery criterion.** Plan sec. 6 ZOS-9 ("levels L1-L4 of sec. 13 in full") and the "full battery ->
  ZOS-9/10" deferrals are not executable as written: 268k oracle application lines (~80 jobs under the ~4,000-line
  practice) and five runs exceed the site limit alone, which LINES= / new output datasets would be needed to run (not
  authorised). Proposed replacement for ZOS-9: the D12 edge / code-path coverage criterion of section 5 (every
  documented edge and every renderer family executed on z/OS at least once with exact equivalence, else closed by an
  explicit composition argument). Whether ZOS-10 re-runs run-only decks on the release build (plan sec. 14 step 3) is a
  ZOS-10 design question.
- **DEC-2 PRESENT release default.** The installed CLIST defaults to PRESENT(EVERY) (D33). On this TSO / TN3270E path
  EVERY is protocol / input blocked for interactive REALTIME (R1-T3, ZV-D33 cause). The plan's ZOS-9 live check "CLIST
  with no operand, G8 scenario twice" would therefore exercise a known-blocked default; it is NOT proposed. The choice
  (keep EVERY + document, or COALESCED default = a Z5 CLIST change) is a release decision for ZOS-10; changing it is a
  production change outside ZOS-9.
- **DEC-3 Gap closure mode** for Z9-G1 / Z9-G2: (A, recommended) two batch TSD / BAT dry-run jobs (7.3); (B) close them
  by the ZOS-5 composition argument (the renderer is byte-producing COBOL identical to 2.0) and run nothing in ZOS-9.
- **DEC-4 METRICS(YES).** No 2.0 oracle run exists to be equivalent to; proposed APPROVED OUT OF SCOPE (diagnostic
  option, unchanged source; documented as not validated on z/OS).
- **Note for ZOS-10 (not a ZOS-9 action):** any installed live smoke must account for HISCORE = 980: an ARCADE LEVEL 1
  game scoring > 980 WRITES production DATA; the smoke must either stay <= 980, start at LEVEL > 1, or have that write
  approved explicitly. Its expected HUD / end lines start from 980, not from "empty".

### 7.3 Genuine execution gaps (the only ones)
| | Z9-G1 | Z9-G2 |
|---|---|---|
| Requirement IDs | P7 (CLASSIC renderer families), G9 (RT edges) | P7 (ARCADE renderer families), P10, G4, G6 |
| Missing proof | PACSCR / PACDISP / PACPLAT paths never executed by any z/OS binary: HILITE(NO), GLYPHS(BASE), GRAPHIC not scaled, CLASSIC-glyph PARTIAL, SCALE(3), SCALE T size guard, canvases X / M / U / L; PACRT RTCORNER / RTTTL / RTREV / RTEDGE0 | ARCADE screens of the same families + 80x24 compact HUD; edges GPTWOF + popup-two-ghosts, GPTICK, GPFN, G2BGHX, G2BUND, RTGPP (pause in a fright) |
| Why existing evidence is insufficient | every z/OS TSD / TSC run used GRAPHIC scale 4 (W / T / D) or CLASSIC not-scaled FULL; composition cannot cover code never executed | idem; model replay of every executed card set misses these edges |
| Batch / live | batch dry run (TSD + BAT), no terminal | batch dry run (TSD), no terminal |
| Proposed execution | one job PACZ9E1, steps of oracle 310 (own blocks, own PARMs): TSD2, TSD5, TSD14, TSD41, TSD36, TSD43, TSD50, TSD52, TSD55, TSD56, RTB2, RTB3, RTB4, RTB12 | one job PACZ9E2, steps of oracle 311: G3T4, G3T5, G3T8, G3T26, G3T28, G3T7, G3T10, G3T15, G3T14, G3R3 |
| Program | EXEC PGM=PACZ6D (= installed PACMAIN by PACZ6INS IEBCOPY; the accepted dry-run convention), STEPLIB Z00000.PACMAN.LOAD, CEEOPTS `ALL31(OFF),STACK(,,BELOW)`, no PACHS DD | same |
| Expected result | every step CC 0000, SYSOUT = its own oracle 310 block line for line (ASA + padding only) and = ref_gx_screen / ref_rt | every step CC 0000, SYSOUT = its own oracle 311 block and = the GP23 / RP models |
| Checker / oracle | zos_equiv --subset (own-block anchoring) + the frozen models; 310 / 311 unchanged | same (311 anchoring proven by 7DR1 E3) |
| Application SYSOUT (exact, from the oracle blocks) | 55+91+75+89+273+132+324+258+194+194+35+31+31+385 = **2,167** | 224+296+334+167+167+226+394+173+242+405 = **2,628** |
| Estimated spool (JES ~30 lines / step + ~100) | ~2,700 | ~3,050 |
| Datasets read | Z00000.PACMAN.LOAD (PACZ6D) | same |
| Datasets written | none (spool only) | none |
| Production DATA touched | NO (no PACHS DD) | NO |
| Risk | low (read-only, deterministic, < 4,000 lines) | low |
| STOP criteria | any step RC != 0, CEE / abend / $HASP375, unanchored step, any line difference -> freeze spool, classify (section 9), no resubmit | same |
| One execution sufficient | yes (deterministic) | yes |
Not proposed (closed by composition, 7.2 / matrix): G2XP, G2XG, G2X20K (XLIFE shared paragraph), G2CLRO, G2CLRF,
GPLASTO, GPLASTH (level-clear paths executed), RTLONG (2,221 lines; counters > 99 proven: QUANTA 0000589, TURNS 0000374
format), pause-popup (pause and popup state executed separately; G3R3 adds pause in a fright). Optional carriers if the
user prefers execution over composition: RPT39 (G2XG, 2,574 lines, oracle 309), G3T12 (GPLASTO, 1,035).
Local Z9-D preparation (after approval only): deck generation through the existing `make_deck.py --target zos` chunk
mechanism, render review, audit, precheck, checker self-test on the oracle blocks; nothing new unless a test shows it is
needed.

### 7.4 HA6 conclusion
1. Unique requirement: D38 "a practice start (LEVEL > 1) is never recorded even when the score beats the stored record"
   (HA6: stored 2760, LEVEL 13 start, 10090, `START LEVEL 13: HIGH SCORE NOT RECORDED`).
2. Already proven: oracle 312 HA6 = oracle 310 **G2B29** (5,260 lines) + exactly two HS lines (verified locally by
   diff of the oracle blocks). The branch is proven on z/OS by HA7 (stored 2760, LEVEL 99 start, 6160 beats it, not
   recorded; PACZ3HS, exact), live HL1 (stored 720, LEVEL 5, 2180 beats it, not recorded, store unchanged; installed
   program) and L1-L3 (absent store); line format with a 5-digit score and end level by L1 (`HIGH SCORE 0010780 LEVEL
   013`); state neutrality by ref_hs + HA7; PACHSIO unchanged.
3. Unique unproven z/OS behaviour: none in HS. Its gameplay (G2XG: extra life from a ghost, levels 13 -> 15) is a GP2
   edge, handled under G7 (closed by composition; RPT39 optional carrier).
4. Minimum safe proof: none needed. 5. **HA6 = CLOSED BY COMPOSED EVIDENCE** (approved 2026-10-20). Closure chain:
   (1) HA6's gameplay output is exactly the frozen GP2 oracle 310 G2B29 behaviour; (2) its additional high-score
   behaviour is "start at a later level -> do not record"; (3) that rule is demonstrated by accepted z/OS evidence:
   HA7 (batch, PACZ3HS) and HL1 (live, installed program); (4) PACHSIO did not change; (5) therefore HA6 contains no
   unique remaining z/OS behaviour. Not "skipped"; no LINES=, no output dataset, no split, no DATA change.

### 7.5 Cases explicitly NOT rerun (and why)
ZOS-5 A/B/C, ZOS-6 R1/R2, ZOS-7 L1/L2/L3, ZOS-8 HL*, E1-E3, S1-S3: accepted on the current or a path-neutral binary,
nothing invalidated them. Stage F: never (it is no longer a first write and would rewrite production state). HA6:
closed (7.4). The G8 no-operand live: DEC-2. Full batteries: DEC-1. ZOS-2 CLASSIC / ARCADE subsets on the post-Z4
binary: Z4 path-neutral; the release binary is rebuilt in ZOS-10 anyway.

## 8. Original migration plan: superseded criteria (do not reintroduce)
| Original (plan) | Final approved replacement | Authority |
|---|---|---|
| ZOS-6: one write per quantum, no skipped period | logical quantum per 150 / 125 ms, physical stride 2 / 3 (COALESCED), state-only RTQS | ZV-D33, Z4 / Z5 |
| ZOS-6: drift < 1 ms / 100 quanta, client gap median within +-10 ms of T | frozen R1 / R2 gates (median 280-320 / 345-405, p95, max, backlog, reaction) | ZV-D33 sec. 11 |
| ZOS-6: fright / eyes / freeze wall-clock within one quantum | logical counts exact offline; freeze-span proxy; live discrimination where observable | ZV-D33 split, ZOS-7 |
| ZOS-6: 10-minute pause soak | 60 s pause | ZOS-6 design (approved) |
| D33 lateness envelope as a blocking rule | diagnostic only under COALESCED | ZV-D33 decision 2 |
| ZOS-4: line-mode game from native READY | ISPF option 6 Command Shell | ZOS-4 / ZOS-5 practice and checker decision |
| ZOS-2..8: full decks as single jobs | small chunks < 4,000 lines; no LINES= | ZOS-2 decision 2026-10-14 |
| ZOS-3: HS 21 runs + HSP prints | 8 jobs, HA6 deferred, state checks | ZOS-3 option A |
| ZOS-8: HS live L1-L7 on DATA, S2A-S2E live | HL1-HL8 on test data, one production first write; S1-S3 | ZOS-8 U1-U12 |
| ZOS-8: E2 abend path text | recovery to a usable session + clean game, codes not gated | ZOS-8 |
| ZOS-9: L1-L4 "in full" + G8 no-operand live twice | coverage criterion (DEC-1); G8 live depends on DEC-2 | proposed here |
| Release name 1.0-zOS | 2.0-ZOS / tag 2.0-zos | D44 |

## 9. Execution order, micro-gates, failure classification (Z9-D, once authorised)
1. focused read-only precheck (deck of record = generated deck = audited; LOAD(PACZ6D) present; no job of the same name
   pending); 2. submit PACZ9E1 ONCE; 3. retrieve the spool, `zos9_equiv.py --job 1 SPOOLDIR`; 4. require PACZ9E1 PASS
   (every step); 5. only then submit PACZ9E2 ONCE; 6. retrieve, `--job 2`; 7. require PACZ9E2 PASS; 8. STOP.
If PACZ9E1 fails, PACZ9E2 is NOT submitted. No retry without a new decision.
On any mismatch: freeze the evidence (SHA-256, read-only) and STOP; classify first as PRODUCT REGRESSION /
TOOLING-CHECKER DEFECT / ORACLE-ANCHOR-PARSING DEFECT / PLATFORM-ENVIRONMENT DIFFERENCE / OPERATOR-JOB-CONSTRUCTION
ERROR / APPROVED-OBSERVATIONAL DIFFERENCE. Never change PACMAN first, loosen the normalisation, alter a frozen model,
regenerate the MVS oracle or resubmit automatically. A checker change follows the established rule (original verdict
kept, fix approved, same evidence rechecked).

## 10. Proposed ZOS-9 final evidence report (docs/evidence/zos9-equivalence.md)
1. Result and baseline (tags, binaries, production state). 2. Production-change timeline and invalidation verdicts
(sections 2-3). 3. The equivalence matrix (section 4, final statuses). 4. Edge / renderer coverage (section 5, after
Z9-D). 5. Approved z/OS differences AD1-AD17. 6. Z9-D jobs (if run): decks, results, spool digests. 7. HA6 closure.
8. Decisions DEC-1..4 as taken (section 0). 9. Superseded plan criteria. 10. z/OS capability column (Z9-DOC). 11. Errata
applied.
12. Carried to ZOS-10 (release rebuild, PRESENT default, HISCORE-aware smoke, installed 1.0 oracle on the release
binary).

## 11. Z9-D local preparation (2026-10-20; nothing submitted)
Files: tools/zowe/zos9_equiv.py (decks, audit, per-step checker, selftest), jcl/zos/PACZ9E1.jcl and
jcl/zos/PACZ9E2.jcl (decks of record = `zos9_equiv.py --job N --deck`; prefix @@HLQ@@.PACMAN rendered at submission),
tests/test_zos9.py (focused local test). Reused unchanged (guarded = zos-8): make_deck.py + zos_target.py (each step
verbatim from the z/OS rendering of the MVS deck, `EXEC PGM=PACZ6D`), zos_equiv (anchoring, compare, zos_runs),
zos_classic_check.health (spool health), zos6_dry (fail-closed TSD parser, compare_lines), the frozen models
ref_gx_screen / ref_gp2 / ref_rt / ref_mvs6 and tests/test_gp2.py bells() (executed verbatim from the frozen file).
No ZOS-5..8 tool changed; no oracle, model or case file changed.

Step order = deck = oracle order (required by the own-block anchoring); membership exactly as approved (PACZ9E1:
TSD36 before TSD41 / TSD43; PACZ9E2: G3T7 before G3T8, G3T14 before G3T15 - the approved lists were not in deck order).
Every step: `EXEC PGM=PACZ6D,COND=(0,NE)`, STEPLIB <prefix>.LOAD SHR, CEEOPTS `ALL31(OFF),STACK(,,BELOW)` (profile A),
SYSIN = the historical cards, SYSOUT / CEEDUMP SYSOUT=A, SYSUDUMP DUMMY; PARM and cards = the step of
releases/2.0-MVS-MAX/decks (audited). The only dataset named is <prefix>.LOAD: no PACHS, DATA, DELETE, IEBCOPY,
IEWBLINK, IGYCRCTL, ASMA90, SYSLMOD, PACMAIN or PACZ2D. A full screen is recognised by the tests/test_gx.py transport
rule (a frame carrying SF orders X'1D'), proven against every block by the selftest.

### GAP row -> job -> step -> oracle -> model
| Step | Job | Oracle block | Lines | Run (frozen list) | Model | GAP rows / paths closed |
|---|---|---|---|---|---|---|
| TSD2 | PACZ9E1 | 310 TSD2 | 55 | TSD['GX'][1] MOVES H Y A Y P, CLASSIC glyphs | ref_gx_screen.frames + ref_mvs6 end lines | P7 CLASSIC glyphs, partial redraw, not scaled |
| TSD5 | PACZ9E1 | 310 TSD5 | 91 | HILITE N | idem | P7 HILITE(NO) (CLASSIC) |
| TSD14 | PACZ9E1 | 310 TSD14 | 75 | GLYPHS G, no scale | idem | P7 GRAPHIC not scaled (CLASSIC) |
| TSD36 | PACZ9E1 | 310 TSD36 | 273 | SCALE 3 | idem | P7 SCALE(3) 3x2 (CLASSIC) |
| TSD41 | PACZ9E1 | 310 TSD41 | 89 | GLYPHS B, SCALE 4 refused | idem | P7 GLYPHS(BASE) (CLASSIC) |
| TSD43 | PACZ9E1 | 310 TSD43 | 132 | SCALE T | idem | P7 size guard (CLASSIC) |
| TSD50 | PACZ9E1 | 310 TSD50 | 324 | canvas X | idem | P7 132x27 (CLASSIC) |
| TSD52 | PACZ9E1 | 310 TSD52 | 258 | canvas M | idem | P7 80x32 (CLASSIC) |
| TSD55 | PACZ9E1 | 310 TSD55 | 194 | canvas U | idem | P7 100x25, too small (CLASSIC) |
| TSD56 | PACZ9E1 | 310 TSD56 | 194 | canvas L | idem | P7 160x30, > 4095 cells (CLASSIC) |
| RTB2 | PACZ9E1 | 310 RTB2 | 35 | RT_BAT RTCORNER | ref_rt.simulate | G9 RTCORNER |
| RTB3 | PACZ9E1 | 310 RTB3 | 31 | RT_BAT RTTTL | ref_rt.simulate | G9 RTTTL |
| RTB4 | PACZ9E1 | 310 RTB4 | 31 | RT_BAT RTREV | ref_rt.simulate | G9 RTREV |
| RTB12 | PACZ9E1 | 310 RTB12 | 385 | RT_BAT RTEDGE0 | ref_rt.simulate | G9 RTEDGE0 |
| G3T4 | PACZ9E2 | 311 G3T4 | 224 | GP23_TURN GPTWOF, HILITE N, 80x24 | ref_gx_screen on ref_gp2.Level + ref_gp2 end lines | P7 HILITE(NO) (ARCADE); G4 GPTWOF; P10 popup-two-ghosts |
| G3T5 | PACZ9E2 | 311 G3T5 | 296 | GPTICK, GRAPHIC not scaled | idem | P7 GRAPHIC not scaled (ARCADE); G4 GPTICK |
| G3T7 | PACZ9E2 | 311 G3T7 | 226 | GPHOME, scale 4 on 80x24, SOUND Y | idem + test_gp2 bells() | P7 ARCADE on 80x24 (compact HUD) |
| G3T8 | PACZ9E2 | 311 G3T8 | 334 | GPFN, SCALE 3 | idem | P7 SCALE(3) (ARCADE); G4 GPFN |
| G3T10 | PACZ9E2 | 311 G3T10 | 394 | GPREVB, canvas X | idem | P7 132x27 (ARCADE) |
| G3T14 | PACZ9E2 | 311 G3T14 | 242 | GPAI0, SCALE T | idem | P7 size guard (ARCADE) |
| G3T15 | PACZ9E2 | 311 G3T15 | 173 | GPWALKF, canvas M | idem | P7 80x32 (ARCADE) |
| G3T26 | PACZ9E2 | 311 G3T26 | 167 | G2BGHX, CLASSIC glyphs | idem | P7 CLASSIC glyphs (ARCADE); G6 ghost on the fruit cell |
| G3T28 | PACZ9E2 | 311 G3T28 | 167 | G2BUND, BASE | idem | P7 GLYPHS(BASE) (ARCADE); G6 uneaten fruit |
| G3R3 | PACZ9E2 | 311 G3R3 | 405 | GP23_RT RTGPP | ref_rt.tsd on ref_gp2.Level / LevelRT | P10 / G4 pause during a fright |
Application lines: PACZ9E1 2,167, PACZ9E2 2,628 (the frozen blocks, exact). Estimated spool: ~2,700 / ~3,050 (JES
~30 lines per step + ~100). A GAP row closes only when every step carrying it passes on its own (oracle block AND
model);
a job PASS alone closes nothing.

### Checker (per step, fail closed)
`zos9_equiv.py --job N SPOOLDIR`: spool health (COND CODE 0000, PGM PACZ6D, SYSOUT only, STEPLIB retained once per
step, no CEE / abend / $HASP375 text); exact step list and job name; zos_equiv --subset vs the oracle (own block,
oracle order, block end); the step's SYSOUT = its own oracle block line for line; the step's SYSOUT parsed (zos6_dry
parser) = the frozen model (frames byte for byte, TSX transport lines, end lines; BAT lines exact). Report per step.

### Local test results
`python3 tools/zowe/zos9_equiv.py --selftest`: PASS (every step anchored at its own block; model render = oracle block
for all 24 steps; deck audits; GAP paths = run configurations; 16 injected faults detected).
`python3 tests/test_zos9.py`: PASS (frozen guards = zos-8; decks of record = generated; GAP map complete; checker on
simulated spools: both jobs PASS on their oracle blocks, 18 faults FAIL, a one-line change fails that step only).

## 12. Carried to ZOS-10 (frozen now)
1. CLIST REALTIME default -> PRESENT(COALESCED), PRESENT(EVERY) explicit; the DEC-2 verification list.
2. After the clean final rebuild: installed-release checks exercise the line-mode / 1.0-oracle path.
3. Installed release smoke accounts for HISCORE = 980: an ARCADE LEVEL 1 game scoring > 980 writes production DATA -
   stay <= 980, start at LEVEL > 1, or approve that write explicitly; expected HUD / end lines start from 980.

## 13. Z9-D execution (2026-10-20, authorised once each; the only ZOS-9 host executions)
Pre-host gate PASS (HEAD = zos-8 32d99f2, tracked files unchanged, decks = validated renders, diff-check clean).
Read-only precheck: Z00000.PACMAN.LOAD (PDSE, RECFM U) holds PACZ6D; no PACZ9* job on the spool.
| Job | JOBID | CC | Steps | Application lines | Spool lines | Checker | Verdict |
|---|---|---|---|---|---|---|---|
| PACZ9E1 | JOB04412 | 0000 | 14 / 14 PASS (PGM PACZ6D, RC 0000, STEPLIB retained 14 times, SYSOUT only) | 2,167 | 2,571 | zos9_equiv --job 1 | PASS |
| PACZ9E2 | JOB04418 | 0000 | 10 / 10 PASS (idem, STEPLIB retained 10 times) | 2,628 | 2,924 | zos9_equiv --job 2 | PASS |
Every step: own oracle block anchored (zos_equiv --subset, all OK), SYSOUT = its oracle block exactly, SYSOUT = its
frozen model exactly (G3T7 SOUND(YES) by the frozen test_gp2 bells rule; no live-transport rule involved). Submitted
decks = the decks of record rendered with Z00000. JES log: $HASP373 / $HASP395 RC=0000 only; no CEE / abend message;
no extra spool DD. No PACHS, no DATA reference, no compile / assemble / bind / promotion / DELETE, no dataset written:
spool output only; DATA(HISCORE) not referenced. Raw spool kept outside git: build/zos/PACZ9E1-JOB04412,
build/zos/PACZ9E2-JOB04418 (read-only), manifests PACZ9E1-JOB04412.SHA256SUMS (567ba439...), PACZ9E2-JOB04418.SHA256SUMS
(247c07d4...); checker outputs PACZ9E{1,2}-JOB044*.check.{txt,json} (E1 json 4485b1b5..., E2 json e7545d33...).
No classification needed (no discrepancy).

## 14. Closure (2026-10-20)
ZOS-9 CLOSED / PASS: final evidence docs/evidence/zos9-equivalence.md (result, invalidation conclusion, methodology,
PACZ9E1 / PACZ9E2 per-step tables, gaps closed, HA6, approved differences, z/OS capability column, errata). The three
section-6 errata were applied as post-closure documentation errata (docs/ZOS-DIFFS.md, docs/evidence/zos8-services.md).
