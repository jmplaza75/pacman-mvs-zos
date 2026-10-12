      * PACQRYT : MVS-G4 BATCH TEST DRIVER FOR PACQRY (NOT PART OF THE
      * GAME). SYSIN CARDS: COLUMNS 1-8 CASE NAME, 10-73 REPLY BYTES IN
      * HEX (UP TO 32 PER CARD); CONSECUTIVE CARDS WITH THE SAME NAME
      * ARE ONE REPLY. FOR EVERY REPLY ONE LINE IS PRINTED:
      *   QRY NAME     LEN=NNNN C=N H=N GE=N  (COLOUR, HILITE, GE).
      * MVS-RP D40: A DIGIT IN COLUMN 9 = SEQUENCE MODE: THE CARDS OF
      * ONE NAME ARE STARTUP EVENTS, ONE PER DIGIT CHANGE (A CARD
      * WITHOUT HEX = AN EMPTY READ), FED TO PACQRY UNTIL QS-ACT IS
      * NOT R, AS PACPLAT DOES; ONE LINE PER SEQUENCE:
      *   QSL NAME     ACT=A NREC=NN NWAIT=NN C=N H=N GE=N
      * (C/H/GE OF THE ACCEPTED RECORD, 0 WHEN NONE WAS ACCEPTED).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACQRYT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT CARD-FILE ASSIGN TO UT-S-SYSIN.
       DATA DIVISION.
       FILE SECTION.
       FD  CARD-FILE
           RECORDING MODE IS F
           LABEL RECORDS ARE OMITTED
           RECORD CONTAINS 80 CHARACTERS
           DATA RECORD IS CARD-REC.
       01  CARD-REC              PIC X(80).
       WORKING-STORAGE SECTION.
       01  WS-CARD.
           05  CD-NAME           PIC X(8).
           05  CD-SEQ            PIC X.
           05  CD-HEX            PIC X OCCURS 64 TIMES.
           05  FILLER            PIC X(7).
       01  Q-AREA.
           05  Q-CH              PIC X OCCURS 2048 TIMES.
       01  Q-LEN                 PIC S9(4) COMP.
       01  Q-OUT.
           05  QO-COLOUR         PIC 9.
           05  QO-HILITE         PIC 9.
           05  QO-GE             PIC 9.
           05  QO-AW             PIC 999.
           05  QO-AH             PIC 999.
           05  QO-VALID          PIC 9.
           05  QS-ACT            PIC X.
           05  QS-NREC           PIC 99.
           05  QS-NWAIT          PIC 99.
       01  CUR-NAME              PIC X(8) VALUE SPACES.
       01  CUR-SEQ               PIC X VALUE SPACE.
       01  SEQ-ON                PIC 9 VALUE 0.
       01  SL-LINE.
           05  FILLER            PIC X(4) VALUE 'QSL '.
           05  SL-NAME           PIC X(8).
           05  FILLER            PIC X(5) VALUE ' ACT='.
           05  SL-ACT            PIC X.
           05  FILLER            PIC X(6) VALUE ' NREC='.
           05  SL-NREC           PIC 99.
           05  FILLER            PIC X(7) VALUE ' NWAIT='.
           05  SL-NWAIT          PIC 99.
           05  FILLER            PIC X(3) VALUE ' C='.
           05  SL-C              PIC 9.
           05  FILLER            PIC X(3) VALUE ' H='.
           05  SL-H              PIC 9.
           05  FILLER            PIC X(4) VALUE ' GE='.
           05  SL-GE             PIC 9.
       01  WS-EOF                PIC 9 VALUE 0.
       01  WS-K                  PIC 99.
       01  WS-HV                 PIC 99.
       01  WS-LV                 PIC 99.
       01  WS-D                  PIC 99.
       01  WS-C                  PIC X.
       01  WS-NOP                PIC 9.
       01  BW.
           05  BW-N              PIC 9(4) COMP.
       01  BW-X REDEFINES BW.
           05  FILLER            PIC X.
           05  BW-L              PIC X.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  RES-LINE.
           05  FILLER            PIC X(4) VALUE 'QRY '.
           05  RL-NAME           PIC X(8).
           05  FILLER            PIC X(5) VALUE ' LEN='.
           05  RL-LEN            PIC 9(4).
           05  FILLER            PIC X(3) VALUE ' C='.
           05  RL-C              PIC 9.
           05  FILLER            PIC X(3) VALUE ' H='.
           05  RL-H              PIC 9.
           05  FILLER            PIC X(4) VALUE ' GE='.
           05  RL-GE             PIC 9.
           05  FILLER            PIC X(4) VALUE ' AW='.
           05  RL-AW             PIC 999.
           05  FILLER            PIC X(4) VALUE ' AH='.
           05  RL-AH             PIC 999.
       PROCEDURE DIVISION.
       MAIN-PARA.
           OPEN INPUT CARD-FILE.
           MOVE 0 TO Q-LEN.
           PERFORM READ-CARD THRU READ-CARD-EXIT UNTIL WS-EOF = 1.
           IF CUR-NAME NOT = SPACES
               PERFORM FLUSH-NAME.
           CLOSE CARD-FILE.
           DISPLAY 'QRY TEST END'.
           STOP RUN.
       READ-CARD.
           READ CARD-FILE INTO WS-CARD
               AT END MOVE 1 TO WS-EOF
               GO TO READ-CARD-EXIT.
           IF CD-NAME NOT = CUR-NAME AND CUR-NAME NOT = SPACES
               PERFORM FLUSH-NAME.
           IF CD-NAME = CUR-NAME AND SEQ-ON = 1 AND CD-SEQ NOT = CUR-SEQ
               PERFORM SEQ-EVENT.
           IF CD-NAME NOT = CUR-NAME
               PERFORM NEW-NAME.
           MOVE CD-SEQ TO CUR-SEQ.
           MOVE 1 TO WS-K.
           PERFORM ADD-BYTE UNTIL WS-K > 63.
       READ-CARD-EXIT.
           EXIT.
       ADD-BYTE.
           MOVE CD-HEX (WS-K) TO WS-C.
           ADD 1 TO WS-K.
           IF WS-C NOT = SPACE
               PERFORM HEX-PAIR.
           ADD 1 TO WS-K.
       HEX-PAIR.
           PERFORM DIGIT-VAL.
           MOVE WS-D TO WS-HV.
           MOVE CD-HEX (WS-K) TO WS-C.
           PERFORM DIGIT-VAL.
           MOVE WS-D TO WS-LV.
           COMPUTE BW-N = WS-HV * 16 + WS-LV.
           ADD 1 TO Q-LEN.
           MOVE BW-L TO Q-CH (Q-LEN).
       DIGIT-VAL.
           MOVE 1 TO WS-D.
           PERFORM NEXT-DIGIT UNTIL WS-D > 16
               OR HEXDIG (WS-D) = WS-C.
           SUBTRACT 1 FROM WS-D.
       NEXT-DIGIT.
           ADD 1 TO WS-D.
       NEW-NAME.
           MOVE CD-NAME TO CUR-NAME.
           MOVE 0 TO Q-LEN.
           MOVE SPACES TO Q-AREA.
           MOVE 0 TO SEQ-ON.
           IF CD-SEQ NOT = SPACE
               MOVE 1 TO SEQ-ON.
           MOVE 0 TO QS-NREC.
           MOVE 0 TO QS-NWAIT.
           MOVE 'R' TO QS-ACT.
           MOVE 0 TO SL-C.
           MOVE 0 TO SL-H.
           MOVE 0 TO SL-GE.
       FLUSH-NAME.
           IF SEQ-ON = 1
               PERFORM SEQ-EVENT
               PERFORM SEQ-PRINT
           ELSE
               PERFORM EVAL-REPLY.
           MOVE 0 TO WS-NOP.
       SEQ-EVENT.
      * ONE STARTUP EVENT; AFTER A DECISION (A / F) NO MORE IS READ.
           IF QS-ACT = 'R'
               CALL 'PACQRY' USING Q-AREA Q-LEN Q-OUT.
           IF QS-ACT = 'A'
               MOVE QO-COLOUR TO SL-C
               MOVE QO-HILITE TO SL-H
               MOVE QO-GE TO SL-GE.
           MOVE 0 TO Q-LEN.
           MOVE SPACES TO Q-AREA.
       SEQ-PRINT.
           MOVE CUR-NAME TO SL-NAME.
           MOVE QS-ACT TO SL-ACT.
           MOVE QS-NREC TO SL-NREC.
           MOVE QS-NWAIT TO SL-NWAIT.
           DISPLAY SL-LINE.
       EVAL-REPLY.
           MOVE 0 TO QS-NREC.
           MOVE 0 TO QS-NWAIT.
           CALL 'PACQRY' USING Q-AREA Q-LEN Q-OUT.
           MOVE CUR-NAME TO RL-NAME.
           MOVE Q-LEN TO RL-LEN.
           MOVE QO-COLOUR TO RL-C.
           MOVE QO-HILITE TO RL-H.
           MOVE QO-GE TO RL-GE.
           MOVE QO-AW TO RL-AW.
           MOVE QO-AH TO RL-AH.
           DISPLAY RES-LINE.
