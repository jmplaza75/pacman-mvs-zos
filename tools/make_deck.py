#!/usr/bin/env python3
"""Generate a self-contained MVS build+test deck (build/<NAME>.jcl).

Usage: make_deck.py PACHELLO | MVS4 [--hlq HERC01]
Sources are validated (ASCII, 80 columns, no tabs) and uploaded with
IEBGENER, compiled with IKFCBL00, link-edited with IEWL and executed.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from validate_source import validate  # noqa: E402

COBOL_PARM = 'LOAD,LIB,SUPMAP,SIZE=2048K,BUF=1024K'

# name -> (jobname, modules in link order (first = entry), copybooks, load member, run input files)
DECKS = {
    'PACHELLO': ('PACBLD00', ['PACHELLO'], [], 'PACHELLO', [None]),
    'MVS1': ('PACBLD01', ['PACMAIN'], [], 'PACMAIN', [None]),
    'MVS2': ('PACBLD02', ['PACMAIN'], [], 'PACMAIN', ['tests/cases/MOVES.txt', 'tests/cases/EOF.txt']),
    'MVS3': ('PACBLD03', ['PACMAIN'], [], 'PACMAIN', ['tests/cases/MOVES.txt', 'tests/cases/EOF.txt', 'tests/cases/WIN.txt']),
    'MVS4': ('PACBLD04', ['PACMAIN'], [], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0')]),
}


def text_of(path):
    errors = validate(path)
    if errors:
        raise SystemExit('\n'.join(errors))
    return path.read_text(encoding='ascii')


def upload(step, hlq, lib, member, text):
    return (f'//{step:<8} EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD SYSOUT=A\n'
            f'//SYSUT2   DD DSN={hlq}.PACMAN.{lib}({member}),DISP=OLD\n'
            '//SYSIN    DD DUMMY\n//SYSUT1   DD DATA,DLM=ZZ\n' + text + 'ZZ\n')


def compile_step(step, hlq, member, obj):
    return (f'//{step:<8} EXEC PGM=IKFCBL00,COND=(0,NE),\n//         PARM=\'{COBOL_PARM}\'\n'
            '//SYSPRINT DD SYSOUT=A\n//SYSPUNCH DD DUMMY\n'
            + ''.join(f'//SYSUT{i}   DD UNIT=SYSDA,SPACE=(460,(700,100))\n' for i in range(1, 5)) +
            f'//SYSLIN   DD DSN=&&{obj},DISP=(NEW,PASS),UNIT=SYSDA,\n'
            '//            SPACE=(80,(500,100)),\n'
            '//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)\n'
            f'//SYSIN    DD DSN={hlq}.PACMAN.COBOL({member}),DISP=SHR\n'
            f'//SYSLIB   DD DSN={hlq}.PACMAN.COPY,DISP=SHR\n')


def link_step(hlq, objs, load, entry):
    t = "//LINK     EXEC PGM=IEWL,COND=(0,NE),PARM='LIST,XREF'\n"
    for i, o in enumerate(objs):
        t += f'//{"SYSLIN" if i == 0 else "":<8} DD DSN=&&{o},DISP=(OLD,DELETE)\n'
    t += '//         DD DDNAME=SYSIN\n'
    t += (f'//SYSLMOD  DD DSN={hlq}.PACMAN.LOAD({load}),DISP=OLD\n'
          '//SYSLIB   DD DSN=SYS1.COBLIB,DISP=SHR\n'
          '//SYSUT1   DD UNIT=SYSDA,SPACE=(1024,(50,20))\n'
          f'//SYSPRINT DD SYSOUT=A\n//SYSIN    DD *\n ENTRY {entry}\n/*\n')
    return t


def run_step(step, hlq, load, sysin):
    t = (f'//{step:<8} EXEC PGM={load},COND=(0,NE)\n'
         f'//STEPLIB  DD DSN={hlq}.PACMAN.LOAD,DISP=SHR\n')
    if sysin is not None:
        t += '//SYSIN    DD *\n' + sysin + '/*\n'
    return t + '//SYSOUT   DD SYSOUT=A\n//SYSUDUMP DD SYSOUT=A\n'


def build(name, hlq):
    job, modules, copies, load, runs = DECKS[name]
    out = (f'//{job} JOB (1),\'PACMAN {name}\',CLASS=A,MSGCLASS=A,\n'
           '//             MSGLEVEL=(1,1),REGION=4096K\n')
    for i, c in enumerate(copies, 1):
        out += upload(f'CPY{i}', hlq, 'COPY', c, text_of(ROOT / f'src/copy/{c}.cpy'))
    for i, m in enumerate(modules, 1):
        out += upload(f'SRC{i}', hlq, 'COBOL', m, text_of(ROOT / f'src/cobol/{m}.cob'))
        out += compile_step(f'COB{i}', hlq, m, f'OBJ{i}')
    out += link_step(hlq, [f'OBJ{i}' for i in range(1, len(modules) + 1)], load, modules[0])
    for i, r in enumerate(runs, 1):
        sysin = None if r is None else text_of(ROOT / r)
        out += run_step(f'RUN{i}', hlq, load, sysin)
    return out + '//\n'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('deck', choices=sorted(DECKS))
    ap.add_argument('--hlq', default='HERC01')
    a = ap.parse_args()
    dest = ROOT / 'build' / f'{a.deck}.jcl'
    dest.write_text(build(a.deck, a.hlq), encoding='ascii')
    print(dest)
