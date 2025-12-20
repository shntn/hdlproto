import pytest
from hdlproto.signal import Wire, OutputWire
from hdlproto.signal_array import WireArray, OutputWireArray, RegArray
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
# 1. 初期化ロジック (Wrap WireArray)
# =================================================================
def test_output_wire_array_init_scalar(ctx):
    """
    WireArray をラップして初期化した際、値が正しく透くか確認。
    """
    count = 5
    init_val = 10
    width = 8

    # 1. Target作成
    target = WireArray(count=count, width=width, init=init_val)

    # 2. OutputWireArray作成
    arr = OutputWireArray(target)

    # 配列の長さ確認
    assert len(arr) == count

    # 各要素の確認
    for i, out in enumerate(arr):
        out._set_context(f"out{i}", None, ctx)
        assert isinstance(out, OutputWire)
        assert out._get_width() == width
        assert out.w == init_val  # Targetの値が見えているか


def test_output_wire_array_init_list_padding(ctx):
    """
    リスト初期化された WireArray をラップした場合の確認。
    """
    # Target (Paddingあり)
    target = WireArray(count=3, width=8, init=[0xAA, 0xBB])

    arr = OutputWireArray(target)

    for i, out in enumerate(arr):
        out._set_context(f"out{i}", None, ctx)

    # インデックスアクセス
    assert arr[0].w == 0xAA
    assert arr[1].w == 0xBB
    assert arr[2].w == 0x00  # Paddingも反映されているか


def test_output_wire_array_init_tuple(ctx):
    """
    タプル初期化された WireArray をラップした場合の確認。
    """
    target = WireArray(count=3, width=8, init=(0x1, 0x2))
    arr = OutputWireArray(target)

    for out in arr:
        out._set_context("out", None, ctx)

    assert arr[0].w == 0x1
    assert arr[1].w == 0x2
    assert arr[2].w == 0x0


def test_output_wire_array_init_default():
    """
    デフォルト(0)の WireArray をラップした場合の確認。
    """
    target = WireArray(count=2, width=4)
    arr = OutputWireArray(target)

    assert arr[0].w == 0
    assert arr[1].w == 0


# =================================================================
# 2. アクセスと操作 (_SignalArray functionality)
# =================================================================
def test_output_wire_array_getitem_index(ctx):
    """
    インデックスアクセスのテスト。
    """
    target = WireArray(count=3, width=8, init=[10, 20, 30])
    arr = OutputWireArray(target)

    # 正のインデックス
    assert arr[0].w == 10
    assert arr[2].w == 30

    # 負のインデックス
    assert arr[-1].w == 30


def test_output_wire_array_getitem_tuple_access(ctx):
    """
    タプルアクセス (arr[index, slice]) のテスト。
    OutputWireArray経由でもスライス読み出しができるか。
    """
    target = WireArray(count=2, width=8, init=[0x5A, 0xC3])
    arr = OutputWireArray(target)
    arr[0]._set_context("out", None, ctx)

    # arr[0, 7:4] -> 0番目の値(0x5A)の上位4ビット
    # 期待値: 0101 -> 0x5
    slice_val = arr[0, 7:4]
    assert slice_val == 0x5

    # arr[1, 7] -> 1番目の値(0xC3)の 7ビット目
    # 期待値: 1
    bit_val = arr[1, 7]
    assert bit_val == 1


def test_output_wire_array_iter(ctx):
    """
    __iter__ のテスト。
    """
    init_vals = [1, 2, 3]
    target = WireArray(count=3, width=8, init=init_vals)
    arr = OutputWireArray(target)

    extracted_vals = [out.w for out in arr]
    assert extracted_vals == init_vals


# =================================================================
# 3. OutputWireArray 固有メソッド & 制約
# =================================================================
def test_output_wire_array_set_array(ctx):
    """
    _set_array メソッドのテスト。
    OutputWire のリストで差し替えられるか確認。
    """
    target = WireArray(count=1, width=8, init=10)
    arr = OutputWireArray(target)
    old_output = arr[0]

    # 新しい OutputWire リストで上書き
    w1 = Wire(width=8, init=99)
    w2 = Wire(width=8, init=100)
    new_outputs = [OutputWire(w1), OutputWire(w2)]

    arr._set_array(new_outputs)

    assert len(arr) == 2
    assert arr[0].w == 99
    assert arr[1].w == 100

    # 古い要素への参照確認
    assert old_output.w == 10


def test_output_wire_array_write_behavior(ctx):
    """
    OutputWireArrayの要素に対する書き込みが正しく機能するか確認。
    """
    target = WireArray(count=1, width=8, init=0x00)
    for w in target:
        w._set_context("t", None, ctx)

    arr = OutputWireArray(target)
    out = arr[0]
    out._set_context("out0", None, ctx)

    # 書き込み
    out.w = 0xFF
    target[0]._commit()
    assert target[0].w == 0xFF

    # スライス書き込み
    # 下位4ビットに 0xA を書き込む
    arr[0, 3:0] = 0xA
    target[0]._commit()
    assert target[0].w == 0xFA  # 上位F + 下位A


def test_output_wire_array_rejects_reg_array(ctx):
    """
    OutputWireArray に RegArray を渡すとエラーになること。
    """
    reg_arr = RegArray(count=2)

    # OutputWire cannot wrap a Reg
    with pytest.raises(TypeError, match="OutputWire cannot wrap a Reg"):
        _ = OutputWireArray(reg_arr)


# =================================================================
# 4. OutputWireArray 階層接続
# =================================================================
def test_output_wire_array_nested_chaining(ctx):
    """
    OutputWireArray をさらに OutputWireArray でラップできるか確認する。
    (WireArray -> OutputWireArray(Mid) -> OutputWireArray(Top))
    """
    # 1. Root (WireArray)
    root = WireArray(count=3, width=8, init=0x00)
    for w in root:
        w._set_context("root", None, ctx)

    # 2. Mid (OutputWireArray)
    mid = OutputWireArray(root)
    # Contextセット (Mid)
    for i, out in enumerate(mid):
        out._set_context(f"mid{i}", None, ctx)

    # 3. Top (OutputWireArray が OutputWireArray をラップ)
    top = OutputWireArray(mid)

    # Contextセット (Top)
    for i, out in enumerate(top):
        out._set_context(f"top{i}", None, ctx)

    # 検証
    assert len(top) == 3

    # Top からの書き込み
    top[0].w = 0xAA
    root[0]._commit()

    # Rootまで伝播するか
    assert root[0].w == 0xAA
    # Midからも見えるか
    assert mid[0].w == 0xAA

    # 内部構造の確認
    assert top[0]._get_signal() is root[0]


def test_output_wire_array_rejects_direct_item_assignment(ctx):
    """
    arr[i] = val (要素そのものの置換) は禁止されていることを確認する。

    値を書き込みたい場合は arr[i].w = val を使うべき。
    もし arr[i] = val を許すと、配列内の OutputWire オブジェクトが
    ただの整数などで上書きされてしまい、回路構造が破壊されるため。
    """
    target = WireArray(count=1, width=8)
    arr = OutputWireArray(target)

    # 1. 整数での上書き禁止
    with pytest.raises(TypeError, match="only supports tuple assignment"):
        arr[0] = 0xFF

    # 2. 別のオブジェクトでの上書きも禁止 (構造が変わるため)
    with pytest.raises(TypeError, match="only supports tuple assignment"):
        arr[0] = OutputWire(Wire(width=8))