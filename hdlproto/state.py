from enum import Enum, auto


class Edge(Enum):
    """Specifies a clock edge type for sequential logic triggers.

    This enumeration is used in `@always_ff` decorators to define whether a
    process should trigger on a rising (`POS`) or falling (`NEG`) edge of a
    clock signal.

    Attributes
    ----------
    POS : Enum
        Represents a positive (rising) edge transition (e.g., 0 to 1).
    NEG : Enum
        Represents a negative (falling) edge transition (e.g., 1 to 0).
    """

    POS = auto()    #: Rising edge
    NEG = auto()    #: Falling edge
