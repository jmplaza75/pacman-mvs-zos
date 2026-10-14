#!/usr/bin/env python3
"""Upload one source member with an explicit IBM-037 conversion and prove byte identity (ZOS-1).

Usage: zos_upload.py LOCAL_FILE LIB [--member NAME] [--hlq HLQ]
  LIB = COBOL | COPY | ASM | CLIST ...; the target is <HLQ>.PACMAN.<LIB>(<MEMBER>), MEMBER defaults to the file stem.
The member is then downloaded in binary (records as-is, no delimiters) and compared with the local file encoded to
IBM-037 and padded to fixed 80-byte records; any difference or truncation is a failure (exit 1).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zoslib import ENCODING, LRECL, R, fixed_records, hlq, zowe  # noqa: E402


def upload_verify(local, lib, member, h, outdir):
    local = Path(local)
    member = (member or local.stem).upper()
    want = fixed_records(local)                         # fails before any upload if a line exceeds 80 bytes
    dsn = f'{h}.PACMAN.{lib}({member})'
    zowe('zos-files', 'upload', 'file-to-data-set', str(local), dsn, '--encoding', ENCODING, json_out=True)
    dl = outdir / lib / f'{member}.bin'
    dl.parent.mkdir(parents=True, exist_ok=True)
    zowe('zos-files', 'download', 'data-set', dsn, '--binary', '-f', str(dl), json_out=True)
    got = dl.read_bytes()
    if got != want:
        recs = max(len(got), len(want)) // LRECL + 1
        first = next((i for i in range(recs) if got[i * LRECL:(i + 1) * LRECL] != want[i * LRECL:(i + 1) * LRECL]), None)
        return False, f'{dsn}: MISMATCH local {len(want)} bytes / {len(want) // LRECL} records, dataset {len(got)} ' \
                      f'bytes; first differing record {first + 1 if first is not None else "-"}'
    return True, f'{dsn}: identical ({len(got) // LRECL} records x {LRECL})'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('local')
    ap.add_argument('lib')
    ap.add_argument('--member')
    ap.add_argument('--hlq')
    ap.add_argument('--out', type=Path, default=R / 'build/zos1/dl')
    a = ap.parse_args()
    ok, msg = upload_verify(a.local, a.lib.upper(), a.member, hlq(a.hlq), a.out)
    print(msg)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
