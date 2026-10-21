# MVS-10 - REALTIME Right on PF12 (D46; release 2.1-mvs) - evidence (2026-10-20 / 21)
Design: docs/MVS10-PF12.md. Release material: releases/2.1-MVS/. Listings `build/<JOB>-<n>.txt`, the c3270 trace and the
driver log stay outside git (JES data, terminal data); their SHA-256 are recorded here. No credential appears anywhere.

## 1. Result
**MVS-10 CLOSED / PASS; release 2.1-mvs.** REALTIME Right is PF12 (X'7C'); PF11 (X'7B') does nothing; no PF key quits;
QUIT is only `Q` + ENTER; TURN, batch, the game and every oracle unchanged. Built from source revision
`815c98b08e0c3ff36adb566de52a7a2843fc5faf`; the installed program differs from the installed 2.0 program by one byte.

## 2. Host jobs (TK4- / MVS 3.8J, HERC01; prefix of the new libraries HERC01.PACMAN.R21)
| JOB | Role | Result |
|---|---|---|
| 319 PACR21CK | read-only LISTCAT LEVEL(HERC01.PACMAN.R21) | RC 0004, IDC3012I NOT FOUND: no R21 dataset existed |
| 320 PACALC10 | ALLOC R21 COBOL / COPY / LOAD / CLIST / DATA (DISP=NEW) | RC 0000, 5 CATALOGED |
| 321 PACREL20 | build of record: upload, IKFCBL00 x 10, IFOX00 x 3, IEWL `R21.LOAD(PACMAIN)`; 1.0-MVS oracle; CLIST PARMs | 60 steps RC 0000, no warnings; ENTRY PACMAIN, TOTAL LENGTH X'308F8', "DOES NOT EXIST BUT HAS BEEN ADDED"; listing shows `IF WS-V = 124` |
| 322 PACBLDS2 | S2 run-only on R21 | 31 steps RC 0000; 25 TSD runs = 2986 model streams; 4 BAT / TSO = oracle / models |
| 323 PACBLDRP | RP run-only | 12 TSD runs = 1495 model streams; 9 BAT = 6268 model lines; CLIST PARM 7 sets |
| 324 PACBLGP2, 325 PACBLG23, 326 PACBLDHS | GP2 / GP23 / HS run-only | GP2 208 steps RC 0000; S1 regression 134 steps; RT regression; HS 42 steps (HSFILL RC 0012 by design) PASS |
| 327 PACCLS10 | R21 CLIST store + print back | 75 lines = src/clist/PACMAN.clist for HERC01.PACMAN.R21 |
| 328 PACINS20 | promotion: IEBCOPY R21 -> HERC01.PACMAN.LOAD(PACMAIN) (replace) + AMASPZAP DUMP of both | COPY / MARK / ZAPSRC / ZAPINST RC 0000; IEB154I PACMAIN COPIED; dumps identical (33 CSECTs, 4494 hex rows) |
| 329 PACREL10 | 1.0-MVS oracle run-only on the installed member | 26 steps RC 0000; 25 blocks = JOB 321 |
| 330 PACBLDS2 | S2 run-only on the installed member | PASS (2986 streams) |
| 331 PACCLS10 | installed CLIST store + print back | 75 lines = src/clist/PACMAN.clist for HERC01.PACMAN |
| 332 PACREL10 | after the DASD recovery: 1.0 oracle run-only on R21 (read-only) | 26 steps RC 0000; 25 blocks = JOB 321 |
| 333 PACVER21 | after the recovery: read-only AMASPZAP dumps (R21, installed) + installed CLIST print (IEBGENER, IEBPTPCH) | MARK / ZAPSRC / ZAPINST / PRINT RC 0000; PTPCH RC 0012 (section 5) |
Every deck and listing passed tools/g8_jcl_audit.py (R21 decks at HERC01.PACMAN.R21, install / verify at
HERC01.PACMAN); every validation by tests/test_g8.py (--rel20, --s2, --rp, --gp2, --gp23, --hs, --clist, --inst, --oracle).

## 3. Byte identity
- Installed PACMAIN = R21 PACMAIN: AMASPZAP dumps identical (JOB 328, again JOB 333).
- Installed dump SHA-256 (the normalised dump rows of tests/test_g8.py zap_dumps):
  `78b09d28be15a76d76202f6f9f0f99921bc7230788821b18adb516073e0dbd39` (JOB 328 = JOB 333; R21 dump the same).
- Against the installed 2.0 module (JOB 314, dump SHA-256 `812ee8bf880614510ed67042e34835e6efb4491a063e93f215cfa020b5431484`):
  4527 dump rows, exactly one differs - CSECT PACINPT (LEN 16A8), offset X'780':
  `247C248C 122C123C 249C110C ...` -> `247C248C 122C124C 249C110C ...` (the RT-TSC literal table: PF11 123C -> PF12 124C).

## 4. Host DASD incident and recovery (2026-10-21; before JOBs 332 / 333 and the live gate)
- Two Hercules instances opened the same CCKD volumes: the unattended `./mvs` instance started from this session on
  2026-10-20 was still running when a second instance was started. The JOBs 319-331 had completed before.
- `dasd/mvsdlb.248` was corrupted; cckdcdsk recovered 260 track images on a copy; the repaired volume passes
  `cckdcdsk -f -ro -3` and is active. Preserved (untouched): `mvsdlb.248.corrupt-20261021` and
  `mvsdlb.248.pre-recovery-20261021` (both SHA-256 `85d62e8d324ea97a2a892c42a2815cfdd4358f3d0677ccbf9b33789777418ba5`),
  `mvsdlb.248.repaired` (`47fcc41e858df59ba70b09e6b46446709a7561dfc33b8bf2308d3a062310780f`).
- The former `mvsres.148` (SHA-256 `88e6fe1b0ea07eade6dacc649e46703bc84b8d308c2efd3c66f72686a4227036`) passes cckdcdsk
  structurally but `ipl 148` always ends in `HHC00809I disabled wait state 00020000 80000005`: retired, preserved as
  `dasd/mvsres.148.pre-pristine-test-20261021`.
- Active system volume: `mvsres.148` from the pristine TK4- image (tk4-_v1.00_current.zip, SHA-256 at extraction
  `96323a17451bf0950369c8f54f1bf8caea69ca2ee23bb3b4217f180f2a45787e`, cckdcdsk clean). After this phase (clean shutdown)
  it is `cc72aebf4e97476fa80b60fde3136f4272c04a80f17c365c55e8b49b668a28b8` (17518881 bytes), preserved as
  `dasd/mvsres.148.post-recovery-mvs10-20261021` (same SHA-256, read-only).
- Boot procedure since the recovery (docs/ENVIRONMENT.md): `./start_herc`, console `c3270 -model 2
  CONS@127.0.0.1:3270`, `ipl 148`, at IEA101A `R 00,CMD=02`.

## 5. Restored-environment checks
- TSO (by the user): `EXEC 'HERC01.PACMAN.R21.CLIST(PACMAN)' 'RULES(CLASSIC) PLAY(TURN) COLOR(NO)'` - board, Q + ENTER,
  READY. (A bare `CALL '...R21.LOAD(PACMAIN)'` ends IKJ56641I by design: PACMAIN needs the CLIST's SYSIN / SYSOUT
  allocations and PARM - not a fault.)
- JOB 332: the 25 1.0-MVS blocks of R21 = the pre-incident build of record (JOB 321).
- JOB 333: R21 and installed dumps identical and equal to JOB 328 (SHA-256 above); the installed CLIST printed by
  IEBGENER = the 75 source lines exactly once, = the JOB 331 print-back. The IEBPTPCH step ended RC 0012 with
  `IEB414I MAXNAME PARAMETER IS TOO SMALL`: the diagnostic deck's PRINT statement lacked MAXNAME=1 for its MEMBER
  statement - a deck control-statement error, nothing printed, no data effect, not a product failure; the IEBGENER
  comparison is authoritative.

## 6. Live gate (installed release, c3270 4.5 via tools/c3270_rt.sh, 120 x 27)
- Driver tools/mvs10_live.py (48 tokens of tests/mvs10live/LIVE10.txt): `EXEC 'HERC01.PACMAN.CLIST(PACMAN)'
  'RULES(CLASSIC) AI(0) GHOSTS(1) SOUND(NO)'` (CLASSIC: no high-score dataset). Checker tools/mvs10_trace.py:
  **MVS-10 LIVE GATE PASS**.
- 68 live screen writes, 68 = the 2.1 model byte for byte; the 2.0 mapping (PF11 R, PF12 nothing) reproduces only 29;
  "PF12 ignored" and "PF11 as Right" controls both fail to reproduce -> PF12 moved right, PF11 did not.
- PF12 and PF11 reached the host as AID-only records (no ENTER, no field); PF12 x 3, PF11 x 3, the game continued
  after each; PF1-PF24 swept (PF1-PF6, PF13-PF24 ignored, PF7 / PF8 / PF10 moves, PF9 pause + resume, PA2 redraw), no
  PF key ended the game. End: QUIT banner, `QUIT / TURNS 025 / SCORE 0250 / LIVES 3 / QUANTA 0000065`, READY.
- **Q hold (3270 behaviour on TK4- + c3270)**: typing `Q` alone caused no host input; the typed `Q` survived 20
  subsequent game screen writes; ENTER then transmitted `Q` and the game quit. On this combination the game's partial
  screen writes do not erase the untransmitted input field.
- Evidence files (outside git, read-only):
  | File | Size | SHA-256 |
  |---|---|---|
  | ~/mvs10-gate.txt (c3270 trace, final after the window was closed) | 450746 | `da87d93e3eae484c7973c7376f7270017132b5620091afcc449e4f6c266f70c2` |
  | ~/mvs10-gate-driver.jsonl | 2066 | `c704ea3499ed60acdec849c1cc49a6a1ebb004411634e6b750d065745139317f` |
  | ~/mvs10-gate-check.txt (the accepted check) | 1601 | `612627cffe85ae65d45edbd5b772cae2507c6737881bf76905b9abd68ef6e537` |
  | ~/mvs10-gate-check-final.txt (re-check of the final trace: same 10 PASS lines; the informational post-game text also shows the TSO logoff) | - | `1a5e7b9f9b9020686cf1b64d206c4ce2e77205e319ba5e973841e7c940d700d3` |

## 7. Clean shutdown (2026-10-21) and an operational finding
- `f bsppilot,shutnow` stalled after `$P LINE3`: `IEA404A SEVERE WTO BUFFER SHORTAGE - 100% FULL`. `D C` showed all 250
  WTO buffers queued on console 01F (MVS console ID 04, a 3215 with nothing connected, `IEA000A 01F,INT REQ`); JES2 could
  not answer commands. `K Q,L=04` -> `IEA406I WTO BUFFER SHORTAGE RELIEVED`; the pilot finished SHUTNOW (`$HASP099`), then
  `$PJES2` -> `$HASP085`, `Z EOD` -> `IEE334I`, `QUIESCE` -> `HHC00809I disabled wait state 000A0000 00000CCC`;
  Hercules `stopall`, `sysclear`, `quit` -> `HHC01425I Hercules shutdown complete`; no process held the DASD files.
- Lesson (docs/ENVIRONMENT.md): with the manual console boot, purge or attach console 01F before a shutdown.

## 8. Rollback
`HERC01.PACMAN.R20.LOAD(PACMAIN)` (the 2.0 module of record) is untouched; the 2.0 CLIST text is `releases/2.0-MVS-MAX`.
