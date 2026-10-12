#!/usr/bin/env python3
"""MVS-HS independent model (D38, docs/HS-HISCORE.md): the persistent ARCADE high score, written from the design
text only (no COBOL is read). A member is None (missing) or a list of 80-byte records; a PDS is a dict of members
plus a 'full' flag (directory full: a new member cannot be added).

dd kinds: None = no PACHS DD (not configured), ('M', member) = a member of the PDS, 'NOMEM' / 'DUMMY' = unusable.
"""
TAG = 'PACHS001'


def record(score, level):
    return f'{score:07d} {TAG} {level:03d}'.ljust(80)


def parse(rec):
    """(score, level) of a valid record, else None (D38: columns 1-7 digits, 9-16 the tag, 18-20 digits)."""
    rec = rec.ljust(80)
    if rec[0:7].isdigit() and rec[8:16] == TAG and rec[17:20].isdigit():
        return int(rec[0:7]), int(rec[17:20])
    return None


class Pds:
    def __init__(self, members=None, full=False):
        self.members = dict(members or {})
        self.full = full

    def read(self, dd):
        """-> (state, score, level): N not configured, E unavailable, R loaded, Z zero (missing / empty / malformed)."""
        if dd is None:
            return 'N', 0, 0
        if not (isinstance(dd, tuple) and dd[0] == 'M'):
            return 'E', 0, 0
        recs = self.members.get(dd[1])
        if not recs or parse(recs[0]) is None:
            return 'Z', 0, 0
        return ('R',) + parse(recs[0])

    def write(self, member, state, rec):
        """True when saved. R: the first record replaced in place; Z: the member becomes the one record (added or
        replaced; adding fails when the directory is full)."""
        recs = self.members.get(member)
        if state == 'R' and recs:
            self.members[member] = [rec] + recs[1:]
            return True
        if recs is None and self.full:
            return False
        self.members[member] = [rec]
        return True


def end_lines(pds, dd, score, level, start, arcade=True):
    """The HS end lines of one game, and the PDS updated as the game leaves it."""
    if not arcade:
        return []
    state, hi, hl = pds.read(dd)
    if state == 'N':
        return []
    if state == 'E':
        return ['HIGH SCORE UNAVAILABLE']
    out, extra = (score, level) if score > hi else (hi, hl), []
    if score > hi:
        if start != 1:
            extra = [f'START LEVEL {start:02d}: HIGH SCORE NOT RECORDED']
        elif pds.write(dd[1], state, record(score, level)):
            extra = ['NEW HIGH SCORE']
        else:
            extra = ['HIGH SCORE NOT SAVED']
    return [f'HIGH SCORE {out[0]:07d} LEVEL {out[1]:03d}'] + extra


def final(out):
    """(score, level) from the end lines of a game's text output."""
    score = [int(l[6:]) for l in out if l.startswith('SCORE ') and l[6:].isdigit()][-1]
    level = [int(l[6:]) for l in out if l.startswith('LEVEL ') and l[6:].isdigit()][-1]
    return score, level


if __name__ == '__main__':
    p = Pds()
    assert end_lines(p, ('M', 'X'), 1310, 1, 1) == ['HIGH SCORE 0001310 LEVEL 001', 'NEW HIGH SCORE']
    assert end_lines(p, ('M', 'X'), 1310, 1, 1) == ['HIGH SCORE 0001310 LEVEL 001']
    assert end_lines(p, ('M', 'X'), 9000, 9, 9) == ['HIGH SCORE 0009000 LEVEL 009',
                                                     'START LEVEL 09: HIGH SCORE NOT RECORDED']
    assert p.members['X'] == [record(1310, 1)]
    assert end_lines(Pds(full=True), ('M', 'Y'), 5, 1, 1)[-1] == 'HIGH SCORE NOT SAVED'
    assert end_lines(p, None, 5, 1, 1) == [] and end_lines(p, 'DUMMY', 5, 1, 1) == ['HIGH SCORE UNAVAILABLE']
    print('ref_hs self-check PASS')
