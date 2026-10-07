*        PACTSO : TSO LINE-MODE SCREEN SERVICE FOR PACPLAT (MVS-8).
*        CALL 'PACTSO' USING OP RC
*          OP X(4)  'CLS ' = NEXT LINE-MODE OUTPUT STARTS AT LINE 1
*                   OF A FRESH SCREEN (STLINENO LINE=1), SO A FRAME
*                   NEVER OVERFLOWS INTO THE TSO '***' PAGING PROMPT.
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
         CLC   0(4,2),=C'CLS '
         BNE   DONE
         LA    4,4
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         STLINENO LINE=1
         LR    4,15
DONE     DS    0H
         STH   4,0(3)
         L     13,SAVE+4
         LM    14,12,12(13)
         SR    15,15
         BR    14
SAVE     DC    18F'0'
         LTORG
         END
