import pytest
import os
from hdlproto import *


# --- テスト用モジュール定義 (変更なし) ---
class ArrayTestModule(Module):
    def __init__(self, clk):
        super().__init__()
        self.clk = InputWire(clk)
        self.mem = RegArray(4, width=8)
        self.bus = WireArray(2, width=4)

    @always_ff((Edge.POS, 'clk'))
    def logic(self):
        self.mem[0].r = 0x0A
        self.mem[1][7:4] = 0xF
        # ここで mem[0] を読むとき、同じサイクルでの書き込み(0x0A)はまだ反映されていない
        self.mem[2].r = self.mem[0].r + 1

    @always_comb
    def comb_logic(self):
        self.bus[0].w = 0x3
        self.bus[1].w = self.mem[1][7:4]


class TbArray(TestBench):
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.dut = ArrayTestModule(self.clk)


# --- テスト関数 (修正箇所) ---
def test_array_functionality():
    """WireArray, RegArray の動作検証"""
    tb = TbArray()
    vcd_file = "test_array.vcd"
    vcd = VCDWriter()
    sim = Simulator(tb, tb.clk, vcd=vcd)
    vcd.open(vcd_file)

    try:
        # --- 初期状態 ---
        assert tb.dut.mem[0].r == 0

        # --- 1クロック目 ---
        sim.clock()

        # mem[0] は 10 になった
        assert tb.dut.mem[0].r == 0x0A

        # mem[1] も正しく F0 になった
        assert tb.dut.mem[1].r == 0xF0

        # 【重要】mem[2] は、更新前の mem[0](=0) + 1 を計算したので、ここは 1 になるのが正しい
        assert tb.dut.mem[2].r == 1

        # WireArrayの検証
        assert tb.dut.bus[0].w == 3
        assert tb.dut.bus[1].w == 0xF

        # --- 2クロック目 (ここを追加) ---
        sim.clock()

        # ここで初めて mem[0] の値(10) が計算に使われ、mem[2] が 11 になる
        assert tb.dut.mem[2].r == 11

    finally:
        vcd.close()
        if os.path.exists(vcd_file):
            os.remove(vcd_file)


def test_array_init():
    # テスト用のダミーモジュール
    class InitTest(Module):
        def __init__(self):
            super().__init__()
            # 初期値リスト指定
            self.rom = RegArray(4, width=8, init=[0xAA, 0xBB])
            # 単一初期値指定
            self.ram = RegArray(4, width=8, init=0xFF)

    dut = InitTest()

    # 検証: リスト指定
    assert dut.rom[0].r == 0xAA  # 指定あり
    assert dut.rom[1].r == 0xBB  # 指定あり
    assert dut.rom[2].r == 0  # 指定なし(デフォルト0)

    # 検証: 単一指定
    assert dut.ram[0].r == 0xFF
    assert dut.ram[3].r == 0xFF


if __name__ == "__main__":
    test_array_functionality()
    test_array_init()
    print("All tests passed!")