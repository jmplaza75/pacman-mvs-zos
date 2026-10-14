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
