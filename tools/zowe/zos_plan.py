#!/usr/bin/env python3
"""ZOS-2 job / step / result matrix (Z2-2..Z2-4) for review before any submission.

Usage: zos_plan.py [CHUNK ...] [--budget 4000]
For every job of tools/zowe/zos_target.py CHUNKS: the steps, program, expected RC, the expected output of each run
(lines of its block in the oracle job, located by the TK4- two-line separators) and an estimate of the job's spool
lines (program output + JES lines per step, measured on JOB08331 / JOB08497). Fails if an estimate exceeds --budget
(default 4,000: comfortably below the ~5,000-line site limit). Estimates only; the jobs are judged on the exact
expectations (RC per step, tools/zowe/zos_equiv.py --subset against the oracle job).
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zos_target as Z  # noqa: E402

R = Z.R
ORACLE = {307: '307-PACREL20', 308: '308-PACBLDS2', 309: '309-PACBLDRP', 310: '310-PACBLGP2'}
# spool lines per step besides program output (JESYSMSG + JESJCL, JOB08331 / JOB08497) and fixed per job
JES = {'IGYCRCTL': 95, 'ASMA90': 30, 'IEWBLINK': 25, 'run': 25}
JOB_FIXED = 60
# build listings (estimates): COBOL NOSOURCE listing = JOB08497 SYSPRINT size; HLASM NOGEN ~ statements + 150;
# binder LIST,MAP ~ 40 + 25 per included object
COBOL_LIST = {'PACMAIN': 130, 'PACGAME': 139, 'PACMAP': 120, 'PACAI': 129, 'PACINPT': 112, 'PACDISP': 143,
              'PACPLAT': 120, 'PACSCR': 138, 'PACQRY': 97, 'PACRT': 139, 'PACQRYT': 97, 'PACTSOT': 97}


def blocks(job):
    """{run step: output lines} of an oracle job: run blocks follow an exact two-line separator, in step order
    (PACMAIN runs start with 'PACMAN' or 'TSX', the drivers with 'QRY ' / 'TSOT ')."""
    o = json.load(gzip.open(R / f'tests/oracle20/{ORACLE[job]}.json.gz'))
    s = o['stream']
    starts = [p + 2 for p in range(len(s) - 2) if s[p] == '' and s[p + 1] == '' and s[p + 2] != ''
              and (p == 0 or s[p - 1] != '')]
    ends = starts[1:] + [len(s) + 2]
    size = {p: e - 2 - p for p, e in zip(starts, ends)}
    deck = Z.steps_of_deck((R / 'releases/2.0-MVS-MAX/decks' / o['deck']).read_text())
    kind = {st: ('TSD' if "PARM='TSD" in deck[st].split('\n', 2)[0] + deck[st].split('\n', 2)[1] else 'TXT')
            for st, p, _ in o['steps'] if p == 'PACMAIN'}
    out = {}
    for group, heads in ((('PACMAIN', 'TXT'), ('PACMAN',)), (('PACMAIN', 'TSD'), ('TSX',)),
                         (('PACQRYT', None), ('QRY ',)), (('PACTSOT', None), ('TSOT ',))):
        names = [st for st, p, _ in o['steps'] if p == group[0] and kind.get(st) == group[1]]
        hits = [p for p in starts if s[p].startswith(heads)]
        if group == ('PACMAIN', 'TXT'):       # the text runs (BAT / TSO): one block each, exactly
            assert len(hits) == len(names), (job, group, len(hits), len(names))
        out.update({n: size[p] for n, p in zip(names, hits)} if len(hits) == len(names) else {})
    return out, {st: p for st, p, _ in o['steps']}


def plan(names, budget):
    import make_deck as md  # noqa: E402
    Z.apply(md, Z.PREFIX)
    bad = 0
    cache = {}
    for name in names:
        job, base, steps, extra, ojob = Z.CHUNKS[name]
        full = Z.steps_of_deck(md.build(base, Z.PREFIX, Z.LOAD))
        if ojob and ojob not in cache:
            cache[ojob] = blocks(ojob)
        sizes, oprog = cache.get(ojob, ({}, {}))
        total = JOB_FIXED
        rows = []
        for s in steps:
            head = full[s].split('\n', 1)[0]
            pgm = head.split('PGM=')[1].split(',')[0].strip()
            if pgm == 'IGYCRCTL':
                member = full[s].split('.COBOL(')[1].split(')')[0]
                lines, rc, how = COBOL_LIST[member], '0000', f'compile {member}'
            elif pgm == 'ASMA90':
                member = full[s].split('.ASM(')[1].split(')')[0]
                n = sum(1 for l in (R / f'src/asm/{member}.asm').read_text().splitlines() if l[:1] != '*')
                lines, rc = n + 150, '0004 (C3: only ASMA303W)' if member == 'PACFSIO' else '0000'
                how = f'assemble {member}'
            elif pgm == 'IEWBLINK':
                inc = full[s].count('INCLUDE OBJ(')
                lines, rc = 40 + 25 * inc, '0000'
                how = 'bind ' + full[s].split('NAME ')[1].split('(')[0] + f' ({inc} objects, AMODE 24 RMODE 24)'
            else:
                assert oprog.get(s) in ('PACMAIN', 'PACQRYT', 'PACTSOT'), (name, s)
                lines, rc = sizes[s], '0000'
                how = 'RT3 timing rules' if oprog[s] == 'PACTSOT' else f'= oracle JOB {ojob} {s}'
            total += lines + JES.get(pgm, JES['run'])
            parm = head.split("PARM='")[1].rstrip("'") if "PARM='" in head else ''
            rows.append((s, pgm, rc, lines, how, parm))
        ok = total <= budget
        bad += not ok
        print(f'{job} ({name}) base {base}{" + " + extra if extra else ""}, oracle {ojob or "-"}: '
              f'{len(steps)} steps, ~{total} spool lines {"OK" if ok else "OVER BUDGET"}')
        for s, pgm, rc, lines, how, parm in rows:
            print(f'   {s:<6} {pgm:<9} RC {rc:<26} {lines:>5}  {how}' + (f"  PARM '{parm}'" if parm else ''))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chunks', nargs='*')
    ap.add_argument('--budget', type=int, default=4000)
    a = ap.parse_args()
    sys.path.insert(0, str(R / 'tools'))
    bad = plan(a.chunks or list(Z.CHUNKS), a.budget)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
