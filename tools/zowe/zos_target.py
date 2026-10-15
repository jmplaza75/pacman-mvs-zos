"""z/OS target of tools/make_deck.py (ZOS-2, D45 build profile A; docs/zos-build.md).

make_deck.py --target zos DECK [--load MEMBER] [--job NAME] [--prefix P]
The MVS generator is reused unchanged; only its step builders are replaced for this process (apply()):
- upload: no in-stream upload step; the sources are the members tools/zowe/zos_sync.py uploaded and verified (IBM-037,
  fixed 80) in <prefix>.COBOL / COPY / ASM;
- compile: IGYCRCTL (Enterprise COBOL 6.5) with profile A, object into <prefix>.OBJ(<member>);
- assemble: ASMA90 (HLASM) from <prefix>.ASM(<member>), object into <prefix>.OBJ(<member>);
- link: IEWBLINK, INCLUDE OBJ(...), AMODE=24, RMODE=24, RENT, into <prefix>.LOAD(<load>);
- run: the MVS run step text itself (EXEC, PARM, STEPLIB, PACHS, SYSIN cards, SYSOUT) plus a CEEOPTS DD after STEPLIB
  and CEEDUMP; SYSUDUMP DUMMY. Cards, PARM and DDs stay the MVS ones;
- job card: CLASS=7, NOTIFY=&SYSUID (site rules), no MSGCLASS.
The default prefix is @@HLQ@@.PACMAN (rendered by tools/zowe/zos_submit.py; no HLQ literal in the repository).
Extra decks: ZCMP (Z2-1, diagnostic compile inventory: every release COBOL and assembler module, no bind, no run);
ZHSA (Z2-1b, PACHSIO assembled alone, compact listing); the ZOS-2 / ZOS-3 jobs of CHUNKS: a build job, or a
deterministic subset of the run steps of an MVS deck (or of several, SOURCES), each step taken verbatim from that deck's z/OS rendering, each job
kept well under the site limit of ~5,000 spool lines (docs/ZOS-ENVIRONMENT.md).
Listing options (no effect on the object code): COBOL NOSOURCE,NOXREF; HLASM PCONTROL(NOGEN) and no cross-reference
tables; binder LIST (no MAP). Build steps run with COND=(4,LT): RC 4 is accepted by the JCL only so that the known PACFSIO
ASMA303W (C3) does not flush the bind; the job is then judged on the exact per-step expectations (tools/zowe/zos_plan.py).
"""
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
PREFIX = '@@HLQ@@.PACMAN'
COBOL_PARM = ("('RENT,RMODE(24),DATA(24),NODYNAM',", "'TRUNC(STD),NUMPROC(NOPFD),NOSOURCE,NOXREF')")
ASM_PARM = ("('OBJECT,NODECK,PCONTROL(NOGEN)',", "'NOXREF,NORXREF,NODXREF,NOMXREF,NOESD,NORLD')")
BIND_PARM = 'LIST,AMODE=24,RMODE=24,RENT'
CEEOPTS = ['ALL31(OFF),STACK(,,BELOW)']
JOBNAME = None
PREFIX_IN_USE = [PREFIX]
OBJ = {}                  # make_deck temporary object name -> object member
LOAD = 'PACZ2D'
# name -> (job name, MVS deck whose z/OS rendering gives the steps, steps in deck order, extra LE options, oracle job)
CHUNKS = {
    'Z2BLD': ('PACZ2BLD', 'REL20', [f'COB{i}' for i in range(1, 11)] + ['ASM1', 'ASM2', 'ASM3', 'LINK'], None, None),
    'Z2DRV': ('PACZ2DRV', 'GP2', ['COBQ1', 'LINKQ', 'QRY1', 'COBT', 'LINKT', 'TSOT1'], None, 310),
    'Z2C1': ('PACZ2C1', 'REL20', ['RUN1', 'RUN2', 'RUN3', 'RUN4', 'RUN5'], None, 307),
    'Z2C2': ('PACZ2C2', 'REL20', ['RUN6', 'RUN7', 'RUN8'], None, 307),
    'Z2C3': ('PACZ2C3', 'REL20', ['RUN9'], None, 307),
    'Z2C4': ('PACZ2C4', 'REL20', ['RUN10'], None, 307),
    'Z2C5': ('PACZ2C5', 'REL20', ['RUN11', 'RUN12'], None, 307),
    'Z2C6': ('PACZ2C6', 'REL20', ['RUN13', 'RUN14', 'RUN15', 'RUN16'], None, 307),
    'Z2C7': ('PACZ2C7', 'REL20', ['RUN17', 'RUN18', 'RUN19', 'TSO1', 'TSO2', 'TSO3', 'TSO4', 'TSO5', 'TSO6'], None, 307),
    'Z2ST0': ('PACZ2ST0', 'GP2', ['RUN3', 'RUN13', 'TSO3', 'G2B21', 'G2R7'], 'STORAGE(00,NONE,00)', 310),
    'Z2STF': ('PACZ2STF', 'GP2', ['RUN3', 'RUN13', 'TSO3', 'G2B21', 'G2R7'], 'STORAGE(FF,NONE,FF)', 310),
    'Z2G1': ('PACZ2G1', 'GP2', ['G2B1', 'G2B2', 'G2B9', 'G2B12', 'G2B21', 'G2B33', 'G2B45', 'G2B49', 'G2B55', 'G2T1'],
             None, 310),
    'Z2G2': ('PACZ2G2', 'GP2', ['RTB1', 'RTB7', 'RTB8', 'RTB10', 'RTB11', 'G2R1', 'G2R5', 'G2R7'], None, 310),
    'Z2G3': ('PACZ2G3', 'GP2', ['G2B19', 'G2T3'], None, 310),
    'Z2RP': ('PACZ2RP', 'RP', ['R3B1', 'R3B2', 'R3B4', 'R3B5', 'R3B6', 'R3B7', 'R3B9'], None, 309),
    'Z2S2': ('PACZ2S2', 'S2', ['S2L1', 'S2L2', 'S2L4'], None, 308),
    # ZOS-3 (docs/zos3-design.md): the PACFSIO batch contract, the only two TSO + COLOR(AUTO) runs of the oracles
    'Z3FS': ('PACZ3FS', 'GP2+S2', ['S1S3', 'S2L4'], None, '310+308'),
    # ZOS-3 PACZ3TD1..4: the minimum ALARM(PATTERN) TSD set (docs/zos3-pacz3tsd-review.md): the 12 S2T runs that
    # together reach every D41 edge of tests/test_s2.py (9 are the only run of an edge), in deck order, under the budget
    'Z3TSD1': ('PACZ3TD1', 'S2', ['S2T1', 'S2T3', 'S2T5', 'S2T6', 'S2T7'], None, 308),
    'Z3TSD2': ('PACZ3TD2', 'S2', ['S2T8', 'S2T9', 'S2T10'], None, 308),
    'Z3TSD3': ('PACZ3TD3', 'S2', ['S2T13', 'S2T17', 'S2T25'], None, 308),
    'Z3TSD4': ('PACZ3TD4', 'S2', ['S2T23'], None, 308),
}
# chunks whose steps come from more than one MVS deck: step -> (MVS deck, oracle job of that deck)
SOURCES = {'Z3FS': {'S1S3': ('GP2', 310), 'S2L4': ('S2', 308)}}
# ZOS-3 PACZ3HS1..8 (user decision 2026-10-15, option A): the frozen HS runs in their frozen order, split under the spool
# budget; HA6 (5,262 lines alone) deferred to ZOS-9/10; HSCLS1/2 + HSCLT (CLIST block) -> ZOS-4; HSP1..9 replaced by
# read-only catalog / member / content checks; HSDEL9 is a DELETE (never).
HS_JOBS = {'Z3HS1': ['HA1', 'HA2', 'HA3'], 'Z3HS2': ['HA4'], 'Z3HS3': ['HA5'], 'Z3HS4': ['HA7', 'HA8'],
           'Z3HS5': ['HB1', 'HC1', 'HD1'], 'Z3HS6': ['HE1', 'HE2', 'HF1', 'HF2'], 'Z3HS7': ['HG1', 'HG2', 'HG3'],
           'Z3HS8': ['HH1', 'HTSO1', 'HTSO2']}
HS_DEFERRED = ['HA6']
DECKS = ['ZCMP', 'ZHSA', 'Z3HA'] + list(HS_JOBS) + ['Z4CL', 'Z4LE', 'Z4Z2'] + list(CHUNKS)
# ZOS-4 PACZ4LE (docs/zos4-le-diagnostic.md): LE runtime-option diagnostic with the ZOS-1 probes (no Pac-Man):
# (step, program, PARM, CEEOPTS records or None). ZHARG is not an LE option name: the program's PARM echo shows which
# side of the '/' LE gave it (CBLOPTS(ON): arguments/options).
Z4LE_STEPS = [('D1', 'ZHELLO31', 'ZHARG/RPTOPTS(ON)', None),
              ('D2', 'ZHELLO24', 'ZHARG/RPTOPTS(ON)', 'ALL31(OFF),STACK(,,BELOW)'),
              ('D3', 'ZHELLO31', 'ZHARG/STACK(,,ANYWHERE),RPTOPTS(ON)', 'ALL31(ON),STACK(,,BELOW)')]
# ZOS-4 PACZ4CL (docs/zos4-design.md): the CLIST PARM lines (MVS G8CLS / G8CLT) and the HS CLIST block (MVS HSCLS1/2 +
# HSCLT) under the TMP in batch, with fresh attempt datasets instead of DELETE: a work PDS for the test CLISTs, a DATA
# PDS for the present path, a prefix whose DATA is never allocated for the missing path
Z4_ATTEMPT = 'T1'
Z4_SETS = {'work': ('Z4CL', '(TRK,(2,1,2))'), 'present': ('Z4HSY', None), 'missing': ('Z4HSN', None),
           'cee_present': ('Z4CEY', None), 'cee_missing': ('Z4CEN', None)}


def zos_clist_text(pfx):
    """The z/OS CLIST (src/zos/PACMAN.clist: the 2.0 CLIST + Z-entry Z2) for a prefix."""
    return (R / 'src/zos/PACMAN.clist').read_text(encoding='ascii').replace('@@PREFIX@@', pfx)


Z4Z2_SETS = {'work': 'Z4CL.T2', 'cee_present': 'Z4CY2', 'cee_missing': 'Z4CN2'}   # ZOS-4 Z2 attempt T2


def z2_test_clist(prefix, listing=False):
    """PACZ4CL Z2 test member: the Z2 lines of the z/OS CLIST verbatim (rendered with prefix), the CALL replaced by a
    marker and a LISTALC (nothing is called), SYSIN / SYSOUT allocated DUMMY first as the CLIST allocates them DA(*)."""
    lines = zos_clist_text(prefix).splitlines()
    i = lines.index(next(l for l in lines if l.startswith('/* Z2 (ZOS-4)')))
    j = lines.index('FREE F(CEEOPTS)')
    block = [l for l in lines[i:j + 1]]
    k = next(n for n, l in enumerate(block) if l.startswith('CALL '))
    block[k:k + 1] = ['WRITE Z2 CALL REACHED', 'LISTALC STATUS']
    return ('PROC 0\n' + ('CONTROL LIST\n' if listing else '') + 'SET &W = C\nALLOC F(SYSIN) DUMMY REUSE\n'
            'ALLOC F(SYSOUT) DUMMY REUSE\n' + '\n'.join(block)
            + '\nLISTALC STATUS\nFREE F(SYSIN SYSOUT)\nWRITE Z2 END\n')
# ZOS-3 PACZ3HA (docs/zos3-design.md): the high-score test PDSs of one attempt (fresh, never deleted; a rerun uses the
# next suffix). Only the two PDSs the batch HS runs use; HSCL.DATA belongs to the CLIST block check (ZOS-4).
HS_ATTEMPT = 'T1'
HS_SETS = [('HSTEST', '(TRK,(5,1,5))'), ('HSFULL', '(TRK,(5,1,1))')]
_md = []
ZCMP_COBOL = ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACQRY', 'PACRT',
              'PACQRYT', 'PACTSOT']
ZCMP_ASM = ['PACTSO', 'PACFSIO', 'PACHSIO']
UT = '//{0:<9}DD UNIT=SYSALLDA,SPACE=(TRK,(5,5))\n'
COB_LIBS = ('//STEPLIB  DD DSN=IGY650.SIGYCOMP,DISP=SHR\n//         DD DSN=CEE.SCEERUN,DISP=SHR\n'
            '//         DD DSN=CEE.SCEERUN2,DISP=SHR\n')
ASM_LIBS = ('//STEPLIB  DD DSN=HLA.SASMMOD1,DISP=SHR\n'
            '//SYSLIB   DD DSN=SYS1.MACLIB,DISP=SHR\n//         DD DSN=SYS1.MODGEN,DISP=SHR\n')
_mvs = {}


def job_card(job, title):
    return (f"//{JOBNAME or job} JOB 1,'{title[:20]}',CLASS=7,MSGLEVEL=(1,1),\n"
            '//             NOTIFY=&SYSUID\n')


def upload(step, pfx, lib, member, text):
    want = (R / f'src/{"cobol" if lib == "COBOL" else "copy"}/{member}.{"cob" if lib == "COBOL" else "cpy"}')
    assert want.read_text(encoding='ascii') == text, f'{lib}({member}) is not the shared source'
    return ''


def cobol_work():
    return ''.join(UT.format(f'SYSUT{i}') for i in range(1, 16)) + '//SYSMDECK DD UNIT=SYSALLDA,SPACE=(TRK,(5,5))\n'


def compile_step(step, pfx, member, obj):
    OBJ[obj] = member
    return (f'//{step:<8} EXEC PGM=IGYCRCTL,COND=(4,LT),REGION=0M,\n'
            f'//             PARM={COBOL_PARM[0]}\n//             {COBOL_PARM[1]}\n' + COB_LIBS +
            f'//SYSIN    DD DSN={pfx}.COBOL({member}),DISP=SHR\n//SYSLIB   DD DSN={pfx}.COPY,DISP=SHR\n'
            f'//SYSPRINT DD SYSOUT=*\n//SYSLIN   DD DSN={pfx}.OBJ({member}),DISP=SHR\n' + cobol_work())


def asm_member(text):
    for p in sorted((R / 'src/asm').glob('*.asm')):
        if p.read_text(encoding='ascii') == text:
            return p.stem
    raise SystemExit('z/OS target: an assembler source outside src/asm (probe) has no uploaded member')


def asm_step(step, obj, text):
    member = asm_member(text)
    OBJ[obj] = member
    pfx = PREFIX_IN_USE[0]
    return (f'//{step:<8} EXEC PGM=ASMA90,COND=(4,LT),\n//             PARM={ASM_PARM[0]}\n'
            f'//             {ASM_PARM[1]}\n' + ASM_LIBS +
            f'//SYSIN    DD DSN={pfx}.ASM({member}),DISP=SHR\n//SYSPRINT DD SYSOUT=*\n'
            f'//SYSLIN   DD DSN={pfx}.OBJ({member}),DISP=SHR\n' + UT.format('SYSUT1'))



def link_step(pfx, objs, load, entry, step='LINK'):
    t = (f'//{step:<8} EXEC PGM=IEWBLINK,COND=(4,LT),\n//             PARM=\'{BIND_PARM}\'\n'
         '//SYSLIB   DD DSN=CEE.SCEELKEX,DISP=SHR\n//         DD DSN=CEE.SCEELKED,DISP=SHR\n'
         f'//OBJ      DD DSN={pfx}.OBJ,DISP=SHR\n//SYSLMOD  DD DSN={pfx}.LOAD,DISP=SHR\n'
         '//SYSPRINT DD SYSOUT=*\n//SYSLIN   DD *\n')
    t += ''.join(f'  INCLUDE OBJ({OBJ[o]})\n' for o in objs)
    return t + f'  ENTRY {entry}\n  NAME {load}(R)\n/*\n'


def run_step(step, pfx, load, sysin, parm=None, dd=None, cond='(0,NE)'):
    if parm is not None:
        assert '/' not in parm, f'{step}: a slash in the PARM would be read by LE as runtime options'
    t = _mvs['run_step'](step, pfx, load, sysin, parm=parm, dd=dd, cond=cond)
    lib = f'//STEPLIB  DD DSN={pfx}.LOAD,DISP=SHR\n'
    tail = '//SYSOUT   DD SYSOUT=A\n//SYSUDUMP DD SYSOUT=A\n'
    assert t.count(lib) == 1 and t.endswith(tail), step
    t = t.replace(lib, lib + '//CEEOPTS  DD *\n' + ''.join(c + '\n' for c in CEEOPTS) + '/*\n')
    return t[:-len(tail)] + '//SYSOUT   DD SYSOUT=A\n//CEEDUMP  DD SYSOUT=A\n//SYSUDUMP DD DUMMY\n'


def no_clist(pfx):
    return ''        # ZOS-2 excludes the CLIST (ZOS-6); the REL20 CLIST PARM steps are left out


def apply(md, prefix):
    """Replace the step builders of the make_deck module md for this process (the MVS code is not edited)."""
    PREFIX_IN_USE[0] = prefix
    _md[:] = [md]
    for name in ('job_card', 'upload', 'compile_step', 'asm_step', 'link_step', 'run_step', 'g8_clist_steps'):
        _mvs[name] = getattr(md, name)
    md.job_card, md.upload, md.compile_step, md.asm_step = job_card, upload, compile_step, asm_step
    md.link_step, md.run_step, md.g8_clist_steps = link_step, run_step, no_clist


def zcmp_deck(pfx):
    """Z2-1 PACZ2CMP: compile-only diagnostic inventory. No COND: every module is compiled whatever the others give."""
    out = job_card('PACZ2CMP', 'PACMAN ZOS2')
    out += ('//CBL      PROC M=\n//C        EXEC PGM=IGYCRCTL,REGION=0M,\n'
            "//             PARM=('RENT,RMODE(24),DATA(24),NODYNAM',\n"
            "//             'TRUNC(STD),NUMPROC(NOPFD),NOSOURCE,NOXREF')\n" + COB_LIBS +
            f'//SYSIN    DD DSN={pfx}.COBOL(&M),DISP=SHR\n//SYSLIB   DD DSN={pfx}.COPY,DISP=SHR\n'
            f'//SYSPRINT DD SYSOUT=*\n//SYSLIN   DD DSN={pfx}.OBJ(&M),DISP=SHR\n' + cobol_work() +
            '//         PEND\n')
    out += ("//ASM      PROC M=\n//A        EXEC PGM=ASMA90,PARM='OBJECT,NODECK'\n" + ASM_LIBS +
            f'//SYSIN    DD DSN={pfx}.ASM(&M),DISP=SHR\n//SYSPRINT DD SYSOUT=*\n'
            f'//SYSLIN   DD DSN={pfx}.OBJ(&M),DISP=SHR\n' + UT.format('SYSUT1') + '//         PEND\n')
    out += ''.join(f'//{m:<8} EXEC CBL,M={m}\n' for m in ZCMP_COBOL)
    out += ''.join(f'//{m:<8} EXEC ASM,M={m}\n' for m in ZCMP_ASM)
    return out


def zhsa_deck(pfx):
    """Z2-1b PACZ2HSA: PACHSIO assembled alone (no source change), compact listing: macro expansions not printed
    (PCONTROL(NOGEN); diagnostics are still listed), no symbol / macro / DSECT cross-reference, ESD or RLD tables."""
    return (job_card('PACZ2HSA', 'PACMAN ZOS2') +
            f'//PACHSIO  EXEC PGM=ASMA90,\n//             PARM={ASM_PARM[0]}\n//             {ASM_PARM[1]}\n' +
            ASM_LIBS + f'//SYSIN    DD DSN={pfx}.ASM(PACHSIO),DISP=SHR\n//SYSPRINT DD SYSOUT=*\n'
            f'//SYSLIN   DD DSN={pfx}.OBJ(PACHSIO),DISP=SHR\n' + UT.format('SYSUT1'))


def z3ha_deck(pfx):
    """ZOS-3 PACZ3HA: allocate <prefix>.HSTEST.<attempt> and <prefix>.HSFULL.<attempt> as real PDSs (DSNTYPE=PDS: a PDSE
    has no directory blocks, so the HH1 full-directory case needs a PDS), FB 80 with BLKSIZE 80 coded (PACHSIO accepts
    only F(B) 80/80; without it the system would choose a larger block size), catalogued also on an abnormal end (no
    DELETE anywhere; an existing dataset fails the allocation, nothing is reused). Then the frozen MVS HS setup steps,
    verbatim apart from the dataset names: HSSEED1..3 (members HS9, BAD, EMPTY) and HSFILL (IEBUPDTE: M01.. until the
    one directory block is full, IEB813I, RC 12). Last, a read-only TSO LISTDS of both PDSs (attributes + members)."""
    md = _md[0]
    mvs = steps_of_deck(md.hs_steps(pfx, LOAD))
    ren = {f'{pfx}.{n}': f'{pfx}.{n}.{HS_ATTEMPT}' for n, _ in HS_SETS}
    out = job_card('PACZ3HA', f'PACMAN ZOS3 Z3HA')
    out += '//ALLOC    EXEC PGM=IEFBR14\n'
    for i, (n, sp) in enumerate(HS_SETS, 1):
        out += (f'//D{i}       DD DSN={ren[pfx + "." + n]},DISP=(NEW,CATLG,CATLG),\n'
                f'//            DSNTYPE=PDS,DSORG=PO,RECFM=FB,LRECL=80,BLKSIZE=80,\n'
                f'//            SPACE={sp}\n')
    for s in ('HSSEED1', 'HSSEED2', 'HSSEED3', 'HSFILL'):
        text = mvs[s]
        for old, new in ren.items():
            text = re.sub(rf'DSN={re.escape(old)}([(,])', rf'DSN={new}\1', text)
        out += text
    out += ('//HSLIST   EXEC PGM=IKJEFT01,COND=EVEN\n//SYSTSPRT DD SYSOUT=A\n//SYSTSIN  DD *\n'
            + ''.join(f"  LISTDS '{d}' MEMBERS\n" for d in ren.values()) + '/*\n')
    return out


def z3hs_deck(name, pfx):
    """ZOS-3 PACZ3HS<n>: steps of the z/OS rendering of the frozen MVS HS deck, verbatim except: the two test PDSs are
    the attempt's (<prefix>.HSTEST.<attempt>, HSFULL.<attempt>); COND=(0,NE,LINK) -> COND=(0,NE) (no LINK step here: any
    non-zero RC flushes the rest of the job); the IKJEFT01 steps get the profile A CEEOPTS (LE reads the step's
    CEEOPTS DD for the CALLed program), CEEDUMP and SYSUDUMP DUMMY like every run step."""
    md = _md[0]
    mvs = steps_of_deck(md.hs_steps(pfx, LOAD))
    ren = {f'{pfx}.{n}': f'{pfx}.{n}.{HS_ATTEMPT}' for n, _ in HS_SETS}
    out = job_card(f'PACZ3HS{name[-1]}', f'PACMAN ZOS3 {name}')
    for s in HS_JOBS[name]:
        text = mvs[s]
        for old, new in ren.items():
            text = re.sub(rf"(DSN=|DA\('){re.escape(old)}([(,'])", rf'\g<1>{new}\2', text)
        assert text.count('COND=(0,NE,LINK)') == 1, s
        text = text.replace('COND=(0,NE,LINK)', 'COND=(0,NE)')
        if s.startswith('HTSO'):
            sysout = '//SYSOUT   DD SYSOUT=A\n'
            assert text.count(sysout) == 1 and 'CEEOPTS' not in text, s
            text = text.replace(sysout, sysout + '//CEEOPTS  DD *\n' + ''.join(c + '\n' for c in CEEOPTS) + '/*\n'
                                '//CEEDUMP  DD SYSOUT=A\n//SYSUDUMP DD DUMMY\n')
        out += text
    return out


def z4cl_deck(pfx):
    """ZOS-4 PACZ4CL: ALLOC (the work PDS <prefix>.Z4CL.<attempt> and the present-path DATA <prefix>.Z4HSY.DATA, both
    real PDSs FB 80/80 like the production DATA, catalogued also on an abnormal end, no DELETE); G8CLS = the MVS step
    (the PROC and PARM lines of the CLIST + WRITE G8PARM=&P=) into the work PDS; HSCLS1 / HSCLS2 = the MVS HS-block
    test CLISTs with the present / missing prefixes; Z2CEE writes the present-path project CEEOPTS (the record of every
    run's CEEOPTS); Z2CLS1..3 the Z2 test CLISTs (z2_test_clist) and the wrapper Z2RUN (writes Z2RC=&LASTCC); one TMP
    step: the 4 G8 keyword sets, the two HS-block CLISTs, then the three Z2 cases. Every step COND=(0,NE)."""
    md = _md[0]
    ds = f'{pfx}.{Z4_SETS["work"][0]}.{Z4_ATTEMPT}'
    yes, no = (f'{pfx}.{Z4_SETS[k][0]}' for k in ('present', 'missing'))
    out = job_card('PACZ4CL', 'PACMAN ZOS4 Z4CL')
    out += '//ALLOC    EXEC PGM=IEFBR14\n'
    for i, (d, sp) in enumerate(((ds, Z4_SETS['work'][1]), (yes + '.DATA', md.DATA_SPACE)), 1):
        out += (f'//D{i}       DD DSN={d},DISP=(NEW,CATLG,CATLG),\n'
                f'//            DSNTYPE=PDS,DSORG=PO,{md.DATA_DCB},\n//            SPACE={sp}\n')
    out += ('//G8CLS    EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD SYSOUT=A\n//SYSIN    DD DUMMY\n'
            f'//SYSUT2   DD DSN={ds}(PARMS),DISP=OLD\n//SYSUT1   DD DATA,DLM=ZZ\n'
            + '\n'.join(md.rp3_clist_lines(pfx)) + '\nWRITE G8PARM=&P=\nZZ\n')
    for i, (m, p) in enumerate((('HSCLY', yes), ('HSCLN', no)), 1):
        block = '\n'.join(md.hs_clist_block(p)) + '\n'
        clist = 'PROC 0\nSET &W = A\n' + block + 'LISTALC STATUS\nIF &W = A THEN FREE F(PACHS)\nWRITE HSCL END\n'
        assert all(len(l) <= 72 for l in clist.splitlines()), m
        out += (f'//HSCLS{i}   EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD SYSOUT=A\n//SYSIN    DD DUMMY\n'
                f'//SYSUT2   DD DSN={ds}({m}),DISP=OLD\n//SYSUT1   DD DATA,DLM=ZZ\n' + clist + 'ZZ\n')
    cy, cn = (f'{pfx}.{Z4_SETS[k][0]}' for k in ('cee_present', 'cee_missing'))
    out += ('//Z2CEE    EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD SYSOUT=A\n//SYSIN    DD DUMMY\n'
            f'//SYSUT2   DD DSN={cy}.CEEOPTS,DISP=(NEW,CATLG,CATLG),\n'
            f'//            {md.DATA_DCB},SPACE=(TRK,(1,1))\n'
            '//SYSUT1   DD *\n' + CEEOPTS[0] + '\n/*\n')
    for i, (m, text) in enumerate((('Z2Y', z2_test_clist(cy)), ('Z2N', z2_test_clist(cn)),
                                   ('Z2RUN', f"PROC 1 M\nEXEC '{ds}(&M)'\nWRITE Z2RC=&LASTCC\n")), 1):
        assert all(len(l) <= 72 for l in text.splitlines()), m
        out += (f'//Z2CLS{i}   EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD SYSOUT=A\n//SYSIN    DD DUMMY\n'
                f'//SYSUT2   DD DSN={ds}({m}),DISP=OLD\n//SYSUT1   DD DATA,DLM=ZZ\n' + text + 'ZZ\n')
    cmds = []
    for k in md.G8_CLIST:
        c = f"  EXEC '{ds}(PARMS)'" + (f" '{k}'" if k else '')
        cmds.append(c if len(c) <= 72 else f"  EXEC '{ds}(PARMS)' +\n  '{k}'")
    cmds += [f"  EXEC '{ds}(HSCLY)'", f"  EXEC '{ds}(HSCLN)'"]
    cmds += [f"  EXEC '{ds}(Z2RUN)' 'Z2Y'", f"  EXEC '{ds}(Z2RUN)' 'Z2N'",       # Z2 cases 1 and 2
             f"  ALLOC F(CEEOPTS) DA('{ds}(PARMS)') SHR",                         # case 3: a CEEOPTS DD exists
             f"  EXEC '{ds}(Z2RUN)' 'Z2Y'", '  LISTALC STATUS', '  FREE F(CEEOPTS)']
    assert all(len(x) <= 72 for c in cmds for x in c.split('\n')), 'a SYSTSIN card ends at column 72'
    out += ('//CLT      EXEC PGM=IKJEFT01,COND=(0,NE)\n//SYSTSPRT DD SYSOUT=A\n//SYSTSIN  DD *\n'
            + ''.join(c + '\n' for c in cmds) + '/*\n')
    return out


def z4le_deck(pfx):
    """ZOS-4 PACZ4LE: three runs of the ZOS-1 probe programs (ZHELLOC + ZHELLOA, already in <prefix>.LOAD), STEPLIB
    only, no dataset written, SYSOUT (DISPLAY and the LE MSGFILE) to the spool."""
    out = job_card('PACZ4LE', 'PACMAN ZOS4 Z4LE')
    for step, pgm, parm, cee in Z4LE_STEPS:
        out += (f"//{step:<8} EXEC PGM={pgm},COND=(0,NE),\n//             PARM='{parm}'\n"
                f'//STEPLIB  DD DSN={pfx}.LOAD,DISP=SHR\n')
        if cee:
            out += f'//CEEOPTS  DD *\n{cee}\n/*\n'
        out += '//SYSOUT   DD SYSOUT=A\n//CEEDUMP  DD SYSOUT=A\n//SYSUDUMP DD DUMMY\n'
    return out


def z4z2_deck(pfx):
    """ZOS-4 PACZ4Z2 (attempt T2): the three Z2 paths only (G8 / HS proved by JOB03750). As PACZ4CL's Z2 part, with:
    fresh T2 names; the current Z2 lines (SYSDSN result OK / DATASET NOT FOUND / anything else reported); CONTROL LIST in
    the test members, so every TSO command the CLIST issues is listed - the ALLOC F(CEEOPTS) line in case 3 proves the
    SYSDSN check passed and the ALLOC was reached; the IKJEFT01 step with DYNAMNBR=200 like the interactive logon proc
    DBPROCDG; a LISTALC right before and right after case 3 (the pre-existing DD must be identical)."""
    md = _md[0]
    ds = f'{pfx}.{Z4Z2_SETS["work"]}'
    cy, cn = (f'{pfx}.{Z4Z2_SETS[k]}' for k in ('cee_present', 'cee_missing'))
    out = job_card('PACZ4Z2', 'PACMAN ZOS4 Z4Z2')
    out += (f'//ALLOC    EXEC PGM=IEFBR14\n//D1       DD DSN={ds},DISP=(NEW,CATLG,CATLG),\n'
            f'//            DSNTYPE=PDS,DSORG=PO,{md.DATA_DCB},\n//            SPACE=(TRK,(2,1,2))\n')
    out += ('//Z2CEE    EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD SYSOUT=A\n//SYSIN    DD DUMMY\n'
            f'//SYSUT2   DD DSN={cy}.CEEOPTS,DISP=(NEW,CATLG,CATLG),\n'
            f'//            {md.DATA_DCB},SPACE=(TRK,(1,1))\n//SYSUT1   DD *\n' + CEEOPTS[0] + '\n/*\n')
    for i, (m, text) in enumerate((('Z2Y', z2_test_clist(cy, True)), ('Z2N', z2_test_clist(cn, True)),
                                   ('Z2RUN', f"PROC 1 M\nEXEC '{ds}(&M)'\nWRITE Z2RC=&LASTCC\n")), 1):
        assert all(len(l) <= 72 for l in text.splitlines()), m
        out += (f'//Z2CLS{i}   EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD SYSOUT=A\n//SYSIN    DD DUMMY\n'
                f'//SYSUT2   DD DSN={ds}({m}),DISP=OLD\n//SYSUT1   DD DATA,DLM=ZZ\n' + text + 'ZZ\n')
    cmds = [f"  EXEC '{ds}(Z2RUN)' 'Z2Y'", f"  EXEC '{ds}(Z2RUN)' 'Z2N'",
            f"  ALLOC F(CEEOPTS) DA('{ds}(Z2N)') SHR", '  LISTALC STATUS',
            f"  EXEC '{ds}(Z2RUN)' 'Z2Y'", '  LISTALC STATUS', '  FREE F(CEEOPTS)']
    assert all(len(c) <= 72 for c in cmds)
    out += ('//CLT      EXEC PGM=IKJEFT01,COND=(0,NE),DYNAMNBR=200\n//SYSTSPRT DD SYSOUT=A\n//SYSTSIN  DD *\n'
            + ''.join(c + '\n' for c in cmds) + '/*\n')
    return out


def steps_of_deck(text):
    """{step: text} of a deck, split at every EXEC statement (in-stream cards never start with //)."""
    import re
    parts = re.split(r'(?m)^(?=//\w+\s+EXEC )', text)
    return {re.match(r'//(\w+)', b).group(1): b for b in parts[1:]}


def chunk_deck(name, pfx):
    job, base, steps, extra, _ = CHUNKS[name]
    md = _md[0]
    if extra:
        CEEOPTS[:] = [CEEOPTS[0] + ',' + extra]
    if name in SOURCES:            # each step verbatim from its own deck; the step names are unique across them
        src = SOURCES[name]
        assert list(src) == steps and '+'.join(dict.fromkeys(d for d, _ in src.values())) == base, name
        decks = {d: steps_of_deck(md.build(d, pfx, LOAD)) for d in dict.fromkeys(d for d, _ in src.values())}
        assert all(sum(s in f for f in decks.values()) == 1 for s in steps), f'{name}: a step name is not unique'
        full = {s: decks[src[s][0]][s] for s in steps}
    else:
        full = steps_of_deck(md.build(base, pfx, LOAD))
    order = list(full)
    assert all(s in full for s in steps), [s for s in steps if s not in full]
    assert [s for s in order if s in steps] == steps, f'{name}: steps not in deck order'
    out = job_card(job, f'PACMAN ZOS{name[1]} {name}')
    for s in steps:
        t = full[s].replace('\n//\n', '\n') if full[s].endswith('\n//\n') else full[s]
        head = t.split('\n', 1)[0]
        assert re.search(r'COND=\((0,NE|4,LT)\)', head) or 'COND=' not in head, f'{s}: COND refers to other steps'
        out += t
    return out


import re  # noqa: E402


def deck(name, pfx):
    if name in CHUNKS:
        return chunk_deck(name, pfx)
    if name in HS_JOBS:
        return z3hs_deck(name, pfx)
    return {'ZCMP': zcmp_deck, 'ZHSA': zhsa_deck, 'Z3HA': z3ha_deck, 'Z4CL': z4cl_deck, 'Z4LE': z4le_deck,
            'Z4Z2': z4z2_deck}[name](pfx)
