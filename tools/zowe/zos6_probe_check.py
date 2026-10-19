#!/usr/bin/env python3
"""ZOS-6 protocol probe analyzer (docs/zos6-protocol-probe.md). Local, read-only, DIAGNOSTIC: no acceptance verdict.

Usage: zos6_probe_check.py --mode P0|PT|PN|PH|PB4|PR2|PR2I --trace TRACE --drive-log LOG

Telnet framing with the ZOS-5 reader (blocks / telnet, unchanged); every TN3270E header is then only DECODED and counted
(an inventory: SIGNAL, unknown DATA-TYPEs or flags are reported, never rejected). The probe window runs from the probe
screen (`PACZ6P ZOS-6 PROTOCOL PROBE`) to its first summary line (`PACZ6P MODE`). Reported:
- frames (host 3270-DATA `F1 C2` + `QUANTUM nnnn`): count, quantum sequence (order / loss), SDI (REQUEST-FLAG 01) and
  KRI (02) per frame; empty 3270-DATA controls by REQUEST-FLAG; BIDs, SIGNAL BIDs (04), the record after each SDI;
  RESPONSEs positive / negative; other records;
- send-state: the c3270 keyboard lock / unlock lines inside the window (windows, durations, longest lock);
- terminal arrival cadence of the frames (gaps, mean) and the lag of frame q behind first + (q - 1) x 150 ms;
- input: the AIDs on the wire (byte, ms after the first frame) vs the driver log (attempts and results) vs the
  probe's own host-side summary (AID, quantum, host ms) - the host-side proof of receipt; `aid_test_exercised` is true
  only if the driver actually SENT at least one planned probe AID (PF4 / PF5 / PF6): with nothing sent, the two
  `*_match_*` equalities compare empty lists and prove nothing about delivery;
- host timing from the summary: quanta issued, elapsed, issue lateness, the longest output call (TPUT / TPG), and
  (HOLDS line) the number of HOLD output calls, the longest HOLD and the longest other output call;
- terminal lag (behind first + (q - 1) x 150 ms) by thirds of the run (bounded or growing) and, for PB4, by quantum
  phase q mod 4 (phase 0 = the HOLD barrier frames): how much lag builds between barriers and whether each drains it;
- PR2 (render every 2nd logical quantum): the frames must carry the even quanta 2, 4, ... in order (step 2; a replayed
  skipped quantum or a burst breaks `quanta_in_order`); `logical_quanta` / `physical_writes` / `skipped_writes` from
  the host summary (QUANTA, WRITES, SKIPPED) and `frames_on_wire`; the lag is measured against the LOGICAL 150 ms
  schedule (frame q due at first + (q - q1) x 150), the arrival gaps are those of the physical writes;
- PR2I (PR2 plus the host table): `instr` from the summary lines `PACZ6P S1` / `S2` (one status character per
  executed quantum: `.` RC 4, `a` RC 0 with data, `z` RC 0 length 0, `e` other RC; upper case / `:` = a write
  quantum) and `PACZ6P I` (quantum, write flag, TGET RC, length, AID, AIDCNT before > after, ms before / after the
  TPUT, ms before / after the TGET; `------` = no TPUT). Host clock only: no subtraction against the wire clock.
  `host_pattern`: `odd-poll-success` if any no-write quantum returned an AID; `write-poll-only` if every AID came on
  a write quantum with at least one empty no-write poll among the 3 quanta before; otherwise `other`.
"""
import argparse
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zos5_live_check as Z5  # noqa: E402

TITLE = 'PACZ6P ZOS-6 PROTOCOL PROBE'
T = 150


def ms(ts):
    return Z5.ms(ts)


def stats(xs):
    s = sorted(xs)
    if not s:
        return {'n': 0}
    return {'n': len(s), 'mean': round(sum(s) / len(s), 1), 'median': statistics.median(s),
            'p95': s[min(len(s) - 1, int(len(s) * .95))], 'max': s[-1]}


def text(p):
    return ' '.join(Z5.texts(p)) if len(p) > 2 else ''


def instrumentation(summ):
    """The PR2I host table from the line-mode summary (see the module docstring); None if absent."""
    m1, m2 = re.search(r'PACZ6P S1 ([.:a-zA-Z]*)', summ), re.search(r'PACZ6P S2 ([.:a-zA-Z]*)', summ)
    if not m1:
        return None
    st = m1.group(1) + (m2.group(1) if m2 else '')
    det = [dict(q=int(q), write=w == '1', rc=rc, length=None if ln == '---' else int(ln), aid=aid,
                cnt_before=int(cb), cnt_after=int(ca), tput=[None if x.startswith('-') else int(x) for x in (t1, t2)],
                tget=[int(t3), int(t4)])
           for q, w, rc, ln, aid, cb, ca, t1, t2, t3, t4 in re.findall(
               r'PACZ6P I (\d{3}) ([01]) ([0-9A-F]{2}) (\d{3}|---) ([0-9A-F]{2}) (\d{2})>(\d{2}) (\d{6}|-{6}) '
               r'(\d{6}|-{6}) (\d{6}|-{6}) (\d{6}|-{6})', summ)]
    writes = [q for q, c in enumerate(st, 1) if c == ':' or c.isupper()]
    hits = [q for q, c in enumerate(st, 1) if c in 'aA']
    deliveries = [dict(q=q, write=st[q - 1] == 'A', before=[(p, st[p - 1]) for p in range(max(1, q - 3), q)])
                  for q in hits]
    if any(not d['write'] for d in deliveries):
        pattern = 'odd-poll-success'
    elif deliveries and all(any(c == '.' for _, c in d['before']) for d in deliveries):
        pattern = 'write-poll-only'
    else:
        pattern = 'other'
    return dict(quanta=len(st), status=st, writes=writes,
                writes_even_only=writes == [q for q in range(1, len(st) + 1) if q % 2 == 0],
                hits=hits, odd_hits=[q for q in hits if q % 2], errors=[q for q, c in enumerate(st, 1) if c in 'eE'],
                deliveries=deliveries, detail=det, host_pattern=pattern)


def analyse(trace, log_lines, mode):
    recs, keep = Z5.telnet(Z5.blocks(trace)[0])
    funcs = sorted(Z5.functions(trace))
    i0 = next((i for i, (_, d, _, r) in enumerate(recs) if d == '<' and len(r) > 5 and TITLE in text(r[5:])), None)
    if i0 is None:
        raise SystemExit('no probe screen in the trace')
    i1 = next((i for i in range(i0, len(recs)) if recs[i][1] == '<' and len(recs[i][3]) > 5
               and 'PACZ6P MODE' in text(recs[i][3][5:])), len(recs))
    win = recs[i0 + 1:i1]
    step = 2 if mode in ('PR2', 'PR2I') else 1
    frames, ctl, bids, sig, resp, aids, other, after_sdi = [], {}, 0, 0, [0, 0], [], {}, {}
    hosts = [(ms(ts), r) for _, d, ts, r in win if d == '<']
    for k, (tm, r) in enumerate(hosts):
        dt, rq = r[0], r[1]
        if dt == 0x00 and len(r) > 7 and r[5:7] == b'\xf1\xc2' and 'QUANTUM' in text(r[5:]):
            m = re.search(r'QUANTUM (\d{4})', text(r[5:]))
            frames.append((tm, int(m.group(1)) if m else None, rq))
        elif dt == 0x00 and len(r) == 5:
            ctl[f'{rq:02X}'] = ctl.get(f'{rq:02X}', 0) + 1
        elif dt == 0x09:
            bids += 1
            sig += bool(rq & 0x04)
        else:
            key = f'DT {dt:02X} RQ {rq:02X} len {len(r) - 5}'
            other[key] = other.get(key, 0) + 1
        if dt == 0x00 and rq & 0x01 and k + 1 < len(hosts):
            nx = hosts[k + 1][1]
            key = 'BID' if nx[0] == 0x09 else f'DT {nx[0]:02X} RQ {nx[1]:02X}'
            after_sdi[key] = after_sdi.get(key, 0) + 1
    for _, d, ts, r in win:
        if d == '>' and r[0] == 0x02:
            resp[0 if r[2] == 0 else 1] += 1
        elif d == '>' and r[0] == 0x00 and len(r) > 5:
            aids.append((ms(ts), r[5]))
    f0 = frames[0][0] if frames else ms(win[0][2])
    qs = [q for _, q, _ in frames]
    gaps = [b[0] - a[0] for a, b in zip(frames, frames[1:])]
    lagq = [(q, tm - (f0 + (q - qs[0]) * T)) for tm, q, _ in frames if q is not None and qs[0] is not None]
    lag = [x for _, x in lagq]
    n3 = len(lag) // 3
    thirds = [stats(lag[:n3]), stats(lag[n3:2 * n3]), stats(lag[2 * n3:])] if n3 else []
    phases = {str(ph): stats([x for q, x in lagq if q % 4 == ph]) for ph in (1, 2, 3, 0)} if mode == 'PB4' else None
    t_lo, t_hi = ms(win[0][2]), ms(win[-1][2])
    kb = [(ms(m.group(1)), m.group(2).strip() != 'none') for m in
          re.finditer(r'^(\d{8}\.\d{6}\.\d{3}) kybd\s+Keyboard (?:lock|unlock)\(.*?->\s*(.*)$', trace, re.M)
          if t_lo <= ms(m.group(1)) <= t_hi]
    windows, locks, state, since = [], [], None, t_lo
    for tm, lk in kb:
        if state is False and lk:
            windows.append(tm - since)
        if state is True and not lk:
            locks.append(tm - since)
        if lk != state:
            state, since = lk, tm
    summ = [text(r[5:]) for _, d, _, r in recs[i1:] if d == '<' and len(r) > 5 and 'PACZ6P' in text(r[5:])]
    host = {}
    for s in summ:
        for k, v in re.findall(r'(MODE|QUANTA|ELAPSED-MS|LATE>75MS|MAXLATE-MS|MAXPUT-MS|RCOUT|RCIN|AIDS|HOLDS|MAXHOLD-MS|MAXNOHOLD-MS|WRITES|SKIPPED) (\S+)', s):
            host.setdefault(k, v)
    host_aids = [(a, int(q), int(t)) for a, q, t in re.findall(r'PACZ6P AID ([0-9A-F]{2}) QUANTUM (\d+) MS (\d+)',
                                                              ' '.join(summ))]
    instr = instrumentation(' '.join(summ)) if mode == 'PR2I' else None
    log = [json.loads(x) for x in log_lines if x.strip()]
    attempts = [(x['action'], x['result']) for x in log if x['category'] == 'probe']
    sent = [x['action'] for x in log if x['category'] == 'probe' and x['result'] == 'ok']
    wire = [f'{a:02X}' for _, a in aids]
    want = {'PF4': 'F4', 'PF5': 'F5', 'PF6': 'F6'}
    num = lambda k: int(host[k]) if k in host and host[k].isdigit() else None
    rep = {
        'mode': mode, 'functions': funcs, 'keepalive': keep,
        'frames': len(frames), 'frame_step': step,
        'quanta_in_order': qs == list(range(qs[0], qs[0] + step * len(qs), step)) if qs and qs[0] else False,
        'frames_sdi': sum(1 for *_, rq in frames if rq & 1), 'frames_kri': sum(1 for *_, rq in frames if rq & 2),
        'empty_controls': ctl, 'bids': bids, 'signal_bids': sig, 'after_sdi': after_sdi, 'responses_pos_neg': resp,
        'other_records': other, 'arrival_gaps': stats(gaps),
        'mean_period': round((frames[-1][0] - frames[0][0]) / (len(frames) - 1), 1) if len(frames) > 1 else None,
        'lag_vs_first_frame_schedule': stats(lag), 'lag_by_third': thirds, 'lag_by_q_mod4': phases,
        'unlock_windows': stats(windows), 'locked_intervals': stats(locks),
        'wire_aids': [(t - f0, f'{a:02X}') for t, a in aids], 'driver_attempts': attempts,
        'aid_test_exercised': bool(sent), 'aids_planned': len(want), 'aids_attempted': len(attempts),
        'aids_sent': len(sent),
        'driver_sent_match_wire': [want[a] for a in sent] == wire,
        'host_summary': host, 'host_aids': host_aids,
        'logical_quanta': num('QUANTA'), 'physical_writes': num('WRITES'), 'skipped_writes': num('SKIPPED'),
        'frames_on_wire': len(frames), 'instr': instr,
        'host_received_match_wire': [a for a, _, _ in host_aids] == wire[:8],
    }
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', required=True, choices=['P0', 'PT', 'PN', 'PH', 'PB4', 'PR2', 'PR2I'])
    ap.add_argument('--trace', required=True)
    ap.add_argument('--drive-log', required=True)
    a = ap.parse_args()
    raw, lg = Path(a.trace).read_bytes(), Path(a.drive_log).read_bytes()
    print(f'{a.mode} probe trace SHA-256 {hashlib.sha256(raw).hexdigest()}; driver log SHA-256 '
          f'{hashlib.sha256(lg).hexdigest()}')
    rep = analyse(raw.decode('utf-8', 'replace'), lg.decode().splitlines(), a.mode)
    for k, v in rep.items():
        print(f'  {k}: {json.dumps(v)}')
    print('DIAGNOSTIC ONLY - not a ZOS-6 acceptance result')


if __name__ == '__main__':
    main()
