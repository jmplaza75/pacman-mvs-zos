# PACMAN 2.1-zos - launcher defaults (ZOS-11)
Unchanged from 2.0-zos: every keyword, default, value and PARM column is the table of `releases/2.0-ZOS/DEFAULTS.md`.
The 2.1-zos CLIST (`src/zos/PACMAN.clist` of 35b803e) differs from the 2.0-zos CLIST only in its help comment
(`ARROWS = PF7/8/10/12`), so `EXEC 'Z00000.PACMAN.CLIST(PACMAN)'` with or without operands builds the same PARM as in
2.0-zos (pinned by `tests/zos_c2.py`, D46 exact).

Keys in REALTIME (2.1-zos): Up PF7, Down PF8, Left PF10, **Right PF12**, PF9 pause / resume, PA2 redraw; PF11 and every
other PF key do nothing; quit = type `Q`, then ENTER. In TURN mode commands are typed characters (unchanged).
