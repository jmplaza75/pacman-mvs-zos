# Pac-Man for z/OS

A real-time Pac-Man written in COBOL with a few small assembler services. It runs entirely on an IBM mainframe and is
played on a 3270 terminal (TSO).

![READY! screen](releases/2.0-MVS-MAX/screenshots/g8-01-ready.png)

> **You are on the `zos` branch: the z/OS port (release 2.1-zos).**
> The original MVS 3.8J / Hercules version is in the
> [**`main` branch**](https://github.com/jmplaza75/pacman-mvs-zos/tree/main).

## Which branch is which

| Branch | Platform | Release | Toolchain |
|---|---|---|---|
| [`main`](https://github.com/jmplaza75/pacman-mvs-zos/tree/main) | MVS 3.8J (TK4-) on Hercules | 2.1-mvs | IBM OS COBOL, assembler |
| **`zos`** (this one) | IBM z/OS V3R1 | 2.1-zos | Enterprise COBOL 6.5, HLASM, LE |

This branch contains both versions. The game core is shared. The z/OS parts are in `jcl/zos/`, `src/zos/`,
`tools/zowe/` and `releases/2.1-ZOS/`. The differences from MVS are listed in [`docs/ZOS-DIFFS.md`](docs/ZOS-DIFFS.md).

## What you get

- Arcade rules: power pellets, frightened ghosts, levels, fruit, extra lives.
- Real time: the game moves by itself every 150 ms.
- Colour 3270 screen with a scaled maze, partial redraw and animation.
- Terminal bell as sound, with a different pattern per event.
- Four ghost AI levels, deterministic and testable.
- A persistent high score kept in a z/OS dataset.

## Requirements

- A z/OS 3.1 system with TSO. It was developed and tested on IBM Z Xplore.
- Enterprise COBOL 6.5 and HLASM on that system.
- [Zowe CLI](https://docs.zowe.org/) with a working z/OSMF profile.
- A 3270 emulator such as `c3270`.
- Python 3 on your computer.

## Play

1. Make the terminal window 120 x 30, then connect:
   ```bash
   c3270 -model 2 -oversize auto <host>:623
   ```
2. Log on to TSO.
3. At `READY` (or ISPF option 6), start the game:
   ```
   EXEC '<HLQ>.PACMAN.CLIST(PACMAN)'
   ```
   `<HLQ>` is your user ID. With no operand you get the arcade game in real time.

Pac-Man waits for your first move, then keeps going on his own.

### Controls

| Action | Key |
|---|---|
| Up / Down / Left | PF7 / PF8 / PF10 |
| Right | PF12 |
| Pause / resume | PF9 |
| Redraw the screen | PA2 |
| Quit | type `Q`, then ENTER |

`tools/c3270_rt.sh` maps the arrow keys to these PF keys. No PF key quits the game.

### Options

Add options in quotes after the CLIST name:

```
EXEC '<HLQ>.PACMAN.CLIST(PACMAN)' 'RULES(CLASSIC) PLAY(TURN)'
EXEC '<HLQ>.PACMAN.CLIST(PACMAN)' 'SPEED(FAST) SOUND(NO)'
EXEC '<HLQ>.PACMAN.CLIST(PACMAN)' 'COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC)'
```

All options and their defaults are in [`releases/2.0-ZOS/DEFAULTS.md`](releases/2.0-ZOS/DEFAULTS.md).

## Install on your own z/OS user

There is no one-command installer yet. Read this before you try.

The job decks use `@@HLQ@@` instead of a user ID, so nothing is tied to one account. Every dataset is created under
`<HLQ>.PACMAN.*`.

The 2.1-zos decks assume that an earlier release is already installed. They build into new `RZ21` libraries and then
copy the program and the CLIST over the installed ones. The steps are:

1. `PACZ11AL.jcl` allocates the empty `RZ21` libraries.
2. `tools/zowe/zos11_release.py --zos upload` uploads the sources and the CLIST.
3. `PACZ11BL.jcl` compiles, assembles and binds.
4. `PACZ11IP.jcl` and `PACZ11IC.jcl` install the program and the CLIST.

The decks are in `releases/2.1-ZOS/decks/`. Submit each one once:

```bash
python3 tools/zowe/zos_submit.py releases/2.1-ZOS/decks/PACZ11AL.jcl --hlq <HLQ>
```

The tool checks that a deck only writes under `<HLQ>.PACMAN.*` and never deletes anything.

On a clean account you also need the base datasets first (`LOAD`, `CLIST`, `DATA`, `CEEOPTS`). Their layout and the site
quirks, such as allocating in tracks, are in [`docs/zos-build.md`](docs/zos-build.md). The decks that created them are in
`jcl/zos/` (`PACZALLO.jcl`, `PACZ4INS.jcl`).

## Repository layout

| Path | Contents |
|---|---|
| `src/` | COBOL, assembler and copybooks. `src/zos/` has the z/OS launcher. |
| `jcl/zos/`, `releases/*/decks/` | z/OS job decks |
| `tools/zowe/` | Zowe-based tools: submit, upload, check |
| `tests/` | Python models and regression tests (no mainframe needed) |
| `docs/` | Design notes, decisions, evidence |
| `releases/` | Release notes, manifests, checksums |

## Tests

The game rules are checked against independent Python models with fixed seeds. Run one test at a time:

```bash
python3 tests/test_core_frozen.py
```

Some tests compare the code with release tags, so clone with the tags (`git clone` does this by default).

## More documentation

- [`docs/FULL-GUIDE.md`](docs/FULL-GUIDE.md): the complete original guide, with every phase and option.
- [`docs/zos-build.md`](docs/zos-build.md): the z/OS build procedure.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): how the program is layered.
- [`docs/DECISIONS.md`](docs/DECISIONS.md): rules and design decisions.
- [`releases/2.1-ZOS/RELEASE-NOTES.md`](releases/2.1-ZOS/RELEASE-NOTES.md): what changed in 2.1-zos.

## License

MIT, see [LICENSE](LICENSE).
