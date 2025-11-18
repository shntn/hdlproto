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
    Edge,
)
from hdlproto.error import SignalUnstableError


def build_simulator(tb_cls, config: SimConfig | None = None):
    tb = tb_cls()
    sim_config = config or SimConfig(clock=None)
    sim_config.clock=tb.clk
    return Simulator(sim_config, tb)


class Counter(Module):
    def __init__(self, clk, reset, enable, count_out):
        self.clk = Input(clk)
        self.reset = Input(reset)
        self.enable = Input(enable)
        self.count_out = Output(count_out)
        self.count = Reg(init=0, width=4)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def seq(self):
        if self.reset.w:
            self.count.r = 0
        elif self.enable.w:
            self.count.r = (self.count.r + 1) % 16

    @always_comb
    def comb(self):
        self.count_out.w = self.count.r


class TbCounter(HDLTestBench):
    def __init__(self):
        self.clk = Wire()
        self.reset = Wire(init=1)
        self.enable = Wire(init=1)
        self.count_out = Wire(init=0, width=4)
        self.counter = Counter(self.clk, self.reset, self.enable, self.count_out)
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
    sim.clock()
    sim._tb.reset.w = 0
    sim.testcase("run")
    assert sim._tb.samples == [1, 2, 3, 3, 3, 3]


class PassThrough(Module):
    def __init__(self, clk, reset, in_wire, out_wire):
        self.clk = Input(clk)
        self.reset = Input(reset)
        self.inp = Input(in_wire)
        self.outp = Output(out_wire)
        self.reg = Reg(init=0, width=8)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def capture(self):
        if self.reset.w:
            self.reg.r = 0
        else:
            self.reg.r = self.inp.w

    @always_comb
    def drive(self):
        self.outp.w = self.reg.r


class TbPassThrough(HDLTestBench):
    def __init__(self):
        self.clk = Wire()
        self.reset = Wire(init=1)
        self.src = Wire(init=0, width=8)
        self.dst = Wire(init=0, width=8)
        self.dut = PassThrough(self.clk, self.reset, self.src, self.dst)
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
    sim.clock()
    sim._tb.reset.w = 0
    sim.testcase("run")
    # 1サイクル遅れて出力に現れる（FF -> COMB の順序を確認）
    assert sim._tb.history == [5, 7, 1]


class DualEdge(Module):
    def __init__(self, clk, reset_wire, pos_wire, neg_wire):
        self.clk = Input(clk)
        self.reset = Input(reset_wire)
        self.pos_out = Output(pos_wire)
        self.neg_out = Output(neg_wire)
        self.pos_reg = Reg(init=0, width=4)
        self.neg_reg = Reg(init=0, width=4)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def pos_logic(self):
        if self.reset.w:
            self.pos_reg.r = 0
        else:
            self.pos_reg.r = (self.pos_reg.r + 1) % 16

    @always_ff((Edge.NEG, 'clk'))
    def neg_logic(self):
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
        self.clk = Wire()
        self.reset = Wire(init=1)
        self.pos_wire = Wire(init=0, width=4)
        self.neg_wire = Wire(init=0, width=4)
        self.dut = DualEdge(self.clk, self.reset, self.pos_wire, self.neg_wire)
        self.history = []
        super().__init__()

    @hdl_testcase
    def run(self, simulator):
        simulator.clock()
        self.reset.w = 0
        for _ in range(3):
            simulator.half_clock()
            self.history.append(('pos', self.pos_wire.w))
            simulator.half_clock()
            self.history.append(('neg', self.neg_wire.w))


def test_dual_edge_flops_advance_on_pos_and_neg_edges():
    sim = build_simulator(TbDualEdge)
    sim.testcase("run")
    assert sim._tb.history == [
        ('pos', 1), ('neg', 1),
        ('pos', 2), ('neg', 2),
        ('pos', 3), ('neg', 3),
    ]


class TbMultipleTestcases(HDLTestBench):
    def __init__(self):
        self.clk = Wire()
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
    sim.testcase("alpha")
    assert sim._tb.log == ["alpha"]
    sim._tb.log.clear()
    sim.testcase()
    assert sim._tb.log == ["alpha", "beta"]


class UnstableComb(Module):
    def __init__(self, clk):
        self.clk = Input(clk)
        self.osc = Wire(init=0)
        super().__init__()

    @always_comb
    def oscillate(self):
        self.osc.w = (~self.osc.w) & 1


class TbUnstable(HDLTestBench):
    def __init__(self):
        self.clk = Wire()
        self.dut = UnstableComb(self.clk)
        super().__init__()

    @hdl_testcase
    def run(self, simulator):
        simulator.clock()


def test_signal_unstable_error_is_raised():
    config = SimConfig(clock=None, max_comb_loops=4)
    sim = build_simulator(TbUnstable, config)
    with pytest.raises(SignalUnstableError):
        sim.clock()
