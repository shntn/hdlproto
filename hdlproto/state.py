from enum import Enum, auto


class _SimulationState(Enum):
    IDLE = auto()
    ALWAYS_FF = auto()
    ALWAYS_COMB = auto()


class _SignalType(Enum):
    WIRE = auto()
    REG = auto()
    INPUT = auto()
    OUTPUT = auto()
    EXTERNAL = auto()

class Edge(Enum):
    POS = auto()
    NEG = auto()

class _ModuleType(Enum):
    MODULE = auto()
    TESTBENCH = auto()
