      * PACE7P : MVS-G3 PROBE E7 (SEE PACFS7). PARM = VARIANT A, N OR W.
      * NOTHING IS PRINTED BEFORE THE FULL-SCREEN PART. AFTERWARDS:
      * VARIANT, RC OF THE FIRST FULLSCR, RC OF THE LAST TICK, TICKS
      * SENT, PA2 SEEN, FULL SCREENS SENT, FINAL AID (HEX).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACE7P.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  P-VAR                 PIC X VALUE 'A'.
       01  P-RC1                 PIC S9(4) COMP.
       01  P-RC2                 PIC S9(4) COMP.
       01  P-NPART               PIC S9(4) COMP.
       01  P-NPA2                PIC S9(4) COMP.
       01  P-NSCR                PIC S9(4) COMP.
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
           05  FILLER            PIC X(8) VALUE 'G7P V=  '.
           05  RS-VAR            PIC X.
           05  FILLER            PIC X(5) VALUE ' RC1='.
           05  RS-RC1            PIC 9(4).
           05  FILLER            PIC X(5) VALUE ' RC2='.
           05  RS-RC2            PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' TICKS='.
           05  RS-NPART          PIC 9(4).
           05  FILLER            PIC X(5) VALUE ' PA2='.
           05  RS-NPA2           PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' SCRNS='.
           05  RS-NSCR           PIC 9(4).
           05  FILLER            PIC X(5) VALUE ' AID='.
           05  RS-AID.
               10  RS-AID1       PIC X.
               10  RS-AID2       PIC X.
       LINKAGE SECTION.
       01  PARM-AREA.
           05  PARM-LEN          PIC S9(4) COMP.
           05  PARM-VAR          PIC X.
       PROCEDURE DIVISION USING PARM-AREA.
       MAIN-PARA.
           IF PARM-LEN > 0
               MOVE PARM-VAR TO P-VAR.
           CALL 'PACFS7' USING P-VAR P-RC1 P-RC2 P-NPART P-NPA2
                               P-NSCR P-AID.
           MOVE P-VAR TO RS-VAR.
           MOVE P-RC1 TO RS-RC1.
           MOVE P-RC2 TO RS-RC2.
           MOVE P-NPART TO RS-NPART.
           MOVE P-NPA2 TO RS-NPA2.
           MOVE P-NSCR TO RS-NSCR.
           MOVE P-AID TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           MOVE HEXDIG (WS-Q) TO RS-AID1.
           MOVE HEXDIG (WS-R) TO RS-AID2.
           DISPLAY RES-LINE.
           DISPLAY 'G7P PROBE END'.
           STOP RUN.
