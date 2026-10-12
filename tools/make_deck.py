#!/usr/bin/env python3
"""Generate MVS decks (build/<NAME>.jcl). Every dataset name derives from --prefix (default HERC01.PACMAN).

Build+test decks: PACHELLO, MVS1..MVS8 (phase history), RELEASE (= MVS8 content, release job name).
Install/use decks: ALLOC (first use: COBOL/COPY/LOAD/CLIST libraries), CLIST (store the TSO launcher),
RUN (play the installed game in batch from a card file, default tests/cases/MOVES.txt; --cards FILE).
Sources are validated (ASCII, 80 columns, COBOL to column 72, assembler to 71, no tabs) and uploaded with
IEBGENER, compiled with IKFCBL00 (+ IFOX00 for the PACTSO stub), link-edited with IEWL and executed.
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
    'MVS5': ('PACBLD05', ['PACMAIN'], [], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1')]),
    'MVS6': ('PACBLD06', ['PACMAIN'], [], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'MVS7': ('PACBLD07', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT'],
             ['PACSTATE', 'PACREQ', 'PACMREQ'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'RELEASE': ('PACREL10', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT'],
                ['PACSTATE', 'PACREQ', 'PACMREQ'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'G0': ('PACBLDG0', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT'],
           ['PACSTATE', 'PACREQ', 'PACMREQ'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'G1': ('PACBLDG1', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR'],
           ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'G2': ('PACBLDG2', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR'],
           ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'G3': ('PACBLDG3', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR'],
           ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'G4': ('PACBLDG4', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACQRY'],
           ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'GS': ('PACBLDGS', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACQRY'],
           ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'GX': ('PACBLDGX', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACQRY'],
           ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'RT': ('PACBLDRT', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACQRY', 'PACRT'],
           ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    'S1': ('PACBLDS1', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACQRY', 'PACRT'],
           ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    # MVS-GP1 (D36): the S1 deck + the core copybook PACARC (CPY6, after the S1 copies), then the ARCADE runs
    'GP1': ('PACBLGP1', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACQRY', 'PACRT'],
            ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS', 'PACARC'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    # MVS-GP2 (D37): the same modules and copies as GP1 (PACARC grew, PACREQ +REQ-START), then the GP2 runs
    'GP2': ('PACBLGP2', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACQRY', 'PACRT'],
            ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS', 'PACARC'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
    # MVS-GP2 GP2.3 (screens): build only (the GP2 deck stays the text / CLASSIC regression), then the TSD runs
    'GP23': ('PACBLG23', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACQRY', 'PACRT'],
             ['PACSTATE', 'PACREQ', 'PACMREQ', 'PACPAL', 'PACDS', 'PACARC'], 'PACMAIN', []),
    'MVS8': ('PACBLD08', ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT'],
             ['PACSTATE', 'PACREQ', 'PACMREQ'], 'PACMAIN', ['tests/cases/' + n + '.txt' for n in ('MOVES', 'RAND', 'CATCH1', 'WIN0', 'CATCH0', 'DIE1', 'LOST0', 'WINAFTER', 'LOST1', 'EDGE3', 'EDGE2', 'EDGE1', 'P2', 'P2N3', 'R1N2', 'C3WALK', 'C3', 'C3N2', 'MULTI')]),
}


def text_of(path):
    errors = validate(path)
    if errors:
        raise SystemExit('\n'.join(errors))
    return path.read_text(encoding='ascii')


def upload(step, pfx, lib, member, text):
    return (f'//{step:<8} EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD SYSOUT=A\n'
            f'//SYSUT2   DD DSN={pfx}.{lib}({member}),DISP=OLD\n'
            '//SYSIN    DD DUMMY\n//SYSUT1   DD DATA,DLM=ZZ\n' + text + 'ZZ\n')


def compile_step(step, pfx, member, obj):
    return (f'//{step:<8} EXEC PGM=IKFCBL00,COND=(0,NE),\n//         PARM=\'{COBOL_PARM}\'\n'
            '//SYSPRINT DD SYSOUT=A\n//SYSPUNCH DD DUMMY\n'
            + ''.join(f'//SYSUT{i}   DD UNIT=SYSDA,SPACE=(460,(700,100))\n' for i in range(1, 5)) +
            f'//SYSLIN   DD DSN=&&{obj},DISP=(NEW,PASS),UNIT=SYSDA,\n'
            '//            SPACE=(80,(500,100)),\n'
            '//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)\n'
            f'//SYSIN    DD DSN={pfx}.COBOL({member}),DISP=SHR\n'
            f'//SYSLIB   DD DSN={pfx}.COPY,DISP=SHR\n')


def link_step(pfx, objs, load, entry, step='LINK'):
    t = f"//{step:<8} EXEC PGM=IEWL,COND=(0,NE),PARM='LIST,XREF'\n"
    for i, o in enumerate(objs):
        t += f'//{"SYSLIN" if i == 0 else "":<8} DD DSN=&&{o},DISP=(OLD,DELETE)\n'
    t += '//         DD DDNAME=SYSIN\n'
    t += (f'//SYSLMOD  DD DSN={pfx}.LOAD({load}),DISP=OLD\n'
          '//SYSLIB   DD DSN=SYS1.COBLIB,DISP=SHR\n'
          '//SYSUT1   DD UNIT=SYSDA,SPACE=(1024,(50,20))\n'
          f'//SYSPRINT DD SYSOUT=A\n//SYSIN    DD *\n ENTRY {entry}\n/*\n')
    return t


def run_step(step, pfx, load, sysin, parm=None):
    t = (f'//{step:<8} EXEC PGM={load},COND=(0,NE)' + (f",PARM='{parm}'" if parm else '') + '\n'
         f'//STEPLIB  DD DSN={pfx}.LOAD,DISP=SHR\n')
    if sysin is not None:
        t += '//SYSIN    DD *\n' + sysin + '/*\n'
    return t + '//SYSOUT   DD SYSOUT=A\n//SYSUDUMP DD SYSOUT=A\n'


ASM = {'RT': ['PACTSO', 'PACFSIO'], 'MVS8': ['PACTSO'], 'RELEASE': ['PACTSO'], 'G0': ['PACTSO'], 'G1': ['PACTSO', 'PACFSIO'], 'G2': ['PACTSO', 'PACFSIO'], 'G3': ['PACTSO', 'PACFSIO'], 'G4': ['PACTSO', 'PACFSIO'], 'GS': ['PACTSO', 'PACFSIO'], 'GX': ['PACTSO', 'PACFSIO'], 'S1': ['PACTSO', 'PACFSIO'], 'GP1': ['PACTSO', 'PACFSIO'], 'GP2': ['PACTSO', 'PACFSIO'], 'GP23': ['PACTSO', 'PACFSIO']}          # assembler stubs (src/asm/NAME.asm) linked with the COBOL objects


def asm_step(step, obj, text):
    return (f'//{step:<8} EXEC PGM=IFOX00,COND=(0,NE),PARM=\'OBJECT,NODECK,NOXREF\'\n'
            '//SYSLIB   DD DSN=SYS1.MACLIB,DISP=SHR\n//         DD DSN=SYS1.AMODGEN,DISP=SHR\n'
            + ''.join(f'//SYSUT{i}   DD UNIT=SYSDA,SPACE=(CYL,(3,1))\n' for i in range(1, 4)) +
            '//SYSPRINT DD SYSOUT=A\n'
            f'//SYSGO    DD DSN=&&{obj},DISP=(NEW,PASS),UNIT=SYSDA,\n'
            '//            SPACE=(80,(500,100)),\n'
            '//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)\n'
            '//SYSIN    DD DATA,DLM=ZZ\n' + text + 'ZZ\n')


TSO = {'MVS8': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'RELEASE': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'G0': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'G1': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'G2': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'G3': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'G4': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'GS': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'GX': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'RT': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'S1': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'GP1': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR'],
       'GP2': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR']}
TSD = {'G1': ['MOVES', 'TSORDR', 'MULTI', 'C3N2', 'DIE1'],
       # G2: (case, highlight flag in PARM column 13): 5 with highlights, 2 without (= G1 screens)
       'G2': [('MOVES', 'Y'), ('TSORDR', 'Y'), ('MULTI', 'Y'), ('C3N2', 'Y'), ('DIE1', 'Y'), ('MOVES', 'N'), ('DIE1', 'N')],
       # G3: (case, hilite, anim, redraw): P = partial redraw, F = full (G2 screens when anim is N)
       'G3': [('MOVES', 'Y', 'Y', 'P'), ('TSORDR', 'Y', 'Y', 'P'), ('MULTI', 'Y', 'Y', 'P'), ('DIE1', 'Y', 'Y', 'P'),
              ('C3N2', 'N', 'Y', 'P'), ('TICKS', 'Y', 'Y', 'P'), ('MOVES', 'Y', 'N', 'P'),
              ('MOVES', 'Y', 'Y', 'F'), ('TICKS', 'Y', 'Y', 'F'),
              ('MOVES', 'Y', 'N', 'F'), ('DIE1', 'Y', 'N', 'F'), ('MULTI', 'Y', 'N', 'F')]}
# G4: the 12 G3 runs unchanged (no column 16 = CLASSIC) + (case, hilite, anim, redraw, glyphs) G/B/C/A profile runs
TSD['G4'] = TSD['G3'] + [
    ('MOVES', 'Y', 'Y', 'P', 'G'), ('TSORDR', 'Y', 'Y', 'P', 'G'), ('MULTI', 'Y', 'Y', 'P', 'G'), ('DIE1', 'Y', 'Y', 'P', 'G'),
    ('TICKS', 'Y', 'Y', 'P', 'G'), ('C3N2', 'N', 'Y', 'P', 'G'), ('FACE', 'Y', 'Y', 'P', 'G'), ('FACE', 'N', 'N', 'F', 'G'),
    ('MOVES', 'Y', 'N', 'F', 'G'), ('MULTI', 'Y', 'Y', 'P', 'B'), ('TICKS', 'Y', 'Y', 'P', 'B'), ('DIE1', 'N', 'N', 'F', 'B'),
    ('MOVES', 'Y', 'Y', 'P', 'C'), ('MOVES', 'Y', 'Y', 'P', 'A')]
# MVS-GS: the 26 G4 runs unchanged (no column 17 = SCALE(NO), the G4 regression) + (case, hilite, anim, redraw, glyphs,
# scale) runs: 4x2 / 3x2 scaled (all four end banners: QUIT, EOF, LOST, WIN), AUTO, the fallbacks (no highlight, BASE,
# CLASSIC), the size guard (T: 4x2 with a 1000-byte limit -> G4) and an explicit N
GS_RUNS = [
    ('MOVES', 'Y', 'Y', 'P', 'G', '4'), ('TSORDR', 'Y', 'Y', 'P', 'G', '4'), ('MULTI', 'Y', 'Y', 'P', 'G', '4'),
    ('DIE1', 'Y', 'Y', 'P', 'G', '4'), ('TICKS', 'Y', 'Y', 'P', 'G', '4'), ('FACE', 'Y', 'Y', 'P', 'G', '4'),
    ('C3N2', 'Y', 'Y', 'P', 'G', '4'), ('EDGE2', 'Y', 'N', 'P', 'G', '4'), ('MOVES', 'Y', 'N', 'F', 'G', '4'),
    ('MULTI', 'Y', 'Y', 'P', 'G', '3'), ('FACE', 'Y', 'Y', 'P', 'G', '3'), ('C3N2', 'Y', 'N', 'F', 'G', '3'),
    ('MOVES', 'Y', 'Y', 'P', 'G', 'A'), ('MOVES', 'N', 'Y', 'P', 'G', '4'), ('MOVES', 'Y', 'Y', 'P', 'B', '4'),
    ('MOVES', 'Y', 'Y', 'P', 'A', 'A'), ('MULTI', 'Y', 'Y', 'P', 'G', 'T'), ('TICKS', 'Y', 'Y', 'P', 'G', 'N')]
TSD['GS'] = TSD['G4'] + GS_RUNS
# MVS-GS geometry (D32): the 44 GS runs unchanged (no column 18 = CANVAS DEFAULT, the regression) + (case, hilite, anim,
# redraw, glyphs, scale, canvas) runs on simulated buffers: W 120x27, X 132x27, T 80x43, M 80x32, U 100x25 (too small),
# L 160x30 (> 4095 cells), D explicit default
GX_RUNS = [
    ('MOVES', 'Y', 'Y', 'P', 'G', '4', 'W'), ('MULTI', 'Y', 'Y', 'P', 'G', '4', 'W'), ('C3N2', 'Y', 'Y', 'P', 'G', '4', 'W'),
    ('TSORDR', 'Y', 'Y', 'P', 'G', '4', 'W'), ('TICKS', 'Y', 'Y', 'P', 'G', '4', 'W'), ('FACE', 'Y', 'Y', 'P', 'G', '4', 'X'),
    ('MULTI', 'Y', 'Y', 'P', 'G', '4', 'T'), ('DIE1', 'Y', 'Y', 'P', 'G', '4', 'M'), ('EDGE2', 'Y', 'N', 'P', 'G', '4', 'W'),
    ('MOVES', 'Y', 'N', 'F', 'G', '4', 'W'), ('MOVES', 'Y', 'Y', 'P', 'G', '4', 'U'), ('MOVES', 'Y', 'Y', 'P', 'G', '4', 'L'),
    ('MULTI', 'Y', 'Y', 'P', 'G', '3', 'W'), ('MOVES', 'Y', 'Y', 'P', 'G', 'N', 'W'), ('MULTI', 'Y', 'Y', 'P', 'G', 'T', 'W'),
    ('MOVES', 'Y', 'Y', 'P', 'G', '4', 'D'), ('TICKS', 'N', 'Y', 'P', 'G', '4', 'W')]
TSD['GX'] = TSD['GS'] + GX_RUNS
TSD['RT'] = TSD['GX']
TSD['S1'] = TSD['RT']
TSD['GP1'] = TSD['S1']
TSD['GP2'] = TSD['S1']
# MVS-RT (D33): REALTIME runs after the whole GX regression. Batch (PARM column 19 R): one card = one quantum
# (tests/rtcases); TSD: (case, canvas) with COLOR N, HILITE Y, ANIM Y, REDRAW P, GLYPHS G, SCALE 4, PLAY R.
RT_BAT = ['RTLINE', 'RTCORNER', 'RTTTL', 'RTREV', 'RTMULTI', 'RTPRE', 'RTSTILL', 'RTPAUSE', 'RTLONG', 'RTWIN', 'RTEDGE',
          'RTEDGE0']
RT_TSD = [('RTCORNER', 'W'), ('RTSTILL', 'W'), ('RTPAUSE', 'W'), ('RTPRE', 'W'), ('RTMULTI', 'W'), ('RTLINE', 'D')]


def rt_parm_and_cards(case):
    lines = text_of(ROOT / f'tests/rtcases/{case}.txt').splitlines(keepends=True)
    if lines and lines[0][:1] == 'A':
        return 'TSD ' + lines[0].rstrip('\n')[:5], ''.join(lines[1:])
    return 'TSD AI1 1', ''.join(lines)


def rt_steps(pfx, load):
    # RT3: the PACTSO clock (TIME / DLWT) tested in batch by the driver PACTSOT (LOAD(PACTSOT), not the game)
    out = upload('SRCT', pfx, 'COBOL', 'PACTSOT', text_of(ROOT / 'src/cobol/PACTSOT.cob'))
    out += compile_step('COBT', pfx, 'PACTSOT', 'OBJT')
    out += asm_step('ASMT', 'OBJAT', text_of(ROOT / 'src/asm/PACTSO.asm'))
    out += link_step(pfx, ['OBJT', 'OBJAT'], 'PACTSOT', 'PACTSOT', step='LINKT')
    out += run_step('TSOT1', pfx, 'PACTSOT', None)
    for i, c in enumerate(RT_BAT, 1):
        out += run_step(f'RTB{i}', pfx, load, text_of(ROOT / f'tests/rtcases/{c}.txt'), parm='BAT'.ljust(18) + 'R')
    for i, (c, cv) in enumerate(RT_TSD, 1):
        parm, cards = rt_parm_and_cards(c)
        out += run_step(f'RTT{i}', pfx, load, cards, parm=parm.ljust(11) + 'NYYPG4' + cv + 'R')
    return out   # colour screens dry run (PARM 'TSD ...', hex output)   # replayed in interactive mode (PARM='TSO')


# MVS-S1: after the whole RT deck (the regression, SOUND absent = N), a marker step, then SOUND runs (PARM column 20).
# TURN TSD: (case, hilite, anim, redraw, glyphs, scale, canvas, sound) with column 19 T; scaled (end screen) and not
# scaled (bell-only write before line mode), start / death / last death / win / death + win in one move, AUTO and NO.
S1_TURN = [('DIE1', 'Y', 'Y', 'P', 'G', '4', 'W', 'Y'), ('LOST0', 'Y', 'Y', 'P', 'G', '4', 'W', 'Y'),
           ('WIN0', 'Y', 'N', 'P', 'G', '4', 'W', 'Y'), ('EDGE3', 'Y', 'Y', 'P', 'G', '4', 'W', 'Y'),
           ('DIE1', 'Y', 'Y', 'P', 'G', 'N', 'D', 'Y'), ('LOST0', 'Y', 'Y', 'P', 'G', 'N', 'D', 'Y'),
           ('WIN0', 'Y', 'N', 'F', 'C', 'N', 'D', 'Y'), ('EDGE1', 'Y', 'N', 'F', 'C', 'N', 'D', 'Y'),
           ('DIE1', 'Y', 'Y', 'P', 'G', '4', 'W', 'A'), ('DIE1', 'Y', 'Y', 'P', 'G', '4', 'W', 'N')]
# REALTIME TSD (case, canvas, sound): COLOR N, HILITE Y, ANIM Y, REDRAW P, GLYPHS G, SCALE 4, PLAY R
S1_RT = [('RTSTILL', 'W', 'Y'), ('RTEDGE', 'W', 'Y'), ('RTEDGE0', 'W', 'Y'), ('RTWIN', 'W', 'Y'), ('RTPAUSE', 'W', 'Y')]
# line and batch modes ignore SOUND: (kind, case) - BAT TURN, BAT REALTIME, TSO line mode (COLOR AUTO fails in batch)
S1_SILENT = [('BAT', 'LOST0'), ('RTB', 'RTSTILL'), ('TSO', 'DIE1')]
S1_MARK = 'PACMAN-S1-SOUND-RUNS-FOLLOW'


def s1_steps(pfx, load):
    out = ('//S1MARK   EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD DUMMY\n//SYSIN    DD DUMMY\n'
           f'//SYSUT1   DD *\n{S1_MARK}\n/*\n//SYSUT2   DD SYSOUT=A\n')
    for i, (c, h, a, r, g, sc, cv, snd) in enumerate(S1_TURN, 1):
        parm, cards = tso_parm_and_cards(c)
        parm = 'TSD' + parm[3:]
        parm = (parm + ' AI1 1' if parm == 'TSD' else parm).ljust(11) + 'N' + h + a + r + g + sc + cv + 'T' + snd
        out += run_step(f'S1T{i}', pfx, load, cards, parm=parm)
    for i, (c, cv, snd) in enumerate(S1_RT, 1):
        parm, cards = rt_parm_and_cards(c)
        out += run_step(f'S1R{i}', pfx, load, cards, parm=parm.ljust(11) + 'NYYPG4' + cv + 'R' + snd)
    for i, (kind, c) in enumerate(S1_SILENT, 1):
        if kind == 'BAT':
            out += run_step(f'S1S{i}', pfx, load, text_of(ROOT / f'tests/cases/{c}.txt'), parm='BAT'.ljust(19) + 'Y')
        elif kind == 'RTB':
            out += run_step(f'S1S{i}', pfx, load, text_of(ROOT / f'tests/rtcases/{c}.txt'), parm='BAT'.ljust(18) + 'RY')
        else:
            parm, cards = tso_parm_and_cards(c)
            out += run_step(f'S1S{i}', pfx, load, cards, parm=parm.ljust(11) + 'AAAPAAAAY')
    return out


# MVS-GP1 (D36): after the whole S1 deck (the CLASSIC regression: no PARM column 21), a marker step, then RULES(ARCADE)
# runs (PARM column 21 A): BAT TURN (tests/gpcases edge cases from tests/search_gp1.py + scripted GPAI0/GPHOME, and four
# 1.0-MVS cases), BAT REALTIME (one card = one quantum), TSO line mode (config from the PARM, blank card = redraw),
# then column 21 present but not A (= CLASSIC: 1.0-MVS oracle / RT model).
GP1_BAT = [('gpcases', c) for c in ('GPAI0', 'GPHOME', 'GPDEYE', 'GPDFR', 'GPFN', 'GPFWALK', 'GPLASTH', 'GPLASTO',
                                    'GPPOW2', 'GPPOWE', 'GPREVB', 'GPTIE', 'GPTWOF', 'GPWALKF')] + \
          [('cases', c) for c in ('MULTI', 'C3N2', 'RAND', 'LOST1')]
GP1_RT = [('gpcases', c) for c in ('RTGPA', 'RTGPD', 'RTGPP')] + [('rtcases', c) for c in ('RTSTILL', 'RTMULTI', 'RTPAUSE')]
GP1_TSO = ['GPTSO', 'GPAI0']
GP1_CLASSIC = [('BAT', 'LOST0', 'C'), ('BAT', 'MULTI', ' '), ('RTB', 'RTSTILL', 'X')]
GP1_MARK = 'PACMAN-GP1-ARCADE-RUNS-FOLLOW'


def gp1_steps(pfx, load):
    out = ('//GP1MARK  EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD DUMMY\n//SYSIN    DD DUMMY\n'
           f'//SYSUT1   DD *\n{GP1_MARK}\n/*\n//SYSUT2   DD SYSOUT=A\n')
    for i, (d, c) in enumerate(GP1_BAT, 1):
        out += run_step(f'GPB{i}', pfx, load, text_of(ROOT / f'tests/{d}/{c}.txt'), parm='BAT'.ljust(20) + 'A')
    for i, (d, c) in enumerate(GP1_RT, 1):
        out += run_step(f'GPR{i}', pfx, load, text_of(ROOT / f'tests/{d}/{c}.txt'), parm='BAT'.ljust(18) + 'R A')
    for i, c in enumerate(GP1_TSO, 1):
        lines = text_of(ROOT / f'tests/gpcases/{c}.txt').splitlines(keepends=True)
        out += run_step(f'GPT{i}', pfx, load, ''.join(lines[1:]), parm=('TSO ' + lines[0].rstrip('\n')[:5]).ljust(20) + 'A')
    for i, (kind, c, col) in enumerate(GP1_CLASSIC, 1):
        if kind == 'BAT':
            out += run_step(f'GPC{i}', pfx, load, text_of(ROOT / f'tests/cases/{c}.txt'), parm='BAT'.ljust(20) + col)
        else:
            out += run_step(f'GPC{i}', pfx, load, text_of(ROOT / f'tests/rtcases/{c}.txt'), parm='BAT'.ljust(18) + 'R ' + col)
    return out


# MVS-GP1 GP1.3 (screens): after the GP1.2 runs, a second marker, then RULES(ARCADE) TSD dry runs. TURN: (case of
# tests/gpcases, hilite, anim, redraw, glyphs, scale, canvas, sound) with PARM column 19 T and column 21 A: the three
# glyph profiles unscaled, 4x2 / 3x2 scaled on every family (W 120x27, X 132x27, T 80x43, M 80x32, B 80x24), the size
# guard (scale T), ticks and a redraw (GPTICK), full redraw, SOUND. REALTIME: (case, canvas, sound), COLOR N, HILITE Y,
# ANIM Y, REDRAW P, GLYPHS G, SCALE 4.
GP13_TURN = [('GPAI0', 'Y', 'Y', 'P', 'C', 'N', 'D', 'N'), ('GPAI0', 'Y', 'N', 'F', 'B', 'N', 'D', 'N'),
             ('GPHOME', 'Y', 'Y', 'P', 'G', 'N', 'D', 'N'), ('GPTWOF', 'N', 'Y', 'P', 'G', 'N', 'D', 'N'),
             ('GPTICK', 'Y', 'Y', 'P', 'G', 'N', 'D', 'N'), ('GPAI0', 'Y', 'Y', 'P', 'G', '4', 'W', 'N'),
             ('GPHOME', 'Y', 'Y', 'P', 'G', '4', 'D', 'Y'), ('GPFN', 'Y', 'Y', 'P', 'G', '3', 'D', 'N'),
             ('GPDEYE', 'Y', 'Y', 'P', 'G', '4', 'T', 'N'), ('GPREVB', 'Y', 'Y', 'P', 'G', '4', 'X', 'N'),
             ('GPPOW2', 'Y', 'N', 'F', 'G', '4', 'W', 'N'), ('GPLASTO', 'Y', 'Y', 'P', 'G', '4', 'W', 'Y'),
             ('GPTICK', 'Y', 'Y', 'P', 'G', '4', 'W', 'N'), ('GPAI0', 'Y', 'Y', 'P', 'G', 'T', 'W', 'N'),
             ('GPWALKF', 'Y', 'Y', 'P', 'G', '4', 'M', 'N'), ('GPTSO', 'Y', 'Y', 'P', 'G', '4', 'W', 'N')]
GP13_RT = [('RTGPA', 'W', 'Y'), ('RTGPD', 'W', 'Y'), ('RTGPP', 'W', 'N'), ('RTGPA', 'D', 'N'), ('RTGPD', 'T', 'N')]
GP13_MARK = 'PACMAN-GP1-SCREEN-RUNS-FOLLOW'


def gp_parm_and_cards(case, mode):
    lines = text_of(ROOT / f'tests/gpcases/{case}.txt').splitlines(keepends=True)
    return f'{mode} ' + lines[0].rstrip('\n')[:5], ''.join(lines[1:])


def gp13_steps(pfx, load):
    out = ('//GP13MARK EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD DUMMY\n//SYSIN    DD DUMMY\n'
           f'//SYSUT1   DD *\n{GP13_MARK}\n/*\n//SYSUT2   DD SYSOUT=A\n')
    for i, (c, h, a, r, g, sc, cv, snd) in enumerate(GP13_TURN, 1):
        parm, cards = gp_parm_and_cards(c, 'TSD')
        out += run_step(f'GQT{i}', pfx, load, cards, parm=parm.ljust(11) + 'N' + h + a + r + g + sc + cv + 'T' + snd + 'A')
    for i, (c, cv, snd) in enumerate(GP13_RT, 1):
        parm, cards = gp_parm_and_cards(c, 'TSD')
        out += run_step(f'GQR{i}', pfx, load, cards, parm=parm.ljust(11) + 'NYYPG4' + cv + 'R' + snd + 'A')
    return out


# MVS-GP2 (D37): after the whole S1 deck (the CLASSIC regression: no PARM column 21), a marker step, then
# RULES(ARCADE) runs with the start level in PARM columns 22-23 ('' = absent; any text is passed as is, so the
# validation of PACMAIN is exercised: blank, 00, ab, one digit, three digits). (directory, case, start):
# the GP1 cases (gp1 BAT / RT / TSO, start absent) rerun against the GP2 model; the GP2 edge cases (tests/gp2cases,
# tests/search_gp2.py); the row probe G2ROW at every start level 1-13; AI0 / AI2 / AI3 bumps; REALTIME (one card = one
# quantum); TSO line mode; then column 21 not A with columns 22-23 present (= CLASSIC: 1.0-MVS oracle / RT model).
GP2_BAT = [(d, c, '') for d, c in GP1_BAT] + \
          [('gp2cases', c, st) for c, st in (
              ('G2CLR', ''), ('G2CLR', '99'), ('G2BDIE', ''), ('G2BGH', ''), ('G2BUND', ''), ('G2CLRD', ''),
              ('G2CLRF', ''), ('G2CLRL', ''), ('G2CLRO', ''), ('G2XP', '13'), ('G2XG', '13'), ('G2XF', '13'),
              ('G2XD', '13'), ('G2X20K', '13'))] + \
          [('gp2cases', 'G2ROW', '%02d' % k) for k in range(1, 14)] + \
          [('gp2cases', 'G2ROW', st) for st in ('', '  ', '00', 'ab', '5', '123', '99', '7 ')] + \
          [('gpcases', 'GPAI0', '09'), ('cases', 'MULTI', '05'), ('cases', 'P2', '05')]
GP2_RT = [(d, c, '') for d, c in GP1_RT] + \
         [('gp2cases', 'G2RCLR', ''), ('gp2cases', 'G2RB2', ''), ('gp2cases', 'G2RPAU', ''), ('gp2cases', 'G2RXD', '13'),
          ('rtcases', 'RTMULTI', '04'), ('rtcases', 'RTSTILL', '05')]
GP2_TSO = [('GPTSO', ''), ('GPAI0', ''), ('GPTSO', '03')]
GP2_CLASSIC = [('BAT', 'LOST0', 'C', '05'), ('RTB', 'RTSTILL', ' ', '07')]
GP2_MARK = 'PACMAN-GP2-ARCADE-RUNS-FOLLOW'


def gp2_steps(pfx, load):
    out = ('//GP2MARK  EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD DUMMY\n//SYSIN    DD DUMMY\n'
           f'//SYSUT1   DD *\n{GP2_MARK}\n/*\n//SYSUT2   DD SYSOUT=A\n')
    for i, (d, c, st) in enumerate(GP2_BAT, 1):
        out += run_step(f'G2B{i}', pfx, load, text_of(ROOT / f'tests/{d}/{c}.txt'), parm='BAT'.ljust(20) + 'A' + st)
    for i, (d, c, st) in enumerate(GP2_RT, 1):
        out += run_step(f'G2R{i}', pfx, load, text_of(ROOT / f'tests/{d}/{c}.txt'), parm='BAT'.ljust(18) + 'R A' + st)
    for i, (c, st) in enumerate(GP2_TSO, 1):
        lines = text_of(ROOT / f'tests/gpcases/{c}.txt').splitlines(keepends=True)
        out += run_step(f'G2T{i}', pfx, load, ''.join(lines[1:]),
                        parm=('TSO ' + lines[0].rstrip('\n')[:5]).ljust(20) + 'A' + st)
    for i, (kind, c, col, st) in enumerate(GP2_CLASSIC, 1):
        if kind == 'BAT':
            out += run_step(f'G2C{i}', pfx, load, text_of(ROOT / f'tests/cases/{c}.txt'), parm='BAT'.ljust(20) + col + st)
        else:
            out += run_step(f'G2C{i}', pfx, load, text_of(ROOT / f'tests/rtcases/{c}.txt'),
                            parm='BAT'.ljust(18) + 'R ' + col + st)
    return out


# MVS-GP2 GP2.3 (screens, deck GP23): after the build, a marker, then RULES(ARCADE) TSD dry runs with the start level
# in PARM columns 22-23. TURN: (directory, case, hilite, anim, redraw, glyphs, scale, canvas, sound, start) = the GP1.3
# runs (GP13_TURN, start absent) and the GP2 cases on every glyph profile unscaled, 4x2 / 3x2 scaled, the W / X / T /
# M / B families, the size guard (scale T), full redraw, SOUND (level clear, extra life, extra life + death, clear +
# death). REALTIME: (directory, case, canvas, sound, start), COLOR N, HILITE Y, ANIM Y, REDRAW P, GLYPHS G, SCALE 4.
GP23_TURN = [('gpcases',) + r + ('',) for r in GP13_TURN] + [('gp2cases',) + r for r in (
    ('G2CLR', 'Y', 'Y', 'P', 'C', 'N', 'D', 'Y', ''), ('G2CLR', 'Y', 'N', 'F', 'B', 'N', 'D', 'N', ''),
    ('G2CLR', 'Y', 'Y', 'P', 'G', 'N', 'D', 'N', ''), ('G2CLR', 'Y', 'Y', 'P', 'G', '4', 'W', 'Y', ''),
    ('G2CLR', 'Y', 'Y', 'P', 'G', '3', 'D', 'N', ''), ('G2CLR', 'Y', 'Y', 'P', 'G', '4', 'T', 'N', ''),
    ('G2CLR', 'Y', 'Y', 'P', 'G', 'T', 'W', 'N', ''), ('G2CLR', 'Y', 'Y', 'P', 'G', '4', 'W', 'N', '99'),
    ('G2BGHX', 'Y', 'Y', 'P', 'G', '4', 'W', 'N', ''), ('G2BGHX', 'Y', 'Y', 'P', 'C', 'N', 'D', 'N', ''),
    ('G2BDIE', 'Y', 'Y', 'P', 'G', '4', 'M', 'Y', ''), ('G2BUND', 'Y', 'Y', 'P', 'B', 'N', 'D', 'N', ''),
    ('G2XD', 'Y', 'Y', 'P', 'G', '4', 'W', 'Y', '13'), ('G2XF', 'Y', 'Y', 'P', 'G', '4', 'X', 'Y', '13'),
    ('G2ROW', 'Y', 'Y', 'P', 'G', '4', 'W', 'N', '99'), ('G2ROW', 'Y', 'Y', 'P', 'G', '4', 'T', 'N', '10'),
    ('G2CLRD', 'Y', 'Y', 'P', 'G', '4', 'W', 'Y', ''))]
GP23_RT = [('gpcases',) + r + ('',) for r in GP13_RT] + [('gp2cases',) + r for r in (
    ('G2RCLR', 'W', 'Y', ''), ('G2RPAU', 'W', 'N', ''), ('G2RXD', 'W', 'Y', '13'), ('G2RB2', 'D', 'N', ''),
    ('G2RCLR', 'T', 'N', ''))]
GP23_MARK = 'PACMAN-GP2-SCREEN-RUNS-FOLLOW'


def gp23_steps(pfx, load):
    out = ('//GP23MARK EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD DUMMY\n//SYSIN    DD DUMMY\n'
           f'//SYSUT1   DD *\n{GP23_MARK}\n/*\n//SYSUT2   DD SYSOUT=A\n')
    for i, (d, c, h, a, r, g, sc, cv, snd, st) in enumerate(GP23_TURN, 1):
        lines = text_of(ROOT / f'tests/{d}/{c}.txt').splitlines(keepends=True)
        parm = ('TSD ' + lines[0].rstrip('\n')[:5]).ljust(11) + 'N' + h + a + r + g + sc + cv + 'T' + snd + 'A' + st
        out += run_step(f'G3T{i}', pfx, load, ''.join(lines[1:]), parm=parm)
    for i, (d, c, cv, snd, st) in enumerate(GP23_RT, 1):
        lines = text_of(ROOT / f'tests/{d}/{c}.txt').splitlines(keepends=True)
        parm = ('TSD ' + lines[0].rstrip('\n')[:5]).ljust(11) + 'NYYPG4' + cv + 'R' + snd + 'A' + st
        out += run_step(f'G3R{i}', pfx, load, ''.join(lines[1:]), parm=parm)
    return out


def tso_parm_and_cards(case):
    """Interactive mode takes the config from the PARM ('TSO AI3 2'), not from a first card."""
    lines = (ROOT / f'tests/cases/{case}.txt').read_text(encoding='ascii').splitlines(keepends=True)
    if lines and lines[0][:1] == 'A':
        return 'TSO ' + lines[0].rstrip('\n')[:5], ''.join(lines[1:])
    return 'TSO', ''.join(lines)


def build(name, pfx):
    job, modules, copies, load, runs = DECKS[name]
    out = job_card(job, f'PACMAN {name}') + f'//* PREFIX {pfx}\n'
    for i, c in enumerate(copies, 1):
        out += upload(f'CPY{i}', pfx, 'COPY', c, text_of(ROOT / f'src/copy/{c}.cpy'))
    for i, m in enumerate(modules, 1):
        out += upload(f'SRC{i}', pfx, 'COBOL', m, text_of(ROOT / f'src/cobol/{m}.cob'))
        out += compile_step(f'COB{i}', pfx, m, f'OBJ{i}')
    objs = [f'OBJ{i}' for i in range(1, len(modules) + 1)]
    for i, a in enumerate(ASM.get(name, []), 1):
        out += asm_step(f'ASM{i}', f'OBJA{i}', text_of(ROOT / f'src/asm/{a}.asm'))
        objs.append(f'OBJA{i}')
    out += link_step(pfx, objs, load, modules[0])
    for i, r in enumerate(runs, 1):
        sysin = None if r is None else text_of(ROOT / r)
        out += run_step(f'RUN{i}', pfx, load, sysin)
    for i, c in enumerate(TSO.get(name, []), 1):
        text_of(ROOT / f'tests/cases/{c}.txt')
        parm, cards = tso_parm_and_cards(c)
        out += run_step(f'TSO{i}', pfx, load, cards, parm=parm)
    for i, c in enumerate(TSD.get(name, []), 1):
        hilite = None
        if isinstance(c, tuple):
            c, hilite = c[0], ''.join(c[1:])
        parm, cards = tso_parm_and_cards(c)
        parm = 'TSD' + parm[3:]
        if hilite:
            parm = (parm + ' AI1 1' if parm == 'TSD' else parm).ljust(11) + 'N' + hilite
        out += run_step(f'TSD{i}', pfx, load, cards, parm=parm)
    if name in ('G4', 'GS', 'GX', 'RT', 'S1', 'GP1', 'GP2'):
        out += qry_test_steps(pfx)
    if name in ('RT', 'S1', 'GP1', 'GP2'):
        out += rt_steps(pfx, load)
    if name in ('S1', 'GP1', 'GP2'):
        out += s1_steps(pfx, load)
    if name == 'GP2':
        out += gp2_steps(pfx, load)
    if name == 'GP23':
        out += gp23_steps(pfx, load)
    if name == 'GP1':
        out += gp1_steps(pfx, load)
        out += gp13_steps(pfx, load)
    return out + '//\n'


def qry_test_steps(pfx):
    """MVS-G4: PACQRY (pure capability parsing) tested in batch with recorded Query Replies (tests/qry_cases.py):
    driver PACQRYT + PACQRY compiled again into LOAD(PACQRYT), one run over all cases."""
    sys.path.insert(0, str(ROOT / 'tests'))
    from qry_cases import cards  # noqa: E402
    out = upload('SRCQ', pfx, 'COBOL', 'PACQRYT', text_of(ROOT / 'src/cobol/PACQRYT.cob'))
    out += compile_step('COBQ1', pfx, 'PACQRYT', 'OBJQ1')
    out += compile_step('COBQ2', pfx, 'PACQRY', 'OBJQ2')
    out += link_step(pfx, ['OBJQ1', 'OBJQ2'], 'PACQRYT', 'PACQRYT', step='LINKQ')
    return out + run_step('QRY1', pfx, 'PACQRYT', cards())


def job_card(job, title):
    return f"//{job} JOB (1),'{title}',CLASS=A,MSGCLASS=A,\n//             MSGLEVEL=(1,1),REGION=4096K\n"


def clist_text(pfx):
    return text_of(ROOT / 'src/clist/PACMAN.clist').replace('@@PREFIX@@', pfx)


def alloc_deck(pfx):
    out = job_card('PACALC10', 'PACMAN ALLOC') + (
        '//* FIRST USE ONLY: CREATES THE PROJECT LIBRARIES. NOT IDEMPOTENT AND NEVER\n'
        '//* DELETES ANYTHING: IF A DATASET EXISTS THE JOB FAILS WITH NOT CATLGD 2.\n'
        '//ALLOC    EXEC PGM=IEFBR14\n')
    for dd, lib, space, dcb in (('COBOL', 'COBOL', '(TRK,(15,5,10))', 'RECFM=FB,LRECL=80,BLKSIZE=3120'),
                                ('COPY', 'COPY', '(TRK,(5,2,5))', 'RECFM=FB,LRECL=80,BLKSIZE=3120'),
                                ('LOAD', 'LOAD', '(TRK,(15,5,10))', 'RECFM=U,BLKSIZE=6144'),
                                ('CLIST', 'CLIST', '(TRK,(2,1,5))', 'RECFM=FB,LRECL=80,BLKSIZE=3120')):
        out += (f'//{dd:<8} DD DSN={pfx}.{lib},DISP=(NEW,CATLG,DELETE),\n'
                f'//            UNIT=SYSDA,SPACE={space},\n'
                f'//            DCB=(DSORG=PO,{dcb})\n')
    return out + '//\n'


def compress_deck(pfx):
    """Maintenance: compress the source libraries in place (IEBCOPY). Every build re-uploads every member and a PDS
    never reuses the space of replaced members, so the COBOL library eventually ends with SE37 (MVS-G4, JOB 193).
    The COBOL, COPY and (MVS-S1, JOB 231: SE37 in LINK) LOAD libraries; every member is rebuilt from git by a build
    or probe deck."""
    out = job_card('PACCMP10', 'PACMAN COMPRESS')
    for i, lib in enumerate(('COBOL', 'COPY', 'LOAD'), 1):
        out += (f'//CMP{i}     EXEC PGM=IEBCOPY\n//SYSPRINT DD SYSOUT=A\n'
                f'//LIB      DD DSN={pfx}.{lib},DISP=OLD\n'
                '//SYSUT3   DD UNIT=SYSDA,SPACE=(TRK,(5,5))\n'
                '//SYSUT4   DD UNIT=SYSDA,SPACE=(TRK,(5,5))\n'
                '//SYSIN    DD *\n  COPY INDD=LIB,OUTDD=LIB\n/*\n')
    return out + '//\n'


def clist_deck(pfx):
    return (job_card('PACCLS10', 'PACMAN CLIST') + '//* STORES/REPLACES THE TSO LAUNCHER MEMBER PACMAN.\n'
            '//STORE    EXEC PGM=IEBGENER\n//SYSPRINT DD SYSOUT=A\n'
            f'//SYSUT2   DD DSN={pfx}.CLIST(PACMAN),DISP=OLD\n//SYSIN    DD DUMMY\n'
            '//SYSUT1   DD DATA,DLM=ZZ\n' + clist_text(pfx) + 'ZZ\n//\n')


def run_deck(pfx, cards):
    return (job_card('PACRUN10', 'PACMAN RUN') + '//* PLAYS THE INSTALLED GAME IN BATCH: ONE COMMAND PER CARD BELOW\n'
            '//* (OPTIONAL FIRST CARD AI<L> <N>, THEN U/D/L/R, Q TO QUIT).\n'
            + run_step('PLAY', pfx, 'PACMAIN', text_of(cards)) + '//\n')


# MVS-G0 extra checks on the installed load module: optional metrics, and the display replaced without recompiling
# the core (alternative PACDISP linked over LOAD(PACMAIN) into LOAD(PACALT)).
G0_METRICS = [('MET1', 'MOVES', 'BAT'), ('MET2', 'P2N3', 'BAT'), ('MET3', 'MULTI', 'TSO'), ('MET4', 'TSORDR', 'TSO')]
G0_ALT = [('ALT1', 'MOVES', 'BAT'), ('ALT2', 'MULTI', 'BAT'), ('ALT3', 'TSORDR', 'TSO')]


def mode_run(step, pfx, load, case, mode, metric):
    flag = 'M' if metric else ''
    if mode == 'TSO':
        parm, cards = tso_parm_and_cards(case)
        parm = (parm + ' AI1 1' if parm == 'TSO' else parm).ljust(10) + flag
    else:
        parm, cards = 'BAT'.ljust(10) + flag, text_of(ROOT / f'tests/cases/{case}.txt')
    return run_step(step, pfx, load, cards, parm=parm.rstrip() or None)


def g0x_deck(pfx):
    out = job_card('PACG0X01', 'PACMAN G0 CHECKS') + f'//* PREFIX {pfx}\n'
    for step, case, mode in G0_METRICS:
        out += mode_run(step, pfx, 'PACMAIN', case, mode, True)
    out += upload('SRCX', pfx, 'COBOL', 'PACDSPX', text_of(ROOT / 'src/cobol/alt/PACDSPX.cob'))
    out += compile_step('COBX', pfx, 'PACDSPX', 'OBJX')
    out += ("//LINKALT  EXEC PGM=IEWL,COND=(0,NE),PARM='LIST,XREF'\n"
            '//SYSLIN   DD DSN=&&OBJX,DISP=(OLD,DELETE)\n//         DD DDNAME=SYSIN\n'
            f'//LOADIN   DD DSN={pfx}.LOAD,DISP=SHR\n'
            f'//SYSLMOD  DD DSN={pfx}.LOAD(PACALT),DISP=OLD\n'
            '//SYSLIB   DD DSN=SYS1.COBLIB,DISP=SHR\n'
            '//SYSUT1   DD UNIT=SYSDA,SPACE=(1024,(50,20))\n'
            '//SYSPRINT DD SYSOUT=A\n//SYSIN    DD *\n INCLUDE LOADIN(PACMAIN)\n ENTRY PACMAIN\n/*\n')
    for step, case, mode in G0_ALT:
        out += mode_run(step, pfx, 'PACALT', case, mode, False)
    return out + '//\n'


def g1p_deck(pfx):
    """MVS-G1 capability probe: PACG1P (COBOL) + PACFS (assembler) -> LOAD(PACG1P), launcher CLIST G1PROBE,
    and one batch run (must report 'not a TSO session')."""
    out = job_card('PACG1P01', 'PACMAN G1 PROBE') + f'//* PREFIX {pfx}\n'
    out += upload('SRC1', pfx, 'COBOL', 'PACG1P', text_of(ROOT / 'src/probe/PACG1P.cob'))
    out += compile_step('COB1', pfx, 'PACG1P', 'OBJ1')
    out += asm_step('ASM1', 'OBJA1', text_of(ROOT / 'src/probe/PACFS.asm'))
    out += link_step(pfx, ['OBJ1', 'OBJA1'], 'PACG1P', 'PACG1P')
    out += upload('CLS1', pfx, 'CLIST', 'G1PROBE',
                  text_of(ROOT / 'src/probe/G1PROBE.clist').replace('@@PREFIX@@', pfx))
    out += run_step('BATCH', pfx, 'PACG1P', None)
    return out + '//\n'


def g1q_deck(pfx):
    """MVS-G1 probe 2 (single hypothesis H1): PACG1Q + PACFS2 -> LOAD(PACG1Q), CLIST G1PROBE2, one batch run."""
    out = job_card('PACG1Q01', 'PACMAN G1 PROBE2') + f'//* PREFIX {pfx}\n'
    out += upload('SRC1', pfx, 'COBOL', 'PACG1Q', text_of(ROOT / 'src/probe/PACG1Q.cob'))
    out += compile_step('COB1', pfx, 'PACG1Q', 'OBJ1')
    out += asm_step('ASM1', 'OBJA1', text_of(ROOT / 'src/probe/PACFS2.asm'))
    out += link_step(pfx, ['OBJ1', 'OBJA1'], 'PACG1Q', 'PACG1Q')
    for i, m in enumerate(('G1PROBE2', 'G1PROBE3', 'G1PROBE4', 'G1PROBE5'), 1):
        out += upload(f'CLS{i}', pfx, 'CLIST', m, text_of(ROOT / f'src/probe/{m}.clist').replace('@@PREFIX@@', pfx))
    out += run_step('BATCH', pfx, 'PACG1Q', None)
    out += run_step('BATCHC', pfx, 'PACG1Q', None, parm='C')
    out += run_step('BATCHK', pfx, 'PACG1Q', None, parm='K')
    out += run_step('BATCHQ', pfx, 'PACG1Q', None, parm='Q')
    return out + '//\n'


def g3p_deck(pfx):
    """MVS-G3 probe E6 (partial TPUT): PACG3P + PACFS3 -> LOAD(PACG3P), CLIST G3PROBE, one batch run per variant."""
    out = job_card('PACG3P01', 'PACMAN G3 PROBE') + f'//* PREFIX {pfx}\n'
    out += upload('SRC1', pfx, 'COBOL', 'PACG3P', text_of(ROOT / 'src/probe/PACG3P.cob'))
    out += compile_step('COB1', pfx, 'PACG3P', 'OBJ1')
    out += asm_step('ASM1', 'OBJA1', text_of(ROOT / 'src/probe/PACFS3.asm'))
    out += link_step(pfx, ['OBJ1', 'OBJA1'], 'PACG3P', 'PACG3P')
    out += upload('CLS1', pfx, 'CLIST', 'G3PROBE', text_of(ROOT / 'src/probe/G3PROBE.clist').replace('@@PREFIX@@', pfx))
    out += run_step('BATCH', pfx, 'PACG3P', None)
    return out + '//\n'


def e7p_deck(pfx):
    """MVS-G3 probe E7 (idle tick visibility): PACE7P + PACFS7 -> LOAD(PACE7P), CLIST E7PROBE, one batch run."""
    out = job_card('PACE7P01', 'PACMAN G3 PROBE E7') + f'//* PREFIX {pfx}\n'
    out += upload('SRC1', pfx, 'COBOL', 'PACE7P', text_of(ROOT / 'src/probe/PACE7P.cob'))
    out += compile_step('COB1', pfx, 'PACE7P', 'OBJ1')
    out += asm_step('ASM1', 'OBJA1', text_of(ROOT / 'src/probe/PACFS7.asm'))
    out += link_step(pfx, ['OBJ1', 'OBJA1'], 'PACE7P', 'PACE7P')
    out += upload('CLS1', pfx, 'CLIST', 'E7PROBE', text_of(ROOT / 'src/probe/E7PROBE.clist').replace('@@PREFIX@@', pfx))
    out += run_step('BATCH', pfx, 'PACE7P', None)
    return out + '//\n'


def e8p_deck(pfx):
    """MVS-G3 probe E8 (protocol bisect from E6): PACE8P + PACFS8 -> LOAD(PACE8P), CLIST E8PROBE, one batch run."""
    out = job_card('PACE8P01', 'PACMAN G3 PROBE E8') + f'//* PREFIX {pfx}\n'
    out += upload('SRC1', pfx, 'COBOL', 'PACE8P', text_of(ROOT / 'src/probe/PACE8P.cob'))
    out += compile_step('COB1', pfx, 'PACE8P', 'OBJ1')
    out += asm_step('ASM1', 'OBJA1', text_of(ROOT / 'src/probe/PACFS8.asm'))
    out += link_step(pfx, ['OBJ1', 'OBJA1'], 'PACE8P', 'PACE8P')
    out += upload('CLS1', pfx, 'CLIST', 'E8PROBE', text_of(ROOT / 'src/probe/E8PROBE.clist').replace('@@PREFIX@@', pfx))
    out += run_step('BATCH', pfx, 'PACE8P', None)
    return out + '//\n'


def g4p_deck(pfx):
    """MVS-G4 probe E9 (second character set via GE / SA X'43', full Query Reply): PACG4P + PACFS9 -> LOAD(PACG4P),
    CLIST G4PROBE, one batch run (must end with RC 4: not a TSO session)."""
    out = job_card('PACG4P01', 'PACMAN G4 PROBE E9') + f'//* PREFIX {pfx}\n'
    out += upload('SRC1', pfx, 'COBOL', 'PACG4P', text_of(ROOT / 'src/probe/PACG4P.cob'))
    out += compile_step('COB1', pfx, 'PACG4P', 'OBJ1')
    out += asm_step('ASM1', 'OBJA1', text_of(ROOT / 'src/probe/PACFS9.asm'))
    out += link_step(pfx, ['OBJ1', 'OBJA1'], 'PACG4P', 'PACG4P')
    out += upload('CLS1', pfx, 'CLIST', 'G4PROBE', text_of(ROOT / 'src/probe/G4PROBE.clist').replace('@@PREFIX@@', pfx))
    out += run_step('BATCH', pfx, 'PACG4P', None)
    return out + '//\n'


def g5p_deck(pfx):
    """MVS-G5 probe E10 (Programmed Symbols, isolated from PACMAN): PACG5P + PACFSA -> LOAD(PACG5P), CLIST G5PROBE,
    one batch run (must end with RC 4 and LOADRC=NONE: not a TSO session, nothing sent)."""
    out = job_card('PACG5P01', 'PACMAN G5 PROBE E10') + f'//* PREFIX {pfx}\n'
    out += upload('SRC1', pfx, 'COBOL', 'PACG5P', text_of(ROOT / 'src/probe/PACG5P.cob'))
    out += compile_step('COB1', pfx, 'PACG5P', 'OBJ1')
    out += asm_step('ASM1', 'OBJA1', text_of(ROOT / 'src/probe/PACFSA.asm'))
    out += link_step(pfx, ['OBJ1', 'OBJA1'], 'PACG5P', 'PACG5P')
    out += upload('CLS1', pfx, 'CLIST', 'G5PROBE', text_of(ROOT / 'src/probe/G5PROBE.clist').replace('@@PREFIX@@', pfx))
    out += run_step('BATCH', pfx, 'PACG5P', None)
    return out + '//\n'


def gsp_deck(pfx):
    """Scaled-renderer study, probe E11 (2x2/3x2/4x2 layouts, isolated from PACMAN): PACGSP + PACFSB -> LOAD(PACGSP),
    CLIST GSPROBE, one batch run (must end with RC 4: not a TSO session, nothing sent)."""
    out = job_card('PACGSP01', 'PACMAN PROBE E11') + f'//* PREFIX {pfx}\n'
    out += upload('SRC1', pfx, 'COBOL', 'PACGSP', text_of(ROOT / 'src/probe/PACGSP.cob'))
    out += compile_step('COB1', pfx, 'PACGSP', 'OBJ1')
    out += asm_step('ASM1', 'OBJA1', text_of(ROOT / 'src/probe/PACFSB.asm'))
    out += link_step(pfx, ['OBJ1', 'OBJA1'], 'PACGSP', 'PACGSP')
    out += upload('CLS1', pfx, 'CLIST', 'GSPROBE', text_of(ROOT / 'src/probe/GSPROBE.clist').replace('@@PREFIX@@', pfx))
    out += run_step('BATCH', pfx, 'PACGSP', None)
    return out + '//\n'


def gep_deck(pfx):
    """MVS-GS geometry probe E12 (alternate screen size via Erase/Write Alternate, isolated from PACMAN): PACGEP + PACFSC
    -> LOAD(PACGEP), CLIST GEPROBE, one batch run (must print 'NOT A TSO SESSION')."""
    out = job_card('PACGEP01', 'PACMAN PROBE E12') + f'//* PREFIX {pfx}\n'
    out += upload('SRC1', pfx, 'COBOL', 'PACGEP', text_of(ROOT / 'src/probe/PACGEP.cob'))
    out += compile_step('COB1', pfx, 'PACGEP', 'OBJ1')
    out += asm_step('ASM1', 'OBJA1', text_of(ROOT / 'src/probe/PACFSC.asm'))
    out += link_step(pfx, ['OBJ1', 'OBJA1'], 'PACGEP', 'PACGEP')
    out += upload('CLS1', pfx, 'CLIST', 'GEPROBE', text_of(ROOT / 'src/probe/GEPROBE.clist').replace('@@PREFIX@@', pfx))
    out += run_step('BATCH', pfx, 'PACGEP', None)
    return out + '//\n'


def s1p_deck(pfx):
    """MVS-S1 probe E15 (3270 WCC alarm, isolated from PACMAN): PACS1P + PACS1A (tools/gen_probe_e15.py) + the UNCHANGED
    production PACFSIO -> LOAD(PACS1P), CLIST S1PROBE, one batch run (must print 'E15 RC=0004': not a TSO session,
    nothing sent)."""
    out = job_card('PACS1P01', 'PACMAN S1 PROBE E15') + f'//* PREFIX {pfx}\n'
    out += upload('SRC1', pfx, 'COBOL', 'PACS1P', text_of(ROOT / 'src/probe/PACS1P.cob'))
    out += compile_step('COB1', pfx, 'PACS1P', 'OBJ1')
    out += asm_step('ASM1', 'OBJA1', text_of(ROOT / 'src/probe/PACS1A.asm'))
    out += asm_step('ASM2', 'OBJA2', text_of(ROOT / 'src/asm/PACFSIO.asm'))
    out += link_step(pfx, ['OBJ1', 'OBJA1', 'OBJA2'], 'PACS1P', 'PACS1P')
    out += upload('CLS1', pfx, 'CLIST', 'S1PROBE', text_of(ROOT / 'src/probe/S1PROBE.clist').replace('@@PREFIX@@', pfx))
    out += run_step('BATCH', pfx, 'PACS1P', None)
    return out + '//\n'


def rtp_deck(pfx):
    """MVS-RT probe E14 (timing / input, isolated from PACMAN): PACRTP + probe clock service PACRTA, linked with the
    UNCHANGED production modules compiled from the library members of the mvs-gs build (PACGAME PACMAP PACAI PACSCR
    PACPLAT PACQRY) and assembled from the repository (PACFSIO PACTSO) -> LOAD(PACRTP), CLIST RTPROBE, log datasets
    E14Q/E14N/E14T/E14U (created if missing), one batch run (TSD 120x27: clock-only and compose-only segments)."""
    out = job_card('PACRTP01', 'PACMAN PROBE E14') + f'//* PREFIX {pfx}\n'
    out += '//ALOG     EXEC PGM=IEFBR14\n'
    for s in 'QNTU':
        out += (f'//E14{s}     DD DSN={pfx}.E14{s},DISP=(MOD,CATLG),\n'
                '//            UNIT=SYSDA,SPACE=(TRK,(30,15)),\n'
                '//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)\n')
    out += upload('SRC1', pfx, 'COBOL', 'PACRTP', text_of(ROOT / 'src/probe/PACRTP.cob'))
    mods = ['PACRTP', 'PACGAME', 'PACMAP', 'PACAI', 'PACSCR', 'PACPLAT', 'PACQRY']
    for i, m in enumerate(mods, 1):
        out += compile_step(f'COB{i}', pfx, m, f'OBJ{i}')
    asms = [('PACRTA', ROOT / 'src/probe/PACRTA.asm'), ('PACFSIO', ROOT / 'src/asm/PACFSIO.asm'),
            ('PACTSO', ROOT / 'src/asm/PACTSO.asm')]
    for i, (m, path) in enumerate(asms, 1):
        out += asm_step(f'ASM{i}', f'OBJA{i}', text_of(path))
    out += link_step(pfx, [f'OBJ{i}' for i in range(1, 8)] + ['OBJA1', 'OBJA2', 'OBJA3'], 'PACRTP', 'PACRTP')
    out += upload('CLS1', pfx, 'CLIST', 'RTPROBE', text_of(ROOT / 'src/probe/RTPROBE.clist').replace('@@PREFIX@@', pfx))
    out += ("//BATCH    EXEC PGM=PACRTP,COND=(0,NE),PARM='BA'\n"
            f'//STEPLIB  DD DSN={pfx}.LOAD,DISP=SHR\n'
            '//E14LOG   DD SYSOUT=A\n//SYSOUT   DD SYSOUT=A\n//SYSUDUMP DD SYSOUT=A\n')
    return out + '//\n'


def rtl_deck(pfx):
    """MVS-RT probe E14: print the four log datasets (after the live runs)."""
    out = job_card('PACRTL01', 'PACMAN E14 LOGS')
    for i, s in enumerate('QNTU', 1):
        out += (f'//LIST{i}    EXEC PGM=IEBGENER\n//SYSPRINT DD SYSOUT=A\n//SYSIN    DD DUMMY\n'
                f'//SYSUT1   DD DSN={pfx}.E14{s},DISP=SHR\n//SYSUT2   DD SYSOUT=A\n')
    return out + '//\n'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('deck', choices=sorted(DECKS) + ['ALLOC', 'CLIST', 'RUN', 'G0X', 'G1P', 'G1Q', 'G3P', 'E7P', 'E8P', 'G4P', 'G5P', 'GSP', 'GEP', 'RTP', 'RTL', 'S1P', 'COMPRESS'])
    ap.add_argument('--hlq', default='HERC01', help='shorthand: prefix becomes HLQ.PACMAN')
    ap.add_argument('--prefix', help='dataset prefix, e.g. HERC01.PACMAN (default HLQ.PACMAN)')
    ap.add_argument('--cards', default='tests/cases/MOVES.txt', help='RUN: card file')
    ap.add_argument('--out', help='output file (default build/<DECK>.jcl)')
    a = ap.parse_args()
    pfx = a.prefix or f'{a.hlq}.PACMAN'
    if a.deck == 'ALLOC':
        text = alloc_deck(pfx)
    elif a.deck == 'CLIST':
        text = clist_deck(pfx)
    elif a.deck == 'COMPRESS':
        text = compress_deck(pfx)
    elif a.deck == 'S1P':
        text = s1p_deck(pfx)
    elif a.deck == 'RTP':
        text = rtp_deck(pfx)
    elif a.deck == 'RTL':
        text = rtl_deck(pfx)
    elif a.deck == 'GEP':
        text = gep_deck(pfx)
    elif a.deck == 'GSP':
        text = gsp_deck(pfx)
    elif a.deck == 'G5P':
        text = g5p_deck(pfx)
    elif a.deck == 'G4P':
        text = g4p_deck(pfx)
    elif a.deck == 'E8P':
        text = e8p_deck(pfx)
    elif a.deck == 'E7P':
        text = e7p_deck(pfx)
    elif a.deck == 'G3P':
        text = g3p_deck(pfx)
    elif a.deck == 'G1Q':
        text = g1q_deck(pfx)
    elif a.deck == 'G1P':
        text = g1p_deck(pfx)
    elif a.deck == 'G0X':
        text = g0x_deck(pfx)
    elif a.deck == 'RUN':
        text = run_deck(pfx, ROOT / a.cards)
    else:
        text = build(a.deck, pfx)
    dest = Path(a.out) if a.out else ROOT / 'build' / f'{a.deck}.jcl'
    dest.write_text(text, encoding='ascii')
    print(dest)
