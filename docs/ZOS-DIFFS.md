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


## Z4 - ZOS-6 presentation decoupling, sources (ZV-D33; implemented 2026-10-19; built / installed in ZOS-6, see Status)
- Approval: production design docs/zos6-production-design.md approved for local implementation (user, 2026-10-19).
  Branch zos only; the MVS sources of record, main, 2.0-mvs-max and the MVS release are untouched.
- Cause: on z/OS TSO / VTAM / TN3270E with CONTENTION-RESOLUTION one TPUT NOHOLD per 150 ms quantum grows the output
  queue without bound and AIDs never reach TGET (R1-T3, probe P0); writing every second quantum keeps it bounded with
  input delivered (probe PR2-A; PR2I-C2: AIDs became readable right after a write). Evidence:
  docs/zos6-protocol-probe.md, docs/zos6-io-architecture-memo.md.
- Change (hunks exact: tests/zos_z4.json, guard tests/zos_c2.py z4_guard; z4_reverse gives back the Z1 text):
  - src/copy/PACREQ.cpy: REQ-PMODE, REQ-PRES appended (no existing offset moves).
  - src/cobol/PACMAIN.cob: PARM column 26 (C = COALESCED); RT-PBASE (start / resume = presentation base); per running
    quantum PACPLAT PSLT after PACRT RQ; RT-FRAME (prompt frame) kept until a presented quantum; COALESCED TSC only,
    after a presented write: RT-POST-READ = exactly one RTRD (one PACPLAT POLL = one TGET ASIS,NOWAIT), its event for
    the next quantum; RT-OVER tested before the deadline.
  - src/cobol/PACPLAT.cob: op PSLT in logical time (PS-TP 300, PS-ACC reset on a slot: NORMAL every 2nd, FAST every 3rd
    quantum; Y always unless REQ-PMODE C and TSC / TSD).
  - src/cobol/PACDISP.cob: RTQF with REQ-PRES N = SCR-RTQS (PACSCR RTQS, the S2 pattern countdown, no screen, no send).
  - src/cobol/PACSCR.cob: op RTQS = RP-STATE + SET-FACE + (ANIM Y) VIS = REQ-VIS (popup, facing and the animation
    frame the end screen draws follow the logical quantum; VIS added after PACZ6DR1 JOB09418), no image / diff.
- Unchanged: PACFSIO, PACTSO, PACRT, PACGAME, PACMAP, PACAI, PACINPT, every other copybook (tests section 22).
- PRESENT(EVERY) (no column 26) = the D33 loop: PSLT always Y, no RTQS, no post-write read, RT-FRAME cleared every
  quantum; same TGET / TPUT / STIMER sequence (tests section 22: the PSLT paragraph interpreted from its source).
- Guards: tests/zos_c2.py (Z4 hunks exact), tests/test_g8.py (changed sources within Z1 + Z4), tools/zowe/r3_gate.py
  (MVS decks from the zos tree differ only by Z1 / Z4 lines), tests/test_core_frozen.py (core untouched).
- Not yet proven on z/OS: compile / bind, the TSD dry runs, live R1 / R2.
- Status 2026-10-19 (ZOS-6 closure): built PACZ6BLD JOB09460 RC 0, dry runs JOB09466 / JOB09470 PASS, promoted to
  LOAD(PACMAIN) by PACZ6INS JOB09499, live R1-T4 / R2 PASS (docs/evidence/zos6-realtime.md). Installed.

## Z5 - ZOS-6 CLIST keyword PRESENT(EVERY|COALESCED) (implemented 2026-10-19; installed at ZOS-6 closure, see Status)
- File src/zos/PACMAN.clist (the MVS CLIST unchanged): PROC default `PRESENT(EVERY)`; two help lines; the 2.0 PARM
  line unchanged, then two comment lines, `SET &E = &SUBSTR(1:1,&PRESENT)` and `IF &E = C THEN SET &P = &STR(&P&E)`:
  EVERY leaves the 25-column 2.0 PARM byte for byte, COALESCED appends column 26 = C. Only statement forms the 2.0
  CLIST already runs (no null assignment). Exact lines: tests/zos_c2.py Z5_* (z5_strip before the Z3 / Z2 checks).
  Default during ZOS-6 development = EVERY; R1 / R2 request PRESENT(COALESCED) explicitly; the release default is not
  chosen. Not yet executed on this system.
- Status 2026-10-19 (ZOS-6 closure): test copy PACZ6CL JOB09382 PASS; installed as CLIST(PACMAN) (136 records,
  byte for byte); live R1-T4 / R2 PASS with PRESENT(COALESCED). Default stays PRESENT(EVERY).

## Z6 - ZOS-10 CLIST default PRESENT(AUTO): COALESCED for PLAY(REALTIME) only (DEC-2; approved 2026-10-20)
- File src/zos/PACMAN.clist (branch zos; the MVS CLIST unchanged): PROC default `PRESENT(EVERY)` -> `PRESENT(AUTO)`;
  the two PRESENT help lines -> three; one comment + one statement after the Z5 `SET &E = &SUBSTR(1:1,&PRESENT)`:
  `IF &PRESENT = AUTO AND &Y = R THEN SET &E = C`. The Z5 statements stay byte for byte (no parser change).
- Behaviour: no PRESENT operand (AUTO) + PLAY(REALTIME) -> PARM column 26 = C (COALESCED); AUTO + PLAY(TURN) -> no
  column 26 (the historical 25-column TURN PARM); explicit COALESCED -> C (any PLAY, as Z5); explicit EVERY and any
  other value -> no column 26 (EVERY, as Z5). PACMAIN unchanged: an absent column 26 still means EVERY.
- Reason: on z/OS TSO / VTAM / TN3270E one write per quantum (EVERY) is unsuitable for interactive REALTIME (R1-T3,
  ZV-D33); the accepted REALTIME architecture is COALESCED (ZOS-9 DEC-2: the release default).
- Guards: tests/zos_c2.py Z6_* / z6_strip (exact, required by the guard; z5_strip applies it first);
  tests/test_zos_tools.py section 22 reads the ZOS-6 text through z6_strip; tests/test_zos10.py (PARM matrix).
- Status: implemented locally for ZOS-10 (release preparation); verified on z/OS by PACZ10CL (PARM matrix) and the
  installed live smoke S10 (docs/zos10-design.md).

## D46 - REALTIME Right on PF12 (ZOS-11 / 2.1-zos; NOT a z/OS difference)
- The same change as 2.1-mvs (MVS-10, main): PACINPT RT-TSC `IF WS-V = 123` -> `124` + its comment, the z/OS CLIST
  ARROWS help comment. Shared product evolution, not forced by z/OS, so not a Z-entry; tests/zos_c2.py allows exactly
  these lines as D46 (d46_strip, required), docs/zos11-design.md.

## Model / checker for Z4 (tests and tools only, not z/OS differences in the product)
- tests/ref_rt.py: additive present='C' filter (every quantum runs; writes at the PSLT slots; skipped quanta advance the
  facing and the RP tracker; pending prompt frame), frame tags (qs, cards, imgs, skips) and the frt freeze hook (checker
  mutants only); default output = oracle 310 unchanged. tests/ref_s2.py: skips (the pattern clock on skipped quanta).
- tools/zowe/zos6_live_check.py: logical quanta vs physical frames, bounded backtracking placement, the 9 / 10 / 11
  freeze discrimination, freeze-span proxy, trace-clock input reaction, the predeclared candidate gates.
  zos5_live_check.py frozen.

## Post-closure documentation errata (ZOS-9, 2026-10-20)
Identified in docs/zos9-design.md section 6; recorded in docs/evidence/zos9-equivalence.md.
- C3 above still reads "not resolved": superseded. **C3 was CLOSED in ZOS-8** (Stage D E1-E3: PACFSIO's ESTAE driven on
  z/OS, line mode / session recovered, clean follow-up game each time; docs/evidence/zos8-services.md) with no PACFSIO
  source change; the ASMA303W stays the only, accepted, assembler warning.
- The Z4 / Z5 headings said "NOT built / NOT installed" (their state when written); the headings now point to the
  Status lines, which record the ZOS-6 build (PACZ6BLD JOB09460), promotion (PACZ6INS JOB09499) and CLIST install.
