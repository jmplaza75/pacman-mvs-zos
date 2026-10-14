#!/usr/bin/env python3
"""Compile inventory of a z/OS job (ZOS-2 Z2-1): per step the RC and every IGY (Enterprise COBOL) / ASMA (HLASM)
diagnostic of level I, W, E, S or U found in that step's SYSPRINT, with its source line when the listing gives one.

Usage: zos_compile_report.py SPOOLDIR
Read-only on the saved spool (tools/zowe/zos_submit.py). Messages are quoted as printed (one per line, continuation
lines of a message appended); nothing is filtered except duplicates of the same message on the same line.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zos_listing import steps_of  # noqa: E402

IGY = re.compile(r'^\s*(\d+)?\s*(IGY[A-Z]{2}\d{4})-([IWESU])\s+(.*)$')
ASMA = re.compile(r'^\s*\*\* (ASMA\d{3})([IWESNCU])\s+(.*)$')
STATS = re.compile(r'(\d+) (Informational|Warning|Error|Severe|Terminating)?|Messages\s+Total')


def report(d):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = json.loads((d / 'spool.json').read_text())
    rows = []
    for s, ps, pgm, rc in steps_of(d, job['jobname']):
        f = next((f for f in files if f['stepname'] == s and (f.get('procstep') or None) == ps
                  and f['ddname'] == 'SYSPRINT'), None)
        msgs = []
        if f:
            step = f['stepname'] + (f'.{f["procstep"]}' if f.get('procstep') else '')
            lines = (d / f'{f["id"]:03d}-{step}-{f["ddname"]}.txt').read_text().splitlines()
            seen = set()
            for i, l in enumerate(lines):
                m = IGY.match(l[1:] if l[:1] in ' 01-+' else l)
                if m:
                    line, code, sev, text = m.groups()
                    j = i + 1
                    while j < len(lines) and lines[j][:1] in ' 0' and re.match(r'^\s{10,}\S', lines[j]) \
                            and not IGY.match(lines[j][1:]):
                        text += ' ' + lines[j].strip()
                        j += 1
                    key = (line, code, text)
                    if key not in seen:
                        seen.add(key)
                        msgs.append((sev, code, line or '', text.strip()))
                    continue
                m = ASMA.match(l[1:] if l[:1] in ' 01-+' else l)
                if m:
                    code, sev, text = m.groups()
                    msgs.append(({'N': 'W', 'C': 'S'}.get(sev, sev), code, '', text.strip()))
        rows.append((s, ps, pgm, rc, msgs))
    return job, rows


def main():
    job, rows = report(sys.argv[1])
    print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")}')
    for s, ps, pgm, rc, msgs in rows:
        sev = {k: sum(m[0] == k for m in msgs) for k in 'IWESU'}
        print(f'{s:<8} {ps or "":<4} {pgm:<9} RC={rc}  ' + ' '.join(f'{k}={v}' for k, v in sev.items() if v))
        for m in msgs:
            print(f'    {m[1]}-{m[0]} line {m[2] or "-":>5}: {m[3]}')


if __name__ == '__main__':
    main()
