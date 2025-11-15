import pytest

from hdlproto import (
    Module,
    TestBench as HDLTestBench,
    Simulator,
    SimConfig,
    Reg,
    Wire,
    Input,
    always_comb,
    always_ff,
    Edge,
)
from hdlproto.error import SignalInvalidAccess, SignalWriteConflict


def build_simulator(testbench_cls):
    tb = testbench_cls()
    config = SimConfig(clock=tb.clk)
    return Simulator(config, tb)


class CombWritesReg(Module):
    def __init__(self):
        self.reg = Reg()
        super().__init__()

    @always_comb
    def comb_logic(self):
        self.reg.r = 1


class FFWritesWire(Module):
    def __init__(self, clk):
        self.clk = Input(clk)
        self.out = Wire()
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def ff_logic(self):
        self.out.w = 1


class ConflictingWireDrivers(Module):
    def __init__(self):
        self.bus = Wire()
        super().__init__()

    @always_comb
    def drive_one(self):
        self.bus.w = 1

    @always_comb
    def drive_zero(self):
        self.bus.w = 0


def test_always_comb_reg_write_raises_signal_invalid_access():
    class Tb(HDLTestBench):
        def __init__(self):
            self.clk = Wire()
            self.dut = CombWritesReg()
            super().__init__()

    sim = build_simulator(Tb)
    with pytest.raises(SignalInvalidAccess):
        sim.clock()


def test_always_ff_wire_write_raises_signal_invalid_access():
    class Tb(HDLTestBench):
        def __init__(self):
            self.clk = Wire()
            self.dut = FFWritesWire(self.clk)
            super().__init__()

    sim = build_simulator(Tb)
    with pytest.raises(SignalInvalidAccess):
        sim.clock()


def test_conflicting_signal_writes_raise_signal_write_conflict():
    class Tb(HDLTestBench):
        def __init__(self):
            self.clk = Wire()
            self.dut = ConflictingWireDrivers()
            super().__init__()

    sim = build_simulator(Tb)
    with pytest.raises(SignalWriteConflict):
        sim.clock()
