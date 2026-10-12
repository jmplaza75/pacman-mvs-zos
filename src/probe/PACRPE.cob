      * PACRPE : MVS-RP RP.0 ESTAE LIVE TEST DRIVER (D39, DOCS/RP-
      * POLISH.MD 7). NEVER CALLED BY THE GAME; LINKED WITH THE
      * UNCHANGED PRODUCTION PACFSIO AND PACHSIO. PARM = THE CASE:
      *   E1  FSON (PACFSIO ESTAE), A SCREEN, ENTER, THEN A FORCED 0C7
      *       IN FULL-SCREEN MODE: THE EXIT MUST RESTORE LINE MODE.
      *   E2  AS E1, BUT PACHSIO READ (DD PACHS) RUNS FIRST, SO ITS OWN
      *       ESTAE IS CREATED AND DELETED BEFORE FSON AND THE ABEND.
      *   E3  CONTROL: AS E1, BUT FSOF (LINE MODE, ESTAE CANCELLED)
      *       BEFORE THE 0C7: A PLAIN LINE-MODE ABEND.
      * BATCH (NOT A TSO SESSION): NOTHING IS SENT, THE 0C7 IS STILL
      * FORCED (THE DECK PROVES THE TRIGGER: STEP ENDS S0C7).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACRPE.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  FS-OP                 PIC X(4).
       01  FS-LEN                PIC S9(4) COMP VALUE +0.
       01  FS-RC                 PIC S9(4) COMP VALUE +0.
       01  FS-BUF.
           05  FS-CH             PIC X OCCURS 2048 TIMES.
       01  HS-OP                 PIC X(4) VALUE 'READ'.
       01  HS-RC                 PIC S9(4) COMP VALUE +0.
       01  HS-DDN                PIC X(8) VALUE 'PACHS'.
       01  HS-REC                PIC X(80).
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  WS-P                  PIC 9(4) VALUE 0.
       01  WS-K                  PIC 99 VALUE 0.
       01  WS-A1                 PIC 999 VALUE 0.
       01  WS-A2                 PIC 999 VALUE 0.
       01  WS-TXT.
           05  WS-TCH            PIC X OCCURS 60 TIMES.
       01  WS-TLEN               PIC 99 VALUE 0.
       01  WS-CASE               PIC XX VALUE 'E1'.
       01  L-HEAD.
           05  FILLER            PIC X(35) VALUE
               'PACMAN RP.0 ESTAE LIVE TEST - CASE '.
           05  LH-CASE           PIC XX.
       01  L-HS.
           05  FILLER            PIC X(16) VALUE 'PACHSIO READ RC='.
           05  LS-RC             PIC 9(4).
           05  FILLER            PIC X(18) VALUE
               ' (E2 ONLY, ELSE 0)'.
       01  L-FS.
           05  FILLER            PIC X(13) VALUE 'RPE FSON RC='.
           05  LF-RC             PIC 9(4).
       01  BAD-AREA.
           05  BAD-X             PIC XX VALUE 'ZZ'.
       01  BAD-N REDEFINES BAD-AREA PIC S999 COMPUTATIONAL-3.
       LINKAGE SECTION.
       01  PARM-AREA.
           05  PARM-LEN          PIC S9(4) COMP.
           05  PARM-CASE         PIC XX.
       PROCEDURE DIVISION USING PARM-AREA.
       MAIN-PARA.
           IF PARM-LEN > 1
               MOVE PARM-CASE TO WS-CASE.
           IF WS-CASE NOT = 'E2' AND WS-CASE NOT = 'E3'
               MOVE 'E1' TO WS-CASE.
      * NO LINE OUTPUT BEFORE FSON (RP.0 LIVE 1: A LINE WRITTEN BEFORE
      * THE FULL-SCREEN SWITCH MADE TSO HOLD THE SCREEN WITH '***').
           IF WS-CASE = 'E2'
               CALL 'PACHSIO' USING HS-OP HS-RC HS-DDN HS-REC.
           MOVE HS-RC TO LS-RC.
           MOVE 'FSON' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP FS-BUF FS-LEN FS-RC.
           IF FS-RC NOT = 0
               MOVE FS-RC TO LF-RC
               DISPLAY 'RPE CASE ' WS-CASE ' START'
               DISPLAY L-FS
               DISPLAY L-HS
               DISPLAY 'RPE NOT A TSO SESSION: NOTHING SENT'
               GO TO FORCE-0C7.
           PERFORM BUILD-SCREEN.
           MOVE 'SEND' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP FS-BUF FS-LEN FS-RC.
           MOVE 'RECV' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP FS-BUF FS-LEN FS-RC.
           IF WS-CASE = 'E3'
               MOVE 'FSOF' TO FS-OP
               CALL 'PACFSIO' USING FS-OP FS-BUF FS-LEN FS-RC
               DISPLAY 'RPE E3 LINE MODE RESTORED, FORCING 0C7'.
       FORCE-0C7.
      * 'ZZ' IS NOT PACKED DECIMAL: THE ADD (AP) RAISES A DATA
      * EXCEPTION, SYSTEM ABEND 0C7.
           ADD 1 TO BAD-N.
           DISPLAY 'RPE ERROR: NO ABEND'.
           STOP RUN.
       BUILD-SCREEN.
      * WCC C3, THEN FIVE LINES AT COLUMN 2 (NO FIELDS: ENTER = AID).
           MOVE 0 TO WS-P.
           MOVE 195 TO HEXN.
           PERFORM PUT-B.
           MOVE 193 TO WS-A1.
           MOVE 209 TO WS-A2.
           PERFORM PUT-SBA.
           MOVE WS-CASE TO LH-CASE.
           MOVE L-HEAD TO WS-TXT.
           MOVE 37 TO WS-TLEN.
           PERFORM PUT-T.
           MOVE 195 TO WS-A1.
           MOVE 241 TO WS-A2.
           PERFORM PUT-SBA.
           MOVE L-HS TO WS-TXT.
           MOVE 38 TO WS-TLEN.
           PERFORM PUT-T.
           MOVE 198 TO WS-A1.
           MOVE 209 TO WS-A2.
           PERFORM PUT-SBA.
           MOVE 'PRESS ENTER: THE PROGRAM FORCES A 0C7 ABEND.'
               TO WS-TXT.
           MOVE 44 TO WS-TLEN.
           PERFORM PUT-T.
           MOVE 199 TO WS-A1.
           MOVE 97 TO WS-A2.
           PERFORM PUT-SBA.
           MOVE 'PASS: LINE MODE, ABEND MESSAGE, THEN READY.'
               TO WS-TXT.
           MOVE 44 TO WS-TLEN.
           PERFORM PUT-T.
           MOVE 200 TO WS-A1.
           MOVE 241 TO WS-A2.
           PERFORM PUT-SBA.
           MOVE 'E3 = CONTROL: LINE MODE FIRST (FSOF), THEN 0C7.'
               TO WS-TXT.
           MOVE 47 TO WS-TLEN.
           PERFORM PUT-T.
           MOVE WS-P TO FS-LEN.
       PUT-SBA.
           MOVE 17 TO HEXN.
           PERFORM PUT-B.
           MOVE WS-A1 TO HEXN.
           PERFORM PUT-B.
           MOVE WS-A2 TO HEXN.
           PERFORM PUT-B.
       PUT-B.
           ADD 1 TO WS-P.
           MOVE HX-B TO FS-CH (WS-P).
       PUT-T.
           PERFORM PUT-TC VARYING WS-K FROM 1 BY 1
               UNTIL WS-K > WS-TLEN.
       PUT-TC.
           ADD 1 TO WS-P.
           MOVE WS-TCH (WS-K) TO FS-CH (WS-P).
