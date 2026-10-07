#!/usr/bin/env python3
"""Extract one JES printer job and redact any printed password."""
import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('printer', type=Path)
parser.add_argument('job', type=int)
parser.add_argument('output', type=Path)
args = parser.parse_args()
text = args.printer.read_bytes().decode('ascii', errors='replace').replace('\ufffd', '?')
# Normalize printer line endings, including dumps with non-text bytes.
text = text.replace('\r\n', '\n').replace('\r', '\n')
start = re.search(r'^\*{4}A  START  JOB\s+' + str(args.job) + r'\b', text, re.M)
ends = list(re.finditer(r'^\*{4}A   END   JOB\s+' + str(args.job) + r'\b[^\n]*', text, re.M))
if not start or not ends or ends[-1].end() <= start.start():
    raise SystemExit('Complete job banners not found; wait for printer completion')
output = text[start.start():ends[-1].end()] + '\n'
output = re.sub(r'PASSWORD=[^\s,]*', 'PASSWORD=<REDACTED>', output)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(output, encoding='ascii')
print(args.output)
