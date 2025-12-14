from hdlproto import *


class SimpleCounter(Module):
    """Reg Output Demo: A counter that outputs internal state directly."""

    def __init__(self, clk, count):
        super().__init__()
        self.clk = InputWire(clk)
        self.count = OutputReg(count)

    @always_ff((Edge.POS, "clk"))
    def logic(self):
        # Write to Output(Reg) MUST use '.r'
        # Reading can be done via '.r' or '.w', but '.r' is more natural for register operations
        self.count.r = self.count.r + 1


# --- For verification ---
class Bench(TestBench):
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.count = Reg(width=8)
        self.dut = SimpleCounter(clk=self.clk, count=self.count)


def run_example():
    bench = Bench()
    vcd = VCDWriter()
    sim = Simulator(testbench=bench, clock=bench.clk, vcd=vcd)
    vcd.open("ex_output_reg.vcd")

    print("--- Output Reg Result ---")
    print(f"Initial: {bench.dut.count.r}")

    sim.clock()
    print(f"Cycle 1: {bench.dut.count.r}")

    sim.clock()
    print(f"Cycle 2: {bench.dut.count.r}")

    sim.clock()
    print(f"Cycle 3: {bench.dut.count.r}")

    vcd.close()

if __name__ == "__main__":
    run_example()