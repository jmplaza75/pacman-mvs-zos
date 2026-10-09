# MVS-GS geometry question - probe E12 (alternate screen size) - COMPLETE
Probe: src/probe/PACGEP.cob + src/probe/PACFSC.asm + CLIST GEPROBE, deck `GEP` (job PACGEP01). Isolated from PACMAN
(PACFSIO, GAME/MAP/AI untouched). Builds: JOB 202 (runs A0 and A); JOB 203 = the same probe with two cosmetic ruler
fixes (every 9 of the units ruler was blank: one-digit counter overflow; rows 5..H-1 had no number: loop limit
overwritten) - geometry logic unchanged. Evidence of the build: docs/evidence/gs-e12-probe-build.txt.
Steps: S0 (FULLSCR) - Read Partition Query (NOEDIT) - S1 (FULLSCR, sizes) - S2 Erase/Write Alternate (NOEDIT X'7E') of a
ruler screen of exactly the announced alternate size + after 1 s a partial Write (X'F1') on the last rows; ENTER: the
cursor address is decoded in the alternate geometry - S3 Erase/Write (X'F5') back to the default size - line mode.

## Four layers (c3270 4.5ga6 source c3270/screen.c, traces)
1. macOS window: chosen by the user, any time.
2. c3270 curses viewport: laid out from the window; SIGWINCH -> resizeterm; smaller than the model needs -> "won't fit"
   error; the 3270 canvas is drawn from the top-left (no centring).
3. Negotiated model: decided ONCE at connect (TERMINAL-TYPE). c3270 silently lowers it when the window cannot hold the
   requested model at startup (run A0: `-model 4` in a 120x30 window sent `IBM-3279-2-E`). Never renegotiated on resize.
4. Query Reply default / alternate size: follows the negotiated model; fixed for the connection.

## Run A0 - `c3270 -model 4`, window 120 x 30 (too small) - 2026-10-09
Trace ~/gs-geo-m4.txt: header "Model 3279-4-E, 43 rows", but `SENT SB TERMINAL TYPE IS IBM-3279-2-E` (downgraded by c3270).
`GEP QLEN=0180 DEF=080X024 ALT=080X024 USABLE=080X024`
`GEP EWA-RC=0000 PART-RC=0000 EW-RC=0000 AID=7D CURSOR=024,076 EXPECT=024,076`
=> the host/TSO/VTAM path accepts Erase/Write Alternate, partial Write and Erase/Write (all RC 0, trace shows the EWA
   records); the alternate size stayed 80x24 only because c3270 had negotiated a model 2.

## Run A - `c3270 -model 4`, window >= 46 rows - LIVE PASS (2026-10-09)
Script port during S2: `TerminalName IBM-3278-4-E`, `ScreenSizeCurrent rows 43 columns 80`, `ScreenSizeMax rows 43
columns 80`, `Cursor1 row 43 column 76 offset 3435`, formatted. User: 
`GEP QLEN=0180 DEF=080X024 ALT=080X043 USABLE=080X043`
`GEP EWA-RC=0000 PART-RC=0000 EW-RC=0000 AID=7D CURSOR=043,076 EXPECT=043,076`
- 80x43 alternate geometry: LIVE PASS (row 43 and column 80 addressable, partial Write in the alternate size, inbound
  cursor address decoded correctly in 80x43, Erase/Write back to 80x24 and READY normal).
- Resize below the model's required viewport during the session, then enlarge again: FAIL / unsupported operational
  scenario - the curses display stays corrupted/misaligned. A c3270 curses/UI constraint, not a host or renderer fault.
  Operational requirement: the terminal must be large enough BEFORE connecting and must not be shrunk below the
  negotiated model during the session.
Capture (x3270if Ascii, during S2; JOB 202 build, so rows 5-41 carry no number and every 9 of row 2 is blank):
```
01| E12 ALTERNATE 080X043 VIA ERASE/WRITE ALTERNATE. RULERS: ROWS 2-3
02|12345678 012345678 012345678 012345678 012345678 012345678 012345678 012345678 0
03|         1         2         3         4         5         6         7         8
04|04                                                                             <
05|
06|
07|
08|
09|
10|
11|
12|
13|
14|
15|
16|
17|
18|
19|
20|
21|
22|
23|
24|
25|
26|
27|
28|
29|
30|
31|
32|
33|
34|
35|
36|
37|
38|
39|
40|
41|
42|   PARTIAL WRITE (XF1) IN ALTERNATE SIZE: OK IF READABLE
43|43 LAST ROW  PART                                                  ENTER>
```

## Run B - `c3270 -model 5`, window >= 30 x 132 - LIVE PASS (2026-10-09, JOB 203 build)
Trace ~/gs-geo-m5.txt: `SENT SB TERMINAL TYPE IS IBM-3278-5-E` (no downgrade). Script port during S2: `TerminalName
IBM-3278-5-E`, `ScreenSizeCurrent rows 27 columns 132` (= max), `Cursor1 row 27 column 128 offset 3559`, formatted.
The final GEP lines were not transcribed; the trace shows the ENTER on the alternate screen at `> Enter(27,128)` (= the
expected field, W-4) followed by the probe's Erase/Write. 132 columns and row 27 addressable (highest address 3563 <
4096: 12-bit addressing suffices), partial Write on row 26 in the alternate size.
Capture (x3270if Ascii, during S2; the tens ruler prints the tens digit modulo 10):
```
01| E12 ALTERNATE 132X027 VIA ERASE/WRITE ALTERNATE. RULERS: ROWS 2-3
02|123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012
03|         1         2         3         4         5         6         7         8         9         0         1         2         3
04|04                                                                                                                                 <
05|05                                                                                                                                 <
06|06                                                                                                                                 <
07|07                                                                                                                                 <
08|08                                                                                                                                 <
09|09                                                                                                                                 <
10|10                                                                                                                                 <
11|11                                                                                                                                 <
12|12                                                                                                                                 <
13|13                                                                                                                                 <
14|14                                                                                                                                 <
15|15                                                                                                                                 <
16|16                                                                                                                                 <
17|17                                                                                                                                 <
18|18                                                                                                                                 <
19|19                                                                                                                                 <
20|20                                                                                                                                 <
21|21                                                                                                                                 <
22|22                                                                                                                                 <
23|23                                                                                                                                 <
24|24                                                                                                                                 <
25|25                                                                                                                                 <
26|26 PARTIAL WRITE (XF1) IN ALTERNATE SIZE: OK IF READABLE                                                                           <
27|27 LAST ROW  PART                                                                                                      ENTER>
```

## Run C0 - `c3270 -model 3`, window 120 x 30 (too small) - INVALID for model 3
`SENT SB TERMINAL TYPE IS IBM-3279-2-E` (downgraded by c3270); `ALT=080X024 ... CURSOR=024,076`, all RCs 0000.

## Run C - `c3270 -model 3`, window >= 36 rows - LIVE PASS (2026-10-09)
Trace: `SENT SB TERMINAL TYPE IS IBM-3279-3-E`; script port before logon: max 32 x 80. User:
`GEP QLEN=0180 DEF=080X024 ALT=080X032 USABLE=080X032`
`GEP EWA-RC=0000 PART-RC=0000 EW-RC=0000 AID=7D CURSOR=032,076 EXPECT=032,076`
80x32 fully addressable (row 32, column 80), partial Write in the alternate size, Erase/Write back to 80x24, no
downgrade, no corruption in normal operation.

## Finding: TK4- TSO itself runs line mode in the ALTERNATE size (all traces)
At logon VTAM/TSO send their own Read Partition Query and then Erase/Write Alternate: model 5 `EraseWriteAlternate ...
SetBufferAddress(27,132)` (trace line 722), model 3 `(32,80)`, model 4 (GS live session of 2026-10-09 11:00,
~/gs-live-trace.txt) `(43,80)`; a model 2 session gets a plain Erase/Write. After the probe's Erase/Write back to 80x24,
TSO's next output is again Erase/Write Alternate. Consequences:
- PACMAN's TSC screens are sent by TPUT FULLSCR, which arrives as a Write (E6): they inherit whatever size TSO left.
  Models 3 / 4: the width is 80, the clear prefix nulls the whole (larger) buffer, so the 80x24 layout is correct at the
  top and the extra rows stay empty (the "anchored" look seen live). Model 5: the buffer is 132 wide, so the 80-column
  addresses land on the wrong cells - the G1-GS screens would be garbled (E12 S0 shows it: the 80x24 field at offset
  1915 came back as `Enter(15,68)` in 132 columns). LATENT DEFECT for model 5, not seen before because every live check
  ran on model 2 or 4. Fixing it needs an explicit Erase/Write (or Erase/Write Alternate) from PACMAN = a new PACFSIO
  send op (decision for the user; PACFSIO untouched so far).

## Run D - `c3270 -model 2 -oversize auto`, usual window 120 x 30 - LIVE PASS (2026-10-09)
Trace ~/gs-geo-ov.txt: `SENT SB TERMINAL TYPE IS IBM-DYNAMIC`; script port before logon: current 24 x 80, max 27 x 120
(the 120 x 30 window minus the c3270 menu bar and OIA lines). User:
`GEP QLEN=0180 DEF=080X024 ALT=120X027 USABLE=120X027`
`GEP EWA-RC=0000 PART-RC=0000 EW-RC=0000 AID=7D CURSOR=027,116 EXPECT=027,116`
IBM-DYNAMIC is accepted by Hercules / VTAM / TSO; the 120 x 27 alternate buffer is real (row 27 and column 120
addressable, 3240 cells: 12-bit addressing), partial Write works in it, the cursor address is decoded correctly, and
Erase/Write returns cleanly to 80 x 24.

## Summary (geometry study COMPLETE)
| Session | Negotiated name | Alternate | Live |
|---|---|---|---|
| model 2 (or any model c3270 downgrades) | IBM-3279-2-E | 80 x 24 | protocol path PASS |
| model 3, window >= 36 rows | IBM-3279-3-E | 80 x 32 | PASS |
| model 4, window >= 46 rows | IBM-3278-4-E | 80 x 43 | PASS; shrinking the window mid-session: FAIL (c3270 curses) |
| model 5, window >= 30 x 132 | IBM-3278-5-E | 132 x 27 | PASS |
| oversize auto, window 120 x 30 | IBM-DYNAMIC | 120 x 27 | PASS |
The geometry is fixed at connect time by c3270 (from the window size it sees then); resizing never renegotiates.
