# ZOS-11 step 2C - live gate, attempt 3 (2026-10-21) - ZOS-11 LIVE GATE PASS
Live tooling: driver fix 67dfa21 + checker fix 6d04b6f (HEAD 6d04b6f, no code change before the run); frozen ZOS-5 /
ZOS-6 / ZOS-10 tools = zos-10. Pre-live read-only gate 18 / 18 PASS: LOAD(PACMAIN) `798596b9...5386`, CLIST
`49d6e26d...` ARROWS = PF7/8/10/12, RZ (`306d9736...` / `a437082a...`), RZ21 (`798596b9...` / `49d6e26d...`), PRV20
(`a437082a...`) unchanged, HISCORE `0000980 PACHS001 001`; attempt 1 / 2 evidence = its hashes; dedicated c3270
(script port 4012, 27 x 120, 198.51.100.200:623) at the ISPF Command Shell; trace started after the logon.
Run once, 19:17:40-19:19:10: `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) SOUND(NO)'`, 33 actions,
`ZOS-11 DRIVER: plan sent completely`, back at the ISPF Command Shell.

| File (~/Documents/Worktrees/Pacman-zOS-raw/zos11, read-only) | Bytes | SHA-256 |
|---|---|---|
| zos11-Z11-attempt3.trace (Trace(Off) before hashing) | 686,391 | `3a6e7c6513de639d6f44243d8a90aacd57b8d500d233f5c5a0c655c2428e6464` |
| zos11-Z11-attempt3-drive.jsonl | 5,932 | `4c8aa57b7e75b4516fe458053eaf261f340c618e7f07887ad1d6ec26b0ed6ee7` |
| zos11-Z11-attempt3-check.txt | 2,322 | `388785b37cd97648fd93e47240307e7fb53f46c8257167de383ff55031339483` |

## Checker: ZOS-11 LIVE GATE PASS (check() state PASS, nothing blocked)
- 251 live writes = the COALESCED model with the 2.1 map, 496 quanta; placements PF8 D (1), PF10 L (12), PF12 R (39),
  PF7 U (51), PF9 pause (63) / PF9 resume (64), PA2 redraw (81), PF12 R (205), Q (498); post-resume writes normal.
- Timing: physical gap max **942 ms** (<= 1,000; median 300, p95 438); principal segment 289 quanta, mean 150.528 ms
  (T = 150), drift 152 ms; input reaction 331-773 ms (n 9).
- Controls (each a model mismatch): 2.0 map fails at gameplay AID 3 (PF11), PF12 ignored fails at AID 2 (PF12), PF11
  as Right fails at AID 3.
- PF12 (x 2), PF11 (x 2) and PF1-PF24 reached the host as AID-only records; the game wrote on after every PF AID.
- End: `QUIT`, `TURNS 025`, `SCORE 0250`, `LIVES 3`, `QUANTA 0000496`, `***`, closure ENTER (`7D C95D`, bare), ISPF
  Command Shell.

## Q hold
TYPEQ sent 19:19:03.189; ENTER action unlocked 19:19:06.362: 11 game writes, 0 inbound records; the field after
`COMMAND ===>` held `Q` -> direct ENTER (variant A, no fallback); inbound `7D 6F5B 11 6FD9 D8` (ENTER + field `Q`) at
19:19:06.376; the game quit.

## Safety
HISCORE after: `0000980 PACHS001 001`. No job, no promotion, no z/OS write; installed LOAD / CLIST, RZ, RZ21, PRV20
untouched; attempt 1 / 2 evidence unchanged; no tag, no release closure, no push.
