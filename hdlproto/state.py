from enum import Enum, auto


class SimulationState(Enum):
    IDLE = auto()
    ALWAYS_FF = auto()
    ALWAYS_COMB = auto()


class SignalType(Enum):
    WIRE = auto()
    REG = auto()
    INPUT = auto()
    OUTPUT = auto()
    EXTERNAL = auto()

class Edge(Enum):
    POS = auto()
    NEG = auto()

class ModuleType(Enum):
    MODULE = auto()
    TESTBENCH = auto()
