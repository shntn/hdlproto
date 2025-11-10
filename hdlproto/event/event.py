from dataclasses import dataclass, field
from enum import Enum, auto


class EventType(Enum):
    SIGNAL_WRITE = auto()
    SIGNAL_WRITE_TRACKED = auto()
    FUNCTION_START = auto()
    FUNCTION_END = auto()

class EventSource(Enum):
    WIRE = auto()
    REG = auto()
    INPUT = auto()
    OUTPUT = auto()
    EXTERNAL = auto()
    FUNCTION = auto()
    ALWAYS_COMB = auto()
    ALWAYS_FF = auto()
    ALWAYS_FF_POS = auto()
    ALWAYS_FF_NEG = auto()

@dataclass
class Event:
    event_type: EventType=None
    source_type: EventSource=None
    info: dict = field(default_factory=dict)
