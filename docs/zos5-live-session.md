# ZOS-5 live full-screen session - procedure for final review (nothing executed)

Design: docs/zos5-design.md, decisions approved by the user 2026-10-16 (one session; games
A / B / C in this order and no other; the trace is the primary evidence, PrintText secondary; checker before the
session; 120 x 30 is the window, the reply decides the canvas; no batch, rebuild, source / CLIST change or z/OS write).
Installed baseline under test (tag zos-4): Z00000.PACMAN.LOAD(PACMAIN), CLIST(PACMAN) (Z3 + Z2), CEEOPTS.

## 0. Before the session (read-only)
1. Local: `python3 tests/test_zos_tools.py` (section 19: the checker, its fixtures, model = oracle 310 TSD45 / TSD48 /
   TSD28) - PASS.
2. z/OS, once, immediately before the session: `python3 tools/zowe/zos5_precheck.py` - PASS (the zos-4 closure state:
   CLIST(PACMAN) SHA-256 f8989cfa..., PACSRCT template, CEEOPTS exact, PACMAIN / PACZ2D attributes). Any FAIL: no
   session.

## 1. Terminal and logon (no trace yet)
- macOS Terminal window sized to **120 x 30 before connecting**; never resized while connected.
- `c3270 -model 2 -oversize auto -scriptport 4001 198.51.100.200:623`
  (the ZOS-4 launch + the local script port, which only accepts connections from this Mac).
- `logon Z00000`, password typed by the user (plain TN3270E). ISPF Primary Option Menu.
- Option `6` (ISPF Command Shell), exactly as in ZOS-4. (Correction, user 2026-10-16: `=X` + log disposition 3 ends the
  whole TSO session on this logon procedure - no native READY is reachable; that attempt had no trace and ran no game,
  so it is not a ZOS-5 live attempt.)

## 2. Trace on (in the ISPF Command Shell only)
In a second Terminal tab:
```
mkdir -p ~/zos5-live
```
```
x3270if -t 4001 'Trace(On,/Users/usuario/zos5-live/zos5-live.trace)'
```
c3270 starts the file with its settings, a replay of the telnet state and a dump of the current (option 6) screen,
then ` Data stream:`; the logon is not in it (it happened before). The checker treats everything before that marker as
non-data and only audits it.

## 3. Games (type each line exactly, then ENTER; `·` = nothing typed)
Game A - MOVES / oracle 310 TSD45 - on the option 6 command line:
```
EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'RULES(CLASSIC) PLAY(TURN) SOUND(NO)'
```
PARM `TSO AI1 1 NAAAPAAATNC01NP`. Then: `R` `R` `U` `L` `L` `L` `D` `D` `R` `X` `r` `R` `R` `D` `Q`
(expected LAST field: MOVED, MOVED, BLOCKED, MOVED, MOVED, BLOCKED, MOVED, MOVED, MOVED, -, MOVED, MOVED, MOVED,
BLOCKED; `X` shows `INVALID COMMAND X`; `Q` shows the QUIT banner).
Game B - TSORDR / TSD48 - after the clean return to the ISPF Command Shell, the same command; then: `R`; **CLEAR** (the screen blanks; nothing
else); **PA2** (the 120 x 27 game screen must come back exactly); `D` (BLOCKED); `Q`.
Game C - TSORDR / TSD28 - after the clean return to the ISPF Command Shell:
```
EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC) RULES(CLASSIC) PLAY(TURN) SOUND(NO)'
```
PARM `TSO AI1 1 NYYAPGAATNC01NP`. Then: `R`; `·` (empty ENTER = redraw); `D` (BLOCKED); `Q`.
Pace is free: waiting only adds animation ticks, which the checker accounts for. Do not press any other key (PF keys,
PA1, ATTN, SysReq) during a game.

## 4. Trace off, logoff, preservation
After game C's clean return to the ISPF Command Shell (still in option 6):
```
x3270if -t 4001 'Trace(Off)'
```
Then leave ISPF normally (`=X`, log disposition as usual) - this ends the session on this logon procedure. Preserve the raw trace immutably (it stays outside git):
```
shasum -a 256 ~/zos5-live/zos5-live.trace > ~/zos5-live/zos5-live.trace.sha256
```
```
chmod a-w ~/zos5-live/zos5-live.trace ~/zos5-live/zos5-live.trace.sha256
```
Optional (secondary) screen captures at the milestones only - A first screen, A after `X`, B after PA2, C first
screen, each while it is shown:
```
x3270if -t 4001 'PrintText(html,file,/Users/usuario/zos5-live/A1.html)'
```
(names A1, A2, B1, C1).

## 5. Expected significant screens (from the model; byte-level truth = the checker)
Game A and B, first screen (120 x 27, wide layout, maze rows 4-23 / columns 21-100): title yellow, HUD turquoise
(SCORE / PELLETS / TURN / LAST / STATE, lives as three yellow Pac-Man icons), walls blue box-drawing (GE), pellets
white, Pac-Man yellow half-block sprite at the top left, the ghost red at the bottom right, keys green, `COMMAND ===>`
green on row 26:
```
02|                                                     P A C - M A N
04|                    ┌──────────────────────────────────────────────────────────────────────────────┐
05|  SCORE   0000      │  ┌────────────────────────────────┐      ┌────────────────────────────────┐  │  GHOSTS  AI1
06|                    │  │▄█▀  •   •   •   •   •   •   •  │      │ •   •   •   •   •   •   •   •  │  │
07|  PELLETS 100       │  │▀█▄                             │      │                                │  │  ∩ 19,09
09|  TURN    000       │  │    └──────┘    └──────────┘    └──────┘    └──────────┘    └──────┘    │  │
11|  LAST      START   │  │                                                                        │  │
13|  STATE   READY     │  │    └──────┘    │  │    └───────┐      ┌───────┘    │  │    └──────┘    │  │
15|  LIVES   ⊂ ⊂ ⊂     │  │                │  │            │      │            │  │                │  │
17|                    │  │    └──────┘    └──────────┘    └──────┘    └──────────┘    └──────┘    │  │  U D L R ENTER
18|                    │  │ •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •  │  │  Q QUIT  PA2
20|                    │  │ •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •  ▄°°▄│  │
21|                    │  │                                                                    █▀█▀│  │
23|                    └──────────────────────────────────────────────────────────────────────────────┘
26|                    COMMAND ===>
```
Game A after `X`: HUD `SCORE 0050`, `PELLETS 095`, `TURN 009`, `LAST R MOVED`, `STATE RUNNING`, ghost `16,09`; row 25
`INVALID COMMAND X` red, blinking. Game A end: row 25 ` QUIT ` green reverse banner for about 3 s, then line mode
`QUIT` / `TURNS 013` / `SCORE 0080` / `LIVES 3`, ISPF's `***` (ENTER), the ISPF Command Shell. Game B end: `QUIT` / `TURNS 002` / `SCORE 0010` / `LIVES 3`.
Game C, first screen (80 x 24 GS, no side HUD):
```
01|┌──────────────────────────────────────────────────────────────────────────────┐
03|│  │▄█▀  •   •   •   •   •   •   •  │      │ •   •   •   •   •   •   •   •  │  │
04|│  │▀█▄                             │      │                                │  │
17|│  │ •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •  ▄°°▄│  │
18|│  │                                                                    █▀█▀│  │
20|└──────────────────────────────────────────────────────────────────────────────┘
21| T000   START   X=02 Y=02 S=0000 L=100 G=19,09 V=3 ST=READY
23| COMMAND ===>      PACMAN GS  U D L R + ENTER   Q QUIT   PA2 REDRAW
```
Animation: Pac-Man's mouth and the ghost alternate about every 0.5 s while waiting (in A / B possibly only after the
first input: D28, recorded, not a failure).

## 6. STOP (end the session at once: no retry, no other game, nothing changed; trace off, logoff, report)
- any IGZ, CEE, IKJ, IEC, abend / ABEND, `PACMAN:` message, or `***` during a game;
- game A or B starting in line mode (a `T000 ...` text line instead of the full screen) - the query / parser /
  terminal path failed: STOP after game A, do not play B / C;
- a corrupted, misplaced or unreadable screen; the screen not restored by PA2 after CLEAR in game B;
- keyboard locked with no way to continue;
- no clean return to the ISPF Command Shell after a game (ISPF's `***` after the end lines + ENTER is the
  normal return); any unexpected panel or prompt.
Not a STOP: animation held until the first input (D28); a slower response; ISPF's `***` after the end lines.

## 7. After the session (local, read-only)
1. `python3 tools/zowe/zos5_live_check.py ~/zos5-live/zos5-live.trace --reply-out tests/qreply_zos_dyn.hex`
   - exit 0 PASS: as designed (A / B profile colour, highlight, GE = (1, 1, 1), canvas 120 x 27 from the reply; every
     game write = the model; end lines; the ISPF Command Shell);
   - exit 2 MODEL-IDENTICAL-OTHER-PROFILE: the writes match the model of the profile / canvas the reply announced, but
     not the designed one: reported for review, not accepted as the wide-layout PASS;
   - exit 1 FAIL: framing (TN3270E header, flags, SEQ-NUMBER, responses, telnet commands, truncation) or game failure,
     with the first reason.
2. Audit before anything is committed: the raw trace is never committed; the checker reports the words of the start
   dump to review (LOGON / PASSWORD / IKJ567xx) and fails on LOGON / PASSWORD text inside the data stream; the derived
   report, the reply hex and the reviewed PrintText captures are what may go into docs/evidence/zos5-fullscreen.md.
3. Evidence: docs/evidence/zos5-fullscreen.md (trace SHA-256, checker report, user observations, z/OS capability table).
