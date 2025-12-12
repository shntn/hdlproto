from typing import Callable

from .signal import Wire, Reg
from .simulation_context import _SimulationContext


class _SignalList:
    """Container tracking all wires and registers participating in simulation.

    This is an internal helper class for the simulator.

    Attributes
    ----------
    _wires : list of Wire
        A list of all `Wire` objects in the design.
    _regs : list of Reg
        A list of all `Reg` objects in the design.
    """

    def __init__(self):
        self._wires = []
        self._regs = []

    def _append_wire(self, wire: Wire):
        """Register a wire-like signal for later iteration.

        Parameters
        ----------
        wire : Wire
            The wire to add to the list.
        """
        self._wires.append(wire)

    def _append_reg(self, reg: Reg):
        """Register a register signal for later iteration.

        Parameters
        ----------
        reg : Reg
            The register to add to the list.
        """
        self._regs.append(reg)

    def _exec_wires(self, func: Callable) -> bool:
        """Apply a function to each wire.

        Parameters
        ----------
        func : Callable
            A function that takes a `Wire` as input.

        Returns
        -------
        bool
            True if `func` returned a truthy value for any wire.
        """
        result = False
        for wire in self._wires:
            r = func(wire)
            result |= bool(r)
        return result

    def _exec_regs(self, func: Callable) -> bool:
        """Apply a function to each register.

        Parameters
        ----------
        func : Callable
            A function that takes a `Reg` as input.

        Returns
        -------
        bool
            True if `func` returned a truthy value for any register.
        """
        result = False
        for reg in self._regs:
            r = func(reg)
            result |= bool(r)
        return result

    def _exec_all(self, func: Callable) -> bool:
        """Apply a function to every signal.

        Parameters
        ----------
        func : Callable
            A function that takes a `_Signal` as input.

        Returns
        -------
        bool
            True if `func` returned a truthy value for any signal.
        """
        result = False
        for sig in self._wires + self._regs:
            r = func(sig)
            result |= bool(r)
        return result


class _FunctionList:
    """Container for all @always_comb and @always_ff functions in the design.

    This is an internal helper class for the simulator.

    Attributes
    ----------
    _always_comb : list of callable
        A list of all `@always_comb` decorated functions.
    _always_ff : list of callable
        A list of all `@always_ff` decorated functions (BoundAlwaysFF objects).
    _sim_context : _SimulationContext
        A reference to the simulation context.
    """

    def __init__(self, sim_context: _SimulationContext):
        self._always_comb = []
        self._always_ff = []
        self._sim_context = sim_context

    def _append_always_comb(self, func: Callable):
        """Register a combinational function.

        Parameters
        ----------
        func : callable
            The `@always_comb` function to add.
        """
        self._always_comb.append(func)

    def _append_always_ff(self, func: Callable):
        """Register a sequential function.

        Parameters
        ----------
        func : callable
            The `BoundAlwaysFF` object to add.
        """
        self._always_ff.append(func)

    def _exec_always_comb(self, func: Callable):
        """Execute a function for each registered @always_comb process.

        This wraps the execution with context tracking to monitor which
        signals are being read or written.

        Parameters
        ----------
        func : Callable
            A function that takes the `@always_comb` callable as input.
        """
        for always_comb in self._always_comb:
            self._sim_context._enter_always_comb(always_comb)
            func(always_comb)
            self._sim_context._exit()

    def _exec_always_ff(self, func: Callable):
        """Execute a function for each registered @always_ff process.

        This wraps the execution with context tracking.

        Parameters
        ----------
        func : Callable
            A function that takes the `BoundAlwaysFF` object as input.
        """
        for always_ff in self._always_ff:
            self._sim_context._enter_always_ff(always_ff)
            func(always_ff)
            self._sim_context._exit()

    def _list_always_ff(self):
        """Yield every registered always_ff block."""
        for always_ff in self._always_ff:
            yield always_ff


class _ActiveRegion:
    """Implements the event-driven active region of the simulation cycle.

    In HDL simulation, the active region is where `always` blocks are
    evaluated. This class orchestrates that evaluation, first settling the
    combinational logic (`@always_comb`) and then evaluating the sequential
    blocks (`@always_ff`).

    Parameters
    ----------
    sim_context : _SimulationContext
        The global simulation context.
    signal_list : _SignalList
        The container for all signals in the design.
    function_list : _FunctionList
        The container for all processes in the design.
    """



    def __init__(
            self,
            sim_context: _SimulationContext,
            signal_list: _SignalList,
            function_list: _FunctionList
    ):
        self._sim_context = sim_context
        self._signal_list = signal_list
        self._function_list = function_list

    def _execute(self):
        """Run one pass of the active region.

        This involves first evaluating `@always_comb` blocks until they stabilize,
        then evaluating triggered `@always_ff` blocks once.
        """
        self._evaluate_always_comb()
        self._evaluate_always_ff()

    def _evaluate_always_comb(self):
        """Propagate combinational logic until it stabilizes.

        This method repeatedly executes all `@always_comb` blocks until no
        `Wire` values change in a pass. This is known as reaching a fixed
        point or quiescence. This loop models the near-instantaneous
        propagation of signals through combinational logic.
        """
        while True:
            self._signal_list._exec_wires(lambda sig: sig._snapshot_epsilon())
            self._sim_context._enter_delta_cycle()
            self._function_list._exec_always_comb(lambda func: func())
            self._sim_context._exit_delta_cycle()
            self._signal_list._exec_wires(lambda sig: sig._commit())
            is_changed = self._signal_list._exec_wires(lambda sig: sig._is_epsilon_changed())
            if not is_changed:
                break

    def _evaluate_always_ff(self):
        """Execute triggered sequential blocks once.

        This method iterates through all `@always_ff` blocks and executes
        only those whose trigger conditions (e.g., a positive clock edge)
        have been met in the current simulation cycle.
        """
        self._sim_context._enter_delta_cycle()
        self._function_list._exec_always_ff(
            lambda func: func() if func._trigger._is_triggered() else None
        )
        self._sim_context._exit_delta_cycle()


class _NBARegion:
    """Implements the Non-Blocking Assignment (NBA) region of the simulation.

    In Verilog/VHDL, non-blocking assignments (`<=`) are evaluated during the
    active region, but the results are only made visible at a later stage.
    This class simulates that behavior by committing the pending values of
    all `Reg` signals after the active region has completed for a delta cycle.

    Parameters
    ----------
    sim_context : _SimulationContext
        The global simulation context.
    signal_list : _SignalList
        The container for all signals in the design.
    """

    def __init__(
            self,
            sim_context: _SimulationContext,
            signal_list: _SignalList,
    ):
        self._sim_context = sim_context
        self._signal_list = signal_list

    def _execute(self):
        """Commit pending register values.

        This applies the values staged by non-blocking assignments in `@always_ff`
        blocks during the active region.
        """
        self._signal_list._exec_regs(lambda reg: reg._commit())