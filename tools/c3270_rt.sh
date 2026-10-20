#!/bin/sh
# MVS-RT: start c3270 for probe E14 / real-time play. 120x27 IBM-DYNAMIC (size the window to 120x30 BEFORE starting),
# arrow keys -> PF7 (up) PF8 (down) PF10 (left) PF12 (right; MVS-10 / D46, was PF11) = one direct AID each, script
# port 4001 (read-only sampling by the tools), optional trace FILE (keep it OUTSIDE the repository: it contains the
# logon). No key of this keymap quits: QUIT = type Q, then ENTER.
# typeahead is OFF by default in this launcher only (D33: a held arrow must not queue stale directions);
# TYPEAHEAD=true restores c3270's normal behaviour. Nothing outside this launcher is changed.
# Usage: tools/c3270_rt.sh [TRACEFILE]      TYPEAHEAD=true tools/c3270_rt.sh   (typeahead on)
set -eu
KEYMAP='<Key>UP: PF(7)\n<Key>DOWN: PF(8)\n<Key>LEFT: PF(10)\n<Key>RIGHT: PF(12)'
# RT3: P / p -> PF9 (pause) only in the TEMPORARY keymap 'pacgame', switched on by tools/rt_play.sh while a game
# runs, so logon, password and TSO commands keep a normal 'p'.
GAMEKEYS='<Key>p: PF(9)\n<Key>P: PF(9)'
set -- -model 2 -oversize auto -scriptport 4001 -xrm 'c3270.keymap: pacman' -xrm "c3270.keymap.pacman: $KEYMAP" \
  -xrm "c3270.keymap.pacgame: $GAMEKEYS" \
  ${1:+-trace -tracefile "$1"} -xrm "c3270.typeahead: ${TYPEAHEAD:-false}"
exec c3270 "$@" localhost:3270
