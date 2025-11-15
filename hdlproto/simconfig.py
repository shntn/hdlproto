from hdlproto.signal.signal import Wire


class SimConfig:
    def __init__(self, clock: Wire, max_comb_loops: int = 30):
        self.max_comb_loops = max_comb_loops
        self.clock = clock

    def __iter__(self):
        for attr in self.__dict__:
            if not attr.startswith("_"):
                yield attr

    def items(self):
        for attr in self:
            yield attr, getattr(self, attr)