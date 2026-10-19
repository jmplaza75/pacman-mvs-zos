# ZOS-6 REALTIME - live session procedure (for review; not executed)

Executed 2026-10-19 (R1-T4, R2; both PASS, PRESENT(COALESCED)): docs/evidence/zos6-realtime.md. The text below is the
procedure as reviewed; the runs used the same steps with the trace names zos6-R1-T4.* and zos6-R2.*.

Design: docs/zos6-design.md (approved, commit 6609b9d, plus the final local hardening). Tools: tools/zowe/zos6_drive.py
(input driver), tools/zowe/zos6_live_check.py (acceptance authority). One c3270 / logon session, two immutable raw
traces (R1, R2). R2 runs ONLY after the frozen R1 trace got FUNCTIONAL PASS and TIMING PASS from the checker (RC 0,
`NEXT CASE ALLOWED: yes`). No remote precheck, no build / install / upload / JCL / job; the installed PACMAIN, CLIST and
CEEOPTS are used unchanged. No delete, no purge, no automatic retry; nothing outside Z00000.PACMAN.* is touched (never
Z00000.ZHEIST.*). Credentials are typed by the operator only: never stored, logged, scripted or sent by any tool.

## 0. Placeholders and local setup (operator's Mac; run the python commands from the project directory)
```
RAW=<raw-trace-dir>
```
```
PORT=<script-port>
```
`<raw-trace-dir>`: an existing directory OUTSIDE the repository. `<script-port>`: a fresh local port (4005 suggested).
Check that no c3270 is already using the port; if it is in use: STOP and choose another port (never kill a session):
```
pgrep -fl c3270
```
```
lsof -nP -iTCP:$PORT -sTCP:LISTEN
```
None of the eight files may exist (never overwritten, never deleted); any `EXISTS` line = STOP:
```
for f in zos6-R1.trace zos6-R1.trace.sha256 zos6-R1-drive.jsonl zos6-R1-gate.txt zos6-R2.trace zos6-R2.trace.sha256 zos6-R2-drive.jsonl zos6-R2-check.txt; do [ -e "$RAW/$f" ] && echo "EXISTS: $f"; done; echo checked
```

## 1. Terminal, logon, ISPF option 6 (no trace yet)
Window 120 x 30 before connecting; never resized while connected.
```
c3270 -model 2 -oversize auto -scriptport $PORT 198.51.100.200:623
```
Log on by hand (userid and password typed by the operator only), ISPF Primary Option Menu, option `6`. Then, from a
second Terminal tab, prove that x3270if is bound to THIS session and the shell is visible (must print 1; else STOP):
```
x3270if -t $PORT 'Ascii()' | grep -c 'ISPF Command Shell'
```

## 2. R1 - NORMAL (T = 150 ms)
Start the R1 trace and confirm it names the intended file (`Trace file is <raw-trace-dir>/zos6-R1.trace.`; else STOP):
```
x3270if -t $PORT "Trace(On,$RAW/zos6-R1.trace)"
```
```
x3270if -t $PORT 'Trace()'
```
Run the driver. It owns EVERY action of the case, including the EXEC: do not type the EXEC or any key yourself while
it runs (the driver starts only with the ISPF Command Shell on the screen, and the checker requires the EXEC + ENTER of
the driver as the only pre-game inputs).
```
python3 tools/zowe/zos6_drive.py --port $PORT --case R1 --log "$RAW/zos6-R1-drive.jsonl"
```
What the driver sends (each action after Wait(5,Unlock); the waits are driver scheduling, not timing criteria):
1. transition: `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO)'` (PARM
   `TSO AI0 1 NAAAPAAARNC01NP`); waits for ISPF's `***`; transition ENTER; waits for the game screen (<= 30 s);
2. 5 s (press-to-start: blocking read, no game writes); PF8 (start, down); 60 s running (the principal segment);
3. PF9 (pause); 60 s paused (no game writes); PF9 (resume); 10 s running;
4. `x` + ENTER (invalid); 3 s; PA2 (redraw); 3 s;
5. PF11 (right): Pac-Man runs into the still ghost, dies, exactly 10 death-stop quanta, respawns; the REALTIME loop keeps
   emitting quanta (Pac-Man stationary - not a blocking wait); 10 s after PF11: `Q` + ENTER while the loop is active;
6. closure: waits for the end lines and `***` (<= 60 s); closure ENTER; waits for the ISPF Command Shell (<= 60 s).
Success: the driver prints `ZOS-6 DRIVER R1: plan sent completely ...`. Any `ZOS-6 DRIVER STOP` = STOP (section 6):
no retry; keep the trace on only as long as needed to capture the resulting state, then `Trace(Off)` and freeze.

### R1 end and freeze (only after the driver's success message, still in the ISPF Command Shell)
```
x3270if -t $PORT 'Trace(Off)'
```
```
shasum -a 256 "$RAW/zos6-R1.trace" > "$RAW/zos6-R1.trace.sha256"
```
```
chmod a-w "$RAW/zos6-R1.trace" "$RAW/zos6-R1.trace.sha256" "$RAW/zos6-R1-drive.jsonl"
```
```
cat "$RAW/zos6-R1.trace.sha256"
```
Do not leave c3270; stay in the ISPF Command Shell.

### R1 gate (local, read-only, on the frozen files)
```
shasum -a 256 -c "$RAW/zos6-R1.trace.sha256"
```
```
python3 tools/zowe/zos6_live_check.py --case R1 --trace "$RAW/zos6-R1.trace" --drive-log "$RAW/zos6-R1-drive.jsonl" > "$RAW/zos6-R1-gate.txt" 2>&1; rc=$?; cat "$RAW/zos6-R1-gate.txt"; echo "RC=$rc"
```
```
chmod a-w "$RAW/zos6-R1-gate.txt"; shasum -a 256 -c "$RAW/zos6-R1.trace.sha256"
```
Meaning (exactly as implemented):
- RC=0 and the last line `NEXT CASE ALLOWED: yes`: R1 PASS (functional + timing); R2 may run.
- RC=2 (`R1: ENVIRONMENT/TIMING BLOCKED - ...`, `NEXT CASE ALLOWED: no`, possibly `(STOP)`): R2 MUST NOT run.
- RC=1 (`R1: FUNCTIONAL FAIL: ...`, `NEXT CASE ALLOWED: no`): R2 MUST NOT run.
Also STOP if the output lacks `NEXT CASE ALLOWED: yes`, a SHA-256 check is not OK, the output shows a Python exception,
or the plan / driver log / trace do not agree. RC 1 or 2 is never reinterpreted to proceed. If R1 is not PASS: no R2, no
retry, evidence preserved, STOP for analysis (go to section 7 to leave the session).
What the R1 output reports (no expected values are prescribed): principal segment quanta (>= 200), mean period, median,
p95 / max gap, endpoint drift and trend (a live proxy, not the host-side drift), BID count / latency, keyboard-locked
fraction (if derivable), the pause (no game writes is part of the model match), the first five post-resume gaps, the
death stop (exactly 10 quanta; observed wall duration), the end lines, `***`, the shell, PF8 / PF11 directional lines.

## 3. R2 - FAST (T = 125 ms), only after the R1 gate said PASS / NEXT CASE ALLOWED
Same c3270 / logon session, ISPF Command Shell on the screen (the check must print 1), R2 files still absent:
```
x3270if -t $PORT 'Ascii()' | grep -c 'ISPF Command Shell'
```
```
for f in zos6-R2.trace zos6-R2.trace.sha256 zos6-R2-drive.jsonl zos6-R2-check.txt; do [ -e "$RAW/$f" ] && echo "EXISTS: $f"; done; echo checked
```
```
x3270if -t $PORT "Trace(On,$RAW/zos6-R2.trace)"
```
```
x3270if -t $PORT 'Trace()'
```
```
python3 tools/zowe/zos6_drive.py --port $PORT --case R2 --log "$RAW/zos6-R2-drive.jsonl"
```
No manual input. The driver sends:
1. transition: `EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO) SPEED(FAST)'` (PARM
   `TSO AI0 1 NAAAPAAARNC01FP`); `***`; transition ENTER; the game screen;
2. 2 s (pre-start); PF11 (start); 5 s; PF8; 2 s; PF7; 2 s; PF10;
3. the clean 30-second principal FAST segment (no driver input);
4. `Q` + ENTER while running; closure: end lines, `***`, closure ENTER, ISPF Command Shell.
Directional coverage (the checker, not the driver, is the authority): PF7 -> AID F7 -> U, PF8 -> AID F8 -> D,
PF10 -> AID 7A -> L, PF11 -> AID 7B -> R (R1 adds PF8 and PF11 again).
After the driver's success message:
```
x3270if -t $PORT 'Trace(Off)'
```
```
shasum -a 256 "$RAW/zos6-R2.trace" > "$RAW/zos6-R2.trace.sha256"
```
```
chmod a-w "$RAW/zos6-R2.trace" "$RAW/zos6-R2.trace.sha256" "$RAW/zos6-R2-drive.jsonl"
```
```
cat "$RAW/zos6-R2.trace.sha256"
```

### R2 final check (local, read-only)
```
shasum -a 256 -c "$RAW/zos6-R2.trace.sha256"
```
```
python3 tools/zowe/zos6_live_check.py --case R2 --trace "$RAW/zos6-R2.trace" --drive-log "$RAW/zos6-R2-drive.jsonl" > "$RAW/zos6-R2-check.txt" 2>&1; rc=$?; cat "$RAW/zos6-R2-check.txt"; echo "RC=$rc"
```
```
chmod a-w "$RAW/zos6-R2-check.txt"; shasum -a 256 -c "$RAW/zos6-R2.trace.sha256"
```
RC=0 with `R2: PASS` is required. RC=2: ENVIRONMENT/TIMING BLOCKED, ZOS-6 stays OPEN. RC=1: FUNCTIONAL FAIL, ZOS-6
stays OPEN. No retry. (The checker prints a `NEXT CASE ALLOWED` line for every case; after R2 there is no next case.)
What the R2 output reports: principal segment quanta (>= 200, after PF10), mean, median, p95 / max, BID count / latency,
the FAST keyboard-locked fraction, the four-layer lines of PF11 / PF8 / PF7 / PF10 (action, send time, AID byte, write,
window, model direction), the end lines, `***`, the shell.

## 4. Phase result
ZOS-6 closes only with R1 PASS (RC 0) and R2 PASS (RC 0). ENVIRONMENT/TIMING BLOCKED or FUNCTIONAL FAIL in either case
leaves ZOS-6 open; no tolerance change, no CONTENTION-RESOLUTION change, no rebuild or reinstall follows automatically.

## 5. What is never done
No rebuild, reinstall, upload, job, dataset change; no tolerance change; no disabling of CONTENTION-RESOLUTION; no
oracle or source edit; no automatic retry; no manual key while a driver runs; no overwrite or deletion of a raw file.

## 6. STOP (immediately; no retry; freeze what exists)
- `Ascii()` does not show `ISPF Command Shell` (wrong session bound, or not in option 6);
- a raw file already exists, or `Trace()` does not name the intended file;
- the driver prints `ZOS-6 DRIVER STOP` (timeout, error, keyboard locked > 5 s, an action not delivered, IKJ / IEC /
  IGZ / CEE / ABEND / PACMAN: on the screen, the game in line mode, no game screen / `***` / shell in time);
- the terminal returns to line mode unexpectedly, or c3270 disconnects;
- the checker reports FUNCTIONAL FAIL or ENVIRONMENT/TIMING BLOCKED, or the R1 output lacks `NEXT CASE ALLOWED: yes`;
- a trace / checker inconsistency, or a `shasum -c` that is not OK after freezing.
After a STOP: if the trace is still on, `Trace(Off)`; freeze (shasum + chmod a-w) whatever exists; then section 7.

## 7. Leaving the session
Only after the R2 trace is frozen and checked, or after a STOP with its evidence frozen: in the ISPF Command Shell,
leave ISPF normally (`=X`, log disposition as usual), which ends the session on this logon procedure.

## 8. Security
Raw traces, driver logs and the gate / check outputs stay in `<raw-trace-dir>`, outside git, until audited. Evidence
committed later holds only audited derived information and SHA-256 values: never a raw trace, a raw driver log, ISPF
command history, unrelated session content or a personal absolute path.
