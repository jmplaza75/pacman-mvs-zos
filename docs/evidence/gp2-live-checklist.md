# MVS-GP2 GP2.4 live acceptance in c3270 - checklist (prepared 2026-10-12; to be run by the user)
Build of record: GP2.3 = JOB 246 (deck GP23, screens) + JOB 247 (deck GP2, text / CLASSIC regression), load module
HERC01.PACMAN.LOAD(PACMAIN); CLIST JOB 248 (defaults `RULES(CLASSIC) LEVEL(1)`). Checkpoint commit 3c7cf59.
No full maze is cleared by hand: three deterministic scenarios are played by `tools/gp2_live.py` through the c3270
script port (keys only), and every scenario is then replayed from the c3270 trace through the independent GP2 model by
`tools/c3270_gp2_trace.py` (every live host write compared byte for byte, as GP1.4). The scenario card files
`tests/gp2live/LIVE[ABC].txt` come from the Hercules-tested edge cases G2RCLR, G2XF and G2RXD
(`tests/gp2live/make_live.py`; redundant direction keys dropped, game identical in the model).

## 0. Setup (about 2 minutes)
1. Hercules / TK4- running. macOS Terminal: window 120 x 30 or larger BEFORE connecting; Settings > Profiles >
   Advanced > "Audible bell" ON.
2. Terminal 1: `TYPEAHEAD=false tools/c3270_rt.sh ~/gp2-live.txt` (trace OUTSIDE the repository: it holds the logon).
   Log on as HERC01 by hand and stay at `READY`.
3. Terminal 2 (repository directory): the commands below. Do not type in c3270 while a scenario runs.

## 1. Scenario A - REALTIME level 1 -> level 2 (about 35 s): `python3 tools/gp2_live.py A`
`RULES(ARCADE) AI(0) GHOSTS(1)` (LEVEL default 1; AI0 = still ghost). Quantum Qn is about n x 0.15 s after the start.
| When | Expected on screen / sound | Checks |
|---|---|---|
| start | bell; wide HUD right column `LEVEL   01`, `CHERRY     0100` (green); title `P A C - M A N   A R C A D E` | level HUD, start bell |
| Q32 (~5 s) | green fruit sprite appears at the lower middle corridor (10,8) | fruit appears (item 30) |
| Q52 (~8 s) | Pac-Man reaches the fruit: it disappears, score +100 | fruit collected |
| Q78 (~12 s) | the second fruit appears | |
| Q108 (~16 s) | `PAUSED` banner for 3 s, fruit still shown; then the game resumes exactly where it was | pause, fruit timer frozen |
| Q121 (~18 s) | PA2: the screen is redrawn completely, nothing changes (fruit, score, LEVEL 01) | PA2 redraw |
| Q138 (~21 s) | the second fruit vanishes untouched (60 quanta = 9 s after Q78, pause not counted) | fruit timeout |
| Q183 (~28 s) | last pellet: bell; maze refilled at once (all pellets + 4 `o`), Pac-Man and the ghost at their start cells, HUD `LAST L CLEARED`, `LEVEL   02`, `STRAWBERRY 0300`; then 1.5 s still (10-quantum freeze) | level clear, refill, freeze, level-clear bell |
| Q196-Q197 | PA2 redraw on level 2 (`LEVEL 02` kept); Pac-Man eats the `o` at (2,4): ghost blue for 34 quanta (5.1 s; level 1 was 40) | level state after PA2, changed progression |
| Q200 | `Q` + ENTER: end banner `QUIT`, short pause, TSO line mode `QUIT TURNS 0000188 SCORE 0001350 LIVES 3 QUANTA 0000200 GHOSTS EATEN 0000 FRUITS EATEN 001 LEVEL 002`, `READY` | clean QUIT / READY |
Expected alarm writes: [0, 184] (start, level clear).

## 2. Scenario B - TURN at LEVEL(13), extra life (about 20 s): `python3 tools/gp2_live.py B`
`RULES(ARCADE) AI(0) GHOSTS(1) LEVEL(13) PLAY(TURN) ANIM(NO)` (ANIM(NO): no idle ticks, so one screen per command).
| Turn | Expected | Checks |
|---|---|---|
| start | bell; `LEVEL   13`, `KEY        5000`; 3 life icons | `LEVEL(n)` start: fresh level-13 game, score 0 |
| T2 / T6 | power pellets: the ghost is blue for only 4 turns (level 1: 20) | changed progression at a later level |
| T32 / T38 | key fruit appears / eaten: score 0005440 | fruit appearance and collection |
| T74 / T76 | second key appears / eaten: score 0010780, bell, a 4th life icon | extra life at 10000 + its bell |
| T76 + Q | end banner, line mode `QUIT TURNS 0000076 SCORE 0010780 LIVES 4 GHOSTS EATEN 0000 FRUITS EATEN 002 LEVEL 013`, `READY` | lives after the extra life, clean QUIT |
Expected alarm writes: [0, 76] (start, extra life).

## 3. Scenario C - REALTIME at LEVEL(13), chasing ghost (about 30 s): `python3 tools/gp2_live.py C`
`RULES(ARCADE) AI(2) GHOSTS(1) LEVEL(13)`: AI2 + 2 = AI3 (HUD `GHOSTS  AI3`), REALTIME ghost step 9/10, fright 7 quanta.
| When | Expected | Checks |
|---|---|---|
| start | bell; `LEVEL   13`, `GHOSTS  AI3`, `KEY        5000` | later-level progression in REALTIME |
| Q2 / Q6 | power pellets: blue for about 1 s only | short fright at level 13 |
| Q40 / Q43 | key fruit appears / eaten (score 0005410) | |
| Q44 (~7 s) | the ghost catches Pac-Man: bell, 2 lives, 1.5 s freeze | death bell, freeze |
| Q113 (~17 s) | second death: bell, 1 life, freeze | |
| Q136 / Q145 | second key appears; at Q145 Pac-Man eats it (score 0010850, extra life) and is caught in the same quantum: ONE bell, lives stay 1 | extra life + death in one write = one alarm |
| Q147 | `Q`: line mode `QUIT TURNS 0000110 SCORE 0010850 LIVES 1 QUANTA 0000147 GHOSTS EATEN 0000 FRUITS EATEN 002 LEVEL 013`, `READY` | clean QUIT |
Expected alarm writes: [0, 44, 113, 145].

## 4. Optional (about 30 s each, by hand)
- `python3 tools/rt_play.py 'RULES(ARCADE) LEVEL(9)'`: free play, eat a power pellet (blue about 1 s), `Q`. Analyse with
  `--cfg 'AI1 1' --start 9` (any route; the replay still checks every write).
- CLASSIC unchanged: `EXEC 'HERC01.PACMAN.CLIST(PACMAN)'` (no keywords): title `P A C - M A N` (no ARCADE, no level,
  no fruit), `Q`.

## 5. After the session
Log off, close c3270 and send me the trace path (and `~/gp2-live-driver.log`). Analysis (start times from the driver):
```
python3 tools/c3270_gp2_trace.py ~/gp2-live.txt --scenario A --from HHMMSS
python3 tools/c3270_gp2_trace.py ~/gp2-live.txt --scenario B --from HHMMSS
python3 tools/c3270_gp2_trace.py ~/gp2-live.txt --scenario C --from HHMMSS
```
Pass: every scenario `ALL IDENTICAL` (write 0 may carry the platform clear prefix), the listed events in the report,
the expected alarm writes, the end lines and `READY`; plus your observations (bells heard, freeze visible, PAUSED
banner, nothing changed by PA2). If the driver ever lost a key (the replay is still identical but an event is missing,
e.g. no level clear), simply rerun that scenario. The tag `mvs-gp2` follows only after this analysis.
Self-test of the analysis (no terminal): synthetic traces built from the model streams of A / B / C are reported
`ALL IDENTICAL` with the alarm writes above.
