# MVS-HS: persistent high score under RULES(ARCADE) - design (D38, APPROVED 2026-10-12 with the D4 amendment)
Source: docs/ROADMAP-POST-RT.md row 4 ("Top ARCADE score kept in `HERC01.PACMAN.DATA(HISCORE)` through PACPLAT (read at
start, rewritten when beaten). GAME never sees the file. A missing or bad member means 0, never a failure. Batch tests
use a test member.") and probe E16 (docs/evidence/hs-e16-probe.md, JOB 254, PASS), which proved the disk access this
design uses. Nothing in GAME / MAP / AI changes: no authorised core change is needed.
Status: approved by the user on 2026-10-12. D1, D2, D3, D5, D6 as proposed; D4 amended (empty / bad data self-heals
on the next eligible save; `NOT SAVED` only for a write that was attempted and failed); the semantics of section 1
made explicit. Frozen as D38 in docs/DECISIONS.md.

## 0. Steps
| Step | Content | Exit |
|---|---|---|
| HS.0 | probe E16: one record in a PDS member, batch + TSO, every failure case | PASS, JOB 254 (docs/evidence/hs-e16-probe.md) |
| HS.1 | this design | approved 2026-10-12, D38 frozen |
| HS.2 | PACHSIO (production service from PACHSA, + REPL and the abend guard), PACPLAT ops HSRD/HSWR, PACREQ (appended), PACMAIN (two calls), PACDISP end lines, CLIST, ALLOC + DATA decks | deck `HS`, tests/test_hs.py: CLASSIC and every ARCADE run without a DD = earlier references byte for byte; ARCADE runs with a DD = independent model (lines + member content) |
| HS.3 | live c3270 checklist (new high score, lower score, missing dataset, missing member) | docs/evidence/hs-live.md, README, CURRENT_PHASE, tag `mvs-hs` |

## 1. Semantics (D38)
- Persistence is ARCADE only (`RULES(ARCADE)`). CLASSIC = 1.0-MVS byte for byte: no read, no write, no line, even with
  a DD.
- One global ARCADE high score: not per level, AI setting, ghost count, PLAY or display mode.
- In-memory high score = max(persistent value, current score): it rises immediately whenever the current score
  exceeds it. HS shows it in the end lines; the RP HUD will show the same derived value during play (no per-step state
  is added for it).
- Eligible game (D2, D3): an ARCADE game started at level 1 (`LEVEL(1)`, the default), whatever its end (LOST, WIN,
  QUIT, EOF). A `LEVEL(n>1)` start loads and shows the high score but never saves one.
- Disk is written only when the persistent value must increase: an eligible game whose final score is strictly
  greater than the persistent value. An equal score does not rewrite the record. The persistent high score can never
  decrease.
- The level stored with the record is the highest level reached by the run that set the score (`ARC-LEVEL` at the end
  of that run: the level never decreases within a run).
- Missing member, empty member, malformed record: high score 0; the next eligible save writes a valid one-record member
  in its place (self-healing, D4). A valid record is updated in place, only when beaten.
- `HIGH SCORE NOT SAVED` means a write was attempted and failed. `HIGH SCORE UNAVAILABLE` means persistence is not
  usable (DD present but no usable dataset / member, e.g. the CLIST found no DATA dataset).
- No `PACHS` DD at all = persistence not configured: silent, no line (every batch reference and existing deck).
- An I/O or persistence problem never abends PACMAN, never changes the gameplay result and never prevents the clean
  return to READY (PACHSIO guards its I/O, section 3).
- No new alarm for a high score (sound unchanged; celebration belongs to RP / S2). No screen change in HS: the HUD
  high score is RP work; in colour mode the end lines follow the final screen in line mode (unchanged mechanism).

## 2. Storage
- Dataset `<prefix>.DATA` (default `HERC01.PACMAN.DATA`): PDS, RECFM FB, LRECL 80, **BLKSIZE 80** (one record per block;
  PACHSIO refuses any other attributes, E16), SPACE (TRK,(1,1,5)). Member `HISCORE`. It is not a build library: the
  build decks and COMPRESS never touch it, so a rebuild cannot erase the player's score.
- Install (D6): the ALLOC deck (fresh installs, 2.0 rebuild) creates it with the libraries; a new one-time deck
  `make_deck.py DATA` creates it on the current install (fails harmlessly with NOT CATLGD 2 if it exists). The member
  is not seeded.
- Updates of a valid record are in place (E16: same TTR): no space consumed. Only a heal / first save writes a new
  member block (one block, once).
- Record (D1, 80 bytes, display digits):

| Columns | Content |
|---|---|
| 1-7 | high score, 7 digits (`ARC-SCORE` is `PIC 9(7)`) |
| 8 | blank |
| 9-16 | format tag `PACHS001` |
| 17 | blank |
| 18-20 | level reached by the run that set it, 3 digits |
| 21-80 | blank |

  Valid = columns 1-7 numeric and columns 9-16 = `PACHS001`. No date, no initials.

## 3. PACHSIO (src/asm/PACHSIO.asm, production form of the E16 PACHSA)
`CALL 'PACHSIO' USING OP RC DDN REC` - RC `S9(4) COMP`, DDN `X(8)` (PACPLAT passes `PACHS`), REC `X(80)`.
- `READ`: as E16. RC 0 record, 4 no DD, 8 unusable (DUMMY / no member on the DD / not a PDS with FB 80/80), 12 member
  missing or empty, 16 I/O error.
- `WRIT` (valid record on disk): QSAM UPDAT, GET + PUTX of the first record, RC 0. If the member is missing or empty
  at that moment it falls through to REPL.
- `REPL` (missing / empty / bad data): QSAM OUTPUT of one record to the member named on the DD (STOW replaces or adds
  at CLOSE), RC 2. The fresh-RDJFCB safety check of E16 runs before every QSAM OPEN (never the whole PDS).
- Abend guard: the I/O of every call runs under an ESTAE whose exit retries into PACHSIO's return path with RC 16
  (any 013, x37, B14, 913 ... during OPEN, GET, PUT, PUTX, CLOSE or STOW). Removed before returning, so the PACFSIO
  ESTAE stays as it is.
- Linked into PACMAIN with PACTSO and PACFSIO; only PACPLAT calls it. Works in batch and TSO (E16).

## 4. Flow
1. Start - PACMAIN, right after `PACPLAT INIT`, only when `REQ-RULES = 'A'`: `PACPLAT HSRD` (READ):

| PACHSIO READ | REQ-HSST | REQ-HISCORE / REQ-HSLVL |
|---|---|---|
| RC 4 (no DD) | `N` not configured, silent | 0 / 0 |
| RC 0, valid record | `R` | the record |
| RC 0 malformed, RC 12 | `Z` (heal on the next save) | 0 / 0 |
| RC 8, 16 | `E` unavailable | 0 / 0 |

2. End - PACMAIN, after the game loop and before `PACDISP END`, only when `REQ-RULES = 'A'`: copies `ARC-SCORE`,
   `ARC-LEVEL` and the eligibility (`REQ-START = 01`) into `REQ-HSSCORE`, `REQ-HSGLVL`, `REQ-HSELIG`, then
   `PACPLAT HSWR`. PACPLAT decides (not GAME, not the driver):
   - `REQ-HSST` `R` or `Z` and `REQ-HSSCORE > REQ-HISCORE`: eligible -> write (`R`: WRIT, `Z`: REPL). RC 0 / 2:
     `REQ-HSNEW = 'Y'`, REQ-HISCORE / REQ-HSLVL := score / level. Other RC: `REQ-HSNEW = 'F'`, the persistent values
     stay. Not eligible: `REQ-HSNEW = 'P'` (practice start), nothing written.
   - anything else: `REQ-HSNEW = 'N'`, nothing written.
3. One write at most per game, after the last frame; an abend of the game itself before it writes nothing (the record
   is one block).
4. Concurrency: TSO allocates the member SHR; one TSO session per user. Two users sharing one prefix = last writer
   wins (documented, not tested).

## 5. Text output (ARCADE, REQ-HSST not `N`)
After the existing ARCADE end lines (`... LEVEL nnn`), before METRICS:
```
HIGH SCORE nnnnnnn LEVEL nnn               in-memory high score: max(persistent, this game's score) and its level
NEW HIGH SCORE                             REQ-HSNEW = Y (saved)
HIGH SCORE NOT SAVED                       REQ-HSNEW = F (write attempted and failed)
START LEVEL nn: HIGH SCORE NOT RECORDED    REQ-HSNEW = P (beaten by a LEVEL(n>1) game)
HIGH SCORE UNAVAILABLE                     instead of all the above when REQ-HSST = E
```
When the game did not beat the persistent value the first line shows the persistent value and its level.
`HIGH SCORE 0000000 LEVEL 000` = nothing recorded yet and a score of 0. METRICS line and character counters include
the new lines. No bell.

## 6. PACREQ (appended, adapter interface, no authorisation needed)
```
      * MVS-HS (D38): HIGH SCORE (ARCADE ONLY). REQ-HSST N NOT
      * CONFIGURED (NO DD), R LOADED, Z ZERO (MISSING/EMPTY/BAD:
      * HEALED ON SAVE), E UNAVAILABLE. REQ-HSNEW Y SAVED, F NOT
      * SAVED (WRITE FAILED), P PRACTICE START (NOT RECORDED), N NO.
           05  REQ-HSST              PIC X.
           05  REQ-HISCORE           PIC 9(7).
           05  REQ-HSLVL             PIC 999.
           05  REQ-HSSCORE           PIC 9(7).
           05  REQ-HSGLVL            PIC 999.
           05  REQ-HSELIG            PIC X.
           05  REQ-HSNEW             PIC X.
```

## 7. CLIST (D5)
No new keyword. Only for `RULES(ARCADE)`; CLASSIC allocates nothing. The `&SYSDSN` pre-check prevents the CLIST from
ending on a failed ALLOC (E16):
- DATA exists: `ALLOC F(PACHS) DA('<prefix>.DATA(HISCORE)') SHR REUSE`.
- DATA missing: `ALLOC F(PACHS) DUMMY REUSE` -> PACHSIO READ RC 8 -> `HIGH SCORE UNAVAILABLE`; the game plays normally.
- After the CALL: `FREE F(PACHS)` when allocated.
(Exact syntax checked against the 72-column rule; the DUMMY path is also a batch test, the CLIST itself in HS.3 live.)
The RUN deck (batch play) gets an optional `--hiscore` switch that adds the DD.

## 8. Tests (D9, D10, D12)
Deck `HS` (job PACBLDHS): full build (+ PACHSIO), scratch PDSs `<prefix>.HSTEST` (FB 80/80) and `<prefix>.HSFULL`
(FB 80/80, one directory block, filled) created at the start and deleted at the end (production `DATA(HISCORE)` is
never touched by a test), runs, IEBGENER prints of the test members after the runs that write. Independent model
tests/ref_hs.py (record parse / validate / compare / expected end lines and member content); the game lines come from
the existing tests/ref_gp2.py. Every edge case of this design is a case (D12):

| Case | Setup | Expected |
|---|---|---|
| H0 | existing ARCADE / CLASSIC runs, no DD | byte-identical to the GP2 / S1 / oracle references |
| H1 | eligible scoring game, member missing | first line = score, `NEW HIGH SCORE`, member created (REPL) |
| H2 | next step, lower score | persistent value shown, no second line, member unchanged |
| H3 | equal score | not new, member unchanged |
| H4 | higher score | NEW, record updated in place (WRIT) |
| H5 | malformed member (several records) | counts as 0; healed: member = one valid record |
| H6 | empty member | counts as 0; healed: member = one valid record |
| H7 | DD without a member name / DD DUMMY | `HIGH SCORE UNAVAILABLE`, nothing written, PDS untouched |
| H8 | score 0 (immediate Q), member missing | `HIGH SCORE 0000000 LEVEL 000`, nothing created |
| H9 | member `9999999` | not new (no overflow), member unchanged |
| H10 | `LEVEL(5)` start beating the record | in-memory value shown, `START LEVEL 05: HIGH SCORE NOT RECORDED`, member unchanged |
| H11 | eligible QUIT / EOF / LOST / WIN ends | each saves when beaten |
| H12 | CLASSIC with the DD | identical to the oracle, member untouched |
| H13 | REALTIME batch and TSD dry run with the DD | lines as H1-H4; TSD screen streams = the GP2 streams |
| H14 | TSO line mode through IKJEFT01, `ALLOC ... SHR` | same as batch |
| H15 | eligible new score, missing member in the full-directory PDS | STOW fails (B14) inside PACHSIO, caught: `HIGH SCORE NOT SAVED`, game result and end lines otherwise unchanged, step RC 0 |

Write failure: H15 is a genuine write failure (directory full), with no test hook. A physical device / I/O error
(SYNAD) cannot be induced in the normal Hercules environment; that path shares the same RC 16 handling and is
documented as not induced.

Regression kept: tests/test_gp2.py (+ test_gp1, test_s1, test_rt, test_gx, test_gs, test_g4, test_core_frozen). The
deck stays below the 255-step JES limit (HS cases + a representative regression subset); the GP2 decks are rerun
unchanged against the new load module.

## 9. Decisions (user, 2026-10-12)
- D1 Record: 7-digit score, level reached, format tag; no date, no initials. Approved.
- D2 Eligible starts: only `LEVEL(1)`; `LEVEL(n>1)` loads / shows, never saves. Approved.
- D3 Eligible ends: LOST, WIN, QUIT, EOF. Approved.
- D4 Amended: missing / empty / malformed = 0 and healed by the next eligible save; a valid record is updated only when
  beaten; `NOT SAVED` = a failed attempted write, tested by the narrowest genuine mechanism (H15), not by weakening the
  product behaviour; `UNAVAILABLE` = no usable DD / dataset.
- D5 CLIST: no keyword; automatic for ARCADE when the dataset exists; otherwise the game plays without persistence;
  `&SYSDSN` pre-check approved; CLASSIC unaffected. Approved.
- D6 Install: ALLOC deck + one-time DATA deck; the data stays outside the build libraries. Approved.
- Additional: semantics of section 1; no new alarm.
