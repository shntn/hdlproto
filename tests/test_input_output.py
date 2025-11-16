import pytest
from hdlproto import Wire, Reg, Input, Output, Module

class TestInput:
    def test_defined_without_param(self):
        wire = Wire()
        in_wire = Input(wire)
        assert in_wire.w == 0

    def test_defined_without_sign_width(self):
        wire = Wire(init=1)
        in_wire = Input(wire)
        assert in_wire.w == 1

    def test_defined_without_sign_init(self):
        wire = Wire(width=1)
        in_wire = Input(wire)
        assert in_wire.w == 0

    #def test_defined_without_width_init(self):
    #    with pytest.raises(ValueError) as e:
    #        wire = Wire(sign=True)
    #    assert str(e.value) == "Signal width must be greater than 1."

    def test_defined_without_sign(self):
        wire = Wire(width=2, init=3)
        in_wire = Input(wire)
        assert in_wire.w == 3

    #def test_defined_without_width(self):
    #    with pytest.raises(ValueError) as e:
    #        wire = Wire(sign=True, init=1)
    #    assert str(e.value) == "Signal width must be greater than 1."

    def test_defined_without_init(self):
        wire = Wire(sign=True, width=4)
        in_wire = Input(wire)
        assert in_wire.w == 0

    def test_defined_with_all_none(self):
        wire = Wire(sign=None, width=None, init=None)
        in_wire = Input(wire)
        assert in_wire.w is None

    def test_defined_with_init(self):
        wire = Wire(sign=None, width=None, init=1)
        in_wire = Input(wire)
        assert in_wire.w == 1

    def test_defined_with_width(self):
        wire = Wire(sign=None, width=4, init=None)
        in_wire = Input(wire)
        assert in_wire.w is None

    def test_defined_with_sign(self):
        wire = Wire(sign=False, width=None, init=None)
        in_wire = Input(wire)
        assert in_wire.w is None

    def test_defined_with_width_init(self):
        wire = Wire(sign=None, width=4, init=12)
        in_wire = Input(wire)
        assert in_wire.w == 12

    def test_defined_with_sign_init(self):
        wire = Wire(sign=False, width=None, init=1)
        in_wire = Input(wire)
        assert in_wire.w == 1

    def test_defined_with_sign_width(self):
        wire = Wire(sign=False, width=4, init=None)
        in_wire = Input(wire)
        assert in_wire.w is None

    def test_defined_with_unsigned_init(self):
        wire = Wire(sign=False, width=4, init=12)
        in_wire = Input(wire)
        assert in_wire.w == 12


class TestOutput:
    def test_defined_without_param(self):
        wire = Wire()
        out_wire = Output(wire)
        assert out_wire.w == 0

    def test_defined_without_sign_width(self):
        wire = Wire(init=1)
        out_wire = Output(wire)
        assert out_wire.w == 1

    def test_defined_without_sign_init(self):
        wire = Wire(width=1)
        out_wire = Output(wire)
        assert out_wire.w == 0

    #def test_defined_without_width_init(self):
    #    with pytest.raises(ValueError) as e:
    #        wire = Wire(sign=True)
    #    assert str(e.value) == "Signal width must be greater than 1."

    def test_defined_without_sign(self):
        wire = Wire(width=2, init=3)
        out_wire = Output(wire)
        assert out_wire.w == 3

    #def test_defined_without_width(self):
    #    with pytest.raises(ValueError) as e:
    #        wire = Wire(sign=True, init=1)
    #    assert str(e.value) == "Signal width must be greater than 1."

    def test_defined_without_init(self):
        wire = Wire(sign=True, width=4)
        out_wire = Output(wire)
        assert out_wire.w == 0

    def test_defined_with_all_none(self):
        wire = Wire(sign=None, width=None, init=None)
        out_wire = Output(wire)
        assert out_wire.w is None

    def test_defined_with_init(self):
        wire = Wire(sign=None, width=None, init=1)
        out_wire = Output(wire)
        assert out_wire.w == 1

    def test_defined_with_width(self):
        wire = Wire(sign=None, width=4, init=None)
        out_wire = Output(wire)
        assert out_wire.w is None

    def test_defined_with_sign(self):
        wire = Wire(sign=False, width=None, init=None)
        out_wire = Output(wire)
        assert out_wire.w is None

    def test_defined_with_width_init(self):
        wire = Wire(sign=None, width=4, init=12)
        out_wire = Output(wire)
        assert out_wire.w == 12

    def test_defined_with_sign_init(self):
        wire = Wire(sign=False, width=None, init=1)
        out_wire = Output(wire)
        assert out_wire.w == 1

    def test_defined_with_sign_width(self):
        wire = Wire(sign=False, width=4, init=None)
        out_wire = Output(wire)
        assert out_wire.w is None

    def test_defined_with_unsigned_init(self):
        wire = Wire(sign=False, width=4, init=12)
        out_wire = Output(wire)
        assert out_wire.w == 12


class TestInputSlice:
    def test_set_bit_and_get_bit(self):
        wire = Wire(width=4, init=0)
        in_wire = Input(wire)
        with pytest.raises(TypeError) as e:
            in_wire[2] = 1
        assert str(e.value) == "'Input' object does not support item assignment"
        wire[2] = 1
        wire._update()
        assert in_wire.w == 4
        assert in_wire[2] == 1

    def test_set_slice_and_get_slice(self):
        wire = Wire(width=4, init=0)
        in_wire = Input(wire)
        with pytest.raises(TypeError) as e:
            in_wire[2:1] = 3
        assert str(e.value) == "'Input' object does not support item assignment"
        wire[2:1] = 3
        wire._update()
        assert in_wire.w == 6
        assert in_wire[2:1] == 3


class TestOutputSlice:
    def test_set_bit_and_get_bit(self):
        wire = Wire(width=4, init=0)
        out_wire = Output(wire)
        out_wire[2] = 1
        out_wire._update()
        assert out_wire.w == 4
        assert out_wire[2] == 1

    def test_set_slice_and_get_slice(self):
        wire = Wire(width=4, init=0)
        out_wire = Output(wire)
        out_wire[2:1] = 3
        out_wire._update()
        assert out_wire.w == 6
        assert out_wire[2:1] == 3


class TestInputSigned:
    def test_unsigned(self):
        wire1 = Wire(sign=False, width=4, init=0)
        in_wire1 = Input(wire1)
        with pytest.raises(AttributeError) as e:
            in_wire1.w = 6
        assert str(e.value) == "property 'w' of 'Input' object has no setter"
        wire1.w = 6
        wire1._update()
        assert in_wire1.w == 6
        wire1.w = 17
        wire1._update()
        assert in_wire1.w == 1
        wire1.w = -7
        wire1._update()
        assert in_wire1.w == 9
        wire1.w = -15
        wire1._update()
        assert in_wire1.w == 1

    def test_signed(self):
        wire1 = Wire(sign=True, width=4, init=0)
        in_wire1 = Input(wire1)
        with pytest.raises(AttributeError) as e:
            in_wire1.w = 6
        assert str(e.value) == "property 'w' of 'Input' object has no setter"
        wire1.w = 6
        wire1._update()
        assert in_wire1.w == 6
        wire1.w = 17
        wire1._update()
        assert in_wire1.w == 1
        wire1.w = -7
        wire1._update()
        assert in_wire1.w == -7
        wire1.w = -15
        wire1._update()
        assert in_wire1.w == 1


class TestOutputSigned:
    def test_unsigned(self):
        wire1 = Wire(sign=False, width=4, init=0)
        out_wire1 = Output(wire1)
        out_wire1.w = 6
        out_wire1._update()
        assert out_wire1.w == 6
        out_wire1.w = 17
        out_wire1._update()
        assert out_wire1.w == 1
        out_wire1.w = -7
        out_wire1._update()
        assert out_wire1.w == 9
        out_wire1.w = -15
        out_wire1._update()
        assert out_wire1.w == 1

    def test_signed(self):
        wire1 = Wire(sign=True, width=4, init=0)
        out_wire1 = Output(wire1)
        out_wire1.w = 6
        out_wire1._update()
        assert out_wire1.w == 6
        out_wire1.w = 17
        out_wire1._update()
        assert out_wire1.w == 1
        out_wire1.w = -7
        out_wire1._update()
        assert out_wire1.w == -7
        out_wire1.w = -15
        out_wire1._update()
        assert out_wire1.w == 1
