      * PACG1P : MVS-G1 3270 CAPABILITY PROBE (NOT PART OF THE GAME).
      * RUN IN TSO WITH SYSOUT ALLOCATED TO THE TERMINAL (CLIST
      * G1PROBE). 1) READ PARTITION QUERY: PRINTS THE REPLY IN HEX,
      * THE QUERY CODES FOUND AND THE USABLE AREA. 2) COLOUR AND
      * HIGHLIGHT TEST SCREEN; PRESS ENTER TO RETURN. IN BATCH THE
      * SERVICE REPORTS RC 4 (NOT A TSO SESSION) AND NOTHING IS SENT.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACG1P.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  FS-OP                 PIC X(4).
       01  FS-BUF.
           05  FS-CH             PIC X OCCURS 1024 TIMES.
       01  FS-LEN                PIC S9(4) COMP.
       01  FS-RC                 PIC S9(4) COMP.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  OUT-LINE.
           05  OUT-CH            PIC X OCCURS 72 TIMES.
       01  WS-K                  PIC 9(4).
       01  WS-P                  PIC 9(4).
       01  WS-O                  PIC 99.
       01  WS-V                  PIC 9(4).
       01  WS-L                  PIC 9(4).
       01  WS-ID                 PIC 9(4).
       01  WS-QC                 PIC 9(4).
       01  WS-W                  PIC 9(4).
       01  WS-H                  PIC 9(4).
       01  WS-LIM                PIC 9(4).
       01  WS-Q                  PIC 99.
       01  WS-R                  PIC 99.
       01  WS-STOP               PIC 9.
       01  RC-LINE.
           05  FILLER            PIC X(8) VALUE 'G1 RC  ='.
           05  RL-RC             PIC 9(4).
           05  FILLER            PIC X(6) VALUE ' LEN ='.
           05  RL-LEN            PIC 9(4).
       01  AREA-LINE.
           05  FILLER            PIC X(18) VALUE 'G1 USABLE AREA W ='.
           05  AL-W              PIC 9(4).
           05  FILLER            PIC X(4) VALUE ' H ='.
           05  AL-H              PIC 9(4).
       PROCEDURE DIVISION.
       MAIN-PARA.
           DISPLAY 'G1 PROBE: READ PARTITION QUERY'.
           MOVE 'QRY ' TO FS-OP.
           PERFORM CALL-FS.
           IF FS-RC = 4
               DISPLAY 'G1 NOT A TSO SESSION: NOTHING SENT'
           ELSE
               PERFORM SHOW-QUERY THRU SHOW-QUERY-EXIT
               MOVE 'LINE' TO FS-OP
               PERFORM CALL-FS
               DISPLAY 'G1 PROBE: COLOUR DEMO (PRESS ENTER THERE)'
               MOVE 'DEMO' TO FS-OP
               PERFORM CALL-FS
               MOVE 'LINE' TO FS-OP
               PERFORM CALL-FS
               DISPLAY 'G1 DEMO RETURNED. AID AND DATA:'
               PERFORM SHOW-HEX THRU SHOW-HEX-EXIT.
           DISPLAY 'G1 PROBE END'.
           STOP RUN.
       CALL-FS.
           CALL 'PACFS' USING FS-OP FS-BUF FS-LEN FS-RC.
           MOVE FS-RC TO RL-RC.
           MOVE FS-LEN TO RL-LEN.
           DISPLAY RC-LINE.
       SHOW-QUERY.
           PERFORM SHOW-HEX THRU SHOW-HEX-EXIT.
           DISPLAY 'G1 QUERY CODES (X81 SUMMARY/AREA, 85 CHARSETS,'.
           DISPLAY 'G1  86 COLOUR, 87 HIGHLIGHT, 88 REPLY MODES):'.
           MOVE SPACES TO OUT-LINE.
           MOVE 0 TO WS-O.
           MOVE 0 TO WS-W.
           MOVE 0 TO WS-H.
           MOVE 2 TO WS-P.
           MOVE 0 TO WS-STOP.
           PERFORM NEXT-SF THRU NEXT-SF-EXIT
               UNTIL WS-STOP = 1.
           DISPLAY OUT-LINE.
           MOVE WS-W TO AL-W.
           MOVE WS-H TO AL-H.
           DISPLAY AREA-LINE.
       SHOW-QUERY-EXIT.
           EXIT.
       NEXT-SF.
           COMPUTE WS-LIM = WS-P + 3.
           IF WS-LIM > FS-LEN OR WS-O > 66
               MOVE 1 TO WS-STOP
               GO TO NEXT-SF-EXIT.
           MOVE WS-P TO WS-K.
           PERFORM BYTE-VAL.
           COMPUTE WS-L = WS-V * 256.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           ADD WS-V TO WS-L.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           MOVE WS-V TO WS-ID.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           MOVE WS-V TO WS-QC.
           IF WS-ID = 129
               PERFORM ADD-HEX
               ADD 1 TO WS-O.
           IF WS-ID = 129 AND WS-QC = 129
               PERFORM AREA-SIZE.
           IF WS-L < 4
               MOVE 1 TO WS-STOP
           ELSE
               ADD WS-L TO WS-P.
       NEXT-SF-EXIT.
           EXIT.
       AREA-SIZE.
           COMPUTE WS-K = WS-P + 6.
           PERFORM BYTE-VAL.
           COMPUTE WS-W = WS-V * 256.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           ADD WS-V TO WS-W.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           COMPUTE WS-H = WS-V * 256.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           ADD WS-V TO WS-H.
       BYTE-VAL.
           MOVE FS-CH (WS-K) TO HX-B.
           MOVE HEXN TO WS-V.
       ADD-HEX.
           DIVIDE WS-V BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-Q) TO OUT-CH (WS-O).
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-R) TO OUT-CH (WS-O).
       SHOW-HEX.
      * FIRST 128 BYTES OF FS-BUF, 32 PER LINE.
           MOVE FS-LEN TO WS-LIM.
           IF WS-LIM > 128
               MOVE 128 TO WS-LIM.
           MOVE 1 TO WS-K.
           PERFORM HEX-LINE UNTIL WS-K > WS-LIM.
       SHOW-HEX-EXIT.
           EXIT.
       HEX-LINE.
           MOVE SPACES TO OUT-LINE.
           MOVE 0 TO WS-O.
           PERFORM HEX-BYTE UNTIL WS-O > 62 OR WS-K > WS-LIM.
           DISPLAY OUT-LINE.
       HEX-BYTE.
           PERFORM BYTE-VAL.
           DIVIDE WS-V BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-Q) TO OUT-CH (WS-O).
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-R) TO OUT-CH (WS-O).
           ADD 1 TO WS-K.
