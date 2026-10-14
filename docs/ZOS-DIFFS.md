# z/OS differences register (Z-entries, docs/ZOS-MIGRATION-PLAN.md R0)
Every difference between z/OS and the 2.0-mvs-max oracle that z/OS forces: cause, evidence, test that pins it, user
approval. Empty until a difference is proven.

## Candidates (not yet differences)
- C1 (ZOS-0 A3): paragraph name `VALIDATE` in src/cobol/PACQRY.cob is an Enterprise COBOL 6 reserved word; expected
  compile error in ZOS-2. **Not confirmed by the compiler** (Z2-1 JOB08497: PACQRY RC 0000, no message at all). No
  change needed; kept here only as the record of the ZOS-0 prediction.
- C2 (Z2-1 JOB08497): ANS-68 `01  <name> COPY <member>.` in 9 modules (PACMAIN, PACGAME, PACMAP, PACAI, PACINPT,
  PACDISP, PACPLAT, PACSCR, PACRT; 28 statements). IKFCBL00 replaces the whole 01 entry by the member (whose own first
  entry is `01 <name>.`, D16); Enterprise COBOL 6.5 (ANS-85) inserts the member text after `01 <name>`, so every such
  name is defined twice: IGYDS1159-E / IGYDS1082-E at the COPY, IGYSC2025-W on the LINKAGE copies, IGYPS0037-S on
  every reference; RC 0012. All 260 printed messages name only these 01 items. Mechanical dialect difference;
  resolution pending the user's decision (docs/evidence/zos2-portable-core.md).
- C3 (Z2-1): ASMA303W in PACFSIO (overlapping USING *,12 and USING ABEXIT,15 in the ESTAE exit), RC 0004; the only
  affected reference, `S 12,ABOFF`, resolved to base R15 (5BC0 F014), the base the code requires. Benign, no change
  proposed; to be accepted (or not) by the user.
