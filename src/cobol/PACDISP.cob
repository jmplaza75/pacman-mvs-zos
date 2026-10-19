      * PACDISP : DISPLAY ADAPTER (PLAIN TEXT, LEVEL G0). READS THE
      * STATE, NEVER CHANGES IT.  OPS : HEAD  STAT  INVL  END  PRMT
      * PRMT shows the input prompt in TSO mode only (no-op in BAT).
      * TSO: EVERY FRAME AFTER THE FIRST STARTS ON A FRESH SCREEN
      * (PACPLAT CLS), SO TSO NEVER PAGES A FRAME WITH '***'.
      * MVS-G0: COUNTS FRAMES, LINES, CHARACTERS AND SCREEN CLEARS;
      * THE TOTALS ARE PRINTED AFTER THE END LINES ONLY WHEN
      * REQ-METRIC = 'M' (OPTIONAL; NORMAL OUTPUT IS UNCHANGED).
      * MVS-G1: IN TSC (COLOUR FULL-SCREEN) AND TSD (ITS BATCH DRY RUN)
      * THE FRAME IS COMPOSED BY PACSCR AND SENT BY PACPLAT ONCE PER
      * READ (PRMT); NO LINE OUTPUT UNTIL THE END, WHEN PACPLAT FSOF
      * RESTORES LINE MODE BEFORE THE USUAL END LINES.
      * MVS-RT (D33): OP RTQF = THE ONE FRAME OF A REALTIME QUANTUM.
      * TSC/TSD: REQ-RTFR P = PRMT (INPUT FIELD RESET), F = PRMT AS A
      * FULL REDRAW, ELSE PACSCR RTQF (ALWAYS ONE STREAM). BAT: THE RT
      * STATUS LINE (QUANTUM, INPUTS, STEP KIND, DIRECTIONS, STATE) AND
      * THE GHOSTS LINE. END ADDS 'QUANTA' IN REALTIME ONLY.
      * MVS-S1: BEFORE EVERY SCREEN SENT, SET-BELL READS THE STATE
      * (NEVER CHANGES IT): REQ-BELL Y ON THE FIRST SCREEN (START),
      * WHEN LIVES FELL SINCE THE LAST SCREEN (DEATH, THE LAST ONE TOO)
      * AND ON THE FIRST SCREEN AFTER THE WIN; PACPLAT RINGS ONLY WITH
      * SOUND Y.
      * WITHOUT AN END SCREEN (NOT SCALED) A PENDING ALARM GOES ON A
      * RESTORE-ONLY WRITE (C2 28 00 00) BEFORE LINE MODE RETURNS.
      * MVS-GP1 (D36, ARC-ON = 1): 'RULES ARCADE' AFTER THE BANNER, ONE
      * ARCADE LINE (7-DIGIT SCORE, FRIGHT, CHAIN, EVENT, GHOST MODES)
      * AFTER EACH STATUS / RT GHOSTS LINE, GHOSTS F (FRIGHTENED) AND E
      * (EYES) ON THE BOARD, END 'SCORE NNNNNNN' + 'GHOSTS EATEN NNN'.
      * MVS-GP2 (D37, ARC-ON = 1): 'LEVEL NNN' AFTER 'RULES ARCADE', A
      * LEVEL LINE AFTER THE ARCADE LINE, FRUIT % ON THE BOARD (UNDER
      * PAC-MAN AND THE GHOSTS), END 'TURNS NNNNNNN', 'GHOSTS EATEN
      * NNNN', 'FRUITS EATEN NNN', 'LEVEL NNN'. ALARM (S1) IN ARCADE
      * FROM THE GAME COUNTERS, NEVER FROM A DROP IN LIVES: A DEATH
      * (ARC-NDIE ROSE), THE EXTRA LIFE (ARC-XL 0 -> 1), A LEVEL CLEAR
      * (ARC-LEVEL ROSE), PLUS START AND THE FINAL WIN AS IN S1. ONE
      * ALARM PER SCREEN: EVENTS OF ONE SCREEN ARE COALESCED.
      * MVS-HS (D38, ARC-ON = 1, REQ-HSST NOT N): AFTER 'LEVEL NNN' THE
      * END LINE 'HIGH SCORE NNNNNNN LEVEL NNN' = MAX(PERSISTENT, THIS
      * GAME), THEN 'NEW HIGH SCORE' / 'HIGH SCORE NOT SAVED' / 'START
      * LEVEL NN: HIGH SCORE NOT RECORDED'; OR 'HIGH SCORE UNAVAILABLE'.
      * MVS-RP (D39): AN ARCADE REALTIME GAME LOST ON SCREEN PLAYS
      * THE 6 DEATH FRAMES (PACSCR RTQF, REQ-RTSTAT FRZ, REQ-RTFRZ
      * 10..5; TSC: ONE PERIOD APART BY PACPLAT CLOK / WDLN) BEFORE
      * THE END SCREEN.
      * MVS-S2 (D41, DOCS/S2-PATTERNS.MD): WITH REQ-ALARM P AND SOUND Y
      * EVERY SCREEN GOES THROUGH BELL-SET: PAT-CLASS NAMES THE HIGHEST
      * EVENT OF THE SCREEN (START 1, EXTRA LIFE 2, DEATH 3, LEVEL
      * CLEAR 4, WIN 5, GAME OVER 6) FROM THE SAME COUNTERS AS SET-BELL,
      * PAT-PLAY RINGS ITS PATTERN (1 2 2 3 4 3 BELLS, PT-G QUANTA
      * APART: 2 AT 150 MS, 3 AT 125 MS) ON THE REALTIME QUANTUM
      * WRITES ONLY (PT-QW); A HIGHER OR EQUAL EVENT REPLACES IT, TURN
      * PLAY RINGS THE FIRST BELL ONLY. AT THE END ONLY A WIN / GAME
      * OVER PATTERN GOES ON, AS BELL-ONLY WRITES INSIDE THE 3-S END
      * PAUSE (END-PAUSE). REQ-ALARM S = THE S1 / GP2 PATH UNCHANGED.
      * ZOS-6 (ZV-D33, Z4): RTQF WITH REQ-PRES N (A COALESCED QUANTUM,
      * TSC / TSD) = SCR-RTQS: NO SCREEN, NO SEND; PACSCR RTQS ADVANCES
      * THE DISPLAY STATE OF LOGICAL TIME (FACING, POPUP) AND THE S2
      * PATTERN CLOCK COUNTS THE QUANTUM (PT-NEXT DOWN TO 1 AT MOST: A
      * STEP DUE ON A SKIPPED QUANTUM RINGS ON THE NEXT WRITE). THE
      * BELL SNAPSHOT, METRICS AND THE SCREEN IMAGE ADVANCE ONLY WITH
      * WHAT IS SENT.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACDISP.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-LINE               PIC X(20).
       01  WS-LINE-CELLS REDEFINES WS-LINE.
           05  WS-LINE-CELL      PIC X OCCURS 20 TIMES.
       01  WS-ROW                PIC 99.
       01  WS-SAVE-OP            PIC X(4).
       01  WS-G                  PIC 9.
       01  WS-GX                 PIC 99.
       COPY PACDS.
       01  M-FRAMES              PIC 9(4) VALUE 0.
       01  M-LINES               PIC 9(5) VALUE 0.
       01  M-CHARS               PIC 9(7) VALUE 0.
       01  WS-NOP                PIC 9.
       01  M-CLEARS              PIC 9(4) VALUE 0.
       01  SB-SENT               PIC 9 VALUE 0.
       01  SB-LIVES              PIC 9 VALUE 0.
       01  SB-WON                PIC 9 VALUE 0.
       01  SB-NDIE               PIC 99 VALUE 0.
       01  SB-XL                 PIC 9 VALUE 0.
       01  SB-LVL                PIC 999 VALUE 0.
       01  FD-K                  PIC 99 VALUE 0.
       01  PT-ON                 PIC 9 VALUE 0.
       01  PT-PRI                PIC 9 VALUE 0.
       01  PT-EV                 PIC 9 VALUE 0.
       01  PT-D                  PIC 9 VALUE 0.
       01  PT-LEFT               PIC 9 VALUE 0.
       01  PT-NEXT               PIC 9 VALUE 0.
       01  PT-G                  PIC 9 VALUE 2.
       01  PT-QW                 PIC 9 VALUE 0.
       01  PT-T0                 PIC S9(9) COMP VALUE +0.
       01  PT-TAB                PIC X(6) VALUE '122343'.
       01  PT-TABR REDEFINES PT-TAB.
           05  PT-NB             PIC 9 OCCURS 6 TIMES.
       01  FD-SAVE               PIC X(4).
       01  HEXW.
           05  HX-Z              PIC X VALUE LOW-VALUE.
           05  HX-B              PIC X.
       01  HEXN REDEFINES HEXW   PIC 9(4) COMP.
       01  WS-MET.
           05  FILLER            PIC X(15) VALUE 'METRICS FRAMES='.
           05  MT-FRAMES         PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' LINES='.
           05  MT-LINES          PIC 9(5).
           05  FILLER            PIC X(7) VALUE ' CHARS='.
           05  MT-CHARS          PIC 9(7).
           05  FILLER            PIC X(8) VALUE ' CLEARS='.
           05  MT-CLEARS         PIC 9(4).
       01  WS-STATUS-LINE.
           05  FILLER            PIC X VALUE 'T'.
           05  ST-TURN           PIC 999.
           05  FILLER            PIC X VALUE ' '.
           05  ST-CMD            PIC X.
           05  FILLER            PIC X VALUE ' '.
           05  ST-RESULT         PIC X(7).
           05  FILLER            PIC X(3) VALUE ' X='.
           05  ST-X              PIC 99.
           05  FILLER            PIC X(3) VALUE ' Y='.
           05  ST-Y              PIC 99.
           05  FILLER            PIC X(3) VALUE ' S='.
           05  ST-SCORE          PIC 9(4).
           05  FILLER            PIC X(3) VALUE ' L='.
           05  ST-LEFT           PIC 999.
           05  FILLER            PIC X(3) VALUE ' G='.
           05  ST-GX             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  ST-GY             PIC 99.
           05  FILLER            PIC X(3) VALUE ' V='.
           05  ST-LIVES          PIC 9.
           05  FILLER            PIC X(4) VALUE ' ST='.
           05  ST-STATE          PIC X(7).
       01  WS-XL2.
           05  FILLER            PIC X(3) VALUE 'G2='.
           05  XL2-X             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  XL2-Y             PIC 99.
       01  WS-XL3.
           05  FILLER            PIC X(4) VALUE ' G3='.
           05  XL3-X             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  XL3-Y             PIC 99.
       01  WS-RT-LINE.
           05  FILLER            PIC X VALUE 'Q'.
           05  RT-Q              PIC 9(7).
           05  FILLER            PIC X(4) VALUE ' IN='.
           05  RT-IN             PIC X(8).
           05  FILLER            PIC X(3) VALUE ' K='.
           05  RT-K              PIC X.
           05  FILLER            PIC X(3) VALUE ' C='.
           05  RT-C              PIC X.
           05  FILLER            PIC X(3) VALUE ' R='.
           05  RT-R              PIC X.
           05  FILLER            PIC X(3) VALUE ' T='.
           05  RT-T              PIC 9.
           05  FILLER            PIC X(3) VALUE ' X='.
           05  RT-X              PIC 99.
           05  FILLER            PIC X(3) VALUE ' Y='.
           05  RT-Y              PIC 99.
           05  FILLER            PIC X(3) VALUE ' S='.
           05  RT-S              PIC 9(4).
           05  FILLER            PIC X(3) VALUE ' L='.
           05  RT-L              PIC 999.
           05  FILLER            PIC X(3) VALUE ' V='.
           05  RT-V              PIC 9.
           05  FILLER            PIC X(4) VALUE ' ST='.
           05  RT-ST             PIC X(7).
       01  WS-RTG1.
           05  FILLER            PIC X(4) VALUE '  G='.
           05  RG1-X             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  RG1-Y             PIC 99.
       01  WS-RTG2.
           05  FILLER            PIC X VALUE ' '.
           05  RG2-X             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  RG2-Y             PIC 99.
       01  WS-RTG3.
           05  FILLER            PIC X VALUE ' '.
           05  RG3-X             PIC 99.
           05  FILLER            PIC X VALUE ','.
           05  RG3-Y             PIC 99.
       01  WS-ARC-LINE.
           05  FILLER            PIC X(4) VALUE 'A S='.
           05  AL-S              PIC 9(7).
           05  FILLER            PIC X(4) VALUE ' PW='.
           05  AL-PW             PIC 9.
           05  FILLER            PIC X(4) VALUE ' FR='.
           05  AL-FR             PIC 999.
           05  FILLER            PIC X(4) VALUE ' FT='.
           05  AL-FT             PIC 999.
           05  FILLER            PIC X(4) VALUE ' FA='.
           05  AL-FA             PIC 9.
           05  FILLER            PIC X(4) VALUE ' CH='.
           05  AL-CH             PIC 9.
           05  FILLER            PIC X(4) VALUE ' EV='.
           05  AL-EV             PIC X(4).
           05  FILLER            PIC X(3) VALUE ' P='.
           05  AL-P              PIC 9(4).
           05  FILLER            PIC X(3) VALUE ' N='.
           05  AL-N              PIC 999.
           05  FILLER            PIC X(3) VALUE ' M='.
           05  AL-M1             PIC X.
           05  AL-W1             PIC 999.
       01  WS-ARC-G2.
           05  FILLER            PIC X VALUE ' '.
           05  AL-M2             PIC X.
           05  AL-W2             PIC 999.
       01  WS-ARC-G3.
           05  FILLER            PIC X VALUE ' '.
           05  AL-M3             PIC X.
           05  AL-W3             PIC 999.
      * MVS-GP2 (D37) LEVEL LINE, AFTER THE ARCADE LINE.
       01  WS-LVL-LINE.
           05  FILLER            PIC X(5) VALUE 'L LV='.
           05  LL-LV             PIC 999.
           05  FILLER            PIC X(4) VALUE ' AI='.
           05  LL-AI             PIC 9.
           05  FILLER            PIC X(4) VALUE ' IT='.
           05  LL-IT             PIC 999.
           05  FILLER            PIC X(4) VALUE ' BN='.
           05  LL-BN             PIC 9.
           05  FILLER            PIC X(4) VALUE ' BT='.
           05  LL-BT             PIC 999.
           05  FILLER            PIC X(4) VALUE ' BK='.
           05  LL-BK             PIC X.
           05  FILLER            PIC X(4) VALUE ' BV='.
           05  LL-BV             PIC 9(4).
           05  FILLER            PIC X(4) VALUE ' XL='.
           05  LL-XL             PIC 9.
           05  FILLER            PIC X(4) VALUE ' EV='.
           05  LL-EV             PIC X(5).
       01  WS-QUANTA.
           05  FILLER            PIC X(7) VALUE 'QUANTA '.
           05  QU-N              PIC 9(7).
       01  HS-LINE.
           05  FILLER            PIC X(11) VALUE 'HIGH SCORE '.
           05  HL-S              PIC 9(7).
           05  FILLER            PIC X(7) VALUE ' LEVEL '.
           05  HL-L              PIC 999.
       01  HS-PLINE.
           05  FILLER            PIC X(12) VALUE 'START LEVEL '.
           05  HP-L              PIC 99.
           05  FILLER            PIC X(25)
                   VALUE ': HIGH SCORE NOT RECORDED'.
       LINKAGE SECTION.
       COPY PACSTATE.
       COPY PACREQ.
       COPY PACARC.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ PAC-ARC.
       MAIN-PARA.
           IF REQ-MODE = 'TSC' OR REQ-MODE = 'TSD'
               PERFORM SCREEN-OP THRU SCREEN-OP-EXIT
           ELSE IF REQ-OP = 'HEAD'
               DISPLAY 'PACMAN MVS-6 SMART GHOSTS'
               ADD 1 TO M-LINES
               ADD 25 TO M-CHARS
               PERFORM ARC-HEAD THRU ARC-HEAD-EXIT
           ELSE IF REQ-OP = 'STAT'
               PERFORM SHOW-STATE THRU SHOW-STATE-EXIT
           ELSE IF REQ-OP = 'INVL'
               DISPLAY 'INVALID COMMAND ' REQ-CHAR
               ADD 1 TO M-LINES
               ADD 17 TO M-CHARS
           ELSE IF REQ-OP = 'END '
               PERFORM SHOW-END THRU SHOW-END-EXIT
           ELSE IF REQ-OP = 'PRMT'
               PERFORM SHOW-PROMPT THRU SHOW-PROMPT-EXIT
           ELSE IF REQ-OP = 'RTQF'
               PERFORM SHOW-RT.
           GOBACK.
       SCREEN-OP.
           IF REQ-OP = 'STAT'
               ADD 1 TO M-FRAMES
           ELSE IF REQ-OP = 'INVL'
               CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC
           ELSE IF REQ-OP = 'PRMT'
               PERFORM SCR-PRMT THRU SCR-PRMT-EXIT
           ELSE IF REQ-OP = 'TICK'
               PERFORM SCR-TICK THRU SCR-TICK-EXIT
           ELSE IF REQ-OP = 'RTQF' AND REQ-PRES = 'N'
               PERFORM SCR-RTQS
           ELSE IF REQ-OP = 'RTQF'
               PERFORM SCR-RTQF THRU SCR-RTQF-EXIT
           ELSE IF REQ-OP = 'END '
               PERFORM SCR-ENDS
               MOVE 'FSOF' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ
               MOVE 'END ' TO REQ-OP
               PERFORM SHOW-END THRU SHOW-END-EXIT.
       SCREEN-OP-EXIT.
           EXIT.
       SCR-PRMT.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC.
           ADD DS-LEN TO M-CHARS.
           PERFORM BELL-SET.
           MOVE 'SEND' TO REQ-OP.
           MOVE SPACE TO REQ-SENDST.
           CALL 'PACPLAT' USING PAC-REQ PAC-DS.
           MOVE 'PRMT' TO REQ-OP.
           IF REQ-SENDST = 'R'
               PERFORM SCR-RESEND.
       SCR-PRMT-EXIT.
           EXIT.
       SCR-ENDS.
      * MVS-GS: SCALED ONLY - ONE FINAL SCREEN WITH THE END BANNER, THEN
      * A SHORT PAUSE (PACPLAT WAIT, NO INPUT IS READ) BEFORE LINE MODE.
      * MVS-S2: GAME OVER - ONLY A WIN / GAME OVER PATTERN GOES ON.
           IF PT-PRI < 5
               MOVE 0 TO PT-ON.
           IF ARC-ON = 1 AND F-LOST = 1 AND REQ-PLAY = 'R'
               PERFORM FINAL-DEATH.
           MOVE 0 TO DS-LEN.
           IF REQ-SCALE NOT = 'N'
               MOVE 'ENDS' TO REQ-OP
               CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC
               PERFORM SCR-ENDS-SEND.
           IF DS-LEN = 0
               PERFORM SCR-END-BELL.
           MOVE 'END ' TO REQ-OP.
       SCR-ENDS-SEND.
           IF DS-LEN > 0
               ADD DS-LEN TO M-CHARS
               PERFORM BELL-SET
               MOVE 'SEND' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ PAC-DS
               PERFORM END-PAUSE THRU END-PAUSE-EXIT.
           MOVE 0 TO WS-NOP.
       END-PAUSE.
      * MVS-S2 (D41 5): NO PATTERN LEFT = THE 3-S WAIT AS BEFORE. ELSE
      * EACH STEP LEFT IS A BELL-ONLY WRITE PT-G PERIODS AFTER THE LAST
      * (WDLN FROM THE END SCREEN'S CLOCK T0), THEN WAIT UNTIL T0 + 3 S
      * (DLWT): THE PAUSE IS NEVER LONGER. TSD: THE WRITES, NO WAITS.
           IF PT-ON = 0
               MOVE 'WAIT' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ
               GO TO END-PAUSE-EXIT.
           IF REQ-MODE = 'TSC'
               MOVE 'CLOK' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ
               MOVE REQ-TIME TO PT-T0.
           PERFORM END-STEP THRU END-STEP-EXIT
               UNTIL PT-ON = 0.
           IF REQ-MODE = 'TSC'
               COMPUTE REQ-TIME = PT-T0 + 3000
               MOVE 'DLWT' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
       END-PAUSE-EXIT.
           EXIT.
       END-STEP.
           IF REQ-MODE = 'TSC'
               PERFORM END-WDLN PT-G TIMES.
           MOVE 'Y' TO REQ-BELL.
           PERFORM BELL-WRITE.
           SUBTRACT 1 FROM PT-LEFT.
           IF PT-LEFT = 0
               MOVE 0 TO PT-ON.
       END-STEP-EXIT.
           EXIT.
       END-WDLN.
           MOVE 'WDLN' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
       SCR-END-BELL.
           PERFORM SET-BELL.
           IF REQ-BELL = 'Y' AND REQ-SOUND = 'Y'
               PERFORM BELL-WRITE.
           MOVE 'N' TO REQ-BELL.
       BELL-WRITE.
      * THE RESTORE-ONLY WRITE C2 28 00 00 (PACPLAT ADDS THE ALARM BIT).
           MOVE 194 TO HEXN.
           MOVE HX-B TO DS-BYTE (1).
           MOVE 40 TO HEXN.
           MOVE HX-B TO DS-BYTE (2).
           MOVE LOW-VALUE TO DS-BYTE (3).
           MOVE LOW-VALUE TO DS-BYTE (4).
           MOVE 4 TO DS-LEN.
           MOVE 'P' TO DS-KIND.
           ADD DS-LEN TO M-CHARS.
           MOVE 'SEND' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ PAC-DS.
       FINAL-DEATH.
      * MVS-RP: THE LAST LIFE LOST (NO FREEZE IN THE GAME): THE DEATH
      * FRAMES AS QUANTUM FRAMES, THE STATE UNCHANGED.
           MOVE REQ-RTSTAT TO FD-SAVE.
           MOVE 'FRZ ' TO REQ-RTSTAT.
           MOVE SPACE TO REQ-RTFR.
           IF REQ-MODE = 'TSC'
               MOVE 'CLOK' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           PERFORM FD-FRAME VARYING FD-K FROM REQ-RTFRT BY -1
               UNTIL FD-K NOT > REQ-RTRDY.
           MOVE FD-SAVE TO REQ-RTSTAT.
           MOVE 0 TO REQ-RTFRZ.
       FD-FRAME.
           IF REQ-MODE = 'TSC'
               MOVE 'WDLN' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           MOVE FD-K TO REQ-RTFRZ.
           MOVE 'RTQF' TO REQ-OP.
           PERFORM SCR-RTQF THRU SCR-RTQF-EXIT.
       BELL-SET.
      * MVS-S2 (D41): SET-BELL (S1 / GP2) BETWEEN THE PATTERN STEPS,
      * WHICH RUN ONLY WITH ALARM(PATTERN) AND SOUND Y.
           IF REQ-ALARM = 'P' AND REQ-SOUND = 'Y'
               PERFORM PAT-CLASS THRU PAT-CLASS-EXIT.
           PERFORM SET-BELL.
           IF REQ-ALARM = 'P' AND REQ-SOUND = 'Y'
               PERFORM PAT-PLAY THRU PAT-PLAY-EXIT.
           MOVE 0 TO PT-QW.
       PAT-CLASS.
      * THE HIGHEST EVENT OF THIS SCREEN (0 NONE), READ BEFORE SET-BELL
      * UPDATES ITS SB- COPIES. GAME OVER = A DEATH THAT ENDS THE GAME.
           MOVE 0 TO PT-EV.
           MOVE 0 TO PT-D.
           IF SB-SENT = 0
               MOVE 1 TO PT-EV
               GO TO PAT-CLASS-EXIT.
           IF ARC-ON = 1 AND ARC-XL > SB-XL
               MOVE 2 TO PT-EV.
           IF ARC-ON = 0 AND LIVES < SB-LIVES
               MOVE 1 TO PT-D.
           IF ARC-ON = 1 AND ARC-NDIE > SB-NDIE
               MOVE 1 TO PT-D.
           IF PT-D = 1
               MOVE 3 TO PT-EV.
           IF ARC-ON = 1 AND ARC-LEVEL > SB-LVL
               MOVE 4 TO PT-EV.
           IF F-WON = 1 AND SB-WON = 0
               MOVE 5 TO PT-EV.
           IF PT-D = 1 AND F-LOST = 1
               MOVE 6 TO PT-EV.
       PAT-CLASS-EXIT.
           EXIT.
       PAT-PLAY.
      * AN EVENT AT OR ABOVE THE RUNNING PATTERN STARTS ITS OWN (FIRST
      * BELL ON THIS SCREEN); ELSE A QUANTUM WRITE MAY CARRY A STEP.
           IF PT-EV = 0
               GO TO PAT-STEP.
           IF PT-ON = 1 AND PT-EV < PT-PRI
               GO TO PAT-STEP.
           MOVE 2 TO PT-G.
           IF REQ-RTPER < 150
               MOVE 3 TO PT-G.
           MOVE 'Y' TO REQ-BELL.
           MOVE PT-EV TO PT-PRI.
           MOVE PT-NB (PT-EV) TO PT-LEFT.
           SUBTRACT 1 FROM PT-LEFT.
           MOVE PT-G TO PT-NEXT.
           MOVE 1 TO PT-ON.
           IF PT-LEFT = 0
               MOVE 0 TO PT-ON.
           IF REQ-PLAY = 'T' AND PT-EV < 5
               MOVE 0 TO PT-ON.
           GO TO PAT-PLAY-EXIT.
       PAT-STEP.
           MOVE 'N' TO REQ-BELL.
           IF PT-ON = 0 OR PT-QW = 0
               GO TO PAT-PLAY-EXIT.
           SUBTRACT 1 FROM PT-NEXT.
           IF PT-NEXT > 0
               GO TO PAT-PLAY-EXIT.
           MOVE 'Y' TO REQ-BELL.
           MOVE PT-G TO PT-NEXT.
           SUBTRACT 1 FROM PT-LEFT.
           IF PT-LEFT = 0
               MOVE 0 TO PT-ON.
       PAT-PLAY-EXIT.
           EXIT.
       SET-BELL.
           MOVE 'N' TO REQ-BELL.
           IF SB-SENT = 0
               MOVE 'Y' TO REQ-BELL.
           IF SB-SENT = 1 AND LIVES < SB-LIVES AND ARC-ON = 0
               MOVE 'Y' TO REQ-BELL.
           IF F-WON = 1 AND SB-WON = 0
               MOVE 'Y' TO REQ-BELL
               MOVE 1 TO SB-WON.
           IF ARC-ON = 1
               PERFORM ARC-BELL.
           MOVE 1 TO SB-SENT.
           MOVE LIVES TO SB-LIVES.
       SCR-TICK.
      * MVS-G3: VISUAL TICK (GLYPH FRAME ONLY). NO CHANGE = NO SEND.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC.
           IF DS-LEN > 0
               ADD DS-LEN TO M-CHARS
               PERFORM BELL-SET
               MOVE 'SEND' TO REQ-OP
               MOVE SPACE TO REQ-SENDST
               CALL 'PACPLAT' USING PAC-REQ PAC-DS
               MOVE 'TICK' TO REQ-OP
               IF REQ-SENDST = 'R'
                   PERFORM SCR-RESEND.
       SCR-TICK-EXIT.
           EXIT.
       SCR-RTQS.
      * ZOS-6: A COALESCED QUANTUM (SEE THE HEADER).
           MOVE 'RTQS' TO REQ-OP.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC.
           MOVE 'RTQF' TO REQ-OP.
           IF PT-ON = 1 AND PT-NEXT > 1
               SUBTRACT 1 FROM PT-NEXT.
       SCR-RTQF.
      * MVS-RT: EXACTLY ONE WRITE FOR THE QUANTUM, ALWAYS WITH THE
      * KEYBOARD RESTORE: AFTER ENTER / INVALID INPUT / REDRAW THE
      * PROMPT SCREEN (FIELD RESET; F = FULL), ELSE PACSCR RTQF.
      * MVS-S2: EITHER WAY IT IS THE QUANTUM'S ONE WRITE (PT-QW 1).
           MOVE 1 TO PT-QW.
           IF REQ-RTFR = 'P' OR REQ-RTFR = 'F'
               MOVE 'MOV' TO REQ-KIND
               IF REQ-RTFR = 'F'
                   MOVE 'RDR' TO REQ-KIND.
           IF REQ-RTFR = 'P' OR REQ-RTFR = 'F'
               MOVE 'PRMT' TO REQ-OP
               PERFORM SCR-PRMT THRU SCR-PRMT-EXIT
               MOVE 'RTQF' TO REQ-OP
               GO TO SCR-RTQF-EXIT.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC.
           ADD DS-LEN TO M-CHARS.
           PERFORM BELL-SET.
           MOVE 'SEND' TO REQ-OP.
           MOVE SPACE TO REQ-SENDST.
           CALL 'PACPLAT' USING PAC-REQ PAC-DS.
           MOVE 'PRMT' TO REQ-OP.
           IF REQ-SENDST = 'R'
               PERFORM SCR-RESEND.
           MOVE 'RTQF' TO REQ-OP.
       SCR-RTQF-EXIT.
           EXIT.
       SHOW-RT.
           MOVE REQ-RTQ TO RT-Q.
           MOVE REQ-RTIN TO RT-IN.
           MOVE REQ-STEP TO RT-K.
           MOVE REQ-RTCUR TO RT-C.
           MOVE REQ-RTREQ TO RT-R.
           MOVE REQ-RTTTL TO RT-T.
           MOVE PLAYER-X TO RT-X.
           MOVE PLAYER-Y TO RT-Y.
           MOVE SCORE TO RT-S.
           MOVE PELLETS-LEFT TO RT-L.
           MOVE LIVES TO RT-V.
           MOVE GAME-STATE TO RT-ST.
           DISPLAY WS-RT-LINE.
           MOVE GH-X (1) TO RG1-X.
           MOVE GH-Y (1) TO RG1-Y.
           IF GHOST-COUNT > 1
               MOVE GH-X (2) TO RG2-X
               MOVE GH-Y (2) TO RG2-Y.
           IF GHOST-COUNT > 2
               MOVE GH-X (3) TO RG3-X
               MOVE GH-Y (3) TO RG3-Y.
           IF GHOST-COUNT = 1
               DISPLAY WS-RTG1
           ELSE IF GHOST-COUNT = 2
               DISPLAY WS-RTG1 WS-RTG2
           ELSE
               DISPLAY WS-RTG1 WS-RTG2 WS-RTG3.
           ADD 2 TO M-LINES.
           ADD 85 TO M-CHARS.
           IF ARC-ON = 1
               PERFORM SHOW-ARC.
           MOVE 0 TO WS-NOP.
       SCR-RESEND.
      * THE PARTIAL SEND FAILED (PACPLAT SWITCHED TO FULL REDRAW, NO
      * ANIMATION): SEND THE WHOLE SCREEN INSTEAD.
           MOVE 'FULL' TO REQ-OP.
           CALL 'PACSCR' USING PAC-STATE PAC-REQ PAC-DS
                   PAC-ARC.
           ADD DS-LEN TO M-CHARS.
           MOVE 'SEND' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ PAC-DS.
           MOVE 'PRMT' TO REQ-OP.
       NEW-SCREEN.
           MOVE REQ-OP TO WS-SAVE-OP.
           MOVE 'CLS ' TO REQ-OP.
           ADD 1 TO M-CLEARS.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE WS-SAVE-OP TO REQ-OP.
       SHOW-PROMPT.
           IF REQ-MODE = 'TSO'
               DISPLAY 'CMD (U/D/L/R/Q)?'
               ADD 1 TO M-LINES
               ADD 16 TO M-CHARS.
       SHOW-PROMPT-EXIT.
           EXIT.
       SHOW-END.
           IF F-LOST = 1
               DISPLAY 'LOST'
               ADD 4 TO M-CHARS
           ELSE IF F-WON = 1
               DISPLAY 'WIN'
               ADD 3 TO M-CHARS
           ELSE IF F-QUIT = 1
               DISPLAY 'QUIT'
               ADD 4 TO M-CHARS
           ELSE
               DISPLAY 'EOF'
               ADD 3 TO M-CHARS.
           IF ARC-ON = 1
               DISPLAY 'TURNS ' ARC-TURNS
               ADD 4 TO M-CHARS
           ELSE
               DISPLAY 'TURNS ' TICK-COUNT.
           IF ARC-ON = 1
               DISPLAY 'SCORE ' ARC-SCORE
               ADD 3 TO M-CHARS
           ELSE
               DISPLAY 'SCORE ' SCORE.
           DISPLAY 'LIVES ' LIVES.
           IF REQ-PLAY = 'R'
               MOVE REQ-RTQ TO QU-N
               DISPLAY WS-QUANTA.
           IF ARC-ON = 1
               DISPLAY 'GHOSTS EATEN ' ARC-EATN4
               DISPLAY 'FRUITS EATEN ' ARC-FRUITS
               DISPLAY 'LEVEL ' ARC-LEVEL
               ADD 3 TO M-LINES
               ADD 42 TO M-CHARS.
           IF ARC-ON = 1 AND REQ-HSST NOT = 'N'
               PERFORM SHOW-HS THRU SHOW-HS-EXIT.
           ADD 4 TO M-LINES.
           ADD 26 TO M-CHARS.
           IF REQ-METRIC = 'M'
               PERFORM SHOW-METRICS.
       SHOW-END-EXIT.
           EXIT.
       SHOW-HS.
           IF REQ-HSST = 'E'
               DISPLAY 'HIGH SCORE UNAVAILABLE'
               ADD 1 TO M-LINES
               ADD 22 TO M-CHARS
               GO TO SHOW-HS-EXIT.
           MOVE REQ-HISCORE TO HL-S.
           MOVE REQ-HSLVL TO HL-L.
           IF REQ-HSSCORE > REQ-HISCORE
               MOVE REQ-HSSCORE TO HL-S
               MOVE REQ-HSGLVL TO HL-L.
           DISPLAY HS-LINE.
           ADD 1 TO M-LINES.
           ADD 28 TO M-CHARS.
           IF REQ-HSNEW = 'Y'
               DISPLAY 'NEW HIGH SCORE'
               ADD 1 TO M-LINES
               ADD 14 TO M-CHARS.
           IF REQ-HSNEW = 'F'
               DISPLAY 'HIGH SCORE NOT SAVED'
               ADD 1 TO M-LINES
               ADD 20 TO M-CHARS.
           IF REQ-HSNEW = 'P'
               MOVE REQ-START TO HP-L
               DISPLAY HS-PLINE
               ADD 1 TO M-LINES
               ADD 39 TO M-CHARS.
       SHOW-HS-EXIT.
           EXIT.
       SHOW-METRICS.
           MOVE M-FRAMES TO MT-FRAMES.
           MOVE M-LINES TO MT-LINES.
           MOVE M-CHARS TO MT-CHARS.
           MOVE M-CLEARS TO MT-CLEARS.
           DISPLAY WS-MET.
       SHOW-STATE.
           ADD 1 TO M-FRAMES.
           IF REQ-MODE = 'TSO' AND LAST-RESULT NOT = 'START  '
               PERFORM NEW-SCREEN.
           MOVE TICK-COUNT TO ST-TURN.
           MOVE LAST-CMD TO ST-CMD.
           MOVE LAST-RESULT TO ST-RESULT.
           MOVE PLAYER-X TO ST-X.
           MOVE PLAYER-Y TO ST-Y.
           MOVE SCORE TO ST-SCORE.
           MOVE GH-X (1) TO ST-GX.
           MOVE GH-Y (1) TO ST-GY.
           MOVE LIVES TO ST-LIVES.
           MOVE GAME-STATE TO ST-STATE.
           MOVE PELLETS-LEFT TO ST-LEFT.
           DISPLAY WS-STATUS-LINE.
           ADD 1 TO M-LINES.
           ADD 61 TO M-CHARS.
           IF ARC-ON = 1
               PERFORM SHOW-ARC.
           IF GHOST-COUNT > 1
               PERFORM SHOW-EXTRA THRU SHOW-EXTRA-EXIT.
           PERFORM SHOW-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
       SHOW-STATE-EXIT.
           EXIT.
       SHOW-ROW.
           MOVE MAP-ROW (WS-ROW) TO WS-LINE.
           IF ARC-ON = 1 AND ARC-BT > 0 AND WS-ROW = ARC-BY
               MOVE '%' TO WS-LINE-CELL (ARC-BX).
           IF WS-ROW = PLAYER-Y
               MOVE 'P' TO WS-LINE-CELL (PLAYER-X).
           PERFORM OVERLAY-GHOST THRU OVERLAY-GHOST-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           DISPLAY WS-LINE.
           ADD 1 TO M-LINES.
           ADD 20 TO M-CHARS.
       OVERLAY-GHOST.
           IF WS-ROW = GH-Y (WS-G)
               MOVE GH-X (WS-G) TO WS-GX
               MOVE 'G' TO WS-LINE-CELL (WS-GX)
               IF ARC-ON = 1 AND ARC-GM (WS-G) NOT = 'N'
                   MOVE ARC-GM (WS-G) TO WS-LINE-CELL (WS-GX).
       OVERLAY-GHOST-EXIT.
           EXIT.
       SHOW-EXTRA.
           MOVE GH-X (2) TO XL2-X.
           MOVE GH-Y (2) TO XL2-Y.
           ADD 1 TO M-LINES.
           IF GHOST-COUNT = 2
               DISPLAY WS-XL2
               ADD 8 TO M-CHARS
           ELSE
               MOVE GH-X (3) TO XL3-X
               MOVE GH-Y (3) TO XL3-Y
               DISPLAY WS-XL2 WS-XL3
               ADD 17 TO M-CHARS.
       SHOW-EXTRA-EXIT.
           EXIT.
      * ------------- MVS-GP1 ARCADE TEXT (D36, ARC-ON = 1) ----------
       ARC-HEAD.
           IF ARC-ON = 0
               GO TO ARC-HEAD-EXIT.
           DISPLAY 'RULES ARCADE'.
           DISPLAY 'LEVEL ' ARC-LEVEL.
           ADD 2 TO M-LINES.
           ADD 21 TO M-CHARS.
       ARC-HEAD-EXIT.
           EXIT.
       SHOW-ARC.
           MOVE ARC-SCORE TO AL-S.
           MOVE ARC-POWER TO AL-PW.
           MOVE ARC-FR TO AL-FR.
           MOVE ARC-FTURN TO AL-FT.
           MOVE ARC-FACC TO AL-FA.
           MOVE ARC-CHAIN TO AL-CH.
           MOVE ARC-EVT TO AL-EV.
           MOVE ARC-PTS TO AL-P.
           MOVE ARC-EATEN TO AL-N.
           MOVE ARC-GM (1) TO AL-M1.
           MOVE ARC-GW (1) TO AL-W1.
           MOVE ARC-GM (2) TO AL-M2.
           MOVE ARC-GW (2) TO AL-W2.
           MOVE ARC-GM (3) TO AL-M3.
           MOVE ARC-GW (3) TO AL-W3.
           IF GHOST-COUNT = 1
               DISPLAY WS-ARC-LINE
           ELSE IF GHOST-COUNT = 2
               DISPLAY WS-ARC-LINE WS-ARC-G2
           ELSE
               DISPLAY WS-ARC-LINE WS-ARC-G2 WS-ARC-G3.
           ADD 1 TO M-LINES.
           ADD 80 TO M-CHARS.
           PERFORM SHOW-LVL.
       SHOW-LVL.
           MOVE ARC-LEVEL TO LL-LV.
           MOVE AI-LEVEL TO LL-AI.
           MOVE ARC-ITEMS TO LL-IT.
           MOVE ARC-BN TO LL-BN.
           MOVE ARC-BT TO LL-BT.
           MOVE ARC-BK TO LL-BK.
           MOVE ARC-BV TO LL-BV.
           MOVE ARC-XL TO LL-XL.
           MOVE ARC-EVF TO LL-EV.
           DISPLAY WS-LVL-LINE.
           ADD 1 TO M-LINES.
           ADD 63 TO M-CHARS.
       ARC-BELL.
      * MVS-GP2 (D37): ONLY REQ-BELL AND THE SB- COPIES CHANGE HERE.
           IF SB-SENT = 1 AND ARC-NDIE > SB-NDIE
               MOVE 'Y' TO REQ-BELL.
           IF SB-SENT = 1 AND ARC-XL > SB-XL
               MOVE 'Y' TO REQ-BELL.
           IF SB-SENT = 1 AND ARC-LEVEL > SB-LVL
               MOVE 'Y' TO REQ-BELL.
           MOVE ARC-NDIE TO SB-NDIE.
           MOVE ARC-XL TO SB-XL.
           MOVE ARC-LEVEL TO SB-LVL.
