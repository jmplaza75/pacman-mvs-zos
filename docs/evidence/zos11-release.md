# ZOS-11 Release 2.1-zos - closure evidence (2026-10-21)
Design: docs/zos11-design.md. Release material: releases/2.1-ZOS/. Step evidence (unchanged, kept as recorded):
docs/evidence/zos11-step2a.md, zos11-step2b.md, zos11-step2c-attempt1.md, zos11-step2c-attempt2.md,
zos11-step2c-attempt3.md. Host: IBM Z Xplore S0W1 (z/OSMF 198.51.100.200:10443 reports z/OS `05.29.00`), userid / HLQ
Z00000. Spool, downloads and live traces outside git; no credential and no logon keystroke in any evidence (every live
trace was started after the user's logon). Nothing outside Z00000.PACMAN.* was touched; no DELETE, purge or job retry.

## 1. Final result
**ZOS-11 CLOSED / PASS. PAC-MAN 2.1-zos released and installed** (tags `zos-11`, `2.1-zos` on the closure commit).

## 2. Product change (source of record `35b803e30011fed7427b2f9c5d3492530d985d20`)
D46 (the 2.1-mvs change; not a Z-entry):
- `src/cobol/PACINPT.cob`: REALTIME Right PF11 -> PF12 (`IF WS-V = 123` -> `IF WS-V = 124`) and the header comment;
  PF11 falls to the existing ignored path.
- `src/zos/PACMAN.clist`: help comment `ARROWS = PF7/8/10/11` -> `ARROWS = PF7/8/10/12` (no statement change).
- `tools/c3270_rt.sh`: Right arrow -> PF(12).
QUIT stays Q + ENTER only; TURN, batch, every other key, default and oracle unchanged. Guards: tests/zos_c2.py D46
exact; source hashes vs 2.0-zos differ in PACINPT and the CLIST only (releases/2.1-ZOS/SHA256SUMS).

## 3. Step 2A - fresh build and comparison (docs/evidence/zos11-step2a.md)
- New prefix `Z00000.PACMAN.RZ21` (absent before; allocated empty, PACZ11AL JOB09441); 20 members uploaded from
  35b803e, byte-identical; build PACZ11BL JOB09451 (same RCs, compile statistics and toolchain as 2.0-zos).
- Object gate against the frozen 2.0-zos build (RZ.OBJ = the ZOS-10 record): 13 / 13; the only functional delta is
  D46 - PACINPT one loaded byte, X'3C' -> X'4C' in the RT-TSC literal table `00247C 00248C 00122C 00123C 00249C
  00110C`; the rest = compile timestamps and the recompressed no-load D_MCODE (decompressed identical).
- Batch / TURN regression: C1 JOB09488 (2,572 lines) and C2 JOB09491 (1,163 lines) = oracles 307 / 310 / 311 and the
  frozen models, and byte-identical to the 2.0-zos C1 / C2 outputs.

## 4. Step 2B - backup, promotion, installed checks (docs/evidence/zos11-step2b.md)
- Backup: installed 2.0-zos CLIST -> new `Z00000.PACMAN.PRV20.CLIST(PACMAN)` (PACZ11PV JOB09545), byte-identical.
- Promotion: PACMAIN (PACZ11IP JOB09553), verified installed = RZ21 (binary image `798596b9...5386`, attributes, no
  other LOAD member changed); then the CLIST (PACZ11IC JOB09558), installed = RZ21 = release render (`49d6e26d...`),
  differing from 2.0-zos in record 25 only.
- Installed regression P1 JOB09562: 566 lines = oracle 307 + models = RZ21 C1 = 2.0-zos P1.
- AMASPZAP (PACZ11ZD JOB09560, DUMP only): RZ21 and installed dumps identical, but IGWSPZAP dumps the B_TEXT class only
  (3 assembler modules, LE / IGZ stubs); the COBOL C_CODE, PACINPT included, is not dumped (AMA152I). Corroboration
  only - the proof of the installed PACINPT is the binary identity installed = RZ21 plus the step 2A object gate.

## 5. Step 2C - live gate of the installed release
Session: dedicated c3270 `-model 2 -oversize auto -scriptport 4012` with keymap RIGHT = PF(12), IBM-DYNAMIC 27 x 120,
logged on by the user; `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) SOUND(NO)'` (CLASSIC: no high-score
path). Read-only pre-checks (18 / 18) before each attempt.

| Attempt | Result | Classification |
|---|---|---|
| 1 | ZOS-11 LIVE GATE FAIL | harness: the driver's Q probe read the character left of the cursor; the game's writes move the cursor, so a surviving Q looked erased; fixed in 67dfa21. Diagnostic evidence only |
| 2 | FAIL; offline re-check after 6d04b6f: ENVIRONMENT / TIMING BLOCKED | functionally correct; physical max gap 1,351 ms > 1,000 ms (environment); a checker Q-hold window defect (window ended at the post-Enter `sent` time) fixed in 6d04b6f. Diagnostic evidence only |
| 3 | **ZOS-11 LIVE GATE PASS** | authoritative, accepted |

Attempt 3 (19:17:40-19:19:10, 33 actions, driver completed, back at the ISPF Command Shell):

| Criterion | Result |
|---|---|
| 2.1 model functional match | PASS - 251 writes / 496 quanta; placements PF8 D, PF10 L, PF12 R, PF7 U, PF9 / PF9, PA2, PF12 R, Q |
| Physical timing gate <= 1,000 ms | PASS - max 942 ms, median 300, p95 438; principal mean 150.528 ms (T = 150) |
| Old 2.0 mapping rejected | PASS (model mismatch at gameplay AID 3, PF11) |
| PF12-ignored mapping rejected | PASS (mismatch at AID 2, PF12) |
| PF11-as-Right mapping rejected | PASS (mismatch at AID 3) |
| PF12 bare AID, no ENTER; moves Right | PASS (x 2) |
| PF11 bare AID, not Right, does not quit | PASS (x 2) |
| PF1-PF24 sweep, no PF key quits | PASS |
| Pause / resume, PA2 | PASS |
| Q alone does not quit (Q hold) | PASS - 11 game writes, 0 inbound records in the hold |
| Q + ENTER quits | PASS - `QUIT`, `TURNS 025`, `SCORE 0250`, `LIVES 3`, `QUANTA 0000496`, `***` |
| Return to the ISPF Command Shell | PASS (bare closure ENTER `7D C95D`) |

Q-hold observation: the typed Q remained in `COMMAND ===>`; no host input during the hold; direct ENTER (no
fallback); the inbound record carrying Q: `7D 6F5B 11 6FD9 D8`.

Accepted evidence (~/Documents/Worktrees/Pacman-zOS-raw/zos11, read-only): zos11-Z11-attempt3.trace 686,391 bytes
`3a6e7c6513de639d6f44243d8a90aacd57b8d500d233f5c5a0c655c2428e6464`; zos11-Z11-attempt3-drive.jsonl 5,932 bytes
`4c8aa57b7e75b4516fe458053eaf261f340c618e7f07887ad1d6ec26b0ed6ee7`; zos11-Z11-attempt3-check.txt 2,322 bytes
`388785b37cd97648fd93e47240307e7fb53f46c8257167de383ff55031339483`. Attempt 1 / 2 files kept unchanged beside them
(hashes in zos11-Z11.sha256 / zos11-Z11-attempt2.sha256). Note: the attempt 1 document labels the platform
"z/OS 2.5"; the value of record is the z/OSMF report above (`05.29.00`), the attempt 1 file is left as recorded.

## 6. Production data
`Z00000.PACMAN.DATA(HISCORE)` = `0000980 PACHS001 001`, read-only before and after every step (2A, 2B, each live
attempt); no job or live run allocated it.

## 7. Final installed state
| Dataset / member | State |
|---|---|
| Z00000.PACMAN.LOAD(PACMAIN) | 2.1-zos = RZ21.LOAD(PACMAIN), binary `798596b94ec2d960581a8dd5947d79288bfdb51e92bbbca728b6340d723a5386` |
| Z00000.PACMAN.CLIST(PACMAN) | 2.1-zos = RZ21.CLIST(PACMAN), `49d6e26d644f28720e5ab838ee5ebaeb3c92da117dd965145f7cf44d0d93dcbd`, ARROWS = PF7/8/10/12 |
| Z00000.PACMAN.RZ21.* | the 2.1-zos build of record (COBOL 10, COPY 6, ASM 3, OBJ 13, LOAD 1, CLIST 1) |
| Z00000.PACMAN.RZ.LOAD(PACMAIN) | 2.0-zos program, unchanged - program rollback |
| Z00000.PACMAN.PRV20.CLIST(PACMAN) | the 2.0-zos CLIST - CLIST rollback |
| Z00000.PACMAN.RZ.* / PRV.CLIST / LOAD(PACZ6D) | unchanged (2.0-zos build of record, older rollbacks) |
| Z00000.PACMAN.DATA(HISCORE) | `0000980 PACHS001 001` |

## 8. Closure
No z/OS access during closure (documentation, release folder and tags only). Tooling of record: zos11_release.py,
zos11_live.py (6d04b6f); frozen ZOS-5 / ZOS-6 / ZOS-10 tools = zos-10.
