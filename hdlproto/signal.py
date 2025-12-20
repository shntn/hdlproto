from .state import Edge

def _parse_key(key):
    if isinstance(key, slice):
        msb, lsb = key.start, key.stop
    elif isinstance(key, int):
        msb = lsb = key
    else:
        raise TypeError("Invalid argument type")
    return msb, lsb


def _validate_range(msb, lsb):
    if msb < lsb:
        msb, lsb = lsb, msb
    return msb, lsb


def _assert_msb_lsb(msb, lsb, width):
    if msb >= width or lsb < 0:
        raise AttributeError("Invalid bit range")


def _normalize_slice(key, width):
    raw_msb, raw_lsb = _parse_key(key)
    msb, lsb = _validate_range(raw_msb, raw_lsb)
    _assert_msb_lsb(msb, lsb, width)
    return msb, lsb

def _make_mask(width):
    return (1 << width) - 1


def _replace_bits(base_val: int, insert_val: int, msb: int, lsb: int) -> int:
    width = msb - lsb + 1
    mask = _make_mask(width)
    shifted_val = (insert_val & mask) << lsb
    return (base_val & ~(mask << lsb)) | shifted_val


class _EdgeDetector:
    def __init__(self, init_val: int = 0):
        self._captured_val = init_val

    def _capture(self, current_val: int) -> None:
        self._captured_val = current_val

    def _has_changed(self, current_val: int) -> bool:
        return current_val != self._captured_val

    def _is_pos_edge(self, current_val: int) -> bool:
        return current_val != 0 and self._captured_val == 0

    def _is_neg_edge(self, current_val: int) -> bool:
        return current_val == 0 and self._captured_val != 0


class _SignalHistory:
    def __init__(self, init_val: int):
        self._delta = _EdgeDetector(init_val)
        self._cycle = _EdgeDetector(init_val)
        self._epsilon = _EdgeDetector(init_val)

    def _snapshot_delta(self, val: int) -> None:
        self._delta._capture(val)

    def _is_delta_changed(self, val: int) -> bool:
        return self._delta._has_changed(val)

    def _snapshot_epsilon(self, val: int) -> None:
        self._epsilon._capture(val)

    def _is_epsilon_changed(self, val: int) -> bool:
        return self._epsilon._has_changed(val)

    def _snapshot_cycle(self, val: int) -> None:
        self._cycle._capture(val)

    def _is_cycle_changed(self, val: int) -> bool:
        return self._cycle._has_changed(val)

    def _equal_cycle_edge(self, val: int, edge: Edge) -> bool:
        if edge == Edge.POS: return self._cycle._is_pos_edge(val)
        if edge == Edge.NEG: return self._cycle._is_neg_edge(val)
        return False


class _Signal:
    def __init__(self, init: int, width: int):
        self._width = width
        self._value = init
        self._pending = init
        self._history = _SignalHistory(init)

    def _write(self, value: int) -> None:
        mask = _make_mask(self._width)
        self._pending = value & mask

    def _commit(self) -> None:
        self._value = self._pending

    def _read_bits(self, key: (slice | int)) -> int:
        msb, lsb = _normalize_slice(key, self._width)
        mask = _make_mask(msb - lsb + 1)
        return (self._value >> lsb) & mask

    def _write_bits(self, key: (slice | int), value: int) -> None:
        base_value = self._pending
        msb, lsb = _normalize_slice(key, self._width)
        new_value = _replace_bits(base_value, value, msb, lsb)
        self._write(new_value)

    def _snapshot_delta(self) -> None:
        self._history._snapshot_delta(self._value)

    def _is_delta_changed(self) -> bool:
        return self._history._is_delta_changed(self._value)

    def _snapshot_epsilon(self) -> None:
        self._history._snapshot_epsilon(self._value)

    def _is_epsilon_changed(self) -> bool:
        return self._history._is_epsilon_changed(self._value)

    def _snapshot_cycle(self) -> None:
        self._history._snapshot_cycle(self._value)

    def _is_cycle_changed(self) -> bool:
        return self._history._is_cycle_changed(self._value)

    def _equal_cycle_edge(self, edge: Edge) -> bool:
        return self._history._equal_cycle_edge(self._value, edge)


class Wire:
    def __init__(self, init: int = 0, width: int = 1):
        self._signal = _Signal(init, width)
        self._sim_context = None
        self._name = None
        self._module = None

    @property
    def _is_reg(self) -> bool:
        return False

    def _set_context(self, name: str, module, sim_context) -> None:
        self._name = name
        self._module = module
        self._sim_context = sim_context

    def _get_name(self) -> str:
        return self._name

    @property
    def w(self) -> int:
        return self._signal._value

    @w.setter
    def w(self, value: int) -> None:
        self._sim_context._record_write(self)
        self._signal._write(value)

    def __getitem__(self, key: (int | slice)) -> int:
        return self._signal._read_bits(key)

    def __setitem__(self, key: (int | slice), value: int) -> None:
        self._sim_context._record_write(self)
        self._signal._write_bits(key, value)

    def _get_signal(self):
        return self

    def _get_width(self):
        return self._signal._width

    def _get_value(self):
        return self._signal._value

    def _write(self, value: int) -> None:
        return self._signal._write(value)

    def _write_bits(self, key: (slice | int), value: int) -> None:
        return self._signal._write_bits(key, value)

    def _read_bits(self, key: (slice | int)) -> int:
        return self._signal._read_bits(key)

    def _commit(self) -> None:
        self._signal._commit()

    def _snapshot_delta(self) -> None:
        self._signal._snapshot_delta()

    def _is_delta_changed(self) -> bool:
        return self._signal._is_delta_changed()

    def _snapshot_epsilon(self) -> None:
        self._signal._snapshot_epsilon()

    def _is_epsilon_changed(self) -> bool:
        return self._signal._is_epsilon_changed()

    def _snapshot_cycle(self) -> None:
        self._signal._snapshot_cycle()

    def _is_cycle_changed(self) -> bool:
        return self._signal._is_cycle_changed()

    def _equal_cycle_edge(self, edge: Edge) -> bool:
        return self._signal._equal_cycle_edge(edge)


class Reg:
    def __init__(self, init: int = 0, width: int = 1):
        self._signal = _Signal(init, width)
        self._sim_context = None
        self._name = None
        self._module = None

    @property
    def _is_reg(self) -> bool:
        return True

    def _set_context(self, name: str, module, sim_context) -> None:
        self._name = name
        self._module = module
        self._sim_context = sim_context

    def _get_name(self) -> str:
        return self._name

    @property
    def r(self) -> int:
        return self._signal._value

    @r.setter
    def r(self, value: int) -> None:
        self._sim_context._record_write(self)
        self._signal._write(value)

    def __getitem__(self, key: (int | slice)) -> int:
        return self._signal._read_bits(key)

    def __setitem__(self, key: (int | slice), value: int) -> None:
        self._sim_context._record_write(self)
        self._signal._write_bits(key, value)

    def _get_signal(self):
        return self

    def _get_width(self):
        return self._signal._width

    def _get_value(self):
        return self._signal._value

    def _write(self, value: int) -> None:
        return self._signal._write(value)

    def _write_bits(self, key: (slice | int), value: int) -> None:
        return self._signal._write_bits(key, value)

    def _read_bits(self, key: (slice | int)) -> int:
        return self._signal._read_bits(key)

    def _commit(self) -> None:
        self._signal._commit()

    def _snapshot_delta(self) -> None:
        self._signal._snapshot_delta()

    def _is_delta_changed(self) -> bool:
        return self._signal._is_delta_changed()

    def _snapshot_epsilon(self) -> None:
        self._signal._snapshot_epsilon()

    def _is_epsilon_changed(self) -> bool:
        return self._signal._is_epsilon_changed()

    def _snapshot_cycle(self) -> None:
        self._signal._snapshot_cycle()

    def _is_cycle_changed(self) -> bool:
        return self._signal._is_cycle_changed()

    def _equal_cycle_edge(self, edge: Edge) -> bool:
        return self._signal._equal_cycle_edge(edge)


class InputWire:
    def __init__(self, target: Wire):
        if target._is_reg:
            raise TypeError("Input(Reg) is not allowed. Inputs must be driven by Wires.")
        self._sim_context = None
        self._module = None
        self._target = target
        self._name = None
        self._width = target._get_width()

    @property
    def w(self) -> int:
        return self._target._get_value()

    def __getitem__(self, key):
        return self._target._read_bits(key)

    def __getnewargs__(self):
        return (self._target,)

    @property
    def _is_reg(self) -> bool:
        return self._target._is_reg

    def _commit(self) -> None:
        self._target._commit()

    def _get_signal(self):
        return self._target._get_signal()

    def _get_width(self) -> int:
        return self._target._get_width()

    def _get_value(self):
        return self._target._get_value()

    def _read_bits(self, key: (slice | int)) -> int:
        return self._target._read_bits(key)

    def _get_name(self) -> str:
        return f"{self._name}({self._target._get_name()})"

    def _set_context(self, name: str, module, sim_context) -> None:
        self._name = name
        self._module = module
        self._sim_context = sim_context

    def _snapshot_delta(self) -> None:
        self._target._snapshot_delta()

    def _is_delta_changed(self) -> bool:
        return self._target._is_delta_changed()

    def _snapshot_epsilon(self) -> None:
        self._target._snapshot_epsilon()

    def _is_epsilon_changed(self) -> bool:
        return self._target._is_epsilon_changed()

    def _snapshot_cycle(self) -> None:
        self._target._snapshot_cycle()

    def _is_cycle_changed(self) -> bool:
        return self._target._is_cycle_changed()

    def _equal_cycle_edge(self, edge: Edge) -> bool:
        return self._target._equal_cycle_edge(edge)


class OutputWire:
    def __init__(self, target):
        if target._is_reg:
            raise TypeError("OutputWire cannot wrap a Reg. Use OutputReg instead.")
        self._sim_context = None
        self._module = None
        self._target = target
        self._name = None
        self._width = target._get_width()

    @property
    def w(self) -> int:
        return self._target._get_value()

    @w.setter
    def w(self, value: int) -> None:
        self._sim_context._record_write(self)
        self._target._write(value)

    def __getitem__(self, key):
        return self._target._read_bits(key)

    def __setitem__(self, key: (int | slice), value: int) -> None:
        self._sim_context._record_write(self)
        self._target._write_bits(key, value)

    def __getnewargs__(self):
        return (self._target,)

    @property
    def _is_reg(self) -> bool:
        return self._target._is_reg

    def _commit(self) -> None:
        self._target._commit()

    def _get_signal(self):
        return self._target._get_signal()

    def _get_width(self) -> int:
        return self._target._get_width()

    def _get_value(self):
        return self._target._get_value()

    def _write(self, value: int) -> None:
        self._target._write(value)

    def _write_bits(self, key: (slice | int), value: int) -> None:
        return self._target._write_bits(key, value)

    def _read_bits(self, key: (slice | int)) -> int:
        return self._target._read_bits(key)

    def _get_name(self) -> str:
        return f"{self._name}({self._target._get_name()})"

    def _set_context(self, name: str, module, sim_context) -> None:
        self._name = name
        self._module = module
        self._sim_context = sim_context

    def _snapshot_delta(self) -> None:
        self._target._snapshot_delta()

    def _is_delta_changed(self) -> bool:
        return self._target._is_delta_changed()

    def _snapshot_epsilon(self) -> None:
        self._target._snapshot_epsilon()

    def _is_epsilon_changed(self) -> bool:
        return self._target._is_epsilon_changed()

    def _snapshot_cycle(self) -> None:
        self._target._snapshot_cycle()

    def _is_cycle_changed(self) -> bool:
        return self._target._is_cycle_changed()

    def _equal_cycle_edge(self, edge: Edge) -> bool:
        return self._target._equal_cycle_edge(edge)


class OutputReg:
    def __init__(self, target: Reg):
        if not target._is_reg:
            raise TypeError("OutputReg cannot wrap a Wire. Use OutputWire instead.")
        self._sim_context = None
        self._module = None
        self._target = target
        self._name = None
        self._width = target._get_width()

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
        self._sim_context._record_write(self)
        self._target._write_bits(key, value)

    def __getnewargs__(self):
        return (self._target,)

    @property
    def _is_reg(self) -> bool:
        return self._target._is_reg

    def _commit(self) -> None:
        self._target._commit()

    def _get_signal(self):
        return self._target._get_signal()

    def _get_width(self) -> int:
        return self._target._get_width()

    def _get_value(self):
        return self._target._get_value()

    def _write(self, value: int) -> None:
        self._target._write(value)

    def _write_bits(self, key: (slice | int), value: int) -> None:
        return self._target._write_bits(key, value)

    def _read_bits(self, key: (slice | int)) -> int:
        return self._target._read_bits(key)

    def _get_name(self) -> str:
        return f"{self._name}({self._target._get_name()})"

    def _set_context(self, name: str, module, sim_context) -> None:
        self._name = name
        self._module = module
        self._sim_context = sim_context

    def _snapshot_delta(self) -> None:
        self._target._snapshot_delta()

    def _is_delta_changed(self) -> bool:
        return self._target._is_delta_changed()

    def _snapshot_epsilon(self) -> None:
        self._target._snapshot_epsilon()

    def _is_epsilon_changed(self) -> bool:
        return self._target._is_epsilon_changed()

    def _snapshot_cycle(self) -> None:
        self._target._snapshot_cycle()

    def _is_cycle_changed(self) -> bool:
        return self._target._is_cycle_changed()

    def _equal_cycle_edge(self, edge: Edge) -> bool:
        return self._target._equal_cycle_edge(edge)
