from typing import Callable
from hdlproto.event.event import _Event, _EventType, _EventSource
from hdlproto.state import Edge

class _SignalBase:
    def __init__(self, init=None):
        self._prev_value_for_trigger = init
        self._prev_value_for_write = init
        self._value = init
        self._pending = None

class _SignalBitOperator:
    def __init__(self, _width=1):
        self._width = _width

    def _get_bit(self, value, start, stop):
        mask = self.__make_mask(start, stop)
        masked_value = value & mask
        slice_value = self.__unshift_value(start, stop, masked_value)
        return slice_value

    def _set_bit(self, value, start, stop, new_value):
        mask = self.__make_mask(start, stop)
        shifted_new_value = self.__shift_value(start, stop, new_value)
        masked_new_value = shifted_new_value & mask
        masked_value = value & ~mask
        marged_value = masked_value | masked_new_value
        return marged_value

    @staticmethod
    def __unshift_value(start, stop, value):
        start, stop = (start, stop) if start < stop else (stop, start)
        return value >> start

    @staticmethod
    def __shift_value(start, stop, value):
        start, stop = (start, stop) if start < stop else (stop, start)
        return value << start

    @staticmethod
    def __make_mask(start, stop):
        start, stop = (start, stop) if start < stop else (stop, start)
        width = stop - start + 1
        mask = 2**width - 1
        shifted_mask = mask << start
        return shifted_mask


class _SignalSignOperator:
    def __init__(self, _sign=False, _width=1):
        self.sign = _sign
        self.width = _width

    def _to_integer(self, value):
        return self.__make_integer(value)

    def _to_bits_data(self, value):
        return self.__to_unsigned(value)

    def __make_integer(self, value):
        if self.sign:
            return self.__to_signed(value)
        else:
            return self.__to_unsigned(value)

    def __to_signed(self, value):
        if not isinstance(value, int):
            return value
        width = self.width if self.width is not None else 64
        sign_bit = 1 << (width - 1)
        return (value & (sign_bit - 1)) - (value & sign_bit)

    def __to_unsigned(self, value):
        if not isinstance(value, int):
            return value
        width = self.width if self.width is not None else 64
        mask = 2**width - 1
        limited_unsigned = value & mask
        return limited_unsigned


class _SignalEvents:
    def __init__(self):
        self._handler = None

    def _fire(self, _event: _Event):
        self._handler(_event)


class _Signal:
    def __init__(self, _sign=False, _width=1, _init=0):
        if _sign and _width == 1:
            raise ValueError("Signal width must be greater than 1.")
        self._base = _SignalBase(_init)
        self._bits = _SignalBitOperator(_width)
        self._sign = _SignalSignOperator(_sign, _width)
        self._event = _SignalEvents()

    def _get(self):
        raw_value = self._base._value
        return self._sign._to_integer(raw_value)

    def _set(self, value):
        nbits_value = self._sign._to_bits_data(value)
        value_changed = nbits_value != self._base._value
        if value_changed:
            self._base._pending = nbits_value
        else:
            self._base._pending = None
        return value_changed

    def _get_bit(self, start, stop):
        raw_value = self._base._value
        if not isinstance(raw_value, int):
            raise TypeError("Invalid argument type.")
        bits_value = self._bits._get_bit(raw_value, start, stop)
        return self._sign._to_integer(bits_value)

    def _set_bit(self, start, stop, value):
        raw_value = self._base._value
        if not isinstance(raw_value, int) or not isinstance(value, int):
            raise TypeError("Invalid argument type.")
        bits_value = self._bits._set_bit(raw_value, start, stop, value)
        value_changed = bits_value != self._base._value
        if value_changed:
            self._base._pending = bits_value
        else:
            self._base._pending = None
        return value_changed

    def _store_stabled_value_for_trigger(self):
        self._base._prev_value_for_trigger = self._base._value

    def _is_edge_match_expected(self, _edge: Edge):
        posedge = not self._base._prev_value_for_trigger and self._base._value
        negedge = self._base._prev_value_for_trigger and not self._base._value
        return (posedge and _edge == Edge.POS) or (negedge and _edge == Edge.NEG)

    def _store_stabled_value_for_write(self):
        self._base._prev_value_for_write = self._base._value

    def _is_write(self):
        return self._base._value != self._base._prev_value_for_write

    def _update(self):
        is_unstable = self._base._pending is not None
        if is_unstable:
            self._base._value = self._base._pending
            self._base._pending = None
        return is_unstable

    def _fire(self, _event: _Event):
        self._event._fire(_event)

    def _fire_write_event(self, _source_type: _EventSource, signal_obj, _value_changed: bool):
        if not self._event._handler:
            return
        module_path = getattr(signal_obj._context, "_module_path", None)
        signal_name = getattr(signal_obj._context, "_name", None)
        event = _Event(
            _event_type=_EventType.SIGNAL_WRITE,
            _source_type=_source_type,
            _info={
                "signal": signal_obj,
                "value_changed": _value_changed,
                "signal_name": signal_name,
                "signal_module_path": module_path,
            }
        )
        self._fire(event)


class _SignalContext:
    __slots__ = ("_name", "_signal_type", "_module", "_module_path")

    def __init__(self, signal):
        self._name = None
        self._signal_type = None
        self._module = None
        self._module_path = None


class Wire:
    """
    A multi-bit signal that constitutes a combinational circuit.

    A signal equivalent to HDL's `wire`, which is only allowed to be assigned within an `@always_comb` block.
    It is used by instantiating it within the `__init__` of a `Module` / `TestBench`.

    Parameters
    ----------
    sign : bool, optional
        `True` if handling a signed signal.
        Default: `False` (unsigned)
    width : int, optional
        Bit width. Default: 1.
        `width >= 2` is required if `sign=True`.
    init : int, optional
        Initial value. Default: 0.

    Raises
    ------
    ValueError
        If `sign=True` and `width <= 1`.

    Examples
    --------
    >>> class MyModule(Module):
    ...     def __init__(self):
    ...         self.a = Wire(init=1)
    ...         self.b = Wire(init=2)
    ...         self.y = Wire(width=4)
    ...         super().__init__()
    ...
    ...     @always_comb
    ...     def logic(self):
    ...         # Full addition
    ...         self.y.w = self.a.w + self.b.w
    ...         # Read/write bit slice
    ...         self.y[1:0] = self.a[1:0] | self.b[1:0]

    See Also
    --------
    Input, Output, Module, always_comb
    """
    __slots__ = ("_signal", "_context")

    def __init__(self, sign=False, width=1, init=0):
        self._signal = _Signal(sign, width, init)
        self._context = _SignalContext(self._signal)

    @property
    def w(self):
        """Current value (read/write).

        Reading is done by property access `value = self.foo.w`.
        Writing is done with a setter like `self.foo.w = value`.

        Returns
        -------
        int
            Current value (read).

        Raises
        ------
        SignalInvalidAccess
            If writing to the `w` property outside of an `@always_comb` context.
        SignalWriteConflict
            If writing a value from multiple `@always_comb` blocks.
        SignalUnstableError
            If the change in the `Wire` signal does not converge.
        """
        return self._signal._get()

    @w.setter
    def w(self, value):
        value_changed = self._signal._set(value)
        self._signal._fire_write_event(_EventSource.WIRE, self, value_changed)

    def __getitem__(self, key):
        """Reads a specific bit or slice.

        Reading a specific bit is done like `value = self.foo[2]`.
        Reading a slice is done like `value = self.foo[7:4]`.

        Parameters
        ----------
        key : int or slice
            The bit position (int) or slice range (slice) to read.

        Returns
        -------
        int
            The value of the specified bit or slice.

        Raises
        ------
        TypeError
            If `key` is not an int or slice.

        Examples
        --------
        >>> @always_comb
        >>> def logic(self):
        ...     lower = self.foo[1:0]    # Read lower 2 bits
        ...     bit3 = self.foo[3]       # Read a single bit

        Notes
        -----
        * When specifying a slice value, both `[msb:lsb]` and `[lsb:msb]` are supported.
        """
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            return self._signal._get_bit(start, stop)
        elif isinstance(key, int):
            return self._signal._get_bit(key, key)
        else:
            raise TypeError("Invalid argument type.")

    def __setitem__(self, key, value):
        """Writes a value to a specific bit or slice of the signal.

        Can only be used inside an `@always_comb` block.
        Writing to a specific bit is done like `self.foo[2] = value`.
        Writing to a slice is done like `self.foo[7:4] = value`.

        Parameters
        ----------
        key : int or slice
            The bit position (int) or slice range (slice) to write to.
        value : int
            The value to write.

        Raises
        ------
        TypeError
            If `key` is not an int or slice.
        SignalInvalidAccess
            If writing outside of an `@always_comb` context.
        SignalWriteConflict
            If writing a value from multiple `@always_comb` blocks.
        SignalUnstableError
            If the change in the `Wire` signal does not converge.

        Examples
        --------
        >>>     @always_comb
        >>>     def logic(self):
        ...         # Read/write bit slice
        ...         self.foo[1:0] = value
        ...         self.foo[2:3] = 3
        ...         self.foo[4] = 1

        Notes
        -----
        * When specifying a slice value, both `[msb:lsb]` and `[lsb:msb]` are supported.
        """
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            value_changed = self._signal._set_bit(start, stop, value)
        elif isinstance(key, int):
            value_changed = self._signal._set_bit(key, key, value)
        else:
            raise TypeError("Invalid argument type.")
        self._signal._fire_write_event(_EventSource.WIRE, self, value_changed)

    def _store_stabled_value_for_trigger(self):
        self._signal._store_stabled_value_for_trigger()

    def _is_edge_match_expected(self, edge: Edge):
        self._signal._is_edge_match_expected(edge)

    def _store_stabled_value_for_write(self):
        self._signal._store_stabled_value_for_write()

    def _is_write(self):
        return self._signal._is_write()

    def _update(self):
        return self._signal._update()


class Reg:
    """
    A multi-bit signal that constitutes a sequential circuit.

    A signal equivalent to HDL's `Reg`, which is only allowed to be assigned within an `@always_ff` block.
    It is used by instantiating it within the `__init__` of a `Module` / `TestBench`.

    Parameters
    ----------
    sign : bool, optional
        `True` if handling a signed signal.
        Default: `False` (unsigned)
    width : int, optional
        Bit width. Default: 1.
        `width >= 2` is required if `sign=True`.
    init : int, optional
        Initial value. Default: 0.

    Raises
    ------
    ValueError
        If `sign=True` and `width <= 1`.

    Examples
    --------
    >>> class MyModule(Module):
    ...     def __init__(self, clk):
    ...         self.clk = Input(clk)
    ...         self.a = Reg(init=1)
    ...         self.b = Reg(init=2)
    ...         self.y = Reg(width=4)
    ...         super().__init__()
    ...
    ...     @always_ff((Edge.POS, 'clk'))
    ...     def logic(self):
    ...         # Full addition
    ...         self.y.r = self.a.r + self.b.r
    ...         # Read/write bit slice
    ...         self.y[1:0] = self.a[1:0] | self.b[1:0]

    Notes
    -----
    * Only non-blocking assignment is supported for writing.
    * The written value is reflected in the current value at the next clock cycle.

    See Also
    --------
    Module, always_ff
    """
    __slots__ = ("_signal", "_context")

    def __init__(self, sign=False, width=1, init=0):
        self._signal = _Signal(sign, width, init)
        self._context = _SignalContext(self._signal)

    @property
    def r(self):
        """Reads the current value of the register and writes the next cycle value (read/write).

        Similar to Verilog's `reg`, reading returns the current value.
        Writing is a non-blocking assignment and schedules an update for the next clock cycle.

        Returns
        -------
        int
            Current value (read).

        Raises
        ------
        SignalInvalidAccess
            If writing to the `r` property outside of an `@always_ff` context.
        SignalWriteConflict
            If writing a value from multiple `@always_ff` blocks.
        SignalUnstableError
            If the change in the `Wire` signal does not converge.
        """
        return self._signal._get()

    @r.setter
    def r(self, value):
        value_changed = self._signal._set(value)
        self._signal._fire_write_event(_EventSource.REG, self, value_changed)

    def __getitem__(self, key):
        """Reads a specific bit or slice.

        Reading a specific bit is done like `value = self.foo[2]`.
        Reading a slice is done like `value = self.foo[7:4]`.

        Parameters
        ----------
        key : int or slice
            The bit position (int) or slice range (slice) to read.

        Returns
        -------
        int
            The value of the specified bit or slice.

        Raises
        ------
        TypeError
            If `key` is not an int or slice.

        Examples
        --------
        >>>     @always_ff((Edge.POS, 'clk'))
        >>>     def logic(self):
        ...         lower = self.foo[1:0]    # Read lower 2 bits
        ...         bit3 = self.foo[3]       # Read a single bit

        Notes
        -----
        * When specifying a slice value, both `[msb:lsb]` and `[lsb:msb]` are supported.
        """
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            return self._signal._get_bit(start, stop)
        elif isinstance(key, int):
            return self._signal._get_bit(key, key)
        else:
            raise TypeError("Invalid argument type.")

    def __setitem__(self, key, value):
        """Writes the next cycle value to a specific bit or slice of the signal.

        Can only be used inside an `@always_ff` block.
        Writing to a specific bit is done like `self.foo[2] = value`.
        Writing to a slice is done like `self.foo[7:4] = value`.

        Parameters
        ----------
        key : int or slice
            The bit position (int) or slice range (slice) to write to.
        value : int
            The value to write.

        Raises
        ------
        TypeError
            If `key` is not an int or slice.
        SignalInvalidAccess
            If writing outside of an `@always_ff` context.
        SignalWriteConflict
            If writing a value from multiple `@always_ff` blocks.
        SignalUnstableError
            If the change in the `Wire` signal does not converge.

        Examples
        --------
        >>>     @always_ff((Edge.POS, 'clk'))
        >>>     def logic(self):
        ...         # Read/write bit slice
        ...         self.foo[1:0] = value
        ...         self.foo[2:3] = 3
        ...         self.foo[4] = 1

        Notes
        -----
        * When specifying a slice value, both `[msb:lsb]` and `[lsb:msb]` are supported.
        """
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            value_changed = self._signal._set_bit(start, stop, value)
        elif isinstance(key, int):
            value_changed = self._signal._set_bit(key, key, value)
        else:
            raise TypeError("Invalid argument type.")
        self._signal._fire_write_event(_EventSource.REG, self, value_changed)

    def _store_stabled_value_for_write(self):
        self._signal._store_stabled_value_for_write()

    def _is_write(self):
        return self._signal._is_write()

    def _update(self):
        return self._signal._update()


class Input:
    """
    A multi-bit signal that constitutes a combinational circuit input from outside a module.

    A signal equivalent to HDL's `wire` that is read-only.
    It is used by instantiating it within the `__init__` of a `Module` / `TestBench`.

    Parameters
    ----------
    wire : Wire
        The `Wire` to be input.

    Examples
    --------
    >>> class MyModule(Module):
    ...     def __init__(self, en):
    ...         self.en = Input(en)
    ...         self.cnt = Reg()
    ...         self.cnt_next = Wire()
    ...         super().__init__()
    ...
    ...     @always_comb
    ...     def logic(self):
    ...         self.cnt_next.w = self.cnt.r
    ...         if self.en.w:
    ...             self.cnt_next.w = self.cnt.r + 1

    See Also
    --------
    Wire, Output, Module, always_comb
    """
    __slots__ = ("_signal", "_context")

    def __init__(self, wire: Wire):
        self._signal = wire._signal
        self._context = _SignalContext(self._signal)

    @property
    def w(self):
        """Current value (read).

        Reading is done by property access `value = self.foo.w`.

        Returns
        -------
        int
            Current value (read).

        Raises
        ------
        AttributeError
            If writing to the signal of `Input`.
        """
        return self._signal._get()

    @w.setter
    def w(self, value):
        raise AttributeError("property 'w' of 'Input' object has no setter")

    def __getitem__(self, key):
        """Reads a specific bit or slice.

        Reading a specific bit is done like `value = self.foo[2]`.
        Reading a slice is done like `value = self.foo[7:4]`.

        Parameters
        ----------
        key : int or slice
            The bit position (int) or slice range (slice) to read.

        Returns
        -------
        int
            The value of the specified bit or slice.

        Raises
        ------
        TypeError
            If `key` is not an int or slice.

        Examples
        --------
        >>> @always_comb
        >>> def logic(self):
        ...     lower = self.foo[1:0]    # Read lower 2 bits
        ...     bit3 = self.foo[3]       # Read a single bit

        Notes
        -----
        * When specifying a slice value, both `[msb:lsb]` and `[lsb:msb]` are supported.
        """
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            return self._signal._get_bit(start, stop)
        elif isinstance(key, int):
            return self._signal._get_bit(key, key)
        else:
            raise TypeError("Invalid argument type.")

    def _store_stabled_value_for_trigger(self):
        self._signal._store_stabled_value_for_trigger()

    def _is_edge_match_expected(self, _edge: Edge):
        return self._signal._is_edge_match_expected(_edge)

    def _store_stabled_value_for_write(self):
        self._signal._store_stabled_value_for_write()

    def _is_write(self):
        return self._signal._is_write()

    def _update(self):
        return False


class Output:
    """
    A multi-bit signal that constitutes a combinational circuit output to outside a module.

    A signal equivalent to HDL's `wire`, which is only allowed to be assigned within an `@always_comb` block.
    It is used by instantiating it within the `__init__` of a `Module` / `TestBench`.

    Parameters
    ----------
    wire : Wire
        The `Wire` to be output.

    Examples
    --------
    >>> class MyModule(Module):
    ...     def __init__(self, out):
    ...         self.cnt = Reg(init=4)
    ...         self.out = Output(out)
    ...         super().__init__()
    ...
    ...     @always_comb
    ...     def logic(self):
    ...         self.out.w = self.cnt.r

    See Also
    --------
    Wire, Input, Module, always_comb
    """
    __slots__ = ("_signal", "_context")

    def __init__(self, wire: Wire):
        self._signal = wire._signal
        self._context = _SignalContext(self._signal)

    @property
    def w(self):
        """Current value (read/write).

        Reading is done by property access `value = self.foo.w`.
        Writing is done with a setter like `self.foo.w = value`.

        Returns
        -------
        int
            Current value (read).

        Raises
        ------
        SignalInvalidAccess
            If writing to the `w` property outside of an `@always_comb` context.
        SignalWriteConflict
            If writing a value from multiple `@always_comb` blocks.
        SignalUnstableError
            If the change in the `Wire` signal does not converge.
        """
        return self._signal._get()

    @w.setter
    def w(self, value):
        value_changed = self._signal._set(value)
        self._signal._fire_write_event(_EventSource.OUTPUT, self, value_changed)

    def __getitem__(self, key):
        """Reads a specific bit or slice.

        Reading a specific bit is done like `value = self.foo[2]`.
        Reading a slice is done like `value = self.foo[7:4]`.

        Parameters
        ----------
        key : int or slice
            The bit position (int) or slice range (slice) to read.

        Returns
        -------
        int
            The value of the specified bit or slice.

        Raises
        ------
        TypeError
            If `key` is not an int or slice.

        Examples
        --------
        >>> @always_comb
        >>> def logic(self):
        ...     lower = self.foo[1:0]    # Read lower 2 bits
        ...     bit3 = self.foo[3]       # Read a single bit

        Notes
        -----
        * When specifying a slice value, both `[msb:lsb]` and `[lsb:msb]` are supported.
        """
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            return self._signal._get_bit(start, stop)
        elif isinstance(key, int):
            return self._signal._get_bit(key, key)
        else:
            raise TypeError("Invalid argument type.")

    def __setitem__(self, key, value):
        """Writes a value to a specific bit or slice of the signal.

        Can only be used inside an `@always_comb` block.
        Writing to a specific bit is done like `self.foo[2] = value`.
        Writing to a slice is done like `self.foo[7:4] = value`.

        Parameters
        ----------
        key : int or slice
            The bit position (int) or slice range (slice) to write to.
        value : int
            The value to write.

        Raises
        ------
        TypeError
            If `key` is not an int or slice.
        SignalInvalidAccess
            If writing outside of an `@always_comb` context.
        SignalWriteConflict
            If writing a value from multiple `@always_comb` blocks.
        SignalUnstableError
            If the change in the `Wire` signal does not converge.

        Examples
        --------
        >>>     @always_comb
        >>>     def logic(self):
        ...         # Read/write bit slice
        ...         self.foo[1:0] = value
        ...         self.foo[2:3] = 3
        ...         self.foo[4] = 1

        Notes
        -----
        * When specifying a slice value, both `[msb:lsb]` and `[lsb:msb]` are supported.
        """
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            value_changed = self._signal._set_bit(start, stop, value)
        elif isinstance(key, int):
            value_changed = self._signal._set_bit(key, key, value)
        else:
            raise TypeError("Invalid argument type.")
        self._signal._fire_write_event(_EventSource.OUTPUT, self, value_changed)

    def _store_stabled_value_for_trigger(self):
        self._signal._store_stabled_value_for_trigger()

    def _is_edge_match_expected(self, edge: Edge):
        self._signal._is_edge_match_expected(edge)

    def _store_stabled_value_for_write(self):
        self._signal._store_stabled_value_for_write()

    def _is_write(self):
        return self._signal._is_write()

    def _update(self):
        return self._signal._update()
