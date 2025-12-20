import pytest
from hdlproto.signal import Wire
from hdlproto.signal_array import WireArray
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
# 1. 初期化ロジック (Global Functions & __init__)
# =================================================================
def test_wire_array_init_scalar(ctx):
    """
    _make_initialized_data (スカラー分岐) と _make_signal_array のテスト。
    指定された初期値ですべての要素が初期化されるか。
    """
    count = 5
    init_val = 10
    width = 8

    arr = WireArray(count=count, width=width, init=init_val)

    # 配列の長さ確認 (__len__ -> _SignalArray.__len__)
    assert len(arr) == count

    # 各要素の確認 (__iter__ -> _SignalArray.__iter__)
    for i, w in enumerate(arr):
        w._set_context(f"w{i}", None, ctx)
        assert isinstance(w, Wire)
        assert w._get_width() == width
        assert w.w == init_val


def test_wire_array_init_list_padding(ctx):
    """
    _make_initialized_data (リスト分岐) のテスト。
    要素数が足りない場合に 0 でパディングされるか確認。
    """
    # 3つ要求するが、初期値は2つだけ提供
    arr = WireArray(count=3, width=8, init=[0xAA, 0xBB])

    for i, w in enumerate(arr):
        w._set_context(f"w{i}", None, ctx)

    # インデックスアクセス (__getitem__ -> _SignalArray.__getitem__)
    assert arr[0].w == 0xAA
    assert arr[1].w == 0xBB
    assert arr[2].w == 0x00  # パディングされた値


def test_wire_array_init_tuple(ctx):
    """
    _make_initialized_data (タプル分岐) のテスト。
    タプルで渡してもリスト同様に処理されるか。
    """
    arr = WireArray(count=3, width=8, init=(0x1, 0x2))

    for w in arr:
        w._set_context("w", None, ctx)

    assert arr[0].w == 0x1
    assert arr[1].w == 0x2
    assert arr[2].w == 0x0


def test_wire_array_init_default():
    """
    init 引数を省略した場合のデフォルト動作 (すべて0) を確認。
    """
    arr = WireArray(count=2, width=4)
    # コンテキストなしでも初期値の読み取りは可能
    assert arr[0].w == 0
    assert arr[1].w == 0


# =================================================================
# 2. アクセスと操作 (_SignalArray functionality)
# =================================================================
def test_wire_array_getitem_index(ctx):
    """
    _SignalArray.__getitem__ のインデックスアクセスのテスト。
    """
    arr = WireArray(count=3, width=8, init=[10, 20, 30])

    # 正のインデックス
    assert arr[0].w == 10
    assert arr[2].w == 30

    # 負のインデックス (Pythonのリスト仕様への委譲確認)
    assert arr[-1].w == 30


def test_wire_array_getitem_tuple_access(ctx):
    """
    _SignalArray.__getitem__ のタプルアクセス (arr[index, slice]) のテスト。
    これにより _SignalArray 内の `if isinstance(key, tuple):` 分岐をカバーする。
    """
    arr = WireArray(count=2, width=8, init=[0x5A, 0xC3])
    arr[0]._set_context("w", None, ctx)

    # arr[0, 7:4] -> 0番目のWireの [7:4] ビットを取得
    # 期待値: 0101 -> 0x5
    slice_val = arr[0, 7:4]
    assert slice_val == 0x5

    # arr[1, 7] -> 1番目のWireの 7ビット目を取得
    # 期待値: 1
    bit_val = arr[1, 7]
    assert bit_val == 1


def test_wire_array_iter(ctx):
    """
    __iter__ のテスト。リスト内包表記などで回せるか。
    """
    init_vals = [1, 2, 3]
    arr = WireArray(count=3, width=8, init=init_vals)

    extracted_vals = [w.w for w in arr]
    assert extracted_vals == init_vals


# =================================================================
# 3. WireArray 固有メソッド
# =================================================================
def test_wire_array_set_array(ctx):
    """
    _set_array メソッドのテスト。
    内部の _base (_SignalArray) が差し替わるか確認。
    """
    arr = WireArray(count=1, width=8, init=10)
    old_wire = arr[0]

    # 新しいリストで上書き
    new_wires = [Wire(width=8, init=99), Wire(width=8, init=100)]
    arr._set_array(new_wires)

    assert len(arr) == 2
    assert arr[0].w == 99
    assert arr[1].w == 100

    # 古い要素への参照は切れているが、オブジェクトとしては残っている
    assert old_wire.w == 10


def test_wire_array_write_behavior(ctx):
    """
    WireArrayの要素に対して書き込みを行い、シミュレーションコンテキストに記録されるか確認。
    (Wireクラスとの結合確認)
    """
    arr = WireArray(count=1, width=8)
    w = arr[0]
    w._set_context("w0", None, ctx)

    # 書き込み
    w.w = 0xFF

    # Contextに記録されたか
    assert len(ctx.write_history) == 1
    assert ctx.write_history[0] is w

    # コミット後の値確認
    w._commit()
    assert w.w == 0xFF