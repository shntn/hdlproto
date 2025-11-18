from .signal import Wire


class SimConfig:
    """A class that holds settings for controlling the behavior of the simulation.

    An instance of this class is passed when initializing the `Simulator`.
    It defines global settings that affect the entire simulation.

    Parameters
    ----------
    clock : Wire
        The reference clock signal for the simulation.
        This signal is automatically driven by the simulator.
    max_comb_loops : int, optional
        The maximum number of attempts for the combinational circuit stabilization loop. Defaults to `30`.
        If the signal values do not stabilize after this number of attempts, a `SignalUnstableError` is raised.

    Examples
    --------
    >>> # Create settings specifying the testbench's clock signal
    >>> tb = MyTestBench()
    >>> config = SimConfig(clock=tb.clk, max_comb_loops=50)
    ...
    >>> # Pass the settings to the simulator
    >>> sim = Simulator(config, tb)

    See Also
    --------
    Simulator, TestBench
    """
    def __init__(self, clock: Wire, max_comb_loops: int = 30):
        self.max_comb_loops = max_comb_loops
        self.clock = clock

    def __iter__(self):
        for attr, value in self.__dict__.items():
            if not attr.startswith("_"):
                yield attr, value
