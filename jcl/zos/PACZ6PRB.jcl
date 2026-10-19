//PACZ6PRB JOB 1,'PACMAN ZOS6 PROBE',CLASS=7,MSGLEVEL=(1,1),
//             NOTIFY=&SYSUID
//ASM      EXEC PGM=ASMA90,
//             PARM='OBJECT,NODECK'
//STEPLIB  DD DSN=HLA.SASMMOD1,DISP=SHR
//SYSLIB   DD DSN=SYS1.MACLIB,DISP=SHR
//         DD DSN=SYS1.MODGEN,DISP=SHR
//SYSUT1   DD UNIT=SYSALLDA,SPACE=(TRK,(5,5))
//SYSPRINT DD SYSOUT=*
//SYSLIN   DD DSN=&&OBJ,DISP=(NEW,PASS),UNIT=SYSALLDA,
//             SPACE=(TRK,(5,5)),DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSIN    DD *
*        PACZ6P : ZOS-6 PROTOCOL PROBE (DOCS/ZOS6-PROTOCOL-PROBE.MD).
*        ISOLATED FROM PACMAN: NO PACFSIO, NO COBOL, NO LE, NO ESTAE,
*        NO ATTACH, NO STAX. CALL FROM TSO WITH PARM 'P0', 'PT', 'PN',
*        'PH', 'PB4', 'PR2' OR 'PR2I'.
*        AN ABSOLUTE 150 MS SCHEDULE FOR 20 S (133 QUANTA). EACH
*        QUANTUM: ONE SMALL 3270 WRITE (X'F1' WRITE, WCC X'C2', THE
*        WCC PACMAN USES), THEN ONE TGET ASIS,NOWAIT, THEN STIMER
*        UNTIL THE NEXT ABSOLUTE DEADLINE.
*          P0: THE WRITE BY TPUT NOEDIT (AS PACFSIO SENP TODAY)
*          PT: THE SAME BYTES BY TPG NOEDIT,WAIT,NOHOLD (AN OUTBOUND
*              REQUEST UNIT WITH CHANGE DIRECTION)
*          PN: AS P0, BUT THE TGET ASIS,NOWAIT COMES FIRST IN EACH
*              QUANTUM, BEFORE THE TPUT NOEDIT (POLL BEFORE OUTPUT)
*          PH: AS P0, BUT TPUT NOEDIT,WAIT,HOLD: CONTROL RETURNS ONLY
*              WHEN THE FRAME IS WRITTEN TO THE TERMINAL (OR DISCARDED)
*          PB4: AS P0, BUT EVERY 4TH QUANTUM (Q MOD 4 = 0) WRITES ITS
*              FRAME WITH THE PH TPUT HOLD (A PERIODIC OUTPUT BARRIER)
*          PR2: AS P0 (150 MS QUANTA, A POLL EVERY QUANTUM), BUT ONLY
*              EVEN QUANTA WRITE (THE CURRENT STATE, TPUT NOEDIT);
*              ODD QUANTA WRITE NOTHING AND NOTHING IS WRITTEN LATER
*          PR2I: EXACTLY PR2 (MODE R, SAME TITLE), PLUS A HOST-SIDE
*              TABLE: ONE 32-BYTE RECORD PER QUANTUM, FILLED IN THE
*              LOOP ONLY WITH CLOCK READS AND STORES (NO I/O), PRINTED
*              AFTER LINE MODE IS RESTORED (STATUS LINES S1 / S2 AND
*              DETAIL LINES I FOR THE FIRST 3 AID QUANTA AND THE 3
*              QUANTA BEFORE EACH)
*        AFTER THE RUN, LINE MODE (TPUT): MODE, QUANTA, ELAPSED MS,
*        ISSUE LATENESS (COUNT > 75 MS, MAXIMUM), LONGEST OUTPUT
*        CALL, RETURN CODES, AIDS RECEIVED (AID, QUANTUM, MS SINCE
*        T0; THE FIRST 8). NOT A TSO USER: NOTHING ISSUED, RC 4. BAD
*        PARM: RC 16. TPUT/TPG RC NOT 0 (8 = ATTENTION), TGET RC NOT
*        0/4, OR 60 S ELAPSED: THE LOOP ENDS AT ONCE, LINE MODE IS
*        RESTORED AND THE SUMMARY IS STILL WRITTEN.
PACZ6P   CSECT
PACZ6P   AMODE 24
PACZ6P   RMODE 24
         STM   14,12,12(13)
         BALR  12,0
         USING *,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LA    10,16               RC 16: BAD PARM
         L     2,0(1)              PARM: HALFWORD LENGTH + TEXT
         LA    2,0(2)
         CLC   0(2,2),=H'2'
         BL    EXIT
         CLC   2(2,2),=C'P0'
         BE    PARMOK
         CLC   2(2,2),=C'PT'
         BE    PARMOK
         CLC   2(2,2),=C'PN'
         BE    PARMOK
         CLC   2(2,2),=C'PH'
         BE    PARMOK
         CLC   2(2,2),=C'PB'       PB4: THREE CHARACTERS
         BNE   PARMR
         CLC   0(2,2),=H'3'
         BL    EXIT
         CLI   4(2),C'4'
         BNE   EXIT
         MVI   FMODE+2,C'4'
         MVI   S1MODE+2,C'4'
         B     PARMOK
PARMR    DS    0H
         CLC   2(2,2),=C'PR'       PR2: THREE CHARACTERS
         BNE   EXIT
         CLC   0(2,2),=H'3'
         BL    EXIT
         CLI   4(2),C'2'
         BNE   EXIT
         MVI   FMODE+2,C'2'
         MVI   S1MODE+2,C'2'
         CLC   0(2,2),=H'4'        PR2I: FOUR CHARACTERS
         BL    PARMOK
         CLI   5(2),C'I'
         BNE   EXIT
         MVI   INSTR,1             MODE R + THE TABLE; TITLE AS PR2
         MVI   S1MODE+3,C'I'
PARMOK   DS    0H
         MVC   MODE,3(2)           C'0', C'T', C'N', C'H', C'B', C'R'
         MVC   FMODE(2),2(2)
         MVC   S1MODE(2),2(2)
         LA    10,4                RC 4: NOT A TSO USER
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    EXIT
         TCLEARQ OUTPUT
         TCLEARQ INPUT
         STFSMODE ON,INITIAL=YES
         STTMPMD ON
         LA    1,SCR0
         LA    0,SCR0L
         TPUT  (1),(0),NOEDIT
         ST    15,RCOUT
         BAL   14,NOWMS            T0 := NOW (THE FIRST CALL)
         SR    8,8                 R8 = QUANTUM NUMBER
         L     15,RCOUT
         LTR   15,15
         BNZ   ENDLOOP
LOOP     DS    0H
         LA    8,1(8)
         CLI   INSTR,1             PR2I: THIS QUANTUM'S RECORD
         BNE   NOINS0
         LR    6,8
         BCTR  6,0
         SLL   6,5                 (Q - 1) X 32
         LA    6,ITAB(6)
         MVC   0(32,6),IINIT       SENTINELS, WRITE FLAG 0
         STH   8,0(6)
NOINS0   DS    0H
         BAL   14,NOWMS            R1 = MS SINCE T0
         ST    1,TISSUE
         LR    0,8
         BCTR  0,0
         MH    0,PERIOD            THIS DEADLINE = (Q - 1) * 150
         SR    1,0                 ISSUE LATENESS (MS)
         C     1,MAXLATE
         BNH   LATEA
         ST    1,MAXLATE
LATEA    DS    0H
         C     1,=F'75'
         BNH   LATEB
         L     1,LATECNT
         LA    1,1(1)
         ST    1,LATECNT
LATEB    DS    0H
         CLI   MODE,C'N'           PN: POLL BEFORE THE OUTPUT
         BNE   FRAMEB
         BAL   11,POLL
         LTR   15,15
         BNZ   ENDLOOP
         BAL   14,NOWMS            THE OUTPUT CALL STARTS NOW
         ST    1,TISSUE
FRAMEB   DS    0H
         CLI   MODE,C'R'           PR2: ODD QUANTA WRITE NOTHING
         BNE   FRAMEC
         LR    4,8
         N     4,=F'1'             Q MOD 2
         BZ    FRAMEC
         L     2,SKIPCNT
         LA    2,1(2)
         ST    2,SKIPCNT
         B     PUTOK               STILL POLLED, SAME DEADLINE
FRAMEC   DS    0H
         CVD   8,DW                THE FRAME: QUANTUM, AIDS SO FAR
         UNPK  FQ(4),DW
         OI    FQ+3,X'F0'
         L     1,AIDCNT
         CVD   1,DW
         UNPK  FA(2),DW
         OI    FA+1,X'F0'
         CLI   INSTR,1             PR2I: TIME BEFORE THE TPUT
         BNE   NOINS1
         BAL   14,NOWMS
         ST    1,12(6)
         MVI   2(6),1              WRITE FLAG 1
NOINS1   DS    0H
         MVI   HOLDQ,0
         LA    1,FRAME
         LA    0,FRAMEL
         CLI   MODE,C'T'
         BE    USETPG
         CLI   MODE,C'H'
         BE    USEHOLD
         CLI   MODE,C'B'
         BNE   USENOH
         LR    4,8
         N     4,=F'3'             Q MOD 4
         BZ    USEHOLD             PB4: EVERY 4TH QUANTUM A BARRIER
USENOH   DS    0H
         TPUT  (1),(0),NOEDIT
         B     OUTDONE
USEHOLD  DS    0H
         MVI   HOLDQ,1             THIS QUANTUM'S OUTPUT IS A HOLD
         TPUT  (1),(0),NOEDIT,WAIT,HOLD
         B     OUTDONE
USETPG   DS    0H
*        TPG FORBIDS R0/R1 FOR BUFADDR/BUFSIZE (IHB300, JOB04217).
*        R2/R3 ARE SCRATCH HERE (R2 IS RELOADED AFTER THE TGET).
         LA    2,FRAME
         LA    3,FRAMEL
         TPG   (2),(3),NOEDIT,WAIT,NOHOLD
OUTDONE  DS    0H
         ST    15,RCOUT
         LTR   15,15
         BNZ   ENDLOOP
         L     2,WRCNT             PHYSICAL WRITES ISSUED
         LA    2,1(2)
         ST    2,WRCNT
         CLI   INSTR,1             PR2I: TIME AFTER THE TPUT
         BNE   NOINS2
         BAL   14,NOWMS
         ST    1,16(6)
NOINS2   DS    0H
         BAL   14,NOWMS
         S     1,TISSUE            OUTPUT CALL DURATION (MS)
         CLI   HOLDQ,1
         BNE   PUTNH
         L     2,HOLDCNT           A HOLD CALL: COUNT, LONGEST
         LA    2,1(2)
         ST    2,HOLDCNT
         C     1,MAXHOLD
         BNH   PUTALL
         ST    1,MAXHOLD
         B     PUTALL
PUTNH    DS    0H
         C     1,MAXNOH            ANY OTHER OUTPUT CALL: LONGEST
         BNH   PUTALL
         ST    1,MAXNOH
PUTALL   DS    0H
         C     1,MAXPUT
         BNH   PUTOK
         ST    1,MAXPUT
PUTOK    DS    0H
         CLI   MODE,C'N'           PN: ALREADY POLLED THIS QUANTUM
         BE    NOAID
         BAL   11,POLL             P0 / PT: POLL AFTER THE OUTPUT
         LTR   15,15
         BNZ   ENDLOOP
NOAID    DS    0H
         LR    0,8
         MH    0,PERIOD            THE NEXT DEADLINE = Q * 150
         ST    0,TDEAD
         BAL   14,NOWMS
         C     1,=F'60000'
         BH    ENDLOOP             SAFETY CAP: 60 S
         L     0,TDEAD
         SR    0,1                 REMAINDER TO THE DEADLINE
         BNP   NOSLEEP
         LR    1,0
         M     0,=F'1000'          MS -> US IN R0/R1
         SLDL  0,12                US -> TOD UNITS
         STM   0,1,MICDW
         STIMER WAIT,MICVL=MICDW
NOSLEEP  DS    0H
         C     8,NQUANTA
         BL    LOOP
ENDLOOP  DS    0H
         BAL   14,NOWMS
         ST    1,TEND
         STTMPMD OFF
         STFSMODE OFF
         STLINENO LINE=1
         LR    1,8
         LA    2,S1Q
         BAL   14,DEC6
         L     1,TEND
         LA    2,S1E
         BAL   14,DEC6
         LA    1,SUM1
         LA    0,SUM1L
         TPUT  (1),(0)
         L     1,LATECNT
         LA    2,S2L
         BAL   14,DEC6
         L     1,MAXLATE
         LA    2,S2M
         BAL   14,DEC6
         L     1,MAXPUT
         LA    2,S2P
         BAL   14,DEC6
         LA    1,SUM2
         LA    0,SUM2L
         TPUT  (1),(0)
         L     1,RCOUT
         LA    2,S3O
         BAL   14,DEC6
         L     1,RCIN
         LA    2,S3I
         BAL   14,DEC6
         L     1,AIDCNT
         LA    2,S3A
         BAL   14,DEC6
         LA    1,SUM3
         LA    0,SUM3L
         TPUT  (1),(0)
         L     1,HOLDCNT
         LA    2,S4H
         BAL   14,DEC6
         L     1,MAXHOLD
         LA    2,S4M
         BAL   14,DEC6
         L     1,MAXNOH
         LA    2,S4N
         BAL   14,DEC6
         LA    1,SUM4
         LA    0,SUM4L
         TPUT  (1),(0)
         L     1,WRCNT
         LA    2,S5W
         BAL   14,DEC6
         L     1,SKIPCNT
         LA    2,S5S
         BAL   14,DEC6
         LA    1,SUM5
         LA    0,SUM5L
         TPUT  (1),(0)
         L     9,AIDCNT
         C     9,=F'8'
         BNH   AIDN
         LA    9,8
AIDN     DS    0H
         LTR   9,9
         BZ    SUMEND
         LA    7,AIDTAB
AIDLOOP  DS    0H
         LR    3,7
         LA    2,SAID
         BAL   14,HEX2
         LH    1,2(7)
         LA    2,SAQ
         BAL   14,DEC6
         L     1,4(7)
         LA    2,SAT
         BAL   14,DEC6
         LA    1,SUMA
         LA    0,SUMAL
         TPUT  (1),(0)
         LA    7,8(7)
         BCT   9,AIDLOOP
SUMEND   DS    0H
         CLI   INSTR,1             PR2I: THE TABLE, IN LINE MODE
         BNE   SUMX
         BAL   11,IDUMP
SUMX     DS    0H
         SR    10,10
EXIT     DS    0H
         L     13,SAVE+4
         L     14,12(13)
         LR    15,10
         LM    0,12,20(13)
         BR    14
*        POLL (LINK R11): ONE TGET ASIS,NOWAIT, NEVER A WAIT. RC 0
*        WITH DATA: AID, QUANTUM, MS RECORDED (THE FIRST 8), COUNTED.
*        RC 4 OR LENGTH 0: NOTHING. RETURNS R15 = 0, OR THE TGET RC
*        (NOT 0 / 4, KEPT IN RCIN) TO END THE LOOP. USES R0-R2, R14.
POLL     DS    0H
         CLI   INSTR,1             PR2I: TIME, AIDCNT BEFORE THE READ
         BNE   NOINS3
         BAL   14,NOWMS
         ST    1,20(6)
         L     2,AIDCNT
         STH   2,8(6)
NOINS3   DS    0H
         LA    1,INBUF
         LA    0,256
         TGET  (1),(0),ASIS,NOWAIT
         CLI   INSTR,1             PR2I: TIME, RC, LENGTH, AID
         BNE   NOINS4
         LR    5,1                 R1: BYTES MOVED (RC 0)
         BAL   14,NOWMS
         ST    1,24(6)
         STC   15,3(6)             READ RC (LOW BYTE OF R15)
         LTR   15,15
         BNZ   NOINS5              RC NOT 0: LENGTH STAYS X'FFFF'
         STH   5,4(6)
         LTR   5,5
         BZ    NOINS5
         MVC   6(1,6),INBUF        THE AID BYTE
NOINS5   DS    0H
         LR    1,5
NOINS4   DS    0H
         C     15,=F'4'
         BE    POLLNO
         ST    15,RCIN
         LTR   15,15
         BNZR  11
         LTR   1,1                 LENGTH 0: NOTHING
         BZ    POLLNO
         L     2,AIDCNT
         C     2,=F'8'
         BNL   AIDCOUNT
         MH    2,=H'8'             ENTRY: AID, PAD, QUANTUM, MS
         LA    2,AIDTAB(2)
         MVC   0(1,2),INBUF
         STH   8,2(2)
         BAL   14,NOWMS
         ST    1,4(2)
AIDCOUNT DS    0H
         L     2,AIDCNT
         LA    2,1(2)
         ST    2,AIDCNT
POLLNO   DS    0H
         CLI   INSTR,1             PR2I: AIDCNT AFTER THE READ
         BNE   NOINS6
         L     2,AIDCNT
         STH   2,10(6)
NOINS6   DS    0H
         SR    15,15
         BR    11
*        NOWMS: R1 := MILLISECONDS SINCE T0 (T0 = THE FIRST CALL).
*        AS PACTSO NOWMS. USES R0, R1.
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
         D     0,=F'1000'          MS IN R1
         BR    14
*        IDUMP (LINK R11; AFTER ENDLOOP ONLY, LINE MODE): ONE STATUS
*        CHARACTER PER EXECUTED QUANTUM (NO WRITE: . RC 4, A DATA,
*        Z RC 0 LENGTH 0, E OTHER RC IN LOWER CASE; WRITE: : / UPPER
*        CASE), THEN THE DETAIL LINES. USES R0-R7, R9, R14, R15.
IDUMP    DS    0H
         MVC   ISTRW,ISTRW-1       BLANKS (ISTRW-1 IS A BLANK)
         LA    6,ITAB
         LA    7,ISTRW
         LR    9,8
         LTR   9,9
         BZ    IDPRT
IDST     DS    0H
         MVI   0(7),C'.'
         CLI   3(6),X'04'
         BE    IDSW
         MVI   0(7),C'e'
         CLI   3(6),X'00'
         BNE   IDSW
         MVI   0(7),C'z'
         CLC   4(2,6),=H'0'
         BE    IDSW
         MVI   0(7),C'a'
IDSW     DS    0H
         CLI   2(6),1
         BNE   IDSN
         OI    0(7),X'40'          LOWER TO UPPER CASE
         CLI   0(7),C'.'
         BNE   IDSN
         MVI   0(7),C':'
IDSN     DS    0H
         LA    6,32(6)
         LA    7,1(7)
         BCT   9,IDST
IDPRT    DS    0H
         MVC   IS1T,ISTRW
         MVC   IS2T,ISTRW+67
         LA    1,IS1
         LA    0,IS1L
         TPUT  (1),(0)
         LA    1,IS2
         LA    0,IS2L
         TPUT  (1),(0)
         SR    5,5                 AID QUANTA DETAILED SO FAR
         LA    6,ITAB
         LR    9,8
         LTR   9,9
         BZ    IDEND
IDSCAN   DS    0H
         CLC   10(2,6),8(6)        AIDCNT AFTER > BEFORE?
         BNH   IDNEXT
         C     5,=F'3'
         BNL   IDEND
         LA    5,1(5)
         LR    4,6
         S     4,=F'96'            THE 3 QUANTA BEFORE
         C     4,=A(ITAB)
         BNL   IDLOOP
         LA    4,ITAB
IDLOOP   DS    0H
         BAL   7,IDLINE
         LA    4,32(4)
         CR    4,6
         BNH   IDLOOP
IDNEXT   DS    0H
         LA    6,32(6)
         BCT   9,IDSCAN
IDEND    DS    0H
         BR    11
*        IDLINE (LINK R7): THE RECORD AT 0(R4) AS ONE DETAIL LINE.
IDLINE   DS    0H
         LH    1,0(4)
         LA    2,IDW
         BAL   14,DEC6
         MVC   IQ,IDW+3
         MVI   IW,C'0'
         CLI   2(4),1
         BNE   IDL1
         MVI   IW,C'1'
IDL1     DS    0H
         LA    3,3(4)
         LA    2,IR
         BAL   14,HEX2
         MVC   IL,=C'---'
         CLC   4(2,4),=X'FFFF'
         BE    IDL2
         LH    1,4(4)
         LA    2,IDW
         BAL   14,DEC6
         MVC   IL,IDW+3
IDL2     DS    0H
         LA    3,6(4)
         LA    2,IA
         BAL   14,HEX2
         LH    1,8(4)
         LA    2,IDW
         BAL   14,DEC6
         MVC   ICB,IDW+4
         LH    1,10(4)
         LA    2,IDW
         BAL   14,DEC6
         MVC   ICA,IDW+4
         L     1,12(4)
         LA    2,IT1
         BAL   14,ITIME
         L     1,16(4)
         LA    2,IT2
         BAL   14,ITIME
         L     1,20(4)
         LA    2,IT3
         BAL   14,ITIME
         L     1,24(4)
         LA    2,IT4
         BAL   14,ITIME
         LA    1,IDL
         LA    0,IDLL
         TPUT  (1),(0)
         BR    7
*        ITIME (LINK R14): R1 AS 6 DIGITS AT 0(R2), OR ------ FOR -1.
ITIME    DS    0H
         C     1,=F'-1'
         BNE   ITIME1
         MVC   0(6,2),=C'------'
         BR    14
ITIME1   DS    0H
         CVD   1,DW
         UNPK  0(6,2),DW
         OI    5(2),X'F0'
         BR    14
*        DEC6: R1 (0..999999) AS 6 DECIMAL DIGITS AT 0(R2).
DEC6     DS    0H
         CVD   1,DW
         UNPK  0(6,2),DW
         OI    5(2),X'F0'
         BR    14
*        HEX2: THE BYTE AT 0(R3) AS 2 HEX CHARACTERS AT 0(R2).
HEX2     DS    0H
         SR    15,15
         IC    15,0(3)
         SRL   15,4
         IC    0,HEXC(15)
         STC   0,0(2)
         SR    15,15
         IC    15,0(3)
         N     15,=F'15'
         IC    0,HEXC(15)
         STC   0,1(2)
         BR    14
SAVE     DC    18F'0'
         DS    0D
DW       DC    D'0'
T0       DC    D'0'
NOW      DC    D'0'
MICDW    DC    D'0'
TISSUE   DC    F'0'
TDEAD    DC    F'0'
TEND     DC    F'0'
MAXLATE  DC    F'0'
MAXPUT   DC    F'0'
MAXHOLD  DC    F'0'
MAXNOH   DC    F'0'
HOLDCNT  DC    F'0'
WRCNT    DC    F'0'
SKIPCNT  DC    F'0'
LATECNT  DC    F'0'
AIDCNT   DC    F'0'
RCOUT    DC    F'0'
RCIN     DC    F'0'
NQUANTA  DC    F'133'              20 S AT 150 MS
PERIOD   DC    H'150'
T0SET    DC    X'00'
MODE     DC    C'0'
INSTR    DC    X'00'               1: PR2I TABLE
HOLDQ    DC    X'00'
HEXC     DC    C'0123456789ABCDEF'
SCR0     DC    X'F5C3'             ERASE/WRITE, WCC
         DC    X'114040'           SBA (1,1)
         DC    C'PACZ6P ZOS-6 PROTOCOL PROBE  MODE '
FMODE    DC    C'XX '
         DC    C'  20 S AT 150 MS. DO NOT TYPE.'
SCR0L    EQU   *-SCR0
FRAME    DC    X'F1C2'             WRITE, WCC: KEYBOARD RESTORE
         DC    X'11C261'           SBA (3,2) ON 80 COLUMNS
         DC    C'QUANTUM '
FQ       DC    C'0000'
         DC    C'  AIDS RECEIVED '
FA       DC    C'00'
FRAMEL   EQU   *-FRAME
SUM1     DC    C'PACZ6P MODE '
S1MODE   DC    C'XX  '
         DC    C' QUANTA '
S1Q      DC    C'000000'
         DC    C' ELAPSED-MS '
S1E      DC    C'000000'
SUM1L    EQU   *-SUM1
SUM2     DC    C'PACZ6P LATE>75MS '
S2L      DC    C'000000'
         DC    C' MAXLATE-MS '
S2M      DC    C'000000'
         DC    C' MAXPUT-MS '
S2P      DC    C'000000'
SUM2L    EQU   *-SUM2
SUM3     DC    C'PACZ6P RCOUT '
S3O      DC    C'000000'
         DC    C' RCIN '
S3I      DC    C'000000'
         DC    C' AIDS '
S3A      DC    C'000000'
SUM3L    EQU   *-SUM3
SUM4     DC    C'PACZ6P HOLDS '
S4H      DC    C'000000'
         DC    C' MAXHOLD-MS '
S4M      DC    C'000000'
         DC    C' MAXNOHOLD-MS '
S4N      DC    C'000000'
SUM4L    EQU   *-SUM4
SUM5     DC    C'PACZ6P WRITES '
S5W      DC    C'000000'
         DC    C' SKIPPED '
S5S      DC    C'000000'
SUM5L    EQU   *-SUM5
*        PR2I RECORD (32 BYTES): +0 H QUANTUM, +2 X WRITE FLAG, +3 X
*        TGET RC, +4 H TGET LENGTH (R1 ON RC 0, ELSE X'FFFF'), +6 X AID
*        BYTE (RC 0 WITH DATA), +7 X 0, +8 H AIDCNT BEFORE THE TGET,
*        +10 H AIDCNT AFTER, +12 F MS BEFORE THE TPUT, +16 F MS AFTER
*        (BOTH -1: NO WRITE), +20 F MS BEFORE THE TGET, +24 F MS AFTER,
*        +28 F 0. MS: NOWMS (MILLISECONDS SINCE T0, AS THE SUMMARY).
IINIT    DC    X'0000',X'00',X'FF',X'FFFF',X'00',X'00',X'0000',X'0000'
         DC    F'-1',F'-1',F'-1',F'-1',F'0'
         DC    C' '
ISTRW    DC    CL133' '
IS1      DC    C'PACZ6P S1 '
IS1T     DC    CL67' '
IS1L     EQU   *-IS1
IS2      DC    C'PACZ6P S2 '
IS2T     DC    CL66' '
IS2L     EQU   *-IS2
IDW      DC    CL6' '
IDL      DC    C'PACZ6P I '
IQ       DC    CL3' '
         DC    C' '
IW       DC    CL1' '
         DC    C' '
IR       DC    CL2' '
         DC    C' '
IL       DC    CL3' '
         DC    C' '
IA       DC    CL2' '
         DC    C' '
ICB      DC    CL2' '
         DC    C'>'
ICA      DC    CL2' '
         DC    C' '
IT1      DC    CL6' '
         DC    C' '
IT2      DC    CL6' '
         DC    C' '
IT3      DC    CL6' '
         DC    C' '
IT4      DC    CL6' '
IDLL     EQU   *-IDL
SUMA     DC    C'PACZ6P AID '
SAID     DC    C'XX'
         DC    C' QUANTUM '
SAQ      DC    C'000000'
         DC    C' MS '
SAT      DC    C'000000'
SUMAL    EQU   *-SUMA
INBUF    DS    CL256
AIDTAB   DS    8XL8
         LTORG
ITAB     DS    0F                  PR2I: 133 RECORDS X 32 BYTES
         DS    133XL32
         END
/*
//LKED     EXEC PGM=IEWBLINK,COND=(0,NE),
//             PARM='LIST,AMODE=24,RMODE=24'
//SYSLMOD  DD DSN=@@HLQ@@.PACMAN.Z6PRB.LOAD(PACZ6P),DISP=SHR
//SYSLIN   DD DSN=&&OBJ,DISP=(OLD,PASS)
//SYSPRINT DD SYSOUT=*
