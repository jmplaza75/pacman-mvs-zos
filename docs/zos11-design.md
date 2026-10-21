# ZOS-11 - REALTIME Right on PF12 (D46; release 2.1-zos) - design / specification
Status: CLOSED / PASS 2026-10-21 (release 2.1-zos, tags zos-11 / 2.1-zos; evidence docs/evidence/zos11-release.md).
Step 1 (design, source, documentation, local tests) done locally on branch zos; step 2 ran as 2A (build RZ21), 2B
(promotion) and 2C (live gate, attempt 3 accepted) on separate authorisations. The MVS line did the same change as MVS-10
(release 2.1-mvs, main, docs/MVS10-PF12.md); main is neither merged nor touched here.

## 1. Scope (exact)
REALTIME right movement from PF11 (AID X'7B' = 123) to PF12 (X'7C' = 124), plus the associated guards, live tools
and documentation. No movement model, core, batch, TURN, screen, oracle, timing, CLIST statement / default / PARM or
other key change. 2.0-zos (tag `2.0-zos`, releases/2.0-ZOS, the RZ build, its evidence) stays frozen.

## 2. Product delta (identical to 2.1-mvs; D46, not a z/OS difference)
| File | 2.0-zos | 2.1-zos |
|---|---|---|
| src/cobol/PACINPT.cob RT-TSC | `IF WS-V = 123` (PF11 -> R) | `IF WS-V = 124` (PF12 -> R) |
| src/cobol/PACINPT.cob header comment | `PF7 U PF8 D PF10 L PF11 R, PF9 PAU` | `PF7 U PF8 D PF10 L PF12 R, PF9 PAU` |
| src/zos/PACMAN.clist help comment | `ARROWS = PF7/8/10/11` | `ARROWS = PF7/8/10/12` |
| tools/c3270_rt.sh (client keymap) | `<Key>RIGHT: PF(11)` | `<Key>RIGHT: PF(12)` (byte-identical to main's 2.1-mvs launcher) |
PF11 falls to the existing IGN path; QUIT stays only `Q` typed + ENTER (RT-ENTER -> CLASSIFY); no PF key quits;
PF7 / PF8 / PF10 / PF9 / PA2 and TURN unchanged. The MVS CLIST copy on this branch (src/clist) is not changed (MVS is
released from main).

## 3. Guards (exact allowance, as Z6 in ZOS-10)
- tests/zos_c2.py: `D46` + `d46_strip(rel, text)` put back exactly the three lines (each 2.1 line exactly once, no 2.0
  line left); the guard REQUIRES them (the tree must be 2.1-zos), every other byte stays pinned to 2.0-mvs-max (+ Z1-Z6);
  z6_strip puts the CLIST D46 line back first when present, so every historical CLIST pin (zos-6 / 7 / 8 / 9) holds.
- tools/zowe/r3_gate.py check 4: the PACINPT D46 lines join the allowed source-delta lines (Z1, Z4).
- Phase pins adapted only through d46_strip: tests/test_zos10.py (src since zos-9; the PACZ10CL deck of record inlines
  the CLIST copy: compared with the D46 line put back, required exactly once), tests/test_zos9.py (src = zos-8),
  tests/test_zos_tools.py sections 24 (zos-6), 25 (zos-7), 26-28 (PACINPT = its Z1 text); tests/test_rt.py: the
  keymap assertion (identical to main's).

## 4. Live gate tooling (successor; the frozen ZOS-6 tools are not edited)
tools/zowe/zos11_live.py: plan Z11, driver, checker.
- Plan: `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) SOUND(NO)'` (installed CLIST, no PLAY / PRESENT:
  REALTIME + COALESCED by default; CLASSIC: no high-score path); PF8, PF10, PF11, PF12, PF7, PF9 / PF9, PA2, the
  PF1-PF24 sweep (PF1-PF6, PF11, PF13-PF24), PF12, 40 s idle (>= 200 quanta: the principal timing segment), TYPEQ
  (`Q` typed, no AID) + 3 s hold, ENTER, `***`, closure ENTER, ISPF Command Shell.
- Driver: zos6_drive's Driver (unchanged) with the Z11 steps. Before the final ENTER it reads the field (cursor - 1):
  Q still there -> gameplay `Q` (variant A); erased by a host write -> gameplay `ENTER()` (a blank ENTER = redraw), then
  a fresh `Q` + ENTER (variant B). The driver log records which.
- Checker: zos6_live_check.check() unchanged, with the 2.1 key map supplied in-process (PF12 = R), the ignored keys
  removed from the game input (each proven on the trace: AID-only, the game wrote on), case name Z11 (R1-only death
  rules off; every functional and timing rule on). Gate: model PASS; controls FAIL (2.0 map; PF12 ignored; PF11 as
  Right); PF12 / PF11 / sweep AID-only; the game wrote on after every PF AID; TYPEQ -> ENTER no inbound and >= 5 writes;
  QUIT end lines. BLOCKED timing = environment, not a product verdict (as ZOS-6 / ZOS-10).
- tests/test_zos11.py: the delta, the frozen tools, the plan, and the gate on synthetic z/OS traces (zos6_fixture's
  COALESCED host, used in-process): 2.1 passes in variants A and B; 9 faults fail by their rule. Timing robustness
  (outside the test): early key waits x 0.7 and x 1.3 -> the gate and all three controls still discriminate.

## 5. Host staging (step 2, not authorised yet) - proposal
As ZOS-10, under a NEW empty prefix (not RZ): allocation, upload of the release set from the ZOS-11 commit, clean build,
object comparison against the 2.0-zos RZ objects (expected: PACINPT only - the one literal 123 -> 124 - plus the frozen
timestamps / D_MCODE representation rule), candidate C1 / C2, CLIST PARM matrix, rollback copy, promotion, installed
P1, live gate (zos11_live.py), final read-only checks (HISCORE `0000980 PACHS001 001` unchanged). Then releases/2.1-ZOS,
tags zos-11 / 2.1-zos.
