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
