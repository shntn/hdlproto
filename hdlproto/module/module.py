from functools import wraps
from hdlproto.event import Event, EventType, EventSource


def _create_always_decorator(type_str: str, source_type: EventSource):
    """
    alwaysデコレータを生成するためのファクトリ関数。
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            event_handler = getattr(wrapper, 'handler', None)
            module_path = getattr(wrapper, '_hdlproto_module_path', None)
            if module_path is None:
                module_path = getattr(self, "module_path", None)
            func_name = getattr(wrapper, '_hdlproto_func_name', func.__name__)

            if event_handler:
                start_event = Event(
                    event_type=EventType.FUNCTION_START,
                    source_type=source_type,
                    info={
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
                    end_event = Event(
                        event_type=EventType.FUNCTION_END,
                        source_type=source_type,
                        info={
                            "module": self,
                            "module_path": module_path,
                            "function_name": func_name,
                        }
                    )
                    event_handler(end_event)

            return result

        wrapper.type = type_str
        wrapper.handler = None
        wrapper._hdlproto_func_name = func.__name__
        return wrapper
    return decorator

always_comb = _create_always_decorator('always_comb', EventSource.ALWAYS_COMB)


def always_ff(_func=None, *, edge: str = 'pos'):
    def decorator(func):
        source_type = EventSource.ALWAYS_FF_POS if edge == 'pos' else EventSource.ALWAYS_FF_NEG
        wrapper = _create_always_decorator('always_ff', source_type)(func)
        wrapper._hdlproto_ff_edge = edge
        return wrapper

    if _func is not None and callable(_func):
        return decorator(_func)
    return decorator


class Module:
    def __init__(self):
        self.id = id(self)
        self.parent = None
        self.children = []
        self.class_name = self.__class__.__name__
        self.instance_name = None
        self.module_path = None
        self.make_module_tree()

    @property
    def is_testbench(self):
        return False

    def make_module_tree(self):
        for name, mod in self.__dict__.items():
            if isinstance(mod, Module):
                mod.parent = self
                mod.instance_name = name
                self.children.append(mod)

    def items(self, instance_type):
        if isinstance(instance_type, (tuple, list)):
            instance_type_list = instance_type
        else:
            instance_type_list = [instance_type]
        for name, obj in self.__dict__.items():
            if isinstance(obj, instance_type_list):
                yield name, obj

    def dir(self):
        for name in dir(self):
            yield name

    def log_clock_start(self, cycle):
        pass

    def log_clock_end(self, cycle):
        pass
