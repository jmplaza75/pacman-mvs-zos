#!/usr/bin/env python3
"""MVS-RT probe E14: statistics from an E14 log (job listing or printed dataset; lines 'E14 START', 'SEG', 'Q', 'A').
Per segment: actual period (wake-to-wake) min/avg/p95/max, p95 relative error, wake lateness, every overrun (busy >
period or a skipped deadline; wake lateness > 10% of the period is reported separately as timer jitter) with run lengths (isolated spike vs sustained), busy time
split (poll / move / compose / send), bytes, TPUT RC, frame kinds, and every AID in the exact order MVS received it.
Usage: rt_e14_report.py LOG [--json OUT]"""
import argparse
import json
import re
from collections import Counter

AIDS = {'F7': 'PF7', 'F8': 'PF8', '7A': 'PF10', '7B': 'PF11', '7D': 'ENTER', '6E': 'PA2', '6D': 'CLEAR', 'F3': 'PF3',
        '6C': 'PA1', 'F1': 'PF1', 'F2': 'PF2', 'F4': 'PF4', 'F5': 'PF5', 'F6': 'PF6', 'F9': 'PF9', '7C': 'PF12'}


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))] if v else 0


def parse(path):
    segs, head, cur = [], None, None
    for line in open(path, errors='replace'):
        line = line.rstrip('\n')
        m = re.search(r'(E14 START.*)', line)
        if m and head is None:
            head = m.group(1).strip()
        m = re.match(r'^\s*SEG (\S) P=(\d+) N=(\d+) AIDS=(\d+) LOST=(\d+) MODE=(\S+) ABORT=(\d)', line)
        if m:
            cur = dict(id=m.group(1), p=int(m.group(2)), n=int(m.group(3)), aids=int(m.group(4)),
                       lost=int(m.group(5)), mode=m.group(6), abort=int(m.group(7)), q=[], a=[])
            segs.append(cur)
            continue
        m = re.match(r'^\s*Q (\S) (\d{4}) +(-?\d+) *(-?\d+) *(-?\d+) *(-?\d+) *(-?\d+) *(-?\d+) (\d{4}) *(-?\d+) (\S)(\d) *(-?\d+)', line)
        if m and cur:
            g = m.groups()
            cur['q'].append(dict(q=int(g[1]), wake=int(g[2]), late=int(g[3]), poll=int(g[4]), move=int(g[5]),
                                 comp=int(g[6]), send=int(g[7]), bytes=int(g[8]), rc=int(g[9]), kind=g[10],
                                 naid=int(g[11]), skip=int(g[12])))
            continue
        m = re.match(r'^\s*A (\S) (\d{4}) +(-?\d+) AID=(..) LEN=(\d{4}) SEQ=(\d) RC= *(-?\d+) CH=(.?)', line)
        if m and cur:
            g = m.groups()
            cur['a'].append(dict(q=int(g[1]), t=int(g[2]), aid=g[3], name=AIDS.get(g[3], '?' + g[3]),
                                 len=int(g[4]), seq=int(g[5]), rc=int(g[6]), ch=g[7]))
    return head, segs


def runs(flags):
    out, n = [], 0
    for f in flags + [False]:
        if f:
            n += 1
        elif n:
            out.append(n)
            n = 0
    return out


def seg_stats(s):
    q = s['q']
    P = s['p'] * 1000
    per = [b['wake'] - a['wake'] for a, b in zip(q, q[1:])]
    busy = [x['poll'] + x['move'] + x['comp'] + x['send'] for x in q]
    st = dict(id=s['id'], p_ms=s['p'], quanta=len(q), aids=s['aids'], aids_lost=s['lost'], abort=s['abort'])
    if per and P:
        err = [abs(x - P) / P for x in per]
        late = [x['late'] for x in q]
        over = [b > P or x['skip'] > 0 for x, b in zip(q, busy)]
        jit = [x['late'] > P / 10 for x in q]
        st.update(period_min=min(per), period_avg=round(sum(per) / len(per)), period_p95=pct(per, 95),
                  period_max=max(per), err_p95_pct=round(100 * pct(err, 95), 1), late_p95=pct(late, 95),
                  late_max=max(late), skipped=sum(x['skip'] for x in q), overruns=sum(over),
                  overrun_runs=runs(over), overrun_at=[x['q'] for x, o in zip(q, over) if o][:40],
                  late_gt10pct=sum(jit), late_gt10pct_runs=runs(jit),
                  late_ms_hist=dict(sorted(Counter(x['late'] // 1000 for x in q).items())))
    st.update(busy_avg=round(sum(busy) / len(busy)) if busy else 0, busy_p95=pct(busy, 95), busy_max=max(busy, default=0),
              comp_avg=round(sum(x['comp'] for x in q) / len(q)) if q else 0, comp_max=max((x['comp'] for x in q), default=0),
              send_avg=round(sum(x['send'] for x in q) / len(q)) if q else 0, send_max=max((x['send'] for x in q), default=0),
              move_max=max((x['move'] for x in q), default=0), poll_max=max((x['poll'] for x in q), default=0),
              bytes_avg=round(sum(x['bytes'] for x in q) / len(q)) if q else 0, bytes_max=max((x['bytes'] for x in q), default=0),
              rc=dict(Counter(x['rc'] for x in q)), kinds=dict(Counter(x['kind'] for x in q)),
              multi_aid_quanta=sum(1 for x in q if x['naid'] > 1))
    if s['id'] in 'GIK':
        for k in ('F', 'P'):
            c = [x['comp'] for x in q if x['kind'] == k]
            if c:
                st[f'comp_{k}_avg'] = round(sum(c) / len(c))
                st[f'comp_{k}_max'] = max(c)
                st[f'bytes_{k}_max'] = max(x['bytes'] for x in q if x['kind'] == k)
    st['aid_order'] = [f"q{a['q']}.{a['seq']}:{a['name']}{'/' + a['ch'] if a['ch'].strip() else ''}"
                       + (f" rc{a['rc']}" if a['rc'] else '') for a in s['a']]
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('log')
    ap.add_argument('--json')
    a = ap.parse_args()
    head, segs = parse(a.log)
    print(head)
    out = []
    for s in segs:
        st = seg_stats(s)
        out.append(st)
        keys = [k for k in st if k not in ('aid_order',)]
        print(f"SEG {st['id']} P={st['p_ms']}ms: " + ' '.join(f'{k}={st[k]}' for k in keys[2:]))
        if st['aid_order']:
            print('   AIDS: ' + ' '.join(st['aid_order']))
    if a.json:
        json.dump(dict(head=head, segments=out), open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
