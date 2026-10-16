# ZOS-4 live TSO line-mode acceptance (docs/zos4-live-acceptance.md)

## Session 1 (2026-10-16): FAIL - permanent, never reclassified
`EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) PLAY(TURN) COLOR(NO)'` from ISPF option 6, c3270
`-model 2 -oversize auto` in a 120 x 30 window, CLIST with Z2 only. PACMAIN was reached (Z2 / profile A worked), then
IGZ0201W (COMMAND-FILE 80 vs SYSIN 120), IGZ0035S (OPEN of SYSIN, file status 39), user abend 4038. DIE1 = FAIL before
the first frame; LOST0 = NOT RUN; no retry. Source: the user's report (no screen text was archived). Cause and fix:
docs/zos4-sysin-fix.md -> Z3 (ATTRIB + USING), docs/ZOS-DIFFS.md.

## Session 2 (2026-10-16): PASS
Installed under test: CLIST(PACMAN) with Z3 + Z2 (130 x 80, SHA-256 f8989cfa..., docs/evidence/zos4-z3-install.txt),
LOAD(PACMAIN) = PACZ2D, Z00000.PACMAN.CEEOPTS. Same command, same geometry as session 1 (c3270 `-model 2 -oversize
auto`, 120 x 30 window, 120-column line size). One session, the user at the keyboard, logged off at the end.

| Check | Result (user) |
|---|---|
| Z3 discriminator: DIE1 reaches `T000 ... ST=READY` with no IGZ0201W / IGZ0035S / U4038 / IKJ / SYSIN NOT ALLOCATED | PASS |
| DIE1 played with the frozen inputs, turn lines as the table | PASS |
| clean return to the ISPF option 6 shell after DIE1 | PASS |
| LOST0 played with the frozen inputs, ends LOST | PASS |
| clean return to the ISPF option 6 shell after LOST0 | PASS |
| TSO session logged off | PASS |

Evidence form (recorded as it is): the user's attestation of the live checks above; the E1-E10 clipboard captures were
not provided, so tools/zowe/zos_live_check.py was not run on session 2. The user closed the phase on this basis
(2026-10-16) and asked for no repeat of DIE1 / LOST0 and no further session.

## Read-only closure check (2026-10-16, once): PASS
docs/evidence/zos4-closure-check.txt: CLIST(PACMAN) = rendered src/zos (Z3 + Z2) byte for byte, PACSRCT = the template,
CEEOPTS exact (attributes + binary), LOAD(PACMAIN) attributes = PACZ2D's, PACZ2D unchanged.
