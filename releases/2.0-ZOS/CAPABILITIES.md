# PACMAN 2.0-zos - z/OS capability matrix
Copied from docs/evidence/zos9-equivalence.md section 15 (ZOS-9 I5, accepted evidence only); the last row updated by
ZOS-10 (S10). MVS column: releases/2.0-MVS-MAX/CAPABILITIES.md (unchanged). NOT TESTED = no accepted z/OS evidence.
Path: IBM Z Xplore TSO / VTAM / TN3270E, c3270 4.5ga6 `-model 2 -oversize auto`, 120 x 30 window.

| Capability | z/OS status | Evidence / decision |
|---|---|---|
| 3270 model / screen size | CONFIRMED 80 x 24 | ZOS-5 C (Erase/Write 80 x 24, writes = model) |
| Alternate screen size | CONFIRMED 120 x 27 live; 80x32 / 80x43 / 132x27 / 100x25 / 160x30 layouts exact on simulated buffers only, not negotiated live (not offered on this path) | ZOS-5 A / B; ZOS-3 TD (T), ZOS-6 N5 / F5, PACZ9E1 / E2 (X, M, U, L) |
| Canvas negotiation | fixed at connect, as on MVS (window sized before connecting, never resized) | ZOS-4 / ZOS-5 sessions (same launch) |
| TSO line mode in the alternate size | CONFIRMED at the 120-column line size with Z3 | ZOS-4 session 2 (user attestation), Z3 |
| TSO line-mode output, STLINENO fresh screen | CONFIRMED (observational live; batch exact) | ZOS-4 session 2; ZOS-2 C7 TSO1-6 |
| TSO terminal macros (assemble) | CONFIRMED (HLASM, C3 ASMA303W only) | PACZ2BLD JOB08888 |
| TSO full screen (TPUT FULLSCR / TGET ASIS) | CONFIRMED | ZOS-5 A / B / C |
| TPUT / TGET in batch | CONFIRMED line-mode fallback (FSON RC 4 from the control flow) | ZOS-3 PACZ3FS JOB01362 |
| Extended colour | CONFIRMED | ZOS-5 (QCode X'86', writes = model) |
| Reshow keys | PA2 CONFIRMED; CLEAR not delivered, z/OS TSO / VTAM CLEAR record, redraw by PA2 | ZOS-5 B; R1-T4 PA2 |
| Highlighting | CONFIRMED | ZOS-5 (QCode X'87') |
| Character attributes (SA order) | USED, writes = model | ZOS-5..ZOS-9 TSD / live |
| APL / graphic character set (GE) | CONFIRMED (GE + CP310) | ZOS-5 profile |
| Programmed Symbols | NOT ANNOUNCED on this path; not used | ZOS-5 real Query Reply = qreply_dyn (no loadable sets) |
| Triple-plane PS | NOT APPLICABLE | depends on PS |
| Vector / host graphics (GDDM, GOCA) | NOT TESTED on z/OS; not used by 2.0 | none (outside the 2.0 equivalence) |
| Capability detection (Read Partition Query) | CONFIRMED | ZOS-5 A / B; QRY1 (ZOS-2) |
| Colour renderer TSC | CONFIRMED | ZOS-5; every profile family TSD-exact (PACZ9E1 / E2) |
| Audible alarm (WCC alarm bit) | CONFIRMED, audible at c3270 | ZOS-8 S1-S3 |
| Partial screen update | CONFIRMED | ZOS-5 A / B / C |
| Idle animation | CONFIRMED idle ticks; D28 behaviour as recorded | ZOS-5 (docs/evidence/zos5-fullscreen.md) |
| Viable update rate | logical 150 / 125 ms; physical ~300 / 375 ms under PRESENT(COALESCED); one write per quantum (EVERY) not viable interactively | ZOS-6 R1-T3 / R1-T4 / R2, ZV-D33 |
| Real-time input (PF7/8/10/11, PF9, PA2) | CONFIRMED under COALESCED | ZOS-6 R1-T4 / R2, ZOS-7 L2 / L3 |
| Alarm patterns | CONFIRMED | ZOS-3 TD1-4, ZOS-8 S1-S3 |
| Automatic maximum profile | AUTO profile selection CONFIRMED (COLOR(AUTO) -> GRAPHIC 4x2, 120 x 27); release REALTIME default PRESENT(AUTO) -> COALESCED CONFIRMED on the installed release | ZOS-5 A; DEC-2; ZOS-10 PACZ10CL JOB04866, S10 |
