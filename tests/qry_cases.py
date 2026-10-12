#!/usr/bin/env python3
"""MVS-G4 recorded Query Replies for the PACQRY batch test: the real c3270 reply captured by probe E9
(tests/qreply_c3270.hex, 180 bytes as TGET sees it) and variants derived from it, one capability removed or broken each.
cards() gives the SYSIN deck of PACQRYT (cols 1-8 name, 10-73 hex)."""
from pathlib import Path

R = Path(__file__).resolve().parent.parent
REAL = bytes.fromhex((R / 'tests/qreply_c3270.hex').read_text().strip())
P85, P86 = 46, 73                      # offsets of the X'85' and X'86' fields in REAL (0-based)


def sf_cut(b, p):
    n = int.from_bytes(b[p:p + 2], 'big')
    return b[:p] + b[p + n:]


def with85(b, body):
    sf = (len(body) + 4).to_bytes(2, 'big') + b'\x81\x85' + body
    return b[:P85] + sf + b[P85 + 27:]


def cases():
    r = REAL
    assert r[0] == 0x88 and r[P85 + 3] == 0x85 and r[P86 + 3] == 0x86 and len(r) == 180
    body = r[P85 + 4:P85 + 27]
    dbcs = (bytes([0x8E, 0x00, 0x09, 0x0C, 0, 0, 0, 0, 0x0B])
            + bytes([0x00, 0x00, 0x00, 0, 0, 0, 0]) + bytes.fromhex('02B90025')
            + bytes([0x01, 0x00, 0xF1, 0, 0, 0, 0]) + bytes.fromhex('03C30136')
            + bytes([0x80, 0x20, 0xF8, 0x12, 0x0C, 0x41, 0x7F]) + bytes.fromhex('00000000'))
    return [
        ('C3270', r),                                                   # the live reply: colour, highlight, GE
        ('NOALT', r[:P85 + 4] + b'\x02' + r[P85 + 5:]),                 # GE flag X'80' cleared
        ('NOGF', r[:P85 + 4] + b'\x80' + r[P85 + 5:]),                  # CGCSGID-present flag cleared
        ('NOCP310', r[:P85 + 25] + b'\x00\x25' + r[P85 + 27:]),         # second set is not code page 310
        ('NO85', sf_cut(r, P85)),                                       # no character-sets reply
        ('NOCOLOR', sf_cut(r, P86)),                                    # no colour reply (GE still parsed)
        ('NOTQRY', b'\x7D' + r[1:]),                                    # not a Query Reply (AID ENTER)
        ('TRUNC85', r[:P85 + 20]),                                      # reply ends inside the X'85' field
        ('DBCS', with85(r, dbcs)),                                      # x3270 DBCS form: 11-byte descriptors
        ('ONLY85', r[:1] + r[P85:P85 + 27]),                            # AID + X'85' only
        ('SHORTDL', with85(r, body[:8] + b'\x03' + body[9:])),          # descriptor length < 4: ignored
        ('EMPTY', b''),                                                 # nothing received
    ] + geometry_cases()


def rec(name):
    return bytes.fromhex((R / f'tests/qreply_{name}.hex').read_text().strip())


def geometry_cases():
    """MVS-GS: the replies recorded live by probe E12 (c3270 traces) and edge variants of the size fields."""
    m3, m4, m5, dyn = rec('m3'), rec('m4'), rec('m5'), rec('dyn')
    pa6 = REAL.find(b'\x81\xa6') - 2
    pua = REAL.find(b'\x81\x81') - 2
    assert pa6 > 0 and pua > 0
    return [
        ('M3', m3), ('M4', m4), ('M5', m5), ('DYN', dyn),                   # 80x32, 80x43, 132x27, 120x27
        ('NOA6', sf_cut(dyn, dyn.find(b'\x81\xa6') - 2)),                  # no X'A6': usable area 120x27 used
        ('NOA6UA', sf_cut(sf_cut(dyn, dyn.find(b'\x81\xa6') - 2), pua)),  # neither: 80x24
        ('A6SDP2', dyn[:pa6 + 7] + b'\x02' + dyn[pa6 + 8:]),              # A6 with another parameter id: usable
        ('TRUNCA6', dyn[:pa6 + 12]),                                      # reply ends inside X'A6': usable area
    ]


def expect(b):
    """Independent statement of the rule (docs/G4-GLYPHS.md 1 and 5): (colour, highlight, ge)."""
    c = h = g = 0
    if not b or b[0] != 0x88:
        return 0, 0, 0
    p = 1
    while p + 3 < len(b):
        n, qid, qc = int.from_bytes(b[p:p + 2], 'big'), b[p + 2], b[p + 3]
        if qid == 0x81 and qc == 0x86:
            c = 1
        if qid == 0x81 and qc == 0x87:
            h = 1
        if qid == 0x81 and qc == 0x85 and n > 13 and p + n <= len(b):
            f1, dl = b[p + 4], b[p + 12]
            if f1 & 0x80 and f1 & 0x02 and dl >= 4:
                d = p + 13
                while d + dl <= p + n:
                    if b[d + dl - 2:d + dl] == b'\x01\x36':
                        g = 1
                    d += dl
        if n < 4:
            break
        p += n
    return c, h, g


def expect_size(b):
    """Independent statement of the MVS-GS rule (docs/GS-GEOMETRY.md 4): alternate size from X'A6' (parameter 1),
    else the usable area X'81', else 80 x 24."""
    ua = ip = None
    if b and b[0] == 0x88:
        p = 1
        while p + 3 < len(b):
            n, qid, qc = int.from_bytes(b[p:p + 2], 'big'), b[p + 2], b[p + 3]
            if qid == 0x81 and qc == 0x81 and n > 9 and p + 10 <= len(b):
                ua = (int.from_bytes(b[p + 6:p + 8], 'big'), int.from_bytes(b[p + 8:p + 10], 'big'))
            if qid == 0x81 and qc == 0xA6 and n > 16 and p + 17 <= len(b) and b[p + 7] == 1:
                ip = (int.from_bytes(b[p + 13:p + 15], 'big'), int.from_bytes(b[p + 15:p + 17], 'big'))
            if n < 4:
                break
            p += n
    for v in (ip, ua):
        if v and 0 < v[0] < 1000 and 0 < v[1] < 1000:
            return v
    return 80, 24


def cards():
    out = ''
    for name, b in cases():
        hx = b.hex().upper()
        chunks = [hx[k:k + 64] for k in range(0, len(hx), 64)] or ['']
        out += ''.join(f'{name:<8} {c}\n' for c in chunks)
    for name, events in sequences():      # MVS-RP D40: one startup event per change of the column-9 digit
        for k, b in enumerate(events, 1):
            hx = b.hex().upper()
            chunks = [hx[i:i + 64] for i in range(0, len(hx), 64)] or ['']
            out += ''.join(f'{name:<8}{k % 10}{c}\n' for c in chunks)
    return out


# ---- MVS-RP D40 (docs/RP-POLISH.md 11): startup selection, written from the design ------------------------------
ENTER = bytes([0x7D, 0xC7, 0xE5])                                   # ENTER, cursor, no data (the RP.0 live record)
JUNK = bytes([0x7D, 0xC1, 0xF9, 0x11, 0xC1, 0xF9]) + 'ABC'.encode('cp037')   # ENTER with a typed field
PF9, PA2, CLEAR = bytes([0xF9, 0xC1, 0xF9]), bytes([0x6E]), bytes([0x6D])


def valid(b):
    """A structurally valid Query Reply: >= 5 bytes, AID X'88', an exact chain of fields (length >= 4, ID X'81')
    to the last byte, the first one Summary (QCODE X'80')."""
    if len(b) < 5 or b[0] != 0x88:
        return False
    p, n = 1, 0
    while p < len(b):
        if p + 4 > len(b):
            return False
        ln = int.from_bytes(b[p:p + 2], 'big')
        if ln < 4 or p + ln > len(b) or b[p + 2] != 0x81 or (n == 0 and b[p + 3] != 0x80):
            return False
        p, n = p + ln, n + 1
    return n > 0


def select(events):
    """(action, rejected records, empty reads, (colour, highlight, ge)): A on the first valid reply; F after 8
    rejected records or 6 empty reads; R if the events end first."""
    nrec = nwait = 0
    for b in events:
        if valid(b):
            return 'A', nrec, nwait, expect(b)
        if b:
            nrec += 1
        else:
            nwait += 1
        if nrec >= 8 or nwait >= 6:
            return 'F', nrec, nwait, (0, 0, 0)
    return 'R', nrec, nwait, (0, 0, 0)


def sequences():
    r = REAL
    over = (500).to_bytes(2, 'big') + r[3:]
    first = int.from_bytes(r[1:3], 'big')
    seqs = [
        ('Q1VALID', [r]),                                               # clean start: accepted at once
        ('Q2ENTER', [ENTER, r]),
        ('Q3JUNK', [JUNK, r]),
        ('Q4AIDS', [PF9, PA2, CLEAR, r]),
        ('Q5BAD', [r[:100], r[:1] + over, r[:3] + b'\x82' + r[4:], sf_cut(r, 1), r[:1] + b'\x00\x00' + r[3:], r]),
        ('Q6WAIT', [ENTER, b'', b'', b'', r]),
        ('Q7FALL', [ENTER] * 8 + [r]),                                  # 8 rejected records: fallback (r unread)
        ('Q8TIME', [ENTER] + [b''] * 6 + [r]),                          # 6 empty reads: fallback
        ('Q9ALT', [r[:1] + r[1 + first:]] + [r]),                       # the Summary cut: invalid, then valid
    ]
    names = set()
    for name, b in cases():                                             # every single reply as a 1-event sequence
        v = 'V' + name[:7]
        assert v not in names
        names.add(v)
        seqs.append((v, [b]))
    return seqs


def seq_lines():
    out = []
    for name, ev in sequences():
        a, n, w, (c, h, g) = select(ev)
        out.append(f'QSL {name:<8} ACT={a} NREC={n:02d} NWAIT={w:02d} C={c} H={h} GE={g}')
    return out


if __name__ == '__main__':
    for name, b in cases():
        print(name, len(b), expect(b))
