#!/usr/bin/env python3
"""Print the newest complete job with the given jobname from the JES printer file."""
import re, sys
from pathlib import Path
PRT = Path.home() / 'mainframe/tk4/prt/prt00e.txt'
name = sys.argv[1]
text = PRT.read_bytes().decode('ascii', 'replace').replace('\r', '')
jobs = re.findall(r'^\*{4}A  START  JOB\s+(\d+)\s+' + name + r'\b', text, re.M)
if not jobs:
    sys.exit('job not found')
job = jobs[-1]
s = re.search(r'^\*{4}A  START  JOB\s+' + job + r'\b', text, re.M).start()
ends = list(re.finditer(r'^\*{4}A   END   JOB\s+' + job + r'\b[^\n]*', text, re.M))
if not ends:
    sys.exit('job ' + job + ' not finished yet')
print(re.sub(r'PASSWORD=[^\s,]*', 'PASSWORD=<REDACTED>', text[s:ends[-1].end()]))
