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
