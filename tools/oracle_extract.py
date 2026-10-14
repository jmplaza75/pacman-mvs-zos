#!/usr/bin/env python3
"""ZOS-0: freeze the 2.0-MVS-MAX functional oracle independently of the TK4- listings (docs/ZOS-MIGRATION-PLAN.md
sec. 2 and 13, level L3).

  oracle_extract.py extract --build DIR --out tests/oracle20     write one <JOB>-<JOBNAME>.json.gz per job of record
  oracle_extract.py render FILE.json.gz OUT.txt                    rebuild a TK4--shaped listing (step RC table +
                                                                   SYSOUT datasets) that the existing tests parse
  oracle_extract.py verify --out tests/oracle20                    SHA-256 index check

Per job the oracle keeps: the step table (step, program, RC, from the IEFACTRT lines; checked against the deck of
record in releases/2.0-MVS-MAX/decks) and the program-output stream: every printed SYSOUT line after the system
messages, in print order, right-stripped (D11), split exactly as the tests split a listing (str.splitlines, so a form
feed is a line break). The TK4- printer does not start every SYSOUT dataset on a new page and compiler listings carry
their own page ejects, so datasets are not attributed to steps; on z/OS the per-step spool files are concatenated in
step order and compared with this stream. The compiler / assembler / linkage-editor listings of the build steps stay
in the stream (they interleave with run output, e.g. the PACQRYT driver of the RP deck); the z/OS comparison skips them
by step program. Not kept: JES log, JCL, system messages (everything up to IEF376I), the end banners and the JES2 end
separator page.
No live trace and no credential is read: the decks of record carry no password, and a PASSWORD= in a listing stops the
extraction.
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DECKS = R / 'releases/2.0-MVS-MAX/decks'
# job number -> (listing file, deck of record); releases/2.0-MVS-MAX/MANIFEST.md
JOBS = {
    307: ('PACREL20-307.txt', 'R20-REL20.jcl'),
    308: ('PACBLDS2-308.txt', 'R20-S2.jcl'),
    309: ('PACBLDRP-309.txt', 'R20-RP.jcl'),
    310: ('PACBLGP2-310.txt', 'R20-GP2.jcl'),
    311: ('PACBLG23-311.txt', 'R20-GP23.jcl'),
    312: ('PACBLDHS-312.txt', 'R20-HS.jcl'),
    315: ('PACREL10-315.txt', 'INST-ORACLE.jcl'),
    316: ('PACBLDS2-316.txt', 'INST-S2.jcl'),
}


def deck_steps(text):
    """[(step, pgm)] of a deck; in-stream data skipped (DD * / DD DATA,DLM=xx)."""
    steps, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        l = lines[i]
        m = re.match(r'//(\w+)\s+EXEC\s+PGM=(\w+)', l)
        if m:
            steps.append((m.group(1), m.group(2)))
        m = re.match(r'//(\w+)\s+DD\s+(.*)', l)
        if m:
            d = re.search(r'DLM=(\S\S)', m.group(2))
            if d:
                i += 1
                while not lines[i].startswith(d.group(1)):
                    i += 1
            elif re.match(r'(\*|DATA)\b', m.group(2)):
                i += 1
                while i < len(lines) and not lines[i].startswith(('//', '/*')):
                    i += 1
                continue
        i += 1
    return steps


def extract(listing, deck_name):
    text = listing.read_bytes().decode('ascii', 'replace').replace('\r', '')
    if re.search(r'PASSWORD=(?!<REDACTED>)\S', text):
        raise SystemExit(f'{listing}: unredacted PASSWORD= found, refusing')
    job = re.search(r'^\*{4}A  START  JOB\s+(\d+)\s+(\w+)', text, re.M)
    jobno, jobname = int(job.group(1)), job.group(2)
    table = re.findall(r'^\S+ JOB\s+\d+\s+' + jobname + r'\s+(\w+)\s+(\w+)\s+RC= (\d{4})\s*$', text, re.M)
    assert deck_steps((DECKS / deck_name).read_text()) == [(s, p) for s, p, _ in table], (listing, 'steps != deck')
    ls = text.splitlines()
    start = max(i for i, l in enumerate(ls) if l.startswith('IEF376I')) + 1
    stream = [l.rstrip() for l in ls[start:] if not l.startswith('****A   END   JOB')]
    # the JES2 end separator pages: block letters of the job name and of 'J<jobno>' plus the class letter, nothing
    # else (the page break may fall inside a line, so no empty line marks it); cut only a whole page (>= 10 lines)
    sep = set(jobname + 'J' + str(jobno) + 'A ')
    k = len(stream)
    while k and set(stream[k - 1]) <= sep:
        k -= 1
    assert len(stream) - k >= 10, (listing.name, 'no end separator page found', len(stream) - k)
    del stream[k:]
    return {'format': 'pacman-oracle20/1', 'job': jobno, 'jobname': jobname, 'deck': deck_name,
            'listing': listing.name, 'steps': [[s, p, rc] for s, p, rc in table], 'stream': stream}


def write_gz(obj, path):
    raw = json.dumps(obj, indent=0, ensure_ascii=True).encode('ascii')
    with open(path, 'wb') as f, gzip.GzipFile(fileobj=f, mode='wb', mtime=0, filename='') as g:
        g.write(raw)


def render(obj):
    out = [f'****A  START  JOB  {obj["job"]}  {obj["jobname"]}  (oracle20 reconstruction)',
           f'00.00.00 JOB  {obj["job"]}  IEFACTRT - Stepname  Procstep  Program   Retcode']
    out += [f'00.00.00 JOB  {obj["job"]}  {obj["jobname"]:<10} {s:<19} {p:<9} RC= {rc}' for s, p, rc in obj['steps']]
    out.append(f'IEF376I  JOB /{obj["jobname"]}/ STOP')
    return '\n'.join(out + obj['stream']) + '\n'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('extract')
    e.add_argument('--build', type=Path, required=True)
    e.add_argument('--out', type=Path, default=R / 'tests/oracle20')
    r = sub.add_parser('render')
    r.add_argument('file', type=Path)
    r.add_argument('output', type=Path)
    v = sub.add_parser('verify')
    v.add_argument('--out', type=Path, default=R / 'tests/oracle20')
    a = ap.parse_args()
    if a.cmd == 'extract':
        a.out.mkdir(parents=True, exist_ok=True)
        index = []
        for job, (lst, deck) in sorted(JOBS.items()):
            obj = extract(a.build / lst, deck)
            assert obj['job'] == job
            p = a.out / f'{job}-{obj["jobname"]}.json.gz'
            write_gz(obj, p)
            index.append(f'{sha(p)}  {p.name}')
            print(f'{p.name}: {len(obj["steps"])} steps, {len(obj["stream"])} lines, {p.stat().st_size} bytes')
        (a.out / 'SHA256SUMS').write_text('\n'.join(index) + '\n')
    elif a.cmd == 'render':
        obj = json.loads(gzip.decompress(a.file.read_bytes()))
        a.output.write_text(render(obj), encoding='ascii')
    else:
        bad = 0
        for line in (a.out / 'SHA256SUMS').read_text().splitlines():
            h, name = line.split('  ')
            ok = sha(a.out / name) == h
            bad += not ok
            print(name, 'OK' if ok else 'FAIL')
        sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
