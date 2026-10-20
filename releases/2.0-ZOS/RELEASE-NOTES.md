# Pac-Man 2.0-zos (2026-10-20) - PAC-MAN 2.0 for IBM z/OS
Target: IBM z/OS V3R1 (IBM Z Xplore), Enterprise COBOL 6.5, HLASM R6.0, the z/OS binder, LE, TSO / VTAM / TN3270E,
c3270 4.5 as the terminal. The same game as 2.0-MVS-MAX (`releases/2.0-MVS-MAX/`), ported with only the registered
z/OS differences (`docs/ZOS-DIFFS.md`, Z1-Z6). Release design: `docs/zos10-design.md`; evidence:
`docs/evidence/zos10-release.md`; equivalence with the MVS oracle: `docs/evidence/zos9-equivalence.md` (ZOS-9).

## What 2.0-zos is
- **The 2.0 game on z/OS**: ARCADE rules by default (`RULES(CLASSIC)` = the 1.0-MVS game), real time
  (`PLAY(REALTIME)`, 150 / 125 ms logical quanta), scaled 3270 graphics on the 120 x 27 alternate screen, the 3270 alarm
  as sound, the persistent high score in `Z00000.PACMAN.DATA(HISCORE)`, the same automatic fallbacks.
- **One z/OS-specific presentation default** (Z6, ZOS-9 DEC-2): with PLAY(REALTIME) the launcher selects
  `PRESENT(COALESCED)` - the game logic still advances every 150 / 125 ms, the screen is written every 2nd / 3rd quantum
  (~300 / 375 ms), because one write per quantum is not viable interactively over z/OS TSO / VTAM / TN3270E (ZV-D33).
  `PRESENT(EVERY)` stays selectable; TURN keeps its historical PARM; a PARM without column 26 still means EVERY.
- Behaviour: equivalent to the 2.0-mvs-max oracle (ZOS-9: 51-row matrix, GAP 0, DECISION 0); approved platform
  differences only (COPY syntax, LE options, terminal SYSIN, coalesced presentation).

## Play
1. Size a terminal window to 120 x 30, then `c3270 -model 2 -oversize auto 198.51.100.200:623`; log on (credentials
   typed by the user only).
2. From TSO READY or ISPF option 6: `EXEC 'Z00000.PACMAN.CLIST(PACMAN)'` (or with operands, e.g.
   `'RULES(CLASSIC)'`, `'PLAY(TURN)'`, `'SPEED(FAST)'`). Arrows = PF7 / PF8 / PF10 / PF11 (keymap of
   `tools/c3270_rt.sh`), PF9 pause, PA2 redraw, Q + ENTER quits.
3. Launcher defaults: `DEFAULTS.md`.

## Verification (MANIFEST.md)
- Clean build from new, empty `Z00000.PACMAN.RZ.*` libraries (PACZ10BL JOB04820) of sources uploaded from commit
  2c99fae and byte-verified; build gate PASS (C3 ASMA303W only).
- Object equivalence: 13 / 13 against the accepted ZOS-6 build objects (corrected per-member baseline; compile
  timestamps and the compressed form of the no-load D_MCODE debug class only; executable content exact).
- Candidate batch runs C1 / C2 exact (oracle 307 / 310 / 311 and the frozen models); CLIST PARM matrix PASS.
- Rollback copy before promotion; promotion of PACMAIN and the CLIST complete (no partial state); installed program
  byte-identical to the candidate; installed batch run P1 exact; live smoke S10 (installed CLIST, CLASSIC, REALTIME
  default -> COALESCED) FUNCTIONAL / TIMING / shell return PASS.
- Production high score preserved: `0000980 PACHS001 001`.

## Known limits (environment, documented)
- Interactive REALTIME on z/OS uses COALESCED presentation (EVERY is diagnostic only); live alternate size 120 x 27 on
  this TN3270E path (other layouts exact on simulated buffers only).
- No Programmed Symbols announced on this path; no host graphics used (as on MVS).
- Site job output limit (~5,000 SYSOUT lines per job): the large MVS oracle batteries run as targeted jobs.
- METRICS(YES) is a diagnostic option outside the 2.0-zos equivalence (ZOS-9 DEC-4).
