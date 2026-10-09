      * PACGEP : MVS-GS GEOMETRY PROBE E12 (ISOLATED FROM PACMAN).
      * 1 SCREEN S0 (TPUT FULLSCR, DEFAULT SIZE), ENTER. 2 READ
      * PARTITION QUERY (TPUT NOEDIT), REPLY: DEFAULT / ALTERNATE SIZE
      * FROM QCODE X'A6', USABLE AREA FROM X'81'. 3 SCREEN S1 (FULLSCR)
      * SHOWS THEM, ENTER (THIS AID ALSO ENDS THE TSO HOLD AFTER THE
      * QUERY, D28). 4 S2: ERASE/WRITE ALTERNATE (X'7E') OF A RULER
      * SCREEN OF EXACTLY THE ALTERNATE SIZE, THEN AFTER 1 S A PARTIAL
      * WRITE (X'F1') ON ITS LAST ROWS; ENTER: THE CURSOR ADDRESS IS
      * DECODED IN THE ALTERNATE GEOMETRY. 5 S3: ERASE/WRITE (X'F5')
      * BACK TO THE DEFAULT SIZE, ENTER. 6 LINE MODE, RESULTS.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACGEP.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  FS-OP                 PIC X(4).
       01  FS-LEN                PIC S9(4) COMP.
       01  FS-RC                 PIC S9(4) COMP.
       01  BUF.
           05  BUF-CH            PIC X OCCURS 4096 TIMES.
       01  QBUF.
           05  Q-CH              PIC X OCCURS 1024 TIMES.
       01  Q-LEN                 PIC 9(4) VALUE 0.
       01  CODE-DATA.
           05  FILLER            PIC X(48) VALUE
               '064193194195196197198199200201074075076077078079'.
           05  FILLER            PIC X(48) VALUE
               '080209210211212213214215216217090091092093094095'.
           05  FILLER            PIC X(48) VALUE
               '096097226227228229230231232233106107108109110111'.
           05  FILLER            PIC X(48) VALUE
               '240241242243244245246247248249122123124125126127'.
       01  CODE-TABLE REDEFINES CODE-DATA.
           05  ADDR-CODE         PIC 999 OCCURS 64 TIMES.
       01  BW.
           05  BW-N              PIC 9(4) COMP.
       01  BW-X REDEFINES BW.
           05  BW-H              PIC X.
           05  BW-L              PIC X.
       01  WS-BV                 PIC 9(4).
       01  WS-LEN                PIC 9(4).
       01  WS-W                  PIC 999.
       01  WS-R                  PIC 99.
       01  WS-C                  PIC 999.
       01  WS-A                  PIC 9(4).
       01  WS-HI                 PIC 99.
       01  WS-LO                 PIC 99.
       01  WS-K                  PIC 9(4).
       01  WS-J                  PIC 9(4).
       01  WS-Q                  PIC 9(4).
       01  WS-M                  PIC 9(4).
       01  WS-D                  PIC 99.
       01  WS-TLEN               PIC 99.
       01  WS-TXT.
           05  TXT-CH            PIC X OCCURS 80 TIMES.
       01  DIG-DATA              PIC X(10) VALUE '0123456789'.
       01  DIG-TABLE REDEFINES DIG-DATA.
           05  DIG               PIC X OCCURS 10 TIMES.
       01  HEX-DATA              PIC X(16) VALUE '0123456789ABCDEF'.
       01  HEX-TABLE REDEFINES HEX-DATA.
           05  HEXDIG            PIC X OCCURS 16 TIMES.
       01  G-DW                  PIC 999 VALUE 0.
       01  G-DH                  PIC 999 VALUE 0.
       01  G-AW                  PIC 999 VALUE 0.
       01  G-AH                  PIC 999 VALUE 0.
       01  G-UW                  PIC 999 VALUE 0.
       01  G-UH                  PIC 999 VALUE 0.
       01  R-EWA                 PIC S9(4) COMP VALUE -1.
       01  R-PART                PIC S9(4) COMP VALUE -1.
       01  R-EW                  PIC S9(4) COMP VALUE -1.
       01  R-AID                 PIC X VALUE LOW-VALUE.
       01  C-ROW                 PIC 999 VALUE 0.
       01  C-COL                 PIC 999 VALUE 0.
       01  E-ROW                 PIC 999 VALUE 0.
       01  E-COL                 PIC 999 VALUE 0.
       01  K-LEN                 PIC 9(4) VALUE 0.
       01  V1                    PIC 999.
       01  V2                    PIC 999.
       01  SZ-TXT.
           05  SZ-W              PIC 999.
           05  FILLER            PIC X VALUE 'X'.
           05  SZ-H              PIC 999.
       01  RES-1.
           05  FILLER            PIC X(9) VALUE 'GEP QLEN='.
           05  RS-QLEN           PIC 9(4).
           05  FILLER            PIC X(5) VALUE ' DEF='.
           05  RS-DEF            PIC X(7).
           05  FILLER            PIC X(5) VALUE ' ALT='.
           05  RS-ALT            PIC X(7).
           05  FILLER            PIC X(8) VALUE ' USABLE='.
           05  RS-USE            PIC X(7).
       01  RES-2.
           05  FILLER            PIC X(11) VALUE 'GEP EWA-RC='.
           05  RS-EWA            PIC 9(4).
           05  FILLER            PIC X(9) VALUE ' PART-RC='.
           05  RS-PART           PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' EW-RC='.
           05  RS-EW             PIC 9(4).
           05  FILLER            PIC X(5) VALUE ' AID='.
           05  RS-AID1           PIC X.
           05  RS-AID2           PIC X.
           05  FILLER            PIC X(8) VALUE ' CURSOR='.
           05  RS-CR             PIC 999.
           05  FILLER            PIC X VALUE ','.
           05  RS-CC             PIC 999.
           05  FILLER            PIC X(8) VALUE ' EXPECT='.
           05  RS-ER             PIC 999.
           05  FILLER            PIC X VALUE ','.
           05  RS-EC             PIC 999.
           05  FILLER            PIC X(6) VALUE ' KLEN='.
           05  RS-KLEN           PIC 9(4).
       01  HEX-LINE.
           05  FILLER            PIC X(4) VALUE 'GEQ '.
           05  HL-OFF            PIC 9(4).
           05  FILLER            PIC X VALUE ' '.
           05  HL-CH             PIC X OCCURS 64 TIMES.
       01  WS-O                  PIC 99.
       01  WS-LIM                PIC S9(4).
       01  WS-LIMR               PIC 9(4).
       01  ALT-TITLE.
           05  FILLER            PIC X(14) VALUE 'E12 ALTERNATE '.
           05  AT-SZ             PIC X(7).
           05  FILLER            PIC X(44) VALUE
               ' VIA ERASE/WRITE ALTERNATE. RULERS: ROWS 2-3'.
       PROCEDURE DIVISION.
       MAIN-PARA.
           MOVE 'FSON' TO FS-OP.
           PERFORM FSC.
           IF FS-RC NOT = 0
               DISPLAY 'GEP RC=0004 NOT A TSO SESSION (NOTHING SENT)'
               STOP RUN.
      * S0: DEFAULT SIZE, FULLSCR (TSO SENDS IT AS A WRITE), ENTER.
           MOVE 80 TO WS-W.
           PERFORM START-FULL.
           MOVE 'E12 GEOMETRY PROBE. STEP 1: ENTER STARTS THE QUERY.'
               TO WS-TXT.
           MOVE 51 TO WS-TLEN.
           MOVE 2 TO WS-R.
           MOVE 2 TO WS-C.
           PERFORM PUT-TEXT-AT.
           MOVE 24 TO WS-R.
           PERFORM PUT-FIELD.
           MOVE 'FULL' TO FS-OP.
           PERFORM SEND-BUF.
           PERFORM GET-KEY.
      * QUERY: READ PARTITION QUERY, REPLY KEPT WHOLE.
           MOVE 0 TO WS-LEN.
           MOVE 243 TO WS-BV.
           PERFORM PUT-B.
           MOVE 0 TO WS-BV.
           PERFORM PUT-B.
           MOVE 5 TO WS-BV.
           PERFORM PUT-B.
           MOVE 1 TO WS-BV.
           PERFORM PUT-B.
           MOVE 255 TO WS-BV.
           PERFORM PUT-B.
           MOVE 2 TO WS-BV.
           PERFORM PUT-B.
           MOVE 'NOED' TO FS-OP.
           PERFORM SEND-BUF.
           MOVE 'GETQ' TO FS-OP.
           PERFORM FSC.
           IF FS-RC = 0 AND FS-LEN > 0
               MOVE FS-LEN TO Q-LEN
               MOVE BUF TO QBUF
               PERFORM PARSE-QRY.
      * S1: WHAT THE TERMINAL ANNOUNCED, ENTER.
           MOVE 80 TO WS-W.
           PERFORM START-FULL.
           MOVE G-DW TO SZ-W.
           MOVE G-DH TO SZ-H.
           MOVE SZ-TXT TO RS-DEF.
           MOVE G-AW TO SZ-W.
           MOVE G-AH TO SZ-H.
           MOVE SZ-TXT TO RS-ALT.
           MOVE G-UW TO SZ-W.
           MOVE G-UH TO SZ-H.
           MOVE SZ-TXT TO RS-USE.
           MOVE Q-LEN TO RS-QLEN.
           MOVE RES-1 TO WS-TXT.
           MOVE 52 TO WS-TLEN.
           MOVE 2 TO WS-R.
           MOVE 2 TO WS-C.
           PERFORM PUT-TEXT-AT.
           MOVE 'STEP 2: ENTER = ERASE/WRITE ALTERNATE (X7E), RULERS.'
               TO WS-TXT.
           MOVE 52 TO WS-TLEN.
           MOVE 4 TO WS-R.
           PERFORM PUT-TEXT-AT.
           MOVE 24 TO WS-R.
           PERFORM PUT-FIELD.
           MOVE 'FULL' TO FS-OP.
           PERFORM SEND-BUF.
           PERFORM GET-KEY.
           IF G-AW = 0 OR G-AH = 0
               GO TO BACK.
      * S2: ERASE/WRITE ALTERNATE, RULER OF EXACTLY AW X AH.
           PERFORM BUILD-ALT.
           MOVE 'NOED' TO FS-OP.
           PERFORM SEND-BUF.
           MOVE FS-RC TO R-EWA.
           MOVE 'WAIT' TO FS-OP.
           PERFORM FSC.
           PERFORM BUILD-PART.
           MOVE 'NOED' TO FS-OP.
           PERFORM SEND-BUF.
           MOVE FS-RC TO R-PART.
           PERFORM GET-KEY.
           MOVE FS-LEN TO K-LEN.
           MOVE BUF-CH (1) TO R-AID.
           IF FS-LEN > 2
               PERFORM DECODE-CURSOR.
      * S3: ERASE/WRITE (X'F5') = BACK TO THE DEFAULT SIZE, ENTER.
           MOVE 80 TO WS-W.
           MOVE 0 TO WS-LEN.
           MOVE 245 TO WS-BV.
           PERFORM PUT-B.
           MOVE 195 TO WS-BV.
           PERFORM PUT-B.
           MOVE 1 TO WS-R.
           MOVE 1 TO WS-C.
           PERFORM PUT-SBA.
           MOVE 29 TO WS-BV.
           PERFORM PUT-B.
           MOVE 96 TO WS-BV.
           PERFORM PUT-B.
           MOVE 'STEP 3: ERASE/WRITE (XF5), DEFAULT SIZE. ENTER ENDS.'
               TO WS-TXT.
           MOVE 52 TO WS-TLEN.
           MOVE 2 TO WS-R.
           MOVE 2 TO WS-C.
           PERFORM PUT-TEXT-AT.
           MOVE 24 TO WS-R.
           PERFORM PUT-FIELD.
           MOVE 'NOED' TO FS-OP.
           PERFORM SEND-BUF.
           MOVE FS-RC TO R-EW.
           PERFORM GET-KEY.
       BACK.
           MOVE 'FSOF' TO FS-OP.
           PERFORM FSC.
           PERFORM REPORT-ALL.
           STOP RUN.
       FSC.
           CALL 'PACFSC' USING FS-OP BUF FS-LEN FS-RC.
       SEND-BUF.
           MOVE WS-LEN TO FS-LEN.
           PERFORM FSC.
       GET-KEY.
           MOVE 'GETK' TO FS-OP.
           PERFORM FSC.
       START-FULL.
      * FULLSCR SCREEN: WCC C3, SBA(1,1), RA TO (1,1) WITH NULLS (CLEAR,
      * AS D25), SF PROTECTED AT (1,1).
           MOVE 0 TO WS-LEN.
           MOVE 195 TO WS-BV.
           PERFORM PUT-B.
           MOVE 1 TO WS-R.
           MOVE 1 TO WS-C.
           PERFORM PUT-SBA.
           MOVE 60 TO WS-BV.
           PERFORM PUT-B.
           MOVE 0 TO WS-A.
           PERFORM PUT-ADDR.
           MOVE 0 TO WS-BV.
           PERFORM PUT-B.
           PERFORM PUT-SBA.
           MOVE 29 TO WS-BV.
           PERFORM PUT-B.
           MOVE 96 TO WS-BV.
           PERFORM PUT-B.
       PUT-FIELD.
      * ROW WS-R: 'ENTER>' AT COLUMN W-12, SF UNPROTECTED AT W-5, THE
      * 1-BYTE FIELD AT W-4 (CURSOR), SF PROTECTED AT W-3.
           COMPUTE WS-C = WS-W - 12.
           MOVE 'ENTER>' TO WS-TXT.
           MOVE 6 TO WS-TLEN.
           PERFORM PUT-TEXT-AT.
           COMPUTE WS-C = WS-W - 5.
           PERFORM PUT-SBA.
           MOVE 29 TO WS-BV.
           PERFORM PUT-B.
           MOVE 64 TO WS-BV.
           PERFORM PUT-B.
           MOVE 19 TO WS-BV.
           PERFORM PUT-B.
           MOVE 64 TO WS-BV.
           PERFORM PUT-B.
           MOVE 29 TO WS-BV.
           PERFORM PUT-B.
           MOVE 96 TO WS-BV.
           PERFORM PUT-B.
       BUILD-ALT.
           MOVE G-AW TO WS-W.
           MOVE 0 TO WS-LEN.
           MOVE 126 TO WS-BV.
           PERFORM PUT-B.
           MOVE 195 TO WS-BV.
           PERFORM PUT-B.
           MOVE 1 TO WS-R.
           MOVE 1 TO WS-C.
           PERFORM PUT-SBA.
           MOVE 29 TO WS-BV.
           PERFORM PUT-B.
           MOVE 96 TO WS-BV.
           PERFORM PUT-B.
           MOVE 245 TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE G-AW TO SZ-W.
           MOVE G-AH TO SZ-H.
           MOVE SZ-TXT TO AT-SZ.
           MOVE ALT-TITLE TO WS-TXT.
           MOVE 65 TO WS-TLEN.
           MOVE 1 TO WS-R.
           MOVE 2 TO WS-C.
           PERFORM PUT-TEXT-AT.
      * ROW 2: UNITS OF EVERY COLUMN; ROW 3: TENS AT EVERY 10TH COLUMN.
           MOVE 246 TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE 2 TO WS-R.
           MOVE 1 TO WS-C.
           PERFORM PUT-SBA.
           PERFORM RULER-1 VARYING WS-K FROM 1 BY 1 UNTIL WS-K > G-AW.
           MOVE 3 TO WS-R.
           MOVE 10 TO WS-C.
           PERFORM RULER-2 VARYING WS-K FROM 10 BY 10
               UNTIL WS-K > G-AW.
      * ROWS 4..H-1: ROW NUMBER AT COLUMNS 1-2, '<' AT THE LAST COLUMN.
           MOVE 245 TO WS-BV.
           PERFORM PUT-COLOUR.
           COMPUTE WS-LIMR = G-AH - 1.
           PERFORM ROW-MARK VARYING WS-J FROM 4 BY 1
               UNTIL WS-J > WS-LIMR.
           MOVE G-AH TO WS-R.
           MOVE 1 TO WS-C.
           MOVE G-AH TO WS-Q.
           PERFORM PUT-NUM2.
           MOVE ' LAST ROW' TO WS-TXT.
           MOVE 9 TO WS-TLEN.
           MOVE 3 TO WS-C.
           PERFORM PUT-TEXT-AT.
           PERFORM PUT-FIELD.
       RULER-1.
           DIVIDE WS-K BY 10 GIVING WS-Q REMAINDER WS-D.
           ADD 1 TO WS-D.
           ADD 1 TO WS-LEN.
           MOVE DIG (WS-D) TO BUF-CH (WS-LEN).
       RULER-2.
           MOVE WS-K TO WS-C.
           MOVE 3 TO WS-R.
           PERFORM PUT-SBA.
           DIVIDE WS-K BY 10 GIVING WS-Q.
           DIVIDE WS-Q BY 10 GIVING WS-M REMAINDER WS-D.
           ADD 1 TO WS-D.
           ADD 1 TO WS-LEN.
           MOVE DIG (WS-D) TO BUF-CH (WS-LEN).
       ROW-MARK.
           MOVE WS-J TO WS-R.
           MOVE 1 TO WS-C.
           MOVE WS-J TO WS-Q.
           PERFORM PUT-NUM2.
           MOVE G-AW TO WS-C.
           PERFORM PUT-SBA.
           MOVE 76 TO WS-BV.
           PERFORM PUT-B.
       PUT-NUM2.
           PERFORM PUT-SBA.
           DIVIDE WS-Q BY 10 GIVING WS-M REMAINDER WS-D.
           ADD 1 TO WS-M.
           ADD 1 TO WS-D.
           ADD 1 TO WS-LEN.
           MOVE DIG (WS-M) TO BUF-CH (WS-LEN).
           ADD 1 TO WS-LEN.
           MOVE DIG (WS-D) TO BUF-CH (WS-LEN).
       BUILD-PART.
      * PARTIAL WRITE (X'F1', WCC C2) ON THE LAST ROWS OF THE ALT SIZE.
           MOVE G-AW TO WS-W.
           MOVE 0 TO WS-LEN.
           MOVE 241 TO WS-BV.
           PERFORM PUT-B.
           MOVE 194 TO WS-BV.
           PERFORM PUT-B.
           MOVE 246 TO WS-BV.
           PERFORM PUT-COLOUR.
           MOVE
               'PARTIAL WRITE (XF1) IN ALTERNATE SIZE: OK IF READABLE'
               TO WS-TXT.
           MOVE 53 TO WS-TLEN.
           COMPUTE WS-R = G-AH - 1.
           MOVE 4 TO WS-C.
           PERFORM PUT-TEXT-AT.
           MOVE 'PART' TO WS-TXT.
           MOVE 4 TO WS-TLEN.
           MOVE G-AH TO WS-R.
           MOVE 14 TO WS-C.
           PERFORM PUT-TEXT-AT.
           COMPUTE WS-C = G-AW - 4.
           MOVE G-AH TO WS-R.
           PERFORM PUT-SBA.
           MOVE 19 TO WS-BV.
           PERFORM PUT-B.
       PUT-TEXT-AT.
           PERFORM PUT-SBA.
           PERFORM PUT-T VARYING WS-K FROM 1 BY 1 UNTIL WS-K > WS-TLEN.
       PUT-T.
           ADD 1 TO WS-LEN.
           MOVE TXT-CH (WS-K) TO BUF-CH (WS-LEN).
       PUT-COLOUR.
           MOVE WS-BV TO WS-Q.
           MOVE 40 TO WS-BV.
           PERFORM PUT-B.
           MOVE 66 TO WS-BV.
           PERFORM PUT-B.
           MOVE WS-Q TO WS-BV.
           PERFORM PUT-B.
       PUT-SBA.
           COMPUTE WS-A = (WS-R - 1) * WS-W + WS-C - 1.
           MOVE 17 TO WS-BV.
           PERFORM PUT-B.
           PERFORM PUT-ADDR.
       PUT-ADDR.
           DIVIDE WS-A BY 64 GIVING WS-HI REMAINDER WS-LO.
           ADD 1 TO WS-HI.
           ADD 1 TO WS-LO.
           MOVE ADDR-CODE (WS-HI) TO WS-BV.
           PERFORM PUT-B.
           MOVE ADDR-CODE (WS-LO) TO WS-BV.
           PERFORM PUT-B.
       PUT-B.
           MOVE WS-BV TO BW-N.
           ADD 1 TO WS-LEN.
           MOVE BW-L TO BUF-CH (WS-LEN).
       PARSE-QRY.
      * FIND X'81A6' (IMPLICIT PARTITION) AND X'8181' (USABLE AREA).
           COMPUTE WS-LIM = Q-LEN - 12.
           PERFORM FIND-QC VARYING WS-K FROM 1 BY 1
               UNTIL WS-K > WS-LIM.
       FIND-QC.
           MOVE Q-CH (WS-K) TO BW-L.
           MOVE LOW-VALUE TO BW-H.
           MOVE BW-N TO V1.
           COMPUTE WS-J = WS-K + 1.
           MOVE Q-CH (WS-J) TO BW-L.
           MOVE BW-N TO V2.
           IF V1 = 129 AND V2 = 166
               PERFORM GET-A6.
           IF V1 = 129 AND V2 = 129 AND G-UW = 0
               PERFORM GET-81.
           MOVE 0 TO WS-D.
       GET-A6.
      * 81 A6 00 00 0B 01 00 DW(2) DH(2) AW(2) AH(2)
           COMPUTE WS-J = WS-K + 7.
           PERFORM GET-16.
           MOVE WS-Q TO G-DW.
           COMPUTE WS-J = WS-K + 9.
           PERFORM GET-16.
           MOVE WS-Q TO G-DH.
           COMPUTE WS-J = WS-K + 11.
           PERFORM GET-16.
           MOVE WS-Q TO G-AW.
           COMPUTE WS-J = WS-K + 13.
           PERFORM GET-16.
           MOVE WS-Q TO G-AH.
       GET-81.
      * 81 81 FLAGS FLAGS W(2) H(2)
           COMPUTE WS-J = WS-K + 4.
           PERFORM GET-16.
           MOVE WS-Q TO G-UW.
           COMPUTE WS-J = WS-K + 6.
           PERFORM GET-16.
           MOVE WS-Q TO G-UH.
       GET-16.
           MOVE Q-CH (WS-J) TO BW-H.
           COMPUTE WS-M = WS-J + 1.
           MOVE Q-CH (WS-M) TO BW-L.
           MOVE BW-N TO WS-Q.
       DECODE-CURSOR.
      * INBOUND: AID, CURSOR ADDRESS (12-BIT CODES OR 14-BIT BINARY).
           MOVE LOW-VALUE TO BW-H.
           MOVE BUF-CH (2) TO BW-L.
           MOVE BW-N TO V1.
           MOVE BUF-CH (3) TO BW-L.
           MOVE BW-N TO V2.
           IF V1 < 64
               COMPUTE WS-A = V1 * 256 + V2
           ELSE
               DIVIDE V1 BY 64 GIVING WS-Q REMAINDER WS-M
               DIVIDE V2 BY 64 GIVING WS-Q REMAINDER WS-J
               COMPUTE WS-A = WS-M * 64 + WS-J.
           DIVIDE WS-A BY G-AW GIVING C-ROW REMAINDER C-COL.
           ADD 1 TO C-ROW.
           ADD 1 TO C-COL.
           MOVE G-AH TO E-ROW.
           COMPUTE E-COL = G-AW - 4.
       REPORT-ALL.
           MOVE G-DW TO SZ-W.
           MOVE G-DH TO SZ-H.
           MOVE SZ-TXT TO RS-DEF.
           MOVE G-AW TO SZ-W.
           MOVE G-AH TO SZ-H.
           MOVE SZ-TXT TO RS-ALT.
           MOVE G-UW TO SZ-W.
           MOVE G-UH TO SZ-H.
           MOVE SZ-TXT TO RS-USE.
           MOVE Q-LEN TO RS-QLEN.
           DISPLAY RES-1.
           MOVE 0 TO RS-EWA RS-PART RS-EW.
           IF R-EWA NOT < 0
               MOVE R-EWA TO RS-EWA.
           IF R-PART NOT < 0
               MOVE R-PART TO RS-PART.
           IF R-EW NOT < 0
               MOVE R-EW TO RS-EW.
           MOVE LOW-VALUE TO BW-H.
           MOVE R-AID TO BW-L.
           DIVIDE BW-N BY 16 GIVING WS-Q REMAINDER WS-M.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-M.
           MOVE HEXDIG (WS-Q) TO RS-AID1.
           MOVE HEXDIG (WS-M) TO RS-AID2.
           MOVE C-ROW TO RS-CR.
           MOVE C-COL TO RS-CC.
           MOVE E-ROW TO RS-ER.
           MOVE E-COL TO RS-EC.
           MOVE K-LEN TO RS-KLEN.
           DISPLAY RES-2.
           MOVE 1 TO WS-K.
           PERFORM HEX-ROW UNTIL WS-K > Q-LEN.
           DISPLAY 'GEP PROBE END'.
       HEX-ROW.
           MOVE SPACES TO HEX-LINE.
           MOVE 'GEQ ' TO HEX-LINE.
           COMPUTE HL-OFF = WS-K - 1.
           MOVE 0 TO WS-O.
           MOVE 0 TO WS-J.
           PERFORM HEX-BYTE UNTIL WS-J = 32 OR WS-K > Q-LEN.
           DISPLAY HEX-LINE.
       HEX-BYTE.
           MOVE LOW-VALUE TO BW-H.
           MOVE Q-CH (WS-K) TO BW-L.
           DIVIDE BW-N BY 16 GIVING WS-Q REMAINDER WS-M.
           ADD 1 TO WS-Q.
           ADD 1 TO WS-M.
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-Q) TO HL-CH (WS-O).
           ADD 1 TO WS-O.
           MOVE HEXDIG (WS-M) TO HL-CH (WS-O).
           ADD 1 TO WS-K.
           ADD 1 TO WS-J.
