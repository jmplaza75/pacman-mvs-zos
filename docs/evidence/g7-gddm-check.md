# MVS-G7 host graphics - GDDM check and negative close (2026-10-14, D42)
Paper phase (docs/ROADMAP-POST-RT.md row 7): close negative on the existing terminal evidence plus one read-only
check for a GDDM load library on the installed TK4- system. Nothing of PACMAN was built, changed or installed.

## 1. Terminal side (existing evidence, not re-run)
- E5 Query Reply (JOB 156, docs/evidence/g1-probe-analysis.md; byte-identical in E9 / E10): QCodes 80 81 84 85 86 87
  88 95 A1 A6 only (summary, usable area, alphanumeric partitions, character sets, colour, highlight, reply modes,
  DDM, RPQ names, implicit partition). No graphics-related query reply, so a host graphics program (GDDM / GOCA)
  would find no graphics-capable device and fall back to alphanumeric output at best.
- c3270 4.5ga6 manual page (`man c3270`): 0 matches for `graphic|gddm|goca|vector`. The x3270 family emulates
  alphanumeric 3270/3279 displays only; G5 (D30) already showed c3270 rejects the Load PS structured field, which
  GDDM itself would use for image/symbol output on PS terminals.

## 2. Host side: read-only check (jcl/mvs/G7CHK.jcl)
JOB 300 (PACG7C01) first pass; JOB 301 (PACG7C02) extended to every LNKLST00 library = the evidence of record.
Steps: IDCAMS `LISTCAT ALIAS` + `LISTCAT NONVSAM NAME`; IEBGENER of SYS1.PARMLIB(LNKLST00); IKJEFT01 `LISTDS ...
MEMBERS` of the eight libraries below. All three steps RC 0000 in both jobs. Only reads; no dataset written.

```
11.55.02 JOB  301  PACG7C02   CAT                 IDCAMS    RC= 0000
11.55.02 JOB  301  PACG7C02   LNKLST              IEBGENER  RC= 0000
11.55.02 JOB  301  PACG7C02   TSO                 IKJEFT01  RC= 0000
```

LNKLST00: SYS1.LINKLIB, SYS1.PPLIB, SYS1.CMDLIB, SYS2.LINKLIB, SYS2.CMDLIB, SYS1.PL1LIB, SYS2.DSSLIB.
Catalog: one master catalog (`USERCATALOG 0`), 140 non-VSAM names, 26 aliases:
ALGOL DUCHESS EREP EXH FSI GTF HERC01-04 IPCS JCC KLINGON MAP3270 MVS PASCAL PDPCLIB PL360 RAKF RPF SCRIPT SMF
SYS1.ZMACLIB SYS2.Z9MACLIB TK4- WATFIV.

Scan (`python3 tools/g7_gddm_scan.py build/PACG7C02.txt`, exit 0 = nothing found); GDDM modules are named ADM*,
also searched GDDM / GKS / GOCA / PGF / ICU / IPDS prefixes and GDDM / ADM / GKS / GOCA / PGF in dataset names:

| Library | Member + alias names | GDDM-like |
|---|---|---|
| SYS1.LINKLIB | 959 | none |
| SYS2.LINKLIB | 476 | none |
| SYS1.LPALIB | 1584 | none |
| SYS2.CMDLIB | 217 | none |
| SYS1.CMDLIB | 295 | none |
| SYS1.PPLIB | 5 | none |
| SYS1.PL1LIB | 524 | none |
| SYS2.DSSLIB | 17 | none |
| Catalog (140 non-VSAM + 26 aliases) | 166 | none |

Scanner self-check (D12, not vacuous): a copy of the listing with a member `ADMASP ALIAS(ADMASPX)` inserted in
SYS1.LINKLIB is reported (2 hits); a copy with alias KLINGON renamed GDDM is reported and exits 1.
A parser bug on the first pass (wrapped alias lines ended a member list early: 80 of 959 names) was found by a
line-count cross-check and fixed before the result above.

## 3. Result
NEGATIVE CAPABILITY CLOSURE, not a failed implementation (closure approved by the user 2026-10-14; D42 and JOB 301
are the evidence of record). No GDDM (or other host graphics subsystem) is installed on TK4- MVS 3.8J, and c3270 announces and documents
no graphics capability. GDDM is a licensed IBM program product, not part of the MVS 3.8J public-domain distribution;
requirements sec. 29 forbid adding such a subsystem without verified availability and legal use. G7 closes negative;
the existing 3270 scaled / glyph renderer (GS 4x2 over G4 glyphs) remains the final graphics solution for MVS.
Installed baseline unchanged: PACMAIN = JOB 298 link, CLIST = JOB 299.
Future option, not pursued (same as D30): a graphics-capable terminal plus a licensed host stack, in a separate branch.
