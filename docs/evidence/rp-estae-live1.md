# MVS-RP RP.0 live run 1 (2026-10-12, user) - recovery PASS for E1/E2, RP.0 NOT closed
Trace `~/rp-estae-live.txt` (18:06:49-18:10:19, outside the repository: it contains the logon), decoded host /
terminal records (EBCDIC). Build: deck RPE JOB 266.

## Timeline from the trace
| Time | Direction | Record | Meaning |
|---|---|---|---|
| 18:07:14.426 | in | EXEC RPESTAE CASE(E1) | E1 |
| 18:07:14.454 | out | Write, clear prefix, the 5 E1 lines | PACRPE full screen (FSON + SEND); its DISPLAY line never reached the wire |
| 18:07:22.319 | in | ENTER (unformatted screen: AID + buffer text) | RECV returns, 0C7 forced |
| 18:07:22.323 | out | EraseWriteAlternate, row 1 `PACRPE   ENDED DUE TO ERROR+` | ESTAE exit ran: line mode, fresh screen (STLINENO 1) - same shape as a normal FSOF end |
| 18:07:22.324 | out | `READY` | TMP back |
| 18:07:53 | in/out | `TIME` -> TIME line, READY | terminal usable |
| 18:08:34 | in/out | empty ENTER -> READY | |
| 18:08:35.674 | in | EXEC RPESTAE CASE(E2) | E2 |
| 18:08:35.709 | out | line `RPE CASE E2 START` | the driver's DISPLAY reached the wire (PACHSIO I/O ran before FSON) |
| 18:08:35.712 | out | `***` | TSO holds the screen: line output written before the full-screen switch |
| 18:08:39.719 | in | ENTER | taken by PACRPE's RECV (TGET); the held E2 screen was never sent |
| 18:08:39.720 | out | EraseWriteAlternate `PACRPE   ENDED DUE TO ERROR+`, READY | ESTAE exit ran, line mode restored |
| 18:09:07.418 | in | EXEC PACMAN 'RULES(ARCADE)' | game |
| 18:09:07.422 / .464 | out | a blank line (row 4), then `***` (row 5) | NOT the normal start: in every earlier live trace (gp1-live, hs-live) the first record after EXEC is `7E C3` (EraseWriteAlternate, PACPLAT TRY-COLOUR) |
| 18:09:30.252 | in | ENTER (AID 7D, cursor, no data) | the user's ENTER for `***` |
| 18:09:30.258 | out/in | Read Partition Query; Query Reply 184 bytes | reply byte for byte the normal c3270 reply |
| 18:09:30.263 | out | line-mode header, board, `CMD (U/D/L/R/Q)?`, `INVALID COMMAND A`, `INVALID COMMAND X` | TSO line mode (fallback) |
| 18:09:51-18:10:05 | | QUIT, end lines (HIGH SCORE 0001430, not rewritten), LISTALC, LOGOFF | clean |
E3 does not appear in this trace (no `CASE(E3)` input between 18:06:49 and 18:10:19).

## Answers
1. Sequence: E1 = screen, ENTER, 0C7, exit, `ENDED DUE TO ERROR+`, READY. E2 = (PACHSIO READ), line, `***`, ENTER
   consumed by the driver's TGET, 0C7, exit, `ENDED DUE TO ERROR+`, READY; the E2 screen was never shown. E3: not run
   in this session.
2. There is no FSOF in E1/E2 (by design: the abend comes first). The exit's restore is visible: TSO's next write is an
   EraseWriteAlternate at row 1 followed by READY, the same shape as the normal end of every game (FSOF). E1 is fully
   clean (TIME, empty ENTER and E2's EXEC were all normal input/output cycles).
3. The `***` after the game's EXEC is TSO holding output: a blank line was written (row 4) and the hold followed
   before PACPLAT's `7E C3` could go out. The same hold had just happened inside E2, caused by the driver itself
   (a line written before the full-screen switch, a test-driver defect, fixed below). The trace cannot show TSO's
   internal state; the most likely reading is a TSO output-hold residue left by an abend that happened WHILE output
   was held (E2), not the restore code: E1, with no hold, left nothing behind.
4. Yes. The user's ENTER for the `***` was queued as program input; nothing from the recovery path itself was pending
   (E1/E2's ENTERs were consumed by the driver's own TGET, and FSON clears the input queue).
5. PACPLAT TRY-COLOUR's QRY read the first inbound record after the query: the ENTER (AID 7D + cursor), not the
   Query Reply (AID 88). PACQRY found no colour, so HAS-COLOUR = 0.
6. HAS-COLOUR = 0 -> FSOF -> TSO line mode (the documented fallback). The real Query Reply was then read by the
   line-mode game as commands: its first data byte X'81' is `a` (-> `A`), and a later chunk starts in the `x3270` RPQ
   name part (-> `X`): `INVALID COMMAND A`, `INVALID COMMAND X`.
7. Classification: the recovery code is not proven defective (E1 clean, E2 restored). The relaunch failure is a TSO
   output-hold interaction triggered by a test-sequencing / test-driver defect (line output before FSON in E2), and it
   exposed a separate latent production weakness: the colour query accepts any inbound record as the reply
   (independent of RP.0; a `***` or a stray key at game start always causes the line-mode fallback).

## Fix and retest
- PACRPE: no line output before FSON (DISPLAY only in the not-a-TSO-session path). Deck RPE JOB 267 PASS (same steps,
  no warnings, both batch steps S0C7). Only LOAD(PACRPE) and CLIST(RPESTAE) were replaced; the game is untouched.
- Retest: docs/evidence/rp-estae-checklist.md, section "Retest after live 1".
