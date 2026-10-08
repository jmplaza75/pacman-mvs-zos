      * DRIVER REQUEST BLOCK: OP CODE IN, INPUT RESULT OUT.
       01  PAC-REQ.
           05  REQ-OP                PIC X(4).
           05  REQ-KIND              PIC X(3).
           05  REQ-DIR               PIC X.
           05  REQ-CHAR              PIC X.
           05  REQ-LEVEL             PIC 9.
           05  REQ-COUNT             PIC 9.
           05  REQ-MODE              PIC X(3).
           05  REQ-TEXT              PIC X(8).
           05  REQ-METRIC            PIC X.
           05  REQ-COLOR             PIC X.
           05  REQ-INKEY             PIC X.
           05  REQ-INTEXT.
               10  REQ-INTEXT-CH     PIC X OCCURS 8 TIMES.
           05  REQ-HILITE            PIC X.
