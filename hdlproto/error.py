class HDLProtoError(Exception):
    """Base class for all HDLproto exceptions."""

# --- Signal関連 ---
class SignalError(HDLProtoError):
    """Base class for signal-related errors."""

class SignalWriteConflict(SignalError):
    """Raised when multiple drivers attempt to assign different values."""

class SignalInvalidAccess(SignalError):
    """Raised when a signal is accessed incorrectly (e.g., type mismatch)."""

class SignalUnstableError(SignalError):
    """Raised when a combinational signal fails to stabilize within the allowed iterations."""

# --- Module関連 ---
class ModuleError(HDLProtoError):
    """Base class for module-related errors."""

# --- シミュレーション関連 ---
class SimulationError(HDLProtoError):
    """Base class for simulation control errors."""
