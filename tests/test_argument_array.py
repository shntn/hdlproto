import pytest
from hdlproto import Module, InputWire, OutputWire, Wire, Reg, RegArray, always_comb, always_ff, Edge, TestBench, Simulator


# ==============================================================================
# Target Module (修正版)
# ==============================================================================
class Fifo_VarIn(Module):
    """可変幅入力FIFO (Variable Width Input FIFO)"""

    # 【修正1】 データ信号や制御信号も外部から受け取れるように引数を追加
    def __init__(self, parent=None, name=None, width=8, depth_log2=2,
                 clk=None, din=None, push_len=None, pop=None):
        super().__init__()
        if name: self._name = name
        if parent: self._parent = parent

        # Parameters
        self.p_width = width
        self.p_depth = 1 << depth_log2
        self.p_depth_mask = self.p_depth - 1

        # Ports
        if clk is None: raise ValueError("clk signal is required")
        self.clk = InputWire(clk)

        # 外部からWireが渡されたらそれを使い、なければ内部で作る(デフォルト引数対応)
        self.din = InputWire(din if din is not None else Wire(width=width * 2))
        self.push_len = InputWire(push_len if push_len is not None else Wire(width=2))
        self.pop = InputWire(pop if pop is not None else Wire(width=1))

        self.dout = OutputWire(Wire(width=width))
        self.empty = OutputWire(Wire(width=1))
        self.full = OutputWire(Wire(width=1))

        # Internal State
        self.mem = RegArray(self.p_depth, width=width)
        self.wp = Reg(width=depth_log2)
        self.rp = Reg(width=depth_log2)
        self.count = Reg(width=depth_log2 + 1)

        # Internal Wires
        self.is_push = Wire(width=1)
        self.is_pop = Wire(width=1)
        self.push_2bytes = Wire(width=1)
        self.data_byte0 = Wire(width=width)
        self.data_byte1 = Wire(width=width)
        self.next_wp = Wire(width=depth_log2)
        self.next_rp = Wire(width=depth_log2)
        self.next_count = Wire(width=depth_log2 + 1)
        self.read_data_mux = Wire(width=width)

    @always_comb
    def comb_control_logic(self):
        self.is_push.w = 1 if self.push_len.w != 0 else 0
        self.is_pop.w = 1 if (self.pop.w == 1) and (self.count.r > 0) else 0
        self.push_2bytes.w = 1 if self.push_len.w == 2 else 0

        mask = (1 << self.p_width) - 1
        self.data_byte0.w = self.din.w & mask
        self.data_byte1.w = (self.din.w >> self.p_width) & mask

    @always_comb
    def comb_next_state_logic(self):
        if self.is_push.w:
            self.next_wp.w = (self.wp.r + self.push_len.w) & self.p_depth_mask
        else:
            self.next_wp.w = self.wp.r

        if self.is_pop.w:
            self.next_rp.w = (self.rp.r + 1) & self.p_depth_mask
        else:
            self.next_rp.w = self.rp.r

        push_val = self.push_len.w if self.is_push.w else 0
        pop_val = 1 if self.is_pop.w else 0
        self.next_count.w = self.count.r + push_val - pop_val

    @always_comb
    def comb_output_logic(self):
        self.empty.w = 1 if self.count.r == 0 else 0
        self.full.w = 1 if self.count.r == self.p_depth else 0

        mux_out = 0
        current_rp_val = self.rp.r
        for i in range(self.p_depth):
            if i == current_rp_val:
                mux_out = self.mem[i].r

        self.read_data_mux.w = mux_out
        self.dout.w = self.read_data_mux.w

    @always_ff((Edge.POS, "clk"))
    def seq_update(self):
        self.wp.r = self.next_wp.w
        self.rp.r = self.next_rp.w
        self.count.r = self.next_count.w

        if self.is_push.w:
            current_wp_val = self.wp.r
            for i in range(self.p_depth):
                if i == current_wp_val:
                    self.mem[i].r = self.data_byte0.w

            if self.push_2bytes.w:
                next_addr_val = (current_wp_val + 1) & self.p_depth_mask
                for i in range(self.p_depth):
                    if i == next_addr_val:
                        self.mem[i].r = self.data_byte1.w


# ==============================================================================
# Test Fixture & Helpers
# ==============================================================================

class Bench(TestBench):
    def __init__(self):
        super().__init__()
        # 【修正2】 テストベンチ側で入力用のWireを定義します
        self.clk = Wire()
        self.din = Wire(width=16)
        self.push_len = Wire(width=2)
        self.pop = Wire(width=1)

        # それらをDUTに接続します
        self.dut = Fifo_VarIn(self, "dut", width=8, depth_log2=2,
                              clk=self.clk,
                              din=self.din,
                              push_len=self.push_len,
                              pop=self.pop)


@pytest.fixture
def sim_ctx():
    """シミュレータとテストベンチを初期化して返すフィクスチャ"""
    bench = Bench()
    sim = Simulator(bench, bench.clk)
    return bench, sim


def clock_step(sim):
    """1クロック進めるヘルパー"""
    sim.clock()


# ==============================================================================
# Test Cases
# ==============================================================================

def test_initial_state(sim_ctx):
    bench, sim = sim_ctx
    clock_step(sim)

    # Outputポートは読み取れるので dut.empty.w でOK
    assert bench.dut.empty.w == 1
    assert bench.dut.full.w == 0
    assert bench.dut.count.r == 0


def test_push_pop_1byte(sim_ctx):
    bench, sim = sim_ctx
    clock_step(sim)

    # 【修正3】 bench.dut.din ではなく、bench.din (Wire) に書き込む
    # --- Push 0xAA ---
    bench.din.w = 0xAA
    bench.push_len.w = 1
    bench.pop.w = 0
    clock_step(sim)

    # 信号を戻して1クロック
    bench.push_len.w = 0
    clock_step(sim)

    # 状態確認
    assert bench.dut.empty.w == 0
    assert bench.dut.count.r == 1
    assert bench.dut.dout.w == 0xAA

    # --- Pop ---
    bench.pop.w = 1
    clock_step(sim)

    bench.pop.w = 0
    clock_step(sim)

    assert bench.dut.empty.w == 1
    assert bench.dut.count.r == 0


def test_push_2bytes(sim_ctx):
    bench, sim = sim_ctx
    clock_step(sim)

    # --- Push 0xBBAA ---
    bench.din.w = 0xBBAA
    bench.push_len.w = 2
    clock_step(sim)

    bench.push_len.w = 0
    clock_step(sim)

    assert bench.dut.count.r == 2
    assert bench.dut.dout.w == 0xAA

    # --- Pop 1回目 ---
    bench.pop.w = 1
    clock_step(sim)

    # --- Pop 2回目 ---
    assert bench.dut.dout.w == 0xBB
    clock_step(sim)

    bench.pop.w = 0
    clock_step(sim)

    assert bench.dut.empty.w == 1


def test_full_flag(sim_ctx):
    bench, sim = sim_ctx
    clock_step(sim)

    # --- 4バイト書き込む ---
    bench.din.w = 0x2211
    bench.push_len.w = 2
    clock_step(sim)

    bench.din.w = 0x4433
    bench.push_len.w = 2
    clock_step(sim)

    bench.push_len.w = 0
    clock_step(sim)

    assert bench.dut.count.r == 4
    assert bench.dut.full.w == 1
    assert bench.dut.empty.w == 0
    assert bench.dut.dout.w == 0x11


def test_wrap_around(sim_ctx):
    bench, sim = sim_ctx
    clock_step(sim)

    # 1. 2バイト書いて、2バイト読む
    bench.din.w = 0xDEAD
    bench.push_len.w = 2
    clock_step(sim)

    bench.push_len.w = 0
    bench.pop.w = 1
    clock_step(sim)
    clock_step(sim)
    bench.pop.w = 0

    assert bench.dut.count.r == 0

    # 2. 2バイト書く (addr: 2, 3)
    bench.din.w = 0xBBAA
    bench.push_len.w = 2
    clock_step(sim)

    # 3. さらに2バイト書く (addr: 0, 1 -> Wrap)
    bench.din.w = 0xDDCC
    bench.push_len.w = 2
    clock_step(sim)

    bench.push_len.w = 0
    clock_step(sim)

    assert bench.dut.full.w == 1

    # 4. 読み出し確認
    bench.pop.w = 1

    assert bench.dut.dout.w == 0xAA
    clock_step(sim)

    assert bench.dut.dout.w == 0xBB
    clock_step(sim)

    assert bench.dut.dout.w == 0xCC
    clock_step(sim)

    assert bench.dut.dout.w == 0xDD
    clock_step(sim)

    bench.pop.w = 0
    clock_step(sim)

    assert bench.dut.empty.w == 1