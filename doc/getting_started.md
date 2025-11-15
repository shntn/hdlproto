# Getting Started Guide for HDL Engineers

This guide is intended for engineers with HDL (especially Verilog) design experience to learn how to quickly perform "pre-RTL prototyping" using HDLproto.

## 1. Introduction: The HDLproto Concept

**Why Should HDL Engineers Use HDLproto?**

HDLproto is a tool for quickly verifying logic ideas using only Python, before diving into strict RTL design with languages like Verilog/VHDL.

- **Rapid Prototyping**: No complex simulators or toolchains are required. With just a `pip install`, you can start writing and testing hardware logic in your familiar Python environment.
- **Intuitive Debugging**: Use standard Python debuggers (like `pdb`) and `print` statements to easily trace the state of signals mid-cycle.
- **Leverage the Python Ecosystem**: Seamlessly integrate with Python's rich libraries for advanced testing with `pytest`, waveform plotting with `matplotlib`, data processing with `numpy`, and more.
- **Efficient Testbench Construction**: Describe only the Design Under Test (DUT) in HDLproto, while implementing surrounding components like memory models or stimulus generators as regular Python classes or dictionaries. This dramatically streamlines testbench setup compared to writing everything in HDL.

## 2. Conceptual Mapping with Verilog

The table below maps common Verilog features to their HDLproto equivalents.

| Verilog HDL                  | HDLproto                         | Description                                                                                                   |
| :--------------------------- | :------------------------------- | :------------------------------------------------------------------------------------------------------------ |
| `module`                     | `class MyModule(Module):`        | Define a module as a Python class.                                                                            |
| `reg [7:0] data;`            | `self.data = Reg(width=8)`       | A signal that holds its value between clock cycles.                                                           |
| `wire [7:0] data;`           | `self.data = Wire(width=8)`      | A signal used for connections in combinational logic.                                                         |
| `input clk;`                 | `self.clk = Input(clk)`          | A module's input port.                                                                                        |
| `output [3:0] q;`            | `self.q = Output(q)`             | A module's output port.                                                                                       |
| `inout [7:0] data;`          | **Not Supported**                | `inout` ports are not supported.                                                                              |
| `always @(posedge clk)`      | `@always_ff((Edge.POS, 'clk'))`  | A decorator to describe clock-synchronous sequential circuits.                                                |
| `always @(*)`                | `@always_comb`                   | A decorator to describe combinational circuits.                                                               |
| `q <= d;` (Non-blocking)     | `self.q.r = self.d.w`            | **[Sequential]** `.r` represents a signal in a sequential circuit.                                            |
| `q = d;` (Blocking)          | **Not Supported**                | **[Sequential]** Blocking assignments are not supported within `@always_ff`.                                  |
| `y = a & b;` (Blocking)      | `self.y.w = self.a.w & self.b.w` | **[Combinational]** `.w` represents a signal in a combinational circuit.                                      |
| `assign y = a & b;`          | **Not Supported**                | There is no direct equivalent to `assign`. Use `@always_comb` to describe combinational logic.                |
| `initial begin ... end`      | `@testcase`                      | Describes the sequence for a testbench.                                                                       |

## 3. Hands-On: Designing a Counter

Let's look at a simple 4-bit synchronous counter, comparing the HDLproto and Verilog code.

### Step 1: Module Definition

**HDLproto:**

```python
from hdlproto import *

class Counter(Module):
    def __init__(self, clk, rst, en, q_out):
        self.clk = Input(clk)
        self.rst = Input(rst)
        self.en = Input(en)
        self.q_out = Output(q_out)

        self.count = Reg(width=4, init=0)
        self.count_next = Wire(width=4)
        super().__init__()
```

- *Note: HDLproto requires a `clk` port in the top-level module.*
- *Note: Use `@always_ff((Edge.POS, 'clk')` or `@always_ff((Edge.NEG, 'clk'))` to describe rising- and falling-edge logic.*

**Verilog:**

```verilog
module Counter (
    input wire clk,
    input wire rst,
    input wire en,
    output wire [3:0] q_out
);
    reg [3:0] count;
    wire [3:0] count_next;
```

### Step 2: Combinational Logic

**HDLproto:**

```python
    # (Inside Counter class)
    @always_comb
    def comb_logic(self):
        if self.en.w:
            self.count_next.w = self.count.r + 1
        else:
            self.count_next.w = self.count.r
        
        self.q_out.w = self.count.r
```

**Verilog:**

```verilog
    // (Inside Counter module)
    always @(*) begin
        if (en) begin
            count_next = count + 1;
        end else begin
            count_next = count;
        end
        q_out = count;
    end
```

### Step 3: Sequential Logic

**HDLproto:**

```python
    # (Inside Counter class)
    @always_ff((Edge.POS, 'clk'), (Edge.POS, 'rst'))
    def seq_logic(self):
        if self.rst.w:
            self.count.r = 0
        else:
            self.count.r = self.count_next.w
```

- *Note: Use `@always_ff((Edge.POS, 'clk')` or `@always_ff((Edge.NEG, 'clk'))` to describe rising- and falling-edge logic.*
- *Note: The strings `'clk'`, `'rst'` in the `@always_ff` decorator refer to `self.clk`, `self.rst`.*
- *Note: The method decorated with `@always_ff` does not need to take any arguments.*

**Verilog:**

```verilog
    // (Inside Counter module)
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            count <= 4'b0;
        end else begin
            count <= count_next;
        end
    end
```

### Step 4: Testbench and Simulation

This is where HDLproto's major advantage lies.
It shows how intuitively you can write tests in Python compared to a typical Verilog testbench.

**HDLproto:**

```python
class TestCounter(TestBench):
    def __init__(self):
        self.clk = Wire()
        self.rst = Wire(init=0)
        self.en = Wire(init=0)
        self.q_out = Wire(width=4)
        self.dut = Counter(self.clk, self.rst, self.en, self.q_out)
        super().__init__()

    @testcase
    def run(self, sim):
        # Apply reset first
        self.rst.w = 1
        sim.clock()
        self.rst.w = 0

        # Enable and run for 10 cycles
        self.en.w = 1
        for i in range(10):
            print(f"Cycle {i}: q_out = {self.q_out.w}")
            assert self.q_out.w == i
            sim.clock()

if __name__ == "__main__":
    tb = TestCounter()
    config = SimConfig(clock=tb.clk, max_comb_loops=20)
    sim = Simulator(config, tb)
    sim.testcase("run")
```

- *Note: You must specify the clock to be input to the top module with `SimConfig(clock=...)`.*
- *Note: The clock specified in `SimConfig(clock=...)` will have its value updated by the HDLproto simulator class.*
- *Note: `SimConfig(max_comb_loops=...)` sets the upper limit for the combinational logic stabilization loop. If signals do not converge within this count, a `SignalUnstableError` exception is raised.*

**Verilog:**

```verilog
    // A Verilog testbench tends to be more verbose
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    initial begin
        rst = 1; #10;
        rst = 0;
        en = 1;
        repeat (10) @(posedge clk);
        $finish;
    end
```

## 4. Next Steps

Once you understand the basics, try tackling a more complex design.
The file [`example/ex_sap1.py`](../example/ex_sap1.py) contains a complete model of a SAP-1 (Simple-As-Possible) computer implemented using this library.
It serves as a good reference for hierarchical module design.