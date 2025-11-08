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
    always_comb,
    always_ff,
)


def build_simulator(tb_cls: type[TestBench]) -> Simulator:
    config = SimConfig()
    tb = tb_cls()
    return Simulator(config, tb)


class CombWritesReg(Module):
    """@always_comb で Reg.r に書き込み -> SignalInvalidAccess になる"""

    def __init__(self):
        self.reg = Reg()
        super().__init__()

    @always_comb
    def comb_logic(self):
        self.reg.r = 1


class FFWritesWire(Module):
    """@always_ff で Wire.w に書き込み -> SignalInvalidAccess になる"""

    def __init__(self):
        self.out = Wire()
        super().__init__()

    @always_ff
    def ff_logic(self, reset):
        self.out.w = 1


class ConflictingWireDrivers(Module):
    """2つの @always_comb が同じ Wire に異なる値を書き込み -> SignalWriteConflict"""

    def __init__(self):
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
        self.dut = CombWritesReg()
        super().__init__()


class TbFf(TestBench):
    def __init__(self):
        self.dut = FFWritesWire()
        super().__init__()


class TbConflict(TestBench):
    def __init__(self):
        self.dut = ConflictingWireDrivers()
        super().__init__()


SCENARIOS = {
    "comb_reg": (TbComb, "Reg への @always_comb 書き込み"),
    "ff_wire": (TbFf, "Wire への @always_ff 書き込み"),
    "conflict": (TbConflict, "同一 Wire への複数 always_comb ドライバ"),
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
    # ここで例外が発生し、トレースバックにユーザコードの場所が表示される
    sim.reset()


if __name__ == "__main__":
    main()
