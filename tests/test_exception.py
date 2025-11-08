import pytest

from hdlproto import (
    Module,
    TestBench as HDLTestBench,
    Simulator,
    SimConfig,
    Reg,
    Wire,
    always_comb,
    always_ff,
)
from hdlproto.error import SignalInvalidAccess, SignalWriteConflict


def build_simulator(testbench_cls):
    config = SimConfig()
    tb = testbench_cls()
    return Simulator(config, tb)


class CombWritesReg(Module):
    def __init__(self):
        self.reg = Reg()
        super().__init__()

    @always_comb
    def comb_logic(self):
        self.reg.r = 1


class FFWritesWire(Module):
    def __init__(self):
        self.out = Wire()
        super().__init__()

    @always_ff
    def ff_logic(self, reset):
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
            self.dut = CombWritesReg()
            super().__init__()

    sim = build_simulator(Tb)
    with pytest.raises(SignalInvalidAccess):
        sim.reset()


def test_always_ff_wire_write_raises_signal_invalid_access():
    class Tb(HDLTestBench):
        def __init__(self):
            self.dut = FFWritesWire()
            super().__init__()

    sim = build_simulator(Tb)
    with pytest.raises(SignalInvalidAccess):
        sim.reset()


def test_conflicting_signal_writes_raise_signal_write_conflict():
    class Tb(HDLTestBench):
        def __init__(self):
            self.dut = ConflictingWireDrivers()
            super().__init__()

    sim = build_simulator(Tb)
    with pytest.raises(SignalWriteConflict):
        sim.reset()
