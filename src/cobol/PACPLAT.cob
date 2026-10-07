      * PACPLAT : PLATFORM ADAPTER (MVS 3.8J BATCH). OPS : INIT FINI.
      * Holds everything that depends on the host: start-up checks,
      * and the final return code. Pause/terminal services are added
      * here (MVS-8) so GAME/MAP/AI never see them.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PACPLAT.
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-370.
       OBJECT-COMPUTER. IBM-370.
       DATA DIVISION.
       LINKAGE SECTION.
       01  PAC-REQ COPY PACREQ.
       PROCEDURE DIVISION USING PAC-REQ.
       MAIN-PARA.
           IF REQ-OP = 'FINI'
               MOVE 0 TO RETURN-CODE.
           GOBACK.
