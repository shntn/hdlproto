# HDLproto

HDLproto is a lightweight, pre-RTL simulator that runs on pure Python.
With zero external dependencies, it lets you quickly validate signal timing
and control logic during the early design stages (from spec to architecture).

* Intuitive API: express HDL design rules directly using `@always_ff` / `@always_comb` and `.r` / `.w`
* Event-driven safety: detect rule violations, multiple drivers, and non-convergent combinational logic via exceptions
* Easy to adopt: runs with Python only — great for learning, teaching, and rapid prototyping

## Requirements

- Python 3.10+

## Installation

### From PyPI:

```bash
pip install hdlproto
```

### Development install

```bash
git clone https://github.com/shntn/hdlproto.git
cd hdlproto
pip install -e .
```

Tip (running examples from the repo without installing): PYTHONPATH=. python example/ex_module.py

## Documentation

For a detailed guide on how to use HDLproto, especially for those with Verilog experience, please see our [Getting Started Guide](doc/getting_started.md).

## Quick Start (minimal example)

Save the script below as quickstart.py and run it.

```
from hdlproto import *

class Counter(Module):
    def __init__(self, en, out):
        self.en = Input(en)
        self.out = Output(out)
        self.cnt = Reg(init=0, width=4)
        self.cnt_next = Wire(init=0, width=4)
        super().__init__()

    @always_ff
    def seq(self, reset):
        if reset:
            self.cnt.r = 0
        elif self.en.w:
            self.cnt.r = self.cnt_next.w

    @always_comb
    def comb(self):
        self.cnt_next.w = (self.cnt.r + 1) % 16
        self.out.w = self.cnt.r

class TbCounter(TestBench):
    def __init__(self):
        self.en = Wire(init=1)
        self.out = Wire(init=0, width=4)
        self.dut = Counter(self.en, self.out)
        super().__init__()

    @testcase
    def run(self, simulator):
        for i in range(6):
            if i == 3:  # stop increment mid-way
                self.en.w = 0
            simulator.clock()
            print(f"cycle={i}, out={self.out.w}")

if __name__ == "__main__":
    sim = Simulator(SimConfig(), TbCounter())
    sim.reset()
    sim.testcase("run")
```

What happens:
- Within one clock, the simulator evaluates `@always_ff` (register updates) → `@always_comb` (wire/outputs)
- Dropping `en` to 0 at `i == 3` stops the counter as expected

## Design Rules (important)

- `@always_ff`: only write to Reg via `.r` (writing `Wire`/`Input`/`Output` here is invalid)
- `@always_comb`: only drive `Wire`/`Output` via `.w` (writing `Reg` here is invalid)
- Convergence loop: `@always_comb` re-evaluates until signals stabilize; non-convergence raises an exception

## Key Exceptions

- `SignalInvalidAccess`: phase violation (e.g., writing `Reg` in `always_comb`, writing `Wire` in `always_ff`)
- `SignalWriteConflict`: multiple `always_*` blocks drive the same signal
- `SignalUnstableError`: combinational logic failed to stabilize within the allowed iterations (possible feedback loop)

## Included Examples

- `example/ex_module.py`: a slightly richer starter example
- `example/ex_sap1.py`: a SAP-1 implementation, great for pre-RTL exploration
- `example/ex_exception.py`: small scripts that intentionally raise the main exceptions

## Lisence

This project is licensed under the MIT License, see the LICENSE.txt file for details