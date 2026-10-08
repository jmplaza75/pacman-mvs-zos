MVS-G2 COMPLETE (tag mvs-g2, 2026-10-08): highlighting option HILITE(AUTO|YES|NO) of the TSC renderer, built and tested
on Hercules (JOB 164, 56 steps RC 0000, oracle identical, 132 TSC screens = independent model) and validated live in c3270
(docs/evidence/g2-manual-c3270.md).
Pending note (carried since G1, not G2 work): the ESTAE abend-restore exit in PACFSIO is implemented but not validated live.
NEXT (new session): MVS-G3 per the master doc (animation / partial redraw ladder, see docs/CAPABILITIES.md "Viable update
rate"). Not started.
Start by reading: CLAUDE.md, docs/CURRENT_PHASE.md, docs/DECISIONS.md (D22-D26), docs/G1-RENDERER.md, docs/G2-HIGHLIGHT.md,
docs/CAPABILITIES.md. Regression to keep: tests/test_g2.py (oracle 1.0-MVS + TSO + 132 TSC screens) and
tests/test_core_frozen.py. 1.0-MVS is the immutable functional baseline; z/OS out of scope.
