from typing import TYPE_CHECKING, Callable

from enum import Enum, auto
from .event import Event, EventType, EventSource

if TYPE_CHECKING:
    from .event_mediator import EventMediator

class EventDestination(Enum):
    SIGNAL_MANAGER = auto()
    FUNCTION_MANAGER = auto()
    EVENT_MEDIATOR = auto()

_EVENT_ROUTE_MAP = {
    (EventType.SIGNAL_WRITE, EventSource.WIRE): (EventDestination.EVENT_MEDIATOR,),
    (EventType.SIGNAL_WRITE, EventSource.REG): (EventDestination.EVENT_MEDIATOR,),
    (EventType.SIGNAL_WRITE, EventSource.INPUT): (EventDestination.EVENT_MEDIATOR,),
    (EventType.SIGNAL_WRITE, EventSource.OUTPUT): (EventDestination.EVENT_MEDIATOR,),
    (EventType.SIGNAL_WRITE_TRACKED, EventSource.WIRE): (EventDestination.SIGNAL_MANAGER,),
    (EventType.SIGNAL_WRITE_TRACKED, EventSource.REG): (EventDestination.SIGNAL_MANAGER,),
    (EventType.SIGNAL_WRITE_TRACKED, EventSource.INPUT): (EventDestination.SIGNAL_MANAGER,),
    (EventType.SIGNAL_WRITE_TRACKED, EventSource.OUTPUT): (EventDestination.SIGNAL_MANAGER,),
    (EventType.FUNCTION_START, EventSource.ALWAYS_COMB): (EventDestination.FUNCTION_MANAGER,),
    (EventType.FUNCTION_START, EventSource.ALWAYS_FF): (EventDestination.FUNCTION_MANAGER,),
    (EventType.FUNCTION_START, EventSource.ALWAYS_FF_POS): (EventDestination.FUNCTION_MANAGER,),
    (EventType.FUNCTION_START, EventSource.ALWAYS_FF_NEG): (EventDestination.FUNCTION_MANAGER,),
    (EventType.FUNCTION_END, EventSource.ALWAYS_COMB): (EventDestination.FUNCTION_MANAGER,),
    (EventType.FUNCTION_END, EventSource.ALWAYS_FF): (EventDestination.FUNCTION_MANAGER,),
    (EventType.FUNCTION_END, EventSource.ALWAYS_FF_POS): (EventDestination.FUNCTION_MANAGER,),
    (EventType.FUNCTION_END, EventSource.ALWAYS_FF_NEG): (EventDestination.FUNCTION_MANAGER,),
}

class EventManager:
    def __init__(
            self,
            event_mediator: "EventMediator | None" = None,
            signal_handler: Callable | None = None,
            function_handler: Callable | None = None,
            event_mediator_handler: Callable | None = None,
    ):
        self.event_mediator = event_mediator
        self.signal_handler = signal_handler
        self.function_handler = function_handler
        self.event_mediator_handler = event_mediator_handler

    def get_instance(self, destination: EventDestination):
        mapping = {
            EventDestination.SIGNAL_MANAGER: self.signal_handler,
            EventDestination.FUNCTION_MANAGER: self.function_handler,
            EventDestination.EVENT_MEDIATOR: self.event_mediator_handler,
        }
        return mapping.get(destination)

    def handle_event(self, event: Event):
        key = (event.event_type, event.source_type)
        destinations = _EVENT_ROUTE_MAP.get(key)
        if not destinations:
            return
        for destination in destinations:
            instance = self.get_instance(destination)
            if not instance:
                raise RuntimeError(f"No handler found for destination: {destination}")
            instance(event)
