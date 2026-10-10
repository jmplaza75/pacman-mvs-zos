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
      * MVS-RT (D33): OP RTQF = THE ONE FRAME OF A REALTIME QUANTUM.
      * TSC/TSD: REQ-RTFR P = PRMT (INPUT FIELD RESET), F = PRMT AS A
      * FULL REDRAW, ELSE PACSCR RTQF (ALWAYS ONE STREAM). BAT: THE RT
      * STATUS LINE (QUANTUM, INPUTS, STEP KIND, DIRECTIONS, STATE) AND
      * THE GHOSTS LINE. END ADDS 'QUANTA' IN REALTIME ONLY.
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
       01  WS-NOP                PIC 9.
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
       01  WS-RT-LINE.
           05  FILLER            PIC X VALUE 'Q'.
           05  RT-Q              PIC 9(7).
           05  FILLER            PIC X(4) VALUE ' IN='.
           05  RT-IN             PIC X(8).
           05  FILLER            PIC X(3) VALUE ' K='.
           05  RT-K              PIC X.
           05  FILLER            PIC X(3) VALUE ' C='.
           05  RT-C              PIC X.
           05  FILLER            PIC X(3) VALUE ' R='.
           05  RT-R              PIC X.
           05  FILLER            PIC X(3) VALUE ' T='.
           05  RT-T              PIC 9.
           05  FILLER            PIC X(3) VALUE ' X='.
           05  RT-X              PIC 99.
           05  FILLER            PIC X(3) VALUE ' Y='.
           05  RT-Y              PIC 99.
           05  FILLER            PIC X(3) VALUE ' S='.
           05  RT-S              PIC 9(4).
           05  FILLER            PIC X(3) VALUE ' L='.
           05  RT-L              PIC 999.
           05  FILLER            PIC X(3) VALUE ' V='.
           05  RT-V              PIC 9.
           05  FILLER            PIC X(4) VALUE ' ST='.
           05  RT-ST             PIC X(7).
       01  WS-RTG1.
           05  FILLER            PIC X(4) VALUE '  G='.
           05  RG1-X             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  RG1-Y             PIC 99.
       01  WS-RTG2.
           05  FILLER            PIC X VALUE ' '.
           05  RG2-X             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  RG2-Y             PIC 99.
       01  WS-RTG3.
           05  FILLER            PIC X VALUE ' '.
           05  RG3-X             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  RG3-Y             PIC 99.
       01  WS-QUANTA.
           05  FILLER            PIC X(7) VALUE 'QUANTA '.
           05  QU-N              PIC 9(7).
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
               PERFORM SHOW-PROMPT THRU SHOW-PROMPT-EXIT
           ELSE IF REQ-OP = 'RTQF'
               PERFORM SHOW-RT.
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
           ELSE IF REQ-OP = 'RTQF'
               PERFORM SCR-RTQF THRU SCR-RTQF-EXIT
           ELSE IF REQ-OP = 'END '
               PERFORM SCR-ENDS
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
       SCR-ENDS.
      * MVS-GS: SCALED ONLY - ONE FINAL SCREEN WITH THE END BANNER, THEN
      * A SHORT PAUSE (PACPLAT WAIT, NO INPUT IS READ) BEFORE LINE MODE.
           IF REQ-SCALE NOT = 'N'
               MOVE 'ENDS' TO REQ-OP
               CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
               PERFORM SCR-ENDS-SEND.
           MOVE 'END ' TO REQ-OP.
       SCR-ENDS-SEND.
           IF DS-LEN > 0
               ADD DS-LEN TO M-CHARS
               MOVE 'SEND' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ PAC-DS
               MOVE 'WAIT' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           MOVE 0 TO WS-NOP.
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
       SCR-RTQF.
      * MVS-RT: EXACTLY ONE WRITE FOR THE QUANTUM, ALWAYS WITH THE
      * KEYBOARD RESTORE: AFTER ENTER / INVALID INPUT / REDRAW THE
      * PROMPT SCREEN (FIELD RESET; F = FULL), ELSE PACSCR RTQF.
           IF REQ-RTFR = 'P' OR REQ-RTFR = 'F'
               MOVE 'MOV' TO REQ-KIND
               IF REQ-RTFR = 'F'
                   MOVE 'RDR' TO REQ-KIND.
           IF REQ-RTFR = 'P' OR REQ-RTFR = 'F'
               MOVE 'PRMT' TO REQ-OP
               PERFORM SCR-PRMT THRU SCR-PRMT-EXIT
               MOVE 'RTQF' TO REQ-OP
               GO TO SCR-RTQF-EXIT.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS.
           ADD DS-LEN TO M-CHARS.
           MOVE 'SEND' TO REQ-OP.
           MOVE SPACE TO REQ-SENDST.
           CALL 'PACPLAT' USING PAC-REQ PAC-DS.
           MOVE 'PRMT' TO REQ-OP.
           IF REQ-SENDST = 'R'
               PERFORM SCR-RESEND.
           MOVE 'RTQF' TO REQ-OP.
       SCR-RTQF-EXIT.
           EXIT.
       SHOW-RT.
           MOVE REQ-RTQ TO RT-Q.
           MOVE REQ-RTIN TO RT-IN.
           MOVE REQ-STEP TO RT-K.
           MOVE REQ-RTCUR TO RT-C.
           MOVE REQ-RTREQ TO RT-R.
           MOVE REQ-RTTTL TO RT-T.
           MOVE PLAYER-X TO RT-X.
           MOVE PLAYER-Y TO RT-Y.
           MOVE SCORE TO RT-S.
           MOVE PELLETS-LEFT TO RT-L.
           MOVE LIVES TO RT-V.
           MOVE GAME-STATE TO RT-ST.
           DISPLAY WS-RT-LINE.
           MOVE GH-X (1) TO RG1-X.
           MOVE GH-Y (1) TO RG1-Y.
           IF GHOST-COUNT > 1
               MOVE GH-X (2) TO RG2-X
               MOVE GH-Y (2) TO RG2-Y.
           IF GHOST-COUNT > 2
               MOVE GH-X (3) TO RG3-X
               MOVE GH-Y (3) TO RG3-Y.
           IF GHOST-COUNT = 1
               DISPLAY WS-RTG1
           ELSE IF GHOST-COUNT = 2
               DISPLAY WS-RTG1 WS-RTG2
           ELSE
               DISPLAY WS-RTG1 WS-RTG2 WS-RTG3.
           ADD 2 TO M-LINES.
           ADD 85 TO M-CHARS.
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
           IF REQ-PLAY = 'R'
               MOVE REQ-RTQ TO QU-N
               DISPLAY WS-QUANTA.
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
