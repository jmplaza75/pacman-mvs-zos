      * PACDSPX : ALTERNATIVE DISPLAY (MVS-G0 PROOF OF REPLACEABILITY).
      * SAME CONTRACT AS PACDISP (OPS HEAD STAT INVL END PRMT) BUT ONLY
      * THE STATUS LINE PER FRAME, NO BOARD. LINKED OVER THE 1.0 LOAD
      * MODULE AS CSECT PACDISP; THE CORE IS NOT RECOMPILED.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACDISP.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
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
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'HEAD'
               DISPLAY 'PACMAN ALT DISPLAY'
           ELSE IF REQ-OP = 'STAT'
               PERFORM SHOW-STATE
           ELSE IF REQ-OP = 'INVL'
               DISPLAY 'INVALID COMMAND ' REQ-CHAR
           ELSE IF REQ-OP = 'END '
               PERFORM SHOW-END THRU SHOW-END-EXIT
           ELSE IF REQ-OP = 'PRMT' AND REQ-MODE = 'TSO'
               DISPLAY 'CMD (U/D/L/R/Q)?'.
           GOBACK.
       SHOW-END.
           IF F-LOST = 1
               DISPLAY 'LOST'
           ELSE IF F-WON = 1
               DISPLAY 'WIN'
           ELSE IF F-QUIT = 1
               DISPLAY 'QUIT'
           ELSE
               DISPLAY 'EOF'.
           DISPLAY 'TURNS ' TICK-COUNT.
           DISPLAY 'SCORE ' SCORE.
           DISPLAY 'LIVES ' LIVES.
       SHOW-END-EXIT.
           EXIT.
       SHOW-STATE.
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
