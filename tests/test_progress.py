#!/usr/bin/env python3
"""tools/progress.py (reporting only): output, log and exit status of the wrapped command unchanged; milestones only
from the explicit pattern; no percentage without a measured total, no ETA without a measured history; reporting
failures never mask the command's result; stage / show. Small fake commands only (a few seconds)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tools'))
import progress as P  # noqa: E402

PY = sys.executable
TOOL = str(R / 'tools/progress.py')
CHILD = r'''
import sys, time
sys.stdout.write("start\n"); sys.stdout.flush()
for i in range(int(sys.argv[1])):
    time.sleep(0.05)
    print(f"section {i}: PASS", flush=True)
    print("noise line", flush=True)
sys.stderr.write("warning on stderr\n")
sys.stdout.buffer.write(b"\xc3\xa9 non-ascii \xff raw bytes\n")
sys.exit(int(sys.argv[2]))
'''


def child_direct(t, n, rc):
    f = Path(t) / 'child.py'
    f.write_text(CHILD)
    return subprocess.run([PY, str(f), str(n), str(rc)], capture_output=True)


def wrapped(t, n, rc, *opts, log='run.log'):
    f = Path(t) / 'child.py'
    f.write_text(CHILD)
    lg = Path(t) / log
    r = subprocess.run([PY, TOOL, 'run', '--label', 'fake suite', '--log', str(lg), '--every', '0.1', *opts, '--',
                        PY, str(f), str(n), str(rc)], capture_output=True)
    st = json.loads(Path(str(lg) + '.status.json').read_text())
    return r, lg.read_bytes(), st


with tempfile.TemporaryDirectory() as t:
    hist_real = P.HISTORY
    P.HISTORY = Path(t) / 'history'                       # the module under test, for render / eta units
    # 1. output, log and exit status unchanged; stderr not polluted by progress lines (not a terminal)
    d = child_direct(t, 3, 0)
    r, log, st = wrapped(t, 3, 0, '--milestone', r'\bPASS\b')
    assert r.returncode == 0 and r.stdout == d.stdout and r.stderr == d.stderr, (r.stderr, d.stderr)
    assert sorted(log.splitlines()) == sorted((d.stdout + d.stderr).splitlines())
    assert b'\xff raw bytes' in log and b'%' not in r.stderr
    for rc in (1, 3):
        d = child_direct(t, 2, rc)
        r, log, st = wrapped(t, 2, rc, '--milestone', r'\bPASS\b', log=f'fail{rc}.log')
        assert r.returncode == rc and r.stdout == d.stdout and st['status'] == 'FAIL' and st['rc'] == rc
    # 2. milestones = only the explicit pattern (not "start", "noise line", stderr); none without a pattern
    r, log, st = wrapped(t, 4, 0, '--milestone', r'\bPASS\b', log='m.log')
    assert st['done'] == 4 and st['last'] == 'section 3: PASS' and st['status'] == 'PASS'
    r, log, st = wrapped(t, 4, 0, log='nopattern.log')
    assert st['done'] == 0 and st['total'] is None
    r, log, st = wrapped(t, 2, 0, '--profile', 'zos-tools', log='profile.log')
    assert st['done'] == 2
    # 3. no total -> no percentage; total only from a previous log's milestones (measured), never from line counts
    st_run = dict(st, status='RUNNING', started=0.0, total=None, done=2, eta=None)
    line = P.render(st_run, now=10.0)
    assert '%' not in line and 'total unknown' in line and 'ETA unknown' in line
    prev = Path(t) / 'm.log'
    r, log, st = wrapped(t, 2, 0, '--milestone', r'\bPASS\b', '--total-from', str(prev), log='tf.log')
    assert st['total'] == 4 and st['done'] == 2
    assert '50% 2/4' in P.render(dict(st, status='RUNNING', started=0.0), now=5.0)
    # a measured total that is exceeded is dropped (no percentage above 100 / no invented total)
    r, log, st = wrapped(t, 6, 0, '--milestone', r'\bPASS\b', '--total-from', str(prev), log='over.log')
    assert st['done'] == 6 and st['total'] is None
    # 4. ETA only with a measured history of a successful run; a failed run writes no history
    r, log, st = wrapped(t, 3, 0, '--milestone', r'\bPASS\b', '--history', 'k', log='h1.log')
    assert st['eta'] is None
    hist = json.loads((R / 'build/progress/history/k.json').read_text())
    assert hist['total'] == 3 and len(hist['marks']) == 3 and hist['duration'] > 0
    assert P.eta_of(hist, 1, hist['marks'][0]) is not None and P.eta_of(None, 1, 1.0) is None
    assert P.eta_of(hist, 3, hist['duration'] * 2) is None or P.eta_of(hist, 3, hist['duration'] * 2) >= 0
    r, log, st = wrapped(t, 3, 0, '--milestone', r'\bPASS\b', '--history', 'k', log='h2.log')
    assert st['total'] == 3 and st['status'] == 'PASS'
    (R / 'build/progress/history/k.json').unlink()
    r, log, st = wrapped(t, 3, 2, '--milestone', r'\bPASS\b', '--history', 'kf', log='hf.log')
    assert r.returncode == 2 and not (R / 'build/progress/history/kf.json').exists()
    # 5. a reporting failure cannot mask the command: the status path is a directory (unwritable as a file)
    bad = Path(t) / 'blocked.log'
    Path(str(bad) + '.status.json').mkdir()
    f = Path(t) / 'child.py'
    d = child_direct(t, 2, 4)
    r = subprocess.run([PY, TOOL, 'run', '--label', 'x', '--log', str(bad), '--every', '0.1', '--milestone', 'PASS',
                        '--', PY, str(f), '2', '4'], capture_output=True)
    assert r.returncode == 4 and r.stdout == d.stdout and bad.read_bytes()
    # the wrapper's own failure to start is 125, never a fake success
    r = subprocess.run([PY, TOOL, 'run', '--label', 'x', '--log', str(Path(t) / 'nx.log'), '--',
                        str(Path(t) / 'no-such-command')], capture_output=True)
    assert r.returncode == 125
    # 6. stage (indeterminate) and show
    sf = Path(t) / 'case.status.json'
    for s in ('precheck', 'trace', 'driver'):
        assert P.main(['stage', '--status', str(sf), '--label', 'ZOS-8 E1', s]) == 0
    st = json.loads(sf.read_text())
    assert st['phase'] == 'driver' and [x['stage'] for x in st['stages']] == ['precheck', 'trace', 'driver']
    assert st['total'] is None and '%' not in P.render(st)
    P.main(['stage', '--status', str(sf), '--label', 'ZOS-8 E1', '--state', 'FAIL', 'checker'])
    out = subprocess.run([PY, TOOL, 'show', str(sf)], capture_output=True, text=True).stdout
    assert out.startswith('[') and 'FAIL' in out and '[checker]' in out and '%' not in out
    out = subprocess.run([PY, TOOL, 'show', '--follow', str(Path(t) / 'm.log.status.json')], capture_output=True,
                         text=True, timeout=10).stdout
    assert 'PASS' in out and out.count('\n') == 1                 # --follow ends at a final status
    P.HISTORY = hist_real
print('progress.py: output / log / exit status unchanged, milestones only from the pattern, no percentage without a '
      'measured total, no ETA without a measured history, reporting failures never mask the command, stage / show: '
      'PASS')
