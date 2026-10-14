#!/usr/bin/env python3
"""Translate a z/OS job spool directory (tools/zowe/zos_submit.py) into the TK4- listing shape the existing tests
parse (ZOS-1; docs/ZOS-MIGRATION-PLAN.md sec. 7, 13). It relabels, never invents: every line comes from the spool.

Usage: zos_listing.py SPOOLDIR [OUT.txt]
Shape: '****A  START  JOB  <n>  <JOBNAME>', the TK4- step table ('hh.mm.ss JOB  <n>  <JOBNAME> <step> [<procstep>]
<pgm> RC= nnnn'; RC from JESYSMSG IEF142I, program from the expanded JESJCL; a step without IEF142I (flushed /
abended) is printed as 'RC= FLSH' or 'AB <code>'), 'IEF376I  JOB /<JOBNAME>/ STOP', then every non-JES spool file in
spool order. ASA files (recfm with A): '1' -> form feed, '0' -> one blank line, '-' -> two, '+' -> line dropped, ' ' ->
the line; first column removed. Lines right-stripped. A summary of the spool attributes goes to stderr.
"""
import json
import re
import sys
from pathlib import Path

JES = ('JESMSGLG', 'JESJCL', 'JESYSMSG')


def steps_of(d, jobname):
    jcl = next(d.glob('*-JESJCL.txt')).read_text()
    msg = next(d.glob('*-JESYSMSG.txt')).read_text()
    order, pgm, proc = [], {}, None
    for line in jcl.splitlines():
        m = re.match(r'\s*\d*\s*(//|XX)(\w+)\s+EXEC\s+(.*)', line)
        if not m:
            continue
        kind, name, ops = m.groups()
        p = re.match(r'PGM=([\w#$@]+)', ops)
        if kind == '//':
            proc = None if p else name
            if p:
                order.append((name, None))
                pgm[(name, None)] = p.group(1)
        elif p and proc:
            order.append((proc, name))
            pgm[(proc, name)] = p.group(1)
    rc = {}
    for m in re.finditer(r'IEF142I\s+' + jobname + r'\s+(\w+)(?:\s+(\w+))?\s+-\s+STEP WAS EXECUTED - COND CODE (\d{4})',
                         msg):
        a, b, c = m.groups()
        rc[(b, a) if b and (b, a) in pgm else (a, b)] = c
    for m in re.finditer(r'IEF472I\s+' + jobname + r'\s+(\w+)(?:\s+(\w+))?\s+-\s+COMPLETION CODE - (\S+)', msg):
        a, b, c = m.groups()
        rc[(b, a) if b and (b, a) in pgm else (a, b)] = 'AB ' + c
    return [(s, ps, pgm[(s, ps)], rc.get((s, ps), 'FLSH')) for s, ps in order]


def asa(lines):
    out = []
    for l in lines:
        cc, text = (l[:1], l[1:]) if l else (' ', '')
        if cc == '+':
            continue
        if cc == '1':
            text = '\f' + text
        elif cc == '0':
            out.append('')
        elif cc == '-':
            out += ['', '']
        out.append(text.rstrip())
    return out


def translate(d):
    d = Path(d)
    job = json.loads((d / 'job.json').read_text())
    files = sorted(json.loads((d / 'spool.json').read_text()), key=lambda f: f['id'])
    n = re.sub(r'\D', '', job['jobid']).lstrip('0')
    out = [f'****A  START  JOB  {n}  {job["jobname"]}  (z/OS {job["jobid"]})',
           f'00.00.00 JOB  {n}  IEFACTRT - Stepname  Procstep  Program   Retcode']
    for s, ps, p, rc in steps_of(d, job['jobname']):
        out.append(f'00.00.00 JOB  {n}  {job["jobname"]:<10} {s:<9} {ps or "":<9} {p:<9} RC= {rc}')
    out.append(f'IEF376I  JOB /{job["jobname"]}/ STOP')
    for f in files:
        if f['ddname'] in JES and f['stepname'] == 'JES2':
            continue
        step = f['stepname'] + (f'.{f["procstep"]}' if f.get('procstep') else '')
        lines = (d / f'{f["id"]:03d}-{step}-{f["ddname"]}.txt').read_text().splitlines()
        lines = asa(lines) if 'A' in (f.get('recfm') or '') else [l.rstrip() for l in lines]
        print(f'  {f["id"]:3d} {step:<16} {f["ddname"]:<9} recfm={f.get("recfm")} lrecl={f.get("lrecl")} '
              f'records={f.get("record-count")}', file=sys.stderr)
        out += lines
    return '\n'.join(out) + '\n'


def main():
    text = translate(sys.argv[1])
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(text)
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
