# MVS-RP RP.0 live run 2 (2026-10-12, user) - ESTAE recovery PASS, RP.0 CLOSED; startup `***` = D40
Trace `~/rp-estae-live2.txt` (outside the repository: it contains the logon), decoded host / terminal records.
Driver: deck RPE JOB 267 (no line output before FSON). The session was left by the user at the last `***` (18:37:52).

## Every program start in the trace
| # | Time | Command | What the wire shows | Result |
|---|---|---|---|---|
| 1 | 18:26:55 | RPESTAE E2 | E2 screen shown (no `***`), ENTER, `PACRPE ENDED DUE TO ERROR+` (EraseWriteAlternate, row 1), READY | recovery PASS |
| 2 | 18:30:31 | PACMAN RULES(ARCADE) | `7E C3`, query, reply, full screen; Q, end lines, READY | clean after E2 |
| 3 | 18:30:58 | RPESTAE E3 | screen, ENTER, line `RPE E3 LINE MODE RESTORED, FORCING 0C7` (row 1), abend message, READY | control PASS |
| 4 | 18:31:10 | PACMAN RULES(ARCADE) | 2 ms after the EXEC a blank line (row 5), 43 ms later `***`; ENTER; query; line-mode game, `***` again at QUIT | **startup `***`, line-mode fallback** |
| 5 | 18:32:12 | PACMAN RULES(ARCADE) | clean full screen | clean |
| 6 | 18:32:29 | RPESTAE E3 | as 3; then an empty ENTER (blank line + READY, normal TSO) | control PASS |
| 7 | 18:37:13 | RPESTAE E2 | as 1 | recovery PASS |
| 8 | 18:37:24 | PACMAN RULES(ARCADE) | clean full screen, a short real game (score 150), Q | clean after E2 |
| 9 | 18:37:42 | RPESTAE E3 | as 3 | control PASS |
| 10 | 18:37:52 | PACMAN RULES(ARCADE) | blank line + `***` (same as 4); left untouched | **reproduced** |

## Findings
- The startup `***` follows **every E3 (2 of 2) and no E2 (0 of 2 here)**. E3 is the control case: FSOF has
  already cancelled the PACFSIO ESTAE, so the recovery exit never runs in E3. The `***` therefore does not come from
  the recovery code.
- The common factor of every `***` start (live 1 after E2-with-a-line, live 2 after each E3): the program that
  abended had written **line-mode output** (COBOL DISPLAY to the terminal SYSOUT) before the abend. Abends without
  line output (E1 live 1, E2 live 2 twice) leave a clean session: the next game starts exactly like every earlier
  live trace (`7E C3` within 50 ms of the EXEC).
- Mechanism seen on the wire: on the next command TSO first writes a blank line (2 ms after the input, before PACMAN
  can be loaded), then, when PACMAN switches to full screen, protects that line-mode output with `***`. The ENTER that
  releases it is queued as program input and PACPLAT's capability query takes it as the reply (live 1 analysis):
  line-mode fallback. A later normal program end clears the condition (starts 5 and 8 clean).
- Recovery is proven: the exit restores line mode with the same wire shape as a normal FSOF end, the session stays
  usable, nested PACHSIO ESTAE handling is correct (E2 reads the HISCORE member first), and a game started after a
  recovered full-screen abend runs normally (twice).

## Conclusion
RP.0 (D39 section 7) PASS: E1 (live 1), E2 (live 2, twice, with clean relaunch), E3 control (live 2, twice). The
`***` / capability-query startup problem is a separate production weakness, recorded as **D40 startup hardening**
(open): it is triggered by line output pending at game start (here: an abended program's own output), not by the
ESTAE exit.
To leave the held session: press ENTER, then `Q` at `CMD (U/D/L/R/Q)?` (the line-mode game ends, READY).
