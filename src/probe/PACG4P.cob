      * PACG4P : MVS-G4 PROBE E9 (SEE PACFS9). NOTHING IS PRINTED
      * BEFORE THE FULL-SCREEN PART. AFTERWARDS: RC, QUERY REPLY
      * LENGTH, SCREENS SENT, FINAL AID, THEN THE WHOLE QUERY REPLY IN
      * HEX, 32 BYTES PER LINE (OFFSET FIRST), FOR THE X'85' DECODE.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACG4P.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  Q-BUF.
           05  Q-CH              PIC X OCCURS 1024 TIMES.
       01  Q-LEN                 PIC S9(4) COMP.
       01  P-RC                  PIC S9(4) COMP.
       01  P-AID                 PIC X.
       01  P-NSCR                PIC S9(4) COMP.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  WS-K                  PIC 9(4).
       01  WS-N                  PIC 9(4).
       01  WS-O                  PIC 99.
       01  WS-Q                  PIC 99.
       01  WS-R                  PIC 99.
       01  RES-LINE.
           05  FILLER            PIC X(7) VALUE 'G4P RC='.
           05  RS-RC             PIC 9(4).
           05  FILLER            PIC X(6) VALUE ' QLEN='.
           05  RS-QLEN           PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' SCRNS='.
           05  RS-NSCR           PIC 9(4).
           05  FILLER            PIC X(5) VALUE ' AID='.
           05  RS-AID            PIC X(2).
       01  HEX-LINE.
           05  FILLER            PIC X(4) VALUE 'G4Q '.
           05  HL-OFF            PIC 9(4).
           05  FILLER            PIC X VALUE ' '.
           05  HL-CH             PIC X OCCURS 64 TIMES.
       01  AID-HEX.
           05  AH-CH             PIC X OCCURS 2 TIMES.
       PROCEDURE DIVISION.
       MAIN-PARA.
           MOVE SPACES TO Q-BUF.
           CALL 'PACFS9' USING Q-BUF Q-LEN P-RC P-AID P-NSCR.
           MOVE P-RC TO RS-RC.
           MOVE Q-LEN TO RS-QLEN.
           MOVE P-NSCR TO RS-NSCR.
           MOVE P-AID TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           MOVE HEXDIG (WS-Q) TO AH-CH (1).
           MOVE HEXDIG (WS-R) TO AH-CH (2).
           MOVE AID-HEX TO RS-AID.
           DISPLAY RES-LINE.
           MOVE 1 TO WS-K.
           PERFORM HEX-ROW UNTIL WS-K > Q-LEN.
           DISPLAY 'G4P PROBE END'.
           STOP RUN.
       HEX-ROW.
           MOVE SPACES TO HEX-LINE.
           MOVE 'G4Q ' TO HEX-LINE.
           COMPUTE HL-OFF = WS-K - 1.
           MOVE 0 TO WS-O.
           MOVE 0 TO WS-N.
           PERFORM HEX-BYTE UNTIL WS-N = 32 OR WS-K > Q-LEN.
           DISPLAY HEX-LINE.
       HEX-BYTE.
           MOVE Q-CH (WS-K) TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-Q) TO HL-CH (WS-O).
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-R) TO HL-CH (WS-O).
           ADD 1 TO WS-K.
           ADD 1 TO WS-N.
