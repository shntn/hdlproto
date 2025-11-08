from typing import TYPE_CHECKING

from .signal import Input, Output, Wire, Reg
from hdlproto.event import Event, EventType, EventSource
from hdlproto.state import SignalType
from hdlproto.error import SignalInvalidAccess, SignalWriteConflict

if TYPE_CHECKING:
    from .signal_list import SignalList

SIGNAL_TABLE = [[False, Input, SignalType.INPUT],
                [False, Output, SignalType.OUTPUT],
                [False, Wire, SignalType.WIRE],
                [False, Reg, SignalType.REG],
                [True, Wire, SignalType.EXTERNAL]]


class SignalManager:

    def __init__(self, signal_list: "SignalList | None" = None):
        self.signal_list = signal_list
        self._signal_writers = {}

    def handle_event(self, event: Event):
        if event.event_type == EventType.SIGNAL_WRITE_TRACKED:
            self._handle_signal_write_tracked(event)

    def update_externals(self):
        signals = self.signal_list.of_type(SignalType.EXTERNAL)
        is_unstable = any(signals.execute("update"))
        return is_unstable

    def update_wires(self):
        signals = self.signal_list.of_type((SignalType.WIRE, SignalType.INPUT, SignalType.OUTPUT))
        is_unstable = any(signals.execute("update"))
        return is_unstable

    def update_regs(self):
        signals = self.signal_list.of_type(SignalType.REG)
        is_unstable = any(signals.execute("update"))
        return is_unstable

    def _handle_signal_write_tracked(self, event: Event):
        function_info = event.info.get("function_info")
        signal_name = event.info.get("signal_name")
        signal_module_path = event.info.get("signal_module_path")

        if not function_info:
            # TestBenchなどの外部からの直接ドライブは監視対象外
            return

        signal_label = self._format_signal_label(signal_module_path, signal_name)
        function_phase = function_info.get("source_type")

        self._validate_access_rules(event.source_type, function_phase, signal_label)
        self._ensure_no_conflict(signal_label, function_info)
        self._signal_writers[signal_label] = {
            "function_name": function_info.get("function_name"),
            "module_path": function_info.get("module_path"),
            "source_type": function_phase,
        }

    def _validate_access_rules(self, signal_source: EventSource, function_phase: EventSource | None, signal_label: str):
        if signal_source == EventSource.REG and function_phase == EventSource.ALWAYS_COMB:
            raise SignalInvalidAccess(f"Reg {signal_label} cannot be written inside always_comb.")
        wire_sources = (EventSource.WIRE, EventSource.INPUT, EventSource.OUTPUT, EventSource.EXTERNAL)
        if signal_source in wire_sources and function_phase == EventSource.ALWAYS_FF:
            raise SignalInvalidAccess(f"Wire/Input/Output {signal_label} cannot be written inside always_ff.")

    def _ensure_no_conflict(self, signal_label: str, function_info: dict):
        existing = self._signal_writers.get(signal_label)
        if not existing:
            return
        is_same_function = (
            existing.get("function_name") == function_info.get("function_name") and
            existing.get("module_path") == function_info.get("module_path")
        )
        if not is_same_function:
            prev = f"{existing.get('module_path')}::{existing.get('function_name')}"
            now = f"{function_info.get('module_path')}::{function_info.get('function_name')}"
            raise SignalWriteConflict(f"Signal {signal_label} already driven by {prev}, conflicting with {now}.")

    @staticmethod
    def _format_signal_label(module_path: str | None, signal_name: str | None) -> str:
        if module_path and signal_name:
            return f"{module_path}.{signal_name}"
        return signal_name or "<unknown_signal>"
