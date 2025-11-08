from typing import TYPE_CHECKING

from .testbench import TestBench
from .error import SignalUnstableError
from .simconfig import SimConfig
from .state import SimulationState
from.factories import *

if TYPE_CHECKING:
    from .simconfig import SimConfig
    from .module import ModuleManager
    from .signal import SignalManager
    from .function_manager import FunctionManager
    from .event import EventManager, EventMediator

class Simulator:
    def __init__(self, config: SimConfig, testbench: TestBench):
        self.config = config
        self.tb = testbench
        self.clock_cycle = 0
        self.exector = None
        self.testcase_manager = None
        self._build_environment(config, testbench)
        pass

    def _build_environment(self, config: SimConfig, testbench: TestBench):
        from .environment_builder import EnvironmentBuilder

        env_builder = EnvironmentBuilder(
            config=config,
            testbench=testbench,
            module_manager_factory=module_manager_factory,
            function_manager_factory=function_manager_factory,
            signal_manager_factory=signal_manager_factory,
            event_manager_factory=event_manager_factory,
            event_mediator_factory=event_mediator_factory,
            testcase_manager_factory=testcase_manager_factory,
            simulation_exector_factory=simulation_exector_factory,
        )
        env = env_builder.start_builder()
        self.testcase_manager = env["testcase_manager"]
        self.exector = env["simulation_exector"]
        self.testcase_manager.simulator = self

    def start(self):
        self.tb.log_sim_start(self.config)

    def end(self):
        self.tb.log_sim_end()

    def reset(self):
        self.exector.evaluate_always_ff(reset=True)
        self.exector.evaluate_always_comb()

    def clock(self):
        self.exector.evaluate_external()
        self.tb.log_clock_start(self.clock_cycle)
        self.exector.log_clock_start(self.clock_cycle)
        self.exector.evaluate_always_ff(reset=False)
        self.exector.evaluate_always_comb()
        self.exector.log_clock_end(self.clock_cycle)
        self.clock_cycle += 1

    def testcase(self, name: str=None):
        self.testcase_manager.run_testcase(name)

class SimulationExector:
    def __init__(
            self,
            sim_config: "SimConfig | None" = None,
            module_manager: "ModuleManager | None" = None,
            signal_manager: "SignalManager | None" = None,
            function_manager: "FunctionManager | None" = None,
            event_mediator: "EventMediator | None" = None,
            event_manager: "EventManager | None" = None
    ):
        self.state = SimulationState.IDLE
        self.config = sim_config
        self.module_manager = module_manager
        self.signal_manager = signal_manager
        self.function_manager = function_manager
        self.event_mediator = event_mediator
        self.event_manager = event_manager

    def evaluate_external(self):
        self.signal_manager.update_externals()

    def evaluate_always_ff(self, reset=False):
        self.state = SimulationState.ALWAYS_FF
        self.function_manager.evaluate_always_ff(reset)
        self.signal_manager.update_regs()
        self.state = SimulationState.IDLE

    def evaluate_always_comb(self):
        for iteration in range(self.config.max_comb_loops):
            self.state = SimulationState.ALWAYS_COMB
            self.function_manager.evaluate_always_comb()
            is_unstable = self.signal_manager.update_wires()
            self.state = SimulationState.IDLE
            if not is_unstable:
                return iteration + 1
        raise SignalUnstableError("Signal did not stabilize. Possible combinational feedback loop detected.")

    def log_clock_start(self, clock_cycle):
        self.module_manager.log_clock_start(clock_cycle)

    def log_clock_end(self, clock_cycle):
        self.module_manager.log_clock_end(clock_cycle)