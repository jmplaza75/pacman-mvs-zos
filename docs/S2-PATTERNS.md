# MVS-S2: alarm patterns and sound polish - design (D41, APPROVED and frozen 2026-10-13)
Source: docs/ROADMAP-POST-RT.md row 6 ("Timed alarm sequences, only if the S1 evidence shows separate bells are not
merged. May close negative on the S1 evidence alone.") and the S1 result D35. User decisions: section 8.

## 0. Go / no-go on the S1 evidence (no new probe)
Probe E15 (docs/evidence/s1-e15-alarm.md) screens 5 and 6: three alarm writes were heard as three bells both when they
arrived in one socket read within 1 ms and when spaced 0.5 s apart. Separate bells are not merged, so S2 does **not**
close negative. Pitch and length cannot be controlled (one fixed terminal bell): a pattern is only **how many bells
and how many quanta apart**. No capability is unproven, so there is no probe step; the spacing of section 3 is
confirmed by the live checklist (S2.4).

## 1. Steps
| Step | Content | Exit |
|---|---|---|
| S2.1 | this design | user approval, D41 frozen (done 2026-10-13) |
| S2.2 | PACREQ (appended), PACMAIN (PARM column 25), PACDISP (pattern player), PACPLAT (op DLWT for the end pause), CLIST `ALARM`, model + cases | deck `S2` (TSD runs = model), regression decks rerun, every earlier reference unchanged |
| S2.3 | install (PACMAIN + CLIST) on the user's approval | install jobs |
| S2.4 | live c3270 checklist: the user counts the bells per event; the trace shows the alarm WCC on the modelled writes | docs/evidence/s2-live.md, README, CURRENT_PHASE, tag `mvs-s2` |

## 2. Scope rule (D41.1)
- **Display and platform only.** GAME, MAP, AI, PACARC and PACRT are not modified; tests/core_baseline.json unchanged.
  The pattern player reads the state (the counters S1/GP2 already read), never changes it.
- **Opt-in, byte-compatible.** New option `ALARM(PATTERN|SINGLE)`, PARM column 25 (`P` = PATTERN; absent or anything
  else = SINGLE). SINGLE is the S1/GP2 behaviour byte for byte and wait for wait, so every existing stream reference
  (test_s1, test_gp2, test_hs, test_rp, test_rt, test_gx, ...) is unchanged. The CLIST default becomes `ALARM(PATTERN)`.
- **SOUND(NO) suppresses every alarm**, SINGLE and PATTERN alike (REQ-SOUND not Y: no alarm bit, no bell-only write,
  no end-pause change). ALARM only defines how an enabled alarm sounds.
- **Rings only where a bell can ring today**: colour full-screen (TSC) and its TSD dry run. BAT and TSO line mode are
  unchanged (no SYSOUT change for any rule set).
- **No new write and no new wait during gameplay.** A pattern step is the WCC alarm bit on a REALTIME quantum write
  that is sent anyway (one write per quantum, D33). No STCK scheduling is added to the game loop. The only extra writes
  are bell-only writes (`C6 28 00 00`, the S1 precedent) inside the existing 3-s end pause, after the game is over.
- **Both rule sets**, for the events that already ring (section 3.1). No new sound event.

## 3. Events and patterns (D41.2)
### 3.1 Alarm events before S2 (code and tests read 2026-10-13)
All six events already produced an alarm before S2; S2 adds **no** ringing event, it only changes how many bells an
existing alarm gives.
| Event | Alarm before S2? | Where (PACDISP SET-BELL / ARC-BELL, D35 / D37) | Tests |
|---|---|---|---|
| Start | yes, both rule sets | first screen sent (SB-SENT = 0) | test_s1, test_gp2 |
| Death, lives left | yes, both | CLASSIC: LIVES fell; ARCADE: ARC-NDIE rose | test_s1, test_gp2 |
| Extra life | yes, ARCADE only (CLASSIC has none) | ARC-XL 0 -> 1 | test_gp2 |
| Level clear | yes, ARCADE only (CLASSIC has none) | ARC-LEVEL rose | test_gp2 |
| Game over (last death) | yes, both, **as a death** | the same death rule ("the last one too", D35); ARCADE: PACGAME LOSE-LIFE runs ARC-LOSE (+1 ARC-NDIE) on every hit, the last one too | test_s1 (LOST0), test_gp2 |
| Win | yes, both | first screen after F-WON (SB-WON) | test_s1, test_gp2 |

The only reclassification: under PATTERN a death that ends the game (F-LOST = 1 on that screen) uses the game-over
pattern instead of the death pattern. Under SINGLE it is one bell as before.

### 3.2 Pattern table and spacing (frozen)
Spacing **G** in quanta, exact and deterministic: **G = 2 when REQ-RTPER = 150 (NORMAL, 300 ms), G = 3 when
REQ-RTPER = 125 (FAST, 375 ms)**. A pattern of n bells has the offsets 0, G, 2G, ... (n-1)G quanta from the event's
write; offset 0 is the write that rings today. No millisecond target, no conversion, no extra clock reads.
| Event | Bells | Offsets NORMAL (G 2) | Offsets FAST (G 3) | Carried by |
|---|---|---|---|---|
| Start | 1 | 0 | 0 | the first screen |
| Death, lives left | 2 | 0 2 | 0 3 | the death freeze (10 / 12 quanta) |
| Extra life (ARCADE) | 2 | 0 2 | 0 3 | ordinary quanta |
| Level clear (ARCADE) | 3 | 0 2 4 | 0 3 6 | the clear freeze (10 / 12 quanta) |
| Game over | 3 | 0 2 4 | 0 3 6 | ARCADE REALTIME: the final death frames; otherwise the end pause (section 5) |
| Win | 4 | 0 2 4 6 | 0 3 6 9 | the end pause (section 5) |
Fit: every in-play pattern ends inside its freeze; the ARCADE REALTIME game-over pattern ends on the final death frames
(NORMAL 6 frames after the deciding quantum, offsets 1-6; FAST 7 frames, offsets 1-7), so it needs no end-pause step.

## 4. Player rules (D41.3)
- Event detection is SET-BELL / ARC-BELL unchanged (same counters, same coalescing of the events of one write). With
  SINGLE the result is used exactly as today. With PATTERN the highest event of the write selects its pattern.
- **Priority** GAME OVER > WIN > LEVEL CLEAR > DEATH > EXTRA LIFE > START.
- **One pattern at a time.** An event of higher or equal priority than the running pattern replaces it: its offset 0
  rings on its own write (as today; an event is never delayed) and the old pattern's remaining steps are dropped. The
  minimum spacing G applies inside a pattern; a replacing event's offset 0 may come sooner after the previous bell.
  An event of lower priority while a pattern runs is absorbed (no bell of its own). This case cannot occur in play
  (start ends at once; death and level-clear patterns end inside their freeze, when the game takes no step; only death
  or game over can follow an extra life, and both are higher); the model asserts it never happens in any case.
- **What counts and rings: the quantum writes.** In REALTIME every quantum has exactly one write (D33); it may be the
  plain frame or, after ENTER / invalid input / PA2, a prompt-form frame (REQ-RTFR P / F). Each quantum write advances
  the pattern by one quantum and carries a due step, whatever its form. (Clarification of the S2.1 draft, which called
  the prompt-form frames "not quanta": they are the quantum's one write.)
- **Writes that are not quanta never ring a step and do not advance a pattern**: the pre-start screens after the first
  one, the pause screens (PAUSED, blocking reads), the visual ticks.
- **Pause**: the pattern is held; its remaining steps continue on the quanta after resume (offsets count quanta, not
  wall clock).
- **TURN games**: there are no quanta; during play every event gives its offset-0 bell only (= today's single bell).
  The game-over and win patterns continue in the end pause (section 5).
- **Game end** (WON / LOST / QUIT / EOF): the steps still due from an in-play pattern are dropped; only the game-over
  or win pattern continues into the end pause.

## 5. End pause (D41.4)
- The end pause is the existing 3-s pause after the scaled end screen (PACPLAT WAIT = PACTSO STIMER 3 s). It is never
  lengthened.
- SINGLE, or PATTERN with no step left: PACPLAT `WAIT` exactly as today.
- PATTERN with steps left (TSC): PACDISP reads the clock (`CLOK`) when the end screen is sent (t0). The end screen
  rings only as today (offset 0 when the event is first seen on it). Each remaining step j = 1, 2, ... is a bell-only
  write at t0 + j x G x REQ-RTPER ms (`WDLN` G times per step, the existing absolute-deadline op); then a new PACPLAT
  op `DLWT` waits until t0 + 3000 ms (PACTSO DLWT, unchanged). Total pause = 3 s; the last step is at most
  3 x 3 x 125 = 1125 ms after t0. Every step is at least G quanta after the previous bell (the deciding write is sent
  just before the end screen).
- TSD (dry run): the same writes, no waits (as every TSD wait today).
- **Not scaled** (no end screen, no pause): unchanged from S1 - one bell-only write for a pending offset 0, no pattern
  steps, no new wait.
- ARCADE REALTIME LOST: the pattern is complete on the final death frames; the end pause is the plain WAIT.
- QUIT and EOF never ring (as today).

## 6. Tests (D9, D10, D12)
- Independent model: a pattern layer over the existing screen models (the test_s1 `with_bells` / test_gp2 `bells`
  snapshots), written from this document, not from the COBOL: input = the modelled writes with their events and quantum
  flags, output = the alarm bit per write + the end-pause bell-only writes.
- Deck `S2` (job PACBLDS2): build + TSD runs with `ALARM(PATTERN)` for CLASSIC and ARCADE, REALTIME at NORMAL and FAST,
  and TURN; every stream = model (bytes and alarm bits).
- Regression: every TSD run without column 25 = its existing reference byte for byte (test_s1, test_gp2, test_hs,
  test_rp); test_core_frozen unchanged; 1.0-MVS oracle unchanged.
- Edge cases, each one a run (D12): death during an extra-life pattern (replace); extra life and level clear in one
  step (highest wins); death and extra life in one step; last pellet and a hit in one step (win vs death / game over);
  last death (game over replaces death; ARCADE final death frames carry it, CLASSIC end pause); pause in the middle of a
  pattern (held, resumes); PA2 / ENTER / invalid input on a due quantum (prompt-form frame rings); pre-start inputs (no
  ring after the first screen); QUIT and EOF during a pattern (dropped, silent end); TURN game (single bells in play,
  end pattern in the pause); not scaled end (S1 bell-only write only); FAST spacing; SOUND(NO) with ALARM(PATTERN)
  (silent, = SOUND(NO) reference); column 25 in BAT and TSO line mode (SYSOUT unchanged).
- Static: SET-BELL / ARC-BELL change only their S1/GP2 fields; the player changes only its own fields + REQ-BELL;
  GAME / MAP / AI / PACARC / PACRT sources identical to mvs-rp.

## 7. Live (S2.4)
c3270 checklist: the user counts the bells of each event at NORMAL and FAST (death 2, extra life 2, level clear 3,
game over 3, win 4, start 1) and confirms SOUND(NO) is silent; the trace replay shows the alarm WCC on exactly the
modelled writes and the end pause still about 3 s.

## 8. Decisions (user, 2026-10-13) - D41 frozen
1. `ALARM(PATTERN|SINGLE)` in PARM column 25; absent = historical S1/GP2 bytes; CLIST default PATTERN.
2. TURN: single bells during play; full patterns only where they need no gameplay wait or write (the end pause).
3. Counts start 1, death 2, extra life 2, level clear 3, game over 3, win 4; exact spacing NORMAL 2 quanta (300 ms),
   FAST 3 quanta (375 ms); no STCK scheduling or waits in play to equalise gaps.
4. No additional sound events (power pellet, ghost eaten, fruit, new high score stay silent). Verified: all six
   patterned events already rang before S2 (section 3.1).
5. Total end pause 3 s; end-pattern bell-only writes inside it, never lengthening it.
SOUND(NO) suppresses everything; priority and pause/redraw rules as in section 4.
