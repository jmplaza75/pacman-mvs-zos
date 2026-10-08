#!/usr/bin/env python3
"""Generates src/probe/PACFSA.asm (MVS-G5 probe E10: Programmed Symbols, isolated from PACMAN).
Purpose: establish the graphics ceiling of TK4-/MVS 3.8J + TSO + c3270 for host-defined symbols, not to force PS to work.
Order (the game's validated order, G1-G4 lessons):
 1. Read Partition Query (TPUT NOEDIT) and its reply (AID X'88', returned whole: QCode X'85' load-PS bytes re-checked);
 2. screen 1 (TPUT FULLSCR, WCC C3 restores the keyboard locked by the reply); the user presses ENTER - that first AID
    also releases the NOEDIT hold TSO applies after a Query Reply (D28), so step 3 is not held;
 3. ONE minimum Load Programmed Symbols structured field (WSF X'F3', SF ID X'06') by TPUT NOEDIT, its TPUT RC kept;
 4. a 3-second inbound window (TGET ASIS,NOWAIT every 0.5 s) records anything the terminal sends back (in plain TN3270
    x3270-family emulators discard the result of a rejected structured field: nothing is expected);
 5. screen 2: the loaded code point selected with SA X'43' + the LCID just loaded, the same bytes in the base set and,
    as positive control of the SA path, with SA X'43' X'F1' (APL, proven in E9); ENTER ends, PA2 redraws;
 6. line mode restored (STTMPMD/STFSMODE OFF, STLINENO LINE=1).
Load PS field (non-extended form, our reading of IBM GA23-0059 "Load Programmed Symbols"; it cannot be verified here
because no PS device is available): L(2) X'06' FLAGS=X'00' LCID=X'C1' CHAR=X'C1' TYPE=X'01', then one 9x12 symbol as
12 rows of 2 bytes (9 dots left-justified). x3270 sf.c dispatches on the SF ID after checking only the length, so the
"minimum valid" operation for c3270 is a structurally valid field (exact length, ID X'06'); its content cannot change
the outcome there.
Usage: python3 tools/gen_probe_e10.py   (writes src/probe/PACFSA.asm, prints the Load PS field in hex)"""
from pathlib import Path

R = Path(__file__).resolve().parent.parent
CODES = [0x40, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F,
         0x50, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E, 0x5F,
         0x60, 0x61, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F,
         0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F]
SA, COLOR, CSET, APL = 0x28, 0x42, 0x43, 0xF1
GREEN, TURQ, YELLOW, WHITE, RED = 0xF4, 0xF5, 0xF6, 0xF7, 0xF2
LCID, CHAR = 0xC1, 0xC1
SAMPLE = [0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8]

# Pac-Man facing right, 9 x 12 dots ('#' = on)
GLYPH = ['...###...', '.#######.', '#######..', '######...', '#####....', '####.....',
         '#####....', '######...', '#######..', '.#######.', '...###...', '.........']


def lps_field():
    data = bytearray()
    for row in GLYPH:
        v = int(row.replace('#', '1').replace('.', '0'), 2) << 7     # 9 dots left-justified in 16 bits
        data.extend(v.to_bytes(2, 'big'))
    body = bytes([0x06, 0x00, LCID, CHAR, 0x01]) + bytes(data)
    return bytes([0xF3]) + (len(body) + 2).to_bytes(2, 'big') + body


def screen(steps):
    ds = bytearray()

    def sba(r, c):
        a = (r - 1) * 80 + (c - 1)
        ds.extend([0x11, CODES[a >> 6], CODES[a & 63]])

    def col(v):
        ds.extend([SA, COLOR, v])

    def txt(s):
        ds.extend(s.encode('cp037'))

    def sample(cs):
        if cs is not None:
            ds.extend([SA, CSET, cs])
        for k, v in enumerate(SAMPLE):
            ds.append(v)
            if k < len(SAMPLE) - 1:
                ds.append(0x40)
        if cs is not None:
            ds.extend([SA, CSET, 0x00])

    ds.append(0xC3)                                         # WCC: reset, keyboard restore, reset MDT
    sba(1, 1); ds.extend([0x3C, 0x40, 0x40, 0x00])          # clear prefix (D25)
    sba(1, 2); col(TURQ); txt('PACMAN G5 PROBE E10 - PROGRAMMED SYMBOLS (ISOLATED, NOT THE GAME)')
    if steps == 1:
        sba(3, 2); col(GREEN); txt('STEP 1 DONE: READ PARTITION QUERY SENT, REPLY READ.')
        sba(5, 2); txt('NEXT: ONE LOAD PROGRAMMED SYMBOLS FIELD (WSF, SF ID 06) FOR SET C1, CODE C1,')
        sba(6, 2); txt('THEN A 3 SECOND WINDOW FOR ANY TERMINAL RESPONSE, THEN THE RESULT SCREEN.')
        sba(23, 2); col(WHITE); txt('PRESS ENTER TO SEND LOAD PS. PA2 = REDRAW')
    else:
        sba(3, 2); col(GREEN); txt('STEP 2 DONE: LOAD PS SENT FOR SET C1 (ONE PACMAN SYMBOL AT CODE C1).')
        sba(5, 2); txt('A) SA 43 C1 (THE SET JUST LOADED), BYTES C1-C8:')
        sba(5, 54); col(YELLOW); sample(LCID)
        sba(7, 2); col(GREEN); txt('B) SAME BYTES, BASE SET (REFERENCE):')
        sba(7, 54); col(YELLOW); sample(None)
        sba(9, 2); col(GREEN); txt('C) SAME BYTES, SA 43 F1 (APL, POSITIVE CONTROL):')
        sba(9, 54); col(YELLOW); sample(APL)
        sba(12, 2); col(GREEN); txt('IF PROGRAMMED SYMBOLS WORKED, THE FIRST CELL OF A) WOULD BE A PACMAN')
        sba(13, 2); txt('SHAPE (THE HOST-DEFINED SYMBOL) AND THE REST OF A) BLANK OR UNDEFINED.')
        sba(14, 2); txt('A) EQUAL TO B) = SET C1 NOT LOADED (TERMINAL FALLS BACK TO THE BASE SET).')
        sba(15, 2); txt('C) DIFFERENT FROM B) = THE SA 43 PATH ITSELF WORKS.')
        sba(23, 2); col(WHITE); txt('NOTE ROWS A, B, C; THEN ENTER TO END. PA2 = REDRAW')
    ds.extend([SA, 0x00, 0x00]); sba(24, 2); ds.append(0x13)  # reset attributes, insert cursor
    return bytes(ds)


def dc_lines(label, data):
    out, first = [], True
    for k in range(0, len(data), 24):
        out.append(f"{label if first else '':<8} DC    X'{data[k:k + 24].hex().upper()}'")
        first = False
    return out


HEAD = """*        PACFSA : MVS-G5 PROBE E10 (GENERATED BY GEN_PROBE_E10.PY,
*        DO NOT EDIT). PROGRAMMED SYMBOLS, ISOLATED FROM PACMAN:
*        QUERY + REPLY, SCREEN 1, ENTER, ONE LOAD PS FIELD (WSF X'06')
*        BY TPUT NOEDIT, 3 S INBOUND WINDOW, SCREEN 2 (SA X'43' TO THE
*        LOADED SET, BASE AND APL CONTROLS), ENTER, LINE MODE.
*        CALL 'PACFSA' USING QBUF QLEN RC AID NSCR LRC IBUF ILEN
*          QBUF X(1024) QUERY REPLY, QLEN S9(4) COMP (0 = NO REPLY)
*          RC S9(4) COMP LAST TPUT/TGET RC (4 = NOT A TSO SESSION)
*          AID X(1) FINAL KEY, NSCR S9(4) COMP SCREENS SENT
*          LRC S9(4) COMP TPUT RC OF THE LOAD PS (-1 = NOT SENT)
*          IBUF X(256) INBOUND IN THE WINDOW, ILEN S9(4) COMP ITS
*          LENGTH (0 = NOTHING CAME BACK)
PACFSA   CSECT
         STM   14,12,12(13)
         BALR  12,0
         USING *,12,11
         LA    11,2048(12)
         LA    11,2048(11)
         ST    13,SAVE+4
         LA    14,SAVE
         ST    14,8(13)
         LR    13,14
         LM    2,9,0(1)
         LA    2,0(2)
         LA    3,0(3)
         LA    4,0(4)
         LA    5,0(5)
         LA    6,0(6)
         LA    7,0(7)
         LA    8,0(8)
         LA    9,0(9)
         SR    14,14
         STH   14,0(3)
         STH   14,0(6)
         STH   14,0(9)
         BCTR  14,0
         STH   14,0(7)             LRC = -1: LOAD PS NOT SENT
         MVI   0(5),X'00'
         LA    14,4
         STH   14,0(4)
         L     1,X'224'            PSAAOLD: CURRENT ASCB
         L     1,X'3C'(1)          ASCBTSB: ZERO UNLESS TSO USER
         LTR   1,1
         BZ    DONE
         TCLEARQ OUTPUT
         TCLEARQ INPUT
         STFSMODE ON,INITIAL=YES
         STTMPMD ON
         LA    1,QUERY
         L     0,=A(QUERYL)
         TPUT  (1),(0),NOEDIT
         STH   15,0(4)
         LTR   15,15
         BNZ   BACK
         SR    10,10               EMPTY READS
QREAD    DS    0H
         LR    1,2
         L     0,=F'1024'
         TGET  (1),(0),ASIS
         STH   15,0(4)
         LTR   1,1
         BNZ   QGOT
         LA    10,1(10)
         C     10,=F'10'
         BNL   SHOW1               NO REPLY WITHIN 5 S
         STIMER WAIT,BINTVL=HALFSEC
         B     QREAD
QGOT     DS    0H
         CLI   0(2),X'88'
         BNE   NOTQRY
         STH   1,0(3)
         B     SHOW1
NOTQRY   DS    0H
         MVC   0(1,5),0(2)         A KEY CAME FIRST: NO REPLY
         CLI   0(2),X'6E'
         BNE   BACK
SHOW1    DS    0H                  SCREEN 1 (WCC C3 RESTORES THE
         LA    1,SCR1              KEYBOARD LOCKED BY THE REPLY)
         L     0,=A(SCR1L)
         BAL   10,SENDSCR
         LTR   15,15
         BNZ   BACK
         BAL   10,GETKEY
         LTR   15,15
         BNZ   BACK
         CLI   INBUF,X'6E'         PA2: REDRAW SCREEN 1
         BE    SHOW1
         LA    1,LPS               ONE LOAD PROGRAMMED SYMBOLS FIELD
         L     0,=A(LPSL)
         TPUT  (1),(0),NOEDIT
         STH   15,0(7)
         STH   15,0(4)
         SR    10,10               INBOUND WINDOW: 6 X 0.5 S
IWAIT    DS    0H
         LR    1,8
         L     0,=F'256'
         TGET  (1),(0),ASIS,NOWAIT
         STH   15,0(4)
         LTR   15,15
         BNZ   INONE               RC 4: NOTHING, ELSE ERROR (KEPT)
         STH   1,0(9)              SOMETHING CAME BACK: KEEP IT
         B     SHOW2
INONE    DS    0H
         C     15,=F'4'
         BNE   SHOW2
         LA    10,1(10)
         C     10,=F'6'
         BNL   SHOW2
         STIMER WAIT,BINTVL=HALFSEC
         B     IWAIT
SHOW2    DS    0H
         LA    1,SCR2
         L     0,=A(SCR2L)
         BAL   10,SENDSCR
         LTR   15,15
         BNZ   BACK
         BAL   10,GETKEY
         LTR   15,15
         BNZ   BACK
         CLI   INBUF,X'6E'         PA2: REDRAW SCREEN 2
         BE    SHOW2
         B     BACK
SENDSCR  DS    0H                  R1/R0 = SCREEN, R15 = TPUT RC
         LH    14,0(6)
         LA    14,1(14)
         STH   14,0(6)
         TPUT  (1),(0),FULLSCR
         STH   15,0(4)
         BR    10
GETKEY   DS    0H                  WAIT UP TO 5 MINUTES FOR A KEY
         SR    14,14
         ST    14,KCOUNT
KREAD    DS    0H
         LA    1,INBUF
         L     0,=F'256'
         TGET  (1),(0),ASIS
         STH   15,0(4)
         LTR   1,1
         BNZ   KGOT
         L     14,KCOUNT
         LA    14,1(14)
         ST    14,KCOUNT
         C     14,=F'600'
         BNL   KNONE
         STIMER WAIT,BINTVL=HALFSEC
         B     KREAD
KGOT     DS    0H
         MVC   0(1,5),INBUF
         SR    15,15
         BR    10
KNONE    DS    0H
         LA    15,8
         BR    10
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
KCOUNT   DC    F'0'
HALFSEC  DC    F'50'
QUERY    DC    X'F3000501FF02'
QUERYL   EQU   *-QUERY
         LTORG
INBUF    DS    CL256
"""

lps = lps_field()
s1, s2 = screen(1), screen(2)
lines = HEAD.rstrip('\n').split('\n')
lines += dc_lines('LPS', lps) + ['LPSL     EQU   *-LPS']
lines += dc_lines('SCR1', s1) + ['SCR1L    EQU   *-SCR1']
lines += dc_lines('SCR2', s2) + ['SCR2L    EQU   *-SCR2', '         END']
(R / 'src/probe/PACFSA.asm').write_text('\n'.join(lines) + '\n', encoding='ascii')
print(f'src/probe/PACFSA.asm written: Load PS {len(lps)} bytes, screen 1 {len(s1)}, screen 2 {len(s2)}')
print('Load PS field:', lps.hex().upper())
