# ZOS-6 REALTIME - final design (APPROVED 2026-10-16; not implemented, nothing executed)

Base: tag `zos-5` (e047049), no z/OS write since. Scope: prove `PLAY(REALTIME)` live on the installed PACMAIN through the
full-screen path accepted in ZOS-5. Out: ARCADE (ZOS-7), high score / recovery / PACFSIO C3-E2 (ZOS-8), equivalence
battery (ZOS-9), release (ZOS-10). No build, install, upload, job, source / CLIST / JCL / oracle change; no remote
precheck (nothing REALTIME depends on can have changed since the zos-5 closure); local git verification only.

## 1. Delta
- Already proved: PACTSO TIME (STCK) / DLWT (absolute deadline, STIMER for the remainder, RC 4 when passed) in batch
  (ZOS-2 PACZ2DRV TSOT1: 20 deadlines at 150 ms, RC 0, late deadline RC 4); REALTIME game logic in batch on z/OS
  (ZOS-2 RTB1/7/8/10/11 = oracle 310); the full-screen path live (ZOS-5: TN3270E, CONTENTION-RESOLUTION, PACQRY,
  (1,1,1), 120 x 27, GRAPHIC 4x2, partial / full writes, CLEAR / PA2, ISPF option-6 closure).
- Partly proved: live idle ticks (ZOS-5) came from the TURN idle path (RECT, 0.5 s), not from the REALTIME loop; FAST
  and REALTIME streams ran on z/OS only as TSD dry runs (S2T).
- Not proved (the ZOS-6 delta): the live RT loop (blocking press-to-start, POLL = TGET ASIS,NOWAIT per quantum, CLOK /
  WDLN absolute deadlines with real DLWT, one write per quantum incl. the restore-only write); PF8 / PF9 / PF11 AIDs
  through z/OS TN3270E; live pause (no writes, re-based clock, no catch-up); the live death stop; FAST live; REALTIME
  cadence when nearly every host write needs a TN3270E BID round trip (ZOS-5 traces: BID response -> data median
  ~110 ms, p95 ~210-220 ms, max 690 ms), i.e. the terminal keyboard-locked for most of each quantum.

## 2. Cases (one c3270 / logon session, ISPF option 6, CONTENTION-RESOLUTION enabled as accepted in ZOS-5)
Profile and canvas from the query as in ZOS-5 (expected (1,1,1), 120 x 27, GRAPHIC 4x2). PARM by the CLIST rule
(tests/test_g8.py clist_parm).
R1 NORMAL, T = 150 ms: `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO)'`,
PARM `TSO AI0 1 NAAAPAAARNC01NP`. Plan: pre-game transition ENTER (ISPF `***`); 5 s before press-to-start (zero PACMAN
game writes); PF8 start; 60 s principal run (~400 quanta); PF9 pause; 60 s paused (zero PACMAN game writes); PF9
resume; 10 s run; `x` + ENTER (invalid); PA2; PF11 (runs right on row 9 into the still ghost: death); exactly 10
death-stop quanta; blocking wait; `Q` + ENTER; exact closure; `***`; closure ENTER; ISPF Command Shell.
(ref_rt.simulate of this plan: death, LIVES 2, SCORE 0230; the quantum numbers depend on the live arrival times.)
R2 FAST, T = 125 ms: the same command with `SPEED(FAST)`, PARM `TSO AI0 1 NAAAPAAARNC01FP`. Plan (decision
2026-10-16: all four directional PF AIDs proven on the real z/OS TN3270E / TGET path, PF7 and PF10 added to R2, no
third case): 1 pre-game transition ENTER at `***`; 2 PF11 start; 3 wait 5 s; 4 PF8; 5 wait ~2 s; 6 PF7; 7 wait ~2 s;
8 PF10; 9 the uninterrupted 30 s FAST principal timing segment, starting only after PF10 (no driver input inside it,
~240 quanta); 10 `Q` + ENTER while running; 11 exact closure; 12 `***`; 13 closure ENTER; 14 ISPF Command Shell.
Directional coverage over R1 + R2: PF7 UP, PF8 DOWN, PF10 LEFT, PF11 RIGHT.
R2 runs only after the immutable R1 trace passed the local gate (section 6).
D28: no case. REALTIME starts with an explicit blocking press-to-start read: before the first direction there is no
pending output to retain, and ZOS-5 showed three times that z/OS does not retain output after the query.

## 3. Oracle and model
- Model: tests/ref_rt.py `tsd(cards, canvas, per)` on the ACTUAL cards reconstructed from the trace (an AID may land in
  the quantum after the one its arrival suggests; both assignments tried, the rules of tools/c3270_gp1_trace.py
  `command` / `cards_for`, proven live on MVS G8 / GP1 / GP2 / S2). Anchored locally to the frozen oracle 310 blocks
  RTT1-RTT6 (TSD REALTIME, canvases W / D) and RTB1-RTB12 (batch REALTIME). No new or modified oracle.
- No timing normalisation of game output: the frames carry no clock; QUANTA in the end lines comes from the model.
- Gameplay inputs must also be exactly the planned ones (section 7).

## 4. Migration-plan requirements (docs/ZOS-MIGRATION-PLAN.md, ZOS-6; the plan itself is not rewritten)
Retained unchanged:
- one write per quantum (functional: live writes = model quanta, in order, byte for byte);
- no burst after a pause (functional where protocol evidence proves it; section 5 B);
- client side: gap median within T +/- 10 ms (a timing acceptance gate, section 5);
- freeze duration within one quantum of 1500 ms (NORMAL): 1350..1650 ms, plus the semantic 10 quanta (section 5);
- PA2 during play, PF9 pause, keyboard restore per write (model: every quantum write restores; driver: no lock > 5 s);
- live criteria at NORMAL and FAST; p95 recorded.
Interpreted (not directly observable from the client trace, which sees host scheduling + TN3270E contention
resolution + network + terminal):
- "drift < 1 ms / 100 quanta": the exact host-side drift is not observable. Host-side absolute-deadline semantics rest
  on the PACTSO TIME / DLWT code and on ZOS-2 TSOT1 (real STCK / STIMER). ZOS-6 adds a live non-accumulation proxy on
  the principal run: total elapsed terminal time, ideal elapsed time ((n - 1) x T), endpoint drift, mean period, linear
  trend and residuals. The evidence labels it "live proxy", never the original host measurement. The mean-period band
  is not claimed to be equivalent to the 1 ms / 100 quanta criterion.
- "no skipped period": the semantic target stays no skipped period; a single skipped host deadline cannot always be
  told apart from network / BID delay at the terminal (rules in section 5).
- "no burst after a pause": checked by a conservative client-side proxy (section 5 B).
- "decks = models" (exit criterion): the model is anchored to the frozen RT blocks locally; the z/OS batch REALTIME
  runs of ZOS-2 stand; no further batch deck in ZOS-6 (no jobs); the full battery is ZOS-9.
Not applicable here: fright / eyes durations (ARCADE, ZOS-7).
Explicit deviation (approved 2026-10-16): pause soak 60 s instead of the plan's 10 minutes, chosen to avoid an
uncontrolled TSO inactivity / environment timeout on the shared service. The functional requirement stays strict:
zero PACMAN game writes during the whole PAUSED interval (BID / RESPONSE control traffic is not a game write).

## 5. Classification (per case)
Principal segment = the longest uninterrupted run of quantum writes (first write after the start / resume AID up to a
blocking state or the end screen), derived from the trace, not from nominal seconds; it must hold >= 200 quanta (R1
~400 at 150 ms, R2 ~240 at 125 ms).

| Measure | Rule |
|---|---|
| Mean period of the principal segment | < 0.99 T: FUNCTIONAL / TIMING FAIL (recovering too aggressively, or the reconstruction is wrong), STOP. 0.99-1.02 T: timing PASS. > 1.02 T to 1.10 T: ENVIRONMENT / TIMING BLOCKED, keep evidence, STOP. > 1.10 T: TIMING / ENVIRONMENT STOP, the next case is not run |
| Median gap of the principal segment | within T +/- 10 ms: PASS; outside with exact functional behaviour: ENVIRONMENT / TIMING BLOCKED (not functional). If CONTENTION-RESOLUTION makes it impossible here: keep the evidence, stop ZOS-6 for a separate design decision |
| Death stop (R1) | not exactly 10 quanta: FUNCTIONAL FAIL; 10 quanta but terminal duration outside 1350..1650 ms: ENVIRONMENT / TIMING BLOCKED; raw duration and the BID timing around it reported |
| Skipped periods | a missing quantum / write against the model: FUNCTIONAL FAIL; unambiguous timing evidence of skipped periods: ENVIRONMENT / TIMING BLOCKED; long gaps plausibly caused by BID / network: recorded and correlated with BID timing, not a functional fail by themselves; no timing PASS if the checker concludes skipped host periods probably occurred |
| p95, max gap, BID count / latency, keyboard-locked fraction per quantum | diagnostics only |

B. No burst after PF9 resume (conservative client-side proxy): sustained acceleration = mean < 0.99 T, FAIL. The first
five PACMAN quantum writes after the resume: all five gaps and the corresponding BID timings reported; two or more
consecutive client gaps < 0.5 T = TIMING SUSPICIOUS; if the raw TN3270E / BID ordering proves the host generated an
illegal burst: FUNCTIONAL / TIMING FAIL; if network / BID prevents the distinction: ENVIRONMENT / TIMING BLOCKED. The
allowed burst count is never enlarged from the observed BID latency. Exact model, write count and order stay mandatory.

Results:
- FUNCTIONAL FAIL: PACMAN / model byte mismatch; missing / extra / duplicate gameplay AID; planned != driver log !=
  reconstructed terminal actions; a PACMAN game write before press-to-start or while PAUSED; wrong pause / resume
  state; wrong death-stop quantum count; wrong QUANTA / state / score / lives / closure; invalid full-screen behaviour;
  no return to the shell; sustained cadence < 0.99 T; a host burst proven by protocol evidence; an IKJ / CEE / IGZ /
  IEC / ABEND / PACMAN: diagnostic.
- ENVIRONMENT / TIMING BLOCKED: functional behaviour exact, but a required live timing criterion cannot be accepted
  (mean > 1.02 T, median outside T +/- 10 ms, death stop outside 1350..1650 ms, probable / observed skipped periods,
  post-resume burst-like timing not safely attributable, no trustworthy timing evidence). Does not close ZOS-6, does
  not authorise changing tolerances or disabling CONTENTION-RESOLUTION.
- TIMING PASS: mean in [0.99 T, 1.02 T]; median within T +/- 10 ms; no functional mismatch; no evidence sufficient to
  conclude skipped periods; no illegal post-pause burst; R1 death stop within 1350..1650 ms.
- CASE PASS = FUNCTIONAL PASS + TIMING PASS. PHASE PASS = R1 PASS + R2 PASS.

## 6. Session and the R1 -> R2 gate (two immutable traces, one c3270 / logon session)
1. Log on, ISPF option 6; `Trace(On, <raw-trace-dir>/zos6-R1.trace)` with the ISPF Command Shell visible.
2. Driver R1 to the closure and back to the shell. 3. `Trace(Off)`. 4. SHA-256 of the R1 trace, made read-only.
5. Local read-only gate on the immutable R1 trace (zos6_live_check). 6. Only on FUNCTIONAL PASS and TIMING PASS: a new
`Trace(On, <raw-trace-dir>/zos6-R2.trace)` in the same live c3270 session; driver R2. 7. `Trace(Off)`, hash, freeze.
R1 FUNCTIONAL FAIL, ENVIRONMENT / TIMING BLOCKED or STOP: R2 is not run. Then leave ISPF (=X ends the session).
Raw traces and driver logs stay outside git; derived evidence only after the security / privacy audit.

## 7. Driver contract (tools/zowe/zos6_drive.py)
Actions only through the c3270 script port, spellings checked against the installed x3270 4.5ga6 (local s3270, no
host): `PF(7)` `PF(8)` `PF(9)` `PF(10)` `PF(11)` `PA(2)` `Enter()` `String("x")` `Wait(5,Unlock)` (`Ascii()` to read
the screen).
Per action a log entry: ordinal; category transition | gameplay | closure; planned action; requested timestamp;
Wait(5,Unlock) start; unlock timestamp; send timestamp; result / error. Transition = the EXEC and the pre-game ENTER at
ISPF's `***`; gameplay = the in-game keys (PF7 / PF8 / PF9 / PF10 / PF11 / `x` + ENTER / PA2 / `Q` + ENTER); closure = the ENTER at
the closing `***`. The checker counts only gameplay actions as REALTIME inputs.
Starts only with the ISPF Command Shell on screen; reads the screen only by Ascii (never during logon). Never logs on,
sends a userid / password, starts or stops a trace, starts R2 by itself, or retries. STOP on: keyboard locked > 5 s,
any x3270if error / timeout, IKJ / IEC / IGZ / CEE / ABEND / PACMAN: on screen, the game in line mode, no game screen
within 30 s, no shell within 60 s after the closure.
Acceptance: planned gameplay actions == successful driver gameplay actions == gameplay AIDs reconstructed independently
from TN3270E, in exact order, none missing or duplicated. For every directional action (PF7 / PF8 / PF10 / PF11) all
four layers must agree and are reported explicitly: planned driver action == successfully sent x3270if action ==
reconstructed TN3270E AID (X'F7' / X'F8' / X'7A' / X'7B') == the direction of the card the REALTIME model consumed
(U / D / L / R); no missing, duplicate or substituted PF AID; success is never inferred only from later game state.

## 8. Checker (tools/zowe/zos6_live_check.py; zos5_live_check.py frozen)
Imports the stable ZOS-5 helpers (blocks, telnet, tn3270e, functions, texts, SHELL, outside_errors and the query /
profile rules) without changing them or the return contract of parse(); obtains the raw records (BID, RESPONSE) itself
for the statistics. If a clean reuse proves impossible: STOP for approval before touching zos5_live_check.py.
rt_game(trace, case, T, driver log): switch, query, valid reply, profile / canvas, first screen; zero game writes
before the start AID; cards from the gameplay AIDs (both assignments); every quantum write = ref_rt.tsd byte for byte
(ZOS-5 command-byte rules; restore-only `F1 C2 28 00 00`); PAUSED screen then zero game writes until the resume AID;
10 death-stop quanta per the model; end lines incl. QUANTA = model; `***`, closure ENTER, shell; planned == driver ==
reconstructed, with a per-directional-action report (planned, sent, observed AID byte, quantum and model direction).
The R2 principal segment is the uninterrupted run after PF10 up to `Q`. Timing: principal segment, mean, median, endpoint drift, trend / residuals, inferred skipped periods,
post-resume five gaps with BID timings, death-stop duration, BID count / latency, keyboard-locked fraction (c3270
`kybd` lines inside the game), gap / BID correlation; classification of section 5. Modes: one trace per case; the R1
gate is the same run on the frozen R1 trace.
Tests: section 20 of tests/test_zos_tools.py with tests/zos6_fixture.py (synthetic REALTIME traces from ref_rt, framed as
in ZOS-5 with CONTENTION-RESOLUTION, BIDs and responses, on a T grid) and the local anchor ref_rt = oracle 310
RTT1-6 / RTB1-12; positives R1 / R2; negatives for every FUNCTIONAL FAIL rule and each ENVIRONMENT / TIMING class.

## 9. Files (when implementation is approved)
New: tools/zowe/zos6_live_check.py, tools/zowe/zos6_drive.py, tests/zos6_fixture.py, docs/zos6-live-session.md,
docs/evidence/zos6-realtime.md. Modified: tests/test_zos_tools.py, docs/CURRENT_PHASE.md. Not modified:
tools/zowe/zos5_live_check.py. Game / source / JCL: none.
All design decisions are resolved (user, 2026-10-16); implementation waits for approval.
