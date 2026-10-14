# ZOS-2 Portable core - evidence
Plan: docs/ZOS-MIGRATION-PLAN.md sec. 6 (ZOS-2). Approved 2026-10-14: local tooling + Z2-1; Z2-2..Z2-4 architecture
only (full JCL + step/result matrix before each submission).

## Local tooling (commit b0c36cc)
- `make_deck.py --target zos` (tools/zowe/zos_target.py): MVS step builders replaced in-process only; run steps keep
  the MVS EXEC / PARM / cards / DDs (tests/test_zos_tools.py: 25 REL20 run steps compared).
- `zos_listing.py`: in-stream PROC definitions skipped, `++` expansions = <step> <procstep>.
- `zos_equiv.py`: run-by-run equality with tests/oracle20; framing removed = ASA column + record padding only; TK4-
  separator = exactly two empty lines (verified: 25/25 runs of JOBs 307 and 315, 4/4 of 308). Self-test: 25 runs
  simulated from the independent models = oracle 315; 9 mutations (space, case, digit, order, blank line, split at
  120, missing run, extra spool file, RC) all fail.
- R3 gate `tools/zowe/r3_gate.py`: 13 release decks = releases/2.0-MVS-MAX/SHA256SUMS; 94 MVS deck generations
  byte-identical to tag zos-1. PASS. test_g8 / test_mvs8 / test_core_frozen / oracle verify PASS.

## Z2-1 PACZ2CMP (JOB08497) - diagnostic compile inventory
Deck jcl/zos/PACZ2CMP.jcl (= `make_deck.py --target zos ZCMP`), as approved: in-stream PROCs CBL / ASM, profile A
COBOL options + NOSOURCE,NOXREF, no COND, no bind, no run. Precheck (read-only): the 21 compiled members downloaded in
binary = local IBM-037 fixed-80 records (12 COBOL, 6 COPY, 3 ASM). Submitted once; spool kept (not purged);
analysis `tools/zowe/zos_compile_report.py` (message counts reconcile with every compiler 'Printed:' total).

| Step | Program | RC | Diagnostics |
|---|---|---|---|
| PACMAIN | IGYCRCTL | 0012 | E 6, S 90 (C2) |
| PACGAME | IGYCRCTL | 0012 | W 3, E 8, S 17 (C2) |
| PACMAP | IGYCRCTL | 0012 | W 2, E 4, S 2 (C2) |
| PACAI | IGYCRCTL | 0012 | W 2, E 6, S 8 (C2) |
| PACINPT | IGYCRCTL | 0012 | W 1, E 2, S 3 (C2) |
| PACDISP | IGYCRCTL | 0012 | W 3, E 8, S 47 (C2) |
| PACPLAT | IGYCRCTL | 0012 | W 2, E 4, S 2 (C2) |
| PACSCR | IGYCRCTL | 0012 | W 4, E 10, S 4 (C2) |
| PACQRY | IGYCRCTL | 0000 | none (C1 VALIDATE not confirmed) |
| PACRT | IGYCRCTL | 0012 | W 3, E 8, S 11 (C2) |
| PACQRYT | IGYCRCTL | 0000 | none |
| PACTSOT | IGYCRCTL | 0000 | none |
| PACTSO | ASMA90 | 0000 | none |
| PACFSIO | ASMA90 | 0004 | ASMA303W (C3, benign: `S 12,ABOFF` -> 5BC0 F014, base R15) |
| PACHSIO | ASMA90 | S722 | incomplete: job cancelled at the site output limit ($HASP375 ESTIMATED LINES EXCEEDED, 5,035 records) while printing statement 1178 (IHASDWA expansion); no diagnostic before that point |

C2 proof: in every failing module the set of names quoted by the messages equals the set of `01 <name> COPY <member>`
items of that module, each member's own first entry is `01 <name>.`, and the message codes are only IGYDS1159,
IGYDS1082, IGYSC2025, IGYPS0037. The modules without such a COPY (PACQRY, PACQRYT, PACTSOT) compile with no message.
Core (PACGAME, PACMAP, PACAI, PACRT): only C2; no other diagnostic.

Status after Z2-1: stopped for the user's decisions (C2 resolution, C3 acceptance, PACHSIO re-assembly, output limit
for Z2-2..Z2-4). No source changed by Z2-1.

## Decisions and Z1 (2026-10-14)
- C1 disproved, closed. C3 accepted provisionally (docs/ZOS-DIFFS.md). C2 -> Z1: 28 substitutions on branch zos.
- Guards: tests/zos_c2.py PASS (28 substitutions in 9 sources; copybooks and all other src = 2.0-mvs-max; negative
  checks: an extra edit in PACAI and an edit of a copybook both fail); test_core_frozen PASS with the explicit Z1
  allowance (PACGAME, PACMAP, PACAI; the same two negative checks fail); test_g8, test_mvs8, validate_source PASS;
  R3 gate PASS (13 release files, 13 regenerations with the current tools on the 2.0-mvs-max sources, 94 generator
  comparisons with zos-1, 26 source-carrying decks of the zos tree differ only by Z1 lines).
- Line budget: no LINES=; ZOS-2 jobs = CHUNKS of tools/zowe/zos_target.py, matrix tools/zowe/zos_plan.py.

## Z1 upload (2026-10-14)
The 9 Z1 members (PACAI, PACDISP, PACGAME, PACINPT, PACMAIN, PACMAP, PACPLAT, PACRT, PACSCR) uploaded to
Z00000.PACMAN.COBOL with IBM-037 and verified by binary round trip against the zos-branch sources (fixed 80): 9/9
identical. Read-only check of every other source member (COBOL PACHELLO / PACQRY / PACQRYT / PACTSOT, 6 COPY, 3 ASM,
CLIST): 14/14 unchanged. No delete, no purge.

## Z2-1b PACZ2HSA (JOB08810) - PACHSIO completion
Deck jcl/zos/PACZ2HSA.jcl (= `make_deck.py --target zos ZHSA`), submitted once, spool kept. CC 0000, no JES / output
limit message; 449 spool lines (SYSPRINT 400). HLASM summary: `266 Primary Input Records Read` (= src/asm/PACHSIO.asm,
266 lines), statement 2832 = the source `END` (line 266) listed, `No Statements Flagged in this Assembly`,
`32 Object Records Written`, `Return Code 000`; options PCONTROL(NOGEN) etc. as overriding parameters. No ASMA
diagnostic at all. Z00000.PACMAN.OBJ(PACHSIO) present. Result: clean PASS (RC 0).
Note: OBJ also holds the members written by the RC 12 compiles of Z2-1 (not usable); PACZ2BLD replaces every one of
them before any bind.

## Z2-2 PACZ2BLD (JOB08888) - build of LOAD(PACZ2D), profile A
Deck jcl/zos/PACZ2BLD.jcl (= `make_deck.py --target zos Z2BLD`; binder options LIST,AMODE=24,RMODE=24,RENT, MAP removed
by the user), submitted once, spool kept. Job CC 0004 (= PACFSIO C3). 3,266 spool lines in total (estimate ~3,800 with
MAP). No abend, no CEE message, no step skipped.
| Step | Program | RC | Result |
|---|---|---|---|
| COB1..COB10 (PACMAIN, PACGAME, PACMAP, PACAI, PACINPT, PACDISP, PACPLAT, PACSCR, PACQRY, PACRT) | IGYCRCTL | 0000 each | "no statements flagged", no IGY message; options in effect RENT, RMODE(24), DATA(24), NODYNAM, TRUNC(STD), NUMPROC(NOPFD) |
| ASM1 PACTSO | ASMA90 | 0000 | 109 input records, no statement flagged |
| ASM2 PACFSIO | ASMA90 | 0004 | 216 input records; 1 statement flagged: ASMA303W on stmt 343 `USING ABEXIT,15` vs stmt 38 (+ its ASMA435I record locator, record 196); `S 12,ABOFF` = 5BC0 F014 (base R15). Exactly C3 |
| ASM3 PACHSIO | ASMA90 | 0000 | 266 input records, no statement flagged |
| LINK | IEWBLINK | 0000 | IEW2278I `LIST,AMODE=24,RMODE=24,RENT`; 13 INCLUDE, ENTRY PACMAIN, NAME PACZ2D(R); SAVE: PACZ2D in Z00000.PACMAN.LOAD, PROGRAM OBJECT(FORMAT 3), ADDED NEW; SAVE MODULE ATTRIBUTES AMODE 24, RMODE 24, RENT YES, REUS YES, EXCEEDS 16MB NO, module size X'200B0'; entry PACMAIN MAIN_EP AMODE 24; IEW2008I RETURN CODE 0; message summary: severity 4/8/12/16 NONE |
Every object bound was rewritten by this job (COB1..ASM3) before LINK. LOAD now holds PACHELLO, PACZ2D, ZHELLO24,
ZHELLO31 (no PACMAIN). Result: PASS for the build; no execution submitted (AMODE 24 at run time is proven only by the
run jobs).
Tool fix: tools/zowe/zos_compile_report.py did not list HLASM messages whose carriage-control column holds a machine
control character (U+008D); the ASMA pattern now accepts any first column. Z2-1 report re-run: PACFSIO shows the same
ASMA303W + ASMA435I.

## Z2-2 PACZ2C1 (JOB08984) - first execution of PACZ2D: CLASSIC oracle RUN1..RUN5
Deck jcl/zos/PACZ2C1.jcl (= `make_deck.py --target zos Z2C1`), approved as presented, submitted once, spool kept.
Job CC 0000; spool 3,586 lines (estimate ~3,560): JESMSGLG 22, JESJCL 38, JESYSMSG 101, SYSOUT 3,425. Spool files:
only the JES files and one SYSOUT (FBA 121) per step; no CEEDUMP, no CEE / abend / $HASP375 message, no step skipped.
Each step: `EXEC PGM=PACZ2D`, STEPLIB `Z00000.PACMAN.LOAD` (IGD103I / IGD104I), CEEOPTS ALL31(OFF),STACK(,,BELOW).
| Step | Case | RC | SYSOUT lines | zos_equiv vs oracle 307 | = model |
|---|---|---|---|---|---|
| RUN1 | MOVES | 0000 | 160 | identical, stream 9780-9939 | MVS6-MOVES |
| RUN2 | RAND | 0000 | 643 | identical, stream 9942-10584 | MVS6-RAND |
| RUN3 | CATCH1 | 0000 | 302 | identical, stream 10587-10888 | MVS6-CATCH1 |
| RUN4 | WIN0 | 0000 | 2029 | identical, stream 10891-12919 | MVS6-WIN0 |
| RUN5 | CATCH0 | 0000 | 291 | identical, stream 12922-13212 | MVS6-CATCH0 |
`zos_equiv.py ... 307-PACREL20.json.gz --map PACMAIN=PACZ2D --subset`: 5 runs identical, 0 failures, PASS (20 oracle
runs not in this job). Framing removed: ASA column and record padding only; maximum line 60 characters. First
evidence that the full Pac-Man program object runs under profile A (AMODE 24, RMODE 24, LE ALL31(OFF), stack below)
with output identical to 2.0-mvs-max for these five deterministic CLASSIC games.
Scope (user, 2026-10-14): JOB08984 is the first successful execution proof of PACZ2D on z/OS; it covers these five
deterministic CLASSIC cases only and is not generalised beyond them.

## Z2-2 PACZ2C2 (JOB09000) - CLASSIC oracle RUN6..RUN8
Deck jcl/zos/PACZ2C2.jcl, approved as presented, submitted once, spool kept. Job CC 0000; spool 3,532 lines (estimate
~3,540): JESMSGLG 20, JESJCL 24, JESYSMSG 63, SYSOUT 3,425. Spool files: the JES files and one SYSOUT (FBA 121) per
step; no CEEDUMP, no CEE / abend / $HASP375 message, no step skipped; each step `EXEC PGM=PACZ2D`, STEPLIB
Z00000.PACMAN.LOAD (IGD104I), CEEOPTS ALL31(OFF),STACK(,,BELOW).
| Step | Case | RC | SYSOUT lines | zos_equiv vs oracle 307 | = model |
|---|---|---|---|---|---|
| RUN6 | DIE1 | 0000 | 324 | identical, stream 13215-13538 | MVS6-DIE1 |
| RUN7 | LOST0 | 0000 | 808 | identical, stream 13541-14348 | MVS6-LOST0 |
| RUN8 | WINAFTER | 0000 | 2293 | identical, stream 14351-16643 | MVS6-WINAFTER |
`zos_equiv --subset`: 3 runs identical, 0 failures, PASS (22 oracle runs not in this job). Maximum line 60.
Scope: these three deterministic CLASSIC cases (death, game lost, death then win).

## Z2-2 PACZ2C3 (JOB09015) - CLASSIC oracle RUN9
Deck jcl/zos/PACZ2C3.jcl, approved as presented, submitted once, spool kept. Job CC 0000; spool 839 lines (estimate
~840): JESMSGLG 18, JESJCL 10, JESYSMSG 25, SYSOUT 786. Spool files: the JES files and one SYSOUT (FBA 121); no
CEEDUMP, no CEE / abend / $HASP375 message; the step executed (IEF142I COND CODE 0000), `EXEC PGM=PACZ2D`, STEPLIB
Z00000.PACMAN.LOAD (IGD104I), CEEOPTS ALL31(OFF),STACK(,,BELOW).
| Step | Case | RC | SYSOUT lines | zos_equiv vs oracle 307 | = model |
|---|---|---|---|---|---|
| RUN9 | LOST1 | 0000 | 786 | identical, stream 16646-17431 | MVS6-LOST1 |
`zos_equiv --subset`: 1 run identical, 0 failures, PASS (24 oracle runs not in this job). Maximum line 60.
Scope: this deterministic CLASSIC case (default chasing ghost, game lost). CLASSIC oracle so far: RUN1..RUN9.

## Z2-2 PACZ2C4 (JOB09023) - CLASSIC oracle RUN10 (EDGE3, D11 edge case)
Deck jcl/zos/PACZ2C4.jcl, approved as presented, submitted once, spool kept. Job CC 0000; spool 3,578 lines (estimate
~3,580): JESMSGLG 18, JESJCL 10, JESYSMSG 25, SYSOUT 3,525. Spool files: the JES files and one SYSOUT (FBA 121); no
CEEDUMP, no CEE / abend / $HASP375 message; the step executed (IEF142I COND CODE 0000), `EXEC PGM=PACZ2D`, STEPLIB
Z00000.PACMAN.LOAD (IGD104I), CEEOPTS ALL31(OFF),STACK(,,BELOW).
| Step | Case | RC | SYSOUT lines | zos_equiv vs oracle 307 | = model |
|---|---|---|---|---|---|
| RUN10 | EDGE3 | 0000 | 3525 | identical, stream 17434-20958 | MVS6-EDGE3 |
Last tick `T319 R DIED    X=02 Y=02 S=1000 L=000 G=19,09 V=2 ST=WON`; end lines WIN / TURNS 319 / SCORE 1000 /
LIVES 2 (D11: the hit beats the simultaneous last pellet; lives remain and no pellet is left, so the game is WON).
`zos_equiv --subset`: 1 run identical, 0 failures, PASS. Maximum line 60. CLASSIC oracle so far: RUN1..RUN10.

## Z2-2 PACZ2C5..C7 (user batch approval) and the complete CLASSIC oracle
Each deck = its generated reference (tests/test_zos_tools.py) and passed tools/zowe/zos_run_precheck.py before
submission (audit, only dataset STEPLIB Z00000.PACMAN.LOAD, no DELETE, every step EXEC PGM=PACZ2D, CEEOPTS
ALL31(OFF),STACK(,,BELOW), estimate < 4,000). Submitted once each, in order, spool kept. Checked with
tools/zowe/zos_classic_check.py: spool health (IEF142I COND CODE 0000 per step, IGD104I STEPLIB per step, no CEE /
abend / $HASP375 / IEA995, only one SYSOUT per step), zos_equiv --subset vs oracle 307, and the runtime checks of
tests/test_mvs8.py (batch = MVS6 model + behaviour rules; TSO = batch reference without prompts, board before the
first prompt, one prompt per read, no DBG line).
| Job | JOBID | Steps / cases | RC | SYSOUT lines | Spool lines | Oracle 307 | Models |
|---|---|---|---|---|---|---|---|
| PACZ2C5 | JOB09027 | RUN11 EDGE2, RUN12 EDGE1 | 0000 each | 1688, 1809 | 3,577 | identical | MVS6 = |
| PACZ2C6 | JOB09030 | RUN13 P2, RUN14 P2N3, RUN15 R1N2, RUN16 C3WALK | 0000 each | 885, 785, 845, 764 | 3,413 | identical | MVS6 = |
| PACZ2C7 | JOB09031 | RUN17 C3, RUN18 C3N2, RUN19 MULTI, TSO1 MOVES, TSO2 DIE1, TSO3 P2, TSO4 MULTI, TSO5 C3N2, TSO6 TSORDR | 0000 each | 940, 269, 233, 175, 353, 965, 252, 290, 53 | 3,799 | identical | MVS6 / TSO transcript = |
Combined CLASSIC validation over JOB08984, JOB09000, JOB09015, JOB09023, JOB09027, JOB09030, JOB09031
(docs/evidence/zos2-classic-check.txt): the 25 runs RUN1..RUN19 + TSO1..TSO6 present exactly once, in oracle order;
every run identical to oracle 307 and to its independent model; the 19 batch runs also identical to the MVS-7
before/after evidence (docs/evidence/mvs7-refactor.txt): CLASSIC CHECK PASS. The 1.0-MVS functional oracle
(19 batch + 6 TSO line-mode replays) is reproduced exactly on z/OS by PACZ2D under profile A. Not covered by these
jobs: the REL20 CLIST PARM steps (CLIST out of ZOS-2), ARCADE / REALTIME / RP / S2 / STORAGE (later ZOS-2 jobs).

## Z2-4 PACZ2G1 (JOB09069) - ARCADE representative subset (oracle 310)
Deck jcl/zos/PACZ2G1.jcl (commit 4c0bd92), approved as reviewed, submitted once, spool kept. Job CC 0000; spool 3,268
lines (estimate ~3,280): JESMSGLG 27, JESJCL 73, JESYSMSG 196, SYSOUT 2,972. `tools/zowe/zos_arcade_check.py`:
spool health (IEF142I COND CODE 0000 for all 10 steps, STEPLIB Z00000.PACMAN.LOAD per step, no CEE / abend /
$HASP375, one SYSOUT per step), zos_equiv --subset vs oracle 310, independent model tests/ref_gp2.py as in
tests/test_gp2.py: ARCADE CHECK PASS.
| Step | Case / PARM level | RC | SYSOUT | Oracle 310 own block | ref_gp2 | Observed in the z/OS output |
|---|---|---|---|---|---|---|
| G2B1 | GPAI0 `AI0 3` | 0000 | 738 | 60064-60801 = | = | AI=0, 3 ghosts (L=098 at T000, M=N000 N000 N000); 4 power pellets FR=020; QUIT 51 turns, SCORE 0001310, GHOSTS EATEN 0003 |
| G2B2 | GPHOME `AI0 2` | 0000 | 332 | 60804-61135 = | = | AI=0, 2 ghosts (L=099); 2 power pellets; T019 DIED; LIVES 2, GHOSTS EATEN 0001 |
| G2B9 | GPPOW2 `AI1 1` | 0000 | 101 | 66104-66204 = | = | second power pellet during the fright: FR back to 020 (refresh); ghost F at the end |
| G2B12 | GPTIE `AI2 1` | 0000 | 127 | 67007-67133 = | = | power FR=020, frightened flee with a direction tie (model event flee-tie; order U D L R) |
| G2B21 | G2BDIE `AI1 1` | 0000 | 413 | 75169-75581 = | = | death with the fruit shown (model event deathfruit): T030 DIED, L line BN=1 EV=A---D; LIVES 2 |
| G2B33 | G2ROW `01` | 0000 | 205 | 101009-101213 = | = | LEVEL 001, L LV=001 AI=1, power FR=020 |
| G2B45 | G2ROW `13` | 0000 | 205 | 103493-103697 = | = | LEVEL 013, L LV=013 AI=3 (AI1 + bump 2) BK=K BV=5000, power FR=004 (row 13 fright) |
| G2B49 | G2ROW `ab` | 0000 | 205 | 104321-104525 = | = | invalid start -> LEVEL 001; output identical to G2B33, different from G2B45 |
| G2B55 | MULTI `AI3 3`, `05` | 0000 | 276 | 106096-106371 = | = | LEVEL 005, L LV=005 AI=3 BK=A BV=0700, 3 ghosts (L=098); T014 DIED; EOF, LIVES 2 |
| G2T1 | GPTSO, PARM `TSO AI0 2 ... A` | 0000 | 370 | 111310-111679 = | = | TSO line-mode ARCADE, 2 ghosts (L=099), 24 prompts, blank-card redraw; same game as GPHOME |
Tool note: zos_equiv --subset printed 103700-103904 for G2B49: oracle steps G2B46..G2B49 (start '', '  ', '00', 'ab',
all level 1) print the same 205-line block and the subset search reports the first identical block. A separate
read-only check located every step at its own oracle block (table above): all 10 identical, each with its exact
separator. Not a divergence; a tool improvement (anchor each subset step at its own oracle block) is proposed.

## Tool correction: zos_equiv --subset anchored at each step's own oracle block (2026-10-14, after G1)
Problem (found on JOB09069): in subset mode each z/OS step was located by searching the oracle stream for its content;
oracle 310 G2B46..G2B49 (start '', '  ', '00', 'ab', all level 1) print the same 205-line block, so G2B49 was reported
at G2B46's block (103700) instead of its own (104321). Content was identical either way; the attribution was wrong.
Change (tools/zowe/zos_equiv.py, subset mode only; normalisation unchanged: ASA column + record padding only):
- anchors(oracle, programs): the z/OS step name selects the unique entry of oracle['steps']; its ordinal among the
  oracle's run steps selects the run dataset of the stream (a block after the TK4- two-line separator whose first line
  is a run header). Program and deck PARM (TSD or not) are consistency checks of the header only. A duplicated oracle
  step name, an inconsistent header (that step and every later one) or a stream whose run-dataset count differs from
  the run-step count leaves the step unanchored -> FAIL "cannot be anchored"; no fallback to a content search.
- ends_ok: the block must end where the oracle's next dataset begins (the next run step's own block, else a separator,
  a page eject or the end of the stream); z/OS steps must appear in oracle order; a duplicated z/OS step name fails.
- Full (non-subset) mode untouched: old and new compare() give identical results on the passing simulated job and its
  7 mutations.
Regression (tests/test_zos_tools.py section 6, PASS): G2B46..G2B49 model outputs each anchored at its own block
(G2B49 = 104321-104525, structurally = G2B45 + 4 x 207); a one-character mutation of G2B48 fails G2B48 only; a
truncated G2B49, a wrong order and a level-1 output given to G2B45 fail; a duplicated oracle step name and oracle 309
are not anchorable. Existing sections (CLASSIC subset chunks, full-mode mutations) unchanged and PASS.
Re-processing of the downloaded evidence (no z/OS job): JOB09069 10/10 PASS with G2B49 at 104321-104525 (own block);
a one-character mutation of G2B49 in a scratch copy fails G2B49 at its own block (block line 186), the 9 others OK;
C1..C7 (zos_classic_check --all) PASS with a report byte-identical to docs/evidence/zos2-classic-check.txt.
Finding for a later job: oracle 309 (RP) holds 80 run datasets for 81 PACMAIN run steps (RPT1's TSD output follows
the IEBUPDTE listing after one empty line, not the two-line separator), so no 309 step can be anchored: PACZ2RP as
designed would fail "cannot be anchored" until this is resolved (to be proposed separately; no oracle change).

## Z2-4 PACZ2G2 (JOB09114) - REALTIME, CLASSIC and ARCADE (oracle 310)
Deck jcl/zos/PACZ2G2.jcl (commit 9e3075a: S1S2 removed by the user as redundant with RTB7), local checks PASS (deck =
generated, precheck, 8/8 model = own anchored oracle block, estimate ~2,405), submitted once, spool kept. Job CC 0000;
spool 2,387 lines: JESMSGLG 25, JESJCL 59, JESYSMSG 158, SYSOUT 2,145. `zos_arcade_check.py`: all 8 steps IEF142I
COND CODE 0000, STEPLIB Z00000.PACMAN.LOAD, no CEE / abend / $HASP375, one SYSOUT each; every step anchored at its own
oracle 310 block and identical; ref_rt (RTB) / ref_gp2.rt_simulate (G2R) identical: ARCADE CHECK PASS.
| Step | Case | RC | SYSOUT | Own 310 block | Observed in the z/OS output |
|---|---|---|---|---|---|
| RTB1 | RTLINE `AI0 1` | 0000 | 41 | 38858-38898 | cadence K = P B B B B P B then ghost-only G G G - G; X=09 at Q7 and Q12; EOF, 12 quanta |
| RTB7 | RTSTILL `AI3 1` | 0000 | 251 | 39072-39322 | hit while stationary at Q27 (K=G, X=02 Y=02 respawn), 10 freeze quanta K=F then play; LOST, 117 quanta |
| RTB8 | RTPAUSE `AI1 1` | 0000 | 42 | 39325-39366 | IN=PxP (pause, invalid x, resume), INVALID COMMAND x, IN=* (PA2 redraw), IN=PP; QUIT |
| RTB10 | RTWIN `AI0 1` | 0000 | 383 | 41592-41974 | WIN, TURNS 183, SCORE 1000, LIVES 3, 183 quanta |
| RTB11 | RTEDGE `AI1 1` | 0000 | 335 | 41977-42311 | D11 in REALTIME: L=001 then L=000 with the hit in the same quantum, ST=WON, LIVES 1 |
| G2R1 | RTGPA `AI3 3` ARCADE | 0000 | 213 | 107426-107638 | 3 ghosts (L=098, M=N000 N000 N000), fright FR=040 counting down per quantum with FA accumulator (2/5 cadence), 2 ghosts eaten (P=0200, P=0400, EV=GHST), death at Q47 (EV=----D); LIVES 2 |
| G2R5 | RTMULTI `AI0 1` ARCADE | 0000 | 56 | 108497-108552 | several inputs in one quantum: IN=DL, IN=UDLR (the latest wins); 8 quanta |
| G2R7 | G2RCLR `AI0` ARCADE | 0000 | 824 | 108630-109453 | fruit appears (EV=A, BT=060) and is eaten (EV=-F---, FRUITS EATEN 001); 5 power pellets; level clear at Q183 (EV=---C-), L LV=002 BK=S BV=0300, board reloaded (L=100, PW=4), freeze quanta K=F; end LEVEL 002, SCORE 0001350 |
Not covered here: the real clock (PACTSO TIME / DLWT) is in PACZ2DRV (TSOT1); sound / alarm have later ZOS-2 coverage.

## Z2-4 PACZ2G3 (JOB09128) - ARCADE level clear in TURN, start level through the TSO PARM (oracle 310)
Deck jcl/zos/PACZ2G3.jcl (commit 6f52ffd; S1S3 left out: its oracle 310 block is byte-identical to the 307 TSO2 DIE1
block already PASS in C7), approved as presented, submitted once, spool kept. Job CC 0000; spool 2,943 lines
(estimate ~2,970): JESMSGLG 19, JESJCL 17, JESYSMSG 44, SYSOUT 2,863. `zos_arcade_check.py`: both steps IEF142I COND
CODE 0000, STEPLIB Z00000.PACMAN.LOAD, no CEE / abend / $HASP375, one SYSOUT each; anchored at their own oracle 310
blocks and identical; ref_gp2 identical: ARCADE CHECK PASS.
| Step | Case | RC | SYSOUT | Own 310 block | Observed in the z/OS output |
|---|---|---|---|---|---|
| G2B19 | G2CLR `AI0`, TURN | 0000 | 2493 | 70270-72762 | LEVEL 001; fruits appear at 30 and 70 items (EV=A----, BT=030); the first is eaten (EV=-F---, FRUITS EATEN 001), the second expires (BT 001 -> 000 at IT=089 without F); power pellets FR=020, a second power during the fright refreshes FR=017 -> 020 (twice); level clear T183 CLEARED (EV=---C-) -> L LV=002 BK=S BV=0300, board reloaded (T184 L=099 after a full board, pellets back on the rows); level-2 power FR=017; end QUIT, TURNS 0000190, SCORE 0001370, LEVEL 002 |
| G2T3 | GPTSO, PARM `TSO AI0 2 ... A03` | 0000 | 370 | 112474-112843 | TSO line mode, 2 ghosts (L=099 at T000); start level 03 from the PARM: LEVEL 003, L LV=003 AI=0 (AI0 invariant under the +1 bump) BK=O BV=0500; power FR=014; 1 ghost eaten (EV=GHST); T019 DIED; 24 prompts; blank card = redraw (T003 shown twice); end QUIT, LIVES 2, LEVEL 003 |

## Z2-4 PACZ2DRV (JOB09164) - QRY1 capability parsing and TSOT1 real clock
Deck jcl/zos/PACZ2DRV.jcl (commit f6ba545): COBQ2 / ASMT removed by the user, so LINKQ / LINKT bind the reference-build
objects of JOB08888. Read-only proof before submission: no job submitted after JOB08888 references PACMAN.OBJ;
OBJ(PACQRY) carries the compile timestamp 20261014113044 = JOB08888 COB9 (11:30:44; Z2-1 compiled at 09:48:58);
OBJ(PACTSO) = 10 records (= "10 Object Records Written" of JOB08888 ASM1), END IDR date 2026-287, and its 424 TXT
bytes equal the assembled code of the source (359 bytes listed by Z2-1, 321 by JOB08888, 0 differences; the other
65 bytes are the SAVE 18F'0' remainder and T0SET X'00', all zero). Local: precheck PASS, QRY1 model = own oracle
block, TSOT1 oracle block satisfies RT3, estimate ~800.
Submitted once, spool kept. Job CC 0000; spool 880 lines (JESMSGLG 23, JESJCL 84, JESYSMSG 232, SYSPRINT 470, SYSOUT
71). All 6 steps IEF142I COND CODE 0000; no CEE / abend / $HASP375; only SYSPRINT (build) / SYSOUT (run) spool.
| Step | RC | Result |
|---|---|---|
| COBQ1 (PACQRYT) | 0000 | no IGY message |
| LINKQ | 0000 | LIST,AMODE=24,RMODE=24,RENT; INCLUDE OBJ(PACQRYT) + OBJ(PACQRY); PACQRYT program object FORMAT 3, AMODE 24, RMODE 24, RENT YES, MAIN_EP PACQRYT; severity 4/8/12/16 NONE |
| QRY1 (PACQRYT) | 0000 | STEPLIB Z00000.PACMAN.LOAD; 50 lines = own oracle 310 block 38512-38561 and = qry_cases model (20 QRY lines with C/H/GE/AW/AH, 29 QSL startup sequences, QRY TEST END) |
| COBT (PACTSOT) | 0000 | no IGY message |
| LINKT | 0000 | INCLUDE OBJ(PACTSOT) + OBJ(PACTSO); PACTSOT FORMAT 3, AMODE 24, RMODE 24, RENT YES, MAIN_EP PACTSOT; severity 4/8/12/16 NONE |
| TSOT1 (PACTSOT) | 0000 | STEPLIB Z00000.PACMAN.LOAD; 21 TSOT lines, RT3 rules PASS: 20 deadlines RC 0, lateness 0 ms (one 1 ms at #18), intervals 149-151 ms, LA (deadline 2900, already passed) RC 4 at 3000 = 0 ms after #20 |
First z/OS execution of PACTSO's STCK / STIMER WAIT path (the game's batch REALTIME runs use simulated quanta; CLOK /
WDLN reach PACTSO only in TSC). Host timing only; no terminal / TN3270 involved.

## Site retention of job output (observed 2026-10-14)
A read-only job listing after G3 shows only JOB09069 (G1), JOB09114 (G2), JOB09128 (G3) of the ZOS-2 jobs; z/OSMF
returns "Zero jobs were returned" for JOB08497, JOB08888, JOB08984, JOB09031: the site's retention removed them (no
purge by this project, D44). The complete spool of every job is kept locally under build/zos/<JOBNAME>-<JOBID>/
(downloaded right after each job), but build/ is git-ignored. Also listed: JOB08863 CXZ00000 (class C4Z, ACTIVE) and
TSU09158, not submitted by this project, left untouched.
