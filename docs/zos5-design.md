# ZOS-5 Full-screen / graphics - design (for review; nothing executed, no source / CLIST / JCL / dataset change)

Base: tag `zos-4` (95b2ad9). Process: minimal read-only precheck -> one live session -> focused local postcheck ->
evidence. Scope (user, 2026-10-16): only the genuinely new live behaviour of the 3270 full-screen path. Out: REALTIME
(ZOS-6), ARCADE (ZOS-7), sound / alarm / HS / ESTAE (ZOS-8), CLASSIC line mode (accepted in ZOS-4).

## 1. What is already proved and what is new
| Property | Already proved by | New in ZOS-5 |
|---|---|---|
| CLASSIC TURN TSC renderer (G1-G4, GS 4x2, GX geometry) | MVS: 1371 streams = models (JOB 207); 2.0: oracle 310 TSD1-61 (**ref_gx_screen = all 61 frozen blocks, re-checked 2026-10-16**) | the same module's streams on z/OS (never run there: the z/OS TSD runs so far were ARCADE REALTIME S2T / HG) |
| Wide 4x2 GRAPHIC renderer on z/OS (TSD dry run) | PACZ3TD1-4, HS7 HG2/HG3 (canvas W, GRAPHIC, scale 4) | - |
| PACQRY parsing / D40 selection | QRY1 on z/OS (ZOS-2, 20 replies + 29 sequences = oracle 310) | the real reply of the z/OS TN3270E path |
| PACFSIO not-TSO contract (RC 4 -> line mode) | ZOS-3 batch | FSON, SENX, QRY, SEND, SENP, RECV / RECT, FSOF with a real TSB |
| PACTSO CLS / STLINENO, CLIST, profile A, Z3 SYSIN, line-mode TSO | ZOS-4 live | PACTSO WAIT / DLWT (STIMER) behind the 0.5 s tick and the 3 s end pause |
New host paths, all inside PACFSIO / PACTSO / the TN3270E path (no other module is on the boundary):
STFSMODE / STTMPMD / TCLEARQ (FSON / FSOF), TPUT NOEDIT (SENX size switch, SENP partials, WSF Read Partition Query),
TPUT FULLSCR (first screen), TGET ASIS (query reply, AIDs), TGET ASIS,NOWAIT + 0.5 s wait (RECT idle ticks), STIMER
(end pause), the D28 behaviour (held output after the query) and CLEAR / PA2 on z/OS.

## 2. Geometry (derived, not assumed)
- Frozen tests: the GX geometry runs simulate canvas `W` = 120 x 27 (wide layout: maze rows 4-23, columns 21-100);
  D32 (approved 2026-10-09) fixes 120 x 27 IBM-DYNAMIC as the primary large canvas, launch
  `c3270 -model 2 -oversize auto` in a 120 x 30 window sized before connecting (docs/GS-GEOMETRY.md 10, 14).
- CLIST: `CANVAS(AUTO)` (default) + `COLOR(AUTO)` -> Erase/Write Alternate before the query, the size taken from the
  reply (X'A6', else X'81', else 80 x 24); `COLOR(YES)` or `CANVAS(DEFAULT)` -> Erase/Write 80 x 24, no query.
- z/OS evidence: both ZOS-4 sessions used exactly that launch and window; session 1's IGZ0201W showed the terminal
  line size 120, i.e. the z/OS TN3270E path accepted the oversize terminal with a 120-column alternate screen. The
  rows (27 expected) are known only from the reply: the postcheck reads them from it.
- Therefore: **the same launch and window as ZOS-4**: `c3270 -model 2 -oversize auto 198.51.100.200:623` (+ the script
  port, section 6), window 120 x 30 before connecting, never resized while connected. Expected reply = the TK4-
  IBM-DYNAMIC reply tests/qreply_dyn.hex (c3270 builds it, not the host): qry_cases gives colour 1, highlight 1, GE 1,
  alternate 120 x 27. A different reply is not a FAIL by itself (section 7).

## 3. Cases (frozen 2.0 TSD runs of oracle 310, played live)
| Game | Frozen case | Frozen 2.0 block | Why it is needed |
|---|---|---|---|
| A | `MOVES` (AI1, 1 ghost) | TSD45 = GX run (MOVES, C Y, H Y, ANIM Y, PARTIAL, GRAPHIC, scale 4, canvas W) | the whole AUTO path: real query -> PACQRY -> profile (colour, highlight, GE/APL glyphs, 4x2) -> Erase/Write Alternate 120 x 27 -> wide layout; first full screen (FULLSCR), partial redraws (moves, 3 blocked moves, invalid `X` with the blinking message, lowercase `r`), idle ticks (RECT + wait), QUIT banner, 3 s pause, FSOF, end lines, READY |
| B | `TSORDR` (AI1, 1 ghost) | TSD48 (same profile, canvas W) | a second query in the same session (D40 start after a finished game); the redraw card played as **CLEAR then PA2**: CLEAR drops the terminal to 80 x 24 and is not delivered (E4); PA2 must bring back 120 x 27 by SENX X'7E' + the full screen |
| C | `TSORDR` | TSD28 (C Y, H Y, ANIM Y, PARTIAL, GRAPHIC, scale 4, canvas default 80 x 24) | the explicit override `COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC)`: no query, Erase/Write 80 x 24, the 80 x 24 GS screen (the documented fallback if AUTO ever fails on z/OS); redraw by empty ENTER |
Not included (proved or out of scope): G1-G4 not-scaled profiles, BASE / CLASSIC glyphs, 3x2, tall / 132 layouts, the
size guard (all TSD byte-identical, transport identical); a second geometry (model 3/4/5) - the only z/OS canvas in
use is the one above; SOUND (ZOS-8); REALTIME / PF keys (ZOS-6); ISPF split screen.

## 4. Invocations and PARMs (tests/test_g8.py clist_parm rule)
| Game | Command at READY | PARM |
|---|---|---|
| A, B | `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'RULES(CLASSIC) PLAY(TURN) SOUND(NO)'` | `TSO AI1 1 NAAAPAAATNC01NP` |
| C | `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC) RULES(CLASSIC) PLAY(TURN) SOUND(NO)'` | `TSO AI1 1 NYYAPGAATNC01NP` |
AI(1) GHOSTS(1) are the CLIST defaults and the cases' configuration (no config card). Every other keyword at its 2.0
default: ANIM AUTO (= YES in TSC), REDRAW PARTIAL, SCALE AUTO (-> 4: colour + highlight + GRAPHIC), CANVAS AUTO,
METRICS NO. `SOUND(NO)` keeps the alarm (ZOS-8) out: no alarm bit in any write, so the frozen blocks apply as they are.
The installed CLIST (Z3 + Z2), PACMAIN and CEEOPTS are used unchanged.

## 5. Keyboard sequences (one key line + ENTER per prompt; the game ends at Q)
- A (MOVES): `R` `R` `U` `L` `L` `L` `D` `D` `R` `X` `r` `R` `R` `D` `Q`. Expected: MOVED, MOVED, BLOCKED, MOVED, MOVED,
  BLOCKED, MOVED, MOVED, MOVED, `INVALID COMMAND X` (blinking), MOVED (lowercase), MOVED, MOVED, BLOCKED, QUIT banner.
  End lines `QUIT` / `TURNS 013` / `SCORE 0080` / `LIVES 3`.
- B (TSORDR): `R`; then **CLEAR**, then **PA2** (the redraw); `D` (BLOCKED); `Q`. End lines `QUIT` / `TURNS 002` /
  `SCORE 0010` / `LIVES 3`.
- C (TSORDR): `R`; empty ENTER (redraw); `D` (BLOCKED); `Q`. Same end lines as B.
Pace is free (TURN): idle time only adds visual ticks, which the postcheck accounts for.

## 6. Session procedure (one session, the user at the keyboard)
1. Window 120 x 30; `c3270 -model 2 -oversize auto -scriptport 4001 198.51.100.200:623`; logon and password by the
   user; no trace before step 3.
2. ISPF -> `=X` to TSO READY (decision 1).
3. At READY, from another terminal tab: `x3270if -t 4001 'Trace(On,<file outside the repo>)'`.
4. Game A, then (after the clean return to READY) game B, then game C.
5. `x3270if -t 4001 'Trace(Off)'`; LOGOFF.
Optional screen captures (local, nothing sent to z/OS): `x3270if -t 4001 'PrintText(html,file,<path>)'` at A start,
A after `X`, B after PA2, C start.

## 7. PASS / FAIL and STOP
Per game PASS (postcheck on the trace, section 8, plus the user's observations):
- A / B: first host record of the game = Erase/Write Alternate (X'7E') + WCC, no data; then the WSF Read Partition
  Query; the inbound reply (AID X'88') structurally valid (qry_cases.valid) with the profile colour / highlight / GE and
  the alternate size the postcheck derives from it; for the acceptance as designed: (1, 1, 1) and 120 x 27.
- C: first host record = Erase/Write (X'F5') + WCC; no query, no X'88' inbound.
- Every game write equals the model (ref_gx_screen with the case's profile and canvas, the cards rebuilt from the trace:
  each idle tick write = `+`, each ENTER = its typed command, PA2 / empty ENTER = redraw) byte for byte after the 3270
  command byte (write 0 may carry PACFSIO's clear prefix; later full screens X'7E' / X'F5' as the canvas; partials and
  ticks X'F1'). Without ticks the model is exactly the frozen block (TSD45 / TSD48 / TSD28).
- The end screen, then line mode: the end lines = the frozen block's end lines; READY.
- User observations: maze centred with side HUD (A / B), 80 x 24 GS (C); colours and highlighting (blinking red message,
  reverse banner); GE box walls, half-block Pac-Man and ghost; animation ticks (or held until the first input: D28,
  recorded, not a FAIL); keyboard usable after every write; CLEAR + PA2 restores the 120 x 27 screen; 3 s banner; clean
  READY after each game.
FAIL / STOP (end the session, no retry, nothing changed): any IGZ / CEE / IKJ / IEC / abend message or `PACMAN:` message;
`***` inside a game; game A or B starting in line mode (the query path failed) or C not full-screen; a corrupted or
unreadable screen; keyboard locked with no way to continue; no clean READY; any unexpected panel.
Not a FAIL by itself: a reply with another size or capability set if the writes equal the model for it (recorded; the
wide-layout acceptance then stays open for review); D28 holding.

## 8. Evidence and postcheck (local, read-only)
- One new tool, `tools/zowe/zos5_live_check.py` (to be written after approval; small): reads the trace from the first
  host record after `--from` (nothing before READY exists in it); strips the 5-byte TN3270E header (z/OS is TN3270E,
  TK4- was plain TN3270: the one transport difference for the existing trace readers); splits the three games; rebuilds
  the cards; compares with tests/ref_gx_screen.py; extracts the reply to `tests/qreply_zos_dyn.hex` (the plan's new
  recorded input) and evaluates it with tests/qry_cases.py; reports per game: writes / model-identical / ticks / AIDs,
  command bytes, D28 (ticks before the first AID or not), the end pause, the end lines. Its self-test (local): ref_gx_screen
  = oracle 310 TSD45 / TSD48 / TSD28 (already true: 61 / 61 blocks) and a one-byte mutation fails.
- Repository: docs/evidence/zos5-fullscreen.md (results, the user's observations, a z/OS capability table in
  CAPABILITIES.md form: CONFIRMED / NOT SUPPORTED with evidence), the derived report, the reply hex, optional
  PrintText captures; the raw trace stays outside git (it holds the READY screens and typed commands).

## 9. Source / CLIST / JCL change: none required
- PACFSIO under profile A (AMODE 24, buffers below the line) uses the 24-bit TPUT / TGET forms the plan identified as
  the risk; ZOS-3 assembled it unchanged and ZOS-4 ran PACTSO's STLINENO live. No evidence today requires a Z-entry.
- The CLIST keywords exist; Z3 also covers the SYSIN open in TSC; nothing else is allocated.
- If the live session shows a z/OS difference (reply not reaching TGET, a command byte / chaining difference, a
  STFSMODE / STTMPMD behaviour), it is analysed from the trace and proposed as an isolated Z-entry for review; nothing
  is changed in the session.
-> **No build, no install**: the acceptance runs on the installed zos-4 baseline.

## 10. Pre-live checks
- Read-only (Zowe, once, before the session): the installed state = the zos-4 closure (CLIST(PACMAN) SHA-256
  f8989cfa..., PACSRCT template, CEEOPTS exact, PACMAIN attributes = PACZ2D, PACZ2D unchanged) - the existing
  zos_ins_check functions, as in the ZOS-4 closure.
- Local: the postcheck self-test above. No batch job: the live writes are compared with the same frozen 2.0 blocks a
  batch TSD run would reproduce; a z/OS TSD run of TSD45 / TSD48 / TSD28 (one small job) is only a diagnostic if a live
  write differs (renderer on z/OS vs transport).

## 11. Decisions requested
1. Environment: native TSO READY via `=X` (recommended: the MVS acceptance environment, no ISPF screen manager around
   STFSMODE / TCLEARQ) - or ISPF option 6 (as ZOS-4). If `=X` does not reach READY on this logon procedure, say so and
   option 6 is used instead.
2. One session with the reply captured in the trace and checked afterwards, instead of the plan's two-step "capture,
   PACQRYT batch, then the game" (sec. 12): the live writes = model under the profile derived from the captured reply
   prove the same thing, and PACQRY itself is already proved on z/OS (QRY1).
3. The three games A / B / C as above (SOUND(NO); CLEAR + PA2 in B).
4. Trace on / off and optional PrintText by the user through the script port (`x3270if -t 4001`), after READY only.
5. The postcheck tool of section 8 written and self-tested before the session.

## 12. Decisions (user, 2026-10-16) and preparation
Approved: (1) native TSO READY via `=X` (ISPF log disposition option 3 if asked), trace only from READY; (2) one session,
no PACQRYT batch, STOP after game A on a query / parser / terminal problem; (3) A MOVES / TSD45, B TSORDR / TSD48
(CLEAR + PA2), C TSORDR / TSD28 forced, in this order, no other game; (4) the trace is the primary evidence (on at
READY, off after C's clean READY, raw kept immutable with SHA-256, audited, never committed), PrintText only at
milestones; (5) the checker before the session, with explicit TN3270E header validation that fails closed; (6) 120 x 30
is the window, the reply decides the canvas, 120 x 27 is the expected result; (7) no batch, rebuild, source / CLIST
change or z/OS write.
Prepared (not executed): tools/zowe/zos5_live_check.py, tools/zowe/zos5_precheck.py (read-only), tests/zos5_fixture.py
+ tests/fixtures/zos5/ (synthetic session trace; the real x3270 4.5 output of a mid-session Trace(On) recorded against a
local fake TN3270E host, fake_tn3270e.py), test section 19; the procedure docs/zos5-live-session.md.
Finding from the local x3270 run: Trace(On) during a session writes a telnet-state replay and a dump of the current
screen as `<` lines before ` Data stream:` (no framing, no EOR); the checker reads data only after that marker, requires
each host block to follow `Host socket read complete nr=N` with N bytes, and audits the dump separately. x3270 4.5 with
a 120 x 27 oversize sends exactly tests/qreply_dyn.hex as its Query Reply (the expected-profile prediction).
