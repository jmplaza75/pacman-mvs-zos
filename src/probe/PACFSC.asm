*        PACFSC : MVS-GS GEOMETRY PROBE E12 - MINIMAL TSO FULL-SCREEN
*        SERVICE FOR PACGEP (ISOLATED FROM PACMAN; PACFSIO UNTOUCHED).
*        CALL 'PACFSC' USING OP BUF LEN RC
*          OP X(4): FSON  FULL-SCREEN ON (TSO ONLY, ELSE RC 4)
*                   FSOF  FULL-SCREEN OFF, STLINENO LINE=1
*                   NOED  TPUT NOEDIT OF BUF (LEN BYTES, 1ST BYTE IS
*                         3270 COMMAND: F1 W, F5 EW, 7E EWA, F3 WSF)
*                   FULL  TPUT FULLSCR OF BUF (LEN BYTES, WCC FIRST)
*                   GETK  TGET ASIS, WAIT UP TO 5 MINUTES FOR INPUT
*                   GETQ  TGET ASIS, WAIT UP TO 5 SECONDS (QUERY REPLY)
*                   WAIT  PAUSE 1 SECOND
*          BUF X(4096)  LEN S9(4) COMP (IN: SEND LENGTH, OUT: INPUT
*          LENGTH)  RC S9(4) COMP (TPUT/TGET RC, 4 = NOT TSO, 8 = NO
*          INPUT IN TIME, 12 = UNKNOWN OP)
PACFSC   CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,5,0(1)
         LA    2,0(2)              OP
         LA    3,0(3)              BUF
         LA    4,0(4)              LEN
         LA    5,0(5)              RC
         LA    6,4
         CLC   0(4,2),=C'FSON'
         BE    DOFSON
         CLI   ACTIVE,1            EVERYTHING ELSE NEEDS FULL SCREEN
         BNE   DONE
         CLC   0(4,2),=C'FSOF'
         BE    DOFSOF
         CLC   0(4,2),=C'NOED'
         BE    DONOED
         CLC   0(4,2),=C'FULL'
         BE    DOFULL
         CLC   0(4,2),=C'GETK'
         BE    DOGETK
         CLC   0(4,2),=C'GETQ'
         BE    DOGETQ
         CLC   0(4,2),=C'WAIT'
         BE    DOWAIT
         LA    6,12
         B     DONE
DOFSON   DS    0H
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         TCLEARQ OUTPUT
         TCLEARQ INPUT
         STFSMODE ON,INITIAL=YES
         STTMPMD ON
         MVI   ACTIVE,1
         SR    6,6
         B     DONE
DOFSOF   DS    0H
         STTMPMD OFF
         STFSMODE OFF
         STLINENO LINE=1
         MVI   ACTIVE,0
         SR    6,6
         B     DONE
DONOED   DS    0H
         LR    1,3
         LH    0,0(4)              LENGTH FROM THE CALLER (NEVER LA)
         TPUT  (1),(0),NOEDIT
         LR    6,15
         B     DONE
DOFULL   DS    0H
         LR    1,3
         LH    0,0(4)
         TPUT  (1),(0),FULLSCR
         LR    6,15
         B     DONE
DOGETK   DS    0H
         L     7,=F'600'           600 X 0.5 S = 5 MINUTES
         B     GETLOOP
DOGETQ   DS    0H
         L     7,=F'10'            10 X 0.5 S = 5 SECONDS
GETLOOP  DS    0H
         SR    8,8
         STH   8,0(4)
GETONE   DS    0H
         LR    1,3
         L     0,=F'4096'
         TGET  (1),(0),ASIS
         LR    6,15
         LTR   1,1
         BNZ   GOT
         STIMER WAIT,BINTVL=HALFSEC
         BCT   7,GETONE
         LA    6,8
         B     DONE
GOT      DS    0H
         STH   1,0(4)
         B     DONE
DOWAIT   DS    0H
         STIMER WAIT,BINTVL=ONESEC
         SR    6,6
DONE     DS    0H
         STH   6,0(5)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
SAVE     DC    18F'0'
HALFSEC  DC    F'50'
ONESEC   DC    F'100'
ACTIVE   DC    X'00'
         LTORG
         END
