#!/usr/bin/env python3
"""ZOS-4 PACZ4LE check: the LE runtime-option diagnostic (tools/zowe/zos_target.py Z4LE_STEPS). Read-only.

Usage: zos_le_check.py SPOOLDIR      (exit 0 only if every step behaves as designed; the values are recorded)
Per step, from its SYSOUT (ZHELLOC DISPLAY lines + the LE options report, MSGFILE = SYSOUT):
- the invocation format: `ZH PARMLEN=005` and `ZH PARM=ZHARG` (the part before '/' is the program argument: CBLOPTS
  arguments/options), the report present (RPTOPTS(ON) taken from after the '/'), CBLOPTS reported ON;
- ZHELLOA's readings: TAM / BSM, PARM1 / CSECT / SAVEA BELOW or ABOVE 16 MB;
- the report lines of ALL31, STACK, RPTOPTS with their LAST-WHERE-SET source (the text before the option):
  D1 (ZHELLO31, no CEEOPTS): evidence of the effective no-override LE defaults (not a direct observation of the
     interactive TSO CALL): ALL31 / STACK from the installation defaults (recorded), RPTOPTS from the invocation; the
     save area must be BELOW only if the reported stack is BELOW (ANYWHERE allows either: information only);
  D2 (ZHELLO24, CEEOPTS ALL31(OFF),STACK(,,BELOW)): ALL31 OFF and STACK BELOW from CEEOPTS, TAM = BSM = 0, PARM1 /
     CSECT / SAVEA BELOW;
  D3 (ZHELLO31, CEEOPTS ALL31(ON),STACK(,,BELOW), invocation STACK(,,ANYWHERE)): decided by the report only: STACK
     ANYWHERE from the invocation (it outranks CEEOPTS), ALL31 ON from CEEOPTS; SAVEA recorded for information.
Spool health: COND CODE 0000 per step, only SYSOUT per step, STEPLIB retained once per step, no CEEnnnn message,
no ABEND / IEA995 / $HASP375.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from zos_equiv import zos_runs  # noqa: E402
from zos_target import Z4LE_STEPS  # noqa: E402

OPT = re.compile(r'^\s*(\S.*?)\s{2,}(ALL31|STACK|CBLOPTS|RPTOPTS)\(([^)]*)\)\s*$')


def readings(lines):
    zh = {m.group(1).strip(): m.group(2).strip() for m in (re.match(r'ZH (\w+)\s*=(.*)$', l) for l in lines) if m}
    rep = {m.group(2): (m.group(1).strip(), m.group(3)) for m in (OPT.match(l) for l in lines) if m}
    return zh, rep


def src(rep, opt, word):
    return opt in rep and word in rep[opt][0].upper()


DEFAULT_ORIGINS = ('IBM-SUPPLIED DEFAULT', 'INSTALLATION DEFAULT')   # no runtime override (JOB03693: IBM-supplied)


def default_origin(rep, opt):
    """The option comes from the defaults: exactly 'IBM-supplied default' (what this system reports, JOB03693) or an
    installation default; DD:CEEOPTS, Invocation command or any other origin is not a default."""
    return opt in rep and rep[opt][0].upper() in DEFAULT_ORIGINS


def step_check(step, lines):
    zh, rep = readings(lines)
    res = [(f'{step}: program argument = ZHARG (PARMLEN 005): arguments/options format',
            zh.get('PARMLEN') == '005' and zh.get('PARM', '').rstrip() == 'ZHARG'),
           (f'{step}: options report present, CBLOPTS ON, RPTOPTS(ON) from the invocation',
            rep.get('CBLOPTS', ('', ''))[1] == 'ON' and rep.get('RPTOPTS', ('', ''))[1] == 'ON'
            and src(rep, 'RPTOPTS', 'INVOCATION'))]
    stack = rep.get('STACK', ('', ''))[1].split(',')
    where = stack[2] if len(stack) > 2 else ''
    sav = zh.get('SAVEA', '').split()[-1:] or ['']
    if step == 'D1':
        res.append(('D1: ALL31 / STACK from the defaults, no runtime override (recorded: ALL31(%s) <- %s, STACK(%s) <- %s)'
                    % (rep.get('ALL31', ('?', '?'))[1], rep.get('ALL31', ('?', '?'))[0],
                       rep.get('STACK', ('?', '?'))[1], rep.get('STACK', ('?', '?'))[0]),
                    default_origin(rep, 'ALL31') and default_origin(rep, 'STACK')
                    and zh.get('TAM') == '0000000001' and zh.get('BSM') == '0000000001'
                    and (where != 'BELOW' or sav[0] == 'BELOW')))      # ANYWHERE allows either: information only
    elif step == 'D2':
        res.append(('D2: ALL31(OFF) and STACK(...,BELOW,...) from CEEOPTS',
                    rep.get('ALL31', ('', ''))[1] == 'OFF' and src(rep, 'ALL31', 'CEEOPTS')
                    and where == 'BELOW' and src(rep, 'STACK', 'CEEOPTS')))
        res.append(('D2: AMODE 24 (TAM = BSM = 0), PARM1 / CSECT / SAVEA BELOW 16 MB',
                    zh.get('TAM') == '0000000000' and zh.get('BSM') == '0000000000'
                    and all(zh.get(k, '').endswith('BELOW') for k in ('PARM1', 'CSECT', 'SAVEA'))))
    else:
        res.append(('D3: STACK ANYWHERE from the invocation (outranks CEEOPTS BELOW), ALL31(ON) from CEEOPTS',
                    where in ('ANY', 'ANYWHERE') and src(rep, 'STACK', 'INVOCATION')
                    and rep.get('ALL31', ('', ''))[1] == 'ON' and src(rep, 'ALL31', 'CEEOPTS')))
        res.append(('D3: AMODE 31 (TAM = BSM = 1); SAVEA %s recorded for information only (ANYWHERE allows either)'
                    % (sav[0] or '?'), zh.get('TAM') == '0000000001' and zh.get('BSM') == '0000000001'))
    return res


def main():
    d = Path(sys.argv[1])
    job = json.loads((d / 'job.json').read_text())
    files = json.loads((d / 'spool.json').read_text())
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    jes = ''.join(p.read_text() for p in d.glob('00*-JES2-*.txt'))
    _, steps, runs = zos_runs(d)
    want = [s for s, *_ in Z4LE_STEPS]
    res = [(f'steps {" ".join(want)}', steps == want)]
    for s in want:
        res.append((f'{s} COND CODE 0000',
                    bool(re.search(rf'IEF142I {job["jobname"]} {s} - STEP WAS EXECUTED - COND CODE 0000', msg))))
    res.append(('only SYSOUT per step', {(f['stepname'], f['ddname']) for f in files if f['stepname'] != 'JES2'}
                == {(s, 'SYSOUT') for s in want}))
    res.append(('STEPLIB Z00000.PACMAN.LOAD retained once per step',
                len(re.findall(r'IGD104I Z00000\.PACMAN\.LOAD\s+RETAINED,\s+DDNAME=STEPLIB', msg)) == len(want)))
    allout = [l for s in want for l in runs[s]['lines']]
    res.append(('no CEEnnnn message, no ABEND / IEA995 / $HASP375',
                not re.search(r'\bCEE\d{4}[IWESC]\b', jes + '\n'.join(allout)) and
                not re.search(r'ABEND|IEA995|\$HASP375', jes)))
    for s in want:
        res += step_check(s, runs[s]['lines'])
        zh, rep = readings(runs[s]['lines'])
        print(f'  {s}: ' + ', '.join(f'{k}={v}' for k, v in zh.items() if k in ('PARMLEN', 'PARM', 'TAM', 'BSM',
                                                                                 'PARM1', 'CSECT', 'SAVEA')))
        for o in ('ALL31', 'STACK', 'CBLOPTS', 'RPTOPTS'):
            print(f'      {o}({rep[o][1]}) <- {rep[o][0]}' if o in rep else f'      {o}: not in the report')
    print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}')
    for k, v in res:
        print(f'  {"OK  " if v else "FAIL"} {k}')
    bad = sum(not v for _, v in res)
    print('PACZ4LE CHECK ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
