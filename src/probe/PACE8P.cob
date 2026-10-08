      * PACE8P : MVS-G3 PROBE E8 (SEE PACFS8). PARM = RUNG 0-8.
      * NOTHING IS PRINTED BEFORE THE FULL-SCREEN PART. AFTERWARDS ONE
      * SUMMARY LINE AND, FOR EVERY TPUT, TWO TRACE LINES: SERVICE,
      * R1 (BUFFER), R0 (LENGTH GIVEN TO TPUT), RC; FIRST 32 BYTES.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACE8P.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  P-RUNG                PIC X VALUE '0'.
       01  P-RC1                 PIC S9(4) COMP.
       01  P-NPART               PIC S9(4) COMP.
       01  P-AID                 PIC X.
       01  P-TRCNT               PIC S9(4) COMP.
       01  P-EMPTY               PIC S9(4) COMP.
       01  P-TRTAB.
           05  TR-ENT            PIC X(48) OCCURS 16 TIMES.
       01  WK-ENT.
           05  WK-SVC            PIC X(4).
           05  FILLER            PIC X(44).
       01  WK-BYTES REDEFINES WK-ENT.
           05  WK-B              PIC X OCCURS 48 TIMES.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  HEX-OUT.
           05  HO-CH             PIC X OCCURS 96 TIMES.
       01  HEX-PARTS REDEFINES HEX-OUT.
           05  FILLER            PIC X(8).
           05  HP-ADR            PIC X(8).
           05  HP-LEN            PIC X(8).
           05  HP-RC             PIC X(8).
           05  HP-DATA           PIC X(64).
       01  WS-I                  PIC 99.
       01  WS-J                  PIC 99.
       01  WS-O                  PIC 99.
       01  WS-Q                  PIC 99.
       01  WS-R                  PIC 99.
       01  RES-LINE.
           05  FILLER            PIC X(9) VALUE 'G8P RUNG='.
           05  RS-RUNG           PIC X.
           05  FILLER            PIC X(5) VALUE ' RC1='.
           05  RS-RC1            PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' PARTS='.
           05  RS-NPART          PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' EMPTY='.
           05  RS-EMPTY          PIC 9(4).
           05  FILLER            PIC X(5) VALUE ' AID='.
           05  RS-AID1           PIC X.
           05  RS-AID2           PIC X.
           05  FILLER            PIC X(7) VALUE ' TRACE='.
           05  RS-TRCNT          PIC 99.
       01  TR-LINE1.
           05  FILLER            PIC X(5) VALUE 'G8P T'.
           05  T1-N              PIC 99.
           05  FILLER            PIC X VALUE ' '.
           05  T1-SVC            PIC X(4).
           05  FILLER            PIC X(4) VALUE ' R1='.
           05  T1-ADR            PIC X(8).
           05  FILLER            PIC X(4) VALUE ' R0='.
           05  T1-LEN            PIC X(8).
           05  FILLER            PIC X(4) VALUE ' RC='.
           05  T1-RC             PIC X(8).
       01  TR-LINE2.
           05  FILLER            PIC X(8) VALUE 'G8P   D='.
           05  T2-DATA           PIC X(64).
       LINKAGE SECTION.
       01  PARM-AREA.
           05  PARM-LEN          PIC S9(4) COMP.
           05  PARM-RUNG         PIC X.
       PROCEDURE DIVISION USING PARM-AREA.
       MAIN-PARA.
           IF PARM-LEN > 0
               MOVE PARM-RUNG TO P-RUNG.
           MOVE SPACES TO P-TRTAB.
           CALL 'PACFS8' USING P-RUNG P-RC1 P-NPART P-AID P-TRCNT
                               P-EMPTY P-TRTAB.
           MOVE P-RUNG TO RS-RUNG.
           MOVE P-RC1 TO RS-RC1.
           MOVE P-NPART TO RS-NPART.
           MOVE P-EMPTY TO RS-EMPTY.
           MOVE P-TRCNT TO RS-TRCNT.
           MOVE P-AID TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           MOVE HEXDIG (WS-Q) TO RS-AID1.
           MOVE HEXDIG (WS-R) TO RS-AID2.
           DISPLAY RES-LINE.
           PERFORM SHOW-ENTRY VARYING WS-I FROM 1 BY 1
               UNTIL WS-I > P-TRCNT OR WS-I > 16.
           DISPLAY 'G8P PROBE END'.
           STOP RUN.
       SHOW-ENTRY.
           MOVE TR-ENT (WS-I) TO WK-ENT.
           MOVE 0 TO WS-O.
           PERFORM HEX-BYTE VARYING WS-J FROM 1 BY 1 UNTIL WS-J > 48.
           MOVE WS-I TO T1-N.
           MOVE WK-SVC TO T1-SVC.
           MOVE HP-ADR TO T1-ADR.
           MOVE HP-LEN TO T1-LEN.
           MOVE HP-RC TO T1-RC.
           MOVE HP-DATA TO T2-DATA.
           DISPLAY TR-LINE1.
           DISPLAY TR-LINE2.
       HEX-BYTE.
           MOVE WK-B (WS-J) TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-Q) TO HO-CH (WS-O).
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-R) TO HO-CH (WS-O).
