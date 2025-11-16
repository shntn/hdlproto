from dataclasses import dataclass
from .signal import Wire, Reg, Input, Output
from hdlproto.state import _SignalType


@dataclass
class _SignalContainer:
    _signal: (Wire | Reg | Input | Output)
    _info: dict


class _SignalList:
    def __init__(self, _signals: list[_SignalContainer] | None=None):
        if _signals:
            self._signals = _signals
        else:
            self._signals = []
        self._index = 0

    def __iter__(self):
        self._index = 0
        return self

    def __next__(self):
        if self._index < len(self._signals):
            result = self._signals[self._index]
            self._index += 1
            return result
        raise StopIteration

    def _filtered(self, _filters: dict):
        result = []
        for container in self._signals:
            match = True
            for key, value in _filters.items():
                val = container._info.get(key)
                if isinstance(value, (list, tuple)):
                    if val not in value:
                        match = False
                        break
                else:
                    if val != value:
                        match = False
                        break
            if match:
                result.append(container)
        return _SignalList(result)

    def _append(self, _signal: (Wire | Reg | Input | Output), _info: dict):
        container = _SignalContainer(_signal, _info)
        self._signals.append(container)

    def _of_type(self, _signal_type: _SignalType | tuple[_SignalType, ...]):
        return self._filtered({"signal_type": _signal_type})

    def _execute(self, _command: str):
        results = []
        for container in self._signals:
            if hasattr(container._signal, _command):
                results.append(getattr(container._signal, _command)())
            else:
                raise AttributeError(f"Signal {container._signal} has no attribute {_command}.")
        return results
