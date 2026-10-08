      * PACG1Q : MVS-G1 PROBE 2 (E2, SEE PACFS2). NOTHING IS PRINTED
      * BEFORE THE FULL-SCREEN PART (NO PENDING LINE OUTPUT). AFTERWARDS
      * PRINTS RC, LAST INBOUND LENGTH, SCREENS SENT, THE FIRST 8 BYTES
      * OF THE LAST INBOUND AND THE AID OF EVERY INBOUND (HEX).
      * PARM 'C' SELECTS THE E3 SCREEN (ONE SA COLOUR ORDER), 'K' THE
      * E4 SCREEN (SEVEN-COLOUR PALETTE), 'Q' THE E5 QUERY: THE REPLY
      * IS PRINTED IN HEX (96 BYTES) WITH ITS QUERY CODES AND AREA.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACG1Q.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  FS-BUF.
           05  FS-CH             PIC X OCCURS 1024 TIMES.
       01  FS-LEN                PIC S9(4) COMP.
       01  FS-RC                 PIC S9(4) COMP.
       01  FS-CNT                PIC S9(4) COMP.
       01  FS-SCR                PIC X.
       01  FS-LOG.
           05  LG-CH             PIC X OCCURS 8 TIMES.
       01  AID-LINE.
           05  FILLER            PIC X(9) VALUE 'G1Q AIDS='.
           05  AL-HEX            PIC X(16).
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  HEX-LINE.
           05  HX-CH             PIC X OCCURS 16 TIMES.
       01  WS-K                  PIC 9(4).
       01  WS-P                  PIC 9(4).
       01  WS-V                  PIC 9(4).
       01  WS-L                  PIC 9(4).
       01  WS-ID                 PIC 9(4).
       01  WS-QC                 PIC 9(4).
       01  WS-W                  PIC 9(4).
       01  WS-H                  PIC 9(4).
       01  WS-LIM                PIC 9(4).
       01  WS-STOP               PIC 9.
       01  QC-LINE.
           05  FILLER            PIC X(10) VALUE 'G1Q CODES='.
           05  QC-CH             PIC X OCCURS 60 TIMES.
       01  WIDE-LINE.
           05  FILLER            PIC X(4) VALUE 'G1Q '.
           05  WD-CH             PIC X OCCURS 64 TIMES.
       01  AREA-LINE.
           05  FILLER            PIC X(14) VALUE 'G1Q AREA W/H= '.
           05  AR-W              PIC 9(4).
           05  FILLER            PIC X VALUE '/'.
           05  AR-H              PIC 9(4).
       01  WS-O                  PIC 99.
       01  WS-Q                  PIC 99.
       01  WS-R                  PIC 99.
       01  RES-LINE.
           05  FILLER            PIC X(8) VALUE 'G1Q RC='.
           05  RS-RC             PIC 9(4).
           05  FILLER            PIC X(5) VALUE ' LEN='.
           05  RS-LEN            PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' SCRNS='.
           05  RS-CNT            PIC 9(4).
           05  FILLER            PIC X(6) VALUE ' DATA='.
           05  RS-HEX            PIC X(16).
       LINKAGE SECTION.
       01  PARM-AREA.
           05  PARM-LEN          PIC S9(4) COMP.
           05  PARM-SCR          PIC X.
       PROCEDURE DIVISION USING PARM-AREA.
       MAIN-PARA.
           MOVE SPACES TO FS-BUF.
           MOVE 'P' TO FS-SCR.
           IF PARM-LEN > 0 AND (PARM-SCR = 'C' OR PARM-SCR = 'K'
                                OR PARM-SCR = 'Q')
               MOVE PARM-SCR TO FS-SCR.
           CALL 'PACFS2' USING FS-BUF FS-LEN FS-RC FS-CNT FS-LOG
                               FS-SCR.
           MOVE SPACES TO HEX-LINE.
           MOVE 0 TO WS-O.
           PERFORM LOG-BYTE VARYING WS-K FROM 1 BY 1 UNTIL WS-K > 8.
           MOVE HEX-LINE TO AL-HEX.
           MOVE SPACES TO HEX-LINE.
           MOVE 0 TO WS-O.
           PERFORM HEX-BYTE VARYING WS-K FROM 1 BY 1 UNTIL WS-K > 8.
           MOVE FS-RC TO RS-RC.
           MOVE FS-LEN TO RS-LEN.
           MOVE FS-CNT TO RS-CNT.
           MOVE HEX-LINE TO RS-HEX.
           DISPLAY RES-LINE.
           DISPLAY AID-LINE.
           IF FS-SCR = 'Q'
               PERFORM QUERY-REPORT THRU QUERY-REPORT-EXIT.
           DISPLAY 'G1Q PROBE END'.
           STOP RUN.
       LOG-BYTE.
           MOVE LG-CH (WS-K) TO HX-B.
           PERFORM TO-HEX.
       HEX-BYTE.
           MOVE FS-CH (WS-K) TO HX-B.
           PERFORM TO-HEX.
       TO-HEX.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-Q) TO HX-CH (WS-O).
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-R) TO HX-CH (WS-O).
       QUERY-REPORT.
      * 96 BYTES OF THE INBOUND IN HEX, THEN THE QUERY CODES OF ALL
      * QUERY REPLY STRUCTURED FIELDS (ID X'81') AND THE USABLE AREA.
           MOVE 1 TO WS-K.
           PERFORM WIDE-HEX 3 TIMES.
           MOVE SPACES TO QC-LINE.
           MOVE 'G1Q CODES=' TO QC-LINE.
           MOVE 0 TO WS-O.
           MOVE 0 TO WS-W.
           MOVE 0 TO WS-H.
           MOVE 2 TO WS-P.
           MOVE 0 TO WS-STOP.
           PERFORM NEXT-SF THRU NEXT-SF-EXIT UNTIL WS-STOP = 1.
           DISPLAY QC-LINE.
           MOVE WS-W TO AR-W.
           MOVE WS-H TO AR-H.
           DISPLAY AREA-LINE.
       QUERY-REPORT-EXIT.
           EXIT.
       WIDE-HEX.
           MOVE SPACES TO WIDE-LINE.
           MOVE 'G1Q ' TO WIDE-LINE.
           MOVE 0 TO WS-O.
           PERFORM WIDE-BYTE 32 TIMES.
           DISPLAY WIDE-LINE.
       WIDE-BYTE.
           MOVE FS-CH (WS-K) TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-Q) TO WD-CH (WS-O).
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-R) TO WD-CH (WS-O).
           ADD 1 TO WS-K.
       NEXT-SF.
           COMPUTE WS-LIM = WS-P + 3.
           IF WS-LIM > FS-LEN OR WS-O > 56
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
               PERFORM CODE-HEX.
           IF WS-ID = 129 AND WS-QC = 129
               PERFORM AREA-SIZE.
           IF WS-L < 4
               MOVE 1 TO WS-STOP
           ELSE
               ADD WS-L TO WS-P.
       NEXT-SF-EXIT.
           EXIT.
       CODE-HEX.
           DIVIDE WS-QC BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-Q) TO QC-CH (WS-O).
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-R) TO QC-CH (WS-O).
           ADD 1 TO WS-O.
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
