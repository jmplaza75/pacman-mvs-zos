      * MVS-6: SMARTER GHOSTS. COMMANDS U/D/L/R/Q, ONE PER CARD.
      * OPTIONAL FIRST CARD: AI<L> [<N>] : L = 0 STILL, 1 RANDOM,
      * 2 PERSISTENT DIRECTION, 3 CHASE (MANHATTAN); N = 1-3 GHOSTS.
      * GHOSTS NEVER REVERSE (LEVELS 2-3) UNLESS NO OTHER MOVE EXISTS.
      * LCG SEED IS FIXED (12345) SO EVERY RUN IS REPRODUCIBLE.
      * MAP LITERALS MUST MATCH MAPS/LEVEL1.TXT.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACMAIN.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT COMMAND-FILE ASSIGN TO UT-S-SYSIN.
       DATA DIVISION.
       FILE SECTION.
       FD  COMMAND-FILE
           RECORDING MODE IS F
           LABEL RECORDS ARE OMITTED
           RECORD CONTAINS 80 CHARACTERS
           DATA RECORD IS COMMAND-RECORD.
       01  COMMAND-RECORD.
           05  CMD-CHAR          PIC X.
           05  FILLER            PIC X.
           05  CMD-LEVEL         PIC X.
           05  FILLER            PIC X.
           05  CMD-COUNT         PIC X.
           05  FILLER            PIC X(75).
       WORKING-STORAGE SECTION.
       01  MAP-DATA.
           05  FILLER            PIC X(20) VALUE '####################'.
           05  FILLER            PIC X(20) VALUE '#........##........#'.
           05  FILLER            PIC X(20) VALUE '#.##.###.##.###.##.#'.
           05  FILLER            PIC X(20) VALUE '#..................#'.
           05  FILLER            PIC X(20) VALUE '#.##.#.######.#.##.#'.
           05  FILLER            PIC X(20) VALUE '#....#...##...#....#'.
           05  FILLER            PIC X(20) VALUE '#.##.###.##.###.##.#'.
           05  FILLER            PIC X(20) VALUE '#..................#'.
           05  FILLER            PIC X(20) VALUE '#..................#'.
           05  FILLER            PIC X(20) VALUE '####################'.
       01  MAP-TABLE REDEFINES MAP-DATA.
           05  MAP-ROW           OCCURS 10 TIMES.
               10  MAP-CELL      PIC X OCCURS 20 TIMES.
       01  WS-LINE               PIC X(20).
       01  WS-LINE-CELLS REDEFINES WS-LINE.
           05  WS-LINE-CELL      PIC X OCCURS 20 TIMES.
       01  PLAYER-X              PIC 99 VALUE 2.
       01  PLAYER-Y              PIC 99 VALUE 2.
       01  NEW-X                 PIC 99.
       01  NEW-Y                 PIC 99.
       01  WS-ROW                PIC 99.
       01  TICK-COUNT            PIC 999 VALUE 0.
       01  WS-CMD                PIC X.
       01  WS-RESULT             PIC X(7).
       01  WS-EOF                PIC 9 VALUE 0.
       01  WS-QUIT               PIC 9 VALUE 0.
       01  WS-WON                PIC 9 VALUE 0.
       01  WS-LOST               PIC 9 VALUE 0.
       01  WS-HIT                PIC 9 VALUE 0.
       01  LIVES                 PIC 9 VALUE 3.
       01  GAME-STATE            PIC X(7) VALUE 'READY  '.
       01  AI-LEVEL              PIC 9 VALUE 1.
       01  GHOST-COUNT           PIC 9 VALUE 1.
       01  GHOST-TABLE.
           05  GH-ENTRY          OCCURS 3 TIMES.
               10  GH-X          PIC 99.
               10  GH-Y          PIC 99.
               10  GH-DIR        PIC 9.
       01  GS-DATA               PIC X(15) VALUE '190930209419023'.
       01  GS-TABLE REDEFINES GS-DATA.
           05  GS-ENTRY          OCCURS 3 TIMES.
               10  GS-X          PIC 99.
               10  GS-Y          PIC 99.
               10  GS-DIR        PIC 9.
       01  REV-DATA              PIC X(4) VALUE '2143'.
       01  REV-TABLE REDEFINES REV-DATA.
           05  REV-D             PIC 9 OCCURS 4 TIMES.
       01  WS-G                  PIC 9.
       01  WS-GX                 PIC 99.
       01  WS-GY                 PIC 99.
       01  WS-CUR                PIC 9.
       01  WS-REVD               PIC 9.
       01  WS-J                  PIC 9.
       01  WS-K                  PIC 9.
       01  DIST-X                PIC S99.
       01  DIST-Y                PIC S99.
       01  DIST-T                PIC S999.
       01  BEST-DIST             PIC S999.
       01  GHOST-SEED            PIC 9(5) VALUE 12345.
       01  WS-WORK               PIC 9(9).
       01  WS-QUOT               PIC 9(9).
       01  WS-REM                PIC 9(5).
       01  WS-D                  PIC 9.
       01  CAND-N                PIC 9.
       01  CAND-TABLE.
           05  CAND              PIC 9 OCCURS 4 TIMES.
       01  DIR-DATA              PIC X(8) VALUE '10120121'.
       01  DIR-TABLE REDEFINES DIR-DATA.
           05  DIR-ENTRY         OCCURS 4 TIMES.
               10  DIR-DX        PIC 9.
               10  DIR-DY        PIC 9.
       01  G-NX                  PIC 99.
       01  G-NY                  PIC 99.
       01  WS-COL                PIC 99.
       01  SCORE                 PIC 9(4) VALUE 0.
       01  PELLETS-LEFT          PIC 999 VALUE 0.
       01  WS-STATUS-LINE.
           05  FILLER            PIC X VALUE 'T'.
           05  ST-TURN           PIC 999.
           05  FILLER            PIC X VALUE ' '.
           05  ST-CMD            PIC X.
           05  FILLER            PIC X VALUE ' '.
           05  ST-RESULT         PIC X(7).
           05  FILLER            PIC X(3) VALUE ' X='.
           05  ST-X              PIC 99.
           05  FILLER            PIC X(3) VALUE ' Y='.
           05  ST-Y              PIC 99.
           05  FILLER            PIC X(3) VALUE ' S='.
           05  ST-SCORE          PIC 9(4).
           05  FILLER            PIC X(3) VALUE ' L='.
           05  ST-LEFT           PIC 999.
           05  FILLER            PIC X(3) VALUE ' G='.
           05  ST-GX             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  ST-GY             PIC 99.
           05  FILLER            PIC X(3) VALUE ' V='.
           05  ST-LIVES          PIC 9.
           05  FILLER            PIC X(4) VALUE ' ST='.
           05  ST-STATE          PIC X(7).
       01  WS-XL2.
           05  FILLER            PIC X(3) VALUE 'G2='.
           05  XL2-X             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  XL2-Y             PIC 99.
       01  WS-XL3.
           05  FILLER            PIC X(4) VALUE ' G3='.
           05  XL3-X             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  XL3-Y             PIC 99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           OPEN INPUT COMMAND-FILE.
           DISPLAY 'PACMAN MVS-6 SMART GHOSTS'.
           PERFORM READ-CMD.
           PERFORM READ-CONFIG THRU READ-CONFIG-EXIT.
           PERFORM INIT-GAME.
           MOVE 'START  ' TO WS-RESULT.
           PERFORM SHOW-STATE.
           PERFORM TURN-PARA
               UNTIL WS-EOF = 1 OR WS-QUIT = 1 OR WS-WON = 1
                  OR WS-LOST = 1.
           IF WS-LOST = 1
               DISPLAY 'LOST'
           ELSE IF WS-WON = 1
               DISPLAY 'WIN'
           ELSE IF WS-QUIT = 1
               DISPLAY 'QUIT'
           ELSE
               DISPLAY 'EOF'.
           DISPLAY 'TURNS ' TICK-COUNT.
           DISPLAY 'SCORE ' SCORE.
           DISPLAY 'LIVES ' LIVES.
           CLOSE COMMAND-FILE.
           STOP RUN.
       READ-CONFIG.
           IF CMD-CHAR = 'A' AND WS-EOF = 0
               PERFORM SET-LEVEL THRU SET-LEVEL-EXIT
               PERFORM READ-CMD.
       READ-CONFIG-EXIT.
           EXIT.
       SET-LEVEL.
           IF CMD-LEVEL = '0'
               MOVE 0 TO AI-LEVEL
           ELSE IF CMD-LEVEL = '2'
               MOVE 2 TO AI-LEVEL
           ELSE IF CMD-LEVEL = '3'
               MOVE 3 TO AI-LEVEL
           ELSE
               MOVE 1 TO AI-LEVEL.
           IF CMD-COUNT = '2'
               MOVE 2 TO GHOST-COUNT
           ELSE IF CMD-COUNT = '3'
               MOVE 3 TO GHOST-COUNT
           ELSE
               MOVE 1 TO GHOST-COUNT.
       SET-LEVEL-EXIT.
           EXIT.
       INIT-GAME.
           MOVE ' ' TO MAP-CELL (PLAYER-Y PLAYER-X).
           PERFORM RESET-GHOST VARYING WS-G FROM 1 BY 1
               UNTIL WS-G > GHOST-COUNT.
           PERFORM CLEAR-GHOST-CELL VARYING WS-G FROM 1 BY 1
               UNTIL WS-G > GHOST-COUNT.
           PERFORM COUNT-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
       RESET-GHOST.
           MOVE GS-X (WS-G) TO GH-X (WS-G).
           MOVE GS-Y (WS-G) TO GH-Y (WS-G).
           MOVE GS-DIR (WS-G) TO GH-DIR (WS-G).
       CLEAR-GHOST-CELL.
           MOVE GH-X (WS-G) TO WS-GX.
           MOVE GH-Y (WS-G) TO WS-GY.
           MOVE ' ' TO MAP-CELL (WS-GY WS-GX).
       COUNT-ROW.
           PERFORM COUNT-CELL THRU COUNT-CELL-EXIT
               VARYING WS-COL FROM 1 BY 1 UNTIL WS-COL > 20.
       COUNT-CELL.
           IF MAP-CELL (WS-ROW WS-COL) = '.'
               ADD 1 TO PELLETS-LEFT.
       COUNT-CELL-EXIT.
           EXIT.
       TURN-PARA.
           PERFORM PROCESS-CMD THRU PROCESS-CMD-EXIT.
           PERFORM READ-CMD.
       READ-CMD.
           READ COMMAND-FILE AT END MOVE 1 TO WS-EOF.
           MOVE CMD-CHAR TO WS-CMD.
       PROCESS-CMD.
           MOVE PLAYER-X TO NEW-X.
           MOVE PLAYER-Y TO NEW-Y.
           MOVE 'MOVED  ' TO WS-RESULT.
           IF WS-CMD = 'U' OR WS-CMD = 'u'
               SUBTRACT 1 FROM NEW-Y
               PERFORM TRY-MOVE
           ELSE IF WS-CMD = 'D' OR WS-CMD = 'd'
               ADD 1 TO NEW-Y
               PERFORM TRY-MOVE
           ELSE IF WS-CMD = 'L' OR WS-CMD = 'l'
               SUBTRACT 1 FROM NEW-X
               PERFORM TRY-MOVE
           ELSE IF WS-CMD = 'R' OR WS-CMD = 'r'
               ADD 1 TO NEW-X
               PERFORM TRY-MOVE
           ELSE IF WS-CMD = 'Q' OR WS-CMD = 'q'
               MOVE 1 TO WS-QUIT
               MOVE 'QUIT   ' TO GAME-STATE
           ELSE
               DISPLAY 'INVALID COMMAND ' WS-CMD.
       PROCESS-CMD-EXIT.
           EXIT.
       TRY-MOVE.
           ADD 1 TO TICK-COUNT.
           IF NEW-X < 1 OR NEW-X > 20 OR NEW-Y < 1 OR NEW-Y > 10
               MOVE 'BLOCKED' TO WS-RESULT
           ELSE IF MAP-CELL (NEW-Y NEW-X) = '#'
               MOVE 'BLOCKED' TO WS-RESULT
           ELSE
               MOVE NEW-X TO PLAYER-X
               MOVE NEW-Y TO PLAYER-Y
               PERFORM EAT-PELLET THRU EAT-PELLET-EXIT.
           PERFORM ROUND-END THRU ROUND-END-EXIT.
           PERFORM SET-STATE THRU SET-STATE-EXIT.
           PERFORM SHOW-STATE.
       ROUND-END.
           MOVE 0 TO WS-HIT.
           PERFORM CHECK-HIT THRU CHECK-HIT-EXIT.
           IF WS-HIT = 0 AND WS-WON = 0 AND AI-LEVEL > 0
               PERFORM GHOST-MOVE THRU GHOST-MOVE-EXIT
                   VARYING WS-G FROM 1 BY 1
                   UNTIL WS-G > GHOST-COUNT
               PERFORM CHECK-HIT THRU CHECK-HIT-EXIT.
           IF WS-HIT = 1
               PERFORM LOSE-LIFE THRU LOSE-LIFE-EXIT.
       ROUND-END-EXIT.
           EXIT.
       CHECK-HIT.
           PERFORM HIT-TEST THRU HIT-TEST-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
       CHECK-HIT-EXIT.
           EXIT.
       HIT-TEST.
           IF GH-X (WS-G) = PLAYER-X AND GH-Y (WS-G) = PLAYER-Y
               MOVE 1 TO WS-HIT.
       HIT-TEST-EXIT.
           EXIT.
       LOSE-LIFE.
           MOVE 0 TO WS-WON.
           SUBTRACT 1 FROM LIVES.
           IF LIVES = 0
               MOVE 1 TO WS-LOST
               MOVE 'LOST   ' TO WS-RESULT
           ELSE
               MOVE 'DIED   ' TO WS-RESULT
               MOVE 2 TO PLAYER-X
               MOVE 2 TO PLAYER-Y
               PERFORM RESET-GHOST VARYING WS-G FROM 1 BY 1
                   UNTIL WS-G > GHOST-COUNT
               IF PELLETS-LEFT = 0
                   MOVE 1 TO WS-WON.
       LOSE-LIFE-EXIT.
           EXIT.
       SET-STATE.
           IF WS-LOST = 1
               MOVE 'LOST   ' TO GAME-STATE
           ELSE IF WS-WON = 1
               MOVE 'WON    ' TO GAME-STATE
           ELSE
               MOVE 'RUNNING' TO GAME-STATE.
       SET-STATE-EXIT.
           EXIT.
       GHOST-MOVE.
           MOVE 0 TO CAND-N.
           MOVE GH-DIR (WS-G) TO WS-CUR.
           MOVE REV-D (WS-CUR) TO WS-REVD.
           PERFORM GHOST-PROBE THRU GHOST-PROBE-EXIT
               VARYING WS-D FROM 1 BY 1 UNTIL WS-D > 4.
           IF CAND-N = 0 AND AI-LEVEL > 1
               PERFORM TRY-REVERSE THRU TRY-REVERSE-EXIT.
           IF CAND-N > 0
               PERFORM CHOOSE-DIR THRU CHOOSE-DIR-EXIT
               PERFORM STEP-GHOST.
       GHOST-MOVE-EXIT.
           EXIT.
       GHOST-PROBE.
           COMPUTE G-NX = GH-X (WS-G) + DIR-DX (WS-D) - 1.
           COMPUTE G-NY = GH-Y (WS-G) + DIR-DY (WS-D) - 1.
           IF MAP-CELL (G-NY G-NX) NOT = '#'
               IF AI-LEVEL = 1 OR WS-D NOT = WS-REVD
                   ADD 1 TO CAND-N
                   MOVE WS-D TO CAND (CAND-N).
       GHOST-PROBE-EXIT.
           EXIT.
       TRY-REVERSE.
           MOVE WS-REVD TO WS-D.
           COMPUTE G-NX = GH-X (WS-G) + DIR-DX (WS-D) - 1.
           COMPUTE G-NY = GH-Y (WS-G) + DIR-DY (WS-D) - 1.
           IF MAP-CELL (G-NY G-NX) NOT = '#'
               MOVE 1 TO CAND-N
               MOVE WS-D TO CAND (1).
       TRY-REVERSE-EXIT.
           EXIT.
       CHOOSE-DIR.
           IF AI-LEVEL = 3
               PERFORM PICK-CHASE
           ELSE IF AI-LEVEL = 2 AND CAND-N = 1
               MOVE CAND (1) TO WS-D
           ELSE
               PERFORM PICK-RANDOM.
       CHOOSE-DIR-EXIT.
           EXIT.
       PICK-RANDOM.
           COMPUTE WS-WORK = GHOST-SEED * 75 + 74.
           DIVIDE WS-WORK BY 65537 GIVING WS-QUOT
               REMAINDER GHOST-SEED.
           DIVIDE GHOST-SEED BY CAND-N GIVING WS-QUOT
               REMAINDER WS-REM.
           ADD 1 TO WS-REM.
           MOVE CAND (WS-REM) TO WS-D.
       PICK-CHASE.
           MOVE 999 TO BEST-DIST.
           PERFORM CHASE-EVAL THRU CHASE-EVAL-EXIT
               VARYING WS-J FROM 1 BY 1 UNTIL WS-J > CAND-N.
       CHASE-EVAL.
           MOVE CAND (WS-J) TO WS-K.
           COMPUTE G-NX = GH-X (WS-G) + DIR-DX (WS-K) - 1.
           COMPUTE G-NY = GH-Y (WS-G) + DIR-DY (WS-K) - 1.
           COMPUTE DIST-X = G-NX - PLAYER-X.
           IF DIST-X < 0
               COMPUTE DIST-X = 0 - DIST-X.
           COMPUTE DIST-Y = G-NY - PLAYER-Y.
           IF DIST-Y < 0
               COMPUTE DIST-Y = 0 - DIST-Y.
           COMPUTE DIST-T = DIST-X + DIST-Y.
           IF DIST-T < BEST-DIST
               MOVE DIST-T TO BEST-DIST
               MOVE WS-K TO WS-D.
       CHASE-EVAL-EXIT.
           EXIT.
       STEP-GHOST.
           COMPUTE GH-X (WS-G) = GH-X (WS-G) + DIR-DX (WS-D) - 1.
           COMPUTE GH-Y (WS-G) = GH-Y (WS-G) + DIR-DY (WS-D) - 1.
           MOVE WS-D TO GH-DIR (WS-G).
       EAT-PELLET.
           IF MAP-CELL (PLAYER-Y PLAYER-X) = '.'
               MOVE ' ' TO MAP-CELL (PLAYER-Y PLAYER-X)
               ADD 10 TO SCORE
               SUBTRACT 1 FROM PELLETS-LEFT.
           IF PELLETS-LEFT = 0
               MOVE 1 TO WS-WON.
       EAT-PELLET-EXIT.
           EXIT.
       SHOW-STATE.
           MOVE TICK-COUNT TO ST-TURN.
           IF WS-RESULT = 'START  '
               MOVE ' ' TO ST-CMD
           ELSE
               MOVE WS-CMD TO ST-CMD.
           MOVE WS-RESULT TO ST-RESULT.
           MOVE PLAYER-X TO ST-X.
           MOVE PLAYER-Y TO ST-Y.
           MOVE SCORE TO ST-SCORE.
           MOVE GH-X (1) TO ST-GX.
           MOVE GH-Y (1) TO ST-GY.
           MOVE LIVES TO ST-LIVES.
           MOVE GAME-STATE TO ST-STATE.
           MOVE PELLETS-LEFT TO ST-LEFT.
           DISPLAY WS-STATUS-LINE.
           IF GHOST-COUNT > 1
               PERFORM SHOW-EXTRA THRU SHOW-EXTRA-EXIT.
           PERFORM SHOW-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
       SHOW-ROW.
           MOVE MAP-ROW (WS-ROW) TO WS-LINE.
           IF WS-ROW = PLAYER-Y
               MOVE 'P' TO WS-LINE-CELL (PLAYER-X).
           PERFORM OVERLAY-GHOST THRU OVERLAY-GHOST-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           DISPLAY WS-LINE.
       OVERLAY-GHOST.
           IF WS-ROW = GH-Y (WS-G)
               MOVE GH-X (WS-G) TO WS-GX
               MOVE 'G' TO WS-LINE-CELL (WS-GX).
       OVERLAY-GHOST-EXIT.
           EXIT.
       SHOW-EXTRA.
           MOVE GH-X (2) TO XL2-X.
           MOVE GH-Y (2) TO XL2-Y.
           IF GHOST-COUNT = 2
               DISPLAY WS-XL2
           ELSE
               MOVE GH-X (3) TO XL3-X
               MOVE GH-Y (3) TO XL3-Y
               DISPLAY WS-XL2 WS-XL3.
       SHOW-EXTRA-EXIT.
           EXIT.
