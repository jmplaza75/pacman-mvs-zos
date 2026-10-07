      * MVS-3: PELLETS AND SCORE. COMMANDS U/D/L/R/Q, ONE PER CARD
      * (SYSIN). MAP LITERALS MUST MATCH MAPS/LEVEL1.TXT. THE START
      * CELL IS CLEARED AT INIT WITHOUT SCORING; PELLET = 10 POINTS.
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
           05  FILLER            PIC X(79).
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
       PROCEDURE DIVISION.
       MAIN-PARA.
           OPEN INPUT COMMAND-FILE.
           DISPLAY 'PACMAN MVS-3 PELLETS AND SCORE'.
           PERFORM INIT-GAME.
           MOVE 'START  ' TO WS-RESULT.
           PERFORM SHOW-STATE.
           PERFORM READ-CMD.
           PERFORM TURN-PARA
               UNTIL WS-EOF = 1 OR WS-QUIT = 1 OR WS-WON = 1.
           IF WS-WON = 1
               DISPLAY 'WIN'
           ELSE IF WS-QUIT = 1
               DISPLAY 'QUIT'
           ELSE
               DISPLAY 'EOF'.
           DISPLAY 'TURNS ' TICK-COUNT.
           DISPLAY 'SCORE ' SCORE.
           CLOSE COMMAND-FILE.
           STOP RUN.
       INIT-GAME.
           MOVE ' ' TO MAP-CELL (PLAYER-Y PLAYER-X).
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
           PERFORM SHOW-STATE.
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
           MOVE PELLETS-LEFT TO ST-LEFT.
           DISPLAY WS-STATUS-LINE.
           PERFORM SHOW-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
       SHOW-ROW.
           MOVE MAP-ROW (WS-ROW) TO WS-LINE.
           IF WS-ROW = PLAYER-Y
               MOVE 'P' TO WS-LINE-CELL (PLAYER-X).
           DISPLAY WS-LINE.
