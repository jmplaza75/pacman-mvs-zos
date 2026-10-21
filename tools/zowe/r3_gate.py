#!/usr/bin/env python3
"""R3 gate (ZOS-2, docs/ZOS-MIGRATION-PLAN.md R3): the MVS release and the MVS target of tools/make_deck.py are
unchanged on branch zos.

Usage: r3_gate.py [--ref zos-1] [--tag 2.0-mvs-max]
Since the z/OS port delta Z1 (tests/zos_c2.py) the shared COBOL sources of branch zos are no longer the MVS sources of
record, so the MVS generator is checked on the frozen sources (git archive of --tag, read-only, in a temporary
directory) and the source delta is checked separately:
1. release files: every releases/2.0-MVS-MAX/decks/*.jcl on disk has its SHA-256 of releases/2.0-MVS-MAX/SHA256SUMS;
2. release regeneration: the current tools/ run over the --tag sources rebuild the 13 decks of record with their
   MANIFEST commands, SHA-256 equal to SHA256SUMS;
3. generator: every MVS deck make_deck.py offers (default prefix, with and without --runonly), current tools/ vs the
   tools/ of --ref, both over the --tag sources: byte-identical;
4. source delta: the same MVS decks generated from the zos working tree differ from (3) only by Z1 lines (every
   removed line is the 'old' and every added line the 'new' text of a tests/zos_c2.json entry) and by Z4 lines (ZOS-6,
   the hunks of tests/zos_z4.json, checked exactly on the sources by tests/zos_c2.py) and by the D46 lines (ZOS-11,
   REALTIME Right on PF12: tests/zos_c2.py D46, PACINPT). These decks are not MVS builds of record: MVS is frozen at
   --tag and is never rebuilt from branch zos.
Exit 1 on any difference. Nothing is written outside a temporary directory.
"""
import argparse
import collections
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
R20, INST = 'HERC01.PACMAN.R20', 'HERC01.PACMAN'
RELEASE = [('R20-ALLOC', ['ALLOC', '--prefix', R20]), ('R20-CLIST', ['CLIST', '--prefix', R20]),
           ('R20-REL20', ['REL20', '--prefix', R20])] + \
          [(f'R20-{d}', [d, '--runonly', '--load', 'PACMAIN', '--prefix', R20]) for d in ('S2', 'RP', 'GP2', 'GP23', 'HS')] + \
          [('INST20', ['INST20', '--source', R20, '--prefix', INST]), ('INST-CLIST', ['CLIST', '--prefix', INST]),
           ('DATA', ['DATA', '--prefix', INST]), ('INST-ORACLE', ['RELEASE', '--runonly', '--prefix', INST]),
           ('INST-S2', ['S2', '--runonly', '--load', 'PACMAIN', '--prefix', INST])]


def gen(root, args, out):
    r = subprocess.run([sys.executable, str(root / 'tools/make_deck.py'), *args, '--out', str(out)],
                       capture_output=True, text=True)
    return r.returncode, (r.stderr.strip().splitlines() or [''])[-1]


def choices(root):
    r = subprocess.run([sys.executable, str(root / 'tools/make_deck.py'), '--help'], capture_output=True, text=True)
    sets = re.findall(r'\{([^}]*)\}', ''.join(r.stdout.split()))
    return next(x.split(',') for x in sets if 'ALLOC' in x.split(','))


def git(*a, cwd=R):
    return subprocess.run(['git', *a], cwd=cwd, capture_output=True, check=True).stdout


def tree(ref, dest):
    """The project directory at ref, extracted into dest (read-only use)."""
    prefix = git('rev-parse', '--show-prefix').decode().strip()
    top = git('rev-parse', '--show-toplevel').decode().strip()
    dest.mkdir()
    subprocess.run(['tar', '-x', '-C', str(dest)], input=git('archive', ref, prefix, cwd=top), check=True)
    return dest / prefix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', default='zos-1')
    ap.add_argument('--tag', default='2.0-mvs-max')
    a = ap.parse_args()
    bad = 0
    sums = {l.split()[1]: l.split()[0] for l in (R / 'releases/2.0-MVS-MAX/SHA256SUMS').read_text().splitlines() if l}
    for name, _ in RELEASE:
        key = f'releases/2.0-MVS-MAX/decks/{name}.jcl'
        ok = hashlib.sha256((R / key).read_bytes()).hexdigest() == sums[key]
        bad += not ok
        print(f'{"OK  " if ok else "DIFF"} 1 file {key}')
    z1 = json.loads((R / 'tests/zos_c2.json').read_text()) if (R / 'tests/zos_c2.json').exists() else []
    old_lines = collections.Counter(e['old'] for e in z1)
    new_lines = collections.Counter(e['new'] for e in z1)
    z4 = json.loads((R / 'tests/zos_z4.json').read_text()) if (R / 'tests/zos_z4.json').exists() else {}
    z4_old = {l for hs in z4.values() for h in hs for l in h[2]}      # ZOS-6 Z4 hunks (tests/zos_c2.py z4_guard)
    z4_new = {l for hs in z4.values() for h in hs for l in h[3]}
    sys.path.insert(0, str(R / 'tests'))
    from zos_c2 import D46                                              # ZOS-11 (2.1-zos): the exact PF12 lines
    z4_old |= {o for rel, ls in D46.items() if rel.startswith('src/cobol/') for o, _ in ls}
    z4_new |= {n for rel, ls in D46.items() if rel.startswith('src/cobol/') for _, n in ls}
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        frozen = tree(a.tag, t / 'tag')                 # sources of record + current generator
        shutil.rmtree(frozen / 'tools')
        shutil.copytree(R / 'tools', frozen / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
        refroot = tree(a.ref, t / 'ref')                # generator of --ref (its sources = --tag sources)
        for f in ('src/cobol', 'src/copy', 'src/asm', 'src/clist', 'maps'):      # (zos-1 adds only src/probe/zos)
            assert not subprocess.run(['diff', '-r', '-q', str(frozen / f), str(refroot / f)],
                                      capture_output=True).returncode, f'{a.ref} {f} != {a.tag} {f}'
        for name, args in RELEASE:
            rc, err = gen(frozen, args, t / f'{name}.jcl')
            key = f'releases/2.0-MVS-MAX/decks/{name}.jcl'
            got = hashlib.sha256((t / f'{name}.jcl').read_bytes()).hexdigest() if rc == 0 else err
            ok = got == sums[key]
            bad += not ok
            print(f'{"OK  " if ok else "DIFF"} 2 regenerated {name:<12} {got[:16]}')
        names = choices(refroot)
        assert names == choices(frozen) == choices(R), 'MVS deck list changed'
        n = nz = 0
        for d in names:
            for extra in ([], ['--runonly']):
                rc1, e1 = gen(refroot, [d, *extra], t / 'a.jcl')
                rc2, e2 = gen(frozen, [d, *extra], t / 'b.jcl')
                rc3, e3 = gen(R, [d, *extra], t / 'c.jcl')
                n += 1
                same = (rc1, e1) == (rc2, e2) and (rc1 != 0 or (t / 'a.jcl').read_bytes() == (t / 'b.jcl').read_bytes())
                if not same:
                    bad += 1
                    print(f'DIFF 3 generator {d} {" ".join(extra)} (ref rc {rc1} {e1} / now rc {rc2} {e2})')
                if rc2 == 0 and rc3 == 0:
                    b, c = (t / 'b.jcl').read_text().splitlines(), (t / 'c.jcl').read_text().splitlines()
                    rem, add = collections.Counter(), collections.Counter()
                    for l in difflib.unified_diff(b, c, lineterm='', n=0):
                        if l.startswith('-') and not l.startswith('---'):
                            rem[l[1:]] += 1
                        elif l.startswith('+') and not l.startswith('+++'):
                            add[l[1:]] += 1
                    if rem or add:
                        nz += 1
                    z1r = sum(v for k, v in rem.items() if k in old_lines and k not in z4_old)
                    z1a = sum(v for k, v in add.items() if k in new_lines and k not in z4_new)
                    if set(rem) - set(old_lines) - z4_old or set(add) - set(new_lines) - z4_new or z1r != z1a:
                        bad += 1
                        print(f'DIFF 4 source delta {d} {" ".join(extra)}: removed {dict(rem)} added {dict(add)}')
                elif (rc2, e2) != (rc3, e3):
                    bad += 1
                    print(f'DIFF 4 {d} {" ".join(extra)}: rc {rc2} {e2} / {rc3} {e3}')
                for f in ('a.jcl', 'b.jcl', 'c.jcl'):
                    (t / f).unlink(missing_ok=True)
        print(f'3 {n} MVS deck generations: current generator = {a.ref} generator on the {a.tag} sources')
        print(f'4 {nz} of them carry source text and differ from the frozen ones only by Z1 lines '
              f'({len(z1)} listed substitutions), Z4 lines ({sum(len(v) for v in z4.values())} hunks) and D46 lines')
    print('R3 GATE ' + ('PASS' if not bad else f'FAIL ({bad})'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
