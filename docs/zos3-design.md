# ZOS-3 Platform layer - design / reconnaissance (for review, nothing executed)
Basis: docs/ZOS-MIGRATION-PLAN.md sec. 4 (module matrix), 6 (ZOS-3), 9 (assembler risks), 10 (high score), 11 (ESTAE),
12 (query); module headers of src/cobol/PACPLAT.cob, src/asm/PACTSO.asm, PACFSIO.asm, PACHSIO.asm; ZOS-2 evidence
(tag zos-2 on f426858). Preserved: LOAD(PACZ2D) of JOB08888, profile A, every oracle, 2.0-mvs-max, ZOS-2 evidence.

## 1. What belongs to ZOS-3 (plan sec. 6)
Every host service behind PACPLAT keeps its 2.0 contract (RC values, lengths, units) on z/OS, in batch and TSO batch
(IKJEFT01). **Live acceptance: none** - the first live TSO session is ZOS-4, the first live full-screen ZOS-5.
- PACTSO CLS / WAIT / TIME / DLWT; PACFSIO in batch (RC 4 = not a TSO session, nothing issued) and under IKJEFT01;
  PACHSIO READ / REPL / WRIT on a test PDS incl. error paths; PACPLAT TSD output (batch dry run of the full-screen
  path, no terminal).
- Allowed to change: src/zos/PACTSO|PACFSIO|PACHSIO.asm, src/zos/PACPLAT.cob only if forced (Z-entry each); probes
  under src/probe/zos/; decks, tools, docs. Frozen: core, PACSCR, PACQRY, PACDISP, PACINPT, PACMAIN, copybooks, CLIST.
- Exit: decks = models / oracle; each service RC contract proven incl. error paths (missing DD, missing member, empty /
  garbage member, full directory); every override justified or none needed. Checkpoint tag `zos-3`.

## 2. Modules and interfaces
| Module | Contract (from its header) | Host facilities |
|---|---|---|
| PACPLAT (COBOL) | INIT / FINI / CLS / SEND / RECV / FSOF / WAIT / POLL / CLOK / WDLN / DLWT / HSRD / HSWR; INIT validates REQ-MODE (BAT, TSO, TSD); TSO + COLOR A/Y tries FSON (any failure = TSO line mode); TSD SEND prints the stream in hex (TSX lines = transport decisions) | calls PACTSO, PACFSIO, PACHSIO, PACQRY |
| PACTSO (asm) | CALL OP RC [MS]: CLS (STLINENO 1), WAIT (STIMER 3 s), TIME (STCK ms since first call), DLWT (STIMER WAIT MICVL until the deadline, RC 4 if passed); RC 4 = not TSO (ASCBTSB = 0) for CLS / WAIT | ASCB / TSB, STLINENO, STIMER, STCK |
| PACFSIO (asm) | CALL OP BUF LEN RC: FSON (TCLEARQ, STFSMODE ON, STTMPMD ON, ESTAE), QRY (TPUT NOEDIT WSF Read Partition Query, TGET ASIS), SEND / SENP / SENX (TPUT FULLSCR / NOEDIT), RECV / RECT / POLL (TGET ASIS [NOWAIT]), FSOF (ESTAE cancel, line mode restored); RC 0 / 4 not TSO / 8 / TPUT-TGET RC | TPUT, TGET, STFSMODE, STTMPMD, STLINENO, TCLEARQ, ESTAE, STIMER |
| PACHSIO (asm) | CALL OP RC DDN REC: READ / WRIT / REPL of one 80-byte record in a PDS member; RC 0 / 2 new / 4 no DD / 8 unusable / 12 missing-empty / 16 I/O error or abend caught / 20 bad op; never abends the caller | RDJFCB, OPEN TYPE=J (JFCNWRIT), BLDL, FIND, BPAM READ, QSAM UPDAT / OUTPUT, STOW at CLOSE, ESTAE + retry |
| PACQRY / PACQRYT, PACTSOT | pure parsing / test drivers | none / PACTSO |
Interfaces: PACREQ (REQ-OP, REQ-MODE, colour / hilite / glyphs / scale / sound / time fields, COMP binary shared with
assembler), PACDS (data stream buffer). Only PACPLAT calls assembler.

## 3. Already proved by ZOS-2 - not retested
- PACTSO TIME / DLWT real clock (STCK, STIMER WAIT MICVL): DRV TSOT1, RT3 rules, lateness 0-1 ms.
- PACTSO CLS in batch (ASCBTSB = 0 -> RC 4, nothing issued): every TSO line-mode run of C7 / G1 / G3 / ST0 / STF.
- PACQRY parsing and the 29 D40 startup sequences: DRV QRY1.
- PACPLAT BAT / TSO line-mode paths, LE PARM passing, SYSIN / SYSOUT, REALTIME batch quanta, ESTAE-free core, LE
  storage independence (ST0 / STF), AMODE 24 linkage COBOL -> assembler (PACTSO executed).
- C3 static facts: the only reference inside PACFSIO's USING ABEXIT,15 range, `S 12,ABOFF`, resolves to base R15.

## 4. Not yet executed on z/OS (found in this reconnaissance)
- **PACFSIO has never run on z/OS.** No ZOS-2 run had TSO mode with COLOR A/Y (PARM column 12). The frozen oracles
  hold exactly two such runs: oracle 310 S1S3 `TSO AI0    AAAPAAAAY` and oracle 308 S2L4 `TSO AI0    AAAPAAAAYC01NP`
  (COLOR A): PACPLAT INIT calls PACFSIO FSON, which in batch must return RC 4 without issuing anything, and the game
  falls back to TSO line mode (expected output = the DIE1 TSO transcript, already PASS as C7 TSO2). These runs were
  left out of ZOS-2 as "SOUND ignored"; in ZOS-3 their value is the PACFSIO batch contract, not sound.
- **PACHSIO has never run on z/OS** beyond assembly (JOB08888): no HS run yet.
- **PACPLAT TSD SEND** (hex streams, SENX / SENP decisions, canvas simulation) has never run on z/OS.
- **PACTSO WAIT** (STIMER BINTVL) is only reached in TSC.

## 5. TGET / TPUT, terminal detection, query, recovery on z/OS
- Detection: PACTSO / PACFSIO read PSAAOLD (X'224') -> ASCB, ASCBTSB (X'3C'): non-zero only in a TSO logon address
  space. Plain batch and **IKJEFT01 in batch both have ASCBTSB = 0** (no terminal) -> RC 4, nothing issued. So TSO
  batch exercises the TMP (CALL, ALLOC, CLIST commands) but **not** TPUT / TGET / STFSMODE / STTMPMD / TCLEARQ. Those
  run for the first time in a live TSO session (ZOS-4 line mode: STLINENO / TPUT path of CLS; ZOS-5: FSON, QRY, SEND,
  RECV, FSOF). Risk sec. 9 #1 (24-bit TPUT/TGET register forms) is covered by profile A (AMODE 24, buffers below the
  line); risk #2 (ASCBTSB offset) is proved for the RC 4 side by ZOS-2 and needs the RC 0 side live.
- Query: unchanged path (FSON -> QRY: TPUT NOEDIT WSF -> TGET ASIS -> PACQRY D40 selection); the real z/OS reply is
  captured first in ZOS-5 (tests/qreply_zos_*.hex, run through PACQRYT in batch before the live game).
- Recovery: PACFSIO's ESTAE (FSON) restores line mode and percolates; PACHSIO's ESTAE retries into RC 16 and is deleted
  before every return. Inside an LE enclave (TRAP(ON)) the most recent ESTAE (the assembler's) gets control first for
  a system abend in its own I/O (B14, X37, 013). The PACHSIO full-directory case (HH1: STOW at CLOSE fails, NOT SAVED,
  game RC 0) is the first **batch** proof of an ESTAE + retry on z/OS. PACFSIO's exit can only be reached after a
  successful FSON (live TSO) - ZOS-8 E1-E3 (forced abend PACRPE).

## 6. C3 (PACFSIO ASMA303W) investigation
- Static (ZOS-3, local, no job): from the JOB08497 / JOB08888 listings, list every statement between `USING
  ABEXIT,15` (stmt 343) and `DROP 15` (stmt 347) and its resolved base; confirm `S 12,ABOFF` (5BC0 F014) is the only
  storage reference there and that no statement after the DROP resolves through R15; compare the object code of the
  exit with the IFOX00 assembly on MVS (MVS listing of record, if retained) for byte identity.
- Dynamic: the exit runs only on an abend after FSON, i.e. live full-screen -> ZOS-8 E2 (PACRPE forced abend, then a
  clean game). No change to PACFSIO to silence the warning (C3 rule).

## 7. Batch versus live
| Behaviour | ZOS-3 batch / IKJEFT01 | Live |
|---|---|---|
| PACFSIO not-TSO contract (FSON RC 4, fallback to line mode) | yes (S1S3 / S2L4 PARMs) | - |
| PACFSIO FSON / QRY / SEND / RECV / POLL / FSOF, ESTAE exit | no (needs a TSB) | ZOS-5 / ZOS-6 / ZOS-8 |
| PACTSO CLS / STLINENO, WAIT | RC 4 path only (done in ZOS-2) | ZOS-4 (CLS), ZOS-5 (WAIT) |
| PACHSIO READ / REPL / WRIT, error paths, ESTAE retry | yes (HS deck, test PDSs) | ZOS-8 (installed DATA) |
| PACPLAT TSD SEND (hex streams) | yes (TSD dry runs, no terminal) | - |
| TMP: CALL, ALLOC F(PACHS) in IKJEFT01 | yes (HS HTSO steps) | ZOS-4 (CLIST) |

## 8. Proposed minimum ZOS-3 sequence (each job: full JCL + matrix reviewed before submission)
0. Local only: (a) C3 static analysis; (b) oracle 312 anchoring: HA1 follows the HSFILL IEBUPDTE listing after ONE
   empty line (stream line 149) - 18 run datasets for 19 PACMAIN steps, so no 312 step anchors today; an RP-like
   digest-bound KNOWN_BOUNDARIES entry would need the user's approval; (c) the z/OS form of the HS deck (below).
1. PACZ3FS - PACFSIO batch contract: S1S3 (oracle 310) and S2L4 (oracle 308) as TSO + COLOR(AUTO) runs on PACZ2D:
   RC 0, output = own oracle block = test_mvs8 DIE1 transcript; small (~720 lines).
2. PACZ3HA - one-time allocation of the HS test PDSs (PDS, FB 80/80, as DATA): needs a decision, because the MVS HS
   deck deletes and re-creates <prefix>.HSTEST / HSFULL / HSCL.DATA (DISP=(MOD,DELETE)), which the z/OS rules forbid.
   Options: (i) one fresh, never-deleted set per attempt (e.g. HSTEST.T1, HSFULL.T1), (ii) an explicit user
   authorisation to delete only those project test datasets. The member state carries from step to step, so a
   partial rerun needs a fresh set either way.
3. PACZ3HS - HS batch runs HA1..HH1 (19) + HTSO1/2 (IKJEFT01, ALLOC + CALL) against oracle 312 and tests/ref_hs.py,
   split under the 4,000-line budget only where the member state allows it; the CLIST-block check (HSCLS / HSCLT) is
   CLIST work -> ZOS-4.
4. PACZ3TSD - TSD: the plan lists the TSD runs of the GS / GX / G4 decks for ZOS-3; a minimum subset (one
   unscaled, one 4x2 scaled, one alternate-canvas run) would prove PACPLAT TSD end to end. This is TSD work: it is
   proposed only because the approved plan names it, and needs the user's go-ahead. S2 alarm streams stay deferred.

## 9. STOP conditions and security constraints
- Batch jobs: as ZOS-2 (RC, STEPLIB, CEEOPTS, CEE / abend / S722, spool DDs, anchoring, oracle, model); plus for HS:
  any write outside the approved test datasets, any DELETE disposition not explicitly authorised, any change to
  <HLQ>.PACMAN.DATA (the installed high-score dataset is never written by a deck).
- No live / interactive session in ZOS-3. For the later live phases: the TN3270 path (port 623) is plain text, so the
  password is entered only by the user in their own terminal, never by the assistant, never stored, never in a trace;
  traces and screenshots are reviewed and redacted before they enter the repository; no ISPF / system settings
  changed; one session at a time; logoff after each check; STOP on any unexpected panel, message or security prompt.
