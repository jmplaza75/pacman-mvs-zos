# ZOS-1 toolchain evidence (2026-10-14) - COMPLETE (tag zos-1)
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

## 7. Probe correction before upload (user review)
ZHELLOA made genuinely reentrant (leaf routine: no static save area, no chaining, R13 unchanged, registers saved in
the caller's save area, entry R13 still recorded); RENT added explicitly to the COBOL options and to the binder in J3
and J4. TAM / BSM logic unchanged. Uploads: COBOL(ZHELLOC) 93 records and ASM(ZHELLOA) 56 records, both byte-identical
to their IBM-037 fixed-80 records after binary download.

## 8. J3 PACZPRFA (profile A) - JOB08331, CC 0000: PASS
- COB IGYCRCTL RC 0 (`RENT,RMODE(24),DATA(24),NODYNAM,TRUNC(STD),NUMPROC(NOPFD)`; no statements flagged); ASM ASMA90
  (HLASM R6.0, PTF UO07449) RC 0, no statements flagged; BIND IEWBLINK RC 0, `LIST,MAP,XREF,AMODE=24,RMODE=24,RENT`,
  no IEW warning / error, PROGRAM OBJECT FORMAT 3 ZHELLO24 ADDED NEW: **AMODE 24, RMODE 24, RENT YES, REUS YES, REFR
  NO**; LE pieces resolved from SCEELKED (CEESTART, IGZX*). RUN1 / RUN2 RC 0 with `CEEOPTS ALL31(OFF),STACK(,,BELOW)`;
  no CEE message, no abend, no CEEDUMP produced.
- RUN1: `ZH PARMLEN=025`, `ZH PARM=TSO AI1 1 NAAAPAAARAA01NP` (exact); **TAM=0, BSM=0** (agree: AMODE 24);
  PARM1 = 299520, CSECT = 36416, SAVEA = 155696: all **BELOW** 16 MB. RUN2: PARMLEN 000, empty PARM, same readings.
## 9. J4 PACZPRFB (profile B) - JOB08335, CC 0000: PASS
- COB RC 0 (`RENT,NODYNAM,TRUNC(STD),NUMPROC(NOPFD)`, site DATA(31) / RMODE(AUTO)); ASM RC 0; BIND RC 0
  `AMODE=31,RENT`: **AMODE 31, RMODE 24** (the RMODE 24 ZHELLOA CSECT keeps the module below the line), RENT YES,
  REUS YES. RUN1 / RUN2 RC 0, no CEE message, no abend.
- **TAM=1, BSM=1** (agree: AMODE 31); PARM1 = 458306072 ABOVE, CSECT = 36416 BELOW, SAVEA = 458174512 ABOVE; PARM echo
  exact (025 / 000).
## 10. DISPLAY / SYSOUT format (both jobs)
- DISPLAY output DD SYSOUT: **RECFM FBA, LRECL 121** (ASA byte + 120 data characters). An 80-character line is one
  record; the 130-character line is **split into two records (120 + 10)**, nothing lost. The CHARS line
  (` !"#$%&'()*+,-./0-9:<=>?@A-Z` + `cdelopqru`) arrives intact.
- Impact on Pac-Man: the longest line in the 2.0 oracle (tests/oracle20, all 8 jobs) is exactly 120 characters; no
  2.0 DISPLAY line exceeds 120, so the 121-byte record holds every line. To keep checked in ZOS-2 (any line > 120
  would be split).
- Other spool formats: COBOL SYSPRINT FBA 133, HLASM SYSPRINT FBM 133, binder SYSPRINT FBA 121, JESMSGLG UA 133,
  JESJCL V 136, JESYSMSG VA 137.
## 11. Listing translator on real multi-step jobs
tools/zowe/zos_listing.py on JOB08331 / JOB08335: the test-style step regex (`<JOB>\s+(\w+)\s+(\S+)\s+RC= (\d{4})`)
yields the five steps with their programs and RC 0000; ASA control removed ('1' -> form feed); no IKF / IGY W/E/S
lines; RUN output equals the expected probe lines (addresses aside).
## Status of the ZOS-1 questions
- Enterprise COBOL release of the site procedure: **6.5.0 P260714** (J2).
- HLASM / binder procedure: **established** (J3/J4: IGYCRCTL + ASMA90 + IEWBLINK with SCEELKEX / SCEELKED).
- DISPLAY / SYSOUT format: **FBA 121** (sec. 10).
- Listing translator: **works** on real jobs (sec. 11); full-size validation in ZOS-2.
- PDS for PACMAN.DATA: **yes** (J1).
- AMODE 24: the COBOL 6.5 / HLASM / LE **toolchain probe** runs correctly in AMODE 24 (RMODE 24, DATA(24),
  ALL31(OFF), STACK BELOW) and in AMODE 31. This is NOT a proof for the complete Pac-Man module (TPUT / TGET /
  STFSMODE / ESTAE / BPAM paths, size, LE services); that is established in ZOS-2 / ZOS-3.
Jobs of ZOS-1: JOB08252 (J1), JOB08254 (J2), JOB08331 (J3), JOB08335 (J4); none purged.

## Closure (approved by the user 2026-10-14)
ZOS-1 PASS. Recorded: Enterprise COBOL 6.5.0 P260714; HLASM R6.0; IEWBLINK toolchain; DISPLAY output FBA / LRECL 121
with a 120-character safe oracle limit; IBM-037 round trip successful (23 release members + 2 probes); DATA viable as a
PDS; listing translator working; J3 AMODE 24 PASS and J4 AMODE 31 PASS (toolchain probe only). Build profile A = D45
(docs/zos-build.md). Open into ZOS-2: candidate C1 (PACQRY paragraph VALIDATE); AMODE 24 for the full module;
full-size listing translation.
