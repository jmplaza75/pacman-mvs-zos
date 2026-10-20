# ZOS-9 Final MVS / z/OS equivalence - evidence (2026-10-20)

## 1. Result
**ZOS-9 FINAL EQUIVALENCE: PASS.**
- The requirement / equivalence matrix (docs/zos9-design.md section 4, 51 rows) is the coverage authority (DEC-1).
- No unexplained functional mismatch remains; every difference from 2.0-mvs-max is an approved platform-specific
  adaptation (section 10).
- No execution GAP remains (GAP = 0, DECISION = 0; section 13).
- No accepted ZOS-0..8 evidence was invalidated (section 3).
- Only the genuinely uncovered paths were executed: two read-only batch jobs, 24 steps, all exact (sections 6-8).
- No production-source change in ZOS-9; no production DATA change.

## 2. Baselines
| Role | Tag | Commit |
|---|---|---|
| MVS frozen reference (functional oracle) | 2.0-mvs-max | 94fd6f6 |
| z/OS pre-ZOS-9 baseline | zos-8 | 32d99f2 |
| previous | zos-7 | 75b3fd5 |
Program under test: LOAD(PACZ6D) = the installed LOAD(PACMAIN) (ZOS-6 build PACZ6BLD JOB09460, promoted by PACZ6INS
JOB09499). Oracles: tests/oracle20 (JOBs 307-312, 315, 316), unchanged since ZOS-0.

## 3. Invalidation conclusion
- No accepted ZOS-0..8 evidence item is invalidated or partially invalidated (per-item table: design section 3).
- ZOS-8 made no production-source change (`git diff zos-7 zos-8 -- src` = the test CLIST RPESTAE only); its production
  delta is state only: DATA(HISCORE).
- The one production change after ZOS-2 is ZOS-6 Z4 / Z5 (PRESENT(COALESCED)). Its behaviour is gated by PARM column 26
  = C; on every non-COALESCED path (batch, TURN, line mode, PRESENT(EVERY)) the new code is not reached or returns the
  pre-Z4 value, and the PACREQ fields are append-only. The older non-COALESCED evidence stays valid; post-ZOS-6 runs
  (E1, E2, Z1, E3, B1, GD, S8C, L1, HL*, SF, and now PACZ9E1 / PACZ9E2) confirm it on the rebuilt program.
- TSO line mode: **VALID BY NON-INTERFERENCE**. Final installed line-mode verification is carried to ZOS-10, after the
  clean rebuild.

## 4. Equivalence methodology (DEC-1)
The original plan wording "run the full batteries" (plan sec. 6 ZOS-9, sec. 13 "in full") is superseded. Final rule:
the requirement / equivalence matrix is the coverage authority; every in-scope requirement and relevant path must be
CLOSED, by exact oracle evidence, semantic equivalence, model / batch evidence, live evidence, observational
equivalence, an approved platform-specific difference, or rigorous composed evidence. The coverage measure is D12:
every documented edge and every display path executed on z/OS at least once with exact equivalence, else closed by an
explicit composition argument (design section 5). Re-running the historical batteries (about 268,000 oracle lines;
five single runs above the site output limit; most behaviours already proven) would have added redundant evidence,
not coverage; acceptance quality is unchanged.

## 5. Reused evidence (principal chain)
| Phase | Evidence reused | Requirements it carries |
|---|---|---|
| ZOS-0 / 1 | discovery, oracle freeze, toolchain, upload identity, profile A / B probes | platform, build profile, encoding |
| ZOS-2 | C1-C7 (25 CLASSIC runs = 1.0 oracle), G1-G3 ARCADE, G2 REALTIME, RP3 FAST, ST0 / STF, QRY1, TSOT1 | core rules, AI, determinism, storage independence, query parsing, clock |
| ZOS-3 | PACZ3FS, HS1-8 (18 of 19 HS runs), TD1-4 (21 / 21 D41 edges) | PACFSIO batch contract, PACHSIO, alarm patterns |
| ZOS-4 | Z2 / Z3 CLIST, PACZ4INS, live line mode (attestation) | CLIST, CEEOPTS, terminal SYSIN, line mode |
| ZOS-5 | live A / B / C, real Query Reply | full screen, colour, highlight, GE, partial redraw, PA2 / CLEAR |
| ZOS-6 | PACZ6DR1 / DR2, live R1-T4 / R2 | REALTIME under ZV-D33, freeze (offline exact), input |
| ZOS-7 | PACZ7DR1 / DR2, live L1 / L2 / L3 | ARCADE rules, D1 final death, freeze discriminated |
| ZOS-8 | B1, B2, HL1-HL8, E1-E3, S1-S3, SF | high score, recovery, sound, production first write |
| ZOS-9 | PACZ9E1, PACZ9E2 | the previously never-executed display / rule paths |

## 6. PACZ9E1 - JOB04412, CC 0000: 14 / 14 PASS
Deck jcl/zos/PACZ9E1.jcl (oracle 310 steps verbatim, EXEC PGM=PACZ6D). Application output 2,167 lines exactly; total
spool 2,571 lines. No anomalies (JES log $HASP373 / $HASP395 RC=0000 only, STEPLIB retained 14 times, no CEE / abend,
SYSOUT only).
| Step | Lines | Oracle | Model | Verdict |
|---|---|---|---|---|
| TSD2 | 55 | exact | exact | PASS |
| TSD5 | 91 | exact | exact | PASS |
| TSD14 | 75 | exact | exact | PASS |
| TSD36 | 273 | exact | exact | PASS |
| TSD41 | 89 | exact | exact | PASS |
| TSD43 | 132 | exact | exact | PASS |
| TSD50 | 324 | exact | exact | PASS |
| TSD52 | 258 | exact | exact | PASS |
| TSD55 | 194 | exact | exact | PASS |
| TSD56 | 194 | exact | exact | PASS |
| RTB2 | 35 | exact | exact | PASS |
| RTB3 | 31 | exact | exact | PASS |
| RTB4 | 31 | exact | exact | PASS |
| RTB12 | 385 | exact | exact | PASS |

## 7. PACZ9E2 - JOB04418, CC 0000: 10 / 10 PASS
Deck jcl/zos/PACZ9E2.jcl (oracle 311 steps verbatim, EXEC PGM=PACZ6D). Application output 2,628 lines exactly; total
spool 2,924 lines. No anomalies (as E1; STEPLIB retained 10 times). G3T7 (SOUND(YES)) matched with the frozen batch
bell rule (tests/test_gp2.py bells(), executed verbatim); no live-transport exception was involved.
| Step | Lines | Oracle | Model | Verdict |
|---|---|---|---|---|
| G3T4 | 224 | exact | exact | PASS |
| G3T5 | 296 | exact | exact | PASS |
| G3T7 | 226 | exact | exact | PASS |
| G3T8 | 334 | exact | exact | PASS |
| G3T10 | 394 | exact | exact | PASS |
| G3T14 | 242 | exact | exact | PASS |
| G3T15 | 173 | exact | exact | PASS |
| G3T26 | 167 | exact | exact | PASS |
| G3T28 | 167 | exact | exact | PASS |
| G3R3 | 405 | exact | exact | PASS |
"Oracle exact" = the step's own frozen 2.0 block (zos_equiv own-block anchoring, ASA column and record padding removed
only); "model exact" = the frozen independent model (ref_gx_screen / ref_gp2 / ref_rt / ref_mvs6), frames byte for
byte, transport lines and end lines. Checker: tools/zowe/zos9_equiv.py. Raw spool outside git
(build/zos/PACZ9E1-JOB04412,
build/zos/PACZ9E2-JOB04418, read-only; manifests SHA-256 567ba439... / 247c07d4...).

## 8. Gaps closed by the ZOS-9 executions
Closure is per required step: a row closed only because every step carrying it passed on its own (oracle AND model),
not because a job ended RC 0.
- **G4** (power / fright rules): GPTWOF (G3T4), GPTICK (G3T5), GPFN (G3T8), pause during a fright (G3R3).
- **G6** (fruit): ghost on the fruit cell (G3T26), uneaten fruit (G3T28).
- **G9** (REALTIME): RTCORNER, RTTTL, RTREV, RTEDGE0 (RTB2 / RTB3 / RTB4 / RTB12).
- **P7** (display / profile families never executed before): HILITE(NO) (TSD5, G3T4), GLYPHS(BASE) (TSD41, G3T28),
  GRAPHIC not scaled (TSD14, G3T5), CLASSIC glyphs (TSD2, G3T26), SCALE(3) (TSD36, G3T8), size guard (TSD43, G3T14),
  132x27 (TSD50, G3T10), 80x32 (TSD52, G3T15), 100x25 (TSD55), 160x30 (TSD56), ARCADE on 80x24 (G3T7).
- **P10** (RP screens): two ghosts eaten in one move (G3T4); pause in a fright (G3R3).

## 9. HA6 - CLOSED BY COMPOSED EVIDENCE
(1) HA6's gameplay output is exactly the frozen GP2 oracle 310 G2B29 behaviour (oracle 312 HA6 = G2B29 + two
high-score lines); (2) its additional high-score behaviour is "start at a later level -> do not record"; (3) that rule
is demonstrated by accepted z/OS evidence: HA7 (batch, PACZ3HS) and HL1 (live, installed program, stored record kept);
(4) PACHSIO did not change; (5) therefore HA6 contains no unique remaining z/OS behaviour and needed no direct
execution. No LINES=, no output dataset, no split, no DATA change.

## 10. Approved platform-specific equivalence (part of the result, not open deviations)
- PRESENT(COALESCED): logical NORMAL 150 ms / physical stride 2 (~300 ms), FAST 125 ms / stride 3 (~375 ms); not one
  TPUT per logical quantum (ZV-D33, Z4 / Z5).
- RTQS: skipped quanta advance the logical display state (WS-FACE, PU-*, VIS, logical bell); the diff baseline advances
  only on a write; the final screen follows the logical state.
- No stale replay; START / RESUME re-anchor the presentation; one post-write nonblocking read feeds the next quantum.
- TN3270E BID / CONTENTION-RESOLUTION / keyboard-direction timing is platform behaviour.
- The contextual TSO CONTROL record exactly `F1 C3` (narrow rule); in the SOUND context the preceding WCC may be C3 or
  C7 (C7 = C3 + the alarm bit only).
- D1 ARCADE final death: 6 (NORMAL) / 7 (FAST) consecutive exact writes.
- Freeze 10 / 12 logical quanta exact; stationary live cases observationally indistinguishable, moving cases
  discriminated (ZOS-7).
- Recovery diagnostic codes: LE 0C7 / TSO 0C4 (E1 / E2), 0C7 / 0C7 (E3); acceptance = usable session + clean next game.
- Z1 COPY syntax, Z2 CLIST CEEOPTS (profile A), Z3 terminal SYSIN, ISPF option 6 boundary, z/OS IEC217I form, SYSOUT
  FBA 121 (full list AD1-AD17: design section 6).

## 11. Remaining non-ZOS-9 items (none is a ZOS-9 GAP)
- **I4 - NOT AN EQUIVALENCE GAP; ZOS-10 REQUIRED ACTION.** The release CLIST's REALTIME default becomes
  PRESENT(COALESCED); explicit PRESENT(EVERY) stays selectable; a low-level PARM without column 26 still means EVERY.
- **I6 - release work** (clean rebuild, README, release material, tag 2.0-zos): ZOS-10.
- **P11 - METRICS(YES): APPROVED OUT OF SCOPE - DIAGNOSTIC / NO FROZEN 2.0 EQUIVALENCE ORACLE** (D23 optional; no
  requirement makes it mandatory; no 2.0 oracle run). Not PASS, not proven on z/OS.
- **A11 - PACHELLO console run: OUT OF SCOPE** (approved at ZOS-1 closure; compile + bind only).

## 12. Production DATA safety
PACZ9E1 / PACZ9E2 did not allocate PACHS, did not reference DATA, wrote no persistent dataset (spool only), and
performed no compile, assembly, bind, promotion or DELETE. The only dataset named was Z00000.PACMAN.LOAD (DISP=SHR).
The legitimate production state is unchanged from ZOS-8: `Z00000.PACMAN.DATA(HISCORE)` = `0000980 PACHS001 001`.

## 13. Final matrix result (51 rows; design section 4)
| Status | Rows |
|---|---|
| CLOSED EXACT | 22 |
| CLOSED SEMANTIC | 2 |
| CLOSED MODEL-BATCH | 4 |
| CLOSED LIVE | 11 |
| CLOSED OBSERVATIONAL | 1 |
| CLOSED PLATFORM-SPECIFIC | 5 |
| CLOSED by DEC-1 (I7) | 1 |
| CLOSED DOCUMENTATION (I5, section 15) | 1 |
| NOT AN EQUIVALENCE GAP / ZOS-10 REQUIRED ACTION (I4) | 1 |
| OUT OF SCOPE (A11 PACHELLO, I6 release = ZOS-10, P11 METRICS) | 3 |
| **GAP** | **0** |
| **DECISION** | **0** |

## 14. Conclusion
PACMAN on z/OS is equivalent to the frozen 2.0 MVS reference (2.0-mvs-max) for all in-scope ZOS-9 requirements, with
the documented and approved platform-specific adaptations of section 10.

## 15. z/OS capability column (I5; requirements sec. 28; from accepted evidence only)
Path: IBM Z Xplore TSO / VTAM / TN3270E, c3270 4.5ga6 `-model 2 -oversize auto`, 120 x 30 window. MVS column:
docs/CAPABILITIES.md (2.0-MVS-MAX, unchanged). NOT TESTED = no accepted z/OS evidence; nothing is inferred.
| Capability | z/OS status | Evidence / decision |
|---|---|---|
| 3270 model / screen size | CONFIRMED 80 x 24 | ZOS-5 C (Erase/Write 80 x 24, writes = model) |
| Alternate screen size | CONFIRMED 120 x 27 live; 80x32 / 80x43 / 132x27 / 100x25 / 160x30 layouts exact on simulated buffers only, not negotiated live (not offered on this path) | ZOS-5 A / B; ZOS-3 TD (T), ZOS-6 N5 / F5, PACZ9E1 / E2 (X, M, U, L) |
| Canvas negotiation | fixed at connect, as on MVS (window sized before connecting, never resized) | ZOS-4 / ZOS-5 sessions (same launch) |
| TSO line mode in the alternate size | CONFIRMED at the 120-column line size with Z3 | ZOS-4 session 2 (user attestation), Z3 |
| TSO line-mode output, STLINENO fresh screen | CONFIRMED (observational live; batch exact) | ZOS-4 session 2; ZOS-2 C7 TSO1-6 |
| TSO terminal macros (assemble) | CONFIRMED (HLASM, C3 ASMA303W only) | PACZ2BLD JOB08888 |
| TSO full screen (TPUT FULLSCR / TGET ASIS) | CONFIRMED | ZOS-5 A / B / C |
| TPUT / TGET in batch | CONFIRMED line-mode fallback (FSON RC 4 from the control flow) | ZOS-3 PACZ3FS JOB01362 |
| Extended colour | CONFIRMED | ZOS-5 (QCode X'86', writes = model) |
| Reshow keys | PA2 CONFIRMED; CLEAR not delivered, z/OS TSO / VTAM CLEAR record, redraw by PA2 | ZOS-5 B; R1-T4 PA2 |
| Highlighting | CONFIRMED | ZOS-5 (QCode X'87') |
| Character attributes (SA order) | USED, writes = model | ZOS-5..ZOS-9 TSD / live |
| APL / graphic character set (GE) | CONFIRMED (GE + CP310) | ZOS-5 profile |
| Programmed Symbols | NOT ANNOUNCED on this path; not used | ZOS-5 real Query Reply = qreply_dyn (no loadable sets) |
| Triple-plane PS | NOT APPLICABLE | depends on PS |
| Vector / host graphics (GDDM, GOCA) | NOT TESTED on z/OS; not used by 2.0 | none (outside the 2.0 equivalence) |
| Capability detection (Read Partition Query) | CONFIRMED | ZOS-5 A / B; QRY1 (ZOS-2) |
| Colour renderer TSC | CONFIRMED | ZOS-5; every profile family TSD-exact (PACZ9E1 / E2) |
| Audible alarm (WCC alarm bit) | CONFIRMED, audible at c3270 | ZOS-8 S1-S3 |
| Partial screen update | CONFIRMED | ZOS-5 A / B / C |
| Idle animation | CONFIRMED idle ticks; D28 behaviour as recorded | ZOS-5 (docs/evidence/zos5-fullscreen.md) |
| Viable update rate | logical 150 / 125 ms; physical ~300 / 375 ms under PRESENT(COALESCED); one write per quantum (EVERY) not viable interactively | ZOS-6 R1-T3 / R1-T4 / R2, ZV-D33 |
| Real-time input (PF7/8/10/11, PF9, PA2) | CONFIRMED under COALESCED | ZOS-6 R1-T4 / R2, ZOS-7 L2 / L3 |
| Alarm patterns | CONFIRMED | ZOS-3 TD1-4, ZOS-8 S1-S3 |
| Automatic maximum profile | AUTO profile selection CONFIRMED (COLOR(AUTO) -> GRAPHIC 4x2, 120 x 27); the no-operand REALTIME default is a ZOS-10 action (I4) | ZOS-5 A; DEC-2 |

## 16. Post-closure documentation errata (applied in ZOS-9)
1. docs/evidence/zos8-services.md: "the installed production CLIST(PACMAN) changed" -> **unchanged** (the evidenced
   fact); erratum note added there. No ZOS-8 result changed; tag zos-8 not moved.
2. docs/ZOS-DIFFS.md C3: the "not resolved" text is superseded by an erratum note: C3 CLOSED in ZOS-8 (E1-E3, no
   PACFSIO change).
3. docs/ZOS-DIFFS.md Z4 / Z5 headings: "NOT built / NOT installed" replaced by a pointer to their Status lines (built
   PACZ6BLD JOB09460, promoted PACZ6INS JOB09499, CLIST installed in ZOS-6).
