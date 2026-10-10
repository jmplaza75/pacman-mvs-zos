      * PACGAME : GAME RULES AND STATE (PORTABLE, NO TERMINAL I/O).
      * OPS : RSET  DEFAULTS (3 LIVES, PLAYER 2,2, AI1, 1 GHOST)
      *       CFG   APPLY REQ-LEVEL / REQ-COUNT FROM THE CONFIG CARD
      *       INIT  LOAD MAP, PLACE GHOSTS, COUNT PELLETS
      *       MOVE  ONE TURN (REQ-DIR, REQ-CHAR)   QUIT  EOF
      *       MVS-RT (D33): REQ-STEP P = PLAYER STEP ONLY (NO PACAI),
      *       G = GHOST STEP ONLY (NO PLAYER MOVE, NO TICK), ANYTHING
      *       ELSE = THE WHOLE TURN (B). SAME HIT / LIFE RULES.
      * RULES : SEE DOCS/DECISIONS.MD D7, D9, D11, D14.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACGAME.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  MAP-REQ COPY PACMREQ.
       01  GS-DATA               PIC X(15) VALUE '190930209419023'.
       01  GS-TABLE REDEFINES GS-DATA.
           05  GS-ENTRY          OCCURS 3 TIMES.
               10  GS-X          PIC 99.
               10  GS-Y          PIC 99.
               10  GS-DIR        PIC 9.
       01  WS-G                  PIC 9.
       01  NEW-X                 PIC 99.
       01  NEW-Y                 PIC 99.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'RSET'
               PERFORM DO-RESET
           ELSE IF REQ-OP = 'CFG '
               PERFORM DO-CONFIG
           ELSE IF REQ-OP = 'INIT'
               PERFORM DO-INIT
           ELSE IF REQ-OP = 'MOVE' AND REQ-STEP = 'G'
               PERFORM DO-GHOSTS
           ELSE IF REQ-OP = 'MOVE'
               PERFORM DO-MOVE
           ELSE IF REQ-OP = 'QUIT'
               PERFORM DO-QUIT
           ELSE IF REQ-OP = 'EOF '
               MOVE 1 TO F-EOF.
           GOBACK.
       DO-RESET.
           MOVE 2 TO PLAYER-X.
           MOVE 2 TO PLAYER-Y.
           MOVE 0 TO TICK-COUNT.
           MOVE 0 TO SCORE.
           MOVE 0 TO PELLETS-LEFT.
           MOVE 3 TO LIVES.
           MOVE 'READY  ' TO GAME-STATE.
           MOVE ' ' TO LAST-CMD.
           MOVE 'START  ' TO LAST-RESULT.
           MOVE 0 TO F-WON.
           MOVE 0 TO F-LOST.
           MOVE 0 TO F-QUIT.
           MOVE 0 TO F-EOF.
           MOVE 0 TO F-HIT.
           MOVE 1 TO AI-LEVEL.
           MOVE 1 TO GHOST-COUNT.
           MOVE 12345 TO GHOST-SEED.
       DO-CONFIG.
           MOVE REQ-LEVEL TO AI-LEVEL.
           MOVE REQ-COUNT TO GHOST-COUNT.
       DO-INIT.
           MOVE 'LOAD' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           MOVE PLAYER-X TO M-X.
           MOVE PLAYER-Y TO M-Y.
           MOVE 'CLR ' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           PERFORM RESET-GHOST VARYING WS-G FROM 1 BY 1
               UNTIL WS-G > GHOST-COUNT.
           PERFORM CLEAR-GHOST-CELL VARYING WS-G FROM 1 BY 1
               UNTIL WS-G > GHOST-COUNT.
           MOVE 'CNT ' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           MOVE M-COUNT TO PELLETS-LEFT.
       RESET-GHOST.
           MOVE GS-X (WS-G) TO GH-X (WS-G).
           MOVE GS-Y (WS-G) TO GH-Y (WS-G).
           MOVE GS-DIR (WS-G) TO GH-DIR (WS-G).
       CLEAR-GHOST-CELL.
           MOVE GH-X (WS-G) TO M-X.
           MOVE GH-Y (WS-G) TO M-Y.
           MOVE 'CLR ' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
       DO-QUIT.
           MOVE 1 TO F-QUIT.
           MOVE 'QUIT   ' TO GAME-STATE.
       DO-MOVE.
           MOVE REQ-CHAR TO LAST-CMD.
           MOVE PLAYER-X TO NEW-X.
           MOVE PLAYER-Y TO NEW-Y.
           MOVE 'MOVED  ' TO LAST-RESULT.
           PERFORM AIM-MOVE THRU AIM-MOVE-EXIT.
           ADD 1 TO TICK-COUNT.
           MOVE NEW-X TO M-X.
           MOVE NEW-Y TO M-Y.
           MOVE 'WALL' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 1
               MOVE 'BLOCKED' TO LAST-RESULT
           ELSE
               MOVE NEW-X TO PLAYER-X
               MOVE NEW-Y TO PLAYER-Y
               PERFORM EAT-PELLET THRU EAT-PELLET-EXIT.
           PERFORM ROUND-END THRU ROUND-END-EXIT.
           PERFORM SET-STATE THRU SET-STATE-EXIT.
       DO-GHOSTS.
           PERFORM ROUND-END THRU ROUND-END-EXIT.
           PERFORM SET-STATE THRU SET-STATE-EXIT.
       AIM-MOVE.
           IF REQ-DIR = 'U'
               SUBTRACT 1 FROM NEW-Y
           ELSE IF REQ-DIR = 'D'
               ADD 1 TO NEW-Y
           ELSE IF REQ-DIR = 'L'
               SUBTRACT 1 FROM NEW-X
           ELSE IF REQ-DIR = 'R'
               ADD 1 TO NEW-X.
       AIM-MOVE-EXIT.
           EXIT.
       EAT-PELLET.
           MOVE PLAYER-X TO M-X.
           MOVE PLAYER-Y TO M-Y.
           MOVE 'EAT ' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 1
               ADD 10 TO SCORE
               SUBTRACT 1 FROM PELLETS-LEFT.
           IF PELLETS-LEFT = 0
               MOVE 1 TO F-WON.
       EAT-PELLET-EXIT.
           EXIT.
       ROUND-END.
           MOVE 0 TO F-HIT.
           PERFORM CHECK-HIT THRU CHECK-HIT-EXIT.
           IF F-HIT = 0 AND F-WON = 0 AND AI-LEVEL > 0
                        AND REQ-STEP NOT = 'P'
               CALL 'PACAI' USING PAC-STATE
               PERFORM CHECK-HIT THRU CHECK-HIT-EXIT.
           IF F-HIT = 1
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
               MOVE 1 TO F-HIT.
       HIT-TEST-EXIT.
           EXIT.
       LOSE-LIFE.
           MOVE 0 TO F-WON.
           SUBTRACT 1 FROM LIVES.
           IF LIVES = 0
               MOVE 1 TO F-LOST
               MOVE 'LOST   ' TO LAST-RESULT
           ELSE
               MOVE 'DIED   ' TO LAST-RESULT
               MOVE 2 TO PLAYER-X
               MOVE 2 TO PLAYER-Y
               PERFORM RESET-GHOST VARYING WS-G FROM 1 BY 1
                   UNTIL WS-G > GHOST-COUNT
               IF PELLETS-LEFT = 0
                   MOVE 1 TO F-WON.
       LOSE-LIFE-EXIT.
           EXIT.
       SET-STATE.
           IF F-LOST = 1
               MOVE 'LOST   ' TO GAME-STATE
           ELSE IF F-WON = 1
               MOVE 'WON    ' TO GAME-STATE
           ELSE
               MOVE 'RUNNING' TO GAME-STATE.
       SET-STATE-EXIT.
           EXIT.
