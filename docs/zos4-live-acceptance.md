# ZOS-4 live TSO acceptance - DIE1 and LOST0 (session 1 FAIL, session 2 PASS 2026-10-16: docs/evidence/zos4-live.md)

Installed baseline (PACZ4INS JOB03939, accepted): Z00000.PACMAN.LOAD(PACMAIN), Z00000.PACMAN.CLIST(PACMAN) (src/zos,
Z2), Z00000.PACMAN.CEEOPTS. References: the frozen cases tests/cases/DIE1.txt and LOST0.txt, their independent model
transcripts tests/expected/MVS6-DIE1.txt / MVS6-LOST0.txt (tests/test_mvs8.py: the TSO transcript without prompts =
the batch reference, one prompt per read), the oracle 307 blocks (TSO2 = DIE1 in TSO line mode, accepted on z/OS
JOB09031 / JOB01362 / JOB03939; LOST0 = batch RUN7 of 307 - no TSO-mode oracle block exists for LOST0, its live
reference is the model rule above).

## CLIST invocation (both games)
The case files start with the configuration card `AI0` (AI level 0, ghosts default 1: ref_mvs6.parse_config); in TSO
mode the configuration comes from the PARM, so the CLIST keywords are `AI(0)` (GHOSTS(1) is the default) plus the
plan's conservative path `RULES(CLASSIC) PLAY(TURN) COLOR(NO)`; every other keyword at its 2.0 default.
Command, typed on the ISPF option 6 command line:
```
EXEC 'Z00000.PACMAN.CLIST(PACMAN)' 'AI(0) RULES(CLASSIC) PLAY(TURN) COLOR(NO)'
```
The CLIST builds PARM `TSO AI0 1 NNAAPAAATAC01NP` (tests/test_g8.py clist_parm rule, the rule that reproduced the 4
oracle 307 G8PARM lines on z/OS): TSO line mode, AI 0, 1 ghost, COLOR N (no PACFSIO), PLAY TURN, RULES CLASSIC; the
other columns are ignored in line mode (D16 / D18). Z2 allocates CEEOPTS (profile A) only around the CALL and frees
it; with RULES(CLASSIC) no PACHS allocation. Nothing is printed by the CLIST on success.

## Session procedure (one session, the user at the keyboard)
1. `c3270 -model 2 -oversize auto 198.51.100.200:623`; at the welcome screen `logon Z00000`; type the password
   yourself (plain TN3270E, no TLS). No c3270 trace, no screen capture before the ISPF Primary Option Menu.
2. DBPROCDG brings up ISPF: Primary Option Menu -> option `6` (Command). Capture E1 (see Evidence).
3. Enter the command above. Play DIE1 (inputs below), one input + ENTER per `CMD (U/D/L/R/Q)?` prompt.
4. After the DIE1 end lines, control returns to the option 6 shell (ISPF may show `***` once after the command: press
   ENTER). Require the clean return (criteria below) before going on.
5. Enter the same command again and play LOST0. Require the clean return.
6. Leave ISPF to READY (`=X`) and `LOGOFF`. Nothing else: no other command, no ALLOC / FREE / LISTALC / PROFILE.

## DIE1

Inputs: 29 reads, typed in this order (case card 2..30; the case's last card `R` is
never read: the game ends first). Each line: input number, the key to type, the turn line expected after it.

| # | Type | Expected turn line after ENTER |
|---|---|---|
| 1 | `D` | `T001 D MOVED   X=02 Y=03 S=0010 L=099 G=19,09 V=3 ST=RUNNING` |
| 2 | `D` | `T002 D MOVED   X=02 Y=04 S=0020 L=098 G=19,09 V=3 ST=RUNNING` |
| 3 | `D` | `T003 D MOVED   X=02 Y=05 S=0030 L=097 G=19,09 V=3 ST=RUNNING` |
| 4 | `D` | `T004 D MOVED   X=02 Y=06 S=0040 L=096 G=19,09 V=3 ST=RUNNING` |
| 5 | `D` | `T005 D MOVED   X=02 Y=07 S=0050 L=095 G=19,09 V=3 ST=RUNNING` |
| 6 | `D` | `T006 D MOVED   X=02 Y=08 S=0060 L=094 G=19,09 V=3 ST=RUNNING` |
| 7 | `D` | `T007 D MOVED   X=02 Y=09 S=0070 L=093 G=19,09 V=3 ST=RUNNING` |
| 8 | `R` | `T008 R MOVED   X=03 Y=09 S=0080 L=092 G=19,09 V=3 ST=RUNNING` |
| 9 | `R` | `T009 R MOVED   X=04 Y=09 S=0090 L=091 G=19,09 V=3 ST=RUNNING` |
| 10 | `R` | `T010 R MOVED   X=05 Y=09 S=0100 L=090 G=19,09 V=3 ST=RUNNING` |
| 11 | `R` | `T011 R MOVED   X=06 Y=09 S=0110 L=089 G=19,09 V=3 ST=RUNNING` |
| 12 | `R` | `T012 R MOVED   X=07 Y=09 S=0120 L=088 G=19,09 V=3 ST=RUNNING` |
| 13 | `R` | `T013 R MOVED   X=08 Y=09 S=0130 L=087 G=19,09 V=3 ST=RUNNING` |
| 14 | `R` | `T014 R MOVED   X=09 Y=09 S=0140 L=086 G=19,09 V=3 ST=RUNNING` |
| 15 | `R` | `T015 R MOVED   X=10 Y=09 S=0150 L=085 G=19,09 V=3 ST=RUNNING` |
| 16 | `R` | `T016 R MOVED   X=11 Y=09 S=0160 L=084 G=19,09 V=3 ST=RUNNING` |
| 17 | `R` | `T017 R MOVED   X=12 Y=09 S=0170 L=083 G=19,09 V=3 ST=RUNNING` |
| 18 | `R` | `T018 R MOVED   X=13 Y=09 S=0180 L=082 G=19,09 V=3 ST=RUNNING` |
| 19 | `R` | `T019 R MOVED   X=14 Y=09 S=0190 L=081 G=19,09 V=3 ST=RUNNING` |
| 20 | `R` | `T020 R MOVED   X=15 Y=09 S=0200 L=080 G=19,09 V=3 ST=RUNNING` |
| 21 | `R` | `T021 R MOVED   X=16 Y=09 S=0210 L=079 G=19,09 V=3 ST=RUNNING` |
| 22 | `R` | `T022 R MOVED   X=17 Y=09 S=0220 L=078 G=19,09 V=3 ST=RUNNING` |
| 23 | `R` | `T023 R MOVED   X=18 Y=09 S=0230 L=077 G=19,09 V=3 ST=RUNNING` |
| 24 | `R` | `T024 R DIED    X=02 Y=02 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 25 | `R` | `T025 R MOVED   X=03 Y=02 S=0240 L=076 G=19,09 V=2 ST=RUNNING` |
| 26 | `R` | `T026 R MOVED   X=04 Y=02 S=0250 L=075 G=19,09 V=2 ST=RUNNING` |
| 27 | `D` | `T027 D BLOCKED X=04 Y=02 S=0250 L=075 G=19,09 V=2 ST=RUNNING` |
| 28 | `D` | `T028 D BLOCKED X=04 Y=02 S=0250 L=075 G=19,09 V=2 ST=RUNNING` |
| 29 | `Q` | `(end)` |

Milestones (exact screen text = model; each frame starts on a fresh screen at line 1: the T line, the 10 map rows, then `CMD (U/D/L/R/Q)?`):

first screen (after the command):
```
PACMAN MVS-6 SMART GHOSTS
T000   START   X=02 Y=02 S=0000 L=100 G=19,09 V=3 ST=READY
####################
#P.......##........#
#.##.###.##.###.##.#
#..................#
#.##.#.######.#.##.#
#....#...##...#....#
#.##.###.##.###.##.#
#..................#
#.................G#
####################
CMD (U/D/L/R/Q)?
```
after input 24:
```
T024 R DIED    X=02 Y=02 S=0230 L=077 G=19,09 V=2 ST=RUNNING
####################
#P.......##........#
# ##.###.##.###.##.#
# .................#
# ##.#.######.#.##.#
# ...#...##...#....#
# ##.###.##.###.##.#
# .................#
#                 G#
####################
CMD (U/D/L/R/Q)?
```
after input 28, then input 29 (Q) on the same screen:
```
T028 D BLOCKED X=04 Y=02 S=0250 L=075 G=19,09 V=2 ST=RUNNING
####################
#  P.....##........#
# ##.###.##.###.##.#
# .................#
# ##.#.######.#.##.#
# ...#...##...#....#
# ##.###.##.###.##.#
# .................#
#                 G#
####################
CMD (U/D/L/R/Q)?
Q                      <- typed by the user (input 29)
QUIT
TURNS 028
SCORE 0250
LIVES 2
```

Termination: Q (input 29) -> QUIT; the end lines `QUIT / TURNS 028 / SCORE 0250 / LIVES 2` follow the prompt of the T028
frame (as the z/OS TSO2 output JOB09031 shows); no prompt after them.
Clean return: the option 6 shell is back (after at most one `***` from ISPF), no message between the end lines and
the shell (no PACMAN:, IKJ, CEE, IEC, abend text), and the next command can be entered.

## LOST0

Inputs: 72 reads, typed in this order (case card 2..73; the case's last card `R` is
never read: the game ends first). Each line: input number, the key to type, the turn line expected after it.

| # | Type | Expected turn line after ENTER |
|---|---|---|
| 1 | `D` | `T001 D MOVED   X=02 Y=03 S=0010 L=099 G=19,09 V=3 ST=RUNNING` |
| 2 | `D` | `T002 D MOVED   X=02 Y=04 S=0020 L=098 G=19,09 V=3 ST=RUNNING` |
| 3 | `D` | `T003 D MOVED   X=02 Y=05 S=0030 L=097 G=19,09 V=3 ST=RUNNING` |
| 4 | `D` | `T004 D MOVED   X=02 Y=06 S=0040 L=096 G=19,09 V=3 ST=RUNNING` |
| 5 | `D` | `T005 D MOVED   X=02 Y=07 S=0050 L=095 G=19,09 V=3 ST=RUNNING` |
| 6 | `D` | `T006 D MOVED   X=02 Y=08 S=0060 L=094 G=19,09 V=3 ST=RUNNING` |
| 7 | `D` | `T007 D MOVED   X=02 Y=09 S=0070 L=093 G=19,09 V=3 ST=RUNNING` |
| 8 | `R` | `T008 R MOVED   X=03 Y=09 S=0080 L=092 G=19,09 V=3 ST=RUNNING` |
| 9 | `R` | `T009 R MOVED   X=04 Y=09 S=0090 L=091 G=19,09 V=3 ST=RUNNING` |
| 10 | `R` | `T010 R MOVED   X=05 Y=09 S=0100 L=090 G=19,09 V=3 ST=RUNNING` |
| 11 | `R` | `T011 R MOVED   X=06 Y=09 S=0110 L=089 G=19,09 V=3 ST=RUNNING` |
| 12 | `R` | `T012 R MOVED   X=07 Y=09 S=0120 L=088 G=19,09 V=3 ST=RUNNING` |
| 13 | `R` | `T013 R MOVED   X=08 Y=09 S=0130 L=087 G=19,09 V=3 ST=RUNNING` |
| 14 | `R` | `T014 R MOVED   X=09 Y=09 S=0140 L=086 G=19,09 V=3 ST=RUNNING` |
| 15 | `R` | `T015 R MOVED   X=10 Y=09 S=0150 L=085 G=19,09 V=3 ST=RUNNING` |
| 16 | `R` | `T016 R MOVED   X=11 Y=09 S=0160 L=084 G=19,09 V=3 ST=RUNNING` |
| 17 | `R` | `T017 R MOVED   X=12 Y=09 S=0170 L=083 G=19,09 V=3 ST=RUNNING` |
| 18 | `R` | `T018 R MOVED   X=13 Y=09 S=0180 L=082 G=19,09 V=3 ST=RUNNING` |
| 19 | `R` | `T019 R MOVED   X=14 Y=09 S=0190 L=081 G=19,09 V=3 ST=RUNNING` |
| 20 | `R` | `T020 R MOVED   X=15 Y=09 S=0200 L=080 G=19,09 V=3 ST=RUNNING` |
| 21 | `R` | `T021 R MOVED   X=16 Y=09 S=0210 L=079 G=19,09 V=3 ST=RUNNING` |
| 22 | `R` | `T022 R MOVED   X=17 Y=09 S=0220 L=078 G=19,09 V=3 ST=RUNNING` |
| 23 | `R` | `T023 R MOVED   X=18 Y=09 S=0230 L=077 G=19,09 V=3 ST=RUNNING` |
| 24 | `R` | `T024 R DIED    X=02 Y=02 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 25 | `D` | `T025 D MOVED   X=02 Y=03 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 26 | `D` | `T026 D MOVED   X=02 Y=04 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 27 | `D` | `T027 D MOVED   X=02 Y=05 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 28 | `D` | `T028 D MOVED   X=02 Y=06 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 29 | `D` | `T029 D MOVED   X=02 Y=07 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 30 | `D` | `T030 D MOVED   X=02 Y=08 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 31 | `D` | `T031 D MOVED   X=02 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 32 | `R` | `T032 R MOVED   X=03 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 33 | `R` | `T033 R MOVED   X=04 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 34 | `R` | `T034 R MOVED   X=05 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 35 | `R` | `T035 R MOVED   X=06 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 36 | `R` | `T036 R MOVED   X=07 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 37 | `R` | `T037 R MOVED   X=08 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 38 | `R` | `T038 R MOVED   X=09 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 39 | `R` | `T039 R MOVED   X=10 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 40 | `R` | `T040 R MOVED   X=11 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 41 | `R` | `T041 R MOVED   X=12 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 42 | `R` | `T042 R MOVED   X=13 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 43 | `R` | `T043 R MOVED   X=14 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 44 | `R` | `T044 R MOVED   X=15 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 45 | `R` | `T045 R MOVED   X=16 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 46 | `R` | `T046 R MOVED   X=17 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 47 | `R` | `T047 R MOVED   X=18 Y=09 S=0230 L=077 G=19,09 V=2 ST=RUNNING` |
| 48 | `R` | `T048 R DIED    X=02 Y=02 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 49 | `D` | `T049 D MOVED   X=02 Y=03 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 50 | `D` | `T050 D MOVED   X=02 Y=04 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 51 | `D` | `T051 D MOVED   X=02 Y=05 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 52 | `D` | `T052 D MOVED   X=02 Y=06 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 53 | `D` | `T053 D MOVED   X=02 Y=07 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 54 | `D` | `T054 D MOVED   X=02 Y=08 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 55 | `D` | `T055 D MOVED   X=02 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 56 | `R` | `T056 R MOVED   X=03 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 57 | `R` | `T057 R MOVED   X=04 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 58 | `R` | `T058 R MOVED   X=05 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 59 | `R` | `T059 R MOVED   X=06 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 60 | `R` | `T060 R MOVED   X=07 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 61 | `R` | `T061 R MOVED   X=08 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 62 | `R` | `T062 R MOVED   X=09 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 63 | `R` | `T063 R MOVED   X=10 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 64 | `R` | `T064 R MOVED   X=11 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 65 | `R` | `T065 R MOVED   X=12 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 66 | `R` | `T066 R MOVED   X=13 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 67 | `R` | `T067 R MOVED   X=14 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 68 | `R` | `T068 R MOVED   X=15 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 69 | `R` | `T069 R MOVED   X=16 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 70 | `R` | `T070 R MOVED   X=17 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 71 | `R` | `T071 R MOVED   X=18 Y=09 S=0230 L=077 G=19,09 V=1 ST=RUNNING` |
| 72 | `R` | `T072 R LOST    X=19 Y=09 S=0230 L=077 G=19,09 V=0 ST=LOST` |

Milestones (exact screen text = model; each frame starts on a fresh screen at line 1: the T line, the 10 map rows, then `CMD (U/D/L/R/Q)?`):

first screen (after the command):
```
PACMAN MVS-6 SMART GHOSTS
T000   START   X=02 Y=02 S=0000 L=100 G=19,09 V=3 ST=READY
####################
#P.......##........#
#.##.###.##.###.##.#
#..................#
#.##.#.######.#.##.#
#....#...##...#....#
#.##.###.##.###.##.#
#..................#
#.................G#
####################
CMD (U/D/L/R/Q)?
```
after input 24:
```
T024 R DIED    X=02 Y=02 S=0230 L=077 G=19,09 V=2 ST=RUNNING
####################
#P.......##........#
# ##.###.##.###.##.#
# .................#
# ##.#.######.#.##.#
# ...#...##...#....#
# ##.###.##.###.##.#
# .................#
#                 G#
####################
CMD (U/D/L/R/Q)?
```
after input 48:
```
T048 R DIED    X=02 Y=02 S=0230 L=077 G=19,09 V=1 ST=RUNNING
####################
#P.......##........#
# ##.###.##.###.##.#
# .................#
# ##.#.######.#.##.#
# ...#...##...#....#
# ##.###.##.###.##.#
# .................#
#                 G#
####################
CMD (U/D/L/R/Q)?
```
after input 72:
```
T072 R LOST    X=19 Y=09 S=0230 L=077 G=19,09 V=0 ST=LOST
####################
# .......##........#
# ##.###.##.###.##.#
# .................#
# ##.#.######.#.##.#
# ...#...##...#....#
# ##.###.##.###.##.#
# .................#
#                 G#
####################
LOST
TURNS 072
SCORE 0230
LIVES 0
```

Termination: the third death on input 72 -> LOST; the end lines `LOST / TURNS 072 / SCORE 0230 / LIVES 0` follow the T072
frame directly (no prompt after it: the game is over).
Clean return: the option 6 shell is back (after at most one `***` from ISPF), no message between the end lines and
the shell (no PACMAN:, IKJ, CEE, IEC, abend text), and the next command can be entered.

## STOP immediately (log off, report; no retry, no repair)
- any unexpected allocation, CEE, IKJ, IEC, abend or other message;
- `PACMAN: ... CEEOPTS MISSING`, `PACMAN: CEEOPTS CHECK FAILED (...)` or `PACMAN: A CEEOPTS DD IS ALREADY ALLOCATED`;
- `***` or other terminal-control text inside a game frame (between a T line and its prompt);
- a screen or turn line different from the table / milestones above, or a prompt sequence diverging from it;
- no clean return to the option 6 shell after either game (do not start LOST0 after a DIE1 problem).

## Evidence (text copied from the c3270 window - select and copy; no trace; nothing before the ISPF menu)
E1 the option 6 shell before DIE1 (no userid / password on it beyond what the user agrees to keep);
E2 DIE1 first screen; E3 DIE1 after input 24 (the death); E4 DIE1 final screen with the end lines; E5 the shell after
the return; E6 LOST0 first screen; E7 / E8 after inputs 24 and 48 (deaths); E9 LOST0 final screen with LOST; E10 the
shell after the return. The user also confirms that every turn line matched the table (no divergence seen).
Postcheck (local, read-only): each captured frame compared character for character with the milestone text above
(from the models); a short docs/evidence/zos4-live.md with E1-E10 (redacted if needed).

## After both games PASS: minimal read-only closure
- z/OS (Zowe, read-only): CLIST(PACMAN) still = the rendered member (binary), CLIST(PACSRCT) = the template,
  Z00000.PACMAN.CEEOPTS = the exact record, LOAD(PACMAIN) attributes = PACZ2D's, PACZ2D unchanged (the existing
  zos_ins_check --clist checks + the attribute / CEEOPTS checks, run once).
- Docs: docs/evidence/zos4-live.md, docs/evidence/zos4-classic.md (live section), README pointer, CURRENT_PHASE
  `ZOS-4 COMPLETE`, docs/ZOS-DIFFS.md unchanged (Z1, Z2).
- Commit `ZOS-4 CLASSIC complete: live TSO line-mode acceptance DIE1 / LOST0 PASS on the installed PACMAIN + CLIST (Z2)`
  and annotated tag `zos-4` on it, carrying forward: C3 (ZOS-8 E2), HA6 (ZOS-9/10), HSP1-9 (full battery), the HS
  CLIST block live path (ZOS-8), full-screen / colour / TPUT-TGET (ZOS-5).

## Approval (user, 2026-10-16) and evidence rule
Approved for one interactive session; no functional change. Evidence rule: clipboard captures are compared exactly
through the last expected nonblank character of each line (missing or extra trailing blanks are not a failure);
internal spaces, case, values, line order and frame content must be exact; no other normalisation. `***` inside a
Pac-Man frame is a FAIL; a normal TSO / ISPF `***` after the program has ended is allowed (ENTER). Postcheck tool:
tools/zowe/zos_live_check.py DIR (captures E1.txt .. E10.txt).

## Session 2 (after the Z3 installation is approved and verified; not started)
Session 1 (2026-10-16) is FAIL evidence (DIE1 FAIL before the first frame, LOST0 NOT RUN) and is never reclassified;
session 2 is a new session with the same procedure and inputs, on CLIST(PACMAN) with Z3 + Z2.
- Geometry: exactly the one that failed - `c3270 -model 2 -oversize auto 198.51.100.200:623` in the same 120 x 30
  window (120-column line size). Not 80 columns.
- First required proof (the discriminator): after the EXEC, DIE1 reaches its initial frame with
  `T000   START   X=02 Y=02 S=0000 L=100 G=19,09 V=3 ST=READY` and no `IGZ0201W`, `IGZ0035S`, `U4038` / abend,
  `PACMAN: SYSIN NOT ALLOCATED` or IKJ message. Capture E2 at that point.
- Then DIE1 and LOST0 exactly as above (inputs, milestones, E1-E10, evidence rule, STOP criteria) - the STOP list also
  includes `PACMAN: SYSIN NOT ALLOCATED (Z3, ...)` and any message from ATTRIB / ALLOC / FREE.
- Closure as above, with CLIST(PACMAN) = the rendered Z3 member and docs/ZOS-DIFFS.md listing Z1, Z2, Z3.
