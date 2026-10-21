# PACMAN 2.1-mvs - launcher defaults and controls (MVS-10, D46; defaults = 2.0-MVS-MAX, pinned by tests/test_g8.py)
`EXEC 'HERC01.PACMAN.CLIST(PACMAN)'` with no operand uses exactly these values - unchanged from 2.0-MVS-MAX (MVS-10
changed no default, keyword or PARM column; only the REALTIME Right key, see Controls).

| Keyword | Default | Values | PARM column |
|---|---|---|---|
| AI | 1 | 0 still, 1 random, 2 persistent, 3 chase | config `AI<l>` |
| GHOSTS | 1 | 1-3 | config |
| METRICS | NO | YES (diagnostic end lines) | 11 |
| COLOR | AUTO | AUTO (Read Partition Query), YES, NO (monochrome line mode) | 12 |
| HILITE | AUTO | AUTO, YES, NO | 13 |
| ANIM | AUTO | AUTO, YES, NO | 14 |
| REDRAW | PARTIAL | PARTIAL, FULL | 15 |
| GLYPHS | AUTO | AUTO, GRAPHIC, BASE, CLASSIC | 16 |
| SCALE | AUTO | AUTO, 4, 3, NO | 17 |
| CANVAS | AUTO | AUTO, DEFAULT (80 x 24) | 18 |
| PLAY | REALTIME | REALTIME, TURN | 19 |
| SOUND | AUTO | AUTO, YES, NO | 20 |
| RULES | **ARCADE** | ARCADE, CLASSIC (the 1.0-MVS game) | 21 |
| LEVEL | 1 | 1-99 (ARCADE start level; > 1 = practice, high score not recorded) | 22-23 |
| SPEED | NORMAL | NORMAL (150 ms), FAST (125 ms) | 24 |
| ALARM | PATTERN | PATTERN (1-4 bells per event), SINGLE | 25 |

The PARM the CLIST builds for no operand: `TSO AI1 1 NAAAPAAARAA01NP` (checked under the TMP in REL20 JOB 307; with
`'RULES(CLASSIC)'`: `TSO AI1 1 NAAAPAAARAC01NP`).
Batch and direct calls of PACMAIN are unchanged: a PARM without column 21 is CLASSIC (the 1.0-MVS reference).
Compatibility: `RULES(CLASSIC)`, `PLAY(TURN)`, `CANVAS(DEFAULT)`, `SCALE(NO)`, `GLYPHS(CLASSIC)`, `COLOR(NO)`,
`SOUND(NO)`, `ALARM(SINGLE)` give every earlier look and behaviour.

## Controls (2.1-mvs; D46)
| Action | REALTIME (full screen) | TURN |
|---|---|---|
| Up / Down / Left | PF7 / PF8 / PF10 (Up / Down / Left arrow in `tools/c3270_rt.sh`) | `U` / `D` / `L` + ENTER |
| **Right** | **PF12** (AID X'7C'; the Right arrow in `tools/c3270_rt.sh` sends PF12) | `R` + ENTER |
| Pause / resume | PF9 | - |
| Redraw | PA2 (or an empty ENTER) | PA2 / empty ENTER |
| **Quit** | **type `Q`, then press ENTER** | `Q` + ENTER |
- PF11 (X'7B') is no longer Right (it was in 2.0-MVS-MAX): in REALTIME it does nothing, like PF1-PF6 and PF13-PF24.
- No PF key quits - neither PF11 nor PF12 nor any other. A typed `Q` alone does nothing until ENTER sends it (verified
  live: the typed `Q` survived 20 game screen writes and the following ENTER quit; docs/evidence/mvs10-release.md).
- TURN mode is unchanged (U/D/L/R + ENTER, Q + ENTER; in TURN full screen any key other than ENTER redraws).
