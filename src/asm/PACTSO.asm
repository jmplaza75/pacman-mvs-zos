*        PACTSO : TSO LINE-MODE SCREEN SERVICE FOR PACPLAT (MVS-8).
*        CALL 'PACTSO' USING OP RC [MS]
*          OP X(4)  'CLS ' = NEXT LINE-MODE OUTPUT STARTS AT LINE 1
*                   OF A FRESH SCREEN (STLINENO LINE=1), SO A FRAME
*                   NEVER OVERFLOWS INTO THE TSO '***' PAGING PROMPT.
*                   'WAIT' = PAUSE 3 SECONDS (STIMER), NO TERMINAL
*                   I/O AT ALL (MVS-GS: THE FINAL SCALED SCREEN STAYS
*                   VISIBLE BEFORE THE LINE-MODE END LINES).
*                   MVS-RT (D33, PROBE E14): 'TIME' = MS := MILLI-
*                   SECONDS SINCE THE FIRST TIME CALL (STCK); 'DLWT' =
*                   WAIT UNTIL THE ABSOLUTE DEADLINE MS (STIMER WAIT,
*                   MICVL FOR THE REMAINDER ONLY), RC 4 IF ALREADY
*                   PASSED. MS S9(9) COMP. BOTH WORK IN ANY ADDRESS
*                   SPACE (BATCH TOO).
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
         CLC   0(4,2),=C'TIME'
         BE    DOTIME
         CLC   0(4,2),=C'DLWT'
         BE    DODLWT
         CLC   0(4,2),=C'CLS '
         BE    KNOWN
         CLC   0(4,2),=C'WAIT'
         BNE   DONE
KNOWN    DS    0H
         LA    4,4
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         CLC   0(4,2),=C'WAIT'
         BE    PAUSE
         STLINENO LINE=1
         LR    4,15
         B     DONE
PAUSE    DS    0H
         STIMER WAIT,BINTVL=WAITT
         SR    4,4
DOTIME   DS    0H
         L     5,8(1)              THIRD PARAMETER: MS
         LA    5,0(5)
         BAL   14,NOWMS
         ST    1,0(5)
         SR    4,4
         B     DONE
DODLWT   DS    0H
         L     5,8(1)
         LA    5,0(5)
         BAL   14,NOWMS
         L     0,0(5)              DEADLINE (MS)
         SR    0,1                 REMAINDER = DEADLINE - NOW
         BNP   LATE
         LR    1,0                 THE REMAINDER INTO R1 (M USES R1)
         M     0,=F'1000'          MS -> US IN R0/R1
         SLDL  0,12                US -> TOD UNITS (BIT 51 = 1 US)
         STM   0,1,MICDW
         STIMER WAIT,MICVL=MICDW
         SR    4,4
         B     DONE
LATE     DS    0H
         LA    4,4
         B     DONE
DONE     DS    0H
         STH   4,0(3)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
*        NOWMS: R1 := MILLISECONDS SINCE T0 (T0 = THE FIRST CALL).
*        64-BIT TOD DIFFERENCE, >> 12 = US, / 1000. USES R0, R1, R15;
*        FETCH THE PARAMETERS BEFORE THE CALL (R1 IS OVERWRITTEN).
NOWMS    DS    0H
         STCK  NOW
         CLI   T0SET,1
         BE    HAVET0
         MVC   T0,NOW
         MVI   T0SET,1
HAVET0   DS    0H
         LM    0,1,NOW
         SL    1,T0+4
         BC    3,NOBORROW          CC 2/3: NO BORROW
         BCTR  0,0
NOBORROW DS    0H
         SL    0,T0
         SRDL  0,12                US IN R0/R1
         D     0,=F'1000'          MS IN R1 (REMAINDER IN R0)
         BR    14
SAVE     DC    18F'0'
         DS    0D
T0       DC    D'0'
NOW      DC    D'0'
MICDW    DC    D'0'
T0SET    DC    X'00'
WAITT    DC    F'300'              3 SECONDS (UNITS OF 0.01 S)
         LTORG
         END
