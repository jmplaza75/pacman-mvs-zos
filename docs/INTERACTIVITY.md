# MVS-8 interactivity: investigation, result and validation (2026-10-07)
Goal (requirements sec. 5, level B): play from a 3270 TSO session, keeping the card/batch mode as reference and fallback.

## Final design (only PACMAIN driver + PACINPT/PACDISP/PACPLAT + stub PACTSO; PACGAME/PACMAP/PACAI untouched)
- Launcher CLIST `HERC01.PACMAN.CLIST(PACMAN)` (src/clist/PACMAN.clist): allocates SYSIN and SYSOUT to the terminal
  (`DA(*)`) and runs `CALL 'HERC01.PACMAN.LOAD(PACMAIN)' 'TSO AI<l> <n>'`. Keywords `AI(0-3)` `GHOSTS(1-3)`.
- `PARM='TSO ...'` sets REQ-MODE=TSO (validated by PACPLAT); no PARM = BAT, byte-identical to MVS-7.
- TSO flow (PACMAIN): config from the PARM (PACINPT op PARM classifies it; bytes beyond PARM-LEN are blanked), board shown
  before the first prompt, prompt `CMD (U/D/L/R/Q)?` before every read (PACDISP op PRMT, no-op in BAT), no read after
  QUIT/WON/LOST (this also applies to BAT, where it changes no output: the unread trailing card produced none).
- PACINPT (TSO only): leading blanks/non-printable bytes before the command are skipped; an empty line = RDR (redraw the
  current frame, no turn). In BAT a blank card stays `INVALID COMMAND`.
- Paging: every frame after the first starts a fresh screen. PACDISP asks PACPLAT op CLS, which calls the assembler stub
  PACTSO: `STLINENO LINE=1` (TSO/VTAM line-mode service, SVC 94; not a full-screen interface). PACTSO checks
  PSAAOLD->ASCBTSB and does nothing outside a TSO user address space, so batch and the TSO-mode replays are unaffected.

## Findings along the way
- TPUT/TGET (SVC 93) from a stub under a batch TMP (IKJEFT01) return RC 0 and do nothing (evidence
  mvs8-tputprobe.txt), so a TPUT-based adapter could not be regression-tested: discarded.
- Live session 1: `R` gave INVALID COMMAND and `Q` did not end. Cause of the extra prompt: the loop read one more
  card after QUIT. Fixed.
- Live session 2 (with a temporary hex dump of the input, now removed): input bytes were clean (`Q` = X'D8' + blanks);
  the frame was produced but TSO cleared the full screen before the next read, and later frames were paged with `***`.
- Live session 3 (JOB 138 build): sequence `R R L L D D R U` with `AI(3) GHOSTS(2)`: every turn on its own screen, no
  `***`, two ghosts and `G2=` shown, `Q` ended with QUIT/TURNS/SCORE/LIVES and returned to READY. **Validated by the user
  in c3270 on 2026-10-07.**

## Remaining known limitation
Only frames clear the screen: many consecutive invalid commands (each adds `INVALID COMMAND`, prompt and echo lines)
can still fill the screen and trigger `***` once; ENTER continues. Full-screen 3270 belongs to the graphic ladder (G1+).

## Automated verification (batch, Hercules JOB 138)
19 card runs byte-identical to the accepted MVS-7 output; 6 PARM='TSO' replays (MOVES, DIE1, P2, MULTI, C3N2, TSORDR)
equal the batch reference minus prompts, with the board before the first prompt, exactly one prompt per read, no read
after the end, and an empty line producing a redraw (TSORDR). 43 steps RC 0000 + PACTSO assembly RC 0.
