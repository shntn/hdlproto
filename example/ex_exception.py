"""
Example script that intentionally triggers HDLproto signal-access exceptions.

Usage:
    python example/ex_exception.py [scenario]

Available scenarios:
    comb_reg    - illegal Reg write inside @always_comb
    ff_wire     - illegal Wire write inside @always_ff
    conflict    - conflicting @always_comb drivers on the same Wire

Run with PYTHONPATH=. so that `hdlproto` can be imported from the repo:
    PYTHONPATH=. python example/ex_exception.py comb_reg
"""

import sys

from hdlproto import (
    Module,
    TestBench,
    Simulator,
    SimConfig,
    Reg,
    Wire,
    Input,
    always_comb,
    always_ff,
    Edge,
)


def build_simulator(tb_cls: type[TestBench]) -> Simulator:
    tb = tb_cls()
    config = SimConfig(clock=tb.clk)
    return Simulator(config, tb)


class CombWritesReg(Module):
    """Writing to Reg.r inside @always_comb triggers SignalInvalidAccess."""

    def __init__(self, clk):
        self.clk = Input(clk)
        self.reg = Reg()
        super().__init__()

    @always_comb
    def comb_logic(self):
        self.reg.r = 1


class FFWritesWire(Module):
    """Writing to Wire.w inside @always_ff triggers SignalInvalidAccess."""

    def __init__(self, clk):
        self.clk = Input(clk)
        self.out = Wire()
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def ff_logic(self):
        self.out.w = 1


class ConflictingWireDrivers(Module):
    """Two @always_comb blocks drive different values onto one Wire -> SignalWriteConflict."""

    def __init__(self, clk):
        self.clk = Input(clk)
        self.bus = Wire()
        super().__init__()

    @always_comb
    def drive_one(self):
        self.bus.w = 1

    @always_comb
    def drive_zero(self):
        self.bus.w = 0


class TbComb(TestBench):
    def __init__(self):
        self.clk = Wire()
        self.dut = CombWritesReg(self.clk)
        super().__init__()


class TbFf(TestBench):
    def __init__(self):
        self.clk = Wire()
        self.dut = FFWritesWire(self.clk)
        super().__init__()


class TbConflict(TestBench):
    def __init__(self):
        self.clk = Wire()
        self.dut = ConflictingWireDrivers(self.clk)
        super().__init__()


SCENARIOS = {
    "comb_reg": (TbComb, "Illegal Reg write inside @always_comb"),
    "ff_wire": (TbFf, "Illegal Wire write inside @always_ff"),
    "conflict": (TbConflict, "Multiple @always_comb drivers on the same Wire"),
}


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "comb_reg"
    tb_cls, description = SCENARIOS.get(scenario, (None, None))
    if tb_cls is None:
        names = ", ".join(SCENARIOS.keys())
        raise SystemExit(f"Unknown scenario '{scenario}'. Choose from: {names}")

    print(f"Running scenario '{scenario}': {description}")
    print("This run is expected to raise an HDLproto exception.\n")

    sim = build_simulator(tb_cls)
    # Exceptions thrown here show the user-code location in the traceback
    sim.clock()


if __name__ == "__main__":
    main()
