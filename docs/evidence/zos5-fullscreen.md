# ZOS-5 full-screen / graphics - live acceptance evidence (2026-10-16)

Installed baseline under test (tag zos-4, unchanged; read-only precheck PASS, docs/evidence/zos5-precheck.txt):
Z00000.PACMAN.LOAD(PACMAIN), CLIST(PACMAN) (Z3 + Z2), CEEOPTS. No build, install, job or z/OS write in ZOS-5.
Procedure: docs/zos5-live-session.md (ISPF option 6, c3270 `-model 2 -oversize auto`, 120 x 30 window, trace started in
the ISPF Command Shell). Checker: tools/zowe/zos5_live_check.py (section 19 of tests/test_zos_tools.py).

## Result: PASS, composite acceptance
Status: ZOS-5 CLOSED / PASS. Next phase: ZOS-6 REALTIME. MVS (tag 2.0-mvs-max) stays frozen.
| Game | Frozen 2.0 block | Source trace | Result |
|---|---|---|---|
| A - MOVES, COLOR AUTO (query, 120 x 27 wide) | oracle 310 TSD45 | T5 | PASS |
| B - TSORDR, second query in the same session, CLEAR + PA2 | oracle 310 TSD48 | T2 | PASS |
| C - TSORDR, forced COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC), 80 x 24 | oracle 310 TSD28 | T2 | PASS |
Final run: `zos5_live_check.py --a T5=<raw-trace-dir>/<T5> --bc T2=<raw-trace-dir>/<T2> --reply-out
tests/qreply_zos_dyn.hex`, exit 0, output in docs/evidence/zos5-live-check.txt (the second run of the same command on
the same T2 / T5, made only to write the reply file in the qreply_*.hex convention; the first run had the identical
result and wrote lower-case hex). The first game of T2 is not validated and is not acceptance evidence.

| Game | Profile (colour, highlight, GE) | Canvas | Writes = model | Ticks | Commands | TSO CLEAR writes | End pause |
|---|---|---|---|---|---|---|---|
| A (T5) | (1, 1, 1) from the reply | 120 x 27 (wide) | 103 | 87 | 15 | 0 | 2821 ms (2.821 s) |
| B (T2) | (1, 1, 1) from the reply | 120 x 27 (wide) | 56 | 51 | 4 | 1 | 2973 ms |
| C (T2) | (1, 1, 1) forced, no query | 80 x 24 | 44 | 39 | 4 | 0 | 2752 ms |
Every game: the frozen cards exactly (A `R R U L L L D D R X r R R D Q`, B `R` CLEAR PA2 `D` `Q`, C `R` empty ENTER `D`
`Q`), every PACMAN write byte for byte = the model (= the frozen block when no tick is seen), the frozen end lines
(A `QUIT` / `TURNS 013` / `SCORE 0080` / `LIVES 3`; B and C `QUIT` / `TURNS 002` / `SCORE 0010` / `LIVES 3`), ISPF's
`***` after them, ENTER, and the `ISPF Command Shell` panel. Animation ticks ran before the first input in all three
games: the D28 hold of TK4- did not occur on z/OS.

## Query Reply and capabilities on this z/OS path
- The reply reaches TGET through the z/OS TN3270E server: 180 bytes, the same bytes as tests/qreply_dyn.hex (the TK4-
  IBM-DYNAMIC reply), in A (T5) and B (T2). Recorded as post-run evidence in tests/qreply_zos_dyn.hex, written by the
  final run from T5's game A in the tests/qreply_*.hex convention (upper-case hex, one line, final newline): the file is
  byte-identical to tests/qreply_dyn.hex (`cmp`), SHA-256 371d5a7ec83edb469a4024dd91ff6add4fed156103e64dc76f9bf693154d8745
  for both. No test or oracle reads it as an input.
- Profile from the reply (tests/qry_cases rules): colour 1, highlight 1, GE 1; alternate size 120 x 27.

| Capability (z/OS, TN3270E, c3270 -model 2 -oversize auto) | Status | Evidence |
|---|---|---|
| Read Partition Query reaches the program, valid reply | CONFIRMED | A (T5), B (T2) |
| Extended colour (QCode X'86') | CONFIRMED | profile, writes = model |
| Highlighting (QCode X'87') | CONFIRMED | profile, writes = model |
| GE + CP310 glyphs (GRAPHIC) | CONFIRMED | profile, writes = model |
| 4x2 scaled renderer, partial redraw, idle ticks | CONFIRMED | A, B, C |
| Alternate size 120 x 27 (wide layout, Erase/Write Alternate) | CONFIRMED | A, B |
| 80 x 24 (Erase/Write, forced COLOR(YES), no query) | CONFIRMED | C |
| PA2 full redraw after CLEAR (Erase/Write Alternate restores 120 x 27) | CONFIRMED | B |
| FSON / FSOF, end pause, return to the shell | CONFIRMED | A, B, C |

## Transport facts (z/OS TN3270E)
- Negotiated TN3270E functions (FUNCTIONS IS, from the trace's telnet-state replay), T2 and T5: 00 BIND-IMAGE,
  02 RESPONSES, 04 SYSREQ, 05 CONTENTION-RESOLUTION. Device type IBM-DYNAMIC.
- Every host record asks for a response (RESPONSE-FLAG 02); c3270 answers each with a positive RESPONSE
  (02 00 00 SEQ 00), in order. Host SEQ-NUMBER +1 per record, BIDs included.
- CONTENTION-RESOLUTION: host 3270-DATA REQUEST-FLAG 00 / 01 (SDI) / 03 (SDI + KRI) observed (T2: 46 / 11 / 210);
  BID records (DATA-TYPE 09, REQUEST-FLAG 00, RESPONSE-FLAG 02, no payload; 195 in T2) between writes. No SIGNAL BID.
  The checker accepts exactly this negotiated, observed subset (RFC 2355 core ignores REQUEST-FLAG outside REQUEST;
  CONTENTION-RESOLUTION redefines it as SDI / KRI / SIGNAL bits); unknown DATA-TYPEs, other flag bits, SIGNAL BID and
  unanswered or negative responses fail.
- z/OS CLEAR handling: after the CLEAR key in game B, TSO / VTAM itself sends one record
  `7E C1 11 F2 E7 1D 40 11 40 40 13` (Erase/Write Alternate, WCC C1, SBA(27,120), SF, SBA(1,1), IC): an empty
  alternate-size screen. It is not PACMAN output (PACMAN writes WCC C3 / C2 only; CLEAR is not delivered to the
  program, as on TK4-, where no such write was sent). The checker accepts exactly this record, at most once, only in
  B between CLEAR and PA2; it is no model write. The following PA2 redraw (Erase/Write Alternate + the full screen,
  1736 bytes) equals the model.
- ISPF option 6 adds its own line-mode `***` handshake before each game (after the EXEC, released by an ENTER
  before PACMAN's first write) and after each game (after the end lines). Both are outside the PACMAN stream.

## Live attempts (raw traces kept outside git, read-only, SHA-256 recorded)
| Trace | SHA-256 | Classification |
|---|---|---|
| T1 | 0aaeacd676080dcf201571c524a71738fc57184079609c4489c5c7d4513ca30f | invalid capture: the trace was attached to a different c3270 / logon screen; not a PACMAN functional failure |
| T2 | 64aa4bc7fdb0fc9b45f51e939ca659d8676c9927424dea4123b2413708cc0b5f | ACCEPTED for B / TSD48 and C / TSD28 (c3270 script port 4002). Its A is an operator-input mismatch (14 commands, the third L not sent: `R R U L L D D R X r R R D Q`); for those actual cards all 143 writes equal the model (diagnostic only, not acceptance) |
| T3 | 5d07e5239f944b11d9963bbf32bcfef6f7d04cb2a8897037c01f2f150b3cffc0 | rejected A retry: again only two L sent (position 6 `D`) |
| T4 | 0c031617e88c08d666181cb272b525141c0bc36a1fb5d9ba76a0bc29d8660efc | correct 15-command A (inputs sent through x3270if); all game writes and the end lines passed, but the trace stopped at `***` before the ENTER and the shell panel: incomplete closure boundary, superseded by T5 |
| T5 | 7d26ff6e5d4a3a216bdaed6e122a8b840251b8d45d4fea6a6c6c115c1b98e75c | ACCEPTED for A / TSD45 (the live c3270 reused, script port 4004), traced through `***`, ENTER and the ISPF Command Shell |
T4-close: preserved auxiliary capture, not analysed, not acceptance evidence (outside git; SHA-256
fc11b83473521665183364402a9ccd7f25bf1e41fc83665f303c253cbfc41754). The failed `=X` attempt before the procedure
correction had no trace and ran no game (not a live attempt).

## Checker changes made during the evaluation (local, before acceptance; no frozen model or oracle changed)
1. ISPF option-6 boundary instead of READY (`***` only after the end lines).
2. RFC 2355 REQUEST-FLAG handling and the negotiated CONTENTION-RESOLUTION subset (SDI / KRI, normal BID).
3. The exact, B-only, CLEAR -> PA2 TSO / VTAM CLEAR record.
4. Composite mode (`--a` / `--bc`): A from a one-game trace, B / C from the A / B / C session with
   CONTENTION-RESOLUTION; the B / C source's first game never counts as A.
Each with focused negatives in test section 19 (frozen TSD45 / TSD48 / TSD28 and MOVES unchanged).

## Not proved here (carried forward)
REALTIME / PF keys / timing (ZOS-6); ARCADE (ZOS-7); sound / alarm, live high score, ESTAE / PACFSIO C3 (E2) (ZOS-8);
other z/OS canvases (model 3 / 4 / 5) - not used on this system.
