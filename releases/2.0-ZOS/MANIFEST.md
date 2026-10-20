# PACMAN 2.0-zos - release manifest (ZOS-10)
Identifies the z/OS release and how it was built, verified and installed. Every job ran once on IBM Z Xplore (z/OS V3R1,
system S0W1) under userid / HLQ Z00000; spool is kept locally (`build/zos/<JOBNAME>-<JOBID>/`, not committed: JES
data). Decks in `decks/` are the decks of record (`@@HLQ@@` templates rendered by `tools/zowe/zos_submit.py`; no
credentials anywhere - Zowe secure store only). Full evidence: `docs/evidence/zos10-release.md`; design:
`docs/zos10-design.md`.

## Identity
| Item | Value |
|---|---|
| Release | 2.0-zos (annotated tags `zos-10` and `2.0-zos` on the closure commit) |
| Build provenance | release-preparation commit `2c99fae1ebfa472193c4c299f00efe1701853eab`; the 19 sources and the CLIST were uploaded from that tree and byte-verified on the host |
| Sources | `SHA256SUMS` (10 COBOL, 6 copybooks, 3 assembler, the z/OS CLIST, the 8 decks); `src/` unchanged after 2c99fae |
| Differences vs 2.0-mvs-max | only the registered Z-entries (`docs/ZOS-DIFFS.md`): Z1 COPY syntax, Z2 CEEOPTS, Z3 terminal SYSIN, Z4 / Z5 PRESENT(COALESCED), Z6 PRESENT(AUTO) default |
| Toolchain | Enterprise COBOL 6.5.0 P260714, HLASM R6.0 (PTF UO07449), IEWBLINK; build profile A (AMODE 24 / RMODE 24, RENT, LE ALL31(OFF) STACK BELOW) |
| Build of record | PACZ10BL JOB04820 into the new, empty `Z00000.PACMAN.RZ.*` libraries: `RZ.LOAD(PACMAIN)`, AMODE 24, RMODE 24, RENT, REUS, entry PACMAIN, size X'000204A0' |
| Installed program | `Z00000.PACMAN.LOAD(PACMAIN)` = IEBCOPY copy of `RZ.LOAD(PACMAIN)` (PACZ10IN JOB04870); binary image identical (SHA-256 `306d9736...0c64`) |
| Installed launcher | `Z00000.PACMAN.CLIST(PACMAN)` = `RZ.CLIST(PACMAN)` = `src/zos/PACMAN.clist` rendered for Z00000.PACMAN (140 records, SHA-256 `a437082a...8ab3`) |
| Rollback | program `LOAD(PACZ6D)` (ZOS-6 build JOB09460, unchanged); CLIST `Z00000.PACMAN.PRV.CLIST(PACMAN)` = the zos-9 CLIST (PACZ10PV JOB04868) |
| Production data | `Z00000.PACMAN.DATA(HISCORE)` = `0000980 PACHS001 001`, unchanged (one read-only check at closure) |

## Build, verification and installation of record (2026-10-20)
| Job | Deck | What | Result |
|---|---|---|---|
| (read-only) | - | precheck: RZ / PRV / Z4CL.T1(Z10P) absent; LOAD(PACMAIN), LOAD(PACZ6D), CLIST(PACMAN) present | PASS |
| JOB04812 | PACZ10AL.jcl | allocate the 6 empty RZ libraries | CC 0000 |
| (upload) | - | 19 sources from 2c99fae into RZ.COBOL / COPY / ASM | 19 / 19 byte-identical |
| JOB04820 | PACZ10BL.jcl | 10 compiles, 3 assemblies, bind into RZ.LOAD | CC 0004 (PACFSIO C3 ASMA303W only), gate PASS |
| (local) | - | object equivalence vs the accepted ZOS-6 objects | first attempt 8 / 13 STOP (stale baseline); second, corrected baseline + D_MCODE rule: 13 / 13 PASS |
| JOB04862 | PACZ10C1.jcl | candidate: RUN1, RUN6, TSO1-TSO6 | PASS, 2,572 lines exact |
| JOB04864 | PACZ10C2.jcl | candidate: RTT2, N1, G3T7 | PASS, 1,163 lines exact |
| (upload) | - | release CLIST into RZ.CLIST(PACMAN) | byte-identical |
| JOB04866 | PACZ10CL.jcl | CLIST PARM matrix (10 cases, test copy `Z4CL.T1(Z10P)`) | PASS |
| JOB04868 | PACZ10PV.jcl | rollback copy CLIST(PACMAN) -> PRV.CLIST | PASS, byte-identical |
| JOB04870 | PACZ10IN.jcl | promotion PROM1 PACMAIN, PROM2 CLIST (replace) | PASS, both 1 of 1 |
| (read-only) | - | installed = candidate, PACZ6D unchanged, PRV intact | PASS |
| JOB04874 | PACZ10P1.jcl | installed: RUN1, TSO2, TSO6 | PASS, 566 lines = oracle = C1 |
| (live) | - | S10: `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) SOUND(NO)'` | FUNCTIONAL, TIMING, shell return PASS |
