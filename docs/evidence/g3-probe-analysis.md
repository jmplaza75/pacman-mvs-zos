# MVS-G3 partial-redraw transport probe (E6) - analysis (2026-10-08)
Probe PACG3P + PACFS3 (src/probe), build JOB 167 (docs/evidence/g3-probe-build.txt), CLIST G3PROBE, run live in c3270.
Hypothesis: after a TPUT FULLSCR screen, a second TPUT carrying only WCC + SBA + a few cells changes just those cells.
Eight updates, 0.5 s apart, two cells (row 7 col 10 C/O, col 20 G/W) with SA colour + SA highlight (reverse).
| Variant | Transport | Result (user, live) |
|---|---|---|
| A | TPUT ASIS, data starts with WCC | RC 0, 8 updates, cells alternate, but the REST OF THE SCREEN IS ERASED (TSO prepends Erase/Write). `G3P V=A RC1=0000 RC2=0000 NPART=0008 AID=7D`. Discarded. |
| W | TPUT NOEDIT, data = X'F1' (Write) + WCC + orders | VALIDATED: rest of the screen intact (blue and white static lines kept), cells alternate, no global flicker. `G3P V=W RC1=0000 RC2=0000 NPART=0008 AID=7D`. |
| N | TPUT NOEDIT without command byte | not run: not needed to decide (kept only as optional contrast). |
Decision (D27): partial redraw = explicit 3270 Write command X'F1' as first byte + TPUT NOEDIT (service SENP in PACFSIO).
