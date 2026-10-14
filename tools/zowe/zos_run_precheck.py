#!/usr/bin/env python3
"""ZOS-2 pre-submission gate of a run-chunk deck of record (user batch approval C5..C7): audit, the only dataset is the
STEPLIB load library, no DELETE, every step EXEC PGM=PACZ2D COND=(0,NE), STEPLIB Z00000.PACMAN.LOAD, CEEOPTS exactly
ALL31(OFF),STACK(,,BELOW), steps = the CHUNKS entry, estimate < 4,000 spool lines (tools/zowe/zos_plan.py).
Usage (project directory): zos_run_precheck.py CHUNK   (the deck = generated: tests/test_zos_tools.py)"""
import sys,re,subprocess
sys.path.insert(0,'tools/zowe'); sys.path.insert(0,'tools')
from zoslib import render, audit_deck
import zos_target as Z
name=sys.argv[1]; job=Z.CHUNKS[name][0]
t=open(f'jcl/zos/{job}.jcl').read(); r=render(t,'Z00000')
steps=re.split(r'(?m)^(?=//\w+\s+EXEC )',r)[1:]
ok=[]
ok.append(('audit', audit_deck(r,'Z00000')==[]))
ok.append(('only DSN = STEPLIB load', set(re.findall(r'DSN=([\w.]+)',r))=={'Z00000.PACMAN.LOAD'}))
ok.append(('no DELETE', 'DELETE' not in r))
ok.append(('all PGM=PACZ2D', all(re.match(r'//\w+\s+EXEC PGM=PACZ2D,COND=\(0,NE\)',s) for s in steps)))
ok.append(('STEPLIB each', all('//STEPLIB  DD DSN=Z00000.PACMAN.LOAD,DISP=SHR\n' in s for s in steps)))
ok.append(('CEEOPTS exact', all('//CEEOPTS  DD *\nALL31(OFF),STACK(,,BELOW)\n/*\n' in s for s in steps)))
ok.append(('steps = chunk', [re.match(r'//(\w+)',s).group(1) for s in steps]==Z.CHUNKS[name][2]))
p=subprocess.run([sys.executable,'tools/zowe/zos_plan.py',name,'--budget','4000'],capture_output=True,text=True)
ok.append(('estimate < 4000', p.returncode==0)); print(p.stdout.strip())
for k,v in ok: print(('OK  ' if v else 'FAIL'),k)
sys.exit(0 if all(v for _,v in ok) else 1)
