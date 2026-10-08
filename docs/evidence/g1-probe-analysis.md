# MVS-G1 capability probes - analysis log
## Probe 1 (PACG1P/PACFS, JOB 149) - live result reported by the user (2026-10-07)
`G1 RC =0000 LEN =0001` after the Read Partition Query, `G1 USABLE AREA W =0000 H =0000`, then for the colour demo
`G1 RC =0000 LEN =0000`, no colour screen seen, back to READY.
Reading of the result:
- Both TPUTs returned RC 0, so TSO accepted them; the TGET after the demo returned **0 bytes immediately** (it did not
  wait for ENTER). The probe then issued STFSMODE OFF / STLINENO LINE=1 and line-mode output, which repaints the screen:
  a full-screen image shown for milliseconds is invisible. So probe 1 cannot tell whether the 3270 stream was displayed.
- The query TGET returned 1 byte: not a Query Reply (a reply starts with AID X'88' followed by structured fields).
  Either the WSF did not reach the terminal or the reply is not routed to TGET on this TSO/VTAM.
- Probe 1 mixed several unknowns (WSF, extended orders SA/SF, TGET timing): it is replaced by single-hypothesis probes.
## Environment discrepancy found
The running emulator is the TK4- bundled **Hercules 4.00 (build 2016-06-25, x86_64 under Rosetta)**,
`~/mainframe/tk4/hercules/darwin/bin/hercules`, not Homebrew Hercules 4.9.1 (installed but not used by `start_herc`).
Its tn3270 server (hdt3270) is plain TN3270 (TERMINAL-TYPE, BINARY, EOR; no TN3270E), terminal type 3279 accepted.
## Probe 2 (PACG1Q/PACFS2, JOB 150) - hypothesis H1
A plain screen (no SA/SF/SFE orders, no WSF) sent with TPUT FULLSCR after STFSMODE ON is displayed, and TGET ASIS can
wait for ENTER once stale input is flushed (TCLEARQ INPUT) and TGET is re-issued while it returns no data (0.5 s
pause, at most 60 tries). Batch run: RC 4, nothing issued. Live result: pending.

## Probe 2 - live result reported by the user (2026-10-07)
No full-screen image appeared; the screen showed TSO line-mode output and `***`. After ENTER:
`G1Q RC=0000 LEN=0001 TGETS=0001 DATA=6E40404040404040`.
Reading: TPUT FULLSCR returned RC 0 but TSO was still in the `***` state (line-mode output pending: the probe's own
DISPLAY plus what was already on the screen). TSO gives line-mode output priority; when ENTER cleared `***`, the single
inbound byte X'6E' is the PA2 AID, which TSO/VTAM full-screen support uses as the "reshow" signal (STFSMODE RSHWKEY,
default PA2): the program is expected to send its whole screen again and read again. The probe returned instead.
So probe 2 shows a protocol gap in the probe (no reshow handling, screen not clean before STFSMODE), not yet a
limitation of the route.

## Is there another route? (investigation, no new probe)
- TSO full-screen via TPUT FULLSCR/NOEDIT + TGET ASIS + STFSMODE/STLINENO/STTMPMD is the standard route on MVS 3.8J and
  TK4- ships applications built on it: `LISTDS 'SYS2.CMDLIB' MEMBERS` (JOB 152, evidence g1-tso-cmdlib-list.txt) lists
  RFE, RPF, REVIEW, QUEUE and PDS. If they run full-screen in our c3270 session, the route is usable here and the gap is
  in the probe protocol. ZP60009 (STFSMODE NOEDIT) is installed, which these tools use for unedited 3270 streams.
- Alternative 1, direct device I/O: the 3270s 03C0-03C7 (Hercules group TCAM, not owned by VTAM) can be driven with
  EXCP from a batch job (Erase/Write, WSF Read Partition Query, Read Modified CCWs), bypassing TSO and VTAM; c3270 can
  attach to that group (`c3270 TCAM@localhost:3270`). Gives full datastream control; needs those devices online to MVS
  and not started by TCAM. Kept as fallback.
- Alternative 2, own VTAM application (ACB, OPNDST, SEND/RECEIVE): heavier, needs a VTAM APPL definition (system
  change) - not proposed.
- TCAM application programs: TCAM is not used by this installation's TSO - not proposed.
## Next minimal experiment (E1, no new code)
Run existing full-screen tools in c3270 (RPF, REVIEW) and note: full-screen yes/no, colours/highlighting yes/no.
Outcome decides between: E2 = probe 2 + reshow handling (TSO route), or the direct-EXCP fallback.

## E1 - live result reported by the user (2026-10-07)
RPF runs as a real full-screen 3270 application in c3270: fixed layout, no line output, no `***`, several distinct
colours (white, green, turquoise, red) and intensified fields. Conclusion: the TSO full-screen route and the extended
colour/attributes of c3270 work in this environment; probes 1-2 failed because of their own protocol.
## E2 - probe 2 corrected (JOB 153), still plain (no colour), one hypothesis
Nothing is printed before the full-screen part; TCLEARQ OUTPUT/INPUT; STFSMODE ON,INITIAL=YES + STTMPMD ON; the screen
is sent again whenever TGET returns PA2 X'6E' (reshow) or CLEAR X'6D' (max 10 screens); empty reads are retried
every 0.5 s (max 60); then STTMPMD OFF, STFSMODE OFF, STLINENO LINE=1. Reports screens sent and the AID of every
inbound. Batch run: RC 4, nothing issued. Live result: pending.
E2 live result (user, 2026-10-07): the plain full-screen appeared, stayed until ENTER, no `***`;
`G1Q RC=0000 LEN=0003 SCRNS=0001 DATA=7DC8C14040404040`, `G1Q AIDS=7D00000000000000`, back to READY.
AID X'7D' (ENTER) + cursor address C8C1 (12-bit) received: the TSO full-screen route works with our protocol.
The PA2/CLEAR reshow branch was not exercised yet (pending, must be tested before G1 closes - D12).
## E3 - one extended capability (JOB 154): same protocol, PARM 'C' selects a screen with ONE SA order
X'2842F2' (foreground red) on row 7, reset by X'280000'; rows 5, 9, 11 default. Batch: RC 4, nothing issued.
Live result: pending (CLIST G1PROBE3).
E3 live result (user, 2026-10-07): row 7 red, other rows green (default), no `***`; PA2 pressed twice redrew the screen;
`G1Q RC=0000 LEN=0003 SCRNS=0003 DATA=7D40404040404040`, `G1Q AIDS=6E6E7D0000000000`.
CONFIRMED: TSO full-screen, real AIDs, PA2 reshow (twice), extended foreground colour via one SA order, no paging.
## E4 - full 7-colour palette (JOB 155): same protocol, PARM 'K' screen with one SA X'2842Fn' order per row
(F1 blue, F2 red, F3 pink, F4 green, F5 turquoise, F6 yellow, F7 white) plus one default row; the CLEAR reshow branch is
exercised in this test. Batch: RC 4, nothing issued. Live result: pending (CLIST G1PROBE4).
Remaining G1 experiments after E4, one at a time: E5 colour detection (Read Partition Query sent with TPUT NOEDIT,
reply read with TGET ASIS: expects AID X'88' and the colour query code X'86'); then the G1 renderer design.
Highlighting (reverse, blink, underscore, intensify) belongs to G2 and is not probed in G1.
E4 live result (user, 2026-10-07): all seven colours shown correctly (blue, red, pink, green, turquoise, yellow,
white), default green, no `***`. CLEAR blanked the screen and was NOT passed to the program
(`SCRNS=0001`, `AIDS=7D...`): on this TSO/VTAM + c3270 setup CLEAR is handled by TSO, not delivered as AID X'6D'.
PA2 (X'6E') is the validated redraw key; after CLEAR the user must press PA2 to get the screen back.
## E5 - colour detection (JOB 156), one hypothesis
After the E2-protocol plain screen, a Read Partition Query (WSF X'F3', length 5, X'01', PID X'FF', X'02') is sent with
TPUT NOEDIT; the terminal's Query Reply (AID X'88' + structured fields X'81' qq) should arrive at the next TGET ASIS
without user action. The probe prints 96 bytes of the inbound, the query codes found (86 = colour, 87 = highlighting,
85 = character sets / symbol sets, 81 = usable area, 88 = reply modes, A6 = implicit partition) and the usable area.
If no reply arrives the screen stays and ENTER returns AID 7D. Batch: RC 4. Live result: pending (CLIST G1PROBE5).
E5 live result (user, 2026-10-07): the Query Reply arrived without user action.
`G1Q RC=0000 LEN=0180 SCRNS=0001 DATA=88000E8180808184`, `G1Q AIDS=8800000000000000`,
`G1Q CODES=80 81 84 85 86 87 88 95 A1 A6`, `G1Q AREA W/H=0080/0024`.
Decoded query codes: 80 summary, 81 usable area (80 x 24), 84 alphanumeric partitions, 85 character sets,
86 colour, 87 highlighting, 88 reply modes, 95 DDM (file transfer), A1 RPQ names, A6 implicit partition.
CONFIRMED: automatic capability detection works (TPUT NOEDIT WSF + TGET ASIS), the terminal announces colour and
highlighting, screen is 80 x 24 (model 2 size). Not announced: no graphics/GDDM-related replies.
Character sets (85) is announced; whether loadable symbol sets (Programmed Symbols) are offered is in that reply's
content, not yet decoded (G5).

## G1 live validation 1 (user, 2026-10-08) and the clean-screen fix
TSC worked (all palette elements, moves, INVALID COMMAND in red, Q restores line mode: TURNS 004, SCORE 0020, LIVES 3,
READY) but the first screen kept remnants of the previous TSO screen (`*** TSO Applications Menu terminated. ***`,
`READY`, the EXEC line). Cause: TPUT FULLSCR sends the stream as a plain Write, which keeps the old buffer content.
Fix (PACFSIO SEND only): the stream is sent with TPUT NOEDIT preceded by the 3270 command X'F5' Erase/Write (NOEDIT
transport validated by probe E5), so every TSC screen starts from a clean buffer. PACSCR output, TSD dry runs and the
model are unchanged. JOB 159: 54 steps RC 0000, oracle unchanged, 88 TSC screens identical to the model.
## G1 live validation 2 (user, 2026-10-08): Erase/Write via NOEDIT -> black screen; corrected (JOB 160)
Byte comparison of the transmitted stream (PACSCR output unchanged in every build):
- before JOB 159: TPUT FULLSCR, data = C3 11 40 40 1D 60 ... (len N): visible, with remnants of the TSO screen;
- JOB 159: TPUT NOEDIT, data = F5 C3 11 40 40 1D 60 ... (len N+1): screen erased, then black - the following
  write was not rendered on this TSO/VTAM + Hercules 4.00 local-3270 path, although a 6-byte NOEDIT WSF query works;
- JOB 160: TPUT FULLSCR (the proven transport), data = C3 11 40 40 3C 40 40 00 11 40 40 1D 60 ... (len N+7): after
  the WCC, SBA(1,1) + Repeat-to-Address (1,1) with X'00' nulls the whole buffer (stop address = current address
  fills every position), then the unchanged screen. Only PACFSIO SEND changed.
JOB 160: 54 steps RC 0000, oracle unchanged, 88 TSC screens identical to the model. Live check pending.
## G1 live validation 3 (user, 2026-10-08): JOB 160 also black -> root cause found
Root cause of BOTH black screens (JOB 159 and JOB 160) is one assembler bug in PACFSIO SEND, not the clearing idea:
the length was computed with `LH 0,0(4)` followed by `LA 0,1(0)` (JOB 159) / `LA 0,7(0)` (JOB 160). In S/370 a base
register 0 means "no register", so LA set R0 to the constant 1 / 7: TSO received only the first 1 byte (X'F5': erase,
nothing else) or the first 7 bytes (WCC + SBA + start of the clear prefix) - hence an erased, black screen.
Fix (JOB 161): `AH 0,=H'7'` (length + 7). The transport is the proven TPUT FULLSCR; the single hypothesis under test is
the clear-buffer prefix SBA(1,1) + RA to (1,1) with X'00'. PACSCR, palette, model, core unchanged.
If the clean screen still fails live, fall back to the JOB 157 send (visible, with TSO remnants) and document it.
## G1 live validation 4 (user, 2026-10-08): JOB 161 PASSED
TSC start screen visible, in colour and completely clean (no READY/EXEC/`***`/TSO menu remnants); R -> `T001 R MOVED`,
S=0010, L=097, screen still clean; Q -> line mode: QUIT, TURNS 001, SCORE 0010, LIVES 3, READY.
Earlier live checks on the JOB 157 build (same renderer, before the clean-screen fix): palette of every element,
3 ghost colours, R R D L, INVALID COMMAND X in red, PA2 redraw, Q with line mode restored, COLOR(NO) fallback request.
NOT validated live: the ESTAE abend-restore exit in PACFSIO (implemented; an abend could not be provoked safely).
