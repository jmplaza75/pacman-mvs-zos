"""MVS-10 (D46, docs/MVS10-PF12.md): the exact source delta of the PF12 change, for the tests that pin sources to an
earlier tag. m10_strip() restores the three MVS-10 lines (each required exactly once in the current text), so a pin
on the stripped text still covers every other byte."""
from pathlib import Path

# path -> [(2.0-mvs-max line, MVS-10 line)]
DELTA = {
    'src/cobol/PACINPT.cob': [
        ('      *   TSC: PACPLAT POLL / RECV; PF7 U PF8 D PF10 L PF11 R, PF9 PAU',
         '      *   TSC: PACPLAT POLL / RECV; PF7 U PF8 D PF10 L PF12 R, PF9 PAU'),
        ('           IF WS-V = 123', '           IF WS-V = 124')],
    'src/clist/PACMAN.clist': [
        ('/* 150 MS, SEE SPEED; ARROWS = PF7/8/10/11, P = PF9 PAUSE WITH THE */',
         '/* 150 MS, SEE SPEED; ARROWS = PF7/8/10/12, P = PF9 PAUSE WITH THE */')],
}


def m10_strip(path, text):
    """The text with the MVS-10 lines of `path` put back to their 2.0-mvs-max form; AssertionError if a delta line
    is not present exactly once."""
    lines = text.split('\n')
    for old, new in DELTA.get(path, []):
        assert lines.count(new) == 1 and lines.count(old) == 0, (path, new)
        lines[lines.index(new)] = old
    return '\n'.join(lines)


def lines(root, path):
    """The current file as lines, MVS-10 delta stripped (for the git-show pins)."""
    return m10_strip(path, (Path(root) / path).read_text()).splitlines()
