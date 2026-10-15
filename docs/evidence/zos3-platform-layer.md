# ZOS-3 platform layer - evidence

Design: docs/zos3-design.md (approved 2026-10-15). Load module: PACZ2D of PACZ2BLD JOB08888 (not rebuilt). Source not
modified. Raw spool: docs/evidence/zos3-spool/ (deterministic archives, SHA256SUMS, MANIFEST.txt).

## PACZ3FS JOB01362 - PACFSIO batch contract: PASS

Deck of record jcl/zos/PACZ3FS.jcl, submitted once, unchanged (deck.jcl as submitted = the reviewed rendering, SHA-256
7133666bae82b0564fb4f1a86ccccf4616d1249748f2a04a5ac1916dfb4824fa). Check: tools/zowe/zos_fs_check.py
(output: docs/evidence/zos3-fs-check.txt).

| Criterion | Result |
|---|---|
| S1S3 `PARM='TSO AI0    AAAPAAAAY'` (deck GP2) | COND CODE 0000 |
| S2L4 `PARM='TSO AI0    AAAPAAAAYC01NP'` (deck S2) | COND CODE 0000 |
| Program / STEPLIB | PGM=PACZ2D, IGD104I Z00000.PACMAN.LOAD RETAINED DDNAME=STEPLIB once per step |
| CEEOPTS | exactly `ALL31(OFF),STACK(,,BELOW)` in each step (deck as submitted) |
| Application SYSOUT | 353 lines each |
| Anchoring | S1S3 = oracle 310 run step 195/195 (stream lines 59707-60059); S2L4 = oracle 308 run step 29/29 (stream lines 22758-23110); unique step identity + ordinal, block ends where the oracle's next dataset begins |
| Oracle | exact (ASA column and record padding only) |
| Reference models | = 1.0-MVS oracle TSO DIE1 (tests/test_g0.py, as tests/test_s1.py / test_s2.py) and = the tests/test_mvs8.py TSO line-mode model DIE1 |
| Previously accepted z/OS output | each step byte-identical to PACZ2C7 JOB09031 TSO2 (DIE1 without COLOR) |
| Data stream | no TSD / TSX line |
| Diagnostics | no CEE message, no abend, no IEA995 / S722 / $HASP375; CEEDUMP allocated, empty (no spool dataset) |
| Spool datasets | JESMSGLG, JESJCL, JESYSMSG, S1S3 SYSOUT, S2L4 SYSOUT only (786 lines) |
| Linkage | PACZ2D bind (JOB08888): OBJ(PACPLAT) + OBJ(PACFSIO) included, RC 0, nothing unresolved |

PACFSIO conclusion (recorded as approved by the user):
PACZ3FS dynamically validates entry through the PACPLAT/PACFSIO batch fallback path and clean line-mode fallback.
FSON RC=4 is established from the verified PACFSIO control flow under the independently established no-TSB batch
condition; this job does not directly emit or independently observe that RC.

The SYSOUT alone does not prove that FSON returned 4: an FSON RC 0 in batch would lead to SENX RC 4 and the same
fall-back, with the same transcript. No PACFSIO test driver was added (user decision 2026-10-15).
