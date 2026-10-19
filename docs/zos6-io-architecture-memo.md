# ZOS-6 terminal I/O architecture - decision memo (read-only investigation; nothing built, run or changed)

Inputs: the frozen probe evidence in `<raw-trace-dir>` (checker outputs, read-only re-analysis of the frozen traces),
docs/zos6-r1-t3-analysis.md, docs/zos6-protocol-probe.md, src/asm/PACFSIO.asm, and IBM z/OS TSO/E Programming Services
(SA32-0973) topics listed in section H. Every statement is marked **[D]** documented by IBM, **[O]** observed in our
evidence, or **[I]** inference / hypothesis.

## A. Evidence

| Run | Output / input calls | Frames | Host timing | Terminal arrival | Direction | AIDs |
|---|---|---|---|---|---|---|
| R1-T3 (PACMAN) | TPUT NOEDIT NOHOLD / TGET NOWAIT, 150 ms | 432 game writes (65.5 s window) | on schedule | - | 24 empty SDI+KRI, 24 BID; SDI+KRI gaps median 2.1 s, max 46.8 s | PF9 not sent (no unlock in 5 s) |
| P0 | same as R1, probe | 133 | ELAPSED 19950, MAXLATE 1, MAXPUT 1 | mean 183.6 / med 169.5 / p95 295; lag by thirds 1.1 / 3.4 / 4.8 s | 49 SDI+KRI frames, 49 BID; unlock med 116, lock max 511 | 3 sent, 3 on wire, **0 received** |
| PT | TPG NOEDIT,WAIT,NOHOLD / TGET NOWAIT | 4 | no normal end | gaps about 5 s (each after an AID) | SDI on every frame, no BID / KRI | 3 on wire, 0 received; stalled |
| PN-T2 | TGET NOWAIT before TPUT NOHOLD | 133 | 19950 / 1 / 1 | med 150, max 637 | 0 SDI / KRI / BID, no unlock window | **not exercised** (driver stopped at transition ENTER) |
| PH | TPUT NOEDIT,WAIT,HOLD every quantum | 133 | ELAPSED 20155, LATE>75 96, MAXLATE 359, MAXPUT 509 | mean 149.2 / med 116 / p95 406; lag flat (about -0.2 s) | 7 empty SDI+KRI, 7 BID; unlock med 113, lock max 3108 | 3 / 3 / **3**; wire to host about 826-843 ms |
| PB4 | HOLD on q mod 4 = 0 (33), NOHOLD otherwise | 133 | ELAPSED 20192, LATE>75 100, MAXLATE 588, MAXHOLD 737 | mean 149.6 / med 113 / p95 292; lag flat (-49 / -32 / -64 ms) | 15 SDI+KRI frames, 15 BID; unlock med 110, lock max 1845 | 3 / 3 / **3**, all at barrier quanta 44 / 72 / 108; wire to host 1281-1301 ms |

Host send floor (new read-only measurement on the frozen traces) **[O]**: the interval from one host frame to the next
host record is never below 108 ms (P0 min 115 / med 118; PH 112 / 116; PB4 108 / 112), even in P0 with seconds of
output queued; BID-response to the announced data is the same (med 112-150). The terminal answers every record in
0-1 ms (TN3270E header RESPONSE-FLAG 02, ALWAYS-RESPONSE). So the host sends at most one record per round trip of
about 110-118 ms on this path.

## B. Proven
1. **[O]** TGET ASIS,NOWAIT does retrieve terminal AIDs on z/OS under TN3270E CR (PH 3/3, PB4 3/3, driver == wire ==
   host).
2. **[O]** With one NOHOLD frame per 150 ms, TSO output accumulates without bound (P0 lag 1.1 / 3.4 / 4.8 s) and AIDs
   that reach the wire are never returned by TGET NOWAIT during the loop (P0, after dozens of later polls).
3. **[O]** HOLD (every frame or every 4th) keeps the terminal lag bounded and makes the AIDs retrievable.
4. **[O]** HOLD costs a synchronous wait of up to 509 ms (PH) / 737 ms (PB4) inside the 150 ms loop.
5. **[O]** TPG per frame stops output until the terminal sends an inbound (PT); poll-before-output gives no
   send-state opportunity at all (PN-T2).
6. **[O]** The host-to-terminal path carries at most one record per about 110 ms here.
7. **[D]** TPUT HOLD: the program "cannot continue ... until this output line is written to the terminal or
   deleted"; NOHOLD returns once the line is in the terminal output buffers.

## C. Strongly indicated, not proven
1. **[D]+[O]** TSO gives the terminal its turn only when no output is pending. STBREAK (default YES) documents: if no
   output is pending (and buffers are free) the keyboard is unlocked; a TPUT issued before the user starts typing halts
   the read and sends the output. Matches R1-T3 / P0 (SDI+KRI only when the queue momentarily empties), PH / PB4
   (empty queue at each HOLD).
2. **[I]** AID retrieval is coupled to the drain / change-direction cycle: every PB4 AID was consumed on a barrier
   quantum (3 samples), PH (drain every quantum) retrieved them, P0 (never drained) did not. Not proven that
   retrieval can happen only on a drained queue.
3. **[I]** Budget: one frame costs one round trip (about 112 ms); a turn for the terminal (end bracket, then the
   host's BID) costs at least one more. At 150 ms per frame the slack (about 35 ms) cannot pay for a direction cycle
   on every frame, so with continuous NOHOLD output either the queue grows (P0) or the loop waits (PH / PB4). A
   direction cycle every k frames fits only if k x 150 >= (k + 1) x 112, i.e. k >= 3 - and only if the queue really
   empties then, which TSO decides, not the program.
4. **[O] unexplained:** wire-to-TGET latency of about 0.83 s (PH) and 1.29 s (PB4), roughly constant per run.

## D. Rejected
- TPG per quantum (PT: output stalls until inbound). Poll-before-output (PN-T2: no send window). "TGET NOWAIT cannot
  receive AIDs" (PH / PB4). "The AID is lost by one late poll" (P0: dozens of later polls). HOLD on every quantum as
  the REALTIME design (PH-3). Periodic HOLD at N = 4 for REALTIME timing (PB4-B). The WCC keyboard-restore bit
  deciding send ownership (R1-T3). A barrier-interval sweep (decision of record).

## E/F. Candidate architectures (ranked)

| # | Candidate | Correctness | Latency | Complexity | Shutdown | TSO / ISPF / Z Xplore | PACFSIO impact |
|---|---|---|---|---|---|---|---|
| 1 | Output below link capacity (fewer NOHOLD writes) | medium-high | medium (unknown retrieval latency) | low-medium | trivial | full | none or small; changes the REALTIME model |
| 2 | Periodic HOLD barrier | proven | poor (0.5-0.7 s stalls) | low | as PH (PA1 / disconnect) | full | small |
| 3 | STBREAK NO | unknown | unknown | low | unknown (may stall like PT) | full, but a terminal-control change | small |
| 4 | Input subtask with TGET WAIT (P2) | does not address the budget | - | high | not documented | full | large |
| 5 | STAX / STTMPMD KEYS=ALL | not applicable to PF keys | - | - | - | - | - |
| 6 | VTAM API below TSO | not available | - | very high | - | no | replaces it |

1. **Output below link capacity.** Facility: the existing TPUT NOEDIT (NOHOLD) and TGET ASIS,NOWAIT (PACFSIO SENP /
   POLL), STBREAK default. Options: none new. Flow: the game ticks every 150 ms and polls every tick, but writes a
   frame only when the host can afford it (e.g. every second tick, or only changed frames), so the output queue empties
   between writes. Direction: TSO ends the bracket when nothing is pending **[D, STBREAK]**; the terminal gets SDI+KRI
   and can send. Wake-up: the next TGET NOWAIT poll. Shutdown: nothing blocks; the existing FSOF path. Risks: it
   breaks the D33 REALTIME contract "one write per quantum" (ref_rt oracle, ZOS-6 checker) - a design decision, not a
   tuning; the floor is the round trip of this network path (other users / paths differ); the 0.8-1.3 s retrieval
   latency is unexplained; halves the visual frame rate.
2. **Periodic HOLD barrier.** Facility: TPUT NOEDIT,WAIT,HOLD every N writes. Direction: drained queue at the barrier.
   Wake-up: TGET NOWAIT after the barrier. Shutdown: PA1 (TPUT RC 8) or disconnect (RC X'14') if a HOLD blocks; the
   60 s guard cannot interrupt it. Risk: synchronous stalls up to N round trips; PB4 already unsuitable.
3. **STBREAK NO.** Facility: STBREAK NO (TSO/E terminal control). Documented: the transmit-interrupt (break) feature
   is not used; a 3270 keyboard "is normally unlocked"; output waits until the user finishes the current line.
   Direction under TN3270E CR: undocumented. Wake-up: TGET NOWAIT. Shutdown: TPUT NOHOLD does not block, but the
   output may stop flowing (PT-like); STBREAK YES must be restored. Risks: a session-level terminal-control change
   (needs explicit approval), behaviour on VTAM 3270 under CR unknown.
4. **P2 input subtask** (ATTACH, TGET ASIS,WAIT, ECB / POST, DETACH). Unchanged blocker: no documented way for another
   task to complete a pending TGET WAIT (only input, attention RC 8, disconnect RC X'14'); DETACH of an incomplete
   subtask is an abnormal termination. And by C.1-C.3 a pending TGET would not create direction cycles: input still
   needs the queue to empty. Not pursued.
5. **STAX / STTMPMD.** STAX exits get control on an attention interruption (PA1 / ATTN); PF keys are ordinary AIDs.
   STTMPMD KEYS=ALL passes only the PA1 and CLEAR indications **[D]**. Not applicable.
6. **VTAM API below TSO.** **[I]** The LU2 session belongs to TSO/VTAM (TCAS / VTIOC); a TSO command processor has no
   documented interface to issue SEND / RECEIVE or direction indicators on it, and an own VTAM application needs
   installation VTAM definitions, impossible on Z Xplore. Not pursued. Installation tuning (TSOKEY00 buffer
   parameters) is likewise outside our control.
- Not candidates: removing ALWAYS-RESPONSE or CR (forbidden / not program-controlled).

## G. Next experiment
Documentation plus evidence support exactly one hypothesis that keeps a non-blocking loop: STBREAK YES (the default
already in effect) unlocks the keyboard when no output is pending **[D]**, and the measured floor (about 112 ms per
record) shows that 150 ms per write cannot leave the queue empty **[O]**. The single experiment that would test it is
a probe mode with the P0 calls (TPUT NOEDIT NOHOLD, TGET ASIS,NOWAIT every 150 ms tick) but a frame written only on
every second tick (300 ms between writes, above two round trips): does the queue stay empty, does an SDI+KRI appear
after each write, are the AIDs retrieved without HOLD, with what latency?

It is NOT proposed for execution now: it presupposes that ZOS-6 may decouple the game tick from the write rate,
which changes the approved REALTIME model (one write per quantum, D33) and the oracle. That is a design decision for
the user. If that model change is not acceptable, no documented mechanism found here yields input at 150 ms with
continuous output, and deeper research is required (TSO/VTAM VTIOC bracket / inbound processing rules; STBREAK NO
behaviour on VTAM 3270 under TN3270E CR; the cause of the 0.8-1.3 s wire-to-TGET latency).

## H. Sources (IBM, z/OS TSO/E Programming Services)
TPUT (writ.htm), Return Codes from TPUT (rctput.htm), Register Form of TGET and TPUT, Using TGET (utmglt.htm), Return
Codes from TGET, STBREAK - Set Break, STFSMODE (stfs.htm), STTMPMD, STATTN (attnsim.htm), TCLEARQ, STAX (stx.htm),
DETACH (Assembler Services Reference), TSOKEY00 (Init and Tuning Reference), all under ibm.com/docs SSLTBW.

## I. PR2 - render every 2nd logical quantum (user-accepted evidence; read-only causal analysis)

### I.1 Evidence (frozen PR2 trace, checker output)
| Item | PR2 |
|---|---|
| Logical quanta / physical writes / skipped | 133 / 66 / 67; frame step 2; frames Q2, Q4, ..., Q132 in order, none replayed |
| Host | ELAPSED 19950 ms, LATE>75MS 0, MAXLATE 1, MAXPUT 0, RCOUT 0, RCIN 0, AIDS 3, HOLDS 0 |
| Physical arrival gaps | mean 293.6 / median 300 / p95 410 / max 502 ms |
| Lag vs logical schedule, by thirds | about -300 / -333 / -329 ms: bounded (P0: 1.1 / 3.4 / 4.8 s) |
| Direction | 57 SDI+KRI frames, 59 BID, 0 SIGNAL; unlock median 183 / max 300 ms; locked median 116 / max 332 ms |
| AIDs | 3 planned / attempted / sent, exercised; driver == wire == host; consumed at q40 / q74 / q108 (even = write quanta) |

### I.2 Clock alignment (correction of the wire-to-host latency)
**[O]** The checker's wire times are measured from the arrival of the first frame; the probe's host ms from its own
T0. Those origins differ: the first PR2 frame reached the terminal about 0.6 s after its host issue (start-up output).
Subtracting them directly gives the 0.94-1.07 s figure. Alignment from the trace: whenever the line is idle, TSO sends
the BID for a new frame at once; the three BIDs announcing Q38 / Q72 / Q106 appear at wire +4926 / +10038 / +15128
for host issue times 5550 / 10650 / 15750 ms: a host-to-terminal delay of 624 / 612 / 622 ms on the checker's wire
scale, i.e. host time H reaches the terminal at about H - 620 (this includes the unknown one-way transit t, 0..110 ms;
the round trip is about 110 ms, section A). Hence, with t unknown in [0, 110]:
- AID sent -> host TGET that returned it = H(q) - 620 - t - wire(AID): PF4 209-319 ms, PF5 299-409 ms, PF6 339-449 ms
  (t = 55: 264 / 354 / 394 ms). Not about 1 s.
- Same alignment for PH (TGET right after the HOLD that returned once its frame was answered): PF4 / PF5 / PF6 =
  363 / 361 / 380 ms + t (about 0.42-0.44 s at t = 55), not 0.8 s. PB4 (barrier q44 / q72 / q108): 608 / 632 / 614 ms
  + t (about 0.66-0.69 s), not 1.3 s.

### I.3 Per-AID timelines (wire ms from the first frame; kybd = c3270 keyboard lines)
| | PF4 | PF5 | PF6 |
|---|---|---|---|
| Frame before (direction) | Q36 rq03 +4739 (SDI+KRI), unlock +4740 | Q70 rq03 +9842, unlock +9844 | Q104 rq03 +14960, unlock +14961 |
| Driver Wait start / unlock / x3270if return | 68730 / 68750 / 69095 (epoch ms mod 1e5) | 73729 / 73755 / 74033 | 78728 / 78813 / 79156 |
| Wire AID | +4911 (= 68761, 11 ms after the driver saw the unlock) | +9921 (= 73771) | +14981 (= 78831) |
| Host records after | BID +4926, Q38 rq03 +5241, BID +5363, Q40 rq00 +5479, Q42 rq03 +5635 | BID +10038, Q72 rq03 +10179, BID +10481, Q74 rq03 +10594 | BID +15128, Q106 rq03 +15301, BID +15596, Q108 rq03 +15709 |
| AID reaches host (H = wire + 620 + 2t) | 5531..5751: after q38's write | 10541..10761: around q72's write | 15601..15821: around q106's write |
| TGET polls after arrival without the AID | q39 (odd) if t < 84; q38 if t < 10 | q73 (odd) for every t; q72 if t < 55 | q107 (odd) for every t; q106 if t < 75 |
| Consumed (AIDCNT + 1) | q40 (even, after the TPUT of Q40) | q74 (even) | q108 (even) |
| Records between AID and the consumed quantum's frame | 2 frames, 2 BID, 1 SDI | 2 frames, 2 BID, 2 SDI | 2 frames, 2 BID, 2 SDI |

The x3270if PF() call returns only after the keyboard locks / the host answers: the driver's `sent` (262-345 ms after
the wire AID) is a return time, not the transmission time; the wire time is authoritative. Per-TGET return codes are
NOT recorded by the probe: only AIDCNT (incremented on RC 0 with data, at q40 / q74 / q108), RCIN = 0 (no RC other
than 0 / 4 ever) and the host ms of the consuming TGET.

### I.4 PH / PB4 / PR2 comparison (aligned latencies, t = one-way transit)
| | Output policy during the delay | Writes on wire between AID and the consuming quantum's frame | BIDs | SDI records | First output after AID | Output before the consuming TGET | Aligned latency |
|---|---|---|---|---|---|---|---|
| PH | HOLD every quantum | 1 (Q70 / Q91 / Q125 itself) | 1 | 0 | BID + frame of the next quantum | that quantum's HOLD TPUT | 0.36-0.49 s |
| PB4 | 3 NOHOLD + barrier | 3 (Q42-Q44 etc.) | 1 | 0 | BID + next frame | the barrier HOLD TPUT (q44 / q72 / q108) | 0.61-0.74 s |
| PR2 | NOHOLD on even quanta, nothing on odd | 2 | 2 | 1-2 | BID + next even frame | that even quantum's NOHOLD TPUT | 0.21-0.45 s |
In every run the AID was sent in the unlock window right after a record with SDI+KRI (PH: an empty rq03 control),
and the host's next BID followed it on the wire 15-147 ms later. In PH the first TGET after the AID returned it; in
PB4 the host was late after each barrier, so the polls of q41-q43 most probably ran before the AID existed (not
determinable without per-poll timestamps).

### I.5 What precedes application visibility
- **[O]** All nine AIDs (PH, PB4, PR2) were returned by a TGET that came right after a TPUT in the same quantum. In PR2
  at least one no-write poll (q73, q107 for any t; q39 for t < 84) ran after the AID had reached the host and did not
  return it. No single wire event (the crossing BID, its response, a given SDI+KRI frame, a fixed number of writes)
  fits all three PR2 cases within the alignment uncertainty.
- **[D]** STBREAK YES (in effect): with no output pending the keyboard is unlocked; a TPUT issued before the user starts
  typing halts the read and the output is sent; interrupted input from a 3270 is passed to the program.
- **[I]** TSO makes the arrived input available to TGET when the program's next output halts the pending terminal
  read, not when the inbound arrives. Consistent with all nine AIDs and with STBREAK; not proven. P0 fits only with an
  extra assumption (with seconds of output queued, the new TPUT does not reach that path); unknown.

### I.6 The latency: classification of its parts
- Network transport: about t (half of the about 110 ms round trip) - small part. **[O]/[I]**
- Terminal send opportunity: not the delay - each AID left the terminal 20-171 ms after an unlock. **[O]**
- Application polling: in PR2 the inbound waits for the next even (writing) quantum, up to 300 ms - the odd polls do
  not see it. **[O]** (which poll exactly depends on t: unresolved)
- TSO buffering / delivery: the inbound is not available to TGET on arrival; it becomes available by the TGET that
  follows the next TPUT. **[I]**, mechanism undocumented.

### I.7 Do the odd no-write quanta create input opportunities?
- For the TERMINAL, yes **[O]**: 57 SDI+KRI frames, unlock windows median 183 ms, locked at most 332 ms, every PF sent
  at the first attempt with the keyboard unlocked.
- For the APPLICATION, no observable benefit **[O]**: no AID was ever returned by an odd-quantum poll; the odd polls
  after the AID's arrival returned nothing.

### I.8 Next step
The causal question is not yet answerable from the frozen evidence: the probe does not record which TGET ran when,
with which RC. The only experiment the evidence justifies is a measurement, not a new mechanism: PR2 unchanged plus
host-side per-quantum instrumentation (for each quantum: write or not, host ms before / after the TPUT, TGET RC and
length, host ms) printed compactly in the line-mode summary. It would settle whether delivery follows the TPUT and
remove the t ambiguity. Not prepared; for review. The corrected aligned latency (PR2 about 0.26-0.39 s at t = 55)
should be taken into account when the PR2-D classification is reviewed.

### I.9 Review outcome (user, 2026-10-19) and PR2I
- PR2-D withdrawn; PR2 is classified **PR2-A**: it validates simulation / presentation decoupling as the leading
  z/OS architecture candidate (150 ms logical clock, 66 coalesced NOHOLD writes, bounded backlog, no HOLD / TPG /
  blocking input, 3 / 3 AIDs at about 0.21-0.45 s aligned latency; t = 55 ms is an illustration, not a measurement).
  Not ZOS-6 acceptance; D33 unchanged until a separate decision.
- The PR2 trace is exactly 262144 bytes; it is complete (Trace started / Trace stopped, 66 frames, full driver plan,
  closure, checker integrity, stable SHA-256). Recorded as a curiosity; no rerun on that ground.
- Remaining question (input-delivery causality and optimisation, not whether decoupling works): which TGET first
  returns each AID, and whether no-write polls after the AID's transmission reported no input. PR2I (protocol probe
  section 13) records RC, length, AIDCNT and host times per quantum, printed after the loop. Outcomes PR2I-C1 (an odd
  poll returns the AID), C2 (odd polls empty, first success right after the next TPUT), C3 (another event), C4
  (instrumentation perturbs timing / protocol).


## J. Probe investigation closed (user, 2026-10-19)
PR2I accepted and frozen: **PR2I-C2** (trace SHA-256 `6e9dce16f6861ca65fd71dd9ffc47c9da5f4b2f6f8d56f8c10d6e550f09789fe`,
checker RC 0; QUANTA 133, ELAPSED 19950, LATE>75 0, MAXLATE 1, WRITES 66, SKIPPED 67, AIDS 3, frames q2..q132, no
replay). F4 / F5 / F6: the no-write polls q37 / q39, q71 / q73, q105 / q107 and the write polls q38 / q72 / q106 returned
RC 4; the write polls q40 / q74 / q108 returned RC 0, length 100, the AID, AIDCNT + 1; odd_hits = []. **[O]** every AID
first returned by a TGET immediately after a physical TPUT NOHOLD, the preceding no-write poll RC 4 each time. **[I]**
(strong) AID visibility is coupled to a subsequent output / direction cycle on this TSO / VTAM / TN3270E path. Not
claimed: that IBM documents TPUT as the mechanism that releases the AID; that no-write polls are useless in general.
PR2I transport was noisier (SDI/KRI 50, BID 53, locked max 797 ms, arrival max 945 ms) with the logical scheduler
identical to PR2: PR2 (PR2-A) remains the performance baseline; no timing threshold is derived from PR2I.

| Probe | Result |
|---|---|
| P0 | queue grows, input not delivered |
| PT | per-frame TPG rejected |
| PN | no useful send opportunities |
| PH | input works, HOLD timing rejected (PH-3) |
| PB4 | bounded queue / input, periodic HOLD timing rejected (PB4-B) |
| PR2 | PR2-A: decoupling validated |
| PR2I | PR2I-C2: output-cycle-coupled delivery strongly supported |

No further protocol probe is authorised (no PR3 / PR4, PR2 / PR2I rerun, PB / PH / PT / PN, STBREAK NO or P2). All
evidence hashes above and in sections A / I are preserved; raw traces stay outside git (`<raw-trace-dir>`). Next: the
production design, docs/zos6-production-design.md (proposal for review).
