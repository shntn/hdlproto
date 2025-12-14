from typing import List

from .region import _SignalList, _FunctionList, _ActiveRegion, _NBARegion
from .signal import Wire, Reg
from .module import TestBench
from .simulation_context import _SimulationContext
from .environment_builder import _EnvironmentBuilder
from .vcdwriter import VCDWriter, _IVCDSignal
from .error import SignalUnstableError


class VCDSignalAdapter(_IVCDSignal):
    """Convert HDLproto signals to the minimal interface required by VCDWriter.

    This adapter class wraps a standard hdlproto signal (`Wire`, `Reg`, etc.)
    and exposes its properties through the `_IVCDSignal` interface, which is
    what the `VCDWriter` expects.

    Parameters
    ----------
    signal : _Signal
        The hdlproto signal to adapt.
    """

    def __init__(self, signal):
        self._sig = signal

    @property
    def name(self) -> str:
        """str: The name of the adapted signal."""
        str = self._sig._name
        if '['  in str:
            str = '\\' + str
        return str

    @property
    def width(self) -> int:
        """int: The bit width of the adapted signal."""
        return self._sig._get_width()

    @property
    def is_reg(self) -> bool:
        """bool: Whether the adapted signal is a register."""
        return self._sig._is_reg

    @property
    def value(self) -> int:
        """int: The current value of the adapted signal."""
        return self._sig._get_value()

    @property
    def scope(self) -> List[str]:
        """list of str: The hierarchical scope of the signal."""
        mod = getattr(self._sig, "_module", None)
        if mod is None:
            return []

        if hasattr(mod, "_get_full_scope"):
            return mod._get_full_scope()

        return [str(mod)]


class Simulator:
    """Run HDLproto simulations by scheduling regions and optional VCD dumping.

    The Simulator orchestrates the entire simulation process. It builds the
    design hierarchy, manages the simulation time, executes the logic in
    the correct order according to HDL semantics (active region, NBA region, etc.),
    and interfaces with the VCD writer to dump waveforms.

    Parameters
    ----------
    testbench : TestBench
        The top-level `TestBench` module instance of the design to be simulated.
    clock : Wire
        The primary clock signal for the simulation. The `clock()` and
        `half_clock()` methods will drive this wire.
    max_comb_loops : int, optional
        The maximum number of delta cycles allowed within a single time step
        before assuming that combinational logic is unstable. Defaults to 30.
    vcd : VCDWriter, optional
        An instance of `VCDWriter` to use for dumping waveform data. If provided,
        all signals in the design will be registered with it. Defaults to None.

    Raises
    ------
    SignalUnstableError
        If the number of delta cycles in a time step exceeds `max_comb_loops`.
    """

    def __init__(
            self,
            testbench: TestBench,
            clock: Wire,
            max_comb_loops: int = 30,
            vcd: VCDWriter = None
    ):
        self._testbench = testbench
        self._clock = clock
        self._max_comb_loops = max_comb_loops
        self._sim_context = _SimulationContext()
        self._signal_list = _SignalList()
        self._function_list = _FunctionList(self._sim_context)
        self._active_region = _ActiveRegion(
            self._sim_context,
            self._signal_list,
            self._function_list
        )
        self._nba_region = _NBARegion(self._sim_context, self._signal_list)
        _EnvironmentBuilder()._build(
            self._testbench,
            self._sim_context,
            self._signal_list,
            self._function_list
        )
        self.vcd = vcd
        if self.vcd:
            self._register_signals_for_vcd()

    def clock(self):
        """Toggle the user-provided clock wire for a full cycle.

        This is a convenience method that calls `half_clock()` twice to simulate
        one full clock period (e.g., a low-to-high transition followed by a
        high-to-low transition).
        """
        self.half_clock()
        self.half_clock()

    def half_clock(self):
        """Advance simulation by one half clock cycle.

        This is the main entry point for advancing simulation time. It performs
        the following steps, adhering to standard HDL simulation semantics:
        1. Takes a `cycle` snapshot for edge detection in `@always_ff` blocks.
        2. Toggles the main clock signal.
        3. Enters the delta-cycle loop, which evaluates all active combinational
           and sequential logic until the design stabilizes.
        4. Dumps the new signal values to the VCD file if enabled.

        Raises
        ------
        SignalUnstableError
            If a combinational loop does not stabilize within the limit set by
            `max_comb_loops`.
        """
        # === (1) Cycle snapshot ===
        # Store previous clock-cycle values.
        # Used only for always_ff edge detection.
        self._signal_list._exec_all(lambda sig: sig._snapshot_cycle())

        # === (2) Drive master clock ===
        # HDLproto model:
        #   - clock is updated before evaluating always_ff
        #   - this matches the “input commit → sequential eval” ordering
        self._clock.w = 0 if self._clock.w else 1

        # === (3) Active Region → NBA Region → loop (delta-cycle)
        loop_count = 0
        while True:
            self._signal_list._exec_all(lambda sig: sig._snapshot_delta())
            self._active_region._execute()
            self._nba_region._execute()
            changed = self._signal_list._exec_all(lambda sig: sig._is_delta_changed())
            loop_count += 1
            if loop_count > self._max_comb_loops:
                raise SignalUnstableError("always_comb did not converge before max_comb_loops")
            if not changed:
                break
        self._sim_context._clear()

        if self.vcd:
            self.vcd._dump()

    def _register_signals_for_vcd(self):
        """Register every signal with the VCD writer using the adapter."""
        self._signal_list._exec_all(
            lambda sig: self.vcd._register(VCDSignalAdapter(sig))
        )