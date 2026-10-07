      * PACPLAT : PLATFORM ADAPTER (MVS 3.8J). OPS : INIT FINI CLS.
      * INIT validates the requested REQ-MODE (BAT cards or TSO
      * interactive); anything else falls back to BAT. FINI sets the
      * return code. CLS (TSO only) makes the next line start a
      * fresh screen via PACTSO, avoiding '***' paging; in batch
      * PACTSO does nothing. GAME/MAP/AI never see any of this.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACPLAT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  TSO-OP                PIC X(4) VALUE 'CLS '.
       01  TSO-RC                PIC S9(4) COMP.
       LINKAGE SECTION.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'INIT'
               PERFORM DO-INIT THRU DO-INIT-EXIT
           ELSE IF REQ-OP = 'FINI'
               MOVE 0 TO RETURN-CODE
           ELSE IF REQ-OP = 'CLS ' AND REQ-MODE = 'TSO'
               CALL 'PACTSO' USING TSO-OP TSO-RC.
           GOBACK.
       DO-INIT.
           IF REQ-MODE NOT = 'TSO'
               MOVE 'BAT' TO REQ-MODE.
       DO-INIT-EXIT.
           EXIT.
