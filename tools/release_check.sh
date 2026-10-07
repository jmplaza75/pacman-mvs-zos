#!/bin/sh
# Full release verification: local checks, then build + regression of the RELEASE deck on Hercules.
# Usage: tools/release_check.sh [PREFIX]   (default HERC01.PACMAN; the libraries must exist - see README)
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PREFIX="${1:-HERC01.PACMAN}"
cd "$ROOT"
python3 tools/validate_source.py src/cobol/*.cob src/copy/*.cpy src/asm/*.asm src/clist/*.clist tests/cases/*.txt
for t in tests/test_map.py tests/test_mvs2.py tests/test_mvs3.py tests/test_mvs4.py tests/test_mvs5.py \
         tests/test_mvs6.py tests/test_mvs7.py tests/test_mvs8.py; do
    python3 "$t" >/dev/null || { echo "local check failed: $t" >&2; exit 1; }
done
echo "local checks: PASS"
python3 tools/make_deck.py RELEASE --prefix "$PREFIX" --out build/RELEASE.jcl >/dev/null
LISTING=$(python3 tools/run_deck.py build/RELEASE.jcl)
echo "listing: $LISTING"
python3 tests/test_mvs8.py "$LISTING" | tail -1
