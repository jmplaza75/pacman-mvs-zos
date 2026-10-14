#!/usr/bin/env python3
"""MVS-G8 / 2.0-MVS-MAX acceptance (D43, docs/G8-RELEASE.md).
Local:    the frozen final CLIST default set (only RULES flipped to ARCADE; CLIST otherwise = mvs-s2 apart from comment
          lines); no game / display / platform / assembler / copy source changed since mvs-s2 (PACMAIN absent-PARM
          behaviour unchanged: no RULES column = CLASSIC); core frozen; REL20 = the S2 module, copy and assembler set;
          ALLOC sized for 2.0; every R20 deck passes the JCL audit (tools/g8_jcl_audit.py).
Hercules (any subset of the options):
  --rel20 L  deck REL20 (job PACREL20): JCL audit of the listing, every step RC 0000, no compiler warnings, the
             CLIST runs give the modelled PARM (G8PARM=), the 1.0-MVS oracle (tests/test_mvs8.py on the 1.0 steps).
  --s2 L --rp L --gp2 L --gp23 L --hs L   the regression decks run-only (make_deck.py --runonly --load PACMAIN) on
             the REL20 module: JCL audit, the run-only marker, then test_s2 / test_rp / test_hs (GP23 + GP2) with
             PACMAN_RUNONLY=1 PACMAN_LATER_PHASE=G8 on listings normalised to the decks' default load names.
  --clist L  deck CLIST: the member printed back = src/clist/PACMAN.clist with the prefix.
  --inst L   deck INST20 (job PACINS20): IEBCOPY replaced PACMAIN, the AMASPZAP dumps of the source and the installed
             member are identical (every CSECT, every byte), all RC 0000.
  --oracle L deck RELEASE run-only on the installed member (with --rel20): the 19 batch + 6 TSO blocks = REL20's.
  --prefix P (default HERC01.PACMAN.R20); --load M: the load member the listings ran (default PACMAIN; G8.2 used
             the development member PACR20D under HERC01.PACMAN, the installed PACMAIN untouched)."""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tools'))
ap = argparse.ArgumentParser()
for o in ('rel20', 's2', 'rp', 'gp2', 'gp23', 'hs', 'clist', 'inst', 'oracle'):
    ap.add_argument('--' + o)
ap.add_argument('--prefix', default='HERC01.PACMAN.R20')
ap.add_argument('--load', default='PACMAIN')
ARGS, sys.argv = ap.parse_args(), sys.argv[:1]
os.environ['PACMAN_LATER_PHASE'] = 'G8'
import make_deck as M  # noqa: E402
from g8_jcl_audit import audit_deck, audit_listing  # noqa: E402

BASE = 'mvs-s2'
FINAL = dict(AI='1', GHOSTS='1', COLOR='AUTO', HILITE='AUTO', ANIM='AUTO', REDRAW='PARTIAL', METRICS='NO',
             GLYPHS='AUTO', SCALE='AUTO', CANVAS='AUTO', PLAY='REALTIME', SOUND='AUTO', RULES='ARCADE', LEVEL='1',
             SPEED='NORMAL', ALARM='PATTERN')


def git(*a):
    return subprocess.run(['git', *a], cwd=R, capture_output=True, text=True)


# 1. local ---------------------------------------------------------------------------------------------------------
clist = (R / 'src/clist/PACMAN.clist').read_text()
lines = clist.splitlines()
proc = ' '.join(lines[:next(i for i, l in enumerate(lines) if l.startswith('/*'))])
assert dict(re.findall(r'(\w+)\((\w*)\)', proc)) == FINAL, proc
assert all(len(l) <= 72 for l in clist.replace('@@PREFIX@@', 'HERC01.PACMAN.R20').splitlines())
old = git('show', f'{BASE}:./src/clist/PACMAN.clist').stdout.splitlines()
strip = lambda ls: [l for l in ls if not l.startswith('/*')]
assert [l.replace('RULES(CLASSIC)', 'RULES(ARCADE)') for l in strip(old)] == strip(lines), 'CLIST code changed'
changed = git('diff', '--name-only', BASE, '--', 'src/cobol', 'src/copy', 'src/asm').stdout.split()
assert changed == [], changed
subprocess.run([sys.executable, str(R / 'tests/test_core_frozen.py')], check=True, stdout=subprocess.DEVNULL)
assert M.DECKS['REL20'][1:3] == M.DECKS['S2'][1:3] and M.ASM['REL20'] == M.ASM['S2'] and \
    M.DECKS['REL20'][3] == 'PACMAIN' and M.TSO['REL20'] == M.TSO['RELEASE'] and M.DECKS['REL20'][4] == M.DECKS['RELEASE'][4]
alloc = M.alloc_deck(ARGS.prefix)
assert alloc.count('SPACE=(CYL,(5,2,20))') == 2 and 'SPACE=(TRK,(30,10,10))' in alloc and 'DISP=(NEW,CATLG,DELETE)' in alloc


def clist_parm(kw):
    """The PARM the CLIST builds: first letters, LEVEL zero-padded to 2 (else 01), SPEED column 24, ALARM 25."""
    d = dict(FINAL)
    d.update(re.findall(r'(\w+)\((\w*)\)', kw))
    lv = '0' + d['LEVEL'] if len(d['LEVEL']) == 1 else d['LEVEL']
    lv = lv if len(lv) == 2 else '01'
    return (f"TSO AI{d['AI']} {d['GHOSTS']} " + ('M' if d['METRICS'] == 'YES' else 'N') + ''.join(
        d[k][0] for k in ('COLOR', 'HILITE', 'ANIM', 'REDRAW', 'GLYPHS', 'SCALE', 'CANVAS', 'PLAY', 'SOUND', 'RULES'))
        + lv + d['SPEED'][0] + d['ALARM'][0])


G8_WANT = [clist_parm(k) for k in M.G8_CLIST]
assert G8_WANT[0] == 'TSO AI1 1 NAAAPAAARAA01NP' and G8_WANT[1][20] == 'C' and G8_WANT[0][20] == 'A', G8_WANT

decks = {'ALLOC': alloc, 'CLIST': M.clist_deck(ARGS.prefix), 'REL20': M.build('REL20', ARGS.prefix)}
os.environ['PACMAN_RUNONLY'] = '1'
for k in ('S2', 'RP', 'GP2', 'GP23', 'HS'):
    decks[k] = M.build(k, ARGS.prefix, 'PACMAIN')
    assert M.RUNONLY_MARK in decks[k] and not re.search(r'COBOL\((PACMAIN|PACGAME|PACSCR)\)', decks[k]), k
    assert not re.search(r'//SYSLMOD\s+DD\s+DSN=\S+\(PACMAIN\)', decks[k]), k       # never relinks the release
del os.environ['PACMAN_RUNONLY']
for k, t in decks.items():
    e = audit_deck(t, ARGS.prefix)
    assert not e, (k, e[:5])
print('G8 local checks PASS: final CLIST defaults', ' '.join(f'{k}({v})' for k, v in FINAL.items()),
      f'; sources = {BASE}; core frozen; REL20 = S2 module set; R20 decks audited ({len(decks)})')


# 2. listings ------------------------------------------------------------------------------------------------------
def read(path):
    return Path(path).read_text(errors='replace')


def audited(path):
    text = read(path)
    e = audit_listing(text, ARGS.prefix)
    assert not e, (path, e[:5])
    return text


def run_test(script, listings, renames=()):
    tmp = []
    for i, p in enumerate(listings):
        text = read(p)
        if i < len(renames) and renames[i]:
            text = text.replace(ARGS.load, renames[i])
        elif ARGS.load != 'PACMAIN':
            text = text.replace(ARGS.load, 'PACMAIN')
        f = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
        f.write(text)
        f.close()
        tmp.append(f.name)
    r = subprocess.run([sys.executable, str(R / 'tests' / script)] + tmp, capture_output=True, text=True,
                       env=dict(os.environ, PACMAN_RUNONLY='1', PACMAN_LATER_PHASE='G8',
                                PACMAN_PREFIX=ARGS.prefix))
    assert r.returncode == 0, (script, r.stdout[-3000:], r.stderr[-3000:])
    return r.stdout.strip().splitlines()[-1]


if ARGS.rel20:
    text = audited(ARGS.rel20).replace(ARGS.load, 'PACMAIN')
    ls = text.splitlines()
    rcs = re.findall(r'PACREL20\s+(\w+)\s+(\S+)\s+RC= (\d{4})', text)
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', M.build('REL20', ARGS.prefix), re.M))
    assert len(rcs) == nsteps and all(rc == '0000' for *_, rc in rcs), (nsteps, len(rcs), [x for x in rcs if x[2] != '0000'])
    assert not [l for l in ls if re.search(r'IKF\d{4}I-[WCE]', l)], 'compiler warnings'
    got = [m.group(1) for m in (re.match(r'G8PARM=(.*)=\s*$', l) for l in ls) if m]
    assert got == G8_WANT, (got, G8_WANT)
    # the 1.0-MVS oracle: test_mvs8 on the 1.0 steps only (3 copies, 7 sources / compiles, the link, the runs)
    keep = re.compile(r'(CPY[1-3]|SRC[1-7]|COB[1-7]|LINK|RUN\d+|TSO\d+)$')
    out = [l for l in ls if not ((m := re.search(r'PACREL20\s+(\w+)\s+\S+\s+RC= ', l)) and not keep.match(m.group(1)))]
    f = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
    f.write('\n'.join(out) + '\n')
    f.close()
    r = subprocess.run([sys.executable, str(R / 'tests/test_mvs8.py'), f.name], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    print('REL20 PASS:', len(rcs), 'steps RC 0000, no warnings; CLIST PARMs', got, ';', r.stdout.strip().splitlines()[-1])

for opt in ('s2', 'rp', 'gp2', 'gp23', 'hs'):
    if getattr(ARGS, opt):
        t = audited(getattr(ARGS, opt))
        assert f'{M.RUNONLY_MARK} {ARGS.prefix}.LOAD({ARGS.load})' in t, opt
if ARGS.s2:
    print('S2 run-only:', run_test('test_s2.py', [ARGS.s2], ['PACS2D']))
if ARGS.rp:
    print('RP run-only:', run_test('test_rp.py', [ARGS.rp], ['PACRPD']))
if ARGS.hs and ARGS.gp23 and ARGS.gp2:
    print('HS + GP23 + GP2 run-only:', run_test('test_hs.py', [ARGS.hs, ARGS.gp23, ARGS.gp2]))


def oracle_blocks(ls):
    out, i = [], 0
    while i < len(ls):
        if ls[i] == 'PACMAN MVS-6 SMART GHOSTS':
            j = next(k for k in range(i, len(ls)) if ls[k].startswith('LIVES '))
            out.append([l.rstrip() for l in ls[i:j + 1]])
            i = j
        i += 1
    return out


if ARGS.oracle:
    assert ARGS.rel20, '--oracle needs --rel20'
    t = audited(ARGS.oracle)
    assert f'{M.RUNONLY_MARK} {ARGS.prefix}.LOAD({ARGS.load})' in t
    os.environ['PACMAN_RUNONLY'] = '1'
    nsteps = len(re.findall(r'^//\w+\s+EXEC PGM=', M.build('RELEASE', ARGS.prefix), re.M))
    del os.environ['PACMAN_RUNONLY']
    rcs = re.findall(r'PACREL10\s+(\w+)\s+(\S+)\s+RC= (\d{4})', t)
    assert len(rcs) == nsteps and all(rc == '0000' for *_, rc in rcs), (nsteps, rcs)
    a, b = oracle_blocks(t.splitlines()), oracle_blocks(read(ARGS.rel20).splitlines())
    assert len(a) == 25 and a == b, (len(a), len(b))
    print('installed oracle PASS:', len(rcs), 'steps RC 0000;', len(a), '1.0-MVS blocks = the REL20 runs of the release')

if ARGS.clist:
    t = audited(ARGS.clist)
    rcs = re.findall(r'PACCLS10\s+(\w+)\s+(\S+)\s+RC= (\d{4})', t)
    assert [(n, rc) for n, _, rc in rcs] == [('STORE', '0000'), ('PRINT', '0000')], rcs
    want = M.clist_text(ARGS.prefix).splitlines()
    ls = [l.rstrip() for l in t.splitlines()]
    w = [x.rstrip() for x in want]       # in-stream data is not echoed: the only copy is the PRINT output
    assert sum(ls[i:i + len(w)] == w for i in range(len(ls))) == 1, 'printed CLIST member differs'
    assert dict(re.findall(r'(\w+)\((\w*)\)', ' '.join(want[:4]))) == FINAL
    print('CLIST PASS: member printed back =', len(want), 'lines of src/clist/PACMAN.clist for', ARGS.prefix)


def zap_dumps(ls):
    """The two AMASPZAP DUMP outputs after the marker: per dump, the CSECT names and hex rows (disk addresses and
    page headings dropped)."""
    start = next(i for i, l in enumerate(ls) if M.INST_MARK in l)     # may follow IEB147I on one line
    dumps, cur = [], None
    for l in ls[start:]:
        if 'DUMP PACMAIN ALL' in l:
            cur = []
            dumps.append(cur)
        elif cur is not None:
            m = re.search(r'RECORD LENGTH- *(\S+) .*CSECT NAME-? *(\S+)', l)
            if m:
                cur.append(f'CSECT {m.group(2)} LEN {m.group(1)}')
            m = re.match(r'\s*([0-9A-F]{4,6})\s+((?:[0-9A-F]{8}\s+)*[0-9A-F]{8})\s', l + ' ')
            if m:
                cur.append(m.group(1) + ' ' + ' '.join(m.group(2).split()))
    return dumps


if ARGS.inst:
    t = read(ARGS.inst)
    rcs = re.findall(r'PACINS20\s+(\w+)\s+(\S+)\s+RC= (\d{4})', t)
    assert [(n, rc) for n, _, rc in rcs] == [('COPY', '0000'), ('MARK', '0000'), ('ZAPSRC', '0000'),
                                              ('ZAPINST', '0000')], rcs
    assert re.search(r'PACMAIN\s+HAS BEEN SUCCESSFULLY\s+COPIED', t) and 'IEB154I' in t, 'IEBCOPY message'
    d = zap_dumps(t.splitlines())
    assert len(d) == 2 and d[0] and d[0] == d[1], [len(x) for x in d]
    cs = [x for x in d[0] if x.startswith('CSECT ')]
    print('INST20 PASS: IEBCOPY replaced PACMAIN; AMASPZAP dumps identical:', len(cs), 'CSECTs,', len(d[0]) - len(cs),
          'hex rows')
