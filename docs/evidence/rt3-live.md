# MVS-RT RT3 live validation in c3270 - PASS (user, 2026-10-11)
Build: Hercules JOB 226 (deck RT, tests/test_rt.py PASS, docs/evidence/rt3-build.txt); CLIST JOBs 225 (column-72 fix)
and 227 (PLAY(REALTIME) default). Terminal: `TYPEAHEAD=false tools/c3270_rt.sh ~/rt3-live2.txt` (120x27 IBM-DYNAMIC,
arrows -> PF7/8/10/11, typeahead off), game started by `python3 tools/rt_play.py` (EXEC ... 'PLAY(REALTIME)', temporary
keymap `pacgame` P -> PF9 on while the game ran: enabled 19:01:46.348, cleared 19:03:17.651 at READY).
Traces stay outside the repository (they contain the logon): `~/rt3-live2.txt` (this run), `~/rt3-live1.txt` (failed
integration, below). Analysis: `python3 tools/c3270_rt_game.py ~/rt3-live2.txt --from 190145` (from the game's first
screen on; inbound records by AID only).

## User checklist (live)
| Check | Result |
|---|---|
| Pac-Man waits at rest; one arrow starts continuous movement, no ENTER | PASS |
| Ghosts move automatically | PASS |
| No persistent X Wait; keyboard restored | PASS |
| Buffered turn at an opening | PASS |
| Immediate reversal | PASS |
| Hold an arrow, release, new direction at once (no stale backlog) | PASS |
| P (PF9) pause: PAUSED shown, maze frozen | PASS |
| Arrow while paused does not break the keyboard | PASS |
| P resume: clean, no catch-up burst | PASS |
| PA2 redraw | PASS |
| Caught by a ghost: about 1.5 s freeze, respawn, waits for a new direction | PASS |
| Q + ENTER: QUIT banner, end lines with QUANTA, READY | PASS |
Overall: REALTIME gameplay works and is playable.

## Trace (c3270_rt_game.py, game 19:01:45.861 - 19:03:14.401)
```
outputs 307 {'FULL': 3, 'PART': 274, 'RESTORE': 30}
running output gaps ms n=302 min=61 med=150 p95=160 max=236 | < 20 ms: 0 | > 225 ms: 1
before the first AID: outputs delivered 1
AIDs 44 {'DOWN/PF8': 5, 'ENTER': 1, 'LEFT/PF10': 10, 'PA2': 1, 'PAUSE/PF9': 2, 'RIGHT/PF11': 18, 'UP/PF7': 7}
keyboard lock per AID ms n=44 min=1 med=87 p95=131 max=147
pause 1880 ms; after resume: first frames at +152, +309, +459, +610 ms
```
- 150 ms quantum: median gap 150 ms, p95 160 ms while running; one isolated late wake (236 ms) followed by a 61 ms gap
  back onto the absolute schedule; no sustained lateness, no bursts (< 20 ms gaps: 0).
- Keyboard restore: every one of the 44 AIDs was followed by a host write within 147 ms (< one quantum); 30 of the 307
  writes were the restore-only `F1 C2 28 00 00` (quanta without a visible change).
- Press-to-start / D28: only the first full screen before the first arrow (41 s of blocking read, no polling); the
  first arrow started the clock and the frames flowed at once.
- Pause: PF9 x2 (pause / resume); 1.88 s paused with no frames (blocking read); after the resume frames at +152, +309,
  +459 ms: no catch-up.
- Held keys: 51 key events, 18 of them autorepeats; 44 AIDs reached the host (7 autorepeats dropped while the keyboard
  was locked, typeahead off): no backlog.
- Full screens: the first screen, the PA2 redraw (Erase/Write Alternate) and the QUIT end screen; a DIED screen at
  +74.1 s (death freeze); CLEAR not used.

## Failed integration attempts (historical defect evidence, not acceptance evidence)
1. 2026-10-10, `~/rt3-live1.txt`: the installed CLIST CALL line was 73 columns; TSO cut the closing quote (columns 73-80
   are sequence numbers): `ENDING QUOTE ASSUMED`, a `***` hold, and PACMAN's capability query read the wrong input ->
   line-mode TURN. Fixed (PARM built with SET &P; column-72 check in tests/test_rt.py; rt_play.py stops on `***`).
2. 2026-10-11, `~/rt3-live1.txt` (second game): REALTIME started, but every AID left c3270 in X Wait. Frames came 23,
   45, 88, 175, 350, 719, 1474 ms ... up to 52 s apart: PACTSO DLWT computed the remainder in R0 while M multiplies R1
   (still NOW), so each wait lasted about the time since the start. Every frame that did arrive carried the restore bit
   and unlocked the keyboard at once - the restore logic was right, the clock was not. Fixed (LR 1,0, as in the E14
   probe); new batch clock test PACTSOT in the RT deck (JOB 226: 20 deadlines 150 ms apart, wake lateness <= 13 ms).
