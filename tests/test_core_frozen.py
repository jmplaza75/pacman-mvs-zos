#!/usr/bin/env python3
"""MVS-G0: the game core must match tests/core_baseline.json (see docs/CORE_CHANGES.md to authorise a change).
Branch zos (ZOS-2, docs/ZOS-DIFFS.md Z1): the only allowance is the explicit port delta of tests/zos_c2.json; a core
source that differs from the baseline passes only if it is listed there, the Z1 guard passes, and reversing exactly
its listed lines gives back the frozen SHA-256. Copybooks and maps get no allowance."""
import hashlib
import sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'tools'))
from core_baseline import check  # noqa: E402

base, diff = check()
z1 = []
if diff:
    sys.path.insert(0, str(R / 'tests'))
    import zos_c2  # noqa: E402
    allowed = {e['file'] for e in zos_c2.table()}
    for f in diff:
        assert f in allowed and f.startswith('src/cobol/'), \
            f'unauthorised core change: {f} (use tools/core_baseline.py --authorize)'
        orig = zos_c2.reverse(f, (R / f).read_text(encoding='ascii'))
        assert hashlib.sha256(orig.encode('ascii')).hexdigest() == base['files'][f], f'{f}: more than the Z1 lines changed'
        z1.append(f)
    zos_c2.guard()
print('core frozen (' + base['baseline'] + '): PASS' +
      (f'; z/OS port delta Z1 only in {", ".join(Path(f).stem for f in z1)}' if z1 else ''))
