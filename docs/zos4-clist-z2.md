# ZOS-4 Z-entry Z2 (proposed, for review; NOT installed, NOT written to src/, nothing on z/OS)

Reason (TSO/E / LE difference, plan sec. 6 ZOS-4 "CLIST changed only if a TSO/E difference forces it"): the
interactive session has no CEEOPTS DD (user LISTALC, logon proc DBPROCDG), and PACZ4LE JOB03693 D1 shows the
no-override LE defaults are ALL31(ON) and STACK ANYWHERE (IBM-supplied) - not profile A; D2 shows a CEEOPTS DD gives
the AMODE 24 module profile A; D3 shows invocation options would outrank it, and the CLIST PARM carries none.

## Change
New file `src/zos/PACMAN.clist` (branch zos only; `src/clist/PACMAN.clist`, the 2.0 MVS CLIST, stays frozen), = the
2.0 CLIST plus 12 lines around the CALL; keyword defaults, PARM build and every other line unchanged:

```diff
--- src/clist/PACMAN.clist (2.0, frozen)
+++ src/zos/PACMAN.clist (proposed Z2)
@@ -71,5 +71,16 @@
 /* THE PARM IS BUILT FIRST: A CLIST LINE ENDS AT COLUMN 72.        */
 SET &P = &STR(TSO AI&AI &GHOSTS &M&C&H&A&R&G&S&V&Y&U&W&L&F&K)
+/* Z2 (ZOS-4): LE PROFILE A FOR THE CALL. THE TSO SESSION HAS NO   */
+/* CEEOPTS (IBM DEFAULTS ALL31(ON), STACK ANYWHERE): ALLOCATE ONE.  */
+/* A MISSING DATASET WOULD RUN UNDER THE DEFAULTS: STOP INSTEAD.    */
+IF &SYSDSN('@@PREFIX@@.CEEOPTS') NE OK THEN DO
+  WRITE PACMAN: @@PREFIX@@.CEEOPTS MISSING, GAME NOT STARTED
+  FREE F(SYSIN SYSOUT)
+  IF &W = A THEN FREE F(PACHS)
+  EXIT CODE(8)
+END
+ALLOC F(CEEOPTS) DA('@@PREFIX@@.CEEOPTS') SHR REUSE
 CALL '@@PREFIX@@.LOAD(PACMAIN)' '&P'
+FREE F(CEEOPTS)
 FREE F(SYSIN SYSOUT)
 IF &W = A THEN FREE F(PACHS)
```
Rendered for `Z00000.PACMAN` the longest line is 70 characters (limit 72).

## Supporting dataset (to be created in PACZ4INS, not now)
`Z00000.PACMAN.CEEOPTS`: sequential, RECFM FB, LRECL 80, BLKSIZE 80, one record `ALL31(OFF),STACK(,,BELOW)` - the exact
CEEOPTS of every ZOS-2 / ZOS-3 run and of PACZ4LE D2; written once by IEBGENER (in-stream), DISP=(NEW,CATLG,CATLG), no
DELETE; read SHR by the CLIST.

## Behaviour and scope
- Present: CEEOPTS is allocated just before the CALL and freed right after it; the session had no CEEOPTS DD, so the
  FREE restores it exactly. Precedence: no invocation options in the PARM, no NONOVR / CEEBXITA found -> CEEOPTS rules.
- Missing: a message, SYSIN / SYSOUT (and PACHS for ARCADE) freed, `EXIT CODE(8)`, no CALL: the game never runs under
  the IBM defaults. (Before Z2 a missing dataset could not occur; the check mirrors the HS-block guard: a failed ALLOC
  would end the CLIST.)
- Known limit: a session that already had its own CEEOPTS DD would have it replaced during the game and freed after it
  (not the case with DBPROCDG; recorded).
- The PROC / PARM lines extracted for the G8 check (`make_deck.rp3_clist_lines`) are unchanged: Z2 sits after
  `SET &P` (25 lines extracted, none of them touched).

## Proposed tests (no new mechanism)
- PACZ4CL (approved, not yet submitted) gains a third TMP block: the Z2 lines with a prefix whose CEEOPTS exists (a fresh
  T1 dataset) -> LISTALC shows CEEOPTS SHR, then FREE; and with a prefix whose CEEOPTS never existed -> the message and
  RC 8, no CALL (a stub CALL target is not needed: the block is run up to the CALL line only).
- Local: lines <= 72; 2.0 keyword defaults unchanged; the diff above is the only difference to the frozen CLIST.
- Live (L1): the DIE1 / LOST0 games then run with profile A (optionally one RPTOPTS confirmation with ZHELLO24 in the
  same session).

## Register
docs/ZOS-DIFFS.md entry Z2 (CLIST: profile A CEEOPTS around the CALL; reason above; evidence JOB03693) - to be added
when the Z-entry is approved.

## Refinement (user, 2026-10-15) - candidate in src/zos/PACMAN.clist (not installed)
EXIT CODE(8) on a missing project CEEOPTS approved and required. An already allocated session CEEOPTS must never be
replaced or freed: the ALLOC is issued **without REUSE**, inside a CLIST ERROR routine; if a CEEOPTS DD exists the
ALLOC fails, the existing DD is untouched, the CLIST writes `PACMAN: A CEEOPTS DD IS ALREADY ALLOCATED, GAME NOT
STARTED`, frees SYSIN / SYSOUT (and PACHS for ARCADE) and exits with RC 8 without the CALL. Only when this ALLOC
succeeded (so no CEEOPTS existed) does the CALL run, followed by `FREE F(CEEOPTS)`: the session returns to its
original no-CEEOPTS state. No general DD-stack mechanism. Z2 = 24 lines (23 before the CALL, 1 after); the 2.0 CLIST
is otherwise byte-identical (guarded by tests/zos_c2.py z2_guard and tests/test_zos_tools.py section 14).
PACZ4CL now covers the three cases under the TMP (members Z2Y / Z2N with the Z2 lines verbatim, CALL -> marker +
LISTALC, wrapper Z2RUN writing Z2RC=&LASTCC; project CEEOPTS Z4CEY.CEEOPTS written by step Z2CEE; Z4CEN never
allocated); the G8 and HS parts of PACZ4CL are byte-identical to the previous version.

## Refinement 2 (user, 2026-10-15, after PACZ4CL JOB03750 case 3 SAFE but INCONCLUSIVE)
`&SYSDSN` result handled in three ways: `OK` -> continue; `DATASET NOT FOUND` -> the approved MISSING message, RC 8;
anything else -> `PACMAN: CEEOPTS CHECK FAILED (<result>), GAME NOT STARTED`, RC 8; no CALL in either failure. Z2 =
30 lines (29 before the CALL, 1 after), guarded by tests/zos_c2.py z2_guard. Z2-only attempt T2: jcl/zos/PACZ4Z2.jcl
(tools/zowe/zos_z2_check.py, test section 16): fresh names Z4CL.T2 / Z4CY2.CEEOPTS / Z4CN2.CEEOPTS (never
allocated), IKJEFT01 with DYNAMNBR=200 (as DBPROCDG), CONTROL LIST in the test members so case 3 must show the
listed `ALLOC F(CEEOPTS)` (SYSDSN passed, ALLOC reached) and its refusal; the pre-existing DD (on Z4CL.T2(Z2N)) must
be identical in LISTALC before and after case 3. PACZ4CL (T1) stays frozen as submitted.
