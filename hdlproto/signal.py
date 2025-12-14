from .state import Edge


class _Signal:
    """Base storage element that tracks widths, write staging, and snapshots.

    This is an internal base class and should not be instantiated by users directly.
    It provides the fundamental mechanisms for signal-like behavior, including
    value storage, bit-width, pending writes (for simulation delta cycles),
    and value snapshots for change detection.

    Attributes
    ----------
    _width : int
        The bit width of the signal.
    _value : int
        The current committed value of the signal.
    _pending : int or None
        The new value staged for the next commit. None if no write is pending.
    _snapshot_delta_val : int
        The value of the signal at the last delta snapshot.
    _snapshot_cycle_val : int
        The value of the signal at the last cycle snapshot.
    _snapshot_epsilon_val : int
        The value of the signal at the last epsilon snapshot.
    _sim_context : _SimulationContext
        A reference to the simulation context managing this signal.
    _name : str
        The name of the signal within its module scope.
    _module : Module
        A reference to the module that contains this signal.
    """

    def __init__(self, init: int = 0, width: int = 1):
        """
        Parameters
        ----------
        init : int, optional
            The initial value of the signal, by default 0.
        width : int, optional
            The bit width of the signal, by default 1.
        """
        self._width = width
        self._value = init
        self._pending = None
        self._snapshot_delta_val = 0
        self._snapshot_cycle_val = 0
        self._snapshot_epsilon_val = 0
        self._sim_context = None
        self._name = None
        self._module = None

    @property
    def _is_reg(self) -> bool:
        """Return True if this signal behaves as a register (holds state)."""
        return False

    def _set_context(self, name: str, module, sim_context) -> None:
        """Attach metadata so the signal can resolve scope, module, and simulator.

        Parameters
        ----------
        name : str
            The attribute name of the signal within the module.
        module : Module
            The module instance this signal belongs to.
        sim_context : _SimulationContext
            The simulation context.
        """
        self._name = name
        self._module = module
        self._sim_context = sim_context

    def _write(self, value: int) -> None:
        """Stage a new value (masked to width) for commit at region boundary.

        Parameters
        ----------
        value : int
            The new integer value to stage.
        """
        self._pending = value & ((1 << self._width) - 1)

    def _read_bits(self, key: (slice | int)) -> int:
        """Read a bit or slice using Verilog-style indexing rules.

        Parameters
        ----------
        key : slice or int
            The index or slice to read. Slices are [msb:lsb].

        Returns
        -------
        int
            The integer value of the selected bits.

        Raises
        ------
        TypeError
            If the key is not an int or slice.
        AttributeError
            If the requested bit range is invalid.
        """
        if isinstance(key, slice):
            msb, lsb = key.start, key.stop
        elif isinstance(key, int):
            msb = lsb = key
        else:
            raise TypeError("Invalid argument type")
        if msb < lsb:
            msb, lsb = lsb, msb
        if msb >= self._width or lsb < 0:
            raise AttributeError("Invalid bit range")
        return (self._value >> lsb) & ((1 << (msb - lsb + 1)) - 1)

    def _write_bits(self, key: (slice | int), value: int) -> None:
        """Overwrite selected bits while preserving other staged bits.

        Parameters
        ----------
        key : slice or int
            The index or slice to write to. Slices are [msb:lsb].
        value : int
            The value to write into the selected bits.

        Raises
        ------
        TypeError
            If the key is not an int or slice.
        AttributeError
            If the requested bit range is invalid.
        """
        if isinstance(key, slice):
            msb, lsb = key.start, key.stop
        elif isinstance(key, int):
            msb = lsb = key
        else:
            raise TypeError("Invalid argument type")
        if msb < lsb:
            msb, lsb = lsb, msb
        if msb >= self._width or lsb < 0:
            raise AttributeError("Invalid bit range")
        new_value = self._pending if self._pending is not None else self._value
        new_value = ((value & (2**(msb - lsb + 1) - 1)) << lsb) | (new_value & ~((2**(msb - lsb + 1) - 1) << lsb))
        self._write(new_value)

    def _commit(self) -> None:
        """Apply the staged value to become the visible signal state."""
        if self._pending is None:
            return
        self._value = self._pending
        self._pending = None

    def _snapshot_delta(self) -> None:
        """Remember the current value for delta change detection."""
        self._snapshot_delta_val = self._value

    def _snapshot_epsilon(self) -> None:
        """Remember the current value for epsilon change detection."""
        self._snapshot_epsilon_val = self._value

    def _snapshot_cycle(self) -> None:
        """Remember the current value for cycle/edge-triggered detection."""
        self._snapshot_cycle_val = self._value

    def _is_cycle_changed(self) -> bool:
        """Return True if the value differs from the last cycle snapshot.

        Returns
        -------
        bool
            True if the value has changed since the last cycle snapshot.
        """
        return self._value != self._snapshot_cycle_val

    def _is_delta_changed(self) -> bool:
        """Return True if the value differs from the last delta snapshot.

        Returns
        -------
        bool
            True if the value has changed since the last delta snapshot.
        """
        return self._value != self._snapshot_delta_val

    def _is_epsilon_changed(self) -> bool:
        """Return True if the value differs from the last epsilon snapshot.

        Returns
        -------
        bool
            True if the value has changed since the last epsilon snapshot.
        """
        return self._value != self._snapshot_epsilon_val

    def _equal_cycle_edge(self, edge: Edge) -> bool:
        """Check whether the last transition matches the requested cycle edge.

        Parameters
        ----------
        edge : Edge
            The edge type to check for (Edge.POS or Edge.NEG).

        Returns
        -------
        bool
            True if the transition from the cycle snapshot to the current value
            matches the specified edge.
        """
        if edge == Edge.POS:
            return self._value != 0 and self._snapshot_cycle_val == 0
        elif edge == Edge.NEG:
            return self._value == 0 and self._snapshot_cycle_val != 0
        return False


class Wire(_Signal):
    """Combinational driver that may be written from always_comb blocks only.

    A Wire represents a physical wire in a digital circuit. Its value is
    determined by combinational logic. In hdlproto, this means it should
    only be driven from within an `@always_comb` block.

    Examples
    --------
    >>> a = Wire()
    >>> a.w = 1
    >>> print(a.w)
    1
    """

    @property
    def w(self) -> int:
        """Return the current (committed) wire value.

        Returns
        -------
        int
            The current integer value of the wire.
        """
        return self._value

    @w.setter
    def w(self, value: int) -> None:
        """Request a write through the simulation context with width masking.

        Parameters
        ----------
        value : int
            The new value to assign to the wire.
        """
        self._sim_context._record_write(self)
        self._write(value)

    def __getitem__(self, key: (int | slice)) -> int:
        """Read one or more bits using slice/index syntax.

        Parameters
        ----------
        key : int or slice
            The index or slice ([msb:lsb]) to read.

        Returns
        -------
        int
            The value of the selected bit(s).
        """
        return self._read_bits(key)

    def __setitem__(self, key: (int | slice), value: int) -> None:
        """Write to a slice/index after recording the combinational write.

        Parameters
        ----------
        key : int or slice
            The index or slice ([msb:lsb]) to write to.
        value : int
            The value to write to the selected bit(s).
        """
        self._sim_context._record_write(self)
        self._write_bits(key, value)

    def _get_signal(self):
        return self

    def _get_width(self):
        return self._width

    def _get_value(self):
        return self._value

    def _get_name(self) -> str:
        return self._name


class Reg(_Signal):
    """Sequential storage written inside always_ff blocks and committed in NBA.

    A Reg represents a register or flip-flop. It holds its value across
    clock cycles. In hdlproto, it should only be driven from within an
    `@always_ff` block, mimicking non-blocking assignment behavior in Verilog.

    Examples
    --------
    >>> clk = Wire()
    >>> d = Wire()
    >>> q = Reg()
    ...
    # In an @always_ff block
    q.r = d.w
    """

    @property
    def _is_reg(self) -> bool:
        return True

    @property
    def r(self) -> int:
        """Return the current committed register value.

        Returns
        -------
        int
            The current integer value of the register.
        """
        return self._value

    @r.setter
    def r(self, value: int) -> None:
        """Queue a new register value after validating the write phase.

        Parameters
        ----------
        value : int
            The new value to assign to the register.
        """
        self._sim_context._record_write(self)
        self._write(value)

    def __getitem__(self, key: (int | slice)) -> int:
        """Read bits from the register using slice/index syntax.

        Parameters
        ----------
        key : int or slice
            The index or slice ([msb:lsb]) to read.

        Returns
        -------
        int
            The value of the selected bit(s).
        """
        return self._read_bits(key)

    def __setitem__(self, key: (int | slice), value: int) -> None:
        """Write selected bits into the pending register value.

        Parameters
        ----------
        key : int or slice
            The index or slice ([msb:lsb]) to write to.
        value : int
            The value to write to the selected bit(s).
        """
        self._sim_context._record_write(self)
        self._write_bits(key, value)

    def _get_signal(self):
        return self

    def _get_width(self):
        return self._width

    def _get_value(self):
        return self._value

    def _get_name(self) -> str:
        return self._name


class _Port(_Signal):
    """Proxy base class that forwards to an underlying Wire while exposing a name.

    This is an internal class used to implement Input and Output ports. It
    acts as an alias or proxy to a signal in a different module scope,
    typically a Wire in a parent module.

    Parameters
    ----------
    target : Wire
        The Wire signal that this port is connected to.
    """

    def __init__(self, target: Wire):
        super().__init__()
        self._target = target._get_signal()
        self._name = None
        self._width = target._get_width()

    def __getnewargs__(self):
        return (self._target,)

    @property
    def _is_reg(self) -> bool:
        # Proxy the is_reg property from the target signal
        return self._target._is_reg

    @property
    def w(self) -> int:
        """int: The value of the connected target signal."""
        return self._target.w

    def __getitem__(self, key: (int | slice)) -> int:
        return self._target._read_bits(key)

    def _commit(self) -> None:
        # 【重要】ターゲットが Reg の場合、Port側で _commit() を呼んではいけません。
        # Regはシミュレータによって別途管理され、NBA領域でコミットされるためです。
        # ここで呼んでしまうと、Active領域で値が確定してしまい、レースコンディションになります。
        if isinstance(self._target, Reg):
            return
        self._target._commit()

    def _snapshot_delta(self) -> None:
        self._target._snapshot_delta()

    def _snapshot_cycle(self) -> None:
        self._target._snapshot_cycle()

    def _is_delta_changed(self) -> bool:
        return self._target._is_delta_changed()

    def _equal_cycle_edge(self, edge: Edge) -> bool:
        return self._target._equal_cycle_edge(edge)

    def _get_signal(self):
        return self._target._get_signal()

    def _get_width(self) -> int:
        return self._target._get_width()

    def _get_value(self):
        return self._target._get_value()

    def _get_name(self) -> str:
        return f"{self._name}({self._target._get_name()})"


class InputWire(_Port):
    """Passive port alias that mirrors a Wire value from a parent module.

    An Input port provides read-only access to a Wire in a parent or
    enclosing module. It is used to pass signals down the module hierarchy.

    Parameters
    ----------
    target : Wire
        The Wire signal to connect to this input port.
    """
    def __init__(self, target):
        if target._is_reg:
            raise TypeError("Input(Reg) is not allowed. Inputs must be driven by Wires.")
        super().__init__(target)

    @property
    def w(self) -> int:
        return self._target._get_value()

    def __getitem__(self, key):
        return self._target._read_bits(key)


class OutputWire(_Port):
    """Active port alias that can drive its target wire from child modules.

    An Output port provides write access to a Wire in a parent or
    enclosing module. It is used to drive signals up the module hierarchy.

    Parameters
    ----------
    target : Wire
        The Wire signal that this output port will drive.
    """
    def __init__(self, target: (Wire | Reg)):
        if target._is_reg:
            raise TypeError("OutputWire cannot wrap a Reg. Use OutputReg instead.")
        super().__init__(target)

    @property
    def w(self) -> int:
        """Return the current value."""
        return self._target._get_value()

    @w.setter
    def w(self, value: int) -> None:
        """Drive the target wire with a new value.

        Parameters
        ----------
        value : int
            The new value to drive.
        """
        self._sim_context._record_write(self)
        self._target._write(value)

    def __getitem__(self, key):
        return self._target._read_bits(key)

    def __setitem__(self, key: (int | slice), value: int) -> None:
        """Drive a slice of the target wire with a new value.

        Parameters
        ----------
        key : int or slice
            The index or slice ([msb:lsb]) of the target to drive.
        value : int
            The value to drive into the selected bit(s).
        """
        self._sim_context._record_write(self)
        self._target._write_bits(key, value)


class OutputReg(_Port):
    """Active port alias that can drive its target reg from child modules.

    An Output port provides write access to a Reg in a parent or
    enclosing module. It is used to drive signals up the module hierarchy.

    Parameters
    ----------
    target : Reg
        The Reg signal that this output port will drive.
    """
    def __init__(self, target: Reg):
        if not target._is_reg:
            raise TypeError("OutputReg cannot wrap a Wire. Use OutputWire instead.")
        super().__init__(target)

    @property
    def r(self) -> int:
        return self._target._get_value()

    @r.setter
    def r(self, value: int) -> None:
        self._sim_context._record_write(self)
        self._target._write(value)

    def __getitem__(self, key):
        return self._target._read_bits(key)

    def __setitem__(self, key, value):
        """Drive a slice of the target reg with a new value.

        Parameters
        ----------
        key : int or slice
            The index or slice ([msb:lsb]) of the target to drive.
        value : int
            The value to drive into the selected bit(s).
        """
        self._sim_context._record_write(self)
        self._target._write_bits(key, value)