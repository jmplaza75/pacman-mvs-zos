# ZOS-0 discovery evidence (2026-10-14): parts A, B, C, D, E
Authorised by the user step by step: A (local), B (read-only z/OS), C (TN3270 to the welcome screen), D (manual TSO
logon by the user), E (one IEFBR14 without DD, shown in full and approved). Nothing was uploaded, allocated,
modified, deleted or purged on z/OS; the only job submitted is JOB08215 (E), left on the spool. No credential is
recorded here; the Zowe secure store supplied them. Raw outputs: build/zos0/ (gitignored, local).

## A. Local
- A1 `tools/validate_source.py`: OK. All 24 tests/test_*.py local checks PASS on branch `zos` (PACMAN_LATER_PHASE=G8).
- A2 oracle freeze: `tools/oracle_extract.py` -> `tests/oracle20/` (8 jobs, 1.2 MB gzip, reproducible byte for byte,
  `SHA256SUMS` sha256 95d94e8fcd81f0c39395399d79b605a145bef1195383aacc4c1cd749a28938b0). Source listings read only
  from the MVS checkout's build/ (JOBs 307-312, 315, 316). No live trace, no credential (grep PASSWORD/TK4_/.env = 0).
  Proof that the oracle alone carries the functional result: the renders pass the 2.0 acceptance unchanged:
  `tests/test_g8.py --rel20 --s2 --rp --gp2 --gp23 --hs` (REL20 60 steps + 1.0 oracle + CLIST PARMs; S2 2986 streams;
  RP3 1495 streams + 9 BAT; HS + GP23 + GP2 chain) and, on the installed prefix, `--oracle 315 --s2 316` (25 1.0 blocks
  = REL20; S2 = model); stream 316 = stream 308 apart from the load-library name.
  Design notes: the TK4- printer does not start every SYSOUT dataset on a new page, so the oracle is one ordered
  program-output stream per job (lines right-stripped, split like the tests split a listing) plus the step table; JES
  log, JCL, system messages and the JES2 end separator page are dropped; build listings stay (RP compiles PACQRYT
  after its run-only marker).
- A3 `tools/zos_reserved_scan.py`: 32 COBOL files, 2173 user-defined names, **1 hit: paragraph `VALIDATE` in
  src/cobol/PACQRY.cob (lines 89-106, `PERFORM VALIDATE THRU VALIDATE-EXIT`)**. VALIDATE is reserved in Enterprise
  COBOL 6. Expected to fail compilation in ZOS-2 (PACQRY is display layer, not core). Not fixed (R1); decision needed
  then (rename on `main` = shared-source change with MVS regression, or a z/OS override with a Z-entry).
- A4 codepage: the characters used in code (comments excluded) in src/ are
  `space ! " # $ % & ' ( ) * + , - . / 0-9 : < = > ? @ A-Z` and lowercase `c d e l o p q r u`. None differs between
  CP037 and CP1047 (the differing set is `[ ] ^ ¬ Ý ¨`; `[ ]` occur only in comments). The 2.0 TSD streams already
  equal the cp037-encoding models byte for byte, so the Hercules reader table agrees with CP037 on every character
  that reaches a screen (`"` eyes glyph, `!` of READY!, lowercase `o` power pellet in PACMAP, input letters).
  Conclusion: upload encoding IBM-1047 or IBM-037 gives the same bytes for the code; comment bytes may differ and do
  not matter. Byte identity is still proved by binary download in ZOS-1.

## B. z/OS read-only discovery (Zowe CLI 8.39.0 / Zowe v3.6.0, profile zosmf)
- B1 profiles: zosmf, tso, ssh, rse, zftp, cics, cicsZXP, global_base (names only).
- B2 `zowe zosmf check status`: system **S0W1** (S0W1.DAL-EBIS.IHOST.COM), **z/OS V3R1** (`zos_version 05.29.00`),
  z/OSMF 29.0, API 1; plug-ins include ISPF, Workflow, z/OS Operator Consoles.
- B3 own datasets `Z00000.**`: 46 entries, no `Z00000.PACMAN.*`. PDSE (`dsntp LIBRARY`, PO-E): CBL, JCL, LOAD
  (U/0/4096), SOURCE, INPUT, OUTPUT, ZHEIST.*; true **PDS** exist (`Z00000.CICS.SYSIN` FB/80/400,
  `Z00000.S0W1.ISPF.ISPPROF`): PDS allocation on the user's volumes has happened, so DATA as PDS looks possible
  (confirmed only when ZOS-1 allocates). Other project present: `Z00000.ZHEIST.*` (not to be touched). CICS VSAM
  under `Z00000.CICS.*` (out of scope).
- B4 toolchain catalog:
  - Enterprise COBOL: **three releases** cataloged: `IGY420.*` (V4.2), `IGY640.*` (V6.4), `IGY650.*` (V6.5), each
    with SIGYCOMP / SIGYPROC; `IGY.**` itself is empty.
  - LE: `CEE.*` incl. SCEELKED, SCEELKEX, SCEERUN, SCEERUN2, SCEEBIND, SCEEMAC, SCEEPROC, **SIBMAM24** (AMODE 24
    support library).
  - HLASM: `HLA.SASMMOD1/2`, `HLA.SASMMAC1/2` (no `ASM.*`).
  - Macros: SYS1.MACLIB and SYS1.MODGEN, PDS FB 80, master catalog.
- B5 examples (search only; three members viewed):
  - `IGYWCL` used by Z00000.JCL(JCL2), (JSONJCL) and Z00000.ZHEIST.JCL(ZH95BLD), whose comment says
    "VERIFIED IGYWCL: ENTERPRISE COBOL 6.5, LE CEE" (user's earlier project: a lead, to confirm with a compile listing
    in ZOS-1). Procedure steps COBOL / LKED; LKED.SYSLMOD into a PDSE LOAD; run steps with `STEPLIB &SYSUID..LOAD`,
    `CEEDUMP DD DUMMY`, `SYSOUT DD SYSOUT=*,OUTLIM=15000`.
  - No example uses ASMA90 / ASMAC* (no assembler PROC evidence in the user's datasets).
  - JOB cards: `CLASS=7` in every user job that sets a class (JSONJCL, MERGSORT, PDS1CCAT, ZH95*), `NOTIFY=&SYSUID`,
    `MSGLEVEL=(1,1)` / `(2,0)`; **no example sets MSGCLASS** (site default applies). Accounting: none, `1` or `FB3`.
- B6 own jobs: 9 listed; class 7 x7 (CC 0000 x6, CC 0008 x1), 1 TSU (TSO session, ACTIVE), 1 C4Z (CICS region,
  ACTIVE). Nothing purged.
- B7 `LISTALC STATUS` (z/OSMF TSO, proc IZUFPROC): STEPLIB ZXP.PUBLIC.LOAD; **CEEOPTS** allocated (temporary
  `Z00000.Z00000.TSU08188...`, site LE runtime options for TSO); SYSEXEC ZXP.PUBLIC.EXEC + ISP/SYS1/ISF execs; SYSPROC
  VENDOR.CLIST, ZXP.PUBLIC.CLIST, ISP.SISPCLIB, SYS1.SBPXEXEC; ISPF libraries; SYSOUT / CEEDUMP / SYSUDUMP = NULLFILE.
  Note: this is the z/OSMF TSO address space; the interactive 3270 logon proc may allocate differently (step D).
- No access denied in any B command.

## C. TN3270 (s3270 4.5ga6, no logon, no input)
- `L:198.51.100.200:623` (TLS): **SSL_connect failed, connection reset by peer** -> port 623 does not speak TLS
  (not a certificate issue; `-noverifycert` not used).
- `198.51.100.200:623` (plain, one attempt): connected, **TN3270E** (`connected-tn3270e`), `Query(Tls)` = not
  secure. Device type requested IBM-3278-4-E, accepted; LU **TCP00906**; functions BIND-IMAGE RESPONSES SYSREQ
  CONTENTION-RESOLUTION. Pre-logon (USS) BIND: PLU `TELNET`, default 24x80, alternate 24x80. Welcome screen: Z Xplore
  / "IBM Z, The Next Generation", prompt `Enter "logon" followed by the TSO userid`. Disconnected without input.
- Consequence: the 3270 path is unencrypted; the TSO password typed by the user in D travels in clear over the
  internet (site design, outside the project's control; noted for the user).
- The TSO session BIND (logmode, alternate size) and the Query Reply are only visible after logon: step D (user) and
  ZOS-5 (probe), not ZOS-0.

## D. Manual TSO logon (by the user, 2026-10-14)
`c3270 -model 2 -oversize auto 198.51.100.200:623`, `logon Z00000`: logon succeeded; **no ISPF menu appeared, the
session reached TSO `READY` directly**; c3270 window 120 x 30; no unusual site messages. (The negotiated logical
screen size / logmode of the TSO session was not captured; it is read by the ZOS-5 probe capture.) Claude typed
nothing in the session and entered no password. Result: PASS.

## E. One IEFBR14 (JCL approved verbatim by the user)
```
//Z00000B  JOB 1,'PACMAN ZOS0',CLASS=7,MSGLEVEL=(1,1),
//             NOTIFY=&SYSUID
//BR14     EXEC PGM=IEFBR14
```
`zowe zos-jobs submit local-file build/zos0/BR14.jcl --wait-for-output`: **JOB08215, CC 0000**, status OUTPUT. Spool
read with `zowe zos-jobs view all-spool-content`: JESMSGLG, JESJCL, JESYSMSG (36 print records, 2 KB).
- `$HASP373 Z00000B STARTED - INIT 1 - CLASS 7 - SYS S0W1`, `$HASP395 Z00000B ENDED - RC=0000`; JES2 node SVSCJES2.
- Step table in JESMSGLG: `-STEPNAME PROCSTEP RC EXCP ...` / `-BR14 00 ...`; JESYSMSG `IEF142I Z00000B BR14 - STEP
  WAS EXECUTED - COND CODE 0000`, `IEF373I` / `IEF032I` / `IEF375I` / `IEF033I` (z/OS replaces TK4- IEF374I/IEF376I
  and the TK4- IEFACTRT table: the ZOS-1 listing adapter maps IEF142I / the JESMSGLG step table).
- `IEFC653I SUBSTITUTION JCL ... NOTIFY=Z00000`; `IEFA111I ... SWA=BELOW,TIOT SIZE=32K,DSENQSHR=DISALLOW,GDGBIAS=JOB`.
- No MSGCLASS given: the site default class held the output and Zowe retrieved it. Job not purged.
Result: PASS (submit, wait, spool retrieval proven).

## Classification of findings (plan ZOS-0 exit criteria)
- Blocking: none.
- To resolve in ZOS-1 (toolchain): which Enterprise COBOL release the build uses (IGYWCL reportedly 6.5; 4.2 and 6.4
  also cataloged) and its exact level from a compile listing; AMODE 24 viability with that release (LE SIBMAM24
  present); no assembler PROC in use -> explicit ASMA90 step (HLA.SASMMOD1); SYSOUT DCB / record format of DISPLAY;
  listing adapter (IEF142I, JESMSGLG step table, per-DD spool) to the shape the tests parse; upload encoding (any of
  IBM-037 / IBM-1047 gives the same code bytes, proved by binary download); DATA as PDS (allocation proves it).
- Expected compile issue (ZOS-2): `VALIDATE` paragraph in PACQRY (docs/ZOS-DIFFS.md C1).
- Runtime to characterise later: site CEEOPTS (LE options) in TSO (ZOS-3 / ZOS-8 ESTAE); TSO session logmode and
  Query Reply (ZOS-5); network jitter of the internet 3270 path (ZOS-6).
- Security note (site design): TN3270 on 623 is unencrypted; the TSO password travels in clear.
