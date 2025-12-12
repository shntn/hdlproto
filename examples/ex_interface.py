from hdlproto import *


# --- 1. Interface定義 ---
class HandshakeBus(Interface):
    def __init__(self):
        self.clk = Wire()
        self.valid = Wire()
        self.ready = Wire()
        self.data = Wire(width=8)
        super().__init__()

        # Master側: valid/dataを出力, readyを入力
        self.master = Modport(self,
                              clk=Input, valid=Output, data=Output, ready=Input
                              )

        # Slave側: valid/dataを入力, readyを出力
        self.slave = Modport(self,
                             clk=Input, valid=Input, data=Input, ready=Output
                             )


# --- 2. Masterモジュール ---
class Master(Module):
    def __init__(self, bus: Modport):
        super().__init__()
        self.bus = bus  # Modportを受け取る
        self.counter = Reg(width=8)

    @always_ff((Edge.POS, 'bus.clk'))  # bus.clk という名前でアクセス可能
    def logic(self):
        # 単純なロジック: Readyならカウントアップして送信
        if self.bus.ready.w:
            self.counter.r = self.counter.r + 1

    @always_comb
    def output_logic(self):
        self.bus.valid.w = 1
        self.bus.data.w = self.counter.r


# --- 3. Slaveモジュール ---
class Slave(Module):
    def __init__(self, bus: Modport):
        super().__init__()
        self.bus = bus
        # 内部状態を持たせて、定期的に Ready をトグルさせる
        self.toggle_reg = Reg(width=1)

    @always_ff((Edge.POS, 'bus.clk'))
    def state_update(self):
        # サイクルごとに 0 -> 1 -> 0 -> ... と変化
        self.toggle_reg.r = ~self.toggle_reg.r

    @always_comb
    def logic(self):
        # 内部状態に応じて Ready を出す
        # これにより「待って(Ready=0)」と「いいよ(Ready=1)」を繰り返す
        self.bus.ready.w = self.toggle_reg.r


# --- 4. Top & Simulation ---
class TbInterface(TestBench):
    def __init__(self):
        super().__init__()
        # Interface実体化
        self.bus = HandshakeBus()

        # 接続 (Modportを渡すだけ！)
        self.m = Master(self.bus.master)
        self.s = Slave(self.bus.slave)

    def run(self, sim):
        # クロック駆動はInterface内のWireを直接指定
        sim.clock_wire = self.bus.clk

        for _ in range(10):
            sim.clock()
            print(f"Time={_} Valid={self.bus.valid.w} Data={self.bus.data.w} Ready={self.bus.ready.w}")


if __name__ == "__main__":
    tb = TbInterface()
    vcd = VCDWriter()
    # シミュレータには Interface内の生Wire (tb.bus.clk) を渡す
    sim = Simulator(testbench=tb, clock=tb.bus.clk, vcd=vcd)

    vcd.open("interface.vcd")
    tb.run(sim)
    vcd.close()
    print("Simulation finished. Check interface.vcd")