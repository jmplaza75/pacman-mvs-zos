# Pac-Man 2.1-zos (2026-10-21) - REALTIME Right on PF12
Target and game: as 2.0-zos (`releases/2.0-ZOS/`): IBM z/OS on IBM Z Xplore, Enterprise COBOL 6.5, HLASM, the z/OS
binder, LE, TSO / VTAM / TN3270E, c3270 4.5. 2.1-zos is 2.0-zos with one control change, decision D46 - the same change
as 2.1-mvs on the MVS line. Design: `docs/zos11-design.md`; evidence: `docs/evidence/zos11-release.md`.

## What changed (D46)
| Item | 2.0-zos | 2.1-zos |
|---|---|---|
| REALTIME Right | PF11 (AID X'7B', `IF WS-V = 123`) | **PF12** (AID X'7C', `IF WS-V = 124`) - at once, no ENTER |
| PF11 in REALTIME | Right | nothing (the existing ignored path) |
| CLIST help | `ARROWS = PF7/8/10/11` | `ARROWS = PF7/8/10/12` (comment only: no statement, default or PARM change) |
| c3270 keymap (`tools/c3270_rt.sh`) | Right arrow -> PF(11) | Right arrow -> **PF(12)** |
Unchanged: Up PF7, Down PF8, Left PF10, PF9 pause / resume, PA2 redraw, every other PF key ignored; QUIT only by
typing `Q` then ENTER (no PF key quits); TURN, batch / card mode, the game, every default and every oracle.

## Play
1. Size a terminal window to 120 x 30, then connect with the keymap of `tools/c3270_rt.sh` (Right arrow = PF12), e.g.
   `c3270 -model 2 -oversize auto -xrm 'c3270.keymap: pacman' -xrm 'c3270.keymap.pacman: <Key>UP: PF(7)\n<Key>DOWN:
   PF(8)\n<Key>LEFT: PF(10)\n<Key>RIGHT: PF(12)' 198.51.100.200:623`; log on (credentials typed by the user only).
2. From TSO READY or ISPF option 6: `EXEC 'Z00000.PACMAN.CLIST(PACMAN)'` (operands as in 2.0-zos, `DEFAULTS.md`).
   Arrows = PF7 / PF8 / PF10 / PF12, PF9 pause, PA2 redraw, quit = type Q, then ENTER.

## Verification summary (MANIFEST.md)
- **Step 2A - build**: fresh, empty `Z00000.PACMAN.RZ21.*` libraries; the 35b803e sources uploaded byte-identical;
  clean build (same RCs and compile statistics as 2.0-zos). Object gate against the 2.0-zos build of record: the only
  functional delta is D46 - PACINPT differs in exactly one loaded byte, the RT-TSC literal `00123C` -> `00124C`; every
  other module identical apart from compile timestamps or the compressed form of the no-load D_MCODE debug class
  (decompressed identical). Batch / TURN regression C1 / C2 = oracles and models and = the 2.0-zos outputs byte for
  byte.
- **Step 2B - promotion**: the installed 2.0-zos CLIST backed up to the new `PRV20.CLIST`; PACMAIN promoted, verified,
  then the CLIST; installed = RZ21 (binary image of the program, bytes of the CLIST); installed P1 = oracle = RZ21 =
  2.0-zos. AMASPZAP limitation: on z/OS `DUMP PACMAIN ALL` covers the B_TEXT class only (the 3 assembler modules and
  the LE / IGZ stubs); the 10 COBOL modules keep their code in C_CODE (AMA152I), so PACINPT is not in that dump. The
  dump is corroboration only; the proof of the installed PACINPT is the binary identity installed = RZ21 plus the
  step 2A object gate.
- **Step 2C - live gate** (installed release, `RULES(CLASSIC)`, no high-score path): attempt 1 FAIL (live-driver
  Q-field detection defect, fixed in 67dfa21); attempt 2 functionally correct but ENVIRONMENT / TIMING BLOCKED (physical
  max gap 1,351 ms > 1,000 ms; a checker Q-hold window defect, fixed in 6d04b6f, also showed); **attempt 3 PASS** -
  2.1 model 251 writes / 496 quanta, physical max gap 942 ms (median 300, p95 438), PF12 moves Right as a bare AID,
  PF11 no longer Right, no PF key quits (PF1-PF24 sweep), pause / resume and PA2 as modelled, Q alone does not quit,
  Q + ENTER quits, the 2.0 / PF12-ignored / PF11-as-Right mappings rejected, back at the ISPF Command Shell.
- Production high score unchanged throughout: `0000980 PACHS001 001`.

## Q without ENTER (z/OS observation)
On this z/OS / c3270 path a typed `Q` without ENTER sends nothing: during the 3 s hold the game wrote 11 screens, no
inbound record reached the host, and the Q stayed in the `COMMAND ===>` field; the next ENTER transmitted it
(`7D 6F5B 11 6FD9 D8`) and the game quit. Same behaviour as TK4- (2.1-mvs).

## Known limits
As 2.0-zos (`releases/2.0-ZOS/RELEASE-NOTES.md`): COALESCED presentation for interactive REALTIME, 120 x 27 live
alternate size, no Programmed Symbols, the site output limit. The live timing gate depends on the shared host /
network: one of three live attempts was timing-blocked by the environment.
