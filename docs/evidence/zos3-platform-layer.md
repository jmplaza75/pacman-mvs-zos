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

## PACZ3HA JOB02091 - HS test PDSs, attempt T1: PASS (after a checker fix; see the audit note)

Deck of record jcl/zos/PACZ3HA.jcl, submitted once, unchanged (deck.jcl as submitted = the reviewed rendering, SHA-256
f620505dad30f55d3ab776d7d585267ae44ac0ef95980efa7cb175e0d7eb7e20). Read-only catalog query immediately before the
submission: neither Z00000.PACMAN.HSTEST.T1 nor Z00000.PACMAN.HSFULL.T1 (nor any Z00000.PACMAN.HS*) existed.
Job CC 0012 = the expected HSFILL RC; not a failure by itself.

| Step | Expected | Actual |
|---|---|---|
| ALLOC (IEFBR14) | 0000 | 0000 |
| HSSEED1 / HSSEED2 / HSSEED3 (IEBGENER) | 0000 | 0000 / 0000 / 0000 |
| HSFILL (IEBUPDTE NEW) | 0012 | 0012: IEB817I stowed M01..M20, `IEB813I OUTPUT DIRECTORY FULL` right after `ADD NAME=M21`, nothing stowed after it, IEB818I highest CC 12 |
| HSLIST (IKJEFT01 LISTDS, read-only) | 0000 | 0000 |

No abend, IEA995, S722 or $HASP375; spool DDs only SYSPRINT of HSSEED1..3 / HSFILL and SYSTSPRT of HSLIST; the only
Z00000 datasets named in JESYSMSG (besides the job's own JES datasets) are the two T1 PDSs.

Actual state after the job (read-only z/OSMF queries, 2026-10-15; the datasets were not modified afterwards):

| Dataset | Catalog | DSNTYPE / DSORG | RECFM / LRECL / BLKSIZE | Volume | Members |
|---|---|---|---|---|---|
| Z00000.PACMAN.HSTEST.T1 | CATALOG.ZOSO, created 2026/10/15, 1 extent, not migrated | PDS / PO | FB / 80 / 80 | ZXPC02 | BAD, EMPTY, HS9 |
| Z00000.PACMAN.HSFULL.T1 | CATALOG.ZOSO, created 2026/10/15, 1 extent, not migrated | PDS / PO | FB / 80 / 80 | ZXPL01 | M01..M20 (HISCORE, M21..M30 absent) |

Member contents (z/OSMF view): HS9 = `9999999 PACHS001 099` (1 record); BAD = `XYZZY NOT A SCORE`,
`SECOND JUNK RECORD` (2 records); EMPTY = no record. TSO LISTDS in the job shows the same attributes and members.
z/OSMF reports the space in KILOBYTES (size 103, used 1) and not the directory block count: HSFULL's single full
directory block is established by IEB813I at M21 (20 entries + the end marker fill one 256-byte block, as in oracle
312).

Audit note (both facts kept): the FIRST checker run (docs/evidence/zos3-ha-check-first-run.txt) reported one FAIL,
"LISTDS Z00000.PACMAN.HSFULL.T1": a false FAIL of the checker, not of the job or of the datasets. Its LISTDS parser did
not close the member list at the READY that ends the last LISTDS command, so the final IKJEFT01 `END` control line
was parsed as a 21st HSFULL member (the independent catalog member query in the same run gave exactly M01..M20).
Before the checker was changed, the SHA-256 of every raw JOB02091 file was recorded
(docs/evidence/zos3-pacz3ha-JOB02091-raw.sha256) and the files were made read-only. Fix 6b446cc: each LISTDS result is
parsed only from its exact command echo to its READY; END is accepted only as the last record, unindented, outside
every extent (a member named END is indented and stays a member); any other shape fails closed; regression tests on
the real JOB02091 SYSTSPRT (tests/fixtures/zos/, same SHA-256 as the raw file). The corrected checker on the same
spool and the same read-only queries: every criterion PASS (docs/evidence/zos3-ha-check.txt), no HS semantics changed.
PACZ3HA / JOB02091 = PASS.
