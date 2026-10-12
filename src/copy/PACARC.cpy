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
