*        PACHSIO : MVS-HS (D38) HIGH-SCORE RECORD SERVICE FOR PACPLAT.
*        ONE 80-BYTE RECORD IN THE PDS MEMBER NAMED ON A DD. PRODUCTION
*        FORM OF THE PROBE E16 SERVICE PACHSA (DOCS/EVIDENCE/
*        HS-E16-PROBE.MD, JOBS 254 AND 258). NEVER ABENDS THE CALLER.
*        CALL 'PACHSIO' USING OP RC DDN REC
*          OP  X(4)  'READ' = THE FIRST RECORD OF THE MEMBER INTO REC.
*                    'WRIT' = REC REPLACES THE FIRST RECORD IN PLACE
*                    (QSAM UPDAT, GET + PUTX: SAME BLOCK, NO NEW
*                    SPACE). A MISSING OR EMPTY MEMBER: AS REPL.
*                    'REPL' = THE MEMBER BECOMES THE ONE RECORD REC
*                    (QSAM OUTPUT: ADDED OR REPLACED BY STOW AT CLOSE).
*                    THE MEMBER IS LOOKED UP BY BPAM BLDL WITH THE PDS
*                    OPENED WITHOUT IT (TYPE=J, JFCNWRIT), SO NO OPEN
*                    EVER MEETS A MISSING MEMBER (013-18); BEFORE EVERY
*                    QSAM OPEN A FRESH RDJFCB MUST STILL SHOW THE SAME
*                    MEMBER (NEVER THE WHOLE PDS AS A SEQUENTIAL FILE).
*                    THE I/O RUNS UNDER AN ESTAE: ANY ABEND (X37, B14,
*                    913, 013 ...) RETRIES INTO THE RETURN PATH, RC 16;
*                    THE ESTAE IS DELETED BEFORE EVERY RETURN.
*          RC  S9(4) COMP  0 DONE, 2 MEMBER WRITTEN NEW (ADDED OR
*                    REPLACED), 4 NO SUCH DD, 8 UNUSABLE (DUMMY, NO
*                    MEMBER ON THE DD, NOT RECFM F(B) LRECL 80 BLKSIZE
*                    80), 12 MEMBER MISSING OR EMPTY (READ), 16 I/O
*                    ERROR OR ABEND CAUGHT, 20 BAD OP.
*          DDN X(8)  DD NAME.  REC X(80).
*        ONLY PACPLAT MAY CALL THIS MODULE.
PACHSIO  CSECT
         STM   14,12,12(13)
         BALR  12,0
BASE     DS    0H
         USING BASE,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,5,0(1)            OP RC DDN REC
         LA    5,0(5)
         ST    3,ARC
         ST    5,AREC
         LA    4,0(4)
         MVC   DDN,0(4)
         MVI   ESTON,0
         MVI   RETRIED,0
         MVC   OP,0(2)
         LA    9,20
         CLC   OP,=C'READ'
         BE    OPOK
         CLC   OP,=C'REPL'
         BE    OPOK
         CLC   OP,=C'WRIT'
         BNE   RETURN
OPOK     DS    0H
         ST    12,MYBASE
         ESTAE ESTEXIT,CT
         LTR   15,15
         BNZ   NOGUARD
         MVI   ESTON,1
NOGUARD  DS    0H
         LA    9,4
         DEVTYPE DDN,DVAREA
         LTR   15,15
         BNZ   RETURN
         LA    9,8
         LA    7,PODCB
         BAL   14,DCBRESET
         RDJFCB (PODCB)
         LTR   15,15
         BNZ   RETURN
         TM    JFCB+X'56',X'01'    JFCBIND1 JFCPDS: MEMBER NAMED
         BZ    RETURN
         MVC   BLDLN,JFCB+X'2C'    JFCBELNM
*        E16 JOB 249: OPEN SEARCHES A MEMBER NAMED ON THE DD EVEN FOR
*        BPAM (013-18 IF MISSING). THE MEMBER IS REMOVED FROM THE JFCB
*        COPY AND THE PDS OPENED WITH IT (TYPE=J); BLDL FINDS IT.
*        E16 JOB 251: WITHOUT JFCNWRIT THE CHANGED JFCB WAS WRITTEN
*        BACK (THE NEXT CALL SAW NO MEMBER): JFCBTSDM X'08' SET.
         MVC   JFCB+X'2C'(8),=CL8' '
         NI    JFCB+X'56',X'FE'
         OI    JFCB+X'34',X'08'    JFCBTSDM JFCNWRIT
         MVI   IOERR,0
         OPEN  (PODCB,(INPUT)),TYPE=J
         TM    PODCB+48,X'10'      DCBOFLGS OPEN OK
         BZ    RETURN
         LA    9,8
         CLC   PODCB+82(2),=H'80'  DCBLRECL
         BNE   CLOSEP
         CLC   PODCB+62(2),=H'80'  DCBBLKSI
         BNE   CLOSEP
         TM    PODCB+36,X'80'      DCBRECFM F
         BZ    CLOSEP
         TM    PODCB+36,X'40'      NOT V/U
         BO    CLOSEP
         BLDL  PODCB,BLDLL
         LA    9,16
         CH    15,=H'4'
         BH    CLOSEP
         BE    NOMEM
         CLC   OP,=C'WRIT'
         BE    UPDATE
         CLC   OP,=C'REPL'
         BE    REPLC
         MVI   BLDLK,0             CONCATENATION 0
         FIND  PODCB,BLDLTTR,C
         READ  DECB1,SF,PODCB,BUF,'S'
         CHECK DECB1
         LA    9,16
         CLI   IOERR,0
         BNE   CLOSEP
         SR    9,9
         L     5,AREC
         MVC   0(80,5),BUF
         B     CLOSEP
EOM      DS    0H                  EODAD: NO RECORD IN THE MEMBER
         LA    9,12
         B     CLOSEP
*        E16 JOB 252: BPAM UPDAT + WRITE (MF=E) ABENDED S800; THE
*        REWRITE IS QSAM UPDAT ON THE MEMBER NAMED ON THE DD, WHICH
*        BLDL HAS JUST FOUND.
UPDATE   DS    0H
         CLOSE (PODCB)
         LA    7,QUDCB
         BAL   14,SAMEMEM
         LTR   9,9
         BNZ   RETURN
         OPEN  (QUDCB,(UPDAT))
         LA    9,8
         TM    QUDCB+48,X'10'
         BZ    RETURN
         GET   QUDCB
         L     5,AREC
         MVC   0(80,1),0(5)
         PUTX  QUDCB
         SR    9,9
         CLI   IOERR,0
         BE    CLOSEQ
         LA    9,16
         B     CLOSEQ
QEOM     DS    0H                  EODAD: EMPTY MEMBER -> REPLACE
         CLOSE (QUDCB)
         B     REPLACE
CLOSEQ   DS    0H
         CLOSE (QUDCB)
         B     RETURN
NOMEM    DS    0H
         LA    9,12
         CLC   OP,=C'READ'
         BE    CLOSEP
REPLC    DS    0H
         CLOSE (PODCB)
REPLACE  DS    0H
         LA    7,PSDCB
         BAL   14,SAMEMEM
         LTR   9,9
         BNZ   RETURN
         OPEN  (PSDCB,(OUTPUT))
         LA    9,8
         TM    PSDCB+48,X'10'
         BZ    RETURN
         L     5,AREC
         PUT   PSDCB,(5)
         CLOSE (PSDCB)
         LA    9,2
         B     RETURN
CLOSEP   DS    0H
         CLOSE (PODCB)
RETURN   DS    0H
*        E16B JOB 257: AFTER A RETRY THE EXIT IS STILL ON THE CHAIN
*        (TWO LATER ESTAE 0 BOTH RC 0): DELETED IN BOTH CASES.
         CLI   ESTON,1
         BNE   NOESTAE
         ESTAE 0
NOESTAE  DS    0H
         L     3,ARC
         STH   9,0(3)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
*        SAMEMEM: R7 = A CLOSED QSAM DCB, RESET FOR THE DD. R9 := 0 IF
*        THE DD STILL NAMES THE MEMBER BLDL LOOKED FOR, ELSE 8. SAFETY:
*        A QSAM OPEN OF THE DD WITHOUT ITS MEMBER WOULD OVERWRITE (OR
*        READ) THE WHOLE PDS AS A SEQUENTIAL DATASET.
SAMEMEM  DS    0H
         ST    14,SAVE14
         BAL   14,DCBRESET
         LA    9,8
         RDJFCB ((7))
         LTR   15,15
         BNZ   SAMEX
         TM    JFCB+X'56',X'01'
         BZ    SAMEX
         CLC   BLDLN,JFCB+X'2C'
         BNE   SAMEX
         SR    9,9
SAMEX    DS    0H
         L     14,SAVE14
         BR    14
*        DCBRESET: R7 = A CLOSED DCB. NEW DD NAME; RECFM, BLKSIZE
*        AND LRECL CLEARED: THE NEXT OPEN MERGES THEM FROM THE DSCB.
DCBRESET DS    0H
         MVC   40(8,7),DDN         DCBDDNAM
         MVI   36(7),0             DCBRECFM
         XC    62(2,7),62(7)       DCBBLKSI
         XC    82(2,7),82(7)       DCBLRECL
         BR    14
*        RETRY ROUTINE (FROM ESTEXIT): REBUILD THE BASE, OWN SAVE AREA,
*        RC 16. NO DCB IS TOUCHED AGAIN.
         DROP  12
RETRY    DS    0H
         BALR  11,0
         USING *,11
         L     12,MYBASE
         DROP  11
         USING BASE,12
         LA    13,SAVE
         MVI   RETRIED,1
         LA    9,16
         B     RETURN
         DROP  12
*        ESTAE EXIT: R15 = ENTRY. NO SDWA (R0 = 12): R0 = RETRY,
*        R15 = 4.
*        WITH SDWA: SETRP RETRY, NO DUMP.
ESTEXIT  DS    0H
         USING ESTEXIT,15
         C     0,=F'12'
         BE    NOSDWA
         USING SDWA,1
         L     2,=A(RETRY)
         SETRP RC=4,RETADDR=(2),FRESDWA=YES,DUMP=NO
         DROP  1
         BR    14
NOSDWA   DS    0H
         L     0,=A(RETRY)
         LA    15,4
         BR    14
         DROP  15
         USING BASE,12
IOX      DS    0H                  SYNAD: FLAG, BACK TO CHECK
         MVI   IOERR,1
         BR    14
SAVE     DC    18F'0'
ARC      DC    A(0)
SAVE14   DC    A(0)
AREC     DC    A(0)
DVAREA   DC    2F'0'
DDN      DC    CL8' '
OP       DC    CL4' '
IOERR    DC    X'00'
ESTON    DC    X'00'
RETRIED  DC    X'00'
MYBASE   DC    A(0)
         DS    0F
JX       DC    X'87',AL3(JFCB)
JFCB     DS    CL176
BLDLL    DC    H'1',H'58'
BLDLN    DC    CL8' '
BLDLTTR  DC    XL3'00'
BLDLK    DC    X'00'
BLDLREST DC    XL46'00'
BUF      DS    CL80
PODCB    DCB   DSORG=PO,MACRF=R,EXLST=JX,SYNAD=IOX,EODAD=EOM
PSDCB    DCB   DSORG=PS,MACRF=PM,EXLST=JX
QUDCB    DCB   DSORG=PS,MACRF=(GL,PM),EXLST=JX,SYNAD=IOX,EODAD=QEOM
         LTORG
         IHASDWA
         END
