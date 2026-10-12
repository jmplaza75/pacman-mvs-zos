# MVS-RP RP.0: ESTAE live checklist (D39, docs/RP-POLISH.md section 7)
Build: deck RPE JOB 266 (docs/evidence/rp-estae-build.txt): LOAD(PACRPE) = test driver + the unchanged production
PACFSIO and PACHSIO; CLIST `HERC01.PACMAN.CLIST(RPESTAE)`. The game is not involved.

Start c3270 with a trace kept OUTSIDE the repository (it contains the logon):
`tools/c3270_rt.sh ~/rp-estae-live.txt`, log on as HERC01, then at READY:

| # | Command | Do | Pass |
|---|---|---|---|
| E1 | `EXEC 'HERC01.PACMAN.CLIST(RPESTAE)' 'CASE(E1)'` | the full screen "CASE E1" appears; press ENTER | line mode, abend message (0C7), READY; typing works |
| E1b | `TIME` | - | normal TIME output (terminal usable) |
| E2 | `EXEC 'HERC01.PACMAN.CLIST(RPESTAE)' 'CASE(E2)'` | screen shows `PACHSIO READ RC=0000`; press ENTER | as E1 (PACHSIO's ESTAE was created and deleted first) |
| E3 | `EXEC 'HERC01.PACMAN.CLIST(RPESTAE)' 'CASE(E3)'` | press ENTER | line `RPE E3 LINE MODE RESTORED, FORCING 0C7`, abend message, READY (control) |
| G | `EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'RULES(ARCADE)'` | play a few moves, Q | game starts and ends cleanly after the abends |
| L | `LISTALC` | - | note what is still allocated (the CLIST may stop at the abend) |

Note for each case whether the CLIST's `RPESTAE Ex AFTER CALL LASTCC=...` line appeared (does a CLIST go on after an
abend in CALL?). Afterwards tell Claude the trace file name; the trace is decoded independently for the evidence.

## Retest after live 1 (driver JOB 267; diagnosis docs/evidence/rp-estae-live1.md)
One fresh session, trace `tools/c3270_rt.sh ~/rp-estae-live2.txt`, log on, then six commands; Q ends each game.
| # | Command | Pass |
|---|---|---|
| R1 | `EXEC 'HERC01.PACMAN.CLIST(RPESTAE)' 'CASE(E2)'`, ENTER on the E2 screen | the E2 screen is SHOWN (no `***`), then `ENDED DUE TO ERROR+`, READY |
| R2 | `EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'RULES(ARCADE)'`, Q | full-screen game at once (no `***`), clean end |
| R3 | `EXEC 'HERC01.PACMAN.CLIST(RPESTAE)' 'CASE(E3)'`, ENTER | line `RPE E3 LINE MODE RESTORED, FORCING 0C7`, abend message, READY |
| R4 | `EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'RULES(ARCADE)'`, Q | as R2 |
If a `***` appears anywhere: note where, press ENTER, go on (the trace shows the rest). E1 is not repeated: live 1
already showed it clean (TIME and the next commands normal).
