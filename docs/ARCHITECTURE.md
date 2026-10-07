# Architecture
Target layers (requirements sec. 3): GAME/CORE, MAP, AI, INPUT, DISPLAY, PLATFORM. Until MVS-7 the engine is a
single program, PACMAIN, with paragraphs separated by responsibility (map data, input read, move logic, render)
so the later split needs no logic changes. State fields follow sec. 6 (PLAYER-X/Y, SCORE, PELLETS-LEFT, TICK-COUNT).
Sources: src/cobol (.cob), src/copy; maps/LEVEL1.txt mirrors the map literals (checked by tests).
