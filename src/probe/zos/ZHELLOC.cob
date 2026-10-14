       IDENTIFICATION DIVISION.
       PROGRAM-ID. ZHELLOC.
      * ZOS-1 TOOLCHAIN PROBE (NOT PART OF PACMAN): PARM ECHO, THE
      * ADDRESSING MODE AND ADDRESSES REPORTED BY ZHELLOA, AND SYSOUT
      * LINES OF 80 AND 130 CHARACTERS PLUS THE SOURCE CHARACTER SET.
      * DOCS/ZOS-MIGRATION-PLAN.MD SEC. 6 (ZOS-1) AND SEC. 9 (RISK 1).
       ENVIRONMENT DIVISION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  Z-OUT.
           05  Z-TAM                 PIC S9(9) COMP.
           05  Z-BSM                 PIC S9(9) COMP.
           05  Z-PARM1               PIC S9(9) COMP.
           05  Z-CSECT               PIC S9(9) COMP.
           05  Z-SAVEA               PIC S9(9) COMP.
           05  Z-RC                  PIC S9(9) COMP.
       01  Z-NUM                     PIC 9(10).
       01  Z-LINE.
           05  FILLER                PIC X(3) VALUE 'ZH '.
           05  Z-KEY                 PIC X(6).
           05  FILLER                PIC X VALUE '='.
           05  Z-VAL                 PIC X(10).
           05  FILLER                PIC X VALUE ' '.
           05  Z-WHERE               PIC X(5).
       01  WS-I                      PIC 999.
       01  WS-OUT.
           05  WS-OUT-CH             PIC X OCCURS 100 TIMES.
       01  WS-L80.
           05  FILLER                PIC X(5) VALUE 'ZH80 '.
           05  WS-L80-T              PIC X(75).
       01  WS-L130.
           05  FILLER                PIC X(6) VALUE 'ZH130 '.
           05  WS-L130-T             PIC X(124).
       01  WS-CHARS.
           05  FILLER                PIC X(32)
               VALUE ' !"#$%&''()*+,-./0123456789:<=>?@'.
           05  FILLER                PIC X(26)
               VALUE 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.
           05  FILLER                PIC X(9) VALUE 'cdelopqru'.
       LINKAGE SECTION.
       01  PARM-AREA.
           05  PARM-LEN              PIC S9(4) COMP.
           05  PARM-TEXT.
               10  PARM-CH           PIC X OCCURS 100 TIMES.
       PROCEDURE DIVISION USING PARM-AREA.
       MAIN-PARA.
           MOVE SPACES TO WS-OUT.
           MOVE PARM-LEN TO WS-I.
           DISPLAY 'ZH PARMLEN=' WS-I.
           PERFORM COPY-CH VARYING WS-I FROM 1 BY 1
               UNTIL WS-I > PARM-LEN OR WS-I > 100.
           DISPLAY 'ZH PARM=' WS-OUT.
           CALL 'ZHELLOA' USING Z-OUT.
           MOVE 'TAM   ' TO Z-KEY.
           MOVE Z-TAM TO Z-NUM.
           PERFORM SHOW-ONE THRU SHOW-ONE-EXIT.
           MOVE 'BSM   ' TO Z-KEY.
           MOVE Z-BSM TO Z-NUM.
           PERFORM SHOW-ONE THRU SHOW-ONE-EXIT.
           MOVE 'PARM1 ' TO Z-KEY.
           MOVE Z-PARM1 TO Z-NUM.
           PERFORM SHOW-ONE THRU SHOW-ONE-EXIT.
           MOVE 'CSECT ' TO Z-KEY.
           MOVE Z-CSECT TO Z-NUM.
           PERFORM SHOW-ONE THRU SHOW-ONE-EXIT.
           MOVE 'SAVEA ' TO Z-KEY.
           MOVE Z-SAVEA TO Z-NUM.
           PERFORM SHOW-ONE THRU SHOW-ONE-EXIT.
           MOVE 'RC    ' TO Z-KEY.
           MOVE Z-RC TO Z-NUM.
           PERFORM SHOW-ONE THRU SHOW-ONE-EXIT.
           MOVE ALL '0123456789' TO WS-L80-T.
           DISPLAY WS-L80.
           MOVE ALL '0123456789' TO WS-L130-T.
           DISPLAY WS-L130.
           DISPLAY 'ZH CHARS=' WS-CHARS.
           DISPLAY 'ZH END'.
           GOBACK.
       COPY-CH.
           MOVE PARM-CH (WS-I) TO WS-OUT-CH (WS-I).
       SHOW-ONE.
           MOVE Z-NUM TO Z-VAL.
           MOVE SPACES TO Z-WHERE.
           IF Z-KEY = 'TAM   ' OR Z-KEY = 'BSM   ' OR Z-KEY = 'RC    '
               GO TO SHOW-ONE-PRINT.
           IF Z-NUM < 16777216
               MOVE 'BELOW' TO Z-WHERE
           ELSE
               MOVE 'ABOVE' TO Z-WHERE.
       SHOW-ONE-PRINT.
           DISPLAY Z-LINE.
       SHOW-ONE-EXIT.
           EXIT.
