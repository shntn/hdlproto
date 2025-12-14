"""Test advanced HDL modules and features"""
from hdlproto import *


class ShiftRegister(Module):
    """3-stage shift register"""
    def __init__(self, clk, din, dout):
        super().__init__()
        self.clk = InputWire(clk)
        self.din = InputWire(din)
        self.dout = OutputWire(dout)
        self.stage0 = Reg()
        self.stage1 = Reg()
        self.stage2 = Reg()

    @always_ff((Edge.POS, 'clk'))
    def shift_logic(self):
        self.stage2.r = self.stage1.r
        self.stage1.r = self.stage0.r
        self.stage0.r = self.din.w

    @always_comb
    def output_logic(self):
        self.dout.w = self.stage2.r


class TbShiftRegister(TestBench):
    """Testbench for Shift Register"""
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.din = Wire()
        self.dout = Wire()
        self.shiftreg = ShiftRegister(self.clk, self.din, self.dout)

    def run_test(self, simulator):
        """Test shift register with pattern 1,0,1,1,0"""
        pattern = [1, 0, 1, 1, 0]

        # Shift in the pattern and check output
        # After 1st clock: stage0=1, stage1=0, stage2=0, out=0
        self.din.w = pattern[0]
        simulator.clock()
        assert self.dout.w == 0, f"Clock 0: Expected dout=0, got {self.dout.w}"

        # After 2nd clock: stage0=0, stage1=1, stage2=0, out=0
        self.din.w = pattern[1]
        simulator.clock()
        assert self.dout.w == 0, f"Clock 1: Expected dout=0, got {self.dout.w}"

        # After 3rd clock: stage0=1, stage1=0, stage2=1, out=1
        self.din.w = pattern[2]
        simulator.clock()
        assert self.dout.w == 1, f"Clock 2: Expected dout=1, got {self.dout.w}"

        # After 4th clock: stage0=1, stage1=1, stage2=0, out=0
        self.din.w = pattern[3]
        simulator.clock()
        assert self.dout.w == 0, f"Clock 3: Expected dout=0, got {self.dout.w}"

        # After 5th clock: stage0=0, stage1=1, stage2=1, out=1
        self.din.w = pattern[4]
        simulator.clock()
        assert self.dout.w == 1, f"Clock 4: Expected dout=1, got {self.dout.w}"

        return True


class Mux2to1(Module):
    """2-to-1 multiplexer"""
    def __init__(self, a, b, sel, out):
        super().__init__()
        self.a = InputWire(a)
        self.b = InputWire(b)
        self.sel = InputWire(sel)
        self.out = OutputWire(out)

    @always_comb
    def mux_logic(self):
        if self.sel.w:
            self.out.w = self.b.w
        else:
            self.out.w = self.a.w


class TbMux2to1(TestBench):
    """Testbench for 2-to-1 Mux"""
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.a = Wire(width=4)
        self.b = Wire(width=4)
        self.sel = Wire()
        self.out = Wire(width=4)
        self.mux = Mux2to1(self.a, self.b, self.sel, self.out)

    def run_test(self, simulator):
        """Test mux selection"""
        self.a.w = 5
        self.b.w = 10

        # Select a
        self.sel.w = 0
        simulator.clock()
        assert self.out.w == 5, f"Expected out=5 when sel=0, got {self.out.w}"

        # Select b
        self.sel.w = 1
        simulator.clock()
        assert self.out.w == 10, f"Expected out=10 when sel=1, got {self.out.w}"

        # Change inputs and verify
        self.a.w = 3
        self.b.w = 7

        self.sel.w = 0
        simulator.clock()
        assert self.out.w == 3, f"Expected out=3 when sel=0, got {self.out.w}"

        self.sel.w = 1
        simulator.clock()
        assert self.out.w == 7, f"Expected out=7 when sel=1, got {self.out.w}"

        return True


class RegisteredAdder(Module):
    """Adder with registered output"""
    def __init__(self, clk, a, b, sum_out):
        super().__init__()
        self.clk = InputWire(clk)
        self.a = InputWire(a)
        self.b = InputWire(b)
        self.sum_out = OutputWire(sum_out)
        self.sum_reg = Reg(width=5)

    @always_ff((Edge.POS, 'clk'))
    def register_logic(self):
        self.sum_reg.r = self.a.w + self.b.w

    @always_comb
    def output_logic(self):
        self.sum_out.w = self.sum_reg.r


class TbRegisteredAdder(TestBench):
    """Testbench for Registered Adder"""
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.a = Wire(width=4)
        self.b = Wire(width=4)
        self.sum_out = Wire(width=5)
        self.adder = RegisteredAdder(self.clk, self.a, self.b, self.sum_out)

    def run_test(self, simulator):
        """Test registered adder with pipeline delay"""
        # Set inputs and clock - the register captures 3+5
        self.a.w = 3
        self.b.w = 5
        simulator.clock()
        # After clock, register has captured 3+5=8
        assert self.sum_out.w == 8, \
            f"Expected sum_out=8, got {self.sum_out.w}"

        # Keep same inputs, clock again
        simulator.clock()
        assert self.sum_out.w == 8, \
            f"Expected sum_out=8 (same), got {self.sum_out.w}"

        # Change inputs and clock - register captures 7+9
        self.a.w = 7
        self.b.w = 9
        simulator.clock()
        assert self.sum_out.w == 16, \
            f"Expected sum_out=16, got {self.sum_out.w}"

        return True


class Inverter(Module):
    """Simple inverter"""
    def __init__(self, inp, out):
        super().__init__()
        self.inp = InputWire(inp)
        self.out = OutputWire(out)

    @always_comb
    def invert_logic(self):
        self.out.w = ~self.inp.w & 1


class DoubleInverter(Module):
    """Two inverters in series (submodule test)"""
    def __init__(self, inp, out):
        super().__init__()
        self.inp = InputWire(inp)
        self.out = OutputWire(out)
        self.temp = Wire()
        # サブモジュールには実際のWireを渡す（Input/Outputのターゲット）
        self.inv1 = Inverter(inp, self.temp)
        self.inv2 = Inverter(self.temp, out)


class TbDoubleInverter(TestBench):
    """Testbench for Double Inverter (tests submodule hierarchy)"""
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.inp = Wire()
        self.out = Wire()
        self.double_inv = DoubleInverter(self.inp, self.out)

    def run_test(self, simulator):
        """Test double inverter (should be identity)"""
        # Test 0 -> 0
        self.inp.w = 0
        simulator.clock()
        assert self.out.w == 0, f"Expected out=0 when inp=0, got {self.out.w}"

        # Test 1 -> 1
        self.inp.w = 1
        simulator.clock()
        assert self.out.w == 1, f"Expected out=1 when inp=1, got {self.out.w}"

        return True


# Pytest test functions
def test_shift_register():
    """Test Shift Register module"""
    tb = TbShiftRegister()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.run_test(sim), "Shift Register test failed"


def test_mux2to1():
    """Test 2-to-1 Multiplexer module"""
    tb = TbMux2to1()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.run_test(sim), "Mux2to1 test failed"


def test_registered_adder():
    """Test Registered Adder module"""
    tb = TbRegisteredAdder()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.run_test(sim), "Registered Adder test failed"


def test_double_inverter():
    """Test Double Inverter (submodule hierarchy)"""
    tb = TbDoubleInverter()
    sim = Simulator(testbench=tb, clock=tb.clk)
    assert tb.run_test(sim), "Double Inverter test failed"

