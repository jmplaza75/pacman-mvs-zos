"""MVS-S1: optional snapshot hook for the screen models. Rec is a plain list unless a log is given; then every append
also records state() - (lives, won) at the moment the screen is sent - and log.state keeps the getter, so the final
state is known after the run (the end of a game without an end screen).
MVS-S2 (D41): a Log with kinds = [] also records the kind of every screen: Q a REALTIME quantum write (the plain
frame, a final death frame), P a quantum write in prompt form (after ENTER / invalid input / PA2), E the end
screen, N any other write (default)."""


class Log(list):
    state = None
    kinds = None


class Rec(list):
    def __init__(self, log, state):
        super().__init__()
        self.log, self.state = log, state
        if log is not None:
            log.state = state

    def append(self, x, kind='N'):
        super().append(x)
        if self.log is not None:
            self.log.append(self.state())
            if self.log.kinds is not None:
                self.log.kinds.append(kind)
