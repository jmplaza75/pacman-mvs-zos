      * PACINPT : INPUT ADAPTER. ONE SYSIN CARD -> ONE REQUEST.
      * OPS : OPEN  READ  CLOS  PARM (CLASSIFY REQ-TEXT, NO I/O).
      * REQ-KIND: MOV (REQ-DIR U/D/L/R)  QUI  CFG (REQ-LEVEL,
      *   REQ-COUNT)  INV  EOF, AND IN TSO MODE RDR (BLANK LINE =
      *   REDRAW REQUEST). REQ-CHAR HOLDS THE COMMAND'S FIRST BYTE.
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
       LINKAGE SECTION.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'OPEN'
               OPEN INPUT COMMAND-FILE
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
           IF REQ-KIND = SPACES AND REQ-MODE = 'TSO'
               PERFORM NORMALIZE THRU NORMALIZE-EXIT.
           IF REQ-KIND = SPACES AND REQ-MODE = 'TSO'
                                AND WS-CARD = SPACES
               MOVE 'RDR' TO REQ-KIND.
           IF REQ-KIND = SPACES
               PERFORM CLASSIFY THRU CLASSIFY-EXIT.
       DO-READ-EXIT.
           EXIT.
       NORMALIZE.
      * TSO ONLY: TOLERATE LEADING BLANKS/NON-PRINTABLE BYTES TYPED
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
