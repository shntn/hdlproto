from functools import wraps
from hdlproto.event.event import _Event, _EventType, _EventSource
from hdlproto.state import Edge


def _create_always_decorator(_type_str: str, _source_type: _EventSource):
    """
    alwaysデコレータを生成するためのファクトリ関数。
    """
    def _decorator(func):
        @wraps(func)
        def _wrapper(self, *args, **kwargs):
            event_handler = getattr(_wrapper, '_handler', None)
            module_path = getattr(_wrapper, '_hdlproto_module_path', None)
            if module_path is None:
                module_path = getattr(self, "module_path", None)
            func_name = getattr(_wrapper, '_hdlproto_func_name', func.__name__)

            if event_handler:
                start_event = _Event(
                    _event_type=_EventType.FUNCTION_START,
                    _source_type=_source_type,
                    _info={
                        "module": self,
                        "module_path": module_path,
                        "function_name": func_name,
                    }
                )
                event_handler(start_event)

            try:
                result = func(self, *args, **kwargs)
            finally:
                if event_handler:
                    end_event = _Event(
                        _event_type=_EventType.FUNCTION_END,
                        _source_type=_source_type,
                        _info={
                            "module": self,
                            "module_path": module_path,
                            "function_name": func_name,
                        }
                    )
                    event_handler(end_event)

            return result

        _wrapper._type = _type_str
        _wrapper._handler = None
        _wrapper._hdlproto_func_name = func.__name__
        return _wrapper
    return _decorator

def always_comb(func):
    """always_comb decorator.

    Creates a decorator to define a function for a combinational circuit.

    Returns
    -------
    callable
        Returns a decorator to be applied to the passed function.

    Raises
    ------
    TypeError
        If the arguments are empty or invalid.
    SignalInvalidAccess
        If writing to a `Reg` in `@always_comb`.
    SignalWriteConflict
        If writing to the same `Wire` from multiple `@always_comb` blocks.

    Examples
    --------
    >>> class MyModule(Module):
    ...     def __init__(self):
    ...         self.a = Wire(init=1)
    ...         self.b = Wire(init=2)
    ...         self.y = Wire(width=4)
    ...         super().__init__()
    ...
    ...     @always_comb
    ...     def logic(self):
    ...         # Full addition
    ...         self.y.w = self.a.w + self.b.w
    ...         # Read/write bit slice
    ...         self.y[1:0] = self.a[1:0] | self.b[1:0]

    See Also
    --------
    Wire, Input, Output, Module
    """
    return _create_always_decorator('always_comb', _EventSource.ALWAYS_COMB)(func)


def always_ff(*trigger_specs):
    """always_ff decorator.

    Creates a decorator to define a function triggered by a clock edge.
    A function decorated with `always_ff` becomes a sequential circuit.
    You must provide one or two trigger specifications.

    Parameters
    ----------
    *trigger_specs : tuple of (Edge, str)
        Trigger specification for a clock edge or reset edge.
        The specification must be one or two tuples.
        Each tuple has the format `(Edge, signal_name)`.

        - Edge : Either `Edge.POS` (rising) or `Edge.NEG` (falling).
        - signal_name : A string (`str`) indicating the attribute name corresponding to the signal in the module.

    Returns
    -------
    callable
        Returns a decorator to be applied to the passed function.

    Raises
    ------
    TypeError
        If the arguments are empty or invalid.
    SignalInvalidAccess
        If writing to a `Wire` in `@always_ff`.
    SignalWriteConflict
        If writing to the same `Reg` from multiple `@always_ff` blocks.

    Examples
    --------
    >>> class MyModule1(Module):
    ...     def __init__(self, clk):
    ...         self.clk = Input(clk)
    ...         super().__init__()
    ...
    ...     @always_ff((Edge.POS, 'clk'))
    ...     def logic(self):
    ...

    >>> class MyModule2(Module):
    ...     def __init__(self, clk, reset):
    ...         self.clk = Input(clk)
    ...         self.reset = Input(reset)
    ...         super().__init__()
    ...
    ...     @always_ff((Edge.POS, 'clk'), (Edge.NEG, 'reset'))
    ...     def logic(self):

    Notes
    -----
    * Only non-blocking assignments are possible. Blocking assignments are not supported.

    See Also
    --------
    Reg, Module, Edge
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
        normalized.append({"edge": edge_value, "signal_name": signal_name})

    primary_edge = normalized[0]["edge"]
    source_type = _EventSource.ALWAYS_FF_POS if primary_edge == Edge.POS else _EventSource.ALWAYS_FF_NEG

    def _decorator(func):
        wrapper = _create_always_decorator('always_ff', source_type)(func)
        wrapper._triggers = tuple(normalized)
        return wrapper

    return _decorator


class Module:
    """Base class for hardware modules, equivalent to Verilog's Module.

    Inherit from this class to define your own hardware modules.
    Within the module's `__init__` method, define signals such as `Wire` and `Reg`,
    and other `Module` instances (sub-modules) as attributes.

    After defining all signals and sub-modules, you must call `super().__init__()` at the end.
    This automatically builds the module hierarchy.

    Examples
    --------
    >>> class SubProcessor(Module):
    ...     def __init__(self, clk, data_in, data_out):
    ...         self.clk = Input(clk)
    ...         self.data_in = Input(data_in)
    ...         self.data_out = Output(data_out)
    ...         self.internal_reg = Reg(width=8)
    ...         super().__init__()
    ...
    ...     @always_ff((Edge.POS, 'clk'))
    ...     def seq_logic(self):
    ...         self.internal_reg.r = self.data_in.w
    ...
    ...     @always_comb
    ...     def comb_logic(self):
    ...         self.data_out.w = self.internal_reg.w
    ...
    >>> class TopModule(Module):
    ...     def __init__(self):
    ...         self.clk = Wire()
    ...         self.top_in = Wire(width=8)
    ...         self.top_out = Wire(width=8)
    ...         self.processor = SubProcessor(self.clk, self.top_in, self.top_out)
    ...         super().__init__()

    See Also
    --------
    TestBench, testcase, always_ff, always_comb, Wire, Reg, Input, Output
    """
    def __init__(self):
        self._id = id(self)
        self._parent = None
        self._children = []
        self._class_name = self.__class__.__name__
        self._instance_name = None
        self._module_path = None
        self._make_module_tree()

    @property
    def _is_testbench(self):
        return False

    def _make_module_tree(self):
        for name, mod in self.__dict__.items():
            if isinstance(mod, Module):
                mod._parent = self
                mod._instance_name = name
                self._children.append(mod)

    def _items(self, instance_type):
        if isinstance(instance_type, (tuple, list)):
            instance_type_list = instance_type
        else:
            instance_type_list = [instance_type]
        for name, obj in self.__dict__.items():
            if isinstance(obj, instance_type_list):
                yield name, obj

    def _dir(self):
        for name in dir(self):
            yield name

    def log_clock_start(self, cycle):
        """Hook method called at the start of each clock cycle.

        Can be overridden for debugging and tracing purposes.

        Parameters
        ----------
        cycle : int
            The number of clock cycles elapsed since the start of the simulation.
        """
        pass

    def log_clock_end(self, cycle):
        """Hook method called at the end of each clock cycle.

        Can be overridden for debugging and tracing purposes.

        Parameters
        ----------
        cycle : int
            The number of clock cycles elapsed since the start of the simulation.
        """
        pass
