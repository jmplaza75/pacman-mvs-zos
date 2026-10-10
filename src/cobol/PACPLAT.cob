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
      * (HIGHLIGHT = QCODE X'87' IN THE QUERY REPLY). MVS-G4: THE
      * REPLY IS PARSED BY PACQRY (PURE); REQ-GLYPHS A/G/B/C IN, G/B/C
      * OUT (AUTO = G ONLY WITH GE + CP310 IN THE REPLY). MVS-GS:
      * REQ-SCALE A/4/3/T IN, 4/3/T/N OUT: SCALING NEEDS TSC/TSD,
      * HIGHLIGHT Y AND GLYPHS G (FROM THE SAME QUERY, NO NEW ONE); AUTO
      * = 4. OP WAIT (TSC ONLY): PACTSO PAUSE BEFORE THE END LINES.
      * MVS-GS GEOMETRY (D32): RIGHT AFTER FSON AND BEFORE THE QUERY ONE
      * SIZE SWITCH (PACFSIO SENX): X'7E'+WCC (ERASE/WRITE ALTERNATE)
      * WITH COLOR A AND CANVAS A, ELSE X'F5'+WCC (ERASE/WRITE, 80X24).
      * THE ALTERNATE SIZE COMES FROM THE SAME REPLY (PACQRY) INTO
      * REQ-CW/REQ-CH. THE FIRST FULL SCREEN STAYS A SEND (FULLSCR, NOT
      * HELD AFTER THE QUERY, D28); LATER FULL SCREENS GO BY SENX WITH
      * THE SAME COMMAND (SIZE RE-ESTABLISHED AFTER CLEAR / PA2).
      * TSD: CANVAS W X T M U L SIMULATE A BUFFER; TSX LINES SHOW THE
      * TRANSPORT DECISIONS.
      * MVS-RT (D33): POLL = ONE NON-BLOCKING READ (PACFSIO POLL; NONE =
      * REQ-INKEY N); RECV/POLL KEEP THE AID BYTE IN REQ-AID; REALTIME
      * NEVER USES THE RECT IDLE POLLING (BLOCKING RECV BEFORE THE START
      * AND IN PAUSE). CLOK = MILLISECONDS IN REQ-TIME (PACTSO TIME);
      * WDLN = REQ-TIME + RT-PERIOD (WHOLE PERIODS ALREADY MISSED ARE
      * SKIPPED), THEN WAIT UNTIL IT (PACTSO DLWT).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACPLAT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  TSO-OP                PIC X(4) VALUE 'CLS '.
       01  TSO-WAIT              PIC X(4) VALUE 'WAIT'.
       01  TSO-RC                PIC S9(4) COMP.
       01  TSO-TIME              PIC X(4) VALUE 'TIME'.
       01  TSO-DLWT              PIC X(4) VALUE 'DLWT'.
       01  RT-PERIOD             PIC S9(9) COMP VALUE +150.
       01  RT-LIM                PIC S9(9) COMP.
       01  RT-NOW                PIC S9(9) COMP.
       01  RT-NEXT               PIC S9(9) COMP.
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
       01  WS-V                  PIC 9(4).
       01  WS-O                  PIC 99.
       01  WS-Q                  PIC 99.
       01  WS-R                  PIC 99.
       01  WS-I                  PIC 99.
       01  WS-STOP               PIC 9.
       01  HAS-COLOUR            PIC 9.
       01  HAS-HILITE            PIC 9.
       01  HAS-GE                PIC 9 VALUE 0.
       01  QRY-OUT.
           05  QO-COLOUR         PIC 9.
           05  QO-HILITE         PIC 9.
           05  QO-GE             PIC 9.
           05  QO-AW             PIC 999.
           05  QO-AH             PIC 999.
       01  WS-IDLE               PIC 9(4) VALUE 0.
       01  CV-CMD                PIC 9(4) VALUE 245.
       01  FULL-SENT             PIC 9 VALUE 0.
       01  SX-AREA.
           05  SX-CMD            PIC X.
           05  SX-DATA           PIC X(2048).
       01  SX-LEN                PIC S9(4) COMP.
       01  TSX-SW.
           05  FILLER            PIC X(11) VALUE 'TSX SWITCH '.
           05  TS-CMD            PIC XX.
           05  FILLER            PIC X VALUE ' '.
           05  TS-W              PIC 999.
           05  FILLER            PIC X VALUE 'X'.
           05  TS-H              PIC 999.
       01  TSX-FULL.
           05  FILLER            PIC X(9) VALUE 'TSX FULL '.
           05  TF-CMD            PIC X(5).
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
               PERFORM DO-FSOF THRU DO-FSOF-EXIT
           ELSE IF REQ-OP = 'WAIT' AND REQ-MODE = 'TSC'
               CALL 'PACTSO' USING TSO-WAIT TSO-RC
           ELSE IF REQ-OP = 'POLL'
               PERFORM DO-POLL THRU DO-POLL-EXIT
           ELSE IF REQ-OP = 'CLOK'
               CALL 'PACTSO' USING TSO-TIME TSO-RC REQ-TIME
           ELSE IF REQ-OP = 'WDLN'
               PERFORM DO-WDLN.
           GOBACK.
       DO-INIT.
           IF REQ-MODE NOT = 'TSO' AND REQ-MODE NOT = 'TSD'
               MOVE 'BAT' TO REQ-MODE.
           MOVE 80 TO REQ-CW.
           MOVE 24 TO REQ-CH.
           IF REQ-MODE = 'TSD'
               PERFORM SIM-CANVAS.
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
      * MVS-G4: GLYPH PROFILE G/B ONLY IN TSC/TSD; A BECOMES G ONLY WHEN
      * THE QUERY REPLY ANNOUNCED GE + CP310 (NO QUERY: COLOR YES = C).
           IF REQ-GLYPHS = 'A' AND REQ-MODE = 'TSC' AND HAS-GE = 1
               MOVE 'G' TO REQ-GLYPHS.
           IF REQ-MODE NOT = 'TSC' AND REQ-MODE NOT = 'TSD'
               MOVE 'C' TO REQ-GLYPHS.
           IF REQ-GLYPHS NOT = 'G' AND REQ-GLYPHS NOT = 'B'
               MOVE 'C' TO REQ-GLYPHS.
      * MVS-GS: SCALED ONLY WITH COLOUR (TSC/TSD), HIGHLIGHT (SPRITE
      * BODIES ARE REVERSE VIDEO) AND THE GRAPHIC GLYPHS (GE + CP310),
      * ALL AS ALREADY RESOLVED ABOVE; OTHERWISE THE G4 RENDERER.
           IF REQ-SCALE = 'A'
               MOVE '4' TO REQ-SCALE.
           IF REQ-SCALE NOT = '4' AND REQ-SCALE NOT = '3'
                             AND REQ-SCALE NOT = 'T'
               MOVE 'N' TO REQ-SCALE.
           IF REQ-MODE NOT = 'TSC' AND REQ-MODE NOT = 'TSD'
               MOVE 'N' TO REQ-SCALE.
           IF REQ-HILITE NOT = 'Y' OR REQ-GLYPHS NOT = 'G'
               MOVE 'N' TO REQ-SCALE.
       DO-INIT-EXIT.
           EXIT.
       TRY-COLOUR.
           MOVE 'FSON' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           IF FS-RC NOT = 0
               GO TO TRY-COLOUR-EXIT.
           MOVE 1 TO FS-ACTIVE.
      * MVS-GS: THE BUFFER SIZE IS SET BEFORE THE QUERY (D32).
           MOVE 245 TO CV-CMD.
           IF REQ-COLOR = 'A' AND REQ-CANVAS = 'A'
               MOVE 126 TO CV-CMD.
           MOVE 195 TO HEXN.
           MOVE HX-B TO SX-DATA.
           MOVE 1 TO SX-LEN.
           PERFORM SEND-SX.
           IF FS-RC NOT = 0
               PERFORM DO-FSOF THRU DO-FSOF-EXIT
               GO TO TRY-COLOUR-EXIT.
           IF REQ-COLOR = 'Y'
               MOVE 'TSC' TO REQ-MODE
               GO TO TRY-COLOUR-EXIT.
           MOVE 'QRY ' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           MOVE 0 TO HAS-COLOUR.
           MOVE 0 TO HAS-HILITE.
           MOVE 0 TO HAS-GE.
           IF FS-RC = 0
               CALL 'PACQRY' USING IN-AREA FS-LEN QRY-OUT
               MOVE QO-COLOUR TO HAS-COLOUR
               MOVE QO-HILITE TO HAS-HILITE
               MOVE QO-GE TO HAS-GE.
           IF FS-RC = 0 AND CV-CMD = 126
               MOVE QO-AW TO REQ-CW
               MOVE QO-AH TO REQ-CH.
           IF HAS-COLOUR = 1 AND HAS-HILITE = 1 AND REQ-HILITE = 'A'
               MOVE 'Y' TO REQ-HILITE.
           IF HAS-COLOUR = 1
               MOVE 'TSC' TO REQ-MODE
           ELSE
               PERFORM DO-FSOF THRU DO-FSOF-EXIT.
      * A BUFFER WIDER THAN 170 COLUMNS CANNOT HOLD THE 80 X 24 SCREENS
      * WITH 12-BIT ADDRESSES: LINE MODE (SAFE FALLBACK).
           IF REQ-MODE = 'TSC' AND REQ-CW > 170
               PERFORM FALL-BACK.
       TRY-COLOUR-EXIT.
           EXIT.
       DO-SEND.
           IF REQ-MODE = 'TSD'
               PERFORM TSD-FULL
               PERFORM PRINT-STREAM THRU PRINT-STREAM-EXIT
               GO TO DO-SEND-EXIT.
           IF REQ-MODE NOT = 'TSC'
               GO TO DO-SEND-EXIT.
           IF DS-KIND NOT = 'F'
               PERFORM SEND-PART THRU SEND-PART-EXIT
               GO TO DO-SEND-EXIT.
      * MVS-GS: ONLY THE FIRST FULL SCREEN IS A SEND (FULLSCR); LATER
      * ONES ARE ERASE/WRITE (ALTERNATE) + THE STREAM BY SENX.
           IF FULL-SENT = 1
               MOVE DS-BUF TO SX-DATA
               MOVE DS-LEN TO SX-LEN
               PERFORM SEND-SX
               IF FS-RC NOT = 0
                   PERFORM FALL-BACK
                   GO TO DO-SEND-EXIT
               ELSE
                   GO TO DO-SEND-EXIT.
           MOVE 1 TO FULL-SENT.
           MOVE 'SEND' TO FS-OP.
           MOVE DS-LEN TO FS-LEN.
           CALL 'PACFSIO' USING FS-OP DS-BUF FS-LEN FS-RC.
           IF FS-RC NOT = 0
               PERFORM FALL-BACK.
       DO-SEND-EXIT.
           EXIT.
       SEND-SX.
      * SENX: COMMAND CV-CMD + SX-LEN BYTES OF SX-DATA (TPUT NOEDIT).
           MOVE CV-CMD TO HEXN.
           MOVE HX-B TO SX-CMD.
           COMPUTE FS-LEN = SX-LEN + 1.
           MOVE 'SENX' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP SX-AREA FS-LEN FS-RC.
       TSD-FULL.
      * TSD: WHICH TRANSPORT A FULL SCREEN WOULD USE (TSX LINE).
           IF DS-KIND = 'F'
               MOVE 'FIRST' TO TF-CMD
               IF FULL-SENT = 1
                   PERFORM TSD-CMD
                   DISPLAY TSX-FULL
               ELSE
                   MOVE 1 TO FULL-SENT
                   DISPLAY TSX-FULL.
           MOVE 0 TO WS-I.
       TSD-CMD.
           MOVE 'F5' TO TF-CMD.
           IF CV-CMD = 126
               MOVE '7E' TO TF-CMD.
           MOVE 0 TO WS-I.
       SIM-CANVAS.
      * TSD (NO QUERY): CANVAS LETTERS SIMULATE THE ALTERNATE BUFFER.
           MOVE 245 TO CV-CMD.
           IF REQ-CANVAS = 'W'
               MOVE 120 TO REQ-CW
               MOVE 27 TO REQ-CH.
           IF REQ-CANVAS = 'X'
               MOVE 132 TO REQ-CW
               MOVE 27 TO REQ-CH.
           IF REQ-CANVAS = 'T'
               MOVE 80 TO REQ-CW
               MOVE 43 TO REQ-CH.
           IF REQ-CANVAS = 'M'
               MOVE 80 TO REQ-CW
               MOVE 32 TO REQ-CH.
           IF REQ-CANVAS = 'U'
               MOVE 100 TO REQ-CW
               MOVE 25 TO REQ-CH.
           IF REQ-CANVAS = 'L'
               MOVE 160 TO REQ-CW
               MOVE 30 TO REQ-CH.
           IF REQ-CW NOT = 80 OR REQ-CH NOT = 24
               MOVE 126 TO CV-CMD.
           PERFORM TSD-CMD.
           MOVE TF-CMD TO TS-CMD.
           MOVE REQ-CW TO TS-W.
           MOVE REQ-CH TO TS-H.
           DISPLAY TSX-SW.
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
           IF REQ-ANIM = 'Y' AND REQ-REDRAW = 'P' AND REQ-PLAY NOT = 'R'
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
           PERFORM PARSE-IN THRU PARSE-IN-EXIT.
       DO-RECV-EXIT.
           EXIT.
       PARSE-IN.
           MOVE 'P' TO REQ-INKEY.
           MOVE IN-CH (1) TO REQ-AID.
           MOVE 1 TO WS-K.
           PERFORM BYTE-VAL.
           IF WS-V NOT = 125
               GO TO PARSE-IN-EXIT.
           MOVE 'E' TO REQ-INKEY.
      * READ MODIFIED: AID, CURSOR(2), SBA X'11'(17) + ADDRESS(2), DATA.
           MOVE 4 TO WS-K.
           PERFORM BYTE-VAL.
           IF FS-LEN > 6 AND WS-V = 17
               PERFORM COPY-TEXT THRU COPY-TEXT-EXIT
                   VARYING WS-I FROM 1 BY 1 UNTIL WS-I > 8.
       PARSE-IN-EXIT.
           EXIT.
       DO-POLL.
      * MVS-RT: ONE NON-BLOCKING READ. N = NOTHING, E / P AS RECV, X =
      * ERROR (NOW BACK IN TSO LINE MODE).
           MOVE SPACES TO REQ-INTEXT.
           MOVE 'X' TO REQ-INKEY.
           IF REQ-MODE NOT = 'TSC'
               GO TO DO-POLL-EXIT.
           MOVE 'POLL' TO FS-OP.
           CALL 'PACFSIO' USING FS-OP IN-AREA FS-LEN FS-RC.
           IF FS-RC NOT = 0
               PERFORM FALL-BACK
               GO TO DO-POLL-EXIT.
           MOVE 'N' TO REQ-INKEY.
           IF FS-LEN > 0
               PERFORM PARSE-IN THRU PARSE-IN-EXIT.
       DO-POLL-EXIT.
           EXIT.
       DO-WDLN.
      * MVS-RT ABSOLUTE DEADLINES: NEXT = LAST DEADLINE + PERIOD; WHOLE
      * PERIODS ALREADY MISSED ARE SKIPPED; WAIT ONLY FOR THE REMAINDER.
           COMPUTE RT-NEXT = REQ-TIME + RT-PERIOD.
           CALL 'PACTSO' USING TSO-TIME TSO-RC RT-NOW.
           COMPUTE RT-LIM = RT-NOW - RT-PERIOD.
           PERFORM SKIP-PERIOD UNTIL RT-NEXT > RT-LIM.
           MOVE RT-NEXT TO REQ-TIME.
           CALL 'PACTSO' USING TSO-DLWT TSO-RC REQ-TIME.
       SKIP-PERIOD.
           ADD RT-PERIOD TO RT-NEXT.
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
           MOVE 'C' TO REQ-GLYPHS.
           MOVE 'N' TO REQ-SCALE.
           MOVE 80 TO REQ-CW.
           MOVE 24 TO REQ-CH.
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
