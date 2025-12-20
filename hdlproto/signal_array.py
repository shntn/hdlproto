from typing import Union, List, Tuple, Optional
from .signal import Wire, Reg, InputWire, OutputWire, OutputReg


def _make_initialized_data(count: int,
                           init: Union[int, List[int], Tuple[int, ...]] = 0) -> List[int]:
    if isinstance(init, (list, tuple)):
        return [init[i] if i < len(init) else 0 for i in range(count)]
    return [init] * count


def _make_signal_array(signal_type: type,
                       init_array: list,
                       width: int) -> list:
    items = [signal_type(init=init_data, width=width) for init_data in init_array]
    return items


def _make_inout_array(signal_type: type,
                      target_array) -> list:
    items = [signal_type(target) for target in target_array]
    return items


class _SignalArray:
    def __init__(self, items: list):
        self._items = items

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            index, bit_slice = key
            return self._items[index][bit_slice]
        return self._items[key]


class WireArray:
    def __init__(self,
                 count: int,
                 width: Optional[int] = 1,
                 init: Optional[Union[int, List[int], Tuple[int, ...]]] = 0):
        init_array = _make_initialized_data(count, init)
        signal_array = _make_signal_array(Wire, init_array, width)
        self._base = _SignalArray(signal_array)

    def _set_array(self, array: list):
        self._base = _SignalArray(array)

    def __len__(self):
        return len(self._base)

    def __iter__(self):
        return iter(self._base)

    def __getitem__(self, key):
        return self._base[key]


class RegArray:
    def __init__(self,
                 count: int,
                 width: Optional[int] = 1,
                 init: Optional[Union[int, List[int], Tuple[int, ...]]] = 0):
        init_array = _make_initialized_data(count, init)
        signal_array = _make_signal_array(Reg, init_array, width)
        self._base = _SignalArray(signal_array)

    def _set_array(self, array: list):
        self._base = _SignalArray(array)

    def __len__(self):
        return len(self._base)

    def __iter__(self):
        return iter(self._base)

    def __getitem__(self, key):
        return self._base[key]


class InputWireArray:
    def __init__(self, target_array: WireArray):
        input_array = _make_inout_array(InputWire, target_array)
        self._base = _SignalArray(input_array)

    def _set_array(self, array: list):
        self._base = _SignalArray(array)

    def __iter__(self):
        return iter(self._base)

    def __len__(self):
        return len(self._base)

    def __getitem__(self, key) -> InputWire:
        return self._base[key]


class OutputWireArray:
    def __init__(self, target_array: WireArray):
        output_array = _make_inout_array(OutputWire, target_array)
        self._base = _SignalArray(output_array)

    def _set_array(self, array: list):
        self._base = _SignalArray(array)

    def __iter__(self):
        return iter(self._base)

    def __len__(self):
        return len(self._base)

    def __getitem__(self, key) -> OutputWire:
        return self._base[key]


class OutputRegArray:
    def __init__(self, target_array: RegArray):
        output_array = _make_inout_array(OutputReg, target_array)
        self._base = _SignalArray(output_array)

    def _set_array(self, array: list):
        self._base = _SignalArray(array)

    def __iter__(self):
        return iter(self._base)

    def __len__(self):
        return len(self._base)

    def __getitem__(self, key) -> OutputReg:
        return self._base[key]
