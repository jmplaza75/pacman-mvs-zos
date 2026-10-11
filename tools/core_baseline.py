#!/usr/bin/env python3
"""Frozen game core (MVS-G0). The core files of release 1.0-MVS are protected by SHA-256 checksums in
tests/core_baseline.json; tests/test_core_frozen.py fails on any unauthorised change.

  core_baseline.py --check                       compare the working tree with the baseline
  core_baseline.py --authorize "REASON" --by NAME  accept the current core as the new baseline and log the change
                                                   in docs/CORE_CHANGES.md (who, when, why, old -> new hashes)
An authorised change must still pass the 1.0-MVS regression oracle unless the change is meant to alter mechanics,
in which case the oracle itself must be re-baselined in the same documented step.
"""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ['src/cobol/PACGAME.cob', 'src/cobol/PACMAP.cob', 'src/cobol/PACAI.cob',
        'src/copy/PACSTATE.cpy', 'src/copy/PACMREQ.cpy', 'maps/LEVEL1.txt',
        'src/copy/PACARC.cpy', 'maps/ARCADE1.txt']      # MVS-GP1 (D36): the ARCADE state and power pellet map
BASE = ROOT / 'tests/core_baseline.json'
LOG = ROOT / 'docs/CORE_CHANGES.md'


def digest(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def current():
    return {f: digest(f) for f in CORE}


def check():
    base = json.loads(BASE.read_text())
    diff = [f for f in CORE if base['files'].get(f) != digest(f)]
    return base, diff


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--authorize', metavar='REASON')
    ap.add_argument('--by', default='')
    a = ap.parse_args()
    if a.authorize:
        if not a.by:
            sys.exit('--by NAME is required for an authorisation')
        old = json.loads(BASE.read_text())
        new = current()
        changed = [f for f in CORE if old['files'].get(f) != new[f]]
        if not changed:
            sys.exit('core unchanged: nothing to authorise')
        stamp = datetime.date.today().isoformat()
        with LOG.open('a') as fh:
            fh.write(f'\n## {stamp} - authorised by {a.by}\nReason: {a.authorize}\n')
            for f in changed:
                fh.write(f'- {f}: {old["files"].get(f, "-")[:16]} -> {new[f][:16]}\n')
        BASE.write_text(json.dumps({'baseline': f'authorised {stamp} by {a.by}', 'files': new}, indent=1) + '\n')
        print('baseline updated:', ', '.join(changed))
    else:
        base, diff = check()
        print('core frozen at', base['baseline'], '- OK' if not diff else '- CHANGED: ' + ', '.join(diff))
        sys.exit(1 if diff else 0)
