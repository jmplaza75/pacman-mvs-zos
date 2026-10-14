*        ZHELLOA : ZOS-1 TOOLCHAIN PROBE (NOT PART OF PACMAN).
*        CALL 'ZHELLOA' USING ZOUT FROM ZHELLOC. ZOUT = 6 FULLWORDS:
*          +0  TAM CONDITION CODE: 0 = AMODE 24, 1 = AMODE 31, 3 = 64
*          +4  BSM 2,0 READ-BACK: 1 IF BIT 0 OF R2 BECAME 1 (AMODE
*              31), 0 OTHERWISE (AMODE 24)
*          +8  ADDRESS OF ZOUT (THE FIRST PARAMETER), BIT 0 CLEARED
*          +12 ADDRESS OF THIS CSECT (ENTRY ADDRESS FROM R15)
*          +16 ADDRESS OF THE CALLER'S SAVE AREA (R13 ON ENTRY)
*          +20 RETURN CODE 0
*        TAM ONLY SETS THE CONDITION CODE. BSM 2,0 HAS A ZERO SECOND
*        OPERAND: IT ONLY COPIES THE CURRENT ADDRESSING-MODE BIT INTO
*        BIT 0 OF R2; IT DOES NOT BRANCH AND DOES NOT CHANGE THE MODE.
*        THE TWO READINGS ARE INDEPENDENT AND MUST AGREE.
ZHELLOA  CSECT
ZHELLOA  AMODE ANY
ZHELLOA  RMODE 24
         STM   14,12,12(13)
         LR    12,15
         USING ZHELLOA,12
         LR    11,13               CALLER'S SAVE AREA
         LA    14,SAVE
         ST    13,4(14)            BACK CHAIN
         ST    14,8(13)            FORWARD CHAIN
         LR    13,14
         L     4,0(1)              ADDRESS OF ZOUT
         N     4,=X'7FFFFFFF'      DROP THE END-OF-LIST BIT
*        READING 1: TAM
         SR    5,5
         TAM
         BC    8,TAMX              CC 0: AMODE 24, R5 = 0
         LA    5,1
         BC    4,TAMX              CC 1: AMODE 31
         LA    5,3                 CC 3: AMODE 64
TAMX     ST    5,0(4)
*        READING 2: BSM 2,0 (NO BRANCH, NO MODE CHANGE)
         SR    2,2
         BSM   2,0
         SR    6,6
         LTR   2,2
         BNM   BSMX                BIT 0 OFF: AMODE 24
         LA    6,1
BSMX     ST    6,4(4)
*        ADDRESSES
         ST    4,8(4)
         LR    7,12
         N     7,=X'7FFFFFFF'
         ST    7,12(4)
         LR    7,11
         N     7,=X'7FFFFFFF'
         ST    7,16(4)
         SR    15,15
         ST    15,20(4)
         L     13,4(13)
         L     14,12(13)
         LM    0,12,20(13)
         SR    15,15
         BR    14
SAVE     DS    18F
         LTORG
         END   ZHELLOA
