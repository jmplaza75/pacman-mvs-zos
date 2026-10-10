*        PACFSIO : TSO FULL-SCREEN SERVICE FOR PACPLAT (MVS-G1, TSC).
*        PROTOCOL VALIDATED BY PROBES E2-E5 (DOCS/EVIDENCE/G1-*).
*        CALL 'PACFSIO' USING OP BUF LEN RC
*          OP  X(4)  FSON  TCLEARQ, STFSMODE ON, STTMPMD ON, ESTAE
*                    QRY   READ PARTITION QUERY (TPUT NOEDIT WSF),
*                          REPLY INTO BUF/LEN (TGET ASIS)
*                    SEND  TPUT FULLSCR OF BUF (LEN BYTES, STARTING
*                          WITH THE WCC) WITH A CLEAR-BUFFER PREFIX
*                          AFTER THE WCC: SBA(1,1) + REPEAT TO ADDRESS
*                          (1,1) WITH X'00' = WHOLE BUFFER NULLED.
*                          (ERASE/WRITE X'F5' SENT WITH TPUT NOEDIT
*                          LEFT THE SCREEN BLACK, JOB 159.)
*                    SENP  MVS-G3 PARTIAL SEND: X'F1' (WRITE, NO ERASE)
*                          + BUF (LEN BYTES, STARTING WITH THE WCC),
*                          TPUT NOEDIT (PROBE E6, VARIANT W)
*                    SENX  MVS-GS: TPUT NOEDIT OF BUF AS IT IS (LEN
*                          BYTES); ITS FIRST BYTE IS THE 3270 COMMAND
*                          CHOSEN BY PACPLAT: X'F5' ERASE/WRITE OR
*                          X'7E' ERASE/WRITE ALTERNATE (PROBE E12)
*                    RECV  TGET ASIS INTO BUF (RETRY EMPTY READS)
*                    RECT  ONE TGET ASIS,NOWAIT (R15: 0 INPUT, 4 NONE,
*                          ELSE ERROR); NONE = WAIT 0.5 S, LEN 0, RC 0
*                          (VISUAL TICK FOR THE CALLER)
*                    POLL  MVS-RT: ONE TGET ASIS,NOWAIT INTO BUF, NO
*                          WAIT: INPUT = LEN > 0, NONE = LEN 0, RC 0
*                          (PROBE E14, DOCS/EVIDENCE/RT-E14-TIMING.MD)
*                    FSOF  ESTAE CANCEL, STTMPMD OFF, STFSMODE OFF,
*                          STLINENO LINE=1 (LINE MODE RESTORED)
*          BUF X(2048)   LEN S9(4) COMP   RC S9(4) COMP
*          RC: 0 OK, 4 NOT A TSO SESSION (NOTHING ISSUED), 8 UNKNOWN
*              OP OR NO INPUT, ELSE THE TPUT/TGET RETURN CODE.
*        ABEND SAFETY: FSON ESTABLISHES AN ESTAE EXIT THAT RESTORES
*        LINE MODE (STTMPMD/STFSMODE OFF, STLINENO 1) AND PERCOLATES.
*        ONLY PACPLAT MAY CALL THIS MODULE.
PACFSIO  CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,5,0(1)
         LA    3,0(3)
         LA    4,0(4)
         LA    5,0(5)
         LA    6,4
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         LA    6,8
         CLC   0(4,2),=C'FSON'
         BE    DOFSON
         CLC   0(4,2),=C'QRY '
         BE    DOQRY
         CLC   0(4,2),=C'SEND'
         BE    DOSEND
         CLC   0(4,2),=C'RECV'
         BE    DORECV
         CLC   0(4,2),=C'FSOF'
         BE    DOFSOF
         CLC   0(4,2),=C'SENP'
         BE    DOSENP
         CLC   0(4,2),=C'RECT'
         BE    DORECT
         CLC   0(4,2),=C'SENX'
         BE    DOSENX
         CLC   0(4,2),=C'POLL'
         BE    DOPOLL
         B     DONE
DOFSON   DS    0H
         TCLEARQ OUTPUT
         TCLEARQ INPUT
         STFSMODE ON,INITIAL=YES
         STTMPMD ON
         ESTAE ABEXIT,CT
         LR    6,15
         B     DONE
DOQRY    DS    0H
         LA    1,QUERY
         LA    0,QUERYL
         TPUT  (1),(0),NOEDIT
         LR    6,15
         LTR   15,15
         BNZ   DONE
         B     DORECV
DOSEND   DS    0H
         MVC   SENDBUF(1),0(3)     THE WCC FROM THE CALLER
         MVC   SENDBUF+1(7),CLRPFX SBA(1,1) + RA TO (1,1) WITH NULLS
         LA    8,SENDBUF+8
         LH    9,0(4)
         BCTR  9,0                 REST OF THE STREAM AFTER THE WCC
         LA    10,1(3)
         LR    11,9
         MVCL  8,10
         LA    1,SENDBUF
         LH    0,0(4)
         AH    0,=H'7'             + CLEAR PREFIX (NOT LA 0,7(0): R0 AS
*                                  BASE MEANS ZERO - JOBS 159/160 BUG)
         TPUT  (1),(0),FULLSCR
         LR    6,15
         B     DONE
DOSENP   DS    0H
         MVI   SENDBUF,X'F1'       3270 COMMAND WRITE (NO ERASE)
         LA    8,SENDBUF+1
         LH    9,0(4)
         LR    10,3
         LR    11,9
         MVCL  8,10
         LA    1,SENDBUF
         LH    0,0(4)
         AH    0,=H'1'
         TPUT  (1),(0),NOEDIT
         LR    6,15
         B     DONE
DOSENX   DS    0H
         LR    1,3
         LH    0,0(4)              LENGTH FROM THE CALLER (NEVER LA)
         TPUT  (1),(0),NOEDIT
         LR    6,15
         B     DONE
DORECT   DS    0H
         LR    1,3
         LA    0,2048
         TGET  (1),(0),ASIS,NOWAIT
         LR    6,15
         LTR   15,15
         BZ    RECTGOT             RC 0: INPUT, LENGTH IN R1
         C     15,=F'4'
         BNE   RECTERR             OTHER RC: ERROR (R1 UNDEFINED)
         SR    1,1                 RC 4: NO INPUT, R1 NOT USED
         STH   1,0(4)
         STIMER WAIT,BINTVL=HALFSEC
         SR    6,6
         B     DONE
DOPOLL   DS    0H
         LR    1,3
         LA    0,2048
         TGET  (1),(0),ASIS,NOWAIT
         LR    6,15
         LTR   15,15
         BZ    RECTGOT             RC 0: INPUT, LENGTH IN R1
         C     15,=F'4'
         BNE   RECTERR             OTHER RC: ERROR (R1 UNDEFINED)
         SR    1,1                 RC 4: NO INPUT, R1 NOT USED
         STH   1,0(4)
         SR    6,6
         B     DONE
RECTGOT  DS    0H
         STH   1,0(4)
         B     DONE
RECTERR  DS    0H
         SR    1,1
         STH   1,0(4)
         B     DONE
DORECV   DS    0H
         SR    7,7                 EMPTY-READ COUNTER
RECVLOOP DS    0H
         LR    1,3
         LA    0,2048
         TGET  (1),(0),ASIS
         LR    6,15
         STH   1,0(4)
         LTR   1,1
         BNZ   DONE
         LA    7,1(7)
         C     7,=F'600'
         BNL   NOINPUT
         STIMER WAIT,BINTVL=HALFSEC
         B     RECVLOOP
NOINPUT  DS    0H
         LA    6,8
         B     DONE
DOFSOF   DS    0H
         ESTAE 0
         BAL   14,RESTORE
         SR    6,6
DONE     DS    0H
         STH   6,0(5)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
*        RESTORE LINE MODE (USED BY FSOF AND BY THE ESTAE EXIT).
RESTORE  DS    0H
         ST    14,RESTR14
         STTMPMD OFF
         STFSMODE OFF
         STLINENO LINE=1
         L     14,RESTR14
         BR    14
*        ESTAE EXIT: R15 = ENTRY POINT. REBUILD THE MAIN BASE IN R12,
*        RESTORE LINE MODE, PERCOLATE (R15 = 0, SDWA LEFT UNCHANGED).
ABEXIT   DS    0H
         USING ABEXIT,15
         LR    9,14
         LR    12,15
         S     12,ABOFF
         DROP  15
         BAL   14,RESTORE
         LR    14,9
         SR    15,15
         BR    14
ABOFF    DC    A(ABEXIT-PACFSIO-6)
SAVE     DC    18F'0'
RESTR14  DC    F'0'
HALFSEC  DC    F'50'
SENDBUF  DS    CL2060
CLRPFX   DC    X'114040',X'3C404000'
*        READ PARTITION QUERY: WSF X'F3', LENGTH 5, X'01', PID X'FF',
*        X'02' QUERY (VALIDATED BY PROBE E5).
QUERY    DC    X'F3000501FF02'
QUERYL   EQU   *-QUERY
         LTORG
         END
