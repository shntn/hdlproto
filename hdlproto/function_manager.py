from typing import TYPE_CHECKING

from .event.event import _Event, _EventType, _EventSource

if TYPE_CHECKING:
    from hdlproto.signal.signal_manager import _SignalManager


class _FunctionManager:
    def __init__(
            self,
            _signal_manager: "_SignalManager | None" = None,
    ):
        self._signal_manager = _signal_manager
        self._always_comb_functions = []
        self._always_ff_functions = []
        self._always_ff_functions_triggered = []
        self._current_function = None

    def _handle_event(self, _event: _Event):
        if _event._event_type == _EventType.FUNCTION_START:
            self._current_function = {
                "module": _event._info.get("module"),
                "module_path": _event._info.get("module_path"),
                "function_name": _event._info.get("function_name"),
                "source_type": _event._source_type,
            }
        elif _event._event_type == _EventType.FUNCTION_END:
            self._current_function = None

    def _evaluate_always_ff(self):
        for func in self._always_ff_functions_triggered:
            func()
        self._always_ff_functions_triggered.clear()

    def _evaluate_always_comb(self):
        for func in self._always_comb_functions:
            func()

    def _get_current_function_info(self):
        if not self._current_function:
            return None
        return self._current_function.copy()

    def _extract_triggerd_always_ff(self):
        for func in self._always_ff_functions:
            is_triggerd = self._is_always_ff_triggered(func)
            if is_triggerd:
                self._always_ff_functions_triggered.append(func)

    def _is_always_ff_triggered(self, func):
        is_triggered = False
        triggers = getattr(func, '_resolved_triggers', ())
        for trigger in triggers:
            is_triggered |= self._signal_manager._is_edge_match_expected(trigger['signal'], trigger['edge'])
        return is_triggered