#!/usr/bin/env python3
"""ZOS-6 protocol probe build deck (docs/zos6-protocol-probe.md): jcl/zos/PACZ6PRB.jcl from src/probe/zos/PACZ6P.asm.

One job, two steps (the probe PDSE <HLQ>.PACMAN.Z6PRB.LOAD already exists: created empty by the ALLOC step of the
first build, JOB04217, which failed at ASM with IHB300; it is reused DISP=SHR, never deleted or re-allocated):
ASM (ASMA90 on the source in-stream: nothing uploaded, no member of <HLQ>.PACMAN.ASM / OBJ written), LKED (IEWBLINK
AMODE 24 / RMODE 24 into Z6PRB.LOAD(PACZ6P), only after ASM RC 0). No DELETE disposition, no DISP=NEW of a
permanent dataset, no PACMAIN / PACFSIO / CLIST / DATA reference.
Usage: zos6_probe_deck.py [--check]     writes (or, with --check, compares) jcl/zos/PACZ6PRB.jcl
"""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
SRC = R / 'src/probe/zos/PACZ6P.asm'
DECK = R / 'jcl/zos/PACZ6PRB.jcl'
LOADLIB = '@@HLQ@@.PACMAN.Z6PRB.LOAD'


def deck():
    src = SRC.read_text(encoding='ascii')
    assert all(len(x) <= 71 and not x.startswith(('/*', '//')) for x in src.splitlines())
    return ("//PACZ6PRB JOB 1,'PACMAN ZOS6 PROBE',CLASS=7,MSGLEVEL=(1,1),\n"
            '//             NOTIFY=&SYSUID\n'
            '//ASM      EXEC PGM=ASMA90,\n'
            "//             PARM='OBJECT,NODECK'\n"
            '//STEPLIB  DD DSN=HLA.SASMMOD1,DISP=SHR\n'
            '//SYSLIB   DD DSN=SYS1.MACLIB,DISP=SHR\n'
            '//         DD DSN=SYS1.MODGEN,DISP=SHR\n'
            '//SYSUT1   DD UNIT=SYSALLDA,SPACE=(TRK,(5,5))\n'
            '//SYSPRINT DD SYSOUT=*\n'
            '//SYSLIN   DD DSN=&&OBJ,DISP=(NEW,PASS),UNIT=SYSALLDA,\n'
            '//             SPACE=(TRK,(5,5)),DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)\n'
            '//SYSIN    DD *\n' + src + '/*\n'
            '//LKED     EXEC PGM=IEWBLINK,COND=(0,NE),\n'
            "//             PARM='LIST,AMODE=24,RMODE=24'\n"
            f'//SYSLMOD  DD DSN={LOADLIB}(PACZ6P),DISP=SHR\n'
            '//SYSLIN   DD DSN=&&OBJ,DISP=(OLD,PASS)\n'
            '//SYSPRINT DD SYSOUT=*\n')


def main():
    d = deck()
    if sys.argv[1:] == ['--check']:
        sys.exit(0 if DECK.read_text() == d else 'jcl/zos/PACZ6PRB.jcl is not the generated deck')
    DECK.write_text(d)
    print(f'{DECK.relative_to(R)} written ({len(d.splitlines())} lines)')


if __name__ == '__main__':
    main()
