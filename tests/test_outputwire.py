import pytest
import pickle
from hdlproto.signal import Wire, Reg, OutputWire
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


def setup_nested_output_wire(ctx, width=8, init=0):
    """
    テスト用ヘルパー: OutputWire(top) -> OutputWire(mid) -> Wire(root) を構築して返す。
    戻り値: (root_wire, top_output_wire)
    """
    # 1. 実体 (Root)
    root = Wire(width=width, init=init)
    root._set_context("root_wire", None, ctx)

    # 2. 中間 (Mid)
    mid = OutputWire(root)
    mid._set_context("mid_port", None, ctx)

    # 3. 最上位 (Top) - テスト対象
    top = OutputWire(mid)
    top._set_context("top_port", None, ctx)

    return root, top

# =================================================================
# 1. 基本的な値の透過性 (Pass-through)
# =================================================================
def test_output_wire_pass_through(ctx):
    """
    OutputWireへの書き込みが、ターゲットとなるWireへ
    正しく反映されることを確認する。
    """
    # ターゲット作成
    target = Wire(width=8, init=0x00)
    target._set_context("target_wire", None, ctx)

    # OutputWire作成
    out = OutputWire(target)
    out._set_context("out_port", None, ctx)

    # 1. 初期値の確認
    assert out.w == 0x00, "Should reflect target initial value"

    # 2. OutputWireの値を変更 (InputWireとは逆: out -> target)
    out.w = 0xFF
    # OutputWireへの書き込みは即時反映ではなくコミット待ちになるため、実体をコミット
    target._commit()

    # 3. ターゲット経由で確認
    assert out.w == 0xFF, "Target should reflect updated OutputWire value"
    assert out._get_width() == 8, "Should reflect target width"

def test_output_wire_slice_write(ctx):
    """
    OutputWireに対するスライス書き込みが、ターゲットへのスライス操作として
    正しく委譲されるか確認する。
    """
    target = Wire(width=8, init=0xCA)
    target._set_context("target", None, ctx)

    out = OutputWire(target)
    out._set_context("out_port", None, ctx)

    # 上位4ビットへの書き込み
    assert target[7:4] == 0xC, "Slice write delegation failed (upper)"
    out[7:4] = 0x3
    target._commit()
    assert out[7:4] == 0x3, "Slice write delegation failed (upper)"
    assert target[7:4] == 0x3, "Slice write delegation failed (upper)"

    # 下位4ビットへの書き込み
    assert out[3:0] == 0xA, "Slice write delegation failed (lower)"
    out[3:0] = 0x5
    target._commit()
    assert out[3:0] == 0x5, "Slice write delegation failed (lower)"
    assert target[3:0] == 0x5, "Slice write delegation failed (lower)"

    # ビット指定への書き込み
    assert out[7] == 0, "Index read delegation failed"
    assert target[7] == 0, "Index read delegation failed"
    out[7] = 1
    target._commit()
    assert out[7] == 1, "Index write delegation failed"
    assert target[7] == 1, "Index write delegation failed"


# =================================================================
# 2. 制約とエラーハンドリング (Constraints & Errors)
# =================================================================
def test_output_wire_rejects_reg(ctx):
    """
    OutputWire は Reg をラップできない仕様（TypeError）であることを確認する。
    """
    r = Reg(width=8)

    # エラーメッセージを実際のOutputWireの実装に合わせて修正
    with pytest.raises(TypeError, match="OutputWire cannot wrap a Reg"):
        _ = OutputWire(r)


def test_output_wire_invalid_write_type(ctx):
    """
    OutputWireへの書き込み時に、不正な型（文字列など）が弾かれるか確認する。
    """
    target = Wire(width=8)
    out = OutputWire(target)
    # 書き込みを行う前に必ずコンテキストを設定する (AttributeError回避)
    out._set_context("out_port", None, ctx)

    # 不正な型への代入禁止 (TypeError)
    with pytest.raises(TypeError):
        out.w = "invalid"

    # スライスへの不正な代入禁止
    with pytest.raises(TypeError):
        out[3:0] = None


# =================================================================
# 3. スナップショット
# =================================================================
# -----------------------------------------------
# 1. Epsilon Snapshot の独立性確認
# -----------------------------------------------
def test_output_wire_snapshot_epsilon_only(ctx):
    """
    OutputWire._snapshot_epsilon() を呼んだ時、
    epsilonだけが更新され、deltaやcycleには影響しないことを確認する。
    """
    # 1. 初期化 (値: 0)
    target = Wire(width=1, init=0)
    target._set_context("t", None, ctx)
    out = OutputWire(target)

    # 全てのスナップショットを初期値(0)で揃える
    target._snapshot_epsilon()
    target._snapshot_delta()
    target._snapshot_cycle()

    # 2. 値を更新 (値: 1)
    target.w = 1
    target._commit()

    # 3. OutputWire経由で Epsilon だけスナップショットを撮る
    out._snapshot_epsilon()

    # 4. 検証
    # Epsilon: 最新の値(1)を取り込んだので、現在値(1)と同じ -> 「変化なし(False)」になるべき
    assert out._is_epsilon_changed() is False, \
        "Epsilon history should be updated to current value"

    # Delta: まだ取り込んでいない(0)ので、現在値(1)と違う -> 「変化あり(True)」のままのはず
    assert out._is_delta_changed() is True, \
        "Delta history should NOT be updated (function swap check)"

    # Cycle: まだ取り込んでいない -> 「変化あり」のままのはず
    assert out._is_cycle_changed() is True, \
        "Cycle history should NOT be updated"


# -----------------------------------------------
# 2. Delta Snapshot の独立性確認
# -----------------------------------------------
def test_output_wire_snapshot_delta_only(ctx):
    """
    OutputWire._snapshot_delta() を呼んだ時、
    deltaだけが更新されることを確認する。
    """
    target = Wire(width=1, init=0)
    target._set_context("t", None, ctx)
    out = OutputWire(target)

    target._snapshot_epsilon()
    target._snapshot_delta()
    target._snapshot_cycle()

    # 値を更新
    target.w = 1
    target._commit()

    # OutputWire経由で Delta だけ撮る
    out._snapshot_delta()

    # 検証
    assert out._is_delta_changed() is False, "Delta history should be updated"

    # 他は更新されていないこと
    assert out._is_epsilon_changed() is True, "Epsilon should NOT be updated"
    assert out._is_cycle_changed() is True, "Cycle should NOT be updated"


# -----------------------------------------------
# 3. Cycle Snapshot の独立性確認
# -----------------------------------------------
def test_output_wire_snapshot_cycle_only(ctx):
    """
    OutputWire._snapshot_cycle() を呼んだ時、
    cycleだけが更新されることを確認する。
    """
    target = Wire(width=1, init=0)
    target._set_context("t", None, ctx)
    out = OutputWire(target)

    target._snapshot_epsilon()
    target._snapshot_delta()
    target._snapshot_cycle()

    # 値を更新
    target.w = 1
    target._commit()

    # OutputWire経由で Cycle だけ撮る
    out._snapshot_cycle()

    # 検証
    assert out._is_cycle_changed() is False, "Cycle history should be updated"

    # 他は更新されていないこと
    assert out._is_epsilon_changed() is True, "Epsilon should NOT be updated"
    assert out._is_delta_changed() is True, "Delta should NOT be updated"


# -----------------------------------------------
# 4. Edge Detection (POS/NEG) の委譲確認
# -----------------------------------------------
def test_output_wire_edge_detection_rising(ctx):
    """
    OutputWire 経由で、立ち上がりエッジ (0 -> 1) が正しく判定されるか確認する。
    """
    # 1. 初期化 (0)
    target = Wire(width=1, init=0)
    target._set_context("t", None, ctx)
    out = OutputWire(target)

    # 2. Cycleスナップショット (過去の値 = 0)
    target._snapshot_cycle()

    # 3. 値を更新 (現在の値 = 1)
    target.w = 1
    target._commit()

    # 4. 検証
    # POS (立ち上がり) は検出されるべき
    assert out._equal_cycle_edge(Edge.POS) is True, \
        "Rising edge (0->1) should be detected as POS"

    # NEG (立ち下がり) は検出されてはいけない
    assert out._equal_cycle_edge(Edge.NEG) is False, \
        "Rising edge (0->1) should NOT be detected as NEG"


def test_output_wire_edge_detection_falling(ctx):
    """
    OutputWire 経由で、立ち下がりエッジ (1 -> 0) が正しく判定されるか確認する。
    """
    # 1. 初期化 (1)
    target = Wire(width=1, init=1)
    target._set_context("t", None, ctx)
    out = OutputWire(target)

    # 2. Cycleスナップショット (過去の値 = 1)
    target._snapshot_cycle()

    # 3. 値を更新 (現在の値 = 0)
    target.w = 0
    target._commit()

    # 4. 検証
    # NEG (立ち下がり) は検出されるべき
    assert out._equal_cycle_edge(Edge.NEG) is True, \
        "Falling edge (1->0) should be detected as NEG"

    # POS (立ち上がり) は検出されてはいけない
    assert out._equal_cycle_edge(Edge.POS) is False, \
        "Falling edge (1->0) should NOT be detected as POS"


# =================================================================
# 4. 内部APIとメタデータ (Internal API)
# =================================================================
def test_output_wire_internal_attributes(ctx):
    """
    内部的な属性やメソッドが正しく委譲されているか確認する。
    """
    target = Wire(width=4)
    target._set_context("t", None, ctx)

    out = OutputWire(target)
    out._set_context("p", None, ctx)

    # _is_reg プロパティ (OutputWireはWire専用なのでFalse)
    assert out._is_reg is False

    # _get_signal() は「皮を剥いた」中身（ターゲットの実体）を返す仕様
    assert out._get_signal() is target


def test_output_wire_name_formatting(ctx):
    """
    OutputWireの名前解決が 'port_name(target_name)' 形式になるか確認する。
    """
    target = Wire()
    target._set_context("internal_sig", None, ctx)

    out = OutputWire(target)
    out._set_context("port_a", None, ctx)

    assert out._get_name() == "port_a(internal_sig)"


# =================================================================
# OutputWire ネスト構成 (Chain Delegation) の統合テスト
# =================================================================

def test_nested_pass_through_and_slice(ctx):
    """
    ネストされたOutputWireを通して、値の書き込みとスライス操作が
    最下層のWireまで正しく届くか確認する。
    """
    root, top = setup_nested_output_wire(ctx, width=8, init=0x55)

    # 1. 初期値の確認
    assert top.w == 0x55, "Should reflect root value"
    assert top._get_width() == 8, "Should reflect root width"

    # 2. Topへの書き込み (InputWireとは逆: Top -> Root)
    top.w = 0xCA  # 1100_1010
    top._commit()

    # 3. Rootへの反映確認
    assert top.w == 0xCA, "Should reflect updated top value to top"
    assert root.w == 0xCA, "Should reflect updated top value to root"

    # 4. スライス書き込みの委譲確認
    # --- 修正箇所: 変化がわかるように値を変更 ---
    # 上位4ビットに 0x0 を書く (元はC) -> 0x0A になるはず
    top[7:4] = 0x0
    root._commit()
    assert top.w == 0x0A, "Slice write delegation failed (upper)"
    assert root.w == 0x0A, "Slice write delegation failed (upper)"

    # 下位4ビットに 0xF を書く (元はA) -> 0x0F になるはず
    top[3:0] = 0xF
    root._commit()
    assert top.w == 0x0F, "Slice write delegation failed (lower)"
    assert root.w == 0x0F, "Slice write delegation failed (lower)"

    # ビット指定
    top[7] = 1  # -> 1000 1111 = 0x8F
    root._commit()
    assert top[7] == 1, "Index write delegation failed"
    assert root[7] == 1, "Index write delegation failed"
    assert root.w == 0x8F


def test_nested_constraints_and_internal_api(ctx):
    """
    ネスト状態でも、不正な型の書き込み禁止や内部API(_get_signal)が正しく機能するか確認する。
    """
    root, top = setup_nested_output_wire(ctx)

    # 1. 不正な型の書き込み禁止 (TypeError)
    with pytest.raises(TypeError):
        top.w = "invalid"

    with pytest.raises(TypeError):
        top[3:0] = None

    # 2. _is_reg の委譲
    assert top._is_reg is False, "Nested OutputWire should report _is_reg as False"

    # 3. _get_signal() の再帰的解決
    # OutputWire -> OutputWire -> Wire なので、皮を剥いて最後の Wire が返るべき
    assert top._get_signal() is root, \
        "_get_signal() should verify recursively and return the root Wire"


def test_nested_snapshot_isolation(ctx):
    """
    ネストされたOutputWire経由でスナップショットを撮った際、
    関数が入れ替わらず、正しく最下層まで命令が届くか確認する。
    """
    root, top = setup_nested_output_wire(ctx, width=1, init=0)

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
    ネストされたOutputWire経由で、エッジ検出(POS/NEG)が正しく判定されるか確認する。
    """
    root, top = setup_nested_output_wire(ctx, width=1, init=0)

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
def test_output_wire_getnewargs_direct_call():
    """
    __getnewargs__ が、コンストラクタ (__init__) に渡すべき引数を
    正しくタプルとして返しているか確認する。
    """
    target = Wire(width=8)
    out = OutputWire(target)

    # メソッドを直接コール
    args = out.__getnewargs__()

    # 検証
    assert isinstance(args, tuple), "Return value must be a tuple"
    assert len(args) == 1, "Should contain exactly 1 argument (target)"
    assert args[0] is target, "The argument should be the target wire instance"


def test_output_wire_pickle_roundtrip(ctx):
    """
    実際に pickle (シリアライズ) して復元できるかを確認する統合テスト。
    """
    # ターゲット (値: 0xAA)
    target = Wire(width=8, init=0xAA)
    target._set_context("t", None, ctx)

    out = OutputWire(target)

    # 1. シリアライズ (保存)
    dumped_data = pickle.dumps(out)

    # 2. デシリアライズ (復元)
    restored_out = pickle.loads(dumped_data)

    # 3. 検証
    assert isinstance(restored_out, OutputWire), "Restored object should be OutputWire"
    assert restored_out.w == 0xAA, "Restored object should retain the value"

    # pickleの仕様上、実体は別物になる
    assert restored_out._get_signal() is not target, "Pickle creates a copy of the target"
    assert restored_out._get_signal().w == 0xAA, "Copied target should have the same value"