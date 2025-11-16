from typing import TYPE_CHECKING, Callable
from .event import _Event, _EventType

if TYPE_CHECKING:
    from hdlproto.signal.signal_manager import _SignalManager
    from hdlproto.function_manager import _FunctionManager
    from hdlproto.module.module_manager import _ModuleManager
    from hdlproto.simulator import Simulator, _SimulationExector


class _EventMediator:
    def __init__(
        self,
        _signal_manager: "_SignalManager | None" = None,
        _function_manager: "_FunctionManager | None" = None,
        _module_manager: "_ModuleManager | None" = None,
        _simulation_exector: "_SimulationExector | None" = None,
        _handler: Callable | None = None,
    ):
        self._signal_manager = _signal_manager
        self._function_manager = _function_manager
        self._module_manager = _module_manager
        self._simulation_exector = _simulation_exector
        self._handler = _handler

    def _handle_event(self, event):
        if event._event_type == _EventType.SIGNAL_WRITE:
            self._handle_signal_write(event)

    def _handle_signal_write(self, event: _Event):
        if not self._handler and not self._signal_manager:
            return
        info = dict(event._info) if event._info else {}
        function_info = None
        if self._function_manager:
            function_info = self._function_manager._get_current_function_info()
        info["function_info"] = function_info
        tracked_event = _Event(
            _event_type=_EventType.SIGNAL_WRITE_TRACKED,
            _source_type=event._source_type,
            _info=info
        )
        if self._handler:
            self._handler(tracked_event)
