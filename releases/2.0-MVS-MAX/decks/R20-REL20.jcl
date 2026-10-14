//PACREL20 JOB (1),'PACMAN REL20',CLASS=A,MSGCLASS=A,
//             MSGLEVEL=(1,1),REGION=4096K
//* PREFIX HERC01.PACMAN.R20
//CPY1     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COPY(PACSTATE),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * SHARED GAME STATE. NO VALUE CLAUSES (USED IN LINKAGE TOO).
      * ONLY PACGAME/PACMAP/PACAI MODIFY IT; PACDISP READS IT.
       01  PAC-STATE.
           05  MAP-AREA.
               10  MAP-ROW           OCCURS 10 TIMES.
                   15  MAP-CELL      PIC X OCCURS 20 TIMES.
           05  PLAYER-X              PIC 99.
           05  PLAYER-Y              PIC 99.
           05  TICK-COUNT            PIC 999.
           05  SCORE                 PIC 9(4).
           05  PELLETS-LEFT          PIC 999.
           05  LIVES                 PIC 9.
           05  GAME-STATE            PIC X(7).
           05  LAST-CMD              PIC X.
           05  LAST-RESULT           PIC X(7).
           05  F-WON                 PIC 9.
           05  F-LOST                PIC 9.
           05  F-QUIT                PIC 9.
           05  F-EOF                 PIC 9.
           05  F-HIT                 PIC 9.
           05  AI-LEVEL              PIC 9.
           05  GHOST-COUNT           PIC 9.
           05  GHOST-SEED            PIC 9(5).
           05  GH-ENTRY              OCCURS 3 TIMES.
               10  GH-X              PIC 99.
               10  GH-Y              PIC 99.
               10  GH-DIR            PIC 9.
ZZ
//CPY2     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COPY(PACREQ),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * DRIVER REQUEST BLOCK: OP CODE IN, INPUT RESULT OUT.
       01  PAC-REQ.
           05  REQ-OP                PIC X(4).
           05  REQ-KIND              PIC X(3).
           05  REQ-DIR               PIC X.
           05  REQ-CHAR              PIC X.
           05  REQ-LEVEL             PIC 9.
           05  REQ-COUNT             PIC 9.
           05  REQ-MODE              PIC X(3).
           05  REQ-TEXT              PIC X(8).
           05  REQ-METRIC            PIC X.
           05  REQ-COLOR             PIC X.
           05  REQ-INKEY             PIC X.
           05  REQ-INTEXT.
               10  REQ-INTEXT-CH     PIC X OCCURS 8 TIMES.
           05  REQ-HILITE            PIC X.
           05  REQ-ANIM              PIC X.
           05  REQ-REDRAW            PIC X.
           05  REQ-SENDST            PIC X.
      * MVS-G4 GLYPH PROFILE: A AUTO, G GRAPHIC (GE), B BASE, C CLASSIC.
           05  REQ-GLYPHS            PIC X.
      * MVS-GS SCALE: A AUTO, 4 (4X2), 3 (3X2), N NO; T = 4X2 WITH A
      * 1000-BYTE LIMIT (TEST OF THE SIZE GUARD). RESOLVED: 4/3/T/N.
           05  REQ-SCALE             PIC X.
      * MVS-GS CANVAS: A AUTO (ALTERNATE SIZE FROM THE QUERY REPLY),
      * D OR BLANK DEFAULT 80 X 24; TSD ONLY: W X T M U L = SIMULATED.
      * REQ-CW / REQ-CH = THE RESOLVED BUFFER SIZE (0 = 80 X 24).
           05  REQ-CANVAS            PIC X.
           05  REQ-CW                PIC 999.
           05  REQ-CH                PIC 999.
      * MVS-RT (D33): PLAY T TURN / R REALTIME. REQ-STEP FOR PACGAME
      * MOVE: B PLAYER + GHOSTS (TURN), P PLAYER ONLY, G GHOSTS ONLY.
      * REQ-AID = THE RAW AID BYTE OF THE LAST TSC INPUT. REQ-VIS = THE
      * ANIMATION FRAME CHOSEN BY PACRT. REQ-TIME = MILLISECONDS (CLOCK
      * OR DEADLINE). REQ-RTSTAT WAIT/RUN/PAUS/FRZ, REQ-RTQ QUANTUM,
      * REQ-RTIN INPUTS OF THE QUANTUM, REQ-RTCUR/REQ-RTREQ/REQ-RTTTL
      * CURRENT AND REQUESTED DIRECTION + TTL, REQ-RTFR FRAME OF THE
      * QUANTUM (BLANK = RTQF, P = PROMPT, F = FULL REDRAW).
           05  REQ-PLAY              PIC X.
           05  REQ-STEP              PIC X.
           05  REQ-AID               PIC X.
           05  REQ-VIS               PIC 9.
           05  REQ-TIME              PIC S9(9) COMP.
           05  REQ-RTSTAT            PIC X(4).
           05  REQ-RTQ               PIC 9(7).
           05  REQ-RTIN              PIC X(8).
           05  REQ-RTCUR             PIC X.
           05  REQ-RTREQ             PIC X.
           05  REQ-RTTTL             PIC 9.
           05  REQ-RTFR              PIC X.
      * MVS-S1 SOUND (PARM COLUMN 20): A AUTO, Y YES, N/BLANK NO. OUT
      * OF PACPLAT INIT: Y ONLY IN TSC (OR THE TSD DRY RUN), ELSE N.
      * REQ-BELL Y: PACDISP ASKS FOR THE 3270 ALARM (WCC BIT X'04') ON
      * THE STREAM IT SENDS NOW (START, DEATH, WIN; PROBE E15).
           05  REQ-SOUND             PIC X.
           05  REQ-BELL              PIC X.
      * MVS-GP1 RULES (PARM COLUMN 21, D36): A ARCADE, ANYTHING ELSE
      * CLASSIC (1.0-MVS). PACGAME RSET SETS ARC-ON FROM IT.
           05  REQ-RULES             PIC X.
      * MVS-GP2 START LEVEL (PARM COLUMNS 22-23, D37): 01-99, ARCADE
      * ONLY. PACMAIN SETS IT (1 OR 2 DIGITS UP TO THE PARM END; ANY
      * OTHER VALUE = 01); PACGAME RSET STARTS THE GAME AT THAT LEVEL.
           05  REQ-START             PIC 99.
      * MVS-HS (D38): HIGH SCORE (ARCADE ONLY). REQ-HSST N NOT
      * CONFIGURED (NO DD), R LOADED, Z ZERO (MISSING/EMPTY/BAD:
      * HEALED ON SAVE), E UNAVAILABLE. REQ-HISCORE/REQ-HSLVL = THE
      * PERSISTENT VALUE; REQ-HSSCORE/REQ-HSGLVL = THIS GAME (SET BY
      * PACMAIN AT THE END), REQ-HSELIG Y = STARTED AT LEVEL 1.
      * REQ-HSNEW Y SAVED, F NOT SAVED (WRITE FAILED), P PRACTICE
      * START (NOT RECORDED), N NO.
           05  REQ-HSST              PIC X.
           05  REQ-HISCORE           PIC 9(7).
           05  REQ-HSLVL             PIC 999.
           05  REQ-HSSCORE           PIC 9(7).
           05  REQ-HSGLVL            PIC 999.
           05  REQ-HSELIG            PIC X.
           05  REQ-HSNEW             PIC X.
      * MVS-RP (D39, DOCS/RP-POLISH.MD 3): SET BY PACRT, READ BY THE
      * DISPLAY ONLY. REQ-RTFRZ = FREEZE QUANTA LEFT (10 IN THE DEATH /
      * CLEAR QUANTUM, THEN 9 .. 0). REQ-DTHX/REQ-DTHY = PAC-MAN'S CELL
      * AFTER HIS MOVE OF THE LAST GAME STEP (EVERY HIT IS ON IT: THE
      * DEATH CELL WHEN THE STEP RAISED THE ARCADE DEATH FLAG).
           05  REQ-RTFRZ             PIC 99.
           05  REQ-DTHX              PIC 99.
           05  REQ-DTHY              PIC 99.
      * MVS-RP RP.3 SPEED (D39 6): REQ-RTPER = THE REALTIME QUANTUM IN
      * MS, SET ONCE BY PACMAIN (PARM COLUMN 24: F FAST, ELSE NORMAL).
      * PACRT RINI CONVERTS THE DESIGNED 150 MS QUANTA TO IT: REQ-RTFRT
      * FREEZE LENGTH, REQ-RTRDY READY! QUANTA (LAST OF THE FREEZE),
      * REQ-RTPUQ POPUP QUANTA AFTER ITS FIRST FRAME (DISPLAY ONLY).
           05  REQ-RTPER             PIC 999.
           05  REQ-RTFRT             PIC 99.
           05  REQ-RTRDY             PIC 99.
           05  REQ-RTPUQ             PIC 99.
      * MVS-S2 (D41, DOCS/S2-PATTERNS.MD): REQ-ALARM = PARM COLUMN 25,
      * SET ONCE BY PACMAIN: P = ALARM(PATTERN), S = SINGLE (ABSENT OR
      * ANY OTHER VALUE: THE S1 / GP2 ONE BELL). READ BY PACDISP ONLY.
           05  REQ-ALARM             PIC X.
ZZ
//CPY3     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COPY(PACMREQ),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * MAP SERVICE REQUEST: M-OP = LOAD WALL CLR  EAT  CNT
       01  MAP-REQ.
           05  M-OP                  PIC X(4).
           05  M-X                   PIC 99.
           05  M-Y                   PIC 99.
           05  M-FLAG                PIC 9.
           05  M-COUNT               PIC 999.
ZZ
//CPY4     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COPY(PACPAL),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * MVS-G1/G2 TSC RENDERER: PALETTE, HILITE, LAYOUT (ONE PLACE).
      * COLOURS ARE 3270 SET-ATTRIBUTE VALUES (X'F1'-X'F7' = 241-247),
      * CONFIRMED LIVE BY PROBE E4. LAYOUT FOR AN 80 X 24 SCREEN (E5).
       01  PAC-PAL.
           05  PAL-WALL              PIC 999 VALUE 241.
           05  PAL-PELLET            PIC 999 VALUE 247.
           05  PAL-PLAYER            PIC 999 VALUE 246.
           05  PAL-GHOST-1           PIC 999 VALUE 242.
           05  PAL-GHOST-2           PIC 999 VALUE 243.
           05  PAL-GHOST-3           PIC 999 VALUE 245.
           05  PAL-HUD               PIC 999 VALUE 245.
           05  PAL-ERROR             PIC 999 VALUE 242.
           05  PAL-HELP              PIC 999 VALUE 244.
      * MVS-G2 HIGHLIGHTING: EXTENDED-HIGHLIGHT SA VALUES (X'F1' BLINK
      * =241, X'F2' REVERSE =242, X'F4' UNDERSCORE =244; 0 = NONE).
           05  HI-PLAYER             PIC 999 VALUE 242.
           05  HI-GHOST              PIC 999 VALUE 242.
           05  HI-ERROR              PIC 999 VALUE 241.
           05  HI-INPUT              PIC 999 VALUE 244.
      * MVS-G3 GLYPHS (ANIM): MOUTH OPEN/CLOSED, GHOST FEET A/B.
           05  GLY-PLAYER-1          PIC X VALUE 'C'.
           05  GLY-PLAYER-2          PIC X VALUE 'O'.
           05  GLY-GHOST-1           PIC X VALUE 'G'.
           05  GLY-GHOST-2           PIC X VALUE 'W'.
      * MVS-G4 PROFILES (GRAPHIC G, BASE B). A WALL CELL IS A BLANK IN
      * THE WALL COLOUR WITH THIS HIGHLIGHT (X'F2' REVERSE = A SOLID
      * BLOCK) WHEN HIGHLIGHTING IS ON, ELSE '#'. GRAPHIC CODES ARE
      * CP310, SENT AFTER A GE ORDER X'08' (PROBE E9); BASE IS CP037.
           05  HI-WALL               PIC 999 VALUE 242.
      * PELLET: GRAPHIC X'A3' BULLET, BASE X'B3' MIDDLE DOT.
           05  PEL-G                 PIC 999 VALUE 163.
           05  PEL-B                 PIC 999 VALUE 179.
      * GRAPHIC SPRITES: PAC-MAN FACING RIGHT X'9B', LEFT X'9A',
      * CLOSED X'9D'; GHOST X'AA' AND X'DF' (SECOND FRAME).
           05  GPL-RIGHT             PIC 999 VALUE 155.
           05  GPL-LEFT              PIC 999 VALUE 154.
           05  GPL-CLOSED            PIC 999 VALUE 157.
           05  GGH-1                 PIC 999 VALUE 170.
           05  GGH-2                 PIC 999 VALUE 223.
           05  LAY-STATUS-ROW        PIC 99 VALUE 1.
           05  LAY-GHOSTS-ROW        PIC 99 VALUE 2.
           05  LAY-BOARD-ROW         PIC 99 VALUE 4.
           05  LAY-BOARD-COL         PIC 99 VALUE 31.
           05  LAY-MSG-ROW           PIC 99 VALUE 16.
           05  LAY-CMD-ROW           PIC 99 VALUE 18.
           05  LAY-HELP-ROW          PIC 99 VALUE 23.
      * MVS-GS: LAYOUT FIELDS ADDED WITH THE G1-G4 VALUES (FIRST SF ROW,
      * COLUMNS OF THE GHOSTS AND HELP TEXTS).
           05  LAY-SF-ROW            PIC 99 VALUE 1.
           05  LAY-GHOSTS-COL        PIC 99 VALUE 2.
           05  LAY-HELP-COL          PIC 99 VALUE 2.
      * MVS-GS GEOMETRY: COLUMNS OF THE MESSAGE, COMMAND AND STATUS
      * TEXTS (G1-G4 VALUE 2; THE WIDE/TALL LAYOUTS SET THEIR OWN).
           05  LAY-MSG-COL           PIC 999 VALUE 2.
           05  LAY-CMD-COL           PIC 999 VALUE 2.
           05  LAY-STATUS-COL        PIC 999 VALUE 2.
      * MVS-GS SCALED RENDERER (DOCS/GS-SCALED.MD, D31): LAYOUT B. BOARD
      * ROWS 1-20 (4X2 AT COLUMN 1, 3X2 CENTRED AT COLUMN 11), TEXT ROWS
      * 21-23. COPIED OVER THE LAY- VALUES WHEN SCALING IS ACTIVE.
           05  LS-STATUS-ROW         PIC 99 VALUE 21.
           05  LS-GHOSTS-ROW         PIC 99 VALUE 21.
           05  LS-GHOSTS-COL         PIC 99 VALUE 64.
           05  LS-MSG-ROW            PIC 99 VALUE 22.
           05  LS-CMD-ROW            PIC 99 VALUE 23.
           05  LS-HELP-ROW           PIC 99 VALUE 23.
           05  LS-HELP-COL           PIC 99 VALUE 20.
           05  LS-SF-ROW             PIC 99 VALUE 21.
           05  LS-BOARD-ROW          PIC 99 VALUE 1.
           05  LS-BOARD-COL-4        PIC 99 VALUE 1.
           05  LS-BOARD-COL-3        PIC 99 VALUE 11.
      * WALL CONTOURS (CP310 VIA GE): LINE X'A2', BAR X'85', CORNERS
      * TOP-LEFT X'C5', TOP-RIGHT X'D5', BOTTOM-LEFT X'C4', BOTTOM-
      * RIGHT X'D4'. HALF BLOCKS: UPPER X'93', LOWER X'94'; EYE X'A1'.
           05  SG-HLINE              PIC 999 VALUE 162.
           05  SG-VLINE              PIC 999 VALUE 133.
           05  SG-TL                 PIC 999 VALUE 197.
           05  SG-TR                 PIC 999 VALUE 213.
           05  SG-BL                 PIC 999 VALUE 196.
           05  SG-BR                 PIC 999 VALUE 212.
           05  SG-UPPER              PIC 999 VALUE 147.
           05  SG-LOWER              PIC 999 VALUE 148.
           05  SG-EYE                PIC 999 VALUE 161.
      * SPRITES, 2 ROWS EACH, IN THE ORDER PAC-MAN RIGHT, LEFT, SHUT,
      * GHOST FRAME A, FRAME B. CELL CODES: F = BLANK IN REVERSE VIDEO,
      * T = UPPER HALF, B = LOWER HALF, E = EYE IN REVERSE, ' ' = BLANK.
           05  SPR-4                 PIC X(40) VALUE
               'BFT TFB  TFB BFTBFFBTFFTBEEBFTFTBEEBTFTF'.
           05  SPR-3                 PIC X(30) VALUE
               'BF TF  FB FTBFBTFTBEBFTFBEBTFT'.
      * PELLET: SUB-CELL (ROW 1, COLUMN 2) OF ITS TILE, CP310 X'A3'.
           05  LS-PEL-COL            PIC 9 VALUE 2.
      * MVS-GP1 RULES(ARCADE) (D36, DOCS/GP1-POWER.MD 6): POWER PELLET
      * 'o' WHITE, BLINKING WHEN HIGHLIGHTING IS ON; FRIGHTENED GHOSTS
      * BLUE (WHITE IN THE WARNING WINDOW), NOT IN REVERSE OUTSIDE THE
      * SCALED SPRITES; EYES '"' WHITE (SCALED: THE EYE CELLS ONLY).
           05  PAL-POWER             PIC 999 VALUE 247.
           05  HI-POWER              PIC 999 VALUE 241.
           05  PAL-FRIGHT            PIC 999 VALUE 241.
           05  PAL-WARN              PIC 999 VALUE 247.
           05  PAL-EYES              PIC 999 VALUE 247.
           05  GLY-EYES              PIC X VALUE '"'.
      * SCALED EXTRA SPRITES 6 POWER PELLET, 7 EYES (CODES AS SPR-4;
      * e = EYE NOT IN REVERSE, ALSO USED FOR A FRIGHTENED GHOST'S E).
           05  SPR-4X                PIC X(16) VALUE ' BB  TT  ee     '.
           05  SPR-3X                PIC X(12) VALUE ' B  T  e    '.
      * MVS-GP2 RULES(ARCADE) (D37, DOCS/GP2-PROGRESSION.MD 11): FRUIT
      * '%' GREEN (THE ONE COLOUR NO BOARD ACTOR USES), NO BLINK, BASE
      * SET IN EVERY PROFILE; SCALED: SPRITE 8 (CODES AS SPR-4). FRUIT
      * NAMES BY KIND (WIDE / TALL HUD): KIND LETTER + 10 CHARACTERS.
           05  PAL-FRUIT             PIC 999 VALUE 244.
           05  GLY-FRUIT             PIC X VALUE '%'.
           05  SPR-4Y                PIC X(8) VALUE 'BFFB TT '.
           05  SPR-3Y                PIC X(6) VALUE 'BFB T '.
           05  FRUIT-NAMES.
               10  FILLER        PIC X(11) VALUE 'CCHERRY    '.
               10  FILLER        PIC X(11) VALUE 'SSTRAWBERRY'.
               10  FILLER        PIC X(11) VALUE 'OORANGE    '.
               10  FILLER        PIC X(11) VALUE 'AAPPLE     '.
               10  FILLER        PIC X(11) VALUE 'MMELON     '.
               10  FILLER        PIC X(11) VALUE 'GGALAXIAN  '.
               10  FILLER        PIC X(11) VALUE 'BBELL      '.
               10  FILLER        PIC X(11) VALUE 'KKEY       '.
           05  FRUIT-TAB REDEFINES FRUIT-NAMES.
               10  FRUIT-ENT         OCCURS 8 TIMES.
                   15  FRUIT-K       PIC X.
                   15  FRUIT-NAME    PIC X(10).
      * MVS-RP (D39, DOCS/RP-POLISH.MD 2-5), RULES(ARCADE) ONLY: DEATH
      * SPRITES 9-12 (FRAMES 2-5; CODES AS SPR-4), UNSCALED DEATH GLYPHS
      * (FRAMES 2-5, BASE SET), READY! OVER THE CENTRAL WALL BAR (ROW
      * RP-RDY-Y, CELLS RP-RDY-X ..+5), POPUP COLOUR OF AN EATEN GHOST.
           05  SPR-4D                PIC X(32) VALUE
               'BBBBTFFT    TFFT     TT      BB '.
           05  SPR-3D                PIC X(24) VALUE
               'BBBTFT   TFT    T     B '.
           05  GLY-DEATH             PIC X(4) VALUE 'co.*'.
           05  TXT-READY             PIC X(6) VALUE 'READY!'.
           05  RP-RDY-Y              PIC 99 VALUE 5.
           05  RP-RDY-X              PIC 99 VALUE 8.
           05  PAL-POPUP             PIC 999 VALUE 245.
ZZ
//CPY5     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COPY(PACDS),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * 3270 DATA STREAM BUFFER PASSED FROM PACSCR TO PACPLAT (SEND).
       01  PAC-DS.
           05  DS-LEN                PIC S9(4) COMP.
           05  DS-BUF.
               10  DS-BYTE           PIC X OCCURS 2048 TIMES.
           05  DS-KIND               PIC X.
ZZ
//CPY6     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COPY(PACARC),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * MVS-GP1 (D36): ARCADE STATE, RULES(ARCADE) ONLY. NO VALUE
      * CLAUSES (USED IN LINKAGE TOO). OWNED BY PACMAIN, RESET BY
      * PACGAME RSET; CHANGED BY PACGAME AND PACAI (ARC-FACC AND THE
      * MOVE FLAGS ALSO BY PACRT). CLASSIC (ARC-ON = 0) NEVER USES IT.
      * ARC-GM: N NORMAL, F FRIGHTENED, E EYES (WAITING AT HOME).
      * MVS-GP2 (D37), APPENDED AFTER ARC-GH: LEVEL, ROW VALUES COPIED
      * FROM THE PACGAME TABLE (AIB CONFIGURED AI, KNUM REALTIME NORMAL
      * GHOST STEP OF 10, BV/BK FRUIT POINTS/KIND), FRUIT (BX/BY CELL,
      * ITEMS EATEN IN THE LEVEL, BN SPAWNS, BT TICKS LEFT), XL = THE
      * EXTRA-LIFE-AWARDED FLAG, WIDE TOTALS (TURNS, EATN4 GHOSTS,
      * FRUITS, NDIE DEATHS), EVENTS OF THIS STEP (RESET BY ATIK):
      * EA FRUIT APPEARED A, EF FRUIT EATEN F, EX EXTRA LIFE X, EC LEVEL
      * CLEARED C, ED LIFE LOST D; '-' = NO.
       01  PAC-ARC.
           05  ARC-ON                PIC 9.
           05  ARC-SCORE             PIC 9(7).
           05  ARC-POWER             PIC 9.
           05  ARC-FR                PIC 999.
           05  ARC-FTURN             PIC 999.
           05  ARC-FACC              PIC 9.
           05  ARC-CHAIN             PIC 9.
           05  ARC-EATEN             PIC 999.
           05  ARC-MOVEN             PIC 9.
           05  ARC-MOVEF             PIC 9.
           05  ARC-EVT               PIC X(4).
           05  ARC-PTS               PIC 9(4).
           05  ARC-KWARN             PIC 999.
           05  ARC-KFINC             PIC 9.
           05  ARC-GH                OCCURS 3 TIMES.
               10  ARC-GM            PIC X.
               10  ARC-GW            PIC 999.
               10  ARC-GR            PIC 9.
           05  ARC-LEVEL             PIC 999.
           05  ARC-AIB               PIC 9.
           05  ARC-KNUM              PIC 99.
           05  ARC-BV                PIC 9(4).
           05  ARC-BK                PIC X.
           05  ARC-BX                PIC 99.
           05  ARC-BY                PIC 99.
           05  ARC-ITEMS             PIC 999.
           05  ARC-BN                PIC 9.
           05  ARC-BT                PIC 999.
           05  ARC-XL                PIC 9.
           05  ARC-TURNS             PIC 9(7).
           05  ARC-EATN4             PIC 9(4).
           05  ARC-FRUITS            PIC 999.
           05  ARC-NDIE              PIC 99.
           05  ARC-EVF.
               10  ARC-EA            PIC X.
               10  ARC-EF            PIC X.
               10  ARC-EX            PIC X.
               10  ARC-EC            PIC X.
               10  ARC-ED            PIC X.
ZZ
//SRC1     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COBOL(PACMAIN),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACMAIN : DRIVER ONLY. NO GAME RULES, NO I/O STATEMENTS.
      * PACPLAT (HOST)  PACINPT (CARDS)  PACGAME (RULES)  PACMAP (MAP)
      * PACAI (GHOSTS)  PACDISP (TEXT OUTPUT). SEE DOCS/ARCHITECTURE.MD
      * PARM 'TSO' [AIL N] REQUESTS THE INTERACTIVE TSO ADAPTER
      * (MVS-8): CONFIG COMES FROM THE PARM, THE BOARD IS SHOWN BEFORE
      * THE FIRST PROMPT. NO PARM = BATCH CARD MODE (REFERENCE).
      * NO INPUT IS READ ONCE THE GAME HAS ENDED (QUIT, WON, LOST).
      * OPTIONAL 'M' IN PARM COLUMN 11 (E.G. 'BAT       M' OR
      * 'TSO AI3 2 M') MAKES PACDISP PRINT A FINAL METRICS LINE.
      * COLUMN 12 = COLOUR (MVS-G1): A AUTO, Y YES, N/BLANK NO. PARM
      * 'TSD ...' IS THE BATCH DRY RUN OF THE COLOUR SCREENS (HEX).
      * COLUMN 13 = HIGHLIGHT (MVS-G2): A AUTO, Y YES, N/BLANK NO.
      * COLUMN 14 = ANIM (MVS-G3): A AUTO, Y YES, N/BLANK NO.
      * COLUMN 15 = REDRAW: P PARTIAL, ANYTHING ELSE FULL (REFERENCE).
      * COLUMN 16 = GLYPHS (MVS-G4): A AUTO, G GRAPHIC, B BASE, C OR
      * BLANK CLASSIC (THE G3 SCREENS).
      * COLUMN 17 = SCALE (MVS-GS): A AUTO, 4 4X2, 3 3X2, N/BLANK NO
      * (THE G4 SCREENS).
      * COLUMN 18 = CANVAS (MVS-GS GEOMETRY): A AUTO (THE TERMINAL'S
      * ALTERNATE SIZE), D OR BLANK DEFAULT 80 X 24; TSD: SIMULATED.
      * COLUMN 19 = PLAY (MVS-RT, D33): R REALTIME, ANYTHING ELSE TURN.
      * REALTIME (RT-GAME, SEPARATE FROM THE TURN LOOP) NEEDS TSC OR THE
      * BAT / TSD REFERENCE MODES; TSO LINE MODE PLAYS TURN. BEFORE THE
      * START: BLOCKING READS; THE FIRST DIRECTION STARTS THE CLOCK.
      * EACH QUANTUM: ALL INPUT NOW AVAILABLE -> PACRT RIN, PACRT RQ,
      * ONE FRAME (PACDISP RTQF), THEN THE NEXT ABSOLUTE DEADLINE
      * (PACPLAT WDLN, TSC ONLY). PAUSE: BLOCKING READS. A LOST TSC
      * SESSION CONTINUES AS TURN IN LINE MODE.
      * COLUMN 20 = SOUND (MVS-S1): A AUTO, Y YES, N/BLANK NO (THE 3270
      * ALARM ON START, DEATH AND WIN; COLOUR FULL-SCREEN ONLY).
      * COLUMN 21 = RULES (MVS-GP1, D36): A ARCADE (POWER PELLETS, STATE
      * PAC-ARC), ANYTHING ELSE CLASSIC (1.0-MVS).
      * COLUMNS 22-23 = START LEVEL (MVS-GP2, D37, ARCADE ONLY): 1 OR 2
      * DIGITS FROM COLUMN 22 TO THE PARM END, 1-99; ABSENT OR ANY
      * OTHER VALUE = 1 (THE USUAL START).
      * COLUMN 24 = SPEED (MVS-RP RP.3, D39 6, REALTIME ONLY): F FAST
      * (125 MS QUANTUM), ANYTHING ELSE NORMAL (150 MS). THE LEVEL IS
      * THEN 2 DIGITS (THE CLIST ZERO-PADS IT); A DIGIT IN COLUMN 24
      * MAKES 22-24 ONE 3-DIGIT LEVEL (= 1, AS BEFORE RP.3). THE ONLY
      * PLACE WHERE THE QUANTUM IS CHOSEN: REQ-RTPER (PACPLAT
      * DEADLINES, PACRT AND PACGAME CONVERSIONS, PACSCR TIMERS).
      * COLUMN 25 = ALARM (MVS-S2, D41): P PATTERN (PACDISP RINGS 1 TO
      * 4 BELLS PER EVENT), ANYTHING ELSE SINGLE (THE S1 / GP2 BELL).
      * MVS-HS (D38, ARCADE ONLY): PACPLAT HSRD RIGHT AFTER INIT READS
      * THE HIGH SCORE; AFTER THE LAST FRAME HS-END HANDS THE FINAL
      * SCORE, LEVEL AND ELIGIBILITY (STARTED AT LEVEL 1) TO PACPLAT
      * HSWR, WHICH DECIDES AND WRITES; PACDISP END PRINTS THE RESULT.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACMAIN.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       01  PAC-ARC COPY PACARC.
       01  WS-CFG.
           05  WS-CFG-CH         PIC X OCCURS 5 TIMES.
       01  WS-K                  PIC 99.
       01  RT-OVER               PIC 9 VALUE 0.
       01  RT-FRAME              PIC X VALUE SPACE.
       01  WS-LV.
           05  WS-LV1            PIC X.
           05  WS-LV2            PIC X.
       01  WS-LVN REDEFINES WS-LV PIC 99.
       01  WS-LVK                PIC 99.
       01  WS-NOP                PIC 9.
       LINKAGE SECTION.
       01  PARM-AREA.
           05  PARM-LEN          PIC S9(4) COMP.
           05  PARM-MODE         PIC X(3).
           05  FILLER            PIC X.
           05  PARM-CFG          PIC X(5).
           05  FILLER            PIC X.
           05  PARM-MET          PIC X.
           05  PARM-COLOR        PIC X.
           05  PARM-HILITE       PIC X.
           05  PARM-ANIM         PIC X.
           05  PARM-REDRAW       PIC X.
           05  PARM-GLYPHS       PIC X.
           05  PARM-SCALE        PIC X.
           05  PARM-CANVAS       PIC X.
           05  PARM-PLAY         PIC X.
           05  PARM-SOUND        PIC X.
           05  PARM-RULES        PIC X.
           05  PARM-LV1          PIC X.
           05  PARM-LV2          PIC X.
           05  PARM-SPEED        PIC X.
           05  PARM-ALARM        PIC X.
       PROCEDURE DIVISION USING PARM-AREA.
       MAIN-PARA.
           MOVE 'BAT' TO REQ-MODE.
           MOVE SPACE TO REQ-METRIC.
           IF PARM-LEN > 10 AND PARM-MET = 'M'
               MOVE 'M' TO REQ-METRIC.
           IF PARM-LEN > 2 AND PARM-MODE = 'TSO'
               MOVE 'TSO' TO REQ-MODE.
           IF PARM-LEN > 2 AND PARM-MODE = 'TSD'
               MOVE 'TSD' TO REQ-MODE.
           MOVE 'N' TO REQ-COLOR.
           IF PARM-LEN > 11
               MOVE PARM-COLOR TO REQ-COLOR.
           MOVE 'N' TO REQ-HILITE.
           IF PARM-LEN > 12
               MOVE PARM-HILITE TO REQ-HILITE.
           MOVE 'N' TO REQ-ANIM.
           IF PARM-LEN > 13
               MOVE PARM-ANIM TO REQ-ANIM.
           MOVE 'F' TO REQ-REDRAW.
           IF PARM-LEN > 14
               MOVE PARM-REDRAW TO REQ-REDRAW.
           MOVE 'C' TO REQ-GLYPHS.
           IF PARM-LEN > 15
               MOVE PARM-GLYPHS TO REQ-GLYPHS.
           MOVE 'N' TO REQ-SCALE.
           IF PARM-LEN > 16
               MOVE PARM-SCALE TO REQ-SCALE.
           MOVE 'D' TO REQ-CANVAS.
           MOVE 0 TO REQ-CW.
           MOVE 0 TO REQ-CH.
           IF PARM-LEN > 17
               MOVE PARM-CANVAS TO REQ-CANVAS.
           MOVE 'T' TO REQ-PLAY.
           IF PARM-LEN > 18 AND PARM-PLAY = 'R'
               MOVE 'R' TO REQ-PLAY.
           MOVE 'N' TO REQ-SOUND.
           IF PARM-LEN > 19
               MOVE PARM-SOUND TO REQ-SOUND.
           MOVE 'N' TO REQ-BELL.
           MOVE 'C' TO REQ-RULES.
           IF PARM-LEN > 20
               MOVE PARM-RULES TO REQ-RULES.
           MOVE 1 TO REQ-START.
           IF PARM-LEN = 22
               MOVE '0' TO WS-LV1
               MOVE PARM-LV1 TO WS-LV2
               PERFORM SET-START.
           IF PARM-LEN > 22
               MOVE PARM-LV1 TO WS-LV1
               MOVE PARM-LV2 TO WS-LV2
               PERFORM SET-START.
           IF PARM-LEN > 23 AND PARM-SPEED NUMERIC
               MOVE 1 TO REQ-START.
           MOVE 150 TO REQ-RTPER.
           IF PARM-LEN > 23 AND PARM-SPEED = 'F'
               MOVE 125 TO REQ-RTPER.
           MOVE 'S' TO REQ-ALARM.
           IF PARM-LEN > 24 AND PARM-ALARM = 'P'
               MOVE 'P' TO REQ-ALARM.
           MOVE 0 TO REQ-RTFRT.
           MOVE 0 TO REQ-RTRDY.
           MOVE 0 TO REQ-RTPUQ.
           MOVE 'B' TO REQ-STEP.
           MOVE SPACE TO REQ-SENDST.
           MOVE 'INIT' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE 'N' TO REQ-HSST.
           MOVE 'N' TO REQ-HSNEW.
           IF REQ-RULES = 'A'
               MOVE 'HSRD' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           IF REQ-MODE = 'TSO'
               MOVE 'T' TO REQ-PLAY.
           MOVE 'RSET' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE 'OPEN' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
           MOVE 'HEAD' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           IF REQ-PLAY = 'R'
               PERFORM RT-GAME THRU RT-GAME-EXIT
           ELSE IF REQ-MODE = 'BAT'
               PERFORM BAT-START THRU BAT-START-EXIT
           ELSE
               PERFORM TSO-START THRU TSO-START-EXIT.
           PERFORM TURN-PARA THRU TURN-PARA-EXIT
               UNTIL F-EOF = 1 OR F-QUIT = 1 OR F-WON = 1
                  OR F-LOST = 1.
           IF REQ-RULES = 'A'
               PERFORM HS-END.
           MOVE 'END ' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE 'CLOS' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
           MOVE 'FINI' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           STOP RUN.
       RT-GAME.
           MOVE 'RINI' TO REQ-OP.
           CALL 'PACRT' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           IF REQ-MODE = 'BAT'
               PERFORM RT-READB
               PERFORM RT-CONFIG THRU RT-CONFIG-EXIT
           ELSE IF PARM-LEN > 4
               PERFORM COPY-PARM-CFG
               MOVE 'PARM' TO REQ-OP
               CALL 'PACINPT' USING PAC-REQ
               PERFORM APPLY-CONFIG THRU APPLY-CONFIG-EXIT.
           PERFORM SHOW-START.
      * THE FIRST SCREEN (TSC/TSD; NOTHING IN BAT, WHERE THE EVENT READ
      * AHEAD FOR THE CONFIGURATION MUST STAY IN REQ-KIND).
           IF REQ-MODE NOT = 'BAT'
               MOVE 'MOV' TO REQ-KIND
               MOVE 'PRMT' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC
               PERFORM RT-READB.
           PERFORM RT-PRE THRU RT-PRE-EXIT
               UNTIL REQ-RTSTAT NOT = 'WAIT' OR RT-OVER = 1.
           IF RT-OVER = 0 AND REQ-MODE = 'TSC'
               MOVE 'CLOK' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           PERFORM RT-QUANTUM THRU RT-QUANTUM-EXIT
               UNTIL RT-OVER = 1.
           IF REQ-PLAY = 'T' AND F-EOF = 0 AND F-QUIT = 0
                             AND F-WON = 0 AND F-LOST = 0
               MOVE 'B' TO REQ-STEP
               PERFORM READ-INPUT THRU READ-INPUT-EXIT.
       RT-GAME-EXIT.
           EXIT.
       RT-CONFIG.
      * BATCH REALTIME: AN OPTIONAL FIRST CARD AI<L> <N>.
           IF REQ-KIND = 'CFG'
               MOVE 'CFG ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
               PERFORM RT-READB.
       RT-CONFIG-EXIT.
           EXIT.
       RT-READB.
           MOVE SPACE TO REQ-INKEY.
           MOVE 'RTRB' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
       RT-READ.
           MOVE SPACE TO REQ-INKEY.
           MOVE 'RTRD' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
       RT-PRE.
      * BEFORE THE START: ONE EVENT, THEN A SCREEN (RESTORE);
      * A DIRECTION STARTS THE GAME (ITS QUANTUM IS THE FIRST ONE).
           PERFORM RT-EVENT THRU RT-EVENT-EXIT.
           IF RT-OVER = 1 OR REQ-RTSTAT NOT = 'WAIT'
               GO TO RT-PRE-EXIT.
      * RT3: EVERY INPUT GETS A SCREEN (KEYBOARD RESTORE), ELSE THE NEXT
      * KEY WOULD BE LOST WITH C3270 TYPEAHEAD OFF.
           IF REQ-KIND NOT = 'NON'
               PERFORM RT-PRE-SCREEN.
           PERFORM RT-READB.
       RT-PRE-EXIT.
           EXIT.
       RT-PRE-SCREEN.
           MOVE 'MOV' TO REQ-KIND.
           IF RT-FRAME = 'F'
               MOVE 'RDR' TO REQ-KIND.
           MOVE 'PRMT' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE SPACE TO RT-FRAME.
       RT-QUANTUM.
           PERFORM RT-COLLECT THRU RT-COLLECT-EXIT.
           PERFORM RT-PAUSED THRU RT-PAUSED-EXIT
               UNTIL REQ-RTSTAT NOT = 'PAUS' OR RT-OVER = 1.
           IF RT-OVER = 1
               GO TO RT-QUANTUM-EXIT.
           MOVE 'RQ  ' TO REQ-OP.
           CALL 'PACRT' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE RT-FRAME TO REQ-RTFR.
           MOVE SPACE TO RT-FRAME.
           MOVE 'RTQF' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           IF F-WON = 1 OR F-LOST = 1
               MOVE 1 TO RT-OVER
               GO TO RT-QUANTUM-EXIT.
           IF REQ-MODE = 'TSO'
               MOVE 'T' TO REQ-PLAY
               MOVE 1 TO RT-OVER
               GO TO RT-QUANTUM-EXIT.
           IF REQ-MODE = 'TSC'
               MOVE 'WDLN' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
       RT-QUANTUM-EXIT.
           EXIT.
       RT-COLLECT.
      * EVERY INPUT AVAILABLE NOW (A CARD = THE INPUT OF ONE QUANTUM).
           MOVE SPACES TO REQ-KIND.
           PERFORM RT-DRAIN-ONE THRU RT-DRAIN-ONE-EXIT
               UNTIL REQ-KIND = 'NON' OR RT-OVER = 1.
       RT-COLLECT-EXIT.
           EXIT.
       RT-DRAIN-ONE.
           PERFORM RT-READ.
           PERFORM RT-EVENT THRU RT-EVENT-EXIT.
       RT-DRAIN-ONE-EXIT.
           EXIT.
       RT-PAUSED.
      * PAUSE: THE SCREEN, THEN BLOCKING READS UNTIL P (OR Q / EOF); THE
      * CLOCK RESTARTS FROM NOW; WHAT FOLLOWS IN THE INPUT IS COLLECTED.
           IF RT-FRAME = SPACE
               MOVE 'P' TO RT-FRAME.
           PERFORM RT-PRE-SCREEN.
           PERFORM RT-PAUSE-ONE THRU RT-PAUSE-ONE-EXIT
               UNTIL REQ-RTSTAT NOT = 'PAUS' OR RT-OVER = 1.
           IF RT-OVER = 1
               GO TO RT-PAUSED-EXIT.
           IF REQ-MODE = 'TSC'
               MOVE 'CLOK' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           PERFORM RT-COLLECT THRU RT-COLLECT-EXIT.
       RT-PAUSED-EXIT.
           EXIT.
       RT-PAUSE-ONE.
           PERFORM RT-READB.
           PERFORM RT-EVENT THRU RT-EVENT-EXIT.
           IF RT-OVER = 0 AND REQ-RTSTAT = 'PAUS'
                          AND REQ-KIND NOT = 'NON'
               PERFORM RT-PRE-SCREEN.
       RT-PAUSE-ONE-EXIT.
           EXIT.
       RT-EVENT.
      * ONE INPUT EVENT: DIRECTIONS AND PAUSE GO TO PACRT, EVERY EVENT
      * IS RECORDED THERE; Q / EOF END, A LOST TSC SESSION GOES TURN.
           IF REQ-KIND = 'NON' OR REQ-KIND = 'IGN' OR REQ-KIND = 'CFG'
               GO TO RT-EVENT-EXIT.
           IF REQ-KIND = 'ERR'
               MOVE 'T' TO REQ-PLAY
               MOVE 1 TO RT-OVER
               GO TO RT-EVENT-EXIT.
           IF REQ-KIND = 'EOF'
               MOVE 'EOF ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
               MOVE 1 TO RT-OVER
               GO TO RT-EVENT-EXIT.
           MOVE 'RIN ' TO REQ-OP.
           CALL 'PACRT' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           IF REQ-KIND = 'QUI'
               MOVE 'QUIT' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
               MOVE 1 TO RT-OVER
               GO TO RT-EVENT-EXIT.
           IF REQ-INKEY = 'E' AND RT-FRAME = SPACE
               MOVE 'P' TO RT-FRAME.
           IF REQ-KIND = 'INV'
               MOVE 'INVL' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           IF REQ-KIND = 'INV' AND RT-FRAME = SPACE
               MOVE 'P' TO RT-FRAME.
           IF REQ-KIND = 'RDR'
               MOVE 'F' TO RT-FRAME.
       RT-EVENT-EXIT.
           EXIT.
       BAT-START.
           PERFORM READ-INPUT THRU READ-INPUT-EXIT.
           PERFORM CHECK-CONFIG THRU CHECK-CONFIG-EXIT.
           PERFORM SHOW-START.
       BAT-START-EXIT.
           EXIT.
       TSO-START.
           IF PARM-LEN > 4
               PERFORM COPY-PARM-CFG
               MOVE 'PARM' TO REQ-OP
               CALL 'PACINPT' USING PAC-REQ
               PERFORM APPLY-CONFIG THRU APPLY-CONFIG-EXIT.
           PERFORM SHOW-START.
           PERFORM READ-INPUT THRU READ-INPUT-EXIT.
       TSO-START-EXIT.
           EXIT.
       SET-START.
           MOVE 0 TO WS-LVK.
           IF WS-LV NUMERIC
               MOVE WS-LVN TO WS-LVK.
           IF WS-LVK > 0
               MOVE WS-LVK TO REQ-START.
           MOVE 0 TO WS-NOP.
       COPY-PARM-CFG.
      * ONLY PARM-LEN BYTES ARE VALID: BLANK WHAT LIES BEYOND THEM.
           MOVE PARM-CFG TO WS-CFG.
           COMPUTE WS-K = PARM-LEN - 3.
           PERFORM BLANK-CFG-CH UNTIL WS-K > 5.
           MOVE WS-CFG TO REQ-TEXT.
       BLANK-CFG-CH.
           MOVE SPACE TO WS-CFG-CH (WS-K).
           ADD 1 TO WS-K.
       SHOW-START.
           MOVE 'INIT' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE 'STAT' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
       APPLY-CONFIG.
           IF REQ-KIND = 'CFG'
               MOVE 'CFG ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC.
       APPLY-CONFIG-EXIT.
           EXIT.
       READ-INPUT.
           MOVE 'PRMT' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE 'READ' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
           PERFORM IDLE-TICK UNTIL REQ-KIND NOT = 'TCK'.
           IF REQ-KIND = 'EOF'
               MOVE 'EOF ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC.
       READ-INPUT-EXIT.
           EXIT.
       IDLE-TICK.
      * MVS-G3 VISUAL TICK: THE WAIT FOR INPUT WAS INTERRUPTED BY AN
      * IDLE TICK. ONLY THE SCREEN CHANGES; NO GAME CALL, NO TURN.
           MOVE 'TICK' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE 'READ' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
       CHECK-CONFIG.
           IF REQ-KIND = 'CFG'
               MOVE 'CFG ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
               PERFORM READ-INPUT THRU READ-INPUT-EXIT.
       CHECK-CONFIG-EXIT.
           EXIT.
       TURN-PARA.
           PERFORM DISPATCH THRU DISPATCH-EXIT.
           IF F-QUIT = 0 AND F-WON = 0 AND F-LOST = 0
               PERFORM READ-INPUT THRU READ-INPUT-EXIT.
       TURN-PARA-EXIT.
           EXIT.
       DISPATCH.
           IF REQ-KIND = 'MOV'
               MOVE 'MOVE' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
               MOVE 'STAT' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC
           ELSE IF REQ-KIND = 'QUI'
               MOVE 'QUIT' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
           ELSE IF REQ-KIND = 'RDR'
               MOVE 'STAT' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC
           ELSE
               MOVE 'INVL' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
       DISPATCH-EXIT.
           EXIT.
       HS-END.
           MOVE ARC-SCORE TO REQ-HSSCORE.
           MOVE ARC-LEVEL TO REQ-HSGLVL.
           MOVE 'N' TO REQ-HSELIG.
           IF REQ-START = 1
               MOVE 'Y' TO REQ-HSELIG.
           MOVE 'HSWR' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
ZZ
//COB1     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ1,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.R20.COBOL(PACMAIN),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.R20.COPY,DISP=SHR
//SRC2     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COBOL(PACGAME),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
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
       01  MAP-REQ COPY PACMREQ.
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
ZZ
//COB2     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ2,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.R20.COBOL(PACGAME),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.R20.COPY,DISP=SHR
//SRC3     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COBOL(PACMAP),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACMAP : MAP SERVICE (PORTABLE, NO TERMINAL I/O).
      * OPS : LOAD  COPY THE LEVEL INTO THE STATE
      *       WALL  M-FLAG = 1 IF (M-X,M-Y) IS A WALL OR OUTSIDE
      *       CLR   BLANK THE CELL        EAT  M-FLAG = 1 IF A PELLET
      *       CNT   M-COUNT = PELLETS ON THE MAP
      *       LDA   (MVS-GP1 ARCADE, D36) LOAD + THE 4 POWER PELLETS
      *             'o' (MAPS/ARCADE1.TXT); EAT GIVES M-FLAG = 2 ON
      *             'o', CNT COUNTS '.' AND 'o' (CLASSIC HAS NO 'o').
      * LEVEL LITERALS MUST MATCH MAPS/LEVEL1.TXT.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACMAP.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  MAP-DATA.
           05  FILLER            PIC X(20) VALUE '####################'.
           05  FILLER            PIC X(20) VALUE '#........##........#'.
           05  FILLER            PIC X(20) VALUE '#.##.###.##.###.##.#'.
           05  FILLER            PIC X(20) VALUE '#..................#'.
           05  FILLER            PIC X(20) VALUE '#.##.#.######.#.##.#'.
           05  FILLER            PIC X(20) VALUE '#....#...##...#....#'.
           05  FILLER            PIC X(20) VALUE '#.##.###.##.###.##.#'.
           05  FILLER            PIC X(20) VALUE '#..................#'.
           05  FILLER            PIC X(20) VALUE '#..................#'.
           05  FILLER            PIC X(20) VALUE '####################'.
       01  PWR-DATA              PIC X(16) VALUE '0204190402081908'.
       01  PWR-TABLE REDEFINES PWR-DATA.
           05  PWR-ENTRY         OCCURS 4 TIMES.
               10  PWR-X         PIC 99.
               10  PWR-Y         PIC 99.
       01  WS-K                  PIC 9.
       01  WS-ROW                PIC 99.
       01  WS-COL                PIC 99.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  MAP-REQ COPY PACMREQ.
       PROCEDURE DIVISION USING PAC-STATE MAP-REQ.
       MAIN-PARA.
           MOVE 0 TO M-FLAG.
           IF M-OP = 'LOAD'
               MOVE MAP-DATA TO MAP-AREA
           ELSE IF M-OP = 'LDA '
               MOVE MAP-DATA TO MAP-AREA
               PERFORM PUT-POWER VARYING WS-K FROM 1 BY 1
                   UNTIL WS-K > 4
           ELSE IF M-OP = 'WALL'
               PERFORM DO-WALL THRU DO-WALL-EXIT
           ELSE IF M-OP = 'CLR '
               MOVE ' ' TO MAP-CELL (M-Y M-X)
           ELSE IF M-OP = 'EAT '
               PERFORM DO-EAT THRU DO-EAT-EXIT
           ELSE IF M-OP = 'CNT '
               PERFORM DO-COUNT.
           GOBACK.
       DO-WALL.
           IF M-X < 1 OR M-X > 20 OR M-Y < 1 OR M-Y > 10
               MOVE 1 TO M-FLAG
           ELSE IF MAP-CELL (M-Y M-X) = '#'
               MOVE 1 TO M-FLAG.
       DO-WALL-EXIT.
           EXIT.
       DO-EAT.
           IF MAP-CELL (M-Y M-X) = '.'
               MOVE ' ' TO MAP-CELL (M-Y M-X)
               MOVE 1 TO M-FLAG
           ELSE IF MAP-CELL (M-Y M-X) = 'o'
               MOVE ' ' TO MAP-CELL (M-Y M-X)
               MOVE 2 TO M-FLAG.
       DO-EAT-EXIT.
           EXIT.
       DO-COUNT.
           MOVE 0 TO M-COUNT.
           PERFORM COUNT-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
       COUNT-ROW.
           PERFORM COUNT-CELL THRU COUNT-CELL-EXIT
               VARYING WS-COL FROM 1 BY 1 UNTIL WS-COL > 20.
       COUNT-CELL.
           IF MAP-CELL (WS-ROW WS-COL) = '.'
                                 OR MAP-CELL (WS-ROW WS-COL) = 'o'
               ADD 1 TO M-COUNT.
       COUNT-CELL-EXIT.
           EXIT.
       PUT-POWER.
           MOVE PWR-X (WS-K) TO WS-COL.
           MOVE PWR-Y (WS-K) TO WS-ROW.
           MOVE 'o' TO MAP-CELL (WS-ROW WS-COL).
ZZ
//COB3     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ3,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.R20.COBOL(PACMAP),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.R20.COPY,DISP=SHR
//SRC4     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COBOL(PACAI),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACAI : GHOST MOVEMENT FOR ALL ACTIVE GHOSTS (PORTABLE).
      * AI-LEVEL 1 RANDOM, 2 PERSISTENT DIRECTION, 3 CHASE (MANHATTAN).
      * LCG SEED IN THE STATE (FIXED 12345) KEEPS RUNS REPRODUCIBLE.
      * WALL TESTS GO THROUGH PACMAP. NO NESTED SUBSCRIPTS (D13).
      * MVS-GP1 (D36, ARC-ON = 1): EYES NEVER MOVE; NORMAL GHOSTS MOVE
      * BY THEIR AI LEVEL WHEN ARC-MOVEN = 1; FRIGHTENED ONES WHEN
      * ARC-MOVEF = 1: THE PENDING REVERSAL FIRST (WHEN OPEN), ELSE
      * FLEE = MAXIMUM MANHATTAN DISTANCE FROM PAC-MAN, NO REVERSAL
      * UNLESS NOTHING ELSE IS OPEN, TIE ORDER U D L R, NO SEED USE.
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
       01  WS-SKIP               PIC 9.
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
       01  PAC-ARC COPY PACARC.
       PROCEDURE DIVISION USING PAC-STATE PAC-ARC.
       MAIN-PARA.
           PERFORM GHOST-MOVE THRU GHOST-MOVE-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           GOBACK.
       GHOST-MOVE.
           IF ARC-ON = 1
               PERFORM ARC-CHOOSE THRU ARC-CHOOSE-EXIT
               IF WS-SKIP = 1
                   GO TO GHOST-MOVE-EXIT.
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
      * ------------- MVS-GP1 ARCADE (D36, ARC-ON = 1) -------------
       ARC-CHOOSE.
      * WS-SKIP = 1: THIS GHOST DOES NOT TAKE THE CLASSIC MOVE (EYES,
      * NOT DUE, OR FRIGHTENED: THE FLEE MOVE IS DONE HERE).
           MOVE 1 TO WS-SKIP.
           IF ARC-GM (WS-G) = 'E'
               GO TO ARC-CHOOSE-EXIT.
           IF ARC-GM (WS-G) = 'N'
               IF ARC-MOVEN = 1
                   MOVE 0 TO WS-SKIP
                   GO TO ARC-CHOOSE-EXIT
               ELSE
                   GO TO ARC-CHOOSE-EXIT.
           IF ARC-MOVEF = 1
               PERFORM FLEE-MOVE THRU FLEE-MOVE-EXIT.
       ARC-CHOOSE-EXIT.
           EXIT.
       FLEE-MOVE.
           MOVE GH-DIR (WS-G) TO WS-CUR.
           MOVE REV-D (WS-CUR) TO WS-REVD.
           MOVE 0 TO CAND-N.
           IF ARC-GR (WS-G) = 1
               MOVE 0 TO ARC-GR (WS-G)
               PERFORM TRY-REVERSE THRU TRY-REVERSE-EXIT.
           IF CAND-N = 1
               MOVE CAND (1) TO WS-D
               PERFORM STEP-GHOST
               GO TO FLEE-MOVE-EXIT.
           PERFORM FLEE-PROBE THRU FLEE-PROBE-EXIT
               VARYING WS-D FROM 1 BY 1 UNTIL WS-D > 4.
           IF CAND-N = 0
               PERFORM TRY-REVERSE THRU TRY-REVERSE-EXIT.
           IF CAND-N = 0
               GO TO FLEE-MOVE-EXIT.
           MOVE -1 TO BEST-DIST.
           PERFORM FLEE-EVAL THRU FLEE-EVAL-EXIT
               VARYING WS-J FROM 1 BY 1 UNTIL WS-J > CAND-N.
           PERFORM STEP-GHOST.
       FLEE-MOVE-EXIT.
           EXIT.
       FLEE-PROBE.
           COMPUTE G-NX = GH-X (WS-G) + DIR-DX (WS-D) - 1.
           COMPUTE G-NY = GH-Y (WS-G) + DIR-DY (WS-D) - 1.
           MOVE G-NX TO M-X.
           MOVE G-NY TO M-Y.
           MOVE 'WALL' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 0 AND WS-D NOT = WS-REVD
               ADD 1 TO CAND-N
               MOVE WS-D TO CAND (CAND-N).
       FLEE-PROBE-EXIT.
           EXIT.
       FLEE-EVAL.
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
           IF DIST-T > BEST-DIST
               MOVE DIST-T TO BEST-DIST
               MOVE WS-K TO WS-D.
       FLEE-EVAL-EXIT.
           EXIT.
ZZ
//COB4     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ4,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.R20.COBOL(PACAI),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.R20.COPY,DISP=SHR
//SRC5     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COBOL(PACINPT),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACINPT : INPUT ADAPTER. ONE SYSIN CARD -> ONE REQUEST.
      * OPS : OPEN  READ  CLOS  PARM (CLASSIFY REQ-TEXT, NO I/O).
      * REQ-KIND: MOV (REQ-DIR U/D/L/R)  QUI  CFG (REQ-LEVEL,
      *   REQ-COUNT)  INV  EOF, AND IN TSO MODE RDR (BLANK LINE =
      *   REDRAW REQUEST). REQ-CHAR HOLDS THE COMMAND'S FIRST BYTE.
      * TSC (MVS-G1): READ ASKS PACPLAT RECV FOR ONE FULL-SCREEN INPUT;
      *   ENTER = THE TYPED FIELD, CLASSIFIED AS A CARD; ANY OTHER KEY
      *   (PA2 RESHOW) = RDR; AN ERROR LEAVES TSC AND READS A LINE.
      * MVS-RT (D33): RTRD (NON-BLOCKING) / RTRB (BLOCKING) RETURN ONE
      *   INPUT EVENT: MOV, QUI, PAU (PAUSE), RDR, INV, CFG, IGN (AN AID
      *   WITHOUT MEANING), NON (NOTHING MORE NOW), EOF, ERR (TSC LOST).
      *   TSC: PACPLAT POLL / RECV; PF7 U PF8 D PF10 L PF11 R, PF9 PAU
      *   (RT3: THE LAUNCHER MAPS P TO PF9), PA2 RDR,
      *   ENTER = THE TYPED FIELD (U/D/L/R, Q, P, BLANK = RDR, ELSE INV;
      *   REQ-INKEY STAYS E). BAT/TSD: ONE CARD = ONE QUANTUM, ITS
      *   CHARACTERS IN ORDER UP TO THE FIRST BLANK (U D L R ANY CASE,
      *   Q, P, * = PA2, . OR + = NOTHING, ELSE INV), THEN NON; A CARD
      *   STARTING WITH A IS ONE CFG EVENT.
      * ONLY THIS MODULE KNOWS ABOUT THE TERMINAL/CARD SOURCE.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACINPT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT COMMAND-FILE ASSIGN TO UT-S-SYSIN.
       DATA DIVISION.
       FILE SECTION.
       FD  COMMAND-FILE
           RECORDING MODE IS F
           LABEL RECORDS ARE OMITTED
           RECORD CONTAINS 80 CHARACTERS
           DATA RECORD IS COMMAND-RECORD.
       01  COMMAND-RECORD        PIC X(80).
       WORKING-STORAGE SECTION.
       01  WS-CARD.
           05  CMD-CHAR          PIC X.
           05  FILLER            PIC X.
           05  CMD-LEVEL         PIC X.
           05  FILLER            PIC X.
           05  CMD-COUNT         PIC X.
           05  FILLER            PIC X(75).
       01  RAW-CARD REDEFINES WS-CARD.
           05  RAW-CHAR          PIC X OCCURS 80 TIMES.
       01  NORM-REC.
           05  NR-CHAR           PIC X OCCURS 80 TIMES.
       01  WS-OFF                PIC 99.
       01  WS-I                  PIC 99.
       01  WS-J                  PIC 99.
       01  WS-LIM                PIC 99.
       01  RT-CARD.
           05  RT-CH             PIC X OCCURS 80 TIMES.
       01  RT-POS                PIC 99 VALUE 0.
       01  RT-C                  PIC X.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  WS-V                  PIC 9(4).
       01  WS-NOP                PIC 9.
       LINKAGE SECTION.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'OPEN'
               OPEN INPUT COMMAND-FILE
           ELSE IF (REQ-OP = 'RTRD' OR REQ-OP = 'RTRB')
                                AND REQ-MODE = 'TSC'
               PERFORM RT-TSC THRU RT-TSC-EXIT
           ELSE IF REQ-OP = 'RTRD' OR REQ-OP = 'RTRB'
               PERFORM RT-CARD-READ THRU RT-CARD-READ-EXIT
           ELSE IF REQ-OP = 'READ' AND REQ-MODE = 'TSC'
               PERFORM TSC-READ THRU TSC-READ-EXIT
           ELSE IF REQ-OP = 'READ'
               PERFORM DO-READ THRU DO-READ-EXIT
           ELSE IF REQ-OP = 'CLOS'
               CLOSE COMMAND-FILE
           ELSE IF REQ-OP = 'PARM'
               MOVE SPACES TO WS-CARD
               MOVE REQ-TEXT TO WS-CARD
               PERFORM CLASSIFY THRU CLASSIFY-EXIT.
           GOBACK.
       DO-READ.
           MOVE SPACES TO REQ-KIND.
           READ COMMAND-FILE AT END MOVE 'EOF' TO REQ-KIND.
           IF REQ-KIND = SPACES
               MOVE COMMAND-RECORD TO WS-CARD.
           IF REQ-KIND = SPACES AND REQ-MODE NOT = 'BAT'
               PERFORM NORMALIZE THRU NORMALIZE-EXIT.
           IF REQ-KIND = SPACES AND REQ-MODE NOT = 'BAT'
                                AND WS-CARD = SPACES
               MOVE 'RDR' TO REQ-KIND.
           IF REQ-KIND = SPACES AND REQ-MODE = 'TSD'
                                AND CMD-CHAR = '+'
               MOVE 'TCK' TO REQ-KIND.
           IF REQ-KIND = SPACES
               PERFORM CLASSIFY THRU CLASSIFY-EXIT.
       DO-READ-EXIT.
           EXIT.
       TSC-READ.
           MOVE 'RECV' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE 'READ' TO REQ-OP.
           IF REQ-INKEY = 'X'
               PERFORM DO-READ THRU DO-READ-EXIT
               GO TO TSC-READ-EXIT.
           IF REQ-INKEY = 'T'
               MOVE 'TCK' TO REQ-KIND
               GO TO TSC-READ-EXIT.
           MOVE 'RDR' TO REQ-KIND.
           IF REQ-INKEY NOT = 'E'
               GO TO TSC-READ-EXIT.
           MOVE SPACES TO WS-CARD.
           MOVE REQ-INTEXT TO WS-CARD.
           PERFORM NORMALIZE THRU NORMALIZE-EXIT.
           IF WS-CARD NOT = SPACES
               PERFORM CLASSIFY THRU CLASSIFY-EXIT.
       TSC-READ-EXIT.
           EXIT.
       RT-TSC.
      * MVS-RT TERMINAL INPUT: ONE AID (POLL) OR WAIT FOR ONE (RECV).
           MOVE SPACE TO REQ-CHAR.
           IF REQ-OP = 'RTRD'
               MOVE 'POLL' TO REQ-OP
           ELSE
               MOVE 'RECV' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE 'RTRD' TO REQ-OP.
           MOVE 'NON' TO REQ-KIND.
           IF REQ-INKEY = 'N'
               GO TO RT-TSC-EXIT.
           MOVE 'ERR' TO REQ-KIND.
           IF REQ-INKEY = 'X'
               GO TO RT-TSC-EXIT.
           IF REQ-INKEY = 'E'
               PERFORM RT-ENTER THRU RT-ENTER-EXIT
               GO TO RT-TSC-EXIT.
           MOVE 'IGN' TO REQ-KIND.
           MOVE REQ-AID TO HX-B.
           MOVE HEXN TO WS-V.
           IF WS-V = 247
               MOVE 'U' TO RT-C
               PERFORM RT-CHAR.
           IF WS-V = 248
               MOVE 'D' TO RT-C
               PERFORM RT-CHAR.
           IF WS-V = 122
               MOVE 'L' TO RT-C
               PERFORM RT-CHAR.
           IF WS-V = 123
               MOVE 'R' TO RT-C
               PERFORM RT-CHAR.
           IF WS-V = 249
               MOVE 'P' TO RT-C
               PERFORM RT-CHAR.
           IF WS-V = 110
               MOVE 'RDR' TO REQ-KIND.
       RT-TSC-EXIT.
           EXIT.
       RT-ENTER.
           MOVE 'RDR' TO REQ-KIND.
           MOVE SPACES TO WS-CARD.
           MOVE REQ-INTEXT TO WS-CARD.
           PERFORM NORMALIZE THRU NORMALIZE-EXIT.
           IF WS-CARD = SPACES
               GO TO RT-ENTER-EXIT.
           MOVE CMD-CHAR TO RT-C.
           PERFORM RT-CHAR.
       RT-ENTER-EXIT.
           EXIT.
       RT-CARD-READ.
      * MVS-RT CARDS: THE NEXT EVENT OF THE CURRENT CARD, NON AT ITS END
           IF RT-POS = 0
               PERFORM RT-NEW-CARD THRU RT-NEW-CARD-EXIT
               GO TO RT-CARD-READ-EXIT.
           MOVE 'NON' TO REQ-KIND.
           PERFORM RT-SCAN UNTIL REQ-KIND NOT = 'NON' OR RT-POS = 0.
       RT-CARD-READ-EXIT.
           EXIT.
       RT-NEW-CARD.
           MOVE SPACES TO REQ-KIND.
           READ COMMAND-FILE AT END MOVE 'EOF' TO REQ-KIND.
           IF REQ-KIND = 'EOF'
               GO TO RT-NEW-CARD-EXIT.
           MOVE COMMAND-RECORD TO RT-CARD.
           MOVE 1 TO RT-POS.
           IF RT-CH (1) = 'A'
               MOVE COMMAND-RECORD TO WS-CARD
               PERFORM CLASSIFY THRU CLASSIFY-EXIT
               MOVE 81 TO RT-POS.
           IF REQ-KIND = 'CFG'
               GO TO RT-NEW-CARD-EXIT.
           MOVE 'NON' TO REQ-KIND.
           PERFORM RT-SCAN UNTIL REQ-KIND NOT = 'NON' OR RT-POS = 0.
       RT-NEW-CARD-EXIT.
           EXIT.
       RT-SCAN.
      * ONE CHARACTER: BLANK OR PAST COLUMN 80 ENDS THE CARD (NON).
           IF RT-POS > 80
               MOVE 0 TO RT-POS
           ELSE IF RT-CH (RT-POS) = SPACE
               MOVE 0 TO RT-POS
           ELSE
               MOVE RT-CH (RT-POS) TO RT-C
               ADD 1 TO RT-POS
               PERFORM RT-CARD-CHAR.
           MOVE 0 TO WS-NOP.
       RT-CARD-CHAR.
           IF RT-C NOT = '.' AND RT-C NOT = '+'
               PERFORM RT-CHAR.
           MOVE 0 TO WS-NOP.
       RT-CHAR.
      * ONE REALTIME INPUT CHARACTER -> EVENT (P PAUSE, * REDRAW).
           MOVE RT-C TO REQ-CHAR.
           IF RT-C = 'P' OR RT-C = 'p'
               MOVE 'PAU' TO REQ-KIND
           ELSE IF RT-C = '*'
               MOVE 'RDR' TO REQ-KIND
           ELSE IF RT-C = 'A'
               MOVE 'INV' TO REQ-KIND
           ELSE
               MOVE SPACES TO WS-CARD
               MOVE RT-C TO CMD-CHAR
               PERFORM CLASSIFY THRU CLASSIFY-EXIT.
           MOVE 0 TO WS-NOP.
       NORMALIZE.
      * TSO/TSC ONLY: TOLERATE LEADING BLANKS/NON-PRINTABLE BYTES TYPED
      * BEFORE THE COMMAND: START AT THE FIRST BYTE > BLANK (1-8).
           MOVE 1 TO WS-OFF.
           PERFORM FIND-START UNTIL WS-OFF > 8
               OR RAW-CHAR (WS-OFF) > SPACE.
           IF WS-OFF > 1 AND WS-OFF < 9
               PERFORM SHIFT-LEFT THRU SHIFT-LEFT-EXIT.
       NORMALIZE-EXIT.
           EXIT.
       FIND-START.
           ADD 1 TO WS-OFF.
       SHIFT-LEFT.
           MOVE SPACES TO NORM-REC.
           COMPUTE WS-LIM = 81 - WS-OFF.
           PERFORM COPY-CHAR VARYING WS-I FROM 1 BY 1
               UNTIL WS-I > WS-LIM.
           MOVE NORM-REC TO WS-CARD.
       SHIFT-LEFT-EXIT.
           EXIT.
       COPY-CHAR.
           COMPUTE WS-J = WS-I + WS-OFF - 1.
           MOVE RAW-CHAR (WS-J) TO NR-CHAR (WS-I).
       CLASSIFY.
           MOVE CMD-CHAR TO REQ-CHAR.
           MOVE 'INV' TO REQ-KIND.
           IF CMD-CHAR = 'U' OR CMD-CHAR = 'u'
               MOVE 'MOV' TO REQ-KIND
               MOVE 'U' TO REQ-DIR
           ELSE IF CMD-CHAR = 'D' OR CMD-CHAR = 'd'
               MOVE 'MOV' TO REQ-KIND
               MOVE 'D' TO REQ-DIR
           ELSE IF CMD-CHAR = 'L' OR CMD-CHAR = 'l'
               MOVE 'MOV' TO REQ-KIND
               MOVE 'L' TO REQ-DIR
           ELSE IF CMD-CHAR = 'R' OR CMD-CHAR = 'r'
               MOVE 'MOV' TO REQ-KIND
               MOVE 'R' TO REQ-DIR
           ELSE IF CMD-CHAR = 'Q' OR CMD-CHAR = 'q'
               MOVE 'QUI' TO REQ-KIND
           ELSE IF CMD-CHAR = 'A'
               MOVE 'CFG' TO REQ-KIND
               PERFORM SET-CONFIG THRU SET-CONFIG-EXIT.
       CLASSIFY-EXIT.
           EXIT.
       SET-CONFIG.
           IF CMD-LEVEL = '0'
               MOVE 0 TO REQ-LEVEL
           ELSE IF CMD-LEVEL = '2'
               MOVE 2 TO REQ-LEVEL
           ELSE IF CMD-LEVEL = '3'
               MOVE 3 TO REQ-LEVEL
           ELSE
               MOVE 1 TO REQ-LEVEL.
           IF CMD-COUNT = '2'
               MOVE 2 TO REQ-COUNT
           ELSE IF CMD-COUNT = '3'
               MOVE 3 TO REQ-COUNT
           ELSE
               MOVE 1 TO REQ-COUNT.
       SET-CONFIG-EXIT.
           EXIT.
ZZ
//COB5     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ5,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.R20.COBOL(PACINPT),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.R20.COPY,DISP=SHR
//SRC6     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COBOL(PACDISP),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
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
      * MVS-S1: BEFORE EVERY SCREEN SENT, SET-BELL READS THE STATE
      * (NEVER CHANGES IT): REQ-BELL Y ON THE FIRST SCREEN (START),
      * WHEN LIVES FELL SINCE THE LAST SCREEN (DEATH, THE LAST ONE TOO)
      * AND ON THE FIRST SCREEN AFTER THE WIN; PACPLAT RINGS ONLY WITH
      * SOUND Y.
      * WITHOUT AN END SCREEN (NOT SCALED) A PENDING ALARM GOES ON A
      * RESTORE-ONLY WRITE (C2 28 00 00) BEFORE LINE MODE RETURNS.
      * MVS-GP1 (D36, ARC-ON = 1): 'RULES ARCADE' AFTER THE BANNER, ONE
      * ARCADE LINE (7-DIGIT SCORE, FRIGHT, CHAIN, EVENT, GHOST MODES)
      * AFTER EACH STATUS / RT GHOSTS LINE, GHOSTS F (FRIGHTENED) AND E
      * (EYES) ON THE BOARD, END 'SCORE NNNNNNN' + 'GHOSTS EATEN NNN'.
      * MVS-GP2 (D37, ARC-ON = 1): 'LEVEL NNN' AFTER 'RULES ARCADE', A
      * LEVEL LINE AFTER THE ARCADE LINE, FRUIT % ON THE BOARD (UNDER
      * PAC-MAN AND THE GHOSTS), END 'TURNS NNNNNNN', 'GHOSTS EATEN
      * NNNN', 'FRUITS EATEN NNN', 'LEVEL NNN'. ALARM (S1) IN ARCADE
      * FROM THE GAME COUNTERS, NEVER FROM A DROP IN LIVES: A DEATH
      * (ARC-NDIE ROSE), THE EXTRA LIFE (ARC-XL 0 -> 1), A LEVEL CLEAR
      * (ARC-LEVEL ROSE), PLUS START AND THE FINAL WIN AS IN S1. ONE
      * ALARM PER SCREEN: EVENTS OF ONE SCREEN ARE COALESCED.
      * MVS-HS (D38, ARC-ON = 1, REQ-HSST NOT N): AFTER 'LEVEL NNN' THE
      * END LINE 'HIGH SCORE NNNNNNN LEVEL NNN' = MAX(PERSISTENT, THIS
      * GAME), THEN 'NEW HIGH SCORE' / 'HIGH SCORE NOT SAVED' / 'START
      * LEVEL NN: HIGH SCORE NOT RECORDED'; OR 'HIGH SCORE UNAVAILABLE'.
      * MVS-RP (D39): AN ARCADE REALTIME GAME LOST ON SCREEN PLAYS
      * THE 6 DEATH FRAMES (PACSCR RTQF, REQ-RTSTAT FRZ, REQ-RTFRZ
      * 10..5; TSC: ONE PERIOD APART BY PACPLAT CLOK / WDLN) BEFORE
      * THE END SCREEN.
      * MVS-S2 (D41, DOCS/S2-PATTERNS.MD): WITH REQ-ALARM P AND SOUND Y
      * EVERY SCREEN GOES THROUGH BELL-SET: PAT-CLASS NAMES THE HIGHEST
      * EVENT OF THE SCREEN (START 1, EXTRA LIFE 2, DEATH 3, LEVEL
      * CLEAR 4, WIN 5, GAME OVER 6) FROM THE SAME COUNTERS AS SET-BELL,
      * PAT-PLAY RINGS ITS PATTERN (1 2 2 3 4 3 BELLS, PT-G QUANTA
      * APART: 2 AT 150 MS, 3 AT 125 MS) ON THE REALTIME QUANTUM
      * WRITES ONLY (PT-QW); A HIGHER OR EQUAL EVENT REPLACES IT, TURN
      * PLAY RINGS THE FIRST BELL ONLY. AT THE END ONLY A WIN / GAME
      * OVER PATTERN GOES ON, AS BELL-ONLY WRITES INSIDE THE 3-S END
      * PAUSE (END-PAUSE). REQ-ALARM S = THE S1 / GP2 PATH UNCHANGED.
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
       01  SB-SENT               PIC 9 VALUE 0.
       01  SB-LIVES              PIC 9 VALUE 0.
       01  SB-WON                PIC 9 VALUE 0.
       01  SB-NDIE               PIC 99 VALUE 0.
       01  SB-XL                 PIC 9 VALUE 0.
       01  SB-LVL                PIC 999 VALUE 0.
       01  FD-K                  PIC 99 VALUE 0.
       01  PT-ON                 PIC 9 VALUE 0.
       01  PT-PRI                PIC 9 VALUE 0.
       01  PT-EV                 PIC 9 VALUE 0.
       01  PT-D                  PIC 9 VALUE 0.
       01  PT-LEFT               PIC 9 VALUE 0.
       01  PT-NEXT               PIC 9 VALUE 0.
       01  PT-G                  PIC 9 VALUE 2.
       01  PT-QW                 PIC 9 VALUE 0.
       01  PT-T0                 PIC S9(9) COMP VALUE +0.
       01  PT-TAB                PIC X(6) VALUE '122343'.
       01  PT-TABR REDEFINES PT-TAB.
           05  PT-NB             PIC 9 OCCURS 6 TIMES.
       01  FD-SAVE               PIC X(4).
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
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
       01  WS-ARC-LINE.
           05  FILLER            PIC X(4) VALUE 'A S='.
           05  AL-S              PIC 9(7).
           05  FILLER            PIC X(4) VALUE ' PW='.
           05  AL-PW             PIC 9.
           05  FILLER            PIC X(4) VALUE ' FR='.
           05  AL-FR             PIC 999.
           05  FILLER            PIC X(4) VALUE ' FT='.
           05  AL-FT             PIC 999.
           05  FILLER            PIC X(4) VALUE ' FA='.
           05  AL-FA             PIC 9.
           05  FILLER            PIC X(4) VALUE ' CH='.
           05  AL-CH             PIC 9.
           05  FILLER            PIC X(4) VALUE ' EV='.
           05  AL-EV             PIC X(4).
           05  FILLER            PIC X(3) VALUE ' P='.
           05  AL-P              PIC 9(4).
           05  FILLER            PIC X(3) VALUE ' N='.
           05  AL-N              PIC 999.
           05  FILLER            PIC X(3) VALUE ' M='.
           05  AL-M1             PIC X.
           05  AL-W1             PIC 999.
       01  WS-ARC-G2.
           05  FILLER            PIC X VALUE ' '.
           05  AL-M2             PIC X.
           05  AL-W2             PIC 999.
       01  WS-ARC-G3.
           05  FILLER            PIC X VALUE ' '.
           05  AL-M3             PIC X.
           05  AL-W3             PIC 999.
      * MVS-GP2 (D37) LEVEL LINE, AFTER THE ARCADE LINE.
       01  WS-LVL-LINE.
           05  FILLER            PIC X(5) VALUE 'L LV='.
           05  LL-LV             PIC 999.
           05  FILLER            PIC X(4) VALUE ' AI='.
           05  LL-AI             PIC 9.
           05  FILLER            PIC X(4) VALUE ' IT='.
           05  LL-IT             PIC 999.
           05  FILLER            PIC X(4) VALUE ' BN='.
           05  LL-BN             PIC 9.
           05  FILLER            PIC X(4) VALUE ' BT='.
           05  LL-BT             PIC 999.
           05  FILLER            PIC X(4) VALUE ' BK='.
           05  LL-BK             PIC X.
           05  FILLER            PIC X(4) VALUE ' BV='.
           05  LL-BV             PIC 9(4).
           05  FILLER            PIC X(4) VALUE ' XL='.
           05  LL-XL             PIC 9.
           05  FILLER            PIC X(4) VALUE ' EV='.
           05  LL-EV             PIC X(5).
       01  WS-QUANTA.
           05  FILLER            PIC X(7) VALUE 'QUANTA '.
           05  QU-N              PIC 9(7).
       01  HS-LINE.
           05  FILLER            PIC X(11) VALUE 'HIGH SCORE '.
           05  HL-S              PIC 9(7).
           05  FILLER            PIC X(7) VALUE ' LEVEL '.
           05  HL-L              PIC 999.
       01  HS-PLINE.
           05  FILLER            PIC X(12) VALUE 'START LEVEL '.
           05  HP-L              PIC 99.
           05  FILLER            PIC X(25)
                   VALUE ': HIGH SCORE NOT RECORDED'.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       01  PAC-ARC COPY PACARC.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ PAC-ARC.
       MAIN-PARA.
           IF REQ-MODE = 'TSC' OR REQ-MODE = 'TSD'
               PERFORM SCREEN-OP THRU SCREEN-OP-EXIT
           ELSE IF REQ-OP = 'HEAD'
               DISPLAY 'PACMAN MVS-6 SMART GHOSTS'
               ADD 1 TO M-LINES
               ADD 25 TO M-CHARS
               PERFORM ARC-HEAD THRU ARC-HEAD-EXIT
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
                   PAC-ARC
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
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC.
           ADD DS-LEN TO M-CHARS.
           PERFORM BELL-SET.
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
      * MVS-S2: GAME OVER - ONLY A WIN / GAME OVER PATTERN GOES ON.
           IF PT-PRI < 5
               MOVE 0 TO PT-ON.
           IF ARC-ON = 1 AND F-LOST = 1 AND REQ-PLAY = 'R'
               PERFORM FINAL-DEATH.
           MOVE 0 TO DS-LEN.
           IF REQ-SCALE NOT = 'N'
               MOVE 'ENDS' TO REQ-OP
               CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC
               PERFORM SCR-ENDS-SEND.
           IF DS-LEN = 0
               PERFORM SCR-END-BELL.
           MOVE 'END ' TO REQ-OP.
       SCR-ENDS-SEND.
           IF DS-LEN > 0
               ADD DS-LEN TO M-CHARS
               PERFORM BELL-SET
               MOVE 'SEND' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ PAC-DS
               PERFORM END-PAUSE THRU END-PAUSE-EXIT.
           MOVE 0 TO WS-NOP.
       END-PAUSE.
      * MVS-S2 (D41 5): NO PATTERN LEFT = THE 3-S WAIT AS BEFORE. ELSE
      * EACH STEP LEFT IS A BELL-ONLY WRITE PT-G PERIODS AFTER THE LAST
      * (WDLN FROM THE END SCREEN'S CLOCK T0), THEN WAIT UNTIL T0 + 3 S
      * (DLWT): THE PAUSE IS NEVER LONGER. TSD: THE WRITES, NO WAITS.
           IF PT-ON = 0
               MOVE 'WAIT' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ
               GO TO END-PAUSE-EXIT.
           IF REQ-MODE = 'TSC'
               MOVE 'CLOK' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ
               MOVE REQ-TIME TO PT-T0.
           PERFORM END-STEP THRU END-STEP-EXIT
               UNTIL PT-ON = 0.
           IF REQ-MODE = 'TSC'
               COMPUTE REQ-TIME = PT-T0 + 3000
               MOVE 'DLWT' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
       END-PAUSE-EXIT.
           EXIT.
       END-STEP.
           IF REQ-MODE = 'TSC'
               PERFORM END-WDLN PT-G TIMES.
           MOVE 'Y' TO REQ-BELL.
           PERFORM BELL-WRITE.
           SUBTRACT 1 FROM PT-LEFT.
           IF PT-LEFT = 0
               MOVE 0 TO PT-ON.
       END-STEP-EXIT.
           EXIT.
       END-WDLN.
           MOVE 'WDLN' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
       SCR-END-BELL.
           PERFORM SET-BELL.
           IF REQ-BELL = 'Y' AND REQ-SOUND = 'Y'
               PERFORM BELL-WRITE.
           MOVE 'N' TO REQ-BELL.
       BELL-WRITE.
      * THE RESTORE-ONLY WRITE C2 28 00 00 (PACPLAT ADDS THE ALARM BIT).
           MOVE 194 TO HEXN.
           MOVE HX-B TO DS-BYTE (1).
           MOVE 40 TO HEXN.
           MOVE HX-B TO DS-BYTE (2).
           MOVE LOW-VALUE TO DS-BYTE (3).
           MOVE LOW-VALUE TO DS-BYTE (4).
           MOVE 4 TO DS-LEN.
           MOVE 'P' TO DS-KIND.
           ADD DS-LEN TO M-CHARS.
           MOVE 'SEND' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ PAC-DS.
       FINAL-DEATH.
      * MVS-RP: THE LAST LIFE LOST (NO FREEZE IN THE GAME): THE DEATH
      * FRAMES AS QUANTUM FRAMES, THE STATE UNCHANGED.
           MOVE REQ-RTSTAT TO FD-SAVE.
           MOVE 'FRZ ' TO REQ-RTSTAT.
           MOVE SPACE TO REQ-RTFR.
           IF REQ-MODE = 'TSC'
               MOVE 'CLOK' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           PERFORM FD-FRAME VARYING FD-K FROM REQ-RTFRT BY -1
               UNTIL FD-K NOT > REQ-RTRDY.
           MOVE FD-SAVE TO REQ-RTSTAT.
           MOVE 0 TO REQ-RTFRZ.
       FD-FRAME.
           IF REQ-MODE = 'TSC'
               MOVE 'WDLN' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           MOVE FD-K TO REQ-RTFRZ.
           MOVE 'RTQF' TO REQ-OP.
           PERFORM SCR-RTQF THRU SCR-RTQF-EXIT.
       BELL-SET.
      * MVS-S2 (D41): SET-BELL (S1 / GP2) BETWEEN THE PATTERN STEPS,
      * WHICH RUN ONLY WITH ALARM(PATTERN) AND SOUND Y.
           IF REQ-ALARM = 'P' AND REQ-SOUND = 'Y'
               PERFORM PAT-CLASS THRU PAT-CLASS-EXIT.
           PERFORM SET-BELL.
           IF REQ-ALARM = 'P' AND REQ-SOUND = 'Y'
               PERFORM PAT-PLAY THRU PAT-PLAY-EXIT.
           MOVE 0 TO PT-QW.
       PAT-CLASS.
      * THE HIGHEST EVENT OF THIS SCREEN (0 NONE), READ BEFORE SET-BELL
      * UPDATES ITS SB- COPIES. GAME OVER = A DEATH THAT ENDS THE GAME.
           MOVE 0 TO PT-EV.
           MOVE 0 TO PT-D.
           IF SB-SENT = 0
               MOVE 1 TO PT-EV
               GO TO PAT-CLASS-EXIT.
           IF ARC-ON = 1 AND ARC-XL > SB-XL
               MOVE 2 TO PT-EV.
           IF ARC-ON = 0 AND LIVES < SB-LIVES
               MOVE 1 TO PT-D.
           IF ARC-ON = 1 AND ARC-NDIE > SB-NDIE
               MOVE 1 TO PT-D.
           IF PT-D = 1
               MOVE 3 TO PT-EV.
           IF ARC-ON = 1 AND ARC-LEVEL > SB-LVL
               MOVE 4 TO PT-EV.
           IF F-WON = 1 AND SB-WON = 0
               MOVE 5 TO PT-EV.
           IF PT-D = 1 AND F-LOST = 1
               MOVE 6 TO PT-EV.
       PAT-CLASS-EXIT.
           EXIT.
       PAT-PLAY.
      * AN EVENT AT OR ABOVE THE RUNNING PATTERN STARTS ITS OWN (FIRST
      * BELL ON THIS SCREEN); ELSE A QUANTUM WRITE MAY CARRY A STEP.
           IF PT-EV = 0
               GO TO PAT-STEP.
           IF PT-ON = 1 AND PT-EV < PT-PRI
               GO TO PAT-STEP.
           MOVE 2 TO PT-G.
           IF REQ-RTPER < 150
               MOVE 3 TO PT-G.
           MOVE 'Y' TO REQ-BELL.
           MOVE PT-EV TO PT-PRI.
           MOVE PT-NB (PT-EV) TO PT-LEFT.
           SUBTRACT 1 FROM PT-LEFT.
           MOVE PT-G TO PT-NEXT.
           MOVE 1 TO PT-ON.
           IF PT-LEFT = 0
               MOVE 0 TO PT-ON.
           IF REQ-PLAY = 'T' AND PT-EV < 5
               MOVE 0 TO PT-ON.
           GO TO PAT-PLAY-EXIT.
       PAT-STEP.
           MOVE 'N' TO REQ-BELL.
           IF PT-ON = 0 OR PT-QW = 0
               GO TO PAT-PLAY-EXIT.
           SUBTRACT 1 FROM PT-NEXT.
           IF PT-NEXT > 0
               GO TO PAT-PLAY-EXIT.
           MOVE 'Y' TO REQ-BELL.
           MOVE PT-G TO PT-NEXT.
           SUBTRACT 1 FROM PT-LEFT.
           IF PT-LEFT = 0
               MOVE 0 TO PT-ON.
       PAT-PLAY-EXIT.
           EXIT.
       SET-BELL.
           MOVE 'N' TO REQ-BELL.
           IF SB-SENT = 0
               MOVE 'Y' TO REQ-BELL.
           IF SB-SENT = 1 AND LIVES < SB-LIVES AND ARC-ON = 0
               MOVE 'Y' TO REQ-BELL.
           IF F-WON = 1 AND SB-WON = 0
               MOVE 'Y' TO REQ-BELL
               MOVE 1 TO SB-WON.
           IF ARC-ON = 1
               PERFORM ARC-BELL.
           MOVE 1 TO SB-SENT.
           MOVE LIVES TO SB-LIVES.
       SCR-TICK.
      * MVS-G3: VISUAL TICK (GLYPH FRAME ONLY). NO CHANGE = NO SEND.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC.
           IF DS-LEN > 0
               ADD DS-LEN TO M-CHARS
               PERFORM BELL-SET
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
      * MVS-S2: EITHER WAY IT IS THE QUANTUM'S ONE WRITE (PT-QW 1).
           MOVE 1 TO PT-QW.
           IF REQ-RTFR = 'P' OR REQ-RTFR = 'F'
               MOVE 'MOV' TO REQ-KIND
               IF REQ-RTFR = 'F'
                   MOVE 'RDR' TO REQ-KIND.
           IF REQ-RTFR = 'P' OR REQ-RTFR = 'F'
               MOVE 'PRMT' TO REQ-OP
               PERFORM SCR-PRMT THRU SCR-PRMT-EXIT
               MOVE 'RTQF' TO REQ-OP
               GO TO SCR-RTQF-EXIT.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC.
           ADD DS-LEN TO M-CHARS.
           PERFORM BELL-SET.
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
           IF ARC-ON = 1
               PERFORM SHOW-ARC.
           MOVE 0 TO WS-NOP.
       SCR-RESEND.
      * THE PARTIAL SEND FAILED (PACPLAT SWITCHED TO FULL REDRAW, NO
      * ANIMATION): SEND THE WHOLE SCREEN INSTEAD.
           MOVE 'FULL' TO REQ-OP.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC.
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
           IF ARC-ON = 1
               DISPLAY 'TURNS ' ARC-TURNS
               ADD 4 TO M-CHARS
           ELSE
               DISPLAY 'TURNS ' TICK-COUNT.
           IF ARC-ON = 1
               DISPLAY 'SCORE ' ARC-SCORE
               ADD 3 TO M-CHARS
           ELSE
               DISPLAY 'SCORE ' SCORE.
           DISPLAY 'LIVES ' LIVES.
           IF REQ-PLAY = 'R'
               MOVE REQ-RTQ TO QU-N
               DISPLAY WS-QUANTA.
           IF ARC-ON = 1
               DISPLAY 'GHOSTS EATEN ' ARC-EATN4
               DISPLAY 'FRUITS EATEN ' ARC-FRUITS
               DISPLAY 'LEVEL ' ARC-LEVEL
               ADD 3 TO M-LINES
               ADD 42 TO M-CHARS.
           IF ARC-ON = 1 AND REQ-HSST NOT = 'N'
               PERFORM SHOW-HS THRU SHOW-HS-EXIT.
           ADD 4 TO M-LINES.
           ADD 26 TO M-CHARS.
           IF REQ-METRIC = 'M'
               PERFORM SHOW-METRICS.
       SHOW-END-EXIT.
           EXIT.
       SHOW-HS.
           IF REQ-HSST = 'E'
               DISPLAY 'HIGH SCORE UNAVAILABLE'
               ADD 1 TO M-LINES
               ADD 22 TO M-CHARS
               GO TO SHOW-HS-EXIT.
           MOVE REQ-HISCORE TO HL-S.
           MOVE REQ-HSLVL TO HL-L.
           IF REQ-HSSCORE > REQ-HISCORE
               MOVE REQ-HSSCORE TO HL-S
               MOVE REQ-HSGLVL TO HL-L.
           DISPLAY HS-LINE.
           ADD 1 TO M-LINES.
           ADD 28 TO M-CHARS.
           IF REQ-HSNEW = 'Y'
               DISPLAY 'NEW HIGH SCORE'
               ADD 1 TO M-LINES
               ADD 14 TO M-CHARS.
           IF REQ-HSNEW = 'F'
               DISPLAY 'HIGH SCORE NOT SAVED'
               ADD 1 TO M-LINES
               ADD 20 TO M-CHARS.
           IF REQ-HSNEW = 'P'
               MOVE REQ-START TO HP-L
               DISPLAY HS-PLINE
               ADD 1 TO M-LINES
               ADD 39 TO M-CHARS.
       SHOW-HS-EXIT.
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
           IF ARC-ON = 1
               PERFORM SHOW-ARC.
           IF GHOST-COUNT > 1
               PERFORM SHOW-EXTRA THRU SHOW-EXTRA-EXIT.
           PERFORM SHOW-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
       SHOW-STATE-EXIT.
           EXIT.
       SHOW-ROW.
           MOVE MAP-ROW (WS-ROW) TO WS-LINE.
           IF ARC-ON = 1 AND ARC-BT > 0 AND WS-ROW = ARC-BY
               MOVE '%' TO WS-LINE-CELL (ARC-BX).
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
               MOVE 'G' TO WS-LINE-CELL (WS-GX)
               IF ARC-ON = 1 AND ARC-GM (WS-G) NOT = 'N'
                   MOVE ARC-GM (WS-G) TO WS-LINE-CELL (WS-GX).
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
      * ------------- MVS-GP1 ARCADE TEXT (D36, ARC-ON = 1) ----------
       ARC-HEAD.
           IF ARC-ON = 0
               GO TO ARC-HEAD-EXIT.
           DISPLAY 'RULES ARCADE'.
           DISPLAY 'LEVEL ' ARC-LEVEL.
           ADD 2 TO M-LINES.
           ADD 21 TO M-CHARS.
       ARC-HEAD-EXIT.
           EXIT.
       SHOW-ARC.
           MOVE ARC-SCORE TO AL-S.
           MOVE ARC-POWER TO AL-PW.
           MOVE ARC-FR TO AL-FR.
           MOVE ARC-FTURN TO AL-FT.
           MOVE ARC-FACC TO AL-FA.
           MOVE ARC-CHAIN TO AL-CH.
           MOVE ARC-EVT TO AL-EV.
           MOVE ARC-PTS TO AL-P.
           MOVE ARC-EATEN TO AL-N.
           MOVE ARC-GM (1) TO AL-M1.
           MOVE ARC-GW (1) TO AL-W1.
           MOVE ARC-GM (2) TO AL-M2.
           MOVE ARC-GW (2) TO AL-W2.
           MOVE ARC-GM (3) TO AL-M3.
           MOVE ARC-GW (3) TO AL-W3.
           IF GHOST-COUNT = 1
               DISPLAY WS-ARC-LINE
           ELSE IF GHOST-COUNT = 2
               DISPLAY WS-ARC-LINE WS-ARC-G2
           ELSE
               DISPLAY WS-ARC-LINE WS-ARC-G2 WS-ARC-G3.
           ADD 1 TO M-LINES.
           ADD 80 TO M-CHARS.
           PERFORM SHOW-LVL.
       SHOW-LVL.
           MOVE ARC-LEVEL TO LL-LV.
           MOVE AI-LEVEL TO LL-AI.
           MOVE ARC-ITEMS TO LL-IT.
           MOVE ARC-BN TO LL-BN.
           MOVE ARC-BT TO LL-BT.
           MOVE ARC-BK TO LL-BK.
           MOVE ARC-BV TO LL-BV.
           MOVE ARC-XL TO LL-XL.
           MOVE ARC-EVF TO LL-EV.
           DISPLAY WS-LVL-LINE.
           ADD 1 TO M-LINES.
           ADD 63 TO M-CHARS.
       ARC-BELL.
      * MVS-GP2 (D37): ONLY REQ-BELL AND THE SB- COPIES CHANGE HERE.
           IF SB-SENT = 1 AND ARC-NDIE > SB-NDIE
               MOVE 'Y' TO REQ-BELL.
           IF SB-SENT = 1 AND ARC-XL > SB-XL
               MOVE 'Y' TO REQ-BELL.
           IF SB-SENT = 1 AND ARC-LEVEL > SB-LVL
               MOVE 'Y' TO REQ-BELL.
           MOVE ARC-NDIE TO SB-NDIE.
           MOVE ARC-XL TO SB-XL.
           MOVE ARC-LEVEL TO SB-LVL.
ZZ
//COB6     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ6,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.R20.COBOL(PACDISP),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.R20.COPY,DISP=SHR
//SRC7     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COBOL(PACPLAT),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACPLAT : PLATFORM ADAPTER (MVS 3.8J). OPS : INIT FINI CLS
      * SEND RECV FSOF.  INIT validates REQ-MODE (BAT, TSO, TSD) and,
      * for TSO with REQ-COLOR A(UTO)/Y(ES), tries the TSC colour mode:
      * full-screen on (PACFSIO FSON); AUTO also needs QCode X'86' in
      * the Query Reply. Any failure leaves TSO line mode (monochrome
      * fallback). SEND/RECV move one TSC screen / one inbound; in TSD
      * (batch dry run) SEND prints the data stream in hex. An error in
      * TSC restores line mode and falls back to TSO. FSOF and FINI
      * always restore line mode if full-screen is active (PACFSIO
      * also restores it from an ESTAE exit on abend). CLS (TSO only)
      * starts a fresh line-mode screen via PACTSO. GAME/MAP/AI never
      * see any of this. MVS-G2: REQ-HILITE A/Y/N IN, Y/N OUT
      * (HIGHLIGHT = QCODE X'87' IN THE QUERY REPLY). MVS-G4: THE
      * REPLY IS PARSED BY PACQRY (PURE); REQ-GLYPHS A/G/B/C IN, G/B/C
      * OUT (AUTO = G ONLY WITH GE + CP310 IN THE REPLY). MVS-GS:
      * REQ-SCALE A/4/3/T IN, 4/3/T/N OUT: SCALING NEEDS TSC/TSD,
      * HIGHLIGHT Y AND GLYPHS G (FROM THE SAME QUERY, NO NEW ONE); AUTO
      * = 4. OP WAIT (TSC ONLY): PACTSO PAUSE BEFORE THE END LINES.
      * MVS-GS GEOMETRY (D32): RIGHT AFTER FSON AND BEFORE THE QUERY ONE
      * SIZE SWITCH (PACFSIO SENX): X'7E'+WCC (ERASE/WRITE ALTERNATE)
      * WITH COLOR A AND CANVAS A, ELSE X'F5'+WCC (ERASE/WRITE, 80X24).
      * THE ALTERNATE SIZE COMES FROM THE SAME REPLY (PACQRY) INTO
      * REQ-CW/REQ-CH. THE FIRST FULL SCREEN STAYS A SEND (FULLSCR, NOT
      * HELD AFTER THE QUERY, D28); LATER FULL SCREENS GO BY SENX WITH
      * THE SAME COMMAND (SIZE RE-ESTABLISHED AFTER CLEAR / PA2).
      * TSD: CANVAS W X T M U L SIMULATE A BUFFER; TSX LINES SHOW THE
      * TRANSPORT DECISIONS.
      * MVS-RT (D33): POLL = ONE NON-BLOCKING READ (PACFSIO POLL; NONE =
      * REQ-INKEY N); RECV/POLL KEEP THE AID BYTE IN REQ-AID; REALTIME
      * NEVER USES THE RECT IDLE POLLING (BLOCKING RECV BEFORE THE START
      * AND IN PAUSE). CLOK = MILLISECONDS IN REQ-TIME (PACTSO TIME);
      * WDLN = REQ-TIME + RT-PERIOD (WHOLE PERIODS ALREADY MISSED ARE
      * SKIPPED), THEN WAIT UNTIL IT (PACTSO DLWT). MVS-RP RP.3: THE
      * PERIOD IS REQ-RTPER (PACMAIN: 150 NORMAL, 125 FAST).
      * MVS-S2 (D41): DLWT (TSC ONLY) = WAIT UNTIL THE ABSOLUTE DEADLINE
      * REQ-TIME (PACTSO DLWT, NO WAIT IF IT HAS PASSED): THE END OF
      * THE 3-S END PAUSE WHEN BELLS RING INSIDE IT.
      * MVS-S1: REQ-SOUND A/Y IN, Y/N OUT: Y ONLY IN TSC/TSD (THE ALARM
      * IS BASE 3270: NOTHING TO DETECT, A = Y). SEND WITH REQ-BELL Y
      * AND SOUND Y SETS THE ALARM BIT X'04' IN THE WCC (DS-BYTE 1):
      * C3 -> C7, C2 -> C6, ON THE STREAM ALREADY BEING SENT (E15).
      * MVS-RP D40 (DOCS/RP-POLISH.MD 11): THE QUERY READ ACCEPTS ONLY A
      * VALID QUERY REPLY (PACQRY QS-ACT A). AN ENTER / AID / TYPED OR
      * BROKEN RECORD IS READ PAST (PACFSIO RECT: NOWAIT, 0.5 S WHEN
      * NONE) AT MOST 8 RECORDS / 6 EMPTY READS; NO VALID REPLY = THE
      * LINE-MODE FALLBACK, AFTER A DRAIN (AT MOST 8 RECORDS) SO NO
      * STARTUP INPUT REACHES THE GAME. A VALID FIRST RECORD: NO EXTRA
      * READ AT ALL (THE START IS UNCHANGED).
      * MVS-HS (D38): HSRD / HSWR = THE ARCADE HIGH SCORE IN THE PDS
      * MEMBER ON DD PACHS (PACHSIO; GAME NEVER SEES IT). HSRD SETS
      * REQ-HSST N (NO DD), R (VALID RECORD), Z (MISSING / EMPTY /
      * MALFORMED = 0), E (DD UNUSABLE OR I/O ERROR). HSWR WRITES ONLY
      * WHEN THE GAME SCORE IS STRICTLY GREATER AND THE GAME STARTED AT
      * LEVEL 1: R = UPDATE IN PLACE (WRIT), Z = ONE NEW RECORD (REPL,
      * HEALS THE MEMBER). REQ-HSNEW Y SAVED, F WRITE FAILED, P BEATEN
      * BY A LATER-LEVEL START (NOT RECORDED), N NOTHING.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACPLAT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  TSO-OP                PIC X(4) VALUE 'CLS '.
       01  TSO-WAIT              PIC X(4) VALUE 'WAIT'.
       01  TSO-RC                PIC S9(4) COMP.
       01  TSO-TIME              PIC X(4) VALUE 'TIME'.
       01  TSO-DLWT              PIC X(4) VALUE 'DLWT'.
       01  RT-PERIOD             PIC S9(9) COMP VALUE +150.
       01  RT-LIM                PIC S9(9) COMP.
       01  RT-NOW                PIC S9(9) COMP.
       01  RT-NEXT               PIC S9(9) COMP.
       01  FS-OP                 PIC X(4).
       01  FS-LEN                PIC S9(4) COMP.
       01  FS-RC                 PIC S9(4) COMP.
       01  FS-ACTIVE             PIC 9 VALUE 0.
       01  IN-AREA.
           05  IN-CH             PIC X OCCURS 2048 TIMES.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  HEX-LINE.
           05  FILLER            PIC X(4) VALUE 'TSD '.
           05  HL-CH             PIC X OCCURS 64 TIMES.
       01  LEN-LINE.
           05  FILLER            PIC X(13) VALUE 'TSD FRAME LEN'.
           05  LL-LEN            PIC 9(4).
       01  WS-K                  PIC 9(4).
       01  WS-V                  PIC 9(4).
       01  WS-O                  PIC 99.
       01  WS-Q                  PIC 99.
       01  WS-R                  PIC 99.
       01  WS-I                  PIC 99.
       01  WS-STOP               PIC 9.
       01  HAS-COLOUR            PIC 9.
       01  HAS-HILITE            PIC 9.
       01  HAS-GE                PIC 9 VALUE 0.
       01  QRY-OUT.
           05  QO-COLOUR         PIC 9.
           05  QO-HILITE         PIC 9.
           05  QO-GE             PIC 9.
           05  QO-AW             PIC 999.
           05  QO-AH             PIC 999.
           05  QO-VALID          PIC 9.
           05  QS-ACT            PIC X.
           05  QS-NREC           PIC 99.
           05  QS-NWAIT          PIC 99.
       01  QD-N                  PIC 99 VALUE 0.
       01  QD-MORE               PIC 9 VALUE 0.
       01  WS-NOP                PIC 9 VALUE 0.
       01  WS-IDLE               PIC 9(4) VALUE 0.
       01  CV-CMD                PIC 9(4) VALUE 245.
       01  FULL-SENT             PIC 9 VALUE 0.
       01  SX-AREA.
           05  SX-CMD            PIC X.
           05  SX-DATA           PIC X(2048).
       01  SX-LEN                PIC S9(4) COMP.
       01  TSX-SW.
           05  FILLER            PIC X(11) VALUE 'TSX SWITCH '.
           05  TS-CMD            PIC XX.
           05  FILLER            PIC X VALUE ' '.
           05  TS-W              PIC 999.
           05  FILLER            PIC X VALUE 'X'.
           05  TS-H              PIC 999.
       01  TSX-FULL.
           05  FILLER            PIC X(9) VALUE 'TSX FULL '.
           05  TF-CMD            PIC X(5).
       01  HS-OP                 PIC X(4).
       01  HS-RC                 PIC S9(4) COMP.
       01  HS-DDN                PIC X(8) VALUE 'PACHS'.
       01  HS-REC.
           05  HR-SCORE          PIC X(7).
           05  HR-B1             PIC X.
           05  HR-TAG            PIC X(8).
           05  HR-B2             PIC X.
           05  HR-LVL            PIC X(3).
           05  FILLER            PIC X(60).
       01  HS-NUM REDEFINES HS-REC.
           05  HN-SCORE          PIC 9(7).
           05  FILLER            PIC X(10).
           05  HN-LVL            PIC 999.
           05  FILLER            PIC X(60).
       LINKAGE SECTION.
       01  PAC-REQ COPY PACREQ.
       01  PAC-DS COPY PACDS.
       PROCEDURE DIVISION USING PAC-REQ PAC-DS.
       MAIN-PARA.
           IF REQ-OP = 'INIT'
               PERFORM DO-INIT THRU DO-INIT-EXIT
           ELSE IF REQ-OP = 'FINI'
               PERFORM DO-FSOF THRU DO-FSOF-EXIT
               MOVE 0 TO RETURN-CODE
           ELSE IF REQ-OP = 'CLS ' AND REQ-MODE = 'TSO'
               CALL 'PACTSO' USING TSO-OP TSO-RC
           ELSE IF REQ-OP = 'SEND'
               PERFORM DO-SEND THRU DO-SEND-EXIT
           ELSE IF REQ-OP = 'RECV'
               PERFORM DO-RECV THRU DO-RECV-EXIT
           ELSE IF REQ-OP = 'FSOF'
               PERFORM DO-FSOF THRU DO-FSOF-EXIT
           ELSE IF REQ-OP = 'WAIT' AND REQ-MODE = 'TSC'
               CALL 'PACTSO' USING TSO-WAIT TSO-RC
           ELSE IF REQ-OP = 'POLL'
               PERFORM DO-POLL THRU DO-POLL-EXIT
           ELSE IF REQ-OP = 'CLOK'
               CALL 'PACTSO' USING TSO-TIME TSO-RC REQ-TIME
           ELSE IF REQ-OP = 'WDLN'
               PERFORM DO-WDLN
           ELSE IF REQ-OP = 'DLWT' AND REQ-MODE = 'TSC'
               CALL 'PACTSO' USING TSO-DLWT TSO-RC REQ-TIME
           ELSE IF REQ-OP = 'HSRD'
               PERFORM DO-HSRD THRU DO-HSRD-EXIT
           ELSE IF REQ-OP = 'HSWR'
               PERFORM DO-HSWR THRU DO-HSWR-EXIT.
           GOBACK.
       DO-INIT.
           IF REQ-MODE NOT = 'TSO' AND REQ-MODE NOT = 'TSD'
               MOVE 'BAT' TO REQ-MODE.
           MOVE 80 TO REQ-CW.
           MOVE 24 TO REQ-CH.
           IF REQ-MODE = 'TSD'
               PERFORM SIM-CANVAS.
           IF REQ-MODE = 'TSO'
                   AND (REQ-COLOR = 'A' OR REQ-COLOR = 'Y')
               PERFORM TRY-COLOUR THRU TRY-COLOUR-EXIT.
      * MVS-G2: HIGHLIGHT ONLY IN TSC (OR THE TSD DRY RUN) AND ONLY WHEN
      * ASKED: Y, OR A WITH QCODE X'87' IN THE QUERY REPLY (SET IN
      * TRY-COLOUR). ANYTHING ELSE IS N.
           IF REQ-MODE NOT = 'TSC' AND REQ-MODE NOT = 'TSD'
               MOVE 'N' TO REQ-HILITE.
           IF REQ-HILITE NOT = 'Y'
               MOVE 'N' TO REQ-HILITE.
      * MVS-G3: ANIM Y (A BECOMES Y IN TSC: PARTIAL SEND IS PROVEN,
      * SO THERE IS NOTHING TO DETECT), REDRAW P (PARTIAL) ONLY IN
      * TSC/TSD; EVERYTHING ELSE IS ANIM N / REDRAW F (FULL).
           IF REQ-ANIM = 'A' AND REQ-MODE = 'TSC'
               MOVE 'Y' TO REQ-ANIM.
           IF REQ-MODE NOT = 'TSC' AND REQ-MODE NOT = 'TSD'
               MOVE 'N' TO REQ-ANIM
               MOVE 'F' TO REQ-REDRAW.
           IF REQ-ANIM NOT = 'Y'
               MOVE 'N' TO REQ-ANIM.
           IF REQ-REDRAW NOT = 'P'
               MOVE 'F' TO REQ-REDRAW.
      * MVS-G4: GLYPH PROFILE G/B ONLY IN TSC/TSD; A BECOMES G ONLY WHEN
      * THE QUERY REPLY ANNOUNCED GE + CP310 (NO QUERY: COLOR YES = C).
           IF REQ-GLYPHS = 'A' AND REQ-MODE = 'TSC' AND HAS-GE = 1
               MOVE 'G' TO REQ-GLYPHS.
           IF REQ-MODE NOT = 'TSC' AND REQ-MODE NOT = 'TSD'
               MOVE 'C' TO REQ-GLYPHS.
           IF REQ-GLYPHS NOT = 'G' AND REQ-GLYPHS NOT = 'B'
               MOVE 'C' TO REQ-GLYPHS.
      * MVS-GS: SCALED ONLY WITH COLOUR (TSC/TSD), HIGHLIGHT (SPRITE
      * BODIES ARE REVERSE VIDEO) AND THE GRAPHIC GLYPHS (GE + CP310),
      * ALL AS ALREADY RESOLVED ABOVE; OTHERWISE THE G4 RENDERER.
           IF REQ-SCALE = 'A'
               MOVE '4' TO REQ-SCALE.
           IF REQ-SCALE NOT = '4' AND REQ-SCALE NOT = '3'
                             AND REQ-SCALE NOT = 'T'
               MOVE 'N' TO REQ-SCALE.
           IF REQ-MODE NOT = 'TSC' AND REQ-MODE NOT = 'TSD'
               MOVE 'N' TO REQ-SCALE.
           IF REQ-HILITE NOT = 'Y' OR REQ-GLYPHS NOT = 'G'
               MOVE 'N' TO REQ-SCALE.
           IF REQ-SOUND = 'A'
               MOVE 'Y' TO REQ-SOUND.
           IF REQ-MODE NOT = 'TSC' AND REQ-MODE NOT = 'TSD'
               MOVE 'N' TO REQ-SOUND.
           IF REQ-SOUND NOT = 'Y'
               MOVE 'N' TO REQ-SOUND.
       DO-INIT-EXIT.
           EXIT.
       TRY-COLOUR.
           MOVE 'FSON' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           IF FS-RC NOT = 0
               GO TO TRY-COLOUR-EXIT.
           MOVE 1 TO FS-ACTIVE.
      * MVS-GS: THE BUFFER SIZE IS SET BEFORE THE QUERY (D32).
           MOVE 245 TO CV-CMD.
           IF REQ-COLOR = 'A' AND REQ-CANVAS = 'A'
               MOVE 126 TO CV-CMD.
           MOVE 195 TO HEXN.
           MOVE HX-B TO SX-DATA.
           MOVE 1 TO SX-LEN.
           PERFORM SEND-SX.
           IF FS-RC NOT = 0
               PERFORM DO-FSOF THRU DO-FSOF-EXIT
               GO TO TRY-COLOUR-EXIT.
           IF REQ-COLOR = 'Y'
               MOVE 'TSC' TO REQ-MODE
               GO TO TRY-COLOUR-EXIT.
           MOVE 'QRY ' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           MOVE 0 TO HAS-COLOUR.
           MOVE 0 TO HAS-HILITE.
           MOVE 0 TO HAS-GE.
           MOVE 'F' TO QS-ACT.
           IF FS-RC = 0
               MOVE 0 TO QS-NREC
               MOVE 0 TO QS-NWAIT
               CALL 'PACQRY' USING IN-AREA FS-LEN QRY-OUT
               PERFORM QRY-MORE THRU QRY-MORE-EXIT
                   UNTIL QS-ACT NOT = 'R'.
           IF FS-RC = 0 AND QS-ACT = 'F'
               PERFORM QRY-DRAIN.
           IF QS-ACT NOT = 'A'
               MOVE 4 TO FS-RC.
           IF FS-RC = 0
               MOVE QO-COLOUR TO HAS-COLOUR
               MOVE QO-HILITE TO HAS-HILITE
               MOVE QO-GE TO HAS-GE.
           IF FS-RC = 0 AND CV-CMD = 126
               MOVE QO-AW TO REQ-CW
               MOVE QO-AH TO REQ-CH.
           IF HAS-COLOUR = 1 AND HAS-HILITE = 1 AND REQ-HILITE = 'A'
               MOVE 'Y' TO REQ-HILITE.
           IF HAS-COLOUR = 1
               MOVE 'TSC' TO REQ-MODE
           ELSE
               PERFORM DO-FSOF THRU DO-FSOF-EXIT.
      * A BUFFER WIDER THAN 170 COLUMNS CANNOT HOLD THE 80 X 24 SCREENS
      * WITH 12-BIT ADDRESSES: LINE MODE (SAFE FALLBACK).
           IF REQ-MODE = 'TSC' AND REQ-CW > 170
               PERFORM FALL-BACK.
       TRY-COLOUR-EXIT.
           EXIT.
       QRY-MORE.
      * D40: ONE MORE STARTUP EVENT (A RECORD, OR NONE AFTER 0.5 S).
           MOVE 'RECT' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           IF FS-RC NOT = 0
               MOVE 'F' TO QS-ACT
               GO TO QRY-MORE-EXIT.
           CALL 'PACQRY' USING IN-AREA FS-LEN QRY-OUT.
       QRY-MORE-EXIT.
           EXIT.
       QRY-DRAIN.
      * D40: NO VALID REPLY: WHAT IS STILL QUEUED IS READ AND DROPPED.
           MOVE 0 TO QD-N.
           MOVE 1 TO QD-MORE.
           PERFORM QRY-DRAIN-ONE UNTIL QD-MORE = 0 OR QD-N > 7.
       QRY-DRAIN-ONE.
           ADD 1 TO QD-N.
           MOVE 'RECT' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           IF FS-RC NOT = 0 OR FS-LEN = 0
               MOVE 0 TO QD-MORE.
           MOVE 0 TO WS-NOP.
       DO-SEND.
           IF REQ-BELL = 'Y' AND REQ-SOUND = 'Y'
               PERFORM SET-ALARM.
           IF REQ-MODE = 'TSD'
               PERFORM TSD-FULL
               PERFORM PRINT-STREAM THRU PRINT-STREAM-EXIT
               GO TO DO-SEND-EXIT.
           IF REQ-MODE NOT = 'TSC'
               GO TO DO-SEND-EXIT.
           IF DS-KIND NOT = 'F'
               PERFORM SEND-PART THRU SEND-PART-EXIT
               GO TO DO-SEND-EXIT.
      * MVS-GS: ONLY THE FIRST FULL SCREEN IS A SEND (FULLSCR); LATER
      * ONES ARE ERASE/WRITE (ALTERNATE) + THE STREAM BY SENX.
           IF FULL-SENT = 1
               MOVE DS-BUF TO SX-DATA
               MOVE DS-LEN TO SX-LEN
               PERFORM SEND-SX
               IF FS-RC NOT = 0
                   PERFORM FALL-BACK
                   GO TO DO-SEND-EXIT
               ELSE
                   GO TO DO-SEND-EXIT.
           MOVE 1 TO FULL-SENT.
           MOVE 'SEND' TO FS-OP.
           MOVE DS-LEN TO FS-LEN.
           CALL 'PACFSIO' USING FS-OP DS-BUF FS-LEN FS-RC.
           IF FS-RC NOT = 0
               PERFORM FALL-BACK.
       DO-SEND-EXIT.
           EXIT.
       SET-ALARM.
      * MVS-S1: THE WCC IS THE FIRST BYTE OF EVERY STREAM; ITS ALARM
      * BIT X'04' IS SET UNLESS IT IS ALREADY ON.
           MOVE LOW-VALUE TO HX-Z.
           MOVE DS-BYTE (1) TO HX-B.
           DIVIDE HEXN BY 8 GIVING WS-Q REMAINDER WS-R.
           IF WS-R < 4
               ADD 4 TO HEXN.
           MOVE HX-B TO DS-BYTE (1).
       SEND-SX.
      * SENX: COMMAND CV-CMD + SX-LEN BYTES OF SX-DATA (TPUT NOEDIT).
           MOVE CV-CMD TO HEXN.
           MOVE HX-B TO SX-CMD.
           COMPUTE FS-LEN = SX-LEN + 1.
           MOVE 'SENX' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP SX-AREA FS-LEN FS-RC.
       TSD-FULL.
      * TSD: WHICH TRANSPORT A FULL SCREEN WOULD USE (TSX LINE).
           IF DS-KIND = 'F'
               MOVE 'FIRST' TO TF-CMD
               IF FULL-SENT = 1
                   PERFORM TSD-CMD
                   DISPLAY TSX-FULL
               ELSE
                   MOVE 1 TO FULL-SENT
                   DISPLAY TSX-FULL.
           MOVE 0 TO WS-I.
       TSD-CMD.
           MOVE 'F5' TO TF-CMD.
           IF CV-CMD = 126
               MOVE '7E' TO TF-CMD.
           MOVE 0 TO WS-I.
       SIM-CANVAS.
      * TSD (NO QUERY): CANVAS LETTERS SIMULATE THE ALTERNATE BUFFER.
           MOVE 245 TO CV-CMD.
           IF REQ-CANVAS = 'W'
               MOVE 120 TO REQ-CW
               MOVE 27 TO REQ-CH.
           IF REQ-CANVAS = 'X'
               MOVE 132 TO REQ-CW
               MOVE 27 TO REQ-CH.
           IF REQ-CANVAS = 'T'
               MOVE 80 TO REQ-CW
               MOVE 43 TO REQ-CH.
           IF REQ-CANVAS = 'M'
               MOVE 80 TO REQ-CW
               MOVE 32 TO REQ-CH.
           IF REQ-CANVAS = 'U'
               MOVE 100 TO REQ-CW
               MOVE 25 TO REQ-CH.
           IF REQ-CANVAS = 'L'
               MOVE 160 TO REQ-CW
               MOVE 30 TO REQ-CH.
           IF REQ-CW NOT = 80 OR REQ-CH NOT = 24
               MOVE 126 TO CV-CMD.
           PERFORM TSD-CMD.
           MOVE TF-CMD TO TS-CMD.
           MOVE REQ-CW TO TS-W.
           MOVE REQ-CH TO TS-H.
           DISPLAY TSX-SW.
       SEND-PART.
      * MVS-G3 PARTIAL SEND (WRITE X'F1' + TPUT NOEDIT, PROBE E6). A
      * FAILURE IS NOT FATAL: FULL REDRAW WITHOUT ANIMATION FROM NOW ON
      * AND THE CALLER IS TOLD TO SEND THE WHOLE SCREEN (REQ-SENDST R).
           MOVE 'SENP' TO FS-OP.
           MOVE DS-LEN TO FS-LEN.
           CALL 'PACFSIO' USING FS-OP DS-BUF FS-LEN FS-RC.
           IF FS-RC NOT = 0
               MOVE 'R' TO REQ-SENDST
               MOVE 'F' TO REQ-REDRAW
               MOVE 'N' TO REQ-ANIM.
       SEND-PART-EXIT.
           EXIT.
       DO-RECV.
      * REQ-INKEY: E = ENTER (REQ-INTEXT = TYPED FIELD), P = ANY OTHER
      * AID (PA2 RESHOW ...), X = ERROR (NOW BACK IN TSO LINE MODE).
           MOVE SPACES TO REQ-INTEXT.
           MOVE 'X' TO REQ-INKEY.
           IF REQ-MODE NOT = 'TSC'
               GO TO DO-RECV-EXIT.
           MOVE 'RECV' TO FS-OP.
           IF REQ-ANIM = 'Y' AND REQ-REDRAW = 'P' AND REQ-PLAY NOT = 'R'
               MOVE 'RECT' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           IF FS-RC NOT = 0
               PERFORM FALL-BACK
               GO TO DO-RECV-EXIT.
      * MVS-G3 IDLE TICK: RECT = ONE READ + 0.5 S WAIT. EMPTY = TELL THE
      * CALLER (REQ-INKEY T); AFTER 5 MINUTES OF NOTHING AS BEFORE.
           MOVE 0 TO WS-STOP.
           IF FS-OP = 'RECT' AND FS-LEN < 1
               ADD 1 TO WS-IDLE
               MOVE 'T' TO REQ-INKEY
               MOVE 1 TO WS-STOP.
           IF WS-STOP = 1 AND WS-IDLE > 599
               PERFORM FALL-BACK
               MOVE 'X' TO REQ-INKEY.
           IF WS-STOP = 1
               GO TO DO-RECV-EXIT.
           MOVE 0 TO WS-IDLE.
           IF FS-LEN < 1
               PERFORM FALL-BACK
               GO TO DO-RECV-EXIT.
           PERFORM PARSE-IN THRU PARSE-IN-EXIT.
       DO-RECV-EXIT.
           EXIT.
       PARSE-IN.
           MOVE 'P' TO REQ-INKEY.
           MOVE IN-CH (1) TO REQ-AID.
           MOVE 1 TO WS-K.
           PERFORM BYTE-VAL.
           IF WS-V NOT = 125
               GO TO PARSE-IN-EXIT.
           MOVE 'E' TO REQ-INKEY.
      * READ MODIFIED: AID, CURSOR(2), SBA X'11'(17) + ADDRESS(2), DATA.
           MOVE 4 TO WS-K.
           PERFORM BYTE-VAL.
           IF FS-LEN > 6 AND WS-V = 17
               PERFORM COPY-TEXT THRU COPY-TEXT-EXIT
                   VARYING WS-I FROM 1 BY 1 UNTIL WS-I > 8.
       PARSE-IN-EXIT.
           EXIT.
       DO-POLL.
      * MVS-RT: ONE NON-BLOCKING READ. N = NOTHING, E / P AS RECV, X =
      * ERROR (NOW BACK IN TSO LINE MODE).
           MOVE SPACES TO REQ-INTEXT.
           MOVE 'X' TO REQ-INKEY.
           IF REQ-MODE NOT = 'TSC'
               GO TO DO-POLL-EXIT.
           MOVE 'POLL' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           IF FS-RC NOT = 0
               PERFORM FALL-BACK
               GO TO DO-POLL-EXIT.
           MOVE 'N' TO REQ-INKEY.
           IF FS-LEN > 0
               PERFORM PARSE-IN THRU PARSE-IN-EXIT.
       DO-POLL-EXIT.
           EXIT.
       DO-WDLN.
      * MVS-RT ABSOLUTE DEADLINES: NEXT = LAST DEADLINE + PERIOD; WHOLE
      * PERIODS ALREADY MISSED ARE SKIPPED; WAIT ONLY FOR THE REMAINDER.
           MOVE REQ-RTPER TO RT-PERIOD.
           COMPUTE RT-NEXT = REQ-TIME + RT-PERIOD.
           CALL 'PACTSO' USING TSO-TIME TSO-RC RT-NOW.
           COMPUTE RT-LIM = RT-NOW - RT-PERIOD.
           PERFORM SKIP-PERIOD UNTIL RT-NEXT > RT-LIM.
           MOVE RT-NEXT TO REQ-TIME.
           CALL 'PACTSO' USING TSO-DLWT TSO-RC REQ-TIME.
       SKIP-PERIOD.
           ADD RT-PERIOD TO RT-NEXT.
       COPY-TEXT.
           COMPUTE WS-K = WS-I + 6.
           IF WS-K NOT > FS-LEN
               MOVE IN-CH (WS-K) TO REQ-INTEXT-CH (WS-I).
       COPY-TEXT-EXIT.
           EXIT.
       DO-HSRD.
           MOVE 'N' TO REQ-HSST.
           MOVE 'N' TO REQ-HSNEW.
           MOVE 0 TO REQ-HISCORE.
           MOVE 0 TO REQ-HSLVL.
           MOVE 'READ' TO HS-OP.
           MOVE SPACES TO HS-REC.
           CALL 'PACHSIO' USING HS-OP HS-RC HS-DDN HS-REC.
           IF HS-RC = 4
               GO TO DO-HSRD-EXIT.
           MOVE 'E' TO REQ-HSST.
           IF HS-RC NOT = 0 AND HS-RC NOT = 12
               GO TO DO-HSRD-EXIT.
           MOVE 'Z' TO REQ-HSST.
           IF HS-RC = 12
               GO TO DO-HSRD-EXIT.
           IF HR-SCORE NUMERIC AND HR-TAG = 'PACHS001'
                   AND HR-LVL NUMERIC
               MOVE 'R' TO REQ-HSST
               MOVE HN-SCORE TO REQ-HISCORE
               MOVE HN-LVL TO REQ-HSLVL.
       DO-HSRD-EXIT.
           EXIT.
       DO-HSWR.
           MOVE 'N' TO REQ-HSNEW.
           IF REQ-HSST NOT = 'R' AND REQ-HSST NOT = 'Z'
               GO TO DO-HSWR-EXIT.
           IF REQ-HSSCORE NOT > REQ-HISCORE
               GO TO DO-HSWR-EXIT.
           MOVE 'P' TO REQ-HSNEW.
           IF REQ-HSELIG NOT = 'Y'
               GO TO DO-HSWR-EXIT.
           MOVE SPACES TO HS-REC.
           MOVE REQ-HSSCORE TO HN-SCORE.
           MOVE 'PACHS001' TO HR-TAG.
           MOVE REQ-HSGLVL TO HN-LVL.
           MOVE 'REPL' TO HS-OP.
           IF REQ-HSST = 'R'
               MOVE 'WRIT' TO HS-OP.
           CALL 'PACHSIO' USING HS-OP HS-RC HS-DDN HS-REC.
           MOVE 'F' TO REQ-HSNEW.
           IF HS-RC NOT = 0 AND HS-RC NOT = 2
               GO TO DO-HSWR-EXIT.
           MOVE 'Y' TO REQ-HSNEW.
           MOVE REQ-HSSCORE TO REQ-HISCORE.
           MOVE REQ-HSGLVL TO REQ-HSLVL.
       DO-HSWR-EXIT.
           EXIT.
       DO-FSOF.
           IF FS-ACTIVE = 1
               MOVE 'FSOF' TO FS-OP
               CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC
               MOVE 0 TO FS-ACTIVE.
       DO-FSOF-EXIT.
           EXIT.
       FALL-BACK.
           PERFORM DO-FSOF THRU DO-FSOF-EXIT.
           MOVE 'TSO' TO REQ-MODE.
           MOVE 'N' TO REQ-HILITE.
           MOVE 'N' TO REQ-ANIM.
           MOVE 'F' TO REQ-REDRAW.
           MOVE 'C' TO REQ-GLYPHS.
           MOVE 'N' TO REQ-SCALE.
           MOVE 80 TO REQ-CW.
           MOVE 24 TO REQ-CH.
       BYTE-VAL.
           MOVE IN-CH (WS-K) TO HX-B.
           MOVE HEXN TO WS-V.
       PRINT-STREAM.
      * TSD DRY RUN: THE WHOLE DATA STREAM, 32 BYTES PER LINE IN HEX.
           MOVE DS-LEN TO LL-LEN.
           DISPLAY LEN-LINE.
           MOVE 1 TO WS-K.
           PERFORM PRINT-LINE UNTIL WS-K > DS-LEN.
       PRINT-STREAM-EXIT.
           EXIT.
       PRINT-LINE.
           MOVE SPACES TO HEX-LINE.
           MOVE 'TSD ' TO HEX-LINE.
           MOVE 0 TO WS-O.
           PERFORM PRINT-BYTE UNTIL WS-O > 62 OR WS-K > DS-LEN.
           DISPLAY HEX-LINE.
       PRINT-BYTE.
           MOVE DS-BYTE (WS-K) TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-Q) TO HL-CH (WS-O).
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-R) TO HL-CH (WS-O).
           ADD 1 TO WS-K.
ZZ
//COB7     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ7,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.R20.COBOL(PACPLAT),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.R20.COPY,DISP=SHR
//SRC8     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COBOL(PACSCR),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
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
ZZ
//COB8     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ8,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.R20.COBOL(PACSCR),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.R20.COPY,DISP=SHR
//SRC9     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COBOL(PACQRY),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACQRY : MVS-G4 CAPABILITY PARSING (PURE: NO I/O, NO TERMINAL).
      * CALL 'PACQRY' USING QRY-AREA QRY-LEN QRY-OUT. THE AREA HOLDS A
      * READ PARTITION QUERY REPLY AS RECEIVED BY PACPLAT (AID X'88'
      * + STRUCTURED FIELDS: LENGTH(2), X'81', QCODE, DATA). OUT:
      *   QO-COLOUR 1 = QCODE X'86' (MVS-G1), QO-HILITE 1 = QCODE X'87'
      *   (MVS-G2), QO-GE 1 = QCODE X'85' WITH FLAG X'80' (GE) AND X'02'
      *   (CGCSGID PRESENT) AND A SET WHOSE CODE PAGE IS 310 (APL).
      * THE G1/G2 DECISIONS WERE MOVED HERE FROM PACPLAT UNCHANGED.
      * MVS-GS: QO-AW/QO-AH = THE ALTERNATE SCREEN SIZE: QCODE X'A6'
      * (IMPLICIT PARTITION, ALTERNATE WIDTH/HEIGHT AT +13/+15), ELSE
      * QCODE X'81' (USABLE AREA, WIDTH/HEIGHT AT +6/+8), ELSE 80 X 24.
      * MVS-RP D40 (DOCS/RP-POLISH.MD 11): QO-VALID 1 = A STRUCTURALLY
      * VALID QUERY REPLY (LENGTH >= 5, AID X'88', AN EXACT CHAIN OF
      * FIELDS LL >= 4 WITH ID X'81' TO THE LAST BYTE, THE FIRST ONE
      * QCODE X'80' SUMMARY). EVERY CALL IS ALSO ONE STARTUP EVENT OF
      * THE CALLER'S SELECTION (QS-NREC/QS-NWAIT ZEROED BY THE CALLER
      * BEFORE THE FIRST): LENGTH 0 = AN EMPTY READ (QS-NWAIT + 1), AN
      * INVALID RECORD QS-NREC + 1; QS-ACT A = ACCEPT THIS RECORD, F =
      * GIVE UP (8 RECORDS OR 6 EMPTY READS), R = READ AGAIN. THE
      * CAPABILITY OUTPUTS ARE COMPUTED AS BEFORE FOR EVERY RECORD.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACQRY.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  WS-K                  PIC 9(4).
       01  WS-P                  PIC 9(4).
       01  WS-V                  PIC 9(4).
       01  WS-L                  PIC 9(4).
       01  WS-ID                 PIC 9(4).
       01  WS-QC                 PIC 9(4).
       01  WS-LIM                PIC 9(4).
       01  WS-END                PIC 9(4).
       01  WS-D                  PIC 9(4).
       01  WS-DL                 PIC 9(4).
       01  WS-F1                 PIC 9(4).
       01  WS-Q                  PIC 9(4).
       01  WS-R                  PIC 9(4).
       01  WS-CP                 PIC 9(4).
       01  WS-STOP               PIC 9.
       01  WS-DSTOP              PIC 9.
       01  WS-NOP                PIC 9.
       01  WS-W                  PIC 9(4).
       01  UA-W                  PIC 9(4) VALUE 0.
       01  UA-H                  PIC 9(4) VALUE 0.
       01  IP-W                  PIC 9(4) VALUE 0.
       01  IP-H                  PIC 9(4) VALUE 0.
       01  VA-P                  PIC 9(4).
       01  VA-L                  PIC 9(4).
       01  VA-E                  PIC 9(4).
       01  VA-N                  PIC 9(4).
       01  VA-STOP               PIC 9.
       LINKAGE SECTION.
       01  QRY-AREA.
           05  QRY-CH            PIC X OCCURS 2048 TIMES.
       01  QRY-LEN               PIC S9(4) COMP.
       01  QRY-OUT.
           05  QO-COLOUR         PIC 9.
           05  QO-HILITE         PIC 9.
           05  QO-GE             PIC 9.
           05  QO-AW             PIC 999.
           05  QO-AH             PIC 999.
           05  QO-VALID          PIC 9.
           05  QS-ACT            PIC X.
           05  QS-NREC           PIC 99.
           05  QS-NWAIT          PIC 99.
       PROCEDURE DIVISION USING QRY-AREA QRY-LEN QRY-OUT.
       MAIN-PARA.
           MOVE 0 TO QO-COLOUR.
           MOVE 0 TO QO-HILITE.
           MOVE 0 TO QO-GE.
           MOVE 0 TO UA-W UA-H IP-W IP-H.
           PERFORM FIND-CAPS THRU FIND-CAPS-EXIT.
           MOVE 80 TO QO-AW.
           MOVE 24 TO QO-AH.
           IF UA-W > 0 AND UA-H > 0 AND UA-W < 1000 AND UA-H < 1000
               MOVE UA-W TO QO-AW
               MOVE UA-H TO QO-AH.
           IF IP-W > 0 AND IP-H > 0 AND IP-W < 1000 AND IP-H < 1000
               MOVE IP-W TO QO-AW
               MOVE IP-H TO QO-AH.
           PERFORM VALIDATE THRU VALIDATE-EXIT.
           PERFORM SELECT-STEP.
           GOBACK.
       VALIDATE.
           MOVE 0 TO QO-VALID.
           IF QRY-LEN < 5
               GO TO VALIDATE-EXIT.
           MOVE 1 TO WS-K.
           PERFORM BYTE-VAL.
           IF WS-V NOT = 136
               GO TO VALIDATE-EXIT.
           MOVE 2 TO VA-P.
           MOVE 0 TO VA-N.
           MOVE 0 TO VA-STOP.
           PERFORM VAL-SF THRU VAL-SF-EXIT UNTIL VA-STOP > 0.
           IF VA-STOP = 1
               MOVE 1 TO QO-VALID.
       VALIDATE-EXIT.
           EXIT.
       VAL-SF.
      * VA-STOP 1 = THE CHAIN ENDS EXACTLY AT THE LAST BYTE, 2 = BAD.
           IF VA-P > QRY-LEN AND VA-N > 0
               MOVE 1 TO VA-STOP
               GO TO VAL-SF-EXIT.
           COMPUTE VA-E = VA-P + 3.
           IF VA-E > QRY-LEN
               MOVE 2 TO VA-STOP
               GO TO VAL-SF-EXIT.
           MOVE VA-P TO WS-K.
           PERFORM WORD-VAL.
           MOVE WS-W TO VA-L.
           COMPUTE VA-E = VA-P + VA-L - 1.
           IF VA-L < 4 OR VA-E > QRY-LEN
               MOVE 2 TO VA-STOP
               GO TO VAL-SF-EXIT.
           COMPUTE WS-K = VA-P + 2.
           PERFORM BYTE-VAL.
           IF WS-V NOT = 129
               MOVE 2 TO VA-STOP
               GO TO VAL-SF-EXIT.
           COMPUTE WS-K = VA-P + 3.
           PERFORM BYTE-VAL.
           IF VA-N = 0 AND WS-V NOT = 128
               MOVE 2 TO VA-STOP
               GO TO VAL-SF-EXIT.
           ADD 1 TO VA-N.
           ADD VA-L TO VA-P.
       VAL-SF-EXIT.
           EXIT.
       SELECT-STEP.
           IF QRY-LEN < 1
               ADD 1 TO QS-NWAIT
           ELSE IF QO-VALID = 0
               ADD 1 TO QS-NREC.
           MOVE 'R' TO QS-ACT.
           IF QS-NREC NOT < 8 OR QS-NWAIT NOT < 6
               MOVE 'F' TO QS-ACT.
           IF QO-VALID = 1
               MOVE 'A' TO QS-ACT.
           MOVE 0 TO WS-NOP.
       FIND-CAPS.
      * QUERY REPLY = AID X'88' (136) + STRUCTURED FIELDS: LENGTH(2),
      * X'81' (129), QCODE. COLOUR SUPPORT = QCODE X'86' (134).
           IF QRY-LEN < 1
               GO TO FIND-CAPS-EXIT.
           MOVE 1 TO WS-K.
           PERFORM BYTE-VAL.
           IF WS-V NOT = 136
               GO TO FIND-CAPS-EXIT.
           MOVE 2 TO WS-P.
           MOVE 0 TO WS-STOP.
           PERFORM NEXT-SF THRU NEXT-SF-EXIT UNTIL WS-STOP = 1.
       FIND-CAPS-EXIT.
           EXIT.
       NEXT-SF.
           COMPUTE WS-LIM = WS-P + 3.
           IF WS-LIM > QRY-LEN
               MOVE 1 TO WS-STOP
               GO TO NEXT-SF-EXIT.
           MOVE WS-P TO WS-K.
           PERFORM BYTE-VAL.
           COMPUTE WS-L = WS-V * 256.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           ADD WS-V TO WS-L.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           MOVE WS-V TO WS-ID.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           MOVE WS-V TO WS-QC.
           IF WS-ID = 129 AND WS-QC = 134
               MOVE 1 TO QO-COLOUR.
           IF WS-ID = 129 AND WS-QC = 135
               MOVE 1 TO QO-HILITE.
           IF WS-ID = 129 AND WS-QC = 133 AND WS-L > 13
               PERFORM CHAR-SETS THRU CHAR-SETS-EXIT.
           IF WS-ID = 129 AND WS-QC = 129 AND WS-L > 9
               PERFORM USABLE THRU USABLE-EXIT.
           IF WS-ID = 129 AND WS-QC = 166 AND WS-L > 16
               PERFORM IMPLICIT THRU IMPLICIT-EXIT.
           IF WS-L < 4
               MOVE 1 TO WS-STOP
           ELSE
               ADD WS-L TO WS-P.
       NEXT-SF-EXIT.
           EXIT.
       CHAR-SETS.
      * X'85': FLAGS1 AT +4, DESCRIPTOR LENGTH (DL) AT +12, DESCRIPTORS
      * FROM +13 TO THE END OF THE FIELD; THE CGCSGID IS THE LAST FOUR
      * BYTES OF A DESCRIPTOR, ITS LAST TWO = CODE PAGE (310 = X'0136').
           COMPUTE WS-END = WS-P + WS-L - 1.
           IF WS-END > QRY-LEN
               GO TO CHAR-SETS-EXIT.
           COMPUTE WS-K = WS-P + 4.
           PERFORM BYTE-VAL.
           MOVE WS-V TO WS-F1.
           IF WS-F1 < 128
               GO TO CHAR-SETS-EXIT.
           DIVIDE WS-F1 BY 4 GIVING WS-Q REMAINDER WS-R.
           IF WS-R < 2
               GO TO CHAR-SETS-EXIT.
           COMPUTE WS-K = WS-P + 12.
           PERFORM BYTE-VAL.
           MOVE WS-V TO WS-DL.
           IF WS-DL < 4
               GO TO CHAR-SETS-EXIT.
           COMPUTE WS-D = WS-P + 13.
           MOVE 0 TO WS-DSTOP.
           PERFORM NEXT-DESC UNTIL WS-DSTOP = 1.
       CHAR-SETS-EXIT.
           EXIT.
       NEXT-DESC.
           COMPUTE WS-LIM = WS-D + WS-DL - 1.
           IF WS-LIM > WS-END
               MOVE 1 TO WS-DSTOP.
           IF WS-DSTOP = 0
               PERFORM DESC-CP.
           ADD WS-DL TO WS-D.
       DESC-CP.
           COMPUTE WS-K = WS-LIM - 1.
           PERFORM BYTE-VAL.
           COMPUTE WS-CP = WS-V * 256.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           ADD WS-V TO WS-CP.
           IF WS-CP = 310
               MOVE 1 TO QO-GE.
           MOVE 0 TO WS-NOP.
       USABLE.
      * X'81' USABLE AREA: WIDTH AT +6, HEIGHT AT +8 (2 BYTES EACH).
           COMPUTE WS-END = WS-P + 9.
           IF WS-END > QRY-LEN
               GO TO USABLE-EXIT.
           COMPUTE WS-K = WS-P + 6.
           PERFORM WORD-VAL.
           MOVE WS-W TO UA-W.
           COMPUTE WS-K = WS-P + 8.
           PERFORM WORD-VAL.
           MOVE WS-W TO UA-H.
       USABLE-EXIT.
           EXIT.
       IMPLICIT.
      * X'A6' IMPLICIT PARTITION: SELF-DEFINING PARAMETER X'01' AT +7,
      * ALTERNATE WIDTH AT +13, ALTERNATE HEIGHT AT +15.
           COMPUTE WS-END = WS-P + 16.
           IF WS-END > QRY-LEN
               GO TO IMPLICIT-EXIT.
           COMPUTE WS-K = WS-P + 7.
           PERFORM BYTE-VAL.
           IF WS-V NOT = 1
               GO TO IMPLICIT-EXIT.
           COMPUTE WS-K = WS-P + 13.
           PERFORM WORD-VAL.
           MOVE WS-W TO IP-W.
           COMPUTE WS-K = WS-P + 15.
           PERFORM WORD-VAL.
           MOVE WS-W TO IP-H.
       IMPLICIT-EXIT.
           EXIT.
       WORD-VAL.
           PERFORM BYTE-VAL.
           COMPUTE WS-W = WS-V * 256.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           ADD WS-V TO WS-W.
       BYTE-VAL.
           MOVE QRY-CH (WS-K) TO HX-B.
           MOVE HEXN TO WS-V.
ZZ
//COB9     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ9,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.R20.COBOL(PACQRY),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.R20.COPY,DISP=SHR
//SRC10    EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.R20.COBOL(PACRT),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACRT : MVS-RT REALTIME CONTROLLER (D33). NO TERMINAL OR HOST
      * I/O; THE GAME STATE IS CHANGED ONLY THROUGH PACGAME, WALLS ARE
      * READ THROUGH PACMAP. ITS OWN STATE (DIRECTIONS, TTL, CADENCE,
      * PAUSE, DEATH FREEZE, WIDE COUNTERS) LIVES HERE.
      * OPS: RINI  RESET (NOT STARTED).
      *      RIN   ONE INPUT EVENT (REQ-KIND / REQ-DIR / REQ-CHAR):
      *            MOV = REQUESTED DIRECTION (TTL 3 PLAYER STEPS; THE
      *            FIRST ONE STARTS THE GAME), PAU = PAUSE ON / OFF;
      *            EVERY EVENT IS RECORDED FOR THE QUANTUM'S REQ-RTIN.
      *            DIRECTIONS ARE IGNORED WHILE PAUSED OR FROZEN.
      *      RQ    ONE QUANTUM: ANIMATION FRAME, DEATH FREEZE, GHOST
      *            CADENCE 4/5 (ACC + 4, DUE AT >= 5), REQUEST APPLIED
      *            WHEN LEGAL ELSE TTL - 1, PLAYER STEP WHEN THE
      *            CURRENT DIRECTION IS OPEN; PACGAME MOVE WITH
      *            REQ-STEP B (BOTH), P (PLAYER) OR G (GHOSTS). A LOST
      *            LIFE FREEZES 1.5 S (RT-FRT QUANTA, 10 AT 150 MS) AND
      *            CLEARS BOTH DIRECTIONS.
      * OUT (EVERY OP): REQ-RTSTAT WAIT/RUN /PAUS/FRZ , REQ-RTQ,
      *      REQ-RTCUR, REQ-RTREQ, REQ-RTTTL, REQ-VIS; RQ ALSO REQ-RTIN
      *      (THE QUANTUM'S INPUTS) AND REQ-STEP (B P G - OR F).
      * MVS-GP1 (D36, ARC-ON = 1): EACH RUNNING QUANTUM FIRST CALLS
      *      PACGAME ATIK (FRIGHT TICK), THEN THE FRIGHTENED GHOSTS'
      *      ACCUMULATOR ARC-FACC + ARC-KFINC (DUE AT >= 5, 2/5 OF THE
      *      QUANTA) BESIDE THE NORMAL ONE (4/5); ARC-MOVEN/ARC-MOVEF
      *      TELL PACAI WHICH GHOSTS MOVE. A DEATH RESETS RT-ACC.
      * MVS-GP2 (D37, ARC-ON = 1): THE NORMAL GHOSTS' ACCUMULATOR TAKES
      *      THE LEVEL'S STEP ARC-KNUM (DUE AT >= 10; 8 = THE GP1 4/5
      *      PATTERN). A DEATH OR A LEVEL CLEAR (PACGAME FLAGS D / C,
      *      NOT THE LIVES COUNT: AN EXTRA LIFE MAY COME IN THE SAME
      *      STEP) RESETS RT-ACC AND FREEZES 10 QUANTA.
      * MVS-RP (D39): PUBLISH ALSO GIVES REQ-RTFRZ (FREEZE QUANTA LEFT);
      *      EVERY GAME STEP SETS REQ-DTHX/REQ-DTHY = PAC-MAN'S CELL
      *      AFTER HIS MOVE OF THE STEP (THE DEATH CELL; DISPLAY ONLY).
      * MVS-RP RP.3 SPEED (D39 6): THE DESIGNED QUANTA (150 MS) ARE
      *      CONVERTED ONCE AT RINI TO THE QUANTUM REQ-RTPER BY RT-CONV
      *      (THE SAME PARAGRAPH AS PACGAME): THE FREEZE (10 = 1.5 S),
      *      READY! (4) AND THE POPUP (5), PUBLISHED AS REQ-RTFRT,
      *      REQ-RTRDY, REQ-RTPUQ. MOVEMENT STAYS PER QUANTUM.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACRT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  MAP-REQ COPY PACMREQ.
       01  RT-Q                  PIC 9(7) VALUE 0.
       01  RT-STEPS              PIC 9(7) VALUE 0.
       01  RT-CUR                PIC X VALUE SPACE.
       01  RT-REQ                PIC X VALUE SPACE.
       01  RT-TTL                PIC 9 VALUE 0.
       01  RT-ACC                PIC 99 VALUE 0.
       01  RT-FRZ                PIC 99 VALUE 0.
       01  RT-PAUSE              PIC 9 VALUE 0.
       01  RT-START              PIC 9 VALUE 0.
       01  RT-NIN                PIC 9 VALUE 0.
       01  RT-VIS                PIC 9 VALUE 0.
       01  WS-IN.
           05  WS-IN-CH          PIC X OCCURS 8 TIMES.
       01  TTL-INIT              PIC 9 VALUE 3.
       01  FRZ-INIT              PIC 99 VALUE 10.
       01  RDY-INIT              PIC 99 VALUE 4.
       01  PUQ-INIT              PIC 99 VALUE 5.
       01  RT-FRT                PIC 99 VALUE 10.
       01  RT-RDY                PIC 99 VALUE 4.
       01  RT-PUQ                PIC 99 VALUE 5.
       01  WS-CQ                 PIC 999.
       01  WS-CN                 PIC 9(7).
       01  WS-CD                 PIC 9(4).
       01  GH-NUM                PIC 9 VALUE 4.
       01  GH-DEN                PIC 9 VALUE 5.
       01  GH-DEN10              PIC 99 VALUE 10.
       01  RT-NUM                PIC 99.
       01  RT-DEN                PIC 99.
       01  WS-FRZE               PIC 9.
       01  ANIM-Q                PIC 9 VALUE 3.
       01  WS-DIR                PIC X.
       01  WS-LEGAL              PIC 9.
       01  WS-PMOVE              PIC 9.
       01  WS-GDUE               PIC 9.
       01  WS-KIND               PIC X.
       01  WS-LIVES              PIC 9.
       01  WS-Q                  PIC 9(7).
       01  WS-Q2                 PIC 9(7).
       01  WS-R                  PIC 9.
       01  WS-NOP                PIC 9.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       01  PAC-ARC COPY PACARC.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ PAC-ARC.
       MAIN-PARA.
           IF REQ-OP = 'RINI'
               PERFORM DO-RINI
           ELSE IF REQ-OP = 'RIN '
               PERFORM DO-RIN THRU DO-RIN-EXIT
           ELSE IF REQ-OP = 'RQ  '
               PERFORM DO-RQ THRU DO-RQ-EXIT.
           PERFORM PUBLISH.
           GOBACK.
       DO-RINI.
           MOVE 0 TO RT-Q.
           MOVE 0 TO RT-STEPS.
           MOVE SPACE TO RT-CUR.
           MOVE SPACE TO RT-REQ.
           MOVE 0 TO RT-TTL.
           MOVE 0 TO RT-ACC.
           MOVE 0 TO RT-FRZ.
           MOVE 0 TO RT-PAUSE.
           MOVE 0 TO RT-START.
           MOVE 0 TO RT-NIN.
           MOVE 0 TO RT-VIS.
           MOVE SPACES TO WS-IN.
           MOVE SPACES TO REQ-RTIN.
           MOVE '-' TO REQ-STEP.
           MOVE 0 TO REQ-DTHX.
           MOVE 0 TO REQ-DTHY.
           MOVE FRZ-INIT TO WS-CQ.
           PERFORM RT-CONV THRU RT-CONV-EXIT.
           MOVE WS-CQ TO RT-FRT.
           MOVE RDY-INIT TO WS-CQ.
           PERFORM RT-CONV THRU RT-CONV-EXIT.
           MOVE WS-CQ TO RT-RDY.
           MOVE PUQ-INIT TO WS-CQ.
           PERFORM RT-CONV THRU RT-CONV-EXIT.
           MOVE WS-CQ TO RT-PUQ.
       DO-RIN.
           IF RT-NIN < 8
               ADD 1 TO RT-NIN
               PERFORM NOTE-INPUT.
           IF REQ-KIND = 'PAU' AND RT-START = 1
               PERFORM TOGGLE-PAUSE.
           IF REQ-KIND NOT = 'MOV'
               GO TO DO-RIN-EXIT.
           IF RT-PAUSE = 1 OR RT-FRZ > 0
               GO TO DO-RIN-EXIT.
           MOVE REQ-DIR TO RT-REQ.
           MOVE TTL-INIT TO RT-TTL.
           MOVE 1 TO RT-START.
       DO-RIN-EXIT.
           EXIT.
       NOTE-INPUT.
           MOVE REQ-CHAR TO WS-IN-CH (RT-NIN).
           IF REQ-KIND = 'MOV'
               MOVE REQ-DIR TO WS-IN-CH (RT-NIN).
           IF REQ-KIND = 'QUI'
               MOVE 'Q' TO WS-IN-CH (RT-NIN).
           IF REQ-KIND = 'PAU'
               MOVE 'P' TO WS-IN-CH (RT-NIN).
           IF REQ-KIND = 'RDR'
               MOVE '*' TO WS-IN-CH (RT-NIN).
           IF REQ-KIND = 'CFG'
               MOVE 'A' TO WS-IN-CH (RT-NIN).
           MOVE 0 TO WS-NOP.
       TOGGLE-PAUSE.
           IF RT-PAUSE = 1
               MOVE 0 TO RT-PAUSE
           ELSE
               MOVE 1 TO RT-PAUSE.
           MOVE 0 TO WS-NOP.
       DO-RQ.
           ADD 1 TO RT-Q.
           MOVE WS-IN TO REQ-RTIN.
           MOVE SPACES TO WS-IN.
           MOVE 0 TO RT-NIN.
           MOVE '-' TO REQ-STEP.
           DIVIDE RT-Q BY ANIM-Q GIVING WS-Q.
           DIVIDE WS-Q BY 2 GIVING WS-Q2 REMAINDER WS-R.
           MOVE WS-R TO RT-VIS.
           IF RT-FRZ > 0
               SUBTRACT 1 FROM RT-FRZ
               MOVE 'F' TO REQ-STEP
               GO TO DO-RQ-EXIT.
           IF ARC-ON = 1
               PERFORM ARC-QUANTUM THRU ARC-QUANTUM-EXIT.
           MOVE 0 TO WS-GDUE.
           MOVE GH-NUM TO RT-NUM.
           MOVE GH-DEN TO RT-DEN.
           IF ARC-ON = 1
               MOVE ARC-KNUM TO RT-NUM
               MOVE GH-DEN10 TO RT-DEN.
           ADD RT-NUM TO RT-ACC.
           IF RT-ACC NOT < RT-DEN
               SUBTRACT RT-DEN FROM RT-ACC
               MOVE 1 TO WS-GDUE.
           IF ARC-ON = 1
               MOVE WS-GDUE TO ARC-MOVEN
               IF ARC-MOVEF = 1
                   MOVE 1 TO WS-GDUE.
           IF RT-REQ NOT = SPACE
               PERFORM APPLY-REQ.
           MOVE 0 TO WS-PMOVE.
           IF RT-CUR NOT = SPACE
               MOVE RT-CUR TO WS-DIR
               PERFORM LEGAL THRU LEGAL-EXIT
               MOVE WS-LEGAL TO WS-PMOVE.
           MOVE '-' TO WS-KIND.
           IF WS-PMOVE = 1 AND WS-GDUE = 1
               MOVE 'B' TO WS-KIND
           ELSE IF WS-PMOVE = 1
               MOVE 'P' TO WS-KIND
           ELSE IF WS-GDUE = 1
               MOVE 'G' TO WS-KIND.
           IF WS-KIND NOT = '-'
               PERFORM GAME-STEP.
       DO-RQ-EXIT.
           EXIT.
       APPLY-REQ.
      * THE REQUEST BECOMES THE CURRENT DIRECTION WHEN ITS CELL IS OPEN
      * (A REVERSAL ALWAYS IS); OTHERWISE IT WAITS AT MOST TTL STEPS.
           MOVE RT-REQ TO WS-DIR.
           PERFORM LEGAL THRU LEGAL-EXIT.
           IF WS-LEGAL = 1
               MOVE RT-REQ TO RT-CUR
               MOVE SPACE TO RT-REQ
               MOVE 0 TO RT-TTL
           ELSE
               SUBTRACT 1 FROM RT-TTL.
           IF RT-TTL = 0
               MOVE SPACE TO RT-REQ.
           MOVE 0 TO WS-NOP.
       GAME-STEP.
      * MVS-RP: THE CELL PAC-MAN STANDS ON AFTER HIS MOVE (WS-PMOVE = 1:
      * THE CELL IN RT-CUR IS OPEN), BEFORE A DEATH MAY RESET HIM.
           MOVE PLAYER-X TO REQ-DTHX.
           MOVE PLAYER-Y TO REQ-DTHY.
           IF WS-PMOVE = 1 AND RT-CUR = 'U'
               SUBTRACT 1 FROM REQ-DTHY.
           IF WS-PMOVE = 1 AND RT-CUR = 'D'
               ADD 1 TO REQ-DTHY.
           IF WS-PMOVE = 1 AND RT-CUR = 'L'
               SUBTRACT 1 FROM REQ-DTHX.
           IF WS-PMOVE = 1 AND RT-CUR = 'R'
               ADD 1 TO REQ-DTHX.
           MOVE LIVES TO WS-LIVES.
           MOVE WS-KIND TO REQ-STEP.
           MOVE RT-CUR TO REQ-DIR.
           MOVE RT-CUR TO REQ-CHAR.
           MOVE 'MOVE' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ PAC-ARC.
           MOVE 'RQ  ' TO REQ-OP.
           MOVE 0 TO WS-FRZE.
           IF ARC-ON = 0 AND LIVES < WS-LIVES
               MOVE 1 TO WS-FRZE.
           IF ARC-ON = 1 AND ARC-ED = 'D'
               MOVE 1 TO WS-FRZE.
           IF ARC-ON = 1 AND ARC-EC = 'C'
               MOVE 1 TO WS-FRZE.
           IF ARC-ON = 1 AND WS-FRZE = 1
               MOVE 0 TO RT-ACC.
           IF WS-KIND NOT = 'G'
               ADD 1 TO RT-STEPS.
           IF WS-FRZE = 1 AND F-LOST = 0
               MOVE RT-FRT TO RT-FRZ
               MOVE SPACE TO RT-CUR
               MOVE SPACE TO RT-REQ
               MOVE 0 TO RT-TTL.
           MOVE 0 TO WS-NOP.
       LEGAL.
      * WS-LEGAL = 1 WHEN THE CELL NEXT TO THE PLAYER IN WS-DIR IS OPEN.
           MOVE 0 TO WS-LEGAL.
           MOVE PLAYER-X TO M-X.
           MOVE PLAYER-Y TO M-Y.
           IF WS-DIR = 'U'
               SUBTRACT 1 FROM M-Y
           ELSE IF WS-DIR = 'D'
               ADD 1 TO M-Y
           ELSE IF WS-DIR = 'L'
               SUBTRACT 1 FROM M-X
           ELSE IF WS-DIR = 'R'
               ADD 1 TO M-X
           ELSE
               GO TO LEGAL-EXIT.
           MOVE 'WALL' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 0
               MOVE 1 TO WS-LEGAL.
       LEGAL-EXIT.
           EXIT.
       ARC-QUANTUM.
           MOVE 'ATIK' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ PAC-ARC.
           MOVE 'RQ  ' TO REQ-OP.
           MOVE 0 TO ARC-MOVEF.
           IF ARC-FR = 0
               GO TO ARC-QUANTUM-EXIT.
           ADD ARC-KFINC TO ARC-FACC.
           IF ARC-FACC NOT < GH-DEN
               SUBTRACT GH-DEN FROM ARC-FACC
               MOVE 1 TO ARC-MOVEF.
       ARC-QUANTUM-EXIT.
           EXIT.
       PUBLISH.
           MOVE RT-Q TO REQ-RTQ.
           MOVE RT-CUR TO REQ-RTCUR.
           MOVE RT-REQ TO REQ-RTREQ.
           MOVE RT-TTL TO REQ-RTTTL.
           MOVE RT-VIS TO REQ-VIS.
           MOVE RT-FRZ TO REQ-RTFRZ.
           MOVE RT-FRT TO REQ-RTFRT.
           MOVE RT-RDY TO REQ-RTRDY.
           MOVE RT-PUQ TO REQ-RTPUQ.
           MOVE 'RUN ' TO REQ-RTSTAT.
           IF RT-FRZ > 0
               MOVE 'FRZ ' TO REQ-RTSTAT.
           IF RT-PAUSE = 1
               MOVE 'PAUS' TO REQ-RTSTAT.
           IF RT-START = 0
               MOVE 'WAIT' TO REQ-RTSTAT.
           MOVE 0 TO WS-NOP.
       RT-CONV.
      * MVS-RP RP.3 (D39 6), THE ONE QUANTUM CONVERSION (THE SAME
      * PARAGRAPH AS PACGAME): WS-CQ QUANTA OF 150 MS -> THE SAME LENGTH
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
ZZ
//COB10    EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ10,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.R20.COBOL(PACRT),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.R20.COPY,DISP=SHR
//ASM1     EXEC PGM=IFOX00,COND=(0,NE),PARM='OBJECT,NODECK,NOXREF'
//SYSLIB   DD DSN=SYS1.MACLIB,DISP=SHR
//         DD DSN=SYS1.AMODGEN,DISP=SHR
//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSUT2   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSUT3   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSPRINT DD SYSOUT=A
//SYSGO    DD DSN=&&OBJA1,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DATA,DLM=ZZ
*        PACTSO : TSO LINE-MODE SCREEN SERVICE FOR PACPLAT (MVS-8).
*        CALL 'PACTSO' USING OP RC [MS]
*          OP X(4)  'CLS ' = NEXT LINE-MODE OUTPUT STARTS AT LINE 1
*                   OF A FRESH SCREEN (STLINENO LINE=1), SO A FRAME
*                   NEVER OVERFLOWS INTO THE TSO '***' PAGING PROMPT.
*                   'WAIT' = PAUSE 3 SECONDS (STIMER), NO TERMINAL
*                   I/O AT ALL (MVS-GS: THE FINAL SCALED SCREEN STAYS
*                   VISIBLE BEFORE THE LINE-MODE END LINES).
*                   MVS-RT (D33, PROBE E14): 'TIME' = MS := MILLI-
*                   SECONDS SINCE THE FIRST TIME CALL (STCK); 'DLWT' =
*                   WAIT UNTIL THE ABSOLUTE DEADLINE MS (STIMER WAIT,
*                   MICVL FOR THE REMAINDER ONLY), RC 4 IF ALREADY
*                   PASSED. MS S9(9) COMP. BOTH WORK IN ANY ADDRESS
*                   SPACE (BATCH TOO).
*          RC S9(4) COMP  0 = DONE, 4 = NOT A TSO FOREGROUND SESSION
*                   (BATCH: NOTHING IS ISSUED), 8 = UNKNOWN OP.
*        ONLY PACPLAT MAY CALL THIS MODULE.
PACTSO   CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,3,0(1)
         LA    3,0(3)
         LA    4,8
         CLC   0(4,2),=C'TIME'
         BE    DOTIME
         CLC   0(4,2),=C'DLWT'
         BE    DODLWT
         CLC   0(4,2),=C'CLS '
         BE    KNOWN
         CLC   0(4,2),=C'WAIT'
         BNE   DONE
KNOWN    DS    0H
         LA    4,4
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         CLC   0(4,2),=C'WAIT'
         BE    PAUSE
         STLINENO LINE=1
         LR    4,15
         B     DONE
PAUSE    DS    0H
         STIMER WAIT,BINTVL=WAITT
         SR    4,4
         B     DONE                MVS-S1: NEVER FALL INTO DOTIME
DOTIME   DS    0H
         L     5,8(1)              THIRD PARAMETER: MS
         LA    5,0(5)
         BAL   14,NOWMS
         ST    1,0(5)
         SR    4,4
         B     DONE
DODLWT   DS    0H
         L     5,8(1)
         LA    5,0(5)
         BAL   14,NOWMS
         L     0,0(5)              DEADLINE (MS)
         SR    0,1                 REMAINDER = DEADLINE - NOW
         BNP   LATE
         LR    1,0                 THE REMAINDER INTO R1 (M USES R1)
         M     0,=F'1000'          MS -> US IN R0/R1
         SLDL  0,12                US -> TOD UNITS (BIT 51 = 1 US)
         STM   0,1,MICDW
         STIMER WAIT,MICVL=MICDW
         SR    4,4
         B     DONE
LATE     DS    0H
         LA    4,4
         B     DONE
DONE     DS    0H
         STH   4,0(3)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
*        NOWMS: R1 := MILLISECONDS SINCE T0 (T0 = THE FIRST CALL).
*        64-BIT TOD DIFFERENCE, >> 12 = US, / 1000. USES R0, R1, R15;
*        FETCH THE PARAMETERS BEFORE THE CALL (R1 IS OVERWRITTEN).
NOWMS    DS    0H
         STCK  NOW
         CLI   T0SET,1
         BE    HAVET0
         MVC   T0,NOW
         MVI   T0SET,1
HAVET0   DS    0H
         LM    0,1,NOW
         SL    1,T0+4
         BC    3,NOBORROW          CC 2/3: NO BORROW
         BCTR  0,0
NOBORROW DS    0H
         SL    0,T0
         SRDL  0,12                US IN R0/R1
         D     0,=F'1000'          MS IN R1 (REMAINDER IN R0)
         BR    14
SAVE     DC    18F'0'
         DS    0D
T0       DC    D'0'
NOW      DC    D'0'
MICDW    DC    D'0'
T0SET    DC    X'00'
WAITT    DC    F'300'              3 SECONDS (UNITS OF 0.01 S)
         LTORG
         END
ZZ
//ASM2     EXEC PGM=IFOX00,COND=(0,NE),PARM='OBJECT,NODECK,NOXREF'
//SYSLIB   DD DSN=SYS1.MACLIB,DISP=SHR
//         DD DSN=SYS1.AMODGEN,DISP=SHR
//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSUT2   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSUT3   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSPRINT DD SYSOUT=A
//SYSGO    DD DSN=&&OBJA2,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DATA,DLM=ZZ
*        PACFSIO : TSO FULL-SCREEN SERVICE FOR PACPLAT (MVS-G1, TSC).
*        PROTOCOL VALIDATED BY PROBES E2-E5 (DOCS/EVIDENCE/G1-*).
*        CALL 'PACFSIO' USING OP BUF LEN RC
*          OP  X(4)  FSON  TCLEARQ, STFSMODE ON, STTMPMD ON, ESTAE
*                    QRY   READ PARTITION QUERY (TPUT NOEDIT WSF),
*                          REPLY INTO BUF/LEN (TGET ASIS)
*                    SEND  TPUT FULLSCR OF BUF (LEN BYTES, STARTING
*                          WITH THE WCC) WITH A CLEAR-BUFFER PREFIX
*                          AFTER THE WCC: SBA(1,1) + REPEAT TO ADDRESS
*                          (1,1) WITH X'00' = WHOLE BUFFER NULLED.
*                          (ERASE/WRITE X'F5' SENT WITH TPUT NOEDIT
*                          LEFT THE SCREEN BLACK, JOB 159.)
*                    SENP  MVS-G3 PARTIAL SEND: X'F1' (WRITE, NO ERASE)
*                          + BUF (LEN BYTES, STARTING WITH THE WCC),
*                          TPUT NOEDIT (PROBE E6, VARIANT W)
*                    SENX  MVS-GS: TPUT NOEDIT OF BUF AS IT IS (LEN
*                          BYTES); ITS FIRST BYTE IS THE 3270 COMMAND
*                          CHOSEN BY PACPLAT: X'F5' ERASE/WRITE OR
*                          X'7E' ERASE/WRITE ALTERNATE (PROBE E12)
*                    RECV  TGET ASIS INTO BUF (RETRY EMPTY READS)
*                    RECT  ONE TGET ASIS,NOWAIT (R15: 0 INPUT, 4 NONE,
*                          ELSE ERROR); NONE = WAIT 0.5 S, LEN 0, RC 0
*                          (VISUAL TICK FOR THE CALLER)
*                    POLL  MVS-RT: ONE TGET ASIS,NOWAIT INTO BUF, NO
*                          WAIT: INPUT = LEN > 0, NONE = LEN 0, RC 0
*                          (PROBE E14, DOCS/EVIDENCE/RT-E14-TIMING.MD)
*                    FSOF  ESTAE CANCEL, STTMPMD OFF, STFSMODE OFF,
*                          STLINENO LINE=1 (LINE MODE RESTORED)
*          BUF X(2048)   LEN S9(4) COMP   RC S9(4) COMP
*          RC: 0 OK, 4 NOT A TSO SESSION (NOTHING ISSUED), 8 UNKNOWN
*              OP OR NO INPUT, ELSE THE TPUT/TGET RETURN CODE.
*        ABEND SAFETY: FSON ESTABLISHES AN ESTAE EXIT THAT RESTORES
*        LINE MODE (STTMPMD/STFSMODE OFF, STLINENO 1) AND PERCOLATES.
*        ONLY PACPLAT MAY CALL THIS MODULE.
PACFSIO  CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,5,0(1)
         LA    3,0(3)
         LA    4,0(4)
         LA    5,0(5)
         LA    6,4
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         LA    6,8
         CLC   0(4,2),=C'FSON'
         BE    DOFSON
         CLC   0(4,2),=C'QRY '
         BE    DOQRY
         CLC   0(4,2),=C'SEND'
         BE    DOSEND
         CLC   0(4,2),=C'RECV'
         BE    DORECV
         CLC   0(4,2),=C'FSOF'
         BE    DOFSOF
         CLC   0(4,2),=C'SENP'
         BE    DOSENP
         CLC   0(4,2),=C'RECT'
         BE    DORECT
         CLC   0(4,2),=C'SENX'
         BE    DOSENX
         CLC   0(4,2),=C'POLL'
         BE    DOPOLL
         B     DONE
DOFSON   DS    0H
         TCLEARQ OUTPUT
         TCLEARQ INPUT
         STFSMODE ON,INITIAL=YES
         STTMPMD ON
         ESTAE ABEXIT,CT
         LR    6,15
         B     DONE
DOQRY    DS    0H
         LA    1,QUERY
         LA    0,QUERYL
         TPUT  (1),(0),NOEDIT
         LR    6,15
         LTR   15,15
         BNZ   DONE
         B     DORECV
DOSEND   DS    0H
         MVC   SENDBUF(1),0(3)     THE WCC FROM THE CALLER
         MVC   SENDBUF+1(7),CLRPFX SBA(1,1) + RA TO (1,1) WITH NULLS
         LA    8,SENDBUF+8
         LH    9,0(4)
         BCTR  9,0                 REST OF THE STREAM AFTER THE WCC
         LA    10,1(3)
         LR    11,9
         MVCL  8,10
         LA    1,SENDBUF
         LH    0,0(4)
         AH    0,=H'7'             + CLEAR PREFIX (NOT LA 0,7(0): R0 AS
*                                  BASE MEANS ZERO - JOBS 159/160 BUG)
         TPUT  (1),(0),FULLSCR
         LR    6,15
         B     DONE
DOSENP   DS    0H
         MVI   SENDBUF,X'F1'       3270 COMMAND WRITE (NO ERASE)
         LA    8,SENDBUF+1
         LH    9,0(4)
         LR    10,3
         LR    11,9
         MVCL  8,10
         LA    1,SENDBUF
         LH    0,0(4)
         AH    0,=H'1'
         TPUT  (1),(0),NOEDIT
         LR    6,15
         B     DONE
DOSENX   DS    0H
         LR    1,3
         LH    0,0(4)              LENGTH FROM THE CALLER (NEVER LA)
         TPUT  (1),(0),NOEDIT
         LR    6,15
         B     DONE
DORECT   DS    0H
         LR    1,3
         LA    0,2048
         TGET  (1),(0),ASIS,NOWAIT
         LR    6,15
         LTR   15,15
         BZ    RECTGOT             RC 0: INPUT, LENGTH IN R1
         C     15,=F'4'
         BNE   RECTERR             OTHER RC: ERROR (R1 UNDEFINED)
         SR    1,1                 RC 4: NO INPUT, R1 NOT USED
         STH   1,0(4)
         STIMER WAIT,BINTVL=HALFSEC
         SR    6,6
         B     DONE
DOPOLL   DS    0H
         LR    1,3
         LA    0,2048
         TGET  (1),(0),ASIS,NOWAIT
         LR    6,15
         LTR   15,15
         BZ    RECTGOT             RC 0: INPUT, LENGTH IN R1
         C     15,=F'4'
         BNE   RECTERR             OTHER RC: ERROR (R1 UNDEFINED)
         SR    1,1                 RC 4: NO INPUT, R1 NOT USED
         STH   1,0(4)
         SR    6,6
         B     DONE
RECTGOT  DS    0H
         STH   1,0(4)
         B     DONE
RECTERR  DS    0H
         SR    1,1
         STH   1,0(4)
         B     DONE
DORECV   DS    0H
         SR    7,7                 EMPTY-READ COUNTER
RECVLOOP DS    0H
         LR    1,3
         LA    0,2048
         TGET  (1),(0),ASIS
         LR    6,15
         STH   1,0(4)
         LTR   1,1
         BNZ   DONE
         LA    7,1(7)
         C     7,=F'600'
         BNL   NOINPUT
         STIMER WAIT,BINTVL=HALFSEC
         B     RECVLOOP
NOINPUT  DS    0H
         LA    6,8
         B     DONE
DOFSOF   DS    0H
         ESTAE 0
         BAL   14,RESTORE
         SR    6,6
DONE     DS    0H
         STH   6,0(5)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
*        RESTORE LINE MODE (USED BY FSOF AND BY THE ESTAE EXIT).
RESTORE  DS    0H
         ST    14,RESTR14
         STTMPMD OFF
         STFSMODE OFF
         STLINENO LINE=1
         L     14,RESTR14
         BR    14
*        ESTAE EXIT: R15 = ENTRY POINT. REBUILD THE MAIN BASE IN R12,
*        RESTORE LINE MODE, PERCOLATE (R15 = 0, SDWA LEFT UNCHANGED).
ABEXIT   DS    0H
         USING ABEXIT,15
         LR    9,14
         LR    12,15
         S     12,ABOFF
         DROP  15
         BAL   14,RESTORE
         LR    14,9
         SR    15,15
         BR    14
ABOFF    DC    A(ABEXIT-PACFSIO-6)
SAVE     DC    18F'0'
RESTR14  DC    F'0'
HALFSEC  DC    F'50'
SENDBUF  DS    CL2060
CLRPFX   DC    X'114040',X'3C404000'
*        READ PARTITION QUERY: WSF X'F3', LENGTH 5, X'01', PID X'FF',
*        X'02' QUERY (VALIDATED BY PROBE E5).
QUERY    DC    X'F3000501FF02'
QUERYL   EQU   *-QUERY
         LTORG
         END
ZZ
//ASM3     EXEC PGM=IFOX00,COND=(0,NE),PARM='OBJECT,NODECK,NOXREF'
//SYSLIB   DD DSN=SYS1.MACLIB,DISP=SHR
//         DD DSN=SYS1.AMODGEN,DISP=SHR
//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSUT2   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSUT3   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSPRINT DD SYSOUT=A
//SYSGO    DD DSN=&&OBJA3,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DATA,DLM=ZZ
*        PACHSIO : MVS-HS (D38) HIGH-SCORE RECORD SERVICE FOR PACPLAT.
*        ONE 80-BYTE RECORD IN THE PDS MEMBER NAMED ON A DD. PRODUCTION
*        FORM OF THE PROBE E16 SERVICE PACHSA (DOCS/EVIDENCE/
*        HS-E16-PROBE.MD, JOBS 254 AND 258). NEVER ABENDS THE CALLER.
*        CALL 'PACHSIO' USING OP RC DDN REC
*          OP  X(4)  'READ' = THE FIRST RECORD OF THE MEMBER INTO REC.
*                    'WRIT' = REC REPLACES THE FIRST RECORD IN PLACE
*                    (QSAM UPDAT, GET + PUTX: SAME BLOCK, NO NEW
*                    SPACE). A MISSING OR EMPTY MEMBER: AS REPL.
*                    'REPL' = THE MEMBER BECOMES THE ONE RECORD REC
*                    (QSAM OUTPUT: ADDED OR REPLACED BY STOW AT CLOSE).
*                    THE MEMBER IS LOOKED UP BY BPAM BLDL WITH THE PDS
*                    OPENED WITHOUT IT (TYPE=J, JFCNWRIT), SO NO OPEN
*                    EVER MEETS A MISSING MEMBER (013-18); BEFORE EVERY
*                    QSAM OPEN A FRESH RDJFCB MUST STILL SHOW THE SAME
*                    MEMBER (NEVER THE WHOLE PDS AS A SEQUENTIAL FILE).
*                    THE I/O RUNS UNDER AN ESTAE: ANY ABEND (X37, B14,
*                    913, 013 ...) RETRIES INTO THE RETURN PATH, RC 16;
*                    THE ESTAE IS DELETED BEFORE EVERY RETURN.
*          RC  S9(4) COMP  0 DONE, 2 MEMBER WRITTEN NEW (ADDED OR
*                    REPLACED), 4 NO SUCH DD, 8 UNUSABLE (DUMMY, NO
*                    MEMBER ON THE DD, NOT RECFM F(B) LRECL 80 BLKSIZE
*                    80), 12 MEMBER MISSING OR EMPTY (READ), 16 I/O
*                    ERROR OR ABEND CAUGHT, 20 BAD OP.
*          DDN X(8)  DD NAME.  REC X(80).
*        ONLY PACPLAT MAY CALL THIS MODULE.
PACHSIO  CSECT
         STM   14,12,12(13)
         BALR  12,0
BASE     DS    0H
         USING BASE,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,5,0(1)            OP RC DDN REC
         LA    5,0(5)
         ST    3,ARC
         ST    5,AREC
         LA    4,0(4)
         MVC   DDN,0(4)
         MVI   ESTON,0
         MVI   RETRIED,0
         MVC   OP,0(2)
         LA    9,20
         CLC   OP,=C'READ'
         BE    OPOK
         CLC   OP,=C'REPL'
         BE    OPOK
         CLC   OP,=C'WRIT'
         BNE   RETURN
OPOK     DS    0H
         ST    12,MYBASE
         ESTAE ESTEXIT,CT
         LTR   15,15
         BNZ   NOGUARD
         MVI   ESTON,1
NOGUARD  DS    0H
         LA    9,4
         DEVTYPE DDN,DVAREA
         LTR   15,15
         BNZ   RETURN
         LA    9,8
         LA    7,PODCB
         BAL   14,DCBRESET
         RDJFCB (PODCB)
         LTR   15,15
         BNZ   RETURN
         TM    JFCB+X'56',X'01'    JFCBIND1 JFCPDS: MEMBER NAMED
         BZ    RETURN
         MVC   BLDLN,JFCB+X'2C'    JFCBELNM
*        E16 JOB 249: OPEN SEARCHES A MEMBER NAMED ON THE DD EVEN FOR
*        BPAM (013-18 IF MISSING). THE MEMBER IS REMOVED FROM THE JFCB
*        COPY AND THE PDS OPENED WITH IT (TYPE=J); BLDL FINDS IT.
*        E16 JOB 251: WITHOUT JFCNWRIT THE CHANGED JFCB WAS WRITTEN
*        BACK (THE NEXT CALL SAW NO MEMBER): JFCBTSDM X'08' SET.
         MVC   JFCB+X'2C'(8),=CL8' '
         NI    JFCB+X'56',X'FE'
         OI    JFCB+X'34',X'08'    JFCBTSDM JFCNWRIT
         MVI   IOERR,0
         OPEN  (PODCB,(INPUT)),TYPE=J
         TM    PODCB+48,X'10'      DCBOFLGS OPEN OK
         BZ    RETURN
         LA    9,8
         CLC   PODCB+82(2),=H'80'  DCBLRECL
         BNE   CLOSEP
         CLC   PODCB+62(2),=H'80'  DCBBLKSI
         BNE   CLOSEP
         TM    PODCB+36,X'80'      DCBRECFM F
         BZ    CLOSEP
         TM    PODCB+36,X'40'      NOT V/U
         BO    CLOSEP
         BLDL  PODCB,BLDLL
         LA    9,16
         CH    15,=H'4'
         BH    CLOSEP
         BE    NOMEM
         CLC   OP,=C'WRIT'
         BE    UPDATE
         CLC   OP,=C'REPL'
         BE    REPLC
         MVI   BLDLK,0             CONCATENATION 0
         FIND  PODCB,BLDLTTR,C
         READ  DECB1,SF,PODCB,BUF,'S'
         CHECK DECB1
         LA    9,16
         CLI   IOERR,0
         BNE   CLOSEP
         SR    9,9
         L     5,AREC
         MVC   0(80,5),BUF
         B     CLOSEP
EOM      DS    0H                  EODAD: NO RECORD IN THE MEMBER
         LA    9,12
         B     CLOSEP
*        E16 JOB 252: BPAM UPDAT + WRITE (MF=E) ABENDED S800; THE
*        REWRITE IS QSAM UPDAT ON THE MEMBER NAMED ON THE DD, WHICH
*        BLDL HAS JUST FOUND.
UPDATE   DS    0H
         CLOSE (PODCB)
         LA    7,QUDCB
         BAL   14,SAMEMEM
         LTR   9,9
         BNZ   RETURN
         OPEN  (QUDCB,(UPDAT))
         LA    9,8
         TM    QUDCB+48,X'10'
         BZ    RETURN
         GET   QUDCB
         L     5,AREC
         MVC   0(80,1),0(5)
         PUTX  QUDCB
         SR    9,9
         CLI   IOERR,0
         BE    CLOSEQ
         LA    9,16
         B     CLOSEQ
QEOM     DS    0H                  EODAD: EMPTY MEMBER -> REPLACE
         CLOSE (QUDCB)
         B     REPLACE
CLOSEQ   DS    0H
         CLOSE (QUDCB)
         B     RETURN
NOMEM    DS    0H
         LA    9,12
         CLC   OP,=C'READ'
         BE    CLOSEP
REPLC    DS    0H
         CLOSE (PODCB)
REPLACE  DS    0H
         LA    7,PSDCB
         BAL   14,SAMEMEM
         LTR   9,9
         BNZ   RETURN
         OPEN  (PSDCB,(OUTPUT))
         LA    9,8
         TM    PSDCB+48,X'10'
         BZ    RETURN
         L     5,AREC
         PUT   PSDCB,(5)
         CLOSE (PSDCB)
         LA    9,2
         B     RETURN
CLOSEP   DS    0H
         CLOSE (PODCB)
RETURN   DS    0H
*        E16B JOB 257: AFTER A RETRY THE EXIT IS STILL ON THE CHAIN
*        (TWO LATER ESTAE 0 BOTH RC 0): DELETED IN BOTH CASES.
         CLI   ESTON,1
         BNE   NOESTAE
         ESTAE 0
NOESTAE  DS    0H
         L     3,ARC
         STH   9,0(3)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
*        SAMEMEM: R7 = A CLOSED QSAM DCB, RESET FOR THE DD. R9 := 0 IF
*        THE DD STILL NAMES THE MEMBER BLDL LOOKED FOR, ELSE 8. SAFETY:
*        A QSAM OPEN OF THE DD WITHOUT ITS MEMBER WOULD OVERWRITE (OR
*        READ) THE WHOLE PDS AS A SEQUENTIAL DATASET.
SAMEMEM  DS    0H
         ST    14,SAVE14
         BAL   14,DCBRESET
         LA    9,8
         RDJFCB ((7))
         LTR   15,15
         BNZ   SAMEX
         TM    JFCB+X'56',X'01'
         BZ    SAMEX
         CLC   BLDLN,JFCB+X'2C'
         BNE   SAMEX
         SR    9,9
SAMEX    DS    0H
         L     14,SAVE14
         BR    14
*        DCBRESET: R7 = A CLOSED DCB. NEW DD NAME; RECFM, BLKSIZE
*        AND LRECL CLEARED: THE NEXT OPEN MERGES THEM FROM THE DSCB.
DCBRESET DS    0H
         MVC   40(8,7),DDN         DCBDDNAM
         MVI   36(7),0             DCBRECFM
         XC    62(2,7),62(7)       DCBBLKSI
         XC    82(2,7),82(7)       DCBLRECL
         BR    14
*        RETRY ROUTINE (FROM ESTEXIT): REBUILD THE BASE, OWN SAVE AREA,
*        RC 16. NO DCB IS TOUCHED AGAIN.
         DROP  12
RETRY    DS    0H
         BALR  11,0
         USING *,11
         L     12,MYBASE
         DROP  11
         USING BASE,12
         LA    13,SAVE
         MVI   RETRIED,1
         LA    9,16
         B     RETURN
         DROP  12
*        ESTAE EXIT: R15 = ENTRY. NO SDWA (R0 = 12): R0 = RETRY,
*        R15 = 4.
*        WITH SDWA: SETRP RETRY, NO DUMP.
ESTEXIT  DS    0H
         USING ESTEXIT,15
         C     0,=F'12'
         BE    NOSDWA
         USING SDWA,1
         L     2,=A(RETRY)
         SETRP RC=4,RETADDR=(2),FRESDWA=YES,DUMP=NO
         DROP  1
         BR    14
NOSDWA   DS    0H
         L     0,=A(RETRY)
         LA    15,4
         BR    14
         DROP  15
         USING BASE,12
IOX      DS    0H                  SYNAD: FLAG, BACK TO CHECK
         MVI   IOERR,1
         BR    14
SAVE     DC    18F'0'
ARC      DC    A(0)
SAVE14   DC    A(0)
AREC     DC    A(0)
DVAREA   DC    2F'0'
DDN      DC    CL8' '
OP       DC    CL4' '
IOERR    DC    X'00'
ESTON    DC    X'00'
RETRIED  DC    X'00'
MYBASE   DC    A(0)
         DS    0F
JX       DC    X'87',AL3(JFCB)
JFCB     DS    CL176
BLDLL    DC    H'1',H'58'
BLDLN    DC    CL8' '
BLDLTTR  DC    XL3'00'
BLDLK    DC    X'00'
BLDLREST DC    XL46'00'
BUF      DS    CL80
PODCB    DCB   DSORG=PO,MACRF=R,EXLST=JX,SYNAD=IOX,EODAD=EOM
PSDCB    DCB   DSORG=PS,MACRF=PM,EXLST=JX
QUDCB    DCB   DSORG=PS,MACRF=(GL,PM),EXLST=JX,SYNAD=IOX,EODAD=QEOM
         LTORG
         IHASDWA
         END
ZZ
//LINK     EXEC PGM=IEWL,COND=(0,NE),PARM='LIST,XREF'
//SYSLIN   DD DSN=&&OBJ1,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ2,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ3,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ4,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ5,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ6,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ7,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ8,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ9,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ10,DISP=(OLD,DELETE)
//         DD DSN=&&OBJA1,DISP=(OLD,DELETE)
//         DD DSN=&&OBJA2,DISP=(OLD,DELETE)
//         DD DSN=&&OBJA3,DISP=(OLD,DELETE)
//         DD DDNAME=SYSIN
//SYSLMOD  DD DSN=HERC01.PACMAN.R20.LOAD(PACMAIN),DISP=OLD
//SYSLIB   DD DSN=SYS1.COBLIB,DISP=SHR
//SYSUT1   DD UNIT=SYSDA,SPACE=(1024,(50,20))
//SYSPRINT DD SYSOUT=A
//SYSIN    DD *
 ENTRY PACMAIN
/*
//RUN1     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
R
R
U
L
L
L
D
D
R
X
r
R
R
D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN2     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
L
R
L
R
U
L
L
R
L
D
R
U
U
R
D
L
U
D
R
U
R
L
D
R
U
D
R
L
D
L
L
R
R
U
U
D
L
L
L
L
U
R
L
L
D
U
U
L
R
U
D
U
R
R
R
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN3     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
U
R
U
U
D
U
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN4     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI0
D
D
D
D
D
D
D
R
U
R
D
R
U
U
U
U
U
U
U
L
L
R
R
R
R
R
R
D
D
L
L
D
D
R
R
D
D
D
L
U
L
D
L
U
D
R
U
R
D
R
R
U
R
D
R
U
U
U
R
R
U
U
L
L
U
U
R
R
R
R
D
D
D
D
D
D
D
L
U
L
D
L
U
D
R
U
R
D
R
R
U
R
D
U
R
U
U
U
U
U
U
L
L
R
R
D
D
L
L
R
R
D
D
L
L
R
R
D
D
L
L
D
L
U
U
U
U
U
L
R
U
U
L
L
L
L
D
D
L
L
R
R
R
R
D
D
L
L
D
D
D
L
U
L
D
L
U
U
U
L
L
U
U
L
R
R
R
U
U
L
L
L
L
D
D
L
L
R
R
D
D
L
L
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN5     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI0
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
L
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN6     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI0
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN7     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI0
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN8     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI0
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
D
D
D
D
D
R
U
R
D
R
U
U
U
U
U
U
U
L
L
R
R
R
R
R
R
D
D
L
L
D
D
R
R
D
D
D
L
U
L
D
L
U
D
R
U
R
D
R
R
U
R
D
R
U
U
U
R
R
U
U
L
L
U
U
R
R
R
R
D
D
D
D
D
D
D
L
U
L
D
L
U
D
R
U
R
D
R
R
U
R
D
U
R
U
U
U
U
U
U
L
L
R
R
D
D
L
L
R
R
D
D
L
L
R
R
D
D
L
L
D
L
U
U
U
U
U
L
R
U
U
L
L
L
L
D
D
L
L
R
R
R
R
D
D
L
L
D
D
D
L
U
L
D
L
U
U
U
L
L
U
U
L
R
R
R
U
U
L
L
L
L
D
D
L
L
R
R
D
D
L
L
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN9     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
L
R
L
L
U
L
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
U
R
L
U
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN10    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
U
R
D
R
U
U
U
U
U
U
U
L
L
R
R
R
R
R
R
D
D
L
L
D
D
R
R
D
D
D
L
U
L
D
L
U
R
R
R
R
D
R
U
R
U
U
R
R
U
U
L
L
U
U
R
R
R
R
D
D
D
D
D
D
D
L
U
L
D
L
U
D
L
R
R
R
R
R
U
R
D
U
R
U
U
U
U
U
U
L
L
L
D
D
L
R
R
R
R
D
D
L
L
L
U
U
L
L
L
L
L
L
L
L
L
L
L
L
L
L
D
D
R
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN11    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
U
R
R
R
R
R
R
U
U
U
U
U
U
U
U
U
U
U
U
U
U
R
R
R
D
D
D
D
D
D
L
L
R
R
R
R
R
R
U
U
L
L
U
U
L
L
L
L
L
D
D
R
R
R
U
U
U
U
R
R
R
R
D
D
L
R
R
R
R
U
U
R
R
R
R
D
D
D
D
D
D
D
L
L
L
L
L
L
U
R
R
U
U
R
R
U
U
L
R
R
R
R
R
R
U
U
L
L
R
R
D
D
D
D
L
L
L
D
D
R
D
R
U
R
R
R
R
R
R
R
R
R
R
R
R
R
R
U
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN12    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
U
R
R
R
R
R
R
D
D
D
D
D
D
D
U
R
R
R
R
R
D
U
R
R
R
R
R
R
R
R
R
D
U
R
D
R
U
U
U
U
U
U
U
U
U
U
U
R
R
R
D
D
D
D
D
U
L
L
L
U
U
R
R
R
R
R
D
D
R
R
D
D
D
R
R
R
R
R
R
U
R
U
U
U
U
U
U
L
L
L
L
D
D
L
L
L
U
U
L
L
L
L
D
D
R
R
R
R
R
R
R
R
R
D
D
L
L
D
U
R
R
U
U
R
R
R
R
R
U
U
L
L
R
R
D
D
D
D
D
U
L
L
U
U
U
R
R
D
D
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN13    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI2
L
L
U
R
D
U
D
U
L
R
D
R
U
D
U
D
R
L
D
R
D
U
D
R
D
D
U
U
D
D
D
D
L
L
D
D
D
D
R
L
U
L
R
D
D
L
U
L
L
U
L
U
L
L
L
R
L
D
R
R
D
U
L
U
L
R
U
R
L
R
U
R
U
D
D
U
D
R
L
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN14    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI2 3
L
L
U
R
D
U
D
U
L
R
D
R
U
D
U
D
R
L
D
R
D
U
D
R
D
D
U
U
D
D
D
D
L
L
D
D
D
D
R
L
U
L
R
D
D
L
U
L
L
U
L
U
L
L
L
R
L
D
R
R
D
U
L
U
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN15    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI1 2
L
L
U
R
D
U
D
U
L
R
D
R
U
D
U
D
R
L
D
R
D
U
D
R
D
D
U
U
D
D
D
D
L
L
D
D
D
D
R
L
U
L
R
D
D
L
U
L
L
U
L
U
L
L
L
R
L
D
R
R
D
U
L
U
L
R
U
R
L
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN16    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI3
D
U
D
U
D
U
R
L
L
D
R
L
L
U
R
D
D
D
D
U
R
L
U
R
U
R
R
D
U
U
L
U
U
D
R
U
R
U
D
U
R
R
U
U
L
R
R
L
U
U
D
D
R
D
D
U
L
U
U
D
U
D
U
R
L
R
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN17    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI3
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN18    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI3 2
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN19    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
AI3 3
R
D
R
R
R
U
R
R
U
R
L
D
R
R
R
D
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO1     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO'
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
R
R
U
L
L
L
D
D
R
X
r
R
R
D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO2     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO AI0'
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO3     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO AI2'
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
L
L
U
R
D
U
D
U
L
R
D
R
U
D
U
D
R
L
D
R
D
U
D
R
D
D
U
U
D
D
D
D
L
L
D
D
D
D
R
L
U
L
R
D
D
L
U
L
L
U
L
U
L
L
L
R
L
D
R
R
D
U
L
U
L
R
U
R
L
R
U
R
U
D
D
U
D
R
L
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO4     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO AI3 3'
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
R
D
R
R
R
U
R
R
U
R
L
D
R
R
R
D
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO5     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO AI3 2'
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO6     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO'
//STEPLIB  DD DSN=HERC01.PACMAN.R20.LOAD,DISP=SHR
//SYSIN    DD *
R

D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//G8DEL0   EXEC PGM=IEFBR14,COND=(0,NE)
//D1       DD DSN=HERC01.PACMAN.R20.G8CL,DISP=(MOD,DELETE),
//            UNIT=SYSDA,SPACE=(TRK,(1))
//G8ALC    EXEC PGM=IEFBR14,COND=(0,NE)
//D1       DD DSN=HERC01.PACMAN.R20.G8CL,DISP=(NEW,CATLG),
//            UNIT=SYSDA,SPACE=(TRK,(2,1,2)),
//            DCB=(DSORG=PO,RECFM=FB,LRECL=80,BLKSIZE=80)
//G8CLS    EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSIN    DD DUMMY
//SYSUT2   DD DSN=HERC01.PACMAN.R20.G8CL(PARMS),DISP=OLD
//SYSUT1   DD DATA,DLM=ZZ
PROC 0 AI(1) GHOSTS(1) COLOR(AUTO) HILITE(AUTO) ANIM(AUTO) +
  REDRAW(PARTIAL) METRICS(NO) GLYPHS(AUTO) SCALE(AUTO) CANVAS(AUTO) +
  PLAY(REALTIME) SOUND(AUTO) RULES(ARCADE) LEVEL(1) SPEED(NORMAL) +
  ALARM(PATTERN)
SET &C = &SUBSTR(1:1,&COLOR)
SET &H = &SUBSTR(1:1,&HILITE)
SET &A = &SUBSTR(1:1,&ANIM)
SET &R = &SUBSTR(1:1,&REDRAW)
SET &G = &SUBSTR(1:1,&GLYPHS)
SET &S = &SUBSTR(1:1,&SCALE)
SET &V = &SUBSTR(1:1,&CANVAS)
SET &Y = &SUBSTR(1:1,&PLAY)
SET &U = &SUBSTR(1:1,&SOUND)
SET &W = &SUBSTR(1:1,&RULES)
SET &F = &SUBSTR(1:1,&SPEED)
SET &K = &SUBSTR(1:1,&ALARM)
/* LEVEL ZERO-PADDED TO 2 DIGITS: SPEED IS PARM COLUMN 24, ALARM 25.*/
SET &L = &STR(&LEVEL)
IF &LENGTH(&STR(&L)) = 1 THEN SET &L = &STR(0&L)
IF &LENGTH(&STR(&L)) NE 2 THEN SET &L = &STR(01)
SET &M = N
IF &METRICS = YES THEN SET &M = M
/* A FAILED ALLOC WOULD END THE CLIST (PROBE E16): CHECK FIRST.    */
/* THE PARM IS BUILT FIRST: A CLIST LINE ENDS AT COLUMN 72.        */
SET &P = &STR(TSO AI&AI &GHOSTS &M&C&H&A&R&G&S&V&Y&U&W&L&F&K)
WRITE G8PARM=&P=
ZZ
//G8CLT    EXEC PGM=IKJEFT01,COND=(0,NE)
//SYSTSPRT DD SYSOUT=A
//SYSTSIN  DD *
  EXEC 'HERC01.PACMAN.R20.G8CL(PARMS)'
  EXEC 'HERC01.PACMAN.R20.G8CL(PARMS)' 'RULES(CLASSIC)'
  EXEC 'HERC01.PACMAN.R20.G8CL(PARMS)' +
  'RULES(ARCADE) SPEED(FAST) ALARM(SINGLE)'
  EXEC 'HERC01.PACMAN.R20.G8CL(PARMS)' 'PLAY(TURN) RULES(XYZ) LEVEL(5)'
/*
//G8DEL9   EXEC PGM=IEFBR14,COND=EVEN
//D1       DD DSN=HERC01.PACMAN.R20.G8CL,DISP=(OLD,DELETE)
//
