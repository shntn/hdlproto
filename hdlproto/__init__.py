"""HDLproto package"""
from .signal import Wire, Reg, Input, Output
from .module import Module, always_ff, always_comb
from .testbench import TestBench, testcase
from .simulator import Simulator
from .simconfig import SimConfig
from .error import HDLProtoError, SignalError, SignalWriteConflict, SignalInvalidAccess, SignalUnstableError, \
    ModuleError, SimulationError

__all__ = [
    "Wire",
    "Reg",
    "Input",
    "Output",
    "Module",
    "always_ff",
    "always_comb",
    "TestBench",
    "testcase",
    "Simulator",
    "SimConfig"
]
__version__ = "0.1.0"
