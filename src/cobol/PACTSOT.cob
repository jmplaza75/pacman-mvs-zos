      * PACTSOT : MVS-RT BATCH TEST DRIVER FOR THE PACTSO CLOCK (NOT
      * PART OF THE GAME). TIME, THEN 20 ABSOLUTE DEADLINES 150 MS
      * APART (DLWT), THEN ONE DEADLINE ALREADY PASSED. ONE LINE EACH:
      *   TSOT NN DL=.......... NOW=.......... RC=....
      * (MS SINCE THE FIRST TIME CALL; LATE LINE: TSOT LA ...).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACTSOT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  T-OP                  PIC X(4).
       01  T-RC                  PIC S9(4) COMP.
       01  T-NOW                 PIC S9(9) COMP.
       01  T-DL                  PIC S9(9) COMP.
       01  T-I                   PIC 99 VALUE 0.
       01  T-LINE.
           05  FILLER            PIC X(5) VALUE 'TSOT '.
           05  TL-I              PIC XX.
           05  FILLER            PIC X(4) VALUE ' DL='.
           05  TL-DL             PIC -(9)9.
           05  FILLER            PIC X(5) VALUE ' NOW='.
           05  TL-NOW            PIC -(9)9.
           05  FILLER            PIC X(4) VALUE ' RC='.
           05  TL-RC             PIC -(4)9.
       01  T-NUM                 PIC 99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           MOVE 'TIME' TO T-OP.
           CALL 'PACTSO' USING T-OP T-RC T-NOW.
           MOVE T-NOW TO T-DL.
           PERFORM ONE-DEADLINE 20 TIMES.
           COMPUTE T-DL = T-NOW - 100.
           MOVE 'LA' TO TL-I.
           PERFORM WAIT-AND-SHOW.
           STOP RUN.
       ONE-DEADLINE.
           ADD 1 TO T-I.
           MOVE T-I TO T-NUM.
           MOVE T-NUM TO TL-I.
           ADD 150 TO T-DL.
           PERFORM WAIT-AND-SHOW.
       WAIT-AND-SHOW.
           MOVE 'DLWT' TO T-OP.
           CALL 'PACTSO' USING T-OP T-RC T-DL.
           MOVE T-RC TO TL-RC.
           MOVE 'TIME' TO T-OP.
           CALL 'PACTSO' USING T-OP T-RC T-NOW.
           MOVE T-DL TO TL-DL.
           MOVE T-NOW TO TL-NOW.
           DISPLAY T-LINE.
