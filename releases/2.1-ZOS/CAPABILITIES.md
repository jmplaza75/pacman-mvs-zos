# PACMAN 2.1-zos - z/OS capability matrix
The 2.0-zos matrix (`releases/2.0-ZOS/CAPABILITIES.md`) applies unchanged: D46 changes the key decoding only, not a
terminal or platform capability. Rows added or confirmed again by ZOS-11 (attempt 3, installed release):

| Capability | z/OS status | Evidence |
|---|---|---|
| REALTIME Right on PF12 (AID X'7C') as an AID-only record, no ENTER | CONFIRMED live | ZOS-11 attempt 3 (PF12 x 2 placed as R by the 2.1 model) |
| PF11 and PF1-PF24 (others) ignored in REALTIME, none quits | CONFIRMED live | ZOS-11 attempt 3 (sweep, game wrote on after every AID) |
| Typed Q without ENTER: no inbound record, kept in the input field | CONFIRMED live | ZOS-11 attempt 3 (11 writes, 0 inbound during the hold) |
| COALESCED REALTIME on the installed release (CLASSIC, no PLAY / PRESENT operand) | CONFIRMED again | ZOS-11 attempt 3 (251 writes / 496 quanta = model) |
| Alternate size 120 x 27 (IBM-DYNAMIC) | CONFIRMED again | ZOS-11 live session |
| AMASPZAP dump of a program object | B_TEXT only; COBOL C_CODE not dumped (AMA152I) | PACZ11ZD JOB09560 |
