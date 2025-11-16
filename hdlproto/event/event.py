from dataclasses import dataclass, field
from enum import Enum, auto


class _EventType(Enum):
    SIGNAL_WRITE = auto()
    SIGNAL_WRITE_TRACKED = auto()
    FUNCTION_START = auto()
    FUNCTION_END = auto()

class _EventSource(Enum):
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
class _Event:
    _event_type: _EventType=None
    _source_type: _EventSource=None
    _info: dict = field(default_factory=dict)
