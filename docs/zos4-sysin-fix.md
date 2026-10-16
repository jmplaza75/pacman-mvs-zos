# ZOS-4 live STOP: interactive SYSIN record length - analysis and smallest fix proposal (for review; nothing changed)

## What happened (user, 2026-10-16; first DIE1 launch)
The installed CLIST (with Z2) reached PACMAIN under profile A; then Enterprise COBOL reported
`IGZ0201W` (PACINPT COMMAND-FILE expects record length 80, the file assigned to SYSIN has record length 120) and
`IGZ0035S` (unsuccessful OPEN of SYSIN, file status 39); the CALL ended with user abend 4038 and the EXEC terminated
abnormally. DIE1 = FAIL before the first frame; LOST0 = NOT RUN; no retry. (Z2 worked: the CALL was reached, so the
project CEEOPTS was allocated; profile A is not involved in this failure.)

## Why the interactive SYSIN is LRECL 120
- The only file PACMAIN opens with an FD is PACINPT `COMMAND-FILE` (`ASSIGN TO UT-S-SYSIN`, `RECORDING MODE IS F`,
  `RECORD CONTAINS 80 CHARACTERS`, `PIC X(80)`); SYSOUT is written by DISPLAY through LE, which adapts to the
  dataset (no FD, no record-length check).
- The CLIST allocates `ALLOC F(SYSIN) DA(*) REUSE`: a terminal data set with no DCB attributes; its record length is
  then taken from the terminal's line size. The session ran in c3270 `-model 2 -oversize auto` in a 120 x 30 window
  (ZOS-0 D): line size 120 -> SYSIN LRECL 120.
- Every batch run (ZOS-2 / ZOS-3, PACZ4INS smoke) read cards from `SYSIN DD *` (LRECL 80), so the mismatch never
  appeared. On MVS 3.8J the 1.0 / 2.0 COBOL (IKFCBL00) did not check the record length at OPEN; Enterprise COBOL
  does (file status 39 = fixed file attribute conflict). This is a TSO/E + Enterprise COBOL difference, not a game or
  profile issue.

## Options to present an 80-byte record to the unchanged COMMAND-FILE
| | Change | Effect | Proof needed | Notes |
|---|---|---|---|---|
| A (operational) | none: connect with an 80-column primary screen (`c3270 -model 2 198.51.100.200:623`, no -oversize) | terminal line size 80 -> SYSIN LRECL 80 | the live session itself | no product fix: any wider terminal (e.g. the 120 x 27 screens ZOS-5 needs) would hit the same abend in line mode |
| **B (recommended, Z3)** | CLIST: `ALLOC F(SYSIN) DA(*) REUSE LRECL(80) BLKSIZE(80) RECFM(F)` (one line; SYSOUT unchanged) | the terminal SYSIN gets the FD's fixed 80 attributes whatever the screen width | live, on the same 120-wide terminal that failed (the only environment that shows the effect; batch has no terminal) | smallest product fix; TSO/E ALLOCATE DCB operands on a terminal (DA(*)) allocation - their acceptance and effect are exactly what the live check proves; any IKJ message on that ALLOC = STOP |
| C | `TERMINAL LINESIZE(80)` before the EXEC (or in the CLIST) | session line size 80 | live | changes the user's session setting beyond the CALL; not recommended |
Not considered: COBOL / PACINPT changes, rebuild (excluded), RECFM V tricks.

## Proposed Z3 (not applied)
```diff
-ALLOC F(SYSIN) DA(*) REUSE
+ALLOC F(SYSIN) DA(*) REUSE LRECL(80) BLKSIZE(80) RECFM(F)
 ALLOC F(SYSOUT) DA(*) REUSE
```
src/zos/PACMAN.clist only (the 2.0 MVS CLIST stays frozen); Z2 and profile A unchanged; z2_guard extended to allow
exactly this line; install by the reviewed upload + binary identity (PACSRCT stays the template; the current
CLIST(PACMAN) replaced only after a read-only gate shows it is exactly the installed Z2 version).
Live proof (one session, same terminal geometry that failed, 120 wide): DIE1 then LOST0 exactly as approved; the
first frame of DIE1 is the discriminator (no IGZ0201W / IGZ0035S / U4038).

## Revision (user, 2026-10-16): Z3 approved in principle as ATTRIB + USING - review package, not installed
The inline `ALLOC ... DA(*) LRECL(80) BLKSIZE(80) RECFM(F)` above is **withdrawn**: TSO/E documents that for a terminal
allocation `DA(*)` only FILE / DDNAME, BLOCK / BLKSIZE and USING are processed, so LRECL / RECFM on that ALLOCATE are
not a reliable way to set the DCB. Z3 uses the documented attribute-list mechanism instead.

### The change (src/zos/PACMAN.clist; the 2.0 line `ALLOC F(SYSIN) DA(*) REUSE` becomes these 24 lines)
```
/* Z3 (ZOS-4): SYSIN FIXED 80 (PACINPT COMMAND-FILE) WHATEVER THE  */
/* TERMINAL WIDTH: ON DA(*) ONLY ATTRIB + USING SET THE DCB. THE   */
/* LIST IS FREED AT ONCE (ONLY IF CREATED HERE). FAILURE: RC 8.    */
SET &Z = 0
SET &T = 0
CONTROL NOFLUSH
ERROR DO
  SET &Z = &LASTCC
  RETURN
END
ATTRIB Z3SIATTR RECFM(F) LRECL(80) BLKSIZE(80)
IF &Z = 0 THEN DO
  SET &T = 1
  ALLOC F(SYSIN) DA(*) REUSE USING(Z3SIATTR)
END
SET &I = &Z
IF &T = 1 THEN FREE ATTRLIST(Z3SIATTR)
ERROR OFF
CONTROL FLUSH
IF &Z NE 0 THEN DO
  WRITE PACMAN: SYSIN NOT ALLOCATED (Z3, RC &Z), GAME NOT STARTED
  IF &T = 1 AND &I = 0 THEN FREE F(SYSIN)
  EXIT CODE(8)
END
```
Unchanged: `ALLOC F(SYSOUT) DA(*) REUSE`, the HS block, the PARM, Z2 (byte for byte: removing the Z3 block gives back
the 8724464 source that PACZ4INS installed), CEEOPTS, PACMAIN, every COBOL source.

### Design points
- Attribute-list name `Z3SIATTR`: 8 characters, not a Pac-Man DD name (SYSIN, SYSOUT, PACHS, CEEOPTS, STEPLIB),
  no `PAC` prefix, the `Z3` marks whose it is. An existing list / DD of that name makes ATTRIB fail -> the CLIST never
  frees it (it did not create it), RC 8.
- Lifetime: the list exists only between ATTRIB and the FREE right after the ALLOC (the attributes are taken at
  allocation time). So no later exit holds it: the Z2 failure exits, the normal return after the CALL and even an
  abnormal end of the CALL (as in session 1) leave no attribute list behind, and the Z2 lines need no change.
- Fail closed, same pattern as the accepted Z2 (CONTROL NOFLUSH + ERROR routine that records &LASTCC and RETURNs, then
  ERROR OFF / CONTROL FLUSH): any non-zero RC of ATTRIB, ALLOC or FREE ATTRLIST -> message, RC 8, before SYSOUT, the
  HS block, Z2 and the CALL.

| Outcome | Commands issued after ATTRIB | Result |
|---|---|---|
| all succeed | ALLOC SYSIN USING, FREE ATTRLIST | continue: SYSIN fixed 80, no list left |
| ATTRIB fails (e.g. the name in use) | - | message, RC 8; nothing freed (nothing created) |
| ALLOC fails | FREE ATTRLIST | message, RC 8; only the list freed |
| FREE ATTRLIST fails | (ALLOC done) | message, FREE F(SYSIN), RC 8 (the list cannot be removed: reported RC) |
| ALLOC and FREE ATTRLIST fail | - | message, RC 8 |
Known, unchanged from 2.0: `REUSE` may already have freed a previous SYSIN of the session when the ALLOC fails (the
2.0 CLIST always frees SYSIN at its end too; it never preserved one).

### Package (prepared; nothing uploaded or installed)
- `src/zos/PACMAN.clist` (the change); guard `tests/zos_c2.py` (`Z3_BLOCK` frozen; `z3_strip` puts the one line back and
  `z2_guard` proves every other line against 2.0-mvs-max).
- `tests/test_zos_tools.py` section 18: src/zos minus Z3 = the installed Z2 source (8724464; rendered = SHA-256
  2e9895dc..., the installed member); the diff is exactly `-SYSIN line` + the 24 lines; SYSOUT / Z2 untouched; lines
  <= 72; an independent control-flow model of the block over the 5 outcomes above (list freed iff created; RC 8 before
  SYSOUT / Z2 / CALL on any failure). Section 14 now compares the Z2 structure on the Z3-stripped text. All sections PASS;
  test_core_frozen, test_g8, validate_source PASS.
- `tools/zowe/zos_z3_install.py`: `--gate` (read-only: CLIST(PACMAN) = the installed Z2 member byte for byte and
  SHA-256, PACSRCT = template, CEEOPTS exact, PACMAIN / PACZ2D attributes) - **run 2026-10-16: PASS 7/7**; `--install`
  (the gate again, then one member uploaded with IBM-037 + binary download = rendered, then zos_ins_check --clist).
  Writes only `Z00000.PACMAN.CLIST(PACMAN)`; the previous (Z2) member is recoverable from git 8724464.
- Not covered before live: the failure rows of the table run only by the model (no batch job proposed: in batch
  `DA(*)` has no terminal, and forcing an ATTRIB / ALLOC failure on the host would need extra test allocations); the
  success row is what live session 2 proves. If wanted, a batch IKJEFT01 attempt for the "name in use" row can be
  prepared separately.

### After approval
1. `python3 tools/zowe/zos_z3_install.py --install` (gate, one member, binary identity, --clist check). STOP on any FAIL.
2. Live session 2 (docs/zos4-live-acceptance.md, "Session 2"): the same 120-column c3270 geometry that failed.
