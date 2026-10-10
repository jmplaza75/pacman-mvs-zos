#!/bin/sh
# MVS-RT: start c3270 for probe E14 / real-time play. 120x27 IBM-DYNAMIC (size the window to 120x30 BEFORE starting),
# arrow keys -> PF7 (up) PF8 (down) PF10 (left) PF11 (right) = one direct AID each, script port 4001 (read-only
# sampling by the tools), optional trace FILE (keep it OUTSIDE the repository: it contains the logon).
# Usage: tools/c3270_rt.sh [TRACEFILE]      TYPEAHEAD=false tools/c3270_rt.sh FILE   (c3270 typeahead off)
set -eu
KEYMAP='<Key>UP: PF(7)\n<Key>DOWN: PF(8)\n<Key>LEFT: PF(10)\n<Key>RIGHT: PF(11)'
set -- -model 2 -oversize auto -scriptport 4001 -xrm 'c3270.keymap: pacman' -xrm "c3270.keymap.pacman: $KEYMAP" \
  ${1:+-trace -tracefile "$1"} ${TYPEAHEAD:+-xrm "c3270.typeahead: $TYPEAHEAD"}
exec c3270 "$@" localhost:3270
