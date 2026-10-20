# ZOS-10 Release - evidence (2026-10-20)
Design: docs/zos10-design.md (approved; decisions section 15; object-gate history section 19.7). Host: IBM Z Xplore
S0W1, userid / HLQ Z00000. Every job submitted once with tools/zowe/zos_submit.py and checked with
tools/zowe/zos10_release.py; spool, downloaded images and the S10 raw trace stay outside git (`build/zos/`, the raw
trace directory). Nothing outside Z00000.PACMAN.* was touched; no DELETE, no purge, no retry, no credential stored.

## 1. Final result
**ZOS-10 RELEASE ENGINEERING - PASS. PAC-MAN 2.0-zos released.**
- ZOS-9 proved the final MVS / z/OS **behavioural equivalence** (docs/evidence/zos9-equivalence.md: 51-row matrix,
  GAP 0, DECISION 0); that claim is referenced, not repeated, and stays valid: ZOS-10 changed no program source.
- ZOS-10 proves a different claim: a **clean, reproducible release build** from a committed tree, **continuity** of the
  rebuilt candidate with the accepted program (object level and batch), the **release configuration** (DEC-2 CLIST
  default), a **safe promotion** with a verified rollback copy and no partial state, and the **installed release
  operating** in batch and live.

## 2. Release provenance
- Release-preparation commit `2c99fae1ebfa472193c4c299f00efe1701853eab` (parent zos-9 885c12b): the only production
  change is Z6 in src/zos/PACMAN.clist; COBOL, copybooks and assembler = zos-9 = zos-6.
- Local pre-host gate: HEAD = 2c99fae, branch zos, clean tree, no zos-10 / 2.0-zos tag, the 8 decks of record =
  generated, tests/test_zos10.py, zos_c2 guard and validate_source PASS.
- Source SHA-256: releases/2.0-ZOS/SHA256SUMS (19 sources, the CLIST, the 8 decks).

## 3. Clean allocation and source upload
- Read-only precheck: the six RZ libraries, Z00000.PACMAN.PRV.CLIST and Z4CL.T1(Z10P) absent; LOAD(PACMAIN),
  LOAD(PACZ6D), CLIST(PACMAN) and CEEOPTS present. PACZ6D directory attributes recorded (AC 00, AMODE 24, RMODE 24,
  RN RU, size X'000204A0') as the "unchanged" reference; no PACMAIN = PACZ6D claim was drawn from attributes.
- PACZ10AL JOB04812 CC 0000: RZ.COBOL / COPY / ASM / OBJ (PDSE FB 80 27920), RZ.LOAD (PDSE U 32760), RZ.CLIST (PDSE FB
  80 27920), all empty. Four IGD01007I ZXPACS space reductions (COBOL, COPY, ASM, OBJ): the documented site ACS rule,
  identical to the ZOS-1 allocation of record (PACZALLO JOB08252).
- Upload: exactly the 19-member allow-list from 2c99fae (10 COBOL, 6 COPY, 3 ASM), each byte-identical on the host
  (IBM-037, fixed 80); nothing else in RZ; RZ.OBJ / LOAD / CLIST still empty.

## 4. Build results (PACZ10BL JOB04820, CC 0004, ~3,250 spool lines)
- COB1-COB10 RC 0000, no message above I; ASM1 PACTSO RC 0000; ASM3 PACHSIO RC 0000; ASM2 PACFSIO RC 0004 with only
  the frozen C3 condition (ASMA303W "multiple address resolutions ... USING on statement number 38" + ASMA435I;
  `S 12,ABOFF` = 5BC0 F014); LINK RC 0000.
- Binder: INCLUDE OBJ(PACMAIN ... PACHSIO) x 13, ENTRY PACMAIN, NAME PACMAIN, AMODE 24, RMODE 24, RENT YES, REUS YES,
  EXCEEDS 16MB NO, messages IEW2008 / 2278 / 2322 only, no unresolved external; RZ.LOAD(PACMAIN) X'000204A0'.
- Dataset audit from the actual JES listing: every compile reads RZ.COBOL / RZ.COPY and writes RZ.OBJ(member); every
  assembly reads RZ.ASM and writes RZ.OBJ(member); the binder reads only RZ.OBJ and writes RZ.LOAD; the old
  Z00000.PACMAN.OBJ / ASM never appear (the release tool's prefix rendering fix, design 19.6). RZ.OBJ went from empty
  to exactly the 13 production members.

## 5. Object-equivalence gate and corrected baseline
- **First attempt: 8 / 13 PASS -> STOP** (correctly; C1 not run). Against build/zos/Z6POST (SHA-256 as recorded at
  ZOS-6, verified): PACAI, PACINPT, PACDISP, PACQRY, PACRT, PACTSO, PACFSIO, PACHSIO identical modulo the frozen
  timestamps; PACMAIN, PACGAME, PACMAP, PACPLAT different only in the compressed bytes of D_MCODE; PACSCR C_CODE 32
  bytes longer plus D_MCODE.
- **Classification (accepted): no product regression, no rebuild.** (a) Stale baseline: Z6POST had been captured after
  the superseded PACZ6BLD JOB09365 (PACSCR 2,583 source records / 1,493 procedure statements, before the VIS fix), not
  after JOB09460 (2,586 / 1,495) whose PACZ6D PACZ6INS JOB09499 installed - a ZOS-10 tooling / evidence-baseline
  defect; historical ZOS-6 evidence and tags unchanged. (b) Compiler non-determinism in the compressed form of
  D_MCODE, a no-load debug class (ED loading attribute X'80' as the binder IDR class B_IDRL; C_CODE X'00'); its
  decompressed content was identical.
- **Corrected baseline (decision A)**: the 13 members of Z00000.PACMAN.OBJ, read only = the 13 INCLUDE inputs of the
  JOB09460 bind. Per member: PACMAIN, PACGAME, PACINPT, PACDISP, PACPLAT, PACSCR, PACRT from JOB09460 (timestamps
  2026-10-19 10:10:20-47 = the listing times to the second); PACMAP, PACAI, PACQRY, PACTSO, PACFSIO, PACHSIO from
  PACZ2BLD JOB08888 (2026-10-14 11:30, HLASM 26287), not recompiled by any ZOS-6 build and byte-identical to Z6POST.
  Compile statistics of every module = JOB04820; compiler / assembler levels equal. No later archived job wrote a
  production member (only PACZ8RPE JOB02299: member PACRPE, a probe). SHA-256 and job / timestamp per member:
  `zos10_release.BASE_SHA` / `BASE_PROV`.
- **D_MCODE rule (decision B, `dmcode_eq`)**: compressed representation may differ, logical content may not - one
  no-load D_MCODE ED per image (B_IDRL no-load, C_CODE loaded), ED equal apart from the validated class length, same
  TXT records and headers, contiguous offsets, zero padding, payload header validated, exactly one complete zlib stream,
  decompressed length and bytes equal, every other logical record byte-identical. 13 injected faults rejected, each by
  its rule (tests/test_zos10.py section 6).
- **Second attempt (the same JOB04820 objects): 13 / 13 PASS.**

| Module | Baseline (job) | Timestamps masked (old -> new) | D_MCODE representation | Decompressed D_MCODE | Loadable content | Verdict |
|---|---|---|---|---|---|---|
| PACMAIN | JOB09460 | 20261019101020 -> 20261020132840 | differs (41,337 / 41,344 B) | identical, 133,039 B | exact | PASS |
| PACGAME | JOB09460 | 20261019101024 -> 20261020132845 | differs (55,011 / 55,029) | identical, 176,488 | exact | PASS |
| PACMAP | JOB08888 | 20261014113022 -> 20261020132849 | differs (13,283 / 13,277) | identical, 43,749 | exact | PASS |
| PACAI | JOB08888 | 20261014113026 -> 20261020132853 | equal | identical | exact | PASS |
| PACINPT | JOB09460 | 20261019101029 -> 20261020132858 | equal | identical | exact | PASS |
| PACDISP | JOB09460 | 20261019101033 -> 20261020132902 | equal | identical | exact | PASS |
| PACPLAT | JOB09460 | 20261019101038 -> 20261020132907 | differs (49,481 / 49,504) | identical, 156,713 | exact | PASS |
| PACSCR | JOB09460 | 20261019101042 -> 20261020132911 | differs (191,783 / 191,726) | identical, 635,355 | exact | PASS |
| PACQRY | JOB08888 | 20261014113044 -> 20261020132916 | equal | identical | exact | PASS |
| PACRT | JOB09460 | 20261019101047 -> 20261020132921 | equal | identical | exact | PASS |
| PACTSO / PACFSIO / PACHSIO | JOB08888 | END date 26287 -> 26293 | (HLASM) | - | exact | PASS |
  (COBOL: the 14-digit X'0311' span shown; the 13-digit X'0310' span moved the same way, e.g. PACMAIN 2026292094720 /
  2026292101020 -> 2026293132840.) PACSCR: old baseline = JOB09365 generation, corrected baseline = JOB09460
  generation, executable code (C_CODE) **exact**. Nothing outside the three frozen timestamp spans and the compressed
  D_MCODE representation differs.

## 6. Candidate validation (RZ.LOAD(PACMAIN), STEPLIB RZ.LOAD, no PACHS / DATA)
- PACZ10C1 JOB04862 CC 0000: RUN1 160, RUN6 324, TSO1 175, TSO2 353, TSO3 965, TSO4 252, TSO5 290, TSO6 53 lines, each
  = its own oracle 307 block and its frozen model; 2,572 application lines.
- PACZ10C2 JOB04864 CC 0000: RTT2 = oracle 310 + model (557), N1 = the frozen ZOS-6 N1 model (380; no oracle exists),
  G3T7 = oracle 311 + the ZOS-9 model (226); 1,163 application lines.

## 7. Release CLIST / DEC-2 validation
- RZ.CLIST(PACMAN) = src/zos/PACMAN.clist of 2c99fae rendered for Z00000.PACMAN, byte-identical (140 records).
- Z4CL.T1(Z10P) absent immediately before; PACZ10CL JOB04866 CC 0000 (test copy without the high-score block; every
  case RULES(CLASSIC)): all 10 PARMs as expected - default REALTIME and explicit COALESCED -> `...RAC01NPC`; REALTIME
  EVERY -> `...RAC01NP` (25 columns); TURN default -> `TSO AI1 1 NAAAPAAATAC01NP` (historical, no default C); TURN
  explicit COALESCED -> C; TURN EVERY -> 25 columns; PRESENT(XYZ) / (ABC) -> the EVERY fallback; `AI(0) RULES(CLASSIC)
  SOUND(NO)` -> `TSO AI0 1 NAAAPAAARNC01NPC`.

## 8. Rollback preservation
- The pre-release installed CLIST(PACMAN) downloaded read-only first: 136 records, SHA-256 `6e0a68ec...ebef8`, exactly
  the zos-9 src/zos/PACMAN.clist render.
- PACZ10PV JOB04868 CC 0000: new PRV.CLIST; IGW01551I PACMAN copied, IGW01550I 1 OF 1, IEB147I severity 0; PRV.CLIST
  holds only PACMAN, byte-identical to the pre-release CLIST; the installed CLIST unchanged by PV.

## 9. Promotion and installed-byte verification
- Master gate before PACZ10IN: allocation, upload, build, binder, 13 / 13 objects, C1, C2, RZ CLIST, CL, PV and its
  byte check all PASS; no ZOS-10 job or job output referenced DATA, PACHS or HISCORE.
- PACZ10IN JOB04870 CC 0000: PROM1 IGW01552I PACMAIN copied and replaced, 1 of 1, severity 0; PROM2 (COND=(0,NE))
  IGW01552I PACMAN copied and replaced, 1 of 1, severity 0. **No partial promotion.**
- Read-only in-check PASS: LOAD(PACMAIN) attributes = RZ.LOAD(PACMAIN); CLIST(PACMAN) = RZ.CLIST(PACMAN) = the release
  render; PACZ6D attributes unchanged; PRV.CLIST = the pre-release CLIST. Because PACMAIN, PACZ6D and the candidate
  share the same directory attributes, the program was also compared by binary download (same z/OSMF mechanism for
  each): installed LOAD(PACMAIN) = RZ.LOAD(PACMAIN), 745,472 bytes, SHA-256 `306d973612be...0c64`; LOAD(PACZ6D)
  differs (`ed756b362b1c...3823`, the older bind).

## 10. Installed P1 validation
- PACZ10P1 JOB04874 CC 0000 on the installed LOAD(PACMAIN): RUN1 160, TSO2 353, TSO6 53 lines, each = oracle 307 +
  model and byte-equal to the corresponding C1 candidate output; 566 application lines (candidate -> installed
  continuity; installed line mode / 1.0 oracle).

## 11. S10 live release smoke
- Session: the user's c3270 (`-model 2 -oversize auto -scriptport 4012`, 120 x 30), logged on by the user; idle ISPF
  Command Shell confirmed through Ascii(); raw trace started via the script port in a directory outside the
  repository; the frozen ZOS-6 R1 plan (keys and waits unchanged) driven once by `zos10_release.py --s10-drive`, the
  only change being the operands: `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) SOUND(NO)'` (no PLAY, no
  PRESENT). Trace SHA-256 `573e42cf2f6e698af28fffbe271a0ab1a124386d000251b5a29258fede1f863f` (652,370 bytes), made
  read-only with the driver log and the checker output.
- Checker (`--s10-check` = the frozen zos6_live_check R1 rules): **FUNCTIONAL PASS, TIMING PASS, shell return PASS**
  (`R1: PASS`).
  - 296 physical game writes = the canonical model, 586 logical quanta, PRESENT C (COALESCED stride 2), canvas
    120 x 27; end lines `QUIT`, `TURNS 024`, `SCORE 0230`, `LIVES 2`, `QUANTA 0000586`; `***`, closure ENTER, ISPF
    Command Shell.
  - Principal-segment mean 150.399 ms (T = 150 ms); death stop 1,496 ms (nominal 1,500); PF8 / PF9 / PF9 / x / PA2 /
    PF11 / Q answered as planned; pause and resume correct.
- Effective PARM: the S10 invocation contained no PLAY or PRESENT operand; PACZ10CL had already proven that the
  validated release CLIST generates `TSO AI0 1 NAAAPAAARNC01NPC` for those operands; the installed CLIST is
  byte-identical to that validated CLIST; and S10 showed the expected CLASSIC / COALESCED behaviour. The effective PARM
  is established by that mapping, the installed-byte identity and the observed behaviour - the terminal trace contains
  no literal PARM record.
- The four `FREE F(PACHS)` strings in the trace are pre-existing ISPF command-history lines, on the screen before the
  EXEC was sent; not S10 PACHS activity.

## 12. Production-state safety
- No ZOS-10 executable job referenced PACHS or DATA (decks audited fail-closed; all JES logs and outputs scanned; the
  only textual match is a help comment of the CLIST test copy inlined in the PACZ10CL deck, not a statement).
- S10 is CLASSIC and did not enter the high-score path (no PACHS allocation, no high-score screen).
- The closure procedure performed exactly one intentional read-only check of Z00000.PACMAN.DATA(HISCORE): `0000980
  PACHS001 001`, unchanged (DATA: PDS FB 80 / 80, one member).

## 13. Anomalies and classifications
| Item | Classification | Effect |
|---|---|---|
| First object gate 8 / 13 | stale Z6POST baseline (ZOS-10 tooling / evidence) + compressed no-load D_MCODE (toolchain) | corrected baseline + D_MCODE rule approved; no rebuild; 13 / 13 |
| IGD01007I x 4 in PACZ10AL | documented site ACS rule (ZOS-1) | none |
| PACMAIN / PACZ6D / candidate share directory attributes | attributes cannot identify a program object | binary comparison added (section 9) |
| A local provenance cross-check of the pre-release CLIST first returned False | operator path error in an ad-hoc command (empty `git show` output) | rerun correctly: True |
| Release-tool assembler prefix (preparation) | found by the deck audit before host work | fixed in the tool; the JOB04820 listing confirms RZ only |

## 14. Final installed state (read-only, closure)
| Dataset / member | State |
|---|---|
| Z00000.PACMAN.LOAD(PACMAIN) | the 2.0-zos program = RZ.LOAD(PACMAIN) (binary identical), AMODE 24 / RMODE 24, RN RU, X'000204A0' |
| Z00000.PACMAN.CLIST(PACMAN) | the 2.0-zos launcher = RZ.CLIST(PACMAN) (SHA-256 `a437082ac5c6...8ab3`), PRESENT(AUTO) |
| Z00000.PACMAN.LOAD(PACZ6D) | unchanged (binary identical to its pre-promotion read); program rollback |
| Z00000.PACMAN.PRV.CLIST(PACMAN) | the zos-9 CLIST; CLIST rollback |
| Z00000.PACMAN.RZ.COBOL / COPY / ASM / OBJ / LOAD / CLIST | 10 / 6 / 3 / 13 / 1 / 1 members: the release build of record |
| Z00000.PACMAN.Z4CL.T1(Z10P) | the PACZ10CL test copy (kept) |
| Z00000.PACMAN.DATA(HISCORE) | `0000980 PACHS001 001` |

## 15. Release conclusion
Exit criteria (design section 17) all met: clean build from the committed release set; 13 objects rebuilt; bind
attributes; C3 policy exact; object equivalence 13 / 13 (with the approved corrected baseline and D_MCODE rule); C1,
C2, CL PASS before promotion; rollback copy verified; promotion complete; installed = candidate; P1 PASS; S10 PASS
(REALTIME default -> COALESCED, normal return); explicit PRESENT(EVERY) PARM unchanged; HISCORE unchanged; no
unexplained difference. **ZOS-10 CLOSED / PASS; PAC-MAN 2.0-zos RELEASED.**
