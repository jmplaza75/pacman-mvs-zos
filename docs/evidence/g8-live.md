# MVS-G8 G8.4: installed-release live smoke in c3270 - PASS (2026-10-14)
Release under test: the installed 2.0 release, `HERC01.PACMAN.LOAD(PACMAIN)` = IEBCOPY of the R20 build of record
(REL20 JOB 307 -> INST20 JOB 314, AMASPZAP-identical), `HERC01.PACMAN.CLIST(PACMAN)` = JOB 317. Nothing rebuilt or
relinked. Checklist: docs/evidence/g8-live-checklist.md. Scope (user): one short smoke; RP / S2 live evidence stays
authoritative for FAST timing, alarm patterns, pause / soak, ESTAE and D40.

Run: `TYPEAHEAD=false tools/c3270_rt.sh ~/g8-live.txt` (120 x 30 window, IBM-DYNAMIC 120 x 27), logon by hand, then
`python3 tools/gp2_live.py G8 --snap ~/g8-snaps`. The scenario was played twice in the session (14:16:05 and
14:17:01, the second refreshing the screen captures); both runs are analysed below and are identical. The trace and the
raw captures stay outside the repository (the trace holds the logon).

## User observations (both runs)
| Check | Result |
|---|---|
| 120 x 27 full-screen | PASS |
| no-argument CLIST started ARCADE | PASS |
| READY! and HUD high score | PASS |
| frightened ghost + 200 popup | PASS |
| death animation + READY! | PASS |
| QUIT end screen -> clean READY | PASS |
| unexpected behaviour | none |

## Trace analysis (`tools/c3270_s2_trace.py ~/g8-live.txt --scenario G8 [--from 141700]`)
| Item | Run 1 (14:16:05) | Run 2 (14:17:01) |
|---|---|---|
| Command sent (outbound record) | `EXEC 'HERC01.PACMAN.CLIST(PACMAN)'`, no operand | same |
| Installed release exercised | the installed CLIST (CALL `HERC01.PACMAN.LOAD(PACMAIN)`) | same |
| Host writes vs the model (RULES A, AI1 1 ghost, NORMAL, PATTERN, GRAPHIC 4x2 partial, canvas W = 120 x 27) | 180 / 180 byte-identical | 180 / 180 byte-identical |
| AIDs = scenario cards | yes (179) | yes (179) |
| HUD high score (read from HERC01.PACMAN.DATA) | 0001430 | 0001430 |
| Alarms (write: event) | 0 START, 147 DEATH, 149 step: 1 + 2 bells, gap 297 ms | same, gap 296 ms |
| Cadence of the game writes | median 150, p95 160 ms, 0 gaps > 225 ms | median 150, p95 158 ms, 0 gaps > 225 ms |
| End | write 179 QUIT end screen, line mode after 3010 ms | after 3014 ms |
| Line-mode end lines (= model) | QUIT, TURNS 0000127, SCORE 0001050, LIVES 2, QUANTA 0000178, GHOSTS EATEN 0001, FRUITS EATEN 000, LEVEL 001, `HIGH SCORE 0001430 LEVEL 001` (not new: no write) | same |
| TSO | READY | READY |

Byte identity with the model proves the profile chosen automatically by the defaults: colour full-screen
(COLOR(AUTO) query), highlighting, GRAPHIC glyphs, 4x2 scale, partial redraw, the wide 120 x 27 layout, REALTIME,
ARCADE rules, PATTERN alarms, the HS HUD. The score 1050 is below the stored high score: HISCORE was not rewritten.

Timing of run 2 (`tools/c3270_rt_game.py ~/g8-live.txt --from 141700`): 179 writes over 179 periods (26.7 s), gaps
min 137 / median 150 / p95 159 / max 166 ms, lateness median 5 / p95 12 / max 16 ms, 0 skipped periods, drift +0.6 ms
per 100 quanta, 0 late writes. Keyboard lock per AID median 142 ms: the driver sends each card right after a write,
so the next quantum write releases it (not comparable with hand play; RP measured 59-75 ms medians by hand).

## Screen captures (c3270 PrintText, local, nothing sent to MVS)
At writes 0, 20, 30, 100, 149, 154, 179 (the SNAPS of tools/gp2_live.py). The two runs gave identical captures. The
reviewed set (game screen only; no logon, password or TSO history) is in releases/2.0-MVS-MAX/screenshots/: HTML with
the 3270 colours as c3270 holds them, the UTF-8 text, and PNG rendered from the HTML by headless Chrome.
| Capture | State shown |
|---|---|
| g8-01-ready | start: READY! over the centre bar, 4 power pellets, SCORE 0000000, HIGH 0001430, STATE READY |
| g8-02-fright | power pellet eaten: the ghost blue (frightened), SCORE 0000270 |
| g8-03-popup | the ghost eaten: popup 200 at its cell, eyes going home, SCORE 0000640 |
| g8-04-play | normal ARCADE play after the fright |
| g8-05-death | death animation frame (R DIED), LIVES 2 |
| g8-06-ready-death | READY! after the death |
| g8-07-end | QUIT end screen: `QUIT  SCORE 0001050  HIGH SCORE 0001430` |

G8.4 PASS.
