# ZOS-6 REALTIME - build, dry-run and live acceptance evidence (2026-10-19)

Status: ZOS-6 COMPLETE / PASS. R1-T4 (NORMAL) PASS and R2 (FAST) PASS, both with PRESENT(COALESCED) under ZV-D33.
Design: docs/zos6-design.md (cases, driver, checker contract), docs/zos6-production-design.md (ZV-D33, PSLT,
acceptance split, gates), docs/zos6-protocol-probe.md and docs/zos6-io-architecture-memo.md (why coalescing).
Product changes: Z4 (PACREQ, PACMAIN, PACPLAT, PACDISP, PACSCR) and Z5 (z/OS CLIST), docs/ZOS-DIFFS.md.
Checker: tools/zowe/zos6_live_check.py (tests/test_zos_tools.py sections 20 / 22); driver tools/zowe/zos6_drive.py.
MVS (tag 2.0-mvs-max) stays frozen.

## Final production state (Z00000.PACMAN.*)
| Member | Content |
|---|---|
| LOAD(PACMAIN) | the ZOS-6 program: LOAD(PACZ6D) of JOB09460, promoted by PACZ6INS JOB09499 (IEBCOPY, replace) |
| CLIST(PACMAN) | the ZOS-6 CLIST (src/zos/PACMAN.clist, Z5; 136 records, verified byte for byte); default PRESENT(EVERY) |
| LOAD(PACZ2D) | unchanged: the rollback source (promote it back to PACMAIN to restore the zos-5 program) |
| LOAD(PACZ6D) | unchanged since JOB09460: the ZOS-6 test / build member (dry runs) |
Nothing outside Z00000.PACMAN.* was touched; no delete, purge or reallocation.

## Build and z/OS batch jobs
| Job | Purpose | Result |
|---|---|---|
| PACZ6BLD JOB09327 | first build into PACZ6D | S722 (COB8 PACSCR SYSUT11 B37-04): ENVIRONMENT / TOOLING, superseded |
| PACZ6BLD JOB09365 | rebuild, compiler work space CYL,(1,1) for this deck only | RC 0000; superseded by JOB09460 (VIS fix) |
| PACZ6CL JOB09382 | CLIST test copy: PRESENT(EVERY) / (COALESCED) PARMs | PASS (RC 0000) |
| PACZ6DRY JOB09408 | dry run, one job | JCL error (9-character job name), nothing ran; split + job-name guard |
| PACZ6DR1 JOB09418 | dry run 1 on the JOB09365 build | FAIL: the PACSCR VIS end-screen defect + a comparator defect, both fixed |
| PACZ6BLD JOB09460 | clean production build into PACZ6D (7 compiles + link, AMODE 24 RMODE 24 RENT) | RC 0000 (every step CC 0000) |
| PACZ6DR1 JOB09466 | dry run 1: E1 E2 N1 N2 N3 N4 | PASS (RC 0000, comparator PASS) |
| PACZ6DR2 JOB09470 | dry run 2: N5 F5 F1 F2 F3 F4 Z1 | PASS (RC 0000, comparator PASS) |
| PACZ6INS JOB09499 | promotion PACZ6D -> PACMAIN (PROM1 / PROM2 IEBCOPY) | RC 0000; CLIST(PACMAN) installed |
JOB09460 compiled PACMAIN, PACGAME, PACINPT, PACDISP, PACPLAT, PACSCR, PACRT (PACGAME / PACINPT / PACRT source
unchanged) and reused the objects of PACMAP, PACAI, PACQRY, PACTSO, PACFSIO, PACHSIO. Spools in build/zos (gitignored).

Dry runs (comparator tools/zowe/zos6_dry.py, fail-closed; every step PACZ6D, CC 0000, model exact):
| Step | What | SYSOUT lines | Extra |
|---|---|---|---|
| E1 | EVERY batch RTSTILL = oracle 310 RTB7 | 251 | freeze runs [10, 10] |
| E2 | EVERY TSD RTSTILL = oracle 310 RTT2 | 557 | |
| N1 / F1 | COALESCED TSD RTSTILL with bells, NORMAL / FAST | 380 / 315 | |
| N2 / F2 | COALESCED TSD RTPAUSE | 217 / 211 | |
| N3 / F3 | COALESCED TSD RTPRE (INVALID message row) | 248 / 194 | |
| N4 / F4 | COALESCED TSD AI(2) GHOSTS(3) game over on a skipped quantum | 1181 / 872 | deciding quantum not presented |
| N5 / F5 | COALESCED TSD ARCADE RPCLRPU (tall canvas, popups) | 735 / 568 | |
| Z1 | FAST batch RTSTILL | 259 | freeze runs [12, 12] |

## Live acceptance (one session, ISPF option 6, c3270 `-model 2 -oversize auto`, 120 x 27 IBM-DYNAMIC)
| Case | Trace (raw, outside git) SHA-256 | Checker output | Verdict |
|---|---|---|---|
| R1-T4 NORMAL | e358d933b9906cad127f89e13df6b2297f9184386ee2381c1db2e98197761593 | zos6-r1-check.txt | PASS (rc 0) |
| R2 FAST | c72da2db1c0b0765e1dbf0e5f14fe7e3a722a5e653a660473c49087dd88d5109 | zos6-r2-check.txt | PASS (rc 0) |
Both: `AI(0) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO) PRESENT(COALESCED)` (+ `SPEED(FAST)` for R2), the approved
plans unchanged, TN3270E functions 00 / 02 / 04 / 05, profile (1, 1, 1), Query Reply = qreply_dyn, `***`, closure
ENTER and the ISPF Command Shell. Driver log SHA-256: R1-T4 5f36aa35...b45fb502, R2 4875c734...39c4f52c.

| Fact | R1-T4 NORMAL | R2 FAST |
|---|---|---|
| Logical quantum / stride / nominal presentation | 150 ms / 2 / 300 ms | 125 ms / 3 / 375 ms |
| Game writes = canonical model | 298 | 112 |
| Logical quanta | 589 | 329 |
| TSO CONTROL records `F1 C3` | 2 (after F8 start, F9 resume) | 1 (after PF11 start) |
| Death freeze | one, 10 quanta (model exact) | not exercised |
| Pause / resume | exact; post-resume not suspicious | not in the plan |
| Principal segment | 401 quanta / 201 frames, mean 150.155 ms | 241 quanta / 81 frames, mean 125.579 ms |
| Interval median (gate) | 302 ms (280-320) | 379.5 ms (345-405) |
| Interval p95 (gate) | 413 ms (<= 450) | 520 ms (<= 525) |
| Interval max (gate <= 1000) | 447 ms; 520 ms whole run | 577 ms; 584 ms whole run |
| Backlog delta (gate <= 100) | -1.0 ms | -16.5 ms |
| Input reactions | PF8 366, PF9 473, PF9 344, x 561, PA2 732, PF11 478, Q 606 | PF11 393, PF8 647, PF7 644, PF10 574, Q 558 |
| Reaction median (gate) / max (gate) | 478 (<= 750) / 732 (<= 1000) | 574 (<= 825) / 647 (<= 1075) |
| Freeze-span proxy (gate 1350-1650) | 1363 ms (quanta 536 -> 546) | not exercised |
| Live freeze discrimination | NOT OBSERVABLE (mutants 9 / 11 match; approved) | not exercised |
| Historical lateness envelope | rose 100 ms: diagnostic only | rose 139 ms: diagnostic only |
| End lines | QUIT, TURNS 024, SCORE 0230, LIVES 2, QUANTA 0000589 | QUIT, TURNS 018, SCORE 0090, LIVES 3, QUANTA 0000329 |
Every directional AID: planned == sent == TN3270E AID == model direction (R1 PF8 D, PF11 R; R2 PF11 R, PF8 D, PF7 U,
PF10 L). No stale replay, no catch-up burst, writes only on the approved presentation slots (R1 quanta 1, 3, 5, ...;
R2 1, 4, 7, ...; the resume quantum is the base). Margins (PASS, not tuned, no rerun - user decision): R1 freeze-span
proxy 13 ms above its lower bound, R2 p95 5 ms below its limit.

## Freeze proof split (approved 2026-10-19)
The exact logical freeze (10 quanta NORMAL, 12 FAST) is proved offline: PACRT unchanged and guarded (Z1 text,
FRZ-INIT), RTSTILL batch / TSD / model (dry-run E1 [10, 10], Z1 [12, 12]), and the moving-ghost fixture (10 PASS,
9 / 11 FAIL). Live R1 must match the canonical 10-quantum model and the freeze-span proxy; with AI(0) the 9 / 11
mutants are observationally identical, reported as NOT OBSERVABLE (neither PASS of the discrimination nor failure).

## Checker decisions taken during the live evaluation (user, 2026-10-19; no gate changed)
1. TSO CONTROL record: a bare host Write of exactly `F1 C3`, immediately after an inbound AID read by a blocking TGET
   (start, resume), after a host record with WCC C3, at most one per AID, confirmed by the model (the preceding write
   is not a game write), counted and reported, never a game or model write. Seen in R1-T3 (pre-ZOS-6 binary), R1-T4
   and R2; not in PACMAN's TSD streams; PACFSIO's blocking RECV issues no TPUT, so it is a TSO / VTAM record (the
   mechanism is an inference). Fixtures: blocking PASS; unrelated, duplicated, different and substituted FAIL.
2. Under PRESENT(COALESCED) the historical D33 lateness-envelope rule ("probable skipped period") is diagnostic only;
   under PRESENT(EVERY) it still blocks.
The original R1-T4 verdict (FUNCTIONAL FAIL, a checker false negative) is kept: zos6-r1-check-first-run.txt. R1-T4
was rechecked once on the unchanged frozen trace; no live test was rerun.

## Live attempts (raw traces kept outside git, read-only)
| Trace | SHA-256 | Classification |
|---|---|---|
| R1 | b543666a6f01f7bb549c1b18873e074e39643184e67c2a1fd8616944fb306f4c | first attempt (zos-5 binary, EVERY); no driver log; not acceptance evidence |
| R1-T2 | b56f1eaf452c8b1ce2ba341351dfcb082fcf4e85cf1cf84f284b5689fcc5cfd0 | ABORTED BEFORE GAME START: local driver / x3270if adapter defect; not functional evidence |
| R1-T3 | 11408477c0aad7de28960b5b1b155a3639e6e1096cb401f6bd055d93c8cc1a64 | PROTOCOL / INPUT BLOCKED (EVERY: no send window for PF9; docs/zos6-r1-t3-analysis.md); led to the probes and ZV-D33 |
| R1-T4 | e358d933b9906cad127f89e13df6b2297f9184386ee2381c1db2e98197761593 | ACCEPTED R1 (after the two checker decisions) |
| R2 | c72da2db1c0b0765e1dbf0e5f14fe7e3a722a5e653a660473c49087dd88d5109 | ACCEPTED R2 |
Probe traces (PR2 series): docs/zos6-protocol-probe.md.

## PRESENT default (user decision, 2026-10-19)
ZOS-6 live acceptance uses PRESENT(COALESCED): R1-T4 and R2 were both run with it explicitly. PRESENT(EVERY) (D33,
one write per quantum) stays the CLIST's compatibility / default path; the CLIST is not changed or reinstalled. The
release-default selection is deferred. ZOS-7 REALTIME / ARCADE live work must request PRESENT(COALESCED) explicitly.

## Not proved here (carried forward)
ARCADE live (ZOS-7); sound / alarm, live high score, ESTAE / PACFSIO C3 (E2) (ZOS-8); HA6 (ZOS-9/10); the release
default of PRESENT (the CLIST default stays EVERY = D33; COALESCED is requested explicitly); live freeze-length
discrimination (needs a moving-ghost live plan).
