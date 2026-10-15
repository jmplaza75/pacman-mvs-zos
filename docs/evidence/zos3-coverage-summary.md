# ZOS-3 platform layer - coverage summary (2026-10-15)

All ZOS-3 jobs PASS on IBM Z Xplore (HLQ Z00000), load module PACZ2D of PACZ2BLD JOB08888 (not rebuilt), profile A,
no source change, no DELETE, no purge. Evidence: docs/evidence/zos3-platform-layer.md; raw spool
docs/evidence/zos3-spool/ (14 deterministic archives, SHA256SUMS, MANIFEST.txt).

## Jobs
| Job | JOBID | Content | Result |
|---|---|---|---|
| PACZ3FS | JOB01362 | PACFSIO batch contract: S1S3 (310), S2L4 (308), TSO + COLOR(AUTO) | PASS |
| PACZ3HA | JOB02091 | HS test PDSs T1: allocate, seed, fill (HSFILL RC 12 expected) | PASS (1st check false FAIL: LISTDS parser, fixed 6b446cc) |
| PACZ3HS1..8 | JOB02401, 02404, 02411, 02416, 02417, 02421, 02422, 02433 | the stateful HS sequence, frozen order, state gate before every job | PASS (HS8 1st check false FAIL: IEC217I z/OS continuation form, fixed 76c8852) |
| PACZ3TD1..4 | JOB02506, 02511, 02512, 02516 | the minimum ALARM(PATTERN) TSD set (12 S2T runs, 21 D41 edges) | PASS |

## Proved on z/OS in ZOS-3 (batch / IKJEFT01 batch)
- PACPLAT -> PACFSIO batch fallback path entered (TSO + COLOR A) and clean line-mode fallback; output = oracle 310 / 308
  = the 1.0-MVS DIE1 run = the z/OS COLOR(N) run. FSON RC=4 is established from the verified PACFSIO control flow under
  the independently established no-TSB batch condition; the job does not emit or observe that RC.
- PACHSIO, every HS path of the frozen suite except HA6: REPL new member (STOW add), WRIT in place (QSAM UPDAT), REPL
  replacing a malformed / empty member, read-only lower / equal / 9999999, score 0 on a missing member (not created),
  start level != 1 not recorded (HA7), CLASSIC (no HS I/O), DD without member / DD DUMMY (unavailable), REALTIME and
  TSD TURN / REALTIME new members, TMP ALLOC SHR + CALL new / equal (HTSO1/2, first IKJEFT01 CALL of PACZ2D on z/OS).
- HH1: a genuinely full PDS directory (one block, M01..M20, IEB813I at M21) -> STOW B14-0C on HSFULL.T1(HISCORE),
  recovered by PACHSIO's ESTAE inside the LE enclave (no ABEND escapes, COND CODE 0000), `HIGH SCORE NOT SAVED`,
  HISCORE absent afterwards. PACHSIO's RC 16 is inferred from the control flow, not printed.
- Final T1 state = ref_hs.Pds (read-only member names and contents).
- TSD dry run: the stream engine with ALARM SINGLE (HG2 / HG3) and every ALARM(PATTERN) behaviour of D41 (patterns at
  NORMAL / FAST spacing, priorities and one-write coalescing, replacement, pause hold, steps on prompt-form writes,
  QUIT drop, no pre-start ring, TURN single bells, end-pause bell-only writes, not-scaled S1 write, SOUND(NO)), byte for
  byte against oracle 308 and ref_s2, alarm bits included; canvases W, T, D.
- The S2 alarm coverage deferred from ZOS-2 is now satisfied (as far as a dry run can prove it).

## Tooling added / fixed in ZOS-3 (all locally tested, tests/test_zos_tools.py sections 9-13)
- Oracle 312 HA1 known boundary (digest-bound, fail closed, 19/19); compare() checks a known-boundary step at its
  one-empty-line prefix (309 RPT1 / 312 HA1; all ZOS-2 / ZOS-3 evidence re-checked PASS).
- Frozen models executed verbatim: zos_hs_model (test_hs, G8), zos_s2_model (test_s2 sections 0 + 2).
- Checkers: zos_fs_check, zos_hs_setup_check (LISTDS parser bounded per command extent), zos_hs_check (state gates,
  z/OS IEC217I form), zos_tsd_check; zos_spool_archive --phase.
- Two false FAILs, both checker-format defects caught by fail-closed checks and resolved only with the user's approval,
  raw evidence frozen first (SHA-256 + read-only), both facts kept in the evidence.

## Not proved in ZOS-3 / carried forward
| Item | Where |
|---|---|
| Live TPUT / TGET, STFSMODE / STTMPMD terminal-mode switching, c3270 Query Reply and inputs, real timing, audible bell | ZOS-4 (live TSO), ZOS-5 (live 3270 full screen) |
| C3 (PACFSIO ASMA303W, provisional): PACFSIO ESTAE and terminal services not exercised | ZOS-8 E2 |
| HA6 (5,262 application lines alone, above the site output limit; state-neutral) | DEFERRED to ZOS-9/10 (not PASS) |
| HSP1..9 member prints (replaced by read-only state checks here) | ZOS-9/10 full suite |
| HS CLIST block (HSCLS1/2, HSCLT) | ZOS-4 |
| The other 13 S2T runs, S2L1..3 (redundant for coverage) and the rest of the frozen batteries | ZOS-9/10 full battery |
| Z1 (zos-only COPY delta, guarded) | carried as before |

Accepted T1 datasets (Z00000.PACMAN.HSTEST.T1 / HSFULL.T1) are kept unchanged; nothing in ZOS-3 touched
Z00000.PACMAN.DATA.
