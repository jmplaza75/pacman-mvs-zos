#!/usr/bin/env python3
"""MVS-G0: the game core must match tests/core_baseline.json (see docs/CORE_CHANGES.md to authorise a change)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from core_baseline import check  # noqa: E402

base, diff = check()
assert not diff, f'unauthorised core change: {diff} (use tools/core_baseline.py --authorize)'
print('core frozen (' + base['baseline'] + '): PASS')
