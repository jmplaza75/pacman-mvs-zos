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
