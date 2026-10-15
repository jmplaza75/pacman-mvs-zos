# ZOS-4 - interactive LE runtime options: analysis and recommendation (local / read-only; nothing submitted)

## Facts
- Interactive session (user, LISTALC STATUS): **no CEEOPTS DD**. The logon enters ISPF; procedure **DBPROCDG**.
- VENDOR.PROCLIB(DBPROCDG) (read-only view): `EXEC PGM=IKJEFT01,PARM='EXEC ''VENDOR.CLIST(SETUP)'''`; STEPLIB
  SYS1.DGTLLIB, GIM.SGIMLMD0, ZXP.PUBLIC.LOAD, DSND10.SDSNLOAD, DSND10.SDSNLOD2; SYSPROC VENDOR.CLIST, ZXP.PUBLIC.CLIST,
  SVTSC.CLIST, LVL0.CLIST; TSO DDs only. No CEEOPTS. VENDOR.CLIST(SETUP) allocates ISPF / product libraries only (no
  LE option). No `CEE*` member (CEEDOPT / CEEBXITA / CEEROPT / CEEUOPT) in any of the five STEPLIB libraries; no
  CEEPRMxx in SYS1.PARMLIB (the system's LE parmlib member was not located; not needed, see below).
- PACZ2D was bound without CEEUOPT (PACZ2BLD: INCLUDE of the 13 objects only); the CLIST PARM has no `/`.
- ZOS-1 J4 PACZPRFB JOB08335 ran ZHELLO31 **without CEEOPTS**: its save area (LE stack) was **above** 16 MB
  (SAVEA = 458174512): the installation default stack location is not BELOW, i.e. the installation defaults are not
  profile A.

## 1. Precedence for an interactive TSO CALL without CEEOPTS
Language Environment order (z/OS LE Programming Guide, "order of precedence for runtime options"), highest first:
non-overridable installation options (CEEPRMxx / CEEDOPT NONOVR) > CEEBXITA exit > **CEEOPTS DD** > **invocation
options** (CALL / PARM; for a COBOL main with CBLOPTS(ON) the part after the first `/`) > CEEUOPT / #pragma runopts in
the program > region-level CEEROPT > installation defaults. For the CLIST's CALL today every source above the
installation defaults is absent (no CEEOPTS, no `/`, no CEEUOPT, no STEPLIB CEE module), so PACMAIN would run with the
**installation defaults - the same defaults batch gets without a CEEOPTS DD**, which PACZPRFB shows are not profile A.
Conclusion: profile A is NOT effective interactively. (The order above is from the documentation; the RPTOPTS report
below shows "LAST WHERE SET" per option and confirms it on this system.)

## 2-3. Smallest safe way to report and prove ALL31 / STACK
LE `RPTOPTS(ON)` writes, at enclave end, every option's value and where it was set, to MSGFILE (default SYSOUT). Run it
with the existing diagnostic program **ZHELLO24** (Z00000.PACMAN.LOAD, ZOS-1 J3: profile A COBOL, prints PARM length /
text, TAM / BSM and BELOW / ABOVE for its PARM, CSECT and save area) - no Pac-Man, no new program, no rebuild.
Proposed one batch job (for review, not prepared as a deck yet), each step STEPLIB LOAD, SYSOUT only:
1. `PARM='/RPTOPTS(ON)'`, no CEEOPTS: the installation defaults exactly as the interactive CALL gets them (no session
   source exists, section 1) -> ALL31 / STACK values and their source; SAVEA BELOW / ABOVE.
2. `PARM='TSO/ALL31(OFF),STACK(,,BELOW),RPTOPTS(ON)'`, no CEEOPTS: invocation options take effect; the program's PARM
   echo must be exactly `TSO` (the options are stripped).
3. CEEOPTS DD `ALL31(OFF),STACK(,,BELOW),RPTOPTS(ON)` and `PARM='TSO/ALL31(ON)'`: precedence CEEOPTS over invocation on
   this system.
Effective values are proven by two independent readings per step: the RPTOPTS report (value + source) and ZHELLO24's
own SAVEA BELOW / ABOVE and TAM / BSM. An optional interactive confirmation (one `CALL` of ZHELLO24 with
`'/RPTOPTS(ON)'` inside the live session, SYSOUT temporarily `DA(*)` as the CLIST itself does) only adds that the
session has no hidden source; sections 1 already shows none.

## 5. Alternatives
| | Diagnostic only (RPTOPTS) | Project CEEOPTS allocated by the CLIST | Invocation options in the CALL PARM |
|---|---|---|---|
| What | report / prove, change nothing | `ALLOC F(CEEOPTS) DA('<p>.<ceeopts ds>') SHR REUSE` before CALL, `FREE F(CEEOPTS)` after | `CALL ... '&P/ALL31(OFF),STACK(,,BELOW)'` |
| Precedence | n/a | above invocation, CEEUOPT, defaults; below NONOVR / CEEBXITA (none found) | above CEEUOPT and defaults; below a CEEOPTS DD (none in the session) |
| Scope | none | the CLIST's CALL only; the session had no CEEOPTS, so FREE restores it exactly (no lasting change) | that CALL only |
| Same mechanism as the ZOS-2 / ZOS-3 evidence | - | **yes** (every batch run used a CEEOPTS DD) | no (no `/` ever used; PARM echo to be proven) |
| Cost / risk | none | one new project dataset with one record; CLIST Z-entry (2 lines + an &SYSDSN guard so a missing dataset does not end the CLIST); lines <= 72 | CLIST Z-entry; the G8 PARM check and every PARM-based test must exclude the suffix; a stray `/` in a future PARM would be read by LE |
| Makes PACMAIN run with profile A | no | yes | yes |

## Recommendation
1. Diagnostic first: the 3-step ZHELLO24 RPTOPTS batch job above (no Pac-Man, writes nothing): proves the defaults,
   the invocation path and the CEEOPTS-over-invocation precedence on this system.
2. Then the **project CEEOPTS allocated by the CLIST** as the Z-entry (same mechanism as all accepted evidence, scope
   limited to the CALL, session restored by FREE), reviewed before it is written; invocation options only as the
   fallback if a CEEOPTS DD cannot be used interactively.
3. PACZ4CL, PACZ4INS and the live DIE1 / LOST0 follow unchanged (the CLIST content checked by PACZ4CL is then the
   Z-entry version).
