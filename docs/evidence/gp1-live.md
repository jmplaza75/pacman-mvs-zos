# MVS-GP1 GP1.4 live acceptance in c3270 (user, 2026-10-11) - trace analysis
Build JOB 240 (deck GP1, tests/test_gp1.py PASS), CLIST JOB 241 (default RULES(CLASSIC)). 120x27 IBM-DYNAMIC REALTIME,
`TYPEAHEAD=false tools/c3270_rt.sh ~/gp1-live.txt`, games started with `tools/rt_play.py '... RULES(ARCADE) ...'`.
Analysis: `tools/c3270_gp1_trace.py ~/gp1-live.txt --cfg CFG --from HHMMSS` rebuilds the inputs of every quantum from
the AIDs, replays them through the independent ARCADE model and compares every live host write byte for byte.
Write 0 of each game = the model's first screen + the platform's first-screen clear prefix `11 40 40 3C 40 40 00`
(SBA 0, RA to 0 with nulls), which the TSD dry run does not print; every other write is identical.

## Game A - AI(0) GHOSTS(2), --from 221400: 420/420 writes = model (write 0 with the prefix)
Inputs (cards): D, R (Q14), L, U, L U, R U L U, P P (Q128), PA2 (Q182), L, D, Q (Q417). The user left the planned route
(the right-side power pellets were not eaten), so pause and PA2 happened with no fright running.
- Q2 power pellet (FR=040, ghosts F), Q6 second pellet: restart at 40 (FR was 036, chain reset).
- Q7 ghost 2 eaten, 200 (eyes at 2,9 under Pac-Man); Q27 ghost 2 revives NORMAL during the fright (FR=019).
- Q30 ghost 1 eaten, 400 (chain 2). Warning Q36-Q45 (FR 010..001), Q46 fright end = exactly 40 running quanta
  after Q6. Q50 ghost 1 revives (fright over).
- Q128 pause/resume (FR=000), Q182 PA2 = full redraw identical to the model. Q305 death (normal ghost): the write has
  the alarm bit; alarm writes [0 start, 306 death] only.
- End: QUIT / TURNS 059 / SCORE 0001110 / LIVES 2 / QUANTA 0000417 / GHOSTS EATEN 002, READY.

## Game B - AI(1) GHOSTS(3), --from 222630: 232/232 writes = model (write 0 with the prefix)
- Q2 and Q6 power pellets; Q9 ghost 2 eaten (200); Q28 third pellet (restart, eyes not affected: modes F E F);
  Q29 ghost 2 revives NORMAL in the fright; Q31 a frightened ghost walks into Pac-Man and is eaten (hit check 2);
  Q32 fourth pellet with ghost 1 in eyes (unaffected); Q51 revival in the fright; Q72 fright end = 40 quanta after
  Q32. Frightened moves follow the 2/5 accumulator (FA), normal ghosts 4/5 (byte-identical to the model).
- Q184 death, alarm writes [0 start, 184 death]. End: QUIT / TURNS 153 / SCORE 0001420 / LIVES 2 / QUANTA
  0000230 / GHOSTS EATEN 002, READY.

## Not observed on the human live route (accepted by the user, 2026-10-12)
Pause/resume during an active fright and a PA2 redraw during an active fright were NOT observed live: in game A the
pause (Q128) and the PA2 (Q182) came after the fright had ended. Both combinations are covered by deterministic tests:
batch REALTIME RTGPP (= RTGPA with a pause inside the fright: every game line identical, the timer does not advance)
and the TSD runs GQR3 (RTGPP screens, PAUSED banner in a fright) and GQT16 / GQR1-5 (full redraws in a fright), all
byte-identical on Hercules (JOB 238 / 240).

## Result
All live screens of both games are the model's streams; every listed item is shown live except "pause/resume during
a fright" and "PA2 during a fright", which were done outside a fright in this session (covered in batch by RTGPP and
the TSD run GQR3). The death bell is in the trace (alarm bit on the death write in both games).
