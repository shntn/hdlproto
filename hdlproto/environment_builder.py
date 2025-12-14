import copy

from .module import TestBench, Module, AlwaysFFWrapper
from .simulation_context import _SimulationContext
from .region import _SignalList, _FunctionList
from .signal import Wire, Reg, InputWire, OutputWire, OutputReg
from .signal_array import _SignalArray, InputWireArray, OutputWireArray, OutputRegArray

class _EnvironmentBuilder:
    """Builds the simulation environment by traversing the module hierarchy.

    This internal class is responsible for the setup phase of the simulation.
    It recursively walks the design hierarchy starting from a `TestBench`,
    discovering all `Module` instances, signals (`Wire`, `Reg`, etc.), and
    processes (`@always_comb`, `@always_ff`).

    During traversal, it:
    1. Sets the name and parent of each `Module`.
    2. Attaches the simulation context to each signal.
    3. Registers all signals with the `_SignalList`.
    4. Binds `@always_ff` wrappers to their module instances and registers the
       resulting `BoundAlwaysFF` objects with the `_FunctionList`.
    5. Registers all `@always_comb` functions with the `_FunctionList`.
    """

    def __init__(self):
        self._testbench = None
        self._submodules = []
        self._sim_context = None

    def _build(
            self,
            testbench: TestBench,
            sim_context: _SimulationContext,
            signal_list: _SignalList,
            function_list: _FunctionList,
    ) -> None:
        """Initialize the root TestBench and recursively build the environment.

        Parameters
        ----------
        testbench : TestBench
            The top-level module instance for the simulation.
        sim_context : _SimulationContext
            The simulation context to attach to all objects.
        signal_list : _SignalList
            The list to populate with all discovered signals.
        function_list : _FunctionList
            The list to populate with all discovered processes.
        """
        testbench._name = "TestBench"
        self._build_recursive(testbench, sim_context, signal_list, function_list)

    def _build_recursive(
            self,
            module: Module,
            sim_context: _SimulationContext,
            signal_list: _SignalList,
            function_list: _FunctionList,
    ):
        """Walk a module, collecting its signals, functions, and child modules.

        This method is called recursively for each module in the design hierarchy.

        Parameters
        ----------
        module : Module
            The current module instance to process.
        sim_context : _SimulationContext
            The simulation context.
        signal_list : _SignalList
            The list for registering signals.
        function_list : _FunctionList
            The list for registering functions.
        """
        self._collect_signals(sim_context, module, signal_list)
        self._collect_functions(module, function_list)
        self._collect_modules(module)
        for name, mod in module.__dict__.items():
            if isinstance(mod, Module) and name != "_parent":
                self._build_recursive(mod, sim_context, signal_list, function_list)

    def _collect_signals(
            self,
            sim_context: _SimulationContext,
            module: Module,
            signal_list: _SignalList
    ):
        """Find all signal attributes in a module and register them.

        Parameters
        ----------
        sim_context : _SimulationContext
            The simulation context to attach to the signals.
        module : Module
            The module instance to scan for signals.
        signal_list : _SignalList
            The list to add the found signals to.
        """

        def is_modport(obj):
            return hasattr(obj, '_ports') and hasattr(obj, '_parent') and hasattr(obj, '_ports')

        # 辞書のサイズが変わるのを避けるため、list化してからループする
        for name, signal in list(module.__dict__.items()):
            if isinstance(signal, _SignalArray):
                for i, item in enumerate(signal):
                    item_name = f"{name}[{i}]"
                    if isinstance(item, (Wire, InputWire, OutputWire)):
                        item._set_context(name=item_name, module=module, sim_context=sim_context)
                        signal_list._append_wire(item)
                    elif isinstance(item, (Reg, OutputReg)):
                        item._set_context(name=item_name, module=module, sim_context=sim_context)
                        signal_list._append_reg(item)
            elif isinstance(signal, (Wire, InputWire, OutputWire)):
                signal._set_context(name=name, module=module, sim_context=sim_context)
                signal_list._append_wire(signal)
            elif isinstance(signal, (Reg, OutputReg)):
                signal._set_context(name=name, module=module, sim_context=sim_context)
                signal_list._append_reg(signal)
            elif is_modport(signal):
                modport_copy = copy.copy(signal)
                modport_copy._ports = {}
                for port_name, port_obj in signal._ports.items():
                    full_name = f"{name}.{port_name}"
                    if isinstance(port_obj, _SignalArray):
                        # 配列コンテナのコピー
                        array_copy = copy.copy(port_obj)
                        new_items = []
                        # 中身を1つずつ展開して処理
                        for i, item in enumerate(port_obj):
                            item_copy = copy.copy(item)
                            item_name = f"{full_name}[{i}]"
                            item_copy._set_context(name=item_name, module=module, sim_context=sim_context)
                            if isinstance(item_copy, (Reg, OutputReg)):
                                signal_list._append_reg(item_copy)
                            else:
                                signal_list._append_wire(item_copy)
                            new_items.append(item_copy)
                        array_copy._items = new_items
                        setattr(modport_copy, port_name, array_copy)
                        modport_copy._ports[port_name] = array_copy

                    else:
                        port_copy = copy.copy(port_obj)
                        port_copy._set_context(name=full_name, module=module, sim_context=sim_context)
                        signal_list._append_wire(port_copy)
                        setattr(modport_copy, port_name, port_copy)
                        modport_copy._ports[port_name] = port_copy
                setattr(module, name, modport_copy)

    def _collect_functions(
            self,
            module: Module,
            function_list: _FunctionList
    ):
        """Find all process functions in a module's class and register them.

        This method scans the class (not the instance) for decorated methods.

        Parameters
        ----------
        module : Module
            The module instance whose class will be scanned.
        function_list : _FunctionList
            The list to add the found functions to.
        """
        for name, func in module.__class__.__dict__.items():
            if isinstance(func, AlwaysFFWrapper):
                bound = func.bind(module)
                function_list._append_always_ff(bound)
            elif not callable(func) or not hasattr(func, '_type'):
                continue
            elif func._type == 'always_comb':
                # Get the bound method from the instance
                func_wrapper = getattr(module, name)
                # Attach metadata to the original function object
                func._name = name
                func._module = module
                function_list._append_always_comb(func_wrapper)

    def _collect_modules(
            self,
            module: Module
    ):
        """Find all submodules in a module and set up their hierarchy links.

        Parameters
        ----------
        module : Module
            The parent module instance to scan for children.
        """
        for name, mod in module.__dict__.items():
            if isinstance(mod, Module) and name != "_parent":
                mod._name = name
                mod._parent = module
                module._submodules.append(mod)