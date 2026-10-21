# ZOS-11 step 2C - live gate, attempt 2 (2026-10-21) - checker FAIL (not accepted); classified: no product failure
Driver fix 67dfa21 (Q decision from the `COMMAND ===>` field content, not the cursor; regression tests in
test_zos11 section 6). Pre-live read-only gate 18 / 18 PASS (LOAD `798596b9...`, CLIST `49d6e26d...` ARROWS =
PF7/8/10/12, RZ / RZ21 / PRV20 unchanged, HISCORE `0000980 PACHS001 001`); attempt 1 files = their hashes; same
dedicated c3270 (script port 4012, 27 x 120), ISPF Command Shell, trace started after the logon. Run once,
18:50:48-18:52:17. Evidence outside git (~/Documents/Worktrees/Pacman-zOS-raw/zos11, read-only):

| File | Bytes | SHA-256 |
|---|---|---|
| zos11-Z11-attempt2.trace (Trace(Off) before hashing) | 785,064 | `c6aa175a44574c2bff8e92ad78244b2859ea52cf2a0deb019c8a5e6fadec6601` |
| zos11-Z11-attempt2-drive.jsonl | 5,932 | `f3bf849b36559f60f6eeb83a22956a4020db8ca4b44f69df70606707366923da` |
| zos11-Z11-attempt2-check.txt | 2,380 | `6ce6155a478e2646673b0b99c2768d0c8d1b01aba697c4222a53b4d26e662eb1` |

## Driver
33 actions, `ZOS-11 DRIVER: plan sent completely`, back at the ISPF Command Shell. Q decision: the field held `Q` ->
direct ENTER (variant A), no fallback.

## Checker: ZOS-11 LIVE GATE FAIL
PASS: PF12 AID-only; PF11 + PF1-PF24 sweep AID-only; the game wrote on after every PF AID; end lines `QUIT`,
`TURNS 031`, `SCORE 0310`, `LIVES 3`, `QUANTA 0000500` after the last ENTER; controls (each a genuine model
mismatch): 2.0 map fails at gameplay AID 3, PF12 ignored fails at AID 2, PF11 as Right fails at AID 3.
FAIL: (1) model criterion - check() state ENVIRONMENT/TIMING BLOCKED; (2) the Q-hold criterion.

## Classification
1. Model / timing: every functional placement matched the 2.1 model (PF8 D, PF10 L, PF12 R, PF7, PF9 / PF9, PA2,
   PF12 R, Q; 253 writes, 500 quanta, principal mean 150.29 ms for T = 150); the only blocked gate is the physical
   max gap 1,351 ms > 1,000 ms (diagnostics: 2 long gaps with BID latency > T). Environment (shared host / network),
   not a product verdict - but not a PASS.
2. Q-hold rule: checker window defect. The rule counts inbound records in [TYPEQ sent, ENTER sent); the driver
   stamps `sent` after Enter() returns, so the window contains the ENTER that transmits the Q. Trace: TYPEQ 18:52:10.065;
   ENTER action unlocked 18:52:13.180; inbound `7D 6F5B 11 6FD9 D8` (ENTER + field `Q`) at 18:52:13.190; `sent`
   18:52:13.524. In the real hold (10.065-13.180): 0 inbound records, 11 game writes. Attempt 1 had the same latent
   defect. Any run fails this rule until the window ends at the ENTER's `unlocked` time (or the inbound is excluded).

## Q-hold observation
Q typed, no ENTER for ~3.1 s: no host input, 11 game writes, Q stayed in the game input field (row 25, column 33);
direct ENTER transmitted it (record above) and the game quit; the closure ENTER (`7D C95D`, bare) answered `***`.

## Safety
HISCORE after: `0000980 PACHS001 001`. No job, no promotion, no z/OS write; installed LOAD / CLIST, RZ, RZ21, PRV20
untouched; attempt 1 evidence unchanged (hashes verified); no tag, no push.
