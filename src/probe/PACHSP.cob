      * PACHSP : MVS-HS PROBE E16 DRIVER (SEE PACHSA). ISOLATED FROM
      * PACMAN. DD PACHS. PARM = UP TO 8 SLOTS SEPARATED BY ',': R
      * (READ) OR W + 7-DIGIT VALUE (WRIT), E.G. 'R,W0001230,R'. ONE
      * LINE PER SLOT: OP, DD, RC, MEMBER TTR, RECORD.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACHSP.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  H-OP                  PIC X(4).
       01  H-RC                  PIC S9(4) COMP.
       01  H-DDN                 PIC X(8).
       01  H-REC.
           05  H-VAL             PIC X(7).
           05  H-TXT             PIC X(73).
       01  H-TTR.
           05  H-TB              PIC X OCCURS 3 TIMES.
       01  WS-N                  PIC 9.
       01  WS-I                  PIC 9.
       01  WS-J                  PIC 99.
       01  WS-Q                  PIC 99.
       01  WS-R                  PIC 99.
       01  WS-K1                 PIC 9.
       01  WS-K2                 PIC 9.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  RES-LINE.
           05  FILLER            PIC X(4) VALUE 'E16 '.
           05  RS-OP             PIC X(4).
           05  FILLER            PIC X VALUE ' '.
           05  RS-DDN            PIC X(8).
           05  FILLER            PIC X(4) VALUE ' RC='.
           05  RS-RC             PIC 99.
           05  FILLER            PIC X(5) VALUE ' TTR='.
           05  RS-HEX.
               10  RS-HX         PIC X OCCURS 6 TIMES.
           05  FILLER            PIC X(5) VALUE ' REC='.
           05  RS-REC            PIC X(40).
       LINKAGE SECTION.
       01  PARM-AREA.
           05  PARM-LEN          PIC S9(4) COMP.
           05  PARM-SLOT OCCURS 8 TIMES.
               10  PS-OP         PIC X.
               10  PS-VAL        PIC X(7).
               10  FILLER        PIC X.
       PROCEDURE DIVISION USING PARM-AREA.
       MAIN-PARA.
           COMPUTE WS-N = (PARM-LEN + 8) / 9.
           IF PARM-LEN > 71
               MOVE 8 TO WS-N.
           IF WS-N = 0
               DISPLAY 'E16 NO PARM'.
           PERFORM ONE-OP VARYING WS-I FROM 1 BY 1 UNTIL WS-I > WS-N.
           DISPLAY 'E16 PROBE END'.
           STOP RUN.
       ONE-OP.
           MOVE 'READ' TO H-OP.
           IF PS-OP (WS-I) = 'W'
               MOVE 'WRIT' TO H-OP.
           MOVE 'PACHS' TO H-DDN.
           MOVE ALL '?' TO H-REC.
           IF H-OP = 'WRIT'
               MOVE PS-VAL (WS-I) TO H-VAL
               MOVE ' E16 PROBE RECORD' TO H-TXT.
           MOVE 99 TO H-RC.
           CALL 'PACHSA' USING H-OP H-RC H-DDN H-REC H-TTR.
           MOVE H-OP TO RS-OP.
           MOVE H-DDN TO RS-DDN.
           MOVE H-RC TO RS-RC.
           MOVE H-REC TO RS-REC.
           MOVE 0 TO WS-J.
           PERFORM HEX-BYTE VARYING WS-Q FROM 1 BY 1 UNTIL WS-Q > 3.
           DISPLAY RES-LINE.
       HEX-BYTE.
           MOVE H-TB (WS-Q) TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-R REMAINDER WS-J.
           ADD 1 TO WS-R.
           ADD 1 TO WS-J.
           COMPUTE WS-K2 = WS-Q * 2.
           COMPUTE WS-K1 = WS-K2 - 1.
           MOVE HEXDIG (WS-R) TO RS-HX (WS-K1).
           MOVE HEXDIG (WS-J) TO RS-HX (WS-K2).
