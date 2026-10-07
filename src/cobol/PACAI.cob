      * PACAI : GHOST MOVEMENT FOR ALL ACTIVE GHOSTS (PORTABLE).
      * AI-LEVEL 1 RANDOM, 2 PERSISTENT DIRECTION, 3 CHASE (MANHATTAN).
      * LCG SEED IN THE STATE (FIXED 12345) KEEPS RUNS REPRODUCIBLE.
      * WALL TESTS GO THROUGH PACMAP. NO NESTED SUBSCRIPTS (D13).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACAI.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  MAP-REQ COPY PACMREQ.
       01  WS-WORK               PIC 9(9).
       01  WS-QUOT               PIC 9(9).
       01  WS-REM                PIC 9(5).
       01  WS-D                  PIC 9.
       01  WS-G                  PIC 9.
       01  WS-J                  PIC 9.
       01  WS-K                  PIC 9.
       01  WS-CUR                PIC 9.
       01  WS-REVD               PIC 9.
       01  CAND-N                PIC 9.
       01  CAND-TABLE.
           05  CAND              PIC 9 OCCURS 4 TIMES.
       01  DIR-DATA              PIC X(8) VALUE '10120121'.
       01  DIR-TABLE REDEFINES DIR-DATA.
           05  DIR-ENTRY         OCCURS 4 TIMES.
               10  DIR-DX        PIC 9.
               10  DIR-DY        PIC 9.
       01  REV-DATA              PIC X(4) VALUE '2143'.
       01  REV-TABLE REDEFINES REV-DATA.
           05  REV-D             PIC 9 OCCURS 4 TIMES.
       01  G-NX                  PIC 99.
       01  G-NY                  PIC 99.
       01  DIST-X                PIC S99.
       01  DIST-Y                PIC S99.
       01  DIST-T                PIC S999.
       01  BEST-DIST             PIC S999.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       PROCEDURE DIVISION USING PAC-STATE.
       MAIN-PARA.
           PERFORM GHOST-MOVE THRU GHOST-MOVE-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           GOBACK.
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
           MOVE G-NX TO M-X.
           MOVE G-NY TO M-Y.
           MOVE 'WALL' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 0
               IF AI-LEVEL = 1 OR WS-D NOT = WS-REVD
                   ADD 1 TO CAND-N
                   MOVE WS-D TO CAND (CAND-N).
       GHOST-PROBE-EXIT.
           EXIT.
       TRY-REVERSE.
           MOVE WS-REVD TO WS-D.
           COMPUTE G-NX = GH-X (WS-G) + DIR-DX (WS-D) - 1.
           COMPUTE G-NY = GH-Y (WS-G) + DIR-DY (WS-D) - 1.
           MOVE G-NX TO M-X.
           MOVE G-NY TO M-Y.
           MOVE 'WALL' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 0
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
