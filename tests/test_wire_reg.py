import pytest
from hdlproto import Wire, Reg, Module
from hdlproto.state import SignalType

class TestWire:
    def test_defined_without_param(self):
        wire = Wire()
        assert wire.w == 0

    def test_defined_without_sign_width(self):
        wire = Wire(init=1)
        assert wire.w == 1

    def test_defined_without_sign_init(self):
        wire = Wire(width=1)
        assert wire.w == 0

    def test_defined_without_width_init(self):
        with pytest.raises(ValueError) as e:
            wire = Wire(sign=True)
        assert str(e.value) == "Signal width must be greater than 1."

    def test_defined_without_sign(self):
        wire = Wire(width=2, init=3)
        assert wire.w == 3

    def test_defined_without_width(self):
        with pytest.raises(ValueError) as e:
            wire = Wire(sign=True, init=1)
        assert str(e.value) == "Signal width must be greater than 1."

    def test_defined_without_init(self):
        wire = Wire(sign=True, width=4)
        assert wire.w == 0

    def test_defined_with_all_none(self):
        wire = Wire(sign=None, width=None, init=None)
        assert wire.w is None

    def test_defined_with_init(self):
        wire = Wire(sign=None, width=None, init=1)
        assert wire.w == 1

    def test_defined_with_width(self):
        wire = Wire(sign=None, width=4, init=None)
        assert wire.w is None

    def test_defined_with_sign(self):
        wire = Wire(sign=False, width=None, init=None)
        assert wire.w is None

    def test_defined_with_width_init(self):
        wire = Wire(sign=None, width=4, init=12)
        assert wire.w == 12

    def test_defined_with_sign_init(self):
        wire = Wire(sign=False, width=None, init=1)
        assert wire.w == 1

    def test_defined_with_sign_width(self):
        wire = Wire(sign=False, width=4, init=None)
        assert wire.w is None

    def test_defined_with_unsigned_init(self):
        wire = Wire(sign=False, width=4, init=12)
        assert wire.w == 12


class TestReg:
    def test_defined_without_param(self):
        reg = Reg()
        assert reg.r == 0

    def test_defined_without_sign_width(self):
        reg = Reg(init=1)
        assert reg.r == 1

    def test_defined_without_sign_init(self):
        reg = Reg(width=1)
        assert reg.r == 0

    def test_defined_without_width_init(self):
        with pytest.raises(ValueError) as e:
            reg = Reg(sign=True)
        assert str(e.value) == "Signal width must be greater than 1."

    def test_defined_without_sign(self):
        reg = Reg(width=2, init=3)
        assert reg.r == 3

    def test_defined_without_width(self):
        with pytest.raises(ValueError) as e:
            reg = Reg(sign=True, init=1)
        assert str(e.value) == "Signal width must be greater than 1."

    def test_defined_without_init(self):
        reg = Reg(sign=True, width=4)
        assert reg.r == 0

    def test_defined_with_all_none(self):
        reg = Reg(sign=None, width=None, init=None)
        assert reg.r is None

    def test_defined_with_init(self):
        reg = Reg(sign=None, width=None, init=1)
        assert reg.r == 1

    def test_defined_with_width(self):
        reg = Reg(sign=None, width=4, init=None)
        assert reg.r is None

    def test_defined_with_sign(self):
        reg = Reg(sign=False, width=None, init=None)
        assert reg.r is None

    def test_defined_with_width_init(self):
        reg = Reg(sign=None, width=4, init=12)
        assert reg.r == 12

    def test_defined_with_sign_init(self):
        reg = Reg(sign=False, width=None, init=1)
        assert reg.r == 1

    def test_defined_with_sign_width(self):
        reg = Reg(sign=False, width=4, init=None)
        assert reg.r is None

    def test_defined_with_unsigned_init(self):
        reg = Reg(sign=False, width=4, init=12)
        assert reg.r == 12


class TestWireSlice:
    def test_set_bit_and_get_bit(self):
        wire1 = Wire(width=4, init=0)
        wire1[2] = 1
        wire1.update()
        assert wire1.w == 4
        assert wire1[2] == 1

    def test_set_slice_and_get_slice(self):
        wire2 = Wire(width=4, init=0)
        wire2[2:1] = 3
        wire2.update()
        assert wire2.w == 6
        assert wire2[2:1] == 3


class TestRegSlice:
    def test_set_bit_and_get_bit(self):
        reg1 = Reg(width=4, init=0)
        reg1[2] = 1
        reg1.update()
        assert reg1.r == 4
        assert reg1[2] == 1

    def test_set_slice_and_get_slice(self):
        reg2 = Reg(width=4, init=0)
        reg2[2:1] = 3
        reg2.update()
        assert reg2.r == 6
        assert reg2[2:1] == 3


class TestWireSigned:
    def test_unsigned(self):
        wire1 = Wire(sign=False, width=4, init=0)
        wire1.w = 6
        wire1.update()
        assert wire1.w == 6
        wire1.w = 17
        wire1.update()
        assert wire1.w == 1
        wire1.w = -7
        wire1.update()
        assert wire1.w == 9
        wire1.w = -15
        wire1.update()
        assert wire1.w == 1

    def test_signed(self):
        wire1 = Wire(sign=True, width=4, init=0)
        wire1.w = 6
        wire1.update()
        assert wire1.w == 6
        wire1.w = 17
        wire1.update()
        assert wire1.w == 1
        wire1.w = -7
        wire1.update()
        assert wire1.w == -7
        wire1.w = -15
        wire1.update()
        assert wire1.w == 1


class TestRegSigned:
    def test_unsigned(self):
        reg1 = Reg(sign=False, width=4, init=0)
        reg1.r = 6
        reg1.update()
        assert reg1.r == 6
        reg1.r = 17
        reg1.update()
        assert reg1.r == 1
        reg1.r = -7
        reg1.update()
        assert reg1.r == 9
        reg1.r = -15
        reg1.update()
        assert reg1.r == 1

    def test_signed(self):
        reg1 = Reg(sign=True, width=4, init=0)
        reg1.r = 6
        reg1.update()
        assert reg1.r == 6
        reg1.r = 17
        reg1.update()
        assert reg1.r == 1
        reg1.r = -7
        reg1.update()
        assert reg1.r == -7
        reg1.r = -15
        reg1.update()
        assert reg1.r == 1
