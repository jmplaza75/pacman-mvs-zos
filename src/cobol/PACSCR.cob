      * PACSCR : MVS-G1 TSC RENDERER (DISPLAY LAYER). COMPOSES THE WHOLE
      * 80 X 24 COLOUR SCREEN AS A 3270 DATA STREAM IN PAC-DS FROM THE
      * GAME STATE (READ ONLY). COLOURS AND LAYOUT COME ONLY FROM THE
      * COPYBOOK PACPAL. CALLED BY PACDISP:  CALL 'PACSCR' USING
      * PAC-STATE PAC-REQ PAC-DS.  OPS: INVL (REMEMBER THE INVALID
      * COMMAND FOR THE NEXT SCREEN)  PRMT (COMPOSE THE SCREEN).
      * ORDERS: WCC X'C3', SBA X'11', SF X'1D', SA X'28', IC X'13'.
      * MVS-G2: WITH REQ-HILITE = 'Y' ADDS SA X'41' HIGHLIGHT ORDERS
      * (PLAYER/GHOSTS REVERSE, INVALID BLINK, INPUT UNDERSCORE).
      * MVS-G3: OPS PRMT (FULL OR PARTIAL SCREEN), TICK (GLYPH FRAME
      * ONLY), FULL (FORCED FULL). WITH REQ-REDRAW = 'P' EVERY SCREEN
      * IS FIRST COMPOSED AS A VIRTUAL 24 X 80 CELL IMAGE (VS-CUR) AND
      * ONLY THE CELLS THAT DIFFER FROM THE IMAGE ALREADY ON THE
      * TERMINAL (VS-PREV) ARE SENT (DS-KIND P / T, WRITE WITHOUT
      * ERASE). REQ-ANIM = 'Y' ALTERNATES THE P/G GLYPHS (PACPAL). THE
      * GAME STATE IS NEVER CHANGED: ONLY HOW IT IS DRAWN.
      * MVS-G4: REQ-GLYPHS G (GRAPHIC: CP310 PELLETS AND SPRITES SENT
      * AS GE X'08' + CODE, PAC-MAN FACING THE LAST HORIZONTAL MOVE) OR
      * B (BASE PELLET); IN BOTH, WALL CELLS ARE FILLED (BLANK, WALL
      * COLOUR, REVERSE) WHEN HIGHLIGHTING IS ON, ELSE '#'. C = THE G3
      * SCREENS. EVERY VIRTUAL CELL CARRIES A GE FLAG (CU-CS).
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
       01  WS-HCUR               PIC 999.
       01  WS-HV                 PIC 999.
       01  WS-HP                 PIC 999.
       01  WS-HG                 PIC 999.
       01  WS-HE                 PIC 999.
       01  WS-HN                 PIC 999.
       01  WS-TLEN               PIC 99.
       01  WS-TXT.
           05  TXT-CH            PIC X OCCURS 80 TIMES.
       01  WS-LINE               PIC X(20).
       01  WS-LINE-CELLS REDEFINES WS-LINE.
           05  LINE-CH           PIC X OCCURS 20 TIMES.
       01  CELL-COLOURS.
           05  CELL-COL          PIC 999 OCCURS 20 TIMES.
       01  CELL-HILITE.
           05  CELL-HI           PIC 999 OCCURS 20 TIMES.
       01  CELL-GES.
           05  CELL-GE           PIC 9 OCCURS 20 TIMES.
      * MVS-G4 GLYPH BYTES (BUILT ONCE FROM THE PACPAL VALUES).
       01  TAB-OK                PIC 9 VALUE 0.
       01  X-PEL-G               PIC X.
       01  X-PEL-B               PIC X.
       01  X-GPR                 PIC X.
       01  X-GPL                 PIC X.
       01  X-GPC                 PIC X.
       01  X-GG1                 PIC X.
       01  X-GG2                 PIC X.
       01  WS-FACE               PIC X VALUE 'R'.
       01  WS-HW                 PIC 999.
       01  MSG-ON                PIC 9 VALUE 0.
       01  MSG-LAST              PIC 9 VALUE 0.
       01  VS-MODE               PIC 9 VALUE 0.
       01  VS-POS                PIC 9(4).
       01  VS-COL                PIC 999.
       01  VS-HI                 PIC 999.
       01  VIS                   PIC 9 VALUE 1.
       01  PREV-OK               PIC 9 VALUE 0.
       01  WS-GP                 PIC X VALUE 'P'.
       01  WS-GG                 PIC X VALUE 'G'.
       01  WS-X                  PIC 9(4).
       01  IN-RUN                PIC 9.
       01  RUN-CO                PIC 999.
       01  RUN-HI                PIC 999.
       01  WS-CHG                PIC 9(4).
       01  WS-NOP                PIC 9.
       01  VS-CUR.
           05  CU-CH-G.
               10  CU-CH         PIC X OCCURS 1920 TIMES.
           05  CU-CO-G.
               10  CU-CO         PIC 999 OCCURS 1920 TIMES.
           05  CU-HI-G.
               10  CU-HI         PIC 999 OCCURS 1920 TIMES.
           05  CU-CS-G.
               10  CU-CS         PIC 9 OCCURS 1920 TIMES.
       01  VS-PREV.
           05  PV-CH-G.
               10  PV-CH         PIC X OCCURS 1920 TIMES.
           05  PV-CO-G.
               10  PV-CO         PIC 999 OCCURS 1920 TIMES.
           05  PV-HI-G.
               10  PV-HI         PIC 999 OCCURS 1920 TIMES.
           05  PV-CS-G.
               10  PV-CS         PIC 9 OCCURS 1920 TIMES.
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
           'PACMAN G2  U D L R + ENTER   Q QUIT   PA2 REDRAW'.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       01  PAC-DS COPY PACDS.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ PAC-DS.
       MAIN-PARA.
           IF TAB-OK = 0
               PERFORM INIT-TAB.
           IF REQ-OP = 'INVL'
               MOVE 1 TO MSG-ON
               MOVE REQ-CHAR TO INV-CHAR
           ELSE IF REQ-OP = 'PRMT'
               PERFORM DO-PRMT THRU DO-PRMT-EXIT
           ELSE IF REQ-OP = 'TICK'
               PERFORM DO-TICK THRU DO-TICK-EXIT
           ELSE IF REQ-OP = 'FULL'
               PERFORM DO-FULL THRU DO-FULL-EXIT.
           GOBACK.
       DO-PRMT.
           MOVE 0 TO DS-LEN.
           MOVE 'F' TO DS-KIND.
           PERFORM INIT-HI.
           IF REQ-ANIM = 'Y'
               PERFORM TOGGLE-VIS.
           PERFORM SET-FACE.
           PERFORM SET-GLYPHS.
           IF REQ-REDRAW = 'P'
               PERFORM PRMT-VS
           ELSE
               PERFORM COMPOSE.
           MOVE MSG-ON TO MSG-LAST.
           MOVE 0 TO MSG-ON.
       DO-PRMT-EXIT.
           EXIT.
       PRMT-VS.
      * VIRTUAL IMAGE FIRST; FULL SCREEN WHEN THE TERMINAL HAS NOTHING
      * KNOWN (FIRST SCREEN) OR THE LAST INPUT WAS A REDRAW REQUEST.
           PERFORM BUILD-VS.
           IF PREV-OK = 1 AND REQ-KIND NOT = 'RDR'
               PERFORM BUILD-PARTIAL.
           IF PREV-OK = 0 OR REQ-KIND = 'RDR'
               PERFORM COMPOSE.
           PERFORM KEEP-VS.
       DO-FULL.
           MOVE 0 TO DS-LEN.
           PERFORM INIT-HI.
           PERFORM SET-GLYPHS.
           MOVE MSG-LAST TO MSG-ON.
           PERFORM COMPOSE.
           MOVE 0 TO MSG-ON.
           MOVE 0 TO PREV-OK.
       DO-FULL-EXIT.
           EXIT.
       DO-TICK.
           MOVE 0 TO DS-LEN.
           IF REQ-ANIM = 'Y' AND REQ-REDRAW = 'P' AND PREV-OK = 1
               PERFORM TICK-BUILD.
       DO-TICK-EXIT.
           EXIT.
       INIT-HI.
           MOVE 0 TO WS-HP WS-HG WS-HE WS-HN WS-HW.
           IF REQ-HILITE = 'Y'
               MOVE HI-WALL TO WS-HW
               MOVE HI-PLAYER TO WS-HP
               MOVE HI-GHOST TO WS-HG
               MOVE HI-ERROR TO WS-HE
               MOVE HI-INPUT TO WS-HN.
           MOVE 0 TO WS-NOP.
       TOGGLE-VIS.
           IF VIS = 1
               MOVE 0 TO VIS
           ELSE
               MOVE 1 TO VIS.
           MOVE 0 TO WS-NOP.
       SET-GLYPHS.
           MOVE 'P' TO WS-GP.
           MOVE 'G' TO WS-GG.
           IF REQ-ANIM = 'Y' AND VIS = 0
               MOVE GLY-PLAYER-1 TO WS-GP
               MOVE GLY-GHOST-1 TO WS-GG.
           IF REQ-ANIM = 'Y' AND VIS = 1
               MOVE GLY-PLAYER-2 TO WS-GP
               MOVE GLY-GHOST-2 TO WS-GG.
           IF REQ-GLYPHS = 'G'
               PERFORM SET-GLYPHS-G.
           MOVE 0 TO WS-NOP.
       SET-GLYPHS-G.
      * MVS-G4 GRAPHIC SPRITES: OPEN MOUTH FACING / GHOST, OR (SECOND
      * ANIMATION FRAME) CLOSED MOUTH / GHOST WITH THE EYE.
           MOVE X-GPR TO WS-GP.
           IF WS-FACE = 'L'
               MOVE X-GPL TO WS-GP.
           MOVE X-GG1 TO WS-GG.
           IF REQ-ANIM = 'Y' AND VIS = 1
               MOVE X-GPC TO WS-GP
               MOVE X-GG2 TO WS-GG.
           MOVE 0 TO WS-NOP.
       SET-FACE.
      * PAC-MAN FACES THE LAST HORIZONTAL MOVE THAT WAS NOT BLOCKED;
      * VERTICAL MOVES, BUMPS AND INVALID INPUT KEEP THE FACING.
           IF (LAST-CMD = 'L' OR LAST-CMD = 'l')
                             AND LAST-RESULT NOT = 'BLOCKED'
               MOVE 'L' TO WS-FACE.
           IF (LAST-CMD = 'R' OR LAST-CMD = 'r')
                             AND LAST-RESULT NOT = 'BLOCKED'
               MOVE 'R' TO WS-FACE.
           MOVE 0 TO WS-NOP.
       INIT-TAB.
           MOVE PEL-G TO BW-N.
           MOVE BW-L TO X-PEL-G.
           MOVE PEL-B TO BW-N.
           MOVE BW-L TO X-PEL-B.
           MOVE GPL-RIGHT TO BW-N.
           MOVE BW-L TO X-GPR.
           MOVE GPL-LEFT TO BW-N.
           MOVE BW-L TO X-GPL.
           MOVE GPL-CLOSED TO BW-N.
           MOVE BW-L TO X-GPC.
           MOVE GGH-1 TO BW-N.
           MOVE BW-L TO X-GG1.
           MOVE GGH-2 TO BW-N.
           MOVE BW-L TO X-GG2.
           MOVE 1 TO TAB-OK.
       BUILD-VS.
           MOVE SPACES TO CU-CH-G.
           MOVE ALL '0' TO CU-CO-G.
           MOVE ALL '0' TO CU-HI-G.
           MOVE ALL '0' TO CU-CS-G.
           MOVE 1 TO VS-MODE.
           PERFORM COMPOSE-BODY.
           MOVE 0 TO VS-MODE.
       KEEP-VS.
           MOVE VS-CUR TO VS-PREV.
           MOVE 1 TO PREV-OK.
       BUILD-PARTIAL.
      * LOGICAL PARTIAL SCREEN: WCC (RESET MDT, RESTORE KEYBOARD), THE
      * CHANGED CELLS, THEN THE EMPTY INPUT FIELD WITH THE CURSOR.
           MOVE 0 TO DS-LEN.
           MOVE 'P' TO DS-KIND.
           MOVE 195 TO WS-BV.
           PERFORM PUT-BYTE.
           PERFORM DIFF-ALL.
           PERFORM PUT-FIELD-PART.
           PERFORM PUT-TAIL.
       TICK-BUILD.
      * VISUAL TICK: SAME IMAGE, OTHER GLYPH FRAME. WCC WITHOUT RESET
      * MDT SO THAT WHAT THE USER IS TYPING IS NOT LOST.
           PERFORM TOGGLE-VIS.
           PERFORM SET-GLYPHS.
           MOVE VS-PREV TO VS-CUR.
           PERFORM FLIP-ROW VARYING WS-I FROM 1 BY 1 UNTIL WS-I > 10.
           MOVE 'T' TO DS-KIND.
           MOVE 194 TO WS-BV.
           PERFORM PUT-BYTE.
           PERFORM DIFF-ALL.
           IF WS-CHG = 0
               MOVE 0 TO DS-LEN.
           IF WS-CHG NOT = 0
               PERFORM PUT-TAIL.
           PERFORM KEEP-VS.
       FLIP-ROW.
           PERFORM FLIP-CELL VARYING WS-COL FROM 1 BY 1
               UNTIL WS-COL > 20.
       FLIP-CELL.
      * SPRITE CELLS ARE FOUND BY GLYPH; GE CELLS (MVS-G4) BY THE GE
      * GLYPHS ONLY, SO A CP310 PELLET IS NEVER TAKEN FOR A SPRITE.
           COMPUTE WS-X = (LAY-BOARD-ROW + WS-I - 2) * 80
               + LAY-BOARD-COL + WS-COL - 1.
           IF CU-CS (WS-X) = 0 AND (CU-CH (WS-X) = GLY-PLAYER-1
                          OR CU-CH (WS-X) = GLY-PLAYER-2)
               MOVE WS-GP TO CU-CH (WS-X).
           IF CU-CS (WS-X) = 0 AND (CU-CH (WS-X) = GLY-GHOST-1
                          OR CU-CH (WS-X) = GLY-GHOST-2)
               MOVE WS-GG TO CU-CH (WS-X).
           IF CU-CS (WS-X) = 1 AND (CU-CH (WS-X) = X-GPR
                          OR CU-CH (WS-X) = X-GPL
                          OR CU-CH (WS-X) = X-GPC)
               MOVE WS-GP TO CU-CH (WS-X).
           IF CU-CS (WS-X) = 1 AND (CU-CH (WS-X) = X-GG1
                          OR CU-CH (WS-X) = X-GG2)
               MOVE WS-GG TO CU-CH (WS-X).
           MOVE 0 TO WS-NOP.
       DIFF-ALL.
           MOVE 0 TO IN-RUN.
           MOVE 0 TO RUN-CO.
           MOVE 0 TO RUN-HI.
           MOVE 0 TO WS-CHG.
           PERFORM DIFF-CELL VARYING WS-X FROM 1 BY 1
               UNTIL WS-X > 1920.
       DIFF-CELL.
           MOVE 0 TO WS-HV.
           IF CU-CH (WS-X) NOT = PV-CH (WS-X)
                          OR CU-CO (WS-X) NOT = PV-CO (WS-X)
                          OR CU-HI (WS-X) NOT = PV-HI (WS-X)
                          OR CU-CS (WS-X) NOT = PV-CS (WS-X)
               MOVE 1 TO WS-HV.
           IF WS-HV = 0
               MOVE 0 TO IN-RUN.
           IF WS-HV = 1
               PERFORM EMIT-CELL.
           MOVE 0 TO WS-NOP.
       EMIT-CELL.
           ADD 1 TO WS-CHG.
           COMPUTE WS-ADDR = WS-X - 1.
           DIVIDE WS-ADDR BY 80 GIVING WS-ROW REMAINDER WS-COL.
           ADD 1 TO WS-ROW.
           ADD 1 TO WS-COL.
           IF IN-RUN = 0 OR WS-COL = 1
               PERFORM PUT-SBA.
           MOVE 1 TO IN-RUN.
           IF CU-CO (WS-X) NOT = RUN-CO
               MOVE CU-CO (WS-X) TO RUN-CO
               MOVE RUN-CO TO WS-BV
               PERFORM PUT-COLOUR.
           IF CU-HI (WS-X) NOT = RUN-HI
               MOVE CU-HI (WS-X) TO RUN-HI
               MOVE RUN-HI TO WS-HV
               PERFORM PUT-HILITE.
           IF CU-CS (WS-X) = 1
               MOVE 8 TO WS-BV
               PERFORM PUT-BYTE.
           ADD 1 TO DS-LEN.
           MOVE CU-CH (WS-X) TO DS-BYTE (DS-LEN).
       PUT-FIELD-PART.
      * INPUT FIELD DATA BYTE (ROW 18, COL 15): BLANK AGAIN, CURSOR IN.
           MOVE LAY-CMD-ROW TO WS-ROW.
           MOVE 15 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE 19 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE PAL-HELP TO WS-BV.
           PERFORM PUT-COLOUR.
           IF WS-HN NOT = 0
               MOVE WS-HN TO WS-HV
               PERFORM PUT-HILITE.
           IF WS-HN = 0 AND RUN-HI NOT = 0
               MOVE 0 TO WS-HV
               PERFORM PUT-HILITE.
           MOVE 64 TO WS-BV.
           PERFORM PUT-BYTE.
           IF WS-HN NOT = 0
               MOVE 0 TO WS-HV
               PERFORM PUT-HILITE.
           MOVE 0 TO WS-NOP.
       PUT-TAIL.
           MOVE 40 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 0 TO WS-BV.
           PERFORM PUT-BYTE.
           PERFORM PUT-BYTE.
       COMPOSE.
           MOVE 0 TO DS-LEN.
           MOVE 'F' TO DS-KIND.
           MOVE 195 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 1 TO WS-ROW.
           MOVE 1 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE 29 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 96 TO WS-BV.
           PERFORM PUT-BYTE.
           PERFORM COMPOSE-BODY.
           PERFORM PUT-TAIL.
       COMPOSE-BODY.
           PERFORM SHOW-STATUS.
           IF GHOST-COUNT > 1
               PERFORM SHOW-GHOSTS.
           PERFORM SHOW-BOARD-ROW VARYING WS-I FROM 1 BY 1
               UNTIL WS-I > 10.
           IF MSG-ON = 1
               PERFORM SHOW-MESSAGE.
           PERFORM SHOW-COMMAND.
           IF VS-MODE = 0
               PERFORM SHOW-FIELD.
           PERFORM SHOW-HELP.
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
               MOVE PAL-PLAYER TO CELL-COL (PLAYER-X)
               MOVE WS-HP TO CELL-HI (PLAYER-X).
           PERFORM OVERLAY-GHOST THRU OVERLAY-GHOST-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           PERFORM GLYPH-CELL VARYING WS-COL FROM 1 BY 1
               UNTIL WS-COL > 20.
           MOVE ALL '0' TO CELL-GES.
           IF REQ-GLYPHS = 'G' OR REQ-GLYPHS = 'B'
               PERFORM PROF-CELL THRU PROF-CELL-EXIT
                   VARYING WS-COL FROM 1 BY 1 UNTIL WS-COL > 20.
           COMPUTE WS-ROW = LAY-BOARD-ROW + WS-I - 1.
           MOVE LAY-BOARD-COL TO WS-COL.
           PERFORM PUT-SBA.
           MOVE 0 TO WS-CUR.
           MOVE 0 TO WS-HCUR.
           IF VS-MODE = 1
               PERFORM VS-CELL VARYING WS-COL FROM 1 BY 1
                   UNTIL WS-COL > 20
           ELSE
               PERFORM PUT-CELL VARYING WS-COL FROM 1 BY 1
                   UNTIL WS-COL > 20.
           IF WS-HCUR NOT = 0
               MOVE 0 TO WS-HV
               PERFORM PUT-HILITE.
           MOVE 0 TO WS-HCUR.
       GLYPH-CELL.
           IF LINE-CH (WS-COL) = 'P'
               MOVE WS-GP TO LINE-CH (WS-COL).
           IF LINE-CH (WS-COL) = 'G'
               MOVE WS-GG TO LINE-CH (WS-COL).
           MOVE 0 TO WS-NOP.
       PROF-CELL.
      * MVS-G4: '#' -> FILLED BLOCK (BLANK + REVERSE, WALL COLOUR KEPT)
      * WHEN HIGHLIGHTING IS ON, ELSE '#' AS IT IS; '.' -> THE PELLET
      * GLYPH. IN GRAPHIC THE PELLETS AND SPRITES ARE GE CELLS.
           IF LINE-CH (WS-COL) = SPACE
               GO TO PROF-CELL-EXIT.
           IF LINE-CH (WS-COL) = '#'
               PERFORM WALL-CELL
               GO TO PROF-CELL-EXIT.
           IF REQ-GLYPHS = 'G'
               MOVE 1 TO CELL-GE (WS-COL).
           IF LINE-CH (WS-COL) = '.'
               PERFORM PELLET-GLYPH.
       PROF-CELL-EXIT.
           EXIT.
       WALL-CELL.
           IF WS-HW NOT = 0
               MOVE SPACE TO LINE-CH (WS-COL)
               MOVE WS-HW TO CELL-HI (WS-COL).
           MOVE 0 TO WS-NOP.
       PELLET-GLYPH.
           IF REQ-GLYPHS = 'G'
               MOVE X-PEL-G TO LINE-CH (WS-COL)
           ELSE
               MOVE X-PEL-B TO LINE-CH (WS-COL).
           MOVE 0 TO WS-NOP.
       VS-CELL.
           MOVE LINE-CH (WS-COL) TO CU-CH (VS-POS).
           MOVE CELL-GE (WS-COL) TO CU-CS (VS-POS).
           MOVE CELL-COL (WS-COL) TO CU-CO (VS-POS).
           MOVE CELL-HI (WS-COL) TO CU-HI (VS-POS).
           ADD 1 TO VS-POS.
       BASE-COLOUR.
           MOVE 0 TO CELL-COL (WS-COL).
           MOVE 0 TO CELL-HI (WS-COL).
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
           MOVE WS-HG TO CELL-HI (WS-GX).
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
           IF CELL-HI (WS-COL) NOT = WS-HCUR
               MOVE CELL-HI (WS-COL) TO WS-HCUR
               MOVE WS-HCUR TO WS-HV
               PERFORM PUT-HILITE.
           IF CELL-GE (WS-COL) = 1
               MOVE 8 TO WS-BV
               PERFORM PUT-BYTE.
           ADD 1 TO DS-LEN.
           MOVE LINE-CH (WS-COL) TO DS-BYTE (DS-LEN).
       SHOW-MESSAGE.
           MOVE LAY-MSG-ROW TO WS-ROW.
           MOVE 2 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-ERROR TO WS-BV.
           PERFORM PUT-COLOUR.
           IF WS-HE NOT = 0
               MOVE WS-HE TO WS-HV
               PERFORM PUT-HILITE.
           MOVE WS-INV TO WS-TXT.
           MOVE 17 TO WS-TLEN.
           PERFORM PUT-TEXT.
           IF WS-HE NOT = 0
               MOVE 0 TO WS-HV
               PERFORM PUT-HILITE.
           MOVE 0 TO WS-HV.
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
       SHOW-FIELD.
           MOVE 29 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 64 TO WS-BV.
           PERFORM PUT-BYTE.
           IF WS-HN NOT = 0
               MOVE WS-HN TO WS-HV
               PERFORM PUT-HILITE.
           MOVE 19 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 64 TO WS-BV.
           PERFORM PUT-BYTE.
           IF WS-HN NOT = 0
               MOVE 0 TO WS-HV
               PERFORM PUT-HILITE.
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
           COMPUTE VS-POS = (WS-ROW - 1) * 80 + WS-COL.
           MOVE 0 TO VS-COL.
           MOVE 0 TO VS-HI.
           COMPUTE WS-ADDR = VS-POS - 1.
           DIVIDE WS-ADDR BY 64 GIVING WS-HI REMAINDER WS-LO.
           ADD 1 TO WS-HI.
           ADD 1 TO WS-LO.
           IF VS-MODE = 0
               MOVE 17 TO WS-BV
               PERFORM PUT-BYTE
               MOVE ADDR-CODE (WS-HI) TO WS-BV
               PERFORM PUT-BYTE
               MOVE ADDR-CODE (WS-LO) TO WS-BV
               PERFORM PUT-BYTE.
           MOVE 0 TO WS-NOP.
       PUT-COLOUR.
           MOVE WS-BV TO WS-CUR.
           MOVE WS-BV TO VS-COL.
           IF VS-MODE = 0
               MOVE 40 TO WS-BV
               PERFORM PUT-BYTE
               MOVE 66 TO WS-BV
               PERFORM PUT-BYTE
               MOVE WS-CUR TO WS-BV
               PERFORM PUT-BYTE.
           MOVE 0 TO WS-NOP.
       PUT-HILITE.
      * SA X'41' + VALUE IN WS-HV (0 = DEFAULT, ENDS A HIGHLIGHT RUN).
           MOVE WS-HV TO VS-HI.
           IF VS-MODE = 0
               MOVE 40 TO WS-BV
               PERFORM PUT-BYTE
               MOVE 65 TO WS-BV
               PERFORM PUT-BYTE
               MOVE WS-HV TO WS-BV
               PERFORM PUT-BYTE.
           MOVE 0 TO WS-NOP.
       PUT-TEXT.
           PERFORM PUT-CHAR VARYING WS-I FROM 1 BY 1
               UNTIL WS-I > WS-TLEN.
       PUT-CHAR.
           IF VS-MODE = 1
               PERFORM VS-CHAR
           ELSE
               ADD 1 TO DS-LEN
               MOVE TXT-CH (WS-I) TO DS-BYTE (DS-LEN).
           MOVE 0 TO WS-NOP.
       VS-CHAR.
           MOVE TXT-CH (WS-I) TO CU-CH (VS-POS).
           MOVE VS-COL TO CU-CO (VS-POS).
           MOVE VS-HI TO CU-HI (VS-POS).
           MOVE 0 TO CU-CS (VS-POS).
           IF TXT-CH (WS-I) = SPACE
               MOVE 0 TO CU-CO (VS-POS)
               MOVE 0 TO CU-HI (VS-POS).
           ADD 1 TO VS-POS.
       PUT-BYTE.
           MOVE WS-BV TO BW-N.
           ADD 1 TO DS-LEN.
           MOVE BW-L TO DS-BYTE (DS-LEN).
