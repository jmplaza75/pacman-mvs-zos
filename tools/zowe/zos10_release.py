#!/usr/bin/env python3
"""ZOS-10 release (docs/zos10-design.md, decisions of 2026-10-20): the release set, the decks PACZ10AL / BL / C1 / C2 /
CL / PV / IN / P1, their audits and fail-closed checkers, the object-equivalence gate, the Z6 CLIST PARM evaluator,
the read-only z/OS gates (precheck, provenance, IN-check, closure) and the S10 live-smoke wrapper.

Nothing here runs on z/OS unless a z/OS sub-command is invoked (each one on the user's approval only):
  zos10_release.py --deck NAME OUT.jcl          write a deck (prefix @@HLQ@@.PACMAN)
  zos10_release.py --selftest                   local checks of decks, audits, CLIST matrix, object masks
  zos10_release.py --check NAME SPOOLDIR [--cv1 DIR] [--report F]   check a downloaded job (BL C1 C2 CL P1 PV IN)
  zos10_release.py --objeq OLD_DIR NEW_DIR      object equivalence (local files OBJ.<member>.bin)
  zos10_release.py --zos precheck|provenance|upload|objects|in-check|closure [--out DIR]   read-only z/OS queries
                                                (upload: the release sources into RZ, byte-verified; objects: download
                                                RZ.OBJ in binary)
  zos10_release.py --s10-drive PORT LOG / --s10-check TRACE LOG   the live smoke S10 (frozen ZOS-6 R1 plan and rules,
                                                the release invocation without PLAY / PRESENT)
"""
import argparse
import gzip
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests'), str(R / 'tools')]

PFX = '@@HLQ@@.PACMAN'
RZ = PFX + '.RZ'
PRV = PFX + '.PRV.CLIST'
WORK = PFX + '.Z4CL.T1'                     # the existing ZOS-4 test PDS; member Z10P must be absent before PACZ10CL
LOAD = 'PACMAIN'
CLIST_PREFIX = 'Z00000.PACMAN'              # the installed CLIST's own prefix (render of src/zos/PACMAN.clist)
# the release set (explicit allow-lists, never a glob)
RELEASE = {'COBOL': ['PACMAIN', 'PACGAME', 'PACMAP', 'PACAI', 'PACINPT', 'PACDISP', 'PACPLAT', 'PACSCR', 'PACQRY',
                     'PACRT'],
           'COPY': ['PACARC', 'PACDS', 'PACMREQ', 'PACPAL', 'PACREQ', 'PACSTATE'],
           'ASM': ['PACTSO', 'PACFSIO', 'PACHSIO']}
SRC = {'COBOL': ('src/cobol', '.cob'), 'COPY': ('src/copy', '.cpy'), 'ASM': ('src/asm', '.asm')}
NEVER = ['PACHELLO', 'PACQRYT', 'PACTSOT', 'PACDSPX', 'PACRPE', 'RPESTAE', 'PACZ6P', 'ZHELLOA', 'ZHELLOC']
OBJECTS = RELEASE['COBOL'] + RELEASE['ASM']
# the ZOS-1 allocation of record (jcl/zos/PACZALLO.jcl): (library, DCB, space)
RZ_SETS = [('COBOL', 'DSNTYPE=LIBRARY,RECFM=FB,LRECL=80,BLKSIZE=27920', '(TRK,(15,15,10))'),
           ('COPY', 'DSNTYPE=LIBRARY,RECFM=FB,LRECL=80,BLKSIZE=27920', '(TRK,(5,5,10))'),
           ('ASM', 'DSNTYPE=LIBRARY,RECFM=FB,LRECL=80,BLKSIZE=27920', '(TRK,(5,5,10))'),
           ('OBJ', 'DSNTYPE=LIBRARY,RECFM=FB,LRECL=80,BLKSIZE=27920', '(TRK,(30,15,10))'),
           ('LOAD', 'DSNTYPE=LIBRARY,RECFM=U,BLKSIZE=32760', '(TRK,(45,15,10))'),
           ('CLIST', 'DSNTYPE=LIBRARY,RECFM=FB,LRECL=80,BLKSIZE=27920', '(TRK,(2,2,10))')]
PRV_DCB = ('DSNTYPE=LIBRARY,RECFM=FB,LRECL=80,BLKSIZE=27920', '(TRK,(2,2,10))')
BUILD = [f'COB{i}' for i in range(1, 11)] + ['ASM1', 'ASM2', 'ASM3', 'LINK']
CV1 = ['RUN1', 'RUN6', 'TSO1', 'TSO2', 'TSO3', 'TSO4', 'TSO5', 'TSO6']          # oracle 307 (REL20)
CV2 = ['RTT2', 'N1', 'G3T7']                 # oracle 310 RTT2 (EVERY TSD), ZOS-6 N1 (COALESCED TSD + bells), 311 G3T7
P1 = ['RUN1', 'TSO2', 'TSO6']                # installed PACMAIN, oracle 307
JOBS = {'AL': 'PACZ10AL', 'BL': 'PACZ10BL', 'C1': 'PACZ10C1', 'C2': 'PACZ10C2', 'CL': 'PACZ10CL', 'PV': 'PACZ10PV',
        'IN': 'PACZ10IN', 'P1': 'PACZ10P1'}
APP_LINES = {'C1': 2572, 'C2': 1163, 'P1': 566}
S10_KW = 'AI(0) RULES(CLASSIC) SOUND(NO)'     # no PLAY, no PRESENT: the user-facing default path (decision 1)
HISCORE = '0000980 PACHS001 001'


# ---- the release CLIST (Z6) and its PARM matrix --------------------------------------------------------------------
def release_clist(prefix=CLIST_PREFIX):
    return (R / 'src/zos/PACMAN.clist').read_text(encoding='ascii').replace('@@PREFIX@@', prefix)


def clist_parm(text, kw):
    """Independent evaluator of the CLIST statements that build &P (PROC defaults, operands, SET, IF .. [AND ..] THEN
    SET), up to the CALL; the Z2 / Z3 control variables are not modelled. -> the PARM string."""
    lines = text.split('\n')
    proc = ' '.join(l.rstrip('+ ') for l in lines[:lines.index(next(l for l in lines if l.startswith('/*')))])
    v = dict(re.findall(r'(\w+)\((\w*)\)', proc))
    v.update(re.findall(r'(\w+)\((\w*)\)', kw))
    env = {'&' + k: x for k, x in v.items()}

    def val(x):
        x = x.strip()
        m = re.fullmatch(r'&SUBSTR\(1:1,(&\w+)\)', x)
        if m:
            return env[m.group(1)][:1]
        m = re.fullmatch(r'&STR\((.*)\)', x)
        if m:
            return re.sub(r'&\w+', lambda g: env[g.group(0)], m.group(1))
        m = re.fullmatch(r'&LENGTH\(&STR\((&\w+)\)\)', x)
        if m:
            return str(len(env[m.group(1)]))
        return env[x] if x.startswith('&') else x

    def cond(c):
        out = True
        for part in c.split(' AND '):
            a, op, b = re.fullmatch(r'(\S+) (=|NE) (\S+)', part.strip()).groups()
            out &= (val(a) == val(b)) == (op == '=')
        return out
    for l in lines:
        if l.startswith("CALL '"):
            return env['&P']
        m = re.fullmatch(r'SET (&[A-Z]) = (.*)', l)
        f = re.fullmatch(r'IF (.+) THEN SET (&[A-Z]) = (.*)', l)
        if m and m.group(1) not in ('&Z', '&T', '&I', '&D'):
            env[m.group(1)] = val(m.group(2))
        elif f and f.group(2) not in ('&Z', '&T', '&I', '&D'):
            if cond(f.group(1)):
                env[f.group(2)] = val(f.group(3))
    raise ValueError('no CALL')


def mvs_parm(kw):
    """The 2.0-mvs-max CLIST PARM for the same operands (the historical 25-column form)."""
    return clist_parm((R / 'src/clist/PACMAN.clist').read_text(encoding='ascii'), kw)


# the PACZ10CL matrix (RULES(CLASSIC) always: the high-score block is never entered): (operands, column 26)
CL_CASES = [('RULES(CLASSIC)', 'C'),                                   # 1 default invocation -> REALTIME default
            ('RULES(CLASSIC) PLAY(REALTIME)', 'C'),                    # 2
            ('RULES(CLASSIC) PLAY(REALTIME) PRESENT(COALESCED)', 'C'),  # 3
            ('RULES(CLASSIC) PLAY(REALTIME) PRESENT(EVERY)', ''),      # 4 EVERY: the 25-column 2.0 form
            ('RULES(CLASSIC) PLAY(TURN)', ''),                         # 5 TURN default: historical PARM
            ('RULES(CLASSIC) PLAY(TURN) PRESENT(COALESCED)', 'C'),     # 6 explicit value kept (Z5)
            ('RULES(CLASSIC) PLAY(TURN) PRESENT(EVERY)', ''),          # 7
            ('RULES(CLASSIC) PRESENT(XYZ)', ''),                       # 8 invalid -> EVERY (Z5 rule)
            ('RULES(CLASSIC) PRESENT(ABC)', ''),                       # 9 invalid, only exact AUTO is AUTO
            (S10_KW, 'C')]                                             # 10 the S10 invocation


def cl_expected():
    """[(operands, PARM)]: every PARM = the 2.0 MVS CLIST PARM of the same operands + the column 26 of the matrix."""
    out = []
    for kw, c in CL_CASES:
        legacy = mvs_parm(re.sub(r' ?PRESENT\(\w*\)', '', kw))
        assert len(legacy) == 25
        out.append((kw, legacy + c))
    return out


def cl_test_copy(prefix=PFX):
    """The PACZ10CL test copy: the release CLIST for prefix with (1) the high-score block replaced by a refusal of any
    ARCADE case (no PACHS, no DATA reference), (2) its three `IF &W = A THEN FREE F(PACHS)` lines removed, (3) the CALL
    replaced by `WRITE Z10PARM=<&P>`. Every other line is the release CLIST verbatim."""
    lines = release_clist(prefix).split('\n')
    i = lines.index('IF &W = A THEN DO')
    j = lines.index('END', i)
    assert 'PACHS' in ''.join(lines[i:j + 1]) and j - i == 4
    lines[i:j + 1] = ['IF &W = A THEN EXIT CODE(12)']
    lines = [l for l in lines if l.strip() != 'IF &W = A THEN FREE F(PACHS)']
    k = [n for n, l in enumerate(lines) if l.startswith("CALL '")]
    assert len(k) == 1
    lines[k[0]] = 'WRITE Z10PARM=<&P>'
    text = '\n'.join(lines)
    assert not re.search(r'PACHS(?!IO)', text) and '.DATA' not in text and not any(l.startswith('ZZ') for l in lines)
    return text


# ---- decks -----------------------------------------------------------------------------------------------------------
def _zt(pfx=PFX):
    import make_deck as md
    import zos_target as zt
    if not zt._md:
        zt.apply(md, pfx)
    zt.JOBNAME = None
    return md, zt


def _steps(base, pfx, names, work=None):
    md, zt = _zt()
    old, oldp = zt.COB_WORK[0], zt.PREFIX_IN_USE[0]
    if work:
        zt.COB_WORK[0] = work
    zt.PREFIX_IN_USE[0] = pfx               # zos_target.asm_step names <prefix>.ASM / .OBJ from this global
    try:
        full = zt.steps_of_deck(md.build(base, pfx, LOAD))
    finally:
        zt.COB_WORK[0], zt.PREFIX_IN_USE[0] = old, oldp
    assert [s for s in full if s in names] == names, (base, names)
    return [full[s].replace('\n//\n', '\n') if full[s].endswith('\n//\n') else full[s] for s in names]


def deck(name):
    md, zt = _zt()
    job = JOBS[name]
    out = zt.job_card(job, f'PACMAN ZOS10 {job}')
    if name == 'AL':
        out += '//ALLOC    EXEC PGM=IEFBR14\n'
        for lib, dcb, sp in RZ_SETS:
            out += (f'//{lib:<8} DD DSN={RZ}.{lib},DISP=(NEW,CATLG,CATLG),\n//            {dcb},\n'
                    f'//            SPACE={sp}\n')
    elif name == 'BL':
        out += ''.join(_steps('REL20', RZ, BUILD, work='CYL,(1,1)'))
    elif name == 'C1':
        out += ''.join(_steps('REL20', RZ, CV1))
    elif name == 'C2':
        import zos6_dry as D6
        n1 = next(s for s in D6.STEPS if s['step'] == 'N1')
        out += _steps('GP2', RZ, ['RTT2'])[0]
        out += zt.run_step('N1', RZ, LOAD, '\n'.join(n1['cards']) + '\n', parm=n1['parm'])
        out += _steps('GP23', RZ, ['G3T7'])[0]
    elif name == 'P1':
        out += ''.join(_steps('REL20', PFX, P1))
    elif name == 'CL':
        out += ('//CLCPY    EXEC PGM=IEBGENER\n//SYSPRINT DD SYSOUT=A\n//SYSIN    DD DUMMY\n'
                f'//SYSUT2   DD DSN={WORK}(Z10P),DISP=OLD\n//SYSUT1   DD DATA,DLM=ZZ\n' + cl_test_copy() + '\nZZ\n'
                '//CLT      EXEC PGM=IKJEFT01,COND=(0,NE),DYNAMNBR=200\n//SYSTSPRT DD SYSOUT=A\n//SYSTSIN  DD *\n')
        for kw, _ in CL_CASES:
            out += f"  EXEC '{WORK}(Z10P)' +\n  '{kw}'\n"
        out += '/*\n'
    elif name == 'PV':
        a, b = PRV_DCB
        out += ('//PRV1     EXEC PGM=IEBCOPY\n//SYSPRINT DD SYSOUT=A\n'
                f'//I        DD DSN={PFX}.CLIST,DISP=SHR\n'
                f'//O        DD DSN={PRV},DISP=(NEW,CATLG,CATLG),\n//            {a},\n//            SPACE={b}\n'
                '//SYSIN    DD *\n  COPY OUTDD=O,INDD=I\n  SELECT MEMBER=PACMAN\n/*\n')
    elif name == 'IN':
        out += ('//PROM1    EXEC PGM=IEBCOPY\n//SYSPRINT DD SYSOUT=A\n'
                f'//I        DD DSN={RZ}.LOAD,DISP=SHR\n//O        DD DSN={PFX}.LOAD,DISP=SHR\n'
                '//SYSIN    DD *\n  COPY OUTDD=O,INDD=I\n  SELECT MEMBER=((PACMAIN,,R))\n/*\n'
                '//PROM2    EXEC PGM=IEBCOPY,COND=(0,NE)\n//SYSPRINT DD SYSOUT=A\n'
                f'//I        DD DSN={RZ}.CLIST,DISP=SHR\n//O        DD DSN={PFX}.CLIST,DISP=SHR\n'
                '//SYSIN    DD *\n  COPY OUTDD=O,INDD=I\n  SELECT MEMBER=((PACMAN,,R))\n/*\n')
    audit(name, out)
    return out


# datasets each deck may name (system libraries of the build aside) and the members it may write
NAMES = {'AL': {f'{RZ}.{l}' for l, _, _ in RZ_SETS},
         'BL': {f'{RZ}.{l}' for l in ('COBOL', 'COPY', 'ASM', 'OBJ', 'LOAD')},
         'C1': {f'{RZ}.LOAD'}, 'C2': {f'{RZ}.LOAD'}, 'P1': {f'{PFX}.LOAD'},
         'CL': {WORK}, 'PV': {f'{PFX}.CLIST', PRV}, 'IN': {f'{RZ}.LOAD', f'{PFX}.LOAD', f'{RZ}.CLIST', f'{PFX}.CLIST'}}
SYSTEM = {'IGY650.SIGYCOMP', 'CEE.SCEERUN', 'CEE.SCEERUN2', 'CEE.SCEELKED', 'CEE.SCEELKEX', 'HLA.SASMMOD1',
          'SYS1.MACLIB', 'SYS1.MODGEN'}
STEPS = {'BL': BUILD, 'C1': CV1, 'C2': CV2, 'P1': P1, 'AL': ['ALLOC'], 'CL': ['CLCPY', 'CLT'], 'PV': ['PRV1'],
         'IN': ['PROM1', 'PROM2']}
PGMS = {'AL': {'IEFBR14'}, 'BL': {'IGYCRCTL', 'ASMA90', 'IEWBLINK'}, 'C1': {LOAD}, 'C2': {LOAD}, 'P1': {LOAD},
        'CL': {'IEBGENER', 'IKJEFT01'}, 'PV': {'IEBCOPY'}, 'IN': {'IEBCOPY'}}


def audit(name, text):
    """Fail closed: job name, exact step list, programs, the datasets the deck may name, no PACHS / DATA / DELETE /
    PACZ6D / PACZ2D anywhere, CEEOPTS profile A in every run step, run steps EXEC PGM=PACMAIN from the right LOAD."""
    _, zt = _zt()
    job = JOBS[name]
    assert text.startswith(f'//{job} ') and text.count(' JOB ') == 1, 'job card'
    parts = zt.steps_of_deck(text)
    assert list(parts) == STEPS[name], f'steps {list(parts)}'
    pg = [re.search(r'EXEC PGM=(\w+)', t).group(1) for t in parts.values()]
    assert set(pg) <= PGMS[name], pg
    assert not re.search(r'PACHS(?!IO)', text), 'forbidden PACHS (the high-score DD)'
    for w in ('.DATA', 'DELETE', 'PACZ6D', 'PACZ2D', 'ZHEIST', 'SCRATCH', 'PURGE'):
        assert w not in text, f'forbidden {w!r}'
    dsn = {re.sub(r'\(.*', '', d) for d in re.findall(r'DSN=([^,\s]+)', text)}
    assert dsn - SYSTEM == NAMES[name], f'datasets {sorted(dsn - SYSTEM)}'
    if name != 'BL':
        assert not dsn & SYSTEM, 'system libraries outside the build'
    for s, t in parts.items():
        if s in CV1 + CV2 + P1 and name in ('C1', 'C2', 'P1'):
            lib = PFX if name == 'P1' else RZ
            assert re.match(rf'//{s}\s+EXEC PGM={LOAD},COND=\(0,NE\)', t), s
            assert t.count(f'//STEPLIB  DD DSN={lib}.LOAD,DISP=SHR\n') == 1, s
            assert '//CEEOPTS  DD *\nALL31(OFF),STACK(,,BELOW)\n/*\n' in t, s
            assert re.findall(r'^//(\w+)\s+DD ', t, re.M) == ['STEPLIB', 'CEEOPTS', 'SYSIN', 'SYSOUT', 'CEEDUMP',
                                                             'SYSUDUMP'], s
    if name == 'BL':
        link = parts['LINK']
        assert re.findall(r'INCLUDE OBJ\((\w+)\)', link) == OBJECTS and '  ENTRY PACMAIN\n  NAME PACMAIN(R)\n' in link
        assert f'//OBJ      DD DSN={RZ}.OBJ,DISP=SHR' in link and f'//SYSLMOD  DD DSN={RZ}.LOAD,DISP=SHR' in link
        assert "PARM='LIST,AMODE=24,RMODE=24,RENT'" in link
        for i, m in enumerate(RELEASE['COBOL'], 1):
            t = parts[f'COB{i}']
            assert f'SYSIN    DD DSN={RZ}.COBOL({m}),' in t and f'SYSLIN   DD DSN={RZ}.OBJ({m}),' in t, m
            assert "'RENT,RMODE(24),DATA(24),NODYNAM'," in t and "'TRUNC(STD),NUMPROC(NOPFD),NOSOURCE,NOXREF'" in t
            assert f'SYSLIB   DD DSN={RZ}.COPY,' in t and 'SPACE=(CYL,(1,1))' in t
        for i, m in enumerate(RELEASE['ASM'], 1):
            t = parts[f'ASM{i}']
            assert f'SYSIN    DD DSN={RZ}.ASM({m}),' in t and f'SYSLIN   DD DSN={RZ}.OBJ({m}),' in t, m
        for w in NEVER:
            assert w not in text, w
    if name in ('PV', 'IN'):
        sel = re.findall(r'SELECT MEMBER=(\S+)', text)
        assert sel == (['PACMAN'] if name == 'PV' else ['((PACMAIN,,R))', '((PACMAN,,R))']), sel
        if name == 'IN':
            assert 'COND=(0,NE)' in parts['PROM2'] and 'COND' not in parts['PROM1'].split('\n')[0]
    if name == 'AL':
        assert text.count('DISP=(NEW,CATLG,CATLG)') == 6 and 'LOAD' in text
    if name == 'PV':
        assert text.count('DISP=(NEW,CATLG,CATLG)') == 1 and f'DSN={PFX}.CLIST,DISP=SHR' in text
    if name == 'CL':
        assert f'DSN={WORK}(Z10P),DISP=OLD' in text and \
            text.split('//SYSTSIN  DD *\n')[1].count(f"  EXEC '{WORK}(Z10P)' +\n") == len(CL_CASES)
    return True


# ---- object equivalence (docs/zos10-design.md section 5.5 / 11) ---------------------------------------------------
_E = lambda s: s.encode('cp037')                                  # noqa: E731
_D = b'[\xf0-\xf9]'
SPAN_A = re.compile(_E('20') + _D + b'{12}(?=' + re.escape(_E('0605')) + b')')        # YYYYMMDDHHMMSS + COBOL 06.05
SPAN_B = re.compile(b'(?<=' + re.escape(_E('5655EC6   0605')) + b')' + _E('20') + _D + b'{11}')   # YYYYDDDHHMMSS


def spans(member, b):
    """The metadata spans of one object image: [(offset, length)]. COBOL (GOFF, 80-byte records): exactly one compile
    timestamp YYYYMMDDHHMMSS (14 EBCDIC digits followed by the compiler level 0605) in a TXT record X'03 11' at record
    offset 26, and exactly one YYYYDDDHHMMSS (13 digits after the product id '5655EC6   ' + '0605') in a TXT record X'03
    10' at record offset 42. HLASM (80-byte OBJ): exactly one END record, its IDR assembly date yyddd at offset 47..51.
    Anything else -> ValueError (unexpected format: STOP)."""
    if len(b) % 80:
        raise ValueError(f'{member}: not 80-byte records')
    if member in RELEASE['ASM']:
        ends = [i for i in range(0, len(b), 80) if b[i + 1:i + 4] == _E('END')]
        if len(ends) != 1 or not re.fullmatch(_D + b'{5}', b[ends[0] + 47:ends[0] + 52]):
            raise ValueError(f'{member}: END record / IDR date not as expected')
        return [(ends[0] + 47, 5)]
    a, c = list(SPAN_A.finditer(b)), list(SPAN_B.finditer(b))
    if len(a) != 1 or len(c) != 1:
        raise ValueError(f'{member}: {len(a)} / {len(c)} timestamp spans (1 / 1 required)')
    (pa, qa), (pc, qc) = (a[0].start(), a[0].end()), (c[0].start(), c[0].end())
    if pa % 80 != 26 or b[pa - 26:pa - 24] != b'\x03\x11' or pc % 80 != 42 or b[pc - 42:pc - 40] != b'\x03\x10':
        raise ValueError(f'{member}: timestamp spans not at the documented record positions')
    return [(pa, qa - pa), (pc, qc - pc)]


def objeq(old, new, member):
    """-> (state, detail): IDENTICAL-MODULO-TIMESTAMP when every byte outside the documented spans is equal and the
    spans hold valid timestamps in both images; else DIFFERENT / FORMAT."""
    try:
        so, sn = spans(member, old), spans(member, new)
    except ValueError as e:
        return 'FORMAT', str(e)
    if len(old) != len(new):
        return 'DIFFERENT', f'{member}: {len(old)} / {len(new)} bytes'
    if so != sn:
        return 'DIFFERENT', f'{member}: span positions {so} / {sn}'
    mask = {p for o, n in so for p in range(o, o + n)}
    diff = [i for i in range(len(old)) if old[i] != new[i] and i not in mask]
    if diff:
        return 'DIFFERENT', f'{member}: {len(diff)} byte(s) differ outside the timestamp spans, first at record ' \
                            f'{diff[0] // 80 + 1} offset {diff[0] % 80}'
    return 'IDENTICAL-MODULO-TIMESTAMP', f'{member}: {len(old) // 80} records equal; masked {so}'


def objeq_dirs(old_dir, new_dir):
    res = {}
    for m in OBJECTS:
        res[m] = objeq(Path(old_dir, f'OBJ.{m}.bin').read_bytes(), Path(new_dir, f'OBJ.{m}.bin').read_bytes(), m)
    return all(s == 'IDENTICAL-MODULO-TIMESTAMP' for s, _ in res.values()), res


# ---- spool checkers --------------------------------------------------------------------------------------------------
def _jes(d):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    jes = ''.join(p.read_text() for p in d.glob('00*-JES2-*.txt'))
    return job, msg, jes


def _cc(msg, job, step):
    m = re.search(rf'IEF142I {job} {step} - STEP WAS EXECUTED - COND CODE (\d{{4}})', msg)
    return m.group(1) if m else None


def _sysprint(d, step):
    from zos_equiv import zos_runs  # noqa: F401
    f = sorted(Path(d).glob(f'*-{step}-SYSPRINT.txt'))
    return f[0].read_text().splitlines() if len(f) == 1 else None


def check_bl(d):
    """PACZ10BL gate: per-step RC (COBOL 0, PACTSO / PACHSIO 0, PACFSIO 4 = the C3 policy exactly), compiler / assembler
    messages, the binder INCLUDE list, attributes and message summary."""
    from zos_compile_report import report
    job, msg, jes = _jes(d)
    res, ok = {}, True
    rcs = {s: _cc(msg, job['jobname'], s) for s in BUILD}
    want = dict({s: '0000' for s in BUILD}, ASM2='0004')
    res['step RC'] = rcs
    ok &= rcs == want and job['jobname'] == JOBS['BL']
    _, rows = report(d)
    msgs = {r[0]: r[4] for r in rows}
    for s in BUILD[:10]:
        bad = [m for m in msgs.get(s, []) if m[0] != 'I']
        res[f'{s} messages above I'] = bad
        ok &= not bad
    for s in ('ASM1', 'ASM3'):
        res[f'{s} messages'] = msgs.get(s, [])
        ok &= not msgs.get(s)
    a2 = sorted((m[0], m[1]) for m in msgs.get('ASM2', []))
    lst = _sysprint(d, 'ASM2') or []
    base15 = any(re.search(r'5BC0 F014\s+\d+\s+\d+\s+S\s+12,ABOFF', l) for l in lst)
    using = any('ASMA303W' in l and 'statement number 38' in l for l in lst)
    res['ASM2 C3 policy (ASMA303W + ASMA435I only, S 12,ABOFF = 5BC0 F014, USING on statement 38)'] = \
        a2 == [('I', 'ASMA435'), ('W', 'ASMA303')] and base15 and using
    ok &= res['ASM2 C3 policy (ASMA303W + ASMA435I only, S 12,ABOFF = 5BC0 F014, USING on statement 38)']
    lk = _sysprint(d, 'LINK') or []
    text = '\n'.join(lk)
    inc = re.findall(r'IEW2322I \w+\s+\d+\s+INCLUDE OBJ\((\w+)\)', text)
    attrs = text[text.find('SAVE MODULE ATTRIBUTES'):]
    att = {k: re.search(rf'\n\s+{k}\s+(\S+)', attrs) for k in ('AMODE', 'RMODE', 'RENT', 'REUS')}
    att = {k: v.group(1) if v else None for k, v in att.items()}
    x16 = re.search(r'\n\s+EXCEEDS 16MB\s+(\S+)', attrs)
    iew = sorted(set(re.findall(r'\bIEW(\d{4})[A-Z]\b', text)))
    summ = re.findall(r'MESSAGES\s+\(SEVERITY = (\d\d)\)\s*\n\s*(\S+)', text)
    res['binder'] = {'INCLUDE': inc, 'ENTRY PACMAIN': 'ENTRY PACMAIN' in text,
                     'NAME': re.findall(r'NAME (\w+)\(R\)', text),
                     'attributes': att, 'EXCEEDS 16MB': x16.group(1) if x16 else None, 'IEW messages': iew,
                     'summary': summ, 'RC 0': 'PROCESSING COMPLETED.  RETURN CODE =  0.' in text}
    b = res['binder']
    ok &= (inc == OBJECTS and b['ENTRY PACMAIN'] and b['NAME'] == ['PACMAIN'] and b['RC 0'] and
           att == {'AMODE': '24', 'RMODE': '24', 'RENT': 'YES', 'REUS': 'YES'} and b['EXCEEDS 16MB'] == 'NO' and
           set(iew) <= {'2008', '2278', '2322'} and summ[:4] == [('16', 'NONE'), ('12', 'NONE'), ('08', 'NONE'),
                                                                   ('04', 'NONE')])
    res['no CEE / abend / output-limit text'] = not re.search(r'CEE\d{4}|ABEND|\$HASP375|IEA995', jes)
    ok &= res['no CEE / abend / output-limit text']
    return ok, res


def _run_health(d, name):
    """Run jobs: every step COND CODE 0000, program PACMAIN, SYSOUT only, STEPLIB <lib>.LOAD retained once per step,
    no CEE / abend / output-limit text."""
    from zos_equiv import zos_runs
    job, msg, jes = _jes(d)
    _, names, runs = zos_runs(d)
    lib = ('Z00000.PACMAN' if name == 'P1' else 'Z00000.PACMAN.RZ') + '.LOAD'
    bad = []
    if job['jobname'] != JOBS[name] or names != STEPS[name]:
        bad.append(f'job {job["jobname"]} steps {names}')
    for s in names:
        if _cc(msg, job['jobname'], s) != '0000':
            bad.append(f'{s}: not COND CODE 0000')
        if runs[s]['pgm'] != LOAD or runs[s]['extra']:
            bad.append(f'{s}: {runs[s]["pgm"]} extra {runs[s]["extra"]}')
    if len(re.findall(rf'IGD104I {re.escape(lib)}\s+RETAINED,\s+DDNAME=STEPLIB', msg)) != len(names):
        bad.append(f'STEPLIB {lib} not retained once per step')
    if re.search(r'CEE\d{4}|ABEND|\$HASP375|IEA995', jes):
        bad.append('CEE / abend / output-limit text')
    return runs, bad


def _oracle(job):
    f = {307: '307-PACREL20', 310: '310-PACBLGP2', 311: '311-PACBLG23'}[job]
    return json.load(gzip.open(R / f'tests/oracle20/{f}.json.gz'))


def oracle_block(job, step):
    """The step's own frozen block: zos_equiv's own-step anchor, ended by zos_equiv's block-end rule (the next anchored
    run block, a TK4- separator, a page eject or the end of the stream: ends_ok), right-stripped."""
    import zos_equiv as ZE
    o = _oracle(job)
    anc = ZE.anchors(o, {'PACMAIN'})
    s, b = o['stream'], anc[step]
    e = next(e for e in range(b + 1, len(s) + 1) if ZE.ends_ok(o, anc, step, e))
    return [l.rstrip() for l in s[b:e]]


def step_check(step, lines):
    """-> {oracle, model}: each 'exact' or the first finding."""
    import zos6_dry as D6
    out = {}
    if step in CV1 + P1:
        from zos_classic_check import model
        g, w = D6.compare_lines(lines, oracle_block(307, step))
        r = model(step, lines)
        out['oracle 307'] = 'exact' if g else w
        out['model'] = 'exact' if r is None else r
    elif step == 'RTT2':
        e2 = next(s for s in D6.STEPS if s['step'] == 'E2')
        g, w = D6.compare_lines(lines, oracle_block(310, 'RTT2'))
        g2, w2 = D6.compare_tsd(lines, e2, D6.model(e2))
        out['oracle 310'] = 'exact' if g else w
        out['model'] = 'exact' if g2 else w2
    elif step == 'N1':
        n1 = next(s for s in D6.STEPS if s['step'] == 'N1')
        g2, w2 = D6.compare_tsd(lines, n1, D6.model(n1))
        out['model'] = 'exact' if g2 else w2
    elif step == 'G3T7':
        import zos9_equiv as Z9
        g, w = D6.compare_lines(lines, Z9.oracle_block(2, 'G3T7'))
        g2, w2 = Z9.compare_model(lines, Z9.model('G3T7'))
        out['oracle 311'] = 'exact' if g else w
        out['model'] = 'exact' if g2 else w2
    return out


def check_runs(d, name, cv1=None):
    runs, bad = _run_health(d, name)
    res, ok = {'health': bad or 'OK', 'steps': {}}, not bad
    for s in STEPS[name]:
        if s not in runs:
            res['steps'][s] = 'missing'
            ok = False
            continue
        r = step_check(s, runs[s]['lines'])
        if name == 'P1' and cv1:
            from zos_equiv import zos_runs
            c = zos_runs(cv1)[2].get(s)
            r['= CV1 candidate output'] = 'exact' if c and c['lines'] == runs[s]['lines'] else 'differs'
        r['lines'] = len(runs[s]['lines'])
        res['steps'][s] = r
        ok &= all(v == 'exact' for k, v in r.items() if k != 'lines')
    res['application lines'] = sum(v['lines'] for v in res['steps'].values() if isinstance(v, dict))
    ok &= res['application lines'] == APP_LINES[name]
    return ok, res


def check_cl(d):
    job, msg, jes = _jes(d)
    res = {'CLCPY': _cc(msg, job['jobname'], 'CLCPY'), 'CLT': _cc(msg, job['jobname'], 'CLT')}
    tp = sorted(Path(d).glob('*-CLT-SYSTSPRT.txt'))
    text = tp[0].read_text() if len(tp) == 1 else ''
    got = re.findall(r'Z10PARM=<([^>]*)>', text)
    want = [p for _, p in cl_expected()]
    res['PARMs'] = list(zip([k for k, _ in CL_CASES], got))
    res['= expected'] = got == want
    res['no CLIST error text'] = 'PACMAN:' not in text and not re.search(r'IKJ\d{5}[EI]? .*(ERROR|INVALID)', text)
    ok = res['CLCPY'] == '0000' and res['CLT'] == '0000' and res['= expected'] and res['no CLIST error text'] and \
        job['jobname'] == JOBS['CL']
    return ok, res


def check_copy(d, name):
    """PACZ10PV / PACZ10IN: each IEBCOPY step RC 0, its member copied (and replaced, for IN)."""
    job, msg, jes = _jes(d)
    res, ok = {}, job['jobname'] == JOBS[name]
    for s in STEPS[name]:
        sp = '\n'.join(_sysprint(d, s) or [])
        rc = _cc(msg, job['jobname'], s)
        mem = 'PACMAN' if s in ('PRV1', 'PROM2') else 'PACMAIN'
        copied = re.search(rf'MEMBER {mem}\s+HAS BEEN COPIED' + ('   AND REPLACED' if name == 'IN' else ''), sp)
        res[s] = {'RC': rc, 'copied': bool(copied), '1 of 1 members': re.search(r'IGW01550I 1 OF 1 SPECIFIED\s+'
                                                                            r'MEMBERS WERE COPIED', sp) is not None,
                  'highest severity 0': 'HIGHEST SEVERITY CODE' in sp and
                  re.search(r'END OF JOB - 0 WAS HIGHEST SEVERITY CODE', sp) is not None}
        ok &= rc == '0000' and all(res[s].values()) if rc else False
    return ok, res


# ---- read-only z/OS gates (run only on approval) -------------------------------------------------------------------
def _zowe():
    from zoslib import zowe
    return zowe


def _exists(ds):
    items = _zowe()('zos-files', 'list', 'data-set', ds, json_out=True)['data']['apiResponse']['items']
    return any(i['dsname'] == ds for i in items)


def _members(ds, attrs=False):
    d = _zowe()('zos-files', 'list', 'all-members', ds, *(['-a'] if attrs else []), json_out=True)
    return {m['member']: m for m in d['data']['apiResponse']['items']}


LOAD_ATTR = ('ac', 'amode', 'attr', 'rmode', 'size')


def zos_precheck(h='Z00000'):
    p = f'{h}.PACMAN'
    rz = [f'{p}.RZ.{l}' for l, _, _ in RZ_SETS] + [f'{p}.PRV.CLIST']
    load = _members(f'{p}.LOAD', True)
    work = _members(f'{p}.Z4CL.T1')
    res = {'RZ / PRV absent': {d: not _exists(d) for d in rz},
           'LOAD has PACMAIN and PACZ6D': {m: m in load for m in ('PACMAIN', 'PACZ6D')},
           'Z4CL.T1 exists, member Z10P absent': _exists(f'{p}.Z4CL.T1') and 'Z10P' not in work,
           'CEEOPTS exists': _exists(f'{p}.CEEOPTS')}
    ok = all(res['RZ / PRV absent'].values()) and all(res['LOAD has PACMAIN and PACZ6D'].values()) and \
        res['Z4CL.T1 exists, member Z10P absent'] and res['CEEOPTS exists']
    return ok, res


def zos_provenance(h='Z00000'):
    """Installed PACMAIN = the ZOS-6 promotion of PACZ6D: identical directory attributes (incl. size), PACZ6D
    present."""
    load = _members(f'{h}.PACMAN.LOAD', True)
    a = {m: {k: load.get(m, {}).get(k) for k in LOAD_ATTR} for m in ('PACMAIN', 'PACZ6D')}
    ok = a['PACMAIN'] == a['PACZ6D'] and a['PACZ6D']['size'] is not None and a['PACZ6D']['amode'] == '24' and \
        a['PACZ6D']['rmode'] == '24'
    return ok, a


def zos_upload(h='Z00000', out=R / 'build/zos/Z10UP'):
    from zos_upload import upload_verify
    res, ok = {}, True
    for lib, mems in RELEASE.items():
        d, ext = SRC[lib]
        for m in mems:
            g, t = upload_verify(R / d / f'{m}{ext}', f'RZ.{lib}', m, h, Path(out))
            res[f'{lib}({m})'] = t
            ok &= g
            if not g:
                return False, res
    return ok, res


def zos_upload_clist(h='Z00000', out=R / 'build/zos/Z10UP'):
    from zos_upload import upload_verify
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / 'PACMAN.clist'
        f.write_text(release_clist(f'{h}.PACMAN') + '\n', encoding='ascii')
        return upload_verify(f, 'RZ.CLIST', 'PACMAN', h, Path(out))


def zos_objects(h='Z00000', out=R / 'build/zos/Z10OBJ'):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    mem = sorted(_members(f'{h}.PACMAN.RZ.OBJ'))
    if mem != sorted(OBJECTS):
        return False, {'RZ.OBJ members': mem}
    for m in OBJECTS:
        _zowe()('zos-files', 'download', 'data-set', f'{h}.PACMAN.RZ.OBJ({m})', '--binary', '-f',
                str(out / f'OBJ.{m}.bin'), json_out=True)
    return True, {'downloaded': OBJECTS}


def _download(ds, f):
    _zowe()('zos-files', 'download', 'data-set', ds, '--binary', '-f', str(f), json_out=True)
    return Path(f).read_bytes()


def zos_in_check(h='Z00000', prev_clist=None, provenance=None, out=R / 'build/zos/Z10IN'):
    """Installed = candidate: LOAD(PACMAIN) attributes = RZ.LOAD(PACMAIN); CLIST(PACMAN) bytes = RZ.CLIST(PACMAN) = the
    release render; PACZ6D attributes unchanged (= the provenance record); PRV.CLIST(PACMAN) = the pre-release CLIST."""
    from zoslib import fixed_records
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    p = f'{h}.PACMAN'
    load, rz = _members(f'{p}.LOAD', True), _members(f'{p}.RZ.LOAD', True)
    att = lambda m, d: {k: d.get(m, {}).get(k) for k in LOAD_ATTR}           # noqa: E731
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / 'c.clist'
        f.write_text(release_clist(p) + '\n', encoding='ascii')
        want = fixed_records(f)
    res = {'LOAD(PACMAIN) attributes = RZ.LOAD(PACMAIN)': att('PACMAIN', load) == att('PACMAIN', rz),
           'CLIST(PACMAN) = release render': _download(f'{p}.CLIST(PACMAN)', out / 'CLIST.bin') == want,
           'RZ.CLIST(PACMAN) = release render': _download(f'{p}.RZ.CLIST(PACMAN)', out / 'RZCLIST.bin') == want,
           'PACZ6D unchanged': provenance is not None and att('PACZ6D', load) == provenance}
    if prev_clist is not None:
        res['PRV.CLIST(PACMAN) = pre-release CLIST'] = \
            _download(f'{p}.PRV.CLIST(PACMAN)', out / 'PRV.bin') == Path(prev_clist).read_bytes()
    return all(res.values()), res


def zos_closure(h='Z00000'):
    import zos8_batch as B
    st = B.state('DATA', h)
    return st['HISCORE'] == [HISCORE], st


# ---- S10 (the only live action): the frozen ZOS-6 R1 plan and rules, the release invocation --------------------------
def s10_plan():
    """The R1 plan with only its EXEC operands replaced (no PLAY, no PRESENT); present C expected. Run under the case
    name R1 so that every R1 rule of the frozen checker applies (one death, the freeze-span proxy, the gates)."""
    import zos6_drive as D
    p = dict(D.PLANS['R1'])
    p['kw'] = S10_KW
    return p


def _s10(fn, argv):
    import zos6_drive as D
    D.PLANS['R1'] = s10_plan()          # this process only; the frozen file is not changed
    sys.argv = argv
    fn()


# ---- selftest ------------------------------------------------------------------------------------------------------
def selftest():
    res, det = {}, {}
    rc = release_clist()
    res['release CLIST <= 72 columns, rendered'] = '@@' not in rc and all(len(l) <= 72 for l in rc.split('\n'))
    exp = cl_expected()
    for kw, p in exp:
        res[f'CLIST PARM [{kw}] = {p}'] = clist_parm(rc, kw) == p
    res['TURN default = the historical 2.0 PARM (25 columns, no C)'] = \
        clist_parm(rc, 'RULES(CLASSIC) PLAY(TURN)') == mvs_parm('RULES(CLASSIC) PLAY(TURN)') and \
        len(clist_parm(rc, 'RULES(CLASSIC) PLAY(TURN)')) == 25
    res['ARCADE defaults: REALTIME + C, TURN historical'] = clist_parm(rc, '') == mvs_parm('') + 'C' and \
        clist_parm(rc, 'PLAY(TURN)') == mvs_parm('PLAY(TURN)')
    import difflib
    tc = cl_test_copy()
    d = [x for x in difflib.ndiff(release_clist(PFX).split('\n'), tc.split('\n')) if x[:2] in ('- ', '+ ')]
    hs = release_clist(PFX).split('\n')
    i = hs.index('IF &W = A THEN DO')
    want = ['- ' + l for l in hs[i:i + 5]] + ['+ IF &W = A THEN EXIT CODE(12)']
    res['test copy = release CLIST except the HS block, its FREE F(PACHS) lines and the CALL (exact diff)'] = \
        sorted(d) == sorted(want + ['- ' + l for l in hs if l.strip() == 'IF &W = A THEN FREE F(PACHS)'] +
                            ['+ WRITE Z10PARM=<&P>'] +
                            ['- ' + next(l for l in hs if l.startswith("CALL '"))]) and \
        clist_parm(tc.replace('WRITE Z10PARM=<&P>', "CALL 'X'"), 'RULES(CLASSIC)') == exp[0][1]
    for n in JOBS:
        res[f'deck {JOBS[n]} audit'] = bool(deck(n))
    # deck mutants are refused
    base = {n: deck(n) for n in JOBS}
    mut = {'BL old OBJ library': ('BL', base['BL'].replace(f'//OBJ      DD DSN={RZ}.OBJ',
                                                           f'//OBJ      DD DSN={PFX}.OBJ')),
           'BL missing INCLUDE': ('BL', base['BL'].replace('  INCLUDE OBJ(PACHSIO)\n', '')),
           'BL probe compiled': ('BL', base['BL'].replace(f'{RZ}.COBOL(PACQRY)', f'{RZ}.COBOL(PACQRYT)')),
           'C1 installed load': ('C1', base['C1'].replace(f'{RZ}.LOAD', f'{PFX}.LOAD', 1)),
           'P1 PACHS DD': ('P1', base['P1'].replace('//SYSOUT', '//PACHS    DD DUMMY\n//SYSOUT', 1)),
           'C2 DATA': ('C2', base['C2'].replace(f'DSN={RZ}.LOAD', f'DSN={PFX}.DATA', 1)),
           'IN PROM2 without COND': ('IN', base['IN'].replace('PROM2    EXEC PGM=IEBCOPY,COND=(0,NE)',
                                                              'PROM2    EXEC PGM=IEBCOPY')),
           'IN PACZ6D touched': ('IN', base['IN'].replace('((PACMAIN,,R))', '((PACZ6D,,R))')),
           'AL DELETE': ('AL', base['AL'].replace('(NEW,CATLG,CATLG)', '(NEW,CATLG,DELETE)', 1)),
           'CL DATA alloc': ('CL', base['CL'].replace('IF &W = A THEN EXIT CODE(12)',
                                                      "ALLOC F(PACHS) DA('X.DATA(HISCORE)') SHR")),
           'PV replace': ('PV', base['PV'].replace('SELECT MEMBER=PACMAN', 'SELECT MEMBER=((PACMAN,,R))'))}
    for why, (n, t) in mut.items():
        try:
            audit(n, t)
            det[f'deck {why}'] = False
        except (AssertionError, KeyError, AttributeError):
            det[f'deck {why}'] = True
    # object masks on synthetic images
    cob = bytearray(b'\x40' * 240)
    cob[0:2], cob[26:40], cob[40:44] = b'\x03\x11', _E('20261019094720'), _E('0605')
    cob[160:162], cob[160 + 28:160 + 42], cob[160 + 42:160 + 55] = b'\x03\x10', _E('5655EC6   0605'), \
        _E('2026292094720')
    cob = bytes(cob)
    new = bytearray(cob)
    new[26:40], new[202:215] = _E('20261021101010'), _E('2026294101010')
    res['COBOL image: only the two timestamps differ -> IDENTICAL'] = \
        objeq(cob, bytes(new), 'PACMAIN')[0] == 'IDENTICAL-MODULO-TIMESTAMP'
    bad = bytearray(new)
    bad[100] ^= 1
    det['COBOL code byte changed'] = objeq(cob, bytes(bad), 'PACMAIN')[0] == 'DIFFERENT'
    bad = bytearray(new)
    bad[44] ^= 1
    det['COBOL byte next to the timestamp changed'] = objeq(cob, bytes(bad), 'PACMAIN')[0] == 'DIFFERENT'
    bad = bytearray(new)
    bad[30] = 0xC1
    det['COBOL timestamp not digits'] = objeq(cob, bytes(bad), 'PACMAIN')[0] != 'IDENTICAL-MODULO-TIMESTAMP'
    det['COBOL second timestamp occurrence'] = objeq(cob, cob + bytes(cob[:80]), 'PACMAIN')[0] != \
        'IDENTICAL-MODULO-TIMESTAMP'
    asm = bytearray(b'\x40' * 160)
    asm[81:84], asm[80 + 47:80 + 52] = _E('END'), _E('26287')
    asm = bytes(asm)
    an = bytearray(asm)
    an[127:132] = _E('26294')
    res['HLASM image: only the END date differs -> IDENTICAL'] = \
        objeq(asm, bytes(an), 'PACTSO')[0] == 'IDENTICAL-MODULO-TIMESTAMP'
    an[10] = 0x00
    det['HLASM TXT byte changed'] = objeq(asm, bytes(an), 'PACTSO')[0] == 'DIFFERENT'
    real = R / 'build/zos/Z6POST'
    if real.is_dir():
        import hashlib
        sha = json.loads((real / 'obj-sha256.json').read_text())
        res['accepted ZOS-6 object images = their recorded SHA-256 (13)'] = all(
            hashlib.sha256((real / f'OBJ.{m}.bin').read_bytes()).hexdigest() == sha[m] for m in OBJECTS)
        res['accepted images: spans found exactly as documented (13)'] = all(
            len(spans(m, (real / f'OBJ.{m}.bin').read_bytes())) == (1 if m in RELEASE['ASM'] else 2) for m in OBJECTS)
        res['accepted images compare with themselves'] = objeq_dirs(real, real)[0]
    res['all injected faults detected'] = all(det.values())
    return all(res.values()), res, det


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--deck', nargs=2, metavar=('NAME', 'OUT'))
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--check', nargs=2, metavar=('NAME', 'SPOOLDIR'))
    ap.add_argument('--cv1')
    ap.add_argument('--report')
    ap.add_argument('--objeq', nargs=2, metavar=('OLD', 'NEW'))
    ap.add_argument('--zos', choices=['precheck', 'provenance', 'upload', 'upload-clist', 'objects', 'in-check',
                                      'closure'])
    ap.add_argument('--prev-clist')
    ap.add_argument('--provenance-json')
    ap.add_argument('--s10-drive', nargs=2, metavar=('PORT', 'LOG'))
    ap.add_argument('--s10-check', nargs=2, metavar=('TRACE', 'LOG'))
    a = ap.parse_args()
    if a.deck:
        Path(a.deck[1]).write_text(deck(a.deck[0]))
        print(f'{a.deck[1]}: {JOBS[a.deck[0]]}, steps {STEPS[a.deck[0]]}')
        return
    if a.selftest:
        ok, res, det = selftest()
        for k, v in res.items():
            print(f'{"PASS" if v else "FAIL"}  {k}')
        for k, v in det.items():
            print(f'  {"detected" if v else "MISSED  "}  {k}')
        print('ZOS-10 SELFTEST ' + ('PASS' if ok else 'FAIL'))
        sys.exit(0 if ok else 1)
    if a.s10_drive:
        import zos6_drive as D
        return _s10(D.main, ['zos6_drive.py', '--port', a.s10_drive[0], '--case', 'R1', '--log', a.s10_drive[1]])
    if a.s10_check:
        import zos6_live_check as C
        return _s10(C.main, ['zos6_live_check.py', '--case', 'R1', '--trace', a.s10_check[0], '--drive-log',
                             a.s10_check[1]])
    if a.objeq:
        ok, res = objeq_dirs(*a.objeq)
    elif a.zos:
        if a.zos == 'in-check':
            prov = json.loads(Path(a.provenance_json).read_text())['PACZ6D'] if a.provenance_json else None
            ok, res = zos_in_check(prev_clist=a.prev_clist, provenance=prov)
        else:
            fn = {'precheck': zos_precheck, 'provenance': zos_provenance, 'upload': zos_upload,
                  'upload-clist': zos_upload_clist, 'objects': zos_objects, 'closure': zos_closure}[a.zos]
            ok, res = fn()
    else:
        n, d = a.check
        if n == 'BL':
            ok, res = check_bl(d)
        elif n == 'CL':
            ok, res = check_cl(d)
        elif n in ('PV', 'IN'):
            ok, res = check_copy(d, n)
        else:
            ok, res = check_runs(d, n, a.cv1)
    text = json.dumps(res, indent=1, default=str)
    if a.report:
        Path(a.report).write_text(text + '\n')
    print(text)
    print('RESULT ' + ('PASS' if ok else 'FAIL'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
