from hdlproto import *


# --- 1. Interface definition ---
# The Interface collects related signals (Wire objects) into a single
# reusable bundle. Use an Interface when multiple modules need to share
# a group of signals with well-defined directions.
#
# Steps to define an Interface:
#  1) Create Wire fields (signals) as attributes on the Interface class.
#  2) Call `super().__init__()` to let the framework register the signals.
#  3) Define one or more Modport views that map each signal name to a
#     directional Wire type (InputWire/OutputWire). A Modport is a
#     lightweight "view" of the interface used by a module.
#
# Why Modports:
#  - A Modport specifies which side drives a signal and which side reads it.
#  - Pass a Modport instance (not the raw Interface) to modules so the
#    module's code is checked and intentions are clear.
#  - Example: `self.master = Modport(self, valid=OutputWire, ready=InputWire)`
#    means the master will drive `valid` and observe `ready`.
class HandshakeBus(Interface):
    def __init__(self):
        self.valid = Wire()
        self.ready = Wire()
        self.data = Wire(width=8)
        super().__init__()

        # Master side: outputs valid/data, inputs ready
        # The Modport maps names to directional Wire classes. Modules that
        # receive `self.master` should write to `bus.valid.w` / `bus.data.w`
        # and read `bus.ready.w`.
        self.master = Modport(self,
                              valid=OutputWire, data=OutputWire, ready=InputWire
                              )

        # Slave side: inputs valid/data, outputs ready
        # The slave receives `self.slave` and will read `valid`/`data` and
        # drive `ready`.
        self.slave = Modport(self,
                             valid=InputWire, data=InputWire, ready=OutputWire
                             )


# --- 2. Master module ---
class Master(Module):
    def __init__(self, clk, bus: Modport):
        super().__init__()
        self.clk = InputWire(clk)
        self.bus = bus  # Accept a Modport
        self.counter = Reg(width=8)

    @always_ff((Edge.POS, 'clk'))
    def logic(self):
        # Simple logic: increment counter and send when ready
        if self.bus.ready.w:
            self.counter.r = self.counter.r + 1

    @always_comb
    def output_logic(self):
        self.bus.valid.w = 1
        self.bus.data.w = self.counter.r


# --- 3. Slave module ---
class Slave(Module):
    def __init__(self, clk, bus: Modport):
        super().__init__()
        self.clk = InputWire(clk)
        self.bus = bus
        # Keep internal state to periodically toggle Ready
        self.toggle_reg = Reg(width=1)

    @always_ff((Edge.POS, 'clk'))
    def state_update(self):
        # Toggle 0 -> 1 -> 0 -> ... each cycle
        self.toggle_reg.r = ~self.toggle_reg.r

    @always_comb
    def logic(self):
        # Drive Ready according to internal state
        # This alternates between wait (Ready=0) and go (Ready=1)
        self.bus.ready.w = self.toggle_reg.r


# --- 4. Top & Simulation ---
class TbInterface(TestBench):
    def __init__(self):
        super().__init__()
        self.clk = Wire()
        # Instantiate the interface
        self.bus = HandshakeBus()

        # Connections (just pass Modport!)
        # Important: pass the Modport view (`self.bus.master` / `self.bus.slave`)
        # to modules rather than the raw Interface object. The Modport enforces
        # directionality and documents what each module may drive or observe.
        self.m = Master(self.clk, self.bus.master)
        self.s = Slave(self.clk, self.bus.slave)

    def run(self, simulator):
        for _ in range(10):
            simulator.clock()
            print(f"Time={_} Valid={self.bus.valid.w} Data={self.bus.data.w} Ready={self.bus.ready.w}")


if __name__ == "__main__":
    tb = TbInterface()
    vcd = VCDWriter()
    sim = Simulator(testbench=tb, clock=tb.clk, vcd=vcd)

    vcd.open("interface.vcd")
    tb.run(sim)
    vcd.close()
    print("Simulation finished. Check interface.vcd")