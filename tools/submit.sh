#!/bin/sh
# Send a JCL deck to the Hercules card reader. Credentials: HERC01_PASSWORD (or TK4_PASSWORD)
# from the environment or from the gitignored ./.env file (never committed).
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
[ -f "$ROOT/.env" ] && . "$ROOT/.env"
TK4_USER="${TK4_USER:-HERC01}"
TK4_PASSWORD="${TK4_PASSWORD:-${HERC01_PASSWORD:-}}"
[ "$#" -eq 1 ] && [ -f "$1" ] || { echo "Usage: $0 deck.jcl" >&2; exit 2; }
python3 "$ROOT/tools/validate_source.py" "$1"
! LC_ALL=C grep -q '@@' "$1" || { echo 'Unresolved template marker' >&2; exit 2; }
export TK4_HOST="${TK4_HOST:-127.0.0.1}" TK4_RDR_PORT="${TK4_RDR_PORT:-3505}" TK4_USER TK4_PASSWORD
python3 "$ROOT/tools/send_deck.py" "$1"
echo "Deck sent to $TK4_HOST:$TK4_RDR_PORT; check JES output (tools/job_output.py)."
