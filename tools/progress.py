#!/usr/bin/env python3
"""Lightweight progress reporting for long project tasks (standard library only). It only reports: it never changes
what a command does, prints or returns, and it never decides, stops or retries anything.

  progress.py run --label L --log LOG [--milestone REGEX | --profile NAME] [--total-from PREV_LOG] [--history KEY]
                  [--every S] [--quiet] -- CMD [ARGS...]
      Runs CMD unchanged (PYTHONUNBUFFERED=1 so Python children print as they go). Its stdout / stderr go to this
      process's stdout / stderr unchanged, and both, byte for byte in arrival order, to LOG. The exit status is CMD's.
      Milestones = only the output lines that match REGEX (or the profile's), never arbitrary lines. The total is known
      only from measurement: the KEY history of the last successful run, else the matches in PREV_LOG; otherwise the
      progress is indeterminate (no percentage). The ETA exists only with a KEY history (measured durations).
      Status: LOG.status.json (label, phase, status RUNNING / PASS / FAIL, done / total, elapsed, eta, last milestone);
      a progress line on stderr every S seconds (default 45) and at every milestone, only when stderr is a terminal
      and not --quiet (so redirected logs never get progress lines). Reporting errors are swallowed: they can never
      change CMD's output or exit status. The history is written only after an exit status 0.
  progress.py stage --status FILE --label L STAGE [--state RUNNING|PASS|FAIL]
      For scripted multi-step work (e.g. a z/OS case: precheck, trace, driver, checker, evidence): records the current
      stage and its start; indeterminate (no percentage, no ETA).
  progress.py show [--follow] STATUS_FILE
      Prints the progress line of a status file (--follow: every 2 s until it is no longer RUNNING).
Profiles: zos-tools = tests/test_zos_tools.py, whose every section ends with one summary line containing PASS.
Exit status of `run` when the wrapper cannot start CMD at all: 125.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

R = Path(__file__).resolve().parent.parent
HISTORY = R / 'build/progress/history'
PROFILES = {'zos-tools': r'\bPASS\b'}
BAR = 20


def fmt(sec):
    if sec is None:
        return None
    sec = int(round(sec))
    return f'{sec // 3600}:{sec // 60 % 60:02d}:{sec % 60:02d}' if sec >= 3600 else f'{sec // 60}:{sec % 60:02d}'


def render(st, now=None):
    """One progress line from a status dict (never a percentage without a measured total)."""
    now = now or time.time()
    el = st.get('elapsed') if st.get('status') != 'RUNNING' else now - st['started']
    head = f'{st.get("status", "?")} — {st.get("label", "")}' + (f' [{st["phase"]}]' if st.get('phase') else '')
    done, total = st.get('done', 0), st.get('total')
    if total:
        frac = min(done / total, 1.0)
        bar = '[' + '█' * int(frac * BAR) + '░' * (BAR - int(frac * BAR)) + f'] {int(frac * 100):3d}% {done}/{total}'
    else:
        bar = '[' + '-\\|/'[int(now) % 4] + f'] {done} milestone(s), total unknown' if st.get('status') == 'RUNNING' \
            else f'[{done} milestone(s)]'
    eta = f', ~{fmt(st["eta"])} left' if st.get('eta') is not None and st.get('status') == 'RUNNING' else \
        (', ETA unknown' if st.get('status') == 'RUNNING' else '')
    rc = f' rc {st["rc"]}' if st.get('rc') is not None else ''
    last = f' — {st["last"][:70]}' if st.get('last') else ''
    return f'{bar} {head}{rc} — {fmt(el)} elapsed{eta}{last}'


def write_status(path, st):
    try:
        tmp = Path(str(path) + '.tmp')
        tmp.write_text(json.dumps(st))
        os.replace(tmp, path)
    except Exception:                                      # reporting must never affect the command
        pass


def load_history(key):
    try:
        return json.loads((HISTORY / f'{key}.json').read_text()) if key else None
    except Exception:
        return None


def eta_of(hist, done, elapsed):
    """Remaining seconds from the measured milestone times of the last successful run, scaled by the current pace;
    None without a history or past its end."""
    if not hist or not hist.get('marks'):
        return None
    marks, dur = hist['marks'], hist['duration']
    if done == 0:
        rem = dur - elapsed
    elif done <= len(marks) and marks[done - 1] > 0:
        rem = (dur - marks[done - 1]) * (elapsed / marks[done - 1])
    else:
        return None
    return rem if rem > 0 else None


def run(a):
    rx = re.compile(PROFILES[a.profile] if a.profile else a.milestone) if (a.profile or a.milestone) else None
    hist = load_history(a.history)
    total = None
    if hist and hist.get('total'):
        total = hist['total']
    elif a.total_from and rx:
        try:
            total = sum(1 for l in Path(a.total_from).read_text(errors='replace').splitlines() if rx.search(l)) or None
        except Exception:
            total = None
    status_path = Path(str(a.log) + '.status.json')
    t0 = time.time()
    st = {'label': a.label, 'phase': a.phase, 'status': 'RUNNING', 'started': t0, 'done': 0, 'total': total,
          'eta': eta_of(hist, 0, 0.0), 'last': None, 'rc': None, 'cmd': a.cmd}
    marks, lock = [], threading.Lock()
    tty = sys.stderr.isatty() and not a.quiet
    try:
        log = open(a.log, 'wb')
    except Exception as ex:
        print(f'progress.py: cannot open the log {a.log}: {ex}', file=sys.stderr)
        return 125
    env = dict(os.environ, PYTHONUNBUFFERED='1')
    try:
        p = subprocess.Popen(a.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    except Exception as ex:
        log.close()
        print(f'progress.py: cannot start {a.cmd}: {ex}', file=sys.stderr)
        return 125
    write_status(status_path, st)

    def show():
        if tty:
            try:
                sys.stderr.write(render(st) + '\n')
                sys.stderr.flush()
            except Exception:
                pass

    def pump(src, dst, is_out):
        for raw in iter(src.readline, b''):
            with lock:
                log.write(raw)
                log.flush()
                dst.write(raw)
                dst.flush()
            try:
                line = raw.decode('utf-8', 'replace').rstrip('\n')
                if is_out and rx and rx.search(line):
                    with lock:
                        el = time.time() - t0
                        marks.append(el)
                        st.update(done=len(marks), last=line.strip(), eta=eta_of(hist, len(marks), el))
                        if st['total'] is not None and st['done'] > st['total']:
                            st['total'] = None                   # the measured total no longer holds: no percentage
                    write_status(status_path, st)
                    show()
            except Exception:
                pass
    th = [threading.Thread(target=pump, args=(p.stdout, sys.stdout.buffer, True), daemon=True),
          threading.Thread(target=pump, args=(p.stderr, sys.stderr.buffer, False), daemon=True)]
    for x in th:
        x.start()
    nxt = t0 + a.every
    while p.poll() is None:
        time.sleep(min(0.5, a.every))
        if time.time() >= nxt:
            nxt += a.every
            try:
                with lock:
                    st['eta'] = eta_of(hist, st['done'], time.time() - t0)
                write_status(status_path, st)
                show()
            except Exception:
                pass
    for x in th:
        x.join()
    rc = p.returncode
    log.close()
    el = time.time() - t0
    st.update(status='PASS' if rc == 0 else 'FAIL', rc=rc, elapsed=el, eta=None)
    write_status(status_path, st)
    show()
    if rc == 0 and a.history and rx:
        try:
            HISTORY.mkdir(parents=True, exist_ok=True)
            (HISTORY / f'{a.history}.json').write_text(json.dumps({'total': len(marks) or None, 'marks': marks,
                                                                   'duration': el, 'label': a.label}))
        except Exception:
            pass
    return rc


def stage(a):
    p = Path(a.status)
    try:
        st = json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        st = {}
    now = time.time()
    st.setdefault('started', now)
    st.update(label=a.label, phase=a.stage, status=a.state, done=len(st.get('stages', [])) + 1, total=None, eta=None,
              last=f'stage {a.stage}', rc=None)
    st.setdefault('stages', []).append({'stage': a.stage, 'at': now, 'state': a.state})
    if a.state != 'RUNNING':
        st['elapsed'] = now - st['started']
    write_status(p, st)
    return 0


def show_cmd(a):
    p = Path(a.status)
    while True:
        try:
            st = json.loads(p.read_text())
        except Exception as ex:
            print(f'progress.py: no readable status in {p}: {ex}')
            return 1
        print(render(st), flush=True)
        if not a.follow or st.get('status') != 'RUNNING':
            return 0
        time.sleep(2)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='op', required=True)
    r = sub.add_parser('run')
    r.add_argument('--label', required=True)
    r.add_argument('--log', required=True)
    r.add_argument('--phase')
    g = r.add_mutually_exclusive_group()
    g.add_argument('--milestone', help='regular expression: the output lines that are milestones')
    g.add_argument('--profile', choices=sorted(PROFILES))
    r.add_argument('--total-from', help='a previous complete log of the same command (its milestones = the total)')
    r.add_argument('--history', help='key of the measured milestone history (enables the ETA)')
    r.add_argument('--every', type=float, default=45.0)
    r.add_argument('--quiet', action='store_true')
    r.add_argument('cmd', nargs=argparse.REMAINDER)
    s = sub.add_parser('stage')
    s.add_argument('--status', required=True)
    s.add_argument('--label', required=True)
    s.add_argument('--state', default='RUNNING', choices=['RUNNING', 'PASS', 'FAIL'])
    s.add_argument('stage')
    w = sub.add_parser('show')
    w.add_argument('--follow', action='store_true')
    w.add_argument('status')
    a = ap.parse_args(argv)
    if a.op == 'run':
        if a.cmd[:1] == ['--']:
            a.cmd = a.cmd[1:]
        if not a.cmd:
            ap.error('run: no command after --')
        return run(a)
    return stage(a) if a.op == 'stage' else show_cmd(a)


if __name__ == '__main__':
    sys.exit(main())
