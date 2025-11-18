from .module.module import Module

def testcase(func):
    """A decorator to mark a method in a TestBench as a test case.

    Methods decorated with this define a test sequence to be executed by the
    simulator. Inside the method, you can control the simulation by setting
    values to top-level signals or calling methods on the `simulator` object
    passed as an argument.

    Parameters (arguments received by the decorated function)
    ---------------------------------------------------------
    simulator : Simulator
        The `Simulator` instance for controlling the simulation.
        You can advance the simulation by one clock cycle by calling
        `simulator.clock()`.

    Returns
    -------
    callable
        The decorated function.

    See Also
    --------
    TestBench, Simulator

    Examples
    --------
    >>> class MyTestBench(TestBench):
    ...     def __init__(self):
    ...         self.clk = Wire()
    ...         self.reset = Wire()
    ...         super().__init__()
    ...
    ...     @testcase
    ...     def run_reset_and_check(self, simulator):
    ...         # Reset sequence
    ...         self.reset.w = 1
    ...         simulator.clock()
    ...         self.reset.w = 0
    ...
    ...         # Check behavior for 5 clock cycles
    ...         for _ in range(5):
    ...             simulator.clock()
    """
    func._type = 'testcase'
    return func


class TestBench(Module):
    """Base class for constructing the top level of a simulation.

    Inherit from this class to define a simulation testbench.
    In the `__init__` method, define the module under test (DUT) and
    top-level signals (`Wire`) to drive it as attributes.

    Use the `@testcase` decorator to define methods that describe the
    test sequences. It is necessary to call `super().__init__()` at the end,
    after defining all signals and sub-modules.

    Examples
    --------
    >>> class MyCounter(Module):
    ...     def __init__(self, clk, reset, out):
    ...         self.clk = Input(clk)
    ...         self.reset = Input(reset)
    ...         self.out = Output(out)
    ...         self.count = Reg(width=4)
    ...         super().__init__()
    ...
    ...     @always_ff((Edge.POS, 'clk'))
    ...     def seq(self):
    ...         if self.reset.w:
    ...             self.count.r = 0
    ...         else:
    ...             self.count.r = self.count.r + 1
    ...
    ...     @always_comb
    ...     def comb(self):
    ...         self.out.w = self.count.r
    ...
    ... class MyTestBench(TestBench):
    ...     def __init__(self):
    ...         self.clk = Wire()
    ...         self.reset = Wire()
    ...         self.counter_out = Wire(width=4)
    ...         self.dut = MyCounter(self.clk, self.reset, self.counter_out)
    ...         super().__init__()
    ...
    ...     @testcase
    ...     def run_test(self, simulator):
    ...         self.reset.w = 1
    ...         simulator.clock()
    ...         self.reset.w = 0
    ...         for i in range(5):
    ...             print(f"Count is {self.counter_out.w}")
    ...             simulator.clock()
    ...
    ...     def log_sim_end(self):
    ...         print("Simulation finished.")

    See Also
    --------
    Module, testcase, Simulator
    """
    @property
    def _is_testbench(self):
        return True

    def log_sim_start(self, config):
        """Hook method called at the start of the simulation."""
        pass

    def log_testcase_start(self, name):
        """Hook method called at the start of each test case."""
        pass

    def log_clock_start(self, clock_cycle):
        """Hook method called at the start of each clock cycle."""
        pass

    def log_testcase_end(self, name):
        """Hook method called at the end of each test case."""
        pass

    def log_sim_end(self):
        """Hook method called at the end of the simulation."""
        pass