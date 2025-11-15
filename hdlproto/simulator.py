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

    def clock(self):
        self.tb.log_clock_start(self.clock_cycle)
        self.exector.log_clock_start(self.clock_cycle)
        self.config.clock.w = 0 if self.config.clock.w else 1
        self._half_clock()
        self.config.clock.w = 0 if self.config.clock.w else 1
        self._half_clock()
        self.exector.log_clock_end(self.clock_cycle)
        self.clock_cycle += 1

    def half_clock(self, clock: (1|0)=0):
        self.tb.log_clock_start(self.clock_cycle)
        self.exector.log_clock_start(self.clock_cycle)
        self.config.clock.w = 0 if self.config.clock.w else 1
        self._half_clock()
        self.exector.log_clock_end(self.clock_cycle)
        self.clock_cycle += 1 if clock else 0

    def _half_clock(self):
        is_write = None
        self.exector.store_stabled_value_for_trigger()
        self.exector.store_stabled_value_for_write()
        self.exector.evaluate_external()
        while is_write is not False:
            self.exector.extract_triggerd_always_ff()
            self.exector.evaluate_always_ff()
            self.exector.evaluate_always_comb()
            self.exector.update_reg_to_latest_value()
            is_write = self.exector.is_write()
            self.exector.store_stabled_value_for_write()

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

    def store_stabled_value_for_trigger(self):
        self.signal_manager.store_stabled_value_for_trigger()

    def evaluate_external(self):
        self.signal_manager.update_externals()

    def store_stabled_value_for_write(self):
        self.signal_manager.store_stabled_value_for_write()

    def extract_triggerd_always_ff(self):
        self.function_manager.extract_triggerd_always_ff()

    def evaluate_always_ff(self):
        self.state = SimulationState.ALWAYS_FF
        self.function_manager.evaluate_always_ff()
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

    def update_reg_to_latest_value(self):
        self.signal_manager.update_regs()

    def is_write(self):
        return self.signal_manager.is_write()

    def log_clock_start(self, clock_cycle):
        self.module_manager.log_clock_start(clock_cycle)

    def log_clock_end(self, clock_cycle):
        self.module_manager.log_clock_end(clock_cycle)
