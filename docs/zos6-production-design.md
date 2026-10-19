# ZOS-6 REALTIME production design - logical / presentation decoupling (APPROVED; implemented locally)

Status 2026-10-19: accepted in principle, revised for the five review items (input phases section 6, PRESENT(EVERY)
section 14, death rule section 9, frame sizes section 15, display state section 16), then APPROVED for local
implementation and implemented locally (section 18: not built, not installed, no z/OS access, no live run, nothing
committed). Inputs: the probe series (docs/zos6-protocol-probe.md), the decision memo (docs/zos6-io-architecture-
memo.md), the approved ZOS-6 design (docs/zos6-design.md, D33 baseline) and the sources on branch zos (PACMAIN, PACRT,
PACDISP, PACSCR, PACPLAT, PACFSIO, PACTSO, PACREQ, src/zos/PACMAN.clist, tools/zowe/zos6_live_check.py,
tests/ref_rt.py). Markers: **[D]** documented by IBM, **[O]** observed in our frozen evidence, **[I]** inference,
**[P]** proposal (the [P] items are now approved; ZV-D33 approved for ZOS-6 validation).

## 1. Final probe conclusions (accepted by the user)
| Probe | Classification | Conclusion |
|---|---|---|
| P0 | - | one NOHOLD write per 150 ms: TSO output queue grows (lag by thirds 1.1 / 3.4 / 4.8 s); AIDs reach the wire, never the program |
| PT | rejected | TPG per frame: output stalls until an inbound |
| PN | rejected | poll before output: no useful send opportunities (AID test not exercised in PN-T1 / PN-T2) |
| PH | PH-3 | HOLD every quantum: input works, HOLD timing rejected (MAXHOLD 509 ms, LATE>75 96) |
| PB4 | PB4-B | periodic HOLD: bounded queue and input, periodic HOLD timing rejected (MAXHOLD 737 ms) |
| PR2 | **PR2-A** | 150 ms logical clock, writes on even quanta only, NOHOLD, no catch-up: decoupling validated; primary performance evidence |
| PR2I | **PR2I-C2** | PR2 + host table: output-cycle-coupled AID delivery strongly supported; causal evidence only |

PR2 (trace SHA-256 `1e3093d7...a958ea`) **[O]**: 133 logical quanta / 66 writes / 67 skipped, ELAPSED 19950, LATE>75 0,
MAXLATE 1, frames Q2..Q132 in order, none replayed; physical gaps mean 293.6 / median 300 / p95 410 / max 502 ms; lag
vs the logical schedule by thirds about -300 / -333 / -329 ms (bounded); 57 SDI+KRI, 59 BID, locked max 332 ms; AIDs
3 / 3. Aligned AID-send-to-consuming-TGET latency 0.21-0.45 s (t = 55 ms illustration 264 / 354 / 394 ms; the one-way
component is not measured). The earlier ~1 s figure was an invalid subtraction of different clock origins and is not
used anywhere in this design.

PR2I (trace SHA-256 `6e9dce16f6861ca65fd71dd9ffc47c9da5f4b2f6f8d56f8c10d6e550f09789fe`, checker RC 0) **[O]**: QUANTA 133,
ELAPSED 19950, LATE>75 0, MAXLATE 1, WRITES 66, SKIPPED 67, AIDS 3; frames exactly q2..q132, frame_step 2, no replay.
Per-AID polls (host table):

| AID | q-3 (no write) | q-2 (write) | q-1 (no write) | q (write) |
|---|---|---|---|---|
| F4 | q37 RC 4 | q38 RC 4 | q39 RC 4 | q40 RC 0, len 100, AID F4, AIDCNT 0 -> 1 |
| F5 | q71 RC 4 | q72 RC 4 | q73 RC 4 | q74 RC 0, len 100, AID F5, AIDCNT 1 -> 2 |
| F6 | q105 RC 4 | q106 RC 4 | q107 RC 4 | q108 RC 0, len 100, AID F6, AIDCNT 2 -> 3 |

odd_hits = []; all three successful TGETs ran immediately after a physical TPUT NOHOLD; host_pattern
`write-poll-only`. Transport noisier than PR2 (SDI/KRI 50, BID 53, locked max 797 ms, arrival max 945 ms), the logical
scheduler identical: PR2 stays the performance baseline, PR2I is used for causality only, and no timing threshold is
derived from PR2I.

Separation of claims:
- **[D]** STBREAK YES (default): no output pending -> keyboard unlocked; a TPUT issued before the user types halts the
  read and the output is sent; interrupted 3270 input is passed to the program. TGET RC 0 = R1 bytes moved, RC 4 = no
  input.
- **[O]** All three AIDs were first returned by a TGET immediately after a physical write; the immediately preceding
  no-write poll returned RC 4 every time; no no-write quantum returned an AID.
- **[I]** (strong) Under this TSO / VTAM / TN3270E path, application visibility of an AID is coupled to a subsequent
  output / direction cycle.
- Not proven, not claimed: that IBM documents TPUT as the mechanism that "releases" the AID; that no-write polls are
  useless in general (three samples).

## 2. Logical clock (unchanged authority) [P]
- The game clock stays the existing ZOS-6 logical quantum: REQ-RTPER = 150 ms NORMAL, 125 ms FAST (PACMAIN, PARM
  column 24; the only place where the quantum is chosen). Absolute deadlines unchanged: PACPLAT CLOK / WDLN (next =
  last + T, whole missed periods skipped, wait for the remainder by PACTSO DLWT).
- Every executed logical quantum still runs exactly once the unchanged sequence RT-COLLECT -> PACRT RQ (animation
  frame, death freeze, ghost cadence 4/5, request / TTL, player step, PACGAME MOVE with REQ-STEP B / P / G, score,
  lives, win / loss, freeze start) -> presentation decision -> WDLN. PACRT, PACGAME, PACMAP, PACAI are not touched.
- The 1.5 s freeze stays RT-FRT logical quanta (10 at 150 ms, 12 at 125 ms by RT-CONV), READY! RT-RDY and the popup
  RT-PUQ likewise: all counted in logical quanta, never in physical frames.
- The game is not converted to a 300 ms loop; nothing in the logical path knows whether a quantum was presented.

## 3. Independent presentation scheduler [P]
Owner: the platform adapter PACPLAT (z/OS terminal / link pacing), new op `PSLT` (presentation slot). Policy expressed
as a presentation deadline in LOGICAL time, not as a modulo rule:

```
state (PACPLAT WORKING-STORAGE): PS-TP  PIC 9(4) VALUE 300   minimum presentation interval, ms (PR2-A evidence)
                                 PS-ACC PIC 9(5)             logical ms since the last presented quantum
PSLT in : REQ-PRES 'B' = base (the start quantum, the resume quantum)  'Q' = an ordinary running quantum
     out: REQ-PRES 'Y' = present this quantum (one physical write)     'N' = coalesce (no compose, no write)
  REQ-PMODE not 'C' or REQ-MODE not TSC / TSD   -> 'Y'                 (D33 baseline: every quantum written)
  'B'                                            -> PS-ACC = 0, 'Y'
  'Q'  PS-ACC = PS-ACC + REQ-RTPER
       PS-ACC >= PS-TP                           -> PS-ACC = 0, 'Y'    (reset, not subtract: no catch-up)
       else                                      -> 'N'
```

Properties:
- Deterministic: depends only on the sequence of executed logical quanta, never on wall-clock lateness, so the TSD dry
  run, the Python model and the live TSC stream produce the same physical frame sequence for the same cards (the
  checker can stay byte-exact).
- When a slot occurs the CURRENT logical state is composed (PACSCR RTQF: the image rebuilt from the state, diffed
  against VS-PREV = what the terminal really shows, because a skipped quantum is never composed) and sent once by the
  existing path (PACPLAT SEND -> PACFSIO SENP / SENX = `TPUT NOEDIT`, defaults WAIT,NOHOLD). Skipped states are
  coalesced, never replayed. No HOLD, no TPG, PACFSIO unchanged.
- No catch-up bursts: at most one physical write per executed logical quantum by construction, the accumulator is
  reset (not decremented) on a slot, and the logical loop itself never runs faster than its absolute deadlines (WDLN
  skips whole missed periods).
- Late execution: if quanta run late, presentation slows with them in wall time (the slot is the next executed quantum
  that satisfies the interval); the current state is sent once; nothing is queued for later. The one residual case:
  after a missed deadline WDLN may let one quantum run immediately (deadline in (now - T, now]); two presented quanta
  can then be about one T apart once - bounded, never cumulative.
- Not "sleep twice as long": the loop keeps its 150 ms deadlines and polls; only the write is coalesced.

Writes outside the cadence (each one a response, never a replay):
- start: the quantum of the press-to-start AID is presented (PSLT 'B'), and the grid starts there;
- resume: the resume quantum is presented (PSLT 'B') and the grid re-bases there (same rule as CLOK re-basing);
- PAUSED screen, pre-start prompt screens, the END / closure screens: unchanged paths, not quantum writes;
- prompt-type quantum frames (ENTER-typed input, invalid input, PA2 redraw: RT-FRAME P / F) are NOT forced: RT-FRAME is
  kept pending (F dominates P) and used by the next presented quantum. The keyboard restore therefore comes with the
  next slot (<= one presentation interval).
- the deciding quantum (WIN / LOST) is not forced: the END path shows the final state.

## 4. NORMAL policy [P]
T = 150 ms, PS-TP = 300 ms -> PS-ACC 150 (N), 300 (Y): one physical write every second logical quantum after the
start / resume quantum, i.e. the PR2-A cadence, the only validated one (66 frames, median gap 300 ms, bounded lag,
3 / 3 AIDs). The parity is anchored at the start / resume quantum, not at even q.

## 5. FAST policy and remaining uncertainty [P]
Derivation (FAST logical semantics unchanged: T = 125 ms, freeze 12 quanta, READY! 5, popup 6 by RT-CONV):
- Demonstrated link capacity **[O]**: PR2 sustained one frame per 300 ms with a terminal direction cycle in most
  intervals (57 SDI+KRI / 66 frames); P0 at 150 ms per frame drained at about 184 ms per frame (mean arrival gap 183.6)
  with the queue growing; the host-to-terminal floor is one record per 108-118 ms; memo C.3 **[I]**: a frame plus a
  terminal turn costs about 2 x 112 ms.
- Rule chosen: the same minimum interval PS-TP = 300 ms in logical time (the link property does not depend on the game
  speed) -> PS-ACC 125, 250 (N), 375 (Y): one write every third FAST quantum = 375 ms, uniform (three cells of
  movement per frame). No physical interval is ever shorter than the demonstrated 300 ms.
- Rejected without evidence: every second FAST quantum (250 ms, never demonstrated, below the PR2 cadence, inside the
  frame + turn budget by only about 25 ms) and an anchored 300 ms grid (alternating 250 / 375 ms gaps, the same 250 ms
  exposure plus uneven 2 / 3-cell steps).
- Remaining uncertainty: FAST presentation at 375 ms has never run live; R2 is its acceptance (section 10). If R2 shows
  a bounded queue and acceptable latency, 375 ms stands; a faster FAST cadence (250 ms) would need its own later live
  question, not run now. The FAST input-to-visible latency is about 75 ms longer than NORMAL (section 11).

## 6. Input polling and input phase semantics [P] (review item 1, resolved 2026-10-19)
### 6.1 Phase order of one running logical quantum k (TSC; the code positions are PACMAIN RT-QUANTUM)
```
 A  input        RT-COLLECT: TGET ASIS,NOWAIT until none (all modes; BAT / TSD: the card of quantum k)
                 each event -> RT-EVENT -> PACRT RIN (latched in PACRT, see 6.2); Q ends here (no step k)
                 PAUS -> RT-PAUSED (blocking reads; resume: CLOK re-base, RT-PBASE = 1, RT-COLLECT again)
 S  game step    PACRT RQ: consumes the latch (REQ-RTIN = the events of quantum k), one logical step k
 D  decision     PACPLAT PSLT -> REQ-PRES Y / N                        (PRESENT(EVERY): always Y)
 R  screen build PACDISP RTQF: Y = compose quantum k (PACSCR RTQF / prompt), N = display state only (section 16)
 W  TPUT         Y only: PACPLAT SEND -> PACFSIO (TPUT NOEDIT, NOHOLD)
 B  post-write   Y and PRESENT(COALESCED) and TSC only: RT-COLLECT again -> PACRT RIN (latched for quantum k + 1)
    input        Q ends here (no step k + 1); F-WON / F-LOST are tested before B (an ended game does not read)
 T  deadline     PACPLAT WDLN (absolute deadline; skipped when the game is over)
```
### 6.2 Which logical quantum consumes an AID
- A of quantum k -> consumed by step S of quantum k (as today).
- B of quantum k -> consumed by step S of quantum k + 1. Step k and frame k are complete before B runs.
- Both B of k and A of k + 1 obtain input before step k + 1: all of those events belong to quantum k + 1, applied in
  retrieval order (B first, then A; within each read the TSO queue order). This is exactly the existing several-inputs
  card rule (RTMULTI): the latest direction wins (RT-REQ, TTL 3), each PF9 toggles pause, Q ends at once, ENTER /
  invalid / PA2 set the pending prompt frame (F dominates P), at most 8 events recorded in REQ-RTIN, all applied.
- Pending-input / latch model: no new latch is needed. PACRT RIN already is one: it only changes PACRT's pending
  fields (RT-REQ, RT-TTL, RT-START, RT-PAUSE, the WS-IN record) that the NEXT RQ reads; PACMAIN keeps RT-FRAME pending
  until the next presented frame. RIN's gating (directions ignored while paused or frozen) reads RT-PAUSE / RT-FRZ,
  which no code changes between B of k and A of k + 1, so an event gets the same treatment in B as in A.
- No retroactivity: nothing in B touches step k or frame k. Q in B: PACGAME QUIT after step k, the loop ends - the same
  logical result as Q in A of k + 1 (step k + 1 never runs). PF9 in B: pause before step k + 1; the PAUSED screen comes
  at the top of quantum k + 1 after the deadline T (the same logical point as PF9 in A of k + 1).
- Card equivalence for the model and the checker: card(k + 1) = events(B of k) ++ events(A of k + 1). The checker
  places AIDs on logical quanta (section 9); whether B or A read an AID is not observable and does not matter.
### 6.3 Rationale and limits
- Kept: the top poll A in EVERY logical quantum (all modes), including no-write quanta; PR2I does not show those polls
  useless in general (three samples).
- B reproduces the only delivery point observed in PH / PB4 / PR2 / PR2I (TGET right after a TPUT, probe order write ->
  poll -> wait) and is logically neutral (6.2). It costs one TGET NOWAIT per physical write. COALESCED-only (section
  14): PRESENT(EVERY) keeps today's single poll per quantum.
- Not in BAT / TSD (a read there consumes a card): card semantics and oracle 310 stay byte-identical. Blocking reads
  (pre-start, pause) unchanged.
- Expected practical input latency includes the physical presentation cycle **[I]**: an AID is typically read by B
  after the next physical write, applied in the next logical quantum, and shown by the following physical write (about
  one presentation interval later). Not claimed as a law; measured per AID by the checker.

## 7. Implementation layer, routines and state [P]
Decision: the policy belongs in **PACPLAT** (platform adapter: already owns CLOK / WDLN, POLL, SEND and the terminal
transport decisions), driven by a two-line hook in **PACMAIN**'s REALTIME loop; **not PACFSIO** (a pure TPUT / TGET
service, unchanged since ZOS-5; a suppressed TPUT there would leave PACSCR's VS-PREV describing an image the terminal
never received, so every later partial diff would be wrong) and not PACRT / PACGAME (game logic must stay
platform-independent, D18). PACSCR is unchanged: composing only on presented quanta keeps its diff exact.

Data (PACREQ.cpy, append-only, Z-entry):
```
05  REQ-PMODE   PIC X.   PARM column 26: C = coalesce physical presentation (z/OS TSC); anything else = every quantum
05  REQ-PRES    PIC X.   PSLT in B / Q, out Y / N
```
PACMAIN (Z-entry):
- PARM: `05 PARM-PRES PIC X` (column 26); `MOVE SPACE TO REQ-PMODE`, `IF PARM-LEN > 25 AND PARM-PRES = 'C' MOVE 'C'
  TO REQ-PMODE`.
- RT-GAME / RT-PAUSED: set WS flag RT-PBASE = 1 where CLOK starts / re-bases the clock (start, resume).
- RT-QUANTUM after `PACRT RQ`:
```
           MOVE 'Q' TO REQ-PRES.
           IF RT-PBASE = 1
               MOVE 'B' TO REQ-PRES
               MOVE 0 TO RT-PBASE.
           MOVE 'PSLT' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE RT-FRAME TO REQ-RTFR.
           IF REQ-PRES = 'Y'
               MOVE SPACE TO RT-FRAME.
           MOVE 'RTQF' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ PAC-ARC.
           (F-WON / F-LOST / TSO checks unchanged)
           IF REQ-MODE = 'TSC' AND REQ-PMODE = 'C' AND REQ-PRES = 'Y'
               PERFORM RT-COLLECT THRU RT-COLLECT-EXIT
               IF RT-OVER = 1
                   GO TO RT-QUANTUM-EXIT.
           (WDLN unchanged)
```
  Phase order and input semantics: section 6. With REQ-PMODE not 'C' PSLT always answers 'Y', RT-FRAME is cleared
  every quantum as today and the post-write poll is off (section 14: PRESENT(EVERY)).
PACPLAT (Z-entry): op `PSLT` as in section 3; PS-TP / PS-ACC in WORKING-STORAGE; nothing else changes.
PACDISP (Z-entry): RTQF with REQ-PRES = 'N' does no compose and no send; it advances the display-owned LOGICAL-time
state for one quantum (section 16): the S2 pattern clock (PT-NEXT counted in logical quanta; a step that falls due on a
skipped quantum rings on the next physical write) and CALL PACSCR op `RTQS`. With REQ-PRES = 'Y' the current
SCR-RTQF unchanged. (Stride = PT-G under this policy: 2 / 2 NORMAL, 3 / 3 FAST, so pattern steps land on written
quanta.) S1 single bells and the S2 event class keep their per-screen snapshot (SB-*): physical by design (section 16).
PACSCR (Z-entry, added by the display-state audit): new op `RTQS` (quantum skipped) = `PERFORM RP-STATE THRU
RP-STATE-EXIT` (popup start / position / expiry latched at the quantum where the counter moved) and `PERFORM SET-FACE`
(Pac-Man's facing latched from the step's LAST-CMD / LAST-RESULT); DS-LEN 0; no BUILD-VS, no diff, no KEEP-VS, VS-PREV
and PREV-OK untouched. Never called with REQ-PMODE not 'C'.
CLIST src/zos/PACMAN.clist (Z-entry): keyword PRESENT(EVERY|COALESCED), default EVERY during ZOS-6 development
(section 14); COALESCED appends PARM column 26 `C`, EVERY appends nothing (the PARM stays byte-identical to today).
The MVS CLIST and the MVS release are untouched.
Unchanged: PACFSIO, PACTSO, PACRT, PACGAME, PACMAP, PACAI, PACINPT, PACQRY, PACHSIO, every copybook except PACREQ,
oracle 310, the TURN path.
Deferred to ZOS-7 (ARCADE), recorded now: the RP game-over death frames (PACDISP, six frames one period apart by CLOK /
WDLN = six writes in 0.9 s) must also go through PSLT (proposal: frames shown at the presentation slots, same logical
length); S2 end-pause bell-only writes are already >= 300 ms apart (PT-G periods).
Known cosmetic effect: the animation frame VIS = (q / 3) mod 2 (450 ms) sampled every 300 ms aliases (frames 0 1 0 0 1
0 ...); display only, unchanged model semantics; no change proposed in ZOS-6.

## 8. Proposed D33 z/OS variance (for review; the requirements DOCX is not edited) [P]
D33 stays the historical baseline ("one write per quantum") and remains the MVS contract. Proposed z/OS variance
**ZV-D33** (to be recorded in docs/DECISIONS.md and ZOS-DIFFS only after approval):
1. One logical state update per logical quantum (150 ms NORMAL, 125 ms FAST), every quantum, exactly the 2.0 game
   semantics (movement, ghosts, collisions, timers, freeze, score / state, inputs).
2. A platform may coalesce physical display writes when the terminal / link requires it, provided that:
   a. logical game semantics are preserved (the model of the logical quanta is unchanged; frames are the model's state
      at the presented quanta, byte for byte);
   b. no stale-frame replay occurs (presented quanta strictly increasing; a skipped state is never written later);
   c. the output backlog remains bounded (section 11 B);
   d. input remains usable within an explicit latency requirement (section 11 C);
   e. presentation remains within an explicit cadence requirement (section 11 A).
3. On z/OS TSO / TN3270E (CONTENTION-RESOLUTION) the presentation is coalesced by PSLT with a 300 ms minimum interval in
   logical time; PRESENT(EVERY) keeps the D33 baseline behaviour.
The numbers in 2c-2e are proposals (section 11) and are not final until reviewed.

## 9. Checker redesign (tools/zowe/zos6_live_check.py; before implementation) [P]
Principle: two clocks, never mixed. Logical steps come only from the model; physical frames only from the trace; each
physical frame is tied to the logical quantum q(w) it presents, given by the model. A skipped physical frame is never
read as a skipped logical quantum.
- **Model**: tests/ref_rt.py gains an optional presentation filter (default off = today's behaviour, oracle 310
  untouched): it runs every logical quantum as now and renders / diffs only at the quanta the PSLT rule selects
  (independent re-implementation: accumulator, base at start / resume, pending P / F frame, S2 pattern clock). Output:
  frames with q(w), kinds, rqs per logical quantum (unchanged), plus the presented-quantum list. It also advances the
  display-owned logical-time state on skipped quanta exactly like PACSCR RTQS / the PACDISP pattern clock (section 16).
- **Image invariant** (independent of the filter's diff code): after applying each live quantum frame to a simulated
  3270 buffer, the screen image equals the UNFILTERED (D33) model's image at quantum q(w) (cells, colours,
  highlights); only the data-stream bytes differ (diff against the last presented image). Exceptions, listed: the
  input field of prompt frames, the WCC alarm bit (bells, physical by design), a GS size-guard step taken on a
  different frame than in D33 (then both models must agree on the guard; reported) and (found in implementation) the
  invalid-input message: a one-shot latch (MSG-ON, physical in section 16) shown by the next presented prompt frame, so
  when EVERY shows and clears it inside one coalesced interval the images differ on the message row only.
- **Movement / state progression**: live writes == model frames byte for byte, same count, same order; q(w) strictly
  increasing; Δq per write == the policy (2 NORMAL / 3 FAST, base writes at start and resume) - an extra, missing,
  replayed or burst write fails. Because composition diffs against the last presented image, a wrong logical count
  between two frames shows as a byte mismatch at the next frame.
- **Cards / input causality**: cards stay per LOGICAL quantum. AID window in logical quanta, same causality as 8a
  expressed with physical writes: lo = q(last write that reached the terminal before the AID was sent) + 1 (every poll
  of earlier quanta ran before the AID existed); hi = q(the second write that reached the terminal after the AID) + 1
  (consumed at the latest by the post-write poll of that write); one more physical write only with protocol evidence
  that the round trip exceeded the presentation interval there; never further. First placement in [lo, hi] that
  matches through the next AID's lo (bounded first fit, as now). If several placements give identical frames up to
  the next AID, the earliest is taken and the case is reported as `equivalent placements` (diagnostic: the frames do
  not distinguish them, the logical result is the same). Diagnostic `post_write_consumption`: whether each placement
  is q(write) + 1 (the PR2I-C2 pattern).
- **Inputs**: planned == driver log == TN3270E AIDs == model-consumed events, exactly as now (PF7 F7 U, PF8 F8 D, PF9
  F9 P, PF10 7A L, PF11 7B R, PA2 6E, x / Q + ENTER 7D); per-directional-action report unchanged plus its logical
  quantum and the frame q(w) that first shows it.
- **Pause / resume**: PAUSED screen then zero game writes until the resume AID (unchanged); the resume quantum is a
  presented frame (base); the next frames follow the re-based grid. Post-pause burst proxy on the first five physical
  writes after resume with normalised gaps g / Δq: two consecutive < T / 2 = suspicious, protocol-proven = FAIL.
- **Death (R1)** (review item 3, resolved): logical semantics and wall / visible timing are checked separately.
  Logical (FUNCTIONAL): d = the step that loses the life, frozen quanta d + 1 .. d + RT-FRT (10 NORMAL, 12 FAST), the
  first possibly moving quantum d + RT-FRT + 1. Proof that the live game froze exactly RT-FRT logical quanta:
  (1) the freeze is PACRT code, unchanged and statically guarded (RT-FRZ = RT-FRT, one decrement per RQ, nothing moves
  while RT-FRZ > 0); (2) z/OS batch / TSD RTSTILL = the model (oracle 310) and the coalesced TSD RTSTILL = the filtered
  model; (3) live: every frame is the model's state at its q(w) (byte equality and the image invariant above); the
  frames with q(w) in d + 1 .. d + RT-FRT equal the frozen state, the first frame with q(w) > d + RT-FRT the model's
  post-freeze state; (4) discrimination: the checker re-runs the model on the same cards with the freeze mutated to
  RT-FRT - 1 and RT-FRT + 1 (placements searched again inside the same bounded windows) and requires both mutants to
  be rejected by the live frames. Superseded by the acceptance split (section 18, user 2026-10-19): if a mutant
  also matches, the checker reports `live freeze discrimination: NOT OBSERVABLE` (never a PASS of it, not BLOCKED);
  the exact 10 logical quanta rest on (1) + (2) and the live match against the canonical model (3). Exactly one
  death, exactly RT-FRT 'F' quanta in the model (unchanged rule).
  Wall timing (TIMING, gated, renamed): the old test (arrival of write d -> arrival of write d + 10) assumed a write on
  every quantum; that premise no longer holds and the old test is not reused as such. The grid guarantee: writes are
  every s quanta from the last base (s = 2 NORMAL, 3 FAST) and s divides RT-FRT (2 | 10, 3 | 12); so, when no base
  (pause / resume) falls between d and d + RT-FRT + s, exactly one write lies in d .. d + s - 1 and a write lies exactly
  RT-FRT quanta later. `freeze-span proxy` = arrival difference of that pair = RT-FRT logical quanta of host schedule
  plus the arrival jitter of two frames; band 1350..1650 ms (the D33 "one quantum of 1500 ms") applied to this proxy,
  labelled as such, with the pair's q values reported (it equals the old measurement only when the pair is (d, d +
  RT-FRT)). Missed band with exact logical behaviour = ENVIRONMENT / TIMING BLOCKED, never FAIL. No such pair (a base
  inside the window): proxy not measurable, reported, R1 not PASS on timing (R1's plan has no pause near the death).
  Visible duration (DIAGNOSTIC only, not gated): arrival of the first frame showing the death -> arrival of the first
  frame showing a post-freeze change; quantised by the presentation interval (nominally 1500 +/- Tp_eff ms) and
  content-dependent (after the respawn Pac-Man stands still; a change needs a ghost move), so not a timing criterion.
- **NORMAL / FAST timing**: principal segment = the longest run of presented quanta without consumed input, >= 200
  LOGICAL quanta (as now; >= 100 frames NORMAL, >= 67 FAST). Mean logical period = (a_last - a_first) / (q_last -
  q_first) in [0.99 T, 1.02 T] (unchanged bands, > 1.10 T STOP); median of the normalised gaps g / Δq within T +/- 10
  ms (the D33 tolerance per logical quantum, i.e. median physical gap within 2T +/- 20 NORMAL, 3T +/- 30 FAST); causal
  lower bound arrival(w) >= anchor + (q(w) - q0) T - 2 ms (unchanged formula on logical q); skipped periods: the
  lower envelope of the lateness a(w) - (a0 + (q(w) - q0) T) rising by >= T / 2.
- **Bounded output backlog**: lateness by thirds of the principal segment and its trend (section 11 B).
- **Physical cadence**: physical gap median / p95 / max against section 11 A.
- **Control-response latency**: per gameplay AID, wire send -> arrival of the first frame with q(w) >= its logical
  quantum (for PF9: -> the PAUSED screen; resume: -> the resume frame; Q: -> the first closure record); section 11 C.
- **Q / closure**: Q consumed in a running quantum, no game write after it, end lines (QUIT, TURNS, SCORE, LIVES,
  QUANTA = model logical quanta), `***`, closure ENTER, shell - unchanged. QUANTA is the end-to-end logical counter.
- **PF7 / PF8 / PF9 / PF10 / PF11 mappings**: unchanged, all four layers per directional AID.
- Unchanged: TN3270E parsing, SDI+KRI control validation, game-write boundary (C1), query / profile, driver-log
  integrity, transition, outside errors, zos5_live_check.py frozen.
- Not loosened: byte equality, AID order / count / mapping, death quanta, QUANTA, mean-period bands, median tolerance
  per logical quantum, death duration band, burst rules. New only: presentation, backlog and latency gates.

## 10. Revised R1 / R2 acceptance [P] (not authorised; plans of docs/zos6-design.md section 2 unchanged)
Both run with `PRESENT(COALESCED)` (PARM column 26 `C`) through the installed CLIST.
R1 NORMAL PASS = FUNCTIONAL PASS + TIMING PASS:
- functional: every physical frame == the coalesced model (q(w) on the 2-quantum grid from the start / resume
  quanta), no game write before the start AID or while PAUSED, PF8 / PF9 / PF9 / x+ENTER / PA2 / PF11 / Q + ENTER
  planned == sent == wire == consumed, exactly one death matching the canonical model with exactly 10 logical freeze
  quanta (live freeze discrimination reported, NOT OBSERVABLE for this plan; logical proof offline, section 18),
  respawn and continued quanta, end lines with QUANTA = model, closure to the shell;
- timing: principal >= 200 logical quanta, mean in [0.99 T, 1.02 T], normalised median T +/- 10 ms, death stop
  1350..1650 ms, no probable skipped period, no post-resume burst, section 11 A / B / C within bounds.
R2 FAST PASS: the same with T = 125, the 3-quantum grid (375 ms), PF11 start / PF8 / PF7 / PF10 / Q + ENTER, principal
segment = the run after PF10 (>= 200 logical quanta), FAST freeze / READY! values from RT-CONV inside the model, and
section 11 bounds for FAST. R2 is also the acceptance of the 375 ms FAST presentation interval.
Any presentation / backlog / latency bound missed with exact functional behaviour = ENVIRONMENT / TIMING BLOCKED (never
PASS); a protocol-proven host burst or replay = FUNCTIONAL FAIL. R1 -> R2 gate unchanged (section 6 of the design).

## 11. Proposed timing and input bounds (not adopted; for review) [P]
A. Physical presentation interval (Tp_eff = 300 ms NORMAL, 375 ms FAST):
- median within Tp_eff +/- (quanta per frame) x 10 ms (= T +/- 10 ms per logical quantum: 280-320 / 345-405 ms);
  rationale: the D33 tolerance, unchanged per logical quantum. PR2 median 300 **[O]**.
- p95 <= Tp_eff + 150 ms (450 / 525 ms); rationale: one extra host-to-terminal round trip plus a turn (about 2 x 112
  ms **[O]/[I]**) of jitter; PR2 410 **[O]** (PR2I 429, not used as a threshold).
- max <= 1000 ms outside pause, closure and the start screen; rationale: no visible freeze of the moving game over one
  second; PR2 502 **[O]**.
B. Output backlog / drift (lateness L(w) = a(w) - (a0 + (q(w) - q0) T) on the principal segment):
- mean L of the last third - mean L of the first third <= 100 ms, and the lower-envelope rule (rise < T / 2);
  rationale: an unbounded queue grows by about 34 ms per frame at 150 ms (P0 **[O]**: 4.8 s in 20 s), so 100 ms over
  >= 100 frames cannot hide growth; PR2 -300 / -333 / -329 ms (difference -29) **[O]**.
- linear trend of L <= +25 ms per 100 logical quanta (diagnostic proxy of the D33 drift criterion, labelled proxy).
C. Input-to-visible-reaction latency (wire AID -> arrival of the first frame presenting its logical quantum):
- every gameplay AID <= Tp_eff + 0.7 s (1.0 s NORMAL, 1.075 s FAST); median <= Tp_eff + 0.45 s (0.75 / 0.825 s).
  Rationale: PR2 aligned AID -> consuming TGET 0.21-0.45 s **[O]** + one presentation interval to the frame that shows
  it **[I]** + one-way transit <= 0.11 s **[O]/[I]** = about 0.51-0.86 s NORMAL; FAST adds up to 75 ms on both waits.
  The bound is a usability ceiling with about 15 % margin, not a target. P0-like behaviour (never delivered) and HOLD
  stalls fail it.
- Keyboard: the driver's Wait(5,Unlock) rule (no lock > 5 s) unchanged; locked-interval statistics diagnostic.
Open: these numbers rest on one PR2 run (3 AIDs); R1 / R2 will add 12 AIDs. Any bound may be revised by the user before
implementation, never after a run to make it pass.

## 12. Files that would change during implementation
Source (each a new z/OS Z-entry with guards; branch zos only; MVS / main / 2.0-mvs-max untouched):
- src/copy/PACREQ.cpy (append REQ-PMODE, REQ-PRES);
- src/cobol/PACMAIN.cob (PARM column 26, RT-PBASE, PSLT call, pending RT-FRAME, COALESCED-only post-write collect);
- src/cobol/PACPLAT.cob (op PSLT, PS-TP / PS-ACC);
- src/cobol/PACDISP.cob (RTQF on a skipped quantum: S2 pattern clock + PACSCR RTQS);
- src/cobol/PACSCR.cob (NEW in this revision: op RTQS = RP-STATE + SET-FACE only, section 16);
- src/zos/PACMAN.clist (PRESENT(EVERY|COALESCED), default EVERY; COALESCED -> column 26 `C`).
Tests / tools / docs:
- tests/ref_rt.py (presentation filter incl. the RTQS-equivalent state advance, default off; freeze-mutation hook for
  the discrimination check); tests/zos6_fixture.py (coalesced synthetic R1 / R2);
- tools/zowe/zos6_live_check.py (section 9); tools/zowe/zos6_drive.py (R1 / R2 command with PRESENT(COALESCED));
- tests/test_zos_tools.py section 20 (rewritten expectations), tests/zos_c2.py / zos_c2.json, tests/test_core_frozen.py,
  tests/test_g8.py (Z-entry allowances); the z/OS deck generator for the TSD dry runs;
- docs/ZOS-DIFFS.md (Z4 / Z5), docs/DECISIONS.md (ZV-D33 after approval), docs/zos6-design.md,
  docs/zos6-live-session.md.
Not changed: PACFSIO, PACTSO, PACRT, PACGAME, PACMAP, PACAI, PACINPT, zos5_live_check.py, oracle 310, the MVS CLIST,
the terminal profile.

## 13. Focused tests required
1. Regression: with REQ-PMODE blank (PRESENT(EVERY) / no column 26) every BAT / TSD REALTIME stream and TURN stream =
   oracle 310 / 2.0 byte for byte (test_rt, test_gx, test_core_frozen, the ZOS-2 comparison); the EVERY PARM identical
   to today's; static: with REQ-PMODE blank no PACSCR RTQS call, no post-write poll, RT-FRAME cleared every quantum.
2. PSLT unit (model and COBOL via TSD): NORMAL Y on start, then N Y N Y...; FAST start, then N N Y...; resume re-bases;
   no two Y on consecutive quanta except a base; accumulator reset, never a catch-up after a pause or a long run.
3. TSD coalesced dry runs (new, z/OS batch deck): RTLINE, RTCORNER, RTTTL, RTREV, RTMULTI, RTSTILL (death, 10 / 12
   freeze quanta), RTPAUSE (pause, invalid input, PA2, quit), RTLONG, RTWIN, RTEDGE at NORMAL and FAST; every stream ==
   ref_rt with the filter byte for byte; the image invariant on every frame; pending P / F frames shown at the next
   slot; VS-PREV diff correct across skipped quanta.
4. Display state on skipped quanta: a horizontal move followed by a vertical one inside one interval (facing); a ghost
   / fruit eaten on a skipped quantum (popup start quantum, position, expiry); two eats in one interval; S1 bell on the
   next frame; S2 pattern steps 2 / 3 quanta apart in logical time; READY! and death-frame visibility at the slots
   (ZOS-7 for the end death frames).
5. Input phases (model + checker): an AID read by B and one by A before the same step (order B then A, RTMULTI rules);
   Q and PF9 in B; ENTER / invalid / PA2 in B (pending prompt frame).
6. Checker (section 20 rewritten): positives R1 / R2 coalesced; negatives: a write on a non-slot quantum, a replayed
   skipped frame, a burst, a 9- or 11-quantum freeze (rejected by the mutants rule), a non-discriminating death
   (BLOCKED), a missing / duplicated / substituted AID, an AID beyond its window, QUANTA off by one, a write while
   PAUSED, unbounded lag (P0-like), p95 / max / latency over the bounds (BLOCKED), a broken image invariant.
7. Static: PACFSIO unchanged byte for byte; no HOLD / TPG; post-write collect TSC-only and only with REQ-PMODE C.

## 14. PRESENT(EVERY), development default, risks and rollback
PRESENT(EVERY) (review item 2, resolved) = the pre-change D33 REALTIME loop, as exactly as the source allows:
- the CLIST appends nothing for EVERY: the PARM string is byte-identical to today's (25 columns), so PACMAIN sees
  PARM-LEN 25 and REQ-PMODE blank;
- PSLT answers 'Y' on every quantum, RT-FRAME is cleared every quantum, PACDISP RTQF takes the unchanged 'Y' path,
  PACSCR RTQS is never called;
- the post-write poll B is COALESCED-only (condition `REQ-PMODE = 'C'`): EVERY keeps exactly one RT-COLLECT per
  quantum at the top, as today;
- hence the same terminal I/O sequence (TGET NOWAIT / TPUT / STIMER, in the same order and number), the same data
  streams, the same PACRT / PACGAME calls. The only differences: one extra CALL PACPLAT (PSLT, no I/O) per quantum and
  the appended PACREQ fields (no existing offset moves) - microseconds of CPU, no observable behaviour. Proven offline
  by test 13.1 (TSD / BAT byte identity) and the static checks; live it is, by design, the R1-T3 behaviour.
Default while ZOS-6 is under development: absent PRESENT -> EVERY (the CLIST PROC default `PRESENT(EVERY)`); the
inspection of src/zos/PACMAN.clist found nothing that requires another choice (keyword defaults in the PROC statement,
PARM built in `SET &P` at column <= 72 with room for one more variable; &E is free). R1 / R2 request
`PRESENT(COALESCED)` explicitly. The release default is NOT chosen here.
Risks:
- The coalesced loop is the first production use of the PR2 pattern. Production frames: see section 15 (R1-T3 frames
  are smaller than assumed; moving-game frames are larger, by model only). Mitigation: TSD dry runs first; R1 measures
  it; PS-TP is one constant.
- PR2I-C2 rests on three AIDs; the post-write poll covers a transient-visibility case without changing logic.
- FAST 375 ms is not validated live (R2 is its first evidence).
- Input-to-visible latency of about 0.5-0.9 s may feel slower than MVS RT3; the 3-step request TTL still applies in
  logical quanta (unchanged semantics) - a turn requested near a junction may expire before the frame shows it.
- Visual: 2-cell (NORMAL) / 3-cell (FAST) steps per frame; VIS aliasing (cosmetic). Coalesced diffs are larger than
  single-quantum diffs: the GS size guard (DS-LIMIT 2048, decoration drop / layout down) could trigger more often
  (section 16); covered by the TSD runs.
- New Z-entries widen the z/OS / MVS source difference (guards required).
Rollback:
- Operational: PRESENT(EVERY) (also the development default) restores the D33 loop without rebuilding - the R1-T3
  behaviour, known not to work on this link.
- Source: revert the Z-entries (PACREQ, PACMAIN, PACPLAT, PACDISP, PACSCR, z/OS CLIST) to zos-5; guards make the
  reversal exact (as Z1).
- Decision: if R1 coalesced is BLOCKED or FAILS, ZOS-6 stops for a design decision; no tolerance change, no CR change,
  no automatic retry.

## 15. Production frame-size check (review item 4; READ ONLY, frozen R1-T3 trace)
Source: R1-T3 trace (SHA-256 `11408477...cc1a64`, re-verified, unchanged), parsed with the checker's own TN3270E
helpers (parse6 / bid_times); game writes = host 3270-DATA records from the first game screen to the first line-mode
record; payload = the 3270 data (command + WCC + orders), TN3270E header and telnet escaping excluded. **[O]**:
| | count | median | mean | p95 | max |
|---|---|---|---|---|---|
| all game writes | 2138 | 5 | 22.0 | 53 | 1737 (the first full screen) |
| quantum writes (first screen excluded) | 2137 | 5 | 21.2 | 53 | 104 |
Composition: 1419 x 5 bytes (restore-only `F1 C2 28 00 00`: nothing changed), 710 x 53 bytes (the animation flip every
3 quanta), 7 others 70-104 bytes (Pac-Man moving after PF8 until blocked), WCC C2 on 2136 writes. R1-T3 ran AI(0)
GHOSTS(1): still ghost, and Pac-Man stopped at a wall a few quanta after PF8. It is therefore a near-idle workload; it
says nothing direct about a moving game.
PR2 / PR2I probe quantum frames (same method, `F1 C2 ...` records): median 35 bytes (min 18; `QUANTUM nnnn  AIDS
RECEIVED nn`), not about 100 bytes. Production R1-T3 frames are SMALLER than the probe's in the median (5 vs 35) and of
the same order at p95 / max (53 / 104 vs 35 / 103).
Size vs latency **[O]** (2137 quantum writes): BID response -> data latency (92 BIDs) median 115 / p95 171 / max 442 ms,
Pearson -0.12 / Spearman 0.08 against the payload; the interval to the next record vs the record's size: Pearson
-0.02 (all, first screen excluded), 0.04 inside bursts (gaps < 300 ms); median next-record interval 116 ms (5-byte
writes), 118 ms (6-59), 120 ms (60-104, n = 7). (A raw Pearson 0.66 including the 1737-byte first screen is an artefact:
the gap after it is the 5.2 s blocking wait for the press-to-start key.) Within 2-104 bytes the delivery interval is
set by the per-record round trip (~115 ms), not by size; payloads above 104 bytes are not covered by the trace.
Byte rates: R1-T3 as recorded 47,027 bytes in 325.9 s = 144 B/s (mean 22 B per write, 150 ms); the same frames at
300 ms about 73 B/s. Model-only estimate (tests/ref_rt.py TSD 120 x 27, a 188-quantum moving game, **not evidence**):
AI0 1 ghost: median 52 / p95 86 B per quantum frame; AI1 3 ghosts: median 215 / p95 285 B; a 2-quantum coalesced frame
is at most about the sum of two (AI1 3: median <= 417, p95 <= 564 B) -> about 1.4 KB/s at both 150 ms and 300 ms.
What the trace supports: (a) the binding constraint on this path is the record count (one record per ~115 ms round
trip, P0 / R1-T3), which coalescing halves; (b) in the measured size range (<= 104 B) size does not change delivery
latency. What it does not support: that 300 ms is safe for frames of several hundred bytes (no such frames on the
wire yet), and byte rate alone proves nothing about the TSO queue. R1 / R2 (AI(0) GHOSTS(1), model frames <= ~160 B
coalesced) stay close to the measured range; busier games (more ghosts, ARCADE) are a ZOS-7 / later acceptance
question.

## 16. Display-state audit (review item 5; READ ONLY: PACDISP, PACSCR)
Question: which mutable state advances as a side effect of a display call, so that skipping the call on coalesced
quanta would change what is shown. Classes: L = logical-time state (must advance every logical quantum), P =
physical-presentation state (must advance only on what is sent), N = no issue (recomputed from the game / PACRT state
on every compose, scratch, one-time initialisation, or TURN / end-only).
PACDISP:
| State | Class | Finding |
|---|---|---|
| PT-ON / PT-PRI / PT-LEFT / PT-NEXT / PT-G / PT-QW (S2 pattern) | **L** | counts quantum writes; must count logical quanta (already in the proposal) |
| PT-EV / PT-D | N | per-screen scratch (event class of this screen) |
| SB-SENT / SB-LIVES / SB-WON / SB-NDIE / SB-XL / SB-LVL (bell snapshot) | P | "since the last screen": an event on a skipped quantum rings on the next frame; several events in one interval -> one bell / the highest pattern, which gives the same pattern as D33's "higher or equal replaces" sequence, at most s - 1 quanta later. Accepted, documented |
| M-FRAMES / M-LINES / M-CHARS / M-CLEARS | P | METRICS(YES) counts of what is sent; the coalesced model must count the same; R1 / R2 use METRICS(NO) |
| PT-T0, FD-K, FD-SAVE | N | end pause / end death frames (end-only; ZOS-7 item already recorded) |
| WS-*, HEXW, line records | N | scratch |
PACSCR:
| State | Class | Finding |
|---|---|---|
| VS-CUR / VS-PREV / PREV-OK | P | the image on the terminal; correct only because a skipped quantum is never composed (by design) |
| WS-FACE (Pac-Man facing) | **L** | SET-FACE latches L / R from LAST-CMD / LAST-RESULT at compose time; a horizontal move followed by a vertical one inside one interval would be missed (facing differs from D33) -> must run every quantum |
| PU-ON / PU-T0 / PU-X / PU-Y / PU-EAT / PU-FRT / PU-PTS / PU-COL / PM-* (score popup, ARCADE) | **L** | RP-STATE starts a popup when ARC-EATN4 / ARC-FRUITS moved "since the last screen": PU-T0 = the compose quantum and PU-X / PU-Y = PLAYER-X / Y at compose time; skipped, the popup would start up to s - 1 quanta late and at Pac-Man's later cell -> must run every quantum |
| RP-READY / RP-DTH / RP-DTE / RP-PU / RP-HI / RP-HIV / RP-END / RP-SUPP / RP-DECO / RP-NOW / RP-LIM | N | recomputed by RP-STATE per screen from REQ-RTSTAT / REQ-RTFRZ / REQ-RTQ / scores (RP-HIV = max(high score, score), monotone); RP-STATE is documented safe to repeat |
| MSG-ON / MSG-LAST (invalid-input message) | P | set by the INVL event, carried into the next compose; with RT-FRAME kept pending it reaches the next presented frame. No issue |
| VIS | **L** | set from REQ-VIS by DO-RTQF / DO-PRMT, but DO-ENDS draws the SAVED VIS (found by PACZ6DR1 JOB09418: the end screen after skipped quanta showed the last presented animation frame) -> RTQS also sets VIS = REQ-VIS when ANIM Y (fixed 2026-10-19). Aliasing of presented frames cosmetic only |
| DS-OVF / DS-LIMIT / SV-LAY / SC-* / GW / GH / ORG-* / layout (GS size guard) | P | a stream over DS-LIMIT drops decorations or moves the layout down for the rest of the game; coalesced diffs are larger, so the guard may trigger where D33 would not; the filtered model must apply the same rule; covered by TSD runs |
| BAN-ON, END-SC | N | end screen only |
| TAB-OK / CT-OK / RP-TAB-OK, code tables, sprite / glyph selections | N | one-time initialisation or recomputed per compose |
| HUD-LAST / HL-* / HUD-* | N | rebuilt per compose from LAST-CMD / LAST-RESULT / TICK-COUNT / scores |
Result: ALARM(PATTERN) is NOT the only display-owned logical-time state. Also WS-FACE, the popup latch (PU-*) and
(found on z/OS, PACZ6DR1 JOB09418) VIS when ANIM Y. The
proposal is amended (section 7): on a skipped quantum PACDISP advances the pattern clock and calls the new PACSCR op
RTQS (RP-STATE + SET-FACE, no compose); the filtered model does the same; the image invariant (section 9) checks the
result against the unfiltered D33 model. The bell snapshot, metrics, message, size guard and VS-PREV stay physical by
design.

## 17. Git status (at the end of this design step)
See the report. Docs only: docs/zos6-production-design.md (new, revised for the five review items), plus the earlier
closure notes in docs/zos6-io-architecture-memo.md, docs/zos6-protocol-probe.md and docs/zos6-design.md. Nothing
committed.

## 18. Implementation status (2026-10-19; local only - no build, no z/OS, no live run, nothing committed)
Implemented as approved: Z4 (PACREQ, PACMAIN, PACPLAT, PACDISP, PACSCR) and Z5 (z/OS CLIST), docs/ZOS-DIFFS.md; the
model, checker, fixture and tests (tests/test_zos_tools.py sections 20 = the EVERY rules, 22 = this design). Findings:
1. **R1 freeze discrimination - resolved by decision (user, 2026-10-19): the approved R1 plan is kept unchanged.**
   With AI(0) (the ghost never moves; after the respawn Pac-Man stands still until Q) the freeze length leaves no trace
   in any frame: the 9- and 11-quantum mutants match the live frames as the 10-quantum model does. This is an
   observational limit of the scenario, not a checker defect. Acceptance split:
   - logical freeze proof (mandatory, exactly 10 logical quanta): PACRT unchanged and guarded (Z1 text, FRZ-INIT 10)
     plus the RTSTILL batch / TSD / model evidence (oracle 310; tests section 22 runs RTSTILL at both speeds); the
     test-only moving-ghost fixture (AI(1)) must keep proving freeze 10 PASS, 9 FAIL, 11 FAIL;
   - live R1: must match the canonical 10-quantum model, pass the freeze-span proxy (1350..1650 ms) and every other
     functional / timing / input / presentation gate; it does NOT fail or become BLOCKED because 9 / 10 / 11 are
     observationally identical. The checker reports `live freeze discrimination: NOT OBSERVABLE` (never as a PASS of
     the discrimination) or `DISCRIMINATED` when both mutants are rejected. R1 is not changed to AI(1).
2. **Placement search.** First fit fails under coalescing: two placements can give identical frames for a while (PF9
   one card earlier: the same PAUSED screen) and diverge later. The checker now backtracks depth first inside the same
   bounded windows (never outside), accepting only a placement set that matches every write and the closure end lines.
   An AID sent during a blocking read (pre-start / PAUSED screen) gets the window lo..lo + 1, as under EVERY.
3. **Invalid-input message** (section 9 exemption above): MSG-ON is physical presentation state; the image invariant
   accepts a message-row-only difference with INVALID on one side (1 case in the RT set: RTPRE).
4. A game that ends (LOST) on a coalesced quantum: the fixture now ends a plan without Q where the model's game ends;
   tests section 22 (AI(2) GHOSTS(3), NORMAL and FAST): the deciding quantum is not written, the end screen follows,
   PASS; a host that writes it anyway FAILS.
5. CLIST: no null assignment exists in the repository (the only `&STR()` is a comparison, src/probe/RTPROBE.clist), so
   Z5 uses only statement forms the 2.0 CLIST already runs: the 2.0 PARM line stays as is, then
   `SET &E = &SUBSTR(1:1,&PRESENT)` and `IF &E = C THEN SET &P = &STR(&P&E)`.
6. The NORMAL / FAST candidate gates (section 11 / checker GATES), STRIDE and PS-TP are FROZEN as approved
   (2026-10-19; pinned by tests section 22): they are not tuned from live results.
7. Still unproven: compile / bind on z/OS, the TSD coalesced dry runs on z/OS, these CLIST statements on this system,
   live R1 / R2.

## 19. R1-T4 live run and the two checker decisions (2026-10-19)
Promotion PACZ6INS JOB09499 (LOAD(PACZ6D) -> LOAD(PACMAIN), replace; PACZ2D = rollback source), CLIST(PACMAN) = the
ZOS-6 CLIST (byte for byte). R1-T4 (fresh session, R1 plan unchanged, trace SHA-256 e358d933...761593): the checker as
then written reported FUNCTIONAL FAIL because the host sent a bare `F1 C3` Write right after each AID read by a blocking
TGET (the start PF8, the resume PF9); the same record is in R1-T3 (pre-ZOS-6 binary), never in PACMAN's own TSD
streams, and PACFSIO's blocking RECV issues no TPUT - so it is a TSO / VTAM record (mechanism: inference). Decisions
(user): (1) that exact record in that exact context is a CONTROL record (checker: tso_controls; fixtures: blocking PASS,
unrelated / duplicated / different / substituted FAIL); (2) under COALESCED the historical lateness-envelope rule is
diagnostic only, under EVERY it still blocks. R1-T4 is rechecked once with the corrected checker (no rerun).

## 20. Closure (2026-10-19): ZOS-6 COMPLETE
R1-T4 PASS (recheck on the frozen trace) and R2 FAST PASS (one run), both with the frozen gates of section 11 /
checker GATES; no gate, threshold, model or source changed after a live result. Production state: PACMAIN = the
ZOS-6 program (JOB09460 build, JOB09499 promotion), CLIST(PACMAN) = the ZOS-6 CLIST (default PRESENT(EVERY)),
PACZ2D = rollback source, PACZ6D = test / build member. Evidence: docs/evidence/zos6-realtime.md.
