#!/usr/bin/env python3
"""MVS-RT probe E14: terminal-side timeline from a c3270 -trace file, starting at the first host record that contains
the EBCDIC text 'E14 ' (the probe's first synthetic frame) - nothing of the logon is read before that point, and
inbound records are shown ONLY by their AID byte (no typed data).
Prints: output records (time, length, command, WCC), inter-arrival statistics per window, bursts (records < 20 ms
apart), every key event (keymap / typeahead / script), the AID on the wire, keyboard lock/unlock with cause, and
per AID: key -> wire, wire -> unlock (lock time).
Usage: c3270_rt_trace.py TRACE [--from HHMMSS.mmm] [--to HHMMSS.mmm] [--events] [--json OUT]"""
import argparse
import json
import re

E14 = 'E14 '.encode('cp037')
AIDN = {0xF7: 'PF7', 0xF8: 'PF8', 0x7A: 'PF10', 0x7B: 'PF11', 0x7D: 'ENTER', 0x6E: 'PA2', 0x6D: 'CLEAR', 0xF3: 'PF3',
        0x6C: 'PA1', 0xF1: 'PF1', 0x88: 'SF(QueryReply)'}


def ms(ts):
    h, m, s = int(ts[0:2]), int(ts[2:4]), float(ts[4:])
    return round((h * 3600 + m * 60 + s) * 1000)


def load(path):
    ev, cur, d, ts, start_ts = [], None, None, None, None
    for line in open(path, errors='replace'):
        m = re.match(r'^(?:< \S+)?(\d{8})\.(\d{6})\.(\d{3}) (\S+)\s+(.*)$', line)
        if m:
            ts = m.group(2) + '.' + m.group(3)
            cat, txt = m.group(4), m.group(5)
            if cat == 'kybd' and txt.startswith('Keyboard'):
                ev.append(('kb', ts, txt))
            elif cat == 'ui' and ' -> ' in txt:
                ev.append(('key', ts, txt.split(' -> ', 1)[1]))
            elif cat == 'infra' and txt.startswith('typeahead ->'):
                ev.append(('ta', ts, txt))
        m = re.match(r'^([<>]) 0x([0-9a-f]+)\s+([0-9a-f]+)', line)
        if m:
            if int(m.group(2), 16) == 0:
                if cur is not None:
                    ev.append((d, start_ts, bytes(cur)))
                cur, d, start_ts = bytearray(), m.group(1), ts
            cur += bytes.fromhex(m.group(3))
            continue
        if cur is not None:
            ev.append((d, start_ts, bytes(cur)))
            cur = None
    if cur is not None:
        ev.append((d, start_ts, bytes(cur)))
    return ev


def stats(v):
    v = sorted(v)
    if not v:
        return {}
    return dict(n=len(v), min=v[0], avg=round(sum(v) / len(v), 1), p95=v[min(len(v) - 1, int(round(.95 * (len(v) - 1))))],
                max=v[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('trace')
    ap.add_argument('--from', dest='frm')
    ap.add_argument('--to')
    ap.add_argument('--events', action='store_true')
    ap.add_argument('--json')
    a = ap.parse_args()
    ev = load(a.trace)
    i0 = next(i for i, e in enumerate(ev) if e[0] == '<' and E14 in e[2])
    ev = [e for e in ev[i0:] if e[1]]
    if a.frm:
        ev = [e for e in ev if ms(e[1]) >= ms(a.frm)]
    if a.to:
        ev = [e for e in ev if ms(e[1]) <= ms(a.to)]
    outs = [(ms(t), b) for k, t, b in ev if k == '<']
    gaps = [b[0] - a_[0] for a_, b in zip(outs, outs[1:])]
    bursts = sum(1 for g in gaps if g < 20)
    rows, pend, aids = [], None, []
    for k, t, x in ev:
        if k == '<':
            b = x[:-2] if x.endswith(b'\xff\xef') else x
            txt = b.decode('cp037', 'replace')
            tag = txt[txt.find('E14 '):txt.find('E14 ') + 18] if E14 in b else ''
            rows.append(f'{t} OUT len {len(b):4} cmd {b[0]:02X} wcc {b[1] if len(b) > 1 else 0:02X} {tag}')
        elif k == '>':
            b = x[:-2] if x.endswith(b'\xff\xef') else x
            name = AIDN.get(b[0], f'{b[0]:02X}') if b else '?'
            rows.append(f'{t} IN  AID={name}')
            aids.append(dict(wire=ms(t), aid=name, key=pend[0] if pend else None, how=pend[1] if pend else None))
            pend = None
        elif k in ('key', 'ta'):
            rows.append(f'{t} {k.upper():3} {x}')
            pend = (ms(t), k)
        elif k == 'kb':
            rows.append(f'{t} KB  {x}')
            if x.startswith('Keyboard unlock') and aids and 'unlock' not in aids[-1] and '-OIA_LOCKED' in x:
                aids[-1]['unlock'] = ms(t)
                aids[-1]['cause'] = x.split('(')[1].split(')')[0]
    lock = [x['unlock'] - x['wire'] for x in aids if 'unlock' in x]
    k2w = [x['wire'] - x['key'] for x in aids if x['key'] is not None]
    res = dict(out_records=len(outs), out_gap_ms=stats(gaps), bursts_lt20ms=bursts, aids=len(aids),
               aid_lock_ms=stats(lock), key_to_wire_ms=stats(k2w),
               aid_sequence=[f"{x['aid']}{'(ta)' if x['how'] == 'ta' else ''}" for x in aids],
               typeahead_sends=sum(1 for x in aids if x['how'] == 'ta'))
    if a.events:
        print('\n'.join(rows))
    for k, v in res.items():
        print(f'{k}: {v}')
    if a.json:
        json.dump(dict(summary=res, aids=aids), open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
