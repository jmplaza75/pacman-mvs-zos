# ZOS-10 Release - release design (Z10-A .. Z10-D) - APPROVED 2026-10-20; release preparation done locally

Status: design APPROVED by the user (2026-10-20) with decisions 1-3 and refinements (section 19). Release preparation
implemented locally (Z6, guards, tools/zowe/zos10_release.py, tests/test_zos10.py, decks jcl/zos/PACZ10*.jcl) and
committed as the release-preparation commit (the build's source provenance). Host execution NOT yet authorised: no
z/OS access, no upload, no job, no build, no install, no c3270 so far.
Baseline: branch `zos`, HEAD = tag `zos-9` = 885c12b; `zos-8` =
32d99f2; MVS reference `2.0-mvs-max` = 94fd6f6. Production state carried: `Z00000.PACMAN.DATA(HISCORE)` = one FB 80
record `0000980 PACHS001 001`.

ZOS-10 is release engineering, not equivalence (ZOS-9 proved equivalence, docs/evidence/zos9-equivalence.md). It
answers: can the accepted source be built cleanly and reproducibly, validated as a candidate, installed safely with the
frozen DEC-2 CLIST default, verified as installed, with production state preserved, and frozen as `2.0-zos`.
Sequence: BUILD candidate -> VALIDATE candidate -> INSTALL -> VERIFY installed -> FREEZE.

---------------------------------------------------------------------------------------------------------------------

## 1. Scope (exact)
In: (1) a clean rebuild of the 13 production modules from the release commit's sources into a fresh release area;
(2) candidate validation (build gate, object equivalence, line-mode / 1.0 oracle, presentation paths, CLIST PARMs);
(3) one production source change: **Z6 = the DEC-2 CLIST default** (`PRESENT(EVERY)` -> `PRESENT(COALESCED)` in the
PROC statement + its two help lines), nothing else; (4) promotion of LOAD(PACMAIN) and CLIST(PACMAN) with a rollback
copy; (5) installed verification (batch line mode / 1.0 oracle, one live REALTIME smoke); (6) release material, README
z/OS section, final evidence, tags `zos-10` and `2.0-zos`.
Out: any COBOL / copybook / assembler change; PACMAIN's low-level PARM rule (absent column 26 = EVERY, unchanged);
any equivalence battery; HA6, Stage F, ZOS-5..8 live reruns; METRICS(YES); DATA changes of any kind; a remote / push.

## 2. Z10-A - zos-9 -> release invalidation map
| Release change | What it could invalidate | Exactly what verifies it | Not invalidated (why) |
|---|---|---|---|
| Clean recompile / reassembly / rebind of unchanged sources (same compiler 6.5.0 P260714 if unchanged, same profile A options, same HLASM R6.0, same binder options) | the binary-level identity of every behaviour proven on PACZ6D (ZOS-6..9) and PACZ2D (ZOS-2..5, valid by non-interference) | (a) build gate (RC / attributes, section 6); (b) **object equivalence**: each new object = the accepted object of the installed build (build/zos/Z6POST, 13 images, SHA-256 recorded at ZOS-6) apart from compile date / time fields (section 5.4); (c) candidate batch runs CV1 / CV2 | if (b) holds for all 13 modules, the rebuilt program contains the same code as the tested PACZ6D, so all ZOS-2..9 behavioural evidence carries over unchanged; CV1 / CV2 are then confirmation and the carried line-mode check |
| Compiler / assembler / binder service level changed since 2026-10-19 (site maintenance) | object identity | the listing banners vs P260714 / R6.0; (b) fails -> STOP | - |
| Z6 CLIST default PRESENT(COALESCED) | the user-facing default PARM: REALTIME presentation path chosen without an operand; TURN PARM gains column 26 = C | CLIST PARM test (CLT, section 9.3), local CLIST interpreter tests, live smoke S10 (default path, no PRESENT operand) | TURN with column 26 = C is already the live-proven configuration (ZOS-7 L1, ZOS-8 HL1-HL8, GD, S8C, SF); PACMAIN reads REQ-PMODE only in PSLT (REALTIME); EVERY stays selectable and is the unchanged program default |
| Promotion (IEBCOPY of the candidate, CLIST replace) | installed = candidate | IEBCOPY messages, member attributes, CLIST binary compare, installed batch smoke P1 | - |
| Release documentation / version | nothing executable | review | - |
Not a release change: CEEOPTS dataset, DATA, LOAD(PACZ6D) / PACZ2D (kept), every ZOS-5..9 tool, model and oracle.

## 3. Final source inventory (release set)
| Library | Members (release commit) | Notes |
|---|---|---|
| COBOL (10) | PACMAIN, PACGAME, PACMAP, PACAI, PACINPT, PACDISP, PACPLAT, PACSCR, PACQRY, PACRT | src/cobol (Z1 + Z4 included) |
| COPY (6) | PACARC, PACDS, PACMREQ, PACPAL, PACREQ, PACSTATE | src/copy (Z4: PACREQ) |
| ASM (3) | PACTSO, PACFSIO, PACHSIO | src/asm (= 2.0-mvs-max; C3 accepted) |
| CLIST (1) | PACMAN | src/zos/PACMAN.clist (Z2 + Z3 + Z5 + Z6), rendered with prefix Z00000.PACMAN |
Excluded and never uploaded to the release area or bound: src/cobol/PACHELLO (toolchain hello), PACQRYT / PACTSOT
(test drivers), src/cobol/alt/PACDSPX, everything in src/probe (incl. PACRPE, RPESTAE, PACZ6P, ZHELLO*), src/clist
(the MVS CLIST), tests/, tools/, models, fixtures. Proof: the release inventory is an explicit list in the release
tool (not a glob); the build deck compiles exactly these 13 members and the binder INCLUDEs exactly their 13 objects
(asserted locally and on the binder listing: 13 IEW2322I INCLUDE lines, ENTRY PACMAIN); LOAD(PACRPE) and
CLIST(RPESTAE) stay test members of the existing libraries and are not referenced by any ZOS-10 deck.

## 4. Release datasets (prefix Z00000.PACMAN.RZ, as planned in plan sec. 7 / 14; safest: new, empty, separate from
the installed libraries, nothing existing is rewritten until promotion)
| Dataset | DSORG | RECFM / LRECL / BLKSIZE | Space (dir) | Members | Role |
|---|---|---|---|---|---|
| Z00000.PACMAN.RZ.COBOL | PO (PDSE, DSNTYPE=LIBRARY) | FB 80 27920 | TRK (15,15,10) | 10 | release source (final) |
| Z00000.PACMAN.RZ.COPY | PO (PDSE) | FB 80 27920 | TRK (5,5,10) | 6 | release source (final) |
| Z00000.PACMAN.RZ.ASM | PO (PDSE) | FB 80 27920 | TRK (5,5,10) | 3 | release source (final) |
| Z00000.PACMAN.RZ.OBJ | PO (PDSE) | FB 80 27920 | TRK (30,15,10) | 13 | build objects (final, evidence) |
| Z00000.PACMAN.RZ.LOAD | PO (PDSE program objects) | U 32760 | TRK (45,15,10) | PACMAIN | release program (candidate -> final build of record) |
| Z00000.PACMAN.RZ.CLIST | PO (PDSE) | FB 80 27920 | TRK (2,2,10) | PACMAN | release CLIST (production-prefix render; candidate -> install source) |
| Z00000.PACMAN.PRV.CLIST | PO (PDSE) | FB 80 27920 | TRK (2,2,10) | PACMAN | rollback copy of the zos-9 installed CLIST (made by PACZ10PV before PACZ10IN) |
Attributes copy the ZOS-1 allocation of record (jcl/zos/PACZALLO.jcl), DISP=(NEW,CATLG,CATLG), SMS-managed volume (no
VOL / UNIT coded, as ZOS-1). Precondition: none of these exists (read-only catalog check); if one exists -> STOP (no
delete, no reuse). No RZ.DATA / RZ.CEEOPTS: the candidate is never run through a CLIST, so it can never allocate any
DATA. Existing members written outside RZ / PRV: Z00000.PACMAN.Z4CL.T1(Z10P) (CLIST PARM test copy, existing test PDS,
new member); at promotion LOAD(PACMAIN) and CLIST(PACMAN) (replace). Never touched: DATA, CEEOPTS, LOAD(PACZ6D),
LOAD(PACZ2D), every other existing member, Z00000.ZHEIST.*. No DELETE, no purge anywhere.

## 5. Clean-build strategy
1. Allocation job PACZ10AL (IEFBR14, the six RZ datasets) after the read-only "none exists" check.
2. Upload the 19 release source members from the release commit to RZ.COBOL / COPY / ASM with IBM-037 and verify each
   by binary download = local fixed-80 records (the ZOS-1 upload / verify routine, explicit release inventory).
3. Read-only: RZ.OBJ and RZ.LOAD have no member.
4. Build PACZ10BL: the generated PACZ2BLD structure (make_deck --target zos, chunk Z2BLD rendering) with prefix
   `@@HLQ@@.PACMAN.RZ` and load name PACMAIN: COB1..COB10, ASM1..ASM3, LINK; SYSLIB = RZ.COPY only; objects to RZ.OBJ;
   binder INCLUDE RZ.OBJ(13 members) + SYSLIB SCEELKED (LE only; no project library in any SYSLIB); NAME PACMAIN(R)
   into RZ.LOAD; compiler work files CYL,(1,1) for every compile (the PACZ6BLD JOB09327 B37 lesson). Build steps
   COND=(4,LT) (as every accepted build: RC 4 tolerated by JCL only for the known PACFSIO warning); any step RC >= 8
   skips the bind. The job is judged by the exact per-step table (section 6): any other RC 4 or diagnostic = REJECTED
   candidate (never promoted; no rebuild without a decision).
   Clean proof: RZ.OBJ was empty before the job and is written only by it (13 members afterwards, exactly the release
   names); the binder listing shows exactly 13 INCLUDE OBJ(...) of RZ.OBJ and no other input; old Z00000.PACMAN.OBJ
   members cannot be reached (not in any DD of the job).
5. **Object equivalence (local, read-only download of RZ.OBJ in binary)**: every new object compared with the accepted
   image of the installed build (build/zos/Z6POST, SHA-256 in obj-sha256.json): COBOL GOFF records and HLASM 80-byte
   records equal except the bytes holding the compile date / time (located from the job's own listing timestamps and
   the old object's; any other differing byte -> NOT EQUIVALENT). Result per module IDENTICAL-MODULO-TIMESTAMP or
   DIFFERENT. All 13 identical = the rebuilt program is the tested program. Any DIFFERENT -> STOP (classify: compiler
   service change, option drift, source difference); further verification needs a new decision.

## 6. Build profile and gate (unchanged profile A, D45)
COBOL IGYCRCTL 6.5.0 (P260714 expected): `RENT,RMODE(24),DATA(24),NODYNAM,TRUNC(STD),NUMPROC(NOPFD),NOSOURCE,NOXREF`
(site defaults otherwise, as every accepted build: ARITH(COMPAT) / codepage / NOSSRANGE as reported in the listings).
HLASM ASMA90 R6.0: `OBJECT,NODECK,PCONTROL(NOGEN),NOXREF,...` (zos_target ASM_PARM). Binder IEWBLINK
`LIST,AMODE=24,RMODE=24,RENT`. Runtime LE `ALL31(OFF),STACK(,,BELOW)` (CEEOPTS: decks in-stream, CLIST via
Z00000.PACMAN.CEEOPTS, unchanged).
Gate (all required): COB1..COB10 RC 0000, no IGY message above informational; ASM1 PACTSO RC 0, ASM3 PACHSIO RC 0, no
statement flagged; ASM2 PACFSIO RC 4 with **exactly the C3 policy**: ASMA303W on `USING ABEXIT,15` as the only flagged
statement (+ its ASMA435I locator) and `S 12,ABOFF` assembled with base R15 (5BC0 F014); any other assembler
diagnostic -> STOP. LINK RC 0, severity 4/8/12/16 NONE, no unresolved external; SAVE MODULE ATTRIBUTES AMODE 24,
RMODE 24, RENT YES, REUS YES, EXCEEDS 16MB NO; entry point PACMAIN; NAME PACMAIN in RZ.LOAD. C3 is not reopened.

## 7. Release-candidate naming
Candidate = Z00000.PACMAN.RZ.LOAD(PACMAIN) + Z00000.PACMAN.RZ.CLIST(PACMAN). After the gates it is the build of record
(as MVS R20.LOAD(PACMAIN)); the installed copies are LOAD(PACMAIN) / CLIST(PACMAN). Job names PACZ10AL, PACZ10BL,
PACZ10C1, PACZ10C2, PACZ10CL, PACZ10PV, PACZ10IN, PACZ10P1.

## 8. Z6 - the DEC-2 CLIST default (production change, branch zos only; Z-entry Z6) - option O-C (approved)
`src/zos/PACMAN.clist` (diff in section 19.1): PROC `PRESENT(EVERY)` -> `PRESENT(AUTO)`; the two PRESENT help lines ->
three; after the Z5 statement `SET &E = &SUBSTR(1:1,&PRESENT)` one comment and one statement
`IF &PRESENT = AUTO AND &Y = R THEN SET &E = C` (&Y = the PLAY letter the CLIST already sets). The Z5 statements stay
byte for byte; only the default selection changes (no parser change):
- AUTO (no PRESENT operand) + PLAY(REALTIME) -> C -> PARM column 26 = C (COALESCED);
- AUTO + PLAY(TURN) -> no column 26: the historical 25-column 2.0 TURN PARM (unchanged);
- explicit COALESCED -> C (any PLAY, the Z5 behaviour kept); explicit EVERY -> no column 26;
- any other value -> no column 26 (the Z5 fallback EVERY; only the exact value AUTO is AUTO);
- PACMAIN unchanged: an absent column 26 still means EVERY.
Statement forms already used by the CLIST (`IF .. AND .. THEN`, Z3; `IF &v = literal THEN SET`, 2.0). Lines <= 71
columns with either prefix. Guards: tests/zos_c2.py Z6_* + z6_strip (exact; required by the guard; applied first by
z5_strip, so test sections 14 / 18 are unchanged); test section 22 reads the ZOS-6 text via z6_strip; sections 24 / 25
check the CLIST as z6_strip(current) = its zos-6 / zos-7 text (section 19.6). docs/ZOS-DIFFS.md: Z6.

## 9. Verification design
### 9.1 Pre-install candidate tests (all batch; candidate = RZ.LOAD(PACMAIN), STEPLIB RZ.LOAD, no PACHS / DATA)
| Id | Requirement verified | Why earlier evidence is insufficient | Content | Expected | Checker | App / spool lines |
|---|---|---|---|---|---|---|
| BL | clean build, attributes, C3 policy | new build | PACZ10BL | section 6 table | build checker + zos_compile_report | - / ~3,300 (PACZ2BLD: 3,266) |
| OE | rebuilt code = tested code | new objects | local compare RZ.OBJ vs Z6POST | 13 IDENTICAL-MODULO-TIMESTAMP | new local tool | (no job) |
| CV1 | **line mode / 1.0 oracle on the rebuilt artifact** (ZOS-9 carry) | line mode never ran after a rebuild | PACZ10C1: oracle 307 RUN1 (MOVES), RUN6 (DIE1), TSO1..TSO6 (line-mode transcripts) | each = own oracle 307 block + test_mvs8 model | zos_equiv --subset + zos_classic_check model | 2,572 / ~2,850 |
| CV2 | presentation paths of the rebuilt binary before install | new binary | PACZ10C2: oracle 310 RTT2 (EVERY TSD; = ZOS-6 E2), ZOS-6 N1 (COALESCED NORMAL TSD with bells, model), oracle 311 G3T7 (ARCADE TURN TSD, SOUND(YES)) | each exact (oracle and / or frozen model) | zos_equiv + zos6_dry / zos9_equiv comparators | 1,163 / ~1,300 |
| CLT | Z6 CLIST PARMs | new CLIST | PACZ10CL: test copy of the release CLIST (identical through the PARM build, then `WRITE Z10PARM=<&P>`, no CALL, no ALLOC of PACHS: RULES(CLASSIC) cases) in Z4CL.T1(Z10P), IKJEFT01 | see 9.3 | expected-PARM compare | - / ~150 |
### 9.2 Post-install tests
| Id | Requirement verified | Why needed | Content | Expected | DATA effect | 3270 |
|---|---|---|---|---|---|---|
| IN-check | installed = candidate | promotion | read-only: LOAD(PACMAIN) attributes = RZ.LOAD(PACMAIN) (size, AMODE / RMODE, RN RU); CLIST(PACMAN) binary = release render; PRV.CLIST(PACMAN) = zos-9 render | equal | none | no |
| P1 | **installed line mode / 1.0 oracle** after the clean rebuild (ZOS-9 carry) | installed member | PACZ10P1: PGM=PACMAIN from Z00000.PACMAN.LOAD: RUN1, TSO2 (DIE1 line mode), TSO6 (TSORDR) | = oracle 307 blocks and = the CV1 outputs | none (no PACHS) | no |
| S10 | installed CLIST default selects COALESCED; rebuilt PACMAIN starts, interacts through the accepted REALTIME path, returns to the shell | Z6 is new; the binary is new | one live game, section 9.4 | checker PASS | **none (RULES(CLASSIC): no PACHS allocation)** | yes |
### 9.3 CLIST PARM matrix (PACZ10CL; every case RULES(CLASSIC): the high-score block is never entered)
| # | Operands | Expected PARM (= the 2.0 MVS CLIST PARM + column 26) |
|---|---|---|
| 1 | `RULES(CLASSIC)` (default invocation: REALTIME) | `TSO AI1 1 NAAAPAAARAC01NPC` |
| 2 | `RULES(CLASSIC) PLAY(REALTIME)` | `TSO AI1 1 NAAAPAAARAC01NPC` |
| 3 | `RULES(CLASSIC) PLAY(REALTIME) PRESENT(COALESCED)` | `TSO AI1 1 NAAAPAAARAC01NPC` |
| 4 | `RULES(CLASSIC) PLAY(REALTIME) PRESENT(EVERY)` | `TSO AI1 1 NAAAPAAARAC01NP` (25 columns) |
| 5 | `RULES(CLASSIC) PLAY(TURN)` | `TSO AI1 1 NAAAPAAATAC01NP` (historical TURN PARM, no C) |
| 6 | `RULES(CLASSIC) PLAY(TURN) PRESENT(COALESCED)` | `TSO AI1 1 NAAAPAAATAC01NPC` (explicit value kept) |
| 7 | `RULES(CLASSIC) PLAY(TURN) PRESENT(EVERY)` | `TSO AI1 1 NAAAPAAATAC01NP` |
| 8 | `RULES(CLASSIC) PRESENT(XYZ)` | `TSO AI1 1 NAAAPAAARAC01NP` (invalid -> EVERY) |
| 9 | `RULES(CLASSIC) PRESENT(ABC)` | `TSO AI1 1 NAAAPAAARAC01NP` (only exact AUTO is AUTO) |
| 10 | `AI(0) RULES(CLASSIC) SOUND(NO)` (the S10 invocation) | `TSO AI0 1 NAAAPAAARNC01NPC` = the accepted ZOS-6 R1 PARM |
Expected values are computed by the release evaluator (zos10_release.clist_parm), which agrees with the frozen
section-22 evaluator on the ZOS-6 CLIST; each = the 2.0-mvs-max CLIST PARM of the same operands plus the matrix column.

### 9.4 Live smoke S10 (the only live action)
- Invocation (ISPF option 6, c3270 `-model 2 -oversize auto`, 120 x 30, user logged on manually):
  `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) SOUND(NO)'` - no PLAY (REALTIME default), no PRESENT.
- Gameplay: the frozen ZOS-6 R1 plan (cards, waits, pause, PA2, Q), driven by the frozen zos6_drive plan with only the
  command string replaced; checked by the frozen zos6_live_check rules with present = C (a ZOS-10 wrapper passes the
  plan copy; no frozen tool edited, as ZOS-8 did for the ZOS-7 plans).
- Expected: game writes = the canonical COALESCED model (stride 2), the R1 end lines, F1 C3 control records as
  accepted, `***`, closure ENTER, ISPF Command Shell. If the default had not applied (EVERY) the writes would be one
  per quantum / input blocked -> FUNCTIONAL FAIL.
- Timing: the frozen R1 gates are applied as they are; a gate miss classified ENVIRONMENT / TIMING BLOCKED is a STOP
  for a decision, not a product verdict; no new timing characterisation.
- DATA effect: none - RULES(CLASSIC) never runs the CLIST HS block (no PACHS allocation) and PACMAIN never calls
  HSRD / HSWR for CLASSIC (D38; ZOS-8 GD / S8C). Duration ~3 min.
- Not proposed: a TURN full-screen smoke (TURN + C already live-proven, TURN TSD in CV2 G3T7, line mode in CV1 / P1);
  a live line-mode game (batch TSO transcripts are the line-mode reference, D18); the plan's "CLIST with no operand,
  scenario G8 twice" - **that is ARCADE LEVEL 1 and its MVS score was 1050 > 980: it would rewrite production
  HISCORE** (superseded, section 12); ARCADE LEVEL(2) (option O-A in section 15, reads DATA, never records).

## 10. Production HISCORE protection (proof)
- Batch jobs AL, BL, C1, C2, CL, PV, IN, P1: no PACHS DD, no DSN containing `.DATA` (deck audit, fail closed, + the
  zos_submit audit). CLT runs only RULES(CLASSIC) cases: the HS block (`IF &W = A`) is never entered, so not even an
  ALLOC of DATA happens.
- Live S10: RULES(CLASSIC): no PACHS allocation, no HS I/O - writing HISCORE is impossible by construction, not by a
  score kept below 980.
- No ARCADE LEVEL 1 game anywhere in ZOS-10; no Stage F; DATA never deleted / recreated / reset.
- Evidence: one read-only DATA(HISCORE) member read at closure (the release exit criterion), expected `0000980
  PACHS001 001`, attributes unchanged.

## 11. Installation and rollback
Promotion gate (all PASS before PACZ10IN, else it never runs): PACZ10AL; source upload byte verification; PACZ10BL gate;
object equivalence 13 / 13; PACZ10C1; PACZ10C2; release CLIST uploaded to RZ.CLIST(PACMAN) and byte-verified; PACZ10CL;
provenance gate (read-only: LOAD(PACMAIN) directory attributes = LOAD(PACZ6D)'s, incl. size; AMODE / RMODE 24; PACZ6D
present - the installed PACMAIN is the ZOS-6 promotion of PACZ6D, JOB09499); rollback copy PACZ10PV verified.
1. **PACZ10PV** (rollback copy, before any replacement): PRV1 IEBCOPY CLIST(PACMAN) -> new Z00000.PACMAN.PRV.CLIST
   (SELECT MEMBER=PACMAN, no replace). Then read-only: PRV.CLIST(PACMAN) bytes = the pre-release installed CLIST
   (downloaded before PV). State after PV: nothing installed changed.
2. **PACZ10IN** (two IEBCOPY steps, not atomic): PROM1 RZ.LOAD(PACMAIN) -> LOAD(PACMAIN) replace; PROM2 (COND=(0,NE))
   RZ.CLIST(PACMAN) -> CLIST(PACMAN) replace.
   | Outcome | Installed state | Action |
   |---|---|---|
   | PROM1 fails | zos-9 state (PACMAIN, CLIST unchanged); PROM2 skipped | STOP, classify; nothing to roll back |
   | PROM1 OK, PROM2 fails / skipped | new PACMAIN (object-equivalent to PACZ6D) + zos-9 CLIST (PRESENT default EVERY) - a valid zos-9-equivalent configuration, but a PARTIAL promotion | STOP + rollback decision (no automatic retry) |
   | both OK | release installed | IN-check, then P1 |
   The two-member promotion is not atomic; each step's result is checked (IGW01552I copied and replaced, IGW01550I 1 of
   1, highest severity 0).
Rollback (only on a decision; no deletion): PACMAIN <- LOAD(PACZ6D) (the PACZ6INS JOB09499 procedure; PACZ6D is never
written by ZOS-10); CLIST(PACMAN) <- PRV.CLIST(PACMAN) (IEBCOPY replace). RZ.*, PRV.CLIST, PACZ6D, PACZ2D stay.

## 12. Earlier items assigned to ZOS-10 and how they close
| Item (source) | Closure |
|---|---|
| PRESENT release default (ZOS-6..9, DEC-2) | Z6 + CLT + S10 |
| Installed line mode / 1.0 oracle after the clean rebuild (ZOS-9) | CV1 (candidate) + P1 (installed) |
| HISCORE-aware release smoke (ZOS-9) | S10 is CLASSIC: no DATA contact; closure read-only check |
| Plan sec. 14.1 release_check zos mode | local: validate_source, test_zos10, the four guards, JCL audit of every ZOS-10 deck |
| Plan sec. 14.2-14.3 empty RZ libraries, upload + identity, build of record into RZ.LOAD(PACMAIN) | sections 4-6 |
| Plan sec. 14.3 run-only S2 / RP / GP2 / GP23 / HS on RZ | superseded by DEC-1 (ZOS-9): replaced by OE + CV1 + CV2 |
| Plan sec. 14.4 promotion, identity, installed checks, rollback in PRV | section 11, IN-check, P1 |
| Plan sec. 14.5 live smoke "no operand, G8 twice, HISCORE untouched" | superseded: G8 at LEVEL 1 would write HISCORE (1050 > 980); replaced by S10 |
| Plan sec. 14.6 release material, README z/OS section (authenticity rule, req. sec. 24 / 27) | section 13 |
| Plan sec. 14.7 annotated tag + post-tag read-only identity (as JOB 318) | section 16 (read-only state check before tagging) |
| HA6, full batteries (ZOS-3..7 -> "ZOS-9/10") | closed in ZOS-9 (composed evidence; DEC-1) - nothing in ZOS-10 |
| METRICS(YES) | approved out of scope (ZOS-9 DEC-4) |
| Requirements sec. 13 ZOS-7 "Release z/OS: regresion completa, README z/OS, documentacion de datasets y JCL, conservar release MVS" | ZOS-9 matrix + this release; README / releases/2.0-ZOS; releases/2.0-MVS-MAX untouched |

## 13. Version identification
No runtime banner or source string is added (no requirement asks for one; it would be a source change). `2.0-zos` is
exposed by: the Git tag `2.0-zos`; releases/2.0-ZOS/ (RELEASE-NOTES.md, MANIFEST.md = source SHA-256 of the release
set with the Z1-Z6 deltas vs 2.0-mvs-max, DEFAULTS.md incl. PRESENT(COALESCED), CAPABILITIES.md = ZOS-9 section 15,
decks/ = the ZOS-10 decks of record, SHA256SUMS); README.md z/OS section (install / build / use, what runs on z/OS vs
the client - authenticity rule). releases/2.0-MVS-MAX and the MVS CLIST stay unchanged.

## 14. z/OS actions in order, spool, writes, STOP criteria (each stage fail-fast)
| # | Action | Spool (est.) | Persistent writes | STOP if |
|---|---|---|---|---|
| 0 | local pre-host gate: HEAD = the release-preparation commit, clean tree, test_zos10 + guards, decks = generated | - | - | anything differs |
| 1 | read-only precheck (`--zos precheck`): the 6 RZ datasets and PRV.CLIST absent; LOAD has PACMAIN and PACZ6D; Z4CL.T1 exists and member Z10P absent; CEEOPTS exists | - | none | any condition false |
| 2 | PACZ10AL | ~60 | the 6 RZ datasets (empty) | RC != 0 |
| 3 | `--zos upload` (19 sources from the commit, byte-verified); RZ.OBJ / RZ.LOAD empty | - | RZ.COBOL 10, RZ.COPY 6, RZ.ASM 3 | any mismatch |
| 4 | PACZ10BL; `--check BL` | ~3,300 | RZ.OBJ 13, RZ.LOAD(PACMAIN) | gate fails (candidate rejected) |
| 5 | `--zos objects` (download RZ.OBJ), `--objeq build/zos/Z6POST <dir>` | - | none | any DIFFERENT / FORMAT |
| 6 | PACZ10C1; `--check C1` | ~2,850 | none | any step not exact |
| 7 | PACZ10C2; `--check C2` | ~1,300 | none | any step not exact |
| 8 | `--zos upload-clist` (RZ.CLIST(PACMAN), byte-verified); PACZ10CL; `--check CL` | ~300 | RZ.CLIST(PACMAN); Z4CL.T1(Z10P) (new member) | any PARM differs |
| 9 | `--zos provenance`; download the installed CLIST (pre-release image); PACZ10PV; `--check PV`; PRV byte check | ~70 | PRV.CLIST (new) + PACMAN | any failure |
| 10 | PACZ10IN; `--check IN` | ~140 | LOAD(PACMAIN), CLIST(PACMAN) replaced | any RC != 0 -> STOP + rollback decision |
| 11 | `--zos in-check` (installed = candidate, PACZ6D unchanged, PRV = pre-release CLIST) | - | none | not equal -> rollback decision |
| 12 | PACZ10P1; `--check P1 --cv1 <C1 spool>` | ~700 | none | not exact -> rollback decision |
| 13 | live S10 (the user logs on; trace; `--s10-drive`, `--s10-check`) | trace only | none | FUNCTIONAL FAIL -> rollback decision; TIMING BLOCKED -> STOP for decision |
| 14 | `--zos closure`: DATA(HISCORE) = `0000980 PACHS001 001`; installed state | - | none | HISCORE differs |
Every job submitted once through tools/zowe/zos_submit.py (render, audit, wait, spool). Failure: freeze the evidence,
classify (PRODUCT REGRESSION / BUILD-TOOLCHAIN / TOOLING-CHECKER / ORACLE-ANCHOR / PLATFORM-ENVIRONMENT /
OPERATOR-JOB-CONSTRUCTION / APPROVED DIFFERENCE), STOP; no automatic retry, rebuild, source / oracle / model change.

## 15. Decisions (user, 2026-10-20)
1. S10 = CLASSIC, `AI(0) RULES(CLASSIC) SOUND(NO)`, no PLAY / PRESENT (safe by construction). The old G8 release smoke
   is formally superseded for safety (ARCADE LEVEL 1, MVS score 1050 > 980 would rewrite HISCORE); ARCADE LEVEL(2)
   rejected (CLASSIC never enters the high-score path).
2. CV2 always runs (object equivalence is supporting evidence, not the sole behavioural check).
3. Z6 option O-C: COALESCED by default for PLAY(REALTIME) only; TURN default PARM historical.

## 16. Final evidence, commits and tags
docs/evidence/zos10-release.md: 1 result (ZOS-9 proved equivalence; ZOS-10 proves clean reproducible build,
installation and release configuration - different claims; ZOS-9 matrix referenced, not copied); 2 release set and
provenance (commit, source SHA-256); 3 datasets; 4 build (per-step RC, C3 policy, binder attributes, INCLUDE list);
5 object equivalence; 6 CV1 / CV2 / CLT; 7 promotion + rollback copy; 8 IN-check, P1, S10; 9 HISCORE preserved;
10 Z6; 11 deferred items closed (section 12); 12 exit criteria table.
Commits / tags: (a) one "ZOS-10 release preparation" commit before host work (Z6 CLIST + guards, release tool, decks,
tests, design) - so the release is built from a committed tree (provenance = that commit); (b) after all gates, one
closure commit (evidence, README, releases/2.0-ZOS, CURRENT_PHASE, DECISIONS); (c) annotated `zos-10` and annotated
`2.0-zos` both on the closure commit (phase closure and product release are the same final state; the release-prep
commit recorded as the build provenance). No push, no remote. Both commits / tags only on the user's approval.

## 17. Exit criteria
Clean build from the committed release set; all 13 objects rebuilt into the new RZ.OBJ; bind PASS with AMODE 24 /
RMODE 24 / RENT / REUS / not above 16 MB / entry PACMAIN; C3 policy exact; object equivalence 13 / 13 (or an explicit
decision); CV1, CV2, CLT PASS before promotion; promotion with the PRV rollback copy; installed = candidate (IN-check);
P1 (installed line mode / 1.0 oracle) PASS; S10 PASS (default PRESENT = COALESCED, normal return); explicit
PRESENT(EVERY) PARM unchanged (CLT); HISCORE = `0000980 PACHS001 001`; no unexplained regression; README z/OS section,
releases/2.0-ZOS, evidence complete; repository clean; closure commit; tags `zos-10` and `2.0-zos` only after all
gates.

## 18. Local files (release-preparation commit)
src/zos/PACMAN.clist (Z6); docs/ZOS-DIFFS.md (Z6 entry); tests/zos_c2.py (Z6 guard); tests/test_zos_tools.py (section
22: Z5 text via z6_strip; sections 24 / 25: the frozen-source pins allow exactly Z6 / RPESTAE, section 19.6);
tests/test_zos9.py (the same exact Z6 exclusion in its zos-8 source pin);
tools/zowe/zos10_release.py; tests/test_zos10.py; jcl/zos/PACZ10AL.jcl, PACZ10BL, PACZ10C1, PACZ10C2, PACZ10CL,
PACZ10PV, PACZ10IN, PACZ10P1 (.jcl); docs/zos10-design.md. At closure: docs/evidence/zos10-release.md, README.md,
releases/2.0-ZOS/*, docs/CURRENT_PHASE.md, docs/DECISIONS.md.

## 19. Release preparation (2026-10-20)
### 19.1 Z6 diff (src/zos/PACMAN.clist)
```
-  ALARM(PATTERN) PRESENT(EVERY)
+  ALARM(PATTERN) PRESENT(AUTO)
-/* PRESENT: EVERY (DEFAULT: ONE SCREEN WRITE PER REALTIME QUANTUM)  */
-/* OR COALESCED (ZOS-6, ZV-D33: A WRITE EVERY 2ND / 3RD QUANTUM).   */
+/* PRESENT: AUTO (DEFAULT: COALESCED WITH PLAY(REALTIME), NOTHING  */
+/* WITH TURN), COALESCED (ZOS-6, ZV-D33: A WRITE EVERY 2ND / 3RD    */
+/* QUANTUM) OR EVERY (ONE SCREEN WRITE PER REALTIME QUANTUM).       */
 SET &E = &SUBSTR(1:1,&PRESENT)
+/* Z6 (ZOS-10): PRESENT(AUTO) = COALESCED FOR PLAY(REALTIME) ONLY.  */
+IF &PRESENT = AUTO AND &Y = R THEN SET &E = C
 IF &E = C THEN SET &P = &STR(&P&E)
```
### 19.2 Job inventory and writes
| Job | Steps | Programs | Datasets named | Persistent writes |
|---|---|---|---|---|
| PACZ10AL | ALLOC | IEFBR14 | RZ.COBOL / COPY / ASM / OBJ / LOAD / CLIST | the 6 new datasets |
| PACZ10BL | COB1-COB10, ASM1-ASM3, LINK | IGYCRCTL, ASMA90, IEWBLINK | RZ.COBOL / COPY / ASM / OBJ / LOAD (+ system libraries IGY650.SIGYCOMP, CEE.*, HLA.SASMMOD1, SYS1.MACLIB / MODGEN) | RZ.OBJ 13 members, RZ.LOAD(PACMAIN) |
| PACZ10C1 | RUN1 RUN6 TSO1-TSO6 | PACMAIN | RZ.LOAD | none |
| PACZ10C2 | RTT2 N1 G3T7 | PACMAIN | RZ.LOAD | none |
| PACZ10CL | CLCPY, CLT | IEBGENER, IKJEFT01 | Z4CL.T1 (+ the test copy allocates CEEOPTS SHR, SYSIN / SYSOUT DA(*)) | Z4CL.T1(Z10P) |
| PACZ10PV | PRV1 | IEBCOPY | CLIST, PRV.CLIST | PRV.CLIST (new) + PACMAN |
| PACZ10IN | PROM1, PROM2 | IEBCOPY | RZ.LOAD, LOAD, RZ.CLIST, CLIST | LOAD(PACMAIN), CLIST(PACMAN) replaced |
| PACZ10P1 | RUN1 TSO2 TSO6 | PACMAIN | LOAD | none |
Audit (fail closed, every deck): exact job / steps / programs; exactly the datasets above; no PACHS DD, no `.DATA`, no
DELETE / SCRATCH / PURGE, no PACZ6D / PACZ2D / ZHEIST; run steps EXEC PGM=PACMAIN, STEPLIB of the right LOAD,
CEEOPTS profile A, DDs STEPLIB CEEOPTS SYSIN SYSOUT CEEDUMP SYSUDUMP; BL: each COBOL member compiled from RZ.COBOL
into RZ.OBJ with the profile A options and CYL work files, INCLUDE exactly the 13 objects, ENTRY / NAME PACMAIN, binder
`LIST,AMODE=24,RMODE=24,RENT`, no excluded member; PV / IN: the exact SELECT statements, PROM2 COND=(0,NE). The audit
found during implementation that zos_target.asm_step names <prefix>.ASM / .OBJ from a module global (not the deck's
prefix): the release tool pins that global to RZ while rendering (no frozen tool changed); the audit would refuse a
deck naming the old Z00000.PACMAN.ASM / OBJ.
CV1 / CV2 / P1 application lines (exact, from the frozen blocks / model): 2,572 / 1,163 (557 + 380 + 226) / 566.
### 19.3 Candidate / oracle / model mapping
| Job | Step | Oracle | Model |
|---|---|---|---|
| C1 / P1 | RUN1, RUN6, TSO1-TSO6 (P1: RUN1, TSO2, TSO6) | own oracle 307 block (zos_equiv anchor + block-end rule) | zos_classic_check.model (test_mvs8 MVS6 models / TSO transcript rules) |
| C2 | RTT2 | own oracle 310 block | zos6_dry E2 model (same PARM and cards, EVERY TSD) |
| C2 | N1 | - (a ZOS-6 dry-run step) | zos6_dry N1 model (COALESCED NORMAL TSD with bells) |
| C2 | G3T7 | own oracle 311 block | zos9_equiv G3T7 model (ARCADE TURN TSD, test_gp2 bells) |
P1 additionally = the C1 candidate output of the same steps, byte for byte.
### 19.4 Object-equivalence masks (exact; nothing else is tolerated)
Proof basis: the 13 accepted ZOS-6 images (build/zos/Z6POST, SHA-256 as recorded) inspected record by record.
- COBOL (Enterprise COBOL 6.5 GOFF objects, 80-byte records): exactly two spans per object, both in TXT records:
  (A) record type X'03 11', record offset 26..39: 14 EBCDIC digits YYYYMMDDHHMMSS immediately followed by the compiler
  level '0605'; (B) record type X'03 10', offset 42..54: 13 digits YYYYDDDHHMMSS immediately after the product id
  '5655EC6   ' and level '0605'. Each was found exactly once in each of the 10 accepted images (e.g. PACMAIN record 36
  '20261019094720', record 710 '2026292094720'). They are the compiler-generated compilation timestamp constants of
  the program signature area: data, never instructions, and read by no program logic (no WHEN-COMPILED / CURRENT-DATE
  in any source); only LE diagnostics display them.
- HLASM objects (80-byte ESD / TXT / RLD / END): exactly one END record; its IDR assembly date yyddd at offset 47..51
  (after translator id '569623400 ' and version '0106'); no time field; no assembly-time symbol (&SYSDATE / &SYSTIME)
  in any release assembler source.
- Rule: per object, same length, the spans found at the same positions in both images (exactly once each; else
  FORMAT -> STOP), the span bytes valid EBCDIC digits in both, and every byte outside the spans identical; any other
  difference -> DIFFERENT -> STOP. The masks are fixed in the tool and cannot be widened without a new approval.
### 19.5 S10 (exact)
`tools/zowe/zos10_release.py --s10-drive PORT LOG` / `--s10-check TRACE LOG`: the frozen zos6_drive / zos6_live_check
run in this process with the ZOS-6 plan R1 copied and only its operands replaced by `AI(0) RULES(CLASSIC) SOUND(NO)`
(case name R1, so every R1 rule applies: exactly one death, the freeze-span proxy, the frozen NORMAL gates; present C =
COALESCED expected). The resulting program PARM `TSO AI0 1 NAAAPAAARNC01NPC` is byte-identical to the accepted R1 PARM:
S10 runs the accepted R1 invocation, reached through the release defaults (PLAY default REALTIME, PRESENT default AUTO).
Timing gates as frozen; ENVIRONMENT / TIMING BLOCKED -> STOP for a decision.
### 19.6 Test adaptations and a pre-existing finding
- tests/test_zos_tools.py: section 22 reads the ZOS-6 CLIST text through z6_strip (approved); sections 24 and 25 pin
  `src` to zos-6 / zos-7 and now exclude exactly src/zos/PACMAN.clist, which they check as z6_strip(current) = the tag's
  text (required by Z6; not in the approved list - reported). tests/test_zos9.py pins `src` to zos-8 in the same way
  and gets the same exact Z6 exclusion (z6_strip(current) = the zos-8 text).
- Pre-existing defect found: section 24's pin (`git diff zos-6 -- src` empty) has failed since the ZOS-8 commit 32d99f2
  added the test CLIST src/probe/zos/RPESTAE.clist (section 25 already allowed it); it went unnoticed because ZOS-8 ran
  section 25 alone and ZOS-9 did not run this file. Section 24 now excludes RPESTAE as section 25 does. Section 25 had a
  second latent defect from the same commit: it split `git diff --name-only` output on whitespace, but the repository
  path contains spaces ('Pacman MVS and zOS/...'), so once RPESTAE was committed its allow-list check failed; it now
  reads the names line by line with `--relative`. Both reproduced on the unmodified zos-9 tree; no product impact.
