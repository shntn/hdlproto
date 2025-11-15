# HDLproto

HDLproto is a lightweight, pre-RTL simulator that runs on pure Python.
With zero external dependencies, it lets you quickly validate signal timing
and control logic during the early design stages (from spec to architecture).

* Intuitive API: express HDL design rules directly using `@always_ff` / `@always_comb` and `.r` / `.w`
* Event-driven safety: detect rule violations, multiple drivers, and non-convergent combinational logic via exceptions
* Easy to adopt: runs with Python only — great for learning, teaching, and rapid prototyping

## Installation

### Installation from PyPI

```bash
pip install hdlproto
```

### Install development version

```bash
git clone https://github.com/shntn/hdlproto.git
cd hdlproto
pip install -e .
```

### Run without installation

```bash
git clone https://github.com/shntn/hdlproto.git
cd hdlproto
PYTHONPATH=. python3 example/ex_sap1.py
```

### Requirements

- Python 3.10 or higher

## Documentation

For more detailed usage of HDLproto, especially for those with Verilog experience, please see this [Getting Started Guide](doc/getting_started.md).

## Quick Start (Minimal Example)

Save the following as `quickstart.py` and run it.

```python
from hdlproto import *

class Counter(Module):
    def __init__(self, clk, reset, en, out):
        self.clk = Input(clk)
        self.reset = Input(reset)
        self.en = Input(en)
        self.out = Output(out)
        self.cnt = Reg(init=0, width=4)
        self.cnt_next = Wire(init=0, width=4)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def seq(self):
        if self.reset.w:
            self.cnt.r = 0
        elif self.en.w:
            self.cnt.r = self.cnt_next.w

    @always_comb
    def comb(self):
        self.cnt_next.w = (self.cnt.r + 1) % 16
        self.out.w = self.cnt.r

class TbCounter(TestBench):
    def __init__(self):
        self.clk = Wire()
        self.reset = Wire()
        self.en = Wire(init=1)
        self.out = Wire(init=0, width=4)
        self.dut = Counter(self.clk, self.reset, self.en, self.out)
        super().__init__()

    @testcase
    def run(self, simulator):
        self.reset.w = 1
        simulator.clock()
        self.reset.w = 0
        for i in range(6):
            if i == 3:  # Stop counting
                self.en.w = 0
            simulator.clock()
            print(f"cycle={i}, out={self.out.w}")

if __name__ == "__main__":
    tb = TbCounter()
    config = SimConfig(clock=tb.clk)
    sim = Simulator(config, tb)
    sim.testcase("run")

# Output:
# cycle=0, out=1
# cycle=1, out=2
# cycle=2, out=3
# cycle=3, out=3
# cycle=4, out=3
# cycle=5, out=3
```

**How it works:**
- Within one clock cycle, `@always_ff` (register updates) and `@always_comb` (wire updates) are evaluated.
- When `i==3`, setting `en` to 0 stops the counter.
- `Simulator.clock()` advances one clock cycle. You can select an edge with `Simulator.half_clock(1)` or `Simulator.half_clock(0)`.

## Design Rules (Important)

- `@always_ff((Edge.POS, 'clk'), ...)`: Only non-blocking assignments to `Reg` (writes via `.r`) are valid. Describes sequential logic sensitive to specified signal edges.
- `@always_comb`: Only writes to `Wire`/`Output` (via `.w`) are valid. Writing to `Reg` will raise an exception.
- `Simulator.clock()` drives the clock signal specified in `SimConfig`. The clock signal must be received as an `Input` in the top module and defined as a `Wire` in the `TestBench`.
- Reset is treated as an input signal. Asynchronous reset is implemented by adding the reset signal to the `@always_ff` trigger list (e.g., `@always_ff((Edge.POS, 'clk'), (Edge.POS, 'reset'))`). Synchronous reset is described by writing the reset condition inside an `always_ff` block that only triggers on the clock edge.
- Convergence loop: `@always_comb` is re-evaluated until signals stabilize. Non-convergence raises an exception.

## Changes to @always_ff

The `@always_ff` decorator has been updated to allow for more flexible trigger specifications.

```python
class MyModule(Module):
    def __init__(self, clk, reset_n):
        self.clk = Input(clk)
        self.reset_n = Input(reset_n) # Active-low reset
        self.count = Reg(init=0, width=4)
        super().__init__()

    # Trigger on the rising edge of clk and the falling edge of reset_n
    @always_ff((Edge.POS, 'clk'), (Edge.NEG, 'reset_n'))
    def counter(self):
        if not self.reset_n.w: # Reset when reset_n is 0
            self.count.r = 0
        else:
            self.count.r = self.count.r + 1
```

Key changes are as follows:

*   **Trigger Specification Change**: The old `edge='pos'` argument has been deprecated. Triggers are now specified using a list of tuples in the format `(Edge, 'signal_name')`.
*   **Support for Multiple Triggers**: You can now specify multiple signal edges as triggers, such as a clock and an asynchronous reset. `Edge.POS` (rising) and `Edge.NEG` (falling) can be freely combined.
*   **Signal Name as String**: The trigger signal is specified by its attribute name defined within the module as a string (e.g., `'clk'`, `'reset_n'`).

## Main Exceptions

- `SignalInvalidAccess`: Phase violation write (e.g., writing to `Reg` in a COMB block or `Wire` in an FF block).
- `SignalWriteConflict`: The same signal is driven by multiple `always_*` blocks.
- `SignalUnstableError`: Combinational logic does not stabilize within the specified number of iterations (potential loop or feedback).

## Included Samples

- `example/ex_module.py`: A slightly richer introductory example.
- `example/ex_sap1.py`: A SAP-1 implementation, ideal for pre-RTL exercises.
- `example/ex_exception.py`: Scripts to reproduce exceptions (rule violations, conflicts).

## License

- License: MIT License