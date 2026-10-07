# Pac-Man 1.0-MVS (2026-10-07)
Target: MVS 3.8J TK4- on Hercules 4.9.1 (S/370, IKFCBL00 COBOL, IFOX00, IEWL, JES2).

Contents: ALLOC.jcl (first-use libraries), CLIST.jcl (TSO launcher), BUILD.jcl (upload, compile, assemble, link and
the full regression), RUN.jcl (batch sample game), SHA256SUMS (sources). All decks use prefix HERC01.PACMAN and carry no
credentials; tools/submit.sh adds them from .env at submission time. Regenerate for another prefix with
`tools/make_deck.py <DECK> --prefix HLQ.NAME`.

Features: 20x10 maze, pellets/score, 3 lives, 1-3 ghosts with AI0-AI3 (deterministic), batch card mode (reference)
and interactive TSO mode with fresh-screen redraw (no `***` paging).

Verification:
- From empty libraries under HERC01.PACMAN.R10: ALLOC JOB 139, CLIST JOB 140, BUILD JOB 141 (43 steps RC 0000 +
  ASM RC 0, all regression checks), RUN JOB 142 (WIN, 1000 points).
- Default prefix HERC01.PACMAN: BUILD JOB 143, all checks pass; CLIST JOB 144.
- Interactive mode validated live by the user in c3270 (MVS-8, JOB 138 build; same sources).

Known limitation: in TSO, many consecutive invalid commands can still fill the screen once (ENTER continues).
