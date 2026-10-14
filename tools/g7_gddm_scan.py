#!/usr/bin/env python3
"""MVS-G7: scan a G7CHK listing (jcl/mvs/G7CHK.jcl) for GDDM / host-graphics names.
Usage: tools/g7_gddm_scan.py build/PACG7C02.txt  (exit 1 if any name matches)."""
import re, sys
t=open(sys.argv[1],encoding='ascii',errors='replace').read()
libs={};cur=None;inm=False
for ln in t.splitlines():
    m=re.match(r'^(SYS[12]\.[A-Z0-9]+)\s*$',ln)
    if m: cur=m.group(1);libs[cur]=[];inm=False;continue
    if ln.startswith('--MEMBERS--'): inm=True;continue
    if cur and inm:
        if ln.startswith(' ') and ln.strip():
            libs[cur]+=re.findall(r'[A-Z@#$][A-Z0-9@#$]{0,7}',ln.replace('ALIAS',''))
        else: inm=False
pat=re.compile(r'^(ADM|GDDM|GKS|GOCA|PGF|ICU|IPDS)')
for l,ms in libs.items():
    hits=[x for x in ms if pat.match(x)]
    print(f'{l:14s} members+aliases {len(ms):5d}  GDDM-like {hits}')
ds=re.findall(r'NONVSAM -+ (\S+)',t); al=re.findall(r'ALIAS -+ (\S+)',t)
print('catalog nonvsam',len(ds),'aliases',len(al))
print('dataset hits',[d for d in ds+al if re.search(r'GDDM|ADM|GKS|GOCA|PGF',d)])
sys.exit(1 if any(pat.match(x) for ms in libs.values() for x in ms) or [d for d in ds+al if re.search(r'GDDM|ADM|GKS|GOCA|PGF',d)] else 0)
