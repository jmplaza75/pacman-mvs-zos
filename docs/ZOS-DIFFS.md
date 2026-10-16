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

## Z2 - CLIST: LE profile A CEEOPTS around the CALL (ZOS-4; accepted 2026-10-15)
- File: `src/zos/PACMAN.clist` (branch zos only) = the 2.0-mvs-max `src/clist/PACMAN.clist` + 32 lines (31 before the
  CALL, `FREE F(CEEOPTS)` after it); guarded by tests/zos_c2.py z2_guard. The MVS CLIST is unchanged.
- Reason: the interactive TSO session (logon proc DBPROCDG) has no CEEOPTS DD and the no-override LE defaults are
  ALL31(ON), STACK ANYWHERE (IBM-supplied; PACZ4LE JOB03693 D1), not profile A; a CEEOPTS DD gives the AMODE 24 module
  profile A (D2); invocation options outrank CEEOPTS (D3) and the CLIST PARM carries none.
- Behaviour: SYSDSN of `<prefix>.CEEOPTS`: OK -> ALLOC F(CEEOPTS) SHR without REUSE under CONTROL NOFLUSH + an ERROR
  routine -> CALL -> FREE (the session returns to no CEEOPTS); DATASET NOT FOUND -> MISSING message, RC 8, no CALL;
  any other result -> CHECK FAILED (result) message, RC 8, no CALL; a CEEOPTS DD already allocated -> the ALLOC is
  refused, the existing DD is kept, ALREADY ALLOCATED message, RC 8, no CALL; SYSIN / SYSOUT (and PACHS) freed on
  every failure.
- Evidence: PACZ4Z3 JOB03875 (all three paths, 26/26); history JOB03750 (case 3 inconclusive), JOB03829 (case 3
  handler did not regain control without NOFLUSH).
- Needs the project dataset `<prefix>.CEEOPTS` (PS FB 80/80, one record `ALL31(OFF),STACK(,,BELOW)`), created at
  installation (PACZ4INS).


## Z3 - CLIST: terminal SYSIN fixed 80 through ATTRIB + USING (ZOS-4; accepted 2026-10-16)
- File: `src/zos/PACMAN.clist` (branch zos only): the 2.0 line `ALLOC F(SYSIN) DA(*) REUSE` replaced by the 24-line
  block of docs/zos4-sysin-fix.md ("Revision"); guarded by tests/zos_c2.py (Z3_BLOCK, z3_strip + z2_guard).
- Reason: live session 1 (2026-10-16): the terminal SYSIN took the 120-column line size; Enterprise COBOL checks the
  fixed 80 record length of PACINPT COMMAND-FILE at OPEN (IGZ0201W, IGZ0035S status 39, U4038). For `DA(*)` TSO/E
  processes only FILE, BLOCK / BLKSIZE and USING, so the DCB comes from an attribute list (ATTRIB Z3SIATTR RECFM(F)
  LRECL(80) BLKSIZE(80)), freed right after the ALLOC and only if created there; any failure -> RC 8, no CALL.
- SYSOUT, Z2, CEEOPTS, PACMAIN and the COBOL sources unchanged. Evidence: live session 2 (2026-10-16, same 120-column geometry): DIE1 / LOST0 PASS
  (docs/evidence/zos4-live.md); installed CLIST 130 x 80, SHA-256 f8989cfa....
