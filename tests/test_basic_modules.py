"""Test basic HDL modules using HDLproto"""
from hdlproto import *


class DFF(Module):
    """Simple D Flip-Flop"""
    def __init__(self, clk, d, q):
        super().__init__()
        self.clk = InputWire(clk)
        self.d = InputWire(d)
        self.q = OutputWire(q)
        self.q_reg = Reg()

    @always_ff((Edge.POS, 'clk'))
    def ff_logic(self):
        self.q_reg.r = self.d.w

    @always_comb
    def output_logic(self):
        self.q.w = self.q_reg.r


class TbDFF(TestBench):
    """Testbench for D Flip-Flop"""
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.d = Wire()
        self.q = Wire()
        self.dff = DFF(self.clk, self.d, self.q)

    def run_test(self, simulator):
        """Test D flip-flop behavior"""
        # Test 1: d=0 -> q=0
        self.d.w = 0
        simulator.clock()
        assert self.q.w == 0, "Expected q=0 when d=0"

        # Test 2: d=1 -> q=1
        self.d.w = 1
        simulator.clock()
        assert self.q.w == 1, "Expected q=1 when d=1"

        # Test 3: d=0 -> q=0
        self.d.w = 0
        simulator.clock()
        assert self.q.w == 0, "Expected q=0 when d=0"

        return True


class SimpleCounter(Module):
    """Simple 4-bit counter with reset"""
    def __init__(self, clk, reset, count):
        super().__init__()
        self.clk = InputWire(clk)
        self.reset = InputWire(reset)
        self.count = OutputWire(count)
        self.cnt_reg = Reg(width=4)

    @always_ff((Edge.POS, 'clk'), (Edge.POS, 'reset'))
    def count_logic(self):
        if self.reset.w:
            self.cnt_reg.r = 0
        else:
            self.cnt_reg.r = self.cnt_reg.r + 1

    @always_comb
    def output_logic(self):
        self.count.w = self.cnt_reg.r


class TbSimpleCounter(TestBench):
    """Testbench for Simple Counter"""
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.reset = Wire()
        self.count = Wire(width=4)
        self.counter = SimpleCounter(self.clk, self.reset, self.count)

    def run_test(self, simulator):
        """Test counter behavior"""
        # Test reset
        self.reset.w = 1
        simulator.clock()
        assert self.count.w == 0, "Expected count=0 after reset"

        # Test counting
        self.reset.w = 0
        for i in range(1, 6):
            simulator.clock()
            assert self.count.w == i, f"Expected count={i}, got {self.count.w}"

        # Test reset again
        self.reset.w = 1
        simulator.clock()
        assert self.count.w == 0, "Expected count=0 after second reset"

        return True


class Adder(Module):
    """Combinational adder"""
    def __init__(self, a, b, sum_out):
        super().__init__()
        self.a = InputWire(a)
        self.b = InputWire(b)
        self.sum_out = OutputWire(sum_out)

    @always_comb
    def add_logic(self):
        self.sum_out.w = self.a.w + self.b.w


class TbAdder(TestBench):
    """Testbench for Adder"""
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.a = Wire(width=4)
        self.b = Wire(width=4)
        self.sum_out = Wire(width=5)
        self.adder = Adder(self.a, self.b, self.sum_out)

    def run_test(self, simulator):
        """Test adder behavior"""
        test_cases = [
            (0, 0, 0),
            (1, 1, 2),
            (3, 5, 8),
            (15, 1, 16),
            (7, 8, 15),
        ]

        for a_val, b_val, expected in test_cases:
            self.a.w = a_val
            self.b.w = b_val
            simulator.clock()
            assert self.sum_out.w == expected, \
                f"Expected {a_val} + {b_val} = {expected}, got {self.sum_out.w}"

        return True


# Pytest test functions
def test_dff():
    """Test D Flip-Flop module"""
    tb = TbDFF()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.run_test(sim), "DFF test failed"


def test_simple_counter():
    """Test Simple Counter module"""
    tb = TbSimpleCounter()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.run_test(sim), "Simple Counter test failed"


def test_adder():
    """Test Adder module"""
    tb = TbAdder()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.run_test(sim), "Adder test failed"

