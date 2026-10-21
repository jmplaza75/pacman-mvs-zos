# MVS-10 - REALTIME Right on PF12 (D46; release 2.1-mvs) - design / specification
Status: CLOSED / PASS 2026-10-21 (release 2.1-mvs, tags mvs-10 / 2.1-mvs; evidence docs/evidence/mvs10-release.md). Design,
source and local tests 2026-10-20 (commit 815c98b); host gate JOBs 319-333 and the live gate on separate authorisations. The z/OS line follows as
ZOS-11 (release 2.1-zos) after this one, with the same decision D46.

## 1. Scope (exact)
The REALTIME right movement moves from PF11 (AID X'7B' = 123) to PF12 (AID X'7C' = 124), with the associated tools,
tests and documentation. Nothing else: no movement model, core (GAME / MAP / AI), batch, TURN, screen, oracle, timing
or other key change. The frozen 2.0-MVS-MAX artifacts (tag `2.0-mvs-max`, `releases/2.0-MVS-MAX/`, its evidence) and
the historical live tools stay unchanged and reproducible.

## 2. Current behaviour (2.0-mvs-max, read from the source)
- `src/cobol/PACINPT.cob` RT-TSC (REALTIME terminal input, the only AID decoder): an AID without ENTER sets
  `REQ-KIND = 'IGN'`, then `IF WS-V = n` maps 247 PF7 -> U, 248 PF8 -> D, 122 PF10 -> L, **123 PF11 -> R**, 249 PF9 ->
  P (pause), 110 PA2 -> RDR. Every other AID stays IGN (PACMAIN RT-EVENT drops it: no input, no frame change).
- QUIT: only the character `Q` reaches RT-CHAR -> QUI, and in REALTIME only through RT-ENTER (REQ-INKEY = 'E' = the
  ENTER AID with the typed field; a blank field = RDR). No PF / PA key maps to QUIT. A 3270 terminal sends nothing until
  an AID key is pressed, so a typed `Q` without ENTER never reaches the host.
- TURN (TSC READ, TSO line mode) and batch / TSD cards: commands are characters (U D L R Q P * . +), never AIDs - not
  affected by any AID mapping.
- Client: `tools/c3270_rt.sh` maps the arrow keys UP / DOWN / LEFT / RIGHT to PF(7) / PF(8) / PF(10) / **PF(11)**.

## 3. Change (D46)
| Item | 2.0-mvs-max | 2.1-mvs |
|---|---|---|
| PACINPT RT-TSC right | `IF WS-V = 123` (PF11) | `IF WS-V = 124` (PF12) |
| PACINPT header comment | `PF7 U PF8 D PF10 L PF11 R, PF9 PAU` | `PF7 U PF8 D PF10 L PF12 R, PF9 PAU` |
| PF11 (X'7B') | Right | IGN (the existing ignored path) |
| PF12 (X'7C') | IGN | Right, at once as an AID (no ENTER) |
| QUIT | `Q` + ENTER only | unchanged: `Q` + ENTER only; no PF key quits |
| PF7 / PF8 / PF10 / PF9 / PA2, all other PF keys | U / D / L / pause / redraw; others ignored | unchanged |
| CLIST help comment | `ARROWS = PF7/8/10/11` | `ARROWS = PF7/8/10/12` (comment only; no statement, default or PARM change) |
| c3270 keymap (`tools/c3270_rt.sh`) | `<Key>RIGHT: PF(11)` | `<Key>RIGHT: PF(12)` (the Right arrow keeps moving right) |
| `tools/rt_play.py` message | `arrows = PF7/8/10/11` | `arrows = PF7/8/10/12` (message only) |
Production delta: one statement and one comment line in PACINPT, one comment line in the CLIST. PACINPT is the input
adapter (outside the frozen core, D18); the core baseline is untouched. COBOL dialect unchanged (no new construct).

## 4. Frozen artifacts and successors
- Unchanged (history, reproducible): `releases/2.0-MVS-MAX/`, tag `2.0-mvs-max`, all docs/evidence, the live tools of
  earlier phases (`tools/gp2_live.py`, `tools/c3270_gp1_trace.py`, `tools/c3270_gp2_trace.py`, `tools/c3270_s2_trace.py`,
  `tools/c3270_rt_game.py`, `tools/c3270_rt_trace.py`, `tools/e14_inject.py`, `tools/rt_e14_report.py`) - they keep
  describing the 2.0 key mapping that their evidence used.
- Successors (MVS-10 only, import the frozen helpers, never edit them):
  - `tools/mvs10_live.py` - live driver for the MVS-10 gate scenario (keys through the c3270 script port).
  - `tools/mvs10_trace.py` - live checker: replays the AIDs that reached the host through the independent models with
    the **2.1 AID map** (PF12 = R, PF11 and every other unmapped AID = no input, blank ENTER = redraw as PACINPT), and
    also with the **2.0 map** as a discrimination control.
  - `tests/mvs10live/make_live10.py` + `LIVE10.txt` - the deterministic scenario, built and checked on the models.
- Test pins on earlier tags (test_rt, test_s1, test_gp1, test_gp2, test_hs, test_rp, test_s2, test_g8): adapted only
  through `tests/mvs10_delta.py` (`m10_strip`: restores exactly the three MVS-10 lines, required exactly once each), so
  every other byte stays pinned; `test_rt.py`'s keymap assertion follows the approved keymap change.

## 5. Local verification (tests/test_mvs10.py)
1. PACINPT RT-TSC decode table parsed from the source = the independent 2.1 table {247 U, 248 D, 122 L, 124 R, 249 P,
   110 RDR}; 123 absent (falls to the IGN set before the table); the diff vs 2.0-mvs-max is exactly the statement and the
   comment.
2. No AID maps to Q / QUI: RT-TSC moves only U / D / L / R / P; QUI only from the character `Q` (RT-CHAR), reached in
   REALTIME only from RT-ENTER (ENTER AID). PF11 / PF12 -> not QUIT; `Q` without an AID -> no inbound record -> no
   event (POLL returns REQ-INKEY N).
3. Other mappings unchanged: the table equals 2.0's except 123 -> 124; TURN path (TSC READ / CLASSIFY) and the card
   path (RT-CARD-READ / RT-SCAN) byte-identical to 2.0-mvs-max.
4. Batch / oracle: core baseline, PACMAIN, PACGAME, PACRT and every other module unchanged; the existing local
   regressions (models, TSD streams) pass unchanged.
5. Keymap: `<Key>RIGHT: PF(12)`, no `PF(11)`, UP / DOWN / LEFT / p unchanged.
6. The live checker on synthetic traces: PF12 replayed as R matches; PF11 replayed as no input matches; under the 2.0
   map the same trace diverges (discrimination); `Q` typed without an AID adds no inbound record; `Q` + ENTER = QUIT;
   PF3 / PF1 / PF13-24 ignored; injected faults (PF11 moving right, PF12 ignored, a PF key ending the game) FAIL.
7. Scenario discrimination on the models: LIVE10 under the 2.1 map and under the 2.0 map gives different write streams
   at the PF11 and at the PF12 quanta.

## 6. Live gate (later, separately authorised; TK4- / Hercules, c3270 via tools/c3270_rt.sh)
Rebuild PACINPT + link (REL21 build of record into fresh libraries, as G8 / D43), run-only regressions on that module
(the 1.0 oracle and the 2.0 batch / TSD streams - unchanged), install by copy with byte identity, CLIST install, then
one live run of LIVE10 with `RULES(CLASSIC) AI(0) GHOSTS(1) SOUND(NO)` (CLASSIC: no high-score path):
start; PF7 / PF8 / PF10 moves; PF12 (Right) at once without ENTER; PF11 while moving left (2.0 would reverse); PF9
pause / resume; PA2; PF1, PF3, PF11, PF12, PF13-PF24 as ignored or move AIDs, the game continues after each; `Q` typed
without ENTER, a 3 s hold with the writes continuing and no inbound record; then ENTER -> QUIT (end banner, READY).
Acceptance (all on the live trace, by tools/mvs10_trace.py): 1 PF12 moves right; 2 PF12 needs no ENTER; 3 PF11 does not
move right; 4 PF11 never quits; 5 PF12 never quits; 6 `Q` without ENTER does not quit; 7 `Q` + ENTER quits normally;
8 PF7 / PF8 / PF10 / PF9 / PA2 unchanged and other PF keys ignored; every live write = the model with the 2.1 map; the
2.0-map replay diverges. 9 (independence) = the same gate on z/OS in ZOS-11.

## 7. Release (after the live gate)
`releases/2.1-MVS/` (notes with the control change, manifest, defaults, SHA256SUMS, decks); README, CURRENT_PHASE,
DECISIONS; annotated tag `2.1-mvs` (+ `mvs-10`) on the closure commit; `2.0-mvs-max` untouched.
