# ZOS-6 R1-T3 - derived protocol analysis (Derived protocol analysis; not ZOS-6 acceptance evidence)

Raw trace outside git: R1-T3, SHA-256 11408477c0aad7de28960b5b1b155a3639e6e1096cb401f6bd055d93c8cc1a64 (read-only).
Classification: R1-T3 PROTOCOL/INPUT BLOCKED. Not a PACMAN functional failure; not a driver defect.

## Facts from the trace
- Functions negotiated: 00 BIND-IMAGE, 02 RESPONSES, 04 SYSREQ, 05 CONTENTION-RESOLUTION.
- Transition EXEC and ENTER delivered; PF8 left the terminal at 22:49:50.013 (3270-DATA, flags 00 / 00, terminal SEQ
  000B, payload F8 6F D9) and the host answered (F1 C3 write, RQ 03, then BID / RESPONSE).
- PF8 -> the driver's PF9 Wait(5,Unlock) timeout (65.5 s): 432 game writes (all REQUEST-FLAG 00: no SDI, no KRI),
  24 BID (09 / 00 / 02, all answered positively in 0-1 ms; no SIGNAL), 24 empty 3270-DATA records with REQUEST-FLAG 03
  (SEND-DATA | KEYBOARD-RESTORE), no terminal AID after PF8.
- Cycle: an empty SDI + KRI record returns the send state to the terminal; the next host output starts a new bracket
  with a BID ~116 ms later (positive response: X-CLOCK, keyboard locked); the host keeps direction for a long run of
  RQ 00 writes until the next empty SDI + KRI. Unlock windows: 92 in the whole trace, 114-197 ms (median 116); between
  SDI + KRI records the median gap is 2.1 s, nine gaps exceed 4 s, the longest 46.8 s.
- The Wait(5,Unlock) ran from +60.546 s to +65.547 s inside a 25.9 s interval (+53.966 s .. +79.836 s) without any
  SDI / KRI: no protocol-valid send opportunity existed; PF9 was correctly not sent.
- Every PACMAN write carries the WCC keyboard-restore bit (F1 C2 / F1 C3); under CONTENTION-RESOLUTION c3270 unlocks
  only on KRI / SDI ("Keyboard unlock(kybd_send_data)"), so the WCC restore does not decide send ownership.
- Game-write delivery PF8 -> timeout: mean gap 151.6 ms, median 117, p95 406, max 701 (one record per round trip in
  bursts). BID response -> next host data: median 115 ms, p95 171, max 179.
- After Trace(Off) (not in T3): a direct `x3270if PF(9)` returned rc 0; the screen stayed RUNNING after > 3 s. This is
  not proof that F9 reached the host.

## Protocol semantics (IBM z/OS Communications Server; TN3270E Functional Extensions draft)
KRI is sent when the host VTAM application sends End Bracket; SDI when it sends change direction or End Bracket; a
host BID is forwarded to the client; after a positive BID response the client is input-inhibited and may not send data
until SDI; a server never BIDs while the host already holds direction; only ATTN / SYSREQ may be sent while inhibited.
So the terminal can send a PF AID only between a host End Bracket / change direction and the next BID.

## Checker finding
Empty 3270-DATA SDI + KRI records are legal z/OS TN3270E control records; the ZOS-5 parser (frozen) rejects any empty
3270-DATA. tools/zowe/zos6_live_check.py now accepts exactly that form (REQUEST-FLAG X'03', CONTENTION-RESOLUTION
negotiated) as a control record, outside the game writes and the model, visible in the send-state diagnostics.
