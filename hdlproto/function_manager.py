from typing import Callable

from hdlproto.event import Event, EventType, EventSource



class FunctionManager:
    def __init__(self):
        self.always_comb_functions = []
        self.always_ff_functions = []
        self._current_function = None

    def handle_event(self, event: Event):
        if event.event_type == EventType.FUNCTION_START:
            self._current_function = {
                "module": event.info.get("module"),
                "module_path": event.info.get("module_path"),
                "function_name": event.info.get("function_name"),
                "source_type": event.source_type,
            }
        elif event.event_type == EventType.FUNCTION_END:
            self._current_function = None

    def evaluate_always_ff(self, reset=False):
        for func in self.always_ff_functions:
            func(reset)

    def evaluate_always_comb(self):
        for func in self.always_comb_functions:
            func()

    def get_current_function_info(self):
        if not self._current_function:
            return None
        return self._current_function.copy()
