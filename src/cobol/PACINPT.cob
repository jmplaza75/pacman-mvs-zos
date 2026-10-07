      * PACINPT : INPUT ADAPTER. ONE SYSIN CARD -> ONE REQUEST.
      * OPS : OPEN  READ  CLOS.  READ SETS REQ-KIND:
      *   MOV (REQ-DIR U/D/L/R)  QUI  CFG (REQ-LEVEL, REQ-COUNT)
      *   INV  EOF.  REQ-CHAR ALWAYS HOLDS THE CARD'S FIRST BYTE.
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
       01  COMMAND-RECORD.
           05  CMD-CHAR          PIC X.
           05  FILLER            PIC X.
           05  CMD-LEVEL         PIC X.
           05  FILLER            PIC X.
           05  CMD-COUNT         PIC X.
           05  FILLER            PIC X(75).
       LINKAGE SECTION.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'OPEN'
               OPEN INPUT COMMAND-FILE
           ELSE IF REQ-OP = 'READ'
               PERFORM DO-READ THRU DO-READ-EXIT
           ELSE IF REQ-OP = 'CLOS'
               CLOSE COMMAND-FILE.
           GOBACK.
       DO-READ.
           MOVE SPACES TO REQ-KIND.
           READ COMMAND-FILE AT END MOVE 'EOF' TO REQ-KIND.
           IF REQ-KIND = SPACES
               PERFORM CLASSIFY THRU CLASSIFY-EXIT.
       DO-READ-EXIT.
           EXIT.
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
