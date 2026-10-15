#!/usr/bin/env python3
"""ZOS-4 Z2-only checks (tools/zowe/zos_target.py z4z2_deck): attempt T2 (PACZ4Z2, JOB03829) and T3 (PACZ4Z3). Read-only.

Usage: zos_z2_check.py [--attempt T2|T3] --gate      before a submission: none of the attempt's names exists
       zos_z2_check.py [--attempt T2|T3] SPOOLDIR    after it: spool, the TMP output, then the datasets
(default attempt T3). Each case is judged on its own extent of the TMP output: from its `EXEC ...(Z2RUN)` echo to the
next TMP command echo (two leading blanks; the CONTROL LIST lines of the CLIST have none).
Case 1 (project CEEOPTS present, no CEEOPTS DD before): CEEOPTS on the project dataset at the simulated CALL, no
       CEEOPTS DD after the FREE, Z2RC=0.
Case 2 (project dataset absent): the MISSING message (SYSDSN = DATASET NOT FOUND), no CHECK FAILED, no ALLOC of
       CEEOPTS listed, no CALL marker, no CEEOPTS DD, Z2RC=8.
Case 3 (a CEEOPTS DD pre-allocated on <work>(Z2N)), one criterion each: the listed ALLOC of the project CEEOPTS (SYSDSN
       passed, ALLOC reached); its refusal because the file is in use (IKJ ... CEEOPTS ... FILE IN USE); the ERROR
       routine regained control (the ALREADY ALLOCATED message after the refusal); Z2RC=8 after it; no MISSING / CHECK
       FAILED, no CALL marker; the CEEOPTS entry of the TMP LISTALC before and after identical (<work>(Z2N)); SYSIN and
       SYSOUT not allocated after the controlled failure.
IKJ diagnostics only in case 3; the final FREE F(CEEOPTS) clean.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from zos_equiv import zos_runs  # noqa: E402
from zos_target import Z4_ATTEMPTS  # noqa: E402

HLQ = 'Z00000'
STEPS = ['ALLOC', 'Z2CEE', 'Z2CLS1', 'Z2CLS2', 'Z2CLS3', 'CLT']
MSG_EXISTS = 'PACMAN: A CEEOPTS DD IS ALREADY ALLOCATED, GAME NOT STARTED'
TMP_CMD = re.compile(r'^  (EXEC|ALLOC|LISTALC|FREE)\b')


def names(attempt):
    job, sets = Z4_ATTEMPTS[attempt]
    work = f'{HLQ}.PACMAN.{sets["work"]}'
    cy, cn = (f'{HLQ}.PACMAN.{sets[k]}.CEEOPTS' for k in ('cee_present', 'cee_missing'))
    return job, work, cy, cn


def dds(lines):
    """{ddname: dataset line} of a LISTALC STATUS listing (DD line = ddname + disposition after the dataset line;
    NULLFILE lines carry the ddname themselves)."""
    out = {}
    for i, l in enumerate(lines):
        w = l.split()
        if len(w) == 2 and w[0] == 'NULLFILE':
            out[w[1]] = 'NULLFILE'
        elif len(w) == 2 and l.startswith('  ') and i > 0 and w[0].isupper() and w[1].replace(',', '').isalpha():
            out[w[0]] = lines[i - 1].strip()
    return out


def tmp_check(lines, attempt='T3'):
    _, work, cy, cn = names(attempt)
    run = f"EXEC '{work}(Z2RUN)'"
    echo = [i for i, l in enumerate(lines) if TMP_CMD.match(l)]
    e = [i for i in echo if lines[i].strip() in (f"{run} 'Z2Y'", f"{run} 'Z2N'")]
    if [lines[i].strip()[-5:] for i in e] != ["'Z2Y'", "'Z2N'", "'Z2Y'"]:
        return [('the three cases ran in order', False)]
    nxt = lambda i: next((j for j in echo if j > i), len(lines))  # noqa: E731
    c1, c2, c3 = (lines[i:nxt(i)] for i in e)
    rc = [next((l.strip()[5:] for l in c if l.strip().startswith('Z2RC=')), None) for c in (c1, c2, c3)]
    res = [('the three cases ran in order', True)]
    call = next((i for i, l in enumerate(c1) if l.strip() == 'Z2 CALL REACHED'), None)
    end = next((i for i, l in enumerate(c1) if l.strip() == 'Z2 END'), None)
    d1 = [i for i, l in enumerate(c1) if l.split()[:1] == ['CEEOPTS']]
    res.append(('case 1: project CEEOPTS at the simulated CALL, gone after the FREE, Z2RC=0',
                rc[0] == '0' and call is not None and end is not None and len(d1) == 1 and call < d1[0] < end
                and c1[d1[0] - 1].strip() == cy))
    res.append(('case 2: MISSING (DATASET NOT FOUND), no CHECK FAILED, no ALLOC of CEEOPTS, no CALL marker, no '
                'CEEOPTS DD, Z2RC=8',
                rc[1] == '8' and any(l.strip() == f'PACMAN: {cn} MISSING, GAME NOT STARTED' for l in c2)
                and not any(l.strip().startswith('PACMAN: CEEOPTS CHECK FAILED') for l in c2)
                and not any('ALLOC F(CEEOPTS)' in l for l in c2) and not any(l.strip() == 'Z2 CALL REACHED' for l in c2)
                and not any(l.split()[:1] == ['CEEOPTS'] for l in c2)))
    a = next((i for i, l in enumerate(c3) if l.strip() == f"ALLOC F(CEEOPTS) DA('{cy}') SHR"), None)
    ikj = [i for i, l in enumerate(c3) if re.search(r'IKJ\d{5}', l)]
    refused = [i for i in ikj if 'CEEOPTS' in c3[i] and 'FILE IN USE' in c3[i]]
    m = next((i for i, l in enumerate(c3) if l.strip() == MSG_EXISTS), None)
    r3 = next((i for i, l in enumerate(c3) if l.strip().startswith('Z2RC=')), None)
    res.append(('case 3: SYSDSN passed, the ALLOC of the project CEEOPTS reached (listed)', a is not None))
    res.append(('case 3: the ALLOC refused because CEEOPTS is in use (IKJ ... FILE IN USE), no other IKJ',
                a is not None and len(refused) == 1 and refused[0] > a and ikj == refused))
    res.append(('case 3: the ERROR routine regained control (ALREADY ALLOCATED message after the refusal)',
                bool(refused) and m is not None and m > refused[0]))
    res.append(('case 3: Z2RC=8 after the message', rc[2] == '8' and m is not None and r3 is not None and r3 > m))
    res.append(('case 3: no MISSING / CHECK FAILED path, no CALL marker',
                not any(l.strip().startswith(('PACMAN: CEEOPTS CHECK FAILED', f'PACMAN: {cy} MISSING')) for l in c3)
                and not any(l.strip() == 'Z2 CALL REACHED' for l in c3)))
    la = [i for i in echo if lines[i].strip() == 'LISTALC STATUS']
    pre = [i for i in la if e[1] < i < e[2]]
    post = [i for i in la if i > e[2]]
    before = dds(lines[pre[-1]:nxt(pre[-1])]) if pre else {}
    after = dds(lines[post[0]:nxt(post[0])]) if post else {}
    res.append((f'case 3: the original CEEOPTS DD identical before and after ({before.get("CEEOPTS")})',
                before.get('CEEOPTS') == f'{work}(Z2N)' and after.get('CEEOPTS') == before.get('CEEOPTS')))
    res.append(('case 3: SYSIN and SYSOUT not allocated after the controlled failure',
                bool(post) and 'SYSIN' not in after and 'SYSOUT' not in after))
    out3 = [i for i, l in enumerate(lines) if re.search(r'IKJ\d{5}', l) and not (e[2] <= i < nxt(e[2]))]
    res.append(('IKJ diagnostics only in case 3', not out3))
    fr = [i for i in echo if lines[i].strip() == 'FREE F(CEEOPTS)']
    res.append(('final FREE F(CEEOPTS) clean', bool(fr) and fr[-1] > e[2]
                and not any(re.search(r'IKJ\d{5}', l) for l in lines[fr[-1]:])))
    return res


def spool_check(d, attempt):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = json.loads((d / 'spool.json').read_text())
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    jcl = next(d.glob('*-JESJCL.txt')).read_text()
    jes = ''.join(p.read_text() for p in d.glob('00*-JES2-*.txt'))
    jobname, work, cy, _ = names(attempt)
    _, steps, _ = zos_runs(d)
    res = [(f'job {jobname}, steps {" ".join(STEPS)}', job['jobname'] == jobname and steps == STEPS)]
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
    res.append((f'datasets in JESYSMSG only {work}, {cy}', named <= {work, cy}))
    f = next(f for f in files if (f['stepname'], f['ddname']) == ('CLT', 'SYSTSPRT'))
    raw = (d / f'{f["id"]:03d}-CLT-SYSTSPRT.txt').read_text().splitlines()
    res += tmp_check([l[1:].rstrip() for l in raw], attempt)
    return job, res


def catalog(after, attempt):
    from zoslib import zowe
    _, work, cy, cn = names(attempt)

    def exists(ds):
        items = zowe('zos-files', 'list', 'data-set', ds, '-a', json_out=True)['data']['apiResponse']['items']
        return [i for i in items if i['dsname'] == ds]
    if not after:
        return [(f'{ds} does not exist', not exists(ds)) for ds in (work, cy, cn)]
    mem = sorted(m['member'] for m in zowe('zos-files', 'list', 'all-members', work, json_out=True)['data']
                 ['apiResponse']['items'])
    a = (exists(cy) or [{}])[0]
    rec = [l.rstrip() for l in zowe('zos-files', 'view', 'data-set', cy).stdout.splitlines() if l.strip()]
    return [(f'{work} members exactly Z2N Z2RUN Z2Y', mem == ['Z2N', 'Z2RUN', 'Z2Y']),
            (f'{cy}: PS FB 80 80, one record ALL31(OFF),STACK(,,BELOW)',
             a.get('dsorg') == 'PS' and a.get('recfm') == 'FB' and a.get('lrecl') == '80' and a.get('blksz') == '80'
             and rec == ['ALL31(OFF),STACK(,,BELOW)']),
            (f'{cn} still does not exist', not exists(cn))]


def main():
    a = sys.argv[1:]
    attempt = 'T3'
    if '--attempt' in a:
        i = a.index('--attempt')
        attempt = a[i + 1]
        del a[i:i + 2]
    if a == ['--gate']:
        res, title = catalog(False, attempt), f'{names(attempt)[0]} GATE'
    else:
        job, res = spool_check(a[0], attempt)
        print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}')
        res += catalog(True, attempt)
        title = f'{names(attempt)[0]} CHECK'
    for k, v in res:
        print(f'  {"OK  " if v else "FAIL"} {k}')
    bad = sum(not v for _, v in res)
    print(f'{title} ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
