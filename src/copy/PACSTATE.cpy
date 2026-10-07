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
