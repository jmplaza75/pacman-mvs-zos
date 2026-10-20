#!/usr/bin/env python3
"""ZOS-10 release preparation - local checks (docs/zos10-design.md; nothing submitted):
1. provenance: the only production-source change since zos-9 is Z6 (src/zos/PACMAN.clist, exact z6_strip); the MVS
   CLIST, COBOL, copybooks, assembler, oracles, models and the reused ZOS-2..9 tools = zos-9;
2. tools/zowe/zos10_release.py selftest (decks + audits, CLIST matrix, test copy, object masks, injected faults);
3. the decks of record jcl/zos/PACZ10*.jcl = the generated decks;
4. Z6 PARM matrix: the release evaluator agrees with the frozen section-22 evaluator on the ZOS-6 (Z5) CLIST; REALTIME
   default -> C, explicit EVERY / invalid -> the 2.0 PARM, TURN default = the historical 25-column 2.0 PARM (no C),
   explicit COALESCED kept; the S10 PARM = the accepted ZOS-6 R1 PARM byte for byte;
5. the checkers on simulated spools (PACZ10C1 / C2 / P1 / CL / PV / IN; PACZ10BL on the accepted JOB08888 listing when
   present): positives PASS, faults FAIL;
6. object equivalence on the accepted ZOS-6 images (when present): self PASS, timestamp-only change PASS, any other
   byte FAIL.
Usage: python3 tests/test_zos10.py
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R / 'tools/zowe'), str(R / 'tests'), str(R / 'tools')]
import zos10_release as Z  # noqa: E402
import zos_c2  # noqa: E402


def git(*a):
    return subprocess.run(['git', *a], cwd=R, capture_output=True, text=True, check=True).stdout


# 1. provenance --------------------------------------------------------------------------------------------------------
changed = set(git('diff', '--name-only', '--relative', 'zos-9', '--', 'src').splitlines()) | \
    set(git('ls-files', '--others', '--exclude-standard', '--', 'src').splitlines())
assert changed == {'src/zos/PACMAN.clist'}, changed
assert zos_c2.z6_strip((R / 'src/zos/PACMAN.clist').read_text()) == git('show', 'zos-9:./src/zos/PACMAN.clist')
FROZEN = ['src/cobol', 'src/copy', 'src/asm', 'src/clist', 'src/probe', 'tests/oracle20', 'releases/2.0-MVS-MAX',
          'tools/make_deck.py', 'tools/zowe/zos_target.py', 'tools/zowe/zos_equiv.py',
          'tools/zowe/zos_classic_check.py',
          'tools/zowe/zos_compile_report.py', 'tools/zowe/zos_upload.py', 'tools/zowe/zoslib.py',
          'tools/zowe/zos6_dry.py', 'tools/zowe/zos6_drive.py', 'tools/zowe/zos6_live_check.py',
          'tools/zowe/zos9_equiv.py', 'tools/zowe/zos8_batch.py', 'tests/ref_gx_screen.py', 'tests/ref_gp2.py',
          'tests/ref_rt.py', 'tests/ref_mvs6.py', 'tests/test_gp2.py', 'tests/test_mvs8.py']
for p in FROZEN:
    r = subprocess.run(['git', 'diff', '--quiet', 'zos-9', '--', p], cwd=R)
    assert r.returncode == 0, f'{p} differs from zos-9'
for lib, mems in Z.RELEASE.items():
    d, ext = Z.SRC[lib]
    assert all((R / d / f'{m}{ext}').is_file() for m in mems)
assert sorted(Z.OBJECTS) == sorted(Z.RELEASE['COBOL'] + Z.RELEASE['ASM']) and len(Z.OBJECTS) == 13
assert not set(Z.NEVER) & set(sum(Z.RELEASE.values(), []))
print('provenance: only Z6 changed in src since zos-9 (exact); MVS CLIST, sources, oracles, models, reused tools = '
      'zos-9; release set 10 + 6 + 3 explicit: PASS')

# 2. selftest ----------------------------------------------------------------------------------------------------------
ok, res, det = Z.selftest()
assert ok, [k for k, v in res.items() if not v] + [k for k, v in det.items() if not v]
print(f'zos10_release selftest: {len(res)} checks PASS, {len(det)} injected faults detected: PASS')

# 3. decks of record ---------------------------------------------------------------------------------------------------
for n, job in Z.JOBS.items():
    assert (R / f'jcl/zos/{job}.jcl').read_text() == Z.deck(n), f'{job}: deck of record != generated'
print(f'decks of record ({", ".join(Z.JOBS.values())}) = generated: PASS')

# 4. Z6 PARM matrix ----------------------------------------------------------------------------------------------------
src = (R / 'tests/test_zos_tools.py').read_text()
code = src[src.index('def clist_parm22(text, kw):'):src.index("zcl = zos_c2.z6_strip(")]
ns = {'re': re}
exec(compile(code, str(R / 'tests/test_zos_tools.py'), 'exec'), ns)
z5 = zos_c2.z6_strip((R / 'src/zos/PACMAN.clist').read_text())
for kw in ('', 'RULES(CLASSIC)', 'PLAY(TURN)', 'AI(3) GHOSTS(2) COLOR(NO) LEVEL(7)', 'PRESENT(COALESCED)',
           'PLAY(TURN) PRESENT(COALESCED)', 'METRICS(YES) ALARM(SINGLE) LEVEL(12) SPEED(FAST)', 'PRESENT(EVERY)'):
    assert Z.clist_parm(z5, kw) == ns['clist_parm22'](z5, kw), kw            # the two evaluators agree on Z5
rel = Z.release_clist()
for kw, p in Z.cl_expected():
    assert Z.clist_parm(rel, kw) == p, kw
for kw in ('', 'AI(3) GHOSTS(2)', 'SOUND(NO) SPEED(FAST)', 'COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC)'):
    assert Z.clist_parm(rel, kw) == Z.mvs_parm(kw) + 'C', kw                  # REALTIME (default PLAY) -> C
    assert Z.clist_parm(rel, kw + ' PLAY(TURN)') == Z.mvs_parm(kw + ' PLAY(TURN)'), kw      # TURN: historical
    assert len(Z.clist_parm(rel, kw + ' PLAY(TURN)')) == 25
    assert Z.clist_parm(rel, kw + ' PRESENT(EVERY)') == Z.mvs_parm(kw), kw
    assert Z.clist_parm(rel, kw + ' PLAY(TURN) PRESENT(COALESCED)') == Z.mvs_parm(kw + ' PLAY(TURN)') + 'C', kw
assert Z.clist_parm(rel, Z.S10_KW) == 'TSO AI0 1 NAAAPAAARNC01NPC' == \
    ns['clist_parm22'](z5, 'AI(0) RULES(CLASSIC) PLAY(REALTIME) SOUND(NO) PRESENT(COALESCED)')   # = the R1 PARM
assert Z.s10_plan()['kw'] == 'AI(0) RULES(CLASSIC) SOUND(NO)' and Z.s10_plan()['present'] == 'C'
import zos6_drive  # noqa: E402
assert {k: v for k, v in Z.s10_plan().items() if k != 'kw'} == {k: v for k, v in zos6_drive.PLANS['R1'].items()
                                                                 if k != 'kw'}
print('Z6 matrix: evaluators agree on Z5; REALTIME default -> C, EVERY / invalid -> 2.0 PARM, TURN default historical '
      '(25 columns), explicit COALESCED kept; S10 PARM = the R1 PARM; S10 plan = R1 plan except the operands: PASS')


# 5. checkers on simulated spools --------------------------------------------------------------------------------------
def spool(d, job, steps, outputs=None, pgm=None, lib=None, rc=None, extra=(), sysprint=None, systsprt=None):
    d.mkdir(parents=True)
    (d / 'job.json').write_text(json.dumps({'jobname': job, 'jobid': 'JOB09999', 'retcode': 'CC 0000'}))
    pgm, rc, sysprint = pgm or {}, rc or {}, sysprint or {}
    jcl = [f'        1 //{job} JOB 1,CLASS=7'] + [f'        2 //{s:<8} EXEC PGM={pgm.get(s, "PACMAIN")}' for s in steps]
    msg = []
    for s in steps:
        msg.append(f' IEF142I {job} {s} - STEP WAS EXECUTED - COND CODE {rc.get(s, "0000")}')
        if lib:
            msg.append(f' IGD104I {lib:<44} RETAINED,  DDNAME=STEPLIB')
    files = [{'id': 2, 'ddname': 'JESJCL', 'stepname': 'JES2', 'procstep': None, 'recfm': 'V'},
             {'id': 3, 'ddname': 'JESYSMSG', 'stepname': 'JES2', 'procstep': None, 'recfm': 'VA'}]
    (d / '002-JES2-JESJCL.txt').write_text('\n'.join(jcl) + '\n')
    (d / '003-JES2-JESYSMSG.txt').write_text('\n'.join(msg) + '\n')
    k = 100
    for s, lines in (outputs or {}).items():
        k += 1
        files.append({'id': k, 'ddname': 'SYSOUT', 'stepname': s, 'procstep': None, 'recfm': 'FBA', 'lrecl': 121})
        (d / f'{k:03d}-{s}-SYSOUT.txt').write_text(''.join(' ' + l.ljust(120) + '\n' for l in lines))
    for s, text in sysprint.items():
        k += 1
        files.append({'id': k, 'ddname': 'SYSPRINT', 'stepname': s, 'procstep': None, 'recfm': 'FBA'})
        (d / f'{k:03d}-{s}-SYSPRINT.txt').write_text(text)
    if systsprt is not None:
        k += 1
        files.append({'id': k, 'ddname': 'SYSTSPRT', 'stepname': 'CLT', 'procstep': None, 'recfm': 'FBA'})
        (d / f'{k:03d}-CLT-SYSTSPRT.txt').write_text(systsprt)
    for s, dd in extra:
        k += 1
        files.append({'id': k, 'ddname': dd, 'stepname': s, 'procstep': None, 'recfm': 'FBA'})
        (d / f'{k:03d}-{s}-{dd}.txt').write_text(' x\n')
    (d / 'spool.json').write_text(json.dumps(files))
    return d


import zos6_dry as D6  # noqa: E402
import zos9_equiv as Z9  # noqa: E402
n1 = next(s for s in D6.STEPS if s['step'] == 'N1')
OUT = {s: Z.oracle_block(307, s) for s in set(Z.CV1 + Z.P1)}
OUT.update(RTT2=Z.oracle_block(310, 'RTT2'), N1=D6.render_tsd(D6.model(n1), 'W'), G3T7=Z9.oracle_block(2, 'G3T7'))
LIB = {'C1': 'Z00000.PACMAN.RZ.LOAD', 'C2': 'Z00000.PACMAN.RZ.LOAD', 'P1': 'Z00000.PACMAN.LOAD'}
neg = 0
with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    for n in ('C1', 'C2', 'P1'):
        st = Z.STEPS[n]
        outs = {s: OUT[s] for s in st}
        ok, r = Z.check_runs(spool(t / f'ok{n}', Z.JOBS[n], st, outs, lib=LIB[n]), n)
        assert ok and r['application lines'] == Z.APP_LINES[n], r
        last = st[-1]
        cases = {'one line changed': dict(outputs=dict(outs, **{last: outs[last][:2] + [outs[last][2] + 'X'] +
                                                                 outs[last][3:]}), lib=LIB[n]),
                 'wrong STEPLIB': dict(outputs=outs, lib='Z00000.PACMAN.LOAD' if n != 'P1' else
                                       'Z00000.PACMAN.RZ.LOAD'),
                 'PACZ6D executed': dict(outputs=outs, lib=LIB[n], pgm={st[0]: 'PACZ6D'}),
                 'RC 0004': dict(outputs=outs, lib=LIB[n], rc={st[0]: '0004'}),
                 'CEEDUMP spool': dict(outputs=outs, lib=LIB[n], extra=[(st[0], 'CEEDUMP')])}
        for i, (why, kw) in enumerate(cases.items()):
            assert not Z.check_runs(spool(t / f'n{n}{i}', Z.JOBS[n], st, **kw), n)[0], (n, why)
            neg += 1
        assert not Z.check_runs(spool(t / f'm{n}', Z.JOBS[n], st[:-1], {s: outs[s] for s in st[:-1]}, lib=LIB[n]),
                                n)[0]
        neg += 1
    # P1 must also equal the candidate (CV1) output
    c1 = t / 'okC1'
    assert Z.check_runs(t / 'okP1', 'P1', cv1=c1)[0]
    # CL: the PARM matrix
    good = ''.join(f' Z10PARM=<{p}>\n' for _, p in Z.cl_expected())
    pr = {'CLCPY': 'IEBGENER', 'CLT': 'IKJEFT01'}
    assert Z.check_cl(spool(t / 'cl', 'PACZ10CL', ['CLCPY', 'CLT'], pgm=pr, systsprt=good))[0]
    bad = good.replace('NAAAPAAATAC01NP>', 'NAAAPAAATAC01NPC>', 1)               # TURN default gained a C
    assert not Z.check_cl(spool(t / 'clb', 'PACZ10CL', ['CLCPY', 'CLT'], pgm=pr, systsprt=bad))[0]
    assert not Z.check_cl(spool(t / 'clc', 'PACZ10CL', ['CLCPY', 'CLT'], pgm=pr,
                                systsprt=good + ' PACMAN: Z00000.PACMAN.CEEOPTS MISSING, GAME NOT STARTED\n'))[0]
    assert not Z.check_cl(spool(t / 'cld', 'PACZ10CL', ['CLCPY', 'CLT'], pgm=pr, systsprt=good,
                                rc={'CLT': '0012'}))[0]
    neg += 3
    # PV / IN: IEBCOPY copy results
    ok_pv = ' IGW01551I MEMBER PACMAN   HAS BEEN COPIED\n IGW01550I 1 OF 1 SPECIFIED  MEMBERS WERE COPIED\n' \
        ' IEB147I END OF JOB - 0 WAS HIGHEST SEVERITY CODE\n'
    assert Z.check_copy(spool(t / 'pv', 'PACZ10PV', ['PRV1'], pgm={'PRV1': 'IEBCOPY'}, sysprint={'PRV1': ok_pv}),
                        'PV')[0]
    rp = lambda m: f' IGW01552I MEMBER {m:<8} HAS BEEN COPIED   AND REPLACED\n IGW01550I 1 OF 1 SPECIFIED  ' \
                   'MEMBERS WERE COPIED\n IEB147I END OF JOB - 0 WAS HIGHEST SEVERITY CODE\n'   # noqa: E731
    pin = {'PROM1': 'IEBCOPY', 'PROM2': 'IEBCOPY'}
    assert Z.check_copy(spool(t / 'in', 'PACZ10IN', ['PROM1', 'PROM2'], pgm=pin,
                              sysprint={'PROM1': rp('PACMAIN'), 'PROM2': rp('PACMAN')}), 'IN')[0]
    assert not Z.check_copy(spool(t / 'inp', 'PACZ10IN', ['PROM1', 'PROM2'], pgm=pin, rc={'PROM2': '0004'},
                                  sysprint={'PROM1': rp('PACMAIN'), 'PROM2': rp('PACMAN')}), 'IN')[0]   # partial
    assert not Z.check_copy(spool(t / 'inq', 'PACZ10IN', ['PROM1', 'PROM2'], pgm=pin,
                                  sysprint={'PROM1': rp('PACMAIN'), 'PROM2': ok_pv}), 'IN')[0]           # not replaced
    neg += 2
    # BL on the accepted ZOS-2 build of record (same 13 compiles / assemblies / bind, NAME PACZ2D, job PACZ2BLD)
    acc = R / 'build/zos/PACZ2BLD-JOB08888'
    if acc.is_dir():
        b = t / 'bl'
        shutil.copytree(acc, b)
        ok, r = Z.check_bl(b)
        assert not ok and r['binder']['NAME'] == ['PACZ2D'] and r['binder']['INCLUDE'] == Z.OBJECTS, r
        assert r['binder']['attributes'] == {'AMODE': '24', 'RMODE': '24', 'RENT': 'YES', 'REUS': 'YES'}
        assert r['binder']['EXCEEDS 16MB'] == 'NO' and r['binder']['RC 0']
        assert all(v == [] for k, v in r.items() if k.endswith('messages above I') or k.endswith(' messages'))
        assert r['ASM2 C3 policy (ASMA303W + ASMA435I only, S 12,ABOFF = 5BC0 F014, USING on statement 38)']
        j = json.loads((b / 'job.json').read_text())
        j['jobname'] = 'PACZ10BL'
        (b / 'job.json').write_text(json.dumps(j))
        for f in b.glob('*JESYSMSG*'):
            f.write_text(f.read_text().replace('PACZ2BLD', 'PACZ10BL'))
        for f in b.glob('*-LINK-SYSPRINT.txt'):
            f.write_text(f.read_text().replace('NAME PACZ2D(R)', 'NAME PACMAIN(R)'))
        ok, r = Z.check_bl(b)
        assert ok, r                          # the accepted build passes the gate once named as the release
        for f in b.glob('*-ASM2-SYSPRINT.txt'):
            f.write_text(f.read_text().replace('5BC0 F014', '5BC0 C014'))
        assert not Z.check_bl(b)[0]           # S 12,ABOFF not on base R15: C3 policy fails
        neg += 1
        print('PACZ10BL gate on the accepted JOB08888 listing: 13 RC, C3 policy, binder INCLUDE / attributes / '
              'messages PASS once named PACMAIN; a different ABOFF base FAILS: PASS')
    else:
        print('PACZ10BL listing check: build/zos/PACZ2BLD-JOB08888 not present here (local evidence) - SKIPPED')
print(f'checkers on simulated spools: C1 / C2 / P1 / CL / PV / IN positives PASS, {neg} faults FAIL (incl. a partial '
      'promotion and a TURN PARM with C): PASS')

# 6. object equivalence: the corrected baseline (decision A) and the D_MCODE rule (decision B) -----------------------
def goff_dmcode(img, payload=None, ed=None, extra_ed=False):
    """Re-serialize a COBOL GOFF image with its D_MCODE payload replaced (chunks of 16384, ED class length and TXT
    headers updated as the compiler writes them); ed(bytearray) may alter the ED record."""
    L = Z._logical(img)
    e, chunks, pay, _ = Z._dmcode(L)
    payload = pay if payload is None else payload
    out, tmpl = [], chunks[0][2]
    for i, (t, rs) in enumerate(L):
        if i == chunks[0][0]:
            for off in range(0, len(payload), 16384):
                d = payload[off:off + 16384]
                h = bytearray(tmpl) + len(d).to_bytes(2, 'big')
                h[12:16] = off.to_bytes(4, 'big')
                body, recs = d[56:], [h + d[:56]]
                while body:
                    recs.append(b'\x03\x12\x00' + body[:77])
                    body = body[77:]
                recs = [bytearray(r.ljust(80, b'\x00')) for r in recs]
                for r in recs[:-1]:
                    r[1] |= 1
                out += [bytes(r) for r in recs]
            continue
        if i in {c[0] for c in chunks}:
            continue
        rs = [bytearray(r) for r in rs]
        if rs[0] is not None and t == 0 and bytes(rs[0]) == e:
            rs[0][24:28] = len(payload).to_bytes(4, 'big')
            if ed:
                ed(rs[0])
            out += [bytes(r) for r in rs]
            if extra_ed:
                out.append(bytes(rs[0]))
            continue
        out += [bytes(r) for r in rs]
    return b''.join(out)


def dm_payload(pay, u, level):
    c = zlib.compress(u, level)
    return pay[:12] + (len(u) + 20).to_bytes(4, 'big') + (20 + len(c)).to_bytes(4, 'big') + c


base = Z.BASELINE
if base.is_dir():
    ok, r = Z.baseline_check(base)
    assert ok, r                                   # each baseline image = recorded SHA-256 + its build job's timestamp
    with tempfile.TemporaryDirectory() as t:
        new = Path(t)
        for m in Z.OBJECTS:                        # PASS: timestamp-only changes
            b = bytearray((base / f'OBJ.{m}.bin').read_bytes())
            for o, n in Z.spans(m, bytes(b)):
                b[o:o + n] = (('9' * n) if m in Z.RELEASE['ASM'] else '20' + '9' * (n - 2)).encode('cp037')
            (new / f'OBJ.{m}.bin').write_bytes(bytes(b))
        ok, r = Z.objeq_dirs(base, new)
        assert ok and all(v[0] == 'IDENTICAL-MODULO-TIMESTAMP' for v in r.values()), r
        b = bytearray((new / 'OBJ.PACSCR.bin').read_bytes())
        b[1000] ^= 0x01
        (new / 'OBJ.PACSCR.bin').write_bytes(bytes(b))
        ok, r = Z.objeq_dirs(base, new)
        assert not ok and r['PACSCR'][0] == 'DIFFERENT'
    img = (base / 'OBJ.PACMAP.bin').read_bytes()
    L = Z._logical(img)
    e, ch, pay, u = Z._dmcode(L)
    assert goff_dmcode(img) == img                 # the re-serializer reproduces the compiler's image exactly
    rec = goff_dmcode(img, dm_payload(pay, u, 1))
    assert rec != img and len(Z._dmcode(Z._logical(rec))[2]) != len(pay)
    st = lambda x, m='PACMAP': Z.objeq(img, x, m)[0]        # noqa: E731
    assert st(rec) == 'EQUIVALENT-DMCODE-RECOMPRESSED'      # PASS: other compressed form, same decompressed content
    cc = next(i for i, (t, rs) in enumerate(L) if t == 1 and rs[0][4:8] == Z._eds(L, Z.C_CODE)[0][0][4:8])
    off = sum(len(b''.join(rs)) for _, rs in Z._logical(rec)[:cc]) + 60

    def flip(x, o):
        x = bytearray(x)
        x[o] ^= 0x01
        return bytes(x)
    u2 = bytearray(u)
    u2[100] ^= 0x01
    sp = Z.spans('PACMAP', img)
    neg_obj = {
        'C_CODE (executable) byte changed, D_MCODE recompressed': flip(rec, off),
        'C_CODE byte changed, D_MCODE identical': flip(img, sp[0][0] + 30),
        'one decompressed D_MCODE byte changed': goff_dmcode(img, dm_payload(pay, bytes(u2), 6)),
        'D_MCODE decompressed length changed': goff_dmcode(img, dm_payload(pay, u + b'\x00', 6)),
        'D_MCODE header decompressed length wrong': goff_dmcode(img, dm_payload(pay, u, 1)[:12] +
                                                                (len(u) + 21).to_bytes(4, 'big') +
                                                                dm_payload(pay, u, 1)[16:]),
        'D_MCODE zlib stream truncated': goff_dmcode(img, (lambda p: p[:16] + (len(p) - 5).to_bytes(4, 'big') +
                                                           p[20:-5])(dm_payload(pay, u, 1))),
        'D_MCODE load attribute X\'00\'': goff_dmcode(img, dm_payload(pay, u, 1), ed=lambda r: r.__setitem__(65, 0)),
        'D_MCODE other ED attribute': goff_dmcode(img, dm_payload(pay, u, 1), ed=lambda r: r.__setitem__(60, 1)),
        'D_MCODE missing (renamed)': goff_dmcode(img, dm_payload(pay, u, 1),
                                                 ed=lambda r: r.__setitem__(slice(72, 79), Z._E('D_MCODF'))),
        'extra D_MCODE class': goff_dmcode(img, dm_payload(pay, u, 1), extra_ed=True),
        'structural: one RLD record dropped': b''.join(b''.join(rs) for t, rs in Z._logical(rec) if t != 2),
        'structural: END record changed': (lambda x: x[:-80] + flip(x[-80:], 11))(rec),
    }
    for why, x in neg_obj.items():
        s, d = Z.objeq(img, x, 'PACMAP')
        assert s == 'DIFFERENT', (why, s, d)
        print(f'   {why} -> {d.split("; ")[-1][:100]}')
        neg += 1
    a = (base / 'OBJ.PACTSO.bin').read_bytes()             # HLASM objects stay byte-exact outside the END date
    assert Z.objeq(a, flip(a, 100), 'PACTSO')[0] == 'DIFFERENT'
    print(f'object equivalence on the corrected baseline (13 images = recorded SHA-256 and build-job timestamps): '
          f'timestamp-only IDENTICAL, recompressed D_MCODE EQUIVALENT, {len(neg_obj) + 1} faults DIFFERENT: PASS')
    rz = R / 'build/zos/Z10OBJ'
    if rz.is_dir():                                        # the PACZ10BL JOB04820 PACSCR against JOB09460's
        s, d = Z.objeq((base / 'OBJ.PACSCR.bin').read_bytes(), (rz / 'OBJ.PACSCR.bin').read_bytes(), 'PACSCR')
        assert s in Z.OBJ_PASS, d
        print(f'PACSCR (JOB04820) against the corrected JOB09460 baseline: {s}: PASS')
else:
    print('object equivalence: build/zos/Z10BASE not present here (local evidence) - SKIPPED')
print('ZOS-10 LOCAL CHECKS PASS')
