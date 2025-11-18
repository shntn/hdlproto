from typing import TYPE_CHECKING

from .testbench import TestBench
from .error import SignalUnstableError
from .simconfig import SimConfig
from .state import _SimulationState
from .factories import (_module_manager_factory,
                        _function_manager_factory,
                        _signal_manager_factory,
                        _event_manager_factory,
                        _event_mediator_factory,
                        _testcase_manager_factory,
                        _simulation_exector_factory)

if TYPE_CHECKING:
    from .simconfig import SimConfig
    from .module.module_manager import _ModuleManager
    from .signal.signal_manager import _SignalManager
    from .function_manager import _FunctionManager
    from .event.event_manager import _EventManager
    from .event.event_mediator import _EventMediator

class Simulator:
    """The main class for executing HDLproto simulations.

    This class takes a testbench and simulation settings to manage
    the event-driven simulation loop. Users control the simulation
    through an instance of this class.

    Parameters
    ----------
    config : SimConfig
        A `SimConfig` instance that holds the simulation settings,
        such as the clock signal and the maximum number of loops for
        combinational circuits.
    testbench : TestBench
        The `TestBench` instance that serves as the top level of the
        simulation.

    Examples
    --------
    >>> # Prepare TestBench and SimConfig
    >>> tb = MyTestBench()
    >>> config = SimConfig(clock=tb.clk)
    ...
    >>> # Instantiate the simulator
    >>> sim = Simulator(config, tb)
    ...
    >>> # Explicitly calling start and end of simulation
    >>> sim.start()
    >>> sim.testcase("run_test")
    >>> sim.end()
    ...
    >>> # Simple usage by only calling the testcase method
    >>> sim.testcase("run_test")

    See Also
    --------
    TestBench, SimConfig, testcase
    """
    def __init__(self, config: SimConfig, testbench: TestBench):
        self._config = config
        self._tb = testbench
        self._clock_cycle = 0
        self._exector = None
        self._testcase_manager = None
        self._build_environment(config, testbench)

    def _build_environment(self, config: SimConfig, testbench: TestBench):
        from .environment_builder import _EnvironmentBuilder

        env_builder = _EnvironmentBuilder(
            _config=config,
            _testbench=testbench,
            _module_manager_factory=_module_manager_factory,
            _function_manager_factory=_function_manager_factory,
            _signal_manager_factory=_signal_manager_factory,
            _event_manager_factory=_event_manager_factory,
            _event_mediator_factory=_event_mediator_factory,
            _testcase_manager_factory=_testcase_manager_factory,
            _simulation_exector_factory=_simulation_exector_factory,
        )
        env = env_builder._start_builder()
        self._testcase_manager = env["testcase_manager"]
        self._exector = env["simulation_exector"]
        self._testcase_manager._simulator = self

    def start(self):
        """Starts the simulation and calls the start hook.

        Calls the `log_sim_start` method of the `TestBench`.
        By calling this before executing any test cases, initialization
        processes can be performed.
        """
        self._tb.log_sim_start(self._config)

    def end(self):
        """Ends the simulation and calls the end hook.

        Calls the `log_sim_end` method of the `TestBench`.
        By calling this after all test cases have been executed, final
        processing can be performed.
        """
        self._tb.log_sim_end()

    def clock(self):
        """Advances the simulation by one clock cycle.

        This method executes a full simulation cycle, including both
        the rising and falling edges of the clock.
        Internally, it calls `half_clock` twice.
        """
        self._tb.log_clock_start(self._clock_cycle)
        self._exector._log_clock_start(self._clock_cycle)
        self._config.clock.w = 0 if self._config.clock.w else 1
        self._half_clock()
        self._config.clock.w = 0 if self._config.clock.w else 1
        self._half_clock()
        self._exector._log_clock_end(self._clock_cycle)
        self._clock_cycle += 1

    def half_clock(self):
        """Advances the simulation by half a clock cycle.

        This is mainly used for detailed timing verification and testing
        purposes. It updates the state of the clock signal and executes
        the propagation and stabilization of signal values.
        """
        self._tb.log_clock_start(self._clock_cycle)
        self._exector._log_clock_start(self._clock_cycle)
        self._config.clock.w = 0 if self._config.clock.w else 1
        self._half_clock()
        self._exector._log_clock_end(self._clock_cycle)
        self._clock_cycle += 1 if self._config.clock.w else 0

    def _half_clock(self):
        _is_write = None
        self._exector._store_stabled_value_for_trigger()
        self._exector._store_stabled_value_for_write()
        self._exector._evaluate_external()
        while _is_write is not False:
            self._exector._extract_triggerd_always_ff()
            self._exector._evaluate_always_ff()
            self._exector._evaluate_always_comb()
            self._exector._update_reg_to_latest_value()
            _is_write = self._exector._is_write()
            self._exector._store_stabled_value_for_write()

    def testcase(self, name: str=None):
        """Executes the specified test case.

        Executes a method defined by the `@testcase` decorator within
        the `TestBench`.

        Parameters
        ----------
        name : str, optional
            The name of the test case method to execute.
            If omitted, all defined test cases will be executed in order.
        """
        self._testcase_manager._run_testcase(name)

class _SimulationExector:
    def __init__(
            self,
            _sim_config: "SimConfig | None" = None,
            _module_manager: "_ModuleManager | None" = None,
            _signal_manager: "_SignalManager | None" = None,
            _function_manager: "_FunctionManager | None" = None,
            _event_mediator: "_EventMediator | None" = None,
            _event_manager: "_EventManager | None" = None
    ):
        self._state = _SimulationState.IDLE
        self._config = _sim_config
        self._module_manager = _module_manager
        self._signal_manager = _signal_manager
        self._function_manager = _function_manager
        self._event_mediator = _event_mediator
        self._event_manager = _event_manager

    def _store_stabled_value_for_trigger(self):
        self._signal_manager._store_stabled_value_for_trigger()

    def _evaluate_external(self):
        self._signal_manager._update_externals()

    def _store_stabled_value_for_write(self):
        self._signal_manager._store_stabled_value_for_write()

    def _extract_triggerd_always_ff(self):
        self._function_manager._extract_triggerd_always_ff()

    def _evaluate_always_ff(self):
        self._state = _SimulationState.ALWAYS_FF
        self._function_manager._evaluate_always_ff()
        self._state = _SimulationState.IDLE

    def _evaluate_always_comb(self):
        for iteration in range(self._config.max_comb_loops):
            self._state = _SimulationState.ALWAYS_COMB
            self._function_manager._evaluate_always_comb()
            is_unstable = self._signal_manager._update_wires()
            self._state = _SimulationState.IDLE
            if not is_unstable:
                return iteration + 1
        raise SignalUnstableError("Signal did not stabilize. Possible combinational feedback loop detected.")

    def _update_reg_to_latest_value(self):
        self._signal_manager._update_regs()

    def _is_write(self):
        return self._signal_manager._is_write()

    def _log_clock_start(self, clock_cycle):
        self._module_manager._log_clock_start(clock_cycle)

    def _log_clock_end(self, clock_cycle):
        self._module_manager._log_clock_end(clock_cycle)
