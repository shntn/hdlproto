from .state import Edge


class Trigger:
    """Evaluate trigger specs against a module's signals for always_ff blocks.

    This is an internal helper class for `@always_ff`.

    Parameters
    ----------
    triggers : list of dict
        A list of trigger specifications, where each dict contains the
        'signal' object, and the 'edge' to check for.
    """

    def __init__(self, triggers):
        self._triggers = triggers

    def _is_triggered(self):
        """Check if any of the specified signal transitions have occurred.

        Returns
        -------
        bool
            True if any trigger condition is met, False otherwise.
        """
        for trig in self._triggers:
            sig = trig["signal"]
            if sig._is_delta_changed() and sig._equal_cycle_edge(trig["edge"]):
                return True
        return False


# ============================================================
# always_ff の “クラスレベル wrapper”
# ============================================================
class AlwaysFFWrapper:
    """Descriptor returned by @always_ff that stores trigger specs and target function.

    This class is part of the descriptor protocol used to implement `@always_ff`.
    It is created at class definition time and holds the unevaluated trigger
    specifications and a reference to the decorated function.

    Parameters
    ----------
    func : function
        The function decorated by `@always_ff`.
    trigger_specs : list of dict
        The list of trigger specifications (edge and signal name).
    """

    def __init__(self, func, trigger_specs):
        self.func = func
        self._trigger_specs = trigger_specs
        self._type = "always_ff"
        self._name = func.__name__
        self._module = None

    def __get__(self, instance, owner):
        """Return the wrapper itself so Module._build_structure can bind it later.

        This is part of the descriptor protocol. When accessed on a class, it
        returns itself. When accessed on an instance, it could return a bound
        method, but here we return the wrapper to be processed by the environment
        builder.
        """
        if instance is None:
            return self
        return self

    def bind(self, module_instance):
        """Create a BoundAlwaysFF tied to the provided module instance.

        Parameters
        ----------
        module_instance : Module
            The instance of the module to which this always block belongs.

        Returns
        -------
        BoundAlwaysFF
            A new object that represents the runtime binding of the always
            block to a specific module instance.
        """
        return BoundAlwaysFF(self, module_instance)


# ============================================================
# always_ff の “インスタンスレベル実行体”
# ============================================================
class BoundAlwaysFF:
    """Runtime representation of an always_ff block bound to a module instance.

    This object is created by the environment builder for each `@always_ff`
    block in each module instance. It resolves the signal names in the trigger
    specification to actual signal objects from the instance.

    Parameters
    ----------
    wrapper : AlwaysFFWrapper
        The class-level wrapper that contains the function and trigger specs.
    module_instance : Module
        The specific module instance this block is bound to.
    """

    def __init__(self, wrapper: AlwaysFFWrapper, module_instance):
        self.wrapper = wrapper
        self._module = module_instance

        # method にバインド
        self.func = wrapper.func.__get__(module_instance, module_instance.__class__)

        # trigger へ signal を埋め込む
        self._triggers = []
        for t in wrapper._trigger_specs:
            signal_name = t["signal_name"]
            target_obj = module_instance

            try:
                for part in signal_name.split('.'):
                    target_obj = getattr(target_obj, part)
            except AttributeError:
                raise AttributeError(
                    f"Signal '{signal_name}' not found in module '{type(module_instance).__name__}'."
                )

            self._triggers.append({
                "edge": t["edge"],
                "signal_name": signal_name,
                "signal": target_obj
            })
        self._trigger = Trigger(self._triggers)

        self._name = wrapper._name
        self._module = module_instance
        self._type = "always_ff"

    def __call__(self):
        """Invoke the decorated always_ff function."""
        return self.func()


# ============================================================
# always_ff decorator（class-level wrapper を返す）
# ============================================================
def always_ff(*trigger_specs: tuple[Edge, str]):
    """Decorate a method as a sequential process sensitive to signal edges.

    This decorator marks a method within a `Module` as being an `always_ff`
    block, which is sensitive to explicit edge triggers, typically a clock.
    It simulates the behavior of a Verilog `always @(posedge clk)` block.

    Parameters
    ----------
    *trigger_specs : tuple of (Edge, str)
        A variable number of trigger tuples. Each tuple must contain an
        `Edge` (`Edge.POS` or `Edge.NEG`) and a string with the name of
        the signal to be sensitive to.

    Returns
    -------
    function
        A decorator that wraps the function in an `AlwaysFFWrapper`.

    Raises
    ------
    TypeError
        If the arguments are not in the format `(Edge, str)`.

    Examples
    --------
    >>> class MyModule(Module):
    ...     def __init__(self):
    ...         self.clk = Wire()
    ...         self.q = Reg()
    ...
    ...     @always_ff((Edge.POS, "clk"))
    ...     def my_process(self):
    ...         self.q.r = 1
    """
    if not trigger_specs:
        raise TypeError("@always_ff requires at least one (Edge, signal) trigger tuple.")

    normalized = []
    for spec in trigger_specs:
        if not isinstance(spec, tuple) or len(spec) != 2:
            raise TypeError("always_ff triggers must be tuples of (Edge, signal_name).")
        edge_value, signal_name = spec
        if not isinstance(edge_value, Edge):
            raise TypeError("always_ff triggers must use Edge.POS or Edge.NEG.")
        if not isinstance(signal_name, str):
            raise TypeError("always_ff trigger signal must be provided as an attribute name (str).")
        normalized.append({"edge": edge_value, "signal_name": signal_name, "signal": None})

    def _decorator(func):
        return AlwaysFFWrapper(func, normalized)

    return _decorator


# ============================================================
# always_comb decorator
# ============================================================
def always_comb(func):
    """Decorate a method as a purely combinational process.

    This decorator marks a method within a `Module` as being an `always_comb`
    block. The simulator will execute this block whenever any of the signals
    read within it change. This simulates the behavior of a Verilog
    `always @*` or `always_comb` block.

    The simulator determines the sensitivity list automatically.

    Parameters
    ----------
    func : function
        The method to be decorated.

    Returns
    -------
    function
        The original function, marked with a `_type` attribute.

    Examples
    --------
    >>> class MyAdder(Module):
    ...     def __init__(self):
    ...         self.a = Input(Wire())
    ...         self.b = Input(Wire())
    ...         self.sum = Output(Wire())
    ...
    ...     @always_comb
    ...     def add_logic(self):
    ...         self.sum.w = self.a.w + self.b.w
    """
    func._type = 'always_comb'
    func._name = None
    func._module = None
    return func


class Module:
    """Base class for user-defined HDLproto modules with hierarchical scope support.

    Users should inherit from this class to define a new hardware module.
    Modules can contain signals (`Wire`, `Reg`), ports (`Input`, `Output`),
    instances of other modules, and processes (`@always_comb`, `@always_ff`).

    Attributes
    ----------
    _name : str
        The instance name of the module.
    _parent : Module or None
        The parent module in the hierarchy, or None if it is the top module.
    _submodules : list of Module
        A list of child modules instantiated within this module.
    """

    def __init__(self):
        self._name = None
        self._parent = None
        self._submodules = []

    def _get_full_scope(self):
        """Return a list of scope names from the root down to this module.

        This is used for creating hierarchical names for VCD dumping and
        debugging.

        Returns
        -------
        list of str
            A list of hierarchical scope names.
        """
        names = []
        mod = self
        while mod is not None:
            names.append(mod._name)
            mod = mod._parent
        names.reverse()
        return names


class TestBench(Module):
    """Convenience subclass representing the top-level simulation harness.

    A `TestBench` is the root of the module hierarchy. It is typically
    used to instantiate the device-under-test (DUT), provide stimulus
    to its inputs, and check its outputs.
    """
    __test__ = False
    pass
