      * MVS-GP1 (D36): ARCADE STATE, RULES(ARCADE) ONLY. NO VALUE
      * CLAUSES (USED IN LINKAGE TOO). OWNED BY PACMAIN, RESET BY
      * PACGAME RSET; CHANGED BY PACGAME AND PACAI (ARC-FACC AND THE
      * MOVE FLAGS ALSO BY PACRT). CLASSIC (ARC-ON = 0) NEVER USES IT.
      * ARC-GM: N NORMAL, F FRIGHTENED, E EYES (WAITING AT HOME).
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
