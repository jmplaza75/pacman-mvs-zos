#!/usr/bin/env python3
"""ZOS-11 (2.1-zos, D46; docs/zos11-design.md) local checks - no z/OS access.
1. Product delta: PACINPT RT-TSC decode table = the 2.1 table (PF7 U, PF8 D, PF10 L, PF12 R, PF9 P, PA2 RDR; PF11
   falls to IGN); PACINPT and src/zos/PACMAN.clist = zos-10 (2.0-zos) except exactly the D46 lines (tests/zos_c2.py
   d46_strip), so TURN, the card / batch path, QUIT and every other key are byte-identical; QUIT only from Q + ENTER.
2. Frozen tools: the ZOS-6 live tools, the ZOS-6 fixture and every ZOS-5..10 checker = zos-10 (successor:
   tools/zowe/zos11_live.py).
3. The live gate on synthetic z/OS traces (tests/zos6_fixture.py, the COALESCED host simulation, used in-process with
   the 2.1 key map): the 2.1 product PASSES in both Q variants (A: the typed Q survives, ENTER quits; B: a host write
   erased it, the blank ENTER redraws, a fresh Q + ENTER quits); each fault FAILS by its rule: the 2.0 product, PF12
   ignored, PF11 still Right, PF3 / PF11 / PF12 quitting, an inbound record during the Q hold, a Q-alone quit (no game
   writes during the hold), PF12 sent as ENTER + field.
4. The plan: PF12, PF11, the full PF1-PF24 sweep, PF9 pause / resume, PA2, TYPEQ + hold, Q + ENTER, a >= 200-quantum
   idle segment; RULES(CLASSIC), no PLAY / PRESENT operand (the installed REALTIME default COALESCED)."""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R / 'tests'), str(R / 'tools/zowe')]
import zos_c2  # noqa: E402
import zos6_drive as D  # noqa: E402
import zos6_fixture as FX  # noqa: E402
import zos11_live as Z  # noqa: E402


def git(*a):
    return subprocess.run(['git', *a], cwd=R, capture_output=True, text=True, check=True).stdout


# 1. product delta -----------------------------------------------------------------------------------------------------
inp = (R / 'src/cobol/PACINPT.cob').read_text()
rt = inp[inp.index('       RT-TSC.'):inp.index('       RT-TSC-EXIT.')]
table = {int(v): c for v, c in re.findall(r"IF WS-V = (\d+)\n\s+MOVE '(\w)' TO RT-C\n\s+PERFORM RT-CHAR\.", rt)}
table.update({int(v): 'RDR' for v in re.findall(r"IF WS-V = (\d+)\n\s+MOVE 'RDR' TO REQ-KIND\.", rt)})
assert table == {247: 'U', 248: 'D', 122: 'L', 124: 'R', 249: 'P', 110: 'RDR'}, table
assert 123 not in table and rt.index("MOVE 'IGN' TO REQ-KIND.") < rt.index('IF WS-V =')
for rel in ('src/cobol/PACINPT.cob', 'src/zos/PACMAN.clist'):
    assert zos_c2.d46_strip(rel, (R / rel).read_text()) == git('show', f'zos-10:./{rel}'), rel
changed = set(git('diff', '--name-only', '--relative', 'zos-10', '--', 'src').splitlines())
assert changed == {'src/cobol/PACINPT.cob', 'src/zos/PACMAN.clist'}, changed
assert inp.count("MOVE 'QUI' TO REQ-KIND") == 1 and set(table.values()) <= {'U', 'D', 'L', 'R', 'P', 'RDR'}
assert "IF REQ-INKEY = 'E'\n               PERFORM RT-ENTER THRU RT-ENTER-EXIT" in rt
print('product: PACINPT decode table PF12 R, PF11 IGN, others unchanged; PACINPT and the z/OS CLIST = zos-10 except '
      'exactly the D46 lines; QUIT only Q + ENTER: PASS')

# 2. frozen tools ------------------------------------------------------------------------------------------------------
FROZEN = ['tools/zowe/zos6_drive.py', 'tools/zowe/zos6_live_check.py', 'tests/zos6_fixture.py', 'tests/zos5_fixture.py',
          'tools/zowe/zos5_live_check.py', 'tools/zowe/zos7_live_check.py', 'tools/zowe/zos8_live_check.py',
          'tools/zowe/zos9_equiv.py', 'tools/zowe/zos_equiv.py', 'tests/ref_rt.py', 'tests/oracle20', 'src/clist',
          'src/copy', 'src/asm', 'jcl/zos', 'releases/2.0-MVS-MAX', 'releases/2.0-ZOS']
Z11DECKS = [f'jcl/zos/PACZ11{n}.jcl' for n in ('AL', 'BL', 'C1', 'C2', 'PV', 'IP', 'IC', 'ZD', 'P1')]  # zos11_release
for p in FROZEN:
    ex = [f':!{d}' for d in Z11DECKS] if p == 'jcl/zos' else []
    assert subprocess.run(['git', 'diff', '--quiet', 'zos-10', '--', p, *ex], cwd=R).returncode == 0, f'{p} != zos-10'
assert set(git('diff', '--name-only', '--relative', 'zos-10', '--', 'jcl/zos').split()) <= set(Z11DECKS)
assert 'PF11' in D.EXPECT and D.EXPECT['PF11'] == (0x7B, 'R') and 'PF12' not in D.EXPECT, 'frozen ZOS-6 map'
print(f'frozen: {len(FROZEN)} ZOS-5..10 tools / fixtures / oracles / decks / releases = zos-10 (the ZOS-6 map still '
      'PF11 = R); successor tools/zowe/zos11_live.py: PASS')

# 4. the plan ----------------------------------------------------------------------------------------------------------
st = Z.STEPS
acts = [v for k, v in st if k in ('gameplay', 'ignored', 'hold')]
assert Z.KW == 'AI(0) RULES(CLASSIC) SOUND(NO)' and 'PLAY' not in Z.KW and 'PRESENT' not in Z.KW
assert {f'PF{n}' for n in range(1, 25)} - {'PF7', 'PF8', 'PF9', 'PF10', 'PF12'} <= set(acts)
assert acts.count('PF12') >= 2 and acts.count('PF11') >= 2 and acts.count('PF9') == 2 and 'PA2' in acts
assert acts[-2:] == ['TYPEQ', 'QENTER'] and st[st.index(('hold', 'TYPEQ')) + 1][0] == 'wait'
assert max(v for k, v in st if k == 'wait') * 1000 / Z.PLAN['T'] >= 200, 'a >= 200-quantum idle segment'
print('plan Z11: CLASSIC, no PLAY / PRESENT; PF8 PF10 PF11 PF12 PF7 PF9 PF9 PA2, PF1-PF24 sweep, PF12, 40 s idle, '
      'TYPEQ + 3 s hold, Q + ENTER: PASS')


# 3. the gate on synthetic traces --------------------------------------------------------------------------------------
def synth(card=None, variant='A', quit_on=None, extra_in_hold=False, q_alone=False, pf12_field=False, waits=None):
    """(trace, driver log) of the Z11 plan on a simulated COALESCED z/OS host whose game decodes the keys as `card`
    (key -> card character; default: the 2.1 product)."""
    card = card or {}
    steps = []
    for k, v in Z.STEPS:
        if k == 'ignored':
            steps.append(('gameplay', v))
        elif k == 'hold':
            steps.append(('wait', 0))
        elif v == 'QENTER':
            steps += [('gameplay', 'Q')] if variant == 'A' else [('gameplay', 'ENTER()'), ('wait', 3),
                                                                 ('gameplay', 'Q')]
        else:
            steps.append((k, v))
        if quit_on and (k, v) in (('gameplay', quit_on), ('ignored', quit_on)):
            steps += [('expect', '***'), ('closure', 'ENTER'), ('expect', 'SHELL')]
            break
    if extra_in_hold:
        i = len(steps) - 1 - steps[::-1].index(('wait', 0))
        steps[i + 1:i + 1] = [('wait', 1), ('gameplay', 'PF1')]
    plan = dict(Z.PLAN, steps=steps)
    saved_e, saved_c, saved_aid = dict(D.EXPECT), dict(FX.CARD), FX.aid_bytes
    try:
        for k, a in Z.PF_AID.items():
            D.EXPECT[k] = (a, '.')
            FX.CARD[k] = '.'
        D.EXPECT.update({'PF7': (0xF7, 'U'), 'PF8': (0xF8, 'D'), 'PF9': (0xF9, 'P'), 'PF10': (0x7A, 'L'),
                         'ENTER()': (0x7D, '*')})
        FX.CARD.update({'PF7': 'U', 'PF8': 'D', 'PF9': 'P', 'PF10': 'L', 'PF12': 'R', 'ENTER()': '*'})
        FX.CARD.update(card)
        if quit_on:
            FX.CARD[quit_on] = 'Q'

        def aid_bytes(action):
            if action == 'ENTER()':
                return bytes([0x7D, 0x5B, 0x6F, 0x11, 0x5B, 0x60])
            if action == 'PF12' and pf12_field:
                return bytes([0x7D, 0x5B, 0x6F, 0x11, 0x5B, 0x60]) + FX.e('R')
            return saved_aid(action)
        FX.aid_bytes = aid_bytes
        text, log_lines = FX.build(Z.CASE, plan=plan, waits=waits)
    finally:
        D.EXPECT.clear()
        D.EXPECT.update(saved_e)
        FX.CARD.clear()
        FX.CARD.update(saved_c)
        FX.aid_bytes = saved_aid
    log = [json.loads(x) for x in log_lines]
    ign = {v for k, v in Z.STEPS if k == 'ignored'}
    for x in log:
        if x['action'] in ign and x['category'] == 'gameplay':
            x['category'] = 'ignored'
    if not quit_on:                               # the hold: TYPEQ just before the ENTER, the 3 s hold after it
        enter = next(i for i, x in enumerate(log) if x['category'] == 'gameplay' and x['action'] in ('Q', 'ENTER()')
                     and i > len(log) - 5)
        if extra_in_hold:
            enter -= 1
        t = log[enter]['sent'] - (300 if q_alone else 3000) - (1000 if extra_in_hold else 0)
        log.insert(enter, {'ordinal': 0, 'category': 'hold', 'action': 'TYPEQ', 'requested': t, 'wait_start': t,
                           'unlocked': t, 'sent': t, 'result': 'ok'})
    for n, x in enumerate(log, 1):
        x['ordinal'] = n
    return text, [json.dumps(x) for x in log]


def gate(tr):
    return Z.gate(tr[0], tr[1], epoch=False)


for variant in ('A', 'B'):
    ok, res, det, blocked, rep = gate(synth(variant=variant))
    assert ok, (variant, [k for k, v in res.items() if not v], det)
    print(f'2.1 product, Q variant {variant}: every criterion PASS ({rep["writes"]} writes, end {rep["end_lines"][0]}, '
          f'{len(det["pf_aids"])} PF AIDs, {det["writes TYPEQ->ENTER"]} writes in the Q hold)')
plan = dict(Z.PLAN, steps=[(k, v) for k, v in Z.STEPS])
FAULTS = {   # fault -> (synthetic trace, the criterion that must FAIL)
    '2.0 product (PF11 Right, PF12 nothing)': (synth({'PF11': 'R', 'PF12': '.'}), 'every live write'),
    'PF12 ignored': (synth({'PF12': '.'}), 'every live write'),
    'PF11 still Right': (synth({'PF11': 'R'}), 'every live write'),
    'PF3 quits': (synth(quit_on='PF3'), 'the game wrote on after every PF AID'),
    'PF11 quits': (synth(quit_on='PF11'), 'the game wrote on after every PF AID'),
    'PF12 quits': (synth(quit_on='PF12'), 'the game wrote on after every PF AID'),
    'an inbound record during the Q hold': (synth(extra_in_hold=True), 'TYPEQ -> ENTER'),
    'Q alone quits (no game writes during the hold)': (synth(q_alone=True), 'TYPEQ -> ENTER'),
    'PF12 sent as ENTER + field': (synth(pf12_field=True), 'PF12 reached the host as AID-only'),
}
for why, (tr, crit) in FAULTS.items():
    ok, res, det, blocked, rep = gate(tr)
    failed = [k for k, v in res.items() if not v]
    assert not ok and any(k.startswith(crit) for k in failed), (why, failed)
    print(f'   FAIL as required: {why} -> {next(k for k in failed if k.startswith(crit))}')
print(f'live gate on synthetic z/OS traces: 2.1 PASSES (variants A, B), {len(FAULTS)} faults FAIL by their rule: PASS')

# 5. step 2A tooling: decks PACZ11AL / BL / C1 / C2 (new prefix RZ21 only), audits, the D46 object rule ---------------
import zos11_release as Z11  # noqa: E402
ok, res, det = Z11.selftest()
assert ok, ([k for k, v in res.items() if not v], [k for k, v in det.items() if not v])
print(f'zos11_release selftest: {len(res)} checks PASS, {len(det)} injected faults detected: PASS')
print('ZOS-11 LOCAL CHECKS PASS')
