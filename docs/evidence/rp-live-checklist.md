# MVS-RP RP.4 live checklist (remaining after the RP.3 FAST capture)
Installed build: PACMAIN deck RP JOB 286, CLIST JOB 287 (RPESTAE CLIST and LOAD(PACRPE) from RP.0 unchanged).
Already accepted live: RP.0 ESTAE (rp-estae-live2.md); RP.3 FAST play, READY! / popups / death animation / HUD high
score byte-identical, timers, cadence, D40 case (a) clean startup (rp3-fast-live.md).
Remaining: D40 case (b) (the RP.0 `***` reproduction), a NORMAL ARCADE game to GAME OVER (final death animation, end
screen), the 10-minute pre-start and pause soak (run at SPEED(FAST), which also covers FAST pause / resume).

## Before the session: the TK4- wait limits (design 8)
The soak needs the job wait (JWT, SMF parameters) and any TSO input wait limit noted. They live in SYS1.PARMLIB, which
is outside HERC01.PACMAN.*: either (1) you read `SYS1.PARMLIB(SMFPRM00)` (the JWT value) yourself and tell me, or
(2) you allow one read-only batch job (IEBGENER, `DISP=SHR`, output to SYSOUT only) that prints that member.

## Setup (user)
Window 120x30; `tools/c3270_rt.sh ~/rp4-live.txt` (trace outside the repository); log on; READY.

## Part A - D40 reproduction + NORMAL game to GAME OVER (about 3 minutes)
| # | Action | Expected |
|---|---|---|
| A1 | `EXEC 'HERC01.PACMAN.CLIST(RPESTAE)' 'CASE(E3)'`, ENTER on its screen | line `RPE E3 LINE MODE RESTORED, FORCING 0C7`, abend message, READY (the control abend, as RP.0) |
| A2 | at once, in the second shell: `python3 tools/rt_play.py --hold-ok 'RULES(ARCADE)'` | TSO shows `***` (the script says so and waits; it never presses ENTER) |
| A3 | press ENTER yourself | the **full-screen** game (no line-mode fallback, no `INVALID COMMAND`) - D40 case (b) |
| A4 | play NORMAL speed; once during a death freeze press P, wait ~3 s, P; once during a freeze press PA2 | the freeze resumes where it stopped; the redraw keeps the death frame / READY! |
| A5 | lose all lives | the final death animation (6 frames) before GAME OVER; end screen SCORE / HIGH SCORE (NEW HIGH SCORE if beaten); end lines; READY |

## Part B - soak at SPEED(FAST) (about 21 minutes)
| # | Action | Expected |
|---|---|---|
| B1 | `python3 tools/rt_play.py 'RULES(ARCADE)' 'SPEED(FAST)'`; do NOT press any key for 10 minutes (READY! shown) | no abend / S522 / timeout, screen intact |
| B2 | after 10 minutes, an arrow; play ~30 s (a power pellet if convenient) | game starts at once, normal cadence |
| B3 | P (pause) and leave it 10 minutes | PAUSED banner, no frames, no abend |
| B4 | P (resume); play ~30 s; Q + ENTER | play resumes with no catch-up burst (first frame gap = one period), arrows responsive; QUIT end lines; READY |

Tell me the times rt_play.py printed (A2, B1) and anything that looked or felt wrong.

## Analysis (Claude)
- A1-A3: startup records after the second EXEC by AID byte only: `***` hold, the ENTER, then `7E C3` / query /
  reply / game screen (no line-mode game).
- A4-A5: `c3270_rt_game.py ~/rp4-live.txt --from HHMMSS` (150 ms) and `c3270_gp2_trace.py ~/rp4-live.txt --cfg 'AI1 1'
  --from HHMMSS`: every write = the NORMAL models (pause and PA2 inside a freeze, final death frames, end screen,
  NEW HIGH SCORE line), freeze / fright wall-clock.
- B: `c3270_rt_game.py ... --period 125 --from HHMMSS`: pre-start wait and pause lengths, first frame gaps after the
  resume, drift per stretch; `c3270_gp2_trace.py ... --speed F --from HHMMSS`: writes = the FAST models.
- Evidence: docs/evidence/rp-live.md. Then README, CURRENT_PHASE; tag `mvs-rp` only on your approval.
