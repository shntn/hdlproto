from typing import TYPE_CHECKING

from hdlproto.event import Event, EventType, EventSource

if TYPE_CHECKING:
    from hdlproto.signal import SignalManager


class FunctionManager:
    def __init__(
            self,
            signal_manager: "SignalManager | None" = None,
    ):
        self.signal_manager = signal_manager
        self.always_comb_functions = []
        self.always_ff_functions = []
        self.always_ff_functions_triggered = []
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

    def evaluate_always_ff(self):
        for func in self.always_ff_functions_triggered:
            func()
        self.always_ff_functions_triggered.clear()

    def evaluate_always_comb(self):
        for func in self.always_comb_functions:
            func()

    def get_current_function_info(self):
        if not self._current_function:
            return None
        return self._current_function.copy()

    def extract_triggerd_always_ff(self):
        for func in self.always_ff_functions:
            is_triggerd = self._is_always_ff_triggered(func)
            if is_triggerd:
                self.always_ff_functions_triggered.append(func)

    def _is_always_ff_triggered(self, func):
        is_triggered = False
        triggers = getattr(func, '_resolved_triggers', ())
        for trigger in triggers:
            is_triggered |= self.signal_manager.is_edge_match_expected(trigger['signal'], trigger['edge'])
        return is_triggered