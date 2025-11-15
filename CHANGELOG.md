# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2025-11-15

### Features

- add edge-trigger metadata and clock handling for always_ff
  - require `@always_ff` to specify explicit `(Edge, signal_name)` tuples
    (e.g. migrate from `@always_ff(edge='pos')` to `@always_ff((Edge.POS, "clk"))`)
  - Introduce unified clock input in `SimConfig` for modules and testbenches.
  - Improve `Simulator.clock` with half-cycle clock toggling.
  - Refactor `FunctionManager` and supporting classes for edge-based evaluation.
  - Update examples to align with new clock and reset mechanisms.

### Add

- add dual-edge clock support for @always_ff and update docs
  - allow @always_ff to target posedge or negedge and expose sim.clock(edge=…)
  - register FFs per edge in FunctionManager/Simulator and enforce rules in SignalManager
  - document the new edge support and reset usage in README/Getting Started

### Docs

- update for enhanced `@always_ff` and unified clock/reset handling
  - Update documentation to reflect explicit `(Edge, signal_name)` usage in `@always_ff`.
  - Document the requirement for a unified `clk` input in top-level modules.
  - Revise examples and guides for updated clock/reset simulation in `SimConfig`.

- clarify behavior of @always_ff in example docstring

- Add Getting Started guide

  Create a new "Getting Started" guide for engineers with HDL/Verilog experience.
  This document explains the core concepts of HDLproto by comparing them with Verilog and provides a step-by-step tutorial for designing a simple counter.

  - Create doc/getting_started.md (English)
  - Create doc/getting_started.jp.md (Japanese)
  - Add links to the new guides from README.md and README.ja.md.

### Refactoring & Fixes

- update tests to align with unified clock input and @always_ff enhancements
  - Replace `reset` calls with `clock` for simulation consistency.
  - Migrate `@always_ff` usage to explicit edge targeting `(Edge.POS, "clk")`.
  - Update testbench constructors to include `clk` input where applicable.

- integrate unified clock/reset handling and enhance @always_ff
  - Migrate modules and testbenches to use unified `clk` and `reset` inputs.
  - Update `@always_ff` to accept explicit `(Edge, signal_name)` for edge targeting.
  - Add `Simulator.half_clock` method for half-cycle clock toggling.
  - Revise test cases for compatibility with updated clock/reset mechanisms.

- Remove last_write_value assignment in Signal.set methods

- Prevent setting 'w' property in Input class
