# MVS-RP RP.3 FAST live capture - checklist (one directed session)
Installed build: PACMAIN = deck RP JOB 286 (same sources as JOB 285, full RP / D40 / RP3 checks re-passed on the
installed module), CLIST JOB 287 (defaults unchanged except the new `SPEED(NORMAL)`). Profile: ARCADE + REALTIME +
FAST, 120x27 (CANVAS(AUTO)), AI(1) GHOSTS(1), SOUND(AUTO).

## Setup (user)
1. Size the terminal window to 120x30, then start c3270 with a trace kept OUTSIDE the repository (it contains the logon):
   `tools/c3270_rt.sh ~/rp3-fast-live.txt`
2. Log on and wait for READY.
3. In a second shell: `python3 tools/rt_play.py 'RULES(ARCADE)' 'SPEED(FAST)'` (prints the game start time; game
   keys: arrows = PF7/8/10/11, P = pause, PA2 redraw, Q + ENTER quit).

## Play (about 2-4 minutes of continuous play, one game)
| # | Action | Verifies |
|---|---|---|
| 1 | Wait ~3 s on READY! before the first arrow | READY! at start, no frames before the start |
| 2 | Play normally; change direction often, short taps and one arrow held ~2 s then released | arrows responsive, keyboard restore after every AID, no persistent X Wait, no stale typeahead backlog |
| 3 | Eat a power pellet, eat a ghost; let that fright run out without another pellet if you can | popup, warning flash, fright length (L1: 6.0 s) |
| 4 | Eat 30 items so the fruit appears; leave it to expire once (~9 s); eat a later one if convenient | fruit length (9.0 s), fruit popup |
| 5 | Once, during play: P, wait ~10 s, P | pause stops everything; no catch-up burst after resume |
| 6 | One PA2 | full redraw |
| 7 | Lose at least one life (more is fine) | death animation (7 frames), READY! (5 frames), freeze 1.5 s |
| 8 | Q + ENTER | QUIT end screen -> final lines -> READY |

Note anything that looks or feels wrong (and roughly when). Then tell me the game start time printed by rt_play.py.

## Analysis (Claude, from the trace; nothing before the game title is read)
- `python3 tools/c3270_rt_game.py ~/rp3-fast-live.txt --period 125 --from HHMMSS`: frame cadence (median, p95,
  worst gap), absolute-schedule lateness / skipped periods / drift / recovery per running stretch, keyboard lock per AID,
  pause and the first frames after the resume, end banner.
- `python3 tools/c3270_gp2_trace.py ~/rp3-fast-live.txt --cfg 'AI1 1' --speed F --from HHMMSS`: every live write
  replayed through the FAST models byte for byte (READY!, popups, death frames, HUD high score, end screen; inputs
  consumed in order = no stale backlog) and the wall-clock length of every fright / fruit / eyes / freeze against the
  NORMAL design length.
- Decision gate (user, 2026-10-13): adequate headroom and no accumulating lateness -> keep SPEED(FAST); repeated
  overruns or degraded input / rendering -> stop and report the numbers (no period tuning, no 100 ms).
