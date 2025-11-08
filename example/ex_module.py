"""Getting started example: a simple 4-bit counter.

This sample shows how to use HDLproto to:
- Declare top-level ports with `Wire` and wrap them with `Input`/`Output` inside a `Module`
- Define an internal `Reg` (register) with an initial value and bit width
- Describe sequential logic using the `@always_ff` decorator
- Describe combinational logic using the `@always_comb` decorator

Notes about HDLproto semantics used below:
- In `@always_ff` (sequential) blocks, you may write to `Reg` (via `.r`). Writing to `Wire`/`Input`/`Output` here is invalid.
- In `@always_comb` (combinational) blocks, you may write to `Wire`/`Output` (via `.w`). Writing to `Reg` here is invalid.
- `.w` and `.r` return the current stable value (not the pending value within the same iteration).
- Updates are applied in phases: `@always_ff` updates regs, then `@always_comb` drives wires/outputs until signals stabilize.
"""

from hdlproto import *

class Counter(Module):
    """
    A simple 4-bit counter module that increments when enabled.

    This class demonstrates how to create a `Module` in HDLproto and how to:
    - Wrap top-level `Wire` objects with `Input`/`Output` to form ports
    - Declare an internal `Reg` with width and initial value
    - Write sequential logic in an `@always_ff` method (use `.r` to read/write regs)
    - Write combinational logic in an `@always_comb` method (use `.w` to drive wires/outputs)

    Access rules (enforced by the simulator):
    - In `@always_ff`, writing to `Reg` is allowed; writing to `Wire`/`Input`/`Output` is invalid.
    - In `@always_comb`, writing to `Wire`/`Output` is allowed; writing to `Reg` is invalid.
    """
    def __init__(self, enable, count_out, flag_out):
        # Define input and output ports by wrapping Wire objects
        self.enable = Input(enable)        # Input port for enable signal
        self.count_out = Output(count_out) # Output port for counter value
        self.flag_out = Output(flag_out)

        # Define internal register with initial value 0 and 4-bit width
        self.count = Reg(init=0, width=4)
        # Local combinational wire. In `@always_comb`, we'll drive this with a constant
        # threshold used to raise a flag once the counter exceeds it.
        self.threshold = Wire(width=4)
        super().__init__()

    @always_ff
    def count_logic(self, reset: bool):
        """
        Sequential logic block - executes on the clock edge.

        This method demonstrates:
        - Reset behavior (synchronous reset)
        - Conditional increment based-on-enable signal
        - Register assignment using .r property
        - Modulo arithmetic for counter-wraparound
        """
        if reset:
            self.count.r = 0  # Reset counter to 0
        else:
            if self.enable.w:  # Check if enable is asserted
                self.count.r = (self.count.r + 1) % 16  # Increment with wraparound

    @always_comb
    def output_logic(self):
        """
        Combinational logic block — reevaluated whenever inputs may cause changes.

        Demonstrates:
        - Driving wires/outputs using the `.w` property (legal only in @always_comb)
        - Reading the current stable register value via `.r`
        - Simple compare against a constant threshold

        The simulator may call this multiple times per cycle until signals stabilize.
        """
        # Drive a constant threshold for this example (combinational value)
        self.threshold.w = 4
        # Raise a flag once the counter exceeds the threshold
        self.flag_out.w = int(self.count.r > self.threshold.w)
        # Expose the internal count on an output port
        self.count_out.w = self.count.r

    def log_clock_start(self, cycle):
        """Optional hook: called once per clock cycle just before sequential logic.
        Useful for tracing internal state during simulation.
        """
        print(f"{cycle:>3} | en={self.enable.w} | cnt_out={self.count_out.w:>2} | flg_out={self.flag_out.w} | th={self.threshold.w} | cnt={self.count.r:>2} ")


class TbCounter(TestBench):
    def __init__(self):
        # Create top-level wires that represent DUT ports in the simulation.
        # These wires are driven/read at the testbench level and wrapped inside
        # the DUT as `Input`/`Output` ports.
        self.enable = Wire(init=1, width=1)      # 1-bit enable signal (driven by TB)
        self.count_out = Wire(init=0, width=4)   # 4-bit counter output (driven by DUT)
        self.flag_out = Wire(init=0, width=1)    # 1-bit flag output (driven by DUT)

        # Instantiate the DUT (Counter) with the created wires.
        self.counter = Counter(self.enable, self.count_out, self.flag_out)
        # Build the module tree (enables automatic discovery of children/signals).
        super().__init__()

    @testcase
    def tb_counter(self, simulator):
        """A testcase entry point.
        The `Simulator` instance is injected by the framework; call `simulator.clock()`
        to advance one cycle, and drive top-level `Wire`s to stimulate the DUT.
        """
        # Run simulation for 12 clock cycles
        for i in range(12):
            # Toggle enable signal: inactive during cycles 7–8 (1-based index)
            self.enable.w = 0 if 6 <= i + 1 <= 7 else 1

            # Advance simulation by one clock cycle
            simulator.clock()

    def log_sim_start(self, config):
        print("=== Simulation Start ===")
        print("  configuration:")
        for name, value in config.items():
            print(f"    {name}: {value}")

    def log_testcase_start(self, name):
        print(f"=== {name} Testcase Start ===")

    def log_testcase_end(self, name):
        print(f"=== {name} Testcase End ===")

    def log_sim_end(self):
        print("=== Simulation End ===")

if __name__ == "__main__":
    # Create simulation configuration
    config = SimConfig()

    tb = TbCounter()

    # Instantiate the simulator
    sim = Simulator(config, tb)
    sim.reset()     # Apply reset signal to initialize internal registers
    sim.testcase('tb_counter')
    sim.end()

# Example console output (truncated):
# >>> === tb_counter Testcase Start ===
# >>>   0 | en=1 | cnt_out= 0 | flg_out=0 | th=4 | cnt= 0
# >>>   1 | en=1 | cnt_out= 1 | flg_out=0 | th=4 | cnt= 1
# >>>   2 | en=1 | cnt_out= 2 | flg_out=0 | th=4 | cnt= 2
# >>>   3 | en=1 | cnt_out= 3 | flg_out=0 | th=4 | cnt= 3
# >>>   4 | en=1 | cnt_out= 4 | flg_out=0 | th=4 | cnt= 4
# >>>   5 | en=0 | cnt_out= 5 | flg_out=1 | th=4 | cnt= 5
# >>>   6 | en=0 | cnt_out= 5 | flg_out=1 | th=4 | cnt= 5
# >>>   7 | en=1 | cnt_out= 5 | flg_out=1 | th=4 | cnt= 5
# >>>   8 | en=1 | cnt_out= 6 | flg_out=1 | th=4 | cnt= 6
# >>>   9 | en=1 | cnt_out= 7 | flg_out=1 | th=4 | cnt= 7
# >>>  10 | en=1 | cnt_out= 8 | flg_out=1 | th=4 | cnt= 8
# >>>  11 | en=1 | cnt_out= 9 | flg_out=1 | th=4 | cnt= 9
# >>> === tb_counter Testcase End ===
# >>> === Simulation End ===