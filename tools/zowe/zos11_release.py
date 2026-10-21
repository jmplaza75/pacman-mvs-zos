#!/usr/bin/env python3
"""ZOS-11 step 2A (docs/zos11-design.md section 5; authorisation of 2026-10-21): the 2.1-zos build of record under a
NEW, empty prefix, its decks PACZ11AL / BL / C1 / C2, their audits and checkers, the object gate against the frozen
2.0-zos build of record (RZ, ZOS-10 PACZ10BL JOB04820) and the read-only z/OS gates.

Successor of tools/zowe/zos10_release.py, which stays frozen: its deck builder, audit, build / run checkers, timestamp
spans and D_MCODE rule are reused in-process with the new prefix bound to its module globals (as zos10_release reused
the ZOS-6 tools). No promotion, no installed-library, CLIST, PRV, Z4CL, DATA or RZ write exists in this tool.

Nothing here runs on z/OS unless a z/OS sub-command is invoked (each one on the user's approval only):
  zos11_release.py --deck NAME OUT.jcl          write a deck (prefix @@HLQ@@.PACMAN.RZ21)
  zos11_release.py --selftest                   local checks (decks, audits, the D46 object rule on synthetic images)
  zos11_release.py --check NAME SPOOLDIR        check a downloaded job (BL C1 C2)
  zos11_release.py --objeq OLD_DIR NEW_DIR      object gate: 12 modules = 2.0-zos (ZOS-10 rules), PACINPT = D46 only
  zos11_release.py --zos preflight|upload|objects|rz-objects|load|hiscore [--out DIR]   z/OS reads; upload writes
                                                only RZ21.COBOL / COPY / ASM / CLIST members (byte-verified)
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests'), str(R / 'tools')]
import zos10_release as Z10  # noqa: E402

SOURCE_COMMIT = '35b803e30011fed7427b2f9c5d3492530d985d20'      # the ZOS-11 step 1 commit (source of record)
QUAL = 'RZ21'                                                    # new build namespace: z/OS release 2.1
PFX = Z10.PFX
NEW = f'{PFX}.{QUAL}'
FROZEN_RZ = f'{PFX}.RZ'                                          # 2.0-zos build of record: read only, never in a deck
JOBS = {'AL': 'PACZ11AL', 'BL': 'PACZ11BL', 'C1': 'PACZ11C1', 'C2': 'PACZ11C2'}
# step 2B (authorisation of 2026-10-21): CLIST backup, program promotion, CLIST promotion, AMASPZAP dumps, installed P1
JOBS_2B = {'PV': 'PACZ11PV', 'IP': 'PACZ11IP', 'IC': 'PACZ11IC', 'ZD': 'PACZ11ZD', 'P1': 'PACZ11P1'}
PRV20 = f'{PFX}.PRV20.CLIST'                                      # new: the installed 2.0-zos CLIST before ZOS-11
STEPS_2B = {'PV': ['PRV1'], 'IP': ['PROM1'], 'IC': ['PROM2'], 'ZD': ['ZAPR21', 'ZAPINS'], 'P1': Z10.P1}
LIBS = [l for l, _, _ in Z10.RZ_SETS]                             # COBOL COPY ASM OBJ LOAD CLIST (ZOS-1 / ZOS-10 DCBs)
OUT = R / 'build/zos/Z11'
Z10OBJ = R / 'build/zos/Z10OBJ'                                   # RZ.OBJ read at ZOS-10 (JOB04820 objects)
Z10OBJ_SHA = R / 'build/zos/Z10/z10obj-sha256.txt'
Z10_LOAD_SHA = '306d973612be6f5bc5cff2043f17558901f3395c46cdc2ede681ed639d2a0c64'   # installed = RZ.LOAD(PACMAIN)
Z10_CLIST = R / 'build/zos/Z10IN/CLIST.bin'                       # installed CLIST(PACMAN) read at ZOS-10 closure
Z10_CLIST_SHA = 'a437082ac5c67ab2cea5e28d44b3754869b713baf7829e4a733ebb6e82958ab3'
PRV_SHA = '6e0a68ec7cdc6791d2890167fde6d5900d47ab05f8c9c13be06ba3ceeacebef8'      # PRV.CLIST (zos-9 CLIST)
PACZ6D_SHA = 'ed756b362b1c2853d30eafb0e952936c6dd2d9ac246d7a749dbcd777499a3823'
RZ21_LOAD_SHA = '798596b94ec2d960581a8dd5947d79288bfdb51e92bbbca728b6340d723a5386'  # step 2A, PACZ11BL JOB09451


def bind():
    """Bind the new prefix and job names into the frozen ZOS-10 module (this process only)."""
    Z10.RZ = NEW
    Z10.JOBS = dict(JOBS)
    Z10.NAMES = {'AL': {f'{NEW}.{l}' for l in LIBS},
                 'BL': {f'{NEW}.{l}' for l in ('COBOL', 'COPY', 'ASM', 'OBJ', 'LOAD')},
                 'C1': {f'{NEW}.LOAD'}, 'C2': {f'{NEW}.LOAD'},
                 'PV': {f'{PFX}.CLIST', PRV20}, 'P1': {f'{PFX}.LOAD'}}
    Z10.JOBS.update({k: JOBS_2B[k] for k in ('PV', 'P1')})
    Z10.PRV = PRV20
    Z10._run_health = run_health


def deck(name):
    bind()
    if name in ('IP', 'IC', 'ZD'):
        text = deck_2b(name)
    else:
        text = Z10.deck(name).replace("'PACMAN ZOS10 ", "'PACMAN ZOS11 ")
    audit(name, text)
    return text


def deck_2b(name):
    _, zt = Z10._zt()
    job = JOBS_2B[name]
    out = zt.job_card(job, f'PACMAN ZOS11 {job}')
    if name in ('IP', 'IC'):
        lib, mem, step = ('LOAD', 'PACMAIN', 'PROM1') if name == 'IP' else ('CLIST', 'PACMAN', 'PROM2')
        out += (f'//{step}    EXEC PGM=IEBCOPY\n//SYSPRINT DD SYSOUT=A\n'
                f'//I        DD DSN={NEW}.{lib},DISP=SHR\n//O        DD DSN={PFX}.{lib},DISP=SHR\n'
                f'//SYSIN    DD *\n  COPY OUTDD=O,INDD=I\n  SELECT MEMBER=(({mem},,R))\n/*\n')
    else:                       # read-only AMASPZAP dumps (the MVS-G8 / MVS-10 pattern: DUMP only, SYSLIB DISP=SHR)
        for step, lib in (('ZAPR21', NEW), ('ZAPINS', PFX)):
            out += (f'//{step:<8} EXEC PGM=AMASPZAP\n//SYSPRINT DD SYSOUT=A\n'
                    f'//SYSLIB   DD DSN={lib}.LOAD,DISP=SHR\n//SYSIN    DD *\n DUMP PACMAIN ALL\n/*\n')
    return out


def audit(name, text):
    """The frozen ZOS-10 audit with the new prefix, plus: no frozen RZ, installed LOAD / CLIST, PRV, Z4CL dataset."""
    bind()
    if name in JOBS_2B:
        return audit_2b(name, text)
    Z10.audit(name, text)
    import re
    dsn = {re.sub(r'\(.*', '', d) for d in re.findall(r'DSN=([^,\s]+)', text)} - Z10.SYSTEM
    assert all(d.startswith(NEW + '.') for d in dsn), f'outside {NEW}: {sorted(dsn)}'
    for bad in (f'{FROZEN_RZ}.', f'{PFX}.LOAD', f'{PFX}.CLIST', f'{PFX}.PRV', f'{PFX}.Z4CL', 'IEBCOPY'):
        assert not re.search(re.escape(bad) + r'(?![A-Z0-9])', text.replace(NEW, '')), f'forbidden {bad}'
    return True


def audit_2b(name, text):
    """Step 2B decks, fail closed: job card, exact steps and programs, the exact dataset set and dispositions, no RZ /
    PRV.CLIST / DATA / PACHS / DELETE / SCRATCH / PURGE; IP / IC copy exactly one member (replace) from RZ21; ZD only
    'DUMP PACMAIN ALL' (no VER / REP / other AMASPZAP statement)."""
    import re
    _, zt = Z10._zt()
    job = JOBS_2B[name]
    assert text.startswith(f'//{job} ') and text.count(' JOB ') == 1, 'job card'
    parts = zt.steps_of_deck(text)
    assert list(parts) == STEPS_2B[name], f'steps {list(parts)}'
    pg = {re.search(r'EXEC PGM=(\w+)', t).group(1) for t in parts.values()}
    assert pg == {'PV': {'IEBCOPY'}, 'IP': {'IEBCOPY'}, 'IC': {'IEBCOPY'}, 'ZD': {'AMASPZAP'},
                  'P1': {Z10.LOAD}}[name], pg
    assert not re.search(r'PACHS(?!IO)', text) and 'HISCORE' not in text
    for w in ('.DATA', 'DELETE', 'SCRATCH', 'PURGE', 'ZHEIST', 'PACZ6D', f'{FROZEN_RZ}.', f'{PFX}.PRV.'):
        assert w not in text, f'forbidden {w!r}'
    dsd = sorted(re.findall(r'DSN=([^,\s]+),DISP=(\(NEW,CATLG,CATLG\)|SHR)', text))
    assert len(dsd) == len(re.findall(r'DSN=', text)), 'every DSN with DISP SHR or NEW'
    want = {'PV': [(f'{PFX}.CLIST', 'SHR'), (PRV20, '(NEW,CATLG,CATLG)')],
            'IP': [(f'{NEW}.LOAD', 'SHR'), (f'{PFX}.LOAD', 'SHR')],
            'IC': [(f'{NEW}.CLIST', 'SHR'), (f'{PFX}.CLIST', 'SHR')],
            'ZD': [(f'{NEW}.LOAD', 'SHR'), (f'{PFX}.LOAD', 'SHR')],
            'P1': [(f'{PFX}.LOAD', 'SHR')] * 3}[name]
    assert dsd == sorted(want), dsd
    if name == 'PV':
        Z10.audit('PV', text)
    if name == 'P1':
        Z10.audit('P1', text)
    if name in ('IP', 'IC'):
        lib, mem = ('LOAD', 'PACMAIN') if name == 'IP' else ('CLIST', 'PACMAN')
        assert f'//I        DD DSN={NEW}.{lib},DISP=SHR\n//O        DD DSN={PFX}.{lib},DISP=SHR\n' in text
        assert re.findall(r'^  (\S.*)$', text, re.M) == ['COPY OUTDD=O,INDD=I', f'SELECT MEMBER=(({mem},,R))'], 'SYSIN'
    if name == 'ZD':
        sysin = re.findall(r'//SYSIN    DD \*\n(.*?)/\*\n', text, re.S)
        assert sysin == [' DUMP PACMAIN ALL\n'] * 2, sysin
        assert not re.search(r'^ ?(VER|VERIFY|REP|REPLACE|NAME|IDRDATA|SETSSI|CHECKSUM|BASE|CCHHR|ABSDUMP)\b', text,
                             re.M)
    return True


def run_health(d, name):
    """zos10_release._run_health with the STEPLIB of the new build (every run step COND CODE 0000, PACMAIN, SYSOUT
    only, STEPLIB retained once per step, no CEE / abend / output-limit text)."""
    import re
    from zos_equiv import zos_runs
    job, msg, jes = Z10._jes(d)
    _, names, runs = zos_runs(d)
    lib = (PFX if name == 'P1' else NEW).replace('@@HLQ@@', 'Z00000') + '.LOAD'
    bad = []
    if job['jobname'] != {**JOBS, **JOBS_2B}[name] or names != Z10.STEPS[name]:
        bad.append(f'job {job["jobname"]} steps {names}')
    for s in names:
        if Z10._cc(msg, job['jobname'], s) != '0000':
            bad.append(f'{s}: not COND CODE 0000')
        if runs[s]['pgm'] != Z10.LOAD or runs[s]['extra']:
            bad.append(f'{s}: {runs[s]["pgm"]} extra {runs[s]["extra"]}')
    if len(re.findall(rf'IGD104I {re.escape(lib)}\s+RETAINED,\s+DDNAME=STEPLIB', msg)) != len(names):
        bad.append(f'STEPLIB {lib} not retained once per step')
    if re.search(r'CEE\d{4}|ABEND|\$HASP375|IEA995', jes):
        bad.append('CEE / abend / output-limit text')
    if re.search(r'PACHS(?!IO)|\.DATA\b|HISCORE', msg + jes):
        bad.append('PACHS / DATA / HISCORE in the job log')
    return runs, bad


# ---- the D46 object rule ---------------------------------------------------------------------------------------------
D46_MEMBER = 'PACINPT'
_EB = {d: 0xF0 + d for d in range(10)}


def d46_pair(buf_old, buf_new, p):
    """Is the byte difference at p one encoding of the literal 123 -> 124? Binary (00 7B -> 00 7C), packed
    (12 3x -> 12 4x, x a sign nibble), zoned / EBCDIC display (F1 F2 F3 -> F1 F2 F4, signed C3 -> C4)."""
    o, n = buf_old[p], buf_new[p]
    pre = buf_old[max(0, p - 2):p]
    if buf_new[max(0, p - 2):p] != pre:
        return None
    if (o, n) == (0x7B, 0x7C) and p >= 1 and pre[-1:] == b'\x00':
        return 'binary X\'007B\' -> X\'007C\''
    if o & 0x0F == n & 0x0F and o & 0x0F in (0xC, 0xD, 0xF) and (o >> 4, n >> 4) == (3, 4) and pre[-1:] == b'\x12':
        return f'packed X\'123{o & 15:X}\' -> X\'124{n & 15:X}\''
    if (o, n) in ((0xF3, 0xF4), (0xC3, 0xC4)) and pre == bytes([_EB[1], _EB[2]]):
        return f'zoned X\'F1F2{o:02X}\' -> X\'F1F2{n:02X}\''
    return None


# the RT-TSC decode literal table of PACINPT (PIC 9(4) packed, 3 bytes each): 247 248 122 [123 -> 124] 249 110 -
# the same table the MVS-10 AMASPZAP comparison showed (docs/evidence/mvs10-release.md section 3)
TABLE = (bytes.fromhex('00247C00248C00122C00123C00249C00110C'), bytes.fromhex('00247C00248C00122C00124C00249C00110C'))
TABLE20 = 'the RT-TSC literal table 247C 248C 122C 123C 249C 110C'


def _views(img, sp):
    """One image -> (loaded / structural view: every logical record but the D_MCODE TXT records, the D_MCODE ED with
    its class length masked; the decompressed D_MCODE). Raises ValueError on any format rule of zos10_release."""
    L = Z10._logical(Z10._neutral(img, sp))
    ed, chunks, _, u = Z10._dmcode(L)
    skip = {c[0] for c in chunks}
    view = []
    for i, (t, rs) in enumerate(L):
        if i in skip:
            continue
        b = b''.join(rs)
        if t == 0 and rs[0] == ed:
            b = b[:24] + b'\0\0\0\0' + b[28:]
        view.append((t, b))
    return view, u


def d46_eq(old, new):
    """PACINPT 2.0 / 2.1 images -> (state, detail, findings). D46-ONLY when, after the frozen timestamp spans and the
    compressed D_MCODE representation (zos10 rules), the loadable / structural records differ in exactly one byte: the
    packed literal X'00123C' -> X'00124C' inside the RT-TSC literal table (TABLE), and every difference in the
    decompressed D_MCODE is one encoding of the literal 123 -> 124 (d46_pair; each reported). Anything else: DIFFERENT
    (STOP)."""
    m = D46_MEMBER
    try:
        so, sn = Z10.spans(m, old), Z10.spans(m, new)
        (vo, uo), (vn, un) = _views(old, so), _views(new, sn)
    except ValueError as e:
        return 'FORMAT', str(e), []
    if len(vo) != len(vn) or [(t, len(b)) for t, b in vo] != [(t, len(b)) for t, b in vn]:
        return 'DIFFERENT', f'{m}: logical record structure differs ({len(vo)} / {len(vn)})', []
    found, bad = [], []
    for i, ((t, a), (_, b)) in enumerate(zip(vo, vn)):
        for p in (p for p in range(len(a)) if a[p] != b[p]):
            k = d46_pair(a, b, p)
            ctx = TABLE20 if a[p - 11:p + 7] == TABLE[0] and b[p - 11:p + 7] == TABLE[1] else 'outside the table'
            (found if k else bad).append(f'logical record {i + 1} type {t:X} byte {p}: {a[p]:02X} -> {b[p]:02X}'
                                         + (f' ({k}, {ctx})' if k else ''))
    loaded = len(found)
    tbl = [f for f in found if TABLE20 in f]
    if found and (len(found) != 1 or len(tbl) != 1):
        bad += [f for f in found if f not in tbl]
        found = tbl
        loaded = len(found)
    if len(uo) != len(un):
        bad.append(f'decompressed D_MCODE length {len(uo)} / {len(un)}')
    else:
        for p in (p for p in range(len(uo)) if uo[p] != un[p]):
            k = d46_pair(uo, un, p)
            (found if k else bad).append(f'D_MCODE byte {p}: {uo[p]:02X} -> {un[p]:02X}' + (f' ({k})' if k else ''))
    if bad:
        return 'DIFFERENT', f'{m}: {len(bad)} unexplained difference(s): {bad[:8]}', found + bad
    if not loaded:
        return 'DIFFERENT', f'{m}: no D46 literal change in the loaded text (the 2.1 change is missing)', found
    return 'D46-ONLY', f'{m}: masked {so} / {sn}; {len(found)} D46 byte(s), {loaded} in the loaded text; D_MCODE ' \
                       f'decompressed {len(un)} bytes ({len(found) - loaded} D46 byte(s))', found


def objeq_dirs(old_dir, new_dir):
    """12 modules: zos10_release.objeq (IDENTICAL-MODULO-TIMESTAMP / EQUIVALENT-DMCODE-RECOMPRESSED); PACINPT: d46_eq
    (and it must NOT be equal under the 2.0 rules: the D46 change must be present)."""
    res, ok = {}, True
    for m in Z10.OBJECTS:
        a, b = Path(old_dir, f'OBJ.{m}.bin').read_bytes(), Path(new_dir, f'OBJ.{m}.bin').read_bytes()
        if m == D46_MEMBER:
            s10 = Z10.objeq(a, b, m)
            st, det, found = d46_eq(a, b)
            res[m] = {'state': st, 'detail': det, 'differences': found, 'zos10 rules alone': s10[0]}
            ok &= st == 'D46-ONLY' and s10[0] not in Z10.OBJ_PASS
        else:
            st, det = Z10.objeq(a, b, m)
            res[m] = {'state': st, 'detail': det}
            ok &= st in Z10.OBJ_PASS
    return ok, res


def frozen_baseline_ok(d=Z10OBJ):
    want = dict(reversed(l.split()) for l in Z10OBJ_SHA.read_text().splitlines())
    got = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(Path(d).glob('OBJ.*.bin'))}
    return got == want and len(got) == 13, got


# ---- checkers --------------------------------------------------------------------------------------------------------
def check(name, d):
    bind()
    if name == 'BL':
        ok, res = Z10.check_bl(d)
        res['listing: PACINPT compiled from RZ21.COBOL'] = _pacinpt_compiled(d)
        ok &= res['listing: PACINPT compiled from RZ21.COBOL']
        return ok, res
    if name == 'PV':
        return Z10.check_copy(d, 'PV')
    if name in ('IP', 'IC'):
        return check_promote(d, name)
    if name == 'ZD':
        return check_zap(d)
    return Z10.check_runs(d, name, cv1=cv1_dir() if name == 'P1' else None)


def cv1_dir():
    d = sorted((R / 'build/zos').glob('PACZ11C1-JOB*'))
    assert len(d) == 1, d
    return d[0]


def check_promote(d, name):
    """PACZ11IP / IC: the one IEBCOPY step RC 0, its member copied and replaced, 1 of 1, highest severity 0."""
    import re
    job, msg, jes = Z10._jes(d)
    s = STEPS_2B[name][0]
    mem = 'PACMAIN' if name == 'IP' else 'PACMAN'
    sp = '\n'.join(Z10._sysprint(d, s) or [])
    res = {'job': job['jobname'], 'RC': Z10._cc(msg, job['jobname'], s),
           'copied and replaced': bool(re.search(rf'MEMBER {mem}\s+HAS BEEN COPIED\s+AND REPLACED', sp) or
                                       re.search(rf'IGW01552I .*{mem}', sp)),
           '1 of 1 members': re.search(r'IGW01550I 1 OF 1 SPECIFIED\s+MEMBERS WERE COPIED', sp) is not None,
           'highest severity 0': re.search(r'END OF JOB - 0 WAS HIGHEST SEVERITY CODE', sp) is not None,
           'no abend / IEC / output-limit text': not re.search(r'ABEND|IEC\d{3}I|\$HASP375|IEA995', msg + jes)}
    ok = res['job'] == JOBS_2B[name] and res['RC'] == '0000' and all(v for k, v in res.items()
                                                                       if k not in ('job', 'RC'))
    return ok, res


def zap_dump(lines):
    """One AMASPZAP SYSPRINT -> (statement echo, [normalised dump rows]): page headings (the lines carrying the date,
    time or page number) dropped; every other line kept verbatim (right-stripped) for comparison."""
    import re
    rows = []
    for l in lines:
        t = l.rstrip()
        if not t.strip() or re.search(r'\bPAGE\s+\d+|\d\d[./]\d\d[./]\d\d|\d\d[.:]\d\d[.:]\d\d', t):
            continue
        rows.append(t)
    return rows


def check_zap(d):
    """PACZ11ZD: both AMASPZAP steps RC 0, the DUMP statement echoed, no VER / REP processed, and the two dumps (RZ21,
    installed) identical row for row after the page headings; the dump holds hex rows."""
    import re
    job, msg, jes = Z10._jes(d)
    res, dumps = {'job': job['jobname']}, {}
    for s in STEPS_2B['ZD']:
        ls = Z10._sysprint(d, s) or []
        res[f'{s} RC'] = Z10._cc(msg, job['jobname'], s)
        dumps[s] = zap_dump(ls)
        res[f'{s} rows'] = len(dumps[s])
        res[f'{s} hex rows'] = sum(1 for r in dumps[s] if re.match(r'\s*[0-9A-F]{4,8}\s+[0-9A-F]{8}\b', r))
        res[f'{s} DUMP echoed, no VER / REP'] = any('DUMP PACMAIN ALL' in r for r in dumps[s]) and \
            not any(re.search(r'\b(VER|REP)\b\s+[0-9A-F]', r) for r in dumps[s])
    a, b = dumps['ZAPR21'], dumps['ZAPINS']
    diff = [i for i in range(max(len(a), len(b))) if (a[i:i + 1] or [None]) != (b[i:i + 1] or [None])]
    res['differing rows'] = [(i, a[i] if i < len(a) else None, b[i] if i < len(b) else None) for i in diff[:20]]
    res['dumps identical'] = not diff and bool(a)
    res['sha256 dump rows'] = hashlib.sha256('\n'.join(b).encode()).hexdigest()
    res['no abend / output-limit text'] = not re.search(r'ABEND|\$HASP375|IEA995', msg + jes)
    ok = res['job'] == JOBS_2B['ZD'] and all(res[f'{s} RC'] == '0000' for s in STEPS_2B['ZD']) and \
        res['dumps identical'] and res['ZAPINS hex rows'] > 0 and res['no abend / output-limit text'] and \
        all(res[f'{s} DUMP echoed, no VER / REP'] for s in STEPS_2B['ZD'])
    return ok, res


def _pacinpt_compiled(d):
    import re
    msg = next(Path(d).glob('*-JESYSMSG.txt')).read_text()
    lib = NEW.replace('@@HLQ@@', 'Z00000')
    return re.search(rf'{re.escape(lib)}\.COBOL\s+RETAINED', msg) is not None or f'{lib}.COBOL' in msg


# ---- z/OS (each sub-command only on the user's approval) -------------------------------------------------------------
def _zowe():
    from zoslib import zowe
    return zowe


def _git(*a):
    return subprocess.run(['git', *a], cwd=R, capture_output=True, text=True, check=True).stdout.strip()


def local_source_ok():
    """Every uploaded file (19 sources + the z/OS CLIST) = its blob in SOURCE_COMMIT, working tree clean for them."""
    res = {}
    files = [f'{Z10.SRC[l][0]}/{m}{Z10.SRC[l][1]}' for l, ms in Z10.RELEASE.items() for m in ms] + \
        ['src/zos/PACMAN.clist']
    for f in files:
        blob = _git('rev-parse', f'{SOURCE_COMMIT}:./{f}')
        res[f] = _git('hash-object', f) == blob
    res['src tree = SOURCE_COMMIT'] = _git('diff', '--name-only', SOURCE_COMMIT, '--', 'src') == '' and \
        _git('status', '--porcelain', '--', 'src') == ''
    res['PACINPT: IF WS-V = 124, no IF WS-V = 123'] = (R / 'src/cobol/PACINPT.cob').read_text().count(
        '           IF WS-V = 124\n') == 1 and 'IF WS-V = 123' not in (R / 'src/cobol/PACINPT.cob').read_text()
    return all(res.values()), res


def _list(pattern):
    d = _zowe()('zos-files', 'list', 'data-set', pattern, '-a', json_out=True)
    return d['data']['apiResponse']['items']


def _download(ds, f):
    _zowe()('zos-files', 'download', 'data-set', ds, '--binary', '-f', str(f), json_out=True)
    return Path(f).read_bytes()


def zos_preflight(h='Z00000', out=OUT / 'preflight'):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    z = _zowe()
    st = z('zosmf', 'check', 'status', json_out=True)['data']
    res = {'z/OSMF': {k: st.get(k) for k in ('zos_version', 'zosmf_hostname', 'zosmf_port', 'zosmf_saf_realm',
                                              'zosmf_full_version')}}
    p = f'{h}.PACMAN'
    allds = sorted(i['dsname'] for i in _list(p))
    (out / 'datasets.json').write_text(json.dumps(allds, indent=1))
    res['Z00000.PACMAN.* datasets'] = len(allds)
    res[f'no dataset under {p}.{QUAL}'] = not [d for d in allds if d == f'{p}.{QUAL}' or d.startswith(f'{p}.{QUAL}.')]
    res[f'pattern {p}.{QUAL}.* lists nothing'] = [i['dsname'] for i in _list(f'{p}.{QUAL}.*')] == []
    res['frozen RZ libraries present'] = {l: f'{p}.RZ.{l}' in allds for l in LIBS}
    lb = _download(f'{p}.LOAD(PACMAIN)', out / 'LOAD.PACMAIN.bin')
    res['installed LOAD(PACMAIN) = 2.0-zos (SHA-256 306d9736...)'] = hashlib.sha256(lb).hexdigest() == Z10_LOAD_SHA
    rb = _download(f'{p}.RZ.LOAD(PACMAIN)', out / 'RZ.LOAD.PACMAIN.bin')
    res['RZ.LOAD(PACMAIN) = 2.0-zos'] = hashlib.sha256(rb).hexdigest() == Z10_LOAD_SHA
    cb = _download(f'{p}.CLIST(PACMAN)', out / 'CLIST.bin')
    res['installed CLIST(PACMAN) = the 2.0-zos CLIST (ZOS-10 closure read)'] = cb == Z10_CLIST.read_bytes()
    res['installed CLIST says ARROWS = PF7/8/10/11'] = b''.join(
        bytes([c]) for c in cb).decode('cp037').count('ARROWS = PF7/8/10/11') == 1
    ok = all(v for k, v in res.items() if isinstance(v, bool)) and all(res['frozen RZ libraries present'].values())
    return ok, res


def zos_upload(h='Z00000', out=OUT / 'upload'):
    """The 19 release sources and the CLIST render into RZ21 (members are new: the libraries were allocated empty);
    each member downloaded back in binary and compared."""
    from zos_upload import upload_verify
    ok0, src = local_source_ok()
    if not ok0:
        return False, {'local source != SOURCE_COMMIT': src}
    p = f'{h}.PACMAN'
    for l in LIBS:
        if _zowe()('zos-files', 'list', 'all-members', f'{p}.{QUAL}.{l}', json_out=True)['data']['apiResponse'][
                'items']:
            return False, {f'{QUAL}.{l}': 'not empty before the upload: STOP'}
    res, ok = {}, True
    for lib, mems in Z10.RELEASE.items():
        d, ext = Z10.SRC[lib]
        for m in mems:
            g, t = upload_verify(R / d / f'{m}{ext}', f'{QUAL}.{lib}', m, h, Path(out))
            res[f'{lib}({m})'] = t
            ok &= g
            if not g:
                return False, res
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / 'PACMAN.clist'
        f.write_text(Z10.release_clist(p) + '\n', encoding='ascii')
        g, t2 = upload_verify(f, f'{QUAL}.CLIST', 'PACMAN', h, Path(out))
    res['CLIST(PACMAN)'] = t2
    return ok and g, res


def zos_objects(h='Z00000', lib=QUAL, out=OUT / 'OBJ'):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    mem = sorted(_zowe()('zos-files', 'list', 'all-members', f'{h}.PACMAN.{lib}.OBJ', json_out=True)['data'][
        'apiResponse']['items'], key=lambda x: x['member'])
    mem = [m['member'] for m in mem]
    if mem != sorted(Z10.OBJECTS):
        return False, {f'{lib}.OBJ members': mem}
    for m in Z10.OBJECTS:
        _download(f'{h}.PACMAN.{lib}.OBJ({m})', out / f'OBJ.{m}.bin')
    return True, {'downloaded': Z10.OBJECTS, 'sha256': {m: hashlib.sha256((out / f'OBJ.{m}.bin').read_bytes())
                                                        .hexdigest() for m in Z10.OBJECTS}}


def zos_load(h='Z00000', out=OUT / 'LOAD'):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    p = f'{h}.PACMAN'
    mem = Z10._members(f'{p}.{QUAL}.LOAD', True)
    rz = Z10._members(f'{p}.RZ.LOAD', True)
    att = lambda d: {k: d.get('PACMAIN', {}).get(k) for k in Z10.LOAD_ATTR}     # noqa: E731
    new = _download(f'{p}.{QUAL}.LOAD(PACMAIN)', out / 'LOAD.RZ21.PACMAIN.bin')
    old = (R / 'build/zos/Z10/LOAD.RZ.PACMAIN.bin').read_bytes()
    diff = [i for i in range(min(len(old), len(new))) if old[i] != new[i]]
    runs = []
    for i in diff:
        if runs and i - runs[-1][1] <= 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    res = {'RZ21.LOAD members': sorted(mem), 'RZ21 PACMAIN attributes': att(mem), 'RZ PACMAIN attributes': att(rz),
           'bytes old / new': [len(old), len(new)], 'sha256 new': hashlib.sha256(new).hexdigest(),
           'differing bytes': len(diff),
           'runs': [{'offset': a, 'old': old[a:b + 1].hex(), 'new': new[a:b + 1].hex(),
                     'old ebcdic': old[a:b + 1].decode('cp037', 'replace'),
                     'new ebcdic': new[a:b + 1].decode('cp037', 'replace')} for a, b in runs]}
    ok = sorted(mem) == ['PACMAIN'] and att(mem)['amode'] == '24' and att(mem)['rmode'] == '24'
    return ok, res


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def zos_state(h='Z00000', out=None):
    """Read-only state of every member step 2B may touch or must not touch: binary SHA-256 of the installed, RZ and RZ21
    PACMAIN and PACZ6D, the installed / RZ / RZ21 / PRV / PRV20 CLIST, the installed LOAD directory, RZ.OBJ, HISCORE."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    p = f'{h}.PACMAN'
    allds = {i['dsname'] for i in _list(p)}
    st = {'datasets': len(allds), 'PRV20.CLIST exists': f'{p}.PRV20.CLIST' in allds}
    for key, ds in (('LOAD(PACMAIN)', f'{p}.LOAD(PACMAIN)'), ('LOAD(PACZ6D)', f'{p}.LOAD(PACZ6D)'),
                    ('RZ.LOAD(PACMAIN)', f'{p}.RZ.LOAD(PACMAIN)'), ('RZ21.LOAD(PACMAIN)', f'{p}.{QUAL}.LOAD(PACMAIN)'),
                    ('CLIST(PACMAN)', f'{p}.CLIST(PACMAN)'), ('RZ.CLIST(PACMAN)', f'{p}.RZ.CLIST(PACMAN)'),
                    ('RZ21.CLIST(PACMAN)', f'{p}.{QUAL}.CLIST(PACMAN)'), ('PRV.CLIST(PACMAN)', f'{p}.PRV.CLIST(PACMAN)')
                    ) + ((('PRV20.CLIST(PACMAN)', f'{p}.PRV20.CLIST(PACMAN)'),) if st['PRV20.CLIST exists'] else ()):
        st[key] = _sha(_download(ds, out / (key.replace('(', '.').replace(')', '') + '.bin')))
    cb = (out / 'CLIST.PACMAN.bin').read_bytes()
    recs = [cb[i:i + 80].decode('cp037').rstrip() for i in range(0, len(cb), 80)]
    st['CLIST ARROWS'] = [l for l in recs if 'ARROWS =' in l]
    z = Z10_CLIST.read_bytes()
    old = [z[i:i + 80].decode('cp037').rstrip() for i in range(0, len(z), 80)]
    st['CLIST records differing from 2.0-zos'] = [(i + 1, old[i] if i < len(old) else None, recs[i] if i < len(recs)
                                                   else None) for i in range(max(len(old), len(recs)))
                                                  if (old[i:i + 1] or [None]) != (recs[i:i + 1] or [None])]
    st['LOAD directory'] = {m: {k: v.get(k) for k in Z10.LOAD_ATTR} for m, v in Z10._members(f'{p}.LOAD', True).items()}
    st['RZ21.LOAD directory'] = {m: {k: v.get(k) for k in Z10.LOAD_ATTR}
                                 for m, v in Z10._members(f'{p}.{QUAL}.LOAD', True).items()}
    st['members'] = {l: sorted(Z10._members(f'{p}.{l}')) for l in ('RZ.OBJ', 'RZ.LOAD', 'RZ.CLIST', 'PRV.CLIST',
                                                                    'CLIST', f'{QUAL}.LOAD', f'{QUAL}.CLIST')}
    o = out / 'RZOBJ'
    o.mkdir()
    want = dict(reversed(l.split()) for l in Z10OBJ_SHA.read_text().splitlines())
    st['RZ.OBJ = ZOS-10 record (13)'] = all(_sha(_download(f'{p}.RZ.OBJ({m})', o / f'OBJ.{m}.bin')) ==
                                            want[f'OBJ.{m}.bin'] for m in Z10.OBJECTS)
    st['HISCORE'] = Z10.zos_closure(h)[1]['HISCORE']
    return st


def gate(phase, st, pre=None):
    """Expected state per phase: pre (before PV), pv (after PV), ip (after IP), ic / final (after IC)."""
    rel = Z10.release_clist('Z00000.PACMAN')
    import zoslib
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / 'c'
        f.write_text(rel + '\n', encoding='ascii')
        rel_sha = _sha(zoslib.fixed_records(f))
    prog = RZ21_LOAD_SHA if phase in ('ip', 'ic', 'final') else Z10_LOAD_SHA
    clist = rel_sha if phase in ('ic', 'final') else Z10_CLIST_SHA
    r = {'LOAD(PACMAIN)': st['LOAD(PACMAIN)'] == prog,
         'RZ21.LOAD(PACMAIN) = step 2A build': st['RZ21.LOAD(PACMAIN)'] == RZ21_LOAD_SHA,
         'RZ.LOAD(PACMAIN) = 2.0-zos': st['RZ.LOAD(PACMAIN)'] == Z10_LOAD_SHA,
         'LOAD(PACZ6D) unchanged': st['LOAD(PACZ6D)'] == PACZ6D_SHA,
         'CLIST(PACMAN)': st['CLIST(PACMAN)'] == clist,
         'CLIST ARROWS': len(st['CLIST ARROWS']) == 1 and ('ARROWS = PF7/8/10/12,' if phase in ('ic', 'final')
                                                           else 'ARROWS = PF7/8/10/11,') in st['CLIST ARROWS'][0],
         'CLIST differs from 2.0-zos only in the ARROWS line': st['CLIST records differing from 2.0-zos'] == (
             [] if phase not in ('ic', 'final') else
             [(25, '/* 150 MS, SEE SPEED; ARROWS = PF7/8/10/11, P = PF9 PAUSE WITH THE */',
               '/* 150 MS, SEE SPEED; ARROWS = PF7/8/10/12, P = PF9 PAUSE WITH THE */')]),
         'RZ.CLIST(PACMAN) = 2.0-zos': st['RZ.CLIST(PACMAN)'] == Z10_CLIST_SHA,
         'RZ21.CLIST(PACMAN) = 2.1 release render': st['RZ21.CLIST(PACMAN)'] == rel_sha,
         'PRV.CLIST(PACMAN) = zos-9 CLIST': st['PRV.CLIST(PACMAN)'] == PRV_SHA,
         'PRV20.CLIST': (not st['PRV20.CLIST exists']) if phase == 'pre' else
         st.get('PRV20.CLIST(PACMAN)') == Z10_CLIST_SHA,
         'RZ.OBJ = ZOS-10 record (13)': st['RZ.OBJ = ZOS-10 record (13)'],
         'RZ / PRV / RZ21 member lists': st['members']['RZ.OBJ'] == sorted(Z10.OBJECTS) and
         st['members']['RZ.LOAD'] == ['PACMAIN'] and st['members']['RZ.CLIST'] == ['PACMAN'] and
         st['members']['PRV.CLIST'] == ['PACMAN'] and st['members'][f'{QUAL}.LOAD'] == ['PACMAIN'] and
         st['members'][f'{QUAL}.CLIST'] == ['PACMAN'],
         'HISCORE': st['HISCORE'] == [Z10.HISCORE]}
    if pre is not None:
        r['installed LOAD directory: only PACMAIN may change'] = \
            {m: a for m, a in st['LOAD directory'].items() if m != 'PACMAIN'} == \
            {m: a for m, a in pre['LOAD directory'].items() if m != 'PACMAIN'}
        r['installed CLIST library members unchanged'] = st['members']['CLIST'] == pre['members']['CLIST']
        r['datasets: + PRV20.CLIST only'] = st['datasets'] == pre['datasets'] + (phase != 'pre')
    if phase in ('ip', 'ic', 'final'):
        r['LOAD(PACMAIN) attributes = RZ21'] = st['LOAD directory']['PACMAIN'] == st['RZ21.LOAD directory']['PACMAIN']
    return all(r.values()), r


def zos_hiscore(h='Z00000'):
    return Z10.zos_closure(h)


# ---- selftest --------------------------------------------------------------------------------------------------------
def selftest():
    res, det = {}, {}
    for n in JOBS:
        t = deck(n)
        res[f'deck {JOBS[n]} audit'] = True
        res[f'deck {JOBS[n]} on disk = generated'] = (R / f'jcl/zos/{JOBS[n]}.jcl').read_text() == t
    base = {n: deck(n) for n in JOBS}
    mut = {'BL writes the frozen RZ.OBJ': ('BL', base['BL'].replace(f'//OBJ      DD DSN={NEW}.OBJ',
                                                                     f'//OBJ      DD DSN={FROZEN_RZ}.OBJ')),
           'BL links into the installed LOAD': ('BL', base['BL'].replace(f'SYSLMOD  DD DSN={NEW}.LOAD',
                                                                         f'SYSLMOD  DD DSN={PFX}.LOAD')),
           'BL compiles from the frozen RZ.COBOL': ('BL', base['BL'].replace(f'{NEW}.COBOL(PACINPT)',
                                                                             f'{FROZEN_RZ}.COBOL(PACINPT)')),
           'C1 installed load': ('C1', base['C1'].replace(f'{NEW}.LOAD', f'{PFX}.LOAD', 1)),
           'C1 frozen RZ load': ('C1', base['C1'].replace(f'{NEW}.LOAD', f'{FROZEN_RZ}.LOAD', 1)),
           'C2 PACHS DD': ('C2', base['C2'].replace('//SYSOUT', '//PACHS    DD DUMMY\n//SYSOUT', 1)),
           'C2 DATA': ('C2', base['C2'].replace(f'DSN={NEW}.LOAD', f'DSN={PFX}.DATA', 1)),
           'AL catalog-delete': ('AL', base['AL'].replace('(NEW,CATLG,CATLG)', '(NEW,CATLG,DELETE)', 1)),
           'AL reuses RZ': ('AL', base['AL'].replace(f'{NEW}.CLIST', f'{FROZEN_RZ}.CLIST')),
           'AL OLD instead of NEW': ('AL', base['AL'].replace('DISP=(NEW,CATLG,CATLG)', 'DISP=OLD', 1))}
    for n in JOBS_2B:
        t = deck(n)
        res[f'deck {JOBS_2B[n]} audit'] = True
        res[f'deck {JOBS_2B[n]} on disk = generated'] = (R / f'jcl/zos/{JOBS_2B[n]}.jcl').read_text() == t
        base[n] = t
    mut.update({
        'PV overwrites PRV.CLIST': ('PV', base['PV'].replace(PRV20, f'{PFX}.PRV.CLIST')),
        'PV reuses an existing target (DISP=OLD)': ('PV', base['PV'].replace('DISP=(NEW,CATLG,CATLG)', 'DISP=OLD')),
        'PV replaces': ('PV', base['PV'].replace('SELECT MEMBER=PACMAN', 'SELECT MEMBER=((PACMAN,,R))')),
        'IP promotes from the frozen RZ': ('IP', base['IP'].replace(f'{NEW}.LOAD', f'{FROZEN_RZ}.LOAD')),
        'IP writes into RZ21': ('IP', base['IP'].replace(f'O        DD DSN={PFX}.LOAD', f'O        DD DSN={NEW}.LOAD')),
        'IP touches PACZ6D': ('IP', base['IP'].replace('((PACMAIN,,R))', '((PACZ6D,,R))')),
        'IP copies every member': ('IP', base['IP'].replace('  SELECT MEMBER=((PACMAIN,,R))\n', '')),
        'IC from RZ.CLIST': ('IC', base['IC'].replace(f'{NEW}.CLIST', f'{FROZEN_RZ}.CLIST')),
        'IC into PRV': ('IC', base['IC'].replace(f'O        DD DSN={PFX}.CLIST', f'O        DD DSN={PRV20}')),
        'ZD REP statement': ('ZD', base['ZD'].replace(' DUMP PACMAIN ALL\n/*\n//ZAPINS',
                                                       ' DUMP PACMAIN ALL\n REP 0000 0000\n/*\n//ZAPINS')),
        'ZD VER statement': ('ZD', base['ZD'].replace(' DUMP PACMAIN ALL\n/*\n//ZAPINS',
                                                       ' VER 0000 0000\n DUMP PACMAIN ALL\n/*\n//ZAPINS')),
        'ZD SYSLIB DISP=OLD': ('ZD', base['ZD'].replace(f'{PFX}.LOAD,DISP=SHR', f'{PFX}.LOAD,DISP=OLD')),
        'ZD dumps the frozen RZ': ('ZD', base['ZD'].replace(f'{NEW}.LOAD', f'{FROZEN_RZ}.LOAD')),
        'P1 runs RZ21': ('P1', base['P1'].replace(f'{PFX}.LOAD', f'{NEW}.LOAD', 1)),
        'P1 PACHS DD': ('P1', base['P1'].replace('//SYSOUT', '//PACHS    DD DUMMY\n//SYSOUT', 1)),
        'P1 HISCORE allocation': ('P1', base['P1'].replace('//SYSOUT', f'//X DD DSN={PFX}.DATA(HISCORE),DISP=SHR'
                                                                          '\n//SYSOUT', 1))})
    for why, (n, t) in mut.items():
        try:
            audit(n, t)
            det[why] = False
        except (AssertionError, KeyError, AttributeError):
            det[why] = True
    # the D46 rule on the frozen PACINPT image itself (synthetic 2.1 images)
    old = (Z10OBJ / 'OBJ.PACINPT.bin').read_bytes() if Z10OBJ.is_dir() else None
    if old is not None:
        res['frozen RZ objects = their recorded SHA-256 (13)'] = frozen_baseline_ok()[0]
        st, _, _ = d46_eq(old, old)
        det['PACINPT unchanged (D46 missing) -> not D46-ONLY'] = st != 'D46-ONLY'
        # a synthetic 2.1 image: the table literal X'00123C' -> X'00124C'
        res['frozen PACINPT: the RT-TSC literal table exactly once'] = old.count(TABLE[0]) == 1
        pos = old.find(TABLE[0]) + 11
        new = bytearray(old)
        new[pos] = 0x4C
        st, dt, f = d46_eq(old, bytes(new))
        res['synthetic 2.1 PACINPT (table 123C -> 124C) -> D46-ONLY, one difference'] = st == 'D46-ONLY' and len(f) == 1
        bad = bytearray(new)
        bad[pos] = 0x5C
        det['table 123C -> 125C -> not D46-ONLY'] = d46_eq(old, bytes(bad))[0] != 'D46-ONLY'
        bad = bytearray(new)
        bad[pos + 3] = 0x5C
        det['table 249C changed as well -> not D46-ONLY'] = d46_eq(old, bytes(bad))[0] != 'D46-ONLY'
        # a second literal 123 -> 124 elsewhere in the loaded text (binary X'007B' -> X'007C', outside D_MCODE)
        hit = None
        for j in (j for j in range(len(old) - 1) if old[j:j + 2] == b'\x00\x7b'):
            bad = bytearray(new)
            bad[j + 1] = 0x7C
            st2, dt2, f2 = d46_eq(old, bytes(bad))
            if st2 == 'DIFFERENT' and any('outside the table' in x for x in f2):
                hit = j
                break
        det['a second 123 -> 124 (binary X\'007B\') outside the table -> DIFFERENT'] = hit is not None
        # other modules: any loaded change outside PACINPT is not allowed (the frozen ZOS-10 rules)
        g = (Z10OBJ / 'OBJ.PACMAIN.bin').read_bytes()
        gb = bytearray(g)
        gb[next(i for i in range(0, len(g), 80) if g[i + 1] == 0x10) + 30] ^= 0x01
        det['a loaded byte changed in PACMAIN -> DIFFERENT'] = Z10.objeq(g, bytes(gb), 'PACMAIN')[0] not in \
            Z10.OBJ_PASS
    res['all injected faults detected'] = all(det.values()) and bool(det)
    return all(res.values()), res, det


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--deck', nargs=2, metavar=('NAME', 'OUT'))
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--check', nargs=2, metavar=('NAME', 'SPOOLDIR'))
    ap.add_argument('--objeq', nargs=2, metavar=('OLD', 'NEW'))
    ap.add_argument('--local-source', action='store_true')
    ap.add_argument('--zos', choices=['preflight', 'upload', 'objects', 'rz-objects', 'load', 'hiscore'])
    ap.add_argument('--state', nargs=2, metavar=('PHASE', 'OUTDIR'), help='pre | pv | ip | ic | final (read only)')
    ap.add_argument('--pre', help='the pre-phase state JSON')
    ap.add_argument('--out')
    ap.add_argument('--report')
    a = ap.parse_args()
    if a.deck:
        Path(a.deck[1]).write_text(deck(a.deck[0]))
        print(f'{a.deck[1]}: {({**JOBS, **JOBS_2B})[a.deck[0]]}')
        return
    if a.selftest:
        ok, res, det = selftest()
        for k, v in res.items():
            print(f'{"PASS" if v else "FAIL"}  {k}')
        for k, v in det.items():
            print(f'  {"detected" if v else "MISSED  "}  {k}')
        print('ZOS-11 RELEASE SELFTEST ' + ('PASS' if ok else 'FAIL'))
        sys.exit(0 if ok else 1)
    if a.state:
        st = zos_state(out=a.state[1])
        Path(a.state[1], 'state.json').write_text(json.dumps(st, indent=1))
        ok, g = gate(a.state[0], st, json.loads(Path(a.pre).read_text()) if a.pre else None)
        res = {'gate': g, 'state': st}
    elif a.local_source:
        ok, res = local_source_ok()
    elif a.objeq:
        ok, res = objeq_dirs(*a.objeq)
    elif a.zos:
        kw = {'out': a.out} if a.out else {}
        if a.zos == 'rz-objects':
            ok, res = zos_objects(lib='RZ', **kw)
            if ok:
                want = dict(reversed(l.split()) for l in Z10OBJ_SHA.read_text().splitlines())
                res['= the ZOS-10 RZ.OBJ read (recorded SHA-256)'] = all(
                    want[f'OBJ.{m}.bin'] == s for m, s in res['sha256'].items())
                ok &= res['= the ZOS-10 RZ.OBJ read (recorded SHA-256)']
        else:
            fn = {'preflight': zos_preflight, 'upload': zos_upload, 'objects': zos_objects, 'load': zos_load,
                  'hiscore': zos_hiscore}[a.zos]
            ok, res = fn(**kw) if a.zos not in ('hiscore',) else fn()
    else:
        ok, res = check(*a.check)
    text = json.dumps(res, indent=1, default=str)
    if a.report:
        Path(a.report).write_text(text + '\n')
    print(text)
    print('RESULT ' + ('PASS' if ok else 'FAIL'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
