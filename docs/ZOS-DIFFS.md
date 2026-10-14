# z/OS differences register (Z-entries, docs/ZOS-MIGRATION-PLAN.md R0)
Every difference between z/OS and the 2.0-mvs-max oracle that z/OS forces: cause, evidence, test that pins it, user
approval. Empty until a difference is proven.

## Candidates (not yet differences)
- C1 (ZOS-0 A3): paragraph name `VALIDATE` in src/cobol/PACQRY.cob is an Enterprise COBOL 6 reserved word; expected
  compile error in ZOS-2. Decision pending (rename on main with MVS regression, or z/OS override).
