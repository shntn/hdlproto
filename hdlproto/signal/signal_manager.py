from typing import TYPE_CHECKING

from .signal import Input, Output, Wire, Reg
from hdlproto.event.event import _Event, _EventType, _EventSource
from hdlproto.state import _SignalType, Edge
from hdlproto.error import SignalInvalidAccess, SignalWriteConflict

if TYPE_CHECKING:
    from .signal_list import _SignalList

_SIGNAL_TABLE = [[False, Input, _SignalType.INPUT],
                 [False, Output, _SignalType.OUTPUT],
                 [False, Wire, _SignalType.WIRE],
                 [False, Reg, _SignalType.REG],
                 [True, Wire, _SignalType.EXTERNAL]]


class _SignalManager:

    def __init__(self, _signal_list: "_SignalList | None" = None):
        self._signal_list = _signal_list
        self._signal_writers = {}

    def _handle_event(self, _event: _Event):
        if _event._event_type == _EventType.SIGNAL_WRITE_TRACKED:
            self._handle_signal_write_tracked(_event)

    def _store_stabled_value_for_trigger(self):
        signals = self._signal_list._of_type((_SignalType.WIRE, _SignalType.INPUT, _SignalType.OUTPUT))
        signals._execute("_store_stabled_value_for_trigger")

    def _is_edge_match_expected(self, signal, edge: Edge):
        return signal._is_write() and signal._is_edge_match_expected(edge)

    def _store_stabled_value_for_write(self):
        self._signal_list._execute("_store_stabled_value_for_write")

    def _is_write(self):
        return any(self._signal_list._execute("_is_write"))

    def _update_externals(self):
        signals = self._signal_list._of_type(_SignalType.EXTERNAL)
        is_unstable = any(signals._execute("_update"))
        return is_unstable

    def _update_wires(self):
        signals = self._signal_list._of_type((_SignalType.WIRE, _SignalType.INPUT, _SignalType.OUTPUT))
        is_unstable = any(signals._execute("_update"))
        return is_unstable

    def _update_regs(self):
        signals = self._signal_list._of_type(_SignalType.REG)
        is_unstable = any(signals._execute("_update"))
        return is_unstable

    def _handle_signal_write_tracked(self, event: _Event):
        function_info = event._info.get("function_info")
        signal_name = event._info.get("signal_name")
        signal_module_path = event._info.get("signal_module_path")

        if not function_info:
            # TestBenchなどの外部からの直接ドライブは監視対象外
            return

        signal_label = self._format_signal_label(signal_module_path, signal_name)
        function_phase = function_info.get("source_type")

        self._validate_access_rules(event._source_type, function_phase, signal_label)
        self._ensure_no_conflict(signal_label, function_info)
        self._signal_writers[signal_label] = {
            "function_name": function_info.get("function_name"),
            "module_path": function_info.get("module_path"),
            "source_": function_phase,
        }

    def _validate_access_rules(self, signal_source: _EventSource, function_phase: _EventSource | None, signal_label: str):
        if signal_source == _EventSource.REG and function_phase == _EventSource.ALWAYS_COMB:
            raise SignalInvalidAccess(f"Reg {signal_label} cannot be written inside always_comb.")
        wire_sources = (_EventSource.WIRE, _EventSource.INPUT, _EventSource.OUTPUT, _EventSource.EXTERNAL)
        ff_phases = (_EventSource.ALWAYS_FF, _EventSource.ALWAYS_FF_POS, _EventSource.ALWAYS_FF_NEG)
        if signal_source in wire_sources and function_phase in ff_phases:
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
