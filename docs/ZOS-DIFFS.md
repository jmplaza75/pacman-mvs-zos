# z/OS differences register (Z-entries, docs/ZOS-MIGRATION-PLAN.md R0)
Every difference between z/OS and the 2.0-mvs-max oracle that z/OS forces: cause, evidence, test that pins it, user
approval.

## Z-entries
- **Z1 - ANS-68 `01 <name> COPY <member>.` -> `COPY <member>.`** (ex C2; approved by the user 2026-10-14, branch zos
  only). Cause: Enterprise COBOL 6.5 (ANS-85) inserts the member after the 01 instead of replacing the entry
  (IKFCBL00), so every name is defined twice (Z2-1 JOB08497, RC 12 in 9 modules). Change: the 28 listed statements of
  PACMAIN, PACGAME, PACMAP, PACAI, PACINPT, PACDISP, PACPLAT, PACSCR, PACRT become `COPY <member>.` at the same column;
  each member already owns the identical `01 <name>.` (D16), so the record layouts are those of 2.0-mvs-max.
  Guards: tests/zos_c2.py + tests/zos_c2.json (exactly these 28 substitutions, copybooks and every other src file =
  2.0-mvs-max), tests/test_core_frozen.py (explicit Z1 allowance: reversing the listed lines restores the frozen
  hash), tests/test_g8.py (source diff since mvs-s2 limited to Z1), tools/zowe/r3_gate.py (MVS generator and release
  decks unchanged on the 2.0-mvs-max sources; z/OS-tree MVS decks differ only by Z1 lines). main, 2.0-mvs-max and the
  MVS release are untouched; MVS is not rebuilt from branch zos. Proof of unchanged behaviour: the ZOS-2 runs compared
  with the oracle (Z2-2..Z2-4).

## Candidates (not yet differences)
- C1 (ZOS-0 A3): paragraph name `VALIDATE` in src/cobol/PACQRY.cob predicted as an Enterprise COBOL 6 reserved-word
  error. **Disproved** (Z2-1 JOB08497: PACQRY RC 0000, no message). Not renamed; closed.
- C2: became Z1 (above).
- C3 (Z2-1): ASMA303W in PACFSIO (overlapping USING *,12 and USING ABEXIT,15 in the ESTAE exit), RC 0004; the only
  affected reference, `S 12,ABOFF`, resolved to base R15 (5BC0 F014), the base the code requires. **Known z/OS
  assembler warning, accepted provisionally for ZOS-2 (user, 2026-10-14), not resolved**: PACFSIO passes with RC 4
  only if ASMA303W is its sole diagnostic, the listing still shows `S 12,ABOFF` with base R15, and no other assembler
  warning or error appears. Technical debt to revisit with the ESTAE / recovery work; PACFSIO is not changed to
  silence it.
