# Pac-Man 2.1-mvs (2026-10-21) - the PF12 control release
Target: MVS 3.8J TK4- on Hercules (as 2.0-MVS-MAX, `releases/2.0-MVS-MAX/`). Design: docs/MVS10-PF12.md (D46);
evidence: docs/evidence/mvs10-release.md.

## What changed (only this)
- **REALTIME Right is PF12** (AID X'7C'), no longer PF11 (X'7B'). PF12 acts at once as a key, without ENTER. The Right
  arrow of the supplied c3270 launcher (`tools/c3270_rt.sh`) now sends PF12, so the arrow keys play exactly as before.
- **PF11 does nothing** in REALTIME, like PF1-PF6 and PF13-PF24.
- **No PF key quits.** QUIT is only `Q` typed in the command field followed by ENTER; a typed `Q` alone does nothing.
- TURN mode, batch, the game rules and every screen are unchanged (the 1.0-MVS and 2.0 oracles pass byte for byte).
Controls and defaults: DEFAULTS.md. The installed program differs from the installed 2.0 program in exactly one
byte (the PF12 constant).

## Verification (MANIFEST.md)
- Fresh build of record from empty libraries `HERC01.PACMAN.R21` (JOB 321), every regression run-only on that module
  (JOBs 322-326), installed by copy with byte identity (JOB 328), installed checks (JOBs 329-331).
- After a host DASD incident (two Hercules instances on the same volumes; system volume restored from the pristine TK4-
  image): R21 and the installed members re-verified unchanged (JOBs 332, 333).
- Live gate on the installed release: PF12 Right, PF11 no move, no PF key quits, PF1-PF24 sweep, pause, PA2, `Q` alone
  no effect, `Q` + ENTER quits; all 68 live screen writes = the 2.1 model, the 2.0 mapping reproduces only 29.

## Play
As 2.0: window 120 x 30, `TYPEAHEAD=false tools/c3270_rt.sh`, log on, `EXEC 'HERC01.PACMAN.CLIST(PACMAN)'`.
Host start / stop on this installation: docs/ENVIRONMENT.md (manual boot, documented shutdown).
