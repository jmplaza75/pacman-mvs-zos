#!/usr/bin/env python3
"""MVS-10 (D46, docs/MVS10-PF12.md section 6): the deterministic live scenario of the PF12 gate, played by
tools/mvs10_live.py through the c3270 script port and checked by tools/mvs10_trace.py. RULES(CLASSIC) AI(0) GHOSTS(1)
SOUND(NO), NORMAL (CLASSIC: no high-score path). One token per line after the config card; one AID per quantum except
TYPEQ (types Q in the command field, no AID, then holds) - the tokens:
  PF7 PF8 PF10 PF12  U D L R (PF12 = Right in 2.1)      PF9   pause / resume       PA2  redraw
  PF11 and PF1-PF6, PF13-PF24: no input in 2.1 (PF11 was Right in 2.0)              TYPEQ  Q typed, no AID
  ENTER  the ENTER AID (with the typed Q: QUIT)
cards(tokens, MAP21 / MAP20) gives the model cards; the hold of TYPEQ is HOLD idle quanta on the models (live: what the
trace shows). Checks on the models (make_live10.py --check, tests/test_mvs10.py): the 2.1 replay ends with QUIT after
the ENTER, the game runs through every PF token; the 2.0 map gives a different stream first at the write after PF11
(2.0 would reverse to the right), and PF12 changes the stream at the write after it (dropping it changes the game).
Usage: make_live10.py [--write] [--check]"""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(R / 'tests'))
sys.path.insert(0, str(R / 'tests/s2live'))
import make_live as M  # noqa: E402

CFG = 'AI0 1'
WORDS = 'RULES(CLASSIC) AI(0) GHOSTS(1) SOUND(NO)'
HOLD = 20                                       # idle quanta of the TYPEQ hold on the models (3 s at 150 ms)
IGNORED = ['PF1', 'PF2', 'PF3', 'PF4', 'PF5', 'PF6', 'PF11'] + [f'PF{n}' for n in range(13, 25)]
TOKENS = (['PF8', 'PF8', 'PF8', 'PF10', 'PF1', 'PF1', 'PF11', 'PF1', 'PF1', 'PF1', 'PF12', 'PF1', 'PF1', 'PF1',
           'PF7', 'PF1', 'PF9', 'PF9', 'PF1', 'PA2', 'PF1']
          + IGNORED + ['PF12', 'PF1', 'PF12', 'PF1', 'PF11', 'PF1', 'TYPEQ', 'ENTER'])
PF11_AT, PF12_AT = 6, 10                        # the discriminating PF11 / PF12 tokens (index in TOKENS)
MAP21 = {'PF7': 'U', 'PF8': 'D', 'PF10': 'L', 'PF12': 'R', 'PF9': 'P', 'PA2': '*'}
MAP20 = {'PF7': 'U', 'PF8': 'D', 'PF10': 'L', 'PF11': 'R', 'PF9': 'P', 'PA2': '*'}


def cards(tokens, mp, hold=HOLD):
    """Model cards (one per quantum): TYPEQ = hold idle quanta; ENTER after TYPEQ = Q, else a blank ENTER = redraw."""
    out, typed = [], False
    for t in tokens:
        if t == 'TYPEQ':
            out += ['.'] * hold
            typed = True
        elif t == 'ENTER':
            out.append('Q' if typed else '*')
            typed = False
        else:
            out.append(mp.get(t, '.'))
    return out


def run(cs):
    end, fs, _ = M.run('C', [CFG] + cs, 150)
    return end, fs


def first_diff(a, b):
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None if len(a) == len(b) else min(len(a), len(b)))


def check(tokens=TOKENS):
    """-> dict of named results (all True = the scenario discriminates and ends by Q + ENTER only)."""
    c21, c20 = cards(tokens, MAP21), cards(tokens, MAP20)
    (e21, f21), (_, f20) = run(c21), run(c20)
    k11, k12 = len(cards(tokens[:PF11_AT], MAP21)), len(cards(tokens[:PF12_AT], MAP21))
    drop = list(c21)
    drop[k12] = '.'
    d20, d12 = first_diff(f21, f20), first_diff(f21, run(drop)[1])
    return {'2.1 replay ends with QUIT after the last card (Q + ENTER)':
            e21[:1] == ['QUIT'] and len(f21) == len(c21) + 1,
            'tokens: PF11 / PF12 at the discriminating places': tokens[PF11_AT] == 'PF11' and tokens[PF12_AT] == 'PF12',
            f'2.0 map diverges first at the write after PF11 (write {k11 + 1})': d20 == k11 + 1,
            f'PF12 (Right) changes the stream at the write after it (write {k12 + 1})': d12 == k12 + 1,
            'only ENTER after TYPEQ is a Q card; no PF token is Q': [c for c in c21 if c == 'Q'] == ['Q'] and
            c21[-1] == 'Q',
            'every PF1-PF24 except PF7 PF8 PF9 PF10 PF12 is no input in 2.1': all(
                MAP21.get(f'PF{n}', '.') == '.' for n in range(1, 25) if n not in (7, 8, 9, 10, 12)),
            'PF7 PF8 PF9 PF10 PA2 as in 2.0': all(MAP21[k] == MAP20[k] for k in ('PF7', 'PF8', 'PF9', 'PF10', 'PA2'))}


def main():
    res = check()
    for k, v in res.items():
        print(f'{"PASS" if v else "FAIL"}  {k}')
    end, fs = run(cards(TOKENS, MAP21))
    print(f'{len(TOKENS)} tokens, {len(fs)} model writes (hold {HOLD}); end lines:', ' / '.join(end))
    if '--write' in sys.argv:
        (Path(__file__).parent / 'LIVE10.txt').write_text('\n'.join([CFG] + TOKENS) + '\n')
    return 0 if all(res.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
