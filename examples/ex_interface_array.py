from hdlproto import *


# --- 1. Interface Definition ---
class ArrayBus(Interface):
    def __init__(self):
        # 1. Define signals first
        self.data = WireArray(4, width=8)  # 4-channel, 8-bit bus

        # 2. Call super init
        super().__init__()

        # 3. Define Modports
        # Master: Outputs data
        # Note: Specifying 'OutputWire' automatically handles the WireArray
        self.master = Modport(self,
                              data=OutputWireArray
                              )

        # Slave: Inputs data
        # Note: Specifying 'InputWire' automatically handles the WireArray
        self.slave = Modport(self,
                             data=InputWireArray
                             )


# --- 2. Master Module ---
class Master(Module):
    def __init__(self, clk, bus: Modport):
        super().__init__()
        self.clk = InputWire(clk)
        self.bus = bus
        self.counter = Reg(width=8)

    # 1. Sequential Logic: Update internal state
    @always_ff((Edge.POS, 'clk'))
    def seq_logic(self):
        self.counter.r = self.counter.r + 1

    # 2. Combinational Logic: Drive output wires
    @always_comb
    def comb_logic(self):
        # Access the port as an array using index
        for i in range(4):
            # Drive OutputWire from the internal Reg
            self.bus.data[i].w = self.counter.r + i


# --- 3. Slave Module ---
class Slave(Module):
    def __init__(self, clk, bus: Modport):
        super().__init__()
        self.clk = InputWire(clk)
        self.bus = bus
        self.sum = Reg(width=10)  # Enough width to hold sum of 4x8bit

    @always_ff((Edge.POS, 'clk'))
    def logic(self):
        # Read from the array port using index
        temp_sum = 0
        for i in range(4):
            temp_sum += self.bus.data[i].w

        self.sum.r = temp_sum


# --- 4. Top & Simulation ---
class TbArrayInterface(TestBench):
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        # Instantiate the Interface
        self.bus = ArrayBus()

        # Instantiate modules and connect Modports
        self.m = Master(self.clk, self.bus.master)
        self.s = Slave(self.clk, self.bus.slave)

    def run(self, sim):
        # Drive the clock wire inside the interface

        for cycle in range(5):
            sim.clock()

            # Inspect values for verification
            d0 = self.bus.data[0].w
            d1 = self.bus.data[1].w
            d2 = self.bus.data[2].w
            d3 = self.bus.data[3].w
            total = self.s.sum.r

            print(f"Cycle={cycle} Data=[{d0}, {d1}, {d2}, {d3}] SlaveSum={total}")


if __name__ == "__main__":
    tb = TbArrayInterface()

    # Pass the raw Wire object from the interface to the simulator
    sim = Simulator(testbench=tb, clock=tb.clk)

    tb.run(sim)