# ZOS-11 step 2A - 2.1-zos build under a new prefix (D46) - evidence (2026-10-21)
Design: docs/zos11-design.md. Tool: tools/zowe/zos11_release.py (successor of the frozen zos10_release.py; decks
jcl/zos/PACZ11AL / BL / C1 / C2). Source of record `35b803e30011fed7427b2f9c5d3492530d985d20` (tooling commit c9dfc28
on top; src unchanged). Host: IBM Z Xplore, z/OSMF S0W1.DAL-EBIS.IHOST.COM:10443, z/OS 05.29.00, userid Z00000 (Zowe
profile `zosmf`, credentials in the Zowe secure store). Spool and downloads stay outside git (`build/zos/`). Every job
submitted once with tools/zowe/zos_submit.py; no DELETE, purge or retry. **Scope stops before promotion.**

## 1. Preflight (read only)
- Local: every uploaded file (19 sources + src/zos/PACMAN.clist) = its blob in 35b803e; src tree clean; PACINPT has
  `IF WS-V = 124` once and no `IF WS-V = 123`.
- 26 Z00000.PACMAN.* datasets; none named or under `Z00000.PACMAN.RZ21`; pattern `RZ21.*` lists nothing. Prefix RZ21
  (z/OS release 2.1) chosen: unused, distinct from RZ (2.0-zos build of record) and every existing qualifier.
- Installed LOAD(PACMAIN) and RZ.LOAD(PACMAIN) binary SHA-256 `306d9736...0c64` (= 2.0-zos); installed CLIST(PACMAN)
  = the ZOS-10 closure read (`a437082a...`), `ARROWS = PF7/8/10/11`.
- RZ.OBJ downloaded read only: 13 images = the ZOS-10 recorded SHA-256 (build/zos/Z10/z10obj-sha256.txt).
- HISCORE read only: `0000980 PACHS001 001`.

## 2. Jobs
| JOB | Deck | Purpose | Result |
|---|---|---|---|
| JOB09441 | PACZ11AL | IEFBR14: RZ21.COBOL / COPY / ASM / OBJ / CLIST (PDSE FB 80), RZ21.LOAD (PDSE U), DISP=(NEW,CATLG,CATLG) | ALLOC CC 0000; 4 x IGD01007I (site ACS space reduction, as ZOS-1 / ZOS-10) |
| - | upload | 10 COBOL, 6 COPY, 3 ASM, CLIST(PACMAN) render into empty RZ21 libraries | 20 / 20 byte-identical on read-back |
| JOB09451 | PACZ11BL | IGYCRCTL x 10, ASMA90 x 3, IEWBLINK -> RZ21.LOAD(PACMAIN) | COB1-10 0000, ASM1 0000, ASM2 0004 (frozen C3: ASMA303W + ASMA435I only), ASM3 0000, LINK 0000; tools/zowe/zos11_release.py --check BL PASS |
| JOB09488 | PACZ11C1 | RUN1 RUN6 TSO1-TSO6 on RZ21.LOAD | 8 steps CC 0000; each = oracle 307 + model; 2,572 lines; = PACZ10C1 JOB04862 byte for byte |
| JOB09491 | PACZ11C2 | RTT2 N1 G3T7 on RZ21.LOAD | 3 steps CC 0000; RTT2 = oracle 310 + model, N1 = model, G3T7 = oracle 311 + model; 1,163 lines; = PACZ10C2 JOB04864 |
Dataset audit (JES listings): BL reads RZ21.COBOL / COPY / ASM, writes RZ21.OBJ (13) and RZ21.LOAD; C1 / C2 STEPLIB
RZ21.LOAD only; no RZ, installed LOAD / CLIST, PRV, DATA, PACHS or HISCORE reference in any deck or job log.

## 3. Build
- Compiler Enterprise COBOL 6.5.0 P260714 (= ZOS-10); compile statistics of all 10 modules = JOB04820 (PACINPT 394
  source records, 79 data / 184 procedure statements). NOSOURCE build: the source proof is the byte-identical upload of
  PACINPT (`IF WS-V = 124`) plus the object literal below.
- Binder: INCLUDE x 13 (release order), ENTRY PACMAIN, NAME PACMAIN(R), AMODE 24, RMODE 24, RENT, REUS, EXCEEDS 16MB
  NO, IEW2008 / 2278 / 2322 only, RC 0. RZ21.LOAD(PACMAIN): AC 00, RN RU, size X'000204A0' (= 2.0-zos); binary SHA-256
  `798596b94ec2d960581a8dd5947d79288bfdb51e92bbbca728b6340d723a5386`.

## 4. Object gate against the frozen 2.0-zos build (RZ.OBJ, JOB04820)
| Module | Verdict |
|---|---|
| PACMAIN PACGAME PACMAP PACPLAT PACSCR PACQRY PACTSO PACFSIO PACHSIO | IDENTICAL-MODULO-TIMESTAMP |
| PACAI PACDISP PACRT | EQUIVALENT-DMCODE-RECOMPRESSED (decompressed D_MCODE identical; ZOS-10 decision B) |
| PACINPT | D46-ONLY: one byte, logical TXT record 36 byte 515, X'3C' -> X'4C' = the RT-TSC literal table `00247C 00248C 00122C 00123C 00249C 00110C` -> `... 00124C ...`; D_MCODE decompressed identical (87,882 bytes); under the 2.0 rules alone DIFFERENT (the change is present) |
D46 rule (zos11_release.d46_eq): after the frozen timestamp spans and the D_MCODE rule, exactly one loaded byte may
differ and it must be the table literal 123C -> 124C; selftest: 15 injected faults detected (125C, a second table
literal, a second 123 -> 124 outside the table, the change missing, any loaded byte in another module, deck mutants).

## 5. Program-object image (supplementary; RZ.LOAD vs RZ21.LOAD binary, 745,472 bytes each)
- Up to offset 143,380 (headers and program text): 77 differing bytes = the D46 literal (offset 45,321, X'3C' -> X'4C',
  in the same literal table, found once in each image); the 10 COBOL compile timestamps (20261020 13:28:xx -> 20261021
  08:28:xx); the binder IDR (date 2026293 -> 2026294, time, jobname PACZ10BL -> PACZ11BL); header and class-directory
  size / offset fields of the no-load classes (+X'1C' / +X'1E', from the recompressed D_MCODE lengths).
- From 143,380: the 10 compressed no-load D_MCODE streams - every one decompresses to identical bytes (3 recompressed:
  PACAI +48, PACDISP -17, PACRT -2 bytes, shifting what follows); 20-23 byte stream headers differ only in lengths; the
  trailing 85 KB of binder tables (13 IDR dates 293F -> 294F, the bind date / time again, offset tables) differ by those
  shifts. These no-load tables are not decoded value by value; they are outside the program text and the object gate
  (section 4) is the comparator of record, as in ZOS-10.

## 6. Final state (read only)
- Added exactly six datasets (26 -> 32): Z00000.PACMAN.RZ21.ASM / CLIST / COBOL / COPY / LOAD / OBJ; nothing removed.
- Installed LOAD(PACMAIN) and RZ.LOAD(PACMAIN) still `306d9736...`; installed CLIST and RZ.CLIST still `a437082a...`;
  PRV.CLIST still `6e0a68ec...`; RZ.OBJ / LOAD / CLIST member lists unchanged.
- HISCORE `0000980 PACHS001 001` (read only, before and after).
- No promotion, no installed-library or CLIST change, no RZ write, no live gate, no tag / release, no push.
