      * PACQRY : MVS-G4 CAPABILITY PARSING (PURE: NO I/O, NO TERMINAL).
      * CALL 'PACQRY' USING QRY-AREA QRY-LEN QRY-OUT. THE AREA HOLDS A
      * READ PARTITION QUERY REPLY AS RECEIVED BY PACPLAT (AID X'88'
      * + STRUCTURED FIELDS: LENGTH(2), X'81', QCODE, DATA). OUT:
      *   QO-COLOUR 1 = QCODE X'86' (MVS-G1), QO-HILITE 1 = QCODE X'87'
      *   (MVS-G2), QO-GE 1 = QCODE X'85' WITH FLAG X'80' (GE) AND X'02'
      *   (CGCSGID PRESENT) AND A SET WHOSE CODE PAGE IS 310 (APL).
      * THE G1/G2 DECISIONS WERE MOVED HERE FROM PACPLAT UNCHANGED.
      * MVS-GS: QO-AW/QO-AH = THE ALTERNATE SCREEN SIZE: QCODE X'A6'
      * (IMPLICIT PARTITION, ALTERNATE WIDTH/HEIGHT AT +13/+15), ELSE
      * QCODE X'81' (USABLE AREA, WIDTH/HEIGHT AT +6/+8), ELSE 80 X 24.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACQRY.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  WS-K                  PIC 9(4).
       01  WS-P                  PIC 9(4).
       01  WS-V                  PIC 9(4).
       01  WS-L                  PIC 9(4).
       01  WS-ID                 PIC 9(4).
       01  WS-QC                 PIC 9(4).
       01  WS-LIM                PIC 9(4).
       01  WS-END                PIC 9(4).
       01  WS-D                  PIC 9(4).
       01  WS-DL                 PIC 9(4).
       01  WS-F1                 PIC 9(4).
       01  WS-Q                  PIC 9(4).
       01  WS-R                  PIC 9(4).
       01  WS-CP                 PIC 9(4).
       01  WS-STOP               PIC 9.
       01  WS-DSTOP              PIC 9.
       01  WS-NOP                PIC 9.
       01  WS-W                  PIC 9(4).
       01  UA-W                  PIC 9(4) VALUE 0.
       01  UA-H                  PIC 9(4) VALUE 0.
       01  IP-W                  PIC 9(4) VALUE 0.
       01  IP-H                  PIC 9(4) VALUE 0.
       LINKAGE SECTION.
       01  QRY-AREA.
           05  QRY-CH            PIC X OCCURS 2048 TIMES.
       01  QRY-LEN               PIC S9(4) COMP.
       01  QRY-OUT.
           05  QO-COLOUR         PIC 9.
           05  QO-HILITE         PIC 9.
           05  QO-GE             PIC 9.
           05  QO-AW             PIC 999.
           05  QO-AH             PIC 999.
       PROCEDURE DIVISION USING QRY-AREA QRY-LEN QRY-OUT.
       MAIN-PARA.
           MOVE 0 TO QO-COLOUR.
           MOVE 0 TO QO-HILITE.
           MOVE 0 TO QO-GE.
           MOVE 0 TO UA-W UA-H IP-W IP-H.
           PERFORM FIND-CAPS THRU FIND-CAPS-EXIT.
           MOVE 80 TO QO-AW.
           MOVE 24 TO QO-AH.
           IF UA-W > 0 AND UA-H > 0 AND UA-W < 1000 AND UA-H < 1000
               MOVE UA-W TO QO-AW
               MOVE UA-H TO QO-AH.
           IF IP-W > 0 AND IP-H > 0 AND IP-W < 1000 AND IP-H < 1000
               MOVE IP-W TO QO-AW
               MOVE IP-H TO QO-AH.
           GOBACK.
       FIND-CAPS.
      * QUERY REPLY = AID X'88' (136) + STRUCTURED FIELDS: LENGTH(2),
      * X'81' (129), QCODE. COLOUR SUPPORT = QCODE X'86' (134).
           IF QRY-LEN < 1
               GO TO FIND-CAPS-EXIT.
           MOVE 1 TO WS-K.
           PERFORM BYTE-VAL.
           IF WS-V NOT = 136
               GO TO FIND-CAPS-EXIT.
           MOVE 2 TO WS-P.
           MOVE 0 TO WS-STOP.
           PERFORM NEXT-SF THRU NEXT-SF-EXIT UNTIL WS-STOP = 1.
       FIND-CAPS-EXIT.
           EXIT.
       NEXT-SF.
           COMPUTE WS-LIM = WS-P + 3.
           IF WS-LIM > QRY-LEN
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
           IF WS-ID = 129 AND WS-QC = 134
               MOVE 1 TO QO-COLOUR.
           IF WS-ID = 129 AND WS-QC = 135
               MOVE 1 TO QO-HILITE.
           IF WS-ID = 129 AND WS-QC = 133 AND WS-L > 13
               PERFORM CHAR-SETS THRU CHAR-SETS-EXIT.
           IF WS-ID = 129 AND WS-QC = 129 AND WS-L > 9
               PERFORM USABLE THRU USABLE-EXIT.
           IF WS-ID = 129 AND WS-QC = 166 AND WS-L > 16
               PERFORM IMPLICIT THRU IMPLICIT-EXIT.
           IF WS-L < 4
               MOVE 1 TO WS-STOP
           ELSE
               ADD WS-L TO WS-P.
       NEXT-SF-EXIT.
           EXIT.
       CHAR-SETS.
      * X'85': FLAGS1 AT +4, DESCRIPTOR LENGTH (DL) AT +12, DESCRIPTORS
      * FROM +13 TO THE END OF THE FIELD; THE CGCSGID IS THE LAST FOUR
      * BYTES OF A DESCRIPTOR, ITS LAST TWO = CODE PAGE (310 = X'0136').
           COMPUTE WS-END = WS-P + WS-L - 1.
           IF WS-END > QRY-LEN
               GO TO CHAR-SETS-EXIT.
           COMPUTE WS-K = WS-P + 4.
           PERFORM BYTE-VAL.
           MOVE WS-V TO WS-F1.
           IF WS-F1 < 128
               GO TO CHAR-SETS-EXIT.
           DIVIDE WS-F1 BY 4 GIVING WS-Q REMAINDER WS-R.
           IF WS-R < 2
               GO TO CHAR-SETS-EXIT.
           COMPUTE WS-K = WS-P + 12.
           PERFORM BYTE-VAL.
           MOVE WS-V TO WS-DL.
           IF WS-DL < 4
               GO TO CHAR-SETS-EXIT.
           COMPUTE WS-D = WS-P + 13.
           MOVE 0 TO WS-DSTOP.
           PERFORM NEXT-DESC UNTIL WS-DSTOP = 1.
       CHAR-SETS-EXIT.
           EXIT.
       NEXT-DESC.
           COMPUTE WS-LIM = WS-D + WS-DL - 1.
           IF WS-LIM > WS-END
               MOVE 1 TO WS-DSTOP.
           IF WS-DSTOP = 0
               PERFORM DESC-CP.
           ADD WS-DL TO WS-D.
       DESC-CP.
           COMPUTE WS-K = WS-LIM - 1.
           PERFORM BYTE-VAL.
           COMPUTE WS-CP = WS-V * 256.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           ADD WS-V TO WS-CP.
           IF WS-CP = 310
               MOVE 1 TO QO-GE.
           MOVE 0 TO WS-NOP.
       USABLE.
      * X'81' USABLE AREA: WIDTH AT +6, HEIGHT AT +8 (2 BYTES EACH).
           COMPUTE WS-END = WS-P + 9.
           IF WS-END > QRY-LEN
               GO TO USABLE-EXIT.
           COMPUTE WS-K = WS-P + 6.
           PERFORM WORD-VAL.
           MOVE WS-W TO UA-W.
           COMPUTE WS-K = WS-P + 8.
           PERFORM WORD-VAL.
           MOVE WS-W TO UA-H.
       USABLE-EXIT.
           EXIT.
       IMPLICIT.
      * X'A6' IMPLICIT PARTITION: SELF-DEFINING PARAMETER X'01' AT +7,
      * ALTERNATE WIDTH AT +13, ALTERNATE HEIGHT AT +15.
           COMPUTE WS-END = WS-P + 16.
           IF WS-END > QRY-LEN
               GO TO IMPLICIT-EXIT.
           COMPUTE WS-K = WS-P + 7.
           PERFORM BYTE-VAL.
           IF WS-V NOT = 1
               GO TO IMPLICIT-EXIT.
           COMPUTE WS-K = WS-P + 13.
           PERFORM WORD-VAL.
           MOVE WS-W TO IP-W.
           COMPUTE WS-K = WS-P + 15.
           PERFORM WORD-VAL.
           MOVE WS-W TO IP-H.
       IMPLICIT-EXIT.
           EXIT.
       WORD-VAL.
           PERFORM BYTE-VAL.
           COMPUTE WS-W = WS-V * 256.
           ADD 1 TO WS-K.
           PERFORM BYTE-VAL.
           ADD WS-V TO WS-W.
       BYTE-VAL.
           MOVE QRY-CH (WS-K) TO HX-B.
           MOVE HEXN TO WS-V.
