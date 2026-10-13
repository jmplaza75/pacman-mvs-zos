      * PACMAIN : DRIVER ONLY. NO GAME RULES, NO I/O STATEMENTS.
      * PACPLAT (HOST)  PACINPT (CARDS)  PACGAME (RULES)  PACMAP (MAP)
      * PACAI (GHOSTS)  PACDISP (TEXT OUTPUT). SEE DOCS/ARCHITECTURE.MD
      * PARM 'TSO' [AIL N] REQUESTS THE INTERACTIVE TSO ADAPTER
      * (MVS-8): CONFIG COMES FROM THE PARM, THE BOARD IS SHOWN BEFORE
      * THE FIRST PROMPT. NO PARM = BATCH CARD MODE (REFERENCE).
      * NO INPUT IS READ ONCE THE GAME HAS ENDED (QUIT, WON, LOST).
      * OPTIONAL 'M' IN PARM COLUMN 11 (E.G. 'BAT       M' OR
      * 'TSO AI3 2 M') MAKES PACDISP PRINT A FINAL METRICS LINE.
      * COLUMN 12 = COLOUR (MVS-G1): A AUTO, Y YES, N/BLANK NO. PARM
      * 'TSD ...' IS THE BATCH DRY RUN OF THE COLOUR SCREENS (HEX).
      * COLUMN 13 = HIGHLIGHT (MVS-G2): A AUTO, Y YES, N/BLANK NO.
      * COLUMN 14 = ANIM (MVS-G3): A AUTO, Y YES, N/BLANK NO.
      * COLUMN 15 = REDRAW: P PARTIAL, ANYTHING ELSE FULL (REFERENCE).
      * COLUMN 16 = GLYPHS (MVS-G4): A AUTO, G GRAPHIC, B BASE, C OR
      * BLANK CLASSIC (THE G3 SCREENS).
      * COLUMN 17 = SCALE (MVS-GS): A AUTO, 4 4X2, 3 3X2, N/BLANK NO
      * (THE G4 SCREENS).
      * COLUMN 18 = CANVAS (MVS-GS GEOMETRY): A AUTO (THE TERMINAL'S
      * ALTERNATE SIZE), D OR BLANK DEFAULT 80 X 24; TSD: SIMULATED.
      * COLUMN 19 = PLAY (MVS-RT, D33): R REALTIME, ANYTHING ELSE TURN.
      * REALTIME (RT-GAME, SEPARATE FROM THE TURN LOOP) NEEDS TSC OR THE
      * BAT / TSD REFERENCE MODES; TSO LINE MODE PLAYS TURN. BEFORE THE
      * START: BLOCKING READS; THE FIRST DIRECTION STARTS THE CLOCK.
      * EACH QUANTUM: ALL INPUT NOW AVAILABLE -> PACRT RIN, PACRT RQ,
      * ONE FRAME (PACDISP RTQF), THEN THE NEXT ABSOLUTE DEADLINE
      * (PACPLAT WDLN, TSC ONLY). PAUSE: BLOCKING READS. A LOST TSC
      * SESSION CONTINUES AS TURN IN LINE MODE.
      * COLUMN 20 = SOUND (MVS-S1): A AUTO, Y YES, N/BLANK NO (THE 3270
      * ALARM ON START, DEATH AND WIN; COLOUR FULL-SCREEN ONLY).
      * COLUMN 21 = RULES (MVS-GP1, D36): A ARCADE (POWER PELLETS, STATE
      * PAC-ARC), ANYTHING ELSE CLASSIC (1.0-MVS).
      * COLUMNS 22-23 = START LEVEL (MVS-GP2, D37, ARCADE ONLY): 1 OR 2
      * DIGITS FROM COLUMN 22 TO THE PARM END, 1-99; ABSENT OR ANY
      * OTHER VALUE = 1 (THE USUAL START).
      * COLUMN 24 = SPEED (MVS-RP RP.3, D39 6, REALTIME ONLY): F FAST
      * (125 MS QUANTUM), ANYTHING ELSE NORMAL (150 MS). THE LEVEL IS
      * THEN 2 DIGITS (THE CLIST ZERO-PADS IT); A DIGIT IN COLUMN 24
      * MAKES 22-24 ONE 3-DIGIT LEVEL (= 1, AS BEFORE RP.3). THE ONLY
      * PLACE WHERE THE QUANTUM IS CHOSEN: REQ-RTPER (PACPLAT
      * DEADLINES, PACRT AND PACGAME CONVERSIONS, PACSCR TIMERS).
      * MVS-HS (D38, ARCADE ONLY): PACPLAT HSRD RIGHT AFTER INIT READS
      * THE HIGH SCORE; AFTER THE LAST FRAME HS-END HANDS THE FINAL
      * SCORE, LEVEL AND ELIGIBILITY (STARTED AT LEVEL 1) TO PACPLAT
      * HSWR, WHICH DECIDES AND WRITES; PACDISP END PRINTS THE RESULT.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACMAIN.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       01  PAC-ARC COPY PACARC.
       01  WS-CFG.
           05  WS-CFG-CH         PIC X OCCURS 5 TIMES.
       01  WS-K                  PIC 99.
       01  RT-OVER               PIC 9 VALUE 0.
       01  RT-FRAME              PIC X VALUE SPACE.
       01  WS-LV.
           05  WS-LV1            PIC X.
           05  WS-LV2            PIC X.
       01  WS-LVN REDEFINES WS-LV PIC 99.
       01  WS-LVK                PIC 99.
       01  WS-NOP                PIC 9.
       LINKAGE SECTION.
       01  PARM-AREA.
           05  PARM-LEN          PIC S9(4) COMP.
           05  PARM-MODE         PIC X(3).
           05  FILLER            PIC X.
           05  PARM-CFG          PIC X(5).
           05  FILLER            PIC X.
           05  PARM-MET          PIC X.
           05  PARM-COLOR        PIC X.
           05  PARM-HILITE       PIC X.
           05  PARM-ANIM         PIC X.
           05  PARM-REDRAW       PIC X.
           05  PARM-GLYPHS       PIC X.
           05  PARM-SCALE        PIC X.
           05  PARM-CANVAS       PIC X.
           05  PARM-PLAY         PIC X.
           05  PARM-SOUND        PIC X.
           05  PARM-RULES        PIC X.
           05  PARM-LV1          PIC X.
           05  PARM-LV2          PIC X.
           05  PARM-SPEED        PIC X.
       PROCEDURE DIVISION USING PARM-AREA.
       MAIN-PARA.
           MOVE 'BAT' TO REQ-MODE.
           MOVE SPACE TO REQ-METRIC.
           IF PARM-LEN > 10 AND PARM-MET = 'M'
               MOVE 'M' TO REQ-METRIC.
           IF PARM-LEN > 2 AND PARM-MODE = 'TSO'
               MOVE 'TSO' TO REQ-MODE.
           IF PARM-LEN > 2 AND PARM-MODE = 'TSD'
               MOVE 'TSD' TO REQ-MODE.
           MOVE 'N' TO REQ-COLOR.
           IF PARM-LEN > 11
               MOVE PARM-COLOR TO REQ-COLOR.
           MOVE 'N' TO REQ-HILITE.
           IF PARM-LEN > 12
               MOVE PARM-HILITE TO REQ-HILITE.
           MOVE 'N' TO REQ-ANIM.
           IF PARM-LEN > 13
               MOVE PARM-ANIM TO REQ-ANIM.
           MOVE 'F' TO REQ-REDRAW.
           IF PARM-LEN > 14
               MOVE PARM-REDRAW TO REQ-REDRAW.
           MOVE 'C' TO REQ-GLYPHS.
           IF PARM-LEN > 15
               MOVE PARM-GLYPHS TO REQ-GLYPHS.
           MOVE 'N' TO REQ-SCALE.
           IF PARM-LEN > 16
               MOVE PARM-SCALE TO REQ-SCALE.
           MOVE 'D' TO REQ-CANVAS.
           MOVE 0 TO REQ-CW.
           MOVE 0 TO REQ-CH.
           IF PARM-LEN > 17
               MOVE PARM-CANVAS TO REQ-CANVAS.
           MOVE 'T' TO REQ-PLAY.
           IF PARM-LEN > 18 AND PARM-PLAY = 'R'
               MOVE 'R' TO REQ-PLAY.
           MOVE 'N' TO REQ-SOUND.
           IF PARM-LEN > 19
               MOVE PARM-SOUND TO REQ-SOUND.
           MOVE 'N' TO REQ-BELL.
           MOVE 'C' TO REQ-RULES.
           IF PARM-LEN > 20
               MOVE PARM-RULES TO REQ-RULES.
           MOVE 1 TO REQ-START.
           IF PARM-LEN = 22
               MOVE '0' TO WS-LV1
               MOVE PARM-LV1 TO WS-LV2
               PERFORM SET-START.
           IF PARM-LEN > 22
               MOVE PARM-LV1 TO WS-LV1
               MOVE PARM-LV2 TO WS-LV2
               PERFORM SET-START.
           IF PARM-LEN > 23 AND PARM-SPEED NUMERIC
               MOVE 1 TO REQ-START.
           MOVE 150 TO REQ-RTPER.
           IF PARM-LEN > 23 AND PARM-SPEED = 'F'
               MOVE 125 TO REQ-RTPER.
           MOVE 0 TO REQ-RTFRT.
           MOVE 0 TO REQ-RTRDY.
           MOVE 0 TO REQ-RTPUQ.
           MOVE 'B' TO REQ-STEP.
           MOVE SPACE TO REQ-SENDST.
           MOVE 'INIT' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE 'N' TO REQ-HSST.
           MOVE 'N' TO REQ-HSNEW.
           IF REQ-RULES = 'A'
               MOVE 'HSRD' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           IF REQ-MODE = 'TSO'
               MOVE 'T' TO REQ-PLAY.
           MOVE 'RSET' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE 'OPEN' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
           MOVE 'HEAD' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           IF REQ-PLAY = 'R'
               PERFORM RT-GAME THRU RT-GAME-EXIT
           ELSE IF REQ-MODE = 'BAT'
               PERFORM BAT-START THRU BAT-START-EXIT
           ELSE
               PERFORM TSO-START THRU TSO-START-EXIT.
           PERFORM TURN-PARA THRU TURN-PARA-EXIT
               UNTIL F-EOF = 1 OR F-QUIT = 1 OR F-WON = 1
                  OR F-LOST = 1.
           IF REQ-RULES = 'A'
               PERFORM HS-END.
           MOVE 'END ' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE 'CLOS' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
           MOVE 'FINI' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           STOP RUN.
       RT-GAME.
           MOVE 'RINI' TO REQ-OP.
           CALL 'PACRT' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           IF REQ-MODE = 'BAT'
               PERFORM RT-READB
               PERFORM RT-CONFIG THRU RT-CONFIG-EXIT
           ELSE IF PARM-LEN > 4
               PERFORM COPY-PARM-CFG
               MOVE 'PARM' TO REQ-OP
               CALL 'PACINPT' USING PAC-REQ
               PERFORM APPLY-CONFIG THRU APPLY-CONFIG-EXIT.
           PERFORM SHOW-START.
      * THE FIRST SCREEN (TSC/TSD; NOTHING IN BAT, WHERE THE EVENT READ
      * AHEAD FOR THE CONFIGURATION MUST STAY IN REQ-KIND).
           IF REQ-MODE NOT = 'BAT'
               MOVE 'MOV' TO REQ-KIND
               MOVE 'PRMT' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC
               PERFORM RT-READB.
           PERFORM RT-PRE THRU RT-PRE-EXIT
               UNTIL REQ-RTSTAT NOT = 'WAIT' OR RT-OVER = 1.
           IF RT-OVER = 0 AND REQ-MODE = 'TSC'
               MOVE 'CLOK' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           PERFORM RT-QUANTUM THRU RT-QUANTUM-EXIT
               UNTIL RT-OVER = 1.
           IF REQ-PLAY = 'T' AND F-EOF = 0 AND F-QUIT = 0
                             AND F-WON = 0 AND F-LOST = 0
               MOVE 'B' TO REQ-STEP
               PERFORM READ-INPUT THRU READ-INPUT-EXIT.
       RT-GAME-EXIT.
           EXIT.
       RT-CONFIG.
      * BATCH REALTIME: AN OPTIONAL FIRST CARD AI<L> <N>.
           IF REQ-KIND = 'CFG'
               MOVE 'CFG ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
               PERFORM RT-READB.
       RT-CONFIG-EXIT.
           EXIT.
       RT-READB.
           MOVE SPACE TO REQ-INKEY.
           MOVE 'RTRB' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
       RT-READ.
           MOVE SPACE TO REQ-INKEY.
           MOVE 'RTRD' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
       RT-PRE.
      * BEFORE THE START: ONE EVENT, THEN A SCREEN (RESTORE);
      * A DIRECTION STARTS THE GAME (ITS QUANTUM IS THE FIRST ONE).
           PERFORM RT-EVENT THRU RT-EVENT-EXIT.
           IF RT-OVER = 1 OR REQ-RTSTAT NOT = 'WAIT'
               GO TO RT-PRE-EXIT.
      * RT3: EVERY INPUT GETS A SCREEN (KEYBOARD RESTORE), ELSE THE NEXT
      * KEY WOULD BE LOST WITH C3270 TYPEAHEAD OFF.
           IF REQ-KIND NOT = 'NON'
               PERFORM RT-PRE-SCREEN.
           PERFORM RT-READB.
       RT-PRE-EXIT.
           EXIT.
       RT-PRE-SCREEN.
           MOVE 'MOV' TO REQ-KIND.
           IF RT-FRAME = 'F'
               MOVE 'RDR' TO REQ-KIND.
           MOVE 'PRMT' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE SPACE TO RT-FRAME.
       RT-QUANTUM.
           PERFORM RT-COLLECT THRU RT-COLLECT-EXIT.
           PERFORM RT-PAUSED THRU RT-PAUSED-EXIT
               UNTIL REQ-RTSTAT NOT = 'PAUS' OR RT-OVER = 1.
           IF RT-OVER = 1
               GO TO RT-QUANTUM-EXIT.
           MOVE 'RQ  ' TO REQ-OP.
           CALL 'PACRT' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE RT-FRAME TO REQ-RTFR.
           MOVE SPACE TO RT-FRAME.
           MOVE 'RTQF' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           IF F-WON = 1 OR F-LOST = 1
               MOVE 1 TO RT-OVER
               GO TO RT-QUANTUM-EXIT.
           IF REQ-MODE = 'TSO'
               MOVE 'T' TO REQ-PLAY
               MOVE 1 TO RT-OVER
               GO TO RT-QUANTUM-EXIT.
           IF REQ-MODE = 'TSC'
               MOVE 'WDLN' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
       RT-QUANTUM-EXIT.
           EXIT.
       RT-COLLECT.
      * EVERY INPUT AVAILABLE NOW (A CARD = THE INPUT OF ONE QUANTUM).
           MOVE SPACES TO REQ-KIND.
           PERFORM RT-DRAIN-ONE THRU RT-DRAIN-ONE-EXIT
               UNTIL REQ-KIND = 'NON' OR RT-OVER = 1.
       RT-COLLECT-EXIT.
           EXIT.
       RT-DRAIN-ONE.
           PERFORM RT-READ.
           PERFORM RT-EVENT THRU RT-EVENT-EXIT.
       RT-DRAIN-ONE-EXIT.
           EXIT.
       RT-PAUSED.
      * PAUSE: THE SCREEN, THEN BLOCKING READS UNTIL P (OR Q / EOF); THE
      * CLOCK RESTARTS FROM NOW; WHAT FOLLOWS IN THE INPUT IS COLLECTED.
           IF RT-FRAME = SPACE
               MOVE 'P' TO RT-FRAME.
           PERFORM RT-PRE-SCREEN.
           PERFORM RT-PAUSE-ONE THRU RT-PAUSE-ONE-EXIT
               UNTIL REQ-RTSTAT NOT = 'PAUS' OR RT-OVER = 1.
           IF RT-OVER = 1
               GO TO RT-PAUSED-EXIT.
           IF REQ-MODE = 'TSC'
               MOVE 'CLOK' TO REQ-OP
               CALL 'PACPLAT' USING PAC-REQ.
           PERFORM RT-COLLECT THRU RT-COLLECT-EXIT.
       RT-PAUSED-EXIT.
           EXIT.
       RT-PAUSE-ONE.
           PERFORM RT-READB.
           PERFORM RT-EVENT THRU RT-EVENT-EXIT.
           IF RT-OVER = 0 AND REQ-RTSTAT = 'PAUS'
                          AND REQ-KIND NOT = 'NON'
               PERFORM RT-PRE-SCREEN.
       RT-PAUSE-ONE-EXIT.
           EXIT.
       RT-EVENT.
      * ONE INPUT EVENT: DIRECTIONS AND PAUSE GO TO PACRT, EVERY EVENT
      * IS RECORDED THERE; Q / EOF END, A LOST TSC SESSION GOES TURN.
           IF REQ-KIND = 'NON' OR REQ-KIND = 'IGN' OR REQ-KIND = 'CFG'
               GO TO RT-EVENT-EXIT.
           IF REQ-KIND = 'ERR'
               MOVE 'T' TO REQ-PLAY
               MOVE 1 TO RT-OVER
               GO TO RT-EVENT-EXIT.
           IF REQ-KIND = 'EOF'
               MOVE 'EOF ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
               MOVE 1 TO RT-OVER
               GO TO RT-EVENT-EXIT.
           MOVE 'RIN ' TO REQ-OP.
           CALL 'PACRT' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           IF REQ-KIND = 'QUI'
               MOVE 'QUIT' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
               MOVE 1 TO RT-OVER
               GO TO RT-EVENT-EXIT.
           IF REQ-INKEY = 'E' AND RT-FRAME = SPACE
               MOVE 'P' TO RT-FRAME.
           IF REQ-KIND = 'INV'
               MOVE 'INVL' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           IF REQ-KIND = 'INV' AND RT-FRAME = SPACE
               MOVE 'P' TO RT-FRAME.
           IF REQ-KIND = 'RDR'
               MOVE 'F' TO RT-FRAME.
       RT-EVENT-EXIT.
           EXIT.
       BAT-START.
           PERFORM READ-INPUT THRU READ-INPUT-EXIT.
           PERFORM CHECK-CONFIG THRU CHECK-CONFIG-EXIT.
           PERFORM SHOW-START.
       BAT-START-EXIT.
           EXIT.
       TSO-START.
           IF PARM-LEN > 4
               PERFORM COPY-PARM-CFG
               MOVE 'PARM' TO REQ-OP
               CALL 'PACINPT' USING PAC-REQ
               PERFORM APPLY-CONFIG THRU APPLY-CONFIG-EXIT.
           PERFORM SHOW-START.
           PERFORM READ-INPUT THRU READ-INPUT-EXIT.
       TSO-START-EXIT.
           EXIT.
       SET-START.
           MOVE 0 TO WS-LVK.
           IF WS-LV NUMERIC
               MOVE WS-LVN TO WS-LVK.
           IF WS-LVK > 0
               MOVE WS-LVK TO REQ-START.
           MOVE 0 TO WS-NOP.
       COPY-PARM-CFG.
      * ONLY PARM-LEN BYTES ARE VALID: BLANK WHAT LIES BEYOND THEM.
           MOVE PARM-CFG TO WS-CFG.
           COMPUTE WS-K = PARM-LEN - 3.
           PERFORM BLANK-CFG-CH UNTIL WS-K > 5.
           MOVE WS-CFG TO REQ-TEXT.
       BLANK-CFG-CH.
           MOVE SPACE TO WS-CFG-CH (WS-K).
           ADD 1 TO WS-K.
       SHOW-START.
           MOVE 'INIT' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE 'STAT' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
       APPLY-CONFIG.
           IF REQ-KIND = 'CFG'
               MOVE 'CFG ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC.
       APPLY-CONFIG-EXIT.
           EXIT.
       READ-INPUT.
           MOVE 'PRMT' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE 'READ' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
           PERFORM IDLE-TICK UNTIL REQ-KIND NOT = 'TCK'.
           IF REQ-KIND = 'EOF'
               MOVE 'EOF ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC.
       READ-INPUT-EXIT.
           EXIT.
       IDLE-TICK.
      * MVS-G3 VISUAL TICK: THE WAIT FOR INPUT WAS INTERRUPTED BY AN
      * IDLE TICK. ONLY THE SCREEN CHANGES; NO GAME CALL, NO TURN.
           MOVE 'TICK' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
           MOVE 'READ' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
       CHECK-CONFIG.
           IF REQ-KIND = 'CFG'
               MOVE 'CFG ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
               PERFORM READ-INPUT THRU READ-INPUT-EXIT.
       CHECK-CONFIG-EXIT.
           EXIT.
       TURN-PARA.
           PERFORM DISPATCH THRU DISPATCH-EXIT.
           IF F-QUIT = 0 AND F-WON = 0 AND F-LOST = 0
               PERFORM READ-INPUT THRU READ-INPUT-EXIT.
       TURN-PARA-EXIT.
           EXIT.
       DISPATCH.
           IF REQ-KIND = 'MOV'
               MOVE 'MOVE' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
               MOVE 'STAT' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC
           ELSE IF REQ-KIND = 'QUI'
               MOVE 'QUIT' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
                   PAC-ARC
           ELSE IF REQ-KIND = 'RDR'
               MOVE 'STAT' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC
           ELSE
               MOVE 'INVL' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
                   PAC-ARC.
       DISPATCH-EXIT.
           EXIT.
       HS-END.
           MOVE ARC-SCORE TO REQ-HSSCORE.
           MOVE ARC-LEVEL TO REQ-HSGLVL.
           MOVE 'N' TO REQ-HSELIG.
           IF REQ-START = 1
               MOVE 'Y' TO REQ-HSELIG.
           MOVE 'HSWR' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
