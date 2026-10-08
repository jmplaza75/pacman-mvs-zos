*        PACFS2 : MVS-G1 PROBE 2 (E2), ONE HYPOTHESIS: A PLAIN 3270
*        SCREEN (NO SA/SF/SFE ORDERS, NO WSF) SENT WITH TPUT FULLSCR IS
*        DISPLAYED AND STAYS UNTIL ENTER WHEN THE TSO FULL-SCREEN
*        PROTOCOL IS FOLLOWED: NO PENDING LINE OUTPUT (TCLEARQ), TSO IN
*        FULL-SCREEN MODE (STFSMODE ON + STTMPMD ON) AND THE SCREEN IS
*        SENT AGAIN WHEN TGET RETURNS PA2 X'6E' (RESHOW) OR CLEAR
*        X'6D'.
*        E3: SAME PROTOCOL, SCREEN 'C' ADDS ONE EXTENDED CAPABILITY:
*        A SINGLE SET-ATTRIBUTE ORDER FOR FOREGROUND COLOUR RED
*        (X'2842F2') ON ONE LINE, RESET BY X'280000'.
*        CALL 'PACFS2' USING BUF LEN RC CNT LOG SCR
*          SCR X(1)    'P' PLAIN (E2), 'C' ONE COLOUR (E3),
*                      'K' SEVEN-COLOUR PALETTE (E4), 'Q' PLAIN
*                      SCREEN + READ PARTITION QUERY SENT WITH
*                      TPUT NOEDIT, EXPLICIT WSF COMMAND X'F3' (E5)
*          BUF X(1024) LAST INBOUND DATA   LEN S9(4) COMP ITS LENGTH
*          RC  S9(4) COMP LAST TPUT/TGET RC (4 = NOT A TSO SESSION)
*          CNT S9(4) COMP NUMBER OF SCREENS SENT (1 + RESHOWS)
*          LOG X(8)    FIRST BYTE (AID) OF EACH INBOUND, IN ORDER
PACFS2   CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,5,0(1)
         L     8,16(1)             A(LOG)
         LA    8,0(8)
         L     11,20(1)            A(SCR)
         LA    11,0(11)
         LA    14,SCREEN
         LA    15,SCREENL
         CLI   0(11),C'Q'
         BNE   NOTQ
         LA    14,SCREENQ
         LA    15,SCREENQL
         B     SETSCR
NOTQ     DS    0H
         CLI   0(11),C'K'
         BNE   NOTK
         LA    14,SCREENK
         LA    15,SCREENKL
         B     SETSCR
NOTK     DS    0H
         CLI   0(11),C'C'
         BNE   SETSCR
         LA    14,SCREENC
         LA    15,SCREENCL
SETSCR   DS    0H
         ST    14,SCRADR
         ST    15,SCRLEN
         MVC   0(8,8),=8X'00'
         SR    6,6
         STH   6,0(3)
         STH   6,0(5)
         LA    6,4
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         TCLEARQ OUTPUT
         TCLEARQ INPUT
         STFSMODE ON,INITIAL=YES
         STTMPMD ON
         SR    7,7                 SCREENS SENT
         SR    9,9                 INBOUND COUNT (LOG INDEX)
SEND     DS    0H
         LA    7,1(7)
         STH   7,0(5)
         L     1,SCRADR
         L     0,SCRLEN
         TPUT  (1),(0),FULLSCR
         LR    6,15
         LTR   15,15
         BNZ   BACK
         CLI   0(11),C'Q'          E5: QUERY AFTER 1ST SCREEN
         BNE   NOQRY
         C     7,=F'1'
         BNE   NOQRY
         LA    1,QUERY
         LA    0,QUERYL
         TPUT  (1),(0),NOEDIT
         LR    6,15
         LTR   15,15
         BNZ   BACK
NOQRY    DS    0H
         SR    10,10               EMPTY-READ COUNTER
READ     DS    0H
         LR    1,2
         LA    0,1024
         TGET  (1),(0),ASIS
         LR    6,15
         STH   1,0(3)
         LTR   1,1
         BNZ   GOTDATA
         LA    10,1(10)
         C     10,=F'60'
         BNL   BACK
         STIMER WAIT,BINTVL=HALFSEC
         B     READ
GOTDATA  DS    0H
         C     9,=F'8'
         BNL   NOLOG
         LA    15,0(9,8)
         MVC   0(1,15),0(2)
         LA    9,1(9)
NOLOG    DS    0H
         CLI   0(2),X'6E'          PA2: RESHOW REQUEST
         BE    RESHOW
         CLI   0(2),X'6D'          CLEAR
         BE    RESHOW
         B     BACK
RESHOW   DS    0H
         C     7,=F'10'
         BL    SEND
BACK     DS    0H
         STTMPMD OFF
         STFSMODE OFF
         STLINENO LINE=1
DONE     DS    0H
         STH   6,0(4)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
SAVE     DC    18F'0'
SCRADR   DC    A(0)
SCRLEN   DC    F'0'
HALFSEC  DC    F'50'               0.50 SECONDS IN 1/100 S
*        PLAIN SCREEN: WCC C3, SBA ROW 5 COL 1, TEXT, SBA ROW 7, TEXT,
*        INSERT CURSOR. NO SA/SF/SFE ORDERS.
SCREEN   DC    X'C3'
         DC    X'11C540'
         DC    C'G1 PROBE E2: PLAIN FULL-SCREEN TEST'
         DC    X'11C760'
         DC    C'IF YOU CAN READ THIS, PRESS ENTER'
         DC    X'13'
SCREENL  EQU   *-SCREEN
*        E3 SCREEN: AS ABOVE PLUS ONE SA COLOUR ORDER ON ROW 7.
SCREENC  DC    X'C3'
         DC    X'11C540'
         DC    C'G1 PROBE E3: ONE COLOUR (SA RED)'
         DC    X'11C760'
         DC    X'2842F2'
         DC    C'THIS LINE SHOULD BE RED'
         DC    X'280000'
         DC    X'114A40'
         DC    C'THIS LINE SHOULD HAVE THE DEFAULT COLOUR'
         DC    X'114C60'
         DC    C'PA2 OR CLEAR = REDRAW, ENTER = END'
         DC    X'13'
SCREENCL EQU   *-SCREENC
*        E4 SCREEN: THE FULL 7-COLOUR PALETTE, ONE SA ORDER PER ROW.
SCREENK  DC    X'C3'
         DC    X'11C260'
         DC    C'G1 PROBE E4: SEVEN COLOURS (SA X''42'' F1-F7)'
         DC    X'11C5C22842F1'
         DC    C'F1 BLUE'
         DC    X'280000'
         DC    X'11C6D22842F2'
         DC    C'F2 RED'
         DC    X'280000'
         DC    X'11C7E22842F3'
         DC    C'F3 PINK'
         DC    X'280000'
         DC    X'11C8F22842F4'
         DC    C'F4 GREEN'
         DC    X'280000'
         DC    X'114AC22842F5'
         DC    C'F5 TURQUOISE'
         DC    X'280000'
         DC    X'114BD22842F6'
         DC    C'F6 YELLOW'
         DC    X'280000'
         DC    X'114CE22842F7'
         DC    C'F7 WHITE'
         DC    X'280000'
         DC    X'114FC2'
         DC    C'DEFAULT (NO SA ORDER)'
         DC    X'11D160'
         DC    C'CLEAR = REDRAW, ENTER = END'
         DC    X'13'
SCREENKL EQU   *-SCREENK
*        E5 SCREEN (PLAIN) AND THE READ PARTITION QUERY: WSF COMMAND
*        X'F3', LENGTH 5, X'01' READ PARTITION, PID X'FF', X'02' QUERY.
SCREENQ  DC    X'C3'
         DC    X'11C540'
         DC    C'G1 PROBE E5: QUERY SENT. IF THIS SCREEN STAYS,'
         DC    X'11C760'
         DC    C'THE TERMINAL DID NOT ANSWER: PRESS ENTER'
         DC    X'13'
SCREENQL EQU   *-SCREENQ
QUERY    DC    X'F3000501FF02'
QUERYL   EQU   *-QUERY
         LTORG
         END
