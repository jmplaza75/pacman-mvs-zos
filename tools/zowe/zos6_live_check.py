#!/usr/bin/env python3
"""ZOS-6 REALTIME live postcheck (docs/zos6-design.md). Local, read-only. One case per trace (R1 or R2).

Usage: zos6_live_check.py --case R1|R2 --trace TRACE --drive-log LOG [--prefix Z00000.PACMAN]
       exit 0 PASS, 2 ENVIRONMENT/TIMING BLOCKED, 1 FUNCTIONAL FAIL; "NEXT CASE ALLOWED" only after PASS.

Empty host 3270-DATA records with REQUEST-FLAG exactly SDI + KRI (X'03', CONTENTION-RESOLUTION negotiated) are
TN3270E send-state controls (z/OS, R1-T3): validated as records, never game writes, kept for the diagnostics;
every other empty 3270-DATA record fails. Reuses the closed ZOS-5 checker's helpers unchanged (tools/zowe/zos5_live_check.py: blocks, telnet, tn3270e /
CONTENTION-RESOLUTION, functions, parse, texts, the query / profile rules, outside_errors); the raw TN3270E records
(BID, RESPONSE) are rebuilt here from the same trace for the statistics only.
Functional (any failure = FUNCTIONAL FAIL):
- transition: the inbound records before the size switch are exactly the planned EXEC (typed command) and ENTER;
- the game: switch, query, one valid reply, profile (1,1,1) and its canvas, first screen; the game writes are the host
  records after the first screen up to the first TSO line-mode record (WCC C1; PACMAN writes C3 / C2 only);
- cards: every game write answers exactly one read / poll (a quantum, the PAUSED screen, the resume quantum or the end
  screen); each gameplay AID goes to the first write after it was sent or up to three later (search, longest model
  match); tests/ref_rt.py tsd on those cards (config AI0 1 from the PARM, T of the case) = every write byte for byte
  (write 0: PACFSIO's clear prefix; full screens 7E, partial / quantum / restore-only F1); so no game write before the
  start AID and none while PAUSED (BID / RESPONSE are TN3270E control records, never game writes);
- inputs: planned gameplay actions == successful driver-log gameplay actions == reconstructed TN3270E AIDs (PF7 X'F7',
  PF8 X'F8', PF9 X'F9', PF10 X'7A', PF11 X'7B', PA2 X'6E', x / Q = ENTER X'7D' with the typed field) == the events the
  model consumed (U D P L R * x Q), in order, nothing missing / duplicated / substituted; each directional action is
  reported explicitly (planned, sent, AID byte, quantum, model direction);
- R1: exactly one death and exactly quanta(10) death-stop quanta (model);
- closure: the model's end lines (QUIT / TURNS / SCORE / LIVES / QUANTA) in line mode, `***` only after them, the
  closure ENTER, the ISPF Command Shell; no IKJ / IEC / IGZ / CEE / ABEND / PACMAN: anywhere;
- timing: mean period of the principal segment < 0.99 T, or a quantum write arriving before the earliest time its
  deadline allows (start / resume AID send time + (j - 1) T: a host burst proven by causality) = FUNCTIONAL FAIL.
Timing (functional exact; any failure = ENVIRONMENT/TIMING BLOCKED, never PASS):
- principal segment = the longest run of consecutive quantum writes whose polls consumed no input (>= 200 quanta);
- mean period in [0.99 T, 1.02 T] (> 1.10 T: STOP, the next case is prohibited); median gap within T +/- 10 ms;
- skipped periods: the lower envelope of the lateness t_k - (t_0 + k T) (minimum per 20-quantum window) rising by
  >= T / 2 = probable skipped host period(s); long gaps without that rise are recorded (correlated with BID latency);
- after the PF9 resume: the first five quantum writes; two consecutive client gaps < T / 2 = suspicious, BLOCKED
  unless causality proves a host burst (FAIL);
- R1 death stop (death write -> last death-stop write) within 1350..1650 ms.
Diagnostics only: p95 / max gap, endpoint drift (live proxy, not the host-side drift), trend per 100 quanta, BID count
and latency, the keyboard-locked fraction of the principal segment (c3270 kybd lines), gap / BID correlation.

ZOS-6 production design (docs/zos6-production-design.md, ZV-D33): the plan's `present` (R1 / R2: C = PRESENT(COALESCED);
E / absent = EVERY, the D33 rules above unchanged) selects the model. COALESCED keeps two clocks apart: LOGICAL quanta
come only from the model (tests/ref_rt.py with the PSLT filter: every quantum runs, a write only every STRIDE quanta
from the start / resume base), PHYSICAL frames only from the trace; every quantum write is tied to the logical quantum
q(w) it presents (the model's tag) and must equal the filtered model byte for byte (no exemption is needed for the
stream; the image invariant against the unfiltered model is a model property, tests section 20). Cards are per poll /
logical quantum: an AID is placed on a card inside a window bounded by physical writes (window()). Structure: quantum
writes strictly increasing in q, exactly STRIDE apart inside a segment (a non-slot write or a replayed frame cannot
match). Death: the live frames match the canonical model with exactly quanta(10) frozen logical quanta (FUNCTIONAL);
the same placement search with the freeze mutated to quanta(10) - 1 and + 1 is reported as live freeze discrimination
DISCRIMINATED (both rejected) or NOT OBSERVABLE (a mutant matches too: the scenario cannot show the length - never
PASS, never FAIL / BLOCKED; the exact freeze is then proven offline: PACRT unchanged + RTSTILL); the wall-clock
`freeze-span proxy` = the arrival difference of the two quantum writes exactly quanta(10)
quanta apart around the freeze (the old death-write -> last-death-stop-write test when the pair is (d, d + 10)),
1350..1650 ms, timing only, never a substitute for the logical proof. Timing on logical q: mean period (a_last -
a_first) / (q_last - q_first), median of the gaps per logical quantum within T +/- 10 ms, causality and the lateness
envelope on q. Predeclared candidate gates (COALESCED only, BLOCKED when missed): physical gap median / p95 / max,
backlog delta (mean lateness last third - first third), input reaction = terminal wire AID -> arrival of the first
write that answers its card or a later one (trace clock only; the model decides which frame is causally the first to
present the input, visible change or not) - every one and the median (GATES).
Decisions 2026-10-19 (R1-T4): (1) a bare host Write `F1 C3` right after an AID read by a blocking TGET (start, resume)
is a TSO CONTROL record (parse6 / check: exact bytes, exact context, at most one per AID, confirmed on the model),
counted in `tso_controls`, never a game write; (2) under COALESCED the historical lateness-envelope ("probable skipped
period") rule is diagnostic only (`diag_notes`); under EVERY it stays a BLOCKED rule.
"""
import argparse
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests')]
import zos5_live_check as Z5  # noqa: E402
import ref_rt  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
from ref_snap import Log  # noqa: E402
from zos6_drive import PLANS, EXPECT  # noqa: E402

Fail = Z5.Fail
AID_ACTION = {0xF7: 'PF7', 0xF8: 'PF8', 0xF9: 'PF9', 0x7A: 'PF10', 0x7B: 'PF11', 0x6E: 'PA2'}
EVENT_CHAR = {'MOV': None, 'PAU': 'P', 'RDR': '*', 'INV': None, 'QUI': 'Q'}
DIRS = ('PF7', 'PF8', 'PF10', 'PF11')
STRIDE = {150: 2, 125: 3}           # PRESENT(COALESCED): logical quanta per physical write (PACPLAT PSLT, 300 ms)
# The predeclared candidate R1 / R2 gates, FROZEN as approved 2026-10-19 (tests section 22 pins them): never tuned
# from live results.
GATES = {150: {'median': (280, 320), 'p95': 450, 'max': 1000, 'backlog': 100, 'react': 1000, 'react_median': 750},
         125: {'median': (345, 405), 'p95': 525, 'max': 1000, 'backlog': 100, 'react': 1075, 'react_median': 825}}
PASS, BLOCKED, FAILED = 'PASS', 'ENVIRONMENT/TIMING BLOCKED', 'FUNCTIONAL FAIL'


def ms(ts):
    return Z5.ms(ts)


def typed(p):
    data = p[6:] if len(p) > 6 and p[3] == 0x11 else b''
    return data.decode('cp037', 'replace').strip()


def action_of(p):
    if p[0] == 0x7D:
        t = typed(p)
        return t if t in ('x', 'Q') else f'ENTER({t})'
    return AID_ACTION.get(p[0], f'AID {p[0]:02X}')


def model(cards, canvas, per, present=None, frt=None, cfg='AI0 1'):
    """ref_rt.tsd on the cards -> dict: out (end lines), frames, kinds, full (full-screen set), rqs ((kind, freeze) per
    logical quantum), rins (consumed events), qs (the logical quantum each write presents, None: not a quantum write),
    fc (the card / poll each write answers). present: C = PRESENT(COALESCED); frt: the freeze-length hook (mutants)."""
    full, rqs, rins = set(), [], []
    real_full = gx.full

    def tagged(*a, **kw):
        b = real_full(*a, **kw)
        full.add(b)
        return b

    class Ctl(ref_rt.Controller):
        def rq(self):
            super().rq()
            rqs.append((self.kind, self.frz))

        def rin(self, kind, d, ch):
            rins.append((kind, d, ch))
            super().rin(kind, d, ch)
    lg = Log()
    lg.kinds = []
    gx.full = tagged
    try:
        out, frames = ref_rt.tsd([cfg] + cards, canvas, snap=lg, mk_ctl=Ctl, per=per, present=present, frt=frt)
    finally:
        gx.full = real_full
    return {'out': out, 'frames': list(frames), 'kinds': lg.kinds, 'full': full, 'rqs': rqs, 'rins': rins,
            'qs': list(frames.qs), 'fc': list(frames.cards)}


def cards_for(m, slots, chars):
    cards = ['.'] * m
    for s, c in zip(slots, chars):
        cards[s - 1] = (cards[s - 1] if cards[s - 1] != '.' else '') + c
    return cards


def same(p, f, j, full, fcmd):
    if j == 0:
        return p[:1] in (b'\xf1', b'\xf5') and p[1:] == f[:1] + Z5.CLRPFX + f[1:]
    return p[1:] == f and p[0] == (fcmd if f in full else 0xF1)


def lcp(live, frames, full, fcmd):
    n = 0
    for j, (p, f) in enumerate(zip(live, frames)):
        if not same(p, f, j, full, fcmd):
            break
        n += 1
    return n


def raw_records(text):
    """The raw TN3270E records (with headers) in trace order: [(order, dir, ts, record)] (BID / RESPONSE included)."""
    return Z5.telnet(Z5.blocks(text)[0])[0]


def kb_locks(text):
    """c3270 keyboard state changes: [(ms, locked?)]."""
    out = []
    for m in re.finditer(r'^(\d{8}\.\d{6}\.\d{3}) kybd\s+Keyboard (?:lock|unlock)\(.*?->\s*(.*)$', text, re.M):
        out.append((ms(m.group(1)), m.group(2).strip() != 'none'))
    return out


KRI_CTL = 0x03                           # REQUEST-FLAG SDI + KRI: c3270 "SEND-DATA|KEYBOARD-RESTORE"
SENTINEL = b'\x00KRI-CONTROL\x00'          # never a 3270 command byte: marks a control record inside the ZOS-5 parser


def is_kri_control(d, r, funcs):
    """An empty host 3270-DATA record that only returns the send state / keyboard to the terminal (z/OS TN3270E with
    CONTENTION-RESOLUTION, live trace R1-T3): DATA-TYPE 00, no payload, REQUEST-FLAG exactly SDI + KRI (X'03'), and the
    function negotiated. Every other empty 3270-DATA record stays illegal (the ZOS-5 rules reject it)."""
    return d == '<' and len(r) == 5 and r[0] == 0x00 and r[1] == KRI_CTL and Z5.CR in funcs


def parse6(text):
    """zos5_live_check.parse with one addition: empty SDI + KRI control records are validated as TN3270E records by the
    unchanged ZOS-5 rules (header, flags, SEQ-NUMBER, responses), then removed from the 3270 data events, so they are
    never game writes and never reach the model; their times are returned for the send-state diagnostics."""
    bl, snap = Z5.blocks(text)
    recs, keep = Z5.telnet(bl)
    funcs = Z5.functions(text)
    marked, controls = [], []
    for k, (n, d, ts, r) in enumerate(recs):
        if is_kri_control(d, r, funcs):
            marked.append((n, d, ts, r + SENTINEL + k.to_bytes(4, 'big')))
            controls.append(ms(ts))
        else:
            marked.append((n, d, ts, r))
    ev, rule = Z5.tn3270e(marked, funcs)
    ev = [e for e in ev if not (e[1] == '<' and e[3].startswith(SENTINEL))]
    # the TSO blocking-read control record (R1-T3 / R1-T4, decision 2026-10-19): a 2-byte host Write `F1 C3` (WCC only,
    # no data) right after an inbound AID that the program read with a blocking TGET. Candidate here only when the
    # record is exactly F1 C3, the event before it is that inbound AID and the last host record before the AID is a
    # WCC C3 screen (the pre-start / PAUSED screen of a blocking read); at most one per AID (a second one is not
    # preceded by the AID). check() then confirms, on the model, that the AID was consumed by a blocking read.
    # Mechanism (TSO / VTAM on completion of the full-screen TGET WAIT): an inference; observed fact: the record and
    # this context, already in R1-T3 (before ZOS-6). Never a game write, never a model write.
    tso, kept = [], []
    for k, e in enumerate(ev):
        if e[1] == '<' and e[3] == TSO_C3 and k > 0 and ev[k - 1][1] == '>' and ev[k - 1][3][:1] != b'' \
                and kept and ev[k - 1] is kept[-1]:
            last_host = next((x for x in reversed(kept[:-1]) if x[1] == '<'), None)
            if last_host is not None and last_host[3][1:2] == b'\xc3':
                tso.append({'ms': ms(e[2]), 'ts': e[2], 'aid_ms': ms(ev[k - 1][2]), 'aid': f'{ev[k - 1][3][0]:02X}'})
                continue
        kept.append(e)
    ev = kept
    starts = [k for k, e in enumerate(ev) if e[1] == '<' and len(e[3]) == 2 and e[3][0] in (0x7E, 0xF5) and e[3][1] == 0xC3]
    if any(re.search(r'LOGON|PASSW', ' '.join(Z5.texts(e[3]))) for e in ev if e[1] == '<'):
        raise Fail('audit: LOGON / PASSWORD text in a host record of the data stream')
    words = re.findall(r'[A-Z0-9#@$.]{4,}', snap.replace(b'\x00', b'\x40').decode('cp037', 'replace'))
    return {'records': len(recs), 'keepalive': keep, 'seq': rule, 'funcs': sorted(funcs), 'ev': ev, 'starts': starts,
            'snapshot': len(snap), 'snap_flags': sorted({w for w in words if re.search(r'LOGON|PASSW|IKJ567', w)}),
            'controls': controls, 'tso_controls': tso}


TSO_C3 = b'\xf1\xc3'


def bid_times(text, ev, writes, skip=()):
    """For every game write (by position): the terminal time of the TN3270E BID announcing it and that write's BID
    response -> data latency (an RTT proxy). A write without a BID: its own arrival time, latency None."""
    hd = [r for r in raw_records(text) if r[1] in ('<', '>')]
    data, bid_of, resp, last_bid = [], {}, {}, None
    for o, d, tsr, r in hd:
        sq = int.from_bytes(r[3:5], 'big')
        if d == '<' and r[0] == 0x09:
            last_bid = (sq, ms(tsr))
        elif d == '>' and r[0] == 0x02:
            resp[sq] = ms(tsr)
        elif d == '<' and r[0] == 0x00 and not (len(r) == 5 and r[1] == KRI_CTL) and \
                not (r[5:] == TSO_C3 and tsr in skip):              # KRI / TSO blocking-read controls: not writes
            data.append((ms(tsr), last_bid if last_bid and last_bid[0] == sq - 1 else None))
            last_bid = None
    hosts = [e for e in ev if e[1] == '<']
    bt, lat = [], []
    for w in writes:
        tdata, b = data[hosts.index(w)]
        bt.append(b[1] if b else tdata)
        lat.append(tdata - resp[b[0]] if b and b[0] in resp else None)
    return bt, lat


def window(sent, wt, bid_t, bid_lat, T, prev, m, fc=None, present=None, kinds=None):
    """The permitted placements of a gameplay AID sent at terminal time `sent` (write indices, 1..m):
    lo = the first write whose BID (else its data) reached the terminal after the AID was sent - every earlier write
    was produced by a poll that ran before the AID existed at the host; at least the previous AID's write (order).
    hi = lo + 1: the AID reaches the host one up-path delay after it was sent; poll lo ran no earlier than one
    down-path delay before its BID arrived; with up + down (the round trip) <= T the poll after lo already sees the AID.
    hi = lo + 2 only with protocol evidence that the round trip exceeded T there: the BID response -> data latency of
    write lo or lo + 1 > T. Never more.
    PRESENT(COALESCED) (fc = the card each write answers, from the model with the placements so far): placements are
    cards. lo = the card after the one answered by the last write that reached the terminal before the AID was sent
    (every poll up to it ran before the AID existed); hi = the card after the one answered by the SECOND write that
    reached the terminal after the AID (consumed at the latest by that write's post-write poll B or an earlier poll;
    PR2I-C2: AIDs became visible right after a write); the third such write only with protocol evidence that the round
    trip there exceeded the presentation interval (BID response -> data latency of either write > STRIDE x T). Never
    more. An AID sent while the game waits in a blocking read (the last write before it is a pre-start / PAUSED
    screen, kind N) is the next card or the one after (lo + 1, as under EVERY). Beyond the model's last write the
    card grid is extended by STRIDE per write."""
    if present != 'C':
        lo = next((j for j in range(1, m + 1) if bid_t[j] > sent), m + 1)
        lo = max(lo, prev)
        long_rtt = any(x is not None and x > T for x in bid_lat[lo:lo + 2])
        return lo, min(m, lo + (2 if long_rtt else 1))
    nw = len(bid_t)
    a = next((j for j in range(1, nw) if bid_t[j] > sent), nw)
    if a - 1 >= len(fc):                      # this model has no write there (it diverged earlier): no placement
        return m + 1, m
    lo = max(fc[a - 1] + 1, prev)
    if kinds is not None and kinds[a - 1] == 'N':
        return lo, min(m, lo + 1)
    long_rtt = any(x is not None and x > STRIDE[T] * T for x in bid_lat[a:a + 2])
    b = a + (2 if long_rtt else 1)
    hi = (fc[b] if b < len(fc) else fc[-1] + (b - len(fc) + 1) * STRIDE[T]) + 1
    return lo, max(lo - 1, min(m, hi))


def stats(xs):
    s = sorted(xs)
    return {'n': len(s), 'min': s[0], 'median': statistics.median(s), 'p95': s[min(len(s) - 1, int(len(s) * .95))],
            'max': s[-1]} if s else {'n': 0}


def place(live, aids, chars, wt, bid_t, bid_lat, T, canvas, fcmd, present, m, frt=None, case='', final=None,
          cfg='AI0 1'):
    """The bounded AID placement (8a): -> (slots, windows, final model). Each AID only inside its window (window(),
    computed on the model with the placements before it); a candidate must match the live writes through the next
    AID's lo. Under PRESENT(COALESCED) two placements can give identical frames for a while (a PF9 one card earlier:
    the same PAUSED screen) and diverge later, so the search backtracks inside the windows (depth first, earliest
    placement first) until the whole trace matches (every write and, with final, the closure end lines); it never
    leaves a window. Raises Fail (the deepest AID that has no permitted placement or matches at none)."""
    memo, worst = {}, [(-1, None)]

    def run(cards):
        key = tuple(cards)
        if key not in memo:
            memo[key] = model(cards, canvas, T, present, frt, cfg)
        return memo[key]

    def rec(n, slots, wins, mod):
        if n == len(aids):
            k = lcp(live, mod['frames'], mod['full'], fcmd)
            writes_ok = k == len(live) and len(mod['frames']) == len(live)
            ok = writes_ok and (final is None or final(mod))
            if not ok and n >= worst[0][0]:
                worst[0] = (n, f'{case}: end lines {mod["out"][-5:]} not found in line mode' if writes_ok else
                            f'{case}: game write {k} differs from the model (live {len(live)} writes, model '
                            f'{len(mod["frames"])})')
            return (slots, wins, mod) if ok else None
        lo, hi = window(ms(aids[n][2]), wt, bid_t, bid_lat, T, slots[-1] if slots else 1, m, mod['fc'], present,
                        mod['kinds'])
        if lo > hi:
            if n >= worst[0][0]:
                worst[0] = (n, f'{case}: gameplay AID {n + 1} has no permitted quantum (order / window)')
            return None
        for j in range(lo, hi + 1):
            cand = run(cards_for(m, slots + [j], chars[:n + 1]))
            k = lcp(live, cand['frames'], cand['full'], fcmd)
            if n + 1 < len(aids):
                nlo = window(ms(aids[n + 1][2]), wt, bid_t, bid_lat, T, j, m, cand['fc'], present, cand['kinds'])[0]
                want = min(len(live), next((w for w, c in enumerate(cand['fc']) if c >= nlo), len(cand['frames'])))
            else:
                want = len(live)
            if k >= want:
                r = rec(n + 1, slots + [j], wins + [(lo, hi)], cand)
                if r:
                    return r
        if n >= worst[0][0]:
            worst[0] = (n, f'{case}: gameplay AID {n + 1} does not match the model at any permitted quantum '
                           f'{lo}..{hi} (it is not moved further)')
        return None
    r = rec(0, [], [], run(['.'] * m))
    if r is None:
        raise Fail(worst[0][1] or f'{case}: game writes differ from the model at every permitted placement')
    return r


def check(text, log_lines, case, prefix='Z00000.PACMAN', present=None, plan=None):
    """-> report dict (state PASS / BLOCKED) or raises Fail (FUNCTIONAL FAIL). present / plan: tests only - override
    the plan's PRESENT (C COALESCED / E EVERY) or the whole plan (steps, T, kw, cfg = the game configuration of the
    model, default AI0 1); the live cases use PLANS."""
    plan = plan or PLANS[case]
    cfg = plan.get('cfg', 'AI0 1')

    def planned(case, category=None):
        return [(c, a) for c, a in plan['steps'] if c not in ('wait', 'expect') and category in (None, c)]
    T = plan['T']
    rep = {'case': case, 'T': T, 'blocked': [], 'stop': False, 'present': present or plan.get('present', 'E')}
    t = parse6(text)
    ev, starts = t['ev'], t['starts']
    rep['controls'] = t['controls']
    rep['tso_controls'] = t['tso_controls']
    rep['funcs'] = t['funcs']
    if len(starts) != 1:
        raise Fail(f'{case}: {len(starts)} games in the trace (exactly one expected)')
    if Z5.CR not in t['funcs']:
        raise Fail(f'{case}: CONTENTION-RESOLUTION not negotiated (the accepted ZOS-5 profile)')
    s0 = starts[0]
    # driver log: planned == successful log, per category
    log = [json.loads(x) for x in log_lines if x.strip()]
    bad = [x for x in log if x.get('result') != 'ok']
    if bad:
        raise Fail(f'{case}: driver action not successful: {bad[0]}')
    for x in log:
        if not (x.get('wait_start', 0) <= x.get('unlocked', -1) <= x.get('sent', -1)) or \
                x.get('requested', 1e18) > x['sent']:
            raise Fail(f'{case}: driver log entry {x.get("ordinal")} has inconsistent timestamps')
    if [x.get('ordinal') for x in log] != list(range(1, len(log) + 1)) or \
            any(a['sent'] > b['sent'] for a, b in zip(log, log[1:])):
        raise Fail(f'{case}: driver log ordinals / send order inconsistent')
    if [(x['category'], x['action']) for x in log] != planned(case):
        raise Fail(f'{case}: driver log {[(x["category"], x["action"]) for x in log]} != plan {planned(case)}')
    # transition: inbound before the switch = EXEC, ENTER
    pre = [e for e in ev[:s0] if e[1] == '>']
    if len(pre) != 2 or typed(pre[0][3]) != f"EXEC '{prefix}.CLIST(PACMAN)' '{plan['kw']}'" or pre[1][3][0] != 0x7D or typed(pre[1][3]):
        raise Fail(f'{case}: transition inputs {[action_of(e[3]) for e in pre]} are not EXEC + ENTER')
    G = ev[s0:]
    host = [e for e in G if e[1] == '<']
    if host[1][3] != Z5.QUERY:
        raise Fail(f'{case}: no Read Partition Query after the switch')
    k1, k2 = G.index(host[1]), G.index(host[2])
    inb = [e for e in G[k1:k2] if e[1] == '>']
    if len(inb) != 1 or inb[0][3][:1] != b'\x88' or not Z5.Q.valid(inb[0][3]):
        raise Fail(f'{case}: not exactly one valid Query Reply before the first screen')
    reply = inb[0][3]
    prof, size = Z5.Q.expect(reply), Z5.Q.expect_size(reply)
    canvas = Z5.SIZES.get(size)
    if prof != (1, 1, 1) or canvas is None:
        raise Fail(f'{case}: profile {prof} / canvas {size}: not the REALTIME full-screen profile')
    fcmd = 0x7E if canvas != 'D' else 0xF5
    rep.update(profile=prof, size=size, canvas=canvas, reply_is_dyn=reply == Z5.Q.rec('dyn'))
    # game writes: host records from the first screen up to the first TSO line-mode record (WCC C1)
    i0 = G.index(host[2])
    gend = next((k for k in range(i0 + 1, len(G)) if G[k][1] == '<' and G[k][3][1:2] == b'\xc1'), None)
    if gend is None:
        raise Fail(f'{case}: no line-mode closure after the game')
    writes = [e for e in G[i0:gend] if e[1] == '<']
    aids = [e for e in G[i0:gend] if e[1] == '>']
    live = [e[3] for e in writes]
    wt = [ms(e[2]) for e in writes]
    acts = [action_of(e[3]) for e in aids]
    plan_g = [a for _, a in planned(case, 'gameplay')]
    log_g = [x['action'] for x in log if x['category'] == 'gameplay']
    if not (plan_g == log_g == acts):
        raise Fail(f'{case}: gameplay plan {plan_g} / driver log {log_g} / TN3270E AIDs {acts} differ')
    for e, a in zip(aids, acts):
        if a in EXPECT and e[3][0] != EXPECT[a][0]:
            raise Fail(f'{case}: {a} arrived as AID {e[3][0]:02X}')
    # cards: each gameplay AID goes to the read / poll (card) whose consumption the model needs, inside a window bounded
    # by the protocol (window()); the model only chooses between the permitted placements, in order, never beyond them
    present = rep['present']
    bid_t, bid_lat = bid_times(text, ev, writes, {x['ts'] for x in t['tso_controls']})
    chars = [EXPECT[a][1] for a in acts]
    m = len(live) - 1 if present != 'C' else STRIDE[T] * len(live) + 10
    tail_txt = [x for e in G[gend:] if e[1] == '<' for x in Z5.texts(e[3])]

    def final(md):                            # the closure end lines of this model appear, in order, after the game
        it = iter(tail_txt)
        return all(any(x == want for x in it) for want in md['out'][-5:])
    slots, windows, mod = place(live, aids, chars, wt, bid_t, bid_lat, T, canvas, fcmd, present, m, case=case,
                                final=final, cfg=cfg)
    cards = cards_for(m, slots, chars)
    out, frames, kinds, full, rqs, rins = (mod[x] for x in ('out', 'frames', 'kinds', 'full', 'rqs', 'rins'))
    qs, fc = mod['qs'], mod['fc']
    k = lcp(live, frames, full, fcmd)
    if k != len(live) or len(frames) != len(live):
        raise Fail(f'{case}: game write {k} differs from the model (live {len(live)} writes, model {len(frames)}); '
                   f'cards {"".join(c if len(c) == 1 else "[" + c + "]" for c in cards)[:120]}')
    consumed = []
    for kind, d, ch in rins:
        consumed.append(d if kind == 'MOV' else EVENT_CHAR.get(kind) or ch)
    if consumed != chars:
        raise Fail(f'{case}: the model consumed {consumed}, the AIDs carry {chars}')
    # per-write kinds: N (first / paused / pre-start screens), Q / P (quanta), E (end); q(w) = the logical quantum
    qi = [j for j, kd in enumerate(kinds) if kd in ('Q', 'P')]
    if any(qs[j] is None for j in qi) or any(qs[a] >= qs[b] for a, b in zip(qi, qi[1:])):
        raise Fail(f'{case}: quantum writes not in strictly increasing logical order (replay)')
    if present != 'C' and len(qi) != len(rqs):
        raise Fail(f'{case}: model quanta {len(rqs)} != quantum writes {len(qi)}')
    if present == 'C':                        # the PSLT grid: STRIDE quanta apart inside a segment (no N write between)
        for a, b in zip(qi, qi[1:]):
            if b == a + 1 and qs[b] - qs[a] != STRIDE[T]:
                raise Fail(f'{case}: writes {a} / {b} present quanta {qs[a]} / {qs[b]}: not {STRIDE[T]} apart')
    rep['directional'] = [{'action': a, 'sent': ms(e[2]), 'aid': f'{e[3][0]:02X}', 'write': s, 'window': w,
                           'model': c} for a, e, s, w, c in zip(acts, aids, slots, windows, consumed) if a in DIRS]
    rep['placements'] = [(a, s, w) for a, s, w in zip(acts, slots, windows)]
    rep['frame_quanta'] = [qs[j] for j in qi]
    for c in rep['tso_controls']:                 # CONTROL only after an AID consumed by a blocking read
        n = next((i for i, e in enumerate(aids) if ms(e[2]) == c['aid_ms']), None)
        prev = None if n is None else max((w for w, cc in enumerate(fc) if cc < slots[n]), default=None)
        if prev is None or kinds[prev] != 'N':
            raise Fail(f'{case}: F1 C3 at {c["ts"]} follows an AID that was not read by a blocking read')
        c['card'] = slots[n]
    rep['frame_cards'] = [fc[j] for j in qi]
    # death stop (R1: exactly one death, exactly quanta(10) LOGICAL quanta - the model's freeze, FUNCTIONAL)
    runs, cur = [], 0
    for kind, frz in rqs + [('-', 0)]:
        if kind == 'F':
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    want_frz = ref_rt.quanta(ref_rt.FREEZE, T)
    rep['death_runs'] = runs
    if any(r != want_frz for r in runs):
        raise Fail(f'{case}: death-stop runs {runs}, {want_frz} quanta required')
    if case == 'R1' and len(runs) != 1:
        raise Fail(f'R1: {len(runs)} deaths (exactly one planned)')
    # live freeze discrimination (decision 2026-10-19, acceptance split): the same bounded search with the freeze mutated
    # by -1 / +1. Both rejected = DISCRIMINATED. A mutant that also matches = NOT OBSERVABLE (the scenario cannot show
    # the freeze length, e.g. the approved R1 plan: AI(0), Pac-Man still after the respawn) - reported as such, never as
    # PASS, and neither a failure nor BLOCKED: the exact logical freeze is proven offline (PACRT unchanged and guarded,
    # RTSTILL batch / TSD / model) and live by the canonical model above. A live trace that only a mutant matches
    # cannot reach this point: it fails against the canonical model.
    rep['freeze_mutants'] = {}
    if runs:
        for d in (-1, 1):
            try:
                _, _, mm = place(live, aids, chars, wt, bid_t, bid_lat, T, canvas, fcmd, present, m, want_frz + d, case,
                                 final, cfg)
                ok = lcp(live, mm['frames'], mm['full'], fcmd) == len(live) and len(mm['frames']) == len(live)
            except Fail:
                ok = False
            rep['freeze_mutants'][want_frz + d] = 'matches' if ok else 'rejected'
    rep['live_freeze_discrimination'] = None if not runs else 'NOT OBSERVABLE' if 'matches' in \
        rep['freeze_mutants'].values() else 'DISCRIMINATED'
    rep['logical_freeze_proof'] = None if not runs else ('canonical model exactly quanta(10) frozen quanta; offline: '
                                                          'PACRT unchanged (Z1 text, guarded) + RTSTILL batch / TSD / '
                                                          'model')
    # closure: end lines, ***, ENTER, shell
    tail = G[gend:]
    seq, k = [], 0
    exp = out[-5:]
    star = shell = False
    closure_in = []
    for e in tail:
        if e[1] == '>':
            closure_in.append(e)
            continue
        segs = Z5.texts(e[3])
        for s in segs:
            mt = Z5.BAD_TEXT.search(s)
            if mt and mt.group(0) == '***' and k < len(exp):
                raise Fail(f'{case}: end lines {exp} not complete before ***')
            if mt and mt.group(0) != '***':
                raise Fail(f'{case}: {mt.group(0)} after the game')
            if mt:
                star = True
            if k < len(exp) and s == exp[k]:
                k += 1
        if k == len(exp) and any(Z5.SHELL in s for s in segs):
            shell = True
            break
    if k != len(exp):
        raise Fail(f'{case}: end lines {exp} not found in line mode')
    if not shell:
        raise Fail(f'{case}: no return to the {Z5.SHELL}')
    if len(closure_in) != 1 or closure_in[0][3][0] != 0x7D or typed(closure_in[0][3]):
        raise Fail(f'{case}: closure inputs {[action_of(e[3]) for e in closure_in]} are not one ENTER')
    Z5.outside_errors(ev)
    rep.update(end_lines=exp, star=star, writes=len(live), quanta=len(rqs))
    timing(rep, wt, kinds, qs, fc, cards, slots, aids, acts, rqs, text, T)
    rep['state'] = BLOCKED if rep['blocked'] else PASS
    return rep


def reaction(sent, fc, wt, slot):
    """Input reaction in ONE clock (the terminal trace): the wire send time of the AID -> the arrival of the first
    write that answers its card or a later one (the first frame causally able to present the input, whatever its
    pixels show). -> (write index, ms) or (None, None)."""
    w = next((j for j, c in enumerate(fc[:len(wt)]) if c >= slot), None)
    return (w, wt[w] - sent) if w is not None else (None, None)


def timing(rep, wt, kinds, qs, fc, cards, slots, aids, acts, rqs, text, T):
    present = rep['present']
    s = STRIDE[T] if present == 'C' else 1
    qw = [j for j in range(1, len(wt)) if kinds[j] in ('Q', 'P')]
    wof = {}                                  # card -> its quantum write (base writes: start / resume)
    for j in qw:
        wof.setdefault(fc[j], j)
    # causality: a quantum write cannot arrive before anchor + (q - q0) T (anchor = the start / resume AID send time,
    # q0 = the logical quantum of the write that answered it); a PAUSED / other N screen ends the segment
    anchors = {}
    for sl, a, e in zip(slots, acts, aids):
        if a in DIRS and not anchors and sl in wof:
            anchors[wof[sl]] = ms(e[2])
    for n in [n for n, a in enumerate(acts) if a == 'PF9'][1::2]:
        if slots[n] in wof:
            anchors[wof[slots[n]]] = ms(aids[n][2])
    seg_anchor, q0 = None, 0
    for j in range(1, len(wt)):
        if j in anchors:
            seg_anchor, q0 = anchors[j], qs[j]
        if kinds[j] == 'N':
            seg_anchor = None
        if seg_anchor is not None and kinds[j] in ('Q', 'P') and wt[j] < seg_anchor + (qs[j] - q0) * T - 2:
            early = seg_anchor + (qs[j] - q0) * T - wt[j]
            raise Fail(f'{rep["case"]}: quantum write {j} arrived {early:.0f} ms before its '
                       'earliest deadline (host burst proven by causality)')
    # principal segment: the longest run of consecutive quantum writes with no input in any card they cover
    best, cur = [], []
    for j in range(1, len(wt)):
        prev = cur[-1] if cur else None
        quiet = kinds[j] in ('Q', 'P') and all(c == '.' for c in cards[(fc[prev] if prev else fc[j] - 1):fc[j]])
        if quiet and (prev is None or j == prev + 1):
            cur.append(j)
        else:
            if len(cur) > len(best):
                best = cur
            cur = [j] if quiet else []
    if len(cur) > len(best):
        best = cur
    ts, qq = [wt[j] for j in best], [qs[j] for j in best]
    p = {'quanta': (qq[-1] - qq[0] + 1) if qq else 0, 'frames': len(ts)}
    rep['principal'] = p
    if p['quanta'] < 200:
        rep['blocked'].append(f'principal segment {p["quanta"]} quanta (< 200)')
    else:
        principal(rep, p, ts, qq, T)
    # running physical gaps (consecutive quantum writes, no other write between) for the cadence max gate
    run_gaps = [wt[b] - wt[a] for a, b in zip(qw, qw[1:]) if b == a + 1]
    # post-resume: the first five quantum writes after the resume write (gaps per logical quantum)
    pr = []
    for n in [n for n, a in enumerate(acts) if a == 'PF9'][1::2]:
        r = wof.get(slots[n])
        if r is None:
            continue
        js = [j for j in range(r, len(wt)) if kinds[j] in ('Q', 'P')][:5]
        g = [(wt[b] - wt[a]) / (qs[b] - qs[a]) for a, b in zip(js, js[1:])]
        sus = any(g[i] < T / 2 and g[i + 1] < T / 2 for i in range(len(g) - 1))
        pr.append({'writes': js, 'gaps': g, 'suspicious': sus})
        if sus:
            rep['blocked'].append('post-resume burst-like client timing (not provable from the protocol)')
    rep['post_resume'] = pr
    # R1 freeze-span proxy (wall clock, timing only): the quantum writes exactly FRT logical quanta apart around the
    # freeze: q1 in d .. d + s - 1 (d = the death quantum), q2 = q1 + FRT; EVERY: (d, d + FRT) = the old death stop
    if rep['case'] == 'R1':
        ks = [kd for kd, _ in rqs]
        d, frt = ks.index('F'), rep['death_runs'][0]
        byq = {qs[j]: j for j in qw}
        pair = next(((byq[q1], byq[q1 + frt]) for q1 in range(d, d + s) if q1 in byq and q1 + frt in byq), None)
        if pair is None:
            rep['death_ms'], rep['death_writes'] = None, None
            rep['blocked'].append('freeze-span proxy not measurable (no two writes FRT quanta apart around the freeze)')
        else:
            dur = wt[pair[1]] - wt[pair[0]]
            rep['death_ms'], rep['death_writes'] = dur, pair
            rep['death_pair_quanta'] = (qs[pair[0]], qs[pair[1]])
            if not 1350 <= dur <= 1650:
                rep['blocked'].append(f'death stop (freeze-span proxy) {dur} ms outside 1350..1650 ms')
    # input reaction: wire AID -> the first write answering its card or later (trace clock only)
    react = []
    for n, (a, e) in enumerate(zip(acts, aids)):
        w, lat = reaction(ms(e[2]), fc, wt, slots[n])
        react.append({'action': a, 'card': slots[n], 'write': w, 'ms': lat})
    rep['reaction'] = react
    if present == 'C':                        # the predeclared candidate R1 / R2 gates (ENVIRONMENT / TIMING)
        gt = GATES[T]
        lats = [r['ms'] for r in react if r['ms'] is not None]
        pg = [b - a for a, b in zip(ts, ts[1:])]
        rep['gates'] = {'physical': stats(pg), 'running_max': max(run_gaps, default=None),
                        'reaction': stats(lats), 'backlog_delta': p.get('backlog_delta')}
        if pg:
            med = statistics.median(pg)
            if not gt['median'][0] <= med <= gt['median'][1]:
                rep['blocked'].append(f'physical median gap {med} ms outside {gt["median"][0]}..{gt["median"][1]} ms')
            p95 = stats(pg)['p95']
            if p95 > gt['p95']:
                rep['blocked'].append(f'physical p95 gap {p95} ms > {gt["p95"]} ms')
        if run_gaps and max(run_gaps) > gt['max']:
            rep['blocked'].append(f'physical max gap {max(run_gaps)} ms > {gt["max"]} ms')
        if p.get('backlog_delta') is not None and p['backlog_delta'] > gt['backlog']:
            rep['blocked'].append(f'backlog delta {p["backlog_delta"]:.0f} ms > {gt["backlog"]} ms')
        if any(x is None for x in lats) or len(lats) != len(react):
            rep['blocked'].append('input reaction not measurable for every gameplay AID')
        if lats and max(lats) > gt['react']:
            rep['blocked'].append(f'input reaction {max(lats)} ms > {gt["react"]} ms')
        if lats and statistics.median(lats) > gt['react_median']:
            rep['blocked'].append(f'input reaction median {statistics.median(lats)} ms > {gt["react_median"]} ms')
    # diagnostics: BID latency, keyboard-locked fraction, gap / BID correlation
    if len(ts) < 2:
        rep['diag'] = {}
        return
    raw = raw_records(text)
    bids, resp, data = {}, {}, []
    for o, d, tsr, r in raw:
        sq = int.from_bytes(r[3:5], 'big')
        if d == '<' and r[0] == 0x09:
            bids[sq] = ms(tsr)
        elif d == '>' and r[0] == 0x02:
            resp[sq] = ms(tsr)
        elif d == '<' and r[0] == 0x00:
            data.append((ms(tsr), sq))
    lat_b = {}
    for tdata, sq in data:
        if sq - 1 in bids and sq - 1 in resp:
            lat_b[tdata] = tdata - resp[sq - 1]
    lats = [v for k_, v in lat_b.items() if ts[0] <= k_ <= ts[-1]]
    corr = sum(1 for (a, b) in zip(ts, ts[1:]) if b - a > 1.5 * s * T and lat_b.get(b, 0) > T)
    locks = kb_locks(text)
    locked, state, since = 0, False, ts[0]
    for tm, lk in locks:
        tm2 = min(max(tm, ts[0]), ts[-1])
        if state:
            locked += tm2 - since
        state, since = lk, tm2
    if state:
        locked += ts[-1] - since
    kri = sorted([ms(tsr) for o, d, tsr, r in raw if d == '<' and r[0] == 0x00 and r[1] & 0x02 and ts[0] <= ms(tsr) <= ts[-1]])
    rep['diag'] = {'kri_records': len(kri), 'kri_controls': len([c for c in rep['controls'] if ts[0] <= c <= ts[-1]]),
                   'kri_max_gap': max((b - a for a, b in zip([ts[0]] + kri, kri + [ts[-1]])), default=None),
                   'bids': len([1 for v in bids.values() if ts[0] <= v <= ts[-1]]), 'bid_latency': stats(lats),
                   'locked_fraction': round(locked / max(1, ts[-1] - ts[0]), 3) if locks else None,
                   'long_gaps_with_bid_latency_over_T': corr}


def principal(rep, p, ts, qq, T):
    """Timing of the principal segment on LOGICAL quanta (qq = q(w) of each write; EVERY: consecutive)."""
    dq = [b - a for a, b in zip(qq, qq[1:])]
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    norm = [g / d for g, d in zip(gaps, dq)]
    mean = (ts[-1] - ts[0]) / (qq[-1] - qq[0])
    lat = [x - (ts[0] + (q - qq[0]) * T) for x, q in zip(ts, qq)]
    win = [min(lat[i:i + 20]) for i in range(0, len(lat), 20)]
    rise = max((min(win[s:]) - min(win[:s]) for s in range(1, len(win))), default=0)
    n = len(lat)
    xm = sum(qq) / n
    ym = sum(lat) / n
    slope = sum((q - xm) * (y - ym) for q, y in zip(qq, lat)) / sum((q - xm) ** 2 for q in qq)
    third = max(1, n // 3)
    p.update(first=ts[0], last=ts[-1], elapsed=ts[-1] - ts[0], ideal=(qq[-1] - qq[0]) * T, mean=round(mean, 3),
             gaps=stats(gaps), endpoint_drift=lat[-1] - lat[0], trend_per_100=round(slope * 100, 3),
             envelope_rise=rise, long_gaps=sum(1 for g in norm if g > 1.5 * T),
             backlog_delta=round(sum(lat[-third:]) / third - sum(lat[:third]) / third, 1))
    if mean < 0.99 * T:
        raise Fail(f'{rep["case"]}: mean period {mean:.2f} ms < 0.99 T (faster than the absolute schedule)')
    if mean > 1.10 * T:
        rep['blocked'].append(f'mean period {mean:.2f} ms > 1.10 T')
        rep['stop'] = True
    elif mean > 1.02 * T:
        rep['blocked'].append(f'mean period {mean:.2f} ms > 1.02 T')
    med = statistics.median(norm)
    if abs(med - T) > 10:
        rep['blocked'].append(f'median gap {med} ms per logical quantum outside T +/- 10 ms')
    if rise >= T / 2:
        msg = f'probable skipped period(s): lateness lower envelope rose {rise:.0f} ms'
        if rep['present'] == 'C':     # ZV-D33 (decision 2026-10-19): diagnostic only - its fixed 20-write windows
            rep.setdefault('diag_notes', []).append(msg + ' (diagnostic, COALESCED)')   # span 40 / 60 logical quanta
        else:
            rep['blocked'].append(msg)        # EVERY: the historical D33 rule, unchanged


def r2_eligible(r1_state):
    return r1_state == PASS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True, choices=sorted(PLANS))
    ap.add_argument('--trace', required=True)
    ap.add_argument('--drive-log', required=True)
    ap.add_argument('--prefix', default='Z00000.PACMAN')
    a = ap.parse_args()
    raw = Path(a.trace).read_bytes()
    lg = Path(a.drive_log).read_bytes()
    print(f'{a.case} trace SHA-256 {hashlib.sha256(raw).hexdigest()} ({len(raw)} bytes); driver log SHA-256 '
          f'{hashlib.sha256(lg).hexdigest()}')
    try:
        rep = check(raw.decode('utf-8', 'replace'), lg.decode().splitlines(), a.case, a.prefix)
    except Fail as e:
        print(f'{a.case}: {FAILED}: {e}')
        print('NEXT CASE ALLOWED: no')
        sys.exit(1)
    p = rep['principal']
    print(f'{a.case}: T {rep["T"]} ms; functions {rep["funcs"]}; profile {rep["profile"]} canvas {rep["size"]}; '
          'reply = '
          f'qreply_dyn: {rep["reply_is_dyn"]}; {rep["writes"]} game writes = model, {rep["quanta"]} quanta; death-stop '
          f'runs {rep["death_runs"]}; end lines {rep["end_lines"]}; *** {rep["star"]}; shell yes')
    for d in rep['directional']:
        print(f'  directional {d["action"]}: sent {d["sent"]}, AID {d["aid"]}, write {d["write"]}, model {d["model"]}')
    print(f'  principal segment: {json.dumps(p)}')
    if 'post_resume' in rep:
        print(f'  post-resume: {json.dumps(rep["post_resume"])}')
    print(f'  present {rep["present"]}; frame quanta {rep["frame_quanta"][:12]} ...; freeze mutants '
          f'{rep["freeze_mutants"]}')
    if rep.get('live_freeze_discrimination'):
        print(f'  live freeze discrimination: {rep["live_freeze_discrimination"]}; logical freeze proof: '
              f'{rep["logical_freeze_proof"]}')
    if 'death_ms' in rep:
        print(f'  freeze-span proxy: {rep["death_ms"]} ms between the writes of quanta {rep.get("death_pair_quanta")} '
              '(10 logical quanta = 1500 ms nominal; the logical freeze is proved by the model and the mutants)')
    print(f'  input reaction (wire AID -> first answering frame): {json.dumps(rep["reaction"])}')
    if 'gates' in rep:
        print(f'  candidate gates: {json.dumps(rep["gates"])}')
    print(f'  diagnostics: {json.dumps(rep.get("diag", {}))}')
    print(f'  TSO blocking-read CONTROL records (F1 C3, not game writes): {len(rep["tso_controls"])} '
          f'{[(c["aid"], c.get("card")) for c in rep["tso_controls"]]}')
    for n_ in rep.get('diag_notes', []):
        print(f'  diagnostic: {n_}')
    print('  note: terminal timestamps include host scheduling + TN3270E contention resolution + network; endpoint '
          'drift and trend are a live proxy, not the host-side drift')
    print(f'{a.case}: {rep["state"]}' + (f' - {"; ".join(rep["blocked"])}' if rep['blocked'] else ''))
    print(f'NEXT CASE ALLOWED: {"yes" if rep["state"] == PASS else "no"}' + (' (STOP)' if rep['stop'] else ''))
    sys.exit(0 if rep['state'] == PASS else 2)


if __name__ == '__main__':
    main()
