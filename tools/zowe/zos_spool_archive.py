#!/usr/bin/env python3
"""Preserve the downloaded raw spool of the project's z/OS jobs (ZOS-0..ZOS-4) as immutable archives.

Usage: zos_spool_archive.py [--phase 2|3] [--build build/zos] [--out DIR] [--verify-only]
--phase 2 (default): every job except the ZOS-3 ones (PACZ3*), into docs/evidence/zos2-spool;
--phase 3: the ZOS-3 jobs (PACZ3*) only, into docs/evidence/zos3-spool; --phase 4: PACZ4* into docs/evidence/zos4-spool.
One archive per job directory build/zos/<JOBNAME>-<JOBID>/ (as tools/zowe/zos_submit.py saved it): every raw file
(job.json, spool.json, deck.jcl, NNN-<step>-<dd>.txt) byte for byte, in name order, as <JOBNAME>-<JOBID>/<file>;
files generated later by the analysis tools (report.txt) are not raw spool and are left out. Archives are
deterministic (sorted members, mtime 0, uid/gid 0, mode 0644, gzip mtime 0), so a rebuild gives the same SHA-256.
Writes SHA256SUMS and MANIFEST.txt; --verify-only re-reads every archive, checks SHA256SUMS, decompresses it and
compares each member with the source file.
"""
import argparse
import gzip
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
RAW = lambda f: f.name in ('job.json', 'spool.json', 'deck.jcl') or (f.name[:3].isdigit() and f.suffix == '.txt')


def raw_files(d):
    return sorted(f for f in d.iterdir() if f.is_file() and RAW(f))


def build(d):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0, filename='') as gz:
        with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as tar:
            for f in raw_files(d):
                data = f.read_bytes()
                ti = tarfile.TarInfo(f'{d.name}/{f.name}')
                ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), 0, 0o644, 0, 0, '', ''
                tar.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def verify(d, arc):
    with tarfile.open(arc, 'r:gz') as tar:
        names = tar.getnames()
        want = [f'{d.name}/{f.name}' for f in raw_files(d)]
        assert names == want, (arc.name, names, want)
        for f in raw_files(d):
            assert tar.extractfile(f'{d.name}/{f.name}').read() == f.read_bytes(), (arc.name, f.name)
    return len(names)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', type=Path, default=R / 'build/zos')
    ap.add_argument('--phase', choices=('2', '3', '4'), default='2')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--verify-only', action='store_true')
    a = ap.parse_args()
    a.out = a.out or R / f'docs/evidence/zos{a.phase}-spool'
    phase_of = lambda d: d.name[4] if d.name[:4] == 'PACZ' and d.name[4] in '34' else '2'   # noqa: E731
    dirs = sorted(d for d in a.build.iterdir() if d.is_dir() and (d / 'job.json').exists() and phase_of(d) == a.phase)
    a.out.mkdir(parents=True, exist_ok=True)
    sums = []
    for d in dirs:
        arc = a.out / f'{d.name}.tar.gz'
        data = build(d)
        assert build(d) == data, f'{d.name}: archive not deterministic'
        if a.verify_only:
            assert arc.read_bytes() == data, f'{arc.name}: differs from a rebuild of the raw spool'
        else:
            arc.write_bytes(data)
        n = verify(d, arc)
        sums.append(f'{hashlib.sha256(arc.read_bytes()).hexdigest()}  {arc.name}')
        print(f'{arc.name}: {n} files, {len(data)} bytes, decompressed and compared OK')
    if a.verify_only:
        old = (a.out / 'SHA256SUMS').read_text().splitlines()
        assert old == sums, 'SHA256SUMS differs'
        print('SHA256SUMS verified')
    else:
        (a.out / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')
    return dirs, {s.split()[1]: s.split()[0] for s in sums}


if __name__ == '__main__':
    main()
