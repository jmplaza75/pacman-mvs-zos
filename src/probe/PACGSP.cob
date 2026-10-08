      * PACGSP : SCALED-RENDERER STUDY, PROBE E11 (SEE PACFSB).
      * ISOLATED FROM PACMAN. NOTHING IS PRINTED BEFORE THE
      * FULL-SCREEN PART. AFTERWARDS: LAST TPUT/TGET RC, SCREENS SENT
      * (PA2 REPLAYS INCLUDED), PARTIAL UPDATES SENT, LAST AID.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACGSP.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  P-RC                  PIC S9(4) COMP.
       01  P-NSCR                PIC S9(4) COMP.
       01  P-NPART               PIC S9(4) COMP.
       01  P-AID                 PIC X.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  WS-Q                  PIC 99.
       01  WS-R                  PIC 99.
       01  RES-LINE.
           05  FILLER            PIC X(7) VALUE 'GSP RC='.
           05  RS-RC             PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' SCRNS='.
           05  RS-NSCR           PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' PARTS='.
           05  RS-NPART          PIC 9(4).
           05  FILLER            PIC X(5) VALUE ' AID='.
           05  RS-AID1           PIC X.
           05  RS-AID2           PIC X.
       PROCEDURE DIVISION.
       MAIN-PARA.
           CALL 'PACFSB' USING P-RC P-NSCR P-NPART P-AID.
           MOVE P-RC TO RS-RC.
           MOVE P-NSCR TO RS-NSCR.
           MOVE P-NPART TO RS-NPART.
           MOVE P-AID TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           MOVE HEXDIG (WS-Q) TO RS-AID1.
           MOVE HEXDIG (WS-R) TO RS-AID2.
           DISPLAY RES-LINE.
           DISPLAY 'GSP PROBE END'.
           STOP RUN.
