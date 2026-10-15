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
