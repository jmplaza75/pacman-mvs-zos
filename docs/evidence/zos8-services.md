# ZOS-8 Services - high score, recovery, sound and production persistence evidence (2026-10-20)

Status: **ZOS-8 PASS** (COMPLETE). Next phase: ZOS-9 Final equivalence (not started). MVS (2.0-mvs-max) frozen.
Design and decisions U1-U12 (and the live refinements of sections 19-20): docs/zos8-design.md.

**NO PRODUCTION SOURCE CHANGE WAS REQUIRED BY ZOS-8.** No PACMAN COBOL source or copybook, no assembler source
(PACFSIO and PACHSIO unchanged), and the installed production CLIST(PACMAN) unchanged [erratum, see the end]. No
build of LOAD(PACMAIN), no promotion. The accepted ZOS-8 changes are tooling, tests, JCL decks / test CLISTs / probe
material, documentation, and one production data state: `Z00000.PACMAN.DATA(HISCORE)` (Stage F, below).

ZOS-8 validated on z/OS: the high-score services (PACHSIO through the installed program), persistence on test data,
UNAVAILABLE / NOT SAVED handling, live high-score behaviour, abend recovery, PACFSIO terminal recovery (C3), live sound
(3270 ALARM, audible at the client) and the first real production high-score write.

| Stage | Scope | Result |
|---|---|---|
| A | Local tooling, plans, models, fixtures | Done (test section 25) |
| B | B1 test-PDS first write / tie / update / lower (batch); B2 PACRPE build + batch ESTAE run | PASS |
| C | Live high score on test data: HL1 HL2 HL3 HL4 HL6 HL8, HL7 read-only | PASS (HL8 after the approved offline revalidation) |
| D | Recovery E1 / E2 / E3 + clean follow-up game | PASS (E1 as E1-T2); C3 CLOSED, no PACFSIO change |
| E | Live sound S1 NORMAL / S2 FAST / S3 CLASSIC WIN | PASS (S1 by the corrected offline recheck of its live trace) |
| F | Production first write of DATA(HISCORE) | PASS |

## Stage A - local tooling (ZOS-8 only; ZOS-5 / 6 / 7 acceptance tools imported unchanged, pinned to zos-7)
- tools/zowe/zos8_scen.py: every case, its cards (tests/zos8live/*.txt = the commands each model game consumes), EXEC
  operands, the dataset it may touch and the high-score state chain (ref_hs); Stage F = SF on HL2's LIVEB cards.
- tools/zowe/zos8_batch.py: decks of record jcl/zos/PACZ8HB.jcl (B1) / PACZ8RPE.jcl (B2), audits, spool checkers,
  the test CLISTs PACZ8HT / PACZ8HU / PACZ8HF (= the installed CLIST except their two DATA lines), the read-only
  dataset state query.
- tools/zowe/zos8_drive.py: the live input driver (x3270if script port; never logs on, never starts a trace, never
  retries): TURN / REALTIME plans, the Stage D recovery plan (initial ISPF hold, exact test-screen recognition incl.
  120-column wrap, recovery holds, paged LISTALC, conditional FREE F(CEEOPTS)), --resume-after.
- tools/zowe/zos8_live_check.py: the live postcheck (TURN model + ref_hs lines; REALTIME through the frozen ZOS-7
  check with the bell-rung sound model; recovery; lossless trace joins; Stage F production-state check).
- tests/zos8_fixture.py (synthetic traces / spools), tests/test_zos_tools.py section 25 (positives and fail-closed
  negatives for every rule above), src/probe/zos/RPESTAE.clist (the z/OS ESTAE test CLIST, uploaded as CLIST(RPESTAE)).
- tools/progress.py + tests/test_progress.py: reporting-only progress for long runs (never changes output, exit
  status or gates).

## Stage B - batch
- **B1 PACZ8HB JOB02290 PASS** (PGM=PACZ6D, BAT ARCADE LEVEL 1, DD PACHS = HS8.T1(HISCORE)). HS8.T1 = a new test PDS
  with the production DATA geometry (PDS FB 80/80, SPACE=(TRK,(1,1,5))). H1 GPTSO 370 with the member missing:
  NEW HIGH SCORE, the member created (REPL + STOW of the first member); H2 tie: no write; H3 GPREVB 720: NEW HIGH SCORE,
  updated in place; H4 lower: unchanged. Final HS8.T1 = exactly HISCORE, one record `0000720 PACHS001 001`, 1 extent.
  This established the missing-member -> REPL -> STOW first-write path on DATA-equivalent geometry (the `used 100`
  question of ZOS-7: the first member fits on the primary track) before any production write.
- **B2 PACZ8RPE JOB02299 PASS**: PACRPE compiled / linked AMODE 24 RMODE 24 into LOAD (test member only, never
  promoted); batch E1 / E2 end with S0C7 and LE `CEE3207S` (system completion code 0C7); E2 reads HS8.T1 only.
- Step 4: test CLISTs PACZ8HT / PACZ8HU / PACZ8HF and RPESTAE uploaded, byte-verified; CLIST(PACMAN) unchanged.

## Stage C - live high score on test data (TURN, AI(0), ANIM(NO), SOUND(NO), PRESENT(COALESCED))
| Case | CLIST / store | Game | High-score lines (live = model) | Store after | Result |
|---|---|---|---|---|---|
| HL1 | PACZ8HT / HS8.T1 = 720 | LIVEB LEVEL(5), 2180 | `HIGH SCORE 0002180 LEVEL 005`, `START LEVEL 05: HIGH SCORE NOT RECORDED` | 720 | PASS |
| HL2 | PACZ8HT / 720 | LIVEB, 980 | `HIGH SCORE 0000980 LEVEL 001`, `NEW HIGH SCORE` (update) | 980 | PASS |
| HL3 | PACZ8HT / 980 | LIVEB, 980 (tie) | `HIGH SCORE 0000980 LEVEL 001` (no write) | 980 | PASS |
| HL4 | PACZ8HT / 980 | GPAI0 GHOSTS(3), 1310 | `HIGH SCORE 0001310 LEVEL 001`, `NEW HIGH SCORE` | 1310 | PASS |
| HL6 | PACZ8HU / no dataset (DUMMY) | DIE1, 510 | `HIGH SCORE UNAVAILABLE` | - | PASS |
| HL8 | PACZ8HF / HSFULL.T1 (full directory), HISCORE absent | DIE1, 510 | `HIGH SCORE 0000510 LEVEL 001`, `HIGH SCORE NOT SAVED` | absent, HSFULL.T1 unchanged | PASS (offline revalidation) |
| HL7 | read-only member check of HS8.T1 | - | one record `0001310 PACHS001 001` | - | PASS |
CLASSIC is silent / non-recording: CLASSIC never allocates PACHS (the CLIST block runs for ARCADE only; PACMAIN reads
the high score only for ARCADE), and every CLASSIC game (GD, S8C) ended without a high-score line.
**HL8 history (product vs checker):** the live HL8 checker run was a FUNCTIONAL FAIL (game write 29 differed): the
TURN reference model showed the end-screen `NEW HIGH SCORE` label whenever the score beat the record, while the
program (PACSCR, D38) shows it only when the save succeeded. The checker model was corrected (approved; ZOS-8 checker
only, ref_rp unchanged; the label follows the persistence outcome) and the same preserved trace was revalidated
offline: PASS. No IEC217I message and no TSO hold appeared live. The original FAIL output is preserved
(stageC/zos8-HL8-check.txt); the program behaviour was correct.

## Stage D - recovery (C3)
| Case | Path | Recovery | Follow-up GD | Result |
|---|---|---|---|---|
| E1 (E1-T2) | full screen, forced 0C7 | 1 `***`, shell back < 90 s; CEEOPTS left by the CLIST, freed | CLASSIC DIE1 exact, QUIT | PASS |
| E2 | full screen, PACHSIO READ of HS8.T1, forced 0C7 | same; PACHS left allocated (freed once before E3) | exact, QUIT | PASS |
| E3 | line mode restored first (`RPE E3 LINE MODE RESTORED, FORCING 0C7`), forced 0C7 | same | exact, QUIT | PASS |
Every accepted case: the intentional failure occurred; the session returned to a usable TSO / ISPF state (ISPF
Command Shell) with no reconnect and no manual terminal reset; LISTALC STATUS answered; the clean follow-up game ran
normally; the datasets were unchanged (read-only checks before / after). **C3 CLOSED WITH NO PACFSIO SOURCE CHANGE.**
Tooling history (no product defect): the first E1 attempt stopped on driver issues (the ISPF initial `***` hold, the
test screen's own `ABEND` word) and stayed INCOMPLETE (preserved: stageD/zos8-E1.trace 42578750..., -resume
4793efb3...); a leftover CEEOPTS was freed after a traced LISTALC (stageD-E1-recovery, stageD-E1-free); LISTALC paging
(initial hold + 13 pages) was modelled; E1-T2 stopped once on the 120-column wrap of the test screen and was continued
from its displayed test screen on a second trace, joined only at that named cut (`--cuts screen`).
Observed messages (recorded, not gated): E1 / E2: LE `CEE3207S The system detected a data exception (System
Completion Code=0C7).`, TSO `Command abend - Abend 0C4 hex occurred processing command 'CALL    '.`; E3: LE the same,
TSO `Abend 0C7 hex`. E3 restored line mode before forcing the 0C7; this is consistent with the terminal / full-screen
state being involved, but the reason for the TSO / LE difference is not established and it is not an acceptance gate.

## Stage E - live sound (SOUND(YES), PRESENT(COALESCED))
| Case | Game | Bells expected = observed (host / protocol) | Audible at c3270 | Result |
|---|---|---|---|---|
| S1 S8A | ZOS-7 L2, NORMAL, LEVEL(2) | START 1, DEATH 2, DEATH 2, GAME OVER 3 | YES | original check FUNCTIONAL FAIL (tooling false negative); corrected offline recheck of the same trace PASS |
| S2 S8B | ZOS-7 L3, FAST, LEVEL(2) | START 1, DEATH 2, DEATH 2, GAME OVER 3 | YES | PASS |
| S3 S8C | CLASSIC TURN WIN0 | START 1, WIN 4 (end screen + 3 bell-only writes) | YES | PASS |
The ALARM bit is on exactly the modelled writes (8 / 8 / 5); no sound-induced extra writes; gameplay = model; NORMAL /
FAST timing and input gates pass (final death 6 / 7 writes, D1); DATA read only.
**S1 classification:** with SOUND(YES) the screen before the first AID rings the START bell, so its WCC is C7 = C3 plus
only the alarm bit. The frozen ZOS-6 rule classifies TSO's exact 2-byte keyboard-restore record `F1 C3` as a control
only after a WCC C3 screen, so it was counted as a game write. ZOS-8 tooling only now accepts exactly C3 or C7 in that
one context (zos8_live_check.sound_c3_controls); the record stays exactly `F1 C3` and every other restriction holds.
**The frozen ZOS-5 / 6 / 7 tooling was not changed.** The original S1 output is retained; no live rerun.

## Stage F - production first write (the only write to DATA in ZOS-8)
Frozen case (option A, user decision): LIVEB / HL2 cards, ARCADE, LEVEL 1, TURN, AI(0), ANIM(NO), SOUND(NO),
PRESENT(COALESCED), through the installed CLIST:
`EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) PLAY(TURN) ANIM(NO) SOUND(NO) PRESENT(COALESCED)'`.
One run: 77 LIVEB moves, 78 writes, every write = model, score 980, level 1, normal closure, no IEC / system message.
Expected = observed: `HIGH SCORE 0000980 LEVEL 001`, `NEW HIGH SCORE`.
| | DATA members | DATA(HISCORE) | Attributes |
|---|---|---|---|
| Before | none | absent | PDS PO FB 80/80, 1 extent, 1 track, used 100, ZXPL01 |
| After | HISCORE only | exactly one FB 80 record `0000980 PACHS001 001` (80 bytes = the expected record) | unchanged |
Observable proof chain: member absent before -> the game read no stored score (the HUD model from "empty" matched every
write) -> `NEW HIGH SCORE` (shown only when the save succeeded) -> the member exists afterwards -> exactly one record
with the exact content. This is consistent with PACHSIO's missing-member REPL / STOW first-write path (proven in B1 on
the same geometry); the trace does not show PACHSIO's internal operations directly.

## Final production state (carried into ZOS-9 / ZOS-10)
`Z00000.PACMAN.DATA(HISCORE)` = one record `0000980 PACHS001 001` is **legitimate production state**. It must NOT be
deleted to recreate the historical empty-DATA precondition; later phases start from this record. The test datasets
HS8.T1 (`0001310 PACHS001 001`), HSFULL.T1 and the test members (LOAD(PACRPE), CLIST PACZ8HT / PACZ8HU / PACZ8HF /
RPESTAE) remain as test material. `Z00000.ZHEIST.*` was never touched; nothing was deleted, purged or reallocated.

## Production-source conclusion
- no PACMAN production COBOL source or copybook changed in ZOS-8;
- no production assembler source changed; PACFSIO and PACHSIO unchanged;
- the installed production CLIST(PACMAN) unchanged (byte-verified before / after every stage);
- accepted ZOS-8 changes: tooling, tests, JCL decks, test CLISTs / probe material, documentation, and the production
  DATA(HISCORE) record above.

## Evidence locations (raw traces / logs / spools outside git, read-only, each with its .sha256)
| Item | Location | Accepted digests (SHA-256, first 16) |
|---|---|---|
| B1 / B2 spools + checks | ~/zos8-live/B1-PACZ8HB-JOB02290, B2-PACZ8RPE-JOB02299 (SHA256SUMS) | - |
| Stage C HL1-HL8 | ~/zos8-live/stageC; HL8 revalidation stageC-HL8-OFFLINE-REVALIDATION; HL7 stageC-HL7 | HL2 trace 3397e50d48953c4f, HL8 trace 9dc33fb7cd170a71 |
| Stage D E1 (first attempt, INCOMPLETE) | ~/zos8-live/stageD, stageD-E1-recovery, stageD-E1-free | 4257875071769f95, 4793efb352137a9d |
| Stage D E1-T2 | ~/zos8-live/stageD-E1-T2 | traces 5a342439ceb82e3c + 2994e575d175712f, joined check 8aa3de409d9147a1 |
| Stage D E2 / E3 | ~/zos8-live/stageD-E2, stageD-E3-prep, stageD-E3 | E2 abce17e83e3dfca6, E3 29adba867896662c |
| Stage E S1 / S2 / S3 | ~/zos8-live/stageE-S1-S8A, stageE-S2-S8B, stageE-S3-S8C | S1 trace 2812db30222e32bb (original check ea43386beaa521d4, corrected 361e5eabf9cb57c0), S2 699b3cfde85ad292, S3 464ec0bb7e36cf04 |
| Stage F | ~/zos8-live/stageF | trace cda7b3a93bae0c09, check 83042a084733f11c, HISCORE bytes bbd979a4bb574093 |

## Post-closure documentation erratum (ZOS-9, 2026-10-20)
Identified in docs/zos9-design.md section 6; recorded in docs/evidence/zos9-equivalence.md. The status paragraph
originally said the installed production CLIST(PACMAN) "changed". The evidenced fact is that it was **UNCHANGED**
(byte-verified before / after every stage; production-source conclusion above). Wording corrected only; no ZOS-8
result, verdict or tag changed.
