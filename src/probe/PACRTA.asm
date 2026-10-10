*        PACRTA : MVS-RT PROBE E14 - EXPERIMENTAL CLOCK / POLL / PUT
*        SERVICE FOR PACRTP ONLY (ISOLATED; PACFSIO/PACTSO UNTOUCHED).
*        CALL 'PACRTA' USING OP ARG BUF RC
*          OP X(4): ZERO  STCK -> T0 (START OF THE PROBE CLOCK)
*                   TIME  ARG := MICROSECONDS SINCE T0 (STCK)
*                   WAIT  ARG = ABSOLUTE DEADLINE (US SINCE T0):
*                         STIMER WAIT,MICVL FOR THE REMAINDER ONLY;
*                         RC 4 = DEADLINE ALREADY PASSED (NO WAIT)
*                   POLL  ONE TGET ASIS,NOWAIT INTO BUF (2048):
*                         RC = R15 (0 INPUT, 4 NONE), ARG = LENGTH
*                   PUTN  TPUT NOEDIT OF BUF, ARG BYTES (1ST BYTE IS
*                         THE 3270 COMMAND, E.G. X'F1' WRITE)
*          ARG S9(9) COMP  BUF X(2048)  RC S9(4) COMP
*          POLL/PUTN OUTSIDE A TSO USER ADDRESS SPACE: RC 8, NOTHING
*          ISSUED. UNKNOWN OP: RC 12.
PACRTA   CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,5,0(1)
         LA    2,0(2)              OP
         LA    3,0(3)              ARG
         LA    4,0(4)              BUF
         LA    5,0(5)              RC
         SR    6,6
         CLC   0(4,2),=C'TIME'
         BE    DOTIME
         CLC   0(4,2),=C'WAIT'
         BE    DOWAIT
         CLC   0(4,2),=C'ZERO'
         BE    DOZERO
         LA    6,8
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         CLC   0(4,2),=C'POLL'
         BE    DOPOLL
         CLC   0(4,2),=C'PUTN'
         BE    DOPUTN
         LA    6,12
         B     DONE
DOZERO   DS    0H
         STCK  T0
         B     DONE
DOTIME   DS    0H
         BAL   14,NOWUS
         ST    1,0(3)
         B     DONE
DOWAIT   DS    0H
         BAL   14,NOWUS
         L     0,0(3)              DEADLINE (US SINCE T0)
         SR    0,1                 REMAINDER = DEADLINE - NOW
         BNP   LATE                ZERO OR NEGATIVE: NO WAIT
         LR    1,0
         SR    0,0
         SLDL  0,12                US -> TOD UNITS (BIT 51 = 1 US)
         STM   0,1,MICDW
         STIMER WAIT,MICVL=MICDW
         B     DONE
LATE     DS    0H
         LA    6,4
         B     DONE
DOPOLL   DS    0H
         LR    1,4
         L     0,=F'2048'
         TGET  (1),(0),ASIS,NOWAIT
         LR    6,15
         LTR   15,15
         BNZ   POLLNO              RC 4 NONE, ELSE ERROR (R1 UNUSED)
         ST    1,0(3)
         B     DONE
POLLNO   DS    0H
         SR    1,1
         ST    1,0(3)
         B     DONE
DOPUTN   DS    0H
         LR    1,4
         L     0,0(3)              LENGTH FROM THE CALLER (NEVER LA)
         TPUT  (1),(0),NOEDIT
         LR    6,15
DONE     DS    0H
         STH   6,0(5)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
*        NOWUS: R1 := MICROSECONDS SINCE T0 (64-BIT TOD DIFFERENCE,
*        LOGICAL SUBTRACT WITH BORROW, THEN SHIFT RIGHT 12). USES R0.
NOWUS    DS    0H
         STCK  NOW
         LM    0,1,NOW
         SL    1,T0+4
         BC    3,NOBORROW          CC 2/3: NO BORROW
         BCTR  0,0                 BORROW FROM THE HIGH WORD
NOBORROW DS    0H
         SL    0,T0
         SRDL  0,12
         BR    14
SAVE     DC    18F'0'
         DS    0D
T0       DC    D'0'
NOW      DC    D'0'
MICDW    DC    D'0'
         LTORG
         END
