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
      * MVS-GS: REQ-SCALE 4 / 3 (T = 4 WITH A 1000-BYTE TEST LIMIT):
      * EACH LOGICAL CELL IS A 4X2 / 3X2 TILE OF THE VIRTUAL IMAGE
      * (WALL CONTOURS FROM A TABLE BUILT ONCE FROM THE MAP, HALF-BLOCK
      * SPRITES, PELLET); FULL SCREENS ARE ENCODED FROM THE IMAGE WITH
      * RA AND BLANK SKIPS (ENCODE-S); PARTIAL SCREENS AND TICKS ARE
      * THE G3 DIFF. OP ENDS = FINAL SCREEN WITH THE END BANNER. NO
      * STREAM EVER EXCEEDS DS-LIMIT (2048): ON OVERFLOW THE RENDERER
      * FALLS BACK TO THE G4 SCREENS FOR THE REST OF THE GAME.
      * MVS-GS GEOMETRY (D32): THE BUFFER IS GW X GH (REQ-CW/REQ-CH, SET
      * BY PACPLAT FROM CANVAS AND THE QUERY REPLY). FAMILIES: W (4X2,
      * WIDE >= 120 X 27: MAZE CENTRED, SIDE HUD), T (4X2, TALL >= 32
      * ROWS), B (THE 80 X 24 GS SCREENS) AND G (THE G1-G4 SCREENS),
      * B AND G AT AN ORIGIN CENTRED IN THE BUFFER (1,1 FOR 80 X 24:
      * STREAMS UNCHANGED). SIZE GUARD: W/T -> B -> G.
      * MVS-RT (D33): IN REALTIME (REQ-PLAY R) THE ANIMATION FRAME IS
      * REQ-VIS (PACRT), NOT A TOGGLE. OP RTQF = ONE QUANTUM: THE IMAGE
      * REBUILT FROM THE STATE, ONLY THE CHANGED CELLS, WCC C2 (TEXT
      * BEING TYPED IS KEPT), ALWAYS A STREAM (NO CHANGE = WCC + SA
      * RESET: THE KEYBOARD RESTORE OF THE QUANTUM); FULL REDRAW OR NO
      * IMAGE ON THE TERMINAL YET = PRMT. RT3: WHILE PAUSED (REQ-RTSTAT
      * PAUS) THE MESSAGE ROW SHOWS THE ' PAUSED ' BANNER (HELP COLOUR,
      * REVERSE) INSTEAD OF A MESSAGE.
      * MVS-GP1 (D36, ARC-ON = 1, DOCS/GP1-POWER.MD 6): POWER PELLET
      * 'o' (SCALED: SPRITE 6), BLINKING WITH HIGHLIGHTING; FRIGHTENED
      * GHOSTS BLUE / WHITE IN THE WARNING WINDOW (NOT REVERSED OUTSIDE
      * THE SPRITES, SCALED EYES NOT REVERSED); EYES '"' (SCALED:
      * SPRITE 7) DRAWN UNDER PAC-MAN AND THE OTHER GHOSTS; THE ARCADE
      * STATUS LINE (7-DIGIT SCORE, PW, FR), TALL SCORE LINE, WIDE HUD
      * SCORE AND GHOST COLOURS, ARCADE TITLE. CALLED WITH PAC-ARC.
      * MVS-GP2 (D37, DOCS/GP2-PROGRESSION.MD 11): FRUIT '%' AT ARC-BX/
      * ARC-BY WHILE ARC-BT > 0 (SCALED: SPRITE 8), GREEN, UNDER THE
      * EYES, PAC-MAN AND THE GHOSTS; THE STATUS LINE SHOWS FR, LEVEL
      * AND FRUIT KIND (PW DROPPED: THE BOARD SHOWS THE 'o'); WIDE HUD
      * LEVEL + FRUIT NAME AND POINTS; TALL: LEVEL IN THE TITLE ROW,
      * FRUIT ON THE SCORE LINE.
      * MVS-RP (D39, DOCS/RP-POLISH.MD 2-5, ARC-ON = 1 ONLY): RP-STATE
      * DECIDES PER SCREEN: READY! OVER THE CENTRAL WALL BAR (TURN: NO
      * MOVE YET OR THE DEATH / CLEAR TURN; REALTIME: WAIT, FREEZE
      * QUANTA 4..1), THE DEATH ANIMATION (REALTIME FREEZE QUANTA 10..5
      * AFTER A DEATH: 6 FRAMES AT REQ-DTHX/REQ-DTHY, ACTORS HIDDEN),
      * THE SCORE POPUP OF AN EATEN GHOST / FRUIT (FROM ARC-EATN4 /
      * ARC-FRUITS; 6 QUANTA, TURN: ITS TURN; SCALED IN THE TILE,
      * UNSCALED ON THE MESSAGE ROW), THE HUD HIGH SCORE (REQ-HSST R/Z:
      * MAX(REQ-HISCORE, ARC-SCORE)) AND THE END LINE OF OP ENDS. A
      * SCREEN TOO LONG WITH THEM IS FIRST REBUILT WITHOUT THEM (FULL,
      * SAME LAYOUT); ONLY THEN THE SIZE GUARD STEPS DOWN.
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
       01  WS-COL                PIC 999.
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
               10  CU-CH         PIC X OCCURS 4095 TIMES.
           05  CU-CO-G.
               10  CU-CO         PIC 999 OCCURS 4095 TIMES.
           05  CU-HI-G.
               10  CU-HI         PIC 999 OCCURS 4095 TIMES.
           05  CU-CS-G.
               10  CU-CS         PIC 9 OCCURS 4095 TIMES.
       01  VS-PREV.
           05  PV-CH-G.
               10  PV-CH         PIC X OCCURS 4095 TIMES.
           05  PV-CO-G.
               10  PV-CO         PIC 999 OCCURS 4095 TIMES.
           05  PV-HI-G.
               10  PV-HI         PIC 999 OCCURS 4095 TIMES.
           05  PV-CS-G.
               10  PV-CS         PIC 9 OCCURS 4095 TIMES.
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
      * MVS-GS SCALED RENDERER.
       01  WS-HELP-S             PIC X(48) VALUE
           'PACMAN GS  U D L R + ENTER   Q QUIT   PA2 REDRAW'.
       01  WS-HELP-G             PIC X(48).
       01  SC-INIT               PIC 9 VALUE 0.
       01  SC-ON                 PIC 9 VALUE 0.
       01  SC-W                  PIC 9 VALUE 4.
       01  SC-BROW               PIC 99.
       01  SC-BCOL               PIC 999.
       01  GW                    PIC 999 VALUE 80.
       01  GH                    PIC 999 VALUE 24.
       01  G-CELLS               PIC 9(5) VALUE 1920.
       01  VS-ROWS               PIC 999 VALUE 24.
       01  VS-N                  PIC 9(4) VALUE 1920.
       01  ORG-R                 PIC 99 VALUE 1.
       01  ORG-C                 PIC 999 VALUE 1.
       01  FAM                   PIC X VALUE 'G'.
       01  W-C0                  PIC 999.
       01  W-B0                  PIC 99.
       01  W-L                   PIC 999.
       01  W-R                   PIC 999.
       01  W-K                   PIC 9.
       01  HUD-LINE.
           05  HL-LABEL          PIC X(8).
           05  HL-VALUE          PIC X(9).
       01  HUD-NUM4              PIC 9(4).
       01  HUD-NUM3              PIC 999.
       01  HUD-LAST.
           05  HL-CMD            PIC X.
           05  FILLER            PIC X VALUE SPACE.
           05  HL-RES            PIC X(7).
       01  HUD-GH.
           05  HG-X              PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  HG-Y              PIC 99.
       01  HUD-AI.
           05  FILLER            PIC X(10) VALUE 'GHOSTS  AI'.
           05  HA-LEVEL          PIC 9.
       01  TALL-LINE.
           05  FILLER            PIC X(6) VALUE 'SCORE '.
           05  TL-SCORE          PIC 9(4).
           05  FILLER            PIC X(11) VALUE '   PELLETS '.
           05  TL-PEL            PIC 999.
           05  FILLER            PIC X(8) VALUE '   TURN '.
           05  TL-TURN           PIC 999.
           05  FILLER            PIC X(9) VALUE '   LIVES '.
       01  DS-LIMIT              PIC 9(4) VALUE 2048.
       01  DS-OVF                PIC 9 VALUE 0.
       01  WS-CHB                PIC X.
       01  BAN-ON                PIC 9 VALUE 0.
       01  SV-LAY.
           05  SV-STATUS-ROW     PIC 99.
           05  SV-GHOSTS-ROW     PIC 99.
           05  SV-GHOSTS-COL     PIC 99.
           05  SV-MSG-ROW        PIC 99.
           05  SV-CMD-ROW        PIC 99.
           05  SV-HELP-ROW       PIC 99.
           05  SV-HELP-COL       PIC 99.
           05  SV-SF-ROW         PIC 99.
           05  SV-MSG-COL        PIC 999.
           05  SV-CMD-COL        PIC 999.
           05  SV-STATUS-COL     PIC 999.
       01  SPR-PAC               PIC 9 VALUE 1.
       01  SPR-GH                PIC 9 VALUE 4.
       01  SPR-NO                PIC 99.
       01  SPR-4-T.
           05  SPR-4-CH          PIC X OCCURS 96 TIMES.
       01  SPR-4-R REDEFINES SPR-4-T.
           05  SPR-4-A           PIC X(40).
           05  SPR-4-B           PIC X(16).
           05  SPR-4-C           PIC X(8).
           05  SPR-4-D           PIC X(32).
       01  SPR-3-T.
           05  SPR-3-CH          PIC X OCCURS 72 TIMES.
       01  SPR-3-R REDEFINES SPR-3-T.
           05  SPR-3-A           PIC X(30).
           05  SPR-3-B           PIC X(12).
           05  SPR-3-C           PIC X(6).
           05  SPR-3-D           PIC X(24).
       01  SPR-FR                PIC 9 VALUE 0.
       01  WS-HPW                PIC 999 VALUE 0.
       01  HUD-NUM7              PIC 9(7).
       01  WS-ARC-ST.
           05  FILLER            PIC X VALUE 'T'.
           05  AS-TURN           PIC 999.
           05  FILLER            PIC X VALUE ' '.
           05  AS-CMD            PIC X.
           05  FILLER            PIC X VALUE ' '.
           05  AS-RESULT         PIC X(7).
           05  FILLER            PIC X(3) VALUE ' S='.
           05  AS-SCORE          PIC 9(7).
           05  FILLER            PIC X(3) VALUE ' L='.
           05  AS-LEFT           PIC 999.
           05  FILLER            PIC X(3) VALUE ' V='.
           05  AS-LIVES          PIC 9.
           05  FILLER            PIC X(4) VALUE ' ST='.
           05  AS-STATE          PIC X(7).
           05  FILLER            PIC X(4) VALUE ' FR='.
           05  AS-FR             PIC 999.
           05  FILLER            PIC X(4) VALUE ' LV='.
           05  AS-LV             PIC 99.
           05  FILLER            PIC X VALUE ' '.
           05  AS-BK             PIC X.
           05  FILLER            PIC X VALUE SPACE.
       01  HUD-LVL.
           05  FILLER            PIC X(8) VALUE 'LEVEL   '.
           05  HV-LV             PIC 99.
       01  HUD-LVT.
           05  FILLER            PIC X(6) VALUE 'LEVEL '.
           05  HT-LV             PIC 99.
       01  HUD-FRT.
           05  HF-NAME           PIC X(10).
           05  FILLER            PIC X VALUE ' '.
           05  HF-BV             PIC 9(4).
       01  WS-FK                 PIC 9.
       01  TALL-LINE-A.
           05  FILLER            PIC X(6) VALUE 'SCORE '.
           05  TA-SCORE          PIC 9(7).
           05  FILLER            PIC X(9) VALUE ' PELLETS '.
           05  TA-PEL            PIC 999.
           05  FILLER            PIC X(7) VALUE '  TURN '.
           05  TA-TURN           PIC 999.
           05  FILLER            PIC X(9) VALUE '   LIVES '.
       01  SPR-C                 PIC X.
       01  CT-OK                 PIC 9 VALUE 0.
       01  CT-TABLE.
           05  CT-CODE           PIC 999 OCCURS 1600 TIMES.
       01  CX                    PIC 99.
       01  CY                    PIC 99.
       01  SR                    PIC 9.
       01  SC                    PIC 9.
       01  CT-BASE               PIC 9(4).
       01  CT-K                  PIC 9(4).
       01  WX                    PIC 99.
       01  WY                    PIC 99.
       01  WW                    PIC 9.
       01  NB-N                  PIC 9.
       01  NB-S                  PIC 9.
       01  NB-W                  PIC 9.
       01  NB-E                  PIC 9.
       01  NB-NW                 PIC 9.
       01  NB-NE                 PIC 9.
       01  NB-SW                 PIC 9.
       01  NB-SE                 PIC 9.
       01  CN-V                  PIC 9.
       01  CN-H                  PIC 9.
       01  CN-D                  PIC 9.
       01  CN-OUT                PIC 999.
       01  CN-IN                 PIC 999.
       01  CN-RES                PIC 999.
       01  TL-CH                 PIC X.
       01  TL-CO                 PIC 999.
       01  TL-HI                 PIC 999.
       01  TL-CS                 PIC 9.
       01  TL-KIND               PIC X.
       01  TL-COL                PIC 999.
       01  EA                    PIC 9(4).
       01  ER                    PIC 9(4).
       01  EN                    PIC 9(4).
       01  EL                    PIC 9(4).
       01  EPOS                  PIC 9(4).
       01  EC-CO                 PIC 999.
       01  EC-HI                 PIC 999.
       01  E-SP1                 PIC 9(4).
       01  E-SPF                 PIC 9(4).
       01  E-DONE                PIC 9.
       01  E-BLANK               PIC 9.
       01  E-CB                  PIC 9.
       01  E-K                   PIC 9(4).
       01  WS-BAN.
           05  BAN-CH            PIC X OCCURS 14 TIMES.
       01  BAN-LEN               PIC 99.
       01  BAN-CO                PIC 999.
      * MVS-RP (D39) DECORATIONS OF THE SCREEN BEING BUILT, POPUP STATE.
       01  RP-READY              PIC 9 VALUE 0.
       01  RP-DTH                PIC 9 VALUE 0.
       01  RP-DTE                PIC 9(5) VALUE 0.
       01  RP-DTHMS              PIC 999 VALUE 150.
       01  RP-PU                 PIC 9 VALUE 0.
       01  RP-HI                 PIC 9 VALUE 0.
       01  RP-END                PIC 9 VALUE 0.
       01  RP-DECO               PIC 9 VALUE 0.
       01  RP-SUPP               PIC 9 VALUE 0.
       01  RP-HIV                PIC 9(7) VALUE 0.
       01  RP-NOW                PIC 9(7) VALUE 0.
       01  RP-LIM                PIC 9(7) VALUE 0.
       01  RP-POS                PIC 9(4) VALUE 0.
       01  RP-K                  PIC 99 VALUE 0.
       01  RP-C                  PIC 99 VALUE 0.
       01  RP-DK                 PIC 9 VALUE 0.
       01  RP-KX                 PIC X VALUE '0'.
       01  RP-KN REDEFINES RP-KX PIC 9.
       01  RP-TAB-OK             PIC 9 VALUE 0.
       01  RP-GLY.
           05  RP-GCH            PIC X OCCURS 4 TIMES.
       01  RP-RDY.
           05  RP-RCH            PIC X OCCURS 6 TIMES.
       01  RP-KIND-T             PIC X(4) VALUE '1234'.
       01  RP-KIND-R REDEFINES RP-KIND-T.
           05  RP-KCH            PIC X OCCURS 4 TIMES.
       01  PU-ON                 PIC 9 VALUE 0.
       01  PU-X                  PIC 99 VALUE 0.
       01  PU-Y                  PIC 99 VALUE 0.
       01  PU-COL                PIC 999 VALUE 0.
       01  PU-T0                 PIC 9(7) VALUE 0.
       01  PU-EAT                PIC 9(4) VALUE 0.
       01  PU-FRT                PIC 999 VALUE 0.
       01  PU-PTS                PIC 9(4) VALUE 0.
       01  PU-NUM                PIC 9(4) VALUE 0.
       01  PU-NUMX REDEFINES PU-NUM.
           05  PU-D              PIC X OCCURS 4 TIMES.
       01  PU-T4.
           05  PU-CH4            PIC X OCCURS 4 TIMES.
       01  PU-T3.
           05  PU-CH3            PIC X OCCURS 3 TIMES.
       01  PU-MSG.
           05  PM-KIND           PIC X(6).
           05  PM-PTS            PIC 9(4).
       01  HUD-HI-T.
           05  FILLER            PIC X(3) VALUE 'HI '.
           05  HH-V              PIC 9(7).
       01  HUD-HI-B.
           05  FILLER            PIC X(11) VALUE 'HIGH SCORE '.
           05  HB-V              PIC 9(7).
       01  END-SC.
           05  FILLER            PIC X(6) VALUE 'SCORE '.
           05  ES-V              PIC 9(7).
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       01  PAC-DS COPY PACDS.
       01  PAC-ARC COPY PACARC.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ PAC-DS PAC-ARC.
       MAIN-PARA.
           IF TAB-OK = 0
               PERFORM INIT-TAB.
           IF SC-INIT = 0
               PERFORM INIT-SCALE.
           MOVE 0 TO DS-OVF.
           IF REQ-OP = 'INVL'
               MOVE 1 TO MSG-ON
               MOVE REQ-CHAR TO INV-CHAR
           ELSE IF REQ-OP = 'PRMT'
               PERFORM DO-PRMT THRU DO-PRMT-EXIT
           ELSE IF REQ-OP = 'TICK'
               PERFORM DO-TICK THRU DO-TICK-EXIT
           ELSE IF REQ-OP = 'FULL'
               PERFORM DO-FULL THRU DO-FULL-EXIT
           ELSE IF REQ-OP = 'ENDS'
               PERFORM DO-ENDS THRU DO-ENDS-EXIT
           ELSE IF REQ-OP = 'RTQF'
               PERFORM DO-RTQF THRU DO-RTQF-EXIT.
           GOBACK.
       DO-PRMT.
           MOVE 0 TO DS-LEN.
           MOVE 'F' TO DS-KIND.
           PERFORM RP-STATE THRU RP-STATE-EXIT.
           PERFORM INIT-HI.
           IF REQ-ANIM = 'Y' AND REQ-PLAY = 'R'
               MOVE REQ-VIS TO VIS
           ELSE IF REQ-ANIM = 'Y'
               PERFORM TOGGLE-VIS.
           PERFORM SET-FACE.
           PERFORM SET-GLYPHS.
           PERFORM PRMT-BODY.
      * MVS-GS SIZE GUARD: A SCREEN THAT DID NOT FIT IS REPLACED BY THE
      * NEXT LAYOUT DOWN (W/T -> B -> G4) FOR THE REST OF THE GAME.
           PERFORM PRMT-RETRY UNTIL DS-OVF = 0.
           MOVE MSG-ON TO MSG-LAST.
           MOVE 0 TO MSG-ON.
       DO-PRMT-EXIT.
           EXIT.
       PRMT-RETRY.
           IF RP-DECO = 1 AND RP-SUPP = 0
               PERFORM RP-DROP
           ELSE
               PERFORM RP-STATE THRU RP-STATE-EXIT
               PERFORM LAYOUT-DOWN
               PERFORM SET-GLYPHS.
           PERFORM PRMT-BODY.
       PRMT-BODY.
           IF REQ-REDRAW = 'P'
               PERFORM PRMT-VS
           ELSE
               PERFORM COMPOSE.
           MOVE 0 TO WS-NOP.
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
           PERFORM RP-STATE THRU RP-STATE-EXIT.
           PERFORM INIT-HI.
           PERFORM SET-GLYPHS.
           MOVE MSG-LAST TO MSG-ON.
           PERFORM COMPOSE.
           PERFORM FULL-RETRY UNTIL DS-OVF = 0.
           MOVE 0 TO MSG-ON.
           MOVE 0 TO PREV-OK.
       DO-FULL-EXIT.
           EXIT.
       FULL-RETRY.
           IF RP-DECO = 1 AND RP-SUPP = 0
               PERFORM RP-DROP
           ELSE
               PERFORM RP-STATE THRU RP-STATE-EXIT
               PERFORM LAYOUT-DOWN
               PERFORM SET-GLYPHS.
           PERFORM COMPOSE.
       DO-TICK.
           MOVE 0 TO DS-LEN.
           PERFORM RP-STATE THRU RP-STATE-EXIT.
           IF REQ-ANIM = 'Y' AND REQ-REDRAW = 'P' AND PREV-OK = 1
                             AND SC-ON = 1
               PERFORM TICK-BUILD-S
           ELSE IF REQ-ANIM = 'Y' AND REQ-REDRAW = 'P'
                             AND PREV-OK = 1
               PERFORM TICK-BUILD.
      * A TICK THAT DID NOT FIT: FULL SCREEN OF THE NEXT LAYOUT DOWN.
           PERFORM TICK-RETRY UNTIL DS-OVF = 0.
       DO-TICK-EXIT.
           EXIT.
       TICK-RETRY.
           IF RP-DECO = 1 AND RP-SUPP = 0
               PERFORM RP-DROP
           ELSE
               PERFORM RP-STATE THRU RP-STATE-EXIT
               PERFORM LAYOUT-DOWN
               PERFORM SET-GLYPHS.
           MOVE MSG-LAST TO MSG-ON.
           PERFORM PRMT-VS.
           MOVE 0 TO MSG-ON.
       DO-RTQF.
           MOVE 0 TO DS-LEN.
           PERFORM RP-STATE THRU RP-STATE-EXIT.
           IF REQ-REDRAW NOT = 'P' OR PREV-OK = 0
               PERFORM DO-PRMT THRU DO-PRMT-EXIT
               GO TO DO-RTQF-EXIT.
           PERFORM INIT-HI.
           IF REQ-ANIM = 'Y'
               MOVE REQ-VIS TO VIS.
           PERFORM SET-FACE.
           PERFORM SET-GLYPHS.
           MOVE MSG-LAST TO MSG-ON.
           PERFORM BUILD-VS.
           MOVE 0 TO MSG-ON.
           MOVE 'T' TO DS-KIND.
           MOVE 194 TO WS-BV.
           PERFORM PUT-BYTE.
           PERFORM DIFF-ALL.
           PERFORM PUT-TAIL.
           PERFORM KEEP-VS.
           PERFORM TICK-RETRY UNTIL DS-OVF = 0.
       DO-RTQF-EXIT.
           EXIT.
       DO-ENDS.
      * MVS-GS FINAL SCREEN (SCALED ONLY): THE LAST BOARD WITH THE END
      * BANNER ON THE MESSAGE ROW, ALWAYS A FULL SCREEN. NOT SCALED (OR
      * NOT FITTING): NOTHING (DS-LEN 0), AS BEFORE MVS-GS.
           MOVE 0 TO DS-LEN.
           IF SC-ON = 0
               GO TO DO-ENDS-EXIT.
           PERFORM RP-ENDSET.
           PERFORM INIT-HI.
           PERFORM SET-FACE.
           PERFORM SET-GLYPHS.
           MOVE 0 TO MSG-ON.
           MOVE 1 TO BAN-ON.
           PERFORM COMPOSE.
           MOVE 0 TO BAN-ON.
           PERFORM ENDS-RETRY UNTIL DS-OVF = 0 OR SC-ON = 0.
       DO-ENDS-EXIT.
           EXIT.
       ENDS-RETRY.
           IF RP-DECO = 1 AND RP-SUPP = 0
               PERFORM RP-DROP
           ELSE
               PERFORM RP-ENDSET
               PERFORM LAYOUT-DOWN.
           IF SC-ON = 1
               PERFORM SET-GLYPHS
               MOVE 1 TO BAN-ON
               PERFORM COMPOSE
               MOVE 0 TO BAN-ON.
           MOVE 0 TO WS-NOP.
       INIT-SCALE.
      * MVS-GS: SCALING AS RESOLVED BY PACPLAT (4, 3, T; ANYTHING ELSE
      * IS OFF) AND THE BUFFER GEOMETRY (REQ-CW X REQ-CH, 0 = 80 X 24).
      * THE G1-G4 LAYOUT IS KEPT FOR A LATER FALLBACK.
           MOVE 1 TO SC-INIT.
           MOVE SPR-4 TO SPR-4-A.
           MOVE SPR-4X TO SPR-4-B.
           MOVE SPR-4Y TO SPR-4-C.
           MOVE SPR-4D TO SPR-4-D.
           MOVE SPR-3 TO SPR-3-A.
           MOVE SPR-3X TO SPR-3-B.
           MOVE SPR-3Y TO SPR-3-C.
           MOVE SPR-3D TO SPR-3-D.
           MOVE GLY-DEATH TO RP-GLY.
           MOVE TXT-READY TO RP-RDY.
           MOVE LAY-STATUS-ROW TO SV-STATUS-ROW.
           MOVE LAY-GHOSTS-ROW TO SV-GHOSTS-ROW.
           MOVE LAY-GHOSTS-COL TO SV-GHOSTS-COL.
           MOVE LAY-MSG-ROW TO SV-MSG-ROW.
           MOVE LAY-CMD-ROW TO SV-CMD-ROW.
           MOVE LAY-HELP-ROW TO SV-HELP-ROW.
           MOVE LAY-HELP-COL TO SV-HELP-COL.
           MOVE LAY-SF-ROW TO SV-SF-ROW.
           MOVE LAY-MSG-COL TO SV-MSG-COL.
           MOVE LAY-CMD-COL TO SV-CMD-COL.
           MOVE LAY-STATUS-COL TO SV-STATUS-COL.
           MOVE WS-HELP-TXT TO WS-HELP-G.
           MOVE 80 TO GW.
           MOVE 24 TO GH.
           IF REQ-CW > 0 AND REQ-CH > 0
               MOVE REQ-CW TO GW
               MOVE REQ-CH TO GH.
           COMPUTE G-CELLS = GW * GH.
           MOVE GH TO VS-ROWS.
           IF G-CELLS > 4095
               COMPUTE VS-ROWS = 4094 / GW.
           COMPUTE VS-N = GW * VS-ROWS.
           IF REQ-SCALE = '4' OR REQ-SCALE = '3' OR REQ-SCALE = 'T'
               PERFORM SCALE-ON.
           IF SC-ON = 0
               MOVE 'N' TO REQ-SCALE.
           PERFORM SET-FAMILY.
       SCALE-ON.
           MOVE 1 TO SC-ON.
           MOVE 4 TO SC-W.
           IF REQ-SCALE = '3'
               MOVE 3 TO SC-W.
           IF REQ-SCALE = 'T'
               MOVE 1000 TO DS-LIMIT.
           MOVE 0 TO WS-NOP.
       SET-FAMILY.
      * W: 4X2 AND >= 120 X 27; T: 4X2 AND >= 32 ROWS; B: SCALED, ANY
      * OTHER BUFFER; G: NOT SCALED.
           IF SC-ON = 1 AND SC-W = 4 AND GW > 119 AND VS-ROWS > 26
               PERFORM FAM-W
           ELSE IF SC-ON = 1 AND SC-W = 4 AND VS-ROWS > 31
               PERFORM FAM-T
           ELSE IF SC-ON = 1
               PERFORM FAM-B
           ELSE
               PERFORM FAM-G.
           MOVE 0 TO WS-NOP.
       FAM-CENTRE.
           COMPUTE ORG-R = (VS-ROWS - 24) / 2 + 1.
           COMPUTE ORG-C = (GW - 80) / 2 + 1.
       FAM-G.
           MOVE 'G' TO FAM.
           PERFORM FAM-CENTRE.
           MOVE SV-STATUS-ROW TO LAY-STATUS-ROW.
           MOVE SV-GHOSTS-ROW TO LAY-GHOSTS-ROW.
           MOVE SV-GHOSTS-COL TO LAY-GHOSTS-COL.
           MOVE SV-MSG-ROW TO LAY-MSG-ROW.
           MOVE SV-CMD-ROW TO LAY-CMD-ROW.
           MOVE SV-HELP-ROW TO LAY-HELP-ROW.
           MOVE SV-HELP-COL TO LAY-HELP-COL.
           MOVE SV-SF-ROW TO LAY-SF-ROW.
           MOVE SV-MSG-COL TO LAY-MSG-COL.
           MOVE SV-CMD-COL TO LAY-CMD-COL.
           MOVE SV-STATUS-COL TO LAY-STATUS-COL.
           MOVE WS-HELP-G TO WS-HELP-TXT.
       FAM-B.
      * THE 80 X 24 GS LAYOUT B, CENTRED IN THE BUFFER.
           MOVE 'B' TO FAM.
           PERFORM FAM-CENTRE.
           MOVE LS-STATUS-ROW TO LAY-STATUS-ROW.
           MOVE LS-GHOSTS-ROW TO LAY-GHOSTS-ROW.
           MOVE LS-GHOSTS-COL TO LAY-GHOSTS-COL.
           MOVE LS-MSG-ROW TO LAY-MSG-ROW.
           MOVE LS-CMD-ROW TO LAY-CMD-ROW.
           MOVE LS-HELP-ROW TO LAY-HELP-ROW.
           MOVE LS-HELP-COL TO LAY-HELP-COL.
           MOVE LS-SF-ROW TO LAY-SF-ROW.
           MOVE SV-MSG-COL TO LAY-MSG-COL.
           MOVE SV-CMD-COL TO LAY-CMD-COL.
           MOVE SV-STATUS-COL TO LAY-STATUS-COL.
           MOVE WS-HELP-S TO WS-HELP-TXT.
           COMPUTE SC-BROW = ORG-R + LS-BOARD-ROW - 1.
           COMPUTE SC-BCOL = ORG-C + LS-BOARD-COL-4 - 1.
           IF SC-W = 3
               COMPUTE SC-BCOL = ORG-C + LS-BOARD-COL-3 - 1.
           MOVE 0 TO WS-NOP.
       FAM-W.
      * WIDE: MAZE ROWS B0..B0+19 (B0 = 4 ON 27 ROWS), COLUMNS C0..C0+79
      * (C0 = 21 ON 120, 27 ON 132), SIDE HUD, MESSAGE / COMMAND BELOW.
           MOVE 'W' TO FAM.
           MOVE 1 TO ORG-R.
           MOVE 1 TO ORG-C.
           COMPUTE W-C0 = (GW - 80) / 2 + 1.
           COMPUTE W-B0 = (VS-ROWS - 27) / 2 + 4.
           MOVE W-B0 TO SC-BROW.
           MOVE W-C0 TO SC-BCOL.
           COMPUTE W-L = W-C0 - 18.
           COMPUTE W-R = W-C0 + 82.
           MOVE 1 TO LAY-SF-ROW.
           MOVE 0 TO LAY-STATUS-ROW.
           MOVE 0 TO LAY-GHOSTS-ROW.
           MOVE 0 TO LAY-HELP-ROW.
           COMPUTE LAY-MSG-ROW = W-B0 + 21.
           MOVE W-C0 TO LAY-MSG-COL.
           COMPUTE LAY-CMD-ROW = W-B0 + 22.
           MOVE W-C0 TO LAY-CMD-COL.
           MOVE WS-HELP-S TO WS-HELP-TXT.
       FAM-T.
      * TALL: MAZE CENTRED VERTICALLY (ROWS B0..B0+19), TITLE AND SCORE
      * LINE ABOVE, STATUS / MESSAGE / COMMAND + HELP BELOW.
           MOVE 'T' TO FAM.
           MOVE 1 TO ORG-R.
           MOVE 1 TO ORG-C.
           COMPUTE W-C0 = (GW - 80) / 2 + 1.
           COMPUTE W-B0 = (VS-ROWS - 20) / 2 + 1.
           MOVE W-B0 TO SC-BROW.
           MOVE W-C0 TO SC-BCOL.
           MOVE 1 TO LAY-SF-ROW.
           COMPUTE LAY-STATUS-ROW = W-B0 + 21.
           COMPUTE LAY-STATUS-COL = W-C0 + 1.
           COMPUTE LAY-GHOSTS-ROW = W-B0 + 21.
           COMPUTE LAY-GHOSTS-COL = W-C0 + 63.
           COMPUTE LAY-MSG-ROW = W-B0 + 22.
           COMPUTE LAY-MSG-COL = W-C0 + 1.
           COMPUTE LAY-CMD-ROW = W-B0 + 24.
           COMPUTE LAY-CMD-COL = W-C0 + 1.
           COMPUTE LAY-HELP-ROW = W-B0 + 24.
           COMPUTE LAY-HELP-COL = W-C0 + 19.
           MOVE WS-HELP-S TO WS-HELP-TXT.
       LAYOUT-DOWN.
      * SIZE GUARD STEP: W/T -> B (SAME BUFFER), B -> G4 (SCALE-OFF).
           IF FAM = 'W' OR FAM = 'T'
               PERFORM FAM-B
               MOVE 0 TO PREV-OK
               MOVE 0 TO DS-OVF
               MOVE 0 TO DS-LEN
               MOVE 'F' TO DS-KIND
           ELSE
               PERFORM SCALE-OFF.
           MOVE 0 TO WS-NOP.
       SCALE-OFF.
      * BACK TO THE G4 RENDERER (CENTRED): LAYOUT, HELP TEXT, LIMIT; THE
      * TERMINAL IMAGE IS UNKNOWN NOW, SO THE NEXT SCREEN IS A FULL ONE.
           MOVE 0 TO SC-ON.
           MOVE 'N' TO REQ-SCALE.
           MOVE 2048 TO DS-LIMIT.
           PERFORM FAM-G.
           MOVE 0 TO PREV-OK.
           MOVE 0 TO DS-OVF.
           MOVE 0 TO DS-LEN.
           MOVE 'F' TO DS-KIND.
       INIT-HI.
           MOVE 0 TO WS-HP WS-HG WS-HE WS-HN WS-HW WS-HPW.
           IF REQ-HILITE = 'Y'
               MOVE HI-POWER TO WS-HPW
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
           IF SC-ON = 1
               PERFORM SET-SPRITES.
           MOVE 0 TO WS-NOP.
       SET-SPRITES.
      * MVS-GS SPRITE NUMBERS (PACPAL SPR-4 / SPR-3): PAC-MAN 1 RIGHT,
      * 2 LEFT, 3 SHUT; GHOST 4 FRAME A, 5 FRAME B (SECOND FRAME = THE
      * G3/G4 SECOND ANIMATION FRAME).
           MOVE 1 TO SPR-PAC.
           IF WS-FACE = 'L'
               MOVE 2 TO SPR-PAC.
           MOVE 4 TO SPR-GH.
           IF REQ-ANIM = 'Y' AND VIS = 1
               MOVE 3 TO SPR-PAC
               MOVE 5 TO SPR-GH.
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
           COMPUTE WS-X = (ORG-R + LAY-BOARD-ROW + WS-I - 3) * GW
               + ORG-C + LAY-BOARD-COL + WS-COL - 2.
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
       TICK-BUILD-S.
      * MVS-GS VISUAL TICK: THE SAME STATE DRAWN WITH THE OTHER FRAME,
      * THEN ONLY THE CELLS THAT CHANGED (THE SPRITE TILES).
           PERFORM TOGGLE-VIS.
           PERFORM SET-GLYPHS.
           MOVE MSG-LAST TO MSG-ON.
           PERFORM BUILD-VS.
           MOVE 0 TO MSG-ON.
           MOVE 'T' TO DS-KIND.
           MOVE 194 TO WS-BV.
           PERFORM PUT-BYTE.
           PERFORM DIFF-ALL.
           IF WS-CHG = 0
               MOVE 0 TO DS-LEN.
           IF WS-CHG NOT = 0
               PERFORM PUT-TAIL.
           PERFORM KEEP-VS.
       DIFF-ALL.
           MOVE 0 TO IN-RUN.
           MOVE 0 TO RUN-CO.
           MOVE 0 TO RUN-HI.
           MOVE 0 TO WS-CHG.
           PERFORM DIFF-CELL VARYING WS-X FROM 1 BY 1
               UNTIL WS-X > VS-N.
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
           DIVIDE WS-ADDR BY GW GIVING WS-ROW REMAINDER WS-COL.
           ADD 1 TO WS-ROW.
           ADD 1 TO WS-COL.
           MOVE WS-X TO VS-POS.
           IF IN-RUN = 0 OR WS-COL = 1
               PERFORM PUT-SBA-AT.
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
           MOVE CU-CH (WS-X) TO WS-CHB.
           PERFORM PUT-CHB.
       PUT-FIELD-PART.
      * INPUT FIELD DATA BYTE (ROW 18, COL 15): BLANK AGAIN, CURSOR IN.
           MOVE LAY-CMD-ROW TO WS-ROW.
           COMPUTE WS-COL = LAY-CMD-COL + 13.
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
           IF SC-ON = 1
               PERFORM COMPOSE-S
           ELSE
               PERFORM COMPOSE-G.
           MOVE 0 TO WS-NOP.
       COMPOSE-S.
      * MVS-GS FULL SCREEN: VIRTUAL IMAGE, THEN ITS COMPRESSED STREAM.
           PERFORM BUILD-VS.
           MOVE 0 TO DS-LEN.
           PERFORM ENCODE-S.
       COMPOSE-G.
           MOVE 195 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE LAY-SF-ROW TO WS-ROW.
           MOVE 1 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE 29 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 96 TO WS-BV.
           PERFORM PUT-BYTE.
           PERFORM COMPOSE-BODY.
           PERFORM PUT-TAIL.
       COMPOSE-BODY.
           IF LAY-STATUS-ROW > 0
               PERFORM SHOW-STATUS.
           IF GHOST-COUNT > 1 AND LAY-GHOSTS-ROW > 0
               PERFORM SHOW-GHOSTS.
           IF FAM = 'W' OR FAM = 'T'
               PERFORM SHOW-TOP.
           IF FAM = 'W'
               PERFORM SHOW-HUD.
           IF SC-ON = 1 AND CT-OK = 0
               PERFORM CT-INIT.
           IF SC-ON = 1
               PERFORM SCALED-ROW VARYING CY FROM 1 BY 1
                   UNTIL CY > 10
           ELSE
               PERFORM SHOW-BOARD-ROW VARYING WS-I FROM 1 BY 1
                   UNTIL WS-I > 10.
           IF SC-ON = 1 AND RP-READY = 1
               PERFORM S-READY.
           IF REQ-PLAY = 'R' AND REQ-RTSTAT = 'PAUS'
               PERFORM SHOW-BANNER
           ELSE IF MSG-ON = 1
               PERFORM SHOW-MESSAGE
           ELSE IF RP-PU = 1 AND SC-ON = 0
               PERFORM SHOW-POPMSG.
           IF BAN-ON = 1
               PERFORM SHOW-BANNER.
           IF BAN-ON = 1 AND RP-END = 1
               PERFORM SHOW-ENDL.
           IF RP-HI = 1 AND (FAM = 'B' OR FAM = 'G')
               PERFORM SHOW-HIB.
           PERFORM SHOW-COMMAND.
           IF VS-MODE = 0
               PERFORM SHOW-FIELD.
           IF LAY-HELP-ROW > 0
               PERFORM SHOW-HELP.
           MOVE 0 TO WS-NOP.
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
           MOVE LAY-STATUS-COL TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE WS-STATUS-LINE TO WS-TXT.
           IF ARC-ON = 1
               PERFORM ARC-STATUS.
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
           MOVE LAY-GHOSTS-COL TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           PERFORM PUT-TEXT.
       SHOW-BOARD-ROW.
      * CELL TEXT AS IN PACDISP (PLAYER, THEN GHOSTS IN INDEX ORDER).
           MOVE MAP-ROW (WS-I) TO WS-LINE.
           PERFORM BASE-COLOUR THRU BASE-COLOUR-EXIT
               VARYING WS-COL FROM 1 BY 1 UNTIL WS-COL > 20.
           IF ARC-ON = 1
               PERFORM OVERLAY-FRUIT.
           IF RP-DTH = 0
               PERFORM U-ACTORS
           ELSE IF WS-I = REQ-DTHY
               PERFORM RP-DCELL.
           PERFORM GLYPH-CELL VARYING WS-COL FROM 1 BY 1
               UNTIL WS-COL > 20.
           MOVE ALL '0' TO CELL-GES.
           IF REQ-GLYPHS = 'G' OR REQ-GLYPHS = 'B'
               PERFORM PROF-CELL THRU PROF-CELL-EXIT
                   VARYING WS-COL FROM 1 BY 1 UNTIL WS-COL > 20.
           IF RP-DTH > 1 AND RP-DTH < 6 AND WS-I = REQ-DTHY
               PERFORM U-DCELL.
           IF RP-READY = 1 AND WS-I = RP-RDY-Y
               PERFORM U-RDY-CH VARYING RP-K FROM 1 BY 1
                   UNTIL RP-K > 6.
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
       U-ACTORS.
           IF ARC-ON = 1
               PERFORM OVERLAY-EYES THRU OVERLAY-EYES-EXIT
                   VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           IF WS-I = PLAYER-Y
               MOVE 'P' TO LINE-CH (PLAYER-X)
               MOVE PAL-PLAYER TO CELL-COL (PLAYER-X)
               MOVE WS-HP TO CELL-HI (PLAYER-X).
           PERFORM OVERLAY-GHOST THRU OVERLAY-GHOST-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
       U-DCELL.
      * MVS-RP UNSCALED DEATH FRAMES 2-5: BASE GLYPHS, PLAYER COLOUR.
           MOVE REQ-DTHX TO WS-GX.
           COMPUTE RP-DK = RP-DTH - 1.
           MOVE RP-GCH (RP-DK) TO LINE-CH (WS-GX).
           MOVE PAL-PLAYER TO CELL-COL (WS-GX).
           MOVE 0 TO CELL-HI (WS-GX).
           MOVE 0 TO CELL-GE (WS-GX).
       U-RDY-CH.
           COMPUTE RP-C = RP-RDY-X + RP-K - 1.
           MOVE RP-RCH (RP-K) TO LINE-CH (RP-C).
           MOVE PAL-PLAYER TO CELL-COL (RP-C).
           MOVE 0 TO CELL-HI (RP-C).
           MOVE 0 TO CELL-GE (RP-C).
       GLYPH-CELL.
           IF LINE-CH (WS-COL) = 'P'
               MOVE WS-GP TO LINE-CH (WS-COL).
           IF LINE-CH (WS-COL) = 'G'
               MOVE WS-GG TO LINE-CH (WS-COL).
           IF LINE-CH (WS-COL) = 'F'
               MOVE WS-GG TO LINE-CH (WS-COL).
           IF LINE-CH (WS-COL) = 'Y'
               MOVE GLY-EYES TO LINE-CH (WS-COL).
           MOVE 0 TO WS-NOP.
       PROF-CELL.
      * MVS-G4: '#' -> FILLED BLOCK (BLANK + REVERSE, WALL COLOUR KEPT)
      * WHEN HIGHLIGHTING IS ON, ELSE '#' AS IT IS; '.' -> THE PELLET
      * GLYPH. IN GRAPHIC THE PELLETS AND SPRITES ARE GE CELLS.
           IF LINE-CH (WS-COL) = SPACE
               GO TO PROF-CELL-EXIT.
           IF LINE-CH (WS-COL) = 'o' OR LINE-CH (WS-COL) = GLY-EYES
               GO TO PROF-CELL-EXIT.
           IF LINE-CH (WS-COL) = GLY-FRUIT
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
           IF LINE-CH (WS-COL) = 'o'
               MOVE PAL-POWER TO CELL-COL (WS-COL)
               MOVE WS-HPW TO CELL-HI (WS-COL).
       BASE-COLOUR-EXIT.
           EXIT.
       OVERLAY-GHOST.
           IF WS-I NOT = GH-Y (WS-G)
               GO TO OVERLAY-GHOST-EXIT.
           IF ARC-ON = 1 AND ARC-GM (WS-G) = 'E'
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
           IF ARC-ON = 1 AND ARC-GM (WS-G) = 'F'
               MOVE 'F' TO LINE-CH (WS-GX)
               MOVE 0 TO CELL-HI (WS-GX)
               PERFORM SET-FRC
               MOVE TL-COL TO CELL-COL (WS-GX).
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
           MOVE LINE-CH (WS-COL) TO WS-CHB.
           PERFORM PUT-CHB.
       SHOW-MESSAGE.
           MOVE LAY-MSG-ROW TO WS-ROW.
           MOVE LAY-MSG-COL TO WS-COL.
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
           MOVE LAY-CMD-COL TO WS-COL.
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
           MOVE LAY-HELP-COL TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HELP TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE WS-HELP-TXT TO WS-TXT.
           MOVE 48 TO WS-TLEN.
           PERFORM PUT-TEXT.
       PUT-SBA.
      * LAYOUT ROW/COLUMN -> BUFFER CELL VS-POS (ORIGIN ORG-R/ORG-C IN A
      * GW-WIDE BUFFER; 80 X 24 AT (1,1) = THE G1-GS ADDRESSES).
           COMPUTE VS-POS = (ORG-R + WS-ROW - 2) * GW + ORG-C
               + WS-COL - 1.
           PERFORM PUT-SBA-AT.
       PUT-SBA-AT.
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
               MOVE TXT-CH (WS-I) TO WS-CHB
               PERFORM PUT-CHB.
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
           MOVE BW-L TO WS-CHB.
           PERFORM PUT-CHB.
       PUT-CHB.
      * MVS-GS SIZE GUARD: NEVER BEYOND DS-LIMIT (2048 = PAC-DS AND THE
      * PACFSIO BUFFER); A STREAM THAT WOULD BE LONGER IS FLAGGED.
           IF DS-LEN < DS-LIMIT
               ADD 1 TO DS-LEN
               MOVE WS-CHB TO DS-BYTE (DS-LEN)
           ELSE
               MOVE 1 TO DS-OVF.
           MOVE 0 TO WS-NOP.
      * ---------------------------------------------------------------
      * MVS-GS SCALED BOARD: LOGICAL ROW CY -> 2 IMAGE ROWS OF TILES.
       SCALED-ROW.
           MOVE CY TO WS-I.
           MOVE MAP-ROW (CY) TO WS-LINE.
           PERFORM BASE-COLOUR THRU BASE-COLOUR-EXIT
               VARYING WS-COL FROM 1 BY 1 UNTIL WS-COL > 20.
           IF ARC-ON = 1
               PERFORM OVERLAY-FRUIT.
           IF RP-DTH = 0
               PERFORM S-ACTORS
           ELSE IF CY = REQ-DTHY
               PERFORM RP-DCELL.
      * THE POPUP COVERS PAC-MAN AND EYES (THE EATING SCREEN SHOWS THE
      * POINTS, AS IN THE ARCADE), NEVER A GHOST.
           IF RP-PU = 1 AND CY = PU-Y
                        AND LINE-CH (PU-X) NOT = 'G'
                        AND LINE-CH (PU-X) NOT = 'F'
               MOVE '$' TO LINE-CH (PU-X)
               MOVE PU-COL TO CELL-COL (PU-X).
           PERFORM S-TILE VARYING CX FROM 1 BY 1 UNTIL CX > 20.
       S-ACTORS.
           IF ARC-ON = 1
               PERFORM OVERLAY-EYES THRU OVERLAY-EYES-EXIT
                   VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           IF CY = PLAYER-Y
               MOVE 'P' TO LINE-CH (PLAYER-X)
               MOVE PAL-PLAYER TO CELL-COL (PLAYER-X).
           PERFORM OVERLAY-GHOST THRU OVERLAY-GHOST-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
       S-TILE.
           MOVE LINE-CH (CX) TO TL-KIND.
           MOVE CELL-COL (CX) TO TL-COL.
           PERFORM S-SUB VARYING SR FROM 1 BY 1 UNTIL SR > 2
               AFTER SC FROM 1 BY 1 UNTIL SC > SC-W.
       S-SUB.
           MOVE SPACE TO TL-CH.
           MOVE 0 TO TL-CO.
           MOVE 0 TO TL-HI.
           MOVE 0 TO TL-CS.
           MOVE 0 TO SPR-FR.
           IF TL-KIND = '#'
               PERFORM S-WALL
           ELSE IF TL-KIND = '.'
               PERFORM S-PELLET
           ELSE IF TL-KIND = 'P'
               MOVE SPR-PAC TO SPR-NO
               PERFORM S-SPRITE
           ELSE IF TL-KIND = 'G'
               MOVE SPR-GH TO SPR-NO
               PERFORM S-SPRITE
           ELSE IF TL-KIND = 'F'
               MOVE SPR-GH TO SPR-NO
               MOVE 1 TO SPR-FR
               PERFORM S-SPRITE
           ELSE IF TL-KIND = 'o'
               MOVE 6 TO SPR-NO
               PERFORM S-SPRITE
           ELSE IF TL-KIND = 'Y'
               MOVE 7 TO SPR-NO
               PERFORM S-SPRITE
           ELSE IF TL-KIND = '$'
               PERFORM S-POPUP
           ELSE IF TL-KIND = '1' OR TL-KIND = '2' OR TL-KIND = '3'
                             OR TL-KIND = '4'
               MOVE TL-KIND TO RP-KX
               COMPUTE SPR-NO = RP-KN + 8
               PERFORM S-SPRITE
           ELSE IF TL-KIND = GLY-FRUIT
               MOVE 8 TO SPR-NO
               PERFORM S-SPRITE.
           COMPUTE VS-POS = (SC-BROW - 1 + (CY - 1) * 2 + SR - 1) * GW
               + SC-BCOL + (CX - 1) * SC-W + SC - 1.
           MOVE TL-CH TO CU-CH (VS-POS).
           MOVE TL-CO TO CU-CO (VS-POS).
           MOVE TL-HI TO CU-HI (VS-POS).
           MOVE TL-CS TO CU-CS (VS-POS).
       S-POPUP.
      * MVS-RP POPUP TILE: THE POINTS ON THE UPPER ROW, BASE SET.
           IF SR = 1 AND SC-W = 4
               MOVE PU-CH4 (SC) TO TL-CH.
           IF SR = 1 AND SC-W = 3
               MOVE PU-CH3 (SC) TO TL-CH.
           IF TL-CH NOT = SPACE
               MOVE TL-COL TO TL-CO.
           MOVE 0 TO WS-NOP.
       S-WALL.
           COMPUTE CT-K = ((CY - 1) * 20 + CX - 1) * 8
               + (SR - 1) * 4 + SC.
           IF CT-CODE (CT-K) NOT = 0
               MOVE CT-CODE (CT-K) TO BW-N
               MOVE BW-L TO TL-CH
               MOVE PAL-WALL TO TL-CO
               MOVE 1 TO TL-CS.
           MOVE 0 TO WS-NOP.
       S-PELLET.
           IF SR = 1 AND SC = LS-PEL-COL
               MOVE X-PEL-G TO TL-CH
               MOVE PAL-PELLET TO TL-CO
               MOVE 1 TO TL-CS.
           MOVE 0 TO WS-NOP.
       S-SPRITE.
      * F = BLANK IN REVERSE, T/B = UPPER/LOWER HALF BLOCK, E = EYE IN
      * REVERSE (GE CODES FROM PACPAL), ' ' = BLANK. COLOUR OF THE CELL.
           IF SC-W = 4
               COMPUTE E-K = ((SPR-NO - 1) * 2 + SR - 1) * 4 + SC
               MOVE SPR-4-CH (E-K) TO SPR-C
           ELSE
               COMPUTE E-K = ((SPR-NO - 1) * 2 + SR - 1) * 3 + SC
               MOVE SPR-3-CH (E-K) TO SPR-C.
           IF SPR-FR = 1 AND SPR-C = 'E'
               MOVE 'e' TO SPR-C.
           IF SPR-C NOT = SPACE
               MOVE TL-COL TO TL-CO.
           IF SPR-C = 'F' OR SPR-C = 'E'
               MOVE HI-PLAYER TO TL-HI.
           IF SPR-C = 'T'
               MOVE SG-UPPER TO BW-N.
           IF SPR-C = 'B'
               MOVE SG-LOWER TO BW-N.
           IF SPR-C = 'E' OR SPR-C = 'e'
               MOVE SG-EYE TO BW-N.
           IF SPR-C = 'T' OR SPR-C = 'B' OR SPR-C = 'E' OR SPR-C = 'e'
               MOVE BW-L TO TL-CH
               MOVE 1 TO TL-CS.
           IF TL-KIND = 'o' AND SPR-C NOT = SPACE
               MOVE WS-HPW TO TL-HI.
           MOVE 0 TO WS-NOP.
      * WALL CONTOUR TABLE, BUILT ONCE (WALLS NEVER CHANGE): 8 CODES PER
      * LOGICAL CELL (ROW 1 AT +1..+W, ROW 2 AT +5..+4+W), 0 = BLANK.
      * A NEIGHBOUR OUTSIDE THE MAP COUNTS AS OPEN (DOUBLE BORDER).
       CT-INIT.
           MOVE ALL '0' TO CT-TABLE.
           PERFORM CT-CELL THRU CT-CELL-EXIT
               VARYING CY FROM 1 BY 1 UNTIL CY > 10
               AFTER CX FROM 1 BY 1 UNTIL CX > 20.
           MOVE 1 TO CT-OK.
       CT-CELL.
           IF MAP-CELL (CY, CX) NOT = '#'
               GO TO CT-CELL-EXIT.
           MOVE CX TO WX.
           COMPUTE WY = CY - 1.
           PERFORM GET-W.
           MOVE WW TO NB-N.
           COMPUTE WY = CY + 1.
           PERFORM GET-W.
           MOVE WW TO NB-S.
           COMPUTE WX = CX - 1.
           PERFORM GET-W.
           MOVE WW TO NB-SW.
           MOVE CY TO WY.
           PERFORM GET-W.
           MOVE WW TO NB-W.
           COMPUTE WY = CY - 1.
           PERFORM GET-W.
           MOVE WW TO NB-NW.
           COMPUTE WX = CX + 1.
           PERFORM GET-W.
           MOVE WW TO NB-NE.
           MOVE CY TO WY.
           PERFORM GET-W.
           MOVE WW TO NB-E.
           COMPUTE WY = CY + 1.
           PERFORM GET-W.
           MOVE WW TO NB-SE.
           COMPUTE CT-BASE = ((CY - 1) * 20 + CX - 1) * 8.
           MOVE NB-N TO CN-V.
           MOVE NB-W TO CN-H.
           MOVE NB-NW TO CN-D.
           MOVE SG-TL TO CN-OUT.
           MOVE SG-BR TO CN-IN.
           COMPUTE CT-K = CT-BASE + 1.
           PERFORM CORNER.
           MOVE NB-E TO CN-H.
           MOVE NB-NE TO CN-D.
           MOVE SG-TR TO CN-OUT.
           MOVE SG-BL TO CN-IN.
           COMPUTE CT-K = CT-BASE + SC-W.
           PERFORM CORNER.
           MOVE NB-S TO CN-V.
           MOVE NB-W TO CN-H.
           MOVE NB-SW TO CN-D.
           MOVE SG-BL TO CN-OUT.
           MOVE SG-TR TO CN-IN.
           COMPUTE CT-K = CT-BASE + 5.
           PERFORM CORNER.
           MOVE NB-E TO CN-H.
           MOVE NB-SE TO CN-D.
           MOVE SG-BR TO CN-OUT.
           MOVE SG-TL TO CN-IN.
           COMPUTE CT-K = CT-BASE + 4 + SC-W.
           PERFORM CORNER.
           PERFORM CT-EDGE VARYING SC FROM 2 BY 1 UNTIL SC = SC-W.
       CT-CELL-EXIT.
           EXIT.
       CT-EDGE.
           IF NB-N = 0
               COMPUTE CT-K = CT-BASE + SC
               MOVE SG-HLINE TO CT-CODE (CT-K).
           IF NB-S = 0
               COMPUTE CT-K = CT-BASE + 4 + SC
               MOVE SG-HLINE TO CT-CODE (CT-K).
           MOVE 0 TO WS-NOP.
       CORNER.
           MOVE 0 TO CN-RES.
           IF CN-V = 0 AND CN-H = 0
               MOVE CN-OUT TO CN-RES
           ELSE IF CN-V = 0
               MOVE SG-HLINE TO CN-RES
           ELSE IF CN-H = 0
               MOVE SG-VLINE TO CN-RES
           ELSE IF CN-D = 0
               MOVE CN-IN TO CN-RES.
           MOVE CN-RES TO CT-CODE (CT-K).
       GET-W.
           MOVE 0 TO WW.
           IF WX > 0 AND WX < 21 AND WY > 0 AND WY < 11
               PERFORM GET-W2.
           MOVE 0 TO WS-NOP.
       GET-W2.
           IF MAP-CELL (WY, WX) = '#'
               MOVE 1 TO WW.
           MOVE 0 TO WS-NOP.
      * MVS-GS END BANNER ON THE MESSAGE ROW (REVERSE, ITS COLOUR).
       SHOW-BANNER.
           MOVE ' END OF INPUT ' TO WS-BAN.
           MOVE 14 TO BAN-LEN.
           MOVE PAL-HELP TO BAN-CO.
           IF BAN-ON = 0
               MOVE ' PAUSED ' TO WS-BAN
               MOVE 8 TO BAN-LEN.
           IF F-QUIT = 1
               MOVE ' QUIT ' TO WS-BAN
               MOVE 6 TO BAN-LEN.
           IF F-WON = 1
               MOVE ' YOU WIN ' TO WS-BAN
               MOVE 9 TO BAN-LEN
               MOVE PAL-PLAYER TO BAN-CO.
           IF F-LOST = 1
               MOVE ' GAME OVER ' TO WS-BAN
               MOVE 11 TO BAN-LEN
               MOVE PAL-ERROR TO BAN-CO.
           COMPUTE VS-POS = (ORG-R + LAY-MSG-ROW - 2) * GW + ORG-C
               + LAY-MSG-COL - 1.
           PERFORM BAN-CELL VARYING E-K FROM 1 BY 1
               UNTIL E-K > BAN-LEN.
       BAN-CELL.
           MOVE BAN-CH (E-K) TO CU-CH (VS-POS).
           MOVE BAN-CO TO CU-CO (VS-POS).
           MOVE HI-PLAYER TO CU-HI (VS-POS).
           MOVE 0 TO CU-CS (VS-POS).
           ADD 1 TO VS-POS.
      * MVS-GS FULL-SCREEN ENCODER (IMAGE -> STREAM): SBA ONLY WHERE
      * THE ADDRESS JUMPS, SA ONLY ON A CHANGE, GE BEFORE CP310 CODES,
      * RA FOR A RUN OF EQUAL CELLS WHEN SHORTER, RUNS OF 4+ BLANKS
      * SKIPPED (PACFSIO'S CLEAR PREFIX NULLS THE BUFFER). FIELD AT THE
      * FIRST SF CELL AND AT THE COMMAND FIELD, AS IN THE G1 SCREENS.
       ENCODE-S.
           MOVE 195 TO WS-BV.
           PERFORM PUT-BYTE.
           COMPUTE E-SP1 = (ORG-R + LAY-SF-ROW - 2) * GW + ORG-C.
           COMPUTE E-SPF = (ORG-R + LAY-CMD-ROW - 2) * GW + ORG-C
               + LAY-CMD-COL + 11.
           MOVE 0 TO EC-CO.
           MOVE 0 TO EC-HI.
           MOVE 0 TO EPOS.
           MOVE 1 TO EA.
           PERFORM ENC-STEP UNTIL EA > VS-N.
           IF EC-HI NOT = 0
               MOVE 0 TO WS-HV
               PERFORM PUT-HILITE.
           PERFORM PUT-TAIL.
       ENC-STEP.
           IF EA = E-SP1
               PERFORM ENC-SF1
           ELSE IF EA = E-SPF
               PERFORM ENC-FLD
           ELSE
               PERFORM ENC-RUN THRU ENC-RUN-EXIT.
           MOVE 0 TO WS-NOP.
       ENC-SBA.
           IF EPOS NOT = EA
               MOVE EA TO E-K
               MOVE 17 TO WS-BV
               PERFORM PUT-BYTE
               PERFORM PUT-ADDR.
           MOVE 0 TO WS-NOP.
       ENC-HI-OFF.
           IF EC-HI NOT = 0
               MOVE 0 TO EC-HI
               MOVE 0 TO WS-HV
               PERFORM PUT-HILITE.
           MOVE 0 TO WS-NOP.
       ENC-SF1.
           PERFORM ENC-SBA.
           PERFORM ENC-HI-OFF.
           MOVE 29 TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE 96 TO WS-BV.
           PERFORM PUT-BYTE.
           ADD 1 TO EA.
           MOVE EA TO EPOS.
       ENC-FLD.
           PERFORM ENC-SBA.
           PERFORM ENC-HI-OFF.
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
           ADD 3 TO EA.
           MOVE EA TO EPOS.
       ENC-RUN.
           MOVE EA TO ER.
           MOVE 0 TO E-DONE.
           PERFORM ENC-EXT UNTIL E-DONE = 1.
           COMPUTE EL = ER - EA + 1.
           MOVE 0 TO E-BLANK.
           IF CU-CH (EA) = SPACE AND CU-HI (EA) = 0 AND CU-CS (EA) = 0
               MOVE 1 TO E-BLANK.
           IF E-BLANK = 1 AND EL > 3
               COMPUTE EA = ER + 1
               GO TO ENC-RUN-EXIT.
           PERFORM ENC-SBA.
           IF E-BLANK = 0 AND CU-CO (EA) NOT = EC-CO
               MOVE CU-CO (EA) TO EC-CO
               MOVE EC-CO TO WS-BV
               PERFORM PUT-COLOUR.
           IF CU-HI (EA) NOT = EC-HI
               MOVE CU-HI (EA) TO EC-HI
               MOVE EC-HI TO WS-HV
               PERFORM PUT-HILITE.
           MOVE 1 TO E-CB.
           IF CU-CS (EA) = 1
               MOVE 2 TO E-CB.
           COMPUTE EN = EL * E-CB - E-CB.
           IF EN > 3
               PERFORM ENC-RA
           ELSE
               PERFORM ENC-LIT EL TIMES.
           COMPUTE EA = ER + 1.
           MOVE EA TO EPOS.
       ENC-RUN-EXIT.
           EXIT.
       ENC-EXT.
           COMPUTE EN = ER + 1.
           IF EN > VS-N OR EN = E-SP1 OR EN = E-SPF
               MOVE 1 TO E-DONE
           ELSE
               PERFORM ENC-CMP.
           MOVE 0 TO WS-NOP.
       ENC-CMP.
           IF CU-CH (EN) NOT = CU-CH (EA)
                  OR CU-CO (EN) NOT = CU-CO (EA)
                  OR CU-HI (EN) NOT = CU-HI (EA)
                  OR CU-CS (EN) NOT = CU-CS (EA)
               MOVE 1 TO E-DONE
           ELSE
               MOVE EN TO ER.
           MOVE 0 TO WS-NOP.
       ENC-RA.
      * REPEAT TO ADDRESS X'3C' (THE CELL AFTER THE RUN), [GE] CHAR.
           MOVE 60 TO WS-BV.
           PERFORM PUT-BYTE.
           COMPUTE E-K = ER + 1.
           IF E-K > G-CELLS
               MOVE 1 TO E-K.
           PERFORM PUT-ADDR.
           PERFORM ENC-LIT.
       ENC-LIT.
           IF CU-CS (EA) = 1
               MOVE 8 TO WS-BV
               PERFORM PUT-BYTE.
           MOVE CU-CH (EA) TO WS-CHB.
           PERFORM PUT-CHB.
       PUT-ADDR.
      * 12-BIT ADDRESS OF BUFFER CELL E-K (1-4095), TWO BYTES.
           COMPUTE WS-ADDR = E-K - 1.
           DIVIDE WS-ADDR BY 64 GIVING WS-HI REMAINDER WS-LO.
           ADD 1 TO WS-HI.
           ADD 1 TO WS-LO.
           MOVE ADDR-CODE (WS-HI) TO WS-BV.
           PERFORM PUT-BYTE.
           MOVE ADDR-CODE (WS-LO) TO WS-BV.
           PERFORM PUT-BYTE.
      * MVS-GS WIDE / TALL: TITLE (AND THE TALL SCORE LINE).
       SHOW-TOP.
           COMPUTE WS-ROW = W-B0 - 2.
           IF FAM = 'T'
               COMPUTE WS-ROW = W-B0 - 4.
           COMPUTE WS-COL = W-C0 + 33.
           PERFORM PUT-SBA.
           MOVE PAL-PLAYER TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE 'P A C - M A N' TO WS-TXT.
           MOVE 13 TO WS-TLEN.
           IF ARC-ON = 1
               PERFORM ARC-TITLE.
           PERFORM PUT-TEXT.
           IF FAM = 'T'
               PERFORM SHOW-TALL-LINE.
           IF FAM = 'T' AND ARC-ON = 1
               PERFORM ARC-TALL.
           IF FAM = 'T' AND RP-HI = 1
               PERFORM RP-TALL-HI.
           MOVE 0 TO WS-NOP.
       SHOW-TALL-LINE.
           MOVE SCORE TO TL-SCORE.
           MOVE PELLETS-LEFT TO TL-PEL.
           MOVE TICK-COUNT TO TL-TURN.
           COMPUTE WS-ROW = W-B0 - 2.
           COMPUTE WS-COL = W-C0 + 1.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE TALL-LINE TO WS-TXT.
           IF ARC-ON = 1
               MOVE ARC-SCORE TO TA-SCORE
               MOVE PELLETS-LEFT TO TA-PEL
               MOVE TICK-COUNT TO TA-TURN
               MOVE TALL-LINE-A TO WS-TXT.
           MOVE 44 TO WS-TLEN.
           PERFORM PUT-TEXT.
           COMPUTE W-L = W-C0 + 45.
           PERFORM PUT-LIFE VARYING W-K FROM 1 BY 1 UNTIL W-K > LIVES.
      * MVS-GS WIDE: SIDE HUD (LEFT: SCORE, PELLETS, TURN, LAST, STATE,
      * LIVES; RIGHT: GHOSTS AND AI, ONE LINE PER GHOST, KEYS).
       SHOW-HUD.
           COMPUTE W-L = W-C0 - 18.
           MOVE 'SCORE' TO HL-LABEL.
           MOVE SCORE TO HUD-NUM4.
           MOVE HUD-NUM4 TO HL-VALUE.
           IF ARC-ON = 1
               MOVE ARC-SCORE TO HUD-NUM7
               MOVE HUD-NUM7 TO HL-VALUE.
           COMPUTE WS-ROW = W-B0 + 1.
           PERFORM HUD-LEFT.
           MOVE 'PELLETS' TO HL-LABEL.
           MOVE PELLETS-LEFT TO HUD-NUM3.
           MOVE HUD-NUM3 TO HL-VALUE.
           COMPUTE WS-ROW = W-B0 + 3.
           PERFORM HUD-LEFT.
           MOVE 'TURN' TO HL-LABEL.
           MOVE TICK-COUNT TO HUD-NUM3.
           MOVE HUD-NUM3 TO HL-VALUE.
           COMPUTE WS-ROW = W-B0 + 5.
           PERFORM HUD-LEFT.
           MOVE 'LAST' TO HL-LABEL.
           MOVE LAST-CMD TO HL-CMD.
           MOVE LAST-RESULT TO HL-RES.
           MOVE HUD-LAST TO HL-VALUE.
           COMPUTE WS-ROW = W-B0 + 7.
           PERFORM HUD-LEFT.
           MOVE 'STATE' TO HL-LABEL.
           MOVE GAME-STATE TO HL-VALUE.
           COMPUTE WS-ROW = W-B0 + 9.
           PERFORM HUD-LEFT.
           MOVE 'LIVES' TO HL-LABEL.
           MOVE SPACES TO HL-VALUE.
           COMPUTE WS-ROW = W-B0 + 11.
           PERFORM HUD-LEFT.
           COMPUTE W-L = W-C0 - 10.
           PERFORM PUT-LIFE VARYING W-K FROM 1 BY 1 UNTIL W-K > LIVES.
      * MVS-RP: THE HIGH SCORE BELOW THE LIVES (AFTER THEIR ICONS, WHICH
      * USE WS-ROW).
           COMPUTE W-L = W-C0 - 18.
           IF RP-HI = 1
               MOVE 'HIGH' TO HL-LABEL
               MOVE RP-HIV TO HUD-NUM7
               MOVE HUD-NUM7 TO HL-VALUE
               COMPUTE WS-ROW = W-B0 + 13
               PERFORM HUD-LEFT.
           MOVE AI-LEVEL TO HA-LEVEL.
           COMPUTE WS-ROW = W-B0 + 1.
           MOVE W-R TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE HUD-AI TO WS-TXT.
           MOVE 11 TO WS-TLEN.
           PERFORM PUT-TEXT.
           PERFORM HUD-GHOST VARYING WS-G FROM 1 BY 1
               UNTIL WS-G > GHOST-COUNT.
           IF ARC-ON = 1
               PERFORM ARC-HUD.
           COMPUTE WS-ROW = W-B0 + 13.
           MOVE W-R TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HELP TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE 'U D L R ENTER' TO WS-TXT.
           MOVE 13 TO WS-TLEN.
           PERFORM PUT-TEXT.
           COMPUTE WS-ROW = W-B0 + 14.
           MOVE W-R TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HELP TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE 'Q QUIT  PA2' TO WS-TXT.
           MOVE 11 TO WS-TLEN.
           PERFORM PUT-TEXT.
       HUD-LEFT.
           MOVE W-L TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE HUD-LINE TO WS-TXT.
           MOVE 17 TO WS-TLEN.
           PERFORM PUT-TEXT.
       HUD-GHOST.
           COMPUTE WS-ROW = W-B0 + 2 + WS-G.
           MOVE PAL-GHOST-1 TO TL-COL.
           IF WS-G = 2
               MOVE PAL-GHOST-2 TO TL-COL.
           IF WS-G = 3
               MOVE PAL-GHOST-3 TO TL-COL.
           IF ARC-ON = 1 AND ARC-GM (WS-G) = 'F'
               PERFORM SET-FRC.
           IF ARC-ON = 1 AND ARC-GM (WS-G) = 'E'
               MOVE PAL-EYES TO TL-COL.
           MOVE W-R TO WS-COL.
           MOVE GGH-1 TO BW-N.
           PERFORM PUT-GE-CELL.
           MOVE GH-X (WS-G) TO HG-X.
           MOVE GH-Y (WS-G) TO HG-Y.
           COMPUTE WS-COL = W-R + 2.
           PERFORM PUT-SBA.
           MOVE TL-COL TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE HUD-GH TO WS-TXT.
           MOVE 5 TO WS-TLEN.
           PERFORM PUT-TEXT.
       PUT-LIFE.
      * ONE PAC-MAN ICON (CP310 X'9B') PER LIFE, EVERY SECOND COLUMN.
           COMPUTE WS-COL = W-L + (W-K - 1) * 2.
           MOVE PAL-PLAYER TO TL-COL.
           MOVE GPL-RIGHT TO BW-N.
           PERFORM PUT-GE-CELL.
       PUT-GE-CELL.
      * ONE CP310 CELL (BYTE IN BW-L) AT WS-ROW/WS-COL, COLOUR TL-COL.
           PERFORM PUT-SBA.
           MOVE BW-L TO CU-CH (VS-POS).
           MOVE TL-COL TO CU-CO (VS-POS).
           MOVE 0 TO CU-HI (VS-POS).
           MOVE 1 TO CU-CS (VS-POS).
      * ------------- MVS-GP1 ARCADE SCREENS (D36, ARC-ON = 1) ------
       ARC-STATUS.
           MOVE TICK-COUNT TO AS-TURN.
           MOVE LAST-CMD TO AS-CMD.
           MOVE LAST-RESULT TO AS-RESULT.
           MOVE ARC-SCORE TO AS-SCORE.
           MOVE PELLETS-LEFT TO AS-LEFT.
           MOVE LIVES TO AS-LIVES.
           MOVE GAME-STATE TO AS-STATE.
           MOVE ARC-FR TO AS-FR.
           MOVE ARC-LEVEL TO AS-LV.
           MOVE ARC-BK TO AS-BK.
           MOVE WS-ARC-ST TO WS-TXT.
       ARC-TITLE.
           MOVE 'P A C - M A N   A R C A D E' TO WS-TXT.
           MOVE 27 TO WS-TLEN.
           SUBTRACT 7 FROM WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-PLAYER TO WS-BV.
           PERFORM PUT-COLOUR.
       SET-FRC.
      * FRIGHTENED COLOUR IN TL-COL: BLUE, WHITE IN THE WARNING WINDOW.
           MOVE PAL-FRIGHT TO TL-COL.
           IF ARC-FR > 0 AND ARC-FR NOT > ARC-KWARN
               MOVE PAL-WARN TO TL-COL.
           MOVE 0 TO WS-NOP.
       OVERLAY-EYES.
      * EYES FIRST: PAC-MAN AND THE OTHER GHOSTS ARE DRAWN OVER THEM.
           IF ARC-GM (WS-G) NOT = 'E' OR WS-I NOT = GH-Y (WS-G)
               GO TO OVERLAY-EYES-EXIT.
           MOVE GH-X (WS-G) TO WS-GX.
           MOVE 'Y' TO LINE-CH (WS-GX).
           MOVE PAL-EYES TO CELL-COL (WS-GX).
           MOVE 0 TO CELL-HI (WS-GX).
       OVERLAY-EYES-EXIT.
           EXIT.
      * ------------- MVS-GP2 ARCADE SCREENS (D37, ARC-ON = 1) ------
       OVERLAY-FRUIT.
      * THE FRUIT FIRST: EYES, PAC-MAN AND THE GHOSTS ARE DRAWN OVER IT
      * (IT SHOWS AGAIN WHEN THEY LEAVE ITS CELL WHILE ARC-BT > 0).
           IF ARC-BT > 0 AND WS-I = ARC-BY
               MOVE GLY-FRUIT TO LINE-CH (ARC-BX)
               MOVE PAL-FRUIT TO CELL-COL (ARC-BX)
               MOVE 0 TO CELL-HI (ARC-BX).
           MOVE 0 TO WS-NOP.
       FRUIT-TEXT.
      * HUD-FRT = THE NAME AND THE POINTS OF THE LEVEL'S FRUIT.
           MOVE SPACES TO HF-NAME.
           PERFORM FRUIT-FIND VARYING WS-FK FROM 1 BY 1
               UNTIL WS-FK > 8.
           MOVE ARC-BV TO HF-BV.
       FRUIT-FIND.
           IF FRUIT-K (WS-FK) = ARC-BK
               MOVE FRUIT-NAME (WS-FK) TO HF-NAME.
           MOVE 0 TO WS-NOP.
       ARC-HUD.
      * WIDE: LEVEL AND THE LEVEL'S FRUIT BELOW THE GHOST LINES.
           MOVE ARC-LEVEL TO HV-LV.
           COMPUTE WS-ROW = W-B0 + 7.
           MOVE W-R TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE HUD-LVL TO WS-TXT.
           MOVE 10 TO WS-TLEN.
           PERFORM PUT-TEXT.
           PERFORM FRUIT-TEXT.
           COMPUTE WS-ROW = W-B0 + 9.
           MOVE W-R TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-FRUIT TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE HUD-FRT TO WS-TXT.
           MOVE 15 TO WS-TLEN.
           PERFORM PUT-TEXT.
       ARC-TALL.
      * TALL: LEVEL IN THE TITLE ROW, THE FRUIT AFTER THE LIVES.
           MOVE ARC-LEVEL TO HT-LV.
           COMPUTE WS-ROW = W-B0 - 4.
           COMPUTE WS-COL = W-C0 + 60.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE HUD-LVT TO WS-TXT.
           MOVE 8 TO WS-TLEN.
           PERFORM PUT-TEXT.
           PERFORM FRUIT-TEXT.
           COMPUTE WS-ROW = W-B0 - 2.
           COMPUTE WS-COL = W-C0 + 55.
           PERFORM PUT-SBA.
           MOVE PAL-FRUIT TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE HUD-FRT TO WS-TXT.
           MOVE 15 TO WS-TLEN.
           PERFORM PUT-TEXT.
      * ------------- MVS-RP PRESENTATION (D39, ARC-ON = 1) -----------
       RP-STATE.
      * WHAT THIS SCREEN SHOWS; SAFE TO REPEAT FOR THE SAME SCREEN (THE
      * POPUP STARTS ONLY WHEN A COUNTER MOVED SINCE THE LAST SCREEN).
           MOVE 0 TO RP-READY RP-DTH RP-PU RP-HI RP-END RP-SUPP.
           MOVE 0 TO RP-DECO.
           IF ARC-ON = 0
               GO TO RP-STATE-EXIT.
           MOVE ARC-TURNS TO RP-NOW.
           IF REQ-PLAY = 'R'
               MOVE REQ-RTQ TO RP-NOW.
           IF ARC-FRUITS NOT = PU-FRT
               MOVE ARC-FRUITS TO PU-FRT
               MOVE ARC-BV TO PU-PTS
               MOVE PAL-FRUIT TO PU-COL
               MOVE ARC-BX TO PU-X
               MOVE ARC-BY TO PU-Y
               MOVE 'FRUIT ' TO PM-KIND
               PERFORM PU-START.
           IF ARC-EATN4 NOT = PU-EAT
               MOVE ARC-EATN4 TO PU-EAT
               MOVE ARC-PTS TO PU-PTS
               MOVE PAL-POPUP TO PU-COL
               MOVE PLAYER-X TO PU-X
               MOVE PLAYER-Y TO PU-Y
               MOVE 'GHOST ' TO PM-KIND
               PERFORM PU-START.
           IF PU-ON = 1 AND REQ-PLAY = 'R'
               COMPUTE RP-LIM = PU-T0 + REQ-RTPUQ.
           IF PU-ON = 1 AND REQ-PLAY = 'R' AND RP-NOW > RP-LIM
               MOVE 0 TO PU-ON.
           IF PU-ON = 1 AND REQ-PLAY NOT = 'R' AND RP-NOW NOT = PU-T0
               MOVE 0 TO PU-ON.
           IF ARC-ED = 'D' OR ARC-EC = 'C'
               MOVE 0 TO PU-ON.
           MOVE PU-ON TO RP-PU.
           IF REQ-HSST = 'R' OR REQ-HSST = 'Z'
               MOVE 1 TO RP-HI
               MOVE REQ-HISCORE TO RP-HIV.
           IF RP-HI = 1 AND ARC-SCORE > RP-HIV
               MOVE ARC-SCORE TO RP-HIV.
           IF REQ-PLAY = 'R'
               PERFORM RP-RT
           ELSE IF ARC-TURNS = 0 OR ARC-ED = 'D' OR ARC-EC = 'C'
               MOVE 1 TO RP-READY.
           IF F-LOST = 1 OR F-WON = 1
               MOVE 0 TO RP-READY.
           IF RP-READY = 1 OR RP-DTH > 0 OR RP-PU = 1 OR RP-HI = 1
               MOVE 1 TO RP-DECO.
       RP-STATE-EXIT.
           EXIT.
       RP-RT.
      * REALTIME: READY! BEFORE THE START AND IN THE LAST REQ-RTRDY
      * FREEZE QUANTA (4 AT 150 MS); THE DEATH FRAMES IN THE FREEZE
      * QUANTA BEFORE THEM (10..5 AT 150 MS) OF A DEATH (FLAG D): FRAME
      * = ELAPSED MS / RP-DTHMS + 1 (MAX 6), ELAPSED = (REQ-RTFRT -
      * REQ-RTFRZ) X REQ-RTPER (RP.3; AT 150 MS = 11 - REQ-RTFRZ).
           IF REQ-RTSTAT = 'WAIT'
               MOVE 1 TO RP-READY.
           IF REQ-RTSTAT = 'FRZ ' AND REQ-RTFRZ > 0
                   AND REQ-RTFRZ NOT > REQ-RTRDY
               MOVE 1 TO RP-READY.
           IF REQ-RTSTAT = 'FRZ ' AND REQ-RTFRZ > REQ-RTRDY
                   AND ARC-ED = 'D'
               PERFORM RP-DFRAME.
           MOVE 0 TO WS-NOP.
       RP-DFRAME.
           COMPUTE RP-DTE = (REQ-RTFRT - REQ-RTFRZ) * REQ-RTPER.
           DIVIDE RP-DTE BY RP-DTHMS GIVING RP-DTH.
           ADD 1 TO RP-DTH.
           IF RP-DTH > 6
               MOVE 6 TO RP-DTH.
           MOVE 0 TO WS-NOP.
       PU-START.
      * POPUP TEXT: 4 WIDE = 3 DIGITS + BLANK BELOW 1000, ELSE 4 DIGITS;
      * 3 WIDE = 3 DIGITS, ELSE THOUSANDS + K + HUNDREDS (0 = BLANK).
           MOVE 1 TO PU-ON.
           MOVE RP-NOW TO PU-T0.
           MOVE PU-PTS TO PU-NUM.
           MOVE PU-PTS TO PM-PTS.
           IF PU-PTS < 1000
               MOVE PU-D (2) TO PU-CH4 (1)
               MOVE PU-D (3) TO PU-CH4 (2)
               MOVE PU-D (4) TO PU-CH4 (3)
               MOVE SPACE TO PU-CH4 (4)
               MOVE PU-D (2) TO PU-CH3 (1)
               MOVE PU-D (3) TO PU-CH3 (2)
               MOVE PU-D (4) TO PU-CH3 (3)
           ELSE
               MOVE PU-NUMX TO PU-T4
               MOVE PU-D (1) TO PU-CH3 (1)
               MOVE 'K' TO PU-CH3 (2)
               MOVE PU-D (2) TO PU-CH3 (3).
           IF PU-PTS NOT < 1000 AND PU-D (2) = '0'
               MOVE SPACE TO PU-CH3 (3).
           MOVE 0 TO WS-NOP.
       RP-ENDSET.
      * OP ENDS: NO READY!, DEATH FRAME OR POPUP; THE END LINE.
           PERFORM RP-STATE THRU RP-STATE-EXIT.
           MOVE 0 TO PU-ON RP-PU RP-READY RP-DTH.
           MOVE 0 TO RP-DECO.
           IF RP-HI = 1
               MOVE 1 TO RP-DECO.
           IF ARC-ON = 1
               MOVE 1 TO RP-END
               MOVE 1 TO RP-DECO.
           MOVE 0 TO WS-NOP.
       RP-DROP.
      * TOO LONG WITH THE DECORATIONS: THE SAME LAYOUT WITHOUT THEM, AS
      * A FULL SCREEN (NEVER THE G4 FALLBACK FOR A DECORATION).
           MOVE 1 TO RP-SUPP.
           MOVE 0 TO RP-READY RP-DTH RP-PU RP-HI RP-END.
           MOVE 0 TO PREV-OK.
           MOVE 0 TO DS-OVF.
           MOVE 0 TO DS-LEN.
           MOVE 'F' TO DS-KIND.
       RP-DCELL.
      * DEATH FRAME 1 = PAC-MAN AS DRAWN NORMALLY, 6 = NOTHING; SCALED
      * FRAMES 2-5 = SPRITES 9-12 (TILE KINDS 1-4).
           MOVE REQ-DTHX TO WS-GX.
           IF RP-DTH = 1
               MOVE 'P' TO LINE-CH (WS-GX)
               MOVE PAL-PLAYER TO CELL-COL (WS-GX)
               MOVE WS-HP TO CELL-HI (WS-GX).
           IF RP-DTH > 1 AND RP-DTH < 6 AND SC-ON = 1
               COMPUTE RP-DK = RP-DTH - 1
               MOVE RP-KCH (RP-DK) TO LINE-CH (WS-GX)
               MOVE PAL-PLAYER TO CELL-COL (WS-GX).
           IF RP-DTH = 6
               MOVE SPACE TO LINE-CH (WS-GX)
               MOVE 0 TO CELL-COL (WS-GX)
               MOVE 0 TO CELL-HI (WS-GX).
           MOVE 0 TO WS-NOP.
       S-READY.
      * SCALED READY!: CENTRED ON THE UPPER ROW OF THE WALL BAR TILES.
           COMPUTE RP-POS = (SC-BROW - 1 + (RP-RDY-Y - 1) * 2) * GW
               + SC-BCOL + (RP-RDY-X - 1) * SC-W + 9.
           IF SC-W = 3
               SUBTRACT 3 FROM RP-POS.
           PERFORM S-RDY-CH VARYING RP-K FROM 1 BY 1 UNTIL RP-K > 6.
       S-RDY-CH.
           COMPUTE VS-POS = RP-POS + RP-K - 1.
           MOVE RP-RCH (RP-K) TO CU-CH (VS-POS).
           MOVE PAL-PLAYER TO CU-CO (VS-POS).
           MOVE 0 TO CU-HI (VS-POS).
           MOVE 0 TO CU-CS (VS-POS).
       SHOW-POPMSG.
      * UNSCALED POPUP: 'GHOST NNNN' / 'FRUIT NNNN' ON THE MESSAGE ROW.
           MOVE LAY-MSG-ROW TO WS-ROW.
           MOVE LAY-MSG-COL TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PU-COL TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE PU-MSG TO WS-TXT.
           MOVE 10 TO WS-TLEN.
           PERFORM PUT-TEXT.
       SHOW-HIB.
      * 80 X 24 LAYOUTS: HIGH SCORE ON ROW 24 (B) / ROW 20 (G).
           MOVE 24 TO WS-ROW.
           IF FAM = 'G'
               MOVE 20 TO WS-ROW.
           MOVE 2 TO WS-COL.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE RP-HIV TO HB-V.
           MOVE HUD-HI-B TO WS-TXT.
           MOVE 18 TO WS-TLEN.
           PERFORM PUT-TEXT.
       RP-TALL-HI.
           COMPUTE WS-ROW = W-B0 - 4.
           COMPUTE WS-COL = W-C0 + 69.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE RP-HIV TO HH-V.
           MOVE HUD-HI-T TO WS-TXT.
           MOVE 10 TO WS-TLEN.
           PERFORM PUT-TEXT.
       SHOW-ENDL.
      * END SCREEN (SCALED): SCORE, HIGH SCORE, NEW HIGH SCORE AFTER THE
      * BANNER ON THE MESSAGE ROW.
           MOVE LAY-MSG-ROW TO WS-ROW.
           COMPUTE WS-COL = LAY-MSG-COL + 15.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE ARC-SCORE TO ES-V.
           MOVE END-SC TO WS-TXT.
           MOVE 13 TO WS-TLEN.
           PERFORM PUT-TEXT.
           IF RP-HI = 1
               PERFORM ENDL-HI.
           IF RP-HI = 1 AND REQ-HSNEW = 'Y'
               PERFORM ENDL-NEW.
           MOVE 0 TO WS-NOP.
       ENDL-HI.
           MOVE LAY-MSG-ROW TO WS-ROW.
           COMPUTE WS-COL = LAY-MSG-COL + 30.
           PERFORM PUT-SBA.
           MOVE PAL-HUD TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE RP-HIV TO HB-V.
           MOVE HUD-HI-B TO WS-TXT.
           MOVE 18 TO WS-TLEN.
           PERFORM PUT-TEXT.
       ENDL-NEW.
           MOVE LAY-MSG-ROW TO WS-ROW.
           COMPUTE WS-COL = LAY-MSG-COL + 50.
           PERFORM PUT-SBA.
           MOVE PAL-PLAYER TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE WS-HE TO WS-HV.
           PERFORM PUT-HILITE.
           MOVE 'NEW HIGH SCORE' TO WS-TXT.
           MOVE 14 TO WS-TLEN.
           PERFORM PUT-TEXT.
           MOVE 0 TO WS-HV.
           PERFORM PUT-HILITE.
