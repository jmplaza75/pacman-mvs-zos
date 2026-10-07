      * MVS-5: LIVES AND GAME CYCLE. COMMANDS U/D/L/R/Q, ONE PER CARD.
      * OPTIONAL FIRST CARD AI0 (GHOST STILL) OR AI1 (RANDOM, DEFAULT).
      * MAP LITERALS MUST MATCH MAPS/LEVEL1.TXT. PLAYER AND GHOST START
      * CELLS ARE CLEARED AT INIT; PELLET = 10 POINTS. THREE LIVES;
      * A HIT COSTS ONE AND SENDS BOTH CHARACTERS TO THEIR START CELLS.
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
           05  FILLER            PIC X(77).
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
       01  GHOST-X               PIC 99 VALUE 19.
       01  GHOST-Y               PIC 99 VALUE 9.
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
       PROCEDURE DIVISION.
       MAIN-PARA.
           OPEN INPUT COMMAND-FILE.
           DISPLAY 'PACMAN MVS-5 LIVES AND CYCLE'.
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
           ELSE
               MOVE 1 TO AI-LEVEL.
       SET-LEVEL-EXIT.
           EXIT.
       INIT-GAME.
           MOVE ' ' TO MAP-CELL (PLAYER-Y PLAYER-X).
           MOVE ' ' TO MAP-CELL (GHOST-Y GHOST-X).
           PERFORM COUNT-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
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
           IF WS-HIT = 0 AND WS-WON = 0 AND AI-LEVEL = 1
               PERFORM GHOST-MOVE THRU GHOST-MOVE-EXIT
               PERFORM CHECK-HIT THRU CHECK-HIT-EXIT.
           IF WS-HIT = 1
               PERFORM LOSE-LIFE THRU LOSE-LIFE-EXIT.
       ROUND-END-EXIT.
           EXIT.
       CHECK-HIT.
           IF GHOST-X = PLAYER-X AND GHOST-Y = PLAYER-Y
               MOVE 1 TO WS-HIT.
       CHECK-HIT-EXIT.
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
               MOVE 19 TO GHOST-X
               MOVE 9 TO GHOST-Y
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
           PERFORM GHOST-PROBE THRU GHOST-PROBE-EXIT
               VARYING WS-D FROM 1 BY 1 UNTIL WS-D > 4.
           IF CAND-N > 0
               COMPUTE WS-WORK = GHOST-SEED * 75 + 74
               DIVIDE WS-WORK BY 65537 GIVING WS-QUOT
                   REMAINDER GHOST-SEED
               DIVIDE GHOST-SEED BY CAND-N GIVING WS-QUOT
                   REMAINDER WS-REM
               ADD 1 TO WS-REM
               MOVE CAND (WS-REM) TO WS-D
               COMPUTE GHOST-X = GHOST-X + DIR-DX (WS-D) - 1
               COMPUTE GHOST-Y = GHOST-Y + DIR-DY (WS-D) - 1.
       GHOST-MOVE-EXIT.
           EXIT.
       GHOST-PROBE.
           COMPUTE G-NX = GHOST-X + DIR-DX (WS-D) - 1.
           COMPUTE G-NY = GHOST-Y + DIR-DY (WS-D) - 1.
           IF MAP-CELL (G-NY G-NX) NOT = '#'
               ADD 1 TO CAND-N
               MOVE WS-D TO CAND (CAND-N).
       GHOST-PROBE-EXIT.
           EXIT.
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
           MOVE GHOST-X TO ST-GX.
           MOVE GHOST-Y TO ST-GY.
           MOVE LIVES TO ST-LIVES.
           MOVE GAME-STATE TO ST-STATE.
           MOVE PELLETS-LEFT TO ST-LEFT.
           DISPLAY WS-STATUS-LINE.
           PERFORM SHOW-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
       SHOW-ROW.
           MOVE MAP-ROW (WS-ROW) TO WS-LINE.
           IF WS-ROW = PLAYER-Y
               MOVE 'P' TO WS-LINE-CELL (PLAYER-X).
           IF WS-ROW = GHOST-Y
               MOVE 'G' TO WS-LINE-CELL (GHOST-X).
           DISPLAY WS-LINE.
