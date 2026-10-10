      * PACINPT : INPUT ADAPTER. ONE SYSIN CARD -> ONE REQUEST.
      * OPS : OPEN  READ  CLOS  PARM (CLASSIFY REQ-TEXT, NO I/O).
      * REQ-KIND: MOV (REQ-DIR U/D/L/R)  QUI  CFG (REQ-LEVEL,
      *   REQ-COUNT)  INV  EOF, AND IN TSO MODE RDR (BLANK LINE =
      *   REDRAW REQUEST). REQ-CHAR HOLDS THE COMMAND'S FIRST BYTE.
      * TSC (MVS-G1): READ ASKS PACPLAT RECV FOR ONE FULL-SCREEN INPUT;
      *   ENTER = THE TYPED FIELD, CLASSIFIED AS A CARD; ANY OTHER KEY
      *   (PA2 RESHOW) = RDR; AN ERROR LEAVES TSC AND READS A LINE.
      * MVS-RT (D33): RTRD (NON-BLOCKING) / RTRB (BLOCKING) RETURN ONE
      *   INPUT EVENT: MOV, QUI, PAU (PAUSE), RDR, INV, CFG, IGN (AN AID
      *   WITHOUT MEANING), NON (NOTHING MORE NOW), EOF, ERR (TSC LOST).
      *   TSC: PACPLAT POLL / RECV; PF7 U PF8 D PF10 L PF11 R, PF9 PAU
      *   (RT3: THE LAUNCHER MAPS P TO PF9), PA2 RDR,
      *   ENTER = THE TYPED FIELD (U/D/L/R, Q, P, BLANK = RDR, ELSE INV;
      *   REQ-INKEY STAYS E). BAT/TSD: ONE CARD = ONE QUANTUM, ITS
      *   CHARACTERS IN ORDER UP TO THE FIRST BLANK (U D L R ANY CASE,
      *   Q, P, * = PA2, . OR + = NOTHING, ELSE INV), THEN NON; A CARD
      *   STARTING WITH A IS ONE CFG EVENT.
      * ONLY THIS MODULE KNOWS ABOUT THE TERMINAL/CARD SOURCE.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACINPT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT COMMAND-FILE ASSIGN TO UT-S-SYSIN.
       DATA DIVISION.
       FILE SECTION.
       FD  COMMAND-FILE
           RECORDING MODE IS F
           LABEL RECORDS ARE OMITTED
           RECORD CONTAINS 80 CHARACTERS
           DATA RECORD IS COMMAND-RECORD.
       01  COMMAND-RECORD        PIC X(80).
       WORKING-STORAGE SECTION.
       01  WS-CARD.
           05  CMD-CHAR          PIC X.
           05  FILLER            PIC X.
           05  CMD-LEVEL         PIC X.
           05  FILLER            PIC X.
           05  CMD-COUNT         PIC X.
           05  FILLER            PIC X(75).
       01  RAW-CARD REDEFINES WS-CARD.
           05  RAW-CHAR          PIC X OCCURS 80 TIMES.
       01  NORM-REC.
           05  NR-CHAR           PIC X OCCURS 80 TIMES.
       01  WS-OFF                PIC 99.
       01  WS-I                  PIC 99.
       01  WS-J                  PIC 99.
       01  WS-LIM                PIC 99.
       01  RT-CARD.
           05  RT-CH             PIC X OCCURS 80 TIMES.
       01  RT-POS                PIC 99 VALUE 0.
       01  RT-C                  PIC X.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  WS-V                  PIC 9(4).
       01  WS-NOP                PIC 9.
       LINKAGE SECTION.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'OPEN'
               OPEN INPUT COMMAND-FILE
           ELSE IF (REQ-OP = 'RTRD' OR REQ-OP = 'RTRB')
                                AND REQ-MODE = 'TSC'
               PERFORM RT-TSC THRU RT-TSC-EXIT
           ELSE IF REQ-OP = 'RTRD' OR REQ-OP = 'RTRB'
               PERFORM RT-CARD-READ THRU RT-CARD-READ-EXIT
           ELSE IF REQ-OP = 'READ' AND REQ-MODE = 'TSC'
               PERFORM TSC-READ THRU TSC-READ-EXIT
           ELSE IF REQ-OP = 'READ'
               PERFORM DO-READ THRU DO-READ-EXIT
           ELSE IF REQ-OP = 'CLOS'
               CLOSE COMMAND-FILE
           ELSE IF REQ-OP = 'PARM'
               MOVE SPACES TO WS-CARD
               MOVE REQ-TEXT TO WS-CARD
               PERFORM CLASSIFY THRU CLASSIFY-EXIT.
           GOBACK.
       DO-READ.
           MOVE SPACES TO REQ-KIND.
           READ COMMAND-FILE AT END MOVE 'EOF' TO REQ-KIND.
           IF REQ-KIND = SPACES
               MOVE COMMAND-RECORD TO WS-CARD.
           IF REQ-KIND = SPACES AND REQ-MODE NOT = 'BAT'
               PERFORM NORMALIZE THRU NORMALIZE-EXIT.
           IF REQ-KIND = SPACES AND REQ-MODE NOT = 'BAT'
                                AND WS-CARD = SPACES
               MOVE 'RDR' TO REQ-KIND.
           IF REQ-KIND = SPACES AND REQ-MODE = 'TSD'
                                AND CMD-CHAR = '+'
               MOVE 'TCK' TO REQ-KIND.
           IF REQ-KIND = SPACES
               PERFORM CLASSIFY THRU CLASSIFY-EXIT.
       DO-READ-EXIT.
           EXIT.
       TSC-READ.
           MOVE 'RECV' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE 'READ' TO REQ-OP.
           IF REQ-INKEY = 'X'
               PERFORM DO-READ THRU DO-READ-EXIT
               GO TO TSC-READ-EXIT.
           IF REQ-INKEY = 'T'
               MOVE 'TCK' TO REQ-KIND
               GO TO TSC-READ-EXIT.
           MOVE 'RDR' TO REQ-KIND.
           IF REQ-INKEY NOT = 'E'
               GO TO TSC-READ-EXIT.
           MOVE SPACES TO WS-CARD.
           MOVE REQ-INTEXT TO WS-CARD.
           PERFORM NORMALIZE THRU NORMALIZE-EXIT.
           IF WS-CARD NOT = SPACES
               PERFORM CLASSIFY THRU CLASSIFY-EXIT.
       TSC-READ-EXIT.
           EXIT.
       RT-TSC.
      * MVS-RT TERMINAL INPUT: ONE AID (POLL) OR WAIT FOR ONE (RECV).
           MOVE SPACE TO REQ-CHAR.
           IF REQ-OP = 'RTRD'
               MOVE 'POLL' TO REQ-OP
           ELSE
               MOVE 'RECV' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE 'RTRD' TO REQ-OP.
           MOVE 'NON' TO REQ-KIND.
           IF REQ-INKEY = 'N'
               GO TO RT-TSC-EXIT.
           MOVE 'ERR' TO REQ-KIND.
           IF REQ-INKEY = 'X'
               GO TO RT-TSC-EXIT.
           IF REQ-INKEY = 'E'
               PERFORM RT-ENTER THRU RT-ENTER-EXIT
               GO TO RT-TSC-EXIT.
           MOVE 'IGN' TO REQ-KIND.
           MOVE REQ-AID TO HX-B.
           MOVE HEXN TO WS-V.
           IF WS-V = 247
               MOVE 'U' TO RT-C
               PERFORM RT-CHAR.
           IF WS-V = 248
               MOVE 'D' TO RT-C
               PERFORM RT-CHAR.
           IF WS-V = 122
               MOVE 'L' TO RT-C
               PERFORM RT-CHAR.
           IF WS-V = 123
               MOVE 'R' TO RT-C
               PERFORM RT-CHAR.
           IF WS-V = 249
               MOVE 'P' TO RT-C
               PERFORM RT-CHAR.
           IF WS-V = 110
               MOVE 'RDR' TO REQ-KIND.
       RT-TSC-EXIT.
           EXIT.
       RT-ENTER.
           MOVE 'RDR' TO REQ-KIND.
           MOVE SPACES TO WS-CARD.
           MOVE REQ-INTEXT TO WS-CARD.
           PERFORM NORMALIZE THRU NORMALIZE-EXIT.
           IF WS-CARD = SPACES
               GO TO RT-ENTER-EXIT.
           MOVE CMD-CHAR TO RT-C.
           PERFORM RT-CHAR.
       RT-ENTER-EXIT.
           EXIT.
       RT-CARD-READ.
      * MVS-RT CARDS: THE NEXT EVENT OF THE CURRENT CARD, NON AT ITS END
           IF RT-POS = 0
               PERFORM RT-NEW-CARD THRU RT-NEW-CARD-EXIT
               GO TO RT-CARD-READ-EXIT.
           MOVE 'NON' TO REQ-KIND.
           PERFORM RT-SCAN UNTIL REQ-KIND NOT = 'NON' OR RT-POS = 0.
       RT-CARD-READ-EXIT.
           EXIT.
       RT-NEW-CARD.
           MOVE SPACES TO REQ-KIND.
           READ COMMAND-FILE AT END MOVE 'EOF' TO REQ-KIND.
           IF REQ-KIND = 'EOF'
               GO TO RT-NEW-CARD-EXIT.
           MOVE COMMAND-RECORD TO RT-CARD.
           MOVE 1 TO RT-POS.
           IF RT-CH (1) = 'A'
               MOVE COMMAND-RECORD TO WS-CARD
               PERFORM CLASSIFY THRU CLASSIFY-EXIT
               MOVE 81 TO RT-POS.
           IF REQ-KIND = 'CFG'
               GO TO RT-NEW-CARD-EXIT.
           MOVE 'NON' TO REQ-KIND.
           PERFORM RT-SCAN UNTIL REQ-KIND NOT = 'NON' OR RT-POS = 0.
       RT-NEW-CARD-EXIT.
           EXIT.
       RT-SCAN.
      * ONE CHARACTER: BLANK OR PAST COLUMN 80 ENDS THE CARD (NON).
           IF RT-POS > 80
               MOVE 0 TO RT-POS
           ELSE IF RT-CH (RT-POS) = SPACE
               MOVE 0 TO RT-POS
           ELSE
               MOVE RT-CH (RT-POS) TO RT-C
               ADD 1 TO RT-POS
               PERFORM RT-CARD-CHAR.
           MOVE 0 TO WS-NOP.
       RT-CARD-CHAR.
           IF RT-C NOT = '.' AND RT-C NOT = '+'
               PERFORM RT-CHAR.
           MOVE 0 TO WS-NOP.
       RT-CHAR.
      * ONE REALTIME INPUT CHARACTER -> EVENT (P PAUSE, * REDRAW).
           MOVE RT-C TO REQ-CHAR.
           IF RT-C = 'P' OR RT-C = 'p'
               MOVE 'PAU' TO REQ-KIND
           ELSE IF RT-C = '*'
               MOVE 'RDR' TO REQ-KIND
           ELSE IF RT-C = 'A'
               MOVE 'INV' TO REQ-KIND
           ELSE
               MOVE SPACES TO WS-CARD
               MOVE RT-C TO CMD-CHAR
               PERFORM CLASSIFY THRU CLASSIFY-EXIT.
           MOVE 0 TO WS-NOP.
       NORMALIZE.
      * TSO/TSC ONLY: TOLERATE LEADING BLANKS/NON-PRINTABLE BYTES TYPED
      * BEFORE THE COMMAND: START AT THE FIRST BYTE > BLANK (1-8).
           MOVE 1 TO WS-OFF.
           PERFORM FIND-START UNTIL WS-OFF > 8
               OR RAW-CHAR (WS-OFF) > SPACE.
           IF WS-OFF > 1 AND WS-OFF < 9
               PERFORM SHIFT-LEFT THRU SHIFT-LEFT-EXIT.
       NORMALIZE-EXIT.
           EXIT.
       FIND-START.
           ADD 1 TO WS-OFF.
       SHIFT-LEFT.
           MOVE SPACES TO NORM-REC.
           COMPUTE WS-LIM = 81 - WS-OFF.
           PERFORM COPY-CHAR VARYING WS-I FROM 1 BY 1
               UNTIL WS-I > WS-LIM.
           MOVE NORM-REC TO WS-CARD.
       SHIFT-LEFT-EXIT.
           EXIT.
       COPY-CHAR.
           COMPUTE WS-J = WS-I + WS-OFF - 1.
           MOVE RAW-CHAR (WS-J) TO NR-CHAR (WS-I).
       CLASSIFY.
           MOVE CMD-CHAR TO REQ-CHAR.
           MOVE 'INV' TO REQ-KIND.
           IF CMD-CHAR = 'U' OR CMD-CHAR = 'u'
               MOVE 'MOV' TO REQ-KIND
               MOVE 'U' TO REQ-DIR
           ELSE IF CMD-CHAR = 'D' OR CMD-CHAR = 'd'
               MOVE 'MOV' TO REQ-KIND
               MOVE 'D' TO REQ-DIR
           ELSE IF CMD-CHAR = 'L' OR CMD-CHAR = 'l'
               MOVE 'MOV' TO REQ-KIND
               MOVE 'L' TO REQ-DIR
           ELSE IF CMD-CHAR = 'R' OR CMD-CHAR = 'r'
               MOVE 'MOV' TO REQ-KIND
               MOVE 'R' TO REQ-DIR
           ELSE IF CMD-CHAR = 'Q' OR CMD-CHAR = 'q'
               MOVE 'QUI' TO REQ-KIND
           ELSE IF CMD-CHAR = 'A'
               MOVE 'CFG' TO REQ-KIND
               PERFORM SET-CONFIG THRU SET-CONFIG-EXIT.
       CLASSIFY-EXIT.
           EXIT.
       SET-CONFIG.
           IF CMD-LEVEL = '0'
               MOVE 0 TO REQ-LEVEL
           ELSE IF CMD-LEVEL = '2'
               MOVE 2 TO REQ-LEVEL
           ELSE IF CMD-LEVEL = '3'
               MOVE 3 TO REQ-LEVEL
           ELSE
               MOVE 1 TO REQ-LEVEL.
           IF CMD-COUNT = '2'
               MOVE 2 TO REQ-COUNT
           ELSE IF CMD-COUNT = '3'
               MOVE 3 TO REQ-COUNT
           ELSE
               MOVE 1 TO REQ-COUNT.
       SET-CONFIG-EXIT.
           EXIT.
