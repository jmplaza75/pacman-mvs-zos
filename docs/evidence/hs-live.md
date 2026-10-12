# MVS-HS HS.3: live c3270 acceptance - PASS (user, 2026-10-12)
Build: deck HS JOB 260 (regression GP2 JOB 262, GP23 JOB 263); install: DATA JOB 264 (`HERC01.PACMAN.DATA`, empty, no
member), CLIST JOB 265. Live: c3270 4.5ga6 (`tools/c3270_rt.sh`, 120x27, REALTIME), trace `~/hs-live.txt`
(17:01:58-17:08:45; kept outside the repository: it contains the logon). Checklist: docs/HS-HISCORE.md section 11.
The trace was read independently (host records decoded from EBCDIC; inbound records only for the typed TSO commands):
it agrees with the user's report in every line below.

| # | Command (time) | Game end | End lines in the trace | Result |
|---|---|---|---|---|
| L1 | `EXEC ... 'RULES(ARCADE)'` (17:02:13), member HISCORE missing | QUIT, SCORE 0000370 | `HIGH SCORE 0000370 LEVEL 001` / `NEW HIGH SCORE` | PASS: member created |
| L2 | `'RULES(ARCADE)'` (17:03:29) | QUIT, SCORE 0000140 | `HIGH SCORE 0000370 LEVEL 001` (no NEW) | PASS: read back across executions, not rewritten |
| L3 | `'RULES(ARCADE)'` (17:04:03) | **QUIT**, SCORE 0001430 | `HIGH SCORE 0001430 LEVEL 001` / `NEW HIGH SCORE` | PASS: updated |
| L4 | `'RULES(ARCADE) LEVEL(5)'` (17:05:07) | LOST, SCORE 0002420 | `HIGH SCORE 0002420 LEVEL 005` / `START LEVEL 05: HIGH SCORE NOT RECORDED` | PASS: practice start, not saved |
| L5 | `'RULES(CLASSIC)'` (17:06:13) | QUIT, SCORE 0860 | no high-score line | PASS: CLASSIC unaffected |
| L6 | `RENAME 'HERC01.PACMAN.DATA' 'HERC01.PACMAN.DATAX'` (17:07:18), `'RULES(ARCADE)'` (17:07:24), `RENAME` back (17:08:37) | QUIT, SCORE 0001490 | `HIGH SCORE UNAVAILABLE` | PASS: the CLIST went on (DUMMY), the game played, READY |
| L7 | `LIST 'HERC01.PACMAN.DATA(HISCORE)'` (17:08:45) | - | `0001430 PACHS001 001` | PASS: one record = the L3 score |

## Conclusions
- Real persistence across separate TSO executions (L1 -> L2 -> L3) and across a dataset rename / restore (L6 -> L7).
- The record on disk is the eligible L3 score from level 1 (`0001430 PACHS001 001`): neither the higher LEVEL(5)
  practice score of L4 (2420) nor the higher score of L6 (1490, persistence unavailable) was written.
- A missing DATA dataset does not end the CLIST or the game: `&SYSDSN` pre-check, `ALLOC ... DUMMY`, clean READY.
- Recorded deviation from the checklist: the live higher-score case L3 ended with **QUIT**, not LOST (QUIT is an
  eligible D38 end). A live LOST was seen only on the practice path (L4, not recorded). The eligible LOST save
  (HA4), EOF (HB1), QUIT (HA1, HA5), the practice WIN (HA7, LEVEL(99)), the full-directory write failure (HH1), the
  malformed / empty member heal (HE1, HE2) and the unusable DDs (HF1, HF2) remain covered by the deterministic HS.2
  evidence (JOB 260, docs/evidence/hs-build-tsd.txt, tests/test_hs.py); an eligible WIN needs 99 level clears and is
  covered structurally (docs/HS-HISCORE.md section 8).
- No abend, no alarm change, no screen change (sound and screens as GP2).
