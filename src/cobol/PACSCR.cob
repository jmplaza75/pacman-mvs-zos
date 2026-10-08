      * PACSCR : MVS-G1 TSC RENDERER (DISPLAY LAYER). COMPOSES THE WHOLE
      * 80 X 24 COLOUR SCREEN AS A 3270 DATA STREAM IN PAC-DS FROM THE
      * GAME STATE (READ ONLY). COLOURS AND LAYOUT COME ONLY FROM THE
      * COPYBOOK PACPAL. CALLED BY PACDISP:  CALL 'PACSCR' USING
      * PAC-STATE PAC-REQ PAC-DS.  OPS: INVL (REMEMBER THE INVALID
      * COMMAND FOR THE NEXT SCREEN)  PRMT (COMPOSE THE SCREEN).
      * ORDERS: WCC X'C3', SBA X'11', SF X'1D', SA X'28', IC X'13'.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACSCR.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  PAC-PAL COPY PACPAL.
      * 3270 12-BIT BUFFER ADDRESS CODE TABLE (64 VALUES, DECIMAL).
       01  CODE-DATA.
           05  FILLER            PIC X(48) VALUE
               '064193194195196197198199200201074075076077078079'.
           05  FILLER            PIC X(48) VALUE
               '080209210211212213214215216217090091092093094095'.
           05  FILLER            PIC X(48) VALUE
               '096097226227228229230231232233106107108109110111'.
           05  FILLER            PIC X(48) VALUE
               '240241242243244245246247248249122123124125126127'.
       01  CODE-TABLE REDEFINES CODE-DATA.
           05  ADDR-CODE         PIC 999 OCCURS 64 TIMES.
       01  BW.
           05  BW-N              PIC 9(4) COMP.
       01  BW-X REDEFINES BW.
           05  FILLER            PIC X.
           05  BW-L              PIC X.
       01  WS-BV                 PIC 999.
       01  WS-ROW                PIC 99.
       01  WS-COL                PIC 99.
       01  WS-ADDR               PIC 9(4).
       01  WS-HI                 PIC 99.
       01  WS-LO                 PIC 99.
       01  WS-I                  PIC 99.
       01  WS-G                  PIC 9.
       01  WS-GX                 PIC 99.
       01  WS-CUR                PIC 999.
       01  WS-TLEN               PIC 99.
       01  WS-TXT.
           05  TXT-CH            PIC X OCCURS 80 TIMES.
       01  WS-LINE               PIC X(20).
       01  WS-LINE-CELLS REDEFINES WS-LINE.
           05  LINE-CH           PIC X OCCURS 20 TIMES.
       01  CELL-COLOURS.
           05  CELL-COL          PIC 999 OCCURS 20 TIMES.
       01  MSG-ON                PIC 9 VALUE 0.
       01  WS-INV.
           05  FILLER            PIC X(16) VALUE 'INVALID COMMAND '.
           05  INV-CHAR          PIC X.
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
       01  WS-XL23.
           05  FILLER            PIC X(3) VALUE 'G2='.
           05  X23-2X            PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  X23-2Y            PIC 99.
           05  FILLER            PIC X(4) VALUE ' G3='.
           05  X23-3X            PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  X23-3Y            PIC 99.
       01  WS-CMD-TXT            PIC X(12) VALUE 'COMMAND ===>'.
       01  WS-HELP-TXT           PIC X(48) VALUE
           'PACMAN G1  U D L R + ENTER   Q QUIT   PA2 REDRAW'.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       01  PAC-DS COPY PACDS.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ PAC-DS.
       MAIN-PARA.
           IF REQ-OP = 'INVL'
               MOVE 1 TO MSG-ON
               MOVE REQ-CHAR TO INV-CHAR
           ELSE IF REQ-OP = 'PRMT'
               PERFORM COMPOSE.
           GOBACK.
       COMPOSE.
           MOVE 0 TO DS-LEN.
           MOVE 195 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 1 TO WS-ROW.
           MOVE 1 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE 29 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 96 TO WS-BV.
           PERFORM PUT-BYTE.
           PERFORM SHOW-STATUS.
           IF GHOST-COUNT > 1
               PERFORM SHOW-GHOSTS.
           PERFORM SHOW-BOARD-ROW VARYING WS-I FROM 1 BY 1
               UNTIL WS-I > 10.
           IF MSG-ON = 1
               PERFORM SHOW-MESSAGE.
           PERFORM SHOW-COMMAND.
           PERFORM SHOW-HELP.
           MOVE 40 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 0 TO WS-BV.
           PERFORM PUT-BYTE.
           PERFORM PUT-BYTE.
           MOVE 0 TO MSG-ON.
       SHOW-STATUS.
           MOVE TICK-COUNT TO ST-TURN.
           MOVE LAST-CMD TO ST-CMD.
           MOVE LAST-RESULT TO ST-RESULT.
           MOVE PLAYER-X TO ST-X.
           MOVE PLAYER-Y TO ST-Y.
           MOVE SCORE TO ST-SCORE.
           MOVE PELLETS-LEFT TO ST-LEFT.
           MOVE GH-X (1) TO ST-GX.
           MOVE GH-Y (1) TO ST-GY.
           MOVE LIVES TO ST-LIVES.
           MOVE GAME-STATE TO ST-STATE.
           MOVE LAY-STATUS-ROW TO WS-ROW.
           MOVE 2 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE WS-STATUS-LINE TO WS-TXT.
           MOVE 61 TO WS-TLEN.
           PERFORM PUT-TEXT.
       SHOW-GHOSTS.
           MOVE GH-X (2) TO X23-2X.
           MOVE GH-Y (2) TO X23-2Y.
           MOVE WS-XL23 TO WS-TXT.
           MOVE 8 TO WS-TLEN.
           IF GHOST-COUNT = 3
               MOVE GH-X (3) TO X23-3X
               MOVE GH-Y (3) TO X23-3Y
               MOVE WS-XL23 TO WS-TXT
               MOVE 17 TO WS-TLEN.
           MOVE LAY-GHOSTS-ROW TO WS-ROW.
           MOVE 2 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           PERFORM PUT-TEXT.
       SHOW-BOARD-ROW.
      * CELL TEXT AS IN PACDISP (PLAYER, THEN GHOSTS IN INDEX ORDER).
           MOVE MAP-ROW (WS-I) TO WS-LINE.
           PERFORM BASE-COLOUR THRU BASE-COLOUR-EXIT
               VARYING WS-COL FROM 1 BY 1 UNTIL WS-COL > 20.
           IF WS-I = PLAYER-Y
               MOVE 'P' TO LINE-CH (PLAYER-X)
               MOVE PAL-PLAYER TO CELL-COL (PLAYER-X).
           PERFORM OVERLAY-GHOST THRU OVERLAY-GHOST-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           COMPUTE WS-ROW = LAY-BOARD-ROW + WS-I - 1.
           MOVE LAY-BOARD-COL TO WS-COL.
           PERFORM PUT-SBA.
           MOVE 0 TO WS-CUR.
           PERFORM PUT-CELL VARYING WS-COL FROM 1 BY 1
               UNTIL WS-COL > 20.
       BASE-COLOUR.
           MOVE 0 TO CELL-COL (WS-COL).
           IF LINE-CH (WS-COL) = '#'
               MOVE PAL-WALL TO CELL-COL (WS-COL).
           IF LINE-CH (WS-COL) = '.'
               MOVE PAL-PELLET TO CELL-COL (WS-COL).
       BASE-COLOUR-EXIT.
           EXIT.
       OVERLAY-GHOST.
           IF WS-I NOT = GH-Y (WS-G)
               GO TO OVERLAY-GHOST-EXIT.
           MOVE GH-X (WS-G) TO WS-GX.
           MOVE 'G' TO LINE-CH (WS-GX).
           IF WS-G = 1
               MOVE PAL-GHOST-1 TO CELL-COL (WS-GX).
           IF WS-G = 2
               MOVE PAL-GHOST-2 TO CELL-COL (WS-GX).
           IF WS-G = 3
               MOVE PAL-GHOST-3 TO CELL-COL (WS-GX).
       OVERLAY-GHOST-EXIT.
           EXIT.
       PUT-CELL.
      * A COLOUR ORDER ONLY WHEN A VISIBLE CELL CHANGES COLOUR.
           IF CELL-COL (WS-COL) NOT = 0
                             AND CELL-COL (WS-COL) NOT = WS-CUR
               MOVE CELL-COL (WS-COL) TO WS-CUR
               MOVE WS-CUR TO WS-BV
               PERFORM PUT-COLOUR.
           ADD 1 TO DS-LEN.
           MOVE LINE-CH (WS-COL) TO DS-BYTE (DS-LEN).
       SHOW-MESSAGE.
           MOVE LAY-MSG-ROW TO WS-ROW.
           MOVE 2 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-ERROR TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE WS-INV TO WS-TXT.
           MOVE 17 TO WS-TLEN.
           PERFORM PUT-TEXT.
       SHOW-COMMAND.
      * COMMAND ===> THEN A 1-BYTE UNPROTECTED FIELD WITH THE CURSOR.
           MOVE LAY-CMD-ROW TO WS-ROW.
           MOVE 2 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HELP TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE WS-CMD-TXT TO WS-TXT.
           MOVE 12 TO WS-TLEN.
           PERFORM PUT-TEXT.
           MOVE 29 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 64 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 19 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 64 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 29 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 96 TO WS-BV.
           PERFORM PUT-BYTE.
       SHOW-HELP.
           MOVE LAY-HELP-ROW TO WS-ROW.
           MOVE 2 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HELP TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE WS-HELP-TXT TO WS-TXT.
           MOVE 48 TO WS-TLEN.
           PERFORM PUT-TEXT.
       PUT-SBA.
           COMPUTE WS-ADDR = (WS-ROW - 1) * 80 + WS-COL - 1.
           DIVIDE WS-ADDR BY 64 GIVING WS-HI REMAINDER WS-LO.
           ADD 1 TO WS-HI.
           ADD 1 TO WS-LO.
           MOVE 17 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE ADDR-CODE (WS-HI) TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE ADDR-CODE (WS-LO) TO WS-BV.
           PERFORM PUT-BYTE.
       PUT-COLOUR.
           MOVE WS-BV TO WS-CUR.
           MOVE 40 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 66 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE WS-CUR TO WS-BV.
           PERFORM PUT-BYTE.
       PUT-TEXT.
           PERFORM PUT-CHAR VARYING WS-I FROM 1 BY 1
               UNTIL WS-I > WS-TLEN.
       PUT-CHAR.
           ADD 1 TO DS-LEN.
           MOVE TXT-CH (WS-I) TO DS-BYTE (DS-LEN).
       PUT-BYTE.
           MOVE WS-BV TO BW-N.
           ADD 1 TO DS-LEN.
           MOVE BW-L TO DS-BYTE (DS-LEN).
