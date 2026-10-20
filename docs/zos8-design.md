# ZOS-8 Services - design (APPROVED 2026-10-20, U1-U12; Stage A implemented locally, see sections 18-19)
Status: discovery / design only. No source, CLIST, JCL, dataset or z/OS change; nothing built, submitted, uploaded or
committed. Handoff: branch zos, tree clean, HEAD = tag zos-7 (75b3fd5, annotated), no remote / upstream.
Inputs read: CLAUDE.md, docs/CURRENT_PHASE.md, DECISIONS.md (D38, D39, D40, D41, D44), ZOS-DIFFS.md, ARCHITECTURE.md,
ZOS-MIGRATION-PLAN.md (sec. 4, 5, 6 ZOS-3 / ZOS-8, 9, 10, 11), HS-HISCORE.md, zos6-production-design.md, zos7-design.md,
evidence zos3-platform-layer.md / zos3-coverage-summary.md / zos6-realtime.md / zos7-arcade.md / rp-estae-* /
s2-live-checklist.md, requirements v4 sec. 23, 24, 27, the sources src/asm/PACFSIO.asm, PACHSIO.asm,
src/cobol/PACPLAT.cob, PACMAIN.cob, PACDISP.cob, src/zos/PACMAN.clist, src/probe/PACRPE.cob, RPESTAE.clist, and the
LE options report of PACZ4LE JOB03693 (local spool, git-ignored).

Tags used below: **[O]** = observed / oracle evidence (job, live trace, MVS evidence); **[S]** = read from the source;
**[I]** = inferred (reasoning, not observed). Nothing marked [I] is an acceptance fact.

## 1. Exact scope
ZOS-8 must prove on z/OS what the migration plan (sec. 6 ZOS-8, D44) assigns to it and nothing else:
1. **High-score persistence live**: the D38 contract through the real TSO path (CLIST `ALLOC ... SHR` of a PDS member,
   PACMAIN in TSO foreground, full-screen active while PACHSIO writes): create, read back, tie, update, practice
   start, CLASSIC silent, UNAVAILABLE, NOT SAVED, and the first real write of `Z00000.PACMAN.DATA(HISCORE)` (if
   approved, U1).
2. **Recovery (ESTAE) live**: the RP.0 cases E1 / E2 / E3 (D39) on z/OS under Language Environment: an abend in
   full-screen mode returns the terminal to line mode and the next game starts clean. This also discharges the open
   **C3** item (PACFSIO ASMA303W, "dynamic check in ZOS-8 E2").
3. **Sound / alarm live**: S1 / S2 (D41) bells reaching the terminal on the real z/OS path, under the ZV-D33
   presentation that z/OS requires for REALTIME (PRESENT(COALESCED)).

Out of ZOS-8: REALTIME timing and ARCADE rules (accepted ZOS-6 / ZOS-7, not re-tested), the full GP / RP / HS
batteries and HA6 (ZOS-9 / 10), the release default of PRESENT, any new feature.

**Correction to the premise "PACFSIO = dataset / member service":** PACFSIO is the *TSO full-screen terminal* service
(FS = full screen). The dataset / member service is **PACHSIO**. PACFSIO matters to ZOS-8 only through its ESTAE
exit (recovery, C3); it is audited in full in section 4 as requested, and PACHSIO is audited alongside it (4.2).

## 2. Requirements mapping
| Source | Requirement | ZOS-8 item |
|---|---|---|
| Plan sec. 6 ZOS-8 (D44) | HS L1-L7 live, ESTAE E1-E3, S2 S2A-S2E with bell spacing 2 / 3 quanta and the 3-s end pause; exit = all PASS or an approved Z-entry (e.g. no audible bell) | sections 11, 12 |
| Plan sec. 10 (D38 mapping) | DATA = PDS FB 80/80; record `nnnnnnn PACHS001 nnn`; eligible = ARCADE from LEVEL(1); z/OS high score starts empty; CLIST `&SYSDSN` guard; never abend; decks never write the installed DATA | sections 5, 10 |
| Plan sec. 11 | keep the 2.0 ESTAE design; establish the LE interaction; E2 = "line mode restored, next game clean", not a message text | sections 6, 12 |
| Plan sec. 9 risks 1, 4, 5 | AMODE 24 profile A; ESTAE inside an LE enclave; PDS (not PDSE) semantics | sections 4, 13 |
| D38 (HS-HISCORE.md) | the full persistence contract, H1-H15 | section 5 |
| D39 (RP.0) | ESTAE through the test driver PACRPE (never the game) | section 6 |
| D41 / requirements sec. 27 (S1, S2) + sec. 24 ("repeat the same capability ladder on z/OS") | audible alarm and alarm patterns on the host path; authenticity rule (bell = 3270 WCC alarm, host-driven) | section 7 |
| ZOS-DIFFS C3 | PACFSIO ASMA303W accepted provisionally; revisit with recovery work | sections 4, 6 |
| CLAUDE.md D12 | no documented edge case untested before closing | section 16 |

The requirements document (v4) itself contains no high-score or abend-recovery clause; both come from the approved
project decisions D38 / D39 and the migration plan (D44). Recovery therefore means exactly D39 / plan sec. 11, not a
generic abend-recovery facility.

## 3. Current-state findings
- **Source.** `src/asm` (PACFSIO, PACHSIO, PACTSO) is byte-identical to 2.0-mvs-max **[O: git diff empty]**. No
  `src/zos/*.asm` override exists. PACPLAT / PACMAIN / PACDISP carry only Z1 / Z4.
- **Installed.** LOAD(PACMAIN) = the ZOS-6 program (PACHSIO and PACFSIO linked in), AMODE 24 / RMODE 24, compiled
  RMODE(24) DATA(24); CLIST(PACMAN) = Z2 + Z3 + Z5; CEEOPTS `ALL31(OFF),STACK(,,BELOW)` **[O: ZOS-6 closure]**.
- **PACHSIO on z/OS (batch / TSO batch) already PASS** **[O: ZOS-3 PACZ3HS1..8, JOB02401-02433]**: REPL creating a
  member, WRIT in place (twice), practice start not recorded, CLASSIC silent, malformed and empty members healed, DD
  without member, DUMMY, TSO batch (IKJEFT01, HTSO1 / HTSO2), and the genuine full-directory B14 (HH1) recovered by
  PACHSIO's ESTAE **under LE** with `HIGH SCORE NOT SAVED` and step RC 0. Final state = ref_hs model. Test PDSs
  `Z00000.PACMAN.HSTEST.T1` (SPACE (TRK,(5,1,5))) and `HSFULL.T1` (TRK,(5,1,1), directory full) still exist.
- **Live read path already PASS** **[O: ZOS-7 L1-L3]**: the CLIST `ALLOC F(PACHS) DA('Z00000.PACMAN.DATA(HISCORE)') SHR`
  with the member absent, PACHSIO READ RC 12 -> `Z`, end lines `HIGH SCORE nnnnnnn LEVEL nnn` + `START LEVEL nn: HIGH
  SCORE NOT RECORDED`; DATA unchanged afterwards.
- **Never exercised on z/OS**: a live write (REPL / WRIT) through the CLIST; any write into `Z00000.PACMAN.DATA`; the
  UNAVAILABLE line live; NOT SAVED live (B14 while PACFSIO's ESTAE is also active); any abend in TSO foreground under
  LE (PACFSIO ESTAE exit never driven on z/OS: C3 open); any bell live (every ZOS-5..7 live case was SOUND(NO)).
- **Logical alarm already PASS (dry run, not live)**: ZOS-3 PACZ3TD1..4 (12 S2T TSD runs, all 21 D41 edges, PRESENT
  EVERY) and ZOS-6 PACZ6DR1 N1 / F1 (COALESCED TSD with bells) **[O]**. Note: the logical bell-pattern proof is
  ZOS-3 / ZOS-6 TSD, not ZOS-6 / ZOS-7 live (those ran SOUND(NO)).
- **LE options in effect on this site** (no override except our CEEOPTS) **[O: PACZ4LE JOB03693 RPTOPTS]**:
  `TRAP(ON,SPIE)`, `ABTERMENC(ABEND)`, `TERMTHDACT(TRACE,,96)`, `MSGFILE(SYSOUT,FBA,121,0,NOENQ)`, all IBM-supplied
  defaults (observed in batch; the TSO session is assumed to use the same IBM defaults **[I]** since the logon proc has
  no CEEOPTS - recorded in ZOS-4 D1).

## 4. PACFSIO audit (read only; no change proposed)
### 4.1 PACFSIO (src/asm/PACFSIO.asm, 216 lines, = 2.0-mvs-max)
1. **Entry points / operations**: one CSECT, one entry; `CALL 'PACFSIO' USING OP BUF LEN RC`. OP = FSON, QRY, SEND,
   SENP, SENX, RECV, RECT, POLL, FSOF; anything else -> RC 8.
2. **Callers** **[S]**: production PACPLAT only (10 CALLs; it issues all nine ops); test driver src/probe/PACRPE.cob
   (FSON / SEND / RECV / FSOF for RP.0). No other module.
3. **Parameters**: OP X(4); BUF X(2048); LEN S9(4) COMP (halfword, LH / STH); RC S9(4) COMP. No copybook: PACPLAT's own
   WORKING-STORAGE (FS-OP / FS-BUF / FS-LEN / FS-RC).
4. **Macros / services**: TCLEARQ INPUT/OUTPUT, STFSMODE ON,INITIAL=YES / OFF, STTMPMD ON / OFF, STLINENO LINE=1,
   TPUT FULLSCR / NOEDIT, TGET ASIS (WAIT) and ASIS,NOWAIT, STIMER WAIT BINTVL, ESTAE (create / cancel). Direct
   control-block reads PSAAOLD (X'224') -> ASCBTSB (X'3C') for the TSO test.
5. **AMODE / RMODE**: no AMODE / RMODE statements; inherits the bind: AMODE 24 / RMODE 24 (profile A). TPUT / TGET
   register forms carry flags in the high byte of R1 -> **must stay AMODE 24** **[S]**. ESTAE (not ESTAEX) is valid in
   AMODE 24.
6. **Below-the-line storage**: SAVE, SENDBUF (2060), RESTR14, literals live in the CSECT (RMODE 24 -> below 16 MB);
   BUF is the caller's (PACPLAT WORKING-STORAGE, DATA(24) -> below) **[S + O: ZOS-4 D2 profile A]**.
7. **Registers**: standard STM 14,12 / own 18F save area chained (ST 13,SAVE+4; ST 14,8(13)); returns R15 = 0, the
   result in RC. Not reentrant (writes SAVE, SENDBUF, RESTR14 in its own CSECT); the module is bound RENT but runs
   from a private library in user-key storage, so the stores work **[O: every live write ZOS-5..7]**.
8. **DDNAME / member handling**: none (no dataset I/O).
9. **TGET / TPUT**: all of the module (see 4).
10. **Lifecycle**: FSON (clear queues, full-screen + TMP mode on, ESTAE CT) ... SEND / RECV / POLL ... FSOF (ESTAE 0,
    then RESTORE). PACDISP END calls PACPLAT FSOF before the line-mode end lines; PACMAIN FINI calls it again at the
    end (harmless).
11. **Return codes**: 0 OK; 4 not a TSO session (nothing issued); 8 unknown op / RECV 600 empty reads; else the TPUT /
    TGET R15 (e.g. 8 attention, X'14' disconnect). PACPLAT falls back to line mode on any error.
12. **Error paths**: RECT / POLL RC other than 0 / 4 -> LEN 0, RC = TGET RC; RECV gives up after 600 x 0.5 s.
13. **Recovery**: the ESTAE exit ABEXIT: rebuilds R12 from R15 (entry) minus ABOFF, BAL RESTORE (STTMPMD OFF,
    STFSMODE OFF, STLINENO 1), returns R15 = 0 = **percolate** (no retry, no SDWA change). It does not save
    registers; it uses only R9 / R12 / R14 / R15 and static RESTR14 **[S]**.
14. **MVS-specific assumptions**: ASCBTSB offset (architected, verified ZOS-3 by IHAASCB mapping); STFSMODE on TK4-
    came from usermod ZP60009, on z/OS it is standard TSO/E **[O: ZOS-5..7 live]**.
15. **z/OS incompatibilities / uncertainties**:
    - **C3** (ASMA303W, RC 4): the exit has `USING *,12` (still active) and `USING ABEXIT,15`; HLASM resolves
      `S 12,ABOFF` to base R15 (5BC0 F014 in the ZOS-2 listing **[O: JOB08888]**), which is the base the code needs,
      because at exit entry R15 = ABEXIT and R12 is undefined. ABOFF = ABEXIT - PACFSIO - 6 matches `BALR 12,0` at
      +6. **Statically correct [S]**; dynamically unproven on z/OS (the exit has never run there). A wrong base would
      make `BAL 14,RESTORE` branch wild and the exit would fail recursively, leaving the terminal in full-screen mode,
      so E1 / E2 PASS is a direct dynamic proof. **No change recommended** (a source edit only to silence a warning
      would break the frozen-module rule for no behavioural gain).
    - **LE ordering** (plan sec. 9 risk 4) **[I]**: with `TRAP(ON,SPIE)` a program check in COBOL code goes first to
      LE's ESPIE, not to any ESTAE; LE writes CEE3207S and a traceback (`TERMTHDACT(TRACE)`) to MSGFILE = DD SYSOUT,
      which the CLIST allocates to the terminal (`DA(*)`), **while the terminal is still in full-screen mode**; then
      `ABTERMENC(ABEND)` ends the enclave with an abend, RTM drives the ESTAE chain newest-first, so PACFSIO's exit
      (created after LE's own) restores line mode and percolates. Expected: line mode back, possibly a `***` / garbled
      LE text (D40 situation), then TSO's abend message. The actual abend code (S0C7 or a U40xx) is to be observed,
      not a criterion. If LE ever ended the enclave *without* an abend (ABTERMENC(RETCODE)), no ESTAE would run and
      the terminal would stay in full-screen mode: excluded by the observed site option, rechecked by E1.
    - RECV loop up to 300 s and STIMER waits: unchanged contract, proven live.
**Verdict:** PACFSIO stays unchanged. ZOS-8 owes it exactly one thing: the live E1 / E2 proof of its ESTAE exit under
LE (closes C3).

### 4.2 PACHSIO (the actual dataset / member service; 266 lines, = 2.0-mvs-max)
- Interface `CALL 'PACHSIO' USING OP RC DDN REC`; OP READ / WRIT / REPL; RC 0 done, 2 member written new, 4 no DD,
  8 unusable (DUMMY, no member on the DD, not RECFM F LRECL 80 BLKSIZE 80), 12 member missing / empty, 16 I/O error or
  abend caught, 20 bad op. DDN `PACHS` (PACPLAT literal); REC X(80). Callers: PACPLAT DO-HSRD / DO-HSWR; PACRPE E2
  (READ only).
- Macros: DEVTYPE (DD present), RDJFCB (member named?), OPEN TYPE=J with the member blanked and JFCNWRIT (BPAM, never
  meets a missing member: no 013-18), BLDL, FIND, READ / CHECK, CLOSE; WRIT = QSAM OPEN UPDAT, GET + PUTX (same block,
  no new space); REPL = QSAM OPEN OUTPUT, PUT, CLOSE (STOW adds or replaces the directory entry). Before every QSAM
  OPEN a fresh RDJFCB must still show the same member (never the whole PDS as sequential).
- Allocation: PACHSIO never allocates; the CLIST does (`&SYSDSN` guard, `ALLOC ... DATA(HISCORE) SHR REUSE`, else
  `DUMMY`; ARCADE only; FREE after the CALL and on every failure path) **[S]**. Disposition SHR: no exclusive ENQ on
  the member; one TSO session per user; a concurrent ISPF EDIT of HISCORE is not serialised (SPFEDIT ENQ not taken):
  last writer wins (D38 sec. 4, documented, not tested).
- Recovery: ESTAE CT around all I/O; the exit retries (SETRP RC=4, no dump; no-SDWA path R0 = RETRY, R15 4) into
  RETRY -> RC 16; ESTAE deleted before every return (also after a retry, E16b). Proven on z/OS for B14 **[O: HH1]**.
- AMODE 24 / RMODE 24: DCBs, JFCB, DECB in the CSECT below the line, as BPAM / QSAM / RDJFCB require **[S + O: ZOS-3]**.
- z/OS uncertainty **[I]**: a *program check* inside PACHSIO would be taken by LE's ESPIE first (not PACHSIO's ESTAE);
  only reachable through a code defect, PACHSIO is proven; documented, not tested. DATA must stay a PDS: on a PDSE
  the full-directory case does not exist (plan sec. 9 risk 5); DATA is a PDS **[O: ZOS-7 inspection]**.

## 5. Persistence contract (D38 on z/OS)
| Item | Contract | Basis |
|---|---|---|
| Missing member (HISCORE absent) | READ RC 12 -> REQ-HSST `Z`, high score 0 / level 0; first line `HIGH SCORE <max(0, score)> LEVEL <..>` | [O] ZOS-7 L1-L3, ZOS-3 |
| Existing valid record | READ RC 0, cols 1-7 numeric + cols 9-16 `PACHS001` (+ level) -> `R`, value / level shown | [O] ZOS-3 HS2..HS8 |
| Record format | 80 bytes: score 7 digits, blank, `PACHS001`, blank, level 3 digits, 60 blanks; FB 80 / 80 one record per block | [S] PACPLAT HS-REC, [O] ZOS-3 prints |
| Comparison | write only if this game's score is **strictly greater** than the persistent value | [S] DO-HSWR, [O] H3 |
| Tie | equal score: no write, no NEW line, member untouched | [O] ZOS-3 (H3 case set) |
| Eligibility | ARCADE and REQ-START = 01 (`LEVEL(1)`, the default); LEVEL(n>1) shows, never saves -> `START LEVEL nn: HIGH SCORE NOT RECORDED`; CLASSIC never reads / writes / prints | [S] PACMAIN HS-END, [O] ZOS-3 HA7 / HA8, ZOS-7 live |
| First write | `Z` + beaten + eligible -> REPL: QSAM OUTPUT one record, STOW adds the member, RC 2 -> `NEW HIGH SCORE` | [O] ZOS-3 HS1 (batch) |
| Update | `R` + beaten + eligible -> WRIT: GET + PUTX in place (same TTR, no new space), RC 0 -> `NEW HIGH SCORE` | [O] ZOS-3 HS2 / HS3 |
| Read after write | the next process (next CALL) reads the new record; within one game the in-memory value = max(persistent, current) | [O] ZOS-3 sequence; live: to prove |
| Malformed / empty member | counts as 0 (`Z`); the next eligible beaten save REPLaces it with one valid record (heal) | [O] ZOS-3 HS6 |
| Score 0, member missing | nothing created (0 is not > 0) | [O] ZOS-3 / H8 |
| Read error / unusable DD (DUMMY, attrs, I/O, abend) | `E` -> `HIGH SCORE UNAVAILABLE` only; game unaffected | [O] ZOS-3 (DUMMY / no member); live: to prove |
| No PACHS DD | `N`: silent (batch decks, dry runs) | [O] every ZOS dry run |
| Write error | any RC other than 0 / 2 (B14, x37, 913, I/O) -> `HIGH SCORE NOT SAVED`; persistent value shown unchanged; no abend; step / CALL RC 0 | [O] ZOS-3 HH1 (batch); live: to prove |
| Game / end screen when persistence fails | game result, final screen, D1 final-death frames and the other end lines unchanged; the HS lines come after `LEVEL nnn` in line mode | [S] PACDISP SHOW-END, [O] HH1 |
| Order in a TSC game | HSWR runs in PACMAIN after the game loop and **before** PACDISP END, i.e. while full-screen mode and PACFSIO's ESTAE are still active; PACHSIO's ESTAE is nested on top of it | [S] PACMAIN 196-200, PACDISP 292-296 |
| Partial write | REPL: the data block is written first, the directory changes only at STOW -> a failure before STOW leaves the old directory entry (old member or absence) intact; WRIT: one 80-byte block rewritten in place (a device-level failure during that single block write cannot be induced; same as MVS, documented) | [S], [I] |
| Concurrency | SHR, last writer wins; not tested (D38) | [S] |
| Space for the first write (DATA) | see 5.1 | [I] |

### 5.1 The "used 100" observation on Z00000.PACMAN.DATA
Facts: DATA was allocated SPACE=(TRK,(1,1,5)) (jcl/zos/PACZALLO.jcl) **[S]**; the z/OSMF list showed `used 100` for it
**[O: ZOS-7]**; the member directory is empty **[O]**. z/OSMF `used` is a percentage of the allocated space at track
granularity: 1 track allocated, 1 track holding the 5 directory blocks = 100 % **[I]**.
- It is **reporting, not by itself a failure**: an empty PDS whose directory sits on its only primary track always
  reads 100 %. Whether the first member block lands on that track (room left after five 256-byte directory blocks) or
  in the one-track secondary extent is a DASD-layout question that the listing cannot answer **[I]**.
- It is **not destructive either way**: if REPL needs a new extent and none can be obtained (volume full / extents),
  the x37 abend is caught by PACHSIO's ESTAE -> RC 16 -> `HIGH SCORE NOT SAVED`, no member, game unaffected (the same
  path as HH1's B14) **[O for the mechanism]**. The directory has 5 empty blocks: no B14 for one member **[I]**.
- Later saves are WRIT in place: no new space ever again **[O: ZOS-3]**.
- **Classification: must be checked before the first real write, but not on DATA**: prove it in batch on a test PDS
  with the **identical** allocation (TRK,(1,1,5)), then read its extent count read-only (section 11, B1). Not a guess:
  the batch proof either shows the member written with 1 or 2 extents, or shows NOT SAVED.

## 6. Recovery contract
| Failure class | MVS behaviour (oracle) | z/OS proven so far | Required ZOS-8 behaviour | Prod. change | Safe test |
|---|---|---|---|---|---|
| Missing member | Z, 0, heal on save | live (ZOS-7), batch (ZOS-3) | same | no | HL1 on a test PDS |
| Missing DATA dataset | CLIST DUMMY -> UNAVAILABLE, game plays, READY | batch DUMMY only | same, live | no | HL6: test CLIST naming a never-allocated DSN (no RENAME of DATA) |
| Missing PACHS DD | silent | every dry run | same | no | already proven |
| Allocation failure | CLIST guard `&SYSDSN` before ALLOC (a failed ALLOC ends a CLIST, E16) | guard path live only for OK | same | no | covered by HL6 (guard -> DUMMY) |
| Open failure / wrong attributes | RC 8 -> UNAVAILABLE | batch | same | no | already proven (ZOS-3) |
| Read failure (I/O) | RC 16 -> UNAVAILABLE | not inducible | same | no | documented not induced (as MVS) |
| Malformed data | 0, healed by next save | batch | same | no | already proven (ZOS-3 HS6) |
| Write failure | RC 16 -> NOT SAVED, no abend | batch B14 | same, live in full-screen with nested ESTAEs | no | HL8: test CLIST -> HSFULL.T1 (directory full, existing test PDS) |
| Full dataset / directory | B14 / x37 caught -> NOT SAVED | B14 batch | same | no | HL8 (B14); x37 = same path, not induced |
| Duplicate / member replace | REPL replaces via STOW; WRIT in place | batch | same | no | HL1 / HL3 |
| Abend during service operation (PACHSIO) | ESTAE retry RC 16 | B14 batch | same | no | HL8 |
| Program abend in the game (full screen) | PACFSIO ESTAE: line mode, percolate, READY; next game clean (RP.0 E1/E2/E3) | **never** | E1 / E2 / E3 PASS under LE; the LE message text / abend code recorded, not gated | no (unless E1 fails) | PACRPE test driver (D39), never the game |
| Terminal interruption (PA1 / ATTN) | no STAX; not part of any MVS contract; never tested on MVS | never | **not required** (no oracle, no documented edge case) | no | out of scope unless approved (U7) |
| User exit during service work | the only exit is Q / EOF; HSWR runs after the loop, once; no service work is in flight when the player can act | n/a | same | no | covered by HL1 (Q ends the game, then the write) |
| Abend before the write | nothing written (one write per game, after the last frame) | [S] | same | no | E-cases write nothing (PACRPE E2 reads only) |

No production change is needed for any class, on the present evidence. A change becomes necessary only if E1 / E2
fail on z/OS (the exit does not restore line mode under LE); that would be a PACFSIO z/OS override (a Z-entry) and
stops ZOS-8 for a new design.

## 7. Sound / alarm boundary
- Proven: the bytes. Every S2 behaviour (patterns 1 / 2 / 2 / 3 / 4 / 3 bells, G = 2 / 3 quanta, bell-only writes in
  the 3-s end pause, SINGLE, SOUND(NO)) = models in TSD on z/OS (ZOS-3 PACZ3TD1..4, PRESENT EVERY) and the COALESCED
  pattern clock in TSD (ZOS-6 N1 / F1). Under COALESCED the stride equals PT-G (2 NORMAL / 3 FAST), so pattern steps
  land on written quanta (zos6-production-design sec. 16).
- Unproven live: (a) the WCC alarm bit X'04' and the bell-only writes actually leaving z/OS TSO / VTAM / TN3270E at the
  model positions and spacing during a real game; (b) that the user's terminal (c3270 on macOS) makes them audible as
  separate bells.
- Smallest live validation (no high-score write, no ESTAE in the same session):
  - **S8-A** NORMAL: the ZOS-7 L2 cards (wall-stop, LEVEL 2 = not eligible, LOST) with `SOUND(YES)` instead of
    `SOUND(NO)` (same EXEC length, 57 characters): start 1, two deaths 2 + 2, GAME OVER 3 on the final-death writes ->
    lengths 1 / 2 / 3, NORMAL spacing 2 quanta.
  - **S8-B** FAST: the same + `SPEED(FAST)` (= ZOS-7 L3): 3-quanta spacing.
  - **S8-C** (recommended, U6): an end-of-game pattern on bell-only writes inside the 3-s end pause (4-bell WIN) - the
    MVS S2C scenario (tests/s2live/LIVEC.txt, CLASSIC RTWIN) re-derived under COALESCED; bell-only writes are a host
    write type not yet seen live on z/OS.
  - ALARM(SINGLE) and SOUND(NO): not repeated live (SOUND(NO) is already proven by every ZOS-5..7 live case; SINGLE is
    byte-proven and its writes are a subset of PATTERN's).
- Evidence split: the trace proves (a) objectively (every host write = model byte for byte including the alarm bit;
  bell gaps reported); audibility (b) is the user's attestation, as on MVS S2.4. If (b) fails while (a) passes, the
  outcome is a Z-entry "no audible bell on this client path" (plan exit criterion), not a source change.
- Not coupled with HS: D38 "no new alarm for a high score"; S8 cases run at LEVEL 2 (not eligible) and read DATA only.

## 8. Source-change proposal
**None.** On the current evidence ZOS-8 needs no production source, copybook, assembler or CLIST change. New files
would be test / tooling only (section 9 D) plus one probe override (below). If a live result shows a defect, the phase
stops and a separate change is proposed (Z-entry).

Probe override (test asset, not production; needs approval U4): `src/probe/zos/RPESTAE.clist` = src/probe/RPESTAE.clist
+ the Z2 CEEOPTS block (without it the AMODE 24 PACRPE would run under the session's ALL31(ON) / stack-anywhere
defaults, the reason for Z2) and PACHS pointed at a test PDS for E2 (read only).

## 9. Module classification
| Module | Class | Why |
|---|---|---|
| PACRT, PACGAME, PACMAP, PACAI | **A guaranteed unchanged** | portable core, frozen (R2, ZOS-7) |
| PACSCR, PACDISP | **A guaranteed unchanged** | display; the S2 pattern player and RTQS are proven in TSD; plan: frozen in ZOS-8 |
| PACREQ (copybook) | **A guaranteed unchanged** | HS / alarm fields exist since 2.0 / Z4 |
| PACPLAT | **A guaranteed unchanged** | HSRD / HSWR decision proven (ZOS-3); plan: frozen in ZOS-8 |
| PACMAIN | **A guaranteed unchanged** | HS-END order fixed; nothing in ZOS-8 touches it |
| PACTSO | **A guaranteed unchanged** | no ZOS-8 role beyond the proven clock |
| PACHSIO | **B likely unchanged** | proven on z/OS in batch incl. B14; only live HL1-HL8 remain |
| PACFSIO | **B likely unchanged** | proven live for all ops; only the ESTAE exit is unproven (E1 / E2); C3 statically correct |
| z/OS CLIST PACMAN | **B likely unchanged** | HS block proven for the missing member; test CLIST copies differ only in the DATA DSN |
| (none) | **C likely ZOS-8 modification** | nothing identified |
| tools/zowe/zos8_*.py, tests/zos8_fixture.py, test section 25, decks jcl/zos/PACZ8*.jcl, src/probe/zos/RPESTAE.clist, PACRPE z/OS build deck | **D test / tooling only** | section 15 |

## 10. Safe test-data strategy
- The production member `Z00000.PACMAN.DATA(HISCORE)` is written by **no** batch deck and by **no** live case before
  the final, separately approved production step (U1).
- New test PDS (needs allocation approval, U2): **`Z00000.PACMAN.HS8.T1`**, PDS (not PDSE), RECFM FB, LRECL 80,
  BLKSIZE 80, **SPACE=(TRK,(1,1,5))** - the exact shape of DATA, so the first-write space question is answered on an
  identical dataset. A rerun uses `HS8.T2` (no DELETE, no reallocation; ZOS-3 rule).
- Existing test PDS reused read / write-fail only: `Z00000.PACMAN.HSFULL.T1` (directory full, HISCORE absent) for NOT
  SAVED; its state after a failed STOW is a test-only orphaned data block, directory unchanged (as after ZOS-3 HH1).
- Live test CLISTs (needs upload approval, U3): members rendered from src/zos/PACMAN.clist with **only** the two DATA
  DSN strings replaced, guarded by a test that the diff is exactly those lines:
  `CLIST(PACZ8HT)` -> `HS8.T1(HISCORE)`, `CLIST(PACZ8HU)` -> `Z00000.PACMAN.HS8.NONE` (never allocated: `&SYSDSN` not OK
  -> DUMMY -> UNAVAILABLE; replaces the MVS RENAME of DATA), `CLIST(PACZ8HF)` -> `HSFULL.T1(HISCORE)`. The installed
  CLIST(PACMAN) is not touched.
- Cleanup: the no-delete rule stands, so "cleanup" = the test datasets / members stay, read-only, recorded in the
  evidence with their final state (as ZOS-3 HSTEST / HSFULL); deletion only if the user decides it later.
- Never `Z00000.ZHEIST.*`; only `Z00000.PACMAN.*`.

## 11. Batch validation plan (Stage A offline, Stage B batch)
**Stage A - offline / model / static (no z/OS).** Tools and tests: (1) scenario cards for HL1-HL8 (TURN, AI(0),
deterministic scores; HL2 = an exact replay of HL1 = tie) and their expected end lines from ref_gp2 + ref_hs; (2)
S8-A / S8-B expected streams from ref_rt + ref_s2 (skips) on the ZOS-7 cards with SOUND Y; S8-C re-derived and proven
robust like zos7_scen; (3) checkers `zos8_hs_check` (end lines, CLIST path, read-only member check) and
`zos8_sound_check` (ZOS-7 checker reused + alarm bits / bell gaps), `zos8_estae_check`; (4) fixtures + negatives;
(5) test-CLIST generator + diff guard; (6) PACZ8* deck generation + audit (only `Z00000.PACMAN.*`, no DATA, no
DELETE, < 4,000 estimated spool lines); (7) ZOS-7 tools frozen (U9). PASS = test section 25 + guards green. Not
destructive.

**Stage B - batch service tests (one job each, STOP after each).**
| Job | Purpose | Program | Data touched | Expected | Destructive | PASS evidence |
|---|---|---|---|---|---|---|
| B1 PACZ8HB | first write on a DATA-shaped PDS + read back + tie + update | IEFBR14 (alloc HS8.T1 TRK,(1,1,5)), PACZ6D (installed program's test member) 4 ARCADE batch steps with DD PACHS = HS8.T1(HISCORE): H1 create, H2 lower, H3 equal, H4 higher; IEBGENER print; IKJEFT01 LISTDS | creates HS8.T1 only | step RC 0; lines = ref_hs / oracle 312 blocks; member = one record = H4 value; no IEC / abend | creates a new test PDS (approval U2); nothing else | checker PASS + read-only z/OSMF query of HS8.T1: extents (1 or 2) and member list |
| B2 PACZ8RPE | build the RP.0 test driver | IGYCRCTL PACRPE, bind with the existing OBJ(PACFSIO) / OBJ(PACHSIO) into **LOAD(PACRPE)** AMODE 24 / RMODE 24; batch E1 / E3 steps (no TSO: nothing sent, 0C7 forced) | new member LOAD(PACRPE) | compile / bind RC 0 (PACFSIO C3 not re-assembled); E1 / E3 steps end abnormally with the LE path recorded (CEE3207S, abend code) = trigger proven | adds a test load member (approval U4); PACMAIN untouched | listing check + recorded abend path |
Rollback: none needed (nothing existing is changed); B1 failure = NOT SAVED / IEC message analysed, DATA never involved.

## 12. Live validation plan (Stages C, D, E, F; one case at a time, STOP after each unless approved as a group)
**Stage C - high score on test data** (c3270, ISPF Command Shell, script port; TURN mode, AI(0), ANIM(NO), SOUND(NO),
PRESENT(COALESCED) typed, RULES default ARCADE):
| Case | EXEC | Expected | Data |
|---|---|---|---|
| HL1 | `CLIST(PACZ8HT)`, LEVEL default 1, cards scoring S1 > H4's value, Q | `HIGH SCORE S1 LEVEL 001`, `NEW HIGH SCORE` | HS8.T1 WRIT (or REPL if B1 not run) |
| HL2 | same cards (tie) | `HIGH SCORE S1 ...`, no NEW line | read only |
| HL3 | longer cards, S3 > S1, Q | `NEW HIGH SCORE` S3 | WRIT in place |
| HL4 | `LEVEL(5)` beating S3 | `START LEVEL 05: HIGH SCORE NOT RECORDED` | read only |
| HL5 | `RULES(CLASSIC)` | no high-score line | none |
| HL6 | `CLIST(PACZ8HU)` (no dataset -> DUMMY) | game plays, `HIGH SCORE UNAVAILABLE`, clean return | none |
| HL7 | read-only member query of HS8.T1 | one record `S3 PACHS001 001` | read only |
| HL8 | `CLIST(PACZ8HF)` eligible scoring game | B14 caught inside the full-screen game: `HIGH SCORE NOT SAVED`, end screen and other lines = model, clean return, no ABEND / CEE message | HSFULL.T1 (test) |
Every case: trace = model byte for byte (ZOS-7 TURN checker), end lines = ref_hs, shell regained.

**Stage D - recovery (ESTAE)**, one session, PACRPE through the z/OS RPESTAE test CLIST (never the game): E1, then a
clean game G1 (CLASSIC TURN, Q), E2 (PACHS -> HS8.T1, READ only), G2, E3 (control), G3. PASS: after E1 / E2 the
terminal is in line mode and the shell / READY accepts the next command; G1-G3 start in full screen and end cleanly;
E3 = plain line-mode abend. Recorded, not gated: the LE text, abend code, any `***` (D40). PASS of E1 / E2 closes C3.
Rollback: if the terminal is left in full-screen mode, the user reconnects c3270 (the session is the user's; no kill
by Claude); stop and report.

**Stage E - sound live**: S8-A, S8-B, (S8-C). PASS: trace = model incl. alarm bits and bell-only writes, frozen
ZOS-6 gates on gameplay writes, bell gaps reported; user attests separate audible bells. DATA read only.

**Stage F - production first write (only if U1 = a).** Read-only precheck of DATA (attributes, member list empty,
extents); one eligible game through the installed CLIST(PACMAN) (`AI(0) PLAY(TURN) ANIM(NO) SOUND(NO)`, LEVEL 1),
expected `NEW HIGH SCORE`; read-only member check: one record. This is the only write to DATA in ZOS-8; it is not
reversible without a delete / edit (not allowed), and from then on the z/OS high score is that value.

## 13. Risks (ranked)
| # | Risk | Level | Why |
|---|---|---|---|
| 1 | Terminal cleanup after an abend under LE (E1 / E2) | **HIGH** | never run on z/OS; LE intercepts first and writes to the terminal in full-screen mode; failure leaves the user's c3270 in full-screen (manual reconnect); mitigated: test driver only, its own session, observed ABTERMENC(ABEND) |
| 2 | Recovery after a service failure in a live full-screen game (nested ESTAEs, HL8) | **MEDIUM** | the B14 retry is proven in batch only; live adds PACFSIO's ESTAE underneath; failure modes stay non-destructive (test PDS) |
| 3 | First real HISCORE write (DATA) | **MEDIUM** | persistent, shared, not reversible under the no-delete rule; technical failure is non-destructive (NOT SAVED); mitigated by B1 / Stage C on a DATA-shaped PDS first |
| 4 | Live SOUND / ALARM audibility | **MEDIUM** | client-dependent (c3270 on macOS, terminal bell settings); bytes are proven; failure = Z-entry, not a defect |
| 5 | Dataset space / directory for the first write | **LOW-MEDIUM** | `used 100` is track-granular reporting; outcome either fits / extends or NOT SAVED; answered by B1 on an identical shape |
| 6 | PACFSIO portability (C3) | **LOW** | all ops proven live; the exit's base is statically right (listing); dynamic proof = E1 |
| 7 | PDS member replace semantics | **LOW** | REPL / WRIT / heal proven on z/OS PDS (ZOS-3); DATA is a PDS, not PDSE |
| 8 | Partial / corrupt write | **LOW** | REPL changes the directory only at STOW; WRIT = one block; malformed data heals; one write per game after the last frame |
| 9 | AMODE 24 / below-the-line | **LOW** | profile A proven (ZOS-4 D2) and every live run since; PACHSIO control blocks in an RMODE 24 CSECT |
| 10 | Concurrency (SHR, ISPF edit) | **LOW** | single user ID; documented last-writer-wins |
| 11 | PA1 / ATTN during a game | **not assessed** | no MVS contract; proposed out of scope (U7) |

## 14. Dependencies
- Approvals U1-U12 (section 17) before any tooling that depends on them; each job / live case separately authorised.
- User: c3270 session logged on manually, ISPF Command Shell, script port; terminal bell ON for Stage E; c3270
  reconnect if Stage D leaves full-screen mode.
- Existing z/OS objects (read / reuse only): LOAD(PACMAIN), LOAD(PACZ6D), OBJ(PACFSIO), OBJ(PACHSIO), CLIST(PACMAN),
  CEEOPTS, HSFULL.T1; ZOS-6 / ZOS-7 tools (frozen) and models ref_hs, ref_gp2, ref_rt, ref_s2.
- Site limits: < 4,000 spool lines per job (S722 at ~5,000); no high-volume work.

## 15. Implementation order (after approval)
1. Stage A tooling + test section 25 + test-CLIST generator / guard + decks PACZ8HB / PACZ8RPE (audit) -> STOP.
2. B1 PACZ8HB (allocates HS8.T1) -> STOP -> read-only HS8.T1 query -> STOP.
3. B2 PACZ8RPE (LOAD(PACRPE)) -> STOP.
4. Upload the three test CLISTs + the z/OS RPESTAE test CLIST (byte-verified) -> STOP.
5. Stage C HL1..HL8 -> STOP after each (or as approved).
6. Stage D E1 / G1 / E2 / G2 / E3 / G3 -> STOP.
7. Stage E S8-A, S8-B, (S8-C) -> STOP after each.
8. Stage F production first write (if approved) -> STOP.
9. Closure: evidence docs/evidence/zos8-services.md, ZOS-DIFFS (C3 closed or Z-entry), CURRENT_PHASE, commit + tag
   `zos-8` on approval.

## 16. Acceptance criteria
ZOS-8 is PASS when all of the following hold (or a gap is an approved Z-entry):
1. B1: H1-H4 = models; HS8.T1 = one record = the H4 value; extent count recorded.
2. HL1-HL8 PASS (traces = models, end lines = ref_hs, member states as expected, clean return each time).
3. E1 / E2 / E3 + G1-G3 PASS; C3 closed (no PACFSIO change) or, if E1 / E2 fail, ZOS-8 stopped for a design.
4. S8-A, S8-B (and S8-C if approved): every host write = model incl. alarm bits; frozen ZOS-6 gates PASS; user attests
   audible separate bells, or an approved Z-entry for the client.
5. Stage F (if approved): DATA(HISCORE) = one valid record = the game's score / level, `NEW HIGH SCORE` shown.
6. No production source change (or each one an approved Z-entry); src/asm, core and display byte-identical to zos-7.
7. D12: every documented edge case either tested on z/OS (ZOS-3 batch or ZOS-8 live) or explicitly documented as not
   inducible (device I/O error, x37 distinct from B14, program check inside PACHSIO, concurrency), as on MVS.
8. DATA written at most once (Stage F); `Z00000.ZHEIST.*` never touched; no delete / purge / reallocation.

## 17. Unresolved decisions requiring approval
- **U1 Production DATA write in ZOS-8.** (a) **Recommended:** test PDS first (B1, Stage C), then exactly one production
  first write (Stage F) as the final acceptance; (b) no production write in ZOS-8 (DATA stays absent until the
  ZOS-10 release smoke); (c) the MVS-style L1-L7 directly on DATA (not recommended).
- **U2** Allocate `Z00000.PACMAN.HS8.T1` PDS FB 80/80 SPACE=(TRK,(1,1,5)) in B1 (rerun -> T2, never deleted). Note:
  after B1 the member exists, so Stage C proves live WRIT / tie / read-back but not a live REPL (creation); with U1 (a)
  Stage F is the live creation. With U1 (b) a second identical test PDS `HS8.L1` (empty) for a live HL1 creation is
  proposed instead.
- **U3** Upload three test CLIST members PACZ8HT / PACZ8HU / PACZ8HF into `Z00000.PACMAN.CLIST` (diff = DATA DSN only).
- **U4** Build PACRPE on z/OS into a new member LOAD(PACRPE) (B2) and add the probe override
  `src/probe/zos/RPESTAE.clist` (Z2 CEEOPTS block; E2 PACHS -> HS8.T1, read only), uploaded as `CLIST(RPESTAE)`.
- **U5** C3 disposition: close as "accepted permanently, statically and dynamically correct" after E1 / E2 PASS, no
  PACFSIO change (recommended); alternatively a z/OS PACFSIO override only to silence ASMA303W (not recommended).
- **U6** Sound scope: S8-A + S8-B required; S8-C (4-bell WIN + end-pause bell-only writes) recommended; SINGLE not
  repeated live.
- **U7** PA1 / ATTN during a game: out of scope, recorded as untested with no MVS contract (recommended), or an
  exploratory case.
- **U8** HL8 on the existing `HSFULL.T1` (adds one orphaned test data block) - approve, or skip live NOT SAVED (batch
  HH1 stands).
- **U9** Freeze the ZOS-7 tools (zos7_scen, zos7_drive, zos7_live_check, zos7_dry, zos7_fixture) for ZOS-8 as ZOS-6's
  were for ZOS-7; ZOS-8 tools import them.
- **U10** B1 load module: PACZ6D (test member, as the ZOS-7 dry runs; recommended) or PACMAIN.
- **U11** Live HS mode: TURN (deterministic, no timing; recommended) vs REALTIME (adds nothing to HS; timing already
  accepted).
- **U12** Gate granularity: one STOP per live case (ZOS-7 practice) or an approved group per stage (e.g. HL1-HL7).

## 18. Approved decisions (user, 2026-10-20)
Conclusion: **no production source change is authorized.** PACHSIO is the high-score file service; PACFSIO stays
unchanged unless new runtime evidence proves a defect.
- **U1** Persistence is tested completely on test data first. Stage F (exactly one real first write of
  `Z00000.PACMAN.DATA(HISCORE)` + read back) is **not authorized yet**: it needs a separate explicit go-ahead after
  Stages B-E pass.
- **U2** `Z00000.PACMAN.HS8.T1` approved as the persistence test dataset, with the allocation / record / directory
  geometry of DATA.
- **U3** Three test CLIST copies, derived from the accepted installed CLIST, differing only in the DATA reference the
  test needs. The installed production CLIST is never replaced.
- **U4** Test-only LOAD(PACRPE) and the z/OS RPESTAE test CLIST with the required CEEOPTS block; PACRPE is never
  promoted to PACMAIN.
- **U5** C3 is closed with no PACFSIO change if E1 / E2 show: the expected abend / error; a usable line-mode TSO state
  after recovery; the next clean game running without reconnecting.
- **U6** Live sound: L2 NORMAL with sound on, L3 FAST with sound on, one WIN / end-pause case. No other sound scenario
  unless these expose a real gap.
- **U7** PA1 / ATTN mid-game: out of scope.
- **U8** Live NOT SAVED on the existing HSFULL.T1 (its expected orphaned test block is acceptable); never on DATA.
- **U9** The ZOS-7 tools are frozen; ZOS-8 imports / reuses them and never modifies the accepted drivers, checkers or
  fixtures.
- **U10** Batch service tests run PACZ6D.
- **U11** Live high-score cases run in TURN mode.
- **U12** Stage-level fail-fast execution; exception: each recovery case E1 / E2 / E3 is its own micro-gate (after each
  abend: prove the recovery and run the defined clean follow-up before continuing). Stage F always needs its own
  approval.

## 19. Stage A - local implementation (2026-10-20; nothing allocated, uploaded, built, submitted or run)
Files (new unless noted): tools/zowe/zos8_scen.py (cases, cards, chain), zos8_batch.py (B1 / B2 decks + checkers,
test CLIST renderers + guards, read-only state queries), zos8_drive.py (live driver on the frozen ZOS-6 Driver),
zos8_live_check.py (live checker; imports zos6 / zos7 checkers unchanged), tests/zos8_fixture.py (synthetic traces and
spools), tests/zos8live/*.txt (the exact cards of every live TURN game), src/probe/zos/RPESTAE.clist (test CLIST, U4),
jcl/zos/PACZ8HB.jcl / PACZ8RPE.jcl (decks of record), tests/test_zos_tools.py section 25 (modified: appended).
Unchanged: every production source, copybook, PACHSIO, PACFSIO, the installed / template CLIST, the ZOS-5 / 6 / 7
tools and decks (test section 25 pins them to tag zos-7).

Refinements of section 11 / 12, made while implementing (for review with the Stage A report):
- **B1 games** (all BAT ARCADE LEVEL 1, frozen card files): H1 GPTSO 370 (member missing: REPL creates it, NEW), H2
  GPTSO (tie), H3 GPREVB 720 (WRIT in place, NEW), H4 GPTSO (lower). HS8.T1 after B1 = `0000720 PACHS001 001`.
  The GPREVB base output = oracle 312 HA2 (test section 25). Smaller than the H1-H4 of section 11 (estimated 1,838 SYSOUT
  lines instead of ~4,600 with GPAI0 / G2CLRL).
- **Stage C order** on HS8.T1 (each game TURN, AI(0), ANIM(NO), SOUND(NO), PRESENT(COALESCED)):
  | Case | CLIST | Game (tests/zos8live) | Store before | Expected high-score lines | Store after |
  |---|---|---|---|---|---|
  | HL1 | PACZ8HT | LIVEB at LEVEL(5): 2180 | 720 | `HIGH SCORE 0002180 LEVEL 005`, `START LEVEL 05: HIGH SCORE NOT RECORDED` | 720 |
  | HL2 | PACZ8HT | LIVEB: 980 | 720 | `HIGH SCORE 0000980 LEVEL 001`, `NEW HIGH SCORE` (WRIT) | 980 |
  | HL3 | PACZ8HT | LIVEB: 980 (tie) | 980 | `HIGH SCORE 0000980 LEVEL 001` | 980 |
  | HL4 | PACZ8HT | GPAI0 (GHOSTS(3)): 1310 | 980 | `HIGH SCORE 0001310 LEVEL 001`, `NEW HIGH SCORE` (WRIT) | 1310 |
  | HL6 | PACZ8HU | DIE1: 510 | (no dataset: DUMMY) | `HIGH SCORE UNAVAILABLE` | - |
  | HL8 | PACZ8HF | DIE1: 510 | HSFULL.T1, HISCORE absent | `HIGH SCORE 0000510 LEVEL 001`, `HIGH SCORE NOT SAVED` | absent |
  | HL7 | - | read-only member query of HS8.T1 | | one record `0001310 PACHS001 001` | |
  The live creation (REPL) of a member is B1 H1 (batch) and, with U1, Stage F. **HL5** (CLASSIC silent) is not a separate
  game: CLASSIC never allocates PACHS (the CLIST block runs only for ARCADE), and the CLASSIC games S8C and GD (and ZOS-6
  R1 / R2) are checked to end without a high-score line.
- **HL8 terminal messages:** in TSO foreground the data-management message of the failed STOW (IEC217I B14-0C, seen in
  JESYSMSG in the batch HH1) is expected to reach the terminal, possibly while the game is still in full-screen mode.
  Allowed in HL8 only: at most one IEC217I B14-0C for `<prefix>.HSFULL.T1(HISCORE)`, and at most one TSO hold (`***`
  + one ENTER, logged as category `hold`) before the end screen. Any other IEC / IKJ / CEE / ABEND text fails.
- **Stage D follow-up game GD:** CLASSIC TURN DIE1 through the installed CLIST(PACMAN) (`AI(0) RULES(CLASSIC)
  PLAY(TURN) ANIM(NO) SOUND(NO) PRESENT(COALESCED)`): full screen, a death, QUIT; it touches no dataset (CLASSIC never
  allocates PACHS). Before it, `LISTALC STATUS` proves a usable line-mode TSO; if LISTALC shows a CEEOPTS DD left by
  the RPESTAE CLIST (on MVS the CLIST did not continue after the abending CALL: the evidence of RP.0 shows TSO's `ENDED
  DUE TO ERROR` and READY, not the CLIST's WRITE), the driver sends `FREE F(CEEOPTS)` (category `cleanup`): the
  installed CLIST refuses an existing CEEOPTS DD by design (Z2). The checker requires FREE exactly when CEEOPTS is
  listed. ISPF option 6 behaviour after an abending command is not known on this system: every `***` is answered by
  one ENTER (at most 4), anything else = STOP after 90 s (the user reconnects; nothing more is sent).
- **S8C (WIN / end pause):** CLASSIC TURN WIN0 (183 commands, `RULES(CLASSIC) PLAY(TURN) ANIM(NO) SOUND(YES)`): START 1
  bell, WIN 4 bells = 1 on the end screen + 3 bell-only writes (the D41 end-pause path; the TURN variant of oracle 308
  S2T22 / S2T23, S2T23 PASS on z/OS in PACZ3TD4). Deterministic: no REALTIME timing risk.
- **S8A / S8B:** the ZOS-7 L2 / L3 plans with `SOUND(YES)` (same EXEC length), accepted by the unchanged
  zos7_live_check.check with the bell-rung model; expected bells START 1, DEATH 2, DEATH 2, GAME OVER 3 (on the
  final-death writes); model pattern-step gaps 300 ms (NORMAL) / 375 ms (FAST), reported, not gated.

Local results: zos8_batch.py --selftest PASS; test section 25 PASS (12 live positives + HL8 IEC variants + E-case
leftover variants, 21 live negatives fail closed for the intended reason, 11 batch spool faults fail, sound coverage
never PASS when the bells differ, driver on the fake x3270if incl. the hold / IEC stop / recovery / cleanup branches);
guards tests/zos_c2.py, test_core_frozen.py, test_g8.py, tools/zowe/r3_gate.py rc 0; `git diff --check` clean.

## 20. Live corrections (2026-10-20, each approved by the user before use)
- **HL8 end screen (Stage C):** the live program shows `NEW HIGH SCORE` on the end screen only when the save
  succeeded (PACSCR `IF RP-HI = 1 AND REQ-HSNEW = 'Y'`, D38); tests/ref_rp.py Tracker (unchanged) decides from the
  score alone. zos8_live_check.turn_model now takes the persistence outcome from ref_hs (`saved` = a `NEW HIGH SCORE`
  line): byte-identical model for every saved / practice / unavailable game, only the label on the failed-save end
  screen. Live HL8 = FUNCTIONAL FAIL (preserved); OFFLINE REVALIDATION of the same trace = PASS; HL7 PASS.
- **Initial ISPF hold (Stage D E1):** every EXEC from the ISPF Command Shell is held by TSO / ISPF (`F1 C1`, then
  `***`) until one ENTER, before the command runs (the game plans already had it). The first E plans waited for the
  test screen at once and stopped after 30 s (nothing ran: trace = EXEC, blank write, `***`). E1 / E2 / E3 now:
  EXEC, `***`, one ENTER, the test screen; the checker requires exactly that order (one `***` right before one empty
  ENTER, no text before the screen). The held E1 EXEC is resumed, never resent: zos8_drive.py --resume-after
  <first log> continues from the hold (the screen must be that EXEC's `***`), the ordinals continue the first log; the
  checker joins the two trace segments (--trace2 / --drive-log2) only if lossless: same negotiated functions,
  SEQ-NUMBERs +1 across the boundary in both directions, segment 1 ends with the `***`, segment 2 starts with the
  releasing ENTER, increasing times. Tested in section 25 (missing / duplicated / misordered hold, lost or stray
  boundary record, swapped or single segment, resume refused off the hold or for another case).
- **Test-screen recognition (Stage D E1, second stop):** the RPESTAE test screen's own lines `PRESS ENTER: THE
  PROGRAM FORCES A 0C7 ABEND.` and `PASS: LINE MODE, ABEND MESSAGE, THEN READY.` contain `ABEND`, which the generic
  error detector took for an error. zos8_drive recognises the screen only when all five exact lines of the case are
  on it (zos8_drive.test_screen); only those exact lines are exempt, any error text elsewhere (or in an altered line)
  stops. The checker requires the screen record to be exactly those five lines. --resume-after also resumes from the
  displayed complete test screen (earlier logs exactly [EXEC, hold ENTER]; next = the abend ENTER), and the checker
  joins three segments (EXEC -> `***` | ENTER -> test screen | abend ENTER -> recovery -> LISTALC -> conditional FREE
  -> GD) under the same lossless rules, cut only at those two points. Tested in section 25 (the original false
  positive reproduced; altered / incomplete / other-case screens; missing, repeated, modified, reordered segments).
- **LISTALC paging and CEEOPTS cleanup (Stage D, E1 recovery, 2026-10-20):** observed on two traced LISTALC STATUS
  runs and one FREE on the live session. Every command typed on the shell is first held by ISPF (`F1 C1`, then the
  shell screen with `===> <command>` and `***`), one ENTER. LISTALC then wrote 13 line-mode output pages (`7E C3`
  records ending with `***`, one ENTER each; one page split over two host records, `7E C1` + `F1 C2 ... ***`; the
  first page starts with `--DDNAME---DISP--`), then the shell; FREE F(CEEOPTS) wrote no output (hold, ENTER, shell).
  The first E plans expected one `***` and looked for CEEOPTS on the hold screen only (never on the output).
  CEEOPTS rule (strict): allocated only if exactly one DD line `CEEOPTS <disp>` directly follows the dataset line
  `<prefix>.CEEOPTS` in the output lines of all pages (a pair split across pages counts); absent if CEEOPTS appears
  nowhere; anything else is ambiguous and stops. The CEEOPTS left by the interrupted E1 was listed (`CEEOPTS  KEEP`),
  freed once, and absent from the next LISTALC; the dataset stayed catalogued, all datasets unchanged
  (~/zos8-live/stageD-E1-recovery, stageD-E1-free). zos8_drive.held_command: every screen validated before its
  ENTER (first the initial hold of that command, then only output pages, then the idle shell); any error text, any
  other screen, more than PAGES_MAX = 30 pages or PAGE_TIMEOUT = 30 s without a new screen stops; the page count is
  not fixed. FREE only when the rule says allocated, and it must write no output. zos8_live_check.held_trace checks
  the same in the trace (one `***` per page as its last text, one empty ENTER per hold / page, trace ENTERs = driver
  log ENTERs, no repeated page, header first, cleanup = [FREE, ENTER] or nothing, next input = the GD EXEC). Section 25:
  17 checker and 10 driver faults fail / stop; the checker and the driver accept the two live LISTALC traces / screens.
- **E1-T2: 120-column test screen, screen-cut join, abend messages (Stage D, 2026-10-20):** on the 27 x 120 screen
  of E1-T2 PACRPE's test screen starts its first line at row 1 column 81 and its E3 line at row 5 column 81; the E3
  line continues on row 6 (`...(FSOF), T` / `HEN 0C7.`). The driver matched each approved line within one Ascii() row
  and timed out (driver STOP after EXEC + hold ENTER; nothing else sent). Fix (zos8_drive.screen_buffer /
  screen_state): the Ascii() rows are joined at the screen width into the 3270 buffer, without changing or removing
  any character; the screen is the case's test screen only if each of the five exact lines is in the buffer exactly
  once, in order, and the rest is blank; some but not all lines, a repeat, another order, other text or any error text
  outside the exact lines = STOP; the ABEND exemption stays limited to the exact PRESS ENTER line. Regression: both
  real screens (24 x 80 unwrapped, 27 x 120 wrapped) rebuilt byte-identical to the preserved Ascii() files; 11 altered
  screens stop. The pending E1-T2 invocation was continued from its displayed test screen (zos8_drive --resume-after,
  abend ENTER first, nothing resent) on a second trace; the checker joins two segments cut at the test screen only
  when the cut is named (`--cuts screen`): segment 1 ends with exactly the test screen record, segment 2 starts with
  the abend ENTER, the driver logs split there, per segment terminal inputs = driver actions, SEQ-NUMBERs continuous,
  and every trace / log matches its own `.sha256` file; no other join is enabled. E1-T2 PASS (joined checker rc 0).
  Abend messages on the terminal: LE `CEE3207S The system detected a data exception (System Completion Code=0C7).`,
  then TSO `Command abend - Abend 0C4 hex occurred processing command 'CALL    '.` and `CMD abended - 'EXEC'
  terminated abnormally.` (batch B2: S0C7). The reason LE and TSO report different completion codes is not
  established. The Stage D acceptance criteria are unchanged (the abend text / code is recorded, not gated).
- **Stage E alarm-bit context (S1, 2026-10-20):** with SOUND(YES) the screen before the first gameplay AID rings the
  START bell, so its WCC is C7 instead of C3; C7 is C3 plus only the 3270 alarm bit (X'04'). After that AID TSO sends
  its normal blocking-read keyboard-restore record, the exact 2-byte Write `F1 C3`. The frozen inherited rule
  (zos6_live_check.parse6) classifies that record as a TSO control only when the previous screen's WCC is exactly C3,
  so in S1 it stayed a game write and the checker reported FUNCTIONAL FAIL at gameplay AID 1 (a tooling false
  negative). ZOS-8 tooling only (zos8_live_check.sound_c3_controls / parse8, used for the sound cases S8A / S8B / S8C):
  in that one context the previous WCC may be exactly C3 or C7 (c3_alarm_equiv: only the alarm bit is ignored); the
  record itself must still be exactly 2 bytes `F1 C3`, directly after the AID, the AID the last kept event, at most
  one per AID, and the model must still match every other write (a control cannot replace a modelled write). All
  other context restrictions are unchanged; the frozen ZOS-5 / 6 / 7 tooling was not modified. Section 25: C3 / C7
  pass, the live S1 shape passes (the old rule missed it), wrong bytes / length, duplicate, outside the AID context,
  any other WCC (every single-bit flip but the alarm bit, every other Cx), a second control for one AID, other short
  writes and a control replacing a real write fail; SOUND(NO) and TURN results unchanged. The original S1 FAIL
  output is preserved unchanged (stageE-S1-S8A/zos8-S8A-check.txt); S1 was accepted by one offline re-evaluation of
  the same preserved live trace with the corrected ZOS-8 checker (zos8-S8A-check-CORRECTED.txt, PASS rc 0); no live
  retry was performed. S2 S8B and S3 S8C PASS live; audible bells confirmed by the operator in all three cases.
- **Stage F case frozen (user decision 2026-10-20, option A; supersedes "one eligible game" in section 12):** the
  production first write is case SF = LIVEB, exactly the validated HL2 cards (tests/zos8live/HL2.txt, 77 commands,
  no second card file: zos8_scen.LIVE_ALIAS), ARCADE, LEVEL 1, TURN, through the installed CLIST(PACMAN):
  `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) PLAY(TURN) ANIM(NO) SOUND(NO) PRESENT(COALESCED)'` (the CLIST allocates
  PACHS = Z00000.PACMAN.DATA(HISCORE) for ARCADE). Pre-state: DATA exists with its approved attributes and no
  member. Expected: HSRD finds HISCORE absent; the game ends with score 980 / level 1 and the high-score lines
  `HIGH SCORE 0000980 LEVEL 001` and `NEW HIGH SCORE` (PACHSIO REPL + STOW creates the member); post-state: exactly
  one member HISCORE with exactly one FB 80 record `0000980 PACHS001 001` (blank-padded to 80, zos8_scen.SF_RECORD),
  no other member, attributes unchanged. Chosen because it uses exactly the Stage F keywords (no GHOSTS(3)), was
  proven live in Stage C (HL2), has a known NEW HIGH SCORE path, broader coverage than DIE1, a deterministic record,
  and exercises the missing-member REPL / STOW first-write path. DIE1 / GPAI0 are not substitutes. Tooling (ZOS-8
  only): zos8_drive plan SF (the TURN plan of the cards); zos8_live_check: SF requires `--before ABSENT`, the exact
  frozen lines (and the model still giving them), no NOT SAVED / UNAVAILABLE, and `--sf-store` (check_sf_store: no
  member before; exactly HISCORE after; exactly one record = SF_RECORD in the text view and in the 80 binary bytes;
  attributes unchanged). Section 25: SF positive; 11 game faults (score, level, NEW missing, NOT SAVED, UNAVAILABLE,
  HISCORE present before, changed / missing write, other keywords, a test CLIST, model drift) and 10 production-state
  faults fail. Run once; no retry, repair, delete or overwrite of HISCORE afterwards.
