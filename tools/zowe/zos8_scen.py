#!/usr/bin/env python3
"""ZOS-8 Services scenarios (docs/zos8-design.md, decisions U1-U12 of 2026-10-20): every batch / live case, its cards,
its EXEC operands, the dataset it may touch and the expected high-score state chain. Pure data + the independent
models (tests/ref_gp2.py, ref_hs.py, ref_mvs6.py, ref_gx_screen.py, ref_s2.py); nothing here touches z/OS.

Datasets (only <prefix> = Z00000.PACMAN, rendered from @@HLQ@@; the production DATA is never a target here):
- HS8.T1  test PDS with the exact DATA geometry (U2), created by B1, then Stage C;
- HSFULL.T1  existing ZOS-3 full-directory test PDS: live NOT SAVED (U8);
- HS8.NONE  a name that is never allocated: the CLIST guard falls back to DUMMY (UNAVAILABLE).
Stage C order (fail fast, U12) on HS8.T1 = 0000720 / 001 after B1:
  HL1 LEVEL(5) practice game beating it (P line, member unchanged) -> HL2 eligible 980 (NEW, WRIT in place) ->
  HL3 the same cards (tie: no write) -> HL4 eligible 1310 (NEW, WRIT) -> HL6 UNAVAILABLE (PACZ8HU) ->
  HL8 NOT SAVED (PACZ8HF on HSFULL.T1) -> HL7 = the read-only member check (one record 0001310 PACHS001 001).
HL5 (CLASSIC silent): not a separate game - CLASSIC never allocates PACHS (CLIST `&W = A` only) and the CLASSIC games
of ZOS-6 R1 / R2 and S8-C / the Stage D follow-up games end without a high-score line (checked there).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent
sys.path[:0] = [str(HERE), str(R / 'tests'), str(R / 'tools')]
import ref_gp2 as L  # noqa: E402
import ref_hs as H  # noqa: E402
import ref_mvs6 as M6  # noqa: E402
import ref_gx_screen as gx  # noqa: E402
import zos7_scen as SC7  # noqa: E402

PFX = '@@HLQ@@.PACMAN'
LIVE_DIR = 'zos8live'                     # tests/zos8live/<case>.txt: the exact cards of each live TURN game
STORES = {'T1': 'HS8.T1', 'FULL': 'HSFULL.T1', 'NONE': 'HS8.NONE'}
TEST_CLISTS = {'PACZ8HT': 'T1', 'PACZ8HU': 'NONE', 'PACZ8HF': 'FULL'}
B1_VALUE = H.record(720, 1)               # HS8.T1(HISCORE) after B1 (H3 GPREVB 720 / level 1)

# ---- B1 (batch, PGM=PACZ6D, BAT ARCADE LEVEL 1, DD PACHS = HS8.T1(HISCORE) SHR) --------------------------------------
B1_STEPS = [('H1', 'gpcases', 'GPTSO'),       # 370, member missing: REPL creates it, NEW HIGH SCORE
            ('H2', 'gpcases', 'GPTSO'),       # 370 = 370: tie, no write
            ('H3', 'gpcases', 'GPREVB'),      # 720 > 370: WRIT in place, NEW HIGH SCORE
            ('H4', 'gpcases', 'GPTSO')]       # 370 < 720: lower, member unchanged
B1_PARM = 'BAT                 A'             # columns 1-21 as the frozen MVS HS runs: mode BAT, RULES(ARCADE) col. 21


def cards_of(d, c):
    return (R / f'tests/{d}/{c}.txt').read_text().splitlines()


def b1_model():
    """[(step, expected SYSOUT lines, member records after the step)] from ref_gp2 (BAT) + ref_hs."""
    pds, out = H.Pds(), []
    for step, d, c in B1_STEPS:
        base = [l.rstrip() for l in L.simulate(cards_of(d, c), start=1)]
        hs = H.end_lines(pds, ('M', 'HISCORE'), *H.final(base), 1)
        out.append((step, base + hs, list(pds.members.get('HISCORE') or [])))
    return out


# ---- live TURN games: (source dir, source case, start level, rules) -> tests/zos8live/<name>.txt ------------------
KW_TAIL = 'PLAY(TURN) ANIM(NO) SOUND(NO) PRESENT(COALESCED)'
GAMES = {
    'HL1': ('gp2live', 'LIVEB', 5, 'A'),      # LEVEL(5): 2180 beats 720 -> START LEVEL 05: HIGH SCORE NOT RECORDED
    'HL2': ('gp2live', 'LIVEB', 1, 'A'),      # 980 > 720: NEW (WRIT)
    'HL3': ('gp2live', 'LIVEB', 1, 'A'),      # 980 = 980: tie
    'HL4': ('gpcases', 'GPAI0', 1, 'A'),      # 1310 > 980: NEW (WRIT)
    'HL6': ('cases', 'DIE1', 1, 'A'),         # PACZ8HU: no dataset -> DUMMY -> HIGH SCORE UNAVAILABLE
    'HL8': ('cases', 'DIE1', 1, 'A'),         # PACZ8HF: HSFULL.T1, HISCORE absent, 510 > 0 -> B14 -> NOT SAVED
    'GD': ('cases', 'DIE1', 1, 'C'),          # Stage D clean follow-up game: CLASSIC (no PACHS at all), a death
    'S8C': ('cases', 'WIN0', 1, 'C'),         # Stage E: CLASSIC TURN WIN, SOUND(YES): 1 + 4 bells, 3 bell-only writes
    'SF': ('gp2live', 'LIVEB', 1, 'A'),       # Stage F (frozen 2026-10-20): the production first write, installed
}                                             # CLIST(PACMAN) -> DATA(HISCORE) absent -> 980 NEW (REPL + STOW)
LIVE_ALIAS = {'SF': 'HL2'}                    # SF plays exactly HL2's validated LIVEB cards (no second card file)
# Stage F expected result (user decision 2026-10-20, option A): the high-score lines and the one production record
SF_LINES = ['HIGH SCORE 0000980 LEVEL 001', 'NEW HIGH SCORE']
SF_RECORD = H.record(980, 1)                  # '0000980 PACHS001 001' + blanks to 80 (FB 80)


def kw_of(name):
    d, c, start, rules = GAMES[name]
    ai, n, _ = gx.parse_config(cards_of(d, c))
    k = [f'AI({ai})'] + ([f'GHOSTS({n})'] if n != 1 else []) + (['RULES(CLASSIC)'] if rules == 'C' else []) + \
        ([f'LEVEL({start})'] if start != 1 else [])
    tail = KW_TAIL.replace('SOUND(NO)', 'SOUND(YES)') if name == 'S8C' else KW_TAIL
    return ' '.join(k) + ' ' + tail


def clist_of(name):
    return {'HL1': 'PACZ8HT', 'HL2': 'PACZ8HT', 'HL3': 'PACZ8HT', 'HL4': 'PACZ8HT', 'HL6': 'PACZ8HU',
            'HL8': 'PACZ8HF'}.get(name, 'PACMAN')


def raw_cards(name):
    d, c, _, _ = GAMES[name]
    return cards_of(d, c)


def model_frames(name, cards_dir=None, hs=None, snap=None, case=None):
    d, c, start, rules = GAMES[name]
    mk = (lambda ai, n: L.Level(ai, n, 'T', start)) if rules == 'A' else gx.Game
    return list(gx.frames(case or LIVE_ALIAS.get(name, name), True, False, 'P', 'G', '4', 'W', snap=snap, mk=mk,
                          d=cards_dir or LIVE_DIR, hs=hs if rules == 'A' else None))


def consumed(name):
    """The commands of the source case that the game consumes (one screen each, ANIM N; the game ends with Q / WIN /
    LOST, never EOF - a terminal has no end of file)."""
    d, c, start, rules = GAMES[name]
    cs = cards_of(d, c)
    fr = list(gx.frames(c, True, False, 'P', 'G', '4', 'W',
                        mk=(lambda ai, n: L.Level(ai, n, 'T', start)) if rules == 'A' else gx.Game, d=d,
                        hs=('Z', 0, start) if rules == 'A' else None))
    return [cs[0]] + cs[1:len(fr)]


def end_lines(name, cards):
    d, c, start, rules = GAMES[name]
    if rules == 'C':
        return M6.simulate(cards)[-4:]
    return L.simulate(cards, start=start)[-7:]


def make_live():
    """Write tests/zos8live/<name>.txt (the cards each live game sends); returns {name: cards}."""
    out = {}
    (R / 'tests' / LIVE_DIR).mkdir(exist_ok=True)
    for name in GAMES:
        if name in LIVE_ALIAS:
            continue
        cs = consumed(name)
        (R / 'tests' / LIVE_DIR / f'{name}.txt').write_text('\n'.join(cs) + '\n')
        out[name] = cs
    return out


def live_cards(name):
    return cards_of(LIVE_DIR, LIVE_ALIAS.get(name, name))


# ---- the high-score state chain of Stage C -------------------------------------------------------------------------
HL_ORDER = ['HL1', 'HL2', 'HL3', 'HL4', 'HL6', 'HL8']


def store_of(name):
    return TEST_CLISTS.get(clist_of(name))


def hl_chain():
    """[(case, store, record before or 'ABSENT', expected HS lines, record after or 'ABSENT')] from ref_hs, starting
    from HS8.T1 = B1_VALUE and HSFULL.T1 without HISCORE (full directory)."""
    t1 = H.Pds({'HISCORE': [B1_VALUE]})
    full = H.Pds(full=True)
    rows = []
    for name in HL_ORDER:
        st = store_of(name)
        pds = {'T1': t1, 'FULL': full}.get(st)
        before = (pds.members.get('HISCORE') or ['ABSENT'])[0].rstrip() if pds else 'n/a'
        cs = live_cards(name)
        out = end_lines(name, cs)
        start = GAMES[name][2]
        dd = 'DUMMY' if st == 'NONE' else ('M', 'HISCORE')
        hs = H.end_lines(pds or H.Pds(), dd, *H.final(out), start)
        after = (pds.members.get('HISCORE') or ['ABSENT'])[0].rstrip() if pds else 'n/a'
        rows.append((name, st, before, hs, after))
    return rows


def hs_tuple(name, before):
    """The Tracker hs tuple (REQ-HSST, persistent value, start level) the game reads at its start."""
    start, st = GAMES[name][2], store_of(name)
    if GAMES[name][3] == 'C':
        return None
    if st == 'NONE':
        return ('E', 0, start)
    if before == 'ABSENT':
        return ('Z', 0, start)
    s, v, _ = H.Pds({'HISCORE': [before.ljust(80)]}).read(('M', 'HISCORE'))
    return (s, v, start)


# ---- REALTIME sound cases (Stage E): the ZOS-7 L2 / L3 wall-stop scenario with SOUND(YES) --------------------------
S8_RT = {'S8A': 150, 'S8B': 125}
KW_S8 = 'AI(0) LEVEL(2) PLAY(REALTIME) SOUND(YES) PRESENT(COALESCED)'
S8_BELLS = {'S8A': [['START', 1], ['DEATH', 2], ['DEATH', 2], ['OVER', 3]],
            'S8B': [['START', 1], ['DEATH', 2], ['DEATH', 2], ['OVER', 3]],
            'S8C': [['START', 1], ['WIN', 4]]}
EXEC_MAX = 113          # the longest EXEC proven on the live ISPF Command Shell (ZOS-6 R2)


if __name__ == '__main__':
    if sys.argv[1:] == ['--make']:
        for k, v in make_live().items():
            print(f'tests/{LIVE_DIR}/{k}.txt: {len(v) - 1} commands')
    for row in hl_chain():
        print(row)
