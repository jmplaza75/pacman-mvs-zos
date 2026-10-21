# PACMAN 2.1-mvs - release manifest (MVS-10, D46)
Identifies the release and how it was built, verified, installed and live-checked. Every JOB ran on TK4- / MVS 3.8J
under Hercules; listings are kept locally (`build/<JOBNAME>-<n>.txt`, not committed: JES data), the extracted evidence
is in `docs/evidence/mvs10-release.md`. Decks in `decks/` are the exact decks submitted (no credentials:
`tools/submit.sh` adds them from `.env` at submission).

## Identity
| Item | Value |
|---|---|
| Release | 2.1-mvs (annotated tags `mvs-10` and `2.1-mvs` on the MVS-10 closure commit) |
| Source revision of the build | `815c98b08e0c3ff36adb566de52a7a2843fc5faf` (`src/` unchanged since; `SHA256SUMS`) |
| Change vs 2.0-MVS-MAX | PACINPT RT-TSC `IF WS-V = 123` (PF11) -> `IF WS-V = 124` (PF12) + its comment; the CLIST ARROWS help comment |
| Load module of record | `HERC01.PACMAN.R21.LOAD(PACMAIN)`, JOB 321 (REL20 deck): ENTRY PACMAIN, TOTAL LENGTH X'308F8', "PACMAIN DOES NOT EXIST BUT HAS BEEN ADDED" (fresh library) |
| Installed module | `HERC01.PACMAN.LOAD(PACMAIN)` = IEBCOPY copy of the module of record (JOB 328); AMASPZAP dumps identical (33 CSECTs, 4494 hex rows); dump SHA-256 `78b09d28be15a76d76202f6f9f0f99921bc7230788821b18adb516073e0dbd39`, re-verified after the DASD recovery (JOB 333) |
| Difference to the installed 2.0 module | exactly one dump row: CSECT PACINPT offset X'780', packed literal `123C` -> `124C` |
| Installed launcher | `HERC01.PACMAN.CLIST(PACMAN)`, JOB 331 (printed back = `src/clist/PACMAN.clist`, 75 lines); R21 copy JOB 327; re-verified JOB 333 |
| Rollback | `HERC01.PACMAN.R20.LOAD(PACMAIN)` (the 2.0 module of record, untouched) |

## Build of record and verification (2026-10-20 / 21)
| JOB | Deck (`decks/`) | What | Result |
|---|---|---|---|
| 319 | R21-CHECK.jcl | read-only LISTCAT LEVEL(HERC01.PACMAN.R21) | IDC3012I NOT FOUND: nothing reused |
| 320 | R21-ALLOC.jcl | new empty COBOL, COPY, LOAD, CLIST, DATA under `HERC01.PACMAN.R21` | RC 0000 |
| 321 | R21-REL20.jcl | upload + compile + assemble + link R21 PACMAIN; 1.0-MVS oracle; CLIST PARMs | 60 steps RC 0000, no warnings, PASS |
| 322-326 | R21-S2 / RP / GP2 / GP23 / HS.jcl | run-only regressions on the module of record | PASS (S2 2986 streams, RP 1495 + 6268, GP2 208 steps, S1 134, HS) |
| 327 | R21-CLIST.jcl | R21 launcher stored and printed back | PASS |
| 328 | R21-INST.jcl | IEBCOPY R21 -> installed PACMAIN + AMASPZAP dumps of both | PASS, identical |
| 329, 330 | R21-INST-ORACLE / R21-INST-S2.jcl | run-only on the installed member | PASS |
| 331 | R21-INST-CLIST.jcl | installed launcher stored and printed back | PASS |
| 332 | R21-DIAG-ORACLE.jcl | after the DASD recovery: 1.0 oracle run-only on R21 (read-only) | PASS, = JOB 321 blocks |
| 333 | R21-DIAG-VERIFY.jcl | after the recovery: read-only dumps + installed CLIST print | PASS (PTPCH step RC 0012: deck control-statement error, see evidence) |
| live | (tools/mvs10_live.py, tests/mvs10live/LIVE10.txt) | installed release in c3270, checked by tools/mvs10_trace.py | MVS-10 LIVE GATE PASS, 68 / 68 writes = model |
Every R21 deck and listing passed `tools/g8_jcl_audit.py --prefix HERC01.PACMAN.R21` (the install / verify decks the
same audit at `HERC01.PACMAN`).
