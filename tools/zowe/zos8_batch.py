#!/usr/bin/env python3
"""ZOS-8 Stage B (docs/zos8-design.md, U2 / U4 / U10): the batch decks PACZ8HB (B1) and PACZ8RPE (B2), their
fail-closed checkers, the test CLIST renderers (U3) and their guards, and the read-only state queries.

Usage: zos8_batch.py --deck B1|B2 OUT.jcl            write a deck (prefix @@HLQ@@.PACMAN) + its estimated SYSOUT lines
       zos8_batch.py --check B1|B2 SPOOLDIR          check a fetched spool (exit 0 PASS, 1 FAIL)
       zos8_batch.py --clists OUTDIR [--hlq H]       render PACZ8HT / PACZ8HU / PACZ8HF / RPESTAE for upload
       zos8_batch.py --state HS8|HSFULL|DATA [--hlq H] read-only z/OSMF query (attributes, extents, members, record)
       zos8_batch.py --selftest                      decks, models, guards and injected spool faults (local)
B1 PACZ8HB: ALLOC (IEFBR14) Z00000.PACMAN.HS8.T1 with exactly the DD parameters that created DATA in PACZALLO
  (DSNTYPE=PDS,RECFM=FB,LRECL=80,BLKSIZE=80,SPACE=(TRK,(1,1,5)), DISP=(NEW,CATLG,CATLG)); H1-H4 PGM=PACZ6D BAT ARCADE
  LEVEL 1 with DD PACHS = HS8.T1(HISCORE) SHR (the CLIST disposition): create (REPL), tie, update (WRIT), lower;
  PRINT (IEBGENER of the member to SYSOUT); HSLIST (TSO LISTDS ... MEMBERS, COND=EVEN). Never DATA.
B2 PACZ8RPE: COB (IGYCRCTL PACRPE, uploaded unchanged from src/probe/PACRPE.cob), LINK (IEWBLINK OBJ(PACRPE) +
  the existing OBJ(PACFSIO) / OBJ(PACHSIO), AMODE 24 RMODE 24 RENT -> LOAD(PACRPE), test only, never PACMAIN), E1
  (PARM E1) and E2 (PARM E2, PACHS = HS8.T1(HISCORE) SHR, read only): not a TSO session, nothing sent, the forced
  0C7 must end both steps abnormally (trigger proven under LE; the code and the LE text are recorded, not gated).
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests'), str(R / 'tools')]
import zos8_scen as S  # noqa: E402

PFX = S.PFX
LOAD = 'PACZ6D'
B1_JOB, B2_JOB = 'PACZ8HB', 'PACZ8RPE'
B1_DS = f'{PFX}.{S.STORES["T1"]}'
DATA_DD = ('DSNTYPE=PDS,RECFM=FB,LRECL=80,BLKSIZE=80,', 'SPACE=(TRK,(1,1,5))')   # = jcl/zos/PACZALLO.jcl DATA DD
B1_STEPS = ['ALLOC'] + [s for s, _, _ in S.B1_STEPS] + ['PRINT', 'HSLIST']
B2_STEPS = ['COB', 'LINK', 'E1', 'E2']
RPE_LINES = {'E1': ['RPE CASE E1 START', 'RPE FSON RC= 0004', 'PACHSIO READ RC=0000 (E2 ONLY, ELSE 0)',
                    'RPE NOT A TSO SESSION: NOTHING SENT'],
             'E2': ['RPE CASE E2 START', 'RPE FSON RC= 0004', 'PACHSIO READ RC=0000 (E2 ONLY, ELSE 0)',
                    'RPE NOT A TSO SESSION: NOTHING SENT']}


def _zt():
    import make_deck as md
    import zos_target as zt
    if not zt._md:
        zt.apply(md, PFX)
    zt.JOBNAME = None
    return zt


def b1_deck(pfx=PFX):
    zt = _zt()
    ds = f'{pfx}.{S.STORES["T1"]}'
    mem = f'DSN={ds}(HISCORE),DISP=SHR'
    out = zt.job_card(B1_JOB, 'PACMAN ZOS8 B1')
    out += ('//ALLOC    EXEC PGM=IEFBR14\n'
            f'//HS8      DD DSN={ds},DISP=(NEW,CATLG,CATLG),\n'
            f'//            {DATA_DD[0]}\n//            {DATA_DD[1]}\n')
    for step, d, c in S.B1_STEPS:
        out += zt.run_step(step, pfx, LOAD, '\n'.join(S.cards_of(d, c)) + '\n', parm=S.B1_PARM, dd=mem)
    out += ('//PRINT    EXEC PGM=IEBGENER,COND=(0,NE)\n//SYSPRINT DD DUMMY\n//SYSIN    DD DUMMY\n'
            f'//SYSUT1   DD {mem}\n//SYSUT2   DD SYSOUT=A\n')
    out += ('//HSLIST   EXEC PGM=IKJEFT01,COND=EVEN\n//SYSTSPRT DD SYSOUT=A\n//SYSTSIN  DD *\n'
            f"  LISTDS '{ds}' MEMBERS\n/*\n")
    return out


def b2_deck(pfx=PFX):
    zt = _zt()
    zt.OBJ.update({'OBJR': 'PACRPE', 'OBJF': 'PACFSIO', 'OBJH': 'PACHSIO'})
    out = zt.job_card(B2_JOB, 'PACMAN ZOS8 B2')
    out += zt.compile_step('COB', pfx, 'PACRPE', 'OBJR')
    out += zt.link_step(pfx, ['OBJR', 'OBJF', 'OBJH'], 'PACRPE', 'PACRPE')
    build = '((0,NE,COB),(0,NE,LINK))'
    out += zt.run_step('E1', pfx, 'PACRPE', None, parm='E1', cond=build)
    out += zt.run_step('E2', pfx, 'PACRPE', None, parm='E2', dd=f'DSN={pfx}.{S.STORES["T1"]}(HISCORE),DISP=SHR',
                       cond='((0,NE,COB),(0,NE,LINK),EVEN)')
    return out


def audit(text, kind):
    """Deck rules beyond zoslib.audit_deck: no production DATA, no PACMAIN, no DELETE / SCRATCH, the right programs."""
    from zoslib import audit_deck
    bad = audit_deck(text, '@@HLQ@@')
    if re.search(r'PACMAN\.DATA\b', text):
        bad.append('the production DATA is referenced')
    if 'PGM=PACMAIN' in text or 'NAME PACMAIN' in text or '(PACMAIN)' in text:
        bad.append('PACMAIN referenced')
    if re.search(r'DELETE|SCRATCH|UNCATLG|RENAME', text):
        bad.append('DELETE / SCRATCH / UNCATLG / RENAME')
    pgms = re.findall(r'EXEC PGM=(\w+)', text)
    want = {'B1': ['IEFBR14', LOAD, LOAD, LOAD, LOAD, 'IEBGENER', 'IKJEFT01'],
            'B2': ['IGYCRCTL', 'IEWBLINK', 'PACRPE', 'PACRPE']}[kind]
    if pgms != want:
        bad.append(f'programs {pgms} != {want}')
    if kind == 'B1':
        if text.count('NEW,CATLG,CATLG') != 1 or f'{B1_DS},DISP=(NEW' not in text:
            bad.append('B1 must create exactly HS8.T1')
        if DATA_DD[0] not in text or DATA_DD[1] not in text:
            bad.append('HS8.T1 geometry != DATA')
    if kind == 'B2':
        if 'NAME PACRPE(R)' not in text or 'DISP=(NEW' in text:
            bad.append('B2 must only add LOAD(PACRPE) / OBJ(PACRPE)')
    for l in text.splitlines():
        if len(l) > 71 and l.startswith('//') and not l.startswith('//*'):
            bad.append(f'JCL statement past column 71: {l}')
    return bad


def estimate(kind):
    if kind == 'B1':
        return sum(len(lines) for _, lines, _ in S.b1_model()) + 1 + 12 + 160
    return 120 + 140 + 2 * 60 + 120          # compile (NOSOURCE) + binder LIST + two LE tracebacks + JES


# ---- test CLISTs (U3) and the z/OS RPESTAE test CLIST (U4) ---------------------------------------------------------
def installed_clist(prefix):
    import zos_target as zt
    return zt.zos_clist_text(prefix)


def test_clist(member, prefix):
    """The installed CLIST(PACMAN) text with only its two DATA references pointed at the test store of member."""
    base = installed_clist(prefix)
    ds = f'{prefix}.{S.STORES[S.TEST_CLISTS[member]]}'
    a, b = f"&SYSDSN('{prefix}.DATA')", f"DA('{prefix}.DATA(HISCORE)')"
    assert base.count(a) == 1 and base.count(b) == 1
    return base.replace(a, f"&SYSDSN('{ds}')").replace(b, f"DA('{ds}(HISCORE)')")


def clist_diff(member, prefix):
    old, new = installed_clist(prefix).splitlines(), test_clist(member, prefix).splitlines()
    return [(i, o, n) for i, (o, n) in enumerate(zip(old, new)) if o != n], len(old) == len(new)


RPESTAE = R / 'src/probe/zos/RPESTAE.clist'
Z2_CORE = ["SET &D = &SYSDSN('@@PREFIX@@.CEEOPTS')", 'SET &Z = 0', 'CONTROL NOFLUSH', 'ERROR DO', '  SET &Z = &LASTCC',
           '  RETURN', 'END', "ALLOC F(CEEOPTS) DA('@@PREFIX@@.CEEOPTS') SHR", 'ERROR OFF', 'CONTROL FLUSH']


def rpestae_guard():
    """The z/OS RPESTAE: the MVS probe CLIST's statements + the Z2 core statements of src/zos/PACMAN.clist verbatim and
    in order + FREE F(CEEOPTS) after the CALL; E2 reads the test member HS8.T1(HISCORE); no DATA; columns <= 72."""
    z = RPESTAE.read_text(encoding='ascii').splitlines()
    prod = (R / 'src/zos/PACMAN.clist').read_text(encoding='ascii').splitlines()
    mvs = (R / 'src/probe/RPESTAE.clist').read_text(encoding='ascii').splitlines()
    res = {}
    def subseq(seq, lines):
        it = iter(lines)
        return all(any(x == want for x in it) for want in seq)
    res['Z2 core statements = src/zos/PACMAN.clist, same order'] = subseq(Z2_CORE, prod) and subseq(Z2_CORE, z)
    stmts = [l for l in mvs if not l.startswith('/*')]
    keep = [l.replace("'@@PREFIX@@.DATA'", "'@@PREFIX@@.HS8.T1'").replace('DATA(HISCORE)', 'HS8.T1(HISCORE)')
            for l in stmts]
    res['MVS RPESTAE statements kept (E2 -> HS8.T1)'] = all(l in z for l in keep)
    res['CALL then FREE F(CEEOPTS)'] = z.index('FREE F(CEEOPTS)') > next(i for i, l in enumerate(z) if
                                                                          l.startswith('CALL '))
    res['no production DATA'] = not any(re.search(r'\.DATA\b', l) for l in z)
    res['columns <= 72'] = all(len(l) <= 72 for l in z)
    return res


def rendered_clists(prefix):
    out = {m: test_clist(m, prefix) for m in S.TEST_CLISTS}
    out['RPESTAE'] = RPESTAE.read_text(encoding='ascii').replace('@@PREFIX@@', prefix)
    return out


# ---- checks ------------------------------------------------------------------------------------------------------
def _spool(d):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = sorted(json.loads((d / 'spool.json').read_text()), key=lambda f: f['id'])
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    jes = ''.join(p.read_text() for p in sorted(d.glob('00*-JES2-*.txt')))

    def text(step, dd):
        f = next((f for f in files if f['stepname'] == step and f['ddname'] == dd), None)
        if f is None:
            return None
        from zos_listing import asa
        raw = (d / f'{f["id"]:03d}-{step}-{dd}.txt').read_text().splitlines()
        return asa(raw) if 'A' in (f.get('recfm') or '') else [l.rstrip() for l in raw]
    return job, files, msg, jes, text


def _named(msg, job, hlq):
    own = f'{hlq}.{job["jobname"]}.{job["jobid"]}.'
    return {x.rstrip('.') for x in re.findall(rf'\b({hlq}\.[\w.$#@]+)', msg) if not x.startswith(own)}


def check_b1(d, hlq='Z00000'):
    from zos_equiv import zos_runs
    job, files, msg, jes, text = _spool(d)
    _, names, runs = zos_runs(d)
    ds = f'{hlq}.PACMAN.{S.STORES["T1"]}'
    res = [(f'steps {" ".join(B1_STEPS)}', names == B1_STEPS)]
    for s in B1_STEPS:
        res.append((f'{s} COND CODE 0000', bool(re.search(rf'IEF142I {job["jobname"]} {s} - STEP WAS EXECUTED - '
                                                         r'COND CODE 0000', msg))))
    res.append(('no ABEND / IEA995 / $HASP375 / S722 / CEE / IEC message',
                not re.search(r'ABEND|IEA995|\$HASP375|S722|CEE\d{4}|IEC\d{3}I', jes)))
    m = re.search(r'IGD101I SMS ALLOCATED TO DDNAME \(HS8\s*\)\s+DSN \(([\w.]+)\s*\)\s+STORCLAS \((\w*)\s*\) '
                  r'MGMTCLAS \((\w*)\s*\) DATACLAS \((\w*)\s*\)\s+VOL SER NOS= (\w+)', msg)
    res.append((f'ALLOC created {ds} (IGD101I)', bool(m) and m.group(1) == ds))
    res.append(('no IGD01007I size reduction for HS8.T1 (same request as DATA)', 'IGD01007I' not in msg))
    res.append(('datasets named: the load library and HS8.T1 only (never DATA)',
                _named(msg, job, hlq) <= {f'{hlq}.PACMAN.LOAD', ds}))
    model = S.b1_model()
    for step, want, member in model:
        got = runs.get(step, {}).get('lines')
        res.append((f'{step} SYSOUT = model ({len(want)} lines; {" / ".join(want[-2:])})', got == want))
    pr = text('PRINT', 'SYSUT2') or []
    want_rec = model[-1][2][0].rstrip()
    res.append((f'PRINT: HS8.T1(HISCORE) = one record {want_rec!r}', [l for l in pr if l.strip()] == [want_rec]))
    tp = text('HSLIST', 'SYSTSPRT') or []
    ls = '\n'.join(tp)
    k = next((i for i, l in enumerate(tp) if l.strip() == '--MEMBERS--'), None)
    mems = []
    for l in tp[k + 1:] if k is not None else []:
        if l.strip() in ('READY', 'END') or l.strip().startswith('LISTDS'):
            break
        mems.append(l.strip())
    res.append(('HSLIST: FB 80 80 PO, members exactly HISCORE',
                bool(re.search(r'FB\s+80\s+80\s+PO', ls)) and mems == ['HISCORE'] and not re.search(r'IKJ\d{5}', ls)))
    info = {'classes': m.groups()[1:] if m else None}
    return job, res, info


def check_b2(d, hlq='Z00000'):
    job, files, msg, jes, text = _spool(d)
    from zos_listing import steps_of
    st = steps_of(Path(d), job['jobname'])
    names = [s for s, _, _, _ in st]
    rc = {s: r for s, _, _, r in st}
    res = [(f'steps {" ".join(B2_STEPS)}', names == B2_STEPS),
           ('COB COND CODE 0000', rc.get('COB') == '0000'), ('LINK COND CODE 0000', rc.get('LINK') == '0000')]
    ab = {}
    for s in ('E1', 'E2'):
        ab[s] = rc.get(s, '')
        res.append((f'{s} ended abnormally (forced 0C7 under LE): {ab[s]}', ab[s].startswith('AB ')))
        out = text(s, 'SYSOUT') or []
        res.append((f'{s} SYSOUT starts with the PACRPE batch lines', out[:4] == RPE_LINES[s]))
        res.append((f'{s} never reached "RPE ERROR: NO ABEND"', 'RPE ERROR: NO ABEND' not in out))
    lst = '\n'.join(text('LINK', 'SYSPRINT') or [])
    res.append(('binder: AMODE 24 / RMODE 24, member PACRPE, no severity >= 8 message',
                bool(re.search(r'AMODE\s+24', lst)) and bool(re.search(r'RMODE\s+24', lst)) and 'PACRPE' in lst
                and not re.search(r'IEW\d{4}[ES]', lst)))
    allowed = {f'{hlq}.PACMAN.{x}' for x in ('COBOL', 'COPY', 'OBJ', 'LOAD', S.STORES['T1'])}
    res.append(('datasets named: COBOL / COPY / OBJ / LOAD / HS8.T1 only (never DATA)',
                _named(msg, job, hlq) <= allowed))
    res.append(('no IEC message, no S722 / $HASP375', not re.search(r'IEC\d{3}I|S722|\$HASP375', jes)))
    le = {s: [l for l in (text(s, 'SYSOUT') or [])[4:] if l.strip()][:12] for s in ('E1', 'E2')}
    return job, res, {'abend': ab, 'le_text': le}


# ---- read-only state queries (z/OS; run only when approved) --------------------------------------------------------
def state(which, h):
    from zoslib import zowe
    ds = {'HS8': f'{h}.PACMAN.{S.STORES["T1"]}', 'HSFULL': f'{h}.PACMAN.{S.STORES["FULL"]}',
          'DATA': f'{h}.PACMAN.DATA'}[which]
    items = zowe('zos-files', 'list', 'data-set', ds, '-a', json_out=True)['data']['apiResponse']['items']
    a = items[0] if len(items) == 1 and items[0]['dsname'] == ds else {}
    keys = ('dsntp', 'dsorg', 'recfm', 'lrecl', 'blksz', 'extx', 'sizex', 'spacu', 'used', 'vol', 'migr')
    mem = sorted(m['member'] for m in
                 zowe('zos-files', 'list', 'all-members', ds, json_out=True)['data']['apiResponse']['items'])
    rec = None
    if 'HISCORE' in mem:
        rec = [l.rstrip() for l in zowe('zos-files', 'view', 'data-set', f'{ds}(HISCORE)').stdout.splitlines()
               if l.strip()]
    return {'dsname': ds, 'attrs': {k: a.get(k) for k in keys}, 'members': mem, 'HISCORE': rec}


# ---- self-test ---------------------------------------------------------------------------------------------------
def selftest():
    res = {}
    for k, f in (('B1', b1_deck), ('B2', b2_deck)):
        bad = audit(f(), k)
        res[f'{k} deck audit clean {bad}'] = not bad
    res['B1 deck on disk = generated'] = (R / 'jcl/zos/PACZ8HB.jcl').read_text() == b1_deck()
    res['B2 deck on disk = generated'] = (R / 'jcl/zos/PACZ8RPE.jcl').read_text() == b2_deck()
    m = S.b1_model()
    res['B1 chain: create, tie, update, lower -> 0000720 PACHS001 001'] = \
        [x[1][-1] for x in m] == ['NEW HIGH SCORE', 'HIGH SCORE 0000370 LEVEL 001', 'NEW HIGH SCORE',
                                  'HIGH SCORE 0000720 LEVEL 001'] and m[-1][2] == [S.B1_VALUE]
    for mem in S.TEST_CLISTS:
        diff, same_len = clist_diff(mem, 'Z00000.PACMAN')
        t = test_clist(mem, 'Z00000.PACMAN')
        res[f'{mem}: = installed CLIST except its two DATA lines'] = same_len and len(diff) == 2 and \
            all('Z00000.PACMAN.DATA' in o and 'Z00000.PACMAN.DATA' not in n for _, o, n in diff)
        res[f'{mem}: columns <= 72, no production DATA'] = all(len(l) <= 72 for l in t.splitlines()) and \
            'PACMAN.DATA' not in t
    for k, v in rpestae_guard().items():
        res[f'RPESTAE z/OS: {k}'] = v
    est = {k: estimate(k) for k in ('B1', 'B2')}
    res[f'estimated SYSOUT lines {est} < 4000'] = all(v < 4000 for v in est.values())
    return all(res.values()), res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--deck', nargs=2, metavar=('KIND', 'OUT'))
    ap.add_argument('--check', nargs=2, metavar=('KIND', 'SPOOLDIR'))
    ap.add_argument('--clists')
    ap.add_argument('--state')
    ap.add_argument('--hlq', default='Z00000')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.deck:
        text = {'B1': b1_deck, 'B2': b2_deck}[a.deck[0]]()
        Path(a.deck[1]).write_text(text)
        print(f'{a.deck[1]}: audit {audit(text, a.deck[0]) or "clean"}; estimated SYSOUT lines {estimate(a.deck[0])}')
    elif a.check:
        job, res, info = (check_b1 if a.check[0] == 'B1' else check_b2)(a.check[1], a.hlq)
        print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}')
        for k, v in res:
            print(f'  {"OK  " if v else "FAIL"} {k}')
        print(f'  recorded: {json.dumps(info)}')
        bad = sum(not v for _, v in res)
        print(f'{a.check[0]} CHECK ' + ('PASS' if not bad else f'FAIL ({bad})'))
        sys.exit(1 if bad else 0)
    elif a.clists:
        out = Path(a.clists)
        out.mkdir(parents=True, exist_ok=True)
        import hashlib
        for m, t in rendered_clists(f'{a.hlq}.PACMAN').items():
            (out / f'{m}.clist').write_text(t, encoding='ascii')
            print(f'{out / m}.clist: {len(t.splitlines())} records, sha256 {hashlib.sha256(t.encode()).hexdigest()}')
    elif a.state:
        print(json.dumps(state(a.state, a.hlq), indent=1))
    else:
        ok, res = selftest()
        for k, v in res.items():
            print(f'{"PASS" if v else "FAIL"}  {k}')
        print('ZOS-8 BATCH SELFTEST ' + ('PASS' if ok else 'FAIL'))
        sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
