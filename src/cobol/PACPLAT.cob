      * PACPLAT : PLATFORM ADAPTER (MVS 3.8J). OPS : INIT FINI CLS
      * SEND RECV FSOF.  INIT validates REQ-MODE (BAT, TSO, TSD) and,
      * for TSO with REQ-COLOR A(UTO)/Y(ES), tries the TSC colour mode:
      * full-screen on (PACFSIO FSON); AUTO also needs QCode X'86' in
      * the Query Reply. Any failure leaves TSO line mode (monochrome
      * fallback). SEND/RECV move one TSC screen / one inbound; in TSD
      * (batch dry run) SEND prints the data stream in hex. An error in
      * TSC restores line mode and falls back to TSO. FSOF and FINI
      * always restore line mode if full-screen is active (PACFSIO
      * also restores it from an ESTAE exit on abend). CLS (TSO only)
      * starts a fresh line-mode screen via PACTSO. GAME/MAP/AI never
      * see any of this. MVS-G2: REQ-HILITE A/Y/N IN, Y/N OUT
      * (HIGHLIGHT = QCODE X'87' IN THE QUERY REPLY).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACPLAT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  TSO-OP                PIC X(4) VALUE 'CLS '.
       01  TSO-RC                PIC S9(4) COMP.
       01  FS-OP                 PIC X(4).
       01  FS-LEN                PIC S9(4) COMP.
       01  FS-RC                 PIC S9(4) COMP.
       01  FS-ACTIVE             PIC 9 VALUE 0.
       01  IN-AREA.
           05  IN-CH             PIC X OCCURS 2048 TIMES.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  HEX-LINE.
           05  FILLER            PIC X(4) VALUE 'TSD '.
           05  HL-CH             PIC X OCCURS 64 TIMES.
       01  LEN-LINE.
           05  FILLER            PIC X(13) VALUE 'TSD FRAME LEN'.
           05  LL-LEN            PIC 9(4).
       01  WS-K                  PIC 9(4).
       01  WS-P                  PIC 9(4).
       01  WS-V                  PIC 9(4).
       01  WS-L                  PIC 9(4).
       01  WS-ID                 PIC 9(4).
       01  WS-QC                 PIC 9(4).
       01  WS-LIM                PIC 9(4).
       01  WS-O                  PIC 99.
       01  WS-Q                  PIC 99.
       01  WS-R                  PIC 99.
       01  WS-I                  PIC 99.
       01  WS-STOP               PIC 9.
       01  HAS-COLOUR            PIC 9.
       01  HAS-HILITE            PIC 9.
       01  WS-IDLE               PIC 9(4) VALUE 0.
       LINKAGE SECTION.
       01  PAC-REQ COPY PACREQ.
       01  PAC-DS COPY PACDS.
       PROCEDURE DIVISION USING PAC-REQ PAC-DS.
       MAIN-PARA.
           IF REQ-OP = 'INIT'
               PERFORM DO-INIT THRU DO-INIT-EXIT
           ELSE IF REQ-OP = 'FINI'
               PERFORM DO-FSOF THRU DO-FSOF-EXIT
               MOVE 0 TO RETURN-CODE
           ELSE IF REQ-OP = 'CLS ' AND REQ-MODE = 'TSO'
               CALL 'PACTSO' USING TSO-OP TSO-RC
           ELSE IF REQ-OP = 'SEND'
               PERFORM DO-SEND THRU DO-SEND-EXIT
           ELSE IF REQ-OP = 'RECV'
               PERFORM DO-RECV THRU DO-RECV-EXIT
           ELSE IF REQ-OP = 'FSOF'
               PERFORM DO-FSOF THRU DO-FSOF-EXIT.
           GOBACK.
       DO-INIT.
           IF REQ-MODE NOT = 'TSO' AND REQ-MODE NOT = 'TSD'
               MOVE 'BAT' TO REQ-MODE.
           IF REQ-MODE = 'TSO'
                   AND (REQ-COLOR = 'A' OR REQ-COLOR = 'Y')
               PERFORM TRY-COLOUR THRU TRY-COLOUR-EXIT.
      * MVS-G2: HIGHLIGHT ONLY IN TSC (OR THE TSD DRY RUN) AND ONLY WHEN
      * ASKED: Y, OR A WITH QCODE X'87' IN THE QUERY REPLY (SET IN
      * TRY-COLOUR). ANYTHING ELSE IS N.
           IF REQ-MODE NOT = 'TSC' AND REQ-MODE NOT = 'TSD'
               MOVE 'N' TO REQ-HILITE.
           IF REQ-HILITE NOT = 'Y'
               MOVE 'N' TO REQ-HILITE.
      * MVS-G3: ANIM Y (A BECOMES Y IN TSC: PARTIAL SEND IS PROVEN,
      * SO THERE IS NOTHING TO DETECT), REDRAW P (PARTIAL) ONLY IN
      * TSC/TSD; EVERYTHING ELSE IS ANIM N / REDRAW F (FULL).
           IF REQ-ANIM = 'A' AND REQ-MODE = 'TSC'
               MOVE 'Y' TO REQ-ANIM.
           IF REQ-MODE NOT = 'TSC' AND REQ-MODE NOT = 'TSD'
               MOVE 'N' TO REQ-ANIM
               MOVE 'F' TO REQ-REDRAW.
           IF REQ-ANIM NOT = 'Y'
               MOVE 'N' TO REQ-ANIM.
           IF REQ-REDRAW NOT = 'P'
               MOVE 'F' TO REQ-REDRAW.
       DO-INIT-EXIT.
           EXIT.
       TRY-COLOUR.
           MOVE 'FSON' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           IF FS-RC NOT = 0
               GO TO TRY-COLOUR-EXIT.
           MOVE 1 TO FS-ACTIVE.
           IF REQ-COLOR = 'Y'
               MOVE 'TSC' TO REQ-MODE
               GO TO TRY-COLOUR-EXIT.
           MOVE 'QRY ' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           MOVE 0 TO HAS-COLOUR.
           MOVE 0 TO HAS-HILITE.
           IF FS-RC = 0
               PERFORM FIND-COLOUR THRU FIND-COLOUR-EXIT.
           IF HAS-COLOUR = 1 AND HAS-HILITE = 1 AND REQ-HILITE = 'A'
               MOVE 'Y' TO REQ-HILITE.
           IF HAS-COLOUR = 1
               MOVE 'TSC' TO REQ-MODE
           ELSE
               PERFORM DO-FSOF THRU DO-FSOF-EXIT.
       TRY-COLOUR-EXIT.
           EXIT.
       FIND-COLOUR.
      * QUERY REPLY = AID X'88' (136) + STRUCTURED FIELDS: LENGTH(2),
      * X'81' (129), QCODE. COLOUR SUPPORT = QCODE X'86' (134).
           MOVE 1 TO WS-K.
           PERFORM BYTE-VAL.
           IF WS-V NOT = 136
               GO TO FIND-COLOUR-EXIT.
           MOVE 2 TO WS-P.
           MOVE 0 TO WS-STOP.
           PERFORM NEXT-SF THRU NEXT-SF-EXIT UNTIL WS-STOP = 1.
       FIND-COLOUR-EXIT.
           EXIT.
       NEXT-SF.
           COMPUTE WS-LIM = WS-P + 3.
           IF WS-LIM > FS-LEN
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
               MOVE 1 TO HAS-COLOUR.
           IF WS-ID = 129 AND WS-QC = 135
               MOVE 1 TO HAS-HILITE.
           IF WS-L < 4
               MOVE 1 TO WS-STOP
           ELSE
               ADD WS-L TO WS-P.
       NEXT-SF-EXIT.
           EXIT.
       DO-SEND.
           IF REQ-MODE = 'TSD'
               PERFORM PRINT-STREAM THRU PRINT-STREAM-EXIT
               GO TO DO-SEND-EXIT.
           IF REQ-MODE NOT = 'TSC'
               GO TO DO-SEND-EXIT.
           IF DS-KIND NOT = 'F'
               PERFORM SEND-PART THRU SEND-PART-EXIT
               GO TO DO-SEND-EXIT.
           MOVE 'SEND' TO FS-OP.
           MOVE DS-LEN TO FS-LEN.
           CALL 'PACFSIO' USING FS-OP DS-BUF FS-LEN FS-RC.
           IF FS-RC NOT = 0
               PERFORM FALL-BACK.
       DO-SEND-EXIT.
           EXIT.
       SEND-PART.
      * MVS-G3 PARTIAL SEND (WRITE X'F1' + TPUT NOEDIT, PROBE E6). A
      * FAILURE IS NOT FATAL: FULL REDRAW WITHOUT ANIMATION FROM NOW ON
      * AND THE CALLER IS TOLD TO SEND THE WHOLE SCREEN (REQ-SENDST R).
           MOVE 'SENP' TO FS-OP.
           MOVE DS-LEN TO FS-LEN.
           CALL 'PACFSIO' USING FS-OP DS-BUF FS-LEN FS-RC.
           IF FS-RC NOT = 0
               MOVE 'R' TO REQ-SENDST
               MOVE 'F' TO REQ-REDRAW
               MOVE 'N' TO REQ-ANIM.
       SEND-PART-EXIT.
           EXIT.
       DO-RECV.
      * REQ-INKEY: E = ENTER (REQ-INTEXT = TYPED FIELD), P = ANY OTHER
      * AID (PA2 RESHOW ...), X = ERROR (NOW BACK IN TSO LINE MODE).
           MOVE SPACES TO REQ-INTEXT.
           MOVE 'X' TO REQ-INKEY.
           IF REQ-MODE NOT = 'TSC'
               GO TO DO-RECV-EXIT.
           MOVE 'RECV' TO FS-OP.
           IF REQ-ANIM = 'Y' AND REQ-REDRAW = 'P'
               MOVE 'RECT' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           IF FS-RC NOT = 0
               PERFORM FALL-BACK
               GO TO DO-RECV-EXIT.
      * MVS-G3 IDLE TICK: RECT = ONE READ + 0.5 S WAIT. EMPTY = TELL THE
      * CALLER (REQ-INKEY T); AFTER 5 MINUTES OF NOTHING AS BEFORE.
           MOVE 0 TO WS-STOP.
           IF FS-OP = 'RECT' AND FS-LEN < 1
               ADD 1 TO WS-IDLE
               MOVE 'T' TO REQ-INKEY
               MOVE 1 TO WS-STOP.
           IF WS-STOP = 1 AND WS-IDLE > 599
               PERFORM FALL-BACK
               MOVE 'X' TO REQ-INKEY.
           IF WS-STOP = 1
               GO TO DO-RECV-EXIT.
           MOVE 0 TO WS-IDLE.
           IF FS-LEN < 1
               PERFORM FALL-BACK
               GO TO DO-RECV-EXIT.
           MOVE 'P' TO REQ-INKEY.
           MOVE 1 TO WS-K.
           PERFORM BYTE-VAL.
           IF WS-V NOT = 125
               GO TO DO-RECV-EXIT.
           MOVE 'E' TO REQ-INKEY.
      * READ MODIFIED: AID, CURSOR(2), SBA X'11'(17) + ADDRESS(2), DATA.
           MOVE 4 TO WS-K.
           PERFORM BYTE-VAL.
           IF FS-LEN > 6 AND WS-V = 17
               PERFORM COPY-TEXT THRU COPY-TEXT-EXIT
                   VARYING WS-I FROM 1 BY 1 UNTIL WS-I > 8.
       DO-RECV-EXIT.
           EXIT.
       COPY-TEXT.
           COMPUTE WS-K = WS-I + 6.
           IF WS-K NOT > FS-LEN
               MOVE IN-CH (WS-K) TO REQ-INTEXT-CH (WS-I).
       COPY-TEXT-EXIT.
           EXIT.
       DO-FSOF.
           IF FS-ACTIVE = 1
               MOVE 'FSOF' TO FS-OP
               CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC
               MOVE 0 TO FS-ACTIVE.
       DO-FSOF-EXIT.
           EXIT.
       FALL-BACK.
           PERFORM DO-FSOF THRU DO-FSOF-EXIT.
           MOVE 'TSO' TO REQ-MODE.
           MOVE 'N' TO REQ-HILITE.
           MOVE 'N' TO REQ-ANIM.
           MOVE 'F' TO REQ-REDRAW.
       BYTE-VAL.
           MOVE IN-CH (WS-K) TO HX-B.
           MOVE HEXN TO WS-V.
       PRINT-STREAM.
      * TSD DRY RUN: THE WHOLE DATA STREAM, 32 BYTES PER LINE IN HEX.
           MOVE DS-LEN TO LL-LEN.
           DISPLAY LEN-LINE.
           MOVE 1 TO WS-K.
           PERFORM PRINT-LINE UNTIL WS-K > DS-LEN.
       PRINT-STREAM-EXIT.
           EXIT.
       PRINT-LINE.
           MOVE SPACES TO HEX-LINE.
           MOVE 'TSD ' TO HEX-LINE.
           MOVE 0 TO WS-O.
           PERFORM PRINT-BYTE UNTIL WS-O > 62 OR WS-K > DS-LEN.
           DISPLAY HEX-LINE.
       PRINT-BYTE.
           MOVE DS-BYTE (WS-K) TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-Q) TO HL-CH (WS-O).
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-R) TO HL-CH (WS-O).
           ADD 1 TO WS-K.
