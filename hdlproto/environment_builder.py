from typing import TYPE_CHECKING, Callable
from .simconfig import SimConfig
from .testcase_manager import TestcaseManager
from .function_manager import FunctionManager
from .signal import SignalManager, SignalList, Input, Output, Wire, Reg
from .module import ModuleManager, ModuleList, Module, ModuleContainer
from .event import EventManager, EventMediator
from .state import ModuleType, SignalType
from .testbench import TestBench
from .simulator import Simulator, SimulationExector

class EnvironmentBuilder:
    def __init__(
            self,
            config: SimConfig,
            testbench: TestBench,
            module_manager_factory: Callable[[], ModuleManager] = None,
            function_manager_factory: Callable[[], FunctionManager] = None,
            signal_manager_factory: Callable[[], SignalManager] = None,
            event_manager_factory: Callable[[], EventManager] = None,
            event_mediator_factory: Callable[[], EventMediator] = None,
            testcase_manager_factory: Callable[[], TestcaseManager] = None,
            simulation_exector_factory: Callable[[], SimulationExector] = None,
    ):
        self.config = config
        self.testbench = testbench
        self.module_manager_factory = module_manager_factory or ModuleManager
        self.function_manager_factory = function_manager_factory or FunctionManager
        self.signal_manager_factory = signal_manager_factory or SignalManager
        self.event_manager_factory = event_manager_factory or EventManager
        self.event_mediator_factory = event_mediator_factory or EventMediator
        self.testcase_manager_factory = testcase_manager_factory or TestcaseManager
        self.simulation_exector_factory = simulation_exector_factory or SimulationExector
        self.module_list = []
        self._function_bindings = []

    def start_builder(self):
        self._create_managers()
        self._setup_module_manager()
        self._setup_function_manager()
        self._setup_testcase_manager()
        self._setup_signal_manager()
        self._wire_dependencies()
        self._assign_module_paths()
        self._collect_function_bindings()
        self._assign_function_module_paths()
        self._assign_signal_module_paths()
        self._resolve_always_ff_triggers()
        self._register_signal_event_handler(self.module_list)
        self._register_function_event_handler(self.module_list)
        return self._finalize()

    def _create_managers(self):
        self.module_manager = self.module_manager_factory()
        self.function_manager = self.function_manager_factory()
        self.signal_manager = self.signal_manager_factory()
        self.event_manager = self.event_manager_factory()
        self.event_mediator = self.event_mediator_factory()
        self.testcase_manager = self.testcase_manager_factory()
        self.simulation_exector = self.simulation_exector_factory()

    def _setup_module_manager(self):
        self.module_manager.module_list = ModuleList()
        self.module_list.extend(self._collect_recursive_modules(self.testbench))
        self.module_manager.module_list._modules.extend(self.module_list)

    def _collect_recursive_modules(self, module: (Module | TestBench)):
        modules = []
        if module.is_testbench:
            module_type = ModuleType.TESTBENCH
            modules.append(ModuleContainer(module, {"module_type": module_type}))
        for module in module.children:
            module_type = ModuleType.MODULE if not module.is_testbench else ModuleType.TESTBENCH
            modules.append(ModuleContainer(module, {"module_type": module_type}))
            modules.extend(self._collect_recursive_modules(module))
        return modules

    def _setup_function_manager(self):
        for module_container in self.module_list:
            module = module_container.module
            for name in module.dir():
                func = getattr(module, name)
                if hasattr(func, 'type'):
                    if func.type == 'always_comb':
                        self.function_manager.always_comb_functions.append(func)
                    elif func.type == 'always_ff':
                        self.function_manager.always_ff_functions.append(func)

    def _collect_function_bindings(self):
        self._function_bindings.clear()
        for module_container in self.module_list:
            module = module_container.module
            for name in module.dir():
                func = getattr(module, name)
                if hasattr(func, 'type'):
                    function_obj = getattr(func, "__func__", func)
                    self._function_bindings.append((function_obj, module, name))

    def _setup_testcase_manager(self):
        self.testcase_manager.simulator = None
        for name in dir(self.testbench):
            func = getattr(self.testbench, name)
            if hasattr(func, 'type'):
                if func.type == 'testcase':
                    self.testcase_manager.testcase_functions.append([name, func])

    def _setup_signal_manager(self):
        self.signal_manager.signal_list = SignalList()
        self._collect_and_configure_signals(self.module_list)

    def _collect_and_configure_signals(self, modules):
        for module_container in modules:
            module = module_container.module
            for name, signal in module.__dict__.items():
                if isinstance(signal, (Input, Output, Wire, Reg)):
                    # コンテキスト設定
                    signal_type = Input, Output, Wire, Reg
                    signal.context.name = name
                    signal.context.signal_type = signal_type
                    signal.context.module = module

                    # シグナルリストに追加
                    if signal in self.signal_manager.signal_list:
                        continue
                    if not module.is_testbench and isinstance(signal, Input):
                        self.signal_manager.signal_list.append(signal, {"signal_type": SignalType.INPUT})
                    elif not module.is_testbench and isinstance(signal, Output):
                        self.signal_manager.signal_list.append(signal, {"signal_type": SignalType.OUTPUT})
                    elif not module.is_testbench and isinstance(signal, Wire):
                        self.signal_manager.signal_list.append(signal, {"signal_type": SignalType.WIRE})
                    elif not module.is_testbench and isinstance(signal, Reg):
                        self.signal_manager.signal_list.append(signal, {"signal_type": SignalType.REG})
                    elif module.is_testbench and isinstance(signal, Wire):
                        self.signal_manager.signal_list.append(signal, {"signal_type": SignalType.EXTERNAL})

    def _register_signal_event_handler(self, modules):
        for module_container in modules:
            module = module_container.module
            for name, signal in module.__dict__.items():
                if isinstance(signal, (Input, Output, Wire, Reg)):
                    signal._signal.event.handler = self.event_manager.handle_event

    def _register_function_event_handler(self, modules):
        for module_container in modules:
            module = module_container.module
            for name, func in module.__class__.__dict__.items():
                if callable(func) and hasattr(func, 'type'):
                    if func.type in ['always_comb', 'always_ff']:
                        func.handler = self.event_manager.handle_event

    def _assign_module_paths(self):
        for module_container in self.module_list:
            self._ensure_module_path(module_container.module)

    def _ensure_module_path(self, module: Module):
        if getattr(module, "module_path", None):
            return module.module_path
        if module.parent:
            parent_path = self._ensure_module_path(module.parent)
            name = module.instance_name or module.class_name
            module.module_path = f"{parent_path}.{name}"
        else:
            module.module_path = module.instance_name or module.class_name
        return module.module_path

    def _assign_signal_module_paths(self):
        for module_container in self.module_list:
            module = module_container.module
            module_path = getattr(module, "module_path", None)
            for signal in module.__dict__.values():
                if isinstance(signal, (Input, Output, Wire, Reg)):
                    signal.context.module_path = module_path

    def _assign_function_module_paths(self):
        for function_obj, module, func_name in self._function_bindings:
            module_path = getattr(module, "module_path", None)
            setattr(function_obj, "_hdlproto_module_path", module_path)
            setattr(function_obj, "_hdlproto_func_name", func_name)

    def _resolve_always_ff_triggers(self):
        for module_container in self.module_list:
            module = module_container.module
            for name in module.dir():
                method = getattr(module, name)
                if getattr(method, 'type', None) != 'always_ff':
                    continue
                function_obj = getattr(method, "__func__", method)
                triggers = getattr(function_obj, '_triggers', ())
                resolved = []
                for trigger in triggers:
                    signal_name = trigger.get("signal_name")
                    if signal_name is None:
                        signal_obj = None
                    else:
                        if not hasattr(module, signal_name):
                            raise AttributeError(
                                f"always_ff trigger references unknown signal '{signal_name}' in module {module}"
                            )
                        signal_obj = getattr(module, signal_name)
                    resolved.append({
                        "edge": trigger.get("edge"),
                        "signal": signal_obj,
                    })
                setattr(function_obj, '_resolved_triggers', tuple(resolved))

    def _wire_dependencies(self):
        self.event_manager.event_mediator = self.event_mediator
        self.event_manager.function_handler = self.function_manager.handle_event
        self.event_manager.signal_handler = self.signal_manager.handle_event
        self.event_manager.event_mediator_handler = self.event_mediator.handle_event
        self.event_mediator.module_manager = self.module_manager
        self.event_mediator.signal_manager = self.signal_manager
        self.event_mediator.function_manager = self.function_manager
        self.event_mediator.simulation_exector = self.simulation_exector
        self.event_mediator.handler = self.event_manager.handle_event
        self.simulation_exector.config = self.config
        self.simulation_exector.module_manager = self.module_manager
        self.simulation_exector.signal_manager = self.signal_manager
        self.simulation_exector.function_manager = self.function_manager
        self.simulation_exector.event_mediator = self.event_mediator
        self.simulation_exector.event_manager = self.event_manager
        self.function_manager.signal_manager = self.signal_manager

    def _finalize(self):
        return {
            "testcase_manager": self.testcase_manager,
            "simulation_exector": self.simulation_exector,
        }
