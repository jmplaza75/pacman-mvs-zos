# z/OS build procedure (ZOS-1, D45; branch `zos`)
Target: IBM Z Xplore S0W1, z/OS V3R1 (docs/ZOS-ENVIRONMENT.md). Prefix `<HLQ>.PACMAN` with HLQ from `--hlq` or
`PACMAN_ZOS_HLQ` (never a literal in the repository; JCL templates in jcl/zos/ use `@@HLQ@@`). Zowe profile `zosmf`
(override with `PACMAN_ZOWE_PROFILE`); credentials only in the Zowe secure store.
Evidence: docs/evidence/zos1-toolchain.md (JOBs 08252, 08254, 08331, 08335).

## Toolchain (verified)
| Step | Program | Libraries |
|---|---|---|
| COBOL | IGYCRCTL, **Enterprise COBOL for z/OS 6.5.0 P260714** (site PROC IGYWCL, LNGPRFX IGY650) | STEPLIB IGY650.SIGYCOMP, CEE.SCEERUN, CEE.SCEERUN2; SYSUT1-15 + SYSMDECK work files |
| Assembler | ASMA90, **HLASM R6.0** (PTF UO07449) | STEPLIB HLA.SASMMOD1; SYSLIB SYS1.MACLIB, SYS1.MODGEN |
| Bind | **IEWBLINK** (program objects FORMAT 3 in the PDSE LOAD) | SYSLIB CEE.SCEELKEX, CEE.SCEELKED |
| Run | the program from `<HLQ>.PACMAN.LOAD` (STEPLIB), LE runtime options through a CEEOPTS DD | CEE.SCEERUN (system) |

## Build profile A (D45, initial port profile)
- COBOL: `RENT,RMODE(24),DATA(24),NODYNAM,TRUNC(STD),NUMPROC(NOPFD)` on top of the site defaults (CODEPAGE(1140),
  ARITH(COMPAT), QUOTE, OPTIMIZE(0), OUTDD(SYSOUT), NOSSRANGE).
- Binder: `RENT,AMODE=24,RMODE=24` (plus LIST,MAP,XREF).
- LE: `CEEOPTS` = `ALL31(OFF),STACK(,,BELOW)`.
- Scope of the evidence: J3 (JOB08331) proves the COBOL 6.5 / HLASM R6.0 / IEWBLINK / LE **toolchain probe** in
  AMODE 24 (TAM=0, BSM=0, data and save area below 16 MB). It does **not** prove that the complete Pac-Man application
  is viable in AMODE 24; that is established with the real modules in ZOS-2 / ZOS-3.
- Profile B (fallback only, never adopted automatically): COBOL site defaults (DATA(31), RMODE(AUTO)) + `RENT`,
  binder `RENT,AMODE=31`, no CEEOPTS (J4, JOB08335). If a real Pac-Man module exposes an AMODE 24 limitation, stop and
  report before changing profile or source.

## Datasets (J1, JOB08252)
| Dataset | Type | Format | Use |
|---|---|---|---|
| `<HLQ>.PACMAN.COBOL` | PDSE | FB 80 / 27920 | COBOL sources (shared src/cobol + src/probe/zos) |
| `<HLQ>.PACMAN.COPY` | PDSE | FB 80 / 27920 | copybooks (SYSLIB of IGYCRCTL) |
| `<HLQ>.PACMAN.ASM` | PDSE | FB 80 / 27920 | assembler sources |
| `<HLQ>.PACMAN.CLIST` | PDSE | FB 80 / 27920 | CLIST |
| `<HLQ>.PACMAN.OBJ` | PDSE | FB 80 / 27920 | object decks between compile and bind |
| `<HLQ>.PACMAN.LOAD` | PDSE | U 32760 | program objects |
| `<HLQ>.PACMAN.DATA` | **PDS** | FB 80 / 80 | high score (PACHSIO needs a PDS with BLKSIZE 80) |
The site ACS routine reduces any allocation above 200 KB (`IGD01007I ZXPACS ... ZXP SAYS NO`); PDSE secondary extents
absorb it.

## Source transfer
- `python3 tools/zowe/zos_upload.py FILE LIB` (one member) / `python3 tools/zowe/zos_sync.py` (the 23-member release
  set). Upload with `--encoding IBM-037` (= CP037, matching CODEPAGE(1140) and the MVS sources), then a binary
  download compared byte for byte with the local lines encoded to IBM-037 and padded to fixed 80-byte records; any
  difference or a line over 80 bytes fails. ZOS-1: 23 + 2 members identical.

## Jobs and listings
- `python3 tools/zowe/zos_submit.py jcl/zos/<DECK>.jcl`: renders `@@HLQ@@`, audits the deck (every written dataset
  under `<HLQ>.PACMAN`, no DELETE disposition), submits **once**, waits, saves every spool file under
  `build/zos/<JOBNAME>-<JOBID>/`. `--fetch JOBID` re-reads a job (read-only). Jobs are never purged by the tools.
- `python3 tools/zowe/zos_listing.py <spool dir> OUT.txt`: the TK4- listing shape the tests parse (step table from
  JESJCL + IEF142I, then the non-JES spool files with ASA control applied). Validated on JOB08331 / JOB08335.
- JOB card: `JOB 1,'...',CLASS=7,MSGLEVEL=(1,1),NOTIFY=&SYSUID`; no MSGCLASS (site default class A held).

## z/OS decks (ZOS-2)
- `python3 tools/make_deck.py --target zos DECK [--load M] [--job NAME]` writes build/zos/decks/DECK.jcl with prefix
  `@@HLQ@@.PACMAN`: the MVS deck with the step builders of tools/zowe/zos_target.py (no in-stream upload: the members
  verified by zos_sync; IGYCRCTL profile A -> OBJ(member); ASMA90 from ASM(member); IEWBLINK INCLUDE OBJ(...) AMODE 24;
  run steps = the MVS EXEC / PARM / cards / DDs + CEEOPTS, CEEDUMP, SYSUDUMP DUMMY; REL20 without the CLIST steps).
  `ZCMP` = Z2-1 compile inventory (jcl/zos/PACZ2CMP.jcl); `ZHSA` = PACHSIO assembled alone; the ZOS-2 jobs `Z2*`
  (CHUNKS in tools/zowe/zos_target.py: build, drivers, run subsets, each well under the ~5,000-line site limit;
  `tools/zowe/zos_plan.py` prints the step / RC / expected-output matrix). Build listings are compact (COBOL
  NOSOURCE,NOXREF; HLASM PCONTROL(NOGEN), no cross-reference tables; binder LIST,MAP): no effect on the object code.
  The MVS target is unchanged: `tools/zowe/r3_gate.py` (generator and release decks on the 2.0-mvs-max sources).
- Z1 (docs/ZOS-DIFFS.md): the shared COBOL sources of branch zos carry 28 `COPY <member>.` substitutions
  (tests/zos_c2.py); MVS is never rebuilt from branch zos.
- `tools/zowe/zos_compile_report.py SPOOLDIR`: RC and every IGY / ASMA diagnostic per step.
- `tools/zowe/zos_equiv.py SPOOLDIR tests/oracle20/<JOB>.json.gz --map PACMAIN=<load>`: every run's SYSOUT equal to
  the oracle run (only the ASA column and the record padding removed; TK4- separator = exactly two empty lines).

## DISPLAY / SYSOUT behaviour
COBOL DISPLAY output on DD SYSOUT is **RECFM FBA, LRECL 121**: one ASA byte + 120 data characters. A longer line is
split into further records (the 130-character probe line became 120 + 10). The 2.0 oracle (tests/oracle20) has no
line longer than 120 characters (maximum exactly 120): **120 is the safe limit**; any longer line in a z/OS run is a
difference to investigate.

## Rules (CLAUDE.md, plan R1-R8)
Shared src/ stays = 2.0-mvs-max (overrides only in src/zos/ with a Z-entry); one job at a time; no deletions, no job
purges, nothing outside `<HLQ>.PACMAN.*`; every z/OS action list is shown to the user before it runs.
