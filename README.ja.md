# HDLproto

純Pythonで動作する「前RTL」向けの軽量シミュレータです。
外部依存なしで、HDLの前段（仕様～アーキテクチャ検討）における信号タイミングや制御ロジックの妥当性を素早く検証できます。

- 直感的なAPI: `@always_ff`/`@always_comb` と `.r`/`.w` を使って、HDLの設計規律をそのまま表現
- イベント駆動の安全性: 規約違反や多重ドライブ、非収束など典型的な落とし穴を例外で検知
- 導入容易: 純Pythonのみで動作（学習・教材・プロトタイピングに最適）

### HDLprotoについて（前提と位置づけ）

HDLprotoは、HDL（Verilog/SystemVerilog）風の記述をPython上で模擬するための軽量シミュレーションフレームワークです。
HDLの構文や文法を厳密に再現するものではなく、`always_comb` / `always_ff` や `Wire` / `Reg` といった
「ハードウェアの動作モデル」をPythonで簡潔に試すためのプロトタイピング環境を提供します。

### HDLprotoの目的

HDLprotoは次のような用途を想定して設計されています。

*   CPUのマイクロアーキテクチャ設計の検証
*   小規模なデジタル回路の動作確認
*   制御ユニットやステートマシン（FSM）の試作
*   HDL設計前の「アイデア検証・データフロー整理」
*   教育・学習用途での `always_ff` / `always_comb` の動作理解

Pythonだけで「HDLらしい振る舞い」を気軽に表現し、検証できることが最大の目的です。

### HDLprotoが目指していないこと（非サポート）

*   Verilog / VHDL / SystemVerilogへのコード生成
*   FPGA / ASIC向けの論理合成
*   タイミング解析や論理最適化
*   数千〜数万信号を超えるような大規模RTLの実装

HDLprotoはあくまでプロトタイプ用のシミュレーション環境であり、FPGA等に書き込めるRTLを生成するツールではありません。

### 主な特徴

*   PythonだけでHDL風のモジュールや信号を構築できる
*   `always_comb` と `always_ff` の動作を忠実に模擬
*   `Wire`/`Reg` の伝搬と安定化ループをシミュレータが自動処理
*   モジュール・信号の依存関係を自動分析してシミュレーションを実行
*   小規模CPU（SAP-1やZ80サブセット等）の動作も再現可能

### 想定ユーザー

*   CPUやデジタル回路のプロトタイプを素早く作りたい方
*   HDL設計の前にデータフローやアルゴリズムを検証したい方
*   ハードウェア記述言語の概念を学びたいエンジニアや学生
*   Verilogを書けない状況でもハードウェア的思考で設計したい方
*   Pythonの柔軟性を活かして実験的な回路を試したい方

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

### インストールせずに動作確認

```bash
git clone https://github.com/shntn/hdlproto.git
cd hdlproto
PYTHONPATH=. python3 example/ex_sap1.py
```

### 要件

- Python 3.10 以上

## ドキュメント

HDLproto のより詳細な使い方、特に Verilog の経験がある方向けの解説は、こちらの[スタートガイド](doc/source/getting_started.ja.md)をご覧ください。

## クイックスタート（最小サンプル）

以下を `quickstart.py` に保存して実行してください。

```
from hdlproto import *

class Counter(Module):
    def __init__(self, clk, reset, en, out):
        self.clk = Input(clk)
        self.reset = Input(reset)
        self.en = Input(en)
        self.out = Output(out)
        self.cnt = Reg(init=0, width=4)
        self.cnt_next = Wire(init=0, width=4)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def seq(self):
        if self.reset.w:
            self.cnt.r = 0
        elif self.en.w:
            self.cnt.r = self.cnt_next.w

    @always_comb
    def comb(self):
        self.cnt_next.w = (self.cnt.r + 1) % 16
        self.out.w = self.cnt.r

class TbCounter(TestBench):
    def __init__(self):
        self.clk = Wire()
        self.reset = Wire()
        self.en = Wire(init=1)
        self.out = Wire(init=0, width=4)
        self.dut = Counter(self.clk, self.reset, self.en, self.out)
        super().__init__()

    @testcase
    def run(self, simulator):
        self.reset.w = 1
        simulator.clock()
        self.reset.w = 0
        for i in range(6):
            if i == 3:  # 途中で停止
                self.en.w = 0
            simulator.clock()
            print(f"cycle={i}, out={self.out.w}")

if __name__ == "__main__":
    tb = TbCounter()
    config = SimConfig(clock=tb.clk)
    sim = Simulator(config, tb)
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
- 1クロック内で `@always_ff`（レジスタ更新）と `@always_comb`（ワイヤ更新）を評価
- `i==3` で `en` を 0 に落とすと、カウントが止まります
- `Simulator.clock()` で1クロック進みます。`Simulator.half_clock(1)` or `Simulator.half_clock(0)` でエッジを選べます。

## 設計規律（重要）

- `@always_ff((Edge.POS, 'clk'), ...)`: `Reg` へのノンブロッキング代入（`.r`での書き込み）のみ有効。指定した信号のエッジに反応する順序回路を記述します。
- `@always_comb`: `Wire`/`Output` への書き込み（`.w`）。`Reg` へ書くと例外。
- `Simulator.clock()` は `SimConfig` で指定されたクロック信号を駆動します。クロック信号はトップモジュールで `Input` として受け取り、`TestBench` で `Wire` として定義する必要があります。
- リセットは入力信号として扱います。非同期リセットは `@always_ff` のトリガーリストにリセット信号を追加することで実現します（例: `@always_ff((Edge.POS, 'clk'), (Edge.POS, 'reset'))`）。同期リセットは、クロックエッジでのみ動作する `always_ff` ブロック内でリセット条件を記述します。
- 収束ループ: `@always_comb` は信号が安定するまで再評価されます。収束しない場合は例外が発生します。

## @always_ff の変更点

`@always_ff` デコレータの仕様が更新され、より柔軟なトリガー指定が可能になりました。

```python
class MyModule(Module):
    def __init__(self, clk, reset_n):
        self.clk = Input(clk)
        self.reset_n = Input(reset_n)
        self.count = Reg(init=0, width=4)
        super().__init__()

    # クロックの立ち上がりエッジと、リセットの立ち下がりエッジでトリガー
    @always_ff((Edge.POS, 'clk'), (Edge.NEG, 'reset_n'))
    def counter(self):
        if not self.reset_n.w: # reset_n が 0 の時にリセット
            self.count.r = 0
        else:
            self.count.r = self.count.r + 1
```

主な変更点は以下の通りです。

*   **トリガー指定方法の変更**: 従来の `edge='pos'` 引数による指定は廃止され、`(Edge, 'signal_name')` というタプルのリストでトリガーを指定する方法に統一されました。
*   **複数トリガーのサポート**: クロックと非同期リセットのように、複数の信号エッジをトリガーとして指定できるようになりました。`Edge.POS`（立ち上がり）と `Edge.NEG`（立ち下がり）を自由に組み合わせられます。
*   **信号名の文字列指定**: トリガーとなる信号は、モジュール内で定義された属性名（例: `'clk'`, `'reset_n'`）を文字列で指定します。

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
