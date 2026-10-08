      * 3270 DATA STREAM BUFFER PASSED FROM PACSCR TO PACPLAT (SEND).
       01  PAC-DS.
           05  DS-LEN                PIC S9(4) COMP.
           05  DS-BUF.
               10  DS-BYTE           PIC X OCCURS 2048 TIMES.
