# PACZ4INS - first promotion (ZOS-4), review package (not submitted)

Deck of record jcl/zos/PACZ4INS.jcl (tools/zowe/zos_target.py z4ins_deck), rendered for Z00000: SHA-256
4a679956333e4891cfad8f0df1bdd8151be818a4118fc233888e9bd63546469a, 98 lines. Checks: tools/zowe/zos_ins_check.py
(--gate / SPOOLDIR / --clist); CLIST install: tools/zowe/zos_clist_install.py; tests/test_zos_tools.py section 17.

## Sequence
0. Read-only gate (`zos_ins_check.py --gate`, PASS 2026-10-15): LOAD(PACMAIN) absent; Z00000.PACMAN.CEEOPTS absent;
   CLIST(PACSRCT) absent; CLIST(PACMAN) present and = the frozen raw template src/clist/PACMAN.clist (= 2.0-mvs-max;
   IBM-037, 75 fixed 80-byte records, binary download); PACZ2D attributes AC 00, AMODE 24, RMODE 24, RN RU, size
   000200B0. Rerun immediately before the submission; any FAIL -> STOP.
1-3, 5. One job PACZ4INS (every step after the first COND=(0,NE)):
   - SAVETPL IEBGENER CLIST(PACMAN) -> CLIST(PACSRCT) (record copy; PACSRCT is never written again);
   - CEEOPT IEBGENER -> Z00000.PACMAN.CEEOPTS (new, PS FB 80/80, one record `ALL31(OFF),STACK(,,BELOW)`);
   - PROM1 IEBCOPY LOAD(PACZ2D) -> temporary PDSE &&PROMO as PACMAIN (SELECT rename; the program object is copied,
     not rebound); PROM2 IEBCOPY &&PROMO(PACMAIN) -> LOAD(PACMAIN) (no replace). &&PROMO is a job temporary (PASS),
     released by the system at job end - no DELETE disposition anywhere;
   - RUN1, TSO2: the REL20 oracle 307 steps verbatim with PGM=PACMAIN (identical to the accepted ZOS-2 steps apart from
     the program name): RUN1 = batch CLASSIC run 1 (160 lines), TSO2 = TSO line-mode DIE1 (353 lines, the live
     acceptance game). Profile A CEEOPTS DD, STEPLIB Z00000.PACMAN.LOAD.
4. Read-only after the job (`zos_ins_check.py SPOOLDIR`): z/OSMF member attributes of PACMAIN = PACZ2D's (AC 00, AMODE
   24, RMODE 24, RN RU = RENT REUS, same size 000200B0, in the PDSE program library); PACZ2D unchanged; PACSRCT = the
   template; CEEOPTS = one record; CLIST(PACMAN) still the template.
6. Only if 0-5 passed: `zos_clist_install.py SPOOLDIR` re-checks 1-5, uploads build/zos/PACMAN.zos.clist (src/zos
   rendered for Z00000.PACMAN, lines <= 72) with IBM-037 into CLIST(PACMAN).
7. It downloads CLIST(PACMAN) in binary and requires it = the rendered file encoded IBM-037, fixed 80 (ZOS-1 method),
   then `zos_ins_check.py --clist`: CLIST(PACMAN) = rendered, CLIST(PACSRCT) still the template.

## Expected results
| Step | Program | RC | Output | Check |
|---|---|---|---|---|
| SAVETPL | IEBGENER | 0000 | SYSPRINT | PACSRCT = template (binary) |
| CEEOPT | IEBGENER | 0000 | SYSPRINT | CEEOPTS PS FB 80/80, one record |
| PROM1 | IEBCOPY | 0000 | SYSPRINT: PACZ2D copied as PACMAIN | copy message |
| PROM2 | IEBCOPY | 0000 | SYSPRINT: PACMAIN copied | copy message; attributes = PACZ2D |
| RUN1 | PACMAIN | 0000 | SYSOUT 160 lines | = oracle 307 RUN1 block, = test_mvs8 model |
| TSO2 | PACMAIN | 0000 | SYSOUT 353 lines | = oracle 307 TSO2 block (DIE1), = test_mvs8 TSO model |
Spool estimate: ~ 750 lines (513 program lines + IEBGENER / IEBCOPY listings + JES).

## Pre / post state
| Object | Before | After the job | After step 6-7 |
|---|---|---|---|
| CLIST(PACMAN) | raw template (75 records) | raw template | rendered z/OS CLIST (Z2 included) |
| CLIST(PACSRCT) | absent | = raw template | = raw template (untouched) |
| Z00000.PACMAN.CEEOPTS | absent | PS FB 80/80, `ALL31(OFF),STACK(,,BELOW)` | same |
| LOAD(PACMAIN) | absent | copy of PACZ2D (attributes equal) | same |
| LOAD(PACZ2D) | accepted ZOS-2 module | unchanged | unchanged |

## STOP conditions
Gate FAIL; any COND CODE other than 0000; ABEND / CEE / IEA995 / $HASP375 / S722; a spool DD other than the listed
ones; JESYSMSG naming a Z00000 dataset other than CLIST, CEEOPTS, LOAD (and the job's own); an IEBCOPY copy message
missing; a smoke run not = its oracle block or model; PACMAIN attributes not = PACZ2D's; PACZ2D changed; PACSRCT not the
template; CLIST(PACMAN) changed by the job; after step 6 CLIST(PACMAN) not byte-identical to the rendered member or
PACSRCT changed. On any STOP: no rerun, no repair, no further write; report.
Not in PACZ4INS: no rebind, no DELETE, no Z00000.PACMAN.DATA, no live session (the live DIE1 / LOST0 session follows
only after this is accepted).

## Rendered JCL
```
//PACZ4INS JOB 1,'PACMAN ZOS4 INS',CLASS=7,MSGLEVEL=(1,1),
//             NOTIFY=&SYSUID
//SAVETPL  EXEC PGM=IEBGENER
//SYSPRINT DD SYSOUT=A
//SYSIN    DD DUMMY
//SYSUT1   DD DSN=Z00000.PACMAN.CLIST(PACMAN),DISP=SHR
//SYSUT2   DD DSN=Z00000.PACMAN.CLIST(PACSRCT),DISP=SHR
//CEEOPT   EXEC PGM=IEBGENER,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//SYSIN    DD DUMMY
//SYSUT2   DD DSN=Z00000.PACMAN.CEEOPTS,DISP=(NEW,CATLG,CATLG),
//            RECFM=FB,LRECL=80,BLKSIZE=80,SPACE=(TRK,(1,1))
//SYSUT1   DD *
ALL31(OFF),STACK(,,BELOW)
/*
//PROM1    EXEC PGM=IEBCOPY,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//I        DD DSN=Z00000.PACMAN.LOAD,DISP=SHR
//T        DD DSN=&&PROMO,DISP=(NEW,PASS),DSNTYPE=LIBRARY,
//            RECFM=U,BLKSIZE=32760,UNIT=SYSALLDA,SPACE=(CYL,(2,1,5))
//SYSIN    DD *
  COPY OUTDD=T,INDD=I
  SELECT MEMBER=((PACZ2D,PACMAIN))
/*
//PROM2    EXEC PGM=IEBCOPY,COND=(0,NE)
//SYSPRINT DD SYSOUT=A
//T        DD DSN=&&PROMO,DISP=(OLD,PASS)
//O        DD DSN=Z00000.PACMAN.LOAD,DISP=SHR
//SYSIN    DD *
  COPY OUTDD=O,INDD=T
  SELECT MEMBER=PACMAIN
/*
//RUN1     EXEC PGM=PACMAIN,COND=(0,NE)
//STEPLIB  DD DSN=Z00000.PACMAN.LOAD,DISP=SHR
//CEEOPTS  DD *
ALL31(OFF),STACK(,,BELOW)
/*
//SYSIN    DD *
R
R
U
L
L
L
D
D
R
X
r
R
R
D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//CEEDUMP  DD SYSOUT=A
//SYSUDUMP DD DUMMY
//TSO2     EXEC PGM=PACMAIN,COND=(0,NE),PARM='TSO AI0'
//STEPLIB  DD DSN=Z00000.PACMAN.LOAD,DISP=SHR
//CEEOPTS  DD *
ALL31(OFF),STACK(,,BELOW)
/*
//SYSIN    DD *
D
D
D
D
D
D
D
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
R
D
D
Q
R
/*
//SYSOUT   DD SYSOUT=A
//CEEDUMP  DD SYSOUT=A
//SYSUDUMP DD DUMMY
```
