# ZOS-4 step 1 - interactive CEEOPTS discovery (manual TN3270 session, read-only)

Purpose: find which LE runtime options a program CALLed from the interactive TSO session would get, before PACMAIN is
installed or played. Nothing of Pac-Man runs. Nothing is changed: no PROFILE, SYSPROC, ALLOC / FREE or other
persistent setting.

## Before the session
- Optional (only if step 4 is needed): the read-only REXX `tools/zos4/SHOWCEE.rexx` must be on z/OS. It is NOT uploaded
  yet; uploading it creates one new project dataset `Z00000.PACMAN.Z4CEE.T1` (PDS FB 80, member SHOWCEE) and needs the
  user's go-ahead. The exec only runs LISTDSI and `EXECIO * DISKR` on the session's CEEOPTS DD: no write, no ALLOC, no
  FREE. If the user prefers, step 4 can be skipped when step 3 already names a permanent dataset (then it is read with
  a read-only Zowe query instead).
- Security: 198.51.100.200:623 is plain TN3270E (no TLS): the userid and password cross the network unencrypted. The
  password is typed only by the user; it is never written to a file, script, command line, chat or trace. No c3270
  trace or screen capture before READY.

## The session (the user at the keyboard)
1. Connect as in ZOS-0: `c3270 -model 2 -oversize auto 198.51.100.200:623`. At the Z Xplore welcome screen type
   `logon Z00000` and enter the password yourself.
2. Wait for `READY` (no ISPF on this logon). If any unexpected panel, message or security prompt appears: STOP, do not
   continue, log off (`LOGOFF`) and report it.
3. At READY type `LISTALC STATUS` and press ENTER (page with ENTER if the output continues, `***`). Copy the screen text
   from READY onwards (select and copy in the terminal window; no trace). What matters: the line(s) for DDNAME
   `CEEOPTS` - the dataset name above it and its disposition.
4. Only if step 3 shows CEEOPTS as a temporary / in-stream dataset (a name like `Z00000.Z00000.TSU.....` or
   `JES2.JOB....`), and only if SHOWCEE was uploaded: type `EXEC 'Z00000.PACMAN.Z4CEE.T1(SHOWCEE)'` and copy its
   output (`SHOWCEE ...` and `CEE> ...` lines).
5. Type `LOGOFF`. Do not run Pac-Man, any CLIST of the project or any other command.

## What the assistant does with it (postcheck, read-only)
- Records the CEEOPTS allocation and its contents in docs/evidence/zos4-ceeopts.md (no password, no session id beyond
  what the user agrees to keep).
- Compatible with profile A only if the effective options give `ALL31(OFF)` and `STACK(,,BELOW)`: stated explicitly in
  the CEEOPTS records (and not overridden as non-overridable elsewhere) -> record it, no change.
- If the records set `ALL31(ON)` or a stack location other than BELOW, or do not mention them (the installation
  defaults then apply, which this read cannot show; the z/OS default is ALL31(ON) with the stack anywhere): STOP and
  report the exact allocation and records. No CLIST CEEOPTS override and no PARM `/` runtime options are implemented
  without a separate review.
