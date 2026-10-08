*        INVALID PROBE - KEPT ONLY AS EVIDENCE: SENDTICK BELOW PASSES
*        LENGTH 1 TO TPUT (LA 0,1(0): R0 AS BASE IS ZERO), SO NO TICK
*        EVER CARRIED ITS DATA. ALL E7 RESULTS ARE VOID.
*        PACFS7 : MVS-G3 PROBE E7. WHY DO THE IDLE TICKS (PARTIAL
*        WRITES
*        X'F1' + TPUT NOEDIT) NOT SHOW BEFORE THE FIRST AID IN THE
*        GAME?
*        SAME STARTUP AS THE GAME (TCLEARQ, STFSMODE, STTMPMD, READ
*        PARTITION QUERY, FULL SCREEN WITH THE CLEAR PREFIX, TPUT
*        FULLSCR)
*        AND THE SAME STREAMS (GENERATED FROM THE MODEL BY
*        TOOLS/GEN_PROBE_E7.PY): INITIAL SCREEN + TWO ALTERNATING
*        TICKS.
*        LOOP = 30 TICKS 0.5 S APART (15 S), THEN WAIT FOR AN AID.
*        VARIANT (PARM), EACH ONE FACTOR AWAY FROM A (A = GAME-LIKE):
*          A  NO TGET IN THE LOOP, TICK WCC C2, FIRST TICK AT ONCE
*          B  A + TGET NOWAIT BETWEEN TICKS
*          C  B + TICK WCC C3
*          D  A + STFSMODE ON WITHOUT INITIAL=YES
*          T  A + 2 S WAIT AFTER THE FULL SCREEN (AS PROBE E6)
*          K  A + TICK WCC C3 (AS PROBE E6)
*          Q  A WITHOUT THE READ PARTITION QUERY (AS PROBE E6)
*          P  A WITHOUT THE CLEAR PREFIX IN THE FULL SCREEN (AS E6)
*          F  A WITH THE INITIAL SCREEN WITHOUT 3270 FIELDS (NO SF)
*          I  A WITH TICKS IN THE GAME'S LOGICAL PARTIAL FORMAT (WCC
*             C3 + CELLS + INPUT FIELD WITH IC)
*        PA2 (X'6E') DURING OR AFTER THE LOOP = SEND THE FULL SCREEN
*        AGAIN AND LOOP AGAIN (MAX 3 ROUNDS); ANY OTHER AID ENDS.
*        CALL 'PACFS7' USING VAR RC1 RC2 NTICK NPA2 NSCR AID
*          VAR X(1)  RC1 S9(4) COMP RC OF THE FIRST FULLSCR (4 = NOT
*          TSO)
*          RC2 LAST TICK TPUT RC   NTICK TICKS SENT   NPA2 PA2 SEEN
*          NSCR FULL SCREENS SENT  AID X(1) AID THAT ENDED THE PROBE
PACFS7   CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12,10             TWO BASES: CODE + BUFFERS > 4 KB
         LA    10,2048(12)
         LA    10,2048(10)
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,8,0(1)
         STM   2,8,PTAB
         SR    15,15
         STH   15,RC1
         STH   15,RC2
         STH   15,NT
         STH   15,NP
         STH   15,NS
         STH   15,ROUNDS
         MVI   AIDB,X'00'
         LA    15,4
         STH   15,RC1
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         L     15,PTAB
         MVC   VARB(1),0(15)
         TCLEARQ OUTPUT
         TCLEARQ INPUT
         CLI   VARB,C'D'
         BE    NOINIT
         STFSMODE ON,INITIAL=YES
         B     FSDONE
NOINIT   DS    0H
         STFSMODE ON
FSDONE   DS    0H
         STTMPMD ON
         CLI   VARB,C'Q'
         BE    QRYGOT
         LA    1,QUERY
         LA    0,QUERYL
         TPUT  (1),(0),NOEDIT
         SR    9,9
QRYREAD  DS    0H
         LA    1,INBUF
         LA    0,256
         TGET  (1),(0),ASIS
         LTR   1,1
         BNZ   QRYGOT
         LA    9,1(9)
         C     9,=F'120'
         BNL   BACK
         STIMER WAIT,BINTVL=HALFSEC
         B     QRYREAD
QRYGOT   DS    0H
ROUND    DS    0H
         LH    2,ROUNDS
         LA    2,1(2)
         STH   2,ROUNDS
         C     2,=F'4'
         BNL   BACK
         BAL   11,SENDFULL
         LH    15,RCTMP
         LTR   15,15
         BNZ   BACK
         MVI   PAR,X'00'
         CLI   VARB,C'T'
         BNE   NOWAIT2
         STIMER WAIT,BINTVL=TWOSEC
NOWAIT2  DS    0H
         SR    9,9
         ST    9,CNT
LOOP     DS    0H
         L     9,CNT
         C     9,=F'30'
         BNL   WAITAID
         BAL   11,SENDTICK
         LH    15,RCTMP
         LTR   15,15
         BNZ   BACK
         CLI   VARB,C'B'
         BE    DOGET
         CLI   VARB,C'C'
         BNE   NOGET
DOGET    DS    0H
         LA    1,INBUF
         LA    0,256
         TGET  (1),(0),ASIS,NOWAIT
         LTR   15,15
         BZ    GOTIN
NOGET    DS    0H
         STIMER WAIT,BINTVL=HALFSEC
         L     9,CNT
         LA    9,1(9)
         ST    9,CNT
         B     LOOP
WAITAID  DS    0H
         LA    1,INBUF
         LA    0,256
         TGET  (1),(0),ASIS
GOTIN    DS    0H
         MVC   AIDB(1),INBUF
         CLI   INBUF,X'6E'
         BNE   BACK
         LH    2,NP
         LA    2,1(2)
         STH   2,NP
         B     ROUND
BACK     DS    0H
         STTMPMD OFF
         STFSMODE OFF
         STLINENO LINE=1
DONE     DS    0H
         L     15,PTAB+4
         LH    14,RC1
         STH   14,0(15)
         L     15,PTAB+8
         LH    14,RC2
         STH   14,0(15)
         L     15,PTAB+12
         LH    14,NT
         STH   14,0(15)
         L     15,PTAB+16
         LH    14,NP
         STH   14,0(15)
         L     15,PTAB+20
         LH    14,NS
         STH   14,0(15)
         L     15,PTAB+24
         MVC   0(1,15),AIDB
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
*        FULL SCREEN, AS PACFSIO SEND: WCC, CLEAR PREFIX, REST.
SENDFULL DS    0H
         LA    6,FULLS
         LA    5,FULLSL
         CLI   VARB,C'F'
         BNE   GOTFULL
         LA    6,FULLF
         LA    5,FULLFL
GOTFULL  DS    0H
         CLI   VARB,C'P'
         BNE   WITHPFX
         LR    1,6
         LR    0,5
         B     FULLTPUT
WITHPFX  DS    0H
         ST    5,TLEN
         MVC   SENDBUF(1),0(6)
         MVC   SENDBUF+1(7),CLRPFX
         LA    4,SENDBUF+8
         BCTR  5,0
         LA    6,1(6)
         LR    7,5
         MVCL  4,6
         LA    1,SENDBUF
         L     0,TLEN
         A     0,=F'7'
FULLTPUT DS    0H
         TPUT  (1),(0),FULLSCR
         STH   15,RCTMP
         LH    2,NS
         LTR   2,2
         BNZ   NOTFIRST
         STH   15,RC1
NOTFIRST DS    0H
         LA    2,1(2)
         STH   2,NS
         BR    11
*        TICK, AS PACFSIO SENP: X'F1' + STREAM, TPUT NOEDIT.
SENDTICK DS    0H
         CLI   PAR,X'00'
         BNE   USET2
         LA    6,TICK1
         LA    5,TICK1L
         CLI   VARB,C'I'
         BNE   TCOPY
         LA    6,TICK1I
         LA    5,TICK1IL
         B     TCOPY
USET2    DS    0H
         LA    6,TICK2
         LA    5,TICK2L
         CLI   VARB,C'I'
         BNE   TCOPY
         LA    6,TICK2I
         LA    5,TICK2IL
TCOPY    DS    0H
         ST    5,TLEN
         MVI   SENDBUF,X'F1'
         LA    4,SENDBUF+1
         LR    7,5
         MVCL  4,6
         CLI   VARB,C'C'
         BE    PATCH
         CLI   VARB,C'K'
         BNE   NOPATCH
PATCH    DS    0H
         MVI   SENDBUF+1,X'C3'
NOPATCH  DS    0H
         LA    1,SENDBUF
         L     0,TLEN
         LA    0,1(0)
         TPUT  (1),(0),NOEDIT
         STH   15,RCTMP
         STH   15,RC2
         LH    2,NT
         LA    2,1(2)
         STH   2,NT
         XI    PAR,X'01'
         BR    11
SAVE     DC    18F'0'
PTAB     DS    7F
CNT      DC    F'0'
TLEN     DC    F'0'
RC1      DC    H'0'
RC2      DC    H'0'
RCTMP    DC    H'0'
NT       DC    H'0'
NP       DC    H'0'
NS       DC    H'0'
ROUNDS   DC    H'0'
AIDB     DC    X'00'
VARB     DC    C'A'
PAR      DC    X'00'
HALFSEC  DC    F'50'
TWOSEC   DC    F'200'
INBUF    DS    CL256
SENDBUF  DS    CL2060
CLRPFX   DC    X'114040',X'3C404000'
QUERY    DC    X'F3000501FF02'
QUERYL   EQU   *-QUERY
@@DATA@@
         LTORG
         END
