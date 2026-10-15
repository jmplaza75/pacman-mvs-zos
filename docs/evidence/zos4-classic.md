# ZOS-4 CLASSIC - evidence

## PACZ4LE JOB03693 - LE runtime-option diagnostic: PASS (after a checker fix; see the audit note)
Deck jcl/zos/PACZ4LE.jcl (docs/zos4-le-diagnostic.md), submitted once, unchanged; CC 0000; STEPLIB
Z00000.PACMAN.LOAD retained once per step; only SYSOUT; no CEEnnnn message, no abend. Every step received exactly the
argument `ZHARG` (PARMLEN 005) and produced the options report: the COBOL main takes `arguments/options`
(CBLOPTS(ON), IBM-supplied default) - verified by the run.

| Step | Program | ALL31 (origin) | STACK (origin) | TAM / BSM | PARM1 / CSECT / SAVEA |
|---|---|---|---|---|---|
| D1 no override | ZHELLO31 | ON (IBM-supplied default) | 131072,131072,ANYWHERE,KEEP,524288,131072 (IBM-supplied default) | 1 / 1 | ABOVE / BELOW / ABOVE (information) |
| D2 profile A | ZHELLO24, CEEOPTS ALL31(OFF),STACK(,,BELOW) | OFF (DD:CEEOPTS) | ...,BELOW,... (DD:CEEOPTS) | 0 / 0 | BELOW / BELOW / BELOW |
| D3 precedence | ZHELLO31, CEEOPTS ALL31(ON),STACK(,,BELOW) + invocation STACK(,,ANYWHERE) | ON (DD:CEEOPTS) | ...,ANYWHERE,... (Invocation command) | 1 / 1 | ABOVE / BELOW / ABOVE (information) |

Conclusions: (1) D1 = the effective no-override LE defaults on this system: ALL31(ON), stack ANYWHERE, IBM-supplied
(no installation-level change at all) - not profile A. Because the interactive session has no CEEOPTS DD and no other
option source (docs/zos4-ceeopts-analysis.md), these are the options the CLIST's CALL would get today (evidence, not a
direct observation of that CALL). (2) A CEEOPTS DD gives the AMODE 24 module profile A (D2). (3) Invocation options
outrank DD:CEEOPTS (D3), as IBM documents: a CLIST CEEOPTS allocation is effective while the CLIST PARM carries no
runtime options (it carries none).

Audit note (both facts kept): the FIRST check (docs/evidence/zos4-le-check-first-run.txt) reported one FAIL in D1: a
checker-wording defect - it expected the origin text 'Installation ...', this system reports 'IBM-supplied default'.
The raw files were frozen first (SHA-256 docs/evidence/zos4-pacz4le-JOB03693-raw.sha256, read-only). Fix a800ebf:
D1 accepts exactly 'IBM-supplied default' or 'Installation default' and still fails DD:CEEOPTS, Invocation command
or any other origin (regression on the real D1 SYSOUT + negative origins). The corrected checker on the same raw
files: 18/18 PASS. PACZ4LE / JOB03693 = PASS. Archive docs/evidence/zos4-spool/PACZ4LE-JOB03693.tar.gz.

## PACZ4CL JOB03750 (attempt T1) - G8 PASS, HS CLIST PASS, Z2 1-2 PASS, Z2 case 3 SAFE but INCONCLUSIVE
Deck jcl/zos/PACZ4CL.jcl, name gate PASS just before, submitted once, unchanged; every step COND CODE 0000; no CEE /
abend; JESYSMSG names only Z4CL.T1, Z4HSY.DATA, Z4CEY.CEEOPTS; no DELETE, no PACMAIN, no Z00000.PACMAN.DATA.
- G8: the 4 `G8PARM=` lines = oracle 307. HS CLIST block: present path `PACHS KEEP`, missing path `NULLFILE PACHS`,
  `HSCL END` after each, as oracle 312.
- Z2 case 1 (project CEEOPTS, no DD before): CEEOPTS on Z4CEY.CEEOPTS at the simulated CALL, gone after the FREE,
  Z2RC=0. Z2 case 2 (project dataset absent): the missing message, no CALL marker, no CEEOPTS DD, Z2RC=8.
- Z2 case 3 (a CEEOPTS DD pre-allocated on Z4CL.T1(PARMS)): no CALL, Z2RC=8, the DD still on Z4CL.T1(PARMS) after
  the test (not replaced, not lost), final FREE clean - SAFE; but `&SYSDSN` of the existing Z4CEY.CEEOPTS returned
  not-OK, so the CLIST left through the "MISSING" branch and never reached the ALLOC without REUSE: the intended
  ALLOC-conflict branch is NOT proven - INCONCLUSIVE (probable cause, unverified: the IKJEFT01 step had no DYNAMNBR;
  the interactive DBPROCDG has DYNAMNBR=200). Not accepted as PASS; not rerun.
- Post-job state as reviewed: Z4CL.T1 = HSCLN HSCLY PARMS Z2N Z2RUN Z2Y; Z4HSY.DATA no member; Z4CEY.CEEOPTS one
  record; Z4CEN.CEEOPTS and Z4HSN.DATA absent.
Follow-up (user, 2026-10-15): Z2 SYSDSN handling refined (OK / not found / any other result reported) and a Z2-only
attempt T2 (DYNAMNBR=200) prepared for review.

## PACZ4Z2 JOB03829 (Z2 attempt T2) - cases 1-2 PASS, case 3 SAFE but FAIL (controlled-error handling)
Name gate PASS just before; submitted once, unchanged; every step COND CODE 0000; IKJEFT01 with DYNAMNBR=200; no CEE /
abend; JESYSMSG names only Z4CL.T2 and Z4CY2.CEEOPTS; no DELETE, no PACMAIN, no Z00000.PACMAN.DATA.
- Case 1 PASS: CEEOPTS on Z4CY2.CEEOPTS at the simulated CALL, gone after the FREE, Z2RC=0.
- Case 2 PASS: the exact MISSING message, no CHECK FAILED, no ALLOC of CEEOPTS, no CALL marker, no CEEOPTS DD, Z2RC=8.
- Case 3 SAFE but FAIL: SYSDSN OK (the ALLOC was reached: CONTROL LIST shows
  `ALLOC F(CEEOPTS) DA('Z00000.PACMAN.Z4CY2.CEEOPTS') SHR`), refused with
  `IKJ56246I DATA SET Z00000.PACMAN.Z4CY2.CEEOPTS NOT ALLOCATED, FILE IN USE`; no CALL; the original CEEOPTS DD
  (Z4CL.T2(Z2N), KEEP) identical in LISTALC before and after - but the CLIST and its caller ended right after the
  refusal: the ERROR routine did not regain control, no ALREADY ALLOCATED message, no Z2RC=8, and SYSIN / SYSOUT stayed
  allocated (NULLFILE in the final LISTALC). Hypothesis (to be proven by T3): CONTROL FLUSH (the default) flushed the
  input stack on the command error before the ERROR routine could act.
- Post-job state as reviewed: Z4CL.T2 = Z2N Z2RUN Z2Y; Z4CY2.CEEOPTS one record; Z4CN2.CEEOPTS absent.
Z2 not accepted. Follow-up (user, 2026-10-15): CONTROL NOFLUSH around the ERROR routine + ALLOC, attempt T3.
