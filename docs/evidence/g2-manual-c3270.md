# MVS-G2 manual validation in c3270 (reported by the user, 2026-10-08; build JOB 164, CLIST JOB 165)
Confirmed live: P and G in reverse video; command input field underlined; `INVALID COMMAND X` blinks;
`HILITE(NO)` gives the G1 look; `COLOR(NO)` keeps the monochrome line mode; no visual regressions in the TSC renderer.
Not covered (not G2 work): the ESTAE abend-restore exit in PACFSIO remains implemented but not validated live.
