# MVS-G8 G8.4 installed-release live smoke in c3270 - checklist (prepared 2026-10-14; to be run by the user)
Release under test: the INSTALLED 2.0 release. `HERC01.PACMAN.LOAD(PACMAIN)` = copy of the R20 build of record (REL20
JOB 307, IEBCOPY JOB 314, SPZAP-identical), `HERC01.PACMAN.CLIST(PACMAN)` = JOB 317 (default `RULES(ARCADE)`). Nothing
is rebuilt. Scope (user, 2026-10-14): one short smoke, no soak, no repeat of RP / S2 acceptance, not a score attempt.

One deterministic scenario, G8, sent by `tools/gp2_live.py G8` through the c3270 script port (keys only, as in S2.4):
the CLIST is started with **no operand at all** (every default), so the run itself proves the defaults. Cards:
`tests/s2live/LIVEG8.txt` (`tests/s2live/make_live.py`): the Hercules-tested RP3TIM cards up to its Q, then
direction / idle cards until the ghost catches Pac-Man, then Q. About 180 quanta (27 s + the freezes). Expected on the
models (independent RP / S2 models, HUD high score from the disk):
| Write | State |
|---|---|
| 0 | start screen: READY!, 4 power pellets, HUD with HIGH SCORE (read from HERC01.PACMAN.DATA), 1 bell |
| 2-28 | power pellet eaten: the ghost frightened (blue / white) |
| 29-34 | the ghost eaten: score popup 200, eyes go home |
| 147-152 | Pac-Man caught: 6-frame death animation, 2 bells (ALARM(PATTERN)) |
| 153-156 | READY! after the death |
| 179 | Q: end screen with QUIT, SCORE 0001050, HIGH SCORE (not new: 1050 is below the stored high score, no write) |

`--snap DIR` saves seven screen captures from the emulator (c3270 PrintText: HTML with the 3270 colours + text; a local
action, nothing is sent to MVS) at writes 0, 20, 30, 100, 149, 154, 179. They hold only the game screen.

## 0. Setup (about 2 minutes)
1. Hercules / TK4- running. macOS Terminal window 120 x 30 or larger BEFORE connecting (never shrink it while
   connected). Audible bell optional.
2. Terminal 1: `TYPEAHEAD=false tools/c3270_rt.sh ~/g8-live.txt` (trace OUTSIDE the repository: it holds the logon).
   Log on as HERC01 by hand and stay at `READY`.
3. Terminal 2 (repository directory): `mkdir -p ~/g8-snaps` (outside the repository too).

## 1. The smoke (about 40 s): `python3 tools/gp2_live.py G8 --snap ~/g8-snaps`
Do not type in c3270 while it runs. The driver types `EXEC 'HERC01.PACMAN.CLIST(PACMAN)'` (no operand), plays the
cards and returns when TSO shows `READY`. Please note (yes / no):
| # | Check |
|---|---|
| 1 | the game came up full-screen in colour on the 120 x 27 canvas (maze centred, a panel on each side) |
| 2 | ARCADE: power pellets `o`, READY! at the start, HIGH SCORE in the HUD |
| 3 | frightened ghost and the 200 popup; later the death animation and READY! again |
| 4 | QUIT end screen for about 3 s, then the line-mode end lines and a clean `READY` |
| 5 | anything unexpected (a stall, a wrong screen, a TSO message, a `***`) |

## 2. Optional real screenshot (only if easy)
While the game runs or on the end screen: Cmd-Shift-4, Space, click the c3270 window -> PNG on the Desktop. Only the
game window; no logon screen. Not required: the release PNGs are rendered from the step 1 captures.

## 3. Afterwards (Claude)
`python3 tools/c3270_s2_trace.py ~/g8-live.txt --scenario G8`: every live write vs the model byte for byte (canvas,
profile, ARCADE screens, alarms), the AIDs = the cards, cadence, the 3-s end pause, the line-mode end and `READY`.
Plus: the `EXEC` record in the trace (installed CLIST, no operand). The trace and the raw captures stay outside the
repository; only the reviewed captures (game screen only) go to `releases/2.0-MVS-MAX/screenshots/`.
