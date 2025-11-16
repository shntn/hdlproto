from .signal import Wire


class SimConfig:
    def __init__(self, clock: Wire, max_comb_loops: int = 30):
        self.max_comb_loops = max_comb_loops
        self.clock = clock

    def __iter__(self):
        for attr, value in self.__dict__.items():
            if not attr.startswith("_"):
                yield attr, value
