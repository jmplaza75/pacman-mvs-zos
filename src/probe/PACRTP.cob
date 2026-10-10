      * PACRTP : MVS-RT PROBE E14 (TIMING / INPUT), ISOLATED FROM PACMAN
      * LINKS THE UNCHANGED PACGAME/PACMAP/PACAI/PACSCR/PACPLAT/PACQRY/
      * PACFSIO/PACTSO AND THE PROBE-ONLY CLOCK SERVICE PACRTA (STCK,
      * DEADLINE WAIT, TGET NOWAIT, TPUT NOEDIT). PARM COL 1: Q = THE
      * COLOR(AUTO) QUERY PATH, N = COLOR(YES) HILITE(YES) GLYPHS(G)
      * (NO QUERY), B = BATCH (TSD 120X27: CLOCK + COMPOSE ONLY).
      * COL 2: A ALL, T TIMING ONLY, I INPUT ONLY.  COL 3: S = SHORT.
      * SEGMENTS: W D28 (SYNTHETIC FRAMES UNTIL THE FIRST AID + 10),
      * S SYNTHETIC / G GAME FRAMES PER PERIOD 100 150 175 200 250 MS,
      * I INPUT (200 MS, PF7 U PF8 D PF10 L PF11 R, PF3 ENDS), R
      * RESTORE-ONLY (F1 C2 AFTER AN AID), C CLOCK ONLY, K COMPOSE ONLY.
      * ABSOLUTE DEADLINES: NEXT = NEXT + P; MISSED DEADLINES SKIPPED
      * AND COUNTED. AT MOST ONE TERMINAL WRITE PER QUANTUM. ONE LOG
      * LINE PER QUANTUM / AID TO FILE E14LOG, WRITTEN AFTER EACH
      * SEGMENT (OUTSIDE THE TIMED LOOP).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACRTP.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT LOG-FILE ASSIGN TO UT-S-E14LOG.
       DATA DIVISION.
       FILE SECTION.
       FD  LOG-FILE
           RECORDING MODE IS F
           LABEL RECORDS ARE STANDARD
           BLOCK CONTAINS 39 RECORDS
           RECORD CONTAINS 80 CHARACTERS
           DATA RECORD IS LOG-REC.
       01  LOG-REC               PIC X(80).
       WORKING-STORAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       01  PAC-DS COPY PACDS.
       01  RT-OP                 PIC X(4).
       01  RT-ARG                PIC S9(9) COMP.
       01  RT-BUF.
           05  RB-CH             PIC X OCCURS 2048 TIMES.
       01  RT-RC                 PIC S9(4) COMP.
       01  T-DEAD                PIC S9(9) COMP.
       01  T-WAKE                PIC S9(9) COMP.
       01  T-A                   PIC S9(9) COMP.
       01  T-B                   PIC S9(9) COMP.
       01  T-C                   PIC S9(9) COMP.
       01  T-D                   PIC S9(9) COMP.
       01  P-US                  PIC S9(9) COMP.
       01  P-MS                  PIC 999.
       01  PER-DATA              PIC X(15) VALUE '100150175200250'.
       01  PER-TABLE REDEFINES PER-DATA.
           05  PER-MS            PIC 999 OCCURS 5 TIMES.
       01  DIR-DATA              PIC X(20) VALUE 'RRRRRRDDDDLLLLLLUUUU'.
       01  DIR-TABLE REDEFINES DIR-DATA.
           05  DIR-CH            PIC X OCCURS 20 TIMES.
       01  CODE-DATA.
           05  FILLER            PIC X(48) VALUE
               '064193194195196197198199200201074075076077078079'.
           05  FILLER            PIC X(48) VALUE
               '080209210211212213214215216217090091092093094095'.
           05  FILLER            PIC X(48) VALUE
               '096097226227228229230231232233106107108109110111'.
           05  FILLER            PIC X(48) VALUE
               '240241242243244245246247248249122123124125126127'.
       01  CODE-TABLE REDEFINES CODE-DATA.
           05  ADDR-CODE         PIC 999 OCCURS 64 TIMES.
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  QT-TABLE.
           05  QT-ENT            OCCURS 400 TIMES.
               10  QT-WAKE       PIC S9(9) COMP.
               10  QT-LATE       PIC S9(7) COMP.
               10  QT-POLL       PIC S9(7) COMP.
               10  QT-MOVE       PIC S9(7) COMP.
               10  QT-COMP       PIC S9(7) COMP.
               10  QT-SEND       PIC S9(7) COMP.
               10  QT-BYTES      PIC S9(4) COMP.
               10  QT-RC         PIC S9(4) COMP.
               10  QT-KIND       PIC X.
               10  QT-NAID       PIC 9.
               10  QT-SKIP       PIC S9(4) COMP.
       01  AT-TABLE.
           05  AT-ENT            OCCURS 200 TIMES.
               10  AT-Q          PIC S9(4) COMP.
               10  AT-TIME       PIC S9(9) COMP.
               10  AT-AID        PIC X.
               10  AT-LEN        PIC S9(4) COMP.
               10  AT-SEQ        PIC 9.
               10  AT-CH         PIC X.
               10  AT-RC         PIC S9(4) COMP.
       01  AT-N                  PIC 9(4).
       01  AT-LOST               PIC 9(4).
       01  SEG-ID                PIC X.
       01  SEG-N                 PIC 9(4).
       01  SEG-Q                 PIC 9(4).
       01  SEG-END               PIC 9.
       01  W-GOT                 PIC 9.
       01  W-REM                 PIC 99.
       01  Q-NAID                PIC 9.
       01  Q-SKIP                PIC S9(4) COMP.
       01  POLL-DONE             PIC 9.
       01  FULL-NEXT             PIC 9.
       01  ABORTED               PIC 9 VALUE 0.
       01  CUR-DIR               PIC X VALUE SPACE.
       01  WS-AIDV               PIC 9(4).
       01  WS-CH                 PIC X.
       01  WS-I                  PIC 9(4).
       01  WS-K                  PIC 9(4).
       01  WS-P                  PIC 9.
       01  WS-Q                  PIC 9(4).
       01  WS-R                  PIC 9(4).
       01  WS-NOP                PIC 9.
       01  WS-N                  PIC 9(4).
       01  SYN-ROW               PIC 999.
       01  SYN-COL               PIC 999.
       01  SYN-CW                PIC 999.
       01  SYN-ADDR              PIC 9(4).
       01  SYN-TEXT.
           05  FILLER            PIC X(4) VALUE 'E14 '.
           05  ST-SEG            PIC X.
           05  FILLER            PIC X(3) VALUE ' P='.
           05  ST-P              PIC 999.
           05  FILLER            PIC X(3) VALUE ' Q='.
           05  ST-Q              PIC 9999.
           05  FILLER            PIC X VALUE ' '.
           05  ST-MSG            PIC X(19).
       01  SYN-TAB REDEFINES SYN-TEXT.
           05  SYN-CH            PIC X OCCURS 38 TIMES.
       01  L-HEAD.
           05  FILLER            PIC X(9) VALUE 'E14 START'.
           05  FILLER            PIC X(5) VALUE ' VAR='.
           05  LH-VAR            PIC X.
           05  FILLER            PIC X(4) VALUE ' PH='.
           05  LH-PH             PIC X.
           05  FILLER            PIC X(6) VALUE ' MODE='.
           05  LH-MODE           PIC X(3).
           05  FILLER            PIC X(4) VALUE ' CW='.
           05  LH-CW             PIC 999.
           05  FILLER            PIC X(4) VALUE ' CH='.
           05  LH-CH             PIC 999.
           05  FILLER            PIC X(4) VALUE ' HI='.
           05  LH-HI             PIC X.
           05  FILLER            PIC X(5) VALUE ' GLY='.
           05  LH-GLY            PIC X.
           05  FILLER            PIC X(4) VALUE ' SC='.
           05  LH-SC             PIC X.
           05  FILLER            PIC X(4) VALUE ' AN='.
           05  LH-AN             PIC X.
           05  FILLER            PIC X(4) VALUE ' RD='.
           05  LH-RD             PIC X.
           05  FILLER            PIC X(11) VALUE SPACES.
       01  L-SEG.
           05  FILLER            PIC X(4) VALUE 'SEG '.
           05  LS-ID             PIC X.
           05  FILLER            PIC X(3) VALUE ' P='.
           05  LS-P              PIC 999.
           05  FILLER            PIC X(3) VALUE ' N='.
           05  LS-N              PIC 9999.
           05  FILLER            PIC X(6) VALUE ' AIDS='.
           05  LS-AN             PIC 9999.
           05  FILLER            PIC X(6) VALUE ' LOST='.
           05  LS-AL             PIC 9999.
           05  FILLER            PIC X(6) VALUE ' MODE='.
           05  LS-MODE           PIC X(3).
           05  FILLER            PIC X(7) VALUE ' ABORT='.
           05  LS-AB             PIC 9.
           05  FILLER            PIC X(25) VALUE SPACES.
       01  L-Q.
           05  FILLER            PIC X(2) VALUE 'Q '.
           05  LQ-ID             PIC X.
           05  FILLER            PIC X VALUE ' '.
           05  LQ-Q              PIC 9999.
           05  FILLER            PIC X VALUE ' '.
           05  LQ-WAKE           PIC -(9)9.
           05  LQ-LATE           PIC -(7)9.
           05  LQ-POLL           PIC -(7)9.
           05  LQ-MOVE           PIC -(7)9.
           05  LQ-COMP           PIC -(7)9.
           05  LQ-SEND           PIC -(7)9.
           05  FILLER            PIC X VALUE ' '.
           05  LQ-BYTES          PIC 9999.
           05  LQ-RC             PIC -(4)9.
           05  FILLER            PIC X VALUE ' '.
           05  LQ-KIND           PIC X.
           05  LQ-NAID           PIC 9.
           05  LQ-SKIP           PIC -(4)9.
           05  FILLER            PIC X(3) VALUE SPACES.
       01  L-A.
           05  FILLER            PIC X(2) VALUE 'A '.
           05  LA-ID             PIC X.
           05  FILLER            PIC X VALUE ' '.
           05  LA-Q              PIC 9999.
           05  FILLER            PIC X VALUE ' '.
           05  LA-TIME           PIC -(9)9.
           05  FILLER            PIC X(5) VALUE ' AID='.
           05  LA-H1             PIC X.
           05  LA-H2             PIC X.
           05  FILLER            PIC X(5) VALUE ' LEN='.
           05  LA-LEN            PIC 9999.
           05  FILLER            PIC X(5) VALUE ' SEQ='.
           05  LA-SEQ            PIC 9.
           05  FILLER            PIC X(4) VALUE ' RC='.
           05  LA-RC             PIC -(4)9.
           05  FILLER            PIC X(4) VALUE ' CH='.
           05  LA-CH             PIC X.
           05  FILLER            PIC X(25) VALUE SPACES.
       01  L-END.
           05  FILLER            PIC X(8) VALUE 'E14 END '.
           05  LE-T              PIC -(9)9.
           05  FILLER            PIC X(7) VALUE ' ABORT='.
           05  LE-AB             PIC 9.
           05  FILLER            PIC X(54) VALUE SPACES.
       LINKAGE SECTION.
       01  PARM-AREA.
           05  PARM-LEN          PIC S9(4) COMP.
           05  PARM-VAR          PIC X.
           05  PARM-PH           PIC X.
           05  PARM-SHORT        PIC X.
       PROCEDURE DIVISION USING PARM-AREA.
       MAIN-PARA.
           MOVE 'B' TO LH-VAR.
           IF PARM-LEN > 0
               MOVE PARM-VAR TO LH-VAR.
           MOVE 'A' TO LH-PH.
           IF PARM-LEN > 1
               MOVE PARM-PH TO LH-PH.
           MOVE 150 TO WS-N.
           IF PARM-LEN > 2 AND PARM-SHORT = 'S'
               MOVE 30 TO WS-N.
           PERFORM SET-REQ THRU SET-REQ-EXIT.
           MOVE 'ZERO' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE 'INIT' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           OPEN OUTPUT LOG-FILE.
           PERFORM WRITE-HEAD.
           IF LH-VAR NOT = 'B' AND REQ-MODE NOT = 'TSC'
               MOVE 1 TO ABORTED.
           IF ABORTED = 0
               PERFORM NEW-GAME
               PERFORM FIRST-SCREEN
               PERFORM RUN-ALL THRU RUN-ALL-EXIT.
           MOVE 'FINI' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE 'TIME' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-ARG TO LE-T.
           MOVE ABORTED TO LE-AB.
           WRITE LOG-REC FROM L-END.
           CLOSE LOG-FILE.
           DISPLAY L-HEAD.
           DISPLAY L-END.
           STOP RUN.
       SET-REQ.
      * Q = THE PACMAN CLIST DEFAULTS (QUERY); N = NO QUERY; B = TSD.
           MOVE SPACE TO REQ-METRIC.
           MOVE SPACE TO REQ-SENDST.
           MOVE 'TSO' TO REQ-MODE.
           MOVE 'A' TO REQ-COLOR.
           MOVE 'A' TO REQ-HILITE.
           MOVE 'A' TO REQ-ANIM.
           MOVE 'P' TO REQ-REDRAW.
           MOVE 'A' TO REQ-GLYPHS.
           MOVE 'A' TO REQ-SCALE.
           MOVE 'A' TO REQ-CANVAS.
           MOVE 0 TO REQ-CW.
           MOVE 0 TO REQ-CH.
           IF LH-VAR = 'N'
               MOVE 'Y' TO REQ-COLOR
               MOVE 'Y' TO REQ-HILITE
               MOVE 'G' TO REQ-GLYPHS
               MOVE '4' TO REQ-SCALE.
           IF LH-VAR = 'B'
               MOVE 'TSD' TO REQ-MODE
               MOVE 'Y' TO REQ-HILITE
               MOVE 'Y' TO REQ-ANIM
               MOVE 'G' TO REQ-GLYPHS
               MOVE '4' TO REQ-SCALE
               MOVE 'W' TO REQ-CANVAS.
       SET-REQ-EXIT.
           EXIT.
       WRITE-HEAD.
           MOVE REQ-MODE TO LH-MODE.
           MOVE REQ-CW TO LH-CW.
           MOVE REQ-CH TO LH-CH.
           MOVE REQ-HILITE TO LH-HI.
           MOVE REQ-GLYPHS TO LH-GLY.
           MOVE REQ-SCALE TO LH-SC.
           MOVE REQ-ANIM TO LH-AN.
           MOVE REQ-REDRAW TO LH-RD.
           WRITE LOG-REC FROM L-HEAD.
       NEW-GAME.
           MOVE 'RSET' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ.
           MOVE 2 TO REQ-LEVEL.
           MOVE 3 TO REQ-COUNT.
           MOVE 'CFG ' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ.
           MOVE 'INIT' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ.
           MOVE 1 TO FULL-NEXT.
       FIRST-SCREEN.
           MOVE 'MOV' TO REQ-KIND.
           MOVE 'PRMT' TO REQ-OP.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS.
           MOVE 0 TO FULL-NEXT.
           IF LH-VAR NOT = 'B'
               MOVE 'SEND' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ PAC-DS.
           MOVE 0 TO WS-NOP.
       RUN-ALL.
           IF LH-VAR = 'B'
               PERFORM BATCH-SEGS VARYING WS-P FROM 1 BY 1
                   UNTIL WS-P > 5
               MOVE 'K' TO SEG-ID
               MOVE 0 TO P-MS
               MOVE 300 TO SEG-N
               PERFORM RUN-SEG THRU RUN-SEG-EXIT
               GO TO RUN-ALL-EXIT.
           MOVE 'W' TO SEG-ID.
           MOVE 200 TO P-MS.
           MOVE 310 TO SEG-N.
           PERFORM RUN-SEG THRU RUN-SEG-EXIT.
           IF ABORTED = 0 AND (LH-PH = 'A' OR LH-PH = 'T')
               PERFORM TIMING-SEGS VARYING WS-P FROM 1 BY 1
                   UNTIL WS-P > 5 OR ABORTED = 1.
           IF ABORTED = 0 AND (LH-PH = 'A' OR LH-PH = 'I')
               PERFORM INPUT-SEGS.
       RUN-ALL-EXIT.
           EXIT.
       BATCH-SEGS.
           MOVE PER-MS (WS-P) TO P-MS.
           MOVE 'C' TO SEG-ID.
           MOVE 100 TO SEG-N.
           PERFORM RUN-SEG THRU RUN-SEG-EXIT.
       TIMING-SEGS.
           MOVE PER-MS (WS-P) TO P-MS.
           MOVE 'S' TO SEG-ID.
           MOVE WS-N TO SEG-N.
           PERFORM RUN-SEG THRU RUN-SEG-EXIT.
           MOVE 'G' TO SEG-ID.
           MOVE WS-N TO SEG-N.
           IF ABORTED = 0
               PERFORM RUN-SEG THRU RUN-SEG-EXIT.
           MOVE 0 TO WS-NOP.
       INPUT-SEGS.
           MOVE 200 TO P-MS.
           MOVE 'I' TO SEG-ID.
           MOVE 300 TO SEG-N.
           MOVE SPACE TO CUR-DIR.
           PERFORM RUN-SEG THRU RUN-SEG-EXIT.
           MOVE 'R' TO SEG-ID.
           MOVE 150 TO SEG-N.
           IF ABORTED = 0
               PERFORM RUN-SEG THRU RUN-SEG-EXIT.
           MOVE 0 TO WS-NOP.
      * ONE SEGMENT: SEG-N QUANTA OF P-MS (0 = NO WAIT), THEN THE LOG.
       RUN-SEG.
           MOVE 0 TO SEG-Q.
           MOVE 0 TO SEG-END.
           MOVE 0 TO AT-N.
           MOVE 0 TO AT-LOST.
           MOVE 0 TO W-GOT.
           MOVE 10 TO W-REM.
           COMPUTE P-US = P-MS * 1000.
           IF SEG-ID = 'G' OR SEG-ID = 'I' OR SEG-ID = 'K'
               PERFORM NEW-GAME.
           MOVE 'TIME' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-ARG TO T-DEAD.
           PERFORM QUANTUM THRU QUANTUM-EXIT
               UNTIL SEG-Q NOT < SEG-N OR SEG-END = 1.
           PERFORM WRITE-SEG THRU WRITE-SEG-EXIT.
       RUN-SEG-EXIT.
           EXIT.
       QUANTUM.
           MOVE 0 TO Q-SKIP.
           MOVE 0 TO Q-NAID.
           IF P-US > 0
               MOVE T-DEAD TO RT-ARG
               MOVE 'WAIT' TO RT-OP
               CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE 'TIME' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-ARG TO T-WAKE.
           ADD 1 TO SEG-Q.
           MOVE SEG-Q TO WS-I.
           MOVE T-WAKE TO QT-WAKE (WS-I).
           COMPUTE QT-LATE (WS-I) = T-WAKE - T-DEAD.
           IF P-US > 0
               ADD P-US TO T-DEAD
               PERFORM SKIP-ONE UNTIL T-DEAD > T-WAKE.
           MOVE 0 TO POLL-DONE.
           PERFORM POLL-ONE THRU POLL-ONE-EXIT
               UNTIL POLL-DONE = 1 OR Q-NAID = 9.
           MOVE 'TIME' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-ARG TO T-A.
           MOVE T-A TO T-B.
           MOVE T-A TO T-C.
           MOVE T-A TO T-D.
           MOVE 0 TO QT-BYTES (WS-I).
           MOVE 0 TO QT-RC (WS-I).
           MOVE '-' TO QT-KIND (WS-I).
           PERFORM DO-WORK THRU DO-WORK-EXIT.
           COMPUTE QT-POLL (WS-I) = T-A - T-WAKE.
           COMPUTE QT-MOVE (WS-I) = T-B - T-A.
           COMPUTE QT-COMP (WS-I) = T-C - T-B.
           COMPUTE QT-SEND (WS-I) = T-D - T-C.
           MOVE Q-NAID TO QT-NAID (WS-I).
           MOVE Q-SKIP TO QT-SKIP (WS-I).
           IF SEG-ID = 'W' AND W-GOT = 1
               SUBTRACT 1 FROM W-REM.
           IF SEG-ID = 'W' AND W-REM = 0
               MOVE 1 TO SEG-END.
       QUANTUM-EXIT.
           EXIT.
       SKIP-ONE.
           ADD P-US TO T-DEAD.
           ADD 1 TO Q-SKIP.
      * ONE TGET NOWAIT. RC 4 = EMPTY; RC 8 = NOT TSO (BATCH).
       POLL-ONE.
           MOVE 'POLL' TO RT-OP.
           MOVE 0 TO RT-ARG.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           IF RT-RC = 4 OR RT-RC = 8
               MOVE 1 TO POLL-DONE
               GO TO POLL-ONE-EXIT.
           ADD 1 TO Q-NAID.
           MOVE SPACE TO WS-CH.
           MOVE 0 TO WS-AIDV.
           IF RT-RC = 0 AND RT-ARG > 0
               MOVE RB-CH (1) TO HX-B
               MOVE HEXN TO WS-AIDV.
           IF WS-AIDV = 125 AND RT-ARG > 6
               PERFORM ENTER-CHAR.
           IF RT-RC NOT = 0
               MOVE 1 TO POLL-DONE.
           IF AT-N < 200
               ADD 1 TO AT-N
               PERFORM LOG-AID
           ELSE
               ADD 1 TO AT-LOST.
           PERFORM USE-AID THRU USE-AID-EXIT.
       POLL-ONE-EXIT.
           EXIT.
       ENTER-CHAR.
      * READ MODIFIED: AID, CURSOR(2), SBA X'11' + ADDRESS(2), DATA.
           MOVE RB-CH (4) TO HX-B.
           IF HEXN = 17
               MOVE RB-CH (7) TO WS-CH.
           MOVE 0 TO WS-NOP.
       LOG-AID.
           MOVE AT-N TO WS-K.
           MOVE SEG-Q TO AT-Q (WS-K).
           MOVE 'TIME' TO RT-OP.
           MOVE RT-ARG TO AT-LEN (WS-K).
           MOVE RT-RC TO AT-RC (WS-K).
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-ARG TO AT-TIME (WS-K).
           MOVE RB-CH (1) TO AT-AID (WS-K).
           MOVE Q-NAID TO AT-SEQ (WS-K).
           MOVE WS-CH TO AT-CH (WS-K).
       USE-AID.
           IF SEG-ID = 'W'
               MOVE 1 TO W-GOT.
           IF WS-AIDV = 110 OR WS-AIDV = 109
               MOVE 1 TO FULL-NEXT.
           IF SEG-ID NOT = 'I'
               GO TO USE-AID-EXIT.
           IF WS-AIDV = 247
               MOVE 'U' TO CUR-DIR.
           IF WS-AIDV = 248
               MOVE 'D' TO CUR-DIR.
           IF WS-AIDV = 122
               MOVE 'L' TO CUR-DIR.
           IF WS-AIDV = 123
               MOVE 'R' TO CUR-DIR.
           IF WS-AIDV = 243
               MOVE 1 TO SEG-END.
           IF WS-AIDV = 125
               PERFORM ENTER-DIR.
       USE-AID-EXIT.
           EXIT.
       ENTER-DIR.
           IF WS-CH = 'U' OR WS-CH = 'D' OR WS-CH = 'L' OR WS-CH = 'R'
               MOVE WS-CH TO CUR-DIR.
           MOVE 0 TO WS-NOP.
      * THE WORK OF ONE QUANTUM (AT MOST ONE TERMINAL WRITE).
       DO-WORK.
           IF SEG-ID = 'C'
               GO TO DO-WORK-EXIT.
           IF SEG-ID = 'S' OR SEG-ID = 'W'
               PERFORM SYN-FRAME
               GO TO DO-WORK-EXIT.
           IF SEG-ID = 'R'
               PERFORM RESTORE-ONLY
               GO TO DO-WORK-EXIT.
           PERFORM GAME-FRAME THRU GAME-FRAME-EXIT.
       DO-WORK-EXIT.
           EXIT.
       SYN-FRAME.
           MOVE SEG-ID TO ST-SEG.
           MOVE P-MS TO ST-P.
           MOVE SEG-Q TO ST-Q.
           MOVE 'TIMING - NO KEYS  ' TO ST-MSG.
           IF SEG-ID = 'W'
               MOVE 'PRESS AN ARROW KEY ' TO ST-MSG.
           IF SEG-ID = 'R'
               MOVE 'RESTORE-ONLY: KEYS' TO ST-MSG.
           PERFORM BUILD-SYN.
           MOVE 43 TO RT-ARG.
           PERFORM PUT-BUF.
           MOVE 'S' TO QT-KIND (WS-I).
       RESTORE-ONLY.
      * FIRST QUANTUM: ONE INSTRUCTION LINE; LATER ONLY X'F1' + WCC C2
      * (THE SMALLEST KEYBOARD-RESTORE WRITE) IN QUANTA WITH AN AID.
           IF SEG-Q = 1
               PERFORM SYN-FRAME
           ELSE IF Q-NAID > 0
               MOVE 241 TO HEXN
               MOVE HX-B TO RB-CH (1)
               MOVE 194 TO HEXN
               MOVE HX-B TO RB-CH (2)
               MOVE 2 TO RT-ARG
               PERFORM PUT-BUF
               MOVE 'R' TO QT-KIND (WS-I).
           MOVE 0 TO WS-NOP.
       PUT-BUF.
           MOVE RT-ARG TO QT-BYTES (WS-I).
           MOVE 'TIME' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-ARG TO T-C.
           MOVE QT-BYTES (WS-I) TO RT-ARG.
           MOVE 'PUTN' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-RC TO QT-RC (WS-I).
           MOVE 'TIME' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-ARG TO T-D.
           MOVE T-C TO T-B.
      * X'F1' WRITE, WCC C2 (RESTORE ONLY), SBA(LAST ROW, COL 21 OR 41)
      * AND 38 CHARACTERS.
       BUILD-SYN.
           MOVE 241 TO HEXN.
           MOVE HX-B TO RB-CH (1).
           MOVE 194 TO HEXN.
           MOVE HX-B TO RB-CH (2).
           MOVE 17 TO HEXN.
           MOVE HX-B TO RB-CH (3).
           MOVE 80 TO SYN-CW.
           MOVE 24 TO SYN-ROW.
           MOVE 41 TO SYN-COL.
           IF REQ-CW > 80
               MOVE REQ-CW TO SYN-CW
               MOVE REQ-CH TO SYN-ROW
               MOVE 21 TO SYN-COL.
           COMPUTE SYN-ADDR = (SYN-ROW - 1) * SYN-CW + SYN-COL - 1.
           DIVIDE SYN-ADDR BY 64 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           MOVE ADDR-CODE (WS-Q) TO HEXN.
           MOVE HX-B TO RB-CH (4).
           MOVE ADDR-CODE (WS-R) TO HEXN.
           MOVE HX-B TO RB-CH (5).
           PERFORM COPY-SYN VARYING WS-K FROM 1 BY 1 UNTIL WS-K > 38.
       COPY-SYN.
           COMPUTE WS-Q = WS-K + 5.
           MOVE SYN-CH (WS-K) TO RB-CH (WS-Q).
      * REPRESENTATIVE GS FRAME: ONE LOGICAL TURN (PACGAME), COMPOSE
      * (PACSCR, AS PACDISP SCR-PRMT) AND SEND (PACPLAT) - UNCHANGED.
       GAME-FRAME.
           IF SEG-ID = 'I'
               MOVE CUR-DIR TO REQ-DIR
           ELSE
               DIVIDE SEG-Q BY 20 GIVING WS-Q REMAINDER WS-R
               ADD 1 TO WS-R
               MOVE DIR-CH (WS-R) TO REQ-DIR.
           IF SEG-ID NOT = 'I' AND SEG-Q = 75
               MOVE 1 TO FULL-NEXT.
           MOVE REQ-DIR TO REQ-CHAR.
           MOVE 'MOV' TO REQ-KIND.
           IF REQ-DIR NOT = SPACE
               MOVE 'MOVE' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ.
           IF F-LOST = 1 OR F-WON = 1
               PERFORM NEW-GAME.
           MOVE 'TIME' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-ARG TO T-B.
           IF FULL-NEXT = 1
               MOVE 'RDR' TO REQ-KIND.
           MOVE 0 TO FULL-NEXT.
           MOVE 'PRMT' TO REQ-OP.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS.
           MOVE 'TIME' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-ARG TO T-C.
           MOVE T-C TO T-D.
           MOVE DS-LEN TO QT-BYTES (WS-I).
           MOVE DS-KIND TO QT-KIND (WS-I).
           IF SEG-ID = 'K'
               GO TO GAME-FRAME-EXIT.
           MOVE 'SEND' TO REQ-OP.
           MOVE SPACE TO REQ-SENDST.
           CALL 'PACPLAT' USING PAC-REQ PAC-DS.
           MOVE 'TIME' TO RT-OP.
           CALL 'PACRTA' USING RT-OP RT-ARG RT-BUF RT-RC.
           MOVE RT-ARG TO T-D.
           IF REQ-SENDST = 'R'
               MOVE 98 TO QT-RC (WS-I).
           IF REQ-MODE NOT = 'TSC'
               MOVE 1 TO ABORTED
               MOVE 1 TO SEG-END.
       GAME-FRAME-EXIT.
           EXIT.
      * THE LOG OF ONE SEGMENT (AFTER ITS TIMED LOOP).
       WRITE-SEG.
           MOVE SEG-ID TO LS-ID.
           MOVE P-MS TO LS-P.
           MOVE SEG-Q TO LS-N.
           MOVE AT-N TO LS-AN.
           MOVE AT-LOST TO LS-AL.
           MOVE REQ-MODE TO LS-MODE.
           MOVE ABORTED TO LS-AB.
           WRITE LOG-REC FROM L-SEG.
           PERFORM WRITE-Q VARYING WS-I FROM 1 BY 1
               UNTIL WS-I > SEG-Q.
           PERFORM WRITE-A VARYING WS-K FROM 1 BY 1
               UNTIL WS-K > AT-N.
       WRITE-SEG-EXIT.
           EXIT.
       WRITE-Q.
           MOVE SEG-ID TO LQ-ID.
           MOVE WS-I TO LQ-Q.
           MOVE QT-WAKE (WS-I) TO LQ-WAKE.
           MOVE QT-LATE (WS-I) TO LQ-LATE.
           MOVE QT-POLL (WS-I) TO LQ-POLL.
           MOVE QT-MOVE (WS-I) TO LQ-MOVE.
           MOVE QT-COMP (WS-I) TO LQ-COMP.
           MOVE QT-SEND (WS-I) TO LQ-SEND.
           MOVE QT-BYTES (WS-I) TO LQ-BYTES.
           MOVE QT-RC (WS-I) TO LQ-RC.
           MOVE QT-KIND (WS-I) TO LQ-KIND.
           MOVE QT-NAID (WS-I) TO LQ-NAID.
           MOVE QT-SKIP (WS-I) TO LQ-SKIP.
           WRITE LOG-REC FROM L-Q.
       WRITE-A.
           MOVE SEG-ID TO LA-ID.
           MOVE AT-Q (WS-K) TO LA-Q.
           MOVE AT-TIME (WS-K) TO LA-TIME.
           MOVE AT-AID (WS-K) TO HX-B.
           DIVIDE HEXN BY 16 GIVING WS-Q REMAINDER WS-R.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-R.
           MOVE HEXDIG (WS-Q) TO LA-H1.
           MOVE HEXDIG (WS-R) TO LA-H2.
           MOVE AT-LEN (WS-K) TO LA-LEN.
           MOVE AT-SEQ (WS-K) TO LA-SEQ.
           MOVE AT-RC (WS-K) TO LA-RC.
           MOVE AT-CH (WS-K) TO LA-CH.
           WRITE LOG-REC FROM L-A.
