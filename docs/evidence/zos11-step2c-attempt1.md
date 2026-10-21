# ZOS-11 step 2C - live gate, attempt 1 (2026-10-21) - FAIL (tooling defect), not accepted
Installed 2.1-zos (LOAD(PACMAIN) `798596b9...5386`, CLIST `49d6e26d...`, ARROWS = PF7/8/10/12), pre-live read-only
gate 18 / 18 PASS, HISCORE `0000980 PACHS001 001`. Session: dedicated c3270 `-model 2 -oversize auto -scriptport 4012`
+ keymap RIGHT = PF(12), 198.51.100.200:623, IBM-DYNAMIC max 27 x 120, logged on by the user, ISPF Command Shell. Trace
started after the logon. Driver `tools/zowe/zos11_live.py --drive 4012` (unchanged since 35b803e), invocation
`EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) SOUND(NO)'`. Evidence outside git
(~/Documents/Worktrees/Pacman-zOS-raw/zos11, read-only):

| File | Bytes | SHA-256 |
|---|---|---|
| zos11-Z11.trace (final: Trace(Off) before hashing) | 1,851,096 | `801a77358c01e8a055fcfb6b5aa91cf866795dddff4d2d030c2bf26c49679ae7` |
| zos11-Z11-drive.jsonl | 5,935 | `73f9eabc8bbdce575568649b8d61ca5d6cefbb4bd6e0c5627fcda080ad73cd92` |
| zos11-Z11-check.txt | 6,979 | `73eb2edfc24fbff2e18b148631853d628c01d3e0ed8b59e2a3f3ec48b7ad6d8f` |
| zos11-Z11-diag-relabelled-drive.jsonl (diagnostic only) | 5,932 | `25272bf733d4015e10cc455fbb0aa6411b822f9d4643fb6e1c356171a77f6025` |
| zos11-Z11-diag-relabelled-check.txt (diagnostic only) | 1,536 | `8b7f115b73e7ff93331ba7f9cc7ee83259ed9df1f5cc35a27bda1fa80b25e7fc` |

## Result
Driver: 33 actions sent (EXEC, ENTER, PF8, PF10, PF11, PF12, PF7, PF9, PF9, PA2, PF1-PF6, PF11, PF13-PF24, PF12, TYPEQ,
"ENTER()", Q), then `ZOS-6 DRIVER STOP: *** not on the screen within 60 s` (no retry). Checker: **ZOS-11 LIVE GATE
FAIL** - PASS: PF12 AID-only, PF11 + sweep AID-only, the game wrote on after every PF AID; FAIL: the model comparison
(driver log != plan: no closure ENTER), the Q hold rule, the end rule. The three "control fails" lines are vacuous
(same plan-mismatch error), not discrimination evidence.

## Classification: driver defect in the Q-variant probe (zos11_live.drive), not a product failure
Decoded from the trace (inbound records, host writes):
- TYPEQ 18:22:30.102 -> 18:22:33.18: **no inbound record**, 11 game writes; the typed Q stayed in the input field.
- 18:22:33.198 inbound `7D 6F5B 11 6FD9 D8` = ENTER with field data `Q` (X'D8'): the driver's probe (one character
  left of the cursor) read no Q - the game's writes move the cursor - so it chose variant B and logged a "blank
  ENTER", but that ENTER carried the surviving Q.
- The game quit at once: full screen STATE QUIT, then `QUIT TURNS 031`, `SCORE 0310 LIVES 3 QUANTA 0000505`, `***`.
- 18:22:36.824 the fallback's `Q` + ENTER (`7D C95E 11 C95D D8`) answered ISPF's `***`; ISPF returned to the Command
  Shell (no `Q` command in the history). The driver then waited for a `***` already consumed -> STOP.
- Diagnostic re-check with the trace-derived labels (variant A + closure): still FAIL, because the closure record
  carries `Q` (the frozen rule requires a bare ENTER at `***`). The attempt therefore cannot be accepted; the model
  comparison and the three model controls were not evaluated by this trace.

## Q-hold observation (z/OS 2.5 / c3270 4.5)
Typed Q without ENTER: no host input during the 3 s hold, the game kept writing (11 writes), the Q survived in the
field (it was transmitted with the next ENTER), and Q + ENTER quit normally. Same behaviour as TK4- in MVS-10.

## Safety
HISCORE read after the run: `0000980 PACHS001 001`. No job, no promotion, no z/OS write; RZ, RZ21, PRV20, installed
LOAD / CLIST untouched; no tag, no push.
