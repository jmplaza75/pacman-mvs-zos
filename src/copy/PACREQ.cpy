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
      * MVS-RT (D33): PLAY T TURN / R REALTIME. REQ-STEP FOR PACGAME
      * MOVE: B PLAYER + GHOSTS (TURN), P PLAYER ONLY, G GHOSTS ONLY.
      * REQ-AID = THE RAW AID BYTE OF THE LAST TSC INPUT. REQ-VIS = THE
      * ANIMATION FRAME CHOSEN BY PACRT. REQ-TIME = MILLISECONDS (CLOCK
      * OR DEADLINE). REQ-RTSTAT WAIT/RUN/PAUS/FRZ, REQ-RTQ QUANTUM,
      * REQ-RTIN INPUTS OF THE QUANTUM, REQ-RTCUR/REQ-RTREQ/REQ-RTTTL
      * CURRENT AND REQUESTED DIRECTION + TTL, REQ-RTFR FRAME OF THE
      * QUANTUM (BLANK = RTQF, P = PROMPT, F = FULL REDRAW).
           05  REQ-PLAY              PIC X.
           05  REQ-STEP              PIC X.
           05  REQ-AID               PIC X.
           05  REQ-VIS               PIC 9.
           05  REQ-TIME              PIC S9(9) COMP.
           05  REQ-RTSTAT            PIC X(4).
           05  REQ-RTQ               PIC 9(7).
           05  REQ-RTIN              PIC X(8).
           05  REQ-RTCUR             PIC X.
           05  REQ-RTREQ             PIC X.
           05  REQ-RTTTL             PIC 9.
           05  REQ-RTFR              PIC X.
      * MVS-S1 SOUND (PARM COLUMN 20): A AUTO, Y YES, N/BLANK NO. OUT
      * OF PACPLAT INIT: Y ONLY IN TSC (OR THE TSD DRY RUN), ELSE N.
      * REQ-BELL Y: PACDISP ASKS FOR THE 3270 ALARM (WCC BIT X'04') ON
      * THE STREAM IT SENDS NOW (START, DEATH, WIN; PROBE E15).
           05  REQ-SOUND             PIC X.
           05  REQ-BELL              PIC X.
      * MVS-GP1 RULES (PARM COLUMN 21, D36): A ARCADE, ANYTHING ELSE
      * CLASSIC (1.0-MVS). PACGAME RSET SETS ARC-ON FROM IT.
           05  REQ-RULES             PIC X.
      * MVS-GP2 START LEVEL (PARM COLUMNS 22-23, D37): 01-99, ARCADE
      * ONLY. PACMAIN SETS IT (1 OR 2 DIGITS UP TO THE PARM END; ANY
      * OTHER VALUE = 01); PACGAME RSET STARTS THE GAME AT THAT LEVEL.
           05  REQ-START             PIC 99.
