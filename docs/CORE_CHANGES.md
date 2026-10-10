# Authorised changes to the frozen game core
The core (PACGAME, PACMAP, PACAI, copybooks PACSTATE/PACMREQ, maps/LEVEL1.txt) is frozen at release 1.0-MVS by
tests/core_baseline.json (MVS-G0). A change is possible only through
`python3 tools/core_baseline.py --authorize "REASON" --by NAME`, which records it below and updates the baseline.
PACREQ is the adapter request interface: it may grow (append-only) without authorisation; the 1.0-MVS regression
oracle must still pass.

## 2026-10-07 - baseline
Core frozen at release 1.0-MVS (commit 89fe86b). No changes authorised yet.

## 2026-10-10 - authorised by project owner (RT1 approval)
Reason: MVS-RT RT2 (D33): PACGAME REQ-STEP selector - P player step only (no PACAI), G ghost step only (no player move, no tick), anything else = the existing turn (TURN always B; hit/life/no-swap rules unchanged). Approved with the RT1 design 2026-10-10.
- src/cobol/PACGAME.cob: 33fdf171ddc19297 -> 41ad673a3270d4b3
