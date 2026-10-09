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
