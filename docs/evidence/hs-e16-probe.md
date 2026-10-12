# MVS-HS probe E16: one record in a PDS member, batch and TSO - PASS (2026-10-12, JOB 254)
Question: can PACMAN keep a high score in `HERC01.PACMAN.DATA(HISCORE)` so that a missing DD, a missing dataset, a
missing member, an empty or a garbage member never abends the game, and a rewrite never consumes PDS space?

Probe (isolated from PACMAN): src/probe/PACHSA.asm (disk service) + src/probe/PACHSP.cob (driver: PARM slots `R0000000`
= read, `Wnnnnnnn` = write 7 digits; one line per op: RC, member TTR, record). Deck: `python3 tools/make_deck.py HSP &&
python3 tools/run_deck.py build/HSP.jcl` (job PACHSP01). Scratch PDS `HERC01.PACMAN.HSPROBE` (FB, LRECL 80, BLKSIZE 80),
deleted at the start and at the end of the job. Production datasets are not touched.

## Service as validated (PACHSA)
`CALL 'PACHSA' USING OP RC DDN REC TTR`. DEVTYPE: no DD = RC 4. RDJFCB: the DD must name a member (else RC 8). The PDS
is opened BPAM INPUT with the member removed from a private JFCB copy (`OPEN ... TYPE=J`, JFCNWRIT set) and the member
is looked up with BLDL: missing = RC 12 on READ. READ = FIND + READ of the first block (EODAD on an empty member = RC
12). WRIT of an existing member = QSAM `OPEN UPDAT`, GET + PUTX of the first record (same block, RC 0); WRIT of a
missing member = QSAM OUTPUT + PUT (STOW at CLOSE, RC 2). Before any QSAM OPEN a fresh RDJFCB must still show the same
member on the DD (else RC 8), so the PDS can never be opened as a sequential dataset. Attributes other than RECFM F(B),
LRECL 80, BLKSIZE 80 = RC 8. I/O error (SYNAD) = RC 16.

## Defects found and fixed during the probe (JOBs 249-253)
| Job | Finding | Fix |
|---|---|---|
| 249 | A BPAM OPEN still searches a member named on the DD: `IEC141I 013-18 IGG0191B` on the missing member | member removed from a JFCB copy, `OPEN TYPE=J`; BLDL finds the member |
| 250 | JCL error: PARM beyond column 71 | PARM on a continuation card (deck only) |
| 251 | Every second call in one run got RC 8: OPEN TYPE=J wrote the member-less JFCB back to the DD | JFCBTSDM X'08' (JFCNWRIT); safety re-check before every QSAM OPEN |
| 252 | BPAM `OPEN UPDAT` + `WRITE ... MF=E` abended S800 | rewrite by QSAM UPDAT (GET locate + PUTX) on the member BLDL has found |
| 253 | all cases PASS | - |
| 254 | final run incl. the CLIST check below (evidence of this file) | - |

## JOB 254 results
Steps DEL0 ALC SRC1 COB1 ASM1 (IFOX00 highest severity 0) LINK B1NODD B2NEW B3UPD B4SHR B5NOMEM GENBAD GENEMP B6BAD
B7EMPTY TSO1 GENCL LIST1 LIST2 LIST3 DEL9: RC 0000. TSO2: RC 0012 (expected, see the CLIST case). No abend.

| Case | DD | Ops | Result (RC, TTR, record) | Verdict |
|---|---|---|---|---|
| B1NODD | none | R, W0000111 | 04, 04 | no DD = nothing done, no abend |
| B2NEW | `HSPROBE(HISCORE),DISP=OLD`, member missing | R, W0001230, R | 12; 02 (created); 00 TTR 000004 `0001230` | missing = 12, first write creates |
| B3UPD | same, next step | R, W0004560, R | 00 `0001230` TTR 000004; 00; 00 `0004560` TTR 000004 | persists across steps; update in place (same TTR) |
| B4SHR | same, `DISP=SHR` | R, W0004561, R | 00 TTR 000004 each, `0004561` | SHR works; still the same block |
| B5NOMEM | `HSPROBE,DISP=SHR` (no member) | R, W0000222 | 08, 08 | refused; PDS not opened as sequential |
| B6BAD | member `BAD` = `XYZZY NOT A SCORE` | R | 00 TTR 000006 `XYZZY NOT A SCORE` | raw record returned; validation is the caller's |
| B7EMPTY | member `EMPTY` (IEBGENER from DUMMY) | R, W0000333, R | 12 TTR 000008; 08; 12 | empty = 12; an existing empty member is not rewritten |
| TSO1 a | `ALLOC FI(PACHS) DA('...HSPROBE(HISCORE)') SHR` | R, W0007890, R | 00 `0004561`; 00; 00 `0007890`, TTR 000004 | TSO (IKJEFT01) = batch; still the same block |
| TSO1 b | ALLOC of a missing member `TSONEW` SHR | R, W0000042, R | 12; 02; 00 TTR 000009 `0000042` | TSO ALLOC accepts a missing member; create works |
| TSO1 c | ALLOC of a missing dataset `HERC01.PACMAN.NOSUCH` | R | `IKJ56228I` (no DD), then 04 | a failed ALLOC = no DD = RC 4 |
| LIST1-3 | IEBGENER prints | - | `0007890 E16 PROBE RECORD`, `0000042 E16 PROBE RECORD`, `XYZZY NOT A SCORE` | independent read-back |

CLIST check (TSO2, a CLIST stored in the scratch PDS and run by `EXEC` under IKJEFT01):
```
E16C SYSDSN1=OK                      &SYSDSN('HERC01.PACMAN.HSPROBE')
E16C SYSDSN2=DATASET NOT FOUND       &SYSDSN('HERC01.PACMAN.NOSUCH')
IKJ56228I DATA SET HERC01.PACMAN.NOSUCH NOT IN CATALOG ...   (ALLOC ... SHR REUSE)
```
Nothing after the failed ALLOC ran (no `LASTCC1=` line): a failed ALLOC ends the CLIST (TMP RC 12).

## Conclusions
- Persistent single-record storage in a PDS member works from batch and TSO with no abend for: no DD, missing dataset
  (TSO ALLOC fails = no DD), DD without a member, missing member, empty member, garbage content.
- Rewrites are in place (the member kept TTR 000004 through the rewrites of B3, B4 and TSO1): no PDS space is
  consumed, no compress needed.
  Only the first write of a missing member allocates one block.
- The PDS must be RECFM FB, LRECL 80, BLKSIZE 80 (one record per block); anything else is refused (RC 8).
- The PACMAN CLIST must not ALLOC the high-score member unless `&SYSDSN('...DATA') = OK`: an unguarded failing ALLOC
  would end the CLIST before the game starts.
