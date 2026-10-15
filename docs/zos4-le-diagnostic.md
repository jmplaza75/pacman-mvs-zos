# ZOS-4 PACZ4LE - LE runtime-option diagnostic (for review; not submitted)

Deck of record jcl/zos/PACZ4LE.jcl (zos_target Z4LE_STEPS), rendered SHA-256
ed97cb87180d4d973f1da479e7df2527a79f3b31c16fe33eb0a6f9608863b9db, 26 lines. Programs: the ZOS-1 probes already in
Z00000.PACMAN.LOAD (ZHELLOC COBOL main `PROCEDURE DIVISION USING PARM-AREA` + ZHELLOA HLASM leaf: TAM, BSM, addresses
of the parameter, its CSECT and the caller's save area = the COBOL DSA from the LE stack). ZHELLO24 = profile A bind
(AMODE 24, RMODE 24), ZHELLO31 = profile B bind (AMODE 31). No Pac-Man, no compile, no write; STEPLIB only; every step
COND=(0,NE), SYSOUT (DISPLAY + LE MSGFILE) / CEEDUMP to spool, SYSUDUMP DUMMY. Check: tools/zowe/zos_le_check.py.

Precedence used (IBM z/OS 3.1, user correction): NONOVR > CEEBXITA > invocation options > DD:CEEOPTS > CEEUOPT >
CEEROPT > installation defaults.

## Invocation format - verified by the run, not inferred
For a COBOL main LE splits the PARM by CBLOPTS: ON = `program-arguments/runtime-options`, OFF = the reverse. CBLOPTS
is set only at installation level (or CEEUOPT, not linked here), so its value is not assumed: every step passes
`ZHARG/...` where ZHARG is no LE option name. CBLOPTS(ON): the program echoes `ZH PARMLEN=005`, `ZH PARM=ZHARG` and the
options report appears (RPTOPTS(ON) taken as an option), and the report lists CBLOPTS(ON). CBLOPTS(OFF) would show the
option string as the program argument and no report (LE would also flag ZHARG): that outcome is a FAIL / STOP.

| Step | PGM | PARM | CEEOPTS | Expected options report (value <- LAST WHERE SET) | Argument | TAM / BSM / addresses |
|---|---|---|---|---|---|---|
| D1 effective no-override LE defaults (evidence for, not an observation of, the interactive CALL) | ZHELLO31 (AMODE 31, proven without CEEOPTS: JOB08335) | `ZHARG/RPTOPTS(ON)` | none | ALL31, STACK <- installation default (values recorded, PRFB suggests ALL31(ON), stack ANYWHERE); CBLOPTS(ON); RPTOPTS(ON) <- invocation | ZHARG (005) | 1 / 1; SAVEA BELOW required only if the reported stack is BELOW; with ANYWHERE information only |
| D2 profile A | ZHELLO24 (AMODE 24) | `ZHARG/RPTOPTS(ON)` (only RPTOPTS at the higher-precedence source) | `ALL31(OFF),STACK(,,BELOW)` | ALL31(OFF) <- CEEOPTS; STACK(..,BELOW,..) <- CEEOPTS; RPTOPTS(ON) <- invocation | ZHARG (005) | 0 / 0; PARM1, CSECT, SAVEA all BELOW |
| D3 precedence | ZHELLO31 (AMODE 31: any stack is safe) | `ZHARG/STACK(,,ANYWHERE),RPTOPTS(ON)` | `ALL31(ON),STACK(,,BELOW)` | STACK(..,ANYWHERE,..) <- invocation (outranks CEEOPTS); ALL31(ON) <- CEEOPTS | ZHARG (005) | 1 / 1; SAVEA recorded for information only: STACK(,,ANYWHERE) allows either location, so precedence is decided by the report alone |

D3 safety: the contradiction is on STACK only, on the AMODE 31 probe, with ALL31(ON) in CEEOPTS so STACK ANYWHERE is a
valid combination; no AMODE 24 program ever gets a stack above the line.

RC 0000 for every step. Spool: three SYSOUTs of ~10 program lines + one options report each (~100-150 lines), JES
lines; estimate < 700 lines.
STOP (no rerun, no change) on: a COND CODE other than 0000; any CEEnnnn message (e.g. an invalid option), ABEND,
IEA995, $HASP375; a spool DD other than SYSOUT; STEPLIB not retained once per step; an argument other than ZHARG
(CBLOPTS not ON); no options report; D2 not ALL31(OFF) / STACK BELOW from CEEOPTS or any address ABOVE; D3 STACK not
from the invocation or ALL31(ON) not from CEEOPTS (correction 2026-10-15: SAVEA is not a D3 criterion). The report layout (source column, then option) is the documented LE format; if
the real layout differs the checker fails closed and the result is reviewed, not reclassified silently.
What it decides: D1 = the effective no-override LE defaults, which the interactive CALL gets today only because no
session source exists (docs/zos4-ceeopts-analysis.md) - evidence, not a direct observation of that CALL;
D2 = that a CEEOPTS DD gives profile A to the AMODE 24 module; D3 = that invocation options would outrank it - so a
CLIST CEEOPTS allocation works only while the CLIST PARM carries no runtime options (it carries none).
