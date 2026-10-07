       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACMAIN.
       ENVIRONMENT DIVISION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
      * MVS-1: STATIC MAZE, 20 COLUMNS X 10 ROWS. KEEP IN SYNC WITH
      * MAPS/LEVEL1.TXT (CHECKED BY TESTS/TEST_MAP.PY).
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
       01  MAP-TABLE REDEFINES MAP-DATA.
           05  MAP-ROW           PIC X(20) OCCURS 10 TIMES.
       01  WS-ROW                PIC 99 VALUE 0.
       PROCEDURE DIVISION.
       MAIN-PARA.
           DISPLAY 'PACMAN MVS-1 STATIC MAP 20X10'.
           PERFORM SHOW-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
           DISPLAY 'END OF MAP'.
           STOP RUN.
       SHOW-ROW.
           DISPLAY MAP-ROW (WS-ROW).
