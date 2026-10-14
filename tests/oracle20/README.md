# oracle20: frozen 2.0-MVS-MAX functional oracle (ZOS-0, docs/ZOS-MIGRATION-PLAN.md sec. 2 / 13)
One gzip JSON per job of record (JOBs 307-312, 315, 316 on TK4-): step table (step, program, RC) and the ordered
program-output stream (right-stripped lines). Built by `tools/oracle_extract.py extract --build <MVS build dir>`;
`render` rebuilds a listing the existing tests accept; `verify` checks SHA256SUMS. Never edited by hand.
