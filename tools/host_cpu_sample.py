#!/usr/bin/env python3
"""MVS-RT probe E14: host CPU of the Hercules process(es), from the cumulative CPU time (ps -o time) sampled every
--interval seconds: one line per sample 'epoch_ms pid cpu_pct' (100 = one host core). Stop with Ctrl-C or --seconds.
Usage: host_cpu_sample.py --out FILE [--interval 1] [--seconds 900]"""
import argparse
import subprocess
import time


def cpu_seconds(pid):
    out = subprocess.run(['ps', '-o', 'time=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
    if not out:
        return None
    parts = out.replace('-', ':').split(':')
    sec = 0.0
    for p in parts:
        sec = sec * 60 + float(p)
    return sec


ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--interval', type=float, default=1.0)
ap.add_argument('--seconds', type=float, default=900)
a = ap.parse_args()
pids = [int(p) for p in subprocess.run(['pgrep', 'hercules'], capture_output=True, text=True).stdout.split()]
prev = {p: (time.time(), cpu_seconds(p)) for p in pids}
end = time.time() + a.seconds
with open(a.out, 'w') as f:
    while time.time() < end:
        time.sleep(a.interval)
        for p in pids:
            now, c = time.time(), cpu_seconds(p)
            t0, c0 = prev[p]
            if c is not None and c0 is not None:
                f.write(f'{int(now * 1000)} {p} {100 * (c - c0) / (now - t0):.1f}\n')
                f.flush()
            prev[p] = (now, c)
