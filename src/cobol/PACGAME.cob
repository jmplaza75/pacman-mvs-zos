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
      *       MVS-GP2 (D37, ARC-ON = 1 ONLY): LEVELS 1-99 (START LEVEL
      *       REQ-START); A CLEARED MAZE IS REFILLED AND THE NEXT LEVEL
      *       STARTS (LEVEL 99 CLEARED = WON); PER-LEVEL TABLE K-LVL;
      *       FRUIT AT 30 / 70 ITEMS; ONE EXTRA LIFE AT 10000.
      *       MVS-RP RP.3 (D39 6, ARCADE REALTIME ONLY): THE QUANTA OF
      *       K-ARC ROW R AND K-LVL ARE DESIGNED AT 150 MS; RT-CONV
      *       CONVERTS FRIGHT, WARNING, EYES WAIT AND FRUIT TIME TO THE
      *       QUANTUM REQ-RTPER WHEN LOADED (150 MS = UNCHANGED).
      * RULES : SEE DOCS/DECISIONS.MD D7, D9, D11, D14, D36, D37.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACGAME.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY PACMREQ.
       01  GS-DATA               PIC X(15) VALUE '190930209419023'.
       01  GS-TABLE REDEFINES GS-DATA.
           05  GS-ENTRY          OCCURS 3 TIMES.
               10  GS-X          PIC 99.
               10  GS-Y          PIC 99.
               10  GS-DIR        PIC 9.
       01  WS-G                  PIC 9.
      * ARCADE CONSTANTS (THE ONLY PLACE). PER MODE, ROW 1 TURN
      * (TURNS), ROW 2 REALTIME (QUANTA): EYES WAIT, REALTIME FRIGHT
      * ACCUMULATOR STEP (MVS-GP1), FRUIT TIME (MVS-GP2).
       01  K-ARC-DATA            PIC X(16) VALUE
           'T0102030R0202060'.
       01  K-ARC REDEFINES K-ARC-DATA.
           05  K-ROW             OCCURS 2 TIMES.
               10  K-PLAY        PIC X.
               10  K-EYES        PIC 999.
               10  K-FINC        PIC 9.
               10  K-BT          PIC 999.
      * MVS-GP2 (D37) PER LEVEL, ROW = LEVEL (LEVELS 13-99 USE ROW 13):
      * AI BUMP, REALTIME NORMAL-GHOST STEP (OF 10), FRIGHT TURNS,
      * WARNING TURNS, FRIGHT QUANTA, WARNING QUANTA, FRUIT KIND AND
      * POINTS. EVERY LEVEL-DEPENDENT VALUE LIVES HERE.
       01  K-LVL-DATA.
           05  FILLER  PIC X(20) VALUE '008020005040010C0100'.
           05  FILLER  PIC X(20) VALUE '008017005034010S0300'.
           05  FILLER  PIC X(20) VALUE '108014005027010O0500'.
           05  FILLER  PIC X(20) VALUE '109010004020007O0500'.
           05  FILLER  PIC X(20) VALUE '209007003013007A0700'.
           05  FILLER  PIC X(20) VALUE '209017005034010A0700'.
           05  FILLER  PIC X(20) VALUE '209007003013007M1000'.
           05  FILLER  PIC X(20) VALUE '209007003013007M1000'.
           05  FILLER  PIC X(20) VALUE '209004002007003G2000'.
           05  FILLER  PIC X(20) VALUE '209017005034010G2000'.
           05  FILLER  PIC X(20) VALUE '209007003013007B3000'.
           05  FILLER  PIC X(20) VALUE '209004002007003B3000'.
           05  FILLER  PIC X(20) VALUE '209004002007003K5000'.
       01  K-LVL REDEFINES K-LVL-DATA.
           05  KL-ROW            OCCURS 13 TIMES.
               10  KL-AIB        PIC 9.
               10  KL-NUM        PIC 99.
               10  KL-FRT        PIC 999.
               10  KL-WRT        PIC 999.
               10  KL-FRR        PIC 999.
               10  KL-WRR        PIC 999.
               10  KL-BK         PIC X.
               10  KL-BV         PIC 9(4).
      * MVS-GP2 FIXED VALUES: FRUIT CELL, FRUIT THRESHOLDS (ITEMS EATEN
      * IN THE LEVEL), EXTRA LIFE SCORE, FINAL LEVEL, ROWS OF K-LVL.
       01  K-BX                  PIC 99 VALUE 10.
       01  K-BY                  PIC 99 VALUE 8.
       01  K-B1                  PIC 999 VALUE 30.
       01  K-B2                  PIC 999 VALUE 70.
       01  K-XLIFE               PIC 9(7) VALUE 10000.
       01  K-LAST                PIC 999 VALUE 99.
       01  K-NROW                PIC 99 VALUE 13.
       01  WS-LR                 PIC 99.
       01  WS-Q7                 PIC 9(7).
       01  WS-NOP                PIC 9.
       01  CHAIN-DATA            PIC X(16) VALUE '0200040008001600'.
       01  CHAIN-TABLE REDEFINES CHAIN-DATA.
           05  CHAIN-PTS         PIC 9(4) OCCURS 4 TIMES.
       01  WS-KR                 PIC 9.
       01  WS-Q                  PIC 999.
       01  WS-R                  PIC 9.
       01  NEW-X                 PIC 99.
       01  NEW-Y                 PIC 99.
       01  WS-CQ                 PIC 999.
       01  WS-CN                 PIC 9(7).
       01  WS-CD                 PIC 9(4).
       LINKAGE SECTION.
       COPY PACSTATE.
       COPY PACREQ.
       COPY PACARC.
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
           MOVE REQ-LEVEL TO ARC-AIB.
           MOVE REQ-COUNT TO GHOST-COUNT.
       DO-INIT.
           IF ARC-ON = 1
               PERFORM LEVEL-START THRU LEVEL-START-EXIT.
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
           IF ARC-ON = 1
               PERFORM ARC-TICKS.
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
           IF ARC-ON = 1 AND F-WON = 1
               PERFORM LEVEL-CLEAR THRU LEVEL-CLEAR-EXIT.
           PERFORM SET-STATE THRU SET-STATE-EXIT.
       DO-GHOSTS.
           PERFORM ROUND-END THRU ROUND-END-EXIT.
           IF ARC-ON = 1 AND F-WON = 1
               PERFORM LEVEL-CLEAR THRU LEVEL-CLEAR-EXIT.
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
               PERFORM ARC-LOSE THRU ARC-LOSE-EXIT.
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
           MOVE K-FINC (WS-KR) TO ARC-KFINC.
           MOVE 1 TO ARC-LEVEL.
           IF ARC-ON = 1 AND REQ-START > 0
               MOVE REQ-START TO ARC-LEVEL.
           MOVE 1 TO ARC-AIB.
           MOVE K-BX TO ARC-BX.
           MOVE K-BY TO ARC-BY.
           MOVE 0 TO ARC-XL.
           MOVE 0 TO ARC-TURNS.
           MOVE 0 TO ARC-EATN4.
           MOVE 0 TO ARC-FRUITS.
           MOVE 0 TO ARC-NDIE.
           MOVE '-----' TO ARC-EVF.
           MOVE 0 TO ARC-KWARN.
           MOVE 0 TO ARC-KNUM.
           MOVE 0 TO ARC-BV.
           MOVE SPACE TO ARC-BK.
           PERFORM LEVEL-RESET.
           IF ARC-ON = 1
               PERFORM LEVEL-ROW THRU LEVEL-ROW-EXIT.
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
           MOVE '-----' TO ARC-EVF.
           IF ARC-FR > 0
               SUBTRACT 1 FROM ARC-FR
               IF ARC-FR = 0
                   PERFORM FRIGHT-END THRU FRIGHT-END-EXIT
               ELSE
                   ADD 1 TO ARC-FTURN.
           PERFORM EYES-TICK THRU EYES-TICK-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           IF ARC-BT > 0
               SUBTRACT 1 FROM ARC-BT.
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
           PERFORM XLIFE THRU XLIFE-EXIT.
           IF M-FLAG > 0
               ADD 1 TO ARC-ITEMS
               PERFORM FRUIT-SPAWN THRU FRUIT-SPAWN-EXIT.
           PERFORM FRUIT-EAT THRU FRUIT-EAT-EXIT.
       ARC-EAT-EXIT.
           EXIT.
       FRIGHT-START.
      * A NEW POWER PELLET RESTARTS THE FRIGHT (FULL LENGTH, NOTHING
      * ADDED) AND THE CHAIN; EYES ARE NOT AFFECTED. NO FRIGHTENED
      * GHOST MOVES IN THE STEP WHERE THE FRIGHT STARTS.
           PERFORM PICK-ROW.
           PERFORM PICK-LR.
           MOVE KL-FRR (WS-LR) TO ARC-FR.
           MOVE KL-WRR (WS-LR) TO ARC-KWARN.
           IF WS-KR = 1
               MOVE KL-FRT (WS-LR) TO ARC-FR
               MOVE KL-WRT (WS-LR) TO ARC-KWARN
           ELSE
               MOVE ARC-FR TO WS-CQ
               PERFORM RT-CONV THRU RT-CONV-EXIT
               MOVE WS-CQ TO ARC-FR
               MOVE ARC-KWARN TO WS-CQ
               PERFORM RT-CONV THRU RT-CONV-EXIT
               MOVE WS-CQ TO ARC-KWARN.
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
           ADD 1 TO ARC-EATN4.
           DIVIDE ARC-EATN4 BY 1000 GIVING WS-Q7 REMAINDER ARC-EATEN.
           MOVE 'GHST' TO ARC-EVT.
           PERFORM XLIFE THRU XLIFE-EXIT.
           PERFORM PICK-ROW.
           MOVE 'E' TO ARC-GM (WS-G).
           MOVE K-EYES (WS-KR) TO ARC-GW (WS-G).
           IF WS-KR = 2
               MOVE ARC-GW (WS-G) TO WS-CQ
               PERFORM RT-CONV THRU RT-CONV-EXIT
               MOVE WS-CQ TO ARC-GW (WS-G).
           MOVE 0 TO ARC-GR (WS-G).
           PERFORM RESET-GHOST.
      * ------------- MVS-GP2 ARCADE (D37, ARC-ON = 1) -------------
       PICK-LR.
           MOVE ARC-LEVEL TO WS-LR.
           IF ARC-LEVEL > K-NROW
               MOVE K-NROW TO WS-LR.
           MOVE 0 TO WS-NOP.
       LEVEL-ROW.
      * THE ROW OF THE CURRENT LEVEL: AI = CONFIGURED + BUMP (AT MOST
      * 3; AI0 STAYS 0), REALTIME CADENCE, WARNING WINDOW, FRUIT.
           PERFORM PICK-LR.
           PERFORM PICK-ROW.
           MOVE ARC-AIB TO AI-LEVEL.
           IF ARC-AIB > 0
               ADD KL-AIB (WS-LR) TO AI-LEVEL.
           IF AI-LEVEL > 3
               MOVE 3 TO AI-LEVEL.
           MOVE KL-NUM (WS-LR) TO ARC-KNUM.
           MOVE KL-WRR (WS-LR) TO ARC-KWARN.
           IF WS-KR = 1
               MOVE KL-WRT (WS-LR) TO ARC-KWARN
           ELSE
               MOVE ARC-KWARN TO WS-CQ
               PERFORM RT-CONV THRU RT-CONV-EXIT
               MOVE WS-CQ TO ARC-KWARN.
           MOVE KL-BK (WS-LR) TO ARC-BK.
           MOVE KL-BV (WS-LR) TO ARC-BV.
       LEVEL-ROW-EXIT.
           EXIT.
       LEVEL-RESET.
      * PER-LEVEL STATE: ITEMS EATEN, FRUIT SPAWNS AND FRUIT TIMER.
           MOVE 0 TO ARC-ITEMS.
           MOVE 0 TO ARC-BN.
           MOVE 0 TO ARC-BT.
       LEVEL-START.
      * A NEW LEVEL (THE FIRST ONE TOO): NO FRIGHT, CHAIN OR EYES, NO
      * FRUIT, 4 POWER PELLETS (DO-INIT LOADS THE MAP), ITS ROW.
           PERFORM ARC-DEATH THRU ARC-DEATH-EXIT.
           PERFORM LEVEL-RESET.
           PERFORM LEVEL-ROW THRU LEVEL-ROW-EXIT.
       LEVEL-START-EXIT.
           EXIT.
       LEVEL-CLEAR.
      * THE MAZE IS EMPTY AT THE END OF THE STEP (AFTER THE LIFE LOSS):
      * LEVEL 99 = THE GAME IS WON; ELSE THE NEXT LEVEL, MAZE REFILLED,
      * PAC-MAN AND THE GHOSTS AT THEIR START CELLS. SCORE, LIVES, THE
      * EXTRA-LIFE FLAG, THE SEED AND THE GAME TOTALS ARE KEPT.
           MOVE 'C' TO ARC-EC.
           IF ARC-LEVEL NOT < K-LAST
               GO TO LEVEL-CLEAR-EXIT.
           ADD 1 TO ARC-LEVEL.
           MOVE 0 TO F-WON.
           MOVE 'CLEARED' TO LAST-RESULT.
           MOVE 2 TO PLAYER-X.
           MOVE 2 TO PLAYER-Y.
           PERFORM DO-INIT.
       LEVEL-CLEAR-EXIT.
           EXIT.
       ARC-LOSE.
      * A LIFE LOST: THE GP1 DEATH RESET, THE FRUIT IS REMOVED (ITS
      * THRESHOLDS STAY USED), FLAG D.
           PERFORM ARC-DEATH THRU ARC-DEATH-EXIT.
           MOVE 0 TO ARC-BT.
           MOVE 'D' TO ARC-ED.
           ADD 1 TO ARC-NDIE.
       ARC-LOSE-EXIT.
           EXIT.
       ARC-TICKS.
      * WIDE TURN COUNTER; TICK-COUNT MIRRORS ITS LOW 3 DIGITS.
           ADD 1 TO ARC-TURNS.
           DIVIDE ARC-TURNS BY 1000 GIVING WS-Q7 REMAINDER TICK-COUNT.
       XLIFE.
      * ONE EXTRA LIFE WHEN THE SCORE FIRST REACHES 10000 (ARC-XL IS
      * NEVER CLEARED DURING THE GAME), AT ONCE (BEFORE ANY HIT).
           IF ARC-XL = 1 OR ARC-SCORE < K-XLIFE
               GO TO XLIFE-EXIT.
           MOVE 1 TO ARC-XL.
           ADD 1 TO LIVES.
           MOVE 'X' TO ARC-EX.
       XLIFE-EXIT.
           EXIT.
       FRUIT-SPAWN.
      * AN ITEM WAS EATEN: THE 30TH AND THE 70TH OF THE LEVEL SHOW THE
      * FRUIT (A SHOWN ONE GETS ITS FULL TIME AGAIN).
           IF ARC-ITEMS NOT = K-B1 AND ARC-ITEMS NOT = K-B2
               GO TO FRUIT-SPAWN-EXIT.
           ADD 1 TO ARC-BN.
           PERFORM PICK-ROW.
           MOVE K-BT (WS-KR) TO ARC-BT.
           IF WS-KR = 2
               MOVE ARC-BT TO WS-CQ
               PERFORM RT-CONV THRU RT-CONV-EXIT
               MOVE WS-CQ TO ARC-BT.
           MOVE 'A' TO ARC-EA.
       FRUIT-SPAWN-EXIT.
           EXIT.
       FRUIT-EAT.
      * PAC-MAN ON THE FRUIT CELL WITH A FRUIT SHOWN (ENTERED, OR THE
      * FRUIT APPEARED UNDER HIM): ITS POINTS.
           IF ARC-BT = 0
               GO TO FRUIT-EAT-EXIT.
           IF PLAYER-X NOT = K-BX OR PLAYER-Y NOT = K-BY
               GO TO FRUIT-EAT-EXIT.
           MOVE 0 TO ARC-BT.
           ADD 1 TO ARC-FRUITS.
           ADD ARC-BV TO ARC-SCORE.
           MOVE ARC-SCORE TO SCORE.
           MOVE 'F' TO ARC-EF.
           PERFORM XLIFE THRU XLIFE-EXIT.
       FRUIT-EAT-EXIT.
           EXIT.
       RT-CONV.
      * MVS-RP RP.3 (D39 6), THE ONE QUANTUM CONVERSION (THE SAME
      * PARAGRAPH AS PACRT): WS-CQ QUANTA OF 150 MS -> THE SAME LENGTH
      * IN QUANTA OF REQ-RTPER MS, ROUNDED HALF UP (150 = IDENTITY).
      * NO PERIOD SET (NOT NUMERIC OR 0) = UNCHANGED.
           IF REQ-RTPER NOT NUMERIC
               GO TO RT-CONV-EXIT.
           IF REQ-RTPER = 0
               GO TO RT-CONV-EXIT.
           COMPUTE WS-CN = WS-CQ * 300 + REQ-RTPER.
           COMPUTE WS-CD = REQ-RTPER * 2.
           DIVIDE WS-CN BY WS-CD GIVING WS-CQ.
       RT-CONV-EXIT.
           EXIT.
