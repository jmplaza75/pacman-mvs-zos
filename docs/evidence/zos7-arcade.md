# ZOS-7 ARCADE - dry-run and live acceptance evidence (2026-10-19)

Status: ZOS-7 COMPLETE / PASS (validation only). Next phase: ZOS-8 Services (not started). MVS (2.0-mvs-max) frozen.
Design and decisions D1-D5: docs/zos7-design.md. Installed state under test (zos-6, unchanged): LOAD(PACMAIN) = the
ZOS-6 program, LOAD(PACZ6D) its test member, CLIST(PACMAN) the ZOS-6 CLIST (default RULES(ARCADE), PRESENT(EVERY)).
**No production source change was required**: no COBOL, copybook, assembler or CLIST file changed in ZOS-7; no build,
no promotion. Tools: tools/zowe/zos7_scen.py, zos7_drive.py, zos7_live_check.py, zos7_dry.py, tests/zos7_fixture.py,
tests/test_zos_tools.py section 24; the ZOS-6 / ZOS-5 acceptance tools imported unchanged.

## Dry runs (PGM=PACZ6D, no PACHS DD: no high score read or written)
| Job | Steps | Result | Output |
|---|---|---|---|
| PACZ7DR1 JOB09981 | E3 N6 F6 N7 F7 | CC 0000, every step RC 0000, comparator PASS | zos7-pacz7dr1-check.txt |
| PACZ7DR2 JOB09992 | N8 F8 N9 F9 NL2 FL2 T1 | CC 0000, every step RC 0000, comparator PASS | zos7-pacz7dr2-check.txt |
Every TSD step = its model byte for byte (frames, transport lines, end lines). E3 (G2RPAU, PRESENT(EVERY), the PARM of
oracle 311 G3R7) = the oracle 311 block line for line: Z4 left ARCADE EVERY output unchanged. COALESCED steps: stride 2
NORMAL / 3 FAST, strictly increasing. Coverage under COALESCED at both speeds: death (N6 N7 N8 N9 NL2 / F6 F8 FL2),
level clear (N7 / F7 S2XLC), extra life (N8 / F7 F8 S2XLD), ghost chain (N9 / F9), ghost eaten (NL2 / FL2), final death
(N6 NL2: 6 writes / F6 FL2: 7 writes, consecutive, right before the end screen). NL2 / FL2 / T1 = the exact live cards
of L2 / L3 / L1 (LOST 0000510 1 ghost; QUIT 0010780 LIVES 4).

## High-score state (decision D3; read only)
Before the live session: Z00000.PACMAN.DATA = PDS FB 80/80 (ZOS-1), member directory empty, HISCORE absent (high score
0; checker `--hiscore ABSENT`). After L1, L2 and L3: member directory still empty. Every live case started at LEVEL >= 2
(not eligible): nothing was created, reset or written. ZOS-8 note: DATA was allocated SPACE=(TRK,(1,1,5)) and lists
`used 100` (the primary track holds the directory, one secondary track available) - check before the first save.

## Live acceptance (one c3270 session, ISPF option 6, 120 x 27 IBM-DYNAMIC, script port 4012)
EXEC operands (RULES(ARCADE) = the CLIST default, not typed - approved): L1 `AI(0) LEVEL(13) PLAY(TURN) ANIM(NO)
SOUND(NO) PRESENT(COALESCED)`; L2 `AI(0) LEVEL(2) PLAY(REALTIME) SOUND(NO) PRESENT(COALESCED)`; L3 the same +
`SPEED(FAST)`. One run each, in order L1 -> L2 -> L3, each after the previous PASS.
| Case | Trace SHA-256 (raw, outside git) | Checker | Verdict |
|---|---|---|---|
| L1 TURN | ae8c0de5aaa6d7706112ca0981c0fa77ededf0aa157e0a8671e475b8634bd203 | zos7-l1-check.txt | PASS (rc 0) |
| L2 NORMAL | ac61a444592c196573163a6b3da77fb0b3297467a4f9450ce7ebd3a435ed7375 | zos7-l2-check.txt | PASS (rc 0) |
| L3 FAST | 138b45e19fe25f630ebef253cbba7ca7d31845940a0bb265d25edd7753a23efc | zos7-l3-check.txt | PASS (rc 0) |

| Fact | L1 TURN | L2 NORMAL | L3 FAST |
|---|---|---|---|
| Game writes = model | 78 (77 commands + end screen) | 224 | 179 |
| Logical quanta | - | 431 | 509 |
| Gameplay writes / stride | one screen per command | 216 / 2 | 170 / 3 |
| D1 final-death writes | - | 6, consecutive, before the end screen | 7, consecutive, before the end screen |
| Freeze runs / mutants | - | [10, 10] / 9, 11 rejected: DISCRIMINATED | [12, 12] / 11, 13 rejected: DISCRIMINATED |
| F1 C3 CONTROL records | 0 | 1 (start PF8) | 1 (start PF8) |
| Median / p95 / max interval | no timing gate | 301 / 412 / 510 (511 running) ms | 376 / 507 / 562 (645 running) ms |
| Backlog delta | - | -5.2 ms | -3.4 ms |
| Input reactions | - | 348 612 550 487 553 694 511 621 ms, median 551.5 | 348 590 467 615 544 415 473 625 ms, median 508.5 |
| End lines | QUIT, TURNS 0000076, SCORE 0010780, LIVES 4, GHOSTS EATEN 0000, FRUITS EATEN 002, LEVEL 013 | LOST, TURNS 0000106, SCORE 0000510, LIVES 0, QUANTA 0000431, GHOSTS EATEN 0001, FRUITS EATEN 000, LEVEL 002 | LOST, TURNS 0000106, SCORE 0000510, LIVES 0, QUANTA 0000509, GHOSTS EATEN 0001, FRUITS EATEN 000, LEVEL 002 |
| High-score lines | HIGH SCORE 0010780 LEVEL 013; START LEVEL 13: HIGH SCORE NOT RECORDED | HIGH SCORE 0000510 LEVEL 002; START LEVEL 02: HIGH SCORE NOT RECORDED | same as L2 |
Frozen ZOS-6 gates (gameplay writes only): NORMAL 280-320 / <= 450 / <= 1000 / backlog <= 100 / reaction <= 1000,
median <= 750; FAST 345-405 / <= 525 / <= 1000 / <= 100 / <= 1075, median <= 825 - all PASS, none tuned. Lateness
envelope (diagnostic only): L2 18 ms, L3 1 ms. Closure in every case: the end lines, `***`, one ENTER, the ISPF
Command Shell. Live event coverage (L2 and L3): both power pellets, fright, one ghost eaten with the 200 popup, eyes,
two in-game deaths with READY! and respawn, GAME OVER with the final-death sequence. L1: fruit, two keys, the extra
life at 10000 and the fourth life icon, the LEVEL 13 HUD.

## D1 final-death exception - confirmed on real z/OS
Dry runs (N6 NL2 / F6 FL2) and live (L2 / L3): exactly 6 (NORMAL) / 7 (FAST) writes, consecutive, after every gameplay
write and immediately before the one end screen, bytes and order = the model, no duplicate / extra frame. Timing,
information only (no gate, decision 2026-10-19): L2 gaps 115 175 113 114 115 ms (span 632, nominal 750); L3 gaps 115
177 114 114 115 182 ms (span 817, nominal 750); terminal arrival times include TN3270E delivery (BID latency median
~114 ms). Freeze-span proxy per in-game death, information only: L2 1412 / 1502 ms, L3 1573 / 1481 ms.

## Carried forward
ZOS-8: high-score writing / recovery / UNAVAILABLE / NOT SAVED live (and the DATA space note above), ESTAE and PACFSIO
C3 (E2), sound / alarm patterns live. ZOS-9/10: the full GP1 / GP2 / GP23 / RP batteries, HA6. Release default of
PRESENT: deferred (EVERY stays the CLIST default).
