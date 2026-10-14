"""Shared helpers for the z/OS tools (ZOS-1, docs/ZOS-MIGRATION-PLAN.md sec. 7).

Rules enforced here (CLAUDE.md on branch zos, plan R7): the HLQ is never a literal in the repository (templates use
@@HLQ@@; the value comes from --hlq or PACMAN_ZOS_HLQ); a submitted deck may write only <HLQ>.PACMAN.* datasets; the
tools never delete datasets or purge jobs. Credentials stay in the Zowe secure store; nothing here reads them.
"""
import json
import os
import re
import subprocess
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
PROFILE = os.environ.get('PACMAN_ZOWE_PROFILE', 'zosmf')
ENCODING = 'IBM-037'          # same table as the MVS sources (Hercules reader = CP037 on every code character)
PY_CODEC = 'cp037'
LRECL = 80


def hlq(arg=None):
    v = arg or os.environ.get('PACMAN_ZOS_HLQ')
    if not v or not re.fullmatch(r'[A-Z#$@][A-Z0-9#$@]{0,7}', v):
        raise SystemExit('HLQ missing or invalid: pass --hlq or set PACMAN_ZOS_HLQ')
    return v


def zowe(*args, json_out=False, check=True):
    cmd = ['zowe', *args, '--zosmf-p', PROFILE] + (['--rfj'] if json_out else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if json_out:
        try:
            data = json.loads(r.stdout)
        except ValueError:
            raise SystemExit(f'zowe {" ".join(args)}: no JSON\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}')
        if check and not data.get('success', False):
            raise SystemExit(f'zowe {" ".join(args)} failed: {data.get("message")} {data.get("stderr", "")[-1500:]}')
        return data
    if check and r.returncode != 0:
        raise SystemExit(f'zowe {" ".join(args)} failed rc={r.returncode}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}')
    return r


def fixed_records(path):
    """The expected dataset bytes of a local text source: each line encoded to IBM-037 and padded to 80 bytes."""
    out = bytearray()
    for n, line in enumerate(Path(path).read_text(encoding='ascii').splitlines(), 1):
        b = line.encode(PY_CODEC)
        if len(b) > LRECL:
            raise SystemExit(f'{path}:{n}: {len(b)} bytes > LRECL {LRECL}')
        out += b + b'\x40' * (LRECL - len(b))
    return bytes(out)


def render(template_text, h):
    return template_text.replace('@@HLQ@@', h)


DSN = re.compile(r'DSN=([A-Z0-9#$@.&]+)(?:\(([A-Z0-9#$@+-]+)\))?')


def audit_deck(text, h):
    """Every dataset a deck may write (DISP NEW/MOD/OLD, SYSLMOD/SYSLIN/SYSUT2 outputs) is under <HLQ>.PACMAN;
    no DISP=...DELETE anywhere. Returns a list of problems."""
    bad = []
    stmts, cur = [], ''
    for line in text.splitlines():
        if not line.startswith('//') or line.startswith('//*'):
            continue
        body = line[2:71]
        cur = cur + body.strip() if cur else body
        if not body.rstrip().endswith(','):
            stmts.append(cur)
            cur = ''
    for s in stmts:
        if re.search(r'\bDISP=\([^)]*DELETE', s) or re.search(r'\bDISP=DELETE', s):
            bad.append(f'DELETE disposition: {s[:90]}')
        m = DSN.search(s)
        if not m:
            continue
        name = m.group(1)
        writes = re.search(r'DISP=\(?(NEW|MOD|OLD)', s) or re.match(r'(\S*\.)?(SYSLMOD|SYSLIN|SYSUT2|SYSPUNCH)\s', s)
        if writes and not (name.startswith('&&') or name.startswith(h + '.PACMAN.') or name == h + '.PACMAN'):
            bad.append(f'writes outside {h}.PACMAN: {s[:90]}')
    return bad
