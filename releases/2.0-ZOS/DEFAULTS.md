# PACMAN 2.0-zos - launcher defaults (ZOS-10; pinned by tests/test_zos10.py and tests/zos_c2.py)
`EXEC 'Z00000.PACMAN.CLIST(PACMAN)'` with no operand uses exactly these values. They are the 2.0-MVS-MAX defaults
(`releases/2.0-MVS-MAX/DEFAULTS.md`) plus one z/OS keyword, PRESENT (Z5), whose default is AUTO (Z6, DEC-2).

| Keyword | Default | Values | PARM column |
|---|---|---|---|
| AI | 1 | 0 still, 1 random, 2 persistent, 3 chase | config `AI<l>` |
| GHOSTS | 1 | 1-3 | config |
| METRICS | NO | YES (diagnostic end lines; out of the 2.0-zos equivalence scope, ZOS-9 DEC-4) | 11 |
| COLOR | AUTO | AUTO (Read Partition Query), YES, NO (monochrome line mode) | 12 |
| HILITE | AUTO | AUTO, YES, NO | 13 |
| ANIM | AUTO | AUTO, YES, NO | 14 |
| REDRAW | PARTIAL | PARTIAL, FULL | 15 |
| GLYPHS | AUTO | AUTO, GRAPHIC, BASE, CLASSIC | 16 |
| SCALE | AUTO | AUTO, 4, 3, NO | 17 |
| CANVAS | AUTO | AUTO, DEFAULT (80 x 24) | 18 |
| PLAY | REALTIME | REALTIME, TURN | 19 |
| SOUND | AUTO | AUTO, YES, NO | 20 |
| RULES | ARCADE | ARCADE, CLASSIC (the 1.0-MVS game) | 21 |
| LEVEL | 1 | 1-99 (ARCADE start level; > 1 = practice, high score not recorded) | 22-23 |
| SPEED | NORMAL | NORMAL (150 ms), FAST (125 ms) | 24 |
| ALARM | PATTERN | PATTERN (1-4 bells per event), SINGLE | 25 |
| PRESENT | **AUTO** | AUTO (= COALESCED with PLAY(REALTIME), nothing with TURN), COALESCED, EVERY | 26 (`C` or absent) |

PRESENT policy (Z6):
| Invocation | Column 26 | Presentation |
|---|---|---|
| PLAY(REALTIME) (default), no PRESENT | `C` | COALESCED: a screen write every 2nd (NORMAL) / 3rd (FAST) logical quantum |
| PLAY(REALTIME) PRESENT(COALESCED) | `C` | COALESCED |
| PLAY(REALTIME) PRESENT(EVERY) | absent | EVERY (one write per quantum; diagnostic on z/OS, ZV-D33) |
| PLAY(TURN), no PRESENT | absent | the historical 25-column TURN PARM |
| PLAY(TURN) PRESENT(COALESCED) | `C` | explicit value kept |
| PLAY(TURN) PRESENT(EVERY) | absent | EVERY |
| any other PRESENT value | absent | EVERY (accepted fallback) |

PARMs the release CLIST builds (CLASSIC rows checked under the TMP on z/OS by PACZ10CL JOB04866; the no-operand ARCADE
rows by the independent CLIST evaluator in tests/test_zos10.py - the host matrix stays CLASSIC so that no case can reach
the high-score path):
- no operand: `TSO AI1 1 NAAAPAAARAA01NPC`; `'PLAY(TURN)'`: `TSO AI1 1 NAAAPAAATAA01NP`;
- `'RULES(CLASSIC)'`: `TSO AI1 1 NAAAPAAARAC01NPC`; `'RULES(CLASSIC) PLAY(TURN)'`: `TSO AI1 1 NAAAPAAATAC01NP`;
- `'AI(0) RULES(CLASSIC) SOUND(NO)'` (S10): `TSO AI0 1 NAAAPAAARNC01NPC`.
Batch and direct calls of PACMAIN are unchanged: a PARM without column 26 is EVERY, without column 21 CLASSIC.
