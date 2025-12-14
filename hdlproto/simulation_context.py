from enum import Enum, auto
from typing import Callable
from .signal import Wire, Reg, OutputWire
from .error import SignalInvalidAccess, SignalWriteConflict


class _Phase(Enum):
    """Internal enum to track the current simulation execution phase."""
    ALWAYS_COMB = auto()
    ALWAYS_FF = auto()


class _SimulationContext:
    """Tracks active processes, phases, and write constraints during simulation.

    This internal class acts as a state machine for the simulator. It is
    passed to all simulation objects and provides context about the current
    state of execution. Its primary responsibilities are:

    1. Tracking the currently executing process (`@always_comb` or `@always_ff`).
    2. Enforcing HDL rules, such as preventing writes to a `Reg` from within
       an `@always_comb` block.
    3. Detecting multiple drivers for the same `Wire` within a simulation step.

    Attributes
    ----------
    _current_function : callable or None
        The `always` block function that is currently executing.
    _current_phase : _Phase or None
        The phase (`ALWAYS_COMB` or `ALWAYS_FF`) of the current function.
    _write_log : dict
        A log to track which functions have written to which signals in the
        current step, used to detect multiple drivers.
    _delta_cycle : bool
        A flag indicating if the simulator is currently in a delta cycle.
    """

    def __init__(self):
        self._current_function = None
        self._current_phase = None
        self._write_log = {}
        self._delta_cycle = False

    def _enter_always_ff(self, func: Callable) -> None:
        """Mark entry into an @always_ff block.

        Parameters
        ----------
        func : callable
            The `@always_ff` process function that is starting.
        """
        self._current_function = func
        self._current_phase = _Phase.ALWAYS_FF

    def _enter_always_comb(self, func: Callable) -> None:
        """Mark entry into an @always_comb block.

        Parameters
        ----------
        func : callable
            The `@always_comb` process function that is starting.
        """
        self._current_function = func
        self._current_phase = _Phase.ALWAYS_COMB

    def _exit(self):
        """Mark exit from the current `always` block."""
        self._current_function = None
        self._current_phase = None

    def _enter_delta_cycle(self) -> None:
        """Signal that the simulator has entered a delta-cycle execution window."""
        self._delta_cycle = True

    def _exit_delta_cycle(self) -> None:
        """Signal that the simulator has left the delta-cycle window."""
        self._delta_cycle = False

    def _record_write(self, signal: (Wire | Reg | OutputWire)) -> None:
        """Record and validate a write operation to a signal.

        This method is called by a signal whenever it is written to. It
        checks if the write is legal based on the current simulation phase
        and logs the write to detect multiple drivers.

        Parameters
        ----------
        signal : Wire or Reg or OutputWire
            The signal being written to.

        Raises
        ------
        RuntimeError
            If a write occurs outside of any `always` block context.
        SignalInvalidAccess
            If a `Reg` is written from an `@always_comb` block, or a `Wire`
            is written from an `@always_ff` block.
        SignalWriteConflict
            If multiple distinct processes attempt to write to the same `Wire`
            in the same simulation step.
        """
        func = self._current_function

        if self._delta_cycle and func is None:
            # This should be prevented by the simulator's structure
            raise RuntimeError("Signal write occurred outside of an active always block.")

        if signal._is_reg and self._current_phase == _Phase.ALWAYS_COMB:
            raise SignalInvalidAccess("Cannot write to a Reg from an @always_comb block.")
        if not signal._is_reg and self._current_phase == _Phase.ALWAYS_FF:
            raise SignalInvalidAccess("Cannot write to a Wire from an @always_ff block.")

        funcs = self._write_log.setdefault(signal, set())
        if func in funcs:
            return  # The same function writing to the same signal multiple times is fine
        funcs.add(func)
        if len(funcs) > 1:
            # Format a helpful error message
            driver_names = [f"{item._module._name}.{item._name}" for item in funcs]
            raise SignalWriteConflict(
                f"Multiple drivers for signal '{signal._get_name()}': {', '.join(driver_names)}"
            )

    def _clear(self) -> None:
        """Reset the write log between user-visible half clock steps."""
        self._write_log.clear()
