# PACMAN 2.0-MVS-MAX - final launcher defaults (frozen, D43; pinned by tests/test_g8.py)
`EXEC 'HERC01.PACMAN.CLIST(PACMAN)'` with no operand uses exactly these values. Only RULES changed in 2.0
(CLASSIC -> ARCADE); every other default was already the automatic maximum.

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
