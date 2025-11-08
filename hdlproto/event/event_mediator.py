from typing import TYPE_CHECKING, Callable
from .event import Event, EventType

if TYPE_CHECKING:
    from hdlproto.signal import SignalManager
    from hdlproto.function_manager import FunctionManager
    from hdlproto.module import ModuleManager
    from hdlproto.simulator import Simulator, SimulationExector


class EventMediator:
    def __init__(
        self,
        signal_manager: "SignalManager | None" = None,
        function_manager: "FunctionManager | None" = None,
        module_manager: "ModuleManager | None" = None,
        simulation_exector: "SimulationExector | None" = None,
        handler: Callable | None = None,
    ):
        self.signal_manager = signal_manager
        self.function_manager = function_manager
        self.module_manager = module_manager
        self.simulation_exector = simulation_exector
        self.handler = handler

    def handle_event(self, event):
        if event.event_type == EventType.SIGNAL_WRITE:
            self._handle_signal_write(event)

    def _handle_signal_write(self, event: Event):
        if not self.handler and not self.signal_manager:
            return
        info = dict(event.info) if event.info else {}
        function_info = None
        if self.function_manager:
            function_info = self.function_manager.get_current_function_info()
        info["function_info"] = function_info
        tracked_event = Event(
            event_type=EventType.SIGNAL_WRITE_TRACKED,
            source_type=event.source_type,
            info=info
        )
        if self.handler:
            self.handler(tracked_event)
