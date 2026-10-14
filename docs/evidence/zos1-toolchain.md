# ZOS-1 toolchain evidence (2026-10-14) - parts 1-6
Authorised: local Zowe helpers, J1 PACZALLO, attribute check, IBM-037 uploads with binary round trip, J2 PACZHELO
and its analysis. J3 / J4 (profile probes) and the probe sources are prepared but NOT uploaded or submitted.
Raw spools: build/zos/<JOBNAME>-<JOBID>/ (gitignored). Nothing deleted, nothing purged, one job at a time.

## 1. Tools (tools/zowe/)
- zoslib.py: HLQ only from --hlq / PACMAN_ZOS_HLQ (templates use @@HLQ@@); deck audit: every written dataset under
  <HLQ>.PACMAN, no DELETE disposition (self-test: a ZHEIST write and a DELETE disposition are refused).
- zos_upload.py: upload with `--encoding IBM-037`, binary download, compare with the local lines encoded to IBM-037 and
  padded to fixed 80-byte records (a line over 80 bytes fails before upload).
- zos_sync.py: the 23-member release set (13 COBOL incl. PACHELLO, 6 COPY, 3 ASM, 1 CLIST raw); src/cobol/alt
  (PACDSPX, MVS-G0 alternative display) and src/probe are not in the set.
- zos_submit.py: render, audit, submit once with --wait-for-output, save every spool file; `--fetch` read-only.
- zos_listing.py: spool directory -> TK4- listing shape (step table from JESJCL programs + JESYSMSG IEF142I, then the
  non-JES spool files; ASA control characters interpreted). Checked on JOB08215 (BR14 IEFBR14 RC 0000).

## 2. J1 PACZALLO - JOB08252, CC 0000
IEFBR14 with seven NEW,CATLG,CATLG DDs; IGD101I SMS allocated all seven, IGD104I RETAINED for all.
Site ACS routine: `IGD01007I ZXPACS: ALLOCATION SIZE (>200KB) REDUCED - ZXP SAYS NO` for COBOL, COPY, ASM, OBJ.
## 3. Attributes (zowe zos-files list data-set "Z00000.PACMAN.**" --attributes)
| Dataset | DSORG | DSNTYPE | RECFM/LRECL/BLKSIZE | Space (as reduced) |
|---|---|---|---|---|
| ASM | PO-E | LIBRARY | FB/80/27920 | 14 KB primary |
| CLIST | PO-E | LIBRARY | FB/80/27920 | 2 TRK |
| COBOL | PO-E | LIBRARY | FB/80/27920 | 14 KB primary |
| COPY | PO-E | LIBRARY | FB/80/27920 | 14 KB primary |
| DATA | PO | **PDS** | FB/80/80 | 1 TRK, 5 directory blocks |
| LOAD | PO-E | LIBRARY | U/0/32760 | 5 KB units |
| OBJ | PO-E | LIBRARY | FB/80/27920 | 14 KB primary |
**PDS viability for PACMAN.DATA: answered YES** (allocated as a true PDS with the BLKSIZE 80 PACHSIO requires).

## 4. Uploads: 23 / 23 identical
All 23 members uploaded with IBM-037 and downloaded in binary: every member byte-identical to its IBM-037 fixed-80
records (7123 records; no truncation). The reduced primaries were enough (secondary extents).

## 5. J2 PACZHELO - JOB08254, CC 0000 (compile + bind only; PACHELLO not run: it does DISPLAY UPON CONSOLE)
Steps HELLO.COBOL IGYCRCTL RC 0000, HELLO.LKED IEWBLINK RC 0000.
## 6. Analysis
- **Compiler: IBM Enterprise COBOL for z/OS 6.5.0 P260714** (PP 5655-EC6). PROC IGYWCL: `LNGPRFX='IGY650'`,
  `LIBPRFX='CEE'`; COBOL step STEPLIB IGY650.SIGYCOMP, CEE.SCEERUN, CEE.SCEERUN2, DSND10.DBDG.SDSNEXIT,
  DSND10.SDSNLOAD; SYSUT1-15 + SYSMDECK work files; SYSLIN &&LOADSET (temporary, the proc deletes it in LKED).
- Site options in effect (relevant): CODEPAGE(1140) (= CP037 + euro: matches the IBM-037 upload), DATA(31),
  RMODE(AUTO), RENT, TRUNC(STD), NUMPROC(NOPFD), ARITH(COMPAT), NODYNAM, QUOTE, ARCH(11), OPTIMIZE(0), OUTDD(SYSOUT),
  NOSSRANGE, NOINITCHECK, FLAG(I,I), SEQUENCE. PACHELLO: no statements flagged, RC 0.
- Binder: IEWBLINK, SYSLIB CEE.SCEELKEX + CEE.SCEELKED (+ DB2 libraries); PACHELLO saved as PROGRAM OBJECT FORMAT 3
  in Z00000.PACMAN.LOAD, "ADDED NEW", AMODE 31 / RMODE ANY (no AMODE/RMODE given); IEW2008I RC 0.
- No assembler PROC used: J3/J4 call ASMA90 directly (HLA.SASMMOD1, SYS1.MACLIB, SYS1.MODGEN).
Open after J2: AMODE 24 viability (J3), HLASM / binder procedure (J3/J4), DISPLAY / SYSOUT format (J3/J4 SYSOUT),
listing translator on a real multi-step run (J3/J4).
