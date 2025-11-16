from typing import TYPE_CHECKING, Callable
from .simconfig import SimConfig
from .testcase_manager import _TestcaseManager
from .function_manager import _FunctionManager
from .signal import Input, Output, Wire, Reg
from .signal.signal_manager import _SignalManager
from .signal.signal_list import _SignalList
from .module.module_manager import _ModuleManager
from .module.module_list import  _ModuleList, _ModuleContainer
from .module.module import Module
from .event.event_manager import _EventManager
from .event.event_mediator import _EventMediator
from .state import _ModuleType, _SignalType
from .testbench import TestBench
from .simulator import Simulator, _SimulationExector

class _EnvironmentBuilder:
    def __init__(
            self,
            _config: SimConfig,
            _testbench: TestBench,
            _module_manager_factory: Callable[[], _ModuleManager] = None,
            _function_manager_factory: Callable[[], _FunctionManager] = None,
            _signal_manager_factory: Callable[[], _SignalManager] = None,
            _event_manager_factory: Callable[[], _EventManager] = None,
            _event_mediator_factory: Callable[[], _EventMediator] = None,
            _testcase_manager_factory: Callable[[], _TestcaseManager] = None,
            _simulation_exector_factory: Callable[[], _SimulationExector] = None,
    ):
        self._config = _config
        self._testbench = _testbench
        self._module_manager_factory = _module_manager_factory or _ModuleManager
        self._function_manager_factory = _function_manager_factory or _FunctionManager
        self._signal_manager_factory = _signal_manager_factory or _SignalManager
        self._event_manager_factory = _event_manager_factory or _EventManager
        self._event_mediator_factory = _event_mediator_factory or _EventMediator
        self._testcase_manager_factory = _testcase_manager_factory or _TestcaseManager
        self._simulation_exector_factory = _simulation_exector_factory or _SimulationExector
        self._module_list = []
        self._function_bindings = []

    def _start_builder(self):
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
        self._register_signal_event_handler(self._module_list)
        self._register_function_event_handler(self._module_list)
        return self._finalize()

    def _create_managers(self):
        self._module_manager = self._module_manager_factory()
        self._function_manager = self._function_manager_factory()
        self._signal_manager = self._signal_manager_factory()
        self._event_manager = self._event_manager_factory()
        self._event_mediator = self._event_mediator_factory()
        self._testcase_manager = self._testcase_manager_factory()
        self._simulation_exector = self._simulation_exector_factory()

    def _setup_module_manager(self):
        self._module_manager.module_list = _ModuleList()
        self._module_list.extend(self._collect_recursive_modules(self._testbench))
        self._module_manager.module_list._modules.extend(self._module_list)

    def _collect_recursive_modules(self, module: (Module | TestBench)):
        modules = []
        if module._is_testbench:
            module_type = _ModuleType.TESTBENCH
            modules.append(_ModuleContainer(module, {"module_type": module_type}))
        for module in module._children:
            module_type = _ModuleType.MODULE if not module._is_testbench else _ModuleType.TESTBENCH
            modules.append(_ModuleContainer(module, {"module_type": module_type}))
            modules.extend(self._collect_recursive_modules(module))
        return modules

    def _setup_function_manager(self):
        for module_container in self._module_list:
            module = module_container._module
            for name in module._dir():
                func = getattr(module, name)
                if hasattr(func, '_type'):
                    if func._type == 'always_comb':
                        self._function_manager._always_comb_functions.append(func)
                    elif func._type == 'always_ff':
                        self._function_manager._always_ff_functions.append(func)

    def _collect_function_bindings(self):
        self._function_bindings.clear()
        for module_container in self._module_list:
            module = module_container._module
            for name in module._dir():
                func = getattr(module, name)
                if hasattr(func, '_type'):
                    function_obj = getattr(func, "__func__", func)
                    self._function_bindings.append((function_obj, module, name))

    def _setup_testcase_manager(self):
        self._testcase_manager._simulator = None
        for name in dir(self._testbench):
            func = getattr(self._testbench, name)
            if hasattr(func, '_type'):
                if func._type == 'testcase':
                    self._testcase_manager._testcase_functions.append([name, func])

    def _setup_signal_manager(self):
        self._signal_manager._signal_list = _SignalList()
        self._collect_and_configure_signals(self._module_list)

    def _collect_and_configure_signals(self, modules):
        for module_container in modules:
            module = module_container._module
            for name, signal in module.__dict__.items():
                if isinstance(signal, (Input, Output, Wire, Reg)):
                    # コンテキスト設定
                    signal_type = Input, Output, Wire, Reg
                    signal._context._name = name
                    signal._context._signal_type = signal_type
                    signal._context._module = module

                    # シグナルリストに追加
                    if signal in self._signal_manager._signal_list:
                        continue
                    if not module._is_testbench and isinstance(signal, Input):
                        self._signal_manager._signal_list._append(signal, {"signal_type": _SignalType.INPUT})
                    elif not module._is_testbench and isinstance(signal, Output):
                        self._signal_manager._signal_list._append(signal, {"signal_type": _SignalType.OUTPUT})
                    elif not module._is_testbench and isinstance(signal, Wire):
                        self._signal_manager._signal_list._append(signal, {"signal_type": _SignalType.WIRE})
                    elif not module._is_testbench and isinstance(signal, Reg):
                        self._signal_manager._signal_list._append(signal, {"signal_type": _SignalType.REG})
                    elif module._is_testbench and isinstance(signal, Wire):
                        self._signal_manager._signal_list._append(signal, {"signal_type": _SignalType.EXTERNAL})

    def _register_signal_event_handler(self, modules):
        for module_container in modules:
            module = module_container._module
            for name, signal in module.__dict__.items():
                if isinstance(signal, (Input, Output, Wire, Reg)):
                    signal._signal._event._handler = self._event_manager._handle_event

    def _register_function_event_handler(self, modules):
        for module_container in modules:
            module = module_container._module
            for name, func in module.__class__.__dict__.items():
                if callable(func) and hasattr(func, '_type'):
                    if func._type in ['always_comb', 'always_ff']:
                        func._handler = self._event_manager._handle_event

    def _assign_module_paths(self):
        for module_container in self._module_list:
            self._ensure_module_path(module_container._module)

    def _ensure_module_path(self, module: Module):
        if getattr(module, "module_path", None):
            return module._module_path
        if module._parent:
            parent_path = self._ensure_module_path(module._parent)
            name = module._instance_name or module._class_name
            module._module_path = f"{parent_path}.{name}"
        else:
            module._module_path = module._instance_name or module._class_name
        return module._module_path

    def _assign_signal_module_paths(self):
        for module_container in self._module_list:
            module = module_container._module
            module_path = getattr(module, "_module_path", None)
            for signal in module.__dict__.values():
                if isinstance(signal, (Input, Output, Wire, Reg)):
                    signal._context._module_path = module_path

    def _assign_function_module_paths(self):
        for function_obj, module, func_name in self._function_bindings:
            module_path = getattr(module, "_module_path", None)
            setattr(function_obj, "_hdlproto_module_path", module_path)
            setattr(function_obj, "_hdlproto_func_name", func_name)

    def _resolve_always_ff_triggers(self):
        for module_container in self._module_list:
            module = module_container._module
            for name in module._dir():
                method = getattr(module, name)
                if getattr(method, '_type', None) != 'always_ff':
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
        self._event_manager._event_mediator = self._event_mediator
        self._event_manager._function_handler = self._function_manager._handle_event
        self._event_manager._signal_handler = self._signal_manager._handle_event
        self._event_manager._event_mediator_handler = self._event_mediator._handle_event
        self._event_mediator._module_manager = self._module_manager
        self._event_mediator._signal_manager = self._signal_manager
        self._event_mediator._function_manager = self._function_manager
        self._event_mediator._simulation_exector = self._simulation_exector
        self._event_mediator._handler = self._event_manager._handle_event
        self._simulation_exector._config = self._config
        self._simulation_exector._module_manager = self._module_manager
        self._simulation_exector._signal_manager = self._signal_manager
        self._simulation_exector._function_manager = self._function_manager
        self._simulation_exector._event_mediator = self._event_mediator
        self._simulation_exector._event_manager = self._event_manager
        self._function_manager._signal_manager = self._signal_manager

    def _finalize(self):
        return {
            "testcase_manager": self._testcase_manager,
            "simulation_exector": self._simulation_exector,
        }
