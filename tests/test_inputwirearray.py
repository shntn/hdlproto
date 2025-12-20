import pytest
from hdlproto.signal import Wire, InputWire
from hdlproto.signal_array import WireArray, InputWireArray, OutputWireArray, RegArray
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
def test_input_wire_array_init_scalar(ctx):
    """
    WireArray をラップして初期化した際、値が正しく透くか確認。
    """
    count = 5
    init_val = 10
    width = 8

    # 1. Target作成
    target = WireArray(count=count, width=width, init=init_val)

    # 2. InputWireArray作成
    arr = InputWireArray(target)

    # 配列の長さ確認
    assert len(arr) == count

    # 各要素の確認
    for i, inp in enumerate(arr):
        inp._set_context(f"in{i}", None, ctx)
        assert isinstance(inp, InputWire)
        assert inp._get_width() == width
        assert inp.w == init_val  # Targetの値が見えているか


def test_input_wire_array_init_list_padding(ctx):
    """
    リスト初期化された WireArray をラップした場合の確認。
    """
    # Target (Paddingあり)
    target = WireArray(count=3, width=8, init=[0xAA, 0xBB])

    arr = InputWireArray(target)

    for i, inp in enumerate(arr):
        inp._set_context(f"in{i}", None, ctx)

    # インデックスアクセス
    assert arr[0].w == 0xAA
    assert arr[1].w == 0xBB
    assert arr[2].w == 0x00  # Paddingも反映されているか


def test_input_wire_array_init_tuple(ctx):
    """
    タプル初期化された WireArray をラップした場合の確認。
    """
    target = WireArray(count=3, width=8, init=(0x1, 0x2))
    arr = InputWireArray(target)

    for inp in arr:
        inp._set_context("in", None, ctx)

    assert arr[0].w == 0x1
    assert arr[1].w == 0x2
    assert arr[2].w == 0x0


def test_input_wire_array_init_default():
    """
    デフォルト(0)の WireArray をラップした場合の確認。
    """
    target = WireArray(count=2, width=4)
    arr = InputWireArray(target)

    assert arr[0].w == 0
    assert arr[1].w == 0


# =================================================================
# 2. アクセスと操作 (_SignalArray functionality)
# =================================================================
def test_input_wire_array_getitem_index(ctx):
    """
    インデックスアクセスのテスト。
    """
    target = WireArray(count=3, width=8, init=[10, 20, 30])
    arr = InputWireArray(target)

    # 正のインデックス
    assert arr[0].w == 10
    assert arr[2].w == 30

    # 負のインデックス
    assert arr[-1].w == 30


def test_input_wire_array_getitem_tuple_access(ctx):
    """
    タプルアクセス (arr[index, slice]) のテスト。
    InputWireArray経由でもスライス読み出しができるか。
    """
    target = WireArray(count=2, width=8, init=[0x5A, 0xC3])
    arr = InputWireArray(target)
    arr[0]._set_context("in", None, ctx)

    # arr[0, 7:4] -> 0番目の値(0x5A)の上位4ビット
    # 期待値: 0101 -> 0x5
    slice_val = arr[0, 7:4]
    assert slice_val == 0x5

    # arr[1, 7] -> 1番目の値(0xC3)の 7ビット目
    # 期待値: 1
    bit_val = arr[1, 7]
    assert bit_val == 1


def test_input_wire_array_iter(ctx):
    """
    __iter__ のテスト。
    """
    init_vals = [1, 2, 3]
    target = WireArray(count=3, width=8, init=init_vals)
    arr = InputWireArray(target)

    extracted_vals = [inp.w for inp in arr]
    assert extracted_vals == init_vals


# =================================================================
# 3. InputWireArray 固有メソッド & 制約
# =================================================================
def test_input_wire_array_set_array(ctx):
    """
    _set_array メソッドのテスト。
    InputWire のリストで差し替えられるか確認。
    """
    target = WireArray(count=1, width=8, init=10)
    arr = InputWireArray(target)
    old_input = arr[0]

    # 新しい InputWire リストで上書き
    w1 = Wire(width=8, init=99)
    w2 = Wire(width=8, init=100)
    new_inputs = [InputWire(w1), InputWire(w2)]

    arr._set_array(new_inputs)

    assert len(arr) == 2
    assert arr[0].w == 99
    assert arr[1].w == 100

    # 古い要素への参照確認
    assert old_input.w == 10


def test_input_wire_array_write_behavior_readonly(ctx):
    """
    InputWireArrayの要素に対する書き込みが禁止されているか確認。
    (Write Behavior テストの Read-only 版)
    """
    target = WireArray(count=1, width=8)
    arr = InputWireArray(target)
    inp = arr[0]
    inp._set_context("in0", None, ctx)

    # 書き込み禁止 (AttributeError)
    with pytest.raises(AttributeError):
        inp.w = 0xFF

    # スライス書き込み禁止
    with pytest.raises((TypeError, AttributeError)):
        arr[0, 3:0] = 0xF


def test_input_wire_array_rejects_reg_array(ctx):
    """
    InputWireArray に RegArray を渡すとエラーになること。
    """
    reg_arr = RegArray(count=2)

    # 配列生成時に内部で InputWire(Reg) を作ろうとしてエラーになるはず
    with pytest.raises(TypeError, match="Input\(Reg\) is not allowed"):
        _ = InputWireArray(reg_arr)

# =================================================================
# 4. InputWireArray 階層接続
# =================================================================
def test_input_wire_array_nested_chaining(ctx):
    """
    InputWireArray をさらに InputWireArray でラップできるか確認する。
    (WireArray -> InputWireArray(Mid) -> InputWireArray(Top))
    """
    # 1. Root (WireArray)
    root = WireArray(count=3, width=8, init=0x55)
    for w in root:
        w._set_context("root", None, ctx)

    # 2. Mid (InputWireArray)
    mid = InputWireArray(root)
    # Contextセット (Mid)
    for i, inp in enumerate(mid):
        inp._set_context(f"mid{i}", None, ctx)

    # 3. Top (InputWireArray が InputWireArray をラップ)
    #    ※ 型ヒントは WireArray だが、Pythonの仕様上イテラブルなら通る
    top = InputWireArray(mid)

    # Contextセット (Top)
    for i, inp in enumerate(top):
        inp._set_context(f"top{i}", None, ctx)

    # 検証
    assert len(top) == 3

    # 値の透過確認
    assert top[0].w == 0x55

    # Rootの値変更
    root[0].w = 0xAA
    root[0]._commit()

    # Topまで伝播するか
    assert top[0].w == 0xAA

    # 内部構造の確認: Top の中身は InputWire であり、そのターゲットは RootのWire であること
    # (InputWireの仕様で、皮をむいて実体につなぎ直しているはず)
    assert top[0]._get_signal() is root[0]


def test_input_wire_array_from_output_wire_array(ctx):
    """
    InputWireArray が OutputWireArray をラップできるか確認する。
    (WireArray -> OutputWireArray(Mid) -> InputWireArray(Top))

    これは、OutputWireArrayが駆動している信号を、
    InputWireArrayでモニターする（読み取る）ような構成を想定。
    """
    # 1. Root (WireArray)
    root = WireArray(count=3, width=8, init=0x00)
    for w in root:
        w._set_context("root", None, ctx)

    # 2. Mid (OutputWireArray)
    #    OutputWireArrayはWireArrayをラップする
    mid = OutputWireArray(root)
    for i, out in enumerate(mid):
        out._set_context(f"mid{i}", None, ctx)

    # 3. Top (InputWireArray wraps OutputWireArray)
    #    OutputWireArrayはWireをラップしているので、InputWireArrayはそれを受け入れられるはず
    #    InputWire(OutputWire(Wire)) という構造になる
    top = InputWireArray(mid)

    for i, inp in enumerate(top):
        inp._set_context(f"top{i}", None, ctx)

    # 配列としての長さ確認
    assert len(top) == 3

    # --- 動作確認 ---

    # 1. OutputWireArray (Mid) 経由で書き込む
    mid[0].w = 0xAA
    root[0]._commit()

    # Rootに反映されているか
    assert root[0].w == 0xAA

    # InputWireArray (Top) から読み出せるか
    assert top[0].w == 0xAA

    # 2. Root に直接書き込む
    root[1].w = 0xBB
    root[1]._commit()

    # Top から読み出せるか (OutputWireを透してWireの値が見えるか)
    assert top[1].w == 0xBB

    # 3. 内部構造確認
    # Top(InputWire)の実体(_get_signal)は、最終的にRoot(Wire)を指していること
    assert top[0]._get_signal() is root[0]