#!/usr/bin/env python3
"""MVS-0 acceptance: all steps RC 0000 and PACHELLO printed its banner."""
import re, sys
t = open(sys.argv[1]).read()
rcs = re.findall(r'(\w+)\s+(?:IEBGENER|IKFCBL00|IEWL|PACHELLO)\s+RC= (\d{4})', t)
ok = len(rcs) == 4 and all(r == '0000' for _, r in rcs) \
    and re.search(r'^PACMAN MVS-0 PACHELLO READY$', t, re.M) and 'IKF' not in t.split('IEWL')[0].replace('IKFCBL00', '')
print('MVS-0', 'PASS' if ok else 'FAIL', rcs)
sys.exit(0 if ok else 1)
