from hdlproto import *

class Counter(Module):
    def __init__(self, clk, reset, enable, count_out, flag_out):
        super().__init__()
        self.clk = InputWire(clk)
        self.reset = InputWire(reset)
        self.enable = InputWire(enable)
        self.count_out = OutputWire(count_out)
        self.flag_out = OutputWire(flag_out)
        self.count = Reg(width=4)
        self.threshold = Wire(width=4)

    @always_ff((Edge.POS, 'clk'), (Edge.POS, 'reset'))
    def count_logic(self):
        if self.reset.w:
            self.count.r = 0
        else:
            if self.enable.w:
                self.count.r = (self.count.r + 1)

    @always_comb
    def output_logic(self):
        self.threshold.w = 4
        self.flag_out.w = int(self.count.r > self.threshold.w)
        self.count_out.w = self.count.r


class TbCounter(TestBench):
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.reset = Wire()
        self.enable = Wire()
        self.count_out = Wire()
        self.flag_out = Wire()
        self.counter = Counter(self.clk, self.reset, self.enable, self.count_out, self.flag_out)

    def tb_counter(self, simulator):
        self.reset.w = 1
        simulator.clock()
        self.reset.w = 0
        for i in range(12):
            self.enable.w = 0 if 6 <= i + 1 <= 7 else 1
            simulator.clock()
            print(
                f"{i:>3} | reset={self.reset.w} | en={self.enable.w} | cnt_out={self.count_out.w:>2} | flg_out={self.flag_out.w} | th={self.counter.threshold.w} | cnt={self.counter.count.r:>2}"
            )


if __name__ == "__main__":
    tb = TbCounter()
    vcd = VCDWriter()
    sim = Simulator(testbench=tb, clock=tb.clk, vcd=vcd)
    vcd.open("counter.vcd")
    tb.tb_counter(sim)
    vcd.close()

# Example console output (truncated):
# >>> === tb_counter Testcase Start ===
# >>>   0 | en=1 | cnt_out= 0 | flg_out=0 | th=0 | cnt= 0 
# >>>   1 | en=1 | cnt_out= 0 | flg_out=0 | th=4 | cnt= 0 
# >>>   2 | en=1 | cnt_out= 1 | flg_out=0 | th=4 | cnt= 1 
# >>>   3 | en=1 | cnt_out= 2 | flg_out=0 | th=4 | cnt= 2 
# >>>   4 | en=1 | cnt_out= 3 | flg_out=0 | th=4 | cnt= 3 
# >>>   5 | en=1 | cnt_out= 4 | flg_out=0 | th=4 | cnt= 4 
# >>>   6 | en=1 | cnt_out= 5 | flg_out=1 | th=4 | cnt= 5 
# >>>   7 | en=0 | cnt_out= 5 | flg_out=1 | th=4 | cnt= 5 
# >>>   8 | en=0 | cnt_out= 5 | flg_out=1 | th=4 | cnt= 5 
# >>>   9 | en=1 | cnt_out= 6 | flg_out=1 | th=4 | cnt= 6 
# >>>  10 | en=1 | cnt_out= 7 | flg_out=1 | th=4 | cnt= 7 
# >>>  11 | en=1 | cnt_out= 8 | flg_out=1 | th=4 | cnt= 8 
# >>>  12 | en=1 | cnt_out= 9 | flg_out=1 | th=4 | cnt= 9 
# >>> === tb_counter Testcase End ===
# >>> === Simulation End ===