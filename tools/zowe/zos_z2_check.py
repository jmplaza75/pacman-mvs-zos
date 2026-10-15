#!/usr/bin/env python3
"""ZOS-4 PACZ4Z2 check (attempt T2, tools/zowe/zos_target.py z4z2_deck): the three Z2 paths only. Read-only.

Usage: zos_z2_check.py --gate        before the submission: none of the three T2 names exists
       zos_z2_check.py SPOOLDIR      after it: spool, the TMP output, then the datasets
Case 1 (project CEEOPTS present, no CEEOPTS DD before): CEEOPTS allocated to the project dataset at the simulated CALL,
       no CEEOPTS DD after the FREE, Z2RC=0.
Case 2 (project dataset absent): `PACMAN: <p>.CEEOPTS MISSING, GAME NOT STARTED` (SYSDSN = DATASET NOT FOUND), not the
       CHECK FAILED message, no ALLOC F(CEEOPTS) listed, no CALL marker, no CEEOPTS DD, Z2RC=8.
Case 3 (a CEEOPTS DD pre-allocated on <work>(Z2N)): the CONTROL LIST line of `ALLOC F(CEEOPTS) DA('<p>.CEEOPTS') SHR`
       (proof the SYSDSN check passed and the ALLOC was reached), then its refusal (IKJ diagnostics naming CEEOPTS),
       then `PACMAN: A CEEOPTS DD IS ALREADY ALLOCATED, GAME NOT STARTED`; neither MISSING nor CHECK FAILED; no CALL
       marker; Z2RC=8; the CEEOPTS entry of LISTALC after the case identical to the one before it (<work>(Z2N)).
IKJ diagnostics only inside case 3 and naming CEEOPTS; the final FREE F(CEEOPTS) clean.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from zos_equiv import zos_runs  # noqa: E402
from zos_target import Z4Z2_SETS  # noqa: E402

HLQ = 'Z00000'
WORK = f'{HLQ}.PACMAN.{Z4Z2_SETS["work"]}'
CY = f'{HLQ}.PACMAN.{Z4Z2_SETS["cee_present"]}.CEEOPTS'
CN = f'{HLQ}.PACMAN.{Z4Z2_SETS["cee_missing"]}.CEEOPTS'
STEPS = ['ALLOC', 'Z2CEE', 'Z2CLS1', 'Z2CLS2', 'Z2CLS3', 'CLT']
MSG_MISSING = f'PACMAN: {CN} MISSING, GAME NOT STARTED'
MSG_EXISTS = 'PACMAN: A CEEOPTS DD IS ALREADY ALLOCATED, GAME NOT STARTED'
ALLOC_Y = f"ALLOC F(CEEOPTS) DA('{CY}') SHR"


def is_msg(l, text):
    return l.strip() == text


def cee_entry(lines):
    """(dataset line, DD line) of the CEEOPTS entry in a LISTALC listing, or None."""
    k = [i for i, l in enumerate(lines) if l.split()[:1] == ['CEEOPTS']]
    return (lines[k[0] - 1].strip(), ' '.join(lines[k[0]].split())) if len(k) == 1 and k[0] > 0 else None


def tmp_check(lines):
    run = f"EXEC '{WORK}(Z2RUN)'"
    e = [i for i, l in enumerate(lines) if l.strip() in (f"{run} 'Z2Y'", f"{run} 'Z2N'")]
    rc = [(i, l.strip()[5:]) for i, l in enumerate(lines) if l.strip().startswith('Z2RC=')]
    la = [i for i, l in enumerate(lines) if l.strip() == 'LISTALC STATUS']        # TMP-level LISTALC echoes
    fr = [i for i, l in enumerate(lines) if l.strip() == 'FREE F(CEEOPTS)']
    order = ([lines[i].strip()[-5:] for i in e] == ["'Z2Y'", "'Z2N'", "'Z2Y'"] and len(rc) == 3 and
             all(e[k] < rc[k][0] < (e[k + 1] if k < 2 else len(lines)) for k in range(3)))
    res = [('the three cases ran in order, each with its Z2RC line', order)]
    if not order:
        return res
    pre = [i for i in la if rc[1][0] < i < e[2]]
    post = [i for i in la if i > rc[2][0]]
    c1, c2, c3 = (lines[e[k]:rc[k][0] + 1] for k in range(3))
    call = next((i for i, l in enumerate(c1) if l.strip() == 'Z2 CALL REACHED'), None)
    end = next((i for i, l in enumerate(c1) if l.strip() == 'Z2 END'), None)
    dd1 = [i for i, l in enumerate(c1) if l.split()[:1] == ['CEEOPTS']]
    res.append(('case 1: project CEEOPTS allocated at the simulated CALL, gone after the FREE, Z2RC=0',
                rc[0][1] == '0' and call is not None and end is not None and len(dd1) == 1
                and call < dd1[0] < end and c1[dd1[0] - 1].strip() == CY))
    res.append(('case 2: MISSING message (DATASET NOT FOUND), no CHECK FAILED, no ALLOC of CEEOPTS, no CALL marker, '
                'no CEEOPTS DD, Z2RC=8',
                rc[1][1] == '8' and any(is_msg(l, MSG_MISSING) for l in c2)
                and not any(l.strip().startswith('PACMAN: CEEOPTS CHECK FAILED') for l in c2)
                and not any('ALLOC F(CEEOPTS)' in l for l in c2) and not any(l.strip() == 'Z2 CALL REACHED' for l in c2)
                and not any(l.split()[:1] == ['CEEOPTS'] for l in c2)))
    a = next((i for i, l in enumerate(c3) if ALLOC_Y in l), None)
    ikj = [i for i, l in enumerate(c3) if re.search(r'IKJ\d{5}', l)]
    m = next((i for i, l in enumerate(c3) if is_msg(l, MSG_EXISTS)), None)
    res.append(('case 3: SYSDSN passed and the ALLOC was reached (CONTROL LIST line), refused (IKJ naming CEEOPTS), '
                'then the ALREADY ALLOCATED message; no MISSING / CHECK FAILED, no CALL marker, Z2RC=8',
                rc[2][1] == '8' and a is not None and m is not None and bool(ikj) and a < min(ikj) and max(ikj) < m
                and all('CEEOPTS' in c3[i] for i in ikj)
                and not any(l.strip().startswith(('PACMAN: CEEOPTS CHECK FAILED', f'PACMAN: {CY} MISSING'))
                            for l in c3)
                and not any(l.strip() == 'Z2 CALL REACHED' for l in c3)))
    before = cee_entry(lines[pre[0]:e[2]]) if len(pre) == 1 else None
    after = cee_entry(lines[post[0]:fr[-1]]) if len(post) == 1 and fr and fr[-1] > post[0] else None
    res.append((f'case 3: the pre-existing CEEOPTS DD identical before and after ({before})',
                before is not None and before == after and before[0] == f'{WORK}(Z2N)'))
    out3 = [i for i, l in enumerate(lines) if re.search(r'IKJ\d{5}', l) and not (e[2] <= i <= rc[2][0])]
    res.append(('IKJ diagnostics only in case 3, none elsewhere', not out3))
    res.append(('final FREE F(CEEOPTS) clean', bool(fr) and fr[-1] > rc[2][0]
                and not any(re.search(r'IKJ\d{5}', l) for l in lines[fr[-1]:])))
    return res


def spool_check(d):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = json.loads((d / 'spool.json').read_text())
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    jcl = next(d.glob('*-JESJCL.txt')).read_text()
    jes = ''.join(p.read_text() for p in d.glob('00*-JES2-*.txt'))
    _, steps, _ = zos_runs(d)
    res = [(f'steps {" ".join(STEPS)}', steps == STEPS)]
    for s in STEPS:
        res.append((f'{s} COND CODE 0000',
                    bool(re.search(rf'IEF142I {job["jobname"]} {s} - STEP WAS EXECUTED - COND CODE 0000', msg))))
    res.append(('CLT ran with DYNAMNBR=200', 'DYNAMNBR=200' in jcl))
    res.append(('no ABEND / IEA995 / $HASP375 / S722 / CEE message',
                not re.search(r'ABEND|IEA995|\$HASP375|S722|CEE\d{4}', jes)))
    dd = {(f['stepname'], f['ddname']) for f in files if f['stepname'] != 'JES2'}
    res.append(('spool DDs: SYSPRINT of the IEBGENER steps, SYSTSPRT of CLT',
                dd == {(s, 'SYSPRINT') for s in STEPS[1:-1]} | {('CLT', 'SYSTSPRT')}))
    own = f'{HLQ}.{job["jobname"]}.{job["jobid"]}.'
    named = {x.rstrip('.') for x in re.findall(rf'\b({HLQ}\.[\w.$#@]+)', msg) if not x.startswith(own)}
    res.append((f'datasets in JESYSMSG only {WORK}, {CY}', named <= {WORK, CY}))
    f = next(f for f in files if (f['stepname'], f['ddname']) == ('CLT', 'SYSTSPRT'))
    raw = (d / f'{f["id"]:03d}-CLT-SYSTSPRT.txt').read_text().splitlines()
    res += tmp_check([l[1:].rstrip() for l in raw])
    return job, res


def catalog(after):
    from zoslib import zowe

    def exists(ds):
        items = zowe('zos-files', 'list', 'data-set', ds, '-a', json_out=True)['data']['apiResponse']['items']
        return [i for i in items if i['dsname'] == ds]
    if not after:
        return [(f'{ds} does not exist', not exists(ds)) for ds in (WORK, CY, CN)]
    res = []
    mem = sorted(m['member'] for m in zowe('zos-files', 'list', 'all-members', WORK, json_out=True)['data']
                 ['apiResponse']['items'])
    res.append((f'{WORK} members exactly Z2N Z2RUN Z2Y', mem == ['Z2N', 'Z2RUN', 'Z2Y']))
    a = (exists(CY) or [{}])[0]
    rec = [l.rstrip() for l in zowe('zos-files', 'view', 'data-set', CY).stdout.splitlines() if l.strip()]
    res.append((f'{CY}: PS FB 80 80, one record ALL31(OFF),STACK(,,BELOW)',
                a.get('dsorg') == 'PS' and a.get('recfm') == 'FB' and a.get('lrecl') == '80'
                and a.get('blksz') == '80' and rec == ['ALL31(OFF),STACK(,,BELOW)']))
    res.append((f'{CN} still does not exist', not exists(CN)))
    return res


def main():
    a = sys.argv[1:]
    if a == ['--gate']:
        res, title = catalog(False), 'PACZ4Z2 GATE'
    else:
        job, res = spool_check(a[0])
        print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}')
        res += catalog(True)
        title = 'PACZ4Z2 CHECK'
    for k, v in res:
        print(f'  {"OK  " if v else "FAIL"} {k}')
    bad = sum(not v for _, v in res)
    print(f'{title} ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
