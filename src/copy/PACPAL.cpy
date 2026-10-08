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
           05  LAY-STATUS-ROW        PIC 99 VALUE 1.
           05  LAY-GHOSTS-ROW        PIC 99 VALUE 2.
           05  LAY-BOARD-ROW         PIC 99 VALUE 4.
           05  LAY-BOARD-COL         PIC 99 VALUE 31.
           05  LAY-MSG-ROW           PIC 99 VALUE 16.
           05  LAY-CMD-ROW           PIC 99 VALUE 18.
           05  LAY-HELP-ROW          PIC 99 VALUE 23.
