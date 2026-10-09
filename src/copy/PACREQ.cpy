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
           05  REQ-ANIM              PIC X.
           05  REQ-REDRAW            PIC X.
           05  REQ-SENDST            PIC X.
      * MVS-G4 GLYPH PROFILE: A AUTO, G GRAPHIC (GE), B BASE, C CLASSIC.
           05  REQ-GLYPHS            PIC X.
      * MVS-GS SCALE: A AUTO, 4 (4X2), 3 (3X2), N NO; T = 4X2 WITH A
      * 1000-BYTE LIMIT (TEST OF THE SIZE GUARD). RESOLVED: 4/3/T/N.
           05  REQ-SCALE             PIC X.
      * MVS-GS CANVAS: A AUTO (ALTERNATE SIZE FROM THE QUERY REPLY),
      * D OR BLANK DEFAULT 80 X 24; TSD ONLY: W X T M U L = SIMULATED.
      * REQ-CW / REQ-CH = THE RESOLVED BUFFER SIZE (0 = 80 X 24).
           05  REQ-CANVAS            PIC X.
           05  REQ-CW                PIC 999.
           05  REQ-CH                PIC 999.
