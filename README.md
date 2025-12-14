# HDLproto

HDLproto is a lightweight, pre-RTL simulator that runs on pure Python.
With zero external dependencies, it lets you quickly validate signal timing
and control logic during the early design stages (from spec to architecture).

* Intuitive API: express HDL design rules directly using `@always_ff` / `@always_comb` and `.r` / `.w`
* Event-driven safety: detect rule violations, multiple drivers, and non-convergent combinational logic via exceptions
* Easy to adopt: runs with Python only — great for learning, teaching, and rapid prototyping

### About HDLproto (Concept and Scope)

HDLproto is a lightweight simulation framework for emulating HDL-style (Verilog/SystemVerilog) descriptions in Python.
It does not aim to strictly replicate HDL syntax but rather to provide a prototyping environment for concisely testing "hardware behavior models" like `always_comb` / `always_ff` and `Wire` / `Reg` within Python.

### Target Goals

HDLproto is designed for the following use cases:

*   Verifying CPU microarchitecture designs
*   Checking the behavior of small-scale digital circuits
*   Prototyping control units and Finite State Machines (FSMs)
*   Validating ideas and organizing dataflow before full HDL design
*   Understanding the behavior of `always_ff` / `always_comb` for educational purposes

The primary goal is to enable users to easily express and verify "HDL-like behavior" using only Python.

### What HDLproto is NOT (Unsupported Features)

*   **Code generation** to Verilog / VHDL / SystemVerilog
*   **Logic synthesis** for FPGAs / ASICs
*   Timing analysis or logic optimization
*   Implementation of large-scale RTL (thousands of signals)

HDLproto is strictly a **simulation environment for prototyping** and is not a tool for generating synthesizable RTL for FPGAs.

### Key Features

*   Build HDL-style modules and signals using only Python
*   Faithfully simulates the behavior of `always_comb` and `always_ff`
*   The simulator automatically handles `Wire`/`Reg` propagation and stabilization loops
*   Automatically analyzes dependencies between modules and signals to run simulations
*   Capable of simulating small-scale CPUs (like SAP-1 or a Z80 subset)

### Intended Users

*   Those who want to quickly prototype CPUs or digital circuits
*   Those who want to verify dataflow or algorithms before starting HDL design
*   Engineers and students who want to learn the concepts of hardware description languages
*   Those who want to design with a hardware mindset, even without access to Verilog
*   Those who want to experiment with circuits using the flexibility of Python

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


## Design Rules (Important)

- `@always_ff((Edge.POS, 'clk'), ...)`: Only non-blocking assignments to `Reg` (writes via `.r`) are valid. Describes sequential logic sensitive to specified signal edges.
- `@always_comb`: Only writes to `Wire`/`OutputWire` (via `.w`) are valid. Writing to `Reg`/`OutputReg` will raise an exception.
- `Simulator.clock()` drives the clock signal specified in `SimConfig`. The clock signal must be received as an `InputWire` in the top module and defined as a `Wire` in the `TestBench`.
- Reset is treated as an input signal. Asynchronous reset is implemented by adding the reset signal to the `@always_ff` trigger list (e.g., `@always_ff((Edge.POS, 'clk'), (Edge.POS, 'reset'))`). Synchronous reset is described by writing the reset condition inside an `always_ff` block that only triggers on the clock edge.
- Convergence loop: `@always_comb` is re-evaluated until signals stabilize. Non-convergence raises an exception.


## Included Samples

- `example/ex_module.py`: A slightly richer introductory example.
- `example/ex_sap1.py`: A SAP-1 implementation, ideal for pre-RTL exercises.
- `example/ex_exception.py`: Scripts to reproduce exceptions (rule violations, conflicts).

## License

- License: MIT License