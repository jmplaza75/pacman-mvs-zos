# ZOS-11 step 2B - promotion of the RZ21 2.1-zos build (D46) - evidence (2026-10-21)
Tool tools/zowe/zos11_release.py (commit 8d2df86; decks jcl/zos/PACZ11PV / IP / IC / ZD / P1, audited fail closed).
Source of record 35b803e; build of record RZ21 (step 2A, PACZ11BL JOB09451). Every job submitted once; no DELETE,
purge, retry or rebuild. Spool and downloads outside git (`build/zos/`). **Stops before the live gate.**

## 1. Read-only state gates (zos11_release --state, binary SHA-256 of every member involved)
| Phase | Result |
|---|---|
| pre | 14 / 14 PASS: LOAD(PACMAIN) = RZ.LOAD = `306d9736...` (2.0-zos); RZ21.LOAD = `798596b9...5386`; CLIST = RZ.CLIST = `a437082a...` with `ARROWS = PF7/8/10/11`; RZ21.CLIST = 2.1 render `49d6e26d...`; PRV.CLIST `6e0a68ec...`; PRV20.CLIST absent; RZ.OBJ = ZOS-10 record (13); PACZ6D `ed756b36...`; HISCORE `0000980 PACHS001 001` |
| after PV | 17 / 17 PASS (PRV20.CLIST(PACMAN) = `a437082a...`, only member; nothing else changed) |
| after IP | 18 / 18 PASS (LOAD(PACMAIN) = `798596b9...` = RZ21, attributes = RZ21; every other LOAD member's directory entry unchanged; CLIST still 2.0) |
| after IC / final | 18 / 18 PASS (CLIST(PACMAN) = RZ21.CLIST = 2.1 render `49d6e26d...`; differs from 2.0-zos only in record 25, `ARROWS = PF7/8/10/11` -> `ARROWS = PF7/8/10/12`; HISCORE unchanged; 33 datasets = 32 + PRV20.CLIST) |

## 2. Jobs
| JOB | Deck | Purpose | Result |
|---|---|---|---|
| JOB09545 | PACZ11PV | IEBCOPY CLIST(PACMAN) -> new PRV20.CLIST (DISP=NEW) | PRV1 CC 0000; IGW01551I PACMAN copied, IGW01550I 1 of 1, IEB147I severity 0 |
| JOB09553 | PACZ11IP | IEBCOPY RZ21.LOAD(PACMAIN) -> LOAD (replace) | PROM1 CC 0000; IGW01552I copied and replaced, 1 of 1, severity 0 |
| JOB09558 | PACZ11IC | IEBCOPY RZ21.CLIST(PACMAN) -> CLIST (replace), only after the IP gate passed | PROM2 CC 0000; IGW01552I copied and replaced, 1 of 1, severity 0 |
| JOB09560 | PACZ11ZD | AMASPZAP `DUMP PACMAIN ALL` of RZ21.LOAD and LOAD (SYSLIB DISP=SHR, no VER / REP) | ZAPR21 / ZAPINS CC 0000; AMA113I, AMA100I; dumps identical row for row |
| JOB09562 | PACZ11P1 | RUN1 TSO2 TSO6 on the installed LOAD(PACMAIN) | 3 steps CC 0000; each = oracle 307 + model + the RZ21 C1 output; 566 lines; = 2.0-zos P1 JOB04874 |
No abend, IEC, CEE, output-limit, PACHS, DATA or HISCORE text in any job.

## 3. AMASPZAP scope on z/OS (finding)
IGWSPZAP dumps the B_TEXT class of a program object. The 10 Enterprise COBOL modules carry their code in C_CODE:
AMA152I "NO TEXT DATA OF REQUESTED CLASS" for each of them. The identical dumps therefore cover the 3 assembler modules
and the LE / IGZ stubs (B_TEXT, 268 hex rows), not the COBOL text and not PACINPT. Installed = RZ21 for the whole
program object (all classes) is proven by the binary image identity (section 1); the D46 content of RZ21 by the step 2A
object gate.

## 4. Rollback (kept, unchanged)
Program: Z00000.PACMAN.RZ.LOAD(PACMAIN) (2.0-zos, `306d9736...`). CLIST: Z00000.PACMAN.PRV20.CLIST(PACMAN) (2.0-zos)
and RZ.CLIST(PACMAN). Older: PRV.CLIST (zos-9), LOAD(PACZ6D).
