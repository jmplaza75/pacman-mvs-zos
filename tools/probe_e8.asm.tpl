*        PACFS8 : MVS-G3 PROBE E8, PROTOCOL BISECT FROM THE WORKING
*        PROBE E6. RUNG 0 = E6 (SAME SCREEN, SAME PARTIAL FRAMES, SAME
*        CALLS: TCLEARQ, STFSMODE ON,INITIAL=YES, STTMPMD ON, TPUT
*        FULLSCR, 2 S WAIT, 8 PARTIALS X'F1' + TPUT NOEDIT 0.5 S APART,
*        THEN WAIT FOR ENTER). EACH RUNG ADDS ONE FACTOR TO THE ONE
*        BEFORE IT (CUMULATIVE):
*          1 + READ PARTITION QUERY      2 + CLEAR PREFIX IN FULLSCR
*          3 + 3270 FIELDS (SF, INPUT FIELD WITH IC) IN THE SCREEN
*          4 - THE 2 S WAIT              5 PARTIAL WCC C3 -> C2
*          6 PARTIALS IN THE EXACT G3 TICK FORMAT
*          7 + TGET NOWAIT BETWEEN THE PARTIALS
*          8 THE GAME'S INITIAL SCREEN AND TICK STREAMS
*        TRACE IN MEMORY (NOTHING IS WRITTEN IN FULL-SCREEN): FOR EVERY
*        TPUT THE SERVICE, R1 (BUFFER) AND R0 (LENGTH) EXACTLY AS
*        HANDED TO THE MACRO, THE RC AND THE FIRST 32 BYTES.
*        CALL 'PACFS8' USING RUNG RC1 NPART AID TRCNT NEMPTY TRTAB
PACFS8   CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12,10
         LA    10,2048(12)
         LA    10,2048(10)
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,8,0(1)
         STM   2,8,PTAB
         SR    15,15
         ST    15,TRCNT
         ST    15,NEMPTY
         STH   15,NPART
         MVI   AIDB,X'00'
         LA    15,4
         STH   15,RC1
         L     15,PTAB
         MVC   RUNG(1),0(15)
         NI    RUNG,X'0F'          EBCDIC DIGIT -> 0-9
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         TCLEARQ OUTPUT
         TCLEARQ INPUT
         STFSMODE ON,INITIAL=YES
         STTMPMD ON
         CLI   RUNG,1
         BL    NOQRY
         MVC   TRSVC,=C'QRY '
         LA    1,QUERY
         LA    0,QUERYL
         BAL   11,TRCPUT
         TPUT  (1),(0),NOEDIT
         BAL   11,TRCRC
         SR    9,9
QRYREAD  DS    0H
         LA    1,INBUF
         LA    0,256
         TGET  (1),(0),ASIS
         LTR   1,1
         BNZ   NOQRY
         LA    9,1(9)
         C     9,=F'120'
         BNL   BACK
         STIMER WAIT,BINTVL=HALFSEC
         B     QRYREAD
NOQRY    DS    0H
         LA    6,SCR0
         LA    5,SCR0L
         CLI   RUNG,3
         BL    GOTSCR
         LA    6,SCR3
         LA    5,SCR3L
         CLI   RUNG,8
         BL    GOTSCR
         LA    6,SCRG
         LA    5,SCRGL
GOTSCR   DS    0H
         CLI   RUNG,2
         BNL   PREFIX
         LR    1,6
         LR    0,5
         B     FULLGO
PREFIX   DS    0H
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
FULLGO   DS    0H
         MVC   TRSVC,=C'FULL'
         BAL   11,TRCPUT
         TPUT  (1),(0),FULLSCR
         BAL   11,TRCRC
         STH   15,RC1
         LTR   15,15
         BNZ   BACK
         CLI   RUNG,4
         BNL   NOWAIT1
         STIMER WAIT,BINTVL=TWOSEC
NOWAIT1  DS    0H
         SR    9,9
         ST    9,CNT
LOOP     DS    0H
         L     9,CNT
         C     9,=F'8'
         BNL   READIT
         N     9,=F'1'
         LTR   9,9
         BNZ   ODD
         LA    6,P0O
         LA    5,P0OL
         CLI   RUNG,5
         BL    GOTFRM
         LA    6,P5O
         LA    5,P5OL
         CLI   RUNG,6
         BL    GOTFRM
         LA    6,P6O
         LA    5,P6OL
         CLI   RUNG,8
         BL    GOTFRM
         LA    6,TK1
         LA    5,TK1L
         B     GOTFRM
ODD      DS    0H
         LA    6,P0C
         LA    5,P0CL
         CLI   RUNG,5
         BL    GOTFRM
         LA    6,P5C
         LA    5,P5CL
         CLI   RUNG,6
         BL    GOTFRM
         LA    6,P6C
         LA    5,P6CL
         CLI   RUNG,8
         BL    GOTFRM
         LA    6,TK2
         LA    5,TK2L
GOTFRM   DS    0H
         ST    5,TLEN
         MVI   SENDBUF,X'F1'       3270 WRITE, AS PROBE E6 VARIANT W
         LA    4,SENDBUF+1
         LR    7,5
         MVCL  4,6
         LA    1,SENDBUF
         L     0,TLEN
         A     0,=F'1'             LENGTH + COMMAND BYTE
         MVC   TRSVC,=C'PART'
         BAL   11,TRCPUT
         TPUT  (1),(0),NOEDIT
         BAL   11,TRCRC
         LTR   15,15
         BNZ   BACK
         LH    2,NPART
         LA    2,1(2)
         STH   2,NPART
         CLI   RUNG,7
         BL    NOGET
         LA    1,INBUF
         LA    0,256
         TGET  (1),(0),ASIS,NOWAIT
         LTR   15,15
         BZ    GOTDATA
         L     2,NEMPTY
         LA    2,1(2)
         ST    2,NEMPTY
NOGET    DS    0H
         STIMER WAIT,BINTVL=HALFSEC
         L     9,CNT
         LA    9,1(9)
         ST    9,CNT
         B     LOOP
READIT   DS    0H
         SR    9,9
READ     DS    0H
         LA    1,INBUF
         LA    0,256
         TGET  (1),(0),ASIS
         LTR   1,1
         BNZ   GOTDATA
         LA    9,1(9)
         C     9,=F'120'
         BNL   BACK
         STIMER WAIT,BINTVL=HALFSEC
         B     READ
GOTDATA  DS    0H
         MVC   AIDB(1),INBUF
BACK     DS    0H
         STTMPMD OFF
         STFSMODE OFF
         STLINENO LINE=1
DONE     DS    0H
         L     15,PTAB+4
         LH    14,RC1
         STH   14,0(15)
         L     15,PTAB+8
         LH    14,NPART
         STH   14,0(15)
         L     15,PTAB+12
         MVC   0(1,15),AIDB
         L     15,PTAB+16
         L     14,TRCNT
         STH   14,0(15)
         L     15,PTAB+20
         L     14,NEMPTY
         STH   14,0(15)
         L     15,PTAB+24
         MVC   0(256,15),TRTAB
         MVC   256(256,15),TRTAB+256
         MVC   512(256,15),TRTAB+512
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
*        TRACE ENTRY (48 BYTES): SERVICE, R1, R0, RC, FIRST 32 BYTES
*        OF THE BUFFER. R0/R1 ARE KEPT FOR THE TPUT THAT FOLLOWS.
TRCPUT   DS    0H
         ST    1,TRR1
         ST    0,TRR0
         L     2,TRCNT
         C     2,=F'16'
         BNL   TRCPX
         LR    3,2
         MH    3,=H'48'
         LA    3,TRTAB(3)
         MVC   0(4,3),TRSVC
         MVC   4(4,3),TRR1
         MVC   8(4,3),TRR0
         XC    12(4,3),12(3)
         L     4,TRR1
         LA    4,0(4)
         MVC   16(32,3),0(4)
TRCPX    DS    0H
         L     1,TRR1
         L     0,TRR0
         BR    11
*        RC OF THE TPUT (R15, KEPT) INTO THE CURRENT ENTRY.
TRCRC    DS    0H
         L     2,TRCNT
         C     2,=F'16'
         BNL   TRCRX
         LR    3,2
         MH    3,=H'48'
         LA    3,TRTAB(3)
         ST    15,12(3)
         LA    2,1(2)
         ST    2,TRCNT
TRCRX    DS    0H
         BR    11
SAVE     DC    18F'0'
PTAB     DS    7F
CNT      DC    F'0'
TLEN     DC    F'0'
TRCNT    DC    F'0'
NEMPTY   DC    F'0'
TRR1     DC    F'0'
TRR0     DC    F'0'
TRSVC    DC    CL4' '
RC1      DC    H'0'
NPART    DC    H'0'
AIDB     DC    X'00'
RUNG     DC    X'00'
HALFSEC  DC    F'50'
TWOSEC   DC    F'200'
CLRPFX   DC    X'114040',X'3C404000'
QUERY    DC    X'F3000501FF02'
QUERYL   EQU   *-QUERY
@@DATA@@
         LTORG
INBUF    DS    CL256
TRTAB    DS    CL768
SENDBUF  DS    CL2060
         END
