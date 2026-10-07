# Architecture (MVS-7, requirements sec. 3)
Static-linked COBOL modules, one load module `PACMAIN`; shared state lives in the driver's storage and is passed
by reference (`CALL 'X' USING PAC-STATE ...`). Copybooks (src/copy) start with their own 01 record (D16).

| Module  | Layer     | Responsibility | Touches terminal/host? |
|---------|-----------|----------------|------------------------|
| PACMAIN | driver    | main loop only: reads requests, dispatches, no rules, no I/O verbs | no |
| PACGAME | GAME/CORE | state, turn rules, pellets/score, hits, lives, WON/LOST/QUIT | no |
| PACMAP  | MAP       | level data + cell services LOAD/WALL/CLR/EAT/CNT | no |
| PACAI   | AI        | ghost movement AI1-AI3, fixed-seed LCG (D14) | no |
| PACINPT | INPUT     | SYSIN card -> request (MOV/QUI/CFG/INV/EOF); the only file I/O | card file only |
| PACDISP | DISPLAY   | plain-text G0 rendering; reads state, never changes it | output only |
| PACPLAT | PLATFORM  | host start/finish hooks (MVS batch); pause/terminal services arrive in MVS-8 | yes (host) |

Interfaces (copybooks): `PACSTATE` shared game state (no VALUE clauses); `PACREQ` driver request
(`REQ-OP` RSET/CFG/INIT/MOVE/QUIT/EOF/HEAD/STAT/INVL/END/OPEN/READ/CLOS/INIT/FINI, `REQ-KIND`, `REQ-DIR`,
`REQ-CHAR`, `REQ-LEVEL`, `REQ-COUNT`); `PACMREQ` map service (`M-OP`, `M-X`, `M-Y`, `M-FLAG`, `M-COUNT`).
Rules enforced by `tests/test_mvs7.py`: PACGAME/PACMAP/PACAI contain no DISPLAY/ACCEPT/READ/OPEN/SELECT, no
SYSIN/TSO/ISPF/Zowe/Hercules references; only PACINPT has SELECT; PACMAIN has no DISPLAY; PACMAP is a leaf.
Porting to z/OS (ZOS-*) should only replace PACINPT/PACDISP/PACPLAT (plus JCL).
