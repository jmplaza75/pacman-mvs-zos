#!/usr/bin/env python3
"""Submit a deck, wait for its job to finish and save the listing.

Usage: run_deck.py DECK.jcl [--timeout 600]
Prints the path of build/<JOBNAME>-<JOBNO>.txt. Uses tools/submit.sh (credentials from .env, never printed) and the
JES printer file ~/mainframe/tk4/prt/prt00e.txt. Only a job number newer than any seen before submission is accepted.
"""
import argparse
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRT = Path.home() / 'mainframe/tk4/prt/prt00e.txt'


def printer():
    return PRT.read_bytes().decode('ascii', 'replace').replace('\r', '')


def job_numbers(text, name):
    return [int(n) for n in re.findall(r'^\*{4}A  START  JOB\s+(\d+)\s+' + name + r'\b', text, re.M)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('deck', type=Path)
    ap.add_argument('--timeout', type=int, default=600)
    a = ap.parse_args()
    name = re.match(r'//(\S+)\s+JOB', a.deck.read_text(encoding='ascii')).group(1)
    before = max(job_numbers(printer(), name), default=0)
    subprocess.run([str(ROOT / 'tools/submit.sh'), str(a.deck)], check=True, stdout=subprocess.DEVNULL)
    deadline = time.time() + a.timeout
    while time.time() < deadline:
        time.sleep(10)
        text = printer()
        new = [n for n in job_numbers(text, name) if n > before]
        if not new:
            continue
        job = str(max(new))
        ends = list(re.finditer(r'^\*{4}A   END   JOB\s+' + job + r'\b[^\n]*', text, re.M))
        if not ends:
            continue
        time.sleep(3)                       # let the printer finish the closing banner
        text = printer()
        ends = list(re.finditer(r'^\*{4}A   END   JOB\s+' + job + r'\b[^\n]*', text, re.M))
        start = re.search(r'^\*{4}A  START  JOB\s+' + job + r'\b', text, re.M).start()
        out = re.sub(r'PASSWORD=[^\s,]*', 'PASSWORD=<REDACTED>', text[start:ends[-1].end()] + '\n')
        dest = ROOT / 'build' / f'{name}-{job}.txt'
        dest.write_text(out, encoding='ascii', errors='replace')
        print(dest)
        return
    raise SystemExit(f'{name}: no completed job within {a.timeout}s')


if __name__ == '__main__':
    main()
