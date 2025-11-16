from typing import TYPE_CHECKING, Callable

from enum import Enum, auto
from .event import _Event, _EventType, _EventSource

if TYPE_CHECKING:
    from .event_mediator import _EventMediator

class _EventDestination(Enum):
    SIGNAL_MANAGER = auto()
    FUNCTION_MANAGER = auto()
    EVENT_MEDIATOR = auto()

_EVENT_ROUTE_MAP = {
    (_EventType.SIGNAL_WRITE, _EventSource.WIRE): (_EventDestination.EVENT_MEDIATOR,),
    (_EventType.SIGNAL_WRITE, _EventSource.REG): (_EventDestination.EVENT_MEDIATOR,),
    (_EventType.SIGNAL_WRITE, _EventSource.INPUT): (_EventDestination.EVENT_MEDIATOR,),
    (_EventType.SIGNAL_WRITE, _EventSource.OUTPUT): (_EventDestination.EVENT_MEDIATOR,),
    (_EventType.SIGNAL_WRITE_TRACKED, _EventSource.WIRE): (_EventDestination.SIGNAL_MANAGER,),
    (_EventType.SIGNAL_WRITE_TRACKED, _EventSource.REG): (_EventDestination.SIGNAL_MANAGER,),
    (_EventType.SIGNAL_WRITE_TRACKED, _EventSource.INPUT): (_EventDestination.SIGNAL_MANAGER,),
    (_EventType.SIGNAL_WRITE_TRACKED, _EventSource.OUTPUT): (_EventDestination.SIGNAL_MANAGER,),
    (_EventType.FUNCTION_START, _EventSource.ALWAYS_COMB): (_EventDestination.FUNCTION_MANAGER,),
    (_EventType.FUNCTION_START, _EventSource.ALWAYS_FF): (_EventDestination.FUNCTION_MANAGER,),
    (_EventType.FUNCTION_START, _EventSource.ALWAYS_FF_POS): (_EventDestination.FUNCTION_MANAGER,),
    (_EventType.FUNCTION_START, _EventSource.ALWAYS_FF_NEG): (_EventDestination.FUNCTION_MANAGER,),
    (_EventType.FUNCTION_END, _EventSource.ALWAYS_COMB): (_EventDestination.FUNCTION_MANAGER,),
    (_EventType.FUNCTION_END, _EventSource.ALWAYS_FF): (_EventDestination.FUNCTION_MANAGER,),
    (_EventType.FUNCTION_END, _EventSource.ALWAYS_FF_POS): (_EventDestination.FUNCTION_MANAGER,),
    (_EventType.FUNCTION_END, _EventSource.ALWAYS_FF_NEG): (_EventDestination.FUNCTION_MANAGER,),
}

class _EventManager:
    def __init__(
            self,
            _event_mediator: "_EventMediator | None" = None,
            _signal_handler: Callable | None = None,
            _function_handler: Callable | None = None,
            _event_mediator_handler: Callable | None = None,
    ):
        self._event_mediator = _event_mediator
        self._signal_handler = _signal_handler
        self._function_handler = _function_handler
        self._event_mediator_handler = _event_mediator_handler

    def _get_instance(self, _destination: _EventDestination):
        mapping = {
            _EventDestination.SIGNAL_MANAGER: self._signal_handler,
            _EventDestination.FUNCTION_MANAGER: self._function_handler,
            _EventDestination.EVENT_MEDIATOR: self._event_mediator_handler,
        }
        return mapping.get(_destination)

    def _handle_event(self, _event: _Event):
        key = (_event._event_type, _event._source_type)
        destinations = _EVENT_ROUTE_MAP.get(key)
        if not destinations:
            return
        for destination in destinations:
            instance = self._get_instance(destination)
            if not instance:
                raise RuntimeError(f"No handler found for destination: {destination}")
            instance(_event)
