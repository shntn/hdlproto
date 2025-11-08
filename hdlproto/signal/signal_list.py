from dataclasses import dataclass
from .signal import Wire, Reg, Input, Output
from hdlproto.state import SignalType


@dataclass
class SignalContainer:
    signal: (Wire | Reg | Input | Output)
    info: dict


class SignalList:
    def __init__(self, signals: list[SignalContainer]|None=None):
        if signals:
            self._signals = signals
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

    def filtered(self, filters: dict):
        result = []
        for container in self._signals:
            match = True
            for key, value in filters.items():
                val = container.info.get(key)
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
        return SignalList(result)

    def append(self, signal: (Wire | Reg | Input | Output), info: dict):
        container = SignalContainer(signal, info)
        self._signals.append(container)

    def of_type(self, signal_type: SignalType | tuple[SignalType, ...]):
        return self.filtered({"signal_type": signal_type})

    def execute(self, command: str):
        results = []
        for container in self._signals:
            if hasattr(container.signal, command):
                results.append(getattr(container.signal, command)())
            else:
                raise AttributeError(f"Signal {container.signal} has no attribute {command}.")
        return results
