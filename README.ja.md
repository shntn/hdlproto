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


## 設計規律（重要）

- `@always_ff((Edge.POS, 'clk'), ...)`: `Reg` へのノンブロッキング代入（`.r`での書き込み）のみ有効。指定した信号のエッジに反応する順序回路を記述します。
- `@always_comb`: `Wire`/`Output` への書き込み（`.w`）。`Reg` へ書くと例外。
- `Simulator.clock()` は `SimConfig` で指定されたクロック信号を駆動します。クロック信号はトップモジュールで `Input` として受け取り、`TestBench` で `Wire` として定義する必要があります。
- リセットは入力信号として扱います。非同期リセットは `@always_ff` のトリガーリストにリセット信号を追加することで実現します（例: `@always_ff((Edge.POS, 'clk'), (Edge.POS, 'reset'))`）。同期リセットは、クロックエッジでのみ動作する `always_ff` ブロック内でリセット条件を記述します。
- 収束ループ: `@always_comb` は信号が安定するまで再評価されます。収束しない場合は例外が発生します。


## 付属サンプル

- `example/ex_module.py`: もう少しリッチな入門例
- `example/ex_sap1.py`: 前RTLの演習に最適な SAP-1 実装例
- `example/ex_exception.py`: 例外（規約違反や競合）の再現スクリプト

## ライセンス

- ライセンス: MIT License
