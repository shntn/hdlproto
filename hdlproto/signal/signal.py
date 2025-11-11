from typing import Callable
from hdlproto.event import Event, EventType, EventSource


class SignalBase:
    def __init__(self, init=None):
        self.value = init
        self.pending = None

class SignalBitOperator:
    def __init__(self, width=1):
        self.width = width

    def get_bit(self, value, start, stop):
        mask = self.__make_mask(start, stop)
        masked_value = value & mask
        slice_value = self.__unshift_value(start, stop, masked_value)
        return slice_value

    def set_bit(self, value, start, stop, new_value):
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


class SignalSignOperator:
    def __init__(self, sign=False, width=1):
        self.sign = sign
        self.width = width

    def to_integer(self, value):
        return self.__make_integer(value)

    def to_bits_data(self, value):
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


class SignalEvents:
    def __init__(self):
        self.handler = None

    def fire(self, event: Event):
        self.handler(event)


class Signal:
    def __init__(self, sign=False, width=1, init=0):
        if sign and width == 1:
            raise ValueError("Signal width must be greater than 1.")
        self.base = SignalBase(init)
        self.bits = SignalBitOperator(width)
        self.sign = SignalSignOperator(sign, width)
        self.event = SignalEvents()

    def get(self):
        raw_value = self.base.value
        return self.sign.to_integer(raw_value)

    def set(self, value):
        nbits_value = self.sign.to_bits_data(value)
        value_changed = nbits_value != self.base.value
        if value_changed:
            self.base.pending = nbits_value
        else:
            self.base.pending = None
        return value_changed

    def get_bit(self, start, stop):
        raw_value = self.base.value
        if not isinstance(raw_value, int):
            raise TypeError("Invalid argument type.")
        bits_value = self.bits.get_bit(raw_value, start, stop)
        return self.sign.to_integer(bits_value)

    def set_bit(self, start, stop, value):
        raw_value = self.base.value
        if not isinstance(raw_value, int) or not isinstance(value, int):
            raise TypeError("Invalid argument type.")
        bits_value = self.bits.set_bit(raw_value, start, stop, value)
        value_changed = bits_value != self.base.value
        if value_changed:
            self.base.pending = bits_value
        else:
            self.base.pending = None
        return value_changed

    def update(self):
        is_unstable = self.base.pending is not None
        if is_unstable:
            self.base.value = self.base.pending
            self.base.pending = None
        return is_unstable

    def fire(self, event: Event):
        self.event.fire(event)

    def fire_write_event(self, source_type: EventSource, signal_obj, value_changed: bool):
        if not self.event.handler:
            return
        module_path = getattr(signal_obj.context, "module_path", None)
        signal_name = getattr(signal_obj.context, "name", None)
        event = Event(
            event_type=EventType.SIGNAL_WRITE,
            source_type=source_type,
            info={
                "signal": signal_obj,
                "value_changed": value_changed,
                "signal_name": signal_name,
                "signal_module_path": module_path,
            }
        )
        self.fire(event)


class SignalContext:
    __slots__ = ("name", "signal_type", "module", "module_path")

    def __init__(self, signal):
        self.name = None
        self.signal_type = None
        self.module = None
        self.module_path = None


class Wire:
    __slots__ = ("_signal", "context")

    def __init__(self, sign=False, width=1, init=0):
        self._signal = Signal(sign, width, init)
        self.context = SignalContext(self._signal)

    def set_context(self, name=None, signal_type=None, module=None):
        self.context.set_context(name, signal_type, module)

    @property
    def w(self):
        return self._signal.get()

    @w.setter
    def w(self, value):
        value_changed = self._signal.set(value)
        self._signal.fire_write_event(EventSource.WIRE, self, value_changed)

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            return self._signal.get_bit(start, stop)
        elif isinstance(key, int):
            return self._signal.get_bit(key, key)
        else:
            raise TypeError("Invalid argument type.")

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            value_changed = self._signal.set_bit(start, stop, value)
        elif isinstance(key, int):
            value_changed = self._signal.set_bit(key, key, value)
        else:
            raise TypeError("Invalid argument type.")
        self._signal.fire_write_event(EventSource.WIRE, self, value_changed)

    def update(self):
        return self._signal.update()


class Reg:
    __slots__ = ("_signal", "context")

    def __init__(self, sign=False, width=1, init=0):
        self._signal = Signal(sign, width, init)
        self.context = SignalContext(self._signal)

    def set_context(self, name=None, signal_type=None, module=None):
        self.context.set_context(name, signal_type, module)

    @property
    def r(self):
        return self._signal.get()

    @r.setter
    def r(self, value):
        value_changed = self._signal.set(value)
        self._signal.fire_write_event(EventSource.REG, self, value_changed)

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            return self._signal.get_bit(start, stop)
        elif isinstance(key, int):
            return self._signal.get_bit(key, key)
        else:
            raise TypeError("Invalid argument type.")

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            value_changed = self._signal.set_bit(start, stop, value)
        elif isinstance(key, int):
            value_changed = self._signal.set_bit(key, key, value)
        else:
            raise TypeError("Invalid argument type.")
        self._signal.fire_write_event(EventSource.REG, self, value_changed)

    def update(self):
        return self._signal.update()


class Input:
    __slots__ = ("_signal", "context")

    def __init__(self, wire: Wire):
        self._signal = wire._signal
        self.context = SignalContext(self._signal)

    def set_context(self, name=None, signal_type=None, module=None):
        self.context.set_context(name, signal_type, module)

    @property
    def w(self):
        return self._signal.get()

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            return self._signal.get_bit(start, stop)
        elif isinstance(key, int):
            return self._signal.get_bit(key, key)
        else:
            raise TypeError("Invalid argument type.")

    def update(self):
        return False


class Output:
    __slots__ = ("_signal", "context")

    def __init__(self, wire: Wire):
        self._signal = wire._signal
        self.context = SignalContext(self._signal)

    def set_context(self, name=None, signal_type=None, module=None):
        self.context.set_context(name, signal_type, module)

    @property
    def w(self):
        return self._signal.get()

    @w.setter
    def w(self, value):
        value_changed = self._signal.set(value)
        self._signal.fire_write_event(EventSource.OUTPUT, self, value_changed)

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            return self._signal.get_bit(start, stop)
        elif isinstance(key, int):
            return self._signal.get_bit(key, key)
        else:
            raise TypeError("Invalid argument type.")

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start, stop = key.start, key.stop
            value_changed = self._signal.set_bit(start, stop, value)
        elif isinstance(key, int):
            value_changed = self._signal.set_bit(key, key, value)
        else:
            raise TypeError("Invalid argument type.")
        self._signal.fire_write_event(EventSource.OUTPUT, self, value_changed)

    def update(self):
        return self._signal.update()
