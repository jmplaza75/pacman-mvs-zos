MVS-G1 COMPLETE (tag mvs-g1, 2026-10-08): colour full-screen renderer TSC validated live in c3270 (JOB 161 build).
Pending note: the ESTAE abend-restore exit in PACFSIO is implemented but not validated live.
NEXT (new session): MVS-G2 - highlighting (reverse/blink/underscore/intensity) per master doc sec. 25-26, only where it
improves readability, as an option of the TSC renderer, with G1 colour and TSO monochrome as fallbacks.
Start by reading: CLAUDE.md, docs/CURRENT_PHASE.md, docs/DECISIONS.md (D22-D25), docs/G1-RENDERER.md,
docs/CAPABILITIES.md (highlighting announced by QCode 87, not yet tested visually). Regression to keep:
tests/test_g1.py (oracle 1.0-MVS + TSO + 88 TSD screens) and tests/test_core_frozen.py.
1.0-MVS is the immutable functional baseline; z/OS out of scope; G2 not started.
