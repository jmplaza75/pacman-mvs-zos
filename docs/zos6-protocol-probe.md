# ZOS-6 protocol probe PACZ6P - design and procedure (design approved; build attempts below; not run)

Why: R1-T3 (docs/zos6-r1-t3-analysis.md) showed that with TPUT NOEDIT + TGET ASIS,NOWAIT the z/OS TN3270E session gives
the terminal the send state only at sporadic host End Brackets (empty SDI + KRI records, gaps up to 46.8 s), so a
mid-run PF AID cannot be delivered reliably under CONTENTION-RESOLUTION. Candidate A0 (user, 2026-10-16): TPG NOEDIT.
This probe tests it in isolation (no PACMAN, no PACFSIO change), against the current behaviour as a baseline.

## 1. TPG (primary source: MVS/XA TSO Guide to Writing a TMP or a CP, GC28-1295-0, "The TPG Macro Instruction")
- "Use the TPG macro instruction (SVC 93) to transmit a line of output to the terminal if that line of output will
  cause the device to respond immediately with input ... TPG NOEDIT creates an outbound request unit with an
  associated change direction indicator to allow the device to go into send state. This data is not inspected. A TGET
  macro must be issued to retrieve the ... response."
- Standard, list and execute forms; NOT the R (register) form; the standard form takes the buffer address and size in
  registers, but z/OS HLASM rejects R0 / R1 for them (MNOTE 12 `IHB300 BUFADDR AND BUFSIZE REGS CANNOT BE 0 OR 1`,
  JOB04217; the macro uses R1 for its parameter list), unlike TPUT `(1),(0)`. Size 0..32767.
  24-bit addressing mode; everything below 16 MB.
- NOEDIT: the program supplies the whole data stream (3270 command, WCC, orders); "Users of TPUT NOEDIT and TPG are
  responsible for all device command and write-control-character bit settings"; a TGET after TPUT NOEDIT or TPG does
  NOT make VTAM unlock the keyboard (the WCC keyboard-restore bit stays the program's job: keep WCC X'C2').
- WAIT / NOWAIT: whether to wait for a terminal output buffer (NOWAIT: RC 4 when none). HOLD / NOHOLD: wait until the
  output is written to the terminal, or return once it is queued (NOHOLD default).
- Return codes: 00 completed, 04 NOWAIT and no buffer, 08 attention interruption during TPG (not sent), 10 invalid
  parameters, 14 terminal disconnected.
- STFSMODE NOEDIT (input side) has no effect on TPUT / TPG.
- TN3270E side (z/OS Communications Server): SDI when the host VTAM application sends change direction or End Bracket;
  KRI on End Bracket; a host BID is forwarded; after a positive BID response the client may not send until SDI. So a
  change direction should reach the terminal as SDI (not necessarily KRI), and the next host output should regain
  direction - how (BID, SIGNAL, or held output) is exactly what the probe must show.

## 2. Reuse of the PACMAN frame bytes and the proposed cycle
- PACFSIO SENP builds `X'F1'` + the caller's stream (WCC first) in SENDBUF (RMODE 24, below the line) and issues
  `TPUT (1),(0),NOEDIT`: the same buffer (command and WCC included, 24-bit) is reusable unchanged for TPG, but the
  call must pass its address and length in registers other than R0 / R1 (e.g. `TPG (2),(3),NOEDIT,WAIT,NOHOLD`).
  The WCC X'C2' (keyboard restore) stays unchanged.
- Proposed cycle: absolute deadline -> TPG NOEDIT,WAIT,NOHOLD screen update -> TGET ASIS,NOWAIT -> process an AID if
  RC 0 -> wait until the next absolute deadline. It keeps the PACPLAT / PACFSIO POLL interface and every COBOL
  behaviour unchanged (only the SVC behind the partial write differs); open questions for after the probe: whether the
  PA2 / end full screens (SENX, Erase/Write Alternate) and the first screen also need TPG, and the effect on TURN.
- Not assumed: TPG is documented for output that makes the device respond at once; whether TSO accepts the next
  output before any input (instead of holding it, or reacquiring direction with a SIGNAL) is unknown until measured.

## 3. The probe (src/probe/zos/PACZ6P.asm; one module, MODE parameter; independent runs)
Pure HLASM main program, AMODE 24 / RMODE 24, non-reentrant (static save area), no LE, no COBOL, no PACFSIO, no ESTAE,
no ATTACH, no STAX. `CALL '<hlq>.PACMAN.Z6PRB.LOAD(PACZ6P)' 'P0'`,
`'PT'` or `'PN'` (section 8) from the ISPF Command Shell.
- Not a TSO user: nothing issued, RC 4. Bad PARM: RC 16.
- Start: TCLEARQ OUTPUT / INPUT, STFSMODE ON,INITIAL=YES, STTMPMD ON; TPUT NOEDIT of an Erase/Write title screen
  (`PACZ6P ZOS-6 PROTOCOL PROBE  MODE xx  20 S AT 150 MS. DO NOT TYPE.`); T0 = STCK.
- 133 quanta on absolute deadlines (q - 1) x 150 ms (20 s). Each quantum: issue time (STCK); one write
  `F1 C2 SBA(3,2) 'QUANTUM nnnn  AIDS RECEIVED nn'` - P0 by `TPUT (1),(0),NOEDIT`, PT by
  `LA 2,FRAME`, `LA 3,FRAMEL`, `TPG (2),(3),NOEDIT,WAIT,NOHOLD` (R2 / R3 scratch there); the output
  call duration; `TGET (1),(0),ASIS,NOWAIT` (RC 0 with data: the AID,
  quantum and host ms recorded, first 8); STIMER WAIT,MICVL for the remainder to the next deadline (as PACTSO DLWT).
- End: after 133 quanta, or at once on a TPUT / TPG RC not 0 (e.g. 8 = attention), a TGET RC not 0 / 4, or 60 s:
  STTMPMD OFF, STFSMODE OFF, STLINENO LINE=1, then line-mode summary lines (TPUT):
  `PACZ6P MODE xx QUANTA n ELAPSED-MS n`, `PACZ6P LATE>75MS n MAXLATE-MS n MAXPUT-MS n`,
  `PACZ6P RCOUT n RCIN n AIDS n`, `PACZ6P AID xx QUANTUM n MS n` (one per received AID, up to 8); RC 0.
Build: jcl/zos/PACZ6PRB.jcl, generated by tools/zowe/zos6_probe_deck.py from the source (in-stream: nothing uploaded):
ASM (ASMA90, HLA.SASMMOD1, SYS1.MACLIB / MODGEN), LKED (IEWBLINK `LIST,AMODE=24,RMODE=24`, only after ASM RC 0, into
the existing probe-only PDSE `<hlq>.PACMAN.Z6PRB.LOAD(PACZ6P)`, DISP=SHR). No DELETE, no allocation, no PACMAIN,
CLIST, CEEOPTS, DATA or PACMAN source touched.
- Attempt 1, JOB04217 (deck then with an ALLOC step): ALLOC CC 0 (Z6PRB.LOAD created empty, SMS, catalogued); ASM
  RC 12, the only diagnostic the TPG MNOTE IHB300 (BUFADDR / BUFSIZE in R0 / R1); LKED not run (COND). Output kept
  read-only under build/zos/PACZ6PRB-JOB04217/.
- Attempt 2, JOB04240: TPG on R2 / R3; the ALLOC step removed, the existing empty PDSE (0 members, checked read-only
  before submission) reused DISP=SHR. ASM RC 0 (no statements flagged; the TPG expansion stores R3 as the size and
  R2 as the buffer address, SVC 93); LKED RC 0 (only IEW2650I, entry defaults to PACZ6P), AMODE 24 / RMODE 24;
  member PACZ6P present. Output kept read-only under build/zos/PACZ6PRB-JOB04240/. Not executed.

## 4. Runs (after approval; one c3270 session, ISPF option 6, two separate traces, each frozen before the next)
P0 first, then PT; each: `Trace(On,<raw-trace-dir>/zos6-probe-<mode>.trace)` with the shell visible; then
`python3 tools/zowe/zos6_probe_drive.py --port <script-port> --mode <mode> --log <raw-trace-dir>/zos6-probe-<mode>-drive.jsonl`;
after the driver's done message `Trace(Off)`, shasum, chmod a-w; then
`python3 tools/zowe/zos6_probe_check.py --mode <mode> --trace ... --drive-log ...` (read-only).
The controller (tools/zowe/zos6_probe_drive.py, the real x3270if adapter of zos6_drive): CALL (transition), ENTER at
ISPF's `***` if it appears (transition), from the moment the probe screen is seen PF4 at +5 s, PF5 at +10 s, PF6 at
+15 s, each after Wait(5,Unlock); a 5 s keyboard-locked wait is logged `not sent: keyboard locked 5 s` and NOT
retried (an expected observation for P0); then the closure (`***` after the summary, ENTER, the shell). No other key.

## 5. Expected PT sequence to confirm or refute (trace)
output (3270-DATA with SDI, i.e. change direction) -> terminal in send state (c3270 unlock) -> the next host output
regains direction (a BID, or a SIGNAL BID, or held output) -> next output; an AID sent inside the window is consumed by
the next TGET NOWAIT (host summary) and appears on the wire. The analyzer reports for each run: frames, quantum order,
SDI / KRI per frame, empty controls by flag, BIDs and SIGNAL BIDs, the record after each SDI, RESPONSEs, unlock windows
and locked intervals, arrival gaps and mean period, lag behind first + (q - 1) x 150 ms, AIDs on the wire vs driver vs
host summary. Host timing (summary): quanta issued, elapsed, issue lateness count / maximum, longest TPUT / TPG call.
Terminal arrival timing is reported separately; no PACMAN timing gate applies (protocol probe, not ZOS-6 acceptance).

## 6. Failure and cleanup
- Attention (PA1) during the loop: TPUT / TPG RC 8 -> the loop ends, line mode restored, summary written.
- TPG WAIT blocking (no output buffer): the program waits inside TPG; the operator's PA1 ends it (RC 8). TGET NOWAIT
  never blocks; the 60 s cap ends a slow loop. No ESTAE: an abend (not expected: no storage or program checks beyond
  the loop) would leave the terminal in full-screen mode; TSO restores it at the next line-mode output (READY / ISPF);
  the operator then presses ENTER / PA2. STOP after any abnormal end: no retry, evidence frozen.
- Driver STOP (shell missing, x3270if error other than the 5 s wait, no probe screen / `***` / shell in time): trace
  off, freeze, STOP.

## 7. Decision gates after the runs (user)
PT good (SDI per frame, AIDs delivered and received, loop on schedule) -> TPG becomes the preferred PACFSIO candidate.
PT protocol good / timing bad -> keep the evidence; investigate A1 (pending TGET in a subtask). PT no better -> do not
force it; A1 next. PT hang / error -> evidence frozen, no retry.

## 8. After P0 / PT: P2 deferred, PN (poll before output)
- P0 and PT ran live (user-accepted results): P0 completed 133 quanta on a near-exact host schedule, terminal arrival
  lagged (up to about 4.4 s at the end), PF4 / PF5 / PF6 on the wire, 0 AIDs received by the host. PT completed only 4
  frames (SDI on each, no BID / KRI after them, each frame advanced only after a terminal AID), 0 AIDs received, no
  normal completion: TPG per quantum is rejected.
- P2 (a pending TGET ASIS,WAIT in an ATTACHed input subtask) is DEFERRED, not implemented: IBM documents no
  deterministic way for another task to end a TGET WAIT (it completes only on input, attention RC 8, or disconnect
  RC 14; TCLEARQ INPUT and STATTN do not), and DETACH of an incomplete subtask is an abnormal termination whose effect
  on the pending TSO TGET is undocumented.
- PN isolates one question: AID retrieval ORDER. Per quantum: TGET ASIS,NOWAIT first (RC 0 with data: recorded with
  the quantum that consumed it; RC 4 or length 0: nothing; any other RC ends the loop as before), then the same
  TPUT NOEDIT frame, then the same absolute wait. Everything else as P0 (133 quanta, 150 ms, lifecycle, frame, WCC
  X'C2', summary, 60 s cap, driver PF4 / PF5 / PF6). No TPG, no TGET WAIT, no subtask, no STAX; CR unchanged.
  `CALL '<hlq>.PACMAN.Z6PRB.LOAD(PACZ6P)' 'PN'`. Source: the one TGET is in subroutine POLL (link R11); PN calls it
  before the output, P0 / PT after it (their order unchanged).
- PN does NOT attempt to fix the KRI / send-window problem, and it is not a PACFSIO solution. Its two questions are
  reported separately: (A) delivery - driver == wire == host AIDs; (B) send opportunity - SDI / KRI / BID counts,
  unlock windows, the longest locked interval, compared with P0.
- P0 ordering (read-only, frozen P0 trace): each AID left the terminal 16-24 ms after a frame carrying SDI + KRI
  (REQUEST-FLAG 03: Q0027 / Q0051 / Q0077), with the keyboard unlocked; the next host record was a BID, then the next
  frames; no negative response. Proven by the trace: the AID followed a direction-giving frame. Not observable: host
  TGET times. Source-derived: in P0 the next TGET after an AID always follows a TPUT. But the host ran ahead of the
  wire (queued output: lag about 1.2 s at Q0026 growing to 4.4 s), so after each AID dozens of further TGET NOWAITs
  ran (all without data: AIDS 0, RCIN 0). So the input was not merely missed by one poll; PN can only help if issuing
  output discards input that has already arrived and is not yet read.

## 9. PN-T2 result and PH (TPUT HOLD baseline)
- PN-T2 (user-accepted interpretation): the probe ran 133 quanta in order, host ELAPSED 19950 ms, MAXLATE 1, MAXPUT 1;
  but frames with SDI 0, KRI 0, BIDs 0, SIGNAL 0, no unlock window. The driver's transition ENTER reached the host
  (the probe started) but `Enter()` never returned (no unlock within 10 s): driver STOP, NO PF4 / PF5 / PF6 attempt.
  PN did NOT test AID retrieval; its `*_match_*` equalities compared empty lists. Poll-before-output is rejected as a
  practical input architecture (no send-state opportunity at all under CR); it is not retried.
- PN-T1 (`zos6-PN.trace`, empty driver log): INVALID PREPARATION CAPTURE - the driver stopped before the CALL
  because the ISPF Command Shell was not on the screen; not protocol evidence; kept, never reused.
- Checker: `aid_test_exercised` (true only if the driver actually sent at least one planned probe AID) with
  `aids_planned` / `aids_attempted` / `aids_sent`; with false, the equalities say nothing about delivery (PN-T2: false).
- PH isolates the output backlog: the P0 loop with `TPUT (1),(0),NOEDIT,WAIT,HOLD` (IBM: with HOLD the program
  cannot continue until the output line is written to the terminal or discarded). Order kept: deadline, frame, TPUT
  HOLD, its duration (MAXPUT), TGET ASIS,NOWAIT, then the absolute wait (no sleep if HOLD already passed the
  deadline; lateness recorded as before). `CALL '<hlq>.PACMAN.Z6PRB.LOAD(PACZ6P)' 'PH'`. No TPG, no TGET WAIT, no
  subtask, no STAX, CR unchanged. The 150 ms schedule may be lost: diagnostic, not a timing test.
- PH questions, reported separately: (A) output queue - ELAPSED, MAXPUT, LATE>75MS, MAXLATE, arrival gaps, lag;
  (B) send state vs P0 (SDI 49, KRI 49, BID 49, unlock median about 116 ms, locked max about 511 ms); (C) delivery -
  per PF: attempt, Wait result, send, wire AID, host AID, quantum, ms, and `aid_test_exercised`.
- PH failure path: a HOLD TPUT is one SVC call; the 60 s cap is checked only between quanta and cannot interrupt it.
  Documented exits from a blocked TPUT: completion (written), RC 8 (attention during processing, message not sent),
  RC X'14' (terminal logged off / unreachable); each returns to the probe, whose RC-not-0 path ends the loop through
  ENDLOOP (STTMPMD / STFSMODE OFF, STLINENO, summary). PA1 under ISPF without STAX remains untested here (as for
  P0 / PT). Expected: no block, because HOLD needs only output delivery, which P0 / PN-T2 delivered for every frame
  without any terminal input (unlike TPG, which needed an inbound).

## 10. PH result (PH-3) and PB4 (periodic HOLD barrier)
- PH (user-accepted, PH-3): 133 frames in order; host ELAPSED 20155 ms, LATE>75MS 96, MAXLATE 359 ms, MAXPUT 509 ms,
  AIDS 3; terminal gaps mean 149.2 / median 116 / p95 406 / max 525 ms, lag at most about 44 ms; 7 empty KRI
  controls, 7 BIDs, unlock median about 113 ms, longest lock about 3108 ms; F4 / F5 / F6 driver == wire == host
  (host quanta 70 / 91 / 125). TGET ASIS,NOWAIT does retrieve AIDs; the P0 failure is tied to the NOHOLD output
  backlog / direction state; HOLD on every quantum costs up to about 0.5 s per call: unsuitable for REALTIME.
- PB4 (`CALL '<hlq>.PACMAN.Z6PRB.LOAD(PACZ6P)' 'PB4'`): the P0 loop, but quantum q with q mod 4 = 0 (4, 8, ..., 132:
  33 of 133) writes its frame with the PH call `TPUT (1),(0),NOEDIT,WAIT,HOLD`; the others with the P0 NOHOLD TPUT.
  Poll order as P0 / PH (output, TGET ASIS,NOWAIT, absolute wait). Diagnostic only; 600 ms is not proposed as an
  input latency, and no ZOS-6 threshold changes.
- Added host metrics (all modes; summary line `PACZ6P HOLDS n MAXHOLD-MS n MAXNOHOLD-MS n`): HOLD calls, the
  longest HOLD call, the longest other output call. The mode fields are now 3 characters (`PB4`; a blank after the
  two-character modes). Checker: lag by thirds of the run (bounded or growing; frozen P0: about 1.1 / 3.4 / 4.8 s
  mean, PH about -0.2 / -0.2 / -0.1 s) and, for PB4, lag by phase q mod 4 (phase 0 = barrier frames).
- Failure path as PH (section 9): a HOLD call cannot be interrupted by the 60 s cap; PA1 once, then closing the c3270
  connection as the last resort. PB4 issues 33 HOLD calls instead of 133.

## 11. PB4 result (PB4-B) and the end of the probe series
- PB4 (user-accepted, PB4-B; trace SHA-256 dd2c354e3438f04b2d46f0184bc15b3794071d4297a1efa4d19117ecb2be2b68): 133
  frames in order; ELAPSED 20192 ms, LATE>75MS 100, MAXLATE 588, MAXPUT = MAXHOLD 737, MAXNOHOLD 0, HOLDS 33; terminal
  gaps mean 149.6 / median 113 / p95 292 / max 420 ms; lag by thirds about -49 / -32 / -64 ms (bounded, unlike P0);
  15 SDI+KRI frames, 15 BID, no SIGNAL, unlock median 110 ms, longest lock 1845 ms; F4 / F5 / F6 driver == wire ==
  host, consumed at quanta 44 / 72 / 108 (all barrier quanta), wire to host about 1.28-1.30 s.
- Decision of record: no PB2 / PB3 / PB8 sweep. Conclusions and the architecture options:
  docs/zos6-io-architecture-memo.md.

## 12. PR2 - render every 2nd logical quantum (experimental presentation decoupling; prepared, not built or run)
- `CALL '<hlq>.PACMAN.Z6PRB.LOAD(PACZ6P)' 'PR2'`. 133 logical quanta on the unchanged absolute 150 ms scheduler
  (NQUANTA, PERIOD, lateness and deadline code run for every quantum). Even quanta (2, 4, ..., 132: 66) build the frame
  from the CURRENT quantum and write it with the P0 call `TPUT (1),(0),NOEDIT` (NOHOLD), then TGET ASIS,NOWAIT, then
  the deadline; odd quanta (67) write nothing, count a skip, and do the same TGET ASIS,NOWAIT and deadline. A skipped
  state is never written later (no burst, no catch-up): the next write shows the then-current quantum.
- No HOLD, no TPG, no TGET WAIT, no subtask, no STAX, no STBREAK or CR change. Not PN: the poll stays after the write,
  and every second quantum leaves a whole 150 ms with no new output queued.
- New summary line (all modes) `PACZ6P WRITES n SKIPPED n`; checker: `logical_quanta`, `physical_writes`,
  `skipped_writes`, `frames_on_wire`, `frame_step` 2 with `quanta_in_order` (even quanta in order: a replayed or
  burst frame fails it), lag against the LOGICAL schedule, arrival gaps of the physical writes (about 300 ms expected).
- Questions: bounded `lag_by_third` (vs P0 1.1 / 3.4 / 4.8 s); SDI / KRI / BID and send-state intervals; PF4 / PF5 /
  PF6 driver == wire == host without HOLD; wire-to-host latency. Outcomes PR2-A..E as decided by the user; no other
  render divisor is tried automatically. Failure path: no blocking call is added (as P0).

## 13. PR2I - PR2 with a host-side delivery table (instrumentation only; prepared, not built or run)
- `CALL '<hlq>.PACMAN.Z6PRB.LOAD(PACZ6P)' 'PR2I'`: MODE R exactly as PR2 (same title `MODE PR2`, frames, WCC, writes
  on q = 2, 4, ..., 132 by `TPUT (1),(0),NOEDIT`, `TGET (1),(0),ASIS,NOWAIT` every quantum, 150 ms scheduler,
  lifecycle, driver plan) plus INSTR = 1. Every added loop step sits in a `CLI INSTR,1` / `BNE NOINSn` block that all
  other modes skip, and does only clock reads (NOWMS, the summary's own millisecond clock since T0) and stores.
- Record (32 bytes per quantum, ITAB after LTORG, (q - 1) x 32, initialised from IINIT at the top of the quantum):
  +0 H quantum; +2 X write flag; +3 X TGET RC (low byte of R15); +4 H TGET length = R1 on RC 0 (X'FFFF' otherwise:
  IBM documents R1 = bytes moved for RC 0, nothing for RC 4); +6 X AID byte (first input byte, RC 0 with data); +8 /
  +10 H AIDCNT before / after the TGET; +12 / +16 F ms before / after the TPUT (-1: no write); +20 / +24 F ms before /
  after the TGET; +28 F 0.
- Printed only at SUMEND (after STTMPMD / STFSMODE OFF, STLINENO, the normal summary and AID lines): `PACZ6P S1` /
  `S2` (one status character per executed quantum: `.` RC 4, `a` RC 0 with data, `z` RC 0 length 0, `e` other RC;
  upper case or `:` on a write quantum) and `PACZ6P I` detail lines for the first 3 quanta whose AIDCNT increased and
  the 3 quanta before each (at most 12): about 22 line-mode rows with the summary.
- Checker: `instr` (status, writes, writes_even_only, hits, odd_hits, errors, deliveries with the 3 preceding polls,
  detail) and `host_pattern` (`odd-poll-success` / `write-poll-only` / `other`); host clock only.


## 14. PR2I result (PR2I-C2) and closure of the probe series (user, 2026-10-19)
Build PACZ6PRB JOB08875 RC 0 (ASM 000, LKED 0, AMODE / RMODE 24 / 24). One live run, port 4011; trace SHA-256
`6e9dce16f6861ca65fd71dd9ffc47c9da5f4b2f6f8d56f8c10d6e550f09789fe`, checker RC 0. Host: QUANTA 133, ELAPSED 19950,
LATE>75 0, MAXLATE 1, WRITES 66, SKIPPED 67, AIDS 3; frames q2..q132, frame_step 2, no replay. Every AID (F4 q40, F5
q74, F6 q108) was first returned (RC 0, length 100) by the TGET right after a write; the three preceding polls (two
no-write, one write) returned RC 4; odd_hits = []. Classification **PR2I-C2** (not C4: the logical schedule matched PR2;
the transport was noisier - SDI/KRI 50, BID 53, locked max 797 ms - so PR2 stays the performance baseline).
Series closed: P0 queue grows / input not delivered; PT rejected; PN no useful send opportunities; PH input works, HOLD
timing rejected; PB4 bounded, periodic HOLD timing rejected; PR2 PR2-A decoupling validated; PR2I PR2I-C2. No further
probe mode, render divisor or rerun is authorised. Production design: docs/zos6-production-design.md.
