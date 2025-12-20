import pytest
import pickle
from hdlproto.signal import Wire, Reg, InputWire
from hdlproto.module import Module
from hdlproto.state import Edge

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

@pytest.fixture
def mod():
    return MockModule(name="TestModule")

def setup_nested_wire(ctx, width=8, init=0):
    """
    テスト用ヘルパー: Wire -> InputWire(mid) -> InputWire(top) を構築して返す。
    戻り値: (root_wire, top_input_wire)
    """
    # 1. 実体 (Root)
    root = Wire(width=width, init=init)
    root._set_context("root_wire", None, ctx)

    # 2. 中間 (Mid)
    mid = InputWire(root)
    mid._set_context("mid_port", None, ctx)

    # 3. 最上位 (Top) - テスト対象
    top = InputWire(mid)
    top._set_context("top_port", None, ctx)

    return root, top

# =================================================================
# 1. 基本的な値の透過性 (Pass-through)
# =================================================================
def test_input_wire_pass_through(ctx):
    """
    ターゲットとなるWireの値が変化した時、InputWire経由でも
    同じ値が読み出せることを確認する。
    """
    # ターゲット作成
    target = Wire(width=8, init=0x55)
    target._set_context("target_wire", None, ctx)

    # InputWire作成
    inp = InputWire(target)
    inp._set_context("in_port", None, ctx)

    # 1. 初期値の確認
    assert inp.w == 0x55, "Should reflect target initial value"

    # 2. ターゲットの値を変更
    target.w = 0xFF
    inp._commit()

    # 3. InputWire経由で確認
    assert inp.w == 0xFF, "Should reflect updated target value"
    assert inp._get_width() == 8, "Should reflect target width"

def test_input_wire_slice_read(ctx):
    """
    InputWireに対するスライス読み出しが、ターゲットへのスライス操作として
    正しく委譲されるか確認する。
    """
    target = Wire(width=8, init=0xCA)  # 1100_1010
    target._set_context("target", None, ctx)

    inp = InputWire(target)
    inp._set_context("in_port", None, ctx)

    # 上位4ビット
    assert inp[7:4] == 0xC, "Slice read delegation failed"
    # 下位4ビット
    assert inp[3:0] == 0xA, "Slice read delegation failed"
    # ビット指定
    assert inp[7] == 1, "Index read delegation failed"


# =================================================================
# 2. 制約とエラーハンドリング (Constraints & Errors)
# =================================================================
def test_input_wire_rejects_reg(ctx):
    """
    InputWire は Reg をラップできない仕様（TypeError）であることを確認する。
    (InputポートはWireで駆動されるべきというHDL的な制約)
    """
    r = Reg(width=8)

    with pytest.raises(TypeError, match="Input\(Reg\) is not allowed"):
        _ = InputWire(r)


def test_input_wire_is_read_only(ctx):
    """
    InputWire は読み取り専用であり、書き込み操作が禁止されていることを確認する。
    """
    target = Wire(width=8)
    inp = InputWire(target)

    # .w への代入禁止 (setterが定義されていないため AttributeError)
    with pytest.raises(AttributeError):
        inp.w = 0xFF

    # スライスへの代入禁止 (__setitem__ が委譲されていない、あるいは定義されていない)
    # Pythonの仕様上、__setitem__がないオブジェクトへの代入は TypeError または AttributeError になる
    with pytest.raises((TypeError, AttributeError)):
        inp[3:0].w = 0xF

# =================================================================
# 3. スナップショット
# =================================================================
# -----------------------------------------------
# 1. Epsilon Snapshot の独立性確認
# -----------------------------------------------
def test_input_wire_snapshot_epsilon_only(ctx):
    """
    InputWire._snapshot_epsilon() を呼んだ時、
    epsilonだけが更新され、deltaやcycleには影響しないことを確認する。
    """
    # 1. 初期化 (値: 0)
    target = Wire(width=1, init=0)
    target._set_context("t", None, ctx)
    inp = InputWire(target)

    # 全てのスナップショットを初期値(0)で揃える
    target._snapshot_epsilon()
    target._snapshot_delta()
    target._snapshot_cycle()

    # 2. 値を更新 (値: 1)
    target.w = 1
    target._commit()

    # この時点では、すべてのスナップショット(0)と現在値(1)が違うため、
    # 全員「変化あり(True)」になるはず。

    # 3. InputWire経由で Epsilon だけスナップショットを撮る
    inp._snapshot_epsilon()

    # 4. 検証
    # Epsilon: 最新の値(1)を取り込んだので、現在値(1)と同じ -> 「変化なし(False)」になるべき
    assert inp._is_epsilon_changed() is False, \
        "Epsilon history should be updated to current value"

    # Delta: まだ取り込んでいない(0)ので、現在値(1)と違う -> 「変化あり(True)」のままのはず
    assert inp._is_delta_changed() is True, \
        "Delta history should NOT be updated (function swap check)"

    # Cycle: まだ取り込んでいない -> 「変化あり」のままのはず
    assert inp._is_cycle_changed() is True, \
        "Cycle history should NOT be updated"

# -----------------------------------------------
# 2. Delta Snapshot の独立性確認
# -----------------------------------------------
def test_input_wire_snapshot_delta_only(ctx):
    """
    InputWire._snapshot_delta() を呼んだ時、
    deltaだけが更新されることを確認する。
    """
    target = Wire(width=1, init=0)
    target._set_context("t", None, ctx)
    inp = InputWire(target)

    target._snapshot_epsilon()
    target._snapshot_delta()
    target._snapshot_cycle()

    # 値を更新
    target.w = 1
    target._commit()

    # InputWire経由で Delta だけ撮る
    inp._snapshot_delta()

    # 検証
    assert inp._is_delta_changed() is False, "Delta history should be updated"

    # 他は更新されていないこと
    assert inp._is_epsilon_changed() is True, "Epsilon should NOT be updated"
    assert inp._is_cycle_changed() is True, "Cycle should NOT be updated"


# -----------------------------------------------
# 3. Cycle Snapshot の独立性確認
# -----------------------------------------------
def test_input_wire_snapshot_cycle_only(ctx):
    """
    InputWire._snapshot_cycle() を呼んだ時、
    cycleだけが更新されることを確認する。
    """
    target = Wire(width=1, init=0)
    target._set_context("t", None, ctx)
    inp = InputWire(target)

    target._snapshot_epsilon()
    target._snapshot_delta()
    target._snapshot_cycle()

    # 値を更新
    target.w = 1
    target._commit()

    # InputWire経由で Cycle だけ撮る
    inp._snapshot_cycle()

    # 検証
    assert inp._is_cycle_changed() is False, "Cycle history should be updated"

    # 他は更新されていないこと
    assert inp._is_epsilon_changed() is True, "Epsilon should NOT be updated"
    assert inp._is_delta_changed() is True, "Delta should NOT be updated"


# -----------------------------------------------
# 4. Edge Detection (POS/NEG) の委譲確認
# -----------------------------------------------
def test_input_wire_edge_detection_rising(ctx):
    """
    InputWire 経由で、立ち上がりエッジ (0 -> 1) が正しく判定されるか確認する。
    """
    # 1. 初期化 (0)
    target = Wire(width=1, init=0)
    target._set_context("t", None, ctx)
    inp = InputWire(target)

    # 2. Cycleスナップショット (過去の値 = 0)
    target._snapshot_cycle()

    # 3. 値を更新 (現在の値 = 1)
    target.w = 1
    target._commit()

    # 4. 検証
    # POS (立ち上がり) は検出されるべき
    assert inp._equal_cycle_edge(Edge.POS) is True, \
        "Rising edge (0->1) should be detected as POS"

    # 【重要】NEG (立ち下がり) は検出されてはいけない
    # もし間違って _is_cycle_changed を呼んでいたら、これも True になってしまうため、このAssertで防ぐ
    assert inp._equal_cycle_edge(Edge.NEG) is False, \
        "Rising edge (0->1) should NOT be detected as NEG"


def test_input_wire_edge_detection_falling(ctx):
    """
    InputWire 経由で、立ち下がりエッジ (1 -> 0) が正しく判定されるか確認する。
    """
    # 1. 初期化 (1)
    target = Wire(width=1, init=1)
    target._set_context("t", None, ctx)
    inp = InputWire(target)

    # 2. Cycleスナップショット (過去の値 = 1)
    target._snapshot_cycle()

    # 3. 値を更新 (現在の値 = 0)
    target.w = 0
    target._commit()

    # 4. 検証
    # NEG (立ち下がり) は検出されるべき
    assert inp._equal_cycle_edge(Edge.NEG) is True, \
        "Falling edge (1->0) should be detected as NEG"

    # POS (立ち上がり) は検出されてはいけない
    assert inp._equal_cycle_edge(Edge.POS) is False, \
        "Falling edge (1->0) should NOT be detected as POS"

# =================================================================
# 4. 内部APIとメタデータ (Internal API)
# =================================================================
def test_input_wire_internal_attributes(ctx):
    """
    内部的な属性やメソッドが正しく委譲されているか確認する。
    """
    target = Wire(width=4)
    target._set_context("t", None, ctx)

    inp = InputWire(target)
    inp._set_context("p", None, ctx)

    # _is_reg プロパティの委譲 (WireをラップしているのでFalseのはず)
    assert inp._is_reg is False

    # _get_signal() は「皮を剥いた」中身（ターゲットの実体）を返す仕様
    # InputWire -> Wire なので、targetそのものが返るはず
    assert inp._get_signal() is target


def test_input_wire_name_formatting(ctx):
    """
    InputWireの名前解決が 'port_name(target_name)' 形式になるか確認する。
    (デバッグ表示用)
    """
    target = Wire()
    target._set_context("internal_sig", None, ctx)

    inp = InputWire(target)
    inp._set_context("port_a", None, ctx)

    assert inp._get_name() == "port_a(internal_sig)"


# =================================================================
# InputWire ネスト構成 (Chain Delegation) の統合テスト
# =================================================================

def test_nested_pass_through_and_slice(ctx):
    """
    ネストされたInputWireを通して、値の読み出しとスライス操作が
    最下層のWireまで正しく届くか確認する。
    """
    root, top = setup_nested_wire(ctx, width=8, init=0x55)

    # 1. 初期値の透過確認
    assert top.w == 0x55, "Should reflect root value through nested layers"
    assert top._get_width() == 8, "Should reflect root width"

    # 2. Rootの値変更
    root.w = 0xCA  # 1100_1010
    root._commit()

    # 3. 更新値の透過確認
    assert top.w == 0xCA, "Should reflect updated root value"

    # 4. スライス読み出しの委譲確認
    # 上位4ビット -> 0xC
    assert top[7:4] == 0xC, "Slice read delegation failed (upper)"
    # 下位4ビット -> 0xA
    assert top[3:0] == 0xA, "Slice read delegation failed (lower)"
    # ビット指定
    assert top[7] == 1, "Index read delegation failed"


def test_nested_constraints_and_internal_api(ctx):
    """
    ネスト状態でも、書き込み禁止制約や内部API(_get_signal)が正しく機能するか確認する。
    """
    root, top = setup_nested_wire(ctx)

    # 1. 書き込み禁止 (Read Only)
    with pytest.raises(AttributeError):
        top.w = 0xFF

    with pytest.raises((TypeError, AttributeError)):
        top[3:0].w = 0xF

    # 2. _is_reg の委譲
    assert top._is_reg is False, "Nested InputWire should report _is_reg as False"

    # 3. _get_signal() の再帰的解決
    # InputWire -> InputWire -> Wire なので、皮を剥いて最後の Wire が返るべき
    assert top._get_signal() is root, \
        "_get_signal() should verify recursively and return the root Wire"


def test_nested_snapshot_isolation(ctx):
    """
    ネストされたInputWire経由でスナップショットを撮った際、
    関数が入れ替わらず、正しく最下層まで命令が届くか確認する。
    """
    root, top = setup_nested_wire(ctx, width=1, init=0)

    # --- 準備: 全て初期値(0)でスナップショット作成 ---
    root._snapshot_epsilon()
    root._snapshot_delta()
    root._snapshot_cycle()

    # 値を更新 (0 -> 1)
    root.w = 1
    root._commit()

    # --- 1. Epsilon だけ呼ぶ ---
    top._snapshot_epsilon()

    # 検証: Epsilonのみ更新され(変化なし判定)、他は更新されない(変化あり判定)
    assert root._is_epsilon_changed() is False, "Epsilon should be updated (via nested call)"
    assert root._is_delta_changed() is True, "Delta should NOT be updated"
    assert root._is_cycle_changed() is True, "Cycle should NOT be updated"

    # --- 2. Delta だけ呼ぶ ---
    top._snapshot_delta()

    assert root._is_delta_changed() is False, "Delta should be updated (via nested call)"
    assert root._is_cycle_changed() is True, "Cycle should NOT be updated"

    # --- 3. Cycle だけ呼ぶ ---
    top._snapshot_cycle()

    assert root._is_cycle_changed() is False, "Cycle should be updated (via nested call)"


def test_nested_edge_detection(ctx):
    """
    ネストされたInputWire経由で、エッジ検出(POS/NEG)が正しく判定されるか確認する。
    """
    root, top = setup_nested_wire(ctx, width=1, init=0)

    # 1. Cycleスナップショット (過去=0)
    top._snapshot_cycle()

    # 2. 立ち上がり (0 -> 1)
    root.w = 1
    root._commit()

    # 検証
    assert top._equal_cycle_edge(Edge.POS) is True, "Rising edge should be detected as POS"
    assert top._equal_cycle_edge(Edge.NEG) is False, "Rising edge should NOT be detected as NEG"

    # 3. 立ち下がり (1 -> 0) の準備
    top._snapshot_cycle()  # 現在の1を保存
    root.w = 0
    root._commit()

    # 検証
    assert top._equal_cycle_edge(Edge.NEG) is True, "Falling edge should be detected as NEG"
    assert top._equal_cycle_edge(Edge.POS) is False, "Falling edge should NOT be detected as POS"

# =================================================================
# __getnewargs__
# =================================================================
def test_input_wire_getnewargs_direct_call():
    """
    __getnewargs__ が、コンストラクタ (__init__) に渡すべき引数を
    正しくタプルとして返しているか確認する。
    """
    target = Wire(width=8)
    inp = InputWire(target)

    # メソッドを直接コール
    args = inp.__getnewargs__()

    # 検証
    assert isinstance(args, tuple), "Return value must be a tuple"
    assert len(args) == 1, "Should contain exactly 1 argument (target)"
    assert args[0] is target, "The argument should be the target wire instance"


def test_input_wire_pickle_roundtrip(ctx):
    """
    実際に pickle (シリアライズ) して復元できるかを確認する統合テスト。
    これが通れば __getnewargs__ が正しく機能している証明になる。
    """
    # ターゲット (値: 0xAA)
    target = Wire(width=8, init=0xAA)
    # Contextにはpickle可能なもの(ここではMockContext)が必要
    target._set_context("t", None, ctx)

    inp = InputWire(target)

    # 1. シリアライズ (保存)
    dumped_data = pickle.dumps(inp)

    # 2. デシリアライズ (復元)
    #    ここで内部的に __getnewargs__ が呼ばれ、新しい InputWire(target_copy) が作られる
    restored_inp = pickle.loads(dumped_data)

    # 3. 検証
    assert isinstance(restored_inp, InputWire), "Restored object should be InputWire"
    assert restored_inp.w == 0xAA, "Restored object should retain the value"

    # pickleの仕様上、デフォルトではターゲットもコピーされるため、実体は別物になる
    assert restored_inp._get_signal() is not target, "Pickle creates a copy of the target"
    assert restored_inp._get_signal().w == 0xAA, "Copied target should have the same value"