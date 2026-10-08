      * PACDISP : DISPLAY ADAPTER (PLAIN TEXT, LEVEL G0). READS THE
      * STATE, NEVER CHANGES IT.  OPS : HEAD  STAT  INVL  END  PRMT
      * PRMT shows the input prompt in TSO mode only (no-op in BAT).
      * TSO: EVERY FRAME AFTER THE FIRST STARTS ON A FRESH SCREEN
      * (PACPLAT CLS), SO TSO NEVER PAGES A FRAME WITH '***'.
      * MVS-G0: COUNTS FRAMES, LINES, CHARACTERS AND SCREEN CLEARS;
      * THE TOTALS ARE PRINTED AFTER THE END LINES ONLY WHEN
      * REQ-METRIC = 'M' (OPTIONAL; NORMAL OUTPUT IS UNCHANGED).
      * MVS-G1: IN TSC (COLOUR FULL-SCREEN) AND TSD (ITS BATCH DRY RUN)
      * THE FRAME IS COMPOSED BY PACSCR AND SENT BY PACPLAT ONCE PER
      * READ (PRMT); NO LINE OUTPUT UNTIL THE END, WHEN PACPLAT FSOF
      * RESTORES LINE MODE BEFORE THE USUAL END LINES.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACDISP.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-LINE               PIC X(20).
       01  WS-LINE-CELLS REDEFINES WS-LINE.
           05  WS-LINE-CELL      PIC X OCCURS 20 TIMES.
       01  WS-ROW                PIC 99.
       01  WS-SAVE-OP            PIC X(4).
       01  WS-G                  PIC 9.
       01  WS-GX                 PIC 99.
       01  PAC-DS COPY PACDS.
       01  M-FRAMES              PIC 9(4) VALUE 0.
       01  M-LINES               PIC 9(5) VALUE 0.
       01  M-CHARS               PIC 9(7) VALUE 0.
       01  M-CLEARS              PIC 9(4) VALUE 0.
       01  WS-MET.
           05  FILLER            PIC X(15) VALUE 'METRICS FRAMES='.
           05  MT-FRAMES         PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' LINES='.
           05  MT-LINES          PIC 9(5).
           05  FILLER            PIC X(7) VALUE ' CHARS='.
           05  MT-CHARS          PIC 9(7).
           05  FILLER            PIC X(8) VALUE ' CLEARS='.
           05  MT-CLEARS         PIC 9(4).
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
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ.
       MAIN-PARA.
           IF REQ-MODE = 'TSC' OR REQ-MODE = 'TSD'
               PERFORM SCREEN-OP THRU SCREEN-OP-EXIT
           ELSE IF REQ-OP = 'HEAD'
               DISPLAY 'PACMAN MVS-6 SMART GHOSTS'
               ADD 1 TO M-LINES
               ADD 25 TO M-CHARS
           ELSE IF REQ-OP = 'STAT'
               PERFORM SHOW-STATE THRU SHOW-STATE-EXIT
           ELSE IF REQ-OP = 'INVL'
               DISPLAY 'INVALID COMMAND ' REQ-CHAR
               ADD 1 TO M-LINES
               ADD 17 TO M-CHARS
           ELSE IF REQ-OP = 'END '
               PERFORM SHOW-END THRU SHOW-END-EXIT
           ELSE IF REQ-OP = 'PRMT'
               PERFORM SHOW-PROMPT THRU SHOW-PROMPT-EXIT.
           GOBACK.
       SCREEN-OP.
           IF REQ-OP = 'STAT'
               ADD 1 TO M-FRAMES
           ELSE IF REQ-OP = 'INVL'
               CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
           ELSE IF REQ-OP = 'PRMT'
               PERFORM SCR-PRMT THRU SCR-PRMT-EXIT
           ELSE IF REQ-OP = 'TICK'
               PERFORM SCR-TICK THRU SCR-TICK-EXIT
           ELSE IF REQ-OP = 'END '
               MOVE 'FSOF' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ
               MOVE 'END ' TO REQ-OP
               PERFORM SHOW-END THRU SHOW-END-EXIT.
       SCREEN-OP-EXIT.
           EXIT.
       SCR-PRMT.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS.
           ADD DS-LEN TO M-CHARS.
           MOVE 'SEND' TO REQ-OP.
           MOVE SPACE TO REQ-SENDST.
           CALL 'PACPLAT' USING PAC-REQ PAC-DS.
           MOVE 'PRMT' TO REQ-OP.
           IF REQ-SENDST = 'R'
               PERFORM SCR-RESEND.
       SCR-PRMT-EXIT.
           EXIT.
       SCR-TICK.
      * MVS-G3: VISUAL TICK (GLYPH FRAME ONLY). NO CHANGE = NO SEND.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS.
           IF DS-LEN > 0
               ADD DS-LEN TO M-CHARS
               MOVE 'SEND' TO REQ-OP
               MOVE SPACE TO REQ-SENDST
               CALL 'PACPLAT' USING PAC-REQ PAC-DS
               MOVE 'TICK' TO REQ-OP
               IF REQ-SENDST = 'R'
                   PERFORM SCR-RESEND.
       SCR-TICK-EXIT.
           EXIT.
       SCR-RESEND.
      * THE PARTIAL SEND FAILED (PACPLAT SWITCHED TO FULL REDRAW, NO
      * ANIMATION): SEND THE WHOLE SCREEN INSTEAD.
           MOVE 'FULL' TO REQ-OP.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS.
           ADD DS-LEN TO M-CHARS.
           MOVE 'SEND' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ PAC-DS.
           MOVE 'PRMT' TO REQ-OP.
       NEW-SCREEN.
           MOVE REQ-OP TO WS-SAVE-OP.
           MOVE 'CLS ' TO REQ-OP.
           ADD 1 TO M-CLEARS.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE WS-SAVE-OP TO REQ-OP.
       SHOW-PROMPT.
           IF REQ-MODE = 'TSO'
               DISPLAY 'CMD (U/D/L/R/Q)?'
               ADD 1 TO M-LINES
               ADD 16 TO M-CHARS.
       SHOW-PROMPT-EXIT.
           EXIT.
       SHOW-END.
           IF F-LOST = 1
               DISPLAY 'LOST'
               ADD 4 TO M-CHARS
           ELSE IF F-WON = 1
               DISPLAY 'WIN'
               ADD 3 TO M-CHARS
           ELSE IF F-QUIT = 1
               DISPLAY 'QUIT'
               ADD 4 TO M-CHARS
           ELSE
               DISPLAY 'EOF'
               ADD 3 TO M-CHARS.
           DISPLAY 'TURNS ' TICK-COUNT.
           DISPLAY 'SCORE ' SCORE.
           DISPLAY 'LIVES ' LIVES.
           ADD 4 TO M-LINES.
           ADD 26 TO M-CHARS.
           IF REQ-METRIC = 'M'
               PERFORM SHOW-METRICS.
       SHOW-END-EXIT.
           EXIT.
       SHOW-METRICS.
           MOVE M-FRAMES TO MT-FRAMES.
           MOVE M-LINES TO MT-LINES.
           MOVE M-CHARS TO MT-CHARS.
           MOVE M-CLEARS TO MT-CLEARS.
           DISPLAY WS-MET.
       SHOW-STATE.
           ADD 1 TO M-FRAMES.
           IF REQ-MODE = 'TSO' AND LAST-RESULT NOT = 'START  '
               PERFORM NEW-SCREEN.
           MOVE TICK-COUNT TO ST-TURN.
           MOVE LAST-CMD TO ST-CMD.
           MOVE LAST-RESULT TO ST-RESULT.
           MOVE PLAYER-X TO ST-X.
           MOVE PLAYER-Y TO ST-Y.
           MOVE SCORE TO ST-SCORE.
           MOVE GH-X (1) TO ST-GX.
           MOVE GH-Y (1) TO ST-GY.
           MOVE LIVES TO ST-LIVES.
           MOVE GAME-STATE TO ST-STATE.
           MOVE PELLETS-LEFT TO ST-LEFT.
           DISPLAY WS-STATUS-LINE.
           ADD 1 TO M-LINES.
           ADD 61 TO M-CHARS.
           IF GHOST-COUNT > 1
               PERFORM SHOW-EXTRA THRU SHOW-EXTRA-EXIT.
           PERFORM SHOW-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
       SHOW-STATE-EXIT.
           EXIT.
       SHOW-ROW.
           MOVE MAP-ROW (WS-ROW) TO WS-LINE.
           IF WS-ROW = PLAYER-Y
               MOVE 'P' TO WS-LINE-CELL (PLAYER-X).
           PERFORM OVERLAY-GHOST THRU OVERLAY-GHOST-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           DISPLAY WS-LINE.
           ADD 1 TO M-LINES.
           ADD 20 TO M-CHARS.
       OVERLAY-GHOST.
           IF WS-ROW = GH-Y (WS-G)
               MOVE GH-X (WS-G) TO WS-GX
               MOVE 'G' TO WS-LINE-CELL (WS-GX).
       OVERLAY-GHOST-EXIT.
           EXIT.
       SHOW-EXTRA.
           MOVE GH-X (2) TO XL2-X.
           MOVE GH-Y (2) TO XL2-Y.
           ADD 1 TO M-LINES.
           IF GHOST-COUNT = 2
               DISPLAY WS-XL2
               ADD 8 TO M-CHARS
           ELSE
               MOVE GH-X (3) TO XL3-X
               MOVE GH-Y (3) TO XL3-Y
               DISPLAY WS-XL2 WS-XL3
               ADD 17 TO M-CHARS.
       SHOW-EXTRA-EXIT.
           EXIT.
