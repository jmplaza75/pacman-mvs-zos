# MVS-RT RT0 - probe E14 (real-time timing / input) - CLOSED 2026-10-10
Environment: TK4- / MVS 3.8J + TSO + c3270 4.5ga6 (`tools/c3270_rt.sh`: `-model 2 -oversize auto`, keymap arrows ->
PF7/PF8/PF10/PF11, script port 4001). Baseline `mvs-gs` (62ab854); PACMAN, GAME/MAP/AI, PACSCR, PACPLAT, PACFSIO, PACTSO
and the frozen core are unchanged. Plan: docs/RT-REALTIME.md.

## Probe
- `src/probe/PACRTP.cob` (driver) + `src/probe/PACRTA.asm` (probe-only service: `STCK` clock, `STIMER WAIT,MICVL` for the
  remainder to an absolute deadline, one `TGET ASIS,NOWAIT`, raw `TPUT NOEDIT`), linked with the UNCHANGED PACGAME, PACMAP,
  PACAI, PACSCR, PACPLAT, PACQRY (library members of the mvs-gs build) and PACFSIO, PACTSO (repository). CLIST `RTPROBE`;
  decks `RTP` (build + batch run) and `RTL` (print logs E14Q/N/T/U) in tools/make_deck.py.
- Segments: W (D28: synthetic frames until the first AID + 10), S (synthetic 43-byte frame) and G (representative GS frame:
  PACGAME turn + PACSCR compose + PACPLAT send; AI2, 3 ghosts, scripted route, one forced full frame at quantum 75) for
  100/150/175/200/250 ms, I (input: 200 ms game frames steered by PF AIDs), R (restore-only: `F1 C2` only after an AID).
  Batch: C (clock only) and K (compose only, TSD 120x27). Deadlines absolute (`next += P`; a missed one is skipped and
  counted); at most one terminal write per quantum; logs written after each segment, outside the timed loop.
- Analysis: tools/rt_e14_report.py (MVS log), tools/c3270_rt_trace.py (c3270 trace from the first `E14 ` frame on: no
  logon data; inbound shown by AID only), tools/host_cpu_sample.py (Hercules CPU from cumulative CPU time),
  tools/e14_inject.py (script-port AIDs). Traces stay outside the repository (`~/rt-e14.txt`, `~/rt-e14-run1-aborted.txt`).

## Runs
| Job / run | What | Status |
|---|---|---|
| JOB 210 | build | COB1 RC 4 (IKF5011I-W truncation in the log format), rest flushed; fixed |
| JOB 211 | build + batch (C, K) | all steps RC 0000, no warnings |
| Run 1 aborted (08:25) | `VAR(Q)` | INVALID: stopped by PA1 in G200; kept only as diagnostics (no probe defect found) |
| Run 1 (09:10, log JOB 213) | `VAR(Q)` all phases, 120x27, injector | valid: timing, cadence, D28, single-key latency, injected AIDs, keyboard restore. Not valid for rapid input / typeahead / held keys (not performed) |
| Run 2 (10:29, JOB 214) | `VAR(N) PH(T)`, 80x24, no Query | valid: D28 control, timing, cadence |
| Run 3a (10:44, JOB 215) | `VAR(Q) PH(I) LOG(T)`, typeahead ON | valid: held keys, backlog, ordering, keyboard restore, AIDs per quantum. Not valid for rapid bursts (none in the trace) |
| Run 3b (10:51, JOB 216) | `VAR(Q) PH(I) LOG(U)`, typeahead OFF | valid: held keys, dropped keys, ordering, latency, keyboard restore. No 4-key burst in the trace either |
A 4-distinct-arrow burst within 0.5 s never occurred in any run (checked on every key event of the traces). Burst
behaviour is therefore derived from the measured mechanism (below), not measured. Typeahead was set back to `true`
after Run 3b; a mistaken 8 s toggle at 08:24:43 happened before any probe and is ignored.

## 1. Clock (absolute deadlines)
Batch (JOB 211, no TSO): averages exact (100.08 / 150.02 / 175.10 / 200.02 / 250.11 ms), wake lateness 0-12.6 ms
uniformly distributed: the MVS 3.8J STIMER granularity, independent of the period. No drift (absolute deadlines).
Live, game frames (G), period min / avg / p95 / max in ms, p95 relative error, overruns:
| P | Run 1, 120x27 (Query) | err p95 | Run 2, 80x24 (no Query) | err p95 | overruns R1 / R2 |
|---|---|---|---|---|---|
| 100 | 87.5 / 100.07 / 100.4 / 111.4 | 4.4 % | 93.6 / 100.01 / 100.2 / 111.3 | 5.1 % | 0 / 0 |
| 150 | 143.8 / 150.02 / 154.3 / 161.4 | 3.6 % | 137.7 / 150.03 / 154.0 / 161.6 | 5.6 % | 0 / 0 |
| 175 | 162.6 / 175.06 / 185.2 / 186.7 | 5.9 % | 162.6 / 175.03 / 179.5 / 186.8 | 3.7 % | 0 / 0 |
| 200 | 187.6 / 200.01 / 209.6 / 211.3 | 4.8 % | 187.6 / 200.03 / 202.7 / 211.4 | 3.6 % | 0 / 0 |
| 250 | 237.3 / 250.07 / 259.9 / 261.4 | 4.0 % | 239.6 / 250.06 / 258.6 / 261.4 | 3.5 % | 0 / 0 |
Synthetic (S) segments: p95 error 3.3-6.1 %, 0 overruns. Input segments (200 ms, runs 1/3a/3b): p95 error 4.2-5.1 %,
0 overruns. Total: 0 skipped deadlines and 0 quanta with busy > P in all live quanta of runs 1, 2, 3a, 3b.
Timer jitter: wake lateness 0-12.8 ms at every period; wakes > 10 % of P late: 26-29 / 150 (Run 1) and 19-22 / 150 (Run 2)
at 100 ms, at most 1 / 150 above. Isolated host stalls (no sustained effect): one 24 ms late wake (Run 2 S250); compose
spikes of 58, 85 ms (Run 1) and 51, 53, 69 ms and one full frame of 108 ms (Run 2 G250, normal 32 ms). Such a stall would
be one skipped deadline at 100 ms; it fits at 150 ms and above.
Clock alignment MVS TOD vs host: offset drift about 12 ms over 6 minutes (Run 1, from 887 tagged frames).

## 2. Frame cadence at c3270
After the first AID, every segment of every run: median gap = P, p95 = P + 1-10 ms, max = P + 10-17 ms, no gap > 1.5 P;
the only gaps < 20 ms are the segment-boundary frames. TPUT -> c3270 delivery (tagged frames): median 0.5 ms, p95 1 ms,
max 19.6 ms. No batching or bursts.

## 3. D28 (capability Query retention)
| Run | Query | Before the first AID | First direction AID |
|---|---|---|---|
| 1 | yes | only frame Q=1 delivered; 125 frames held 25.1 s | PF11 at quantum 127: whole backlog released within 30 ms (merged into 12 records), then normal cadence |
| 3a | yes | frames held 15.7 s | released at once |
| 3b | yes | frames held 1.6 s | released at once |
| 2 | no | all 119 W frames delivered every 190-212 ms from the start | - |
The first direction AID releases TSO's post-Query retention; without the Query there is no retention.

## 4. Renderer and busy cost (unchanged PACSCR)
| | 120x27 W layout (Run 1) | 80x24 GS (Run 2) | batch TSD 120x27 |
|---|---|---|---|
| partial frame compose | 20.6-21.4 ms avg, about 307 bytes | 16.7-17.0 ms, about 305 bytes | 21.0 ms |
| full frame compose | 37.0-39.3 ms, 1,824 bytes | 31.9-33.1 ms, 1,639 bytes | 37.1 ms |
| busy per game quantum | about 21.2 ms | about 17.2 ms | - |
PACGAME turn + TPUT < 0.5 ms; synthetic quantum about 0.1 ms. Guest CPU (one emulated 3033) busy fraction for 120x27:
21 % at 100 ms, 14 % at 150, 12 % at 175, 11 % at 200, 8.5 % at 250.

## 5. CPU (host)
Hercules (pid 72172) runs at 99-100 % of one host core when MVS is idle (baseline) and during every run (Run 1 99.2 %,
Run 2 98.5 %, 3a 97.9 %, 3b 97.7 % average; 8-core host). The probe adds no measurable host CPU: guest busy time is the
cost measure. Between quanta the task is in STIMER WAIT.

## 6. Input: AIDs, ordering, latency
- Keymap validated: arrow keys -> PF7 (U) X'F7', PF8 (D) X'F8', PF10 (L) X'7A', PF11 (R) X'7B'; key -> wire < 2 ms.
- Order: every AID that reached the wire reached MVS, in the same order (Run 1: 26/26, 3a: 124/124 = all 124 key events,
  3b: 65/65). No reordering anywhere.
- c3270 never sends an AID while the keyboard is locked; it is unlocked only by a host write with WCC restore. Script /
  keymap macros wait (KBWAIT); physical keys go to the typeahead queue (ON) or are dropped (OFF).
- AIDs per quantum: normally 1; 2 when an AID arrives after the poll but before that quantum's write (the write unlocks,
  the next key goes out at once): seen 2x in 3a and 3x in 3b. The read loop must drain until empty.
- Latency wire -> MVS poll: 5-200 ms at P = 200 (median 121), i.e. bounded by one quantum.
- Injected AIDs (Run 1): PA2 received (full redraw 96 ms later, Erase/Write Alternate 1,712 bytes); PF1, ENTER received
  (no effect); `X`+ENTER received with the typed character; PF bursts in order, one per quantum.
- CLEAR: sent by c3270 twice, NEVER returned by TGET (swallowed by this TSO path). Screen blanked; partial frames then
  drew on a blank screen. In restore-only (writes only after a received AID) the keyboard stayed locked 23.8 s until the
  probe ended.

## 7. Held keys and typeahead (macOS autorepeat: first repeat after about 490 ms, then every 84 ms = 12 keys/s)
Typeahead ON (Run 3a): nothing dropped, but at one AID per quantum the c3270 queue grows by about 7 keys/s:
| Hold | Key events | Max queue | Still draining after release |
|---|---|---|---|
| right 0.8 s | 6 | 2 | 0.35 s |
| left 3.1 s | 33 | 18 | 3.5 s |
| down 1.9 s | 19 | 10 | 1.8 s |
| right 4.5 s | 38 | 21 | 4.0 s |
Stale input: after the 4.5 s hold, old PF11 kept arriving 4.0 s (13 of them in the next segment); LEFT pressed 0.7 / 1.6 /
2.9 s after release waited 3.4 / 2.7 / 1.7 s behind them. The host cannot discard this backlog (it never sees it).
Typeahead OFF (Run 3b): 102 key events, 65 sent, 37 dropped. All 37 dropped events were pressed while the keyboard was
locked and all were autorepeat duplicates; 0 of 24 direction changes were dropped. Five holds of 1.0-1.8 s: the last key
sent at most 164 ms before release, NO backlog after release; the next new direction (202-669 ms after release) went out
at once. Keyboard lock 1-199 ms (median 133).
Bursts (not measured): with typeahead OFF a different key pressed while the keyboard is still locked after the previous
AID (up to one quantum) is dropped like the autorepeats above; with ON it is queued and delivered one per quantum.

## 8. Keyboard restore and restore-only
- Every frame write (WCC C2/C3) unlocks; lock time per AID 1-229 ms (median 133-199), never more than one quantum.
- Minimal restore `F1 C2` (2 bytes): unlocks 0-1 ms after arrival. Run 1 snapshots before/after a PF burst and PA2: all 23
  content rows identical, cursor unchanged (26,34). Run 3a: R sent only `F1 C2` (18) + one instruction line: nothing that
  can alter content or cursor. Run 3b: no keys in R (one instruction line only).
- RECT (PACFSIO) is not usable as a clock: after an empty poll it always waits 0.5 s (code; G3 measured idle ticks every
  about 0.52 s, docs/evidence/g3-tick-trace.md).

## RT0 conclusions (for RT1)
1. Logical quantum: every tested period meets the criteria; by the strict "smallest passing" rule 100 ms passes, but its
   margin is thin (12.8 ms timer jitter = up to 13 % of P; a measured 108 ms host stall would overrun; 21 % guest CPU).
   Recommended T = 150 ms (175 ms as fallback); movement speed tuned by the deterministic cadence accumulators.
2. Mapping: UP PF7, DOWN PF8, LEFT PF10, RIGHT PF11 (c3270 keymap); native PF keys for diagnostics; U/D/L/R + ENTER fallback.
3. Latency: key -> MVS <= one quantum (+ timer jitter), visible in the same quantum's frame (+ about 21 ms compose).
4. Queue semantics: drain every AID each quantum (up to 2 seen), apply in order to one requested-direction register
   (latest wins) with the TTL; no host queue. With typeahead OFF no stale backlog can exist.
5. Keyboard restore: every quantum's single write carries WCC restore (the frame, or `F1 C2` when nothing changed);
   never conditional on a received AID (CLEAR is swallowed). Redraw = PA2 (or a keymap key mapped to PA2), not CLEAR.
6. CPU: host unchanged; guest about 14 % at 150 ms (120x27); idle states (before start, pause) should block in TGET.
7. Platform: production needs a non-blocking poll (PACFSIO op POLL = TGET ASIS,NOWAIT without the 0.5 s wait) and a
   TOD/deadline service (PACTSO ops TIME = STCK, WAIT-until-deadline = STIMER WAIT,MICVL remainder). Writes need nothing
   new (SENP/SEND/SENX; `F1 C2` = SENP of the WCC alone).
8. D28: start the clock at the first direction AID (press-to-start, blocking read); that AID releases the retention.
Production c3270: `-model 2 -oversize auto`, keymap arrows -> PF7/8/10/11, `c3270.typeahead: false`.
