import pytest
from hdlproto.signal import Reg, OutputReg, Wire
from hdlproto.signal_array import RegArray, OutputRegArray, WireArray
from hdlproto.module import Module


# =================================================================
# Mock & Helper
# =================================================================
class MockContext:
    def __init__(self):
        self.write_history = []

    def _record_write(self, signal):
        self.write_history.append(signal)


class MockModule(Module):
    def __init__(self, name="top"):
        super().__init__()
        self._name = name


@pytest.fixture
def ctx():
    return MockContext()


# =================================================================
# 1. 初期化ロジック (Wrap RegArray)
# =================================================================
def test_output_reg_array_init_scalar(ctx):
    """
    RegArray をラップして初期化した際、値が正しく透くか確認。
    """
    count = 5
    init_val = 10
    width = 8

    # 1. Target作成
    target = RegArray(count=count, width=width, init=init_val)

    # 2. OutputRegArray作成
    arr = OutputRegArray(target)

    # 配列の長さ確認
    assert len(arr) == count

    # 各要素の確認
    for i, out in enumerate(arr):
        out._set_context(f"out{i}", None, ctx)
        assert isinstance(out, OutputReg)
        assert out._get_width() == width
        assert out.r == init_val


def test_output_reg_array_init_list_padding(ctx):
    """
    リスト初期化された RegArray をラップした場合の確認。
    """
    # Target (Paddingあり)
    target = RegArray(count=3, width=8, init=[0xAA, 0xBB])

    arr = OutputRegArray(target)

    for i, out in enumerate(arr):
        out._set_context(f"out{i}", None, ctx)

    # インデックスアクセス
    assert arr[0].r == 0xAA
    assert arr[1].r == 0xBB
    assert arr[2].r == 0x00


def test_output_reg_array_init_tuple(ctx):
    """
    タプル初期化された RegArray をラップした場合の確認。
    """
    target = RegArray(count=3, width=8, init=(0x1, 0x2))
    arr = OutputRegArray(target)

    for out in arr:
        out._set_context("out", None, ctx)

    assert arr[0].r == 0x1
    assert arr[1].r == 0x2
    assert arr[2].r == 0x0


def test_output_reg_array_init_default():
    """
    デフォルト(0)の RegArray をラップした場合の確認。
    """
    target = RegArray(count=2, width=4)
    arr = OutputRegArray(target)

    assert arr[0].r == 0
    assert arr[1].r == 0


# =================================================================
# 2. アクセスと操作 (_SignalArray functionality)
# =================================================================
def test_output_reg_array_getitem_index(ctx):
    """
    インデックスアクセスのテスト。
    """
    target = RegArray(count=3, width=8, init=[10, 20, 30])
    arr = OutputRegArray(target)

    # 正のインデックス
    assert arr[0].r == 10
    assert arr[2].r == 30

    # 負のインデックス
    assert arr[-1].r == 30


def test_output_reg_array_getitem_tuple_access(ctx):
    """
    タプルアクセス (arr[index, slice]) のテスト。
    OutputRegArray経由でもスライス読み出しができるか。
    """
    target = RegArray(count=2, width=8, init=[0x5A, 0xC3])
    arr = OutputRegArray(target)
    arr[0]._set_context("out", None, ctx)

    # arr[0, 7:4] -> 0番目の値(0x5A)の上位4ビット
    # 期待値: 0101 -> 0x5
    slice_val = arr[0, 7:4]
    assert slice_val == 0x5

    # arr[1, 7] -> 1番目の値(0xC3)の 7ビット目
    # 期待値: 1
    bit_val = arr[1, 7]
    assert bit_val == 1


def test_output_reg_array_iter(ctx):
    """
    __iter__ のテスト。
    """
    init_vals = [1, 2, 3]
    target = RegArray(count=3, width=8, init=init_vals)
    arr = OutputRegArray(target)

    extracted_vals = [out.r for out in arr]
    assert extracted_vals == init_vals


# =================================================================
# 3. OutputRegArray 固有メソッド & 制約
# =================================================================
def test_output_reg_array_set_array(ctx):
    """
    _set_array メソッドのテスト。
    OutputReg のリストで差し替えられるか確認。
    """
    target = RegArray(count=1, width=8, init=10)
    arr = OutputRegArray(target)
    old_output = arr[0]

    # 新しい OutputReg リストで上書き
    r1 = Reg(width=8, init=99)
    r2 = Reg(width=8, init=100)
    new_outputs = [OutputReg(r1), OutputReg(r2)]

    arr._set_array(new_outputs)

    assert len(arr) == 2
    assert arr[0].r == 99
    assert arr[1].r == 100

    # 古い要素への参照確認
    assert old_output.r == 10


def test_output_reg_array_write_behavior(ctx):
    """
    OutputRegArrayの要素に対する書き込みが正しく機能するか確認。
    """
    target = RegArray(count=1, width=8, init=0x00)
    for r in target:
        r._set_context("t", None, ctx)

    arr = OutputRegArray(target)
    out = arr[0]
    out._set_context("out0", None, ctx)

    # 書き込み (array[0].r = ...)
    out.r = 0xFF
    target[0]._commit()
    assert target[0].r == 0xFF

    # スライス書き込み (array[0, 3:0] = ...)
    # これを通すためには OutputRegArray にも __setitem__ が必要
    arr[0, 3:0] = 0xA
    target[0]._commit()
    assert target[0].r == 0xFA


def test_output_reg_array_rejects_wire_array(ctx):
    """
    OutputRegArray に WireArray を渡すとエラーになること。
    """
    wire_arr = WireArray(count=2)

    # OutputReg cannot wrap a Wire
    with pytest.raises(TypeError, match="OutputReg cannot wrap a Wire"):
        _ = OutputRegArray(wire_arr)


# =================================================================
# 4. OutputRegArray 階層接続
# =================================================================
def test_output_reg_array_nested_chaining(ctx):
    """
    OutputRegArray をさらに OutputRegArray でラップできるか確認する。
    (RegArray -> OutputRegArray(Mid) -> OutputRegArray(Top))
    """
    # 1. Root (RegArray)
    root = RegArray(count=3, width=8, init=0x00)
    for r in root:
        r._set_context("root", None, ctx)

    # 2. Mid (OutputRegArray)
    mid = OutputRegArray(root)
    for i, out in enumerate(mid):
        out._set_context(f"mid{i}", None, ctx)

    # 3. Top (OutputRegArray)
    top = OutputRegArray(mid)
    for i, out in enumerate(top):
        out._set_context(f"top{i}", None, ctx)

    # 検証
    assert len(top) == 3

    # Top からの書き込み
    top[0].r = 0xAA
    root[0]._commit()

    # Rootまで伝播するか
    assert root[0].r == 0xAA
    # Midからも見えるか
    assert mid[0].r == 0xAA

    # 内部構造の確認
    assert top[0]._get_signal() is root[0]


def test_output_reg_array_rejects_direct_item_assignment(ctx):
    """
    arr[i] = val (要素そのものの置換) は禁止されていることを確認する。
    """
    target = RegArray(count=1, width=8)
    arr = OutputRegArray(target)

    with pytest.raises(TypeError, match="only supports tuple assignment"):
        arr[0] = 0xFF