# PACMAN 2.0-MVS-MAX - benchmarks (MVS-G8, D43 section 3)
Two kinds, kept apart. (1) **Deterministic presentation cost**: bytes per 3270 write, from the Hercules TSD dry-run
streams of the 2.0 build of record (run-only decks on `HERC01.PACMAN.R20.LOAD(PACMAIN)`, JOBs 308-312), every stream
already matched byte for byte against the independent models. Reproducible with `tools/g8_bench.py LISTING...`.
(2) **Live timing**: c3270 traces of real games, analysed by `tools/c3270_rt_game.py`; reused from the validated RP /
S2 sessions (the REALTIME loop is unchanged since), plus the G8 installed-release smoke. Host CPU is not measured
(not part of the release, D43).

## 1. Cost per frame - the profiles that matter
A full screen is an Erase/Write (first screen, PA2 redraw, end screen); an update is everything else (partial redraw of
the changed cells, a REALTIME quantum write, a keyboard restore or a bell-only write). Bytes are the 3270 data stream
sent by TPUT (WCC + orders + data), before TN3270 framing.
| Profile | Runs | Full screen bytes (median / max) | Updates | Update bytes (median / p95 / max) |
|---|---|---|---|---|
| **2.0 default**: ARCADE, REALTIME, GRAPHIC 4x2, partial, 120 x 27 | 34 | 1851 / 1969 | 3576 | 86 / 214 / 837 |
| CLASSIC, REALTIME, GRAPHIC 4x2, partial, 120 x 27 | 14 | 1714 / 1729 | 1357 | 76 / 148 / 184 |
| ARCADE, REALTIME, GRAPHIC 4x2, partial, 80 x 24 (fallback canvas) | 10 | 1868 / 1992 | 1413 | 92 / 210 / 829 |
| CLASSIC, TURN, GRAPHIC 3x2, partial, 80 x 24 | 2 | 1495 / 1537 | 46 | 122 / 278 / 284 |
| CLASSIC, TURN, GRAPHIC not scaled (G4), partial, 80 x 24 | 2 | 912 / 912 | 100 | 60 / 68 / 86 |
| ARCADE, TURN, CLASSIC glyphs not scaled, partial, 80 x 24 | 4 | 644 / 665 | 482 | 61 / 81 / 291 |
| CLASSIC, TURN, full redraw (G1-style), 80 x 24 | 5 | 598 / 670 | 0 | every frame is a full screen |
| Line mode (G0, no full-screen): one status line + 10 board rows per frame | - | - | - | about 260-280 characters per frame plus the TSO prompt (G0 JOB 146) |

Reading: the 2.0 default sends one full screen of about 1.9 KB at the start (and on PA2), then a median of 86 bytes per
150 ms quantum (p95 214); the largest updates (up to 837 bytes) are the death-animation and level-transition frames.
At 150 ms that is a median of about 0.6 KB/s of 3270 data. Every stream fits the 2048-byte limit checked by the
tests (largest full screen 1992 bytes). Partial redraw (G3) is what keeps a quantum write small: a full redraw of the
scaled maze would be about 1.7-1.9 KB every quantum.

## 2. Live timing (c3270 traces, IBM-DYNAMIC 120 x 27)
| Session | Period | Writes / periods | Frame gap median / p95 / max | Lateness median / p95 | Skipped periods | Drift |
|---|---|---|---|---|---|---|
| RP.3 FAST capture (docs/evidence/rp3-fast-live.md) | 125 ms | 343 / 343 | 125 / 133 / 282 ms | 7 / 13 ms | 0 | +0.5 ms / 100 quanta |
| RP.4 Part A NORMAL ARCADE to GAME OVER (docs/evidence/rp-live.md) | 150 ms | 261 / 261 | 150 / 160 / 319 ms | 5 / 15 ms | 0 | +1.9 ms / 100 quanta |
| RP.4 Part B FAST soak, 10.75 min unattended (rp-live.md) | 125 ms | 5164 quanta | - | 7 / 14 ms | 0 in 10.75 min | -0.3 ms / 100 quanta |
| RP.4 FAST after a 603-s pause (rp-live.md) | 125 ms | 189 / 189 | resume +123 / +249 / +374 / +499 ms | 5 / 12 ms | 0 | - |
| S2.4 six scripted runs (docs/evidence/s2-live.md) | 150 / 125 ms | all at the period | median 149-150 / 125 ms | - | 0 late writes | - |
| **G8.4 installed 2.0 release, defaults (docs/evidence/g8-live.md)** | 150 ms | 179 / 179 | 150 / 159 / 166 ms | 5 / 12 ms | 0 | +0.6 ms / 100 quanta |

Jitter in short: the host keeps the absolute 150 / 125 ms grid with single-digit-millisecond median lateness, never
skips a period and does not drift; isolated late writes (about 160 ms) recover on the next write. Keyboard lock per
arrow by hand: median 59-75 ms (RP), below one period.

## 3. Complete table
`python3 tools/g8_bench.py build/PACBLDS2-308.txt build/PACBLDRP-309.txt build/PACBLGP2-310.txt build/PACBLG23-311.txt
build/PACBLDHS-312.txt` (every TSD profile of the R20 regressions; '-' = PARM column absent, the program default;
scale T = the size-guard test (4x2 with a 1000-byte limit, falls back to G4); 100 x 25 and 160 x 30 = alternate sizes
the geometry layer rejects (100 x 25 too small, 160 x 30 over 4095 cells) and replaces by the centred 80 x 24 layout):

| Glyphs | Scale | Redraw | Canvas | Play | Rules | Runs | Full screens: median / max bytes | Updates | Update bytes: median / p95 / max |
|---|---|---|---|---|---|---|---|---|---|
| - | - | full | 80x24 | TURN | CLASSIC | 5 | 598 / 670 | 0 | - |
| - | - | partial | 80x24 | TURN | CLASSIC | 7 | 600 / 641 | 106 | 69 / 128 / 136 |
| AUTO | - | partial | 80x24 | TURN | CLASSIC | 1 | 600 / 600 | 14 | 72 / 92 / 107 |
| AUTO | AUTO | partial | 80x24 | TURN | CLASSIC | 1 | 600 / 600 | 14 | 72 / 92 / 107 |
| BASE | - | full | 80x24 | TURN | CLASSIC | 1 | 564 / 582 | 0 | - |
| BASE | - | partial | 80x24 | TURN | CLASSIC | 2 | 839 / 851 | 28 | 106 / 134 / 136 |
| BASE | 4x2 | partial | 80x24 | TURN | CLASSIC | 1 | 810 / 810 | 14 | 72 / 92 / 107 |
| BASE | no scale | full | 80x24 | TURN | ARCADE | 4 | 741 / 845 | 0 | - |
| BASE | no scale | partial | 120x27 | TURN | ARCADE | 2 | 833 / 833 | 64 | 85 / 106 / 121 |
| CLASSIC | - | partial | 80x24 | TURN | CLASSIC | 1 | 600 / 600 | 14 | 72 / 92 / 107 |
| CLASSIC | no scale | full | 120x27 | TURN | CLASSIC | 2 | 513 / 600 | 2 | 4 / 4 / 4 |
| CLASSIC | no scale | full | 80x24 | TURN | CLASSIC | 1 | 492 / 600 | 1 | 4 / 4 / 4 |
| CLASSIC | no scale | partial | 120x27 | TURN | ARCADE | 1 | 665 / 665 | 49 | 83 / 108 / 142 |
| CLASSIC | no scale | partial | 80x24 | TURN | ARCADE | 4 | 644 / 665 | 482 | 61 / 81 / 291 |
| CLASSIC | no scale | partial | 80x32 | TURN | ARCADE | 2 | 647 / 647 | 68 | 82 / 95 / 121 |
| GRAPHIC | - | full | 80x24 | TURN | CLASSIC | 2 | 698 / 944 | 0 | - |
| GRAPHIC | - | partial | 80x24 | TURN | CLASSIC | 7 | 917 / 949 | 120 | 70 / 133 / 142 |
| GRAPHIC | 3x2 | full | 80x24 | TURN | CLASSIC | 1 | 1492 / 1501 | 0 | - |
| GRAPHIC | 3x2 | partial | 120x27 | TURN | ARCADE | 1 | 1554 / 1560 | 190 | 93 / 113 / 684 |
| GRAPHIC | 3x2 | partial | 120x27 | TURN | CLASSIC | 1 | 1536 / 1537 | 18 | 246 / 280 / 284 |
| GRAPHIC | 3x2 | partial | 80x24 | TURN | CLASSIC | 2 | 1495 / 1537 | 46 | 122 / 278 / 284 |
| GRAPHIC | 3x2 | partial | 80x43 | TURN | ARCADE | 4 | 1520 / 1612 | 446 | 95 / 183 / 684 |
| GRAPHIC | 4x2 | full | 100x25 | TURN | CLASSIC | 1 | 1719 / 1756 | 0 | - |
| GRAPHIC | 4x2 | full | 120x27 | TURN | ARCADE | 2 | 1812 / 1871 | 0 | - |
| GRAPHIC | 4x2 | full | 80x24 | TURN | CLASSIC | 1 | 1544 / 1581 | 0 | - |
| GRAPHIC | 4x2 | partial | 120x27 | REALTIME | ARCADE | 34 | 1851 / 1969 | 3576 | 86 / 214 / 837 |
| GRAPHIC | 4x2 | partial | 120x27 | REALTIME | CLASSIC | 14 | 1714 / 1729 | 1357 | 76 / 148 / 184 |
| GRAPHIC | 4x2 | partial | 120x27 | TURN | ARCADE | 23 | 1822 / 1990 | 2799 | 124 / 288 / 958 |
| GRAPHIC | 4x2 | partial | 120x27 | TURN | CLASSIC | 16 | 1712 / 1827 | 709 | 105 / 196 / 329 |
| GRAPHIC | 4x2 | partial | 132x27 | TURN | ARCADE | 4 | 1808 / 1868 | 244 | 154 / 272 / 320 |
| GRAPHIC | 4x2 | partial | 132x27 | TURN | CLASSIC | 1 | 1827 / 1839 | 10 | 100 / 306 / 306 |
| GRAPHIC | 4x2 | partial | 160x30 | TURN | CLASSIC | 1 | 1606 / 1616 | 14 | 153 / 173 / 189 |
| GRAPHIC | 4x2 | partial | 80x24 | REALTIME | ARCADE | 10 | 1868 / 1992 | 1413 | 92 / 210 / 829 |
| GRAPHIC | 4x2 | partial | 80x24 | REALTIME | CLASSIC | 4 | 1729 / 1731 | 343 | 136 / 153 / 180 |
| GRAPHIC | 4x2 | partial | 80x24 | TURN | ARCADE | 16 | 1808 / 1969 | 1317 | 110 / 208 / 754 |
| GRAPHIC | 4x2 | partial | 80x24 | TURN | CLASSIC | 12 | 1566 / 1729 | 859 | 114 / 181 / 321 |
| GRAPHIC | 4x2 | partial | 80x32 | TURN | CLASSIC | 1 | 1718 / 1731 | 18 | 290 / 333 / 336 |
| GRAPHIC | 4x2 | partial | 80x43 | REALTIME | ARCADE | 7 | 1667 / 1969 | 477 | 94 / 217 / 304 |
| GRAPHIC | 4x2 | partial | 80x43 | TURN | ARCADE | 3 | 1868 / 1911 | 218 | 106 / 162 / 764 |
| GRAPHIC | 4x2 | partial | 80x43 | TURN | CLASSIC | 1 | 1723 / 1775 | 28 | 126 / 152 / 153 |
| GRAPHIC | AUTO | partial | 80x24 | TURN | CLASSIC | 1 | 1546 / 1556 | 14 | 153 / 173 / 189 |
| GRAPHIC | T | partial | 120x27 | TURN | ARCADE | 2 | 914 / 914 | 380 | 61 / 71 / 388 |
| GRAPHIC | T | partial | 80x24 | TURN | CLASSIC | 2 | 941 / 941 | 36 | 115 / 141 / 142 |
| GRAPHIC | T | partial | 80x32 | TURN | ARCADE | 2 | 943 / 943 | 102 | 74 / 93 / 108 |
| GRAPHIC | no scale | partial | 120x27 | TURN | ARCADE | 4 | 914 / 943 | 498 | 63 / 85 / 388 |
| GRAPHIC | no scale | partial | 120x27 | TURN | CLASSIC | 2 | 941 / 949 | 24 | 74 / 133 / 133 |
| GRAPHIC | no scale | partial | 80x24 | TURN | ARCADE | 5 | 931 / 938 | 332 | 67 / 97 / 398 |
| GRAPHIC | no scale | partial | 80x24 | TURN | CLASSIC | 2 | 912 / 912 | 100 | 60 / 68 / 86 |
