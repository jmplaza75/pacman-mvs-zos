# PACMAN 2.1-zos - release manifest (ZOS-11)
Identifies the z/OS release 2.1-zos and how it was built, verified, installed and accepted. Same host as 2.0-zos (IBM Z
Xplore, system S0W1, z/OSMF 198.51.100.200:10443), userid / HLQ Z00000. Every job ran once (no purge, no retry); spool
and downloads stay local (`build/zos/`, not committed); live traces stay outside git
(`~/Documents/Worktrees/Pacman-zOS-raw/zos11`). Decks in `decks/` are the decks of record (`@@HLQ@@` templates rendered
by `tools/zowe/zos_submit.py`, generated and audited by `tools/zowe/zos11_release.py`; no credentials anywhere - Zowe
secure store only). Evidence: `docs/evidence/zos11-release.md` (closure) and the step files it lists; design:
`docs/zos11-design.md`.

## Identity
| Item | Value |
|---|---|
| Release | 2.1-zos (annotated tags `zos-11` and `2.1-zos` on the ZOS-11 closure commit); 2.0-zos tags unchanged |
| Source of record | commit `35b803e30011fed7427b2f9c5d3492530d985d20`; `src/` unchanged after it; the 19 sources and the CLIST were uploaded from that tree and byte-verified on the host |
| Product change vs 2.0-zos | D46 only (the 2.1-mvs change, not a z/OS difference): `src/cobol/PACINPT.cob` RT-TSC `IF WS-V = 123` -> `124` (REALTIME Right PF11 -> PF12) + its comment; `src/zos/PACMAN.clist` help comment `ARROWS = PF7/8/10/11` -> `PF7/8/10/12` |
| Client keymap | `tools/c3270_rt.sh`: `<Key>RIGHT: PF(12)` (was PF(11)) |
| Live tooling of record | `tools/zowe/zos11_live.py` at 6d04b6f (driver Q-field fix 67dfa21, checker Q-hold window fix 6d04b6f); frozen ZOS-5 / ZOS-6 / ZOS-10 tools = `zos-10` |
| Toolchain | Enterprise COBOL 6.5.0 P260714, HLASM, IEWBLINK (= ZOS-10); build profile A (AMODE 24 / RMODE 24, RENT, LE ALL31(OFF) STACK BELOW) |
| Build of record | PACZ11BL JOB09451 into the new, empty `Z00000.PACMAN.RZ21.*` libraries: `RZ21.LOAD(PACMAIN)`, AC 00, AMODE 24, RMODE 24, RN RU, size X'000204A0', binary SHA-256 `798596b94ec2d960581a8dd5947d79288bfdb51e92bbbca728b6340d723a5386` |
| Installed program | `Z00000.PACMAN.LOAD(PACMAIN)` = IEBCOPY copy of `RZ21.LOAD(PACMAIN)` (PACZ11IP JOB09553); binary image identical (`798596b9...5386`) |
| Installed launcher | `Z00000.PACMAN.CLIST(PACMAN)` = `RZ21.CLIST(PACMAN)` = `src/zos/PACMAN.clist` of 35b803e rendered for Z00000.PACMAN (140 records, SHA-256 `49d6e26d644f28720e5ab838ee5ebaeb3c92da117dd965145f7cf44d0d93dcbd`); differs from the 2.0-zos CLIST in record 25 only (`ARROWS = PF7/8/10/12`) |
| Rollback | program `Z00000.PACMAN.RZ.LOAD(PACMAIN)` (2.0-zos, `306d973612be...0c64`, unchanged); CLIST `Z00000.PACMAN.PRV20.CLIST(PACMAN)` (the installed 2.0-zos CLIST, `a437082a...8ab3`, PACZ11PV JOB09545) and `RZ.CLIST(PACMAN)`; older: `PRV.CLIST` (zos-9), `LOAD(PACZ6D)` |
| Production data | `Z00000.PACMAN.DATA(HISCORE)` = `0000980 PACHS001 001`, unchanged (read-only checks before / after every step) |

## Build, verification, installation and acceptance of record (2026-10-21)
| Job / action | Deck | What | Result |
|---|---|---|---|
| (read-only) | - | preflight: RZ21 absent, installed = 2.0-zos, RZ.OBJ = ZOS-10 record, HISCORE | PASS |
| JOB09441 | PACZ11AL.jcl | allocate the 6 empty RZ21 libraries | CC 0000 (4 x IGD01007I site ACS rule, as ZOS-10) |
| (upload) | - | 19 sources + the CLIST render from 35b803e into RZ21 | 20 / 20 byte-identical |
| JOB09451 | PACZ11BL.jcl | 10 compiles, 3 assemblies, bind into RZ21.LOAD | COB1-10 / ASM1 / ASM3 / LINK 0000, ASM2 0004 (frozen C3 ASMA303W only); gate PASS |
| (local) | - | object gate vs the 2.0-zos build (RZ.OBJ, JOB04820) | 13 / 13: 9 identical modulo timestamps, 3 D_MCODE recompressed (decompressed identical), PACINPT D46-ONLY (one byte, `00123C` -> `00124C` in the RT-TSC literal table) |
| JOB09488 | PACZ11C1.jcl | candidate: RUN1, RUN6, TSO1-TSO6 | PASS, 2,572 lines = oracle 307 + models = PACZ10C1 |
| JOB09491 | PACZ11C2.jcl | candidate: RTT2, N1, G3T7 | PASS, 1,163 lines = oracles 310 / 311 + models = PACZ10C2 |
| JOB09545 | PACZ11PV.jcl | backup installed CLIST(PACMAN) -> new PRV20.CLIST | PASS, byte-identical (`a437082a...`) |
| JOB09553 | PACZ11IP.jcl | promote RZ21.LOAD(PACMAIN) -> LOAD (replace) | PASS, 1 of 1; installed = RZ21 (binary) |
| JOB09558 | PACZ11IC.jcl | promote RZ21.CLIST(PACMAN) -> CLIST (replace), after the IP gate | PASS, 1 of 1; installed = RZ21 = release render |
| JOB09560 | PACZ11ZD.jcl | AMASPZAP `DUMP PACMAIN ALL`, RZ21 and installed (read-only) | CC 0000, dumps identical - B_TEXT class only (see RELEASE-NOTES) |
| JOB09562 | PACZ11P1.jcl | installed: RUN1, TSO2, TSO6 | PASS, 566 lines = oracle 307 + models = RZ21 C1 = 2.0-zos P1 |
| (live) attempt 1 | - | Z11 live gate | FAIL - driver Q-field detection defect (diagnostic only) |
| (live) attempt 2 | - | Z11 live gate | functionally correct, ENVIRONMENT / TIMING BLOCKED (max gap 1,351 ms) (diagnostic only) |
| (live) attempt 3 | - | Z11 live gate, installed release | **ZOS-11 LIVE GATE PASS** (accepted) |

## Accepted live evidence (attempt 3, outside git, read-only)
| File | Bytes | SHA-256 |
|---|---|---|
| zos11-Z11-attempt3.trace | 686,391 | `3a6e7c6513de639d6f44243d8a90aacd57b8d500d233f5c5a0c655c2428e6464` |
| zos11-Z11-attempt3-drive.jsonl | 5,932 | `4c8aa57b7e75b4516fe458053eaf261f340c618e7f07887ad1d6ec26b0ed6ee7` |
| zos11-Z11-attempt3-check.txt | 2,322 | `388785b37cd97648fd93e47240307e7fb53f46c8257167de383ff55031339483` |

## Files
`SHA256SUMS` covers the 19 sources and the z/OS CLIST of 35b803e, the client launcher `tools/c3270_rt.sh`, and the 9
decks of record in `decks/` (each = the deck `tools/zowe/zos11_release.py` generates and audits).
