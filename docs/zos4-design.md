# ZOS-4 CLASSIC - design / reconnaissance (for review; nothing submitted, no live session, no source change)

Base: tag `zos-3` (e624924). Process rule (user, 2026-10-15): one precheck, one execution / session, one focused
postcheck; reuse ZOS-2 / ZOS-3 oracle and model evidence; new tooling only for genuinely new behaviour.

## 1. Scope (migration plan sec. 5-6, ZOS-4)
First complete game on z/OS through the most conservative path: TSO line mode via the CLIST with
`RULES(CLASSIC) PLAY(TURN) COLOR(NO)`. Includes the first promotion (`Z00000.PACMAN.LOAD(PACMAIN)` +
`Z00000.PACMAN.CLIST(PACMAN)`), the CLIST PARM-line check (test_g8 CLIST block with the z/OS prefix) and, carried
from ZOS-3, the HS CLIST block. CLIST changed only by prefix substitution unless a TSO/E difference forces it
(Z-entry). Not in ZOS-4: colour / full screen (ZOS-5), REALTIME (ZOS-6), ARCADE (ZOS-7), live HS / ESTAE / alarm
(ZOS-8).

## 2. First live TSO behaviour
From TSO READY (correction 2026-10-15: the logon, procedure DBPROCDG, enters ISPF; READY through ISPF option 6 or
by leaving ISPF - ZOS-0 D had recorded READY directly):
`EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'RULES(CLASSIC) PLAY(TURN) COLOR(NO)'` playing a frozen card sequence typed by the
user, so the transcript has an exact reference: DIE1 (the 1.0 TSO oracle run, = PACZ2C7 TSO2 / PACZ3FS on z/OS:
moves, a blocked move, empty-ENTER redraw, death, Q -> READY), then LOST0 (a game to LOST). Checklist of the plan:
no `***` mid-frame; READY after each game; repeated from ISPF option 6 as the plan's compatibility note.

## 3. HS CLIST block
With RULES(CLASSIC) the block (`IF &W = A`) is skipped live, so it is proved in batch under the TMP, as on MVS
(HSCLS1/2 + HSCLT), without DELETE: the block text with a scratch prefix whose DATA exists (present path:
`ALLOC F(PACHS) DA('<p>.DATA(HISCORE)') SHR` -> LISTALC `PACHS KEEP`) and with a prefix whose DATA never existed
(missing path: `DUMMY` -> LISTALC `NULLFILE PACHS`); the MVS step deleted the dataset between the two, z/OS uses two
prefixes instead. Same assertions as tests/test_hs.py section 3 (no IKJ56xxx, `HSCL END` twice). The real
`Z00000.PACMAN.DATA` is not touched; live ARCADE high score is ZOS-8.

## 4. Services observable for the first time
| Service | Batch / IKJEFT01 so far | First real use in ZOS-4 |
|---|---|---|
| TSO detection (ASCBTSB) | always 0 (RC 4 paths) | non-zero: the TSO paths really issue SVCs |
| PACTSO CLS (STLINENO LINE=1) | RC 4, nothing issued | real STLINENO before every frame: the `***` avoidance (D20) |
| Terminal SYSIN / SYSOUT (`ALLOC DA(*)`) | cards / spool | QSAM to and from the terminal: prompts, typed input, D19 input rules |
| CLIST: &SYSDSN, ALLOC / FREE, CALL of a PDSE program object, PARM build | HTSO: TMP CALL only | the installed CLIST end to end |
| LE runtime options under the interactive logon proc | CEEOPTS DD in the JCL | see 6.1: the logon proc allocates a site CEEOPTS |
Not reached in ZOS-4: PACFSIO (COLOR(NO)), PACHSIO (CLASSIC), PACTSO TIME / DLWT / WAIT (TURN line mode).

## 5. IKJEFT01 batch versus interactive TSO
- IKJEFT01 batch (ASCBTSB = 0): CLIST logic (PROC defaults, PARM build, &SYSDSN, ALLOC / FREE / LISTALC), the HS
  block, CALL of PACMAIN. Already proved: PACZ3HS8 HTSO1/2 (TMP CALL of PACZ2D, SYSIN / SYSOUT DDs).
- Interactive only: the TSB paths (STLINENO, terminal I/O through DA(*)), the `***` behaviour, the logon proc's
  allocations (CEEOPTS), READY after the CALL.

## 6. Minimum sequence
0. Local: render the CLIST for `Z00000.PACMAN` (prefix substitution only; defaults = 2.0; lines <= 72); decks; test.
1. **Precheck (read-only, Zowe):** LOAD has no PACMAIN, CLIST has no PACMAN (first promotion: nothing to save to
   `PRV`; if either exists, STOP and copy to PRV first per plan sec. 2); the scratch T1 names below do not exist.
   6.1 **Open question - decide before the live session:** the interactive logon proc allocates a site CEEOPTS
   (ZOS-0 B7 saw it for IZUFPROC; the 3270 logon proc is not yet characterised). Without Profile A, LE would apply
   the site / installation options (z/OS default ALL31(ON), stack anywhere) to an AMODE 24 program. Options:
   (a) read-only discovery first: the user, at READY in one short session, issues `LISTALC STATUS` and shows the
   CEEOPTS contents (a read-only REXX `EXECIO` display placed in a T1 work PDS) - then decide;
   (b) a Z-entry in the CLIST: allocate a project CEEOPTS dataset (`ALL31(OFF),STACK(,,BELOW)`) before CALL; it would
   replace the session's site allocation (side effect on the user's own session) and changes the 2.0 CLIST;
   (c) runtime options in the CALL PARM after `/` - precedence against a CEEOPTS DD to be verified first.
   Recommendation: (a), then (b) only if the site options conflict. No assumption is made here.
2. **One job PACZ4CL (IKJEFT01 batch, writes only new T1 scratch datasets):** create `Z00000.PACMAN.Z4CL.T1`
   (PDS FB 80/80: the test CLIST members) and `Z00000.PACMAN.Z4HSY.DATA` (empty PDS FB 80/80, present path; the
   missing-path prefix `Z00000.PACMAN.Z4HSN` is never allocated); IEBGENER the PARM-line CLIST and the two HS-block
   CLISTs; one TMP step: the 4 G8 keyword sets (`G8PARM=` = tests/test_g8.py clist_parm), the two HS-block runs,
   LISTALC. Postcheck: PARM strings exact, HS-block paths as MVS JOB 312, RC 0.
3. **One job PACZ4INS (promotion + smoke):** IEBCOPY `LOAD(PACZ2D)` -> `LOAD(PACMAIN)` (no rebind; the copy
   mechanism within one PDSE is confirmed in the review of the deck), then one batch CLASSIC run and one TSO-mode
   batch run on PACMAIN, compared with their oracle 307 blocks (existing zos_classic_check, PMAP PACMAIN); the CLIST
   member uploaded by Zowe and verified by binary download (ZOS-1 zos_sync method). Postcheck: copy messages, 2 runs
   = oracle, CLIST bytes = rendered.
4. **One live session L1 (user at the keyboard):** logon, READY, the two games of section 2, LOGOFF. Postcheck: the
   transcript (screen text captured after READY) against the existing models: DIE1 = the 1.0 TSO oracle run
   (tests/test_mvs8.py TSO model), LOST0 likewise; no `***` inside a frame; READY after each game.

## 7. Reused, not retested
ZOS-2: the whole CLASSIC game logic in batch and TSO line mode (oracle 307, 25/25, prompts and D19 rules in batch),
storage independence. ZOS-3: TMP CALL of the PDSE program (HTSO1/2), PACFSIO batch fallback, PACHSIO, TSD; the
oracle / model tooling (zos_equiv, zos_classic_check). The installed PACMAIN is a copy of the accepted PACZ2D: its
smoke is 2 runs, not a battery.

## 8. Security (port 623 and interactive traces)
- 198.51.100.200:623 is plain TN3270E (no TLS, ZOS-0 C): userid and password cross the network unencrypted. The user
  decides whether to accept that for this training system; the password is typed only by the user, never by the
  assistant, never stored, never placed in a file, script, command line or trace.
- No terminal trace during logon: c3270 tracing (or screen capture) starts only after READY; any trace is reviewed and
  redacted (userid only if the user agrees) before it enters the repository; raw traces stay out of git.
- One session; no PROFILE / SYSPROC / ISPF / RACF / site setting changed; only `EXEC` of the project CLIST and
  read-only commands; LOGOFF at the end.
- STOP on any unexpected panel, message, security prompt, abend or CEE message; nothing outside `Z00000.PACMAN.*`;
  no DELETE, no purge.

## 9. Decisions requested
1. 6.1: how Profile A reaches the interactive CALL (recommended: read-only discovery first).
2. PACZ4CL as one batch job with fresh T1 scratch datasets (no DELETE).
3. Promotion by IEBCOPY copy of PACZ2D to PACMAIN + 2-run smoke (no rebind, no battery).
4. Live: the user plays the DIE1 and LOST0 card sequences, transcript compared with the existing models.

## 10. Decisions (user, 2026-10-15) and preparation
Design approved. Order: (1) interactive CEEOPTS discovery only (docs/zos4-ceeopts-discovery.md; read-only REXX
tools/zos4/SHOWCEE.rexx prepared, not uploaded); (2) PACZ4CL (one batch job, fresh T1 datasets, no DELETE, never
DATA) prepared for review: jcl/zos/PACZ4CL.jcl, tools/zowe/zos_clist_check.py (--gate / postcheck), test section 14;
gate PASS 2026-10-15; not submitted. PACZ4INS (IEBCOPY PACZ2D -> PACMAIN, no rebind, two oracle 307 smoke runs) and the
live DIE1 / LOST0 acceptance come after the CEEOPTS resolution.
Finding for PACZ4INS: `Z00000.PACMAN.CLIST(PACMAN)` already exists - it is the raw source template (@@PREFIX@@),
uploaded by zos_sync in ZOS-1 as an identity copy, not an install. Installing the rendered CLIST into that member
would replace the template: to be decided in the PACZ4INS review (e.g. PRV copy first, or a separate source library).

## 11. CEEOPTS discovery result (user, 2026-10-15) - STOP as designed
No CEEOPTS DD in the interactive session; the logon (DBPROCDG) enters ISPF. SHOWCEE not uploaded or used. Analysis and
recommendation: docs/zos4-ceeopts-analysis.md (profile A is not effective interactively; diagnostic RPTOPTS job first,
then a reviewed CLIST CEEOPTS allocation). No CLIST change, no PACMAIN promotion yet.
