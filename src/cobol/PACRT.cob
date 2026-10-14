      * PACRT : MVS-RT REALTIME CONTROLLER (D33). NO TERMINAL OR HOST
      * I/O; THE GAME STATE IS CHANGED ONLY THROUGH PACGAME, WALLS ARE
      * READ THROUGH PACMAP. ITS OWN STATE (DIRECTIONS, TTL, CADENCE,
      * PAUSE, DEATH FREEZE, WIDE COUNTERS) LIVES HERE.
      * OPS: RINI  RESET (NOT STARTED).
      *      RIN   ONE INPUT EVENT (REQ-KIND / REQ-DIR / REQ-CHAR):
      *            MOV = REQUESTED DIRECTION (TTL 3 PLAYER STEPS; THE
      *            FIRST ONE STARTS THE GAME), PAU = PAUSE ON / OFF;
      *            EVERY EVENT IS RECORDED FOR THE QUANTUM'S REQ-RTIN.
      *            DIRECTIONS ARE IGNORED WHILE PAUSED OR FROZEN.
      *      RQ    ONE QUANTUM: ANIMATION FRAME, DEATH FREEZE, GHOST
      *            CADENCE 4/5 (ACC + 4, DUE AT >= 5), REQUEST APPLIED
      *            WHEN LEGAL ELSE TTL - 1, PLAYER STEP WHEN THE
      *            CURRENT DIRECTION IS OPEN; PACGAME MOVE WITH
      *            REQ-STEP B (BOTH), P (PLAYER) OR G (GHOSTS). A LOST
      *            LIFE FREEZES 1.5 S (RT-FRT QUANTA, 10 AT 150 MS) AND
      *            CLEARS BOTH DIRECTIONS.
      * OUT (EVERY OP): REQ-RTSTAT WAIT/RUN /PAUS/FRZ , REQ-RTQ,
      *      REQ-RTCUR, REQ-RTREQ, REQ-RTTTL, REQ-VIS; RQ ALSO REQ-RTIN
      *      (THE QUANTUM'S INPUTS) AND REQ-STEP (B P G - OR F).
      * MVS-GP1 (D36, ARC-ON = 1): EACH RUNNING QUANTUM FIRST CALLS
      *      PACGAME ATIK (FRIGHT TICK), THEN THE FRIGHTENED GHOSTS'
      *      ACCUMULATOR ARC-FACC + ARC-KFINC (DUE AT >= 5, 2/5 OF THE
      *      QUANTA) BESIDE THE NORMAL ONE (4/5); ARC-MOVEN/ARC-MOVEF
      *      TELL PACAI WHICH GHOSTS MOVE. A DEATH RESETS RT-ACC.
      * MVS-GP2 (D37, ARC-ON = 1): THE NORMAL GHOSTS' ACCUMULATOR TAKES
      *      THE LEVEL'S STEP ARC-KNUM (DUE AT >= 10; 8 = THE GP1 4/5
      *      PATTERN). A DEATH OR A LEVEL CLEAR (PACGAME FLAGS D / C,
      *      NOT THE LIVES COUNT: AN EXTRA LIFE MAY COME IN THE SAME
      *      STEP) RESETS RT-ACC AND FREEZES 10 QUANTA.
      * MVS-RP (D39): PUBLISH ALSO GIVES REQ-RTFRZ (FREEZE QUANTA LEFT);
      *      EVERY GAME STEP SETS REQ-DTHX/REQ-DTHY = PAC-MAN'S CELL
      *      AFTER HIS MOVE OF THE STEP (THE DEATH CELL; DISPLAY ONLY).
      * MVS-RP RP.3 SPEED (D39 6): THE DESIGNED QUANTA (150 MS) ARE
      *      CONVERTED ONCE AT RINI TO THE QUANTUM REQ-RTPER BY RT-CONV
      *      (THE SAME PARAGRAPH AS PACGAME): THE FREEZE (10 = 1.5 S),
      *      READY! (4) AND THE POPUP (5), PUBLISHED AS REQ-RTFRT,
      *      REQ-RTRDY, REQ-RTPUQ. MOVEMENT STAYS PER QUANTUM.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACRT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY PACMREQ.
       01  RT-Q                  PIC 9(7) VALUE 0.
       01  RT-STEPS              PIC 9(7) VALUE 0.
       01  RT-CUR                PIC X VALUE SPACE.
       01  RT-REQ                PIC X VALUE SPACE.
       01  RT-TTL                PIC 9 VALUE 0.
       01  RT-ACC                PIC 99 VALUE 0.
       01  RT-FRZ                PIC 99 VALUE 0.
       01  RT-PAUSE              PIC 9 VALUE 0.
       01  RT-START              PIC 9 VALUE 0.
       01  RT-NIN                PIC 9 VALUE 0.
       01  RT-VIS                PIC 9 VALUE 0.
       01  WS-IN.
           05  WS-IN-CH          PIC X OCCURS 8 TIMES.
       01  TTL-INIT              PIC 9 VALUE 3.
       01  FRZ-INIT              PIC 99 VALUE 10.
       01  RDY-INIT              PIC 99 VALUE 4.
       01  PUQ-INIT              PIC 99 VALUE 5.
       01  RT-FRT                PIC 99 VALUE 10.
       01  RT-RDY                PIC 99 VALUE 4.
       01  RT-PUQ                PIC 99 VALUE 5.
       01  WS-CQ                 PIC 999.
       01  WS-CN                 PIC 9(7).
       01  WS-CD                 PIC 9(4).
       01  GH-NUM                PIC 9 VALUE 4.
       01  GH-DEN                PIC 9 VALUE 5.
       01  GH-DEN10              PIC 99 VALUE 10.
       01  RT-NUM                PIC 99.
       01  RT-DEN                PIC 99.
       01  WS-FRZE               PIC 9.
       01  ANIM-Q                PIC 9 VALUE 3.
       01  WS-DIR                PIC X.
       01  WS-LEGAL              PIC 9.
       01  WS-PMOVE              PIC 9.
       01  WS-GDUE               PIC 9.
       01  WS-KIND               PIC X.
       01  WS-LIVES              PIC 9.
       01  WS-Q                  PIC 9(7).
       01  WS-Q2                 PIC 9(7).
       01  WS-R                  PIC 9.
       01  WS-NOP                PIC 9.
       LINKAGE SECTION.
       COPY PACSTATE.
       COPY PACREQ.
       COPY PACARC.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ PAC-ARC.
       MAIN-PARA.
           IF REQ-OP = 'RINI'
               PERFORM DO-RINI
           ELSE IF REQ-OP = 'RIN '
               PERFORM DO-RIN THRU DO-RIN-EXIT
           ELSE IF REQ-OP = 'RQ  '
               PERFORM DO-RQ THRU DO-RQ-EXIT.
           PERFORM PUBLISH.
           GOBACK.
       DO-RINI.
           MOVE 0 TO RT-Q.
           MOVE 0 TO RT-STEPS.
           MOVE SPACE TO RT-CUR.
           MOVE SPACE TO RT-REQ.
           MOVE 0 TO RT-TTL.
           MOVE 0 TO RT-ACC.
           MOVE 0 TO RT-FRZ.
           MOVE 0 TO RT-PAUSE.
           MOVE 0 TO RT-START.
           MOVE 0 TO RT-NIN.
           MOVE 0 TO RT-VIS.
           MOVE SPACES TO WS-IN.
           MOVE SPACES TO REQ-RTIN.
           MOVE '-' TO REQ-STEP.
           MOVE 0 TO REQ-DTHX.
           MOVE 0 TO REQ-DTHY.
           MOVE FRZ-INIT TO WS-CQ.
           PERFORM RT-CONV THRU RT-CONV-EXIT.
           MOVE WS-CQ TO RT-FRT.
           MOVE RDY-INIT TO WS-CQ.
           PERFORM RT-CONV THRU RT-CONV-EXIT.
           MOVE WS-CQ TO RT-RDY.
           MOVE PUQ-INIT TO WS-CQ.
           PERFORM RT-CONV THRU RT-CONV-EXIT.
           MOVE WS-CQ TO RT-PUQ.
       DO-RIN.
           IF RT-NIN < 8
               ADD 1 TO RT-NIN
               PERFORM NOTE-INPUT.
           IF REQ-KIND = 'PAU' AND RT-START = 1
               PERFORM TOGGLE-PAUSE.
           IF REQ-KIND NOT = 'MOV'
               GO TO DO-RIN-EXIT.
           IF RT-PAUSE = 1 OR RT-FRZ > 0
               GO TO DO-RIN-EXIT.
           MOVE REQ-DIR TO RT-REQ.
           MOVE TTL-INIT TO RT-TTL.
           MOVE 1 TO RT-START.
       DO-RIN-EXIT.
           EXIT.
       NOTE-INPUT.
           MOVE REQ-CHAR TO WS-IN-CH (RT-NIN).
           IF REQ-KIND = 'MOV'
               MOVE REQ-DIR TO WS-IN-CH (RT-NIN).
           IF REQ-KIND = 'QUI'
               MOVE 'Q' TO WS-IN-CH (RT-NIN).
           IF REQ-KIND = 'PAU'
               MOVE 'P' TO WS-IN-CH (RT-NIN).
           IF REQ-KIND = 'RDR'
               MOVE '*' TO WS-IN-CH (RT-NIN).
           IF REQ-KIND = 'CFG'
               MOVE 'A' TO WS-IN-CH (RT-NIN).
           MOVE 0 TO WS-NOP.
       TOGGLE-PAUSE.
           IF RT-PAUSE = 1
               MOVE 0 TO RT-PAUSE
           ELSE
               MOVE 1 TO RT-PAUSE.
           MOVE 0 TO WS-NOP.
       DO-RQ.
           ADD 1 TO RT-Q.
           MOVE WS-IN TO REQ-RTIN.
           MOVE SPACES TO WS-IN.
           MOVE 0 TO RT-NIN.
           MOVE '-' TO REQ-STEP.
           DIVIDE RT-Q BY ANIM-Q GIVING WS-Q.
           DIVIDE WS-Q BY 2 GIVING WS-Q2 REMAINDER WS-R.
           MOVE WS-R TO RT-VIS.
           IF RT-FRZ > 0
               SUBTRACT 1 FROM RT-FRZ
               MOVE 'F' TO REQ-STEP
               GO TO DO-RQ-EXIT.
           IF ARC-ON = 1
               PERFORM ARC-QUANTUM THRU ARC-QUANTUM-EXIT.
           MOVE 0 TO WS-GDUE.
           MOVE GH-NUM TO RT-NUM.
           MOVE GH-DEN TO RT-DEN.
           IF ARC-ON = 1
               MOVE ARC-KNUM TO RT-NUM
               MOVE GH-DEN10 TO RT-DEN.
           ADD RT-NUM TO RT-ACC.
           IF RT-ACC NOT < RT-DEN
               SUBTRACT RT-DEN FROM RT-ACC
               MOVE 1 TO WS-GDUE.
           IF ARC-ON = 1
               MOVE WS-GDUE TO ARC-MOVEN
               IF ARC-MOVEF = 1
                   MOVE 1 TO WS-GDUE.
           IF RT-REQ NOT = SPACE
               PERFORM APPLY-REQ.
           MOVE 0 TO WS-PMOVE.
           IF RT-CUR NOT = SPACE
               MOVE RT-CUR TO WS-DIR
               PERFORM LEGAL THRU LEGAL-EXIT
               MOVE WS-LEGAL TO WS-PMOVE.
           MOVE '-' TO WS-KIND.
           IF WS-PMOVE = 1 AND WS-GDUE = 1
               MOVE 'B' TO WS-KIND
           ELSE IF WS-PMOVE = 1
               MOVE 'P' TO WS-KIND
           ELSE IF WS-GDUE = 1
               MOVE 'G' TO WS-KIND.
           IF WS-KIND NOT = '-'
               PERFORM GAME-STEP.
       DO-RQ-EXIT.
           EXIT.
       APPLY-REQ.
      * THE REQUEST BECOMES THE CURRENT DIRECTION WHEN ITS CELL IS OPEN
      * (A REVERSAL ALWAYS IS); OTHERWISE IT WAITS AT MOST TTL STEPS.
           MOVE RT-REQ TO WS-DIR.
           PERFORM LEGAL THRU LEGAL-EXIT.
           IF WS-LEGAL = 1
               MOVE RT-REQ TO RT-CUR
               MOVE SPACE TO RT-REQ
               MOVE 0 TO RT-TTL
           ELSE
               SUBTRACT 1 FROM RT-TTL.
           IF RT-TTL = 0
               MOVE SPACE TO RT-REQ.
           MOVE 0 TO WS-NOP.
       GAME-STEP.
      * MVS-RP: THE CELL PAC-MAN STANDS ON AFTER HIS MOVE (WS-PMOVE = 1:
      * THE CELL IN RT-CUR IS OPEN), BEFORE A DEATH MAY RESET HIM.
           MOVE PLAYER-X TO REQ-DTHX.
           MOVE PLAYER-Y TO REQ-DTHY.
           IF WS-PMOVE = 1 AND RT-CUR = 'U'
               SUBTRACT 1 FROM REQ-DTHY.
           IF WS-PMOVE = 1 AND RT-CUR = 'D'
               ADD 1 TO REQ-DTHY.
           IF WS-PMOVE = 1 AND RT-CUR = 'L'
               SUBTRACT 1 FROM REQ-DTHX.
           IF WS-PMOVE = 1 AND RT-CUR = 'R'
               ADD 1 TO REQ-DTHX.
           MOVE LIVES TO WS-LIVES.
           MOVE WS-KIND TO REQ-STEP.
           MOVE RT-CUR TO REQ-DIR.
           MOVE RT-CUR TO REQ-CHAR.
           MOVE 'MOVE' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ PAC-ARC.
           MOVE 'RQ  ' TO REQ-OP.
           MOVE 0 TO WS-FRZE.
           IF ARC-ON = 0 AND LIVES < WS-LIVES
               MOVE 1 TO WS-FRZE.
           IF ARC-ON = 1 AND ARC-ED = 'D'
               MOVE 1 TO WS-FRZE.
           IF ARC-ON = 1 AND ARC-EC = 'C'
               MOVE 1 TO WS-FRZE.
           IF ARC-ON = 1 AND WS-FRZE = 1
               MOVE 0 TO RT-ACC.
           IF WS-KIND NOT = 'G'
               ADD 1 TO RT-STEPS.
           IF WS-FRZE = 1 AND F-LOST = 0
               MOVE RT-FRT TO RT-FRZ
               MOVE SPACE TO RT-CUR
               MOVE SPACE TO RT-REQ
               MOVE 0 TO RT-TTL.
           MOVE 0 TO WS-NOP.
       LEGAL.
      * WS-LEGAL = 1 WHEN THE CELL NEXT TO THE PLAYER IN WS-DIR IS OPEN.
           MOVE 0 TO WS-LEGAL.
           MOVE PLAYER-X TO M-X.
           MOVE PLAYER-Y TO M-Y.
           IF WS-DIR = 'U'
               SUBTRACT 1 FROM M-Y
           ELSE IF WS-DIR = 'D'
               ADD 1 TO M-Y
           ELSE IF WS-DIR = 'L'
               SUBTRACT 1 FROM M-X
           ELSE IF WS-DIR = 'R'
               ADD 1 TO M-X
           ELSE
               GO TO LEGAL-EXIT.
           MOVE 'WALL' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 0
               MOVE 1 TO WS-LEGAL.
       LEGAL-EXIT.
           EXIT.
       ARC-QUANTUM.
           MOVE 'ATIK' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ PAC-ARC.
           MOVE 'RQ  ' TO REQ-OP.
           MOVE 0 TO ARC-MOVEF.
           IF ARC-FR = 0
               GO TO ARC-QUANTUM-EXIT.
           ADD ARC-KFINC TO ARC-FACC.
           IF ARC-FACC NOT < GH-DEN
               SUBTRACT GH-DEN FROM ARC-FACC
               MOVE 1 TO ARC-MOVEF.
       ARC-QUANTUM-EXIT.
           EXIT.
       PUBLISH.
           MOVE RT-Q TO REQ-RTQ.
           MOVE RT-CUR TO REQ-RTCUR.
           MOVE RT-REQ TO REQ-RTREQ.
           MOVE RT-TTL TO REQ-RTTTL.
           MOVE RT-VIS TO REQ-VIS.
           MOVE RT-FRZ TO REQ-RTFRZ.
           MOVE RT-FRT TO REQ-RTFRT.
           MOVE RT-RDY TO REQ-RTRDY.
           MOVE RT-PUQ TO REQ-RTPUQ.
           MOVE 'RUN ' TO REQ-RTSTAT.
           IF RT-FRZ > 0
               MOVE 'FRZ ' TO REQ-RTSTAT.
           IF RT-PAUSE = 1
               MOVE 'PAUS' TO REQ-RTSTAT.
           IF RT-START = 0
               MOVE 'WAIT' TO REQ-RTSTAT.
           MOVE 0 TO WS-NOP.
       RT-CONV.
      * MVS-RP RP.3 (D39 6), THE ONE QUANTUM CONVERSION (THE SAME
      * PARAGRAPH AS PACGAME): WS-CQ QUANTA OF 150 MS -> THE SAME LENGTH
      * IN QUANTA OF REQ-RTPER MS, ROUNDED HALF UP (150 = IDENTITY).
      * NO PERIOD SET (NOT NUMERIC OR 0) = UNCHANGED.
           IF REQ-RTPER NOT NUMERIC
               GO TO RT-CONV-EXIT.
           IF REQ-RTPER = 0
               GO TO RT-CONV-EXIT.
           COMPUTE WS-CN = WS-CQ * 300 + REQ-RTPER.
           COMPUTE WS-CD = REQ-RTPER * 2.
           DIVIDE WS-CN BY WS-CD GIVING WS-CQ.
       RT-CONV-EXIT.
           EXIT.
