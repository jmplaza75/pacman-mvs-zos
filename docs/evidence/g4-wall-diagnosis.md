# MVS-G4 wall geometry diagnosis (2026-10-08) - live visual acceptance FAIL, investigation
Live (user): BASE and GRAPHIC make the maze hard to read compared with CLASSIC; internal walls do not seem to keep the
CLASSIC structure. Both profiles share the wall shaping, so it was examined first (no code changed).
Source of truth = the REAL first full screens of JOB 191 (docs/evidence/g4-build-tsd.txt: TSD run 1 CLASSIC, run 13 GRAPHIC,
run 22 BASE) decoded back to the 20 x 10 board (orders skipped, GE X'08' + code mapped to the c3270 Unicode of E9):
```
     CLASSIC (real)         BASE (real, MULTI)     GRAPHIC (real)
 1   ####################   +--------++--------+   ┌────────┬┬────────┐
 2   #C.......##........#   |C·······++·······G|   │⊂•••••••├┤••••••••│
 3   #.##.###.##.###.##.#   |·--·---·++·---·--·|   │•──•───•└┘•───•──•│
 4   #..................#   |··················|   │••••••••••••••••••│
 5   #.##.#.######.#.##.#   |·--·|·--++--·|·--·|   │•──•│•──┬┬──•│•──•│
 6   #....#...##...#....#   |····|···++···|····|   │••••│•••├┤•••│••••│
 7   #.##.###.##.###.##.#   |·--·+--·++·--+·--·|   │•──•└──•└┘•──┘•──•│
 8   #..................#   |··················|   │••••••••••••••••••│
 9   #.................G#   |G················G|   │•••••••••••••••••∩│
10   ####################   +------------------+   └──────────────────┘
```
## Cell-level checks (98 wall cells)
- Same wall cell set in all three: every `#` is a wall glyph in BASE/GRAPHIC, no wall glyph on an open cell.
- GRAPHIC glyph arms = the cell's wall neighbours for all 98 cells, except the 22 single-neighbour cells (masks 2, 4, 8:
  ends of the short `##` bars), drawn as a full `─`/`│` (the stroke stays inside the wall cell).
- BASE: 18 cells of masks 3, 6, 7, 9, 12, 13, 14 (corners and tees) all become `+`: the direction of the corner is lost and
  each draws arms towards open corridor cells (e.g. y7 x6 `└` -> `+` shows a stroke towards the corridor below).
- 2 x 2 solid wall blocks: 4 (top-left x10,y1 / x10,y2 / x10,y5 / x10,y6) = the two 2-wide stubs; GRAPHIC draws them as
  ladders `┬┬ / ├┤ / └┘` (two parallel walls with rungs and closed cavities), BASE as `++ / ++ / ++`.

## Conclusion: hypothesis CONFIRMED
The algorithm draws the centre-line connectivity graph of the wall cells (strokes from each cell centre to its wall
neighbours). It never invents or removes an orthogonal connection, but it is not a faithful picture of the barriers:
1. a wall cell becomes a thin stroke through its centre, so a blocked cell is no longer visibly occupied; wall rows such as
   `•──•───•` have the same visual weight as the corridor rows next to them (the main readability loss, both profiles);
2. solid 2-wide areas turn into ladders with false internal cavities (structure CLASSIC does not have);
3. BASE has only `+ - |`: 8 different corner/tee shapes collapse to `+`, which also suggests arms into open cells.
It is not a CP310/GE transport issue: the decoded real streams equal the model and the live screens showed no garbage.

## Per-coordinate table (y, x 1-based; mask N1 E2 S4 W8; arms used by PACSCR; glyph sent)
```
y  x  mask arms graphic base
 1  1    6 ES   ┌       +
 1  2   10 EW   ─       -
 1  3   10 EW   ─       -
 1  4   10 EW   ─       -
 1  5   10 EW   ─       -
 1  6   10 EW   ─       -
 1  7   10 EW   ─       -
 1  8   10 EW   ─       -
 1  9   10 EW   ─       -
 1 10   14 ESW  ┬       +
 1 11   14 ESW  ┬       +
 1 12   10 EW   ─       -
 1 13   10 EW   ─       -
 1 14   10 EW   ─       -
 1 15   10 EW   ─       -
 1 16   10 EW   ─       -
 1 17   10 EW   ─       -
 1 18   10 EW   ─       -
 1 19   10 EW   ─       -
 1 20   12 SW   ┐       +
 2  1    5 NS   │       |
 2 10    7 NES  ├       +
 2 11   13 NSW  ┤       +
 2 20    5 NS   │       |
 3  1    5 NS   │       |
 3  3    2 E    ─       -
 3  4    8 W    ─       -
 3  6    2 E    ─       -
 3  7   10 EW   ─       -
 3  8    8 W    ─       -
 3 10    3 NE   └       +
 3 11    9 NW   ┘       +
 3 13    2 E    ─       -
 3 14   10 EW   ─       -
 3 15    8 W    ─       -
 3 17    2 E    ─       -
 3 18    8 W    ─       -
 3 20    5 NS   │       |
 4  1    5 NS   │       |
 4 20    5 NS   │       |
 5  1    5 NS   │       |
 5  3    2 E    ─       -
 5  4    8 W    ─       -
 5  6    4 S    │       |
 5  8    2 E    ─       -
 5  9   10 EW   ─       -
 5 10   14 ESW  ┬       +
 5 11   14 ESW  ┬       +
 5 12   10 EW   ─       -
 5 13    8 W    ─       -
 5 15    4 S    │       |
 5 17    2 E    ─       -
 5 18    8 W    ─       -
 5 20    5 NS   │       |
 6  1    5 NS   │       |
 6  6    5 NS   │       |
 6 10    7 NES  ├       +
 6 11   13 NSW  ┤       +
 6 15    5 NS   │       |
 6 20    5 NS   │       |
 7  1    5 NS   │       |
 7  3    2 E    ─       -
 7  4    8 W    ─       -
 7  6    3 NE   └       +
 7  7   10 EW   ─       -
 7  8    8 W    ─       -
 7 10    3 NE   └       +
 7 11    9 NW   ┘       +
 7 13    2 E    ─       -
 7 14   10 EW   ─       -
 7 15    9 NW   ┘       +
 7 17    2 E    ─       -
 7 18    8 W    ─       -
 7 20    5 NS   │       |
 8  1    5 NS   │       |
 8 20    5 NS   │       |
 9  1    5 NS   │       |
 9 20    5 NS   │       |
10  1    3 NE   └       +
10  2   10 EW   ─       -
10  3   10 EW   ─       -
10  4   10 EW   ─       -
10  5   10 EW   ─       -
10  6   10 EW   ─       -
10  7   10 EW   ─       -
10  8   10 EW   ─       -
10  9   10 EW   ─       -
10 10   10 EW   ─       -
10 11   10 EW   ─       -
10 12   10 EW   ─       -
10 13   10 EW   ─       -
10 14   10 EW   ─       -
10 15   10 EW   ─       -
10 16   10 EW   ─       -
10 17   10 EW   ─       -
10 18   10 EW   ─       -
10 19   10 EW   ─       -
10 20    9 NW   ┘       +
```

## Alternatives considered and decision (user, 2026-10-08)
```
A FILLED (solid wall cells)            B OUTLINE (box drawing, inner strokes removed)
████████████████████                   ┌────────┬┬────────┐
█••••••••██••••••••█                   │••••••••││••••••••│
█•██•███•██•███•██•█                   │•──•───•└┘•───•──•│
█••••••••••••••••••█                   │••••••••••••••••••│
█•██•█•██████•█•██•█                   │•──•│•──┬┬──•│•──•│
█••••█•••██•••█••••█                   │••••│•••││•••│••••│
█•██•███•██•███•██•█                   │•──•└──•└┘•──┘•──•│
```
- A (CHOSEN): each wall cell a blank in the wall colour with reverse video (`#` when highlighting is off): same cell set and
  shape as CLASSIC by construction.
- B (not chosen): drop a stroke between two wall cells when both sides of it are walls; removes the ladders but 1-cell
  walls stay thin strokes and BASE still has no corners.
- C (deferred): arcade contours need sub-cell resolution -> future scaled renderer, preferably 2 x 2 (board 40 x 20).
Result of A: JOB 195, every replayed screen keeps exactly the 98 LEVEL1 wall cells occupied (tests/test_g4.py).
