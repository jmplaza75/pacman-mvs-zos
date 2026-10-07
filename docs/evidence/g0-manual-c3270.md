# MVS-G0 manual validation in c3270 (2026-10-07, reported by the user)
Build: G0 load module (JOB 145). Session: c3270 4.5ga6 -> TSO HERC01.
1. `EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'AI(3) GHOSTS(2)'`, R R D Q: same behaviour as MVS-8, no `***` between turns.
2. ALLOC SYSIN/SYSOUT DA(*), `CALL 'HERC01.PACMAN.LOAD(PACMAIN)' 'TSO AI3 2 M'`, R R D Q:
   `METRICS FRAMES=0004 LINES=00057 CHARS=0001195 CLEARS=0003`, then TURNS 003, SCORE 0020, LIVES 3, back to READY.
   Consistent with the model: banner 1 + 4 frames x 12 lines + 4 prompts + 4 end lines = 57 lines;
   25 + 4 x (61 + 200 + 8) + 4 x 16 + 4 + 26 = 1195 characters; clears = frames after the first = 3.
Note: `***` may still appear once at start-up when TSO's screen is already full before the first frame; turn-by-turn
play is not paged. To be revisited in later presentation phases if still relevant.
