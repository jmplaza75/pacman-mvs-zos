# PACMAN z/OS - target environment (ZOS-0, 2026-10-14; parts A-E done)
Evidence: docs/evidence/zos0-discovery.md. Credentials: Zowe secure store only, never in git.

| Item | Value | Status |
|---|---|---|
| System | IBM Z Xplore, shared non-production; system S0W1 (S0W1.DAL-EBIS.IHOST.COM), host 198.51.100.200 | user + B2 |
| z/OS | V3R1 (`zos_version 05.29.00`), z/OSMF 29.0 | B2 |
| Userid / HLQ | Z00000; project prefix Z00000.PACMAN (does not exist yet) | user + B3 |
| Zowe | CLI 8.39.0 (v3.6.0); profiles zosmf (10443), tso (FB3, IZUFPROC, cp 1047), ssh, rse, zftp; cics* out of scope | B1 |
| Enterprise COBOL | IGY420 (4.2), IGY640 (6.4), IGY650 (6.5) cataloged; site IGYWCL = **6.5.0 P260714** (LNGPRFX IGY650), CODEPAGE(1140), DATA(31), RMODE(AUTO), RENT, TRUNC(STD), NUMPROC(NOPFD) | ZOS-1 J2 |
| LE | CEE.* (SCEELKED, SCEERUN, SCEERUN2, SIBMAM24, ...); TSO (IZUFPROC) allocates a site CEEOPTS | B4/B7 |
| HLASM | HLA.SASMMOD1/2, HLA.SASMMAC1/2; no assembler PROC in user examples | B4/B5 |
| Macros | SYS1.MACLIB, SYS1.MODGEN (PDS FB 80) | B4 |
| Dataset types | PDSE default for user libraries; Z00000.PACMAN.DATA allocated as a true PDS (FB/80/80); site ACS reduces allocations > 200 KB (IGD01007I ZXPACS) | B3, ZOS-1 J1 |
| Job card | CLASS=7, NOTIFY=&SYSUID, no MSGCLASS in any example (site default) | B5/B6 |
| TSO (z/OSMF) | IZUFPROC: STEPLIB ZXP.PUBLIC.LOAD, SYSPROC VENDOR.CLIST + ZXP.PUBLIC.CLIST + ISP | B7 |
| TN3270 | 198.51.100.200:623 plain TN3270E (no TLS), LU TCP00906, IBM-3278-4-E accepted, USS 24x80 | C |
| Interactive TSO | logon OK, no ISPF, TSO READY directly; c3270 window 120 x 30; logical size / logmode not yet captured (ZOS-5) | D |
| Submit + spool | IEFBR14 JOB08215 CC 0000, CLASS 7 INIT 1, JES2 node SVSCJES2, spool JESMSGLG/JESJCL/JESYSMSG via Zowe; no MSGCLASS needed | E |
| Project datasets | Z00000.PACMAN.{COBOL,COPY,ASM,CLIST,OBJ,LOAD} PDSE + DATA PDS (J1 JOB08252); 23 sources uploaded IBM-037, identical | ZOS-1 |
| Binder | IEWBLINK, SYSLIB CEE.SCEELKEX + CEE.SCEELKED; program objects FORMAT 3 in PDSE | ZOS-1 J2 |
