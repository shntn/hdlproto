class HDLProtoError(Exception):
    """Base class for all exceptions raised by the hdlproto library."""
    pass


# --- Signal related ---
class SignalError(HDLProtoError):
    """Base class for errors related to signal access or behavior."""
    pass


class SignalWriteConflict(SignalError):
    """Raised when multiple processes attempt to drive the same wire.

    In HDL, a wire can only be driven by one source. This exception is
    raised when the simulator detects that two or more `@always_comb` or
    `@always_ff` blocks are trying to write to the same `Wire` or `Output`
    in the same simulation step.
    """
    pass


class SignalInvalidAccess(SignalError):
    """Raised when a signal is accessed or written to improperly.

    This error occurs when an operation violates the rules of the simulation
    model.

    Examples
    --------
    - Writing to a `Reg` from within an `@always_comb` block.
    - Writing to a `Wire` from within an `@always_ff` block.
    """
    pass


class SignalUnstableError(SignalError):
    """Raised when combinational logic does not stabilize.

    This error indicates a probable combinational loop in the design.
    The simulator will stop after a fixed number of delta cycles if the
    values of wires are still changing, raising this exception to prevent
    an infinite loop.
    """
    pass