import pytest

from hdlproto import (
    Module,
    TestBench as HDLTestBench,
    testcase as hdl_testcase,
    Simulator,
    SimConfig,
    Wire,
    Reg,
    Input,
    Output,
    always_ff,
    always_comb,
)
from hdlproto.error import SignalUnstableError


def build_simulator(tb_cls, config: SimConfig | None = None):
    sim_config = config or SimConfig()
    tb = tb_cls()
    return Simulator(sim_config, tb)


class Counter(Module):
    def __init__(self, enable, count_out):
        self.enable = Input(enable)
        self.count_out = Output(count_out)
        self.count = Reg(init=0, width=4)
        super().__init__()

    @always_ff
    def seq(self, reset):
        if reset:
            self.count.r = 0
        elif self.enable.w:
            self.count.r = (self.count.r + 1) % 16

    @always_comb
    def comb(self):
        self.count_out.w = self.count.r


class TbCounter(HDLTestBench):
    def __init__(self):
        self.enable = Wire(init=1)
        self.count_out = Wire(init=0, width=4)
        self.counter = Counter(self.enable, self.count_out)
        self.samples = []
        super().__init__()

    @hdl_testcase
    def run(self, simulator):
        for cycle in range(6):
            if cycle == 3:
                self.enable.w = 0
            simulator.clock()
            self.samples.append(self.count_out.w)


def test_counter_simulation_runs_and_updates_outputs():
    sim = build_simulator(TbCounter)
    sim.reset()
    sim.testcase("run")
    assert sim.tb.samples == [1, 2, 3, 3, 3, 3]


class PassThrough(Module):
    def __init__(self, in_wire, out_wire):
        self.inp = Input(in_wire)
        self.outp = Output(out_wire)
        self.reg = Reg(init=0, width=8)
        super().__init__()

    @always_ff
    def capture(self, reset):
        if reset:
            self.reg.r = 0
        else:
            self.reg.r = self.inp.w

    @always_comb
    def drive(self):
        self.outp.w = self.reg.r


class TbPassThrough(HDLTestBench):
    def __init__(self):
        self.src = Wire(init=0, width=8)
        self.dst = Wire(init=0, width=8)
        self.dut = PassThrough(self.src, self.dst)
        self.history = []
        super().__init__()

    @hdl_testcase
    def run(self, simulator):
        values = [5, 7, 1]
        for val in values:
            self.src.w = val
            simulator.clock()
            self.history.append(self.dst.w)


def test_pass_through_shows_ff_before_comb():
    sim = build_simulator(TbPassThrough)
    sim.reset()
    sim.testcase("run")
    # 1サイクル遅れて出力に現れる（FF -> COMB の順序を確認）
    assert sim.tb.history == [5, 7, 1]


class DualEdge(Module):
    def __init__(self, reset_wire, pos_wire, neg_wire):
        self.reset = Input(reset_wire)
        self.pos_out = Output(pos_wire)
        self.neg_out = Output(neg_wire)
        self.pos_reg = Reg(init=0, width=4)
        self.neg_reg = Reg(init=0, width=4)
        super().__init__()

    @always_ff(edge='pos')
    def pos_logic(self, reset):
        if self.reset.w:
            self.pos_reg.r = 0
        else:
            self.pos_reg.r = (self.pos_reg.r + 1) % 16

    @always_ff(edge='neg')
    def neg_logic(self, reset):
        if self.reset.w:
            self.neg_reg.r = 0
        else:
            self.neg_reg.r = self.pos_reg.r

    @always_comb
    def drive(self):
        self.pos_out.w = self.pos_reg.r
        self.neg_out.w = self.neg_reg.r


class TbDualEdge(HDLTestBench):
    def __init__(self):
        self.reset = Wire(init=1)
        self.pos_wire = Wire(init=0, width=4)
        self.neg_wire = Wire(init=0, width=4)
        self.dut = DualEdge(self.reset, self.pos_wire, self.neg_wire)
        self.history = []
        super().__init__()

    @hdl_testcase
    def run(self, simulator):
        simulator.clock(edge='pos')
        simulator.clock(edge='neg')
        self.reset.w = 0
        for _ in range(3):
            simulator.clock(edge='pos')
            self.history.append(('pos', self.pos_wire.w))
            simulator.clock(edge='neg')
            self.history.append(('neg', self.neg_wire.w))


def test_dual_edge_flops_advance_on_pos_and_neg_edges():
    sim = build_simulator(TbDualEdge)
    sim.testcase("run")
    assert sim.tb.history == [
        ('pos', 1), ('neg', 1),
        ('pos', 2), ('neg', 2),
        ('pos', 3), ('neg', 3),
    ]


class TbMultipleTestcases(HDLTestBench):
    def __init__(self):
        self.log = []
        super().__init__()

    @hdl_testcase
    def alpha(self, simulator):
        self.log.append("alpha")

    @hdl_testcase
    def beta(self, simulator):
        self.log.append("beta")


def test_specific_testcase_runs_only_selected_function():
    sim = build_simulator(TbMultipleTestcases)
    sim.reset()
    sim.testcase("alpha")
    assert sim.tb.log == ["alpha"]
    sim.tb.log.clear()
    sim.testcase()
    assert sim.tb.log == ["alpha", "beta"]


class UnstableComb(Module):
    def __init__(self):
        self.osc = Wire(init=0)
        super().__init__()

    @always_comb
    def oscillate(self):
        self.osc.w = (~self.osc.w) & 1


class TbUnstable(HDLTestBench):
    def __init__(self):
        self.dut = UnstableComb()
        super().__init__()

    @hdl_testcase
    def run(self, simulator):
        simulator.clock()


def test_signal_unstable_error_is_raised():
    sim = build_simulator(TbUnstable, SimConfig(max_comb_loops=4))
    with pytest.raises(SignalUnstableError):
        sim.reset()
