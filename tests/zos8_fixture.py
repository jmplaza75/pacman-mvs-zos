#!/usr/bin/env python3
"""ZOS-8: deterministic synthetic c3270 traces (and driver logs) of the live cases of tools/zowe/zos8_drive.py for
tools/zowe/zos8_live_check.py, and synthetic spools of the batch jobs B1 / B2 for tools/zowe/zos8_batch.py. The ZOS-6
fixture (frozen) renders the TN3270E trace (BID per host record, RESPONSEs, kybd lines) and supplies the transition /
shell records; the ZOS-7 fixture (frozen) builds the REALTIME games (S8A / S8B through the sound model); the game
streams come from the independent models (ref_gx_screen + ref_gp2 / CLASSIC, ref_s2 for the bells).

build(case, **inject) -> (trace text, driver log lines). TURN injections: before (the store state the host read),
mutate / drop_write (write index), end_lines (replacement end lines), end_label ('saved' / 'unsaved': the end-screen
NEW HIGH SCORE label of the opposite persistence outcome), iec ('hold': IEC217I B14 + a TSO `***` hold
before the end screen; 'tail': the message among the line-mode end lines; 'bad': another IEC message), member (the
CLIST member typed). ESTAE injections: leftover (LISTALC shows CEEOPTS; the driver then FREEs it), no_free (listed, not
freed), free_anyway (freed, not listed), no_abend, rescreen, e3_late (the E3 line after the abend text), extra_input,
gd (TURN injections for the follow-up game), recovery (number of `***` holds), hold (the EXEC's initial `***` + ENTER:
'ok', 'missing', 'dup', 'order'), screen (replacement test-screen lines), listalc (replacement LISTALC output lines),
page (lines per LISTALC output page), pagefault (a fault of the held LISTALC / FREE answers: see held());
split_segments() / split_at_hold() cut a trace into the segments of a resumed case. LISTALC and FREE are held as live
2026-10-20 (E1 recovery traces): F1 C1, the `***` hold, ENTER, then the output pages (7E C3 ... `***`; one page split
F1 C1-less over two records), one ENTER each, then the shell panel."""
import json
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R / 'tests'), str(R / 'tools/zowe')]
import qry_cases as Q  # noqa: E402
import zos6_fixture as F6  # noqa: E402
import zos7_fixture as F7  # noqa: E402
import zos8_scen as S  # noqa: E402
import zos8_drive as DV  # noqa: E402
import zos8_live_check as Z8  # noqa: E402

UP, DOWN, BIDRTT = F6.UP, F6.DOWN, F6.BIDRTT
e = F6.e
ENTER = bytes([0x7D, 0xC7, 0xE5])
LE_E = ['CEE3207S The system detected a data exception (System Completion Code=0C7).',
        'From compile unit PACRPE at entry point PACRPE at compile unit offset +000003A2.',
        'IEA995I SYMPTOM DUMP OUTPUT', 'SYSTEM COMPLETION CODE=0C7  REASON CODE=00000007',
        'PACRPE ENDED DUE TO ERROR+']


def typed_cmd(text):
    return bytes([0x7D, 0x5B, 0x6F, 0x11, 0x5B, 0x60]) + e(text)


def line_rec(lines, wcc=0xC1):
    return bytes([0x7E, wcc]) + b''.join(bytes([0x11, 0x40 + i, 0x40]) + e(s) for i, s in enumerate(lines))


class Trace:
    def __init__(self, t0=36_000_000):
        self.recs, self.lock, self.log, self.t = [], [], [], t0

    def host(self, p, at):
        self.recs.append(['<', int(at), p, 'H'])

    def term(self, p, at):
        self.recs.append(['>', int(at), p, 'T'])

    def logged(self, cat, act, req, sent):
        self.log.append({'ordinal': len(self.log) + 1, 'category': cat, 'action': act, 'requested': req,
                         'wait_start': req, 'unlocked': sent, 'sent': sent, 'result': 'ok'})

    def write(self, h):
        self.lock.append((h + DOWN, h + DOWN + BIDRTT))

    def unlock_after(self, r):
        for x, y in self.lock:
            if x <= r < y:
                return y + 1
        return r

    def command(self, text, cat, act, outputs=None, star=True):
        """A shell command: typed + ENTER, its line-mode output, `***`, ENTER, the shell panel."""
        t = self.t
        self.term(typed_cmd(text), t)
        self.logged(cat, act, t, t)
        if outputs is not None:
            self.host(line_rec(outputs), t + 200)
        if star:
            self.host(F6.TRANS_STAR, t + 300)
            self.term(ENTER, t + 1300)
            self.logged(cat, 'ENTER', t + 1300, t + 1300)
        self.host(F6.SHELL_PANEL, t + 1500)
        self.t = t + 3000

    def held(self, text, cat, act, pages=(), fault=None):
        """A command typed on the shell, answered as observed live (LISTALC / FREE 2026-10-20): F1 C1, the `***` hold,
        one ENTER, every output page (its lines + `***`) answered by one ENTER, then the shell panel. A page given as
        a pair (a, b) is split over two records (7E C1 a, then F1 C2 b + `***`), as the live page 7 of LISTALC.
        fault: 'no_hold' (no initial hold, no ENTER), 'hold_text' (the hold carries a line), 'missing' (page 2's records
        lost, its ENTER kept), 'missing_log' (page 2's ENTER not in the driver log), 'dup' (page 2 sent and answered
        twice), 'hold_twice' (the hold answered by two ENTERs), 'no_star' (page 2 without `***`), 'after_star'
        (a line after page 2's `***`), 'two_enters' (page 2 answered by two ENTERs)."""
        t = self.t
        self.term(typed_cmd(text), t)
        self.logged(cat, act, t, t)
        t += 100
        if fault != 'no_hold':
            self.host(bytes([0xF1, 0xC1]), t)
            self.host(line_rec(['NOT HELD', '***'], 0xC2) if fault == 'hold_text' else F6.TRANS_STAR, t + 100)
            self.term(ENTER, t + 200)
            self.logged(cat, 'ENTER', t + 200, t + 200)
            if fault == 'hold_twice':
                self.term(ENTER, t + 250)
                self.logged(cat, 'ENTER', t + 250, t + 250)
            t += 300
        seq = list(pages)
        if fault == 'dup':
            seq.insert(2, seq[1])
        for j, pg in enumerate(seq):
            if isinstance(pg, tuple):
                self.host(line_rec(pg[0], 0xC1), t)
                self.host(bytes([0xF1, 0xC2]) + line_rec(pg[1] + ['***'])[2:], t + 50)
            elif not (fault == 'missing' and j == 1):
                tail = [] if fault == 'no_star' and j == 1 else ['***']
                tail += ['LATE LINE'] if fault == 'after_star' and j == 1 else []
                self.host(line_rec(list(pg) + tail, 0xC3), t)
            self.term(ENTER, t + 100)
            if not (fault == 'missing_log' and j == 1):
                self.logged(cat, 'ENTER', t + 100, t + 100)
            if fault == 'two_enters' and j == 1:
                self.term(ENTER, t + 150)
                self.logged(cat, 'ENTER', t + 150, t + 150)
            t += 300
        self.host(F6.SHELL_PANEL, t)
        self.t = t + 2000

    def render(self):
        return F6.render(self.recs, self.lock), [json.dumps(x) for x in self.log]


def turn_game(tr, name, cmd, before, exec_act='EXEC', mutate=None, drop_write=None, end_lines=None, iec=None,
              end_label=None):
    p = DV.PLANS.get(name) or {}
    sound = 'SOUND(YES)' in S.kw_of(name).split()
    t0 = tr.t
    tr.term(typed_cmd(cmd), t0)
    tr.logged('transition', exec_act, t0, t0)
    tr.host(F6.TRANS_STAR, t0 + 300)
    tr.term(bytes([0x7D, 0xD9, 0xC5]), t0 + 1500)
    tr.logged('transition', 'ENTER', t0 + 1500, t0 + 1500)
    tr.host(F6.TRANS_CLR, t0 + 1700)
    hsw = t0 + 1800
    tr.host(bytes([0x7E, 0xC3]), hsw + 170)
    tr.host(F6.QUERY, hsw + 171)
    tr.term(Q.rec('dyn'), hsw + 175)
    hs = S.hs_tuple(name, before) if S.GAMES[name][3] == 'A' else None
    # the end screen carries NEW HIGH SCORE only when the save succeeds (ref_hs); end_label forces the opposite
    # outcome for the negative tests ('saved': the label although the save fails, 'unsaved': no label after a save)
    saved = Z8.saved_of(Z8.expected_lines(name, before)[1]) if hs else None
    if end_label is not None:
        saved = end_label == 'saved'
    mod = Z8.turn_model(name, hs, sound, saved=saved)
    frames, full = mod['frames'], mod['full']
    cards = S.live_cards(name)[1:]
    extra = len(frames) - len(cards) - 1
    assert extra >= 0, (name, len(frames), len(cards))
    hw = [hsw + 250]
    tr.write(hw[0])
    cursor = hw[0] + DOWN + BIDRTT + 1
    for i, a in enumerate(cards):
        sent = tr.unlock_after(cursor + 300)
        tr.term(F7.aid_bytes(a), sent)
        tr.logged('gameplay', a, cursor + 300, sent)
        h = sent + UP + 20
        if i == len(cards) - 1 and iec in ('hold', 'bad'):          # HL8: the message (+ hold) before the end screen
            code = 'IEC217I B14-0C' if iec == 'hold' else 'IEC020I 001-4'
            tr.host(line_rec([f'{code},IGG0201Z,Z00000,ISPFPROC,PACHS,0D38,ZXPL01,',
                              'Z00000.PACMAN.HSFULL.T1(HISCORE)']), h)
            tr.host(F6.TRANS_STAR, h + 10)
            tr.term(ENTER, h + 600)
            tr.logged('hold', 'ENTER', h + 600, h + 600)
            h += 700
        hw.append(h)
        tr.write(h)
        cursor = h + DOWN + BIDRTT + 1
    for _ in range(extra):                                      # bell-only writes in the end pause (S8C)
        hw.append(hw[-1] + 300)
        tr.write(hw[-1])
    arrivals = [h + DOWN + BIDRTT for h in hw]
    for n, (f, at) in enumerate(zip(frames, arrivals)):
        pl = F7.payload(n, f, full)
        if mutate == n:
            pl = pl[:-1] + bytes([pl[-1] ^ 0x01])
        if drop_write == n:
            continue
        tr.host(pl, at)
    end_at = arrivals[-1] + 3000
    if end_lines is None:
        out, hsl = Z8.expected_lines(name, before)
        end_lines = list(out) + hsl
    if iec == 'tail':
        tr.host(line_rec(['IEC217I B14-0C,IGG0201Z,Z00000,ISPFPROC,PACHS,0D38,ZXPL01,',
                          'Z00000.PACMAN.HSFULL.T1(HISCORE)']), end_at - 50)
    tr.host(line_rec(end_lines), end_at)
    tr.host(F6.TRANS_STAR, end_at + 110)
    tr.term(ENTER, end_at + 4000)
    tr.logged('closure', 'ENTER', end_at + 4000, end_at + 4000)
    tr.host(F6.SHELL_PANEL, end_at + 4200)
    tr.t = end_at + 6000


def build(case, before=None, prefix='Z00000.PACMAN', member=None, kw=None, **inj):
    p = DV.PLANS[case]
    if p['kind'] == 'RT':
        with Z8.sound_model():
            return F7.build({150: 'L2', 125: 'L3'}[p['T']], hiscore=before or 'ABSENT', kw=kw or p['kw'], **inj)
    tr = Trace()
    if p['kind'] == 'TURN':
        chain = {c: b for c, _, b, _, _ in S.hl_chain()}
        before = before or chain.get(case, 'ABSENT' if case == 'SF' else 'n/a')   # SF: DATA(HISCORE) absent
        cmd = f"EXEC '{prefix}.CLIST({member or p['clist']})' '{kw or p['kw']}'"
        turn_game(tr, case, cmd, before, **inj)
        return tr.render()
    return estae(tr, case, prefix, **inj)


def estae(tr, case, prefix, leftover=True, no_free=False, free_anyway=False, no_abend=False, rescreen=False,
          e3_late=False, extra_input=False, gd=None, recovery=1, hold='ok', screen=None, listalc=None, page=12,
          pagefault=None, free_output=False, free_fault=None):
    t = tr.t
    tr.term(typed_cmd(DV.command(case, 'EXEC', prefix)), t)
    tr.logged('transition', 'EXEC', t, t)
    # the ISPF / TSO hold of every EXEC from the shell: a blank line-mode write, `***`, one ENTER (hold: 'ok', 'missing'
    # (neither), 'dup' (two *** + ENTER pairs), 'order' (the ENTER before the ***))
    if hold != 'missing':
        tr.host(bytes([0xF1, 0xC1]), t + 100)
    if hold in ('ok', 'dup'):
        tr.host(F6.TRANS_STAR, t + 200)
        tr.term(ENTER, t + 1000)
        tr.logged('transition', 'ENTER', t + 1000, t + 1000)
    if hold == 'dup':
        tr.host(F6.TRANS_STAR, t + 1100)
        tr.term(ENTER, t + 1200)
    if hold == 'order':
        tr.term(ENTER, t + 150)
        tr.logged('transition', 'ENTER', t + 150, t + 150)
        tr.host(F6.TRANS_STAR, t + 200)
    t += 1000
    # the test screen exactly as PACRPE BUILD-SCREEN sends it (TPUT FULLSCR: F1 + WCC C3 + the clear prefix, five lines;
    # the live E1 screen of 2026-10-20); screen: a replacement list of lines (altered-screen negatives)
    sba = [(0xC1, 0xD1), (0xC3, 0xF1), (0xC6, 0xD1), (0xC7, 0x61), (0xC8, 0xF1), (0xC9, 0xC1), (0x4A, 0xD1)]
    assert len(screen or []) <= len(sba)
    scr = bytes([0xF1, 0xC3]) + F6.CLRPFX + b''.join(bytes([0x11, a, b]) + e(s) for (a, b), s in
                                                     zip(sba, screen or DV.test_screen(case)))
    tr.host(scr, t + 400)
    tr.term(ENTER, t + 3000)
    tr.logged('abend', 'ENTER', t + 3000, t + 3000)
    lines = [] if no_abend else list(LE_E)
    if case == 'E3':
        lines = (lines + [Z8.E3_LINE]) if e3_late else ([Z8.E3_LINE] + lines)
    t += 3200
    if rescreen:
        tr.host(scr, t)
        t += 100
    tr.host(line_rec(lines or ['READY']), t)
    for i in range(recovery):
        tr.host(F6.TRANS_STAR, t + 100)
        tr.term(ENTER, t + 1000)
        tr.logged('recovery', 'ENTER', t + 1000, t + 1000)
        if extra_input and i == 0:
            tr.term(typed_cmd('X'), t + 1100)
        t += 1200
    tr.host(F6.SHELL_PANEL, t + 100)
    tr.t = t + 2000
    listed = listalc_lines(prefix, leftover) if listalc is None else listalc
    pages = [listed[i:i + page] for i in range(0, len(listed), page)]
    if pagefault == 'split':                                    # the live page split over two records
        pages[1] = (pages[1][:5], pages[1][5:])
    if pagefault == 'reorder':
        pages[0], pages[1] = pages[1], pages[0]
    if pagefault == 'too_many':
        pages = [pages[0]] + [[f'Z00000.FILL{i:03d}', 'KEEP'] for i in range(DV.PAGES_MAX)]
    if pagefault == 'error':
        pages[1] = pages[1][:3] + ['IKJ56231I DATA SET NOT ALLOCATED'] + pages[1][3:]
    tr.held('LISTALC STATUS', 'check', 'LISTALC', pages,
            pagefault if pagefault not in ('split', 'reorder', 'too_many', 'error') else None)
    if (leftover and not no_free) or free_anyway:
        tr.held('FREE F(CEEOPTS)', 'cleanup', 'FREE', [['IKJ56247I FILE CEEOPTS NOT FREED']] if free_output else [],
                free_fault)
    gcmd = DV.command(case, 'EXEC:GD', prefix)
    turn_game(tr, 'GD', gcmd, 'n/a', exec_act='EXEC:GD', **(gd or {}))
    return tr.render()


def listalc_lines(prefix, leftover=True):
    """LISTALC STATUS output in the live shape (2026-10-20: header, then a dataset line and a DD / DISP line per
    allocation, concatenations with a blank DD); the CEEOPTS pair (dataset line, `CEEOPTS  KEEP`) when left over."""
    out = ['--DDNAME---DISP--', 'SYS1.DGTLLIB', 'STEPLIB  KEEP', 'GIM.SGIMLMD0', 'KEEP', 'ZXP.PUBLIC.LOAD', 'KEEP',
           'ISP.SISPHELP', 'SYSHELP  KEEP', 'SYS1.HELP', 'KEEP', 'Z00000.S0W1.ISPF.ISPPROF', 'ISPPROF  KEEP']
    out += [x for i in range(12) for x in (f'ISP.SISPLIB{i:02d}', 'ISPPLIB  KEEP' if i == 0 else 'KEEP')]
    out += ['Z00000.S0W1.SPFLOG1.LIST', 'ISPLOG  KEEP']
    if leftover:
        out += [f'{prefix}.CEEOPTS', 'CEEOPTS  KEEP']
    return out + ['ISP03481 CATLG', 'TERMFILE  SYSOUT']


def split_segments(text, log_lines, points=('hold',), drop_last=False, extra_first=False):
    """Cut one rendered Stage D trace into the segments of a resumed case, at the defined resume points only: 'hold'
    (segment ends with the EXEC's `***`; the next starts with the hold's ENTER) and 'screen' (segment ends with the
    test screen; the next starts with the abend ENTER). Every segment carries the trace header (a fresh trace). The
    driver log is split the same way. drop_last: the first segment loses its last host record; extra_first: the second
    segment starts with a stray host write before its ENTER (boundary faults). -> (segments, logs)."""
    lines = text.splitlines()
    k = lines.index(' Data stream:') + 1
    head, data = lines[:k], lines[k:]
    log = [json.loads(x) for x in log_lines]
    at = {'hold': 1, 'screen': 2}
    cuts, lcuts = [], []
    for pt in points:
        stamp = F6.FX.stamp(log[at[pt]]['sent'])
        cut = next(i for i, l in enumerate(data) if l[:1].isdigit() and l[:19] >= stamp[:19])
        cuts.append(cut)
        lcuts.append(at[pt])
    segs, prev = [], 0
    for c in cuts + [len(data)]:
        segs.append(data[prev:c])
        prev = c
    if drop_last:
        j = max(i for i, l in enumerate(segs[0]) if 'socket read complete' in l)
        segs[0] = segs[0][:j]
    if extra_first:
        stamp = segs[1][0][:19]
        segs[1] = [f'{stamp} socket Host socket read complete nr=9', '< 0x0   0003020000f1c2ffef'] + segs[1]
    logs, prev = [], 0
    for c in lcuts + [len(log_lines)]:
        logs.append(log_lines[prev:c])
        prev = c
    return ['\n'.join(head + s) + '\n' for s in segs], logs


def split_at_hold(text, log_lines, drop_last=False, extra_first=False):
    """The two segments of a case resumed at its `***` hold (split_segments with ('hold',))."""
    segs, logs = split_segments(text, log_lines, ('hold',), drop_last, extra_first)
    return tuple(segs), logs[0], logs[1]


# ---- synthetic spools for the batch checkers ---------------------------------------------------------------------
def spool(kind, d, faults=()):
    """Write a synthetic job spool directory (zos_submit layout) of B1 / B2 into d; faults = names of injected
    defects."""
    import zos8_batch as B
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    job = {'jobname': B.B1_JOB if kind == 'B1' else B.B2_JOB, 'jobid': 'JOB00001', 'retcode': 'CC 0000'}
    files, n = [], [100]
    jcl, msg = [], [' ICH70001I Z00000   LAST ACCESS AT 10:00:00']

    def add(step, dd, lines, recfm='FB'):
        n[0] += 1
        files.append({'id': n[0], 'stepname': step, 'ddname': dd, 'recfm': recfm, 'procstep': None})
        (d / f'{n[0]:03d}-{step}-{dd}.txt').write_text('\n'.join(lines) + '\n')
    name = job['jobname']
    if kind == 'B1':
        steps = [('ALLOC', 'IEFBR14')] + [(s, 'PACZ6D') for s, _, _ in S.B1_STEPS] + \
            [('PRINT', 'IEBGENER'), ('HSLIST', 'IKJEFT01')]
        model = {s: lines for s, lines, _ in S.b1_model()}
        for s, pgm in steps:
            jcl.append(f'        {len(jcl) + 1} //{s:<8} EXEC PGM={pgm}')
            if s == 'ALLOC':
                msg += [' IEF236I ALLOC. FOR PACZ8HB ALLOC', ' IGD101I SMS ALLOCATED TO DDNAME (HS8     )',
                        '         DSN (Z00000.PACMAN.HS8.T1                       )',
                        '         STORCLAS (ZXPS) MGMTCLAS (        ) DATACLAS (ZXPD)', '         VOL SER NOS= ZXPL01']
            rc = '0004' if (f'{s} rc' in faults) else '0000'
            msg.append(f' IEF142I {name} {s} - STEP WAS EXECUTED - COND CODE {rc}')
            if s in model:
                out = list(model[s])
                if f'{s} line' in faults:
                    out[-1] = out[-1] + 'X'
                add(s, 'SYSOUT', out)
                msg.append(' IGD104I Z00000.PACMAN.LOAD                           RETAINED,  DDNAME=STEPLIB')
                msg.append(' IGD104I Z00000.PACMAN.HS8.T1                         RETAINED,  DDNAME=PACHS')
            if s == 'PRINT':
                add(s, 'SYSUT2', [('0000999 PACHS001 001' if 'print' in faults else S.B1_VALUE.rstrip())])
            if s == 'HSLIST':
                mem = ['   HISCORE'] + (['   EXTRA'] if 'members' in faults else [])
                add(s, 'SYSTSPRT', ['READY', "   LISTDS 'Z00000.PACMAN.HS8.T1' MEMBERS", ' Z00000.PACMAN.HS8.T1',
                                     ' --RECFM-LRECL-BLKSIZE-DSORG', '   FB    80    80      PO', ' --VOLUMES--',
                                     '   ZXPL01', ' --MEMBERS--'] + mem + [' READY', ' END'])
        if 'data' in faults:
            msg.append(' IGD104I Z00000.PACMAN.DATA                           RETAINED,  DDNAME=PACHS')
        if 'iec' in faults:
            msg.append(' IEC217I B14-0C,IGG0201Z,PACZ8HB,H1,PACHS,0D38,ZXPL01,')
    else:
        steps = [('COB', 'IGYCRCTL'), ('LINK', 'IEWBLINK'), ('E1', 'PACRPE'), ('E2', 'PACRPE')]
        for s, pgm in steps:
            jcl.append(f'        {len(jcl) + 1} //{s:<8} EXEC PGM={pgm}')
            if s in ('COB', 'LINK'):
                rc = '0004' if f'{s} rc' in faults else '0000'
                msg.append(f' IEF142I {name} {s} - STEP WAS EXECUTED - COND CODE {rc}')
                if s == 'COB':
                    add(s, 'SYSPRINT', ['PP 5655-EC6 IBM Enterprise COBOL for z/OS  6.5.0',
                                        'End of compilation 1,  program PACRPE,  no statements flagged.'])
                else:
                    add(s, 'SYSPRINT', ['IEW2278I B352 INVOCATION PARAMETERS - LIST,AMODE=24,RMODE=24,RENT',
                                        ' MEMBER NAME  PACRPE', ' AMODE        24',
                                        ' RMODE        ANY' if 'rmode' in faults else ' RMODE        24',
                                        ' IEW2008I 0F03 PROCESSING COMPLETED.'])
            else:
                if f'{s} noabend' in faults:
                    msg.append(f' IEF142I {name} {s} - STEP WAS EXECUTED - COND CODE 0000')
                    out = B.RPE_LINES[s] + ['RPE ERROR: NO ABEND']
                else:
                    msg.append(f' IEF472I {name} {s} - COMPLETION CODE - SYSTEM=0C7 USER=0000 REASON=00000007')
                    out = B.RPE_LINES[s] + ['CEE3207S The system detected a data exception (System Completion '
                                            'Code=0C7).']
                if f'{s} lines' in faults:
                    out[0] = 'RPE CASE E9 START'
                add(s, 'SYSOUT', out)
        msg.append(' IGD104I Z00000.PACMAN.LOAD                           RETAINED,  DDNAME=SYSLMOD')
        if 'data' in faults:
            msg.append(' IGD104I Z00000.PACMAN.DATA                           RETAINED,  DDNAME=PACHS')
    (d / 'job.json').write_text(json.dumps(job))
    files = [{'id': 2, 'stepname': 'JES2', 'ddname': 'JESMSGLG', 'recfm': 'UA', 'procstep': None},
             {'id': 3, 'stepname': 'JES2', 'ddname': 'JESJCL', 'recfm': 'V', 'procstep': None},
             {'id': 4, 'stepname': 'JES2', 'ddname': 'JESYSMSG', 'recfm': 'VA', 'procstep': None}] + files
    (d / '002-JES2-JESMSGLG.txt').write_text(f' $HASP373 {name} STARTED\n')
    (d / '003-JES2-JESJCL.txt').write_text('\n'.join(jcl) + '\n')
    (d / '004-JES2-JESYSMSG.txt').write_text('\n'.join(msg) + '\n')
    (d / 'spool.json').write_text(json.dumps(files))
    return d


def spool_check(kind, faults=()):
    import zos8_batch as B
    with tempfile.TemporaryDirectory() as t:
        d = spool(kind, Path(t) / 'job', faults)
        job, res, info = (B.check_b1 if kind == 'B1' else B.check_b2)(d)
        return res, info


if __name__ == '__main__':
    for c in DV.PLANS:
        text, lg = build(c)
        print(c, len(text.splitlines()), 'trace lines,', len(lg), 'driver actions')
