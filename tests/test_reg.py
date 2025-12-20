import pytest
from hdlproto.signal import Reg
from hdlproto.module import Module
from hdlproto.state import Edge

class MockContext:
    def __init__(self):
        self.write_history = []

    def _record_write(self, signal):
        self.write_history.append(signal)

@pytest.fixture
def ctx():
    return MockContext()

class MockModule(Module):
    def __init__(self, name="top"):
        super().__init__()
        self._name = name

@pytest.fixture
def mod():
    return MockModule(name="TestModule")


# =================================================================
# 1. 基本的な読み書きと境界値 (Basic Read/Write & Boundary)
# =================================================================
@pytest.mark.parametrize("width, input_val, expected_val", [
    (4, 0, 0),          # 最小値 (All 0)
    (4, 15, 15),        # 最大値 (All 1)
    (4, 16, 0),         # 最大値 + 1 (オーバーフロー -> マスクされる)
    (4, 0x1F, 0xF),     # 大きな値 -> 下位ビットのみ
    (4, -1, 15),        # 負の数 -> 補数表現としてマスクされる
])

def test_reg_write_boundary(ctx, width, input_val, expected_val):
    """
    Regへの書き込み時のビットマスク処理と境界値の挙動を確認する。
    """
    r = Reg(width=width)
    r._set_context("r", None, ctx)
    r.r = input_val
    r._commit()
    assert r.r == expected_val, f"Value should be {expected_val} for input {input_val}"


@pytest.mark.parametrize("width, key, expected", [
    (8, slice(7, 0), 0xCA),     # 全範囲
    (8, 7, 1),                  # MSB
    (8, 0, 0),                  # LSB
    (8, slice(7, 4), 0xC),      # 上位ニブル
    (8, slice(3, 0), 0xA),      # 下位ニブル
    (8, slice(1, 1), 1),        # 1ビット幅のスライス
    (8, slice(7, 0), 0xCA),     # 全範囲
    (8, slice(4, 7), 0xC),      # 上位ニブル
    (8, slice(0, 3), 0xA),      # 下位ニブル
])

def test_reg_slice_read(ctx, width, key, expected):
    """
    スライスおよびインデックスによる読み出しが正しいか確認する。
    """
    r = Reg(width=width, init=0xCA)  # 1100_1010
    r._set_context("r", None, ctx)
    assert r[key] == expected, "Slice read returned unexpected value"


# =================================================================
# 2. エラーハンドリング (Error Handling)
# =================================================================
@pytest.mark.parametrize("width, key", [
    # --- 単一インデックス ---
    (4, 4),  # 最大値と同じ (0-indexedなのでアウト)
    (4, 5),  # 最大値より大きい
    (4, -1),  # 負の値 (今の実装はPythonの負のインデックス[-1]をサポートせずエラーにする仕様)

    # --- スライス (msb:lsb) ---
    # msb が範囲外
    (4, slice(4, 0)),       # [4:0]
    (4, slice(5, 0)),       # [5:0]
    (4, slice(0, 4)),       # [0:4]
    (4, slice(0, 5)),       # [0:5]

    # lsb が範囲外 (負)
    (4, slice(3, -1)),      # [3:-1]
    (4, slice(-1, 3)),      # [-1:3]

    # msb, lsb 両方範囲外
    (4, slice(10, 5)),
    (4, slice(5, 10)),
])
def test_reg_index_out_of_range(ctx, width, key):
    """
    範囲外アクセス時に AttributeError が発生することを確認する。
    """
    r = Reg(width=width)
    r._set_context("r", None, ctx)

    with pytest.raises(AttributeError, match="Invalid bit range"):
        _ = r[key]


@pytest.mark.parametrize("invalid_key", [
    "string",  # 文字列
    1.5,  # 浮動小数点
    None,  # None
    [1, 2],  # リスト
])
def test_reg_invalid_key_type(ctx, invalid_key):
    """
    不正な型でのアクセス時に TypeError が発生することを確認する。
    """
    r = Reg(width=4)
    r._set_context("r", None, ctx)

    with pytest.raises(TypeError, match="Invalid argument type"):
        _ = r[invalid_key]


# =================================================================
# 3. スライス書き込み (Slice Write - Bit Preservation)
# =================================================================
@pytest.mark.parametrize("width, init_val, slice_key, write_val, expected_val", [
    # -------------------------------------------------------------------------
    # ケース1: 基本的な部分書き換え (Middle bits)
    # -------------------------------------------------------------------------
    # 初期値: 0x00 (0000_0000)
    # 操作:   [5:2] (4bit幅) に 0xF (1111) を書く
    # 期待値: 0011_1100 -> 0x3C
    (8, 0x00, slice(5, 2), 0xF, 0x3C),

    # -------------------------------------------------------------------------
    # ケース2: 他のビットの保護 (Bit Preservation) ★超重要
    # -------------------------------------------------------------------------
    # 初期値: 0xFF (1111_1111) -> 全部1
    # 操作:   [3:0] (下位4bit) に 0x0 (0000) を書く
    # 期待値: 1111_0000 -> 0xF0 (上位4bitが消えていないこと！)
    (8, 0xFF, slice(3, 0), 0x0, 0xF0),

    # 初期値: 0xFF (1111_1111)
    # 操作:   [7:4] (上位4bit) に 0x0 (0000) を書く
    # 期待値: 0000_1111 -> 0x0F (下位4bitが消えていないこと！)
    (8, 0xFF, slice(7, 4), 0x0, 0x0F),

    # 初期値: 0xFF (1111_1111)
    # 操作:   [4:3] (中間2bit) に 0 (00) を書く
    # 期待値: 111_00_111 -> 0xE7 (両端が残っていること)
    (8, 0xFF, slice(4, 3), 0x0, 0xE7),

    # -------------------------------------------------------------------------
    # ケース3: 書き込み値のマスク機能 (Masking)
    # -------------------------------------------------------------------------
    # スライス幅よりも大きい値を書いた場合、溢れた上位ビットは無視されるべき。
    # 幅:     2bit ([1:0])
    # 書く値: 0xF (1111) -> 幅2bitなので実際は "11" (3) だけが書かれるはず
    # 初期値: 0x00
    # 期待値: 0000_0011 -> 0x03
    (8, 0x00, slice(1, 0), 0xF, 0x03),

    # -------------------------------------------------------------------------
    # ケース4: 単一ビット書き込み (Single Bit)
    # -------------------------------------------------------------------------
    # 初期値: 0x00
    # 操作:   [2] (3ビット目) に 1 を立てる
    # 期待値: 0000_0100 -> 0x04
    (8, 0x00, 2, 1, 0x04),

    # 初期値: 0xFF
    # 操作:   [0] (LSB) を 0 に落とす
    # 期待値: 1111_1110 -> 0xFE
    (8, 0xFF, 0, 0, 0xFE),
])
def test_reg_slice_write(ctx, width, init_val, slice_key, write_val, expected_val):
    """
    スライス書き込み時に、対象ビット以外が保持され、書き込み値がマスクされることを確認する。
    """
    r = Reg(width=width, init=init_val)
    r._set_context("r", None, ctx)
    r[slice_key] = write_val
    r._commit()
    assert r.r == expected_val, \
        f"Slice write failed. Expected {hex(expected_val)}, got {hex(r.r)}"


# =================================================================
# 4. コミット遅延 (Delayed Commit)
# =================================================================
def test_reg_delayed_update(ctx):
    """
    Regへの書き込みは即時反映されず、_commit() を呼んで初めて反映されること。
    """
    # 1. 初期化 (初期値: 0x00)
    r = Reg(width=8, init=0x00)
    r._set_context("r", None, ctx)

    assert r.r == 0x00, "Initial value must be 0x00"

    # 2. 値を書き込む (0xFF)
    r.r = 0xFF

    # 3. 【重要】commit前なので、読み出せる値はまだ「古い値(0x00)」のままであること
    assert r.r == 0x00, "Value must not change before commit is called"

    # 4. コミット実行
    r._commit()

    # 5. 【重要】commit後なので、値が「新しい値(0xFF)」になっていること
    assert r.r == 0xFF, "Value must be updated to 0xFF after commit"


def test_slice_write_delayed_update(ctx):
    """
    スライス書き込みの場合も、同様に遅延反映されること。
    """
    # 初期値: 0x00
    r = Reg(width=8, init=0x00)
    r._set_context("r", None, ctx)

    # 下位4ビットに 0xF を書く
    r[3:0] = 0xF

    # まだ 0 のはず
    assert r.r == 0x00, "Whole value must not change immediately after slice write"
    # 部分読み出ししても 0 のはず
    assert r[3:0] == 0x0, "Slice read must return the old value before commit"

    r._commit()

    # 反映されているはず
    assert r.r == 0x0F, "Whole value must be updated after commit"
    assert r[3:0] == 0xF, "Slice read must return the new value after commit"

# =================================================================
# 5. スナップショットと変化検出 (Snapshot & Change Detection)
# =================================================================
@pytest.mark.parametrize("start_val, end_val, expected_change", [
    (0, 1, True),   # 0 -> 1: 変化あり
    (1, 0, True),   # 1 -> 0: 変化あり
    (0, 0, False),  # 0 -> 0: 変化なし
    (1, 1, False),  # 1 -> 1: 変化なし
])
def test_snapshot_change_detection(ctx, start_val, end_val, expected_change):
    """
    epsilon, delta, cycle の各スナップショットメソッドが、
    値の変化を正しく検出できるかを検証する。
    """
    # 1. 初期値 start_val で初期化
    r = Reg(width=1, init=start_val)
    r._set_context("r", None, ctx)

    # 2. スナップショットを取得（現在の値 start_val をキャプチャ）
    #    テストのため、3種類すべてのスナップショットをここで取得します。
    r._snapshot_epsilon()
    r._snapshot_delta()
    r._snapshot_cycle()

    # 3. 値を end_val に更新してコミット
    r.r = end_val
    r._commit()

    # 4. Epsilon の検証
    if expected_change:
        assert r._is_epsilon_changed() is True, \
            f"Epsilon should detect change from {start_val} to {end_val}"
    else:
        assert r._is_epsilon_changed() is False, \
            f"Epsilon should NOT detect change from {start_val} to {end_val}"

    # 5. Delta の検証
    if expected_change:
        assert r._is_delta_changed() is True, \
            f"Delta should detect change from {start_val} to {end_val}"
    else:
        assert r._is_delta_changed() is False, \
            f"Delta should NOT detect change from {start_val} to {end_val}"

    # 6. Cycle の検証
    if expected_change:
        assert r._is_cycle_changed() is True, \
            f"Cycle should detect change from {start_val} to {end_val}"
    else:
        assert r._is_cycle_changed() is False, \
            f"Cycle should NOT detect change from {start_val} to {end_val}"


@pytest.mark.parametrize("start_val, end_val, expected_pos, expected_neg", [
    (0, 1, True, False),   # 立ち上がり (Rising Edge)
    (1, 0, False, True),   # 立ち下がり (Falling Edge)
    (0, 0, False, False),  # Low安定
    (1, 1, False, False),  # High安定
])
def test_cycle_edge_detection(ctx, start_val, end_val, expected_pos, expected_neg):
    """
    cycle スナップショットが、立ち上がり(POS)・立ち下がり(NEG)エッジを
    正しく判定できるかを検証する。
    """
    # 1. 初期化
    r = Reg(width=1, init=start_val)
    r._set_context("r", None, ctx)

    # 2. cycle スナップショットを取得
    r._snapshot_cycle()

    # 3. 値を更新
    r.r = end_val
    r._commit()

    # 4. 立ち上がりエッジ (POS) の検証
    is_pos = r._equal_cycle_edge(Edge.POS)
    assert is_pos == expected_pos, \
        f"POS edge detection failed for {start_val} -> {end_val}"

    # 5. 立ち下がりエッジ (NEG) の検証
    is_neg = r._equal_cycle_edge(Edge.NEG)
    assert is_neg == expected_neg, \
        f"NEG edge detection failed for {start_val} -> {end_val}"

# =================================================================
# 6. コンテキスト
# =================================================================
# =================================================================
# 1. 基本的なコンテキスト設定 (Wire / Reg)
# =================================================================
def test_reg_context_setting(ctx, mod):
    """
    Regに対して _set_context を呼ぶと、名前・モジュール・シミュレータが
    正しく保持されることを確認する。
    """
    r = Reg(width=8)

    # まだ設定されていない状態
    assert r._get_name() is None, "Name should be None before setting context"

    # コンテキスト設定
    r._set_context(name="my_signal", module=mod, sim_context=ctx)

    # 検証
    assert r._get_name() == "my_signal", \
        "Name must match the value passed to _set_context"

    # 内部属性の確認（直接アクセス）
    assert r._module is mod, "Module reference must match"
    assert r._sim_context is ctx, "Simulation context reference must match"

# =================================================================
# 3. 書き込み時のコンテキスト呼び出し確認
# =================================================================
def test_write_triggers_context_record(ctx, mod):
    """
    信号に書き込みを行った際、設定されたシミュレーションコンテキストの
    _record_write() が呼び出されることを確認する。
    """
    r = Reg()
    r._set_context("active_reg", mod, ctx)

    # 1. 値を書き込む
    r.r = 1

    # 2. MockContextに記録が残っているか確認
    assert len(ctx.write_history) == 1, \
        "_record_write should be called exactly once"
    assert ctx.write_history[0] is r, \
        "The signal instance passed to _record_write should be the Reg itself"

    # 3. スライス書き込みの場合
    r[0] = 0
    assert len(ctx.write_history) == 2, \
        "_record_write should be called again for slice write"

# =================================================================
# 7. 内部インターフェース
# =================================================================
def test_internal_is_reg(ctx):
    """
    _is_reg が正しく返すか確認する。
    """
    r = Reg()
    r._set_context("r", None, ctx)

    # Reg は True を返すはず
    assert r._is_reg is True

def test_internal_getters(ctx):
    """
    _get_signal, _get_width, _get_value が正しく
    内部状態や自身のインスタンスを返すか確認する。
    """
    init_val = 0xAA
    width = 8
    r = Reg(width=width, init=init_val)
    r._set_context("r", None, ctx)

    # 1. _get_signal() は自分自身(self)を返す仕様
    #    (ラッパーが皮を剥ぐために使用される)
    assert r._get_signal() is r, \
        "_get_signal() should return the Reg instance itself"

    # 2. _get_width() は設定したビット幅を返す
    assert r._get_width() == width, \
        f"_get_width() should return {width}"

    # 3. _get_value() は現在のコミット済み値を返す
    assert r._get_value() == init_val, \
        f"_get_value() should return initial value {init_val}"


def test_internal_write_flow(ctx):
    """
    _write() メソッドが内部の pending 状態を更新し、
    _commit() 後に _get_value() に反映される一連の流れを確認する。
    """
    r = Reg(width=8, init=0x00)
    r._set_context("r", None, ctx)

    # 1. _write() を呼び出す
    #    注: .r = 0xFF と違い、_writeは直接呼んでも _record_write チェックを行わないが、
    #    機能としては pending に書き込む。
    r._write(0xFF)

    # 2. まだコミットしていないので、_get_value() は古い値のまま
    assert r._get_value() == 0x00, \
        "_get_value() should return old value before commit"

    # 3. コミット実行
    r._commit()

    # 4. 値が反映されているか
    assert r._get_value() == 0xFF, \
        "_get_value() should return new value after commit"

def test_internal_bit_access(ctx):
    """
    _read_bits() と _write_bits() が正しくビット操作を行えるか確認する。
    """
    # 初期値: 1100_0011 (0xC3)
    r = Reg(width=8, init=0xC3)
    r._set_context("r", None, ctx)

    # --- _read_bits のテスト ---

    # 上位4ビット [7:4] -> 1100 (0xC)
    val_upper = r._read_bits(slice(7, 4))
    assert val_upper == 0xC, \
        "_read_bits() should correctly extract upper nibble"

    # 特定ビット [1] -> 1
    val_bit1 = r._read_bits(1)
    assert val_bit1 == 1, \
        "_read_bits() should correctly extract single bit"

    # --- _write_bits のテスト ---

    # 下位4ビット [3:0] に 0xF (1111) を書き込む
    # 期待値: 1100_1111 (0xCF)
    r._write_bits(slice(3, 0), 0xF)

    # まだ反映されていない
    assert r._get_value() == 0xC3, \
        "Value should not change before commit"

    # コミットして確認
    r._commit()
    assert r._get_value() == 0xCF, \
        "Value should reflect bitwise write after commit"


# =================================================================
# 8. 追加のエッジケース (Additional Edge Cases)
# =================================================================

def test_reg_defaults(ctx):
    """
    引数なしで初期化した時のデフォルト値を確認する。
    仕様: width=1, init=0
    """
    r = Reg()  # デフォルト
    r._set_context("r", None, ctx)

    assert r._get_width() == 1, "Default width should be 1"
    assert r.r == 0, "Default init value should be 0"


def test_slice_write_negative(ctx):
    """
    スライスに対して負の数を書き込んだ場合も、正しくマスクされるか確認する。
    """
    # 8bit: 0000_0000
    r = Reg(width=8, init=0)
    r._set_context("r", None, ctx)

    # [3:0] に -1 (通常は ...1111) を書き込む -> 0xF (1111) になるはず
    r[3:0] = -1
    r._commit()

    assert r.r == 0x0F, "Negative value written to slice should be masked correctly"


def test_write_invalid_type(ctx):
    """
    書き込み時に int 以外を渡した場合の挙動確認。
    (Pythonのビット演算仕様に依存するが、TypeErrorが出ることを期待)
    """
    r = Reg(width=8)
    r._set_context("r", None, ctx)

    with pytest.raises(TypeError):
        r.r = "invalid_string"

    with pytest.raises(TypeError):
        r[3:0] = None