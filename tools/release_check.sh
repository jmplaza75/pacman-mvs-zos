#!/bin/sh
# Full release verification: local checks, then build + regression on Hercules.
# Usage: tools/release_check.sh [PREFIX]          1.0-MVS: RELEASE deck (default HERC01.PACMAN; libraries must exist)
#        tools/release_check.sh 2.0 [PREFIX]      2.0-MVS-MAX (D43): REL20 build of record into PREFIX.LOAD(PACMAIN)
#                                                 (default HERC01.PACMAN.R20, fresh libraries from the ALLOC deck),
#                                                 then the S2 / RP / GP2 / GP23 / HS regressions run-only on that
#                                                 module, every deck and listing audited, tests/test_g8.py
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
if [ "${1:-}" = "2.0" ]; then
    PREFIX="${2:-HERC01.PACMAN.R20}"
    python3 tools/validate_source.py src/cobol/*.cob src/copy/*.cpy src/asm/*.asm src/clist/*.clist tests/cases/*.txt
    python3 tests/test_g8.py --prefix "$PREFIX" | tail -1
    for t in test_s2 test_rp test_hs test_gp2 test_gp1; do
        PACMAN_LATER_PHASE=G8 python3 "tests/$t.py" >/dev/null || { echo "local check failed: $t" >&2; exit 1; }
    done
    for t in test_gs test_g4 test_core_frozen test_mvs8; do
        python3 "tests/$t.py" >/dev/null || { echo "local check failed: $t" >&2; exit 1; }
    done
    echo "local checks: PASS"
    python3 tools/make_deck.py REL20 --prefix "$PREFIX" --out build/REL20.jcl >/dev/null
    for d in S2 RP GP2 GP23 HS; do
        python3 tools/make_deck.py $d --runonly --load PACMAIN --prefix "$PREFIX" --out "build/R20-$d.jcl" >/dev/null
    done
    python3 tools/g8_jcl_audit.py --prefix "$PREFIX" build/REL20.jcl build/R20-*.jcl
    REL=$(python3 tools/run_deck.py build/REL20.jcl --timeout 1800)
    python3 tests/test_g8.py --prefix "$PREFIX" --rel20 "$REL" | tail -1
    S2=$(python3 tools/run_deck.py build/R20-S2.jcl --timeout 1800)
    RP=$(python3 tools/run_deck.py build/R20-RP.jcl --timeout 3600)
    GP2=$(python3 tools/run_deck.py build/R20-GP2.jcl --timeout 3600)
    GP23=$(python3 tools/run_deck.py build/R20-GP23.jcl --timeout 1800)
    HS=$(python3 tools/run_deck.py build/R20-HS.jcl --timeout 1800)
    echo "listings: $REL $S2 $RP $GP2 $GP23 $HS"
    python3 tests/test_g8.py --prefix "$PREFIX" --rel20 "$REL" --s2 "$S2" --rp "$RP" --gp2 "$GP2" --gp23 "$GP23" --hs "$HS"
    exit 0
fi
PREFIX="${1:-HERC01.PACMAN}"
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
