# PACMAN z/OS - target environment (ZOS-0, 2026-10-14; parts A/B/C done, D/E pending)
Evidence: docs/evidence/zos0-discovery.md. Credentials: Zowe secure store only, never in git.

| Item | Value | Status |
|---|---|---|
| System | IBM Z Xplore, shared non-production; system S0W1 (S0W1.DAL-EBIS.IHOST.COM), host 198.51.100.200 | user + B2 |
| z/OS | V3R1 (`zos_version 05.29.00`), z/OSMF 29.0 | B2 |
| Userid / HLQ | Z00000; project prefix Z00000.PACMAN (does not exist yet) | user + B3 |
| Zowe | CLI 8.39.0 (v3.6.0); profiles zosmf (10443), tso (FB3, IZUFPROC, cp 1047), ssh, rse, zftp; cics* out of scope | B1 |
| Enterprise COBOL | IGY420 (4.2), IGY640 (6.4), IGY650 (6.5) cataloged; IGYWCL reported 6.5 by the user's ZHEIST deck | B4/B5, confirm in ZOS-1 |
| LE | CEE.* (SCEELKED, SCEERUN, SCEERUN2, SIBMAM24, ...); TSO (IZUFPROC) allocates a site CEEOPTS | B4/B7 |
| HLASM | HLA.SASMMOD1/2, HLA.SASMMAC1/2; no assembler PROC in user examples | B4/B5 |
| Macros | SYS1.MACLIB, SYS1.MODGEN (PDS FB 80) | B4 |
| Dataset types | PDSE default for user libraries; PDS present on user volumes (CICS.SYSIN, ISPPROF) | B3 |
| Job card | CLASS=7, NOTIFY=&SYSUID, no MSGCLASS in any example (site default) | B5/B6 |
| TSO (z/OSMF) | IZUFPROC: STEPLIB ZXP.PUBLIC.LOAD, SYSPROC VENDOR.CLIST + ZXP.PUBLIC.CLIST + ISP | B7 |
| TN3270 | 198.51.100.200:623 plain TN3270E (no TLS), LU TCP00906, IBM-3278-4-E accepted, USS 24x80 | C |
| Interactive TSO / READY / logmode size | pending (step D, user) | D |
| Submit + spool | pending (step E, IEFBR14) | E |
