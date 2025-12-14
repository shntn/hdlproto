from hdlproto import *


class ParallelInverter(Module):
    """Array Port Demo: Inverts 4-byte inputs in parallel."""

    def __init__(self, clk, din, dout):
        super().__init__()
        self.clk = InputWire(clk)

        # Input(WireArray): 8-bit x 4 input bus
        self.din = InputWireArray(din)

        # Output(RegArray): 8-bit x 4 registered output bus
        self.dout = OutputRegArray(dout)

    @always_ff((Edge.POS, "clk"))
    def logic(self):
        # Access array elements using a loop
        for i in range(4):
            # Read Input array (.w), invert, and write to Output array (.r)
            # Use ~ (NOT) operator
            self.dout[i].r = ~self.din[i].w


# --- For verification ---
class Bench(TestBench):
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        self.din = WireArray(4, width=8)
        self.dout = RegArray(4, width=8)

        # Instantiate the DUT (Device Under Test)
        # Array ports can be connected directly (conceptually)
        self.dut = ParallelInverter(self.clk, self.din, self.dout)


def run_example():
    bench = Bench()
    vcd = VCDWriter()
    sim = Simulator(testbench=bench, clock=bench.clk, vcd=vcd)
    vcd.open("ex_array_port.vcd")

    # Input setup: [0x00, 0x01, 0x02, 0x03]
    for i in range(4):
        bench.din[i].w = i

    sim.clock()  # Advance 1 clock cycle

    print("--- Array Port Result ---")
    for i in range(4):
        # 0x00(00000000) -> Invert -> 0xFF(11111111)
        in_val = bench.din[i].w
        out_val = bench.dout[i].r
        print(f"Index {i}: Input=0x{in_val:02X} -> Output=0x{out_val:02X}")

    vcd.close()


if __name__ == "__main__":
    run_example()