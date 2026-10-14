#!/usr/bin/env python3
"""Submit one deck exactly once, wait, and save its spool per DD (ZOS-1). Never purges, never resubmits.

Usage: zos_submit.py DECK.jcl [--hlq HLQ]      render @@HLQ@@, audit (writes only <HLQ>.PACMAN.*, no DELETE),
                                               submit, wait, download every spool file
       zos_submit.py --fetch JOBID             download the spool of an existing job (read-only)
Output: build/zos/<JOBNAME>-<JOBID>/ with job.json, deck.jcl (as submitted), NN-<step>[.<procstep>]-<dd>.txt and
spool.json; prints that directory. tools/zowe/zos_listing.py turns it into the listing shape the tests parse.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zoslib import R, audit_deck, hlq, render, zowe  # noqa: E402

OUT = R / 'build/zos'


def fetch(jobid, deck_text=None):
    job = zowe('zos-jobs', 'view', 'job-status-by-jobid', jobid, json_out=True)['data']
    d = OUT / f'{job["jobname"]}-{jobid}'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'job.json').write_text(json.dumps(job, indent=1))
    if deck_text is not None:
        (d / 'deck.jcl').write_text(deck_text)
    files = zowe('zos-jobs', 'list', 'spool-files-by-jobid', jobid, json_out=True)['data']
    (d / 'spool.json').write_text(json.dumps(files, indent=1))
    for f in sorted(files, key=lambda x: x['id']):
        step = f['stepname'] + (f'.{f["procstep"]}' if f.get('procstep') else '')
        r = zowe('zos-jobs', 'view', 'spool-file-by-id', jobid, str(f['id']))
        (d / f'{f["id"]:03d}-{step}-{f["ddname"]}.txt').write_text(r.stdout)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('deck', nargs='?', type=Path)
    ap.add_argument('--hlq')
    ap.add_argument('--fetch')
    a = ap.parse_args()
    if a.fetch:
        print(fetch(a.fetch))
        return
    h = hlq(a.hlq)
    text = render(a.deck.read_text(), h)
    if '@@' in text:
        raise SystemExit('unrendered @@ symbol left in the deck')
    bad = audit_deck(text, h)
    if bad:
        raise SystemExit('deck refused:\n  ' + '\n  '.join(bad))
    rendered = OUT / 'submitted' / a.deck.name
    rendered.parent.mkdir(parents=True, exist_ok=True)
    rendered.write_text(text)
    job = zowe('zos-jobs', 'submit', 'local-file', str(rendered), '--wait-for-output', json_out=True)['data']
    print(f'{job["jobname"]} {job["jobid"]} {job.get("retcode")} {job.get("status")}', file=sys.stderr)
    print(fetch(job['jobid'], text))


if __name__ == '__main__':
    main()
