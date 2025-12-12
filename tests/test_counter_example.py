"""Test the Counter example from examples/ex_module.py"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path to import examples
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.ex_module import Counter
from hdlproto import *


class TbCounterBasic(TestBench):
    """Basic testbench for Counter module"""
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.reset = Wire()
        self.enable = Wire()
        self.count_out = Wire(width=4)
        self.flag_out = Wire()
        self.counter = Counter(self.clk, self.reset, self.enable,
                              self.count_out, self.flag_out)

    def test_reset(self, simulator):
        """Test reset functionality"""
        self.reset.w = 1
        self.enable.w = 1
        simulator.clock()
        assert self.count_out.w == 0, "Expected count=0 after reset"
        return True

    def test_counting(self, simulator):
        """Test basic counting"""
        # Reset first
        self.reset.w = 1
        simulator.clock()
        self.reset.w = 0

        # Count from 0 to 5
        self.enable.w = 1
        for i in range(1, 6):
            simulator.clock()
            assert self.count_out.w == i, \
                f"Expected count={i}, got {self.count_out.w}"
        return True

    def test_enable(self, simulator):
        """Test enable signal"""
        # Reset and count to 3
        self.reset.w = 1
        simulator.clock()
        self.reset.w = 0

        self.enable.w = 1
        for _ in range(3):
            simulator.clock()

        count_at_3 = self.count_out.w
        assert count_at_3 == 3, f"Expected count=3, got {count_at_3}"

        # Disable and verify count doesn't change
        self.enable.w = 0
        for _ in range(3):
            simulator.clock()
            assert self.count_out.w == count_at_3, \
                f"Count changed while disabled: {self.count_out.w}"

        # Re-enable and verify counting resumes
        self.enable.w = 1
        simulator.clock()
        assert self.count_out.w == count_at_3 + 1, \
            f"Expected count={count_at_3 + 1}, got {self.count_out.w}"

        return True

    def test_flag(self, simulator):
        """Test flag output (should be 1 when count > threshold=4)"""
        # Reset
        self.reset.w = 1
        simulator.clock()
        self.reset.w = 0

        self.enable.w = 1

        # Count 1-4: flag should be 0
        for i in range(1, 5):
            simulator.clock()
            assert self.flag_out.w == 0, \
                f"Expected flag=0 at count={i}, got flag={self.flag_out.w}"

        # Count 5+: flag should be 1
        for i in range(5, 8):
            simulator.clock()
            assert self.flag_out.w == 1, \
                f"Expected flag=1 at count={i}, got flag={self.flag_out.w}"

        return True

    def test_overflow(self, simulator):
        """Test 4-bit overflow (15 -> 0)"""
        # Reset
        self.reset.w = 1
        simulator.clock()
        self.reset.w = 0

        # Count to 15
        self.enable.w = 1
        for _ in range(15):
            simulator.clock()

        assert self.count_out.w == 15, \
            f"Expected count=15, got {self.count_out.w}"

        # Next clock should overflow to 0
        simulator.clock()
        assert self.count_out.w == 0, \
            f"Expected overflow to 0, got {self.count_out.w}"

        return True


class TbCounterComplete(TestBench):
    """Complete testbench matching the example"""
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.reset = Wire()
        self.enable = Wire()
        self.count_out = Wire(width=4)
        self.flag_out = Wire()
        self.counter = Counter(self.clk, self.reset, self.enable,
                              self.count_out, self.flag_out)

    def run_full_test(self, simulator):
        """Run the full test sequence from ex_module.py"""
        # Expected counts after each clock (after reset)
        expected_counts = [1, 2, 3, 4, 5, 5, 5, 6, 7, 8, 9, 10]
        expected_flags = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1]

        # Reset
        self.reset.w = 1
        simulator.clock()
        self.reset.w = 0

        # Run 12 cycles
        for i in range(12):
            self.enable.w = 0 if 6 <= i + 1 <= 7 else 1
            simulator.clock()

            actual_count = self.count_out.w
            actual_flag = self.flag_out.w

            assert actual_count == expected_counts[i], \
                f"Cycle {i}: Expected count={expected_counts[i]}, got {actual_count}"
            assert actual_flag == expected_flags[i], \
                f"Cycle {i}: Expected flag={expected_flags[i]}, got {actual_flag}"

        return True


# Pytest test functions
def test_counter_reset():
    """Test Counter reset"""
    tb = TbCounterBasic()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.test_reset(sim), "Counter reset test failed"


def test_counter_counting():
    """Test Counter counting"""
    tb = TbCounterBasic()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.test_counting(sim), "Counter counting test failed"


def test_counter_enable():
    """Test Counter enable signal"""
    tb = TbCounterBasic()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.test_enable(sim), "Counter enable test failed"


def test_counter_flag():
    """Test Counter flag output"""
    tb = TbCounterBasic()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.test_flag(sim), "Counter flag test failed"


def test_counter_overflow():
    """Test Counter overflow behavior"""
    tb = TbCounterBasic()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.test_overflow(sim), "Counter overflow test failed"


def test_counter_full_sequence():
    """Test Counter with full example sequence"""
    tb = TbCounterComplete()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.run_full_test(sim), "Counter full sequence test failed"

