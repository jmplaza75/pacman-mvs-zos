//PACREL10 JOB (1),'PACMAN RELEASE',CLASS=A,MSGCLASS=A,
//             MSGLEVEL=(1,1),REGION=4096K
//* PREFIX HERC01.PACMAN
//CPY1     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.COPY(PACSTATE),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * SHARED GAME STATE. NO VALUE CLAUSES (USED IN LINKAGE TOO).
      * ONLY PACGAME/PACMAP/PACAI MODIFY IT; PACDISP READS IT.
       01  PAC-STATE.
           05  MAP-AREA.
               10  MAP-ROW           OCCURS 10 TIMES.
                   15  MAP-CELL      PIC X OCCURS 20 TIMES.
           05  PLAYER-X              PIC 99.
           05  PLAYER-Y              PIC 99.
           05  TICK-COUNT            PIC 999.
           05  SCORE                 PIC 9(4).
           05  PELLETS-LEFT          PIC 999.
           05  LIVES                 PIC 9.
           05  GAME-STATE            PIC X(7).
           05  LAST-CMD              PIC X.
           05  LAST-RESULT           PIC X(7).
           05  F-WON                 PIC 9.
           05  F-LOST                PIC 9.
           05  F-QUIT                PIC 9.
           05  F-EOF                 PIC 9.
           05  F-HIT                 PIC 9.
           05  AI-LEVEL              PIC 9.
           05  GHOST-COUNT           PIC 9.
           05  GHOST-SEED            PIC 9(5).
           05  GH-ENTRY              OCCURS 3 TIMES.
               10  GH-X              PIC 99.
               10  GH-Y              PIC 99.
               10  GH-DIR            PIC 9.
ZZ
//CPY2     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.COPY(PACREQ),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * DRIVER REQUEST BLOCK: OP CODE IN, INPUT RESULT OUT.
       01  PAC-REQ.
           05  REQ-OP                PIC X(4).
           05  REQ-KIND              PIC X(3).
           05  REQ-DIR               PIC X.
           05  REQ-CHAR              PIC X.
           05  REQ-LEVEL             PIC 9.
           05  REQ-COUNT             PIC 9.
           05  REQ-MODE              PIC X(3).
           05  REQ-TEXT              PIC X(8).
ZZ
//CPY3     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.COPY(PACMREQ),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * MAP SERVICE REQUEST: M-OP = LOAD WALL CLR  EAT  CNT
       01  MAP-REQ.
           05  M-OP                  PIC X(4).
           05  M-X                   PIC 99.
           05  M-Y                   PIC 99.
           05  M-FLAG                PIC 9.
           05  M-COUNT               PIC 999.
ZZ
//SRC1     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.COBOL(PACMAIN),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACMAIN : DRIVER ONLY. NO GAME RULES, NO I/O STATEMENTS.
      * PACPLAT (HOST)  PACINPT (CARDS)  PACGAME (RULES)  PACMAP (MAP)
      * PACAI (GHOSTS)  PACDISP (TEXT OUTPUT). SEE DOCS/ARCHITECTURE.MD
      * PARM 'TSO' [AIL N] REQUESTS THE INTERACTIVE TSO ADAPTER
      * (MVS-8): CONFIG COMES FROM THE PARM, THE BOARD IS SHOWN BEFORE
      * THE FIRST PROMPT. NO PARM = BATCH CARD MODE (REFERENCE).
      * NO INPUT IS READ ONCE THE GAME HAS ENDED (QUIT, WON, LOST).
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
       01  WS-CFG.
           05  WS-CFG-CH         PIC X OCCURS 5 TIMES.
       01  WS-K                  PIC 99.
       LINKAGE SECTION.
       01  PARM-AREA.
           05  PARM-LEN          PIC S9(4) COMP.
           05  PARM-MODE         PIC X(3).
           05  FILLER            PIC X.
           05  PARM-CFG          PIC X(5).
       PROCEDURE DIVISION USING PARM-AREA.
       MAIN-PARA.
           MOVE 'BAT' TO REQ-MODE.
           IF PARM-LEN > 2 AND PARM-MODE = 'TSO'
               MOVE 'TSO' TO REQ-MODE.
           MOVE 'INIT' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE 'RSET' TO REQ-OP.
           CALL 'PACGAME' USING PAC-STATE PAC-REQ.
           MOVE 'OPEN' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
           MOVE 'HEAD' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ.
           IF REQ-MODE = 'TSO'
               PERFORM TSO-START THRU TSO-START-EXIT
           ELSE
               PERFORM BAT-START THRU BAT-START-EXIT.
           PERFORM TURN-PARA THRU TURN-PARA-EXIT
               UNTIL F-EOF = 1 OR F-QUIT = 1 OR F-WON = 1
                  OR F-LOST = 1.
           MOVE 'END ' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ.
           MOVE 'CLOS' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
           MOVE 'FINI' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           STOP RUN.
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
           CALL 'PACGAME' USING PAC-STATE PAC-REQ.
           MOVE 'STAT' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ.
       APPLY-CONFIG.
           IF REQ-KIND = 'CFG'
               MOVE 'CFG ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ.
       APPLY-CONFIG-EXIT.
           EXIT.
       READ-INPUT.
           MOVE 'PRMT' TO REQ-OP.
           CALL 'PACDISP' USING PAC-STATE PAC-REQ.
           MOVE 'READ' TO REQ-OP.
           CALL 'PACINPT' USING PAC-REQ.
           IF REQ-KIND = 'EOF'
               MOVE 'EOF ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ.
       READ-INPUT-EXIT.
           EXIT.
       CHECK-CONFIG.
           IF REQ-KIND = 'CFG'
               MOVE 'CFG ' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
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
               MOVE 'STAT' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
           ELSE IF REQ-KIND = 'QUI'
               MOVE 'QUIT' TO REQ-OP
               CALL 'PACGAME' USING PAC-STATE PAC-REQ
           ELSE IF REQ-KIND = 'RDR'
               MOVE 'STAT' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ
           ELSE
               MOVE 'INVL' TO REQ-OP
               CALL 'PACDISP' USING PAC-STATE PAC-REQ.
       DISPATCH-EXIT.
           EXIT.
ZZ
//COB1     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ1,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.COBOL(PACMAIN),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.COPY,DISP=SHR
//SRC2     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.COBOL(PACGAME),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACGAME : GAME RULES AND STATE (PORTABLE, NO TERMINAL I/O).
      * OPS : RSET  DEFAULTS (3 LIVES, PLAYER 2,2, AI1, 1 GHOST)
      *       CFG   APPLY REQ-LEVEL / REQ-COUNT FROM THE CONFIG CARD
      *       INIT  LOAD MAP, PLACE GHOSTS, COUNT PELLETS
      *       MOVE  ONE TURN (REQ-DIR, REQ-CHAR)   QUIT  EOF
      * RULES : SEE DOCS/DECISIONS.MD D7, D9, D11, D14.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACGAME.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  MAP-REQ COPY PACMREQ.
       01  GS-DATA               PIC X(15) VALUE '190930209419023'.
       01  GS-TABLE REDEFINES GS-DATA.
           05  GS-ENTRY          OCCURS 3 TIMES.
               10  GS-X          PIC 99.
               10  GS-Y          PIC 99.
               10  GS-DIR        PIC 9.
       01  WS-G                  PIC 9.
       01  NEW-X                 PIC 99.
       01  NEW-Y                 PIC 99.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'RSET'
               PERFORM DO-RESET
           ELSE IF REQ-OP = 'CFG '
               PERFORM DO-CONFIG
           ELSE IF REQ-OP = 'INIT'
               PERFORM DO-INIT
           ELSE IF REQ-OP = 'MOVE'
               PERFORM DO-MOVE
           ELSE IF REQ-OP = 'QUIT'
               PERFORM DO-QUIT
           ELSE IF REQ-OP = 'EOF '
               MOVE 1 TO F-EOF.
           GOBACK.
       DO-RESET.
           MOVE 2 TO PLAYER-X.
           MOVE 2 TO PLAYER-Y.
           MOVE 0 TO TICK-COUNT.
           MOVE 0 TO SCORE.
           MOVE 0 TO PELLETS-LEFT.
           MOVE 3 TO LIVES.
           MOVE 'READY  ' TO GAME-STATE.
           MOVE ' ' TO LAST-CMD.
           MOVE 'START  ' TO LAST-RESULT.
           MOVE 0 TO F-WON.
           MOVE 0 TO F-LOST.
           MOVE 0 TO F-QUIT.
           MOVE 0 TO F-EOF.
           MOVE 0 TO F-HIT.
           MOVE 1 TO AI-LEVEL.
           MOVE 1 TO GHOST-COUNT.
           MOVE 12345 TO GHOST-SEED.
       DO-CONFIG.
           MOVE REQ-LEVEL TO AI-LEVEL.
           MOVE REQ-COUNT TO GHOST-COUNT.
       DO-INIT.
           MOVE 'LOAD' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           MOVE PLAYER-X TO M-X.
           MOVE PLAYER-Y TO M-Y.
           MOVE 'CLR ' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           PERFORM RESET-GHOST VARYING WS-G FROM 1 BY 1
               UNTIL WS-G > GHOST-COUNT.
           PERFORM CLEAR-GHOST-CELL VARYING WS-G FROM 1 BY 1
               UNTIL WS-G > GHOST-COUNT.
           MOVE 'CNT ' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           MOVE M-COUNT TO PELLETS-LEFT.
       RESET-GHOST.
           MOVE GS-X (WS-G) TO GH-X (WS-G).
           MOVE GS-Y (WS-G) TO GH-Y (WS-G).
           MOVE GS-DIR (WS-G) TO GH-DIR (WS-G).
       CLEAR-GHOST-CELL.
           MOVE GH-X (WS-G) TO M-X.
           MOVE GH-Y (WS-G) TO M-Y.
           MOVE 'CLR ' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
       DO-QUIT.
           MOVE 1 TO F-QUIT.
           MOVE 'QUIT   ' TO GAME-STATE.
       DO-MOVE.
           MOVE REQ-CHAR TO LAST-CMD.
           MOVE PLAYER-X TO NEW-X.
           MOVE PLAYER-Y TO NEW-Y.
           MOVE 'MOVED  ' TO LAST-RESULT.
           PERFORM AIM-MOVE THRU AIM-MOVE-EXIT.
           ADD 1 TO TICK-COUNT.
           MOVE NEW-X TO M-X.
           MOVE NEW-Y TO M-Y.
           MOVE 'WALL' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 1
               MOVE 'BLOCKED' TO LAST-RESULT
           ELSE
               MOVE NEW-X TO PLAYER-X
               MOVE NEW-Y TO PLAYER-Y
               PERFORM EAT-PELLET THRU EAT-PELLET-EXIT.
           PERFORM ROUND-END THRU ROUND-END-EXIT.
           PERFORM SET-STATE THRU SET-STATE-EXIT.
       AIM-MOVE.
           IF REQ-DIR = 'U'
               SUBTRACT 1 FROM NEW-Y
           ELSE IF REQ-DIR = 'D'
               ADD 1 TO NEW-Y
           ELSE IF REQ-DIR = 'L'
               SUBTRACT 1 FROM NEW-X
           ELSE IF REQ-DIR = 'R'
               ADD 1 TO NEW-X.
       AIM-MOVE-EXIT.
           EXIT.
       EAT-PELLET.
           MOVE PLAYER-X TO M-X.
           MOVE PLAYER-Y TO M-Y.
           MOVE 'EAT ' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 1
               ADD 10 TO SCORE
               SUBTRACT 1 FROM PELLETS-LEFT.
           IF PELLETS-LEFT = 0
               MOVE 1 TO F-WON.
       EAT-PELLET-EXIT.
           EXIT.
       ROUND-END.
           MOVE 0 TO F-HIT.
           PERFORM CHECK-HIT THRU CHECK-HIT-EXIT.
           IF F-HIT = 0 AND F-WON = 0 AND AI-LEVEL > 0
               CALL 'PACAI' USING PAC-STATE
               PERFORM CHECK-HIT THRU CHECK-HIT-EXIT.
           IF F-HIT = 1
               PERFORM LOSE-LIFE THRU LOSE-LIFE-EXIT.
       ROUND-END-EXIT.
           EXIT.
       CHECK-HIT.
           PERFORM HIT-TEST THRU HIT-TEST-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
       CHECK-HIT-EXIT.
           EXIT.
       HIT-TEST.
           IF GH-X (WS-G) = PLAYER-X AND GH-Y (WS-G) = PLAYER-Y
               MOVE 1 TO F-HIT.
       HIT-TEST-EXIT.
           EXIT.
       LOSE-LIFE.
           MOVE 0 TO F-WON.
           SUBTRACT 1 FROM LIVES.
           IF LIVES = 0
               MOVE 1 TO F-LOST
               MOVE 'LOST   ' TO LAST-RESULT
           ELSE
               MOVE 'DIED   ' TO LAST-RESULT
               MOVE 2 TO PLAYER-X
               MOVE 2 TO PLAYER-Y
               PERFORM RESET-GHOST VARYING WS-G FROM 1 BY 1
                   UNTIL WS-G > GHOST-COUNT
               IF PELLETS-LEFT = 0
                   MOVE 1 TO F-WON.
       LOSE-LIFE-EXIT.
           EXIT.
       SET-STATE.
           IF F-LOST = 1
               MOVE 'LOST   ' TO GAME-STATE
           ELSE IF F-WON = 1
               MOVE 'WON    ' TO GAME-STATE
           ELSE
               MOVE 'RUNNING' TO GAME-STATE.
       SET-STATE-EXIT.
           EXIT.
ZZ
//COB2     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ2,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.COBOL(PACGAME),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.COPY,DISP=SHR
//SRC3     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.COBOL(PACMAP),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACMAP : MAP SERVICE (PORTABLE, NO TERMINAL I/O).
      * OPS : LOAD  COPY THE LEVEL INTO THE STATE
      *       WALL  M-FLAG = 1 IF (M-X,M-Y) IS A WALL OR OUTSIDE
      *       CLR   BLANK THE CELL        EAT  M-FLAG = 1 IF A PELLET
      *       CNT   M-COUNT = PELLETS ON THE MAP
      * LEVEL LITERALS MUST MATCH MAPS/LEVEL1.TXT.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACMAP.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  MAP-DATA.
           05  FILLER            PIC X(20) VALUE '####################'.
           05  FILLER            PIC X(20) VALUE '#........##........#'.
           05  FILLER            PIC X(20) VALUE '#.##.###.##.###.##.#'.
           05  FILLER            PIC X(20) VALUE '#..................#'.
           05  FILLER            PIC X(20) VALUE '#.##.#.######.#.##.#'.
           05  FILLER            PIC X(20) VALUE '#....#...##...#....#'.
           05  FILLER            PIC X(20) VALUE '#.##.###.##.###.##.#'.
           05  FILLER            PIC X(20) VALUE '#..................#'.
           05  FILLER            PIC X(20) VALUE '#..................#'.
           05  FILLER            PIC X(20) VALUE '####################'.
       01  WS-ROW                PIC 99.
       01  WS-COL                PIC 99.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  MAP-REQ COPY PACMREQ.
       PROCEDURE DIVISION USING PAC-STATE MAP-REQ.
       MAIN-PARA.
           MOVE 0 TO M-FLAG.
           IF M-OP = 'LOAD'
               MOVE MAP-DATA TO MAP-AREA
           ELSE IF M-OP = 'WALL'
               PERFORM DO-WALL THRU DO-WALL-EXIT
           ELSE IF M-OP = 'CLR '
               MOVE ' ' TO MAP-CELL (M-Y M-X)
           ELSE IF M-OP = 'EAT '
               PERFORM DO-EAT THRU DO-EAT-EXIT
           ELSE IF M-OP = 'CNT '
               PERFORM DO-COUNT.
           GOBACK.
       DO-WALL.
           IF M-X < 1 OR M-X > 20 OR M-Y < 1 OR M-Y > 10
               MOVE 1 TO M-FLAG
           ELSE IF MAP-CELL (M-Y M-X) = '#'
               MOVE 1 TO M-FLAG.
       DO-WALL-EXIT.
           EXIT.
       DO-EAT.
           IF MAP-CELL (M-Y M-X) = '.'
               MOVE ' ' TO MAP-CELL (M-Y M-X)
               MOVE 1 TO M-FLAG.
       DO-EAT-EXIT.
           EXIT.
       DO-COUNT.
           MOVE 0 TO M-COUNT.
           PERFORM COUNT-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
       COUNT-ROW.
           PERFORM COUNT-CELL THRU COUNT-CELL-EXIT
               VARYING WS-COL FROM 1 BY 1 UNTIL WS-COL > 20.
       COUNT-CELL.
           IF MAP-CELL (WS-ROW WS-COL) = '.'
               ADD 1 TO M-COUNT.
       COUNT-CELL-EXIT.
           EXIT.
ZZ
//COB3     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ3,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.COBOL(PACMAP),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.COPY,DISP=SHR
//SRC4     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.COBOL(PACAI),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACAI : GHOST MOVEMENT FOR ALL ACTIVE GHOSTS (PORTABLE).
      * AI-LEVEL 1 RANDOM, 2 PERSISTENT DIRECTION, 3 CHASE (MANHATTAN).
      * LCG SEED IN THE STATE (FIXED 12345) KEEPS RUNS REPRODUCIBLE.
      * WALL TESTS GO THROUGH PACMAP. NO NESTED SUBSCRIPTS (D13).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACAI.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  MAP-REQ COPY PACMREQ.
       01  WS-WORK               PIC 9(9).
       01  WS-QUOT               PIC 9(9).
       01  WS-REM                PIC 9(5).
       01  WS-D                  PIC 9.
       01  WS-G                  PIC 9.
       01  WS-J                  PIC 9.
       01  WS-K                  PIC 9.
       01  WS-CUR                PIC 9.
       01  WS-REVD               PIC 9.
       01  CAND-N                PIC 9.
       01  CAND-TABLE.
           05  CAND              PIC 9 OCCURS 4 TIMES.
       01  DIR-DATA              PIC X(8) VALUE '10120121'.
       01  DIR-TABLE REDEFINES DIR-DATA.
           05  DIR-ENTRY         OCCURS 4 TIMES.
               10  DIR-DX        PIC 9.
               10  DIR-DY        PIC 9.
       01  REV-DATA              PIC X(4) VALUE '2143'.
       01  REV-TABLE REDEFINES REV-DATA.
           05  REV-D             PIC 9 OCCURS 4 TIMES.
       01  G-NX                  PIC 99.
       01  G-NY                  PIC 99.
       01  DIST-X                PIC S99.
       01  DIST-Y                PIC S99.
       01  DIST-T                PIC S999.
       01  BEST-DIST             PIC S999.
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       PROCEDURE DIVISION USING PAC-STATE.
       MAIN-PARA.
           PERFORM GHOST-MOVE THRU GHOST-MOVE-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           GOBACK.
       GHOST-MOVE.
           MOVE 0 TO CAND-N.
           MOVE GH-DIR (WS-G) TO WS-CUR.
           MOVE REV-D (WS-CUR) TO WS-REVD.
           PERFORM GHOST-PROBE THRU GHOST-PROBE-EXIT
               VARYING WS-D FROM 1 BY 1 UNTIL WS-D > 4.
           IF CAND-N = 0 AND AI-LEVEL > 1
               PERFORM TRY-REVERSE THRU TRY-REVERSE-EXIT.
           IF CAND-N > 0
               PERFORM CHOOSE-DIR THRU CHOOSE-DIR-EXIT
               PERFORM STEP-GHOST.
       GHOST-MOVE-EXIT.
           EXIT.
       GHOST-PROBE.
           COMPUTE G-NX = GH-X (WS-G) + DIR-DX (WS-D) - 1.
           COMPUTE G-NY = GH-Y (WS-G) + DIR-DY (WS-D) - 1.
           MOVE G-NX TO M-X.
           MOVE G-NY TO M-Y.
           MOVE 'WALL' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 0
               IF AI-LEVEL = 1 OR WS-D NOT = WS-REVD
                   ADD 1 TO CAND-N
                   MOVE WS-D TO CAND (CAND-N).
       GHOST-PROBE-EXIT.
           EXIT.
       TRY-REVERSE.
           MOVE WS-REVD TO WS-D.
           COMPUTE G-NX = GH-X (WS-G) + DIR-DX (WS-D) - 1.
           COMPUTE G-NY = GH-Y (WS-G) + DIR-DY (WS-D) - 1.
           MOVE G-NX TO M-X.
           MOVE G-NY TO M-Y.
           MOVE 'WALL' TO M-OP.
           CALL 'PACMAP' USING PAC-STATE MAP-REQ.
           IF M-FLAG = 0
               MOVE 1 TO CAND-N
               MOVE WS-D TO CAND (1).
       TRY-REVERSE-EXIT.
           EXIT.
       CHOOSE-DIR.
           IF AI-LEVEL = 3
               PERFORM PICK-CHASE
           ELSE IF AI-LEVEL = 2 AND CAND-N = 1
               MOVE CAND (1) TO WS-D
           ELSE
               PERFORM PICK-RANDOM.
       CHOOSE-DIR-EXIT.
           EXIT.
       PICK-RANDOM.
           COMPUTE WS-WORK = GHOST-SEED * 75 + 74.
           DIVIDE WS-WORK BY 65537 GIVING WS-QUOT
               REMAINDER GHOST-SEED.
           DIVIDE GHOST-SEED BY CAND-N GIVING WS-QUOT
               REMAINDER WS-REM.
           ADD 1 TO WS-REM.
           MOVE CAND (WS-REM) TO WS-D.
       PICK-CHASE.
           MOVE 999 TO BEST-DIST.
           PERFORM CHASE-EVAL THRU CHASE-EVAL-EXIT
               VARYING WS-J FROM 1 BY 1 UNTIL WS-J > CAND-N.
       CHASE-EVAL.
           MOVE CAND (WS-J) TO WS-K.
           COMPUTE G-NX = GH-X (WS-G) + DIR-DX (WS-K) - 1.
           COMPUTE G-NY = GH-Y (WS-G) + DIR-DY (WS-K) - 1.
           COMPUTE DIST-X = G-NX - PLAYER-X.
           IF DIST-X < 0
               COMPUTE DIST-X = 0 - DIST-X.
           COMPUTE DIST-Y = G-NY - PLAYER-Y.
           IF DIST-Y < 0
               COMPUTE DIST-Y = 0 - DIST-Y.
           COMPUTE DIST-T = DIST-X + DIST-Y.
           IF DIST-T < BEST-DIST
               MOVE DIST-T TO BEST-DIST
               MOVE WS-K TO WS-D.
       CHASE-EVAL-EXIT.
           EXIT.
       STEP-GHOST.
           COMPUTE GH-X (WS-G) = GH-X (WS-G) + DIR-DX (WS-D) - 1.
           COMPUTE GH-Y (WS-G) = GH-Y (WS-G) + DIR-DY (WS-D) - 1.
           MOVE WS-D TO GH-DIR (WS-G).
ZZ
//COB4     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ4,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.COBOL(PACAI),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.COPY,DISP=SHR
//SRC5     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.COBOL(PACINPT),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
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
ZZ
//COB5     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ5,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.COBOL(PACINPT),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.COPY,DISP=SHR
//SRC6     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.COBOL(PACDISP),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACDISP : DISPLAY ADAPTER (PLAIN TEXT, LEVEL G0). READS THE
      * STATE, NEVER CHANGES IT.  OPS : HEAD  STAT  INVL  END  PRMT
      * PRMT shows the input prompt in TSO mode only (no-op in BAT).
      * TSO: EVERY FRAME AFTER THE FIRST STARTS ON A FRESH SCREEN
      * (PACPLAT CLS), SO TSO NEVER PAGES A FRAME WITH '***'.
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
       LINKAGE SECTION.
       01  PAC-STATE COPY PACSTATE.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-STATE PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'HEAD'
               DISPLAY 'PACMAN MVS-6 SMART GHOSTS'
           ELSE IF REQ-OP = 'STAT'
               PERFORM SHOW-STATE THRU SHOW-STATE-EXIT
           ELSE IF REQ-OP = 'INVL'
               DISPLAY 'INVALID COMMAND ' REQ-CHAR
           ELSE IF REQ-OP = 'END '
               PERFORM SHOW-END THRU SHOW-END-EXIT
           ELSE IF REQ-OP = 'PRMT'
               PERFORM SHOW-PROMPT THRU SHOW-PROMPT-EXIT.
           GOBACK.
       NEW-SCREEN.
           MOVE REQ-OP TO WS-SAVE-OP.
           MOVE 'CLS ' TO REQ-OP.
           CALL 'PACPLAT' USING PAC-REQ.
           MOVE WS-SAVE-OP TO REQ-OP.
       SHOW-PROMPT.
           IF REQ-MODE = 'TSO'
               DISPLAY 'CMD (U/D/L/R/Q)?'.
       SHOW-PROMPT-EXIT.
           EXIT.
       SHOW-END.
           IF F-LOST = 1
               DISPLAY 'LOST'
           ELSE IF F-WON = 1
               DISPLAY 'WIN'
           ELSE IF F-QUIT = 1
               DISPLAY 'QUIT'
           ELSE
               DISPLAY 'EOF'.
           DISPLAY 'TURNS ' TICK-COUNT.
           DISPLAY 'SCORE ' SCORE.
           DISPLAY 'LIVES ' LIVES.
       SHOW-END-EXIT.
           EXIT.
       SHOW-STATE.
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
           IF GHOST-COUNT > 1
               PERFORM SHOW-EXTRA THRU SHOW-EXTRA-EXIT.
           PERFORM SHOW-ROW VARYING WS-ROW FROM 1 BY 1
               UNTIL WS-ROW > 10.
       SHOW-STATE-EXIT.
           EXIT.
       SHOW-ROW.
           MOVE MAP-ROW (WS-ROW) TO WS-LINE.
           IF WS-ROW = PLAYER-Y
               MOVE 'P' TO WS-LINE-CELL (PLAYER-X).
           PERFORM OVERLAY-GHOST THRU OVERLAY-GHOST-EXIT
               VARYING WS-G FROM 1 BY 1 UNTIL WS-G > GHOST-COUNT.
           DISPLAY WS-LINE.
       OVERLAY-GHOST.
           IF WS-ROW = GH-Y (WS-G)
               MOVE GH-X (WS-G) TO WS-GX
               MOVE 'G' TO WS-LINE-CELL (WS-GX).
       OVERLAY-GHOST-EXIT.
           EXIT.
       SHOW-EXTRA.
           MOVE GH-X (2) TO XL2-X.
           MOVE GH-Y (2) TO XL2-Y.
           IF GHOST-COUNT = 2
               DISPLAY WS-XL2
           ELSE
               MOVE GH-X (3) TO XL3-X
               MOVE GH-Y (3) TO XL3-Y
               DISPLAY WS-XL2 WS-XL3.
       SHOW-EXTRA-EXIT.
           EXIT.
ZZ
//COB6     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ6,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.COBOL(PACDISP),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.COPY,DISP=SHR
//SRC7     EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSUT2   DD DSN=HERC01.PACMAN.COBOL(PACPLAT),DISP=OLD
//SYSIN    DD DUMMY
//SYSUT1   DD DATA,DLM=ZZ
      * PACPLAT : PLATFORM ADAPTER (MVS 3.8J). OPS : INIT FINI CLS.
      * INIT validates the requested REQ-MODE (BAT cards or TSO
      * interactive); anything else falls back to BAT. FINI sets the
      * return code. CLS (TSO only) makes the next line start a
      * fresh screen via PACTSO, avoiding '***' paging; in batch
      * PACTSO does nothing. GAME/MAP/AI never see any of this.
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
       LINKAGE SECTION.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'INIT'
               PERFORM DO-INIT THRU DO-INIT-EXIT
           ELSE IF REQ-OP = 'FINI'
               MOVE 0 TO RETURN-CODE
           ELSE IF REQ-OP = 'CLS ' AND REQ-MODE = 'TSO'
               CALL 'PACTSO' USING TSO-OP TSO-RC.
           GOBACK.
       DO-INIT.
           IF REQ-MODE NOT = 'TSO'
               MOVE 'BAT' TO REQ-MODE.
       DO-INIT-EXIT.
           EXIT.
ZZ
//COB7     EXEC PGM=IKFCBL00,COND=(0,NE),
//         PARM='LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'
//SYSPRINT DD SYSOUT=A
//SYSPUNCH DD DUMMY
//SYSUT1   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT2   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT3   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSUT4   DD UNIT=SYSDA,SPACE=(460,(700,100))
//SYSLIN   DD DSN=&&OBJ7,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DSN=HERC01.PACMAN.COBOL(PACPLAT),DISP=SHR
//SYSLIB   DD DSN=HERC01.PACMAN.COPY,DISP=SHR
//ASM1     EXEC PGM=IFOX00,COND=(0,NE),PARM='OBJECT,NODECK,NOXREF'
//SYSLIB   DD DSN=SYS1.MACLIB,DISP=SHR
//         DD DSN=SYS1.AMODGEN,DISP=SHR
//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSUT2   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSUT3   DD UNIT=SYSDA,SPACE=(CYL,(3,1))
//SYSPRINT DD SYSOUT=A
//SYSGO    DD DSN=&&OBJA1,DISP=(NEW,PASS),UNIT=SYSDA,
//            SPACE=(80,(500,100)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD DATA,DLM=ZZ
*        PACTSO : TSO LINE-MODE SCREEN SERVICE FOR PACPLAT (MVS-8).
*        CALL 'PACTSO' USING OP RC
*          OP X(4)  'CLS ' = NEXT LINE-MODE OUTPUT STARTS AT LINE 1
*                   OF A FRESH SCREEN (STLINENO LINE=1), SO A FRAME
*                   NEVER OVERFLOWS INTO THE TSO '***' PAGING PROMPT.
*          RC S9(4) COMP  0 = DONE, 4 = NOT A TSO FOREGROUND SESSION
*                   (BATCH: NOTHING IS ISSUED), 8 = UNKNOWN OP.
*        ONLY PACPLAT MAY CALL THIS MODULE.
PACTSO   CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,3,0(1)
         LA    3,0(3)
         LA    4,8
         CLC   0(4,2),=C'CLS '
         BNE   DONE
         LA    4,4
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         STLINENO LINE=1
         LR    4,15
DONE     DS    0H
         STH   4,0(3)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
SAVE     DC    18F'0'
         LTORG
         END
ZZ
//LINK     EXEC PGM=IEWL,COND=(0,NE),PARM='LIST,XREF'
//SYSLIN   DD DSN=&&OBJ1,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ2,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ3,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ4,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ5,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ6,DISP=(OLD,DELETE)
//         DD DSN=&&OBJ7,DISP=(OLD,DELETE)
//         DD DSN=&&OBJA1,DISP=(OLD,DELETE)
//         DD DDNAME=SYSIN
//SYSLMOD  DD DSN=HERC01.PACMAN.LOAD(PACMAIN),DISP=OLD
//SYSLIB   DD DSN=SYS1.COBLIB,DISP=SHR
//SYSUT1   DD UNIT=SYSDA,SPACE=(1024,(50,20))
//SYSPRINT DD SYSOUT=A
//SYSIN    DD *
 ENTRY PACMAIN
/*
//RUN1     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
R
R
U
L
L
L
D
D
R
X
r
R
R
D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN2     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
L
R
L
R
U
L
L
R
L
D
R
U
U
R
D
L
U
D
R
U
R
L
D
R
U
D
R
L
D
L
L
R
R
U
U
D
L
L
L
L
U
R
L
L
D
U
U
L
R
U
D
U
R
R
R
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN3     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
U
R
U
U
D
U
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN4     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI0
D
D
D
D
D
D
D
R
U
R
D
R
U
U
U
U
U
U
U
L
L
R
R
R
R
R
R
D
D
L
L
D
D
R
R
D
D
D
L
U
L
D
L
U
D
R
U
R
D
R
R
U
R
D
R
U
U
U
R
R
U
U
L
L
U
U
R
R
R
R
D
D
D
D
D
D
D
L
U
L
D
L
U
D
R
U
R
D
R
R
U
R
D
U
R
U
U
U
U
U
U
L
L
R
R
D
D
L
L
R
R
D
D
L
L
R
R
D
D
L
L
D
L
U
U
U
U
U
L
R
U
U
L
L
L
L
D
D
L
L
R
R
R
R
D
D
L
L
D
D
D
L
U
L
D
L
U
U
U
L
L
U
U
L
R
R
R
U
U
L
L
L
L
D
D
L
L
R
R
D
D
L
L
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN5     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI0
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
L
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN6     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI0
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN7     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI0
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN8     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI0
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
D
D
D
D
D
R
U
R
D
R
U
U
U
U
U
U
U
L
L
R
R
R
R
R
R
D
D
L
L
D
D
R
R
D
D
D
L
U
L
D
L
U
D
R
U
R
D
R
R
U
R
D
R
U
U
U
R
R
U
U
L
L
U
U
R
R
R
R
D
D
D
D
D
D
D
L
U
L
D
L
U
D
R
U
R
D
R
R
U
R
D
U
R
U
U
U
U
U
U
L
L
R
R
D
D
L
L
R
R
D
D
L
L
R
R
D
D
L
L
D
L
U
U
U
U
U
L
R
U
U
L
L
L
L
D
D
L
L
R
R
R
R
D
D
L
L
D
D
D
L
U
L
D
L
U
U
U
L
L
U
U
L
R
R
R
U
U
L
L
L
L
D
D
L
L
R
R
D
D
L
L
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN9     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
L
R
L
L
U
L
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
U
R
L
U
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN10    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
U
R
D
R
U
U
U
U
U
U
U
L
L
R
R
R
R
R
R
D
D
L
L
D
D
R
R
D
D
D
L
U
L
D
L
U
R
R
R
R
D
R
U
R
U
U
R
R
U
U
L
L
U
U
R
R
R
R
D
D
D
D
D
D
D
L
U
L
D
L
U
D
L
R
R
R
R
R
U
R
D
U
R
U
U
U
U
U
U
L
L
L
D
D
L
R
R
R
R
D
D
L
L
L
U
U
L
L
L
L
L
L
L
L
L
L
L
L
L
L
D
D
R
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN11    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
U
R
R
R
R
R
R
U
U
U
U
U
U
U
U
U
U
U
U
U
U
R
R
R
D
D
D
D
D
D
L
L
R
R
R
R
R
R
U
U
L
L
U
U
L
L
L
L
L
D
D
R
R
R
U
U
U
U
R
R
R
R
D
D
L
R
R
R
R
U
U
R
R
R
R
D
D
D
D
D
D
D
L
L
L
L
L
L
U
R
R
U
U
R
R
U
U
L
R
R
R
R
R
R
U
U
L
L
R
R
D
D
D
D
L
L
L
D
D
R
D
R
U
R
R
R
R
R
R
R
R
R
R
R
R
R
R
U
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN12    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
U
R
R
R
R
R
R
D
D
D
D
D
D
D
U
R
R
R
R
R
D
U
R
R
R
R
R
R
R
R
R
D
U
R
D
R
U
U
U
U
U
U
U
U
U
U
U
R
R
R
D
D
D
D
D
U
L
L
L
U
U
R
R
R
R
R
D
D
R
R
D
D
D
R
R
R
R
R
R
U
R
U
U
U
U
U
U
L
L
L
L
D
D
L
L
L
U
U
L
L
L
L
D
D
R
R
R
R
R
R
R
R
R
D
D
L
L
D
U
R
R
U
U
R
R
R
R
R
U
U
L
L
R
R
D
D
D
D
D
U
L
L
U
U
U
R
R
D
D
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN13    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI2
L
L
U
R
D
U
D
U
L
R
D
R
U
D
U
D
R
L
D
R
D
U
D
R
D
D
U
U
D
D
D
D
L
L
D
D
D
D
R
L
U
L
R
D
D
L
U
L
L
U
L
U
L
L
L
R
L
D
R
R
D
U
L
U
L
R
U
R
L
R
U
R
U
D
D
U
D
R
L
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN14    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI2 3
L
L
U
R
D
U
D
U
L
R
D
R
U
D
U
D
R
L
D
R
D
U
D
R
D
D
U
U
D
D
D
D
L
L
D
D
D
D
R
L
U
L
R
D
D
L
U
L
L
U
L
U
L
L
L
R
L
D
R
R
D
U
L
U
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN15    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI1 2
L
L
U
R
D
U
D
U
L
R
D
R
U
D
U
D
R
L
D
R
D
U
D
R
D
D
U
U
D
D
D
D
L
L
D
D
D
D
R
L
U
L
R
D
D
L
U
L
L
U
L
U
L
L
L
R
L
D
R
R
D
U
L
U
L
R
U
R
L
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN16    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI3
D
U
D
U
D
U
R
L
L
D
R
L
L
U
R
D
D
D
D
U
R
L
U
R
U
R
R
D
U
U
L
U
U
D
R
U
R
U
D
U
R
R
U
U
L
R
R
L
U
U
D
D
R
D
D
U
L
U
U
D
U
D
U
R
L
R
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN17    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI3
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN18    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI3 2
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//RUN19    EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
AI3 3
R
D
R
R
R
U
R
R
U
R
L
D
R
R
R
D
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO1     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO'
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
R
R
U
L
L
L
D
D
R
X
r
R
R
D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO2     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO AI0'
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO3     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO AI2'
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
L
L
U
R
D
U
D
U
L
R
D
R
U
D
U
D
R
L
D
R
D
U
D
R
D
D
U
U
D
D
D
D
L
L
D
D
D
D
R
L
U
L
R
D
D
L
U
L
L
U
L
U
L
L
L
R
L
D
R
R
D
U
L
U
L
R
U
R
L
R
U
R
U
D
D
U
D
R
L
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO4     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO AI3 3'
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
R
D
R
R
R
U
R
R
U
R
L
D
R
R
R
D
R
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO5     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO AI3 2'
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
U
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//TSO6     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO'
//STEPLIB  DD DSN=HERC01.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
R

D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//SYSUDUMP DD SYSOUT=A
//
