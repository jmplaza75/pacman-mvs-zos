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


def link_step(pfx, objs, load, entry):
    t = "//LINK     EXEC PGM=IEWL,COND=(0,NE),PARM='LIST,XREF'\n"
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


ASM = {'MVS8': ['PACTSO'], 'RELEASE': ['PACTSO'], 'G0': ['PACTSO'], 'G1': ['PACTSO', 'PACFSIO'], 'G2': ['PACTSO', 'PACFSIO']}          # assembler stubs (src/asm/NAME.asm) linked with the COBOL objects


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
       'G2': ['MOVES', 'DIE1', 'P2', 'MULTI', 'C3N2', 'TSORDR']}
TSD = {'G1': ['MOVES', 'TSORDR', 'MULTI', 'C3N2', 'DIE1'],
       # G2: (case, highlight flag in PARM column 13): 5 with highlights, 2 without (= G1 screens)
       'G2': [('MOVES', 'Y'), ('TSORDR', 'Y'), ('MULTI', 'Y'), ('C3N2', 'Y'), ('DIE1', 'Y'), ('MOVES', 'N'), ('DIE1', 'N')]}   # colour screens dry run (PARM 'TSD ...', hex output)   # replayed in interactive mode (PARM='TSO')


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
            c, hilite = c
        parm, cards = tso_parm_and_cards(c)
        parm = 'TSD' + parm[3:]
        if hilite:
            parm = (parm + ' AI1 1' if parm == 'TSD' else parm).ljust(11) + 'N' + hilite
        out += run_step(f'TSD{i}', pfx, load, cards, parm=parm)
    return out + '//\n'


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


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('deck', choices=sorted(DECKS) + ['ALLOC', 'CLIST', 'RUN', 'G0X', 'G1P', 'G1Q'])
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
