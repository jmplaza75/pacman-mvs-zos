# 2.0-MVS-MAX screenshots (installed release, live G8.4, 2026-10-14)
Captured live from c3270 (120 x 27 IBM-DYNAMIC) while `tools/gp2_live.py G8 --snap DIR` played the deterministic
scenario G8 on the installed release, started with `EXEC 'HERC01.PACMAN.CLIST(PACMAN)'` and no operand. Each capture is
c3270's own screen buffer (`PrintText`, a local action: nothing was sent to MVS):
- `.html`: the screen with the 3270 colours as c3270 holds them (unchanged except a page title and a monospace style);
- `.txt`: the same screen as UTF-8 text (CP310 box and APL symbols mapped by c3270), reproducible from the model;
- `.png`: the `.html` rendered by headless Chrome (`--window-size=980,470`), not a photo of the Terminal window.
The scenario was played twice in the session; both runs gave identical captures. No logon, password or TSO history.

| File | Host write | State |
|---|---|---|
| g8-01-ready | 0 | start: READY!, 4 power pellets, HUD with HIGH 0001430 |
| g8-02-fright | 20 | power pellet eaten, the ghost frightened (blue) |
| g8-03-popup | 30 | the ghost eaten: popup 200, eyes going home |
| g8-04-play | 100 | normal ARCADE play |
| g8-05-death | 149 | death animation (R DIED, LIVES 2) |
| g8-06-ready-death | 154 | READY! after the death |
| g8-07-end | 179 | QUIT end screen: SCORE 0001050, HIGH SCORE 0001430 |
Evidence and the trace analysis (every live write = the model): docs/evidence/g8-live.md.
