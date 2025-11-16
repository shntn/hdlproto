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

always_comb = _create_always_decorator('always_comb', _EventSource.ALWAYS_COMB)


def always_ff(*trigger_specs):
    """always_ff デコレータ。必ず (Edge, signal) タプルを渡す。"""

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
        pass

    def log_clock_end(self, cycle):
        pass
