#!/usr/bin/env python3
"""ZOS-2 port compatibility delta Z1 (ex candidate C2, docs/ZOS-DIFFS.md): the ANS-68 `01  <name> COPY <member>.`
entries of the shared COBOL sources become `COPY <member>.` on branch zos only, because Enterprise COBOL (ANS-85)
inserts the member after the 01 instead of replacing the entry, and every member already owns `01 <name>.` (D16).

The allowance is explicit: tests/zos_c2.json lists the 28 substitutions (file, line, text before, text after).
  python3 tests/zos_c2.py             the guard: against tag 2.0-mvs-max, src/ differs by exactly those 28 lines
  python3 tests/zos_c2.py --apply     apply the listed substitutions to a tree equal to 2.0-mvs-max (once)
Guard: (1) every listed line of 2.0-mvs-max is `       01  <name> COPY <member>.` and becomes `       COPY <member>.`;
(2) the member's first data entry is `01  <name>.`; (3) each changed source equals 2.0-mvs-max with exactly its listed
lines replaced, nothing else (same line count, every other byte identical); (4) every other file under src/ (copy,
asm, clist, the other COBOL sources) is byte-identical to 2.0-mvs-max; (5) no ANS-68 01-COPY form is left; (6) 28.
reverse(rel, text) gives back the 2.0-mvs-max text of a changed source: the core guards (tests/test_core_frozen.py,
tests/test_g8.py) accept a core change only when reversing exactly these lines restores the frozen hash.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
TAG = '2.0-mvs-max'
TABLE = R / 'tests/zos_c2.json'
OLD = re.compile(r'^       01  ([A-Z][A-Z0-9-]*) COPY ([A-Z][A-Z0-9]*)\.$')
COUNT = 28


def at_tag(rel):
    r = subprocess.run(['git', 'show', f'{TAG}:./{rel}'], cwd=R, capture_output=True)
    if r.returncode:
        raise SystemExit(f'{rel} not in {TAG}')
    return r.stdout.decode('ascii')


def table():
    return json.loads(TABLE.read_text()) if TABLE.exists() else []


def reverse(rel, text):
    """The 2.0-mvs-max text of a source changed by Z1 (only the listed lines are put back)."""
    lines = text.split('\n')
    for e in table():
        if e['file'] == rel:
            assert lines[e['line'] - 1] == e['new'], (rel, e['line'])
            lines[e['line'] - 1] = e['old']
    return '\n'.join(lines)


def build_table():
    out = []
    for p in sorted((R / 'src/cobol').glob('*.cob')):
        rel = str(p.relative_to(R))
        for n, l in enumerate(at_tag(rel).split('\n'), 1):
            m = OLD.match(l)
            if m:
                out.append({'file': rel, 'line': n, 'name': m.group(1), 'member': m.group(2), 'old': l,
                            'new': f'       COPY {m.group(2)}.'})
    return out


def guard():
    t = table()
    assert len(t) == COUNT, f'{len(t)} substitutions listed, {COUNT} expected'
    assert t == build_table(), 'tests/zos_c2.json does not list exactly the 01-COPY entries of ' + TAG
    for e in t:
        assert OLD.match(e['old']) and e['new'] == f'       COPY {e["member"]}.', e
        cpy = (R / f'src/copy/{e["member"]}.cpy').read_text()
        first = next(l for l in cpy.splitlines() if len(l) > 6 and l[6] != '*' and l.strip())
        assert first == f'       01  {e["name"]}.', (e['member'], first)
    changed = sorted({e['file'] for e in t})
    for p in sorted(R.glob('src/**/*')):
        if not p.is_file() or p.name == '.DS_Store':
            continue
        rel = str(p.relative_to(R))
        if rel.startswith('src/probe/'):            # z/OS probes (ZOS-1) are not part of the release set
            continue
        now = p.read_text(encoding='ascii')
        if rel in changed:
            base = at_tag(rel)
            assert len(now.split('\n')) == len(base.split('\n')), rel
            assert reverse(rel, now) == base, f'{rel}: differs from {TAG} beyond the listed Z1 lines'
            assert not any(OLD.match(l) for l in now.split('\n')), rel
        else:
            assert now == at_tag(rel), f'{rel}: differs from {TAG} (not allowed by Z1)'
    tracked = subprocess.run(['git', 'ls-tree', '-r', '--name-only', TAG, './src/'], cwd=R, capture_output=True,
                             text=True, check=True).stdout.split()
    missing = [x for x in tracked if not (R / x).exists()]
    assert not missing, f'deleted since {TAG}: {missing}'
    return t, changed


if __name__ == '__main__':
    if sys.argv[1:] == ['--apply']:
        t = build_table()
        assert len(t) == COUNT, len(t)
        for rel in sorted({e['file'] for e in t}):
            assert (R / rel).read_text(encoding='ascii') == at_tag(rel), f'{rel} is not the {TAG} text'
            lines = at_tag(rel).split('\n')
            for e in t:
                if e['file'] == rel:
                    lines[e['line'] - 1] = e['new']
            (R / rel).write_text('\n'.join(lines), encoding='ascii')
        TABLE.write_text(json.dumps(t, indent=1) + '\n')
        print(f'applied {len(t)} substitutions')
    t, changed = guard()
    print(f'Z1 (C2) guard PASS: {len(t)} substitutions in {len(changed)} sources, copybooks and every other src file '
          f'= {TAG}')
