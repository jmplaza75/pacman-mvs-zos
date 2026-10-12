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

## 2026-10-11 - authorised by project owner (D36 approval)
Reason: MVS-GP1 GP1.2 (D36, approved by the user 2026-10-11): RULES(ARCADE) power pellets. PACMAP op LDA + EAT flag 2 on 'o' + CNT counts 'o' (CLASSIC map has none: unchanged behaviour); PACGAME op ATIK, ARCADE branches in RSET/INIT/MOVE/EAT/HIT/LOSE-LIFE, constants table K-ARC; PACAI flee move and per-class cadence (ARC-ON only); new core copybook PACARC (own 01) and maps/ARCADE1.txt. PACSTATE, PACMREQ, LEVEL1 unchanged; CLASSIC paragraphs unchanged.
- src/cobol/PACGAME.cob: 41ad673a3270d4b3 -> ac803883d397adb7
- src/cobol/PACMAP.cob: e950175efd22849d -> b91c13ca09a27939
- src/cobol/PACAI.cob: d7c3e1fcfa90ccfb -> 66d916d8503831e6
- src/copy/PACARC.cpy: - -> 2f1d2ea50382fc9d
- maps/ARCADE1.txt: - -> f15db8bdb722db8e

## 2026-10-12 - authorised by project owner (D37 approval)
Reason: MVS-GP2 GP2.2 (D37, approved by the user 2026-10-12): RULES(ARCADE) levels 1-99, maze refill on a full clear, per-level table K-LVL in PACGAME (AI bump, REALTIME step, fright/warning, fruit), fruit at (10,8) after 30/70 items, one extra life at 10000 (ARC-XL), event flags incl. death D, wide counters, start level REQ-START. PACARC grew append-only; PACMAP, PACAI, PACSTATE, PACMREQ, LEVEL1, ARCADE1 unchanged; CLASSIC behaviour unchanged. Build JOB 243 RC 0000.
- src/cobol/PACGAME.cob: ac803883d397adb7 -> a0aab0509d50aae9
- src/copy/PACARC.cpy: 2f1d2ea50382fc9d -> dd5c83db32ae3d3f
