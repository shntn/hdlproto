# HDLproto

純Pythonで動作する「前RTL」向けの軽量シミュレータです。
外部依存なしで、HDLの前段（仕様～アーキテクチャ検討）における信号タイミングや制御ロジックの妥当性を素早く検証できます。

- 直感的なAPI: `@always_ff`/`@always_comb` と `.r`/`.w` を使って、HDLの設計規律をそのまま表現
- イベント駆動の安全性: 規約違反や多重ドライブ、非収束など典型的な落とし穴を例外で検知
- 導入容易: 純Pythonのみで動作（学習・教材・プロトタイピングに最適）

## インストール

### PyPIからのインストール

```bash
pip install hdlproto
```

### 開発版のインストール

```bash
git clone https://github.com/shntn/hdlproto.git
cd hdlproto
pip install -e .
```

### 要件

- Python 3.10 以上

## ドキュメント

HDLproto のより詳細な使い方、特に Verilog の経験がある方向けの解説は、こちらの[スタートガイド](doc/getting_started.jp.md)をご覧ください。

## クイックスタート（最小サンプル）

以下を `quickstart.py` に保存して実行してください。

```
from hdlproto import *

class Counter(Module):
    def __init__(self, en, out):
        self.en = Input(en)
        self.out = Output(out)
        self.cnt = Reg(init=0, width=4)
        self.cnt_next = Wire(init=0, width=4)
        super().__init__()

    @always_ff  # edge を省略すると posedge
    def seq(self, reset):
        if reset:
            self.cnt.r = 0
        elif self.en.w:
            self.cnt.r = self.cnt_next.w

    @always_comb
    def comb(self):
        self.cnt_next.w = (self.cnt.r + 1) % 16
        self.out.w = self.cnt.r

class TbCounter(TestBench):
    def __init__(self):
        self.en = Wire(init=1)
        self.out = Wire(init=0, width=4)
        self.dut = Counter(self.en, self.out)
        super().__init__()

    @testcase
    def run(self, simulator):
        for i in range(6):
            if i == 3:  # 途中で停止
                self.en.w = 0
            simulator.clock()
            print(f"cycle={i}, out={self.out.w}")

if __name__ == "__main__":
    sim = Simulator(SimConfig(), TbCounter())
    sim.reset()
    sim.testcase("run")

# 出力:
# cycle=0, out=1
# cycle=1, out=2
# cycle=2, out=3
# cycle=3, out=3
# cycle=4, out=3
# cycle=5, out=3
```

実行イメージ:
- 1クロック内で `@always_ff`（レジスタ更新）→`@always_comb`（ワイヤ更新）の順に評価
- `i==3` で `en` を 0 に落とすと、カウントが止まります
- `Simulator.clock(edge='pos')` でクロックエッジを選べます。`@always_ff(edge='neg')` と `sim.clock(edge='neg')` を使えばネゲッジ駆動も可能です。

## 設計規律（重要）

- `@always_ff(edge='pos' | 'neg')`: `Reg` への書き込み（`.r`）のみ有効。`edge` を省略すると `'pos'`（立上り）になります。
- `@always_comb`: `Wire`/`Output` への書き込み（`.w`）。`Reg` へ書くと例外
- `Simulator.clock(edge='pos')` でどちらのエッジを評価するか指定できます。`clock()` は `edge='pos'` の省略形です。
- リセットは通常の `Input` 信号として扱ってください（例: `self.rst = Wire(...)`）。`@always_ff` に渡される `reset` 引数は下位互換のために残されていますが、自前のリセット線のみを使っても問題ありません。
- 安定化ループ: `@always_comb` は信号が安定するまで繰り返し評価。非収束時は例外

## 主な例外

- `SignalInvalidAccess`: フェーズ違反の書き込み（例: COMBでReg、FFでWire を書く）
- `SignalWriteConflict`: 同一信号を複数の `always_*` が駆動
- `SignalUnstableError`: 組合せが所定回数で安定しない（ループやフィードバックの可能性）

## 付属サンプル

- `example/ex_module.py`: もう少しリッチな入門例
- `example/ex_sap1.py`: 前RTLの演習に最適な SAP-1 実装例
- `example/ex_exception.py`: 例外（規約違反や競合）の再現スクリプト

## ライセンス

- ライセンス: MIT License
