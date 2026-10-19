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
Z4 (ZOS-6 presentation decoupling, ZV-D33, docs/zos6-production-design.md): PACREQ / PACMAIN / PACPLAT / PACDISP / PACSCR
differ from their Z1 text (2.0-mvs-max + the Z1 lines) by exactly the hunks of tests/zos_z4.json (no core source, no other
file); z4_reverse(rel, text) puts the Z1 text back. Z5 (ZOS-6): the PRESENT keyword lines of src/zos/PACMAN.clist
(Z5_*), put back by z5_strip before the Z3 / Z2 checks.
  python3 tests/zos_c2.py --z4-table  rewrite tests/zos_z4.json from the working tree (an explicit, reviewed step)
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


# Z3 (ZOS-4, proposed 2026-10-16, docs/zos4-sysin-fix.md): the 2.0 line `ALLOC F(SYSIN) DA(*) REUSE` becomes exactly these
# lines (terminal SYSIN fixed 80 through ATTRIB + USING; the attribute list freed at once, only if created here)
Z3_OLD = 'ALLOC F(SYSIN) DA(*) REUSE'
Z3_BLOCK = [
    '/* Z3 (ZOS-4): SYSIN FIXED 80 (PACINPT COMMAND-FILE) WHATEVER THE  */',
    '/* TERMINAL WIDTH: ON DA(*) ONLY ATTRIB + USING SET THE DCB. THE   */',
    '/* LIST IS FREED AT ONCE (ONLY IF CREATED HERE). FAILURE: RC 8.    */',
    'SET &Z = 0',
    'SET &T = 0',
    'CONTROL NOFLUSH',
    'ERROR DO',
    '  SET &Z = &LASTCC',
    '  RETURN',
    'END',
    'ATTRIB Z3SIATTR RECFM(F) LRECL(80) BLKSIZE(80)',
    'IF &Z = 0 THEN DO',
    '  SET &T = 1',
    '  ALLOC F(SYSIN) DA(*) REUSE USING(Z3SIATTR)',
    'END',
    'SET &I = &Z',
    'IF &T = 1 THEN FREE ATTRLIST(Z3SIATTR)',
    'ERROR OFF',
    'CONTROL FLUSH',
    'IF &Z NE 0 THEN DO',
    '  WRITE PACMAN: SYSIN NOT ALLOCATED (Z3, RC &Z), GAME NOT STARTED',
    '  IF &T = 1 AND &I = 0 THEN FREE F(SYSIN)',
    '  EXIT CODE(8)',
    'END',
]


# Z5 (ZOS-6, docs/zos6-production-design.md section 14): PRESENT(EVERY|COALESCED), default EVERY; the 2.0 PARM line is
# unchanged; EVERY adds nothing to the PARM (the 25-column 2.0 PARM byte for byte), COALESCED appends column 26 = C
Z5_PROC = ('  ALARM(PATTERN)', '  ALARM(PATTERN) PRESENT(EVERY)')
Z5_HELP_AFTER = '/* LEVEL CLEAR 3, GAME OVER 3, WIN 4) OR SINGLE (ONE BELL EACH).    */'
Z5_HELP = ['/* PRESENT: EVERY (DEFAULT: ONE SCREEN WRITE PER REALTIME QUANTUM)  */',
           '/* OR COALESCED (ZOS-6, ZV-D33: A WRITE EVERY 2ND / 3RD QUANTUM).   */']
Z5_SET_AFTER = 'SET &P = &STR(TSO AI&AI &GHOSTS &M&C&H&A&R&G&S&V&Y&U&W&L&F&K)'      # the 2.0 PARM line, unchanged
Z5_SET = ['/* Z5 (ZOS-6): PRESENT(COALESCED) ADDS PARM COLUMN 26 = C; EVERY    */',
          '/* LEAVES THE 25-COLUMN 2.0 PARM UNTOUCHED.                         */',
          'SET &E = &SUBSTR(1:1,&PRESENT)',               # only statement forms this CLIST already uses (no null SET)
          'IF &E = C THEN SET &P = &STR(&P&E)']


def z5_strip(text):
    """The Z3 text of src/zos/PACMAN.clist: the Z5 lines (exactly, once each, in place) removed / put back."""
    now = text.split('\n')
    assert now.count(Z5_PROC[1]) == 1 and Z5_PROC[0] not in now, 'Z5: PROC line'
    now[now.index(Z5_PROC[1])] = Z5_PROC[0]
    for after, block in ((Z5_HELP_AFTER, Z5_HELP), (Z5_SET_AFTER, Z5_SET)):
        i = now.index(after) + 1
        assert now[i:i + len(block)] == block, 'Z5: block not exact'
        del now[i:i + len(block)]
    assert not any('PRESENT' in l or '&E' in l for l in now), 'Z5: a PRESENT / &E line outside the Z5 lines'
    assert now.count(Z5_SET_AFTER) == 1, 'Z5: the 2.0 PARM line'
    return '\n'.join(now)


# Z4 (ZOS-6): the sources and the hunk table
Z4_FILES = ['src/copy/PACREQ.cpy', 'src/cobol/PACMAIN.cob', 'src/cobol/PACPLAT.cob', 'src/cobol/PACDISP.cob',
            'src/cobol/PACSCR.cob']
Z4_TABLE = R / 'tests/zos_z4.json'


def z1_text(rel):
    """2.0-mvs-max with the Z1 lines of rel applied (the Z1 text; = the tag text for a file Z1 does not touch)."""
    lines = at_tag(rel).split('\n')
    for e in table():
        if e['file'] == rel:
            lines[e['line'] - 1] = e['new']
    return '\n'.join(lines)


def z4_hunks(old, new):
    import difflib
    a, b = old.split('\n'), new.split('\n')
    return [[i1, i2, a[i1:i2], b[j1:j2]] for op, i1, i2, j1, j2 in
            difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op != 'equal']


def z4_table():
    return json.loads(Z4_TABLE.read_text()) if Z4_TABLE.exists() else {}


def z4_reverse(rel, text):
    """The Z1 text of a Z4 source: the listed hunks undone (asserting each hunk's new lines are in place)."""
    hunks = z4_table().get(rel, [])
    a = z1_text(rel).split('\n')
    out, k = [], 0
    for i1, i2, old, new in hunks:
        out += a[k:i1] + new
        k = i2
    out += a[k:]
    assert '\n'.join(out) == text, f'{rel}: not the Z1 text plus exactly the Z4 hunks of {Z4_TABLE.name}'
    return z1_text(rel)


def z4_guard():
    t = z4_table()
    assert sorted(t) == sorted(Z4_FILES), f'Z4 files {sorted(t)} != {sorted(Z4_FILES)}'
    for rel in Z4_FILES:
        now = (R / rel).read_text(encoding='ascii')
        assert z4_hunks(z1_text(rel), now) == t[rel], f'{rel}: differs from the Z1 text beyond the Z4 hunks'
        z4_reverse(rel, now)
    return t


def z3_strip(text):
    """The Z2-only text of src/zos/PACMAN.clist: the Z3 block (exactly Z3_BLOCK, once, in place of the 2.0 SYSIN line)
    put back to that one line; z2_guard then proves every other line (the position included: lines before Z2 = 2.0)."""
    now = text.split('\n')
    i = now.index(Z3_BLOCK[0])
    assert now[i:i + len(Z3_BLOCK)] == Z3_BLOCK, 'Z3: block not exact'
    assert Z3_OLD not in now and sum(l.startswith('/* Z3 (ZOS-4)') for l in now) == 1, 'Z3: once, replacing the line'
    return '\n'.join(now[:i] + [Z3_OLD] + now[i + len(Z3_BLOCK):])


def z2_guard(text):
    """src/zos/PACMAN.clist = the 2.0-mvs-max src/clist/PACMAN.clist with exactly 31 Z2 lines before the CALL (from the
    '/* Z2 (ZOS-4)' comment) and 'FREE F(CEEOPTS)' right after it; every other line identical (docs/zos4-clist-z2.md)."""
    base, now = at_tag('src/clist/PACMAN.clist').split('\n'), text.split('\n')
    zi = next(i for i, l in enumerate(now) if l.startswith('/* Z2 (ZOS-4)'))
    zc = now.index("CALL '@@PREFIX@@.LOAD(PACMAIN)' '&P'")
    assert zc - zi == 31 and now[:zi] == base[:zi] and now[zc] == base[zi], 'Z2: lines before the CALL'
    assert now[zc + 1] == 'FREE F(CEEOPTS)' and now[zc + 2:] == base[zi + 1:], 'Z2: lines after the CALL'
    assert len(now) - len(base) == 32


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
        if rel == 'src/zos/PACMAN.clist':           # Z2 + Z3 (ZOS-4) + Z5 (ZOS-6): the frozen 2.0 CLIST + Z3 + Z2 + Z5
            z2_guard(z3_strip(z5_strip(p.read_text(encoding='ascii'))))
            continue
        now = p.read_text(encoding='ascii')
        if rel in Z4_FILES:                         # Z4 (ZOS-6): the exact hunks first, then the Z1 rule below
            now = z4_reverse(rel, now)
        if rel in changed:
            base = at_tag(rel)
            assert len(now.split('\n')) == len(base.split('\n')), rel
            assert reverse(rel, now) == base, f'{rel}: differs from {TAG} beyond the listed Z1 lines'
            assert not any(OLD.match(l) for l in now.split('\n')), rel
        else:
            assert now == at_tag(rel), f'{rel}: differs from {TAG} (not allowed by Z1)'
    z4_guard()
    tracked = subprocess.run(['git', 'ls-tree', '-r', '--name-only', TAG, './src/'], cwd=R, capture_output=True,
                             text=True, check=True).stdout.split()
    missing = [x for x in tracked if not (R / x).exists()]
    assert not missing, f'deleted since {TAG}: {missing}'
    return t, changed


if __name__ == '__main__':
    if sys.argv[1:] == ['--z4-table']:
        Z4_TABLE.write_text(json.dumps({rel: z4_hunks(z1_text(rel), (R / rel).read_text(encoding='ascii'))
                                        for rel in Z4_FILES}, indent=1) + '\n')
        print(f'wrote {Z4_TABLE.name}')
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
    z4 = z4_table()
    print(f'Z1 (C2) guard PASS: {len(t)} substitutions in {len(changed)} sources; Z4 (ZOS-6): '
          f'{sum(len(v) for v in z4.values())} hunks in {len(z4)} sources; Z5 CLIST lines exact; every other src '
          f'file = {TAG}')
