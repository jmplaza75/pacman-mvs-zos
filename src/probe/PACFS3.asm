*        PACFS3 : MVS-G3 PROBE (E6), ONE HYPOTHESIS: AFTER A TPUT
*        FULLSCR
*        SCREEN, A SECOND TPUT THAT CARRIES ONLY WCC + SBA + A FEW
*        CELLS
*        CHANGES JUST THOSE CELLS AND LEAVES THE REST OF THE SCREEN.
*        VARIANT (PARM): 'A' TPUT ASIS, 'N' TPUT NOEDIT (BOTH START
*        WITH
*        THE WCC), 'W' TPUT NOEDIT WITH COMMAND X'F1' (WRITE) BEFORE
*        WCC.
*        THE PROBE ALTERNATES TWO CELLS (ROW 7 COL 10 C/O, COL 20 G/W)
*        EIGHT TIMES, 0.5 S APART, THEN WAITS FOR AN AID.
*        CALL 'PACFS3' USING VAR RC1 RC2 NPART AID
*          VAR X(1) VARIANT   RC1 S9(4) COMP RC OF THE FULLSCR TPUT
*          (4 = NOT A TSO SESSION)   RC2 S9(4) COMP RC OF THE LAST
*          PARTIAL TPUT   NPART S9(4) COMP PARTIAL TPUTS DONE
*          AID X(1) FIRST BYTE OF THE FINAL INBOUND (X'00' = NONE)
PACFS3   CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,6,0(1)
         LA    2,0(2)
         LA    3,0(3)
         LA    4,0(4)
         LA    5,0(5)
         LA    6,0(6)
         SR    7,7
         STH   7,0(4)
         STH   7,0(5)
         MVI   0(6),X'00'
         LA    7,4
         STH   7,0(3)
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         TCLEARQ OUTPUT
         TCLEARQ INPUT
         STFSMODE ON,INITIAL=YES
         STTMPMD ON
         LA    1,SCREEN
         LA    0,SCREENL
         TPUT  (1),(0),FULLSCR
         STH   15,0(3)
         LTR   15,15
         BNZ   BACK
         STIMER WAIT,BINTVL=TWOSEC
         SR    7,7
LOOP     DS    0H
         C     7,=F'8'
         BNL   READIT
         LR    8,7
         N     8,=F'1'
         BNZ   CLOSED
         LA    8,FRMO
         LA    9,FRMOL
         LA    10,FRMOB
         B     CHOSE
CLOSED   DS    0H
         LA    8,FRMC
         LA    9,FRMCL
         LA    10,FRMCB
CHOSE    DS    0H
         CLI   0(2),C'W'
         BE    WRITEV
         LR    8,10                SKIP THE LEADING COMMAND BYTE
         B     SENDIT
WRITEV   DS    0H
         LA    9,1(9)              INCLUDE THE COMMAND BYTE
SENDIT   DS    0H
         LR    1,8
         LR    0,9
         CLI   0(2),C'A'
         BE    USEASIS
         TPUT  (1),(0),NOEDIT
         B     SENT
USEASIS  DS    0H
         TPUT  (1),(0),ASIS
SENT     DS    0H
         STH   15,0(4)
         LTR   15,15
         BNZ   BACK
         LA    7,1(7)
         STH   7,0(5)
         STIMER WAIT,BINTVL=HALFSEC
         B     LOOP
READIT   DS    0H
         SR    10,10
READ     DS    0H
         LA    1,INBUF
         LA    0,256
         TGET  (1),(0),ASIS
         LTR   1,1
         BNZ   GOTDATA
         LA    10,1(10)
         C     10,=F'120'
         BNL   BACK
         STIMER WAIT,BINTVL=HALFSEC
         B     READ
GOTDATA  DS    0H
         MVC   0(1,6),INBUF
BACK     DS    0H
         STTMPMD OFF
         STFSMODE OFF
         STLINENO LINE=1
DONE     DS    0H
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
SAVE     DC    18F'0'
INBUF    DS    CL256
HALFSEC  DC    F'50'
TWOSEC   DC    F'200'
SCREEN   DC    X'C3'
         DC    X'11C1D1'
         DC    X'2842F5'
         DC    C'G3 PROBE E6: PARTIAL TPUT TEST'
         DC    X'11C3F1'
         DC    X'2842F4'
         DC    C'ROW 7: COL 10 C/O AND COL 20 G/W SHOULD ALTERNATE'
         DC    X'11C5C1'
         DC    X'2842F4'
         DC    C'EVERYTHING ELSE MUST STAY: NO BLANKING, NO FLICKER'
         DC    X'11C761'
         DC    X'2842F7'
         DC    C'ROW 7 ->'
         DC    X'11C7E92842F62841F2'
         DC    C'C'
         DC    X'284100'
         DC    X'11C7F32842F22841F2'
         DC    C'G'
         DC    X'284100'
         DC    X'114BD1'
         DC    X'2842F1'
         DC    C'STATIC LINE (BLUE): MUST NEVER CHANGE'
         DC    X'114DF1'
         DC    X'2842F7'
         DC    C'STATIC LINE (WHITE): MUST NEVER CHANGE'
         DC    X'11D7F1'
         DC    X'2842F4'
         DC    C'THE ANIMATION ENDS AFTER 8 STEPS; THEN PRESS ENTER'
         DC    X'280000'
         DC    X'13'
SCREENL  EQU   *-SCREEN
FRMO      DC    X'F1'
FRMOB     DC    X'C3'
         DC    X'11C7E92842F62841F2'
         DC    C'C'
         DC    X'284100'
         DC    X'11C7F32842F22841F2'
         DC    C'G'
         DC    X'284100'
         DC    X'280000'
FRMOL    EQU   *-FRMOB
FRMC      DC    X'F1'
FRMCB     DC    X'C3'
         DC    X'11C7E92842F62841F2'
         DC    C'O'
         DC    X'284100'
         DC    X'11C7F32842F22841F2'
         DC    C'W'
         DC    X'284100'
         DC    X'280000'
FRMCL     EQU   *-FRMCB
         LTORG
         END
