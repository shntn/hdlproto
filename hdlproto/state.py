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
    """Specifies a rising or falling edge.

    Used as a trigger for the `@always_ff` decorator.
    """
    POS = auto()    #: Rising edge
    NEG = auto()    #: Falling edge

class _ModuleType(Enum):
    MODULE = auto()
    TESTBENCH = auto()
