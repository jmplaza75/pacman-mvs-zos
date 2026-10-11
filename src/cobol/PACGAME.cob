      * PACGAME : GAME RULES AND STATE (PORTABLE, NO TERMINAL I/O).
      * OPS : RSET  DEFAULTS (3 LIVES, PLAYER 2,2, AI1, 1 GHOST)
      *       CFG   APPLY REQ-LEVEL / REQ-COUNT FROM THE CONFIG CARD
      *       INIT  LOAD MAP, PLACE GHOSTS, COUNT PELLETS
      *       MOVE  ONE TURN (REQ-DIR, REQ-CHAR)   QUIT  EOF
      *       MVS-RT (D33): REQ-STEP P = PLAYER STEP ONLY (NO PACAI),
      *       G = GHOST STEP ONLY (NO PLAYER MOVE, NO TICK), ANYTHING
      *       ELSE = THE WHOLE TURN (B). SAME HIT / LIFE RULES.
      *       MVS-GP1 (D36, RULES(ARCADE), ARC-ON = 1 ONLY): ATIK =
      *       ONE FRIGHT TICK (TIMERS, EYES REVIVAL; TURN DOES IT AT
      *       EACH MOVE, PACRT AT EACH RUNNING QUANTUM); POWER PELLET
      *       'o' 50, FRIGHT, EATEN GHOSTS 200/400/800/1600 -> EYES AT
      *       HOME. STATE IN PAC-ARC; CLASSIC PARAGRAPHS UNCHANGED.
      * RULES : SEE DOCS/DECISIONS.MD D7, D9, D11, D14, D36.
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
      * MVS-GP1 CONSTANTS (THE ONLY PLACE; GP2 MAKES THEM PER LEVEL).
      * ROW 1 TURN (TURNS), ROW 2 REALTIME (QUANTA): FRIGHT LENGTH,
      * WARNING WINDOW, EYES WAIT, REALTIME FRIGHT ACCUMULATOR STEP.
       01  K-ARC-DATA            PIC X(22) VALUE
           'T0200050102R0400100202'.
       01  K-ARC REDEFINES K-ARC-DATA.
           05  K-ROW             OCCURS 2 TIMES.
               10  K-PLAY        PIC X.
               10  K-FR          PIC 999.
               10  K-WARN        PIC 999.
               10  K-EYES        PIC 999.
               10  K-FINC        PIC 9.
       01  CHAIN-DATA            PIC X(16) VALUE '0200040008001600'.
       01  CHAIN-TABLE REDEFINES CHAIN-DATA.
           05  CHAIN-PTS         PIC 9(4) OCCURS 4 TIMES.
       01  WS-KR                 PIC 9.
       01  WS-Q                  PIC 999.
       01  WS-R                  PIC 9.
       01  NEW-X                 PIC 99.
       01  NEW-Y                 PIC 99.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       01  PAC-ARC COPY PACARC.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ PAC-ARC.
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
           ELSE IF REQ-OP = 'ATIK'
               PERFORM DO-ATIK THRU DO-ATIK-EXIT
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
           PERFORM ARC-RESET THRU ARC-RESET-EXIT.
       DO-CONFIG.
           MOVE REQ-LEVEL TO AI-LEVEL.
           MOVE REQ-COUNT TO GHOST-COUNT.
       DO-INIT.
           MOVE 'LOAD' TO M-OP.
           IF ARC-ON = 1
               MOVE 'LDA ' TO M-OP
               MOVE 4 TO ARC-POWER.
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
           IF ARC-ON = 1 AND REQ-PLAY NOT = 'R'
               PERFORM ARC-TURN THRU ARC-TURN-EXIT.
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
           IF ARC-ON = 1
               PERFORM ARC-EAT THRU ARC-EAT-EXIT.
           IF PELLETS-LEFT = 0
               MOVE 1 TO F-WON.
       EAT-PELLET-EXIT.
           EXIT.
       ROUND-END.
           MOVE 0 TO F-HIT.
           PERFORM CHECK-HIT THRU CHECK-HIT-EXIT.
           IF F-HIT = 0 AND F-WON = 0 AND AI-LEVEL > 0
                        AND REQ-STEP NOT = 'P'
               CALL 'PACAI' USING PAC-STATE PAC-ARC
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
           IF ARC-ON = 1
               PERFORM ARC-HIT THRU ARC-HIT-EXIT
               GO TO HIT-TEST-EXIT.
           IF GH-X (WS-G) = PLAYER-X AND GH-Y (WS-G) = PLAYER-Y
               MOVE 1 TO F-HIT.
       HIT-TEST-EXIT.
           EXIT.
       LOSE-LIFE.
           MOVE 0 TO F-WON.
           SUBTRACT 1 FROM LIVES.
           IF ARC-ON = 1
               PERFORM ARC-DEATH THRU ARC-DEATH-EXIT.
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
      * ------------- MVS-GP1 ARCADE (D36, ARC-ON = 1) -------------
       ARC-RESET.
           MOVE 0 TO ARC-ON.
           IF REQ-RULES = 'A'
               MOVE 1 TO ARC-ON.
           MOVE 0 TO ARC-SCORE.
           MOVE 0 TO ARC-POWER.
           MOVE 0 TO ARC-EATEN.
           MOVE 1 TO ARC-MOVEN.
           MOVE SPACES TO ARC-EVT.
           MOVE 0 TO ARC-PTS.
           PERFORM PICK-ROW.
           MOVE K-WARN (WS-KR) TO ARC-KWARN.
           MOVE K-FINC (WS-KR) TO ARC-KFINC.
           PERFORM ARC-DEATH THRU ARC-DEATH-EXIT.
       ARC-RESET-EXIT.
           EXIT.
       PICK-ROW.
           MOVE 1 TO WS-KR.
           IF REQ-PLAY = 'R'
               MOVE 2 TO WS-KR.
           MOVE 0 TO WS-R.
       ARC-DEATH.
      * DEATH (AND RESET): NO FRIGHT, NO CHAIN, NO EYES, ALL NORMAL.
           MOVE 0 TO ARC-FR.
           MOVE 0 TO ARC-FTURN.
           MOVE 0 TO ARC-FACC.
           MOVE 0 TO ARC-CHAIN.
           MOVE 0 TO ARC-MOVEF.
           PERFORM ARC-NORMAL VARYING WS-G FROM 1 BY 1
               UNTIL WS-G > 3.
       ARC-DEATH-EXIT.
           EXIT.
       ARC-NORMAL.
           MOVE 'N' TO ARC-GM (WS-G).
           MOVE 0 TO ARC-GW (WS-G).
           MOVE 0 TO ARC-GR (WS-G).
       ARC-TURN.
      * TURN: ONE FRIGHT TICK PER MOVE; NORMAL GHOSTS MOVE EVERY TURN,
      * FRIGHTENED ONES WHEN ARC-FTURN IS EVEN AND > 0.
           PERFORM DO-ATIK THRU DO-ATIK-EXIT.
           MOVE 1 TO ARC-MOVEN.
           MOVE 0 TO ARC-MOVEF.
           IF ARC-FR = 0
               GO TO ARC-TURN-EXIT.
           DIVIDE ARC-FTURN BY 2 GIVING WS-Q REMAINDER WS-R.
           IF WS-R = 0 AND ARC-FTURN > 0
               MOVE 1 TO ARC-MOVEF.
       ARC-TURN-EXIT.
           EXIT.
       DO-ATIK.
           MOVE SPACES TO ARC-EVT.
           MOVE 0 TO ARC-PTS.
           IF ARC-FR > 0
               SUBTRACT 1 FROM ARC-FR
               IF ARC-FR = 0
                   PERFORM FRIGHT-END THRU FRIGHT-END-EXIT
               ELSE
                   ADD 1 TO ARC-FTURN.
           PERFORM EYES-TICK THRU EYES-TICK-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
       DO-ATIK-EXIT.
           EXIT.
       FRIGHT-END.
           MOVE 0 TO ARC-FR.
           MOVE 0 TO ARC-FTURN.
           MOVE 0 TO ARC-FACC.
           MOVE 0 TO ARC-CHAIN.
           PERFORM UNFRIGHT THRU UNFRIGHT-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
       FRIGHT-END-EXIT.
           EXIT.
       UNFRIGHT.
           IF ARC-GM (WS-G) = 'F'
               MOVE 'N' TO ARC-GM (WS-G)
               MOVE 0 TO ARC-GR (WS-G).
       UNFRIGHT-EXIT.
           EXIT.
       EYES-TICK.
      * EYES WAIT AT HOME; AT 0 THEY REVIVE NORMAL (EVEN DURING A
      * FRIGHT) UNLESS PAC-MAN STANDS ON THE HOME CELL (ONE MORE TICK).
           IF ARC-GM (WS-G) NOT = 'E'
               GO TO EYES-TICK-EXIT.
           SUBTRACT 1 FROM ARC-GW (WS-G).
           IF ARC-GW (WS-G) > 0
               GO TO EYES-TICK-EXIT.
           IF GH-X (WS-G) = PLAYER-X AND GH-Y (WS-G) = PLAYER-Y
               MOVE 1 TO ARC-GW (WS-G)
               GO TO EYES-TICK-EXIT.
           MOVE 'N' TO ARC-GM (WS-G).
           PERFORM RESET-GHOST.
       EYES-TICK-EXIT.
           EXIT.
       ARC-EAT.
      * THE CLASSIC LINES ABOVE ALREADY COUNTED A '.'; HERE THE ARCADE
      * SCORE, AND 'o' (M-FLAG 2): 50 POINTS AND A NEW FRIGHT.
           IF M-FLAG = 1
               ADD 10 TO ARC-SCORE.
           IF M-FLAG = 2
               ADD 50 TO ARC-SCORE
               SUBTRACT 1 FROM PELLETS-LEFT
               SUBTRACT 1 FROM ARC-POWER
               PERFORM FRIGHT-START THRU FRIGHT-START-EXIT.
           MOVE ARC-SCORE TO SCORE.
       ARC-EAT-EXIT.
           EXIT.
       FRIGHT-START.
      * A NEW POWER PELLET RESTARTS THE FRIGHT (FULL LENGTH, NOTHING
      * ADDED) AND THE CHAIN; EYES ARE NOT AFFECTED. NO FRIGHTENED
      * GHOST MOVES IN THE STEP WHERE THE FRIGHT STARTS.
           PERFORM PICK-ROW.
           MOVE K-FR (WS-KR) TO ARC-FR.
           MOVE K-WARN (WS-KR) TO ARC-KWARN.
           MOVE 0 TO ARC-FTURN.
           MOVE 0 TO ARC-FACC.
           MOVE 0 TO ARC-CHAIN.
           MOVE 0 TO ARC-MOVEF.
           MOVE 'POWR' TO ARC-EVT.
           PERFORM FRIGHTEN THRU FRIGHTEN-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
       FRIGHT-START-EXIT.
           EXIT.
       FRIGHTEN.
           IF ARC-GM (WS-G) NOT = 'E'
               MOVE 'F' TO ARC-GM (WS-G)
               MOVE 1 TO ARC-GR (WS-G).
       FRIGHTEN-EXIT.
           EXIT.
       ARC-HIT.
      * ON PAC-MAN'S CELL: EYES NOTHING, FRIGHTENED EATEN, NORMAL HIT
      * (GHOST INDEX ORDER; THE LIFE IS LOST AFTER THE WHOLE CHECK).
           IF GH-X (WS-G) NOT = PLAYER-X OR GH-Y (WS-G) NOT = PLAYER-Y
               GO TO ARC-HIT-EXIT.
           IF ARC-GM (WS-G) = 'N'
               MOVE 1 TO F-HIT
               GO TO ARC-HIT-EXIT.
           IF ARC-GM (WS-G) = 'F'
               PERFORM EAT-GHOST.
       ARC-HIT-EXIT.
           EXIT.
       EAT-GHOST.
           IF ARC-CHAIN < 4
               ADD 1 TO ARC-CHAIN.
           MOVE CHAIN-PTS (ARC-CHAIN) TO ARC-PTS.
           ADD ARC-PTS TO ARC-SCORE.
           MOVE ARC-SCORE TO SCORE.
           ADD 1 TO ARC-EATEN.
           MOVE 'GHST' TO ARC-EVT.
           PERFORM PICK-ROW.
           MOVE 'E' TO ARC-GM (WS-G).
           MOVE K-EYES (WS-KR) TO ARC-GW (WS-G).
           MOVE 0 TO ARC-GR (WS-G).
           PERFORM RESET-GHOST.
