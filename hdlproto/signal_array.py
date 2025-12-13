from typing import Union, List, Tuple, Optional
from .signal import Wire, Reg


class _SignalArray:
    """A container for managing an array of signals (Wire, Reg, or Port).

    This class allows creating and accessing signals as a list, while enabling
    the EnvironmentBuilder to register them individually with indexed names
    (e.g., 'mem[0]', 'mem[1]').
    """

    def __init__(self,
                 count: int,
                 signal_type: type,
                 width: Optional[int] = 1,
                 init: Optional[Union[int, List[int], Tuple[int, ...]]] = None,
                 **kwargs):
        """
        Parameters
        ----------
        count : int
            Number of elements in the array.
        signal_type : type
            The class to instantiate (Wire, Reg, Input, Output).
        init : int or list or tuple, optional
            Initial value(s). Can be a single integer (applied to all)
            or a list/tuple of integers (applied per index).
        **kwargs : dict
            Arguments to pass to the signal constructor (e.g., width=8).

        Examples
        --------
        >>> self.mem = _SignalArray(16, Reg, width=8)
        >>> self.mem[0].r = 10
        """
        init_data = init if init is not None else 0
        self._items = []
        for i in range(count):
            if isinstance(init_data, (list, tuple)):
                val = init_data[i] if i < len(init_data) else 0
            else:
                val = init_data
            self._items.append(signal_type(init=val, width=width, **kwargs))

    def __getitem__(self, key):
        if isinstance(key, tuple):
            index, bit_slice = key
            return self._items[index][bit_slice]
        return self._items[key]

    def __setitem__(self, key, value):
        self._items[key] = value

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

class WireArray(_SignalArray):
    """Array of Wire signals."""

    def __init__(self,
                 count: int,
                 width: Optional[int] = 1,
                 init: Optional[Union[int, List[int], Tuple[int, ...]]] = None,
                 **kwargs):
        super().__init__(count, Wire, width=width, init=init, **kwargs)


class RegArray(_SignalArray):
    """Array of Reg signals."""

    def __init__(self,
                 count: int,
                 width: Optional[int] = 1,
                 init: Optional[Union[int, List[int], Tuple[int, ...]]] = None,
                 **kwargs):
        super().__init__(count, Reg, width=width, init=init, **kwargs)