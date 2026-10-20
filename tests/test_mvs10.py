#!/usr/bin/env python3
"""MVS-10 (D46, docs/MVS10-PF12.md section 5) local checks of the PF12 change - no host access.
1. PACINPT RT-TSC (the only AID decoder): the decode table parsed from the source = the independent 2.1 table
   (PF7 U, PF8 D, PF10 L, PF12 R, PF9 P, PA2 RDR); PF11 (123) is not in it and falls to the IGN set before the table;
   PACINPT = 2.0-mvs-max except exactly the two MVS-10 lines (so TURN, the card / batch path and every other AID are
   byte-identical).
2. QUIT: no AID maps to Q; QUI only from the character Q in RT-CHAR, reached in REALTIME only through RT-ENTER (the
   ENTER AID with the typed field); POLL without an AID = NON (a typed Q alone is no event).
3. CLIST: 2.0-mvs-max except the one help-comment line (statements, defaults, PARM unchanged); every line <= 72.
4. c3270 keymap: Right arrow -> PF(12), PF(11) nowhere, UP / DOWN / LEFT / p unchanged, diff = the MVS-10 lines.
5. The live scenario on the models (tests/mvs10live/make_live10.py): discriminating PF11 / PF12, QUIT by Q + ENTER.
6. The live checker (tools/mvs10_trace.py) on synthetic traces built from the models: the 2.1 product PASSES; the 2.0
   product, PF12 ignored, PF11 still Right, a PF key quitting, Q quitting without ENTER, an inbound record during the
   Q hold, PF12 sent with a field, QUIT by another command - each FAILS.
7. Regressions: every other local test (phase tests with PACMAN_LATER_PHASE=G8, as tools/release_check.sh 2.0)."""
import os
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tools'))
sys.path.insert(0, str(R / 'tests/mvs10live'))
import mvs10_delta as m10  # noqa: E402
import make_live10 as S  # noqa: E402
import mvs10_trace as T  # noqa: E402

BASE = '2.0-mvs-max'


def git_show(path):
    return subprocess.run(['git', 'show', f'{BASE}:./{path}'], cwd=R, capture_output=True, text=True,
                          check=True).stdout


# 1. PACINPT decode table ---------------------------------------------------------------------------------------------
inp = (R / 'src/cobol/PACINPT.cob').read_text()
rt = inp[inp.index('       RT-TSC.'):inp.index('       RT-TSC-EXIT.')]
table = {int(v): c for v, c in re.findall(r"IF WS-V = (\d+)\n\s+MOVE '(\w)' TO RT-C\n\s+PERFORM RT-CHAR\.", rt)}
table.update({int(v): 'RDR' for v in re.findall(r"IF WS-V = (\d+)\n\s+MOVE 'RDR' TO REQ-KIND\.", rt)})
assert table == {247: 'U', 248: 'D', 122: 'L', 124: 'R', 249: 'P', 110: 'RDR'}, table     # PF7 PF8 PF10 PF12 PF9 PA2
assert 123 not in table and rt.count('IF WS-V =') == 6, 'PF11 (X\'7B\') must not be decoded'
assert rt.index("MOVE 'IGN' TO REQ-KIND.") < rt.index('IF WS-V ='), 'an undecoded AID stays IGN'
assert m10.m10_strip('src/cobol/PACINPT.cob', inp) == git_show('src/cobol/PACINPT.cob'), 'PACINPT delta not exact'
old_rt = git_show('src/cobol/PACINPT.cob')
assert re.search(r"IF WS-V = 123\n\s+MOVE 'R' TO RT-C", old_rt), '2.0 baseline: PF11 was Right'
print('PACINPT: decode table PF7 U, PF8 D, PF10 L, PF12 R, PF9 pause, PA2 redraw; PF11 -> IGN; '
      'diff vs 2.0-mvs-max = exactly the statement + comment: PASS')

# 2. QUIT only by Q + ENTER --------------------------------------------------------------------------------------------
assert set(table.values()) <= {'U', 'D', 'L', 'R', 'P', 'RDR'}, 'no AID may decode to Q'
assert "IF REQ-INKEY = 'E'\n               PERFORM RT-ENTER THRU RT-ENTER-EXIT" in rt, 'ENTER -> the typed field'
assert "IF REQ-INKEY = 'N'\n               GO TO RT-TSC-EXIT." in rt and rt.index("MOVE 'NON' TO REQ-KIND.") < \
    rt.index("IF REQ-INKEY = 'N'"), 'no AID (POLL) = NON: a typed Q alone is no event'
ch = inp[inp.index('       RT-CHAR.'):inp.index('       NORMALIZE.')]
assert "MOVE RT-C TO CMD-CHAR\n               PERFORM CLASSIFY THRU CLASSIFY-EXIT." in ch, 'RT-CHAR -> CLASSIFY'
cls = inp[inp.index('       CLASSIFY.'):inp.index('       CLASSIFY-EXIT.')]
assert inp.count("MOVE 'QUI' TO REQ-KIND") == 1 and \
    "ELSE IF CMD-CHAR = 'Q' OR CMD-CHAR = 'q'\n               MOVE 'QUI' TO REQ-KIND" in cls, 'QUI only from Q'
# REALTIME terminal callers of RT-CHAR: the AID table (U D L R P only) and RT-ENTER (the ENTER field) - so a Q, i.e.
# QUIT, comes only from the typed field sent with ENTER; RT-CARD-CHAR is the batch / TSD card path (unchanged)
paras = [(m.start(), m.group(1)) for m in re.finditer(r'^       ([A-Z0-9-]+)\.$', inp, re.M)]
owner = lambda pos: [n for s, n in paras if s < pos][-1]          # noqa: E731
rt_callers = sorted({owner(m.start()) for m in re.finditer(r'PERFORM RT-CHAR', inp)})
assert rt_callers == ['RT-CARD-CHAR', 'RT-ENTER', 'RT-TSC'], rt_callers
print('QUIT: no AID decodes to Q; Q -> QUI only from the ENTER field (or a batch card); no AID = no event: PASS')

# 3. CLIST -------------------------------------------------------------------------------------------------------------
cl = (R / 'src/clist/PACMAN.clist').read_text()
assert m10.m10_strip('src/clist/PACMAN.clist', cl) == git_show('src/clist/PACMAN.clist'), 'CLIST delta not exact'
assert 'PF7/8/10/12' in cl and 'PF7/8/10/11' not in cl
assert all(len(l) <= 72 for l in cl.replace('@@PREFIX@@', 'HERC01.PACMAN').splitlines())
print('CLIST: 2.0-mvs-max except the ARROWS help comment (PF7/8/10/12); statements and defaults unchanged: PASS')

# 4. keymap ------------------------------------------------------------------------------------------------------------
sh = (R / 'tools/c3270_rt.sh').read_text()
km = re.search(r"KEYMAP='([^']*)'", sh).group(1)
assert km == r'<Key>UP: PF(7)\n<Key>DOWN: PF(8)\n<Key>LEFT: PF(10)\n<Key>RIGHT: PF(12)', km
assert 'PF(11)' not in sh and "GAMEKEYS='<Key>p: PF(9)\\n<Key>P: PF(9)'" in sh
old_sh = git_show('tools/c3270_rt.sh')
assert re.search(r"KEYMAP='([^']*)'", old_sh).group(1).replace('PF(11)', 'PF(12)') == km
assert [l for l in old_sh.splitlines() if not l.startswith('#') and 'KEYMAP=' not in l] == \
    [l for l in sh.splitlines() if not l.startswith('#') and 'KEYMAP=' not in l], 'launcher code changed'
assert 'arrows = PF7/8/10/12' in (R / 'tools/rt_play.py').read_text()
print('c3270 keymap: Right arrow -> PF(12) (was PF(11)), UP / DOWN / LEFT / p unchanged, no other code change: PASS')

# 5. the live scenario on the models -----------------------------------------------------------------------------------
res = S.check()
assert all(res.values()), res
assert (R / 'tests/mvs10live/LIVE10.txt').read_text().split() == S.CFG.split() + S.TOKENS, 'LIVE10.txt stale'
print(f'scenario LIVE10 on the models: {len(res)} checks PASS (2.0 map diverges after PF11, PF12 moves the game, '
      f'QUIT only by Q + ENTER)')

# 6. the live checker on synthetic traces ------------------------------------------------------------------------------
AID = {f'PF{n}': 0xF0 + n for n in range(1, 10)} | {'PF10': 0x7A, 'PF11': 0x7B, 'PF12': 0x7C, 'PA2': 0x6E} | \
    {f'PF{n}': 0xC1 + n - 13 for n in range(13, 22)} | {'PF22': 0x4A, 'PF23': 0x4B, 'PF24': 0x4C}
CUR, EOR = b'\x5b\x60', b'\xff\xef'


def synth(tokens=S.TOKENS, product=S.MAP21, hold=S.HOLD, quit_on=None, enter_text='Q', extra_in=False,
          pf12_field=False, stop_in_hold=False):
    """(writes, inbound, end_k, log) of a game played with `tokens` on a product decoding with `product`."""
    cs, inbound, log, j, t0 = [], [], [], 0, 100000
    tw = lambda k: t0 + 150 * k                                    # noqa: E731
    typed = False
    for tok in tokens:
        if tok == 'TYPEQ':
            log.append({'token': tok, 't': tw(j) + 10})
            if extra_in:
                inbound.append((tw(j) + 300, bytes([0xF1]) + CUR + EOR))
            if stop_in_hold:
                break
            cs += ['.'] * hold
            j += hold
            typed = True
            continue
        if tok == 'ENTER':
            log.append({'token': tok, 't': tw(j) + 10})
            inbound.append((tw(j) + 20, bytes([0x7D]) + CUR + b'\x11\x5b\x61' + enter_text.encode('cp037') + EOR))
            cs.append(enter_text if typed else '*')
            j += 1
            break
        rec = bytes([AID[tok]]) + CUR + EOR
        if tok == 'PF12' and pf12_field:
            rec = bytes([0x7D]) + CUR + b'\x11\x5b\x61' + 'R'.encode('cp037') + EOR
        inbound.append((tw(j) + 20, rec))
        if tok == quit_on:
            cs.append('Q')
            j += 1
            break
        cs.append(product.get(tok, '.'))
        j += 1
    end, fs = S.run(cs)
    writes = [(tw(k), f) for k, f in enumerate(fs)]
    return writes, inbound, (len(writes) - 1 if end[:1] == ['QUIT'] else None), log


ok, r, det = T.gate(*synth())
assert ok, (r, det)
faults = {   # fault -> (synthetic trace, the criterion that must FAIL)
    '2.0 product (PF11 Right, PF12 ignored)': (synth(product=S.MAP20), 'control: the 2.0 map'),
    'PF12 ignored': (synth(product={k: v for k, v in S.MAP21.items() if k != 'PF12'}), 'control: PF12 ignored'),
    'PF11 still Right': (synth(product=dict(S.MAP21, PF11='R')), 'control: PF11 as Right'),
    'PF3 quits': (synth(quit_on='PF3'), 'the game went on after every PF AID'),
    'PF12 quits': (synth(quit_on='PF12'), 'the game went on after every PF AID'),
    'PF11 quits': (synth(quit_on='PF11'), 'the game went on after every PF AID'),
    'Q alone quits (no writes during the hold)': (synth(stop_in_hold=True), 'TYPEQ -> ENTER'),
    'an inbound record during the Q hold': (synth(extra_in=True), 'TYPEQ -> ENTER'),
    'PF12 sent as ENTER + field': (synth(pf12_field=True), 'PF12 reached the host as an AID-only record'),
    'the game ended by ENTER with another command': (synth(enter_text='X'), 'the last inbound record before the end'),
}
for why, (tr, crit) in faults.items():
    ok, r, _ = T.gate(*tr)
    failed = [k for k, v in r.items() if not v]
    assert not ok and any(k.startswith(crit) for k in failed), (why, failed)
    print(f'   FAIL as required: {why} -> {next(k for k in failed if k.startswith(crit))}')
print(f'live checker on synthetic traces: the 2.1 product PASSES ({det["live writes"]} writes, '
      f'end {det["end lines"][0]}),'
      f' {len(faults)} faults FAIL: PASS')

# accepted 2.0 live evidence (MVS-S2 S2E, docs/evidence/s2-live.md, local trace outside git): the checker's parser and
# replay reproduce it with the 2.0 map (PF11 = Right, as played then) and reject it with the 2.1 map
s2 = Path.home() / 's2-live.txt'
if s2.is_file():
    w, inb, _, _ = T.parse(str(s2), '224150')
    n20, f20, _, _ = T.replay(w, inb, T.MAP20)
    n21, f21, _, _ = T.replay(w, inb, T.MAP21)
    assert n20 == len(w) == len(f20) == 185 and n21 < len(w), (n20, n21, len(w))
    print(f'accepted S2E live trace (2.0): 2.0 map {n20} / {len(w)} identical, 2.1 map {n21} / {len(w)}: PASS')
else:
    print('accepted S2E live trace: ~/s2-live.txt not present here (local evidence) - SKIPPED')

# 7. regressions -------------------------------------------------------------------------------------------------------
LATER = {'test_gp1', 'test_gp2', 'test_hs', 'test_rp', 'test_rt', 'test_s1', 'test_s2'}
bad = []
for t in sorted((R / 'tests').glob('test_*.py')):
    if t.stem == 'test_mvs10':
        continue
    env = dict(os.environ, **({'PACMAN_LATER_PHASE': 'G8'} if t.stem in LATER else {}))
    if subprocess.run([sys.executable, str(t)], cwd=R, env=env, capture_output=True).returncode:
        bad.append(t.stem)
assert not bad, bad
print('regressions: every other local test PASS (models, 1.0 / 2.0 TSD streams, core frozen, TURN, batch)')
print('MVS-10 LOCAL CHECKS PASS')
