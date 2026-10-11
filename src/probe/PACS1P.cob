      * PACS1P : MVS-S1 PROBE E15 (SEE PACS1A). 3270 ALARM, ISOLATED
      * FROM PACMAN. NOTHING IS PRINTED BEFORE THE FULL-SCREEN PART.
      * AFTERWARDS: RC, SCREENS ANSWERED AND THE SIX ANSWERS TYPED
      * BY THE USER (SCREENS 1-4 Y/N, SCREENS 5-6 BELLS 0-3).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACS1P.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  P-RC                  PIC S9(4) COMP.
       01  P-ANS                 PIC X(6).
       01  P-NSCR                PIC S9(4) COMP.
       01  RES-LINE.
           05  FILLER            PIC X(7) VALUE 'E15 RC='.
           05  RS-RC             PIC 9(4).
           05  FILLER            PIC X(7) VALUE ' SCRNS='.
           05  RS-NSCR           PIC 9(4).
           05  FILLER            PIC X(5) VALUE ' ANS='.
           05  RS-ANS            PIC X(6).
       PROCEDURE DIVISION.
       MAIN-PARA.
           CALL 'PACS1A' USING P-RC P-ANS P-NSCR.
           MOVE P-RC TO RS-RC.
           MOVE P-NSCR TO RS-NSCR.
           MOVE P-ANS TO RS-ANS.
           DISPLAY RES-LINE.
           DISPLAY 'E15 ANS: 1 CONTROL, 2 SENX, 3 SEND, 4 SENP (Y/N);'.
           DISPLAY 'E15 ANS: 5 BURST, 6 0.5 S APART (BELLS 0-3)'.
           DISPLAY 'E15 PROBE END'.
           STOP RUN.
