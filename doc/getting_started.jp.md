# HDL経験者向け Getting Started ガイド

このガイドは、HDL（特にVerilog）の設計経験を持つ方が、HDLprotoを使って「RTL設計前のプロトタイピング」を迅速に行う方法を学ぶことを目的としています。

## 1. はじめに：HDLprotoのコンセプト

**なぜHDL経験者がHDLprotoを使うべきか？**

HDLprotoは、Verilog/VHDLのような厳密なRTL設計に入る前の段階で、Pythonだけを使ってロジックのアイデアを素早く検証するためのツールです。

- **迅速なプロトタイピング**: 複雑なシミュレータやツールチェーンは不要です。`pip install`だけで、使い慣れたPython環境でハードウェアロジックの記述とテストを始められます。
- **直感的なデバッグ**: Pythonのデバッガ（`pdb`など）や`print`文をそのまま利用して、サイクルの途中の信号の状態を簡単に追跡できます。
- **Pythonエコシステムの活用**: `pytest`による高度なテスト、`matplotlib`による波形描画、`numpy`によるデータ処理など、Pythonの豊富なライブラリとシームレスに連携できます。
- **効率的なテスト環境の構築**: 検証対象のデザイン（DUT）のみをHDLprotoで記述し、メモリモデルやスティミュラス生成などの周辺コンポーネントは通常のPythonクラスや辞書として実装できます。
  これにより、すべてをHDLで記述する場合に比べて、テスト環境の構築を劇的に効率化できます。

## 2. Verilogとの概念マッピング

「いつも使っているVerilogのあの機能は、HDLprotoではどう書くのか？」を以下の表にまとめました。

| Verilog HDL                  | HDLproto                         | 説明                                                                                                   |
| :--------------------------- | :------------------------------- | :----------------------------------------------------------------------------------------------------- |
| `module`                     | `class MyModule(Module):`        | Pythonのクラスとしてモジュールを定義します。                                                           |
| `reg [7:0] data;`            | `self.data = Reg(width=8)`       | クロック同期で値を保持する信号です。                                                                   |
| `wire [7:0] data;`           | `self.data = Wire(width=8)`      | 組み合わせ回路の接続に使われる信号です。                                                               |
| `input clk;`                 | `self.clk = Input(clk)`          | モジュールの入力ポートです。                                                                           |
| `output [3:0] q;`            | `self.q = Output(q)`             | モジュールの出力ポートです。                                                                           |
| `inout [7:0] data;`          | **非サポート**                   | `inout`ポートはサポートされていません。                                                                |
| `always @(posedge clk)`      | `@always_ff`                     | クロック同期の順序回路（Sequential Circuit）を記述するデコレータです。                                 |
| `always @(*)`                | `@always_comb`                   | 組み合わせ回路（Combinational Circuit）を記述するデコレータです。                                      |
| `q <= d;` (ノンブロッキング) | `self.q.r = self.d.w`            | **[順序回路]** `.r` は順序回路の信号を表します。                                                       |
| `q = d;` (ブロッキング)      | **非サポート**                   | **[順序回路]** `@always_ff`内でのブロッキング代入はサポートされていません。                            |
| `y = a & b;` (ブロッキング)  | `self.y.w = self.a.w & self.b.w` | **[組み合わせ回路]** `.w` は組み合わせ回路の信号を表します。                                           |
| `assign y = a & b;`          | **非サポート**                   | `assign`に直接対応する機能はありません。組み合わせ回路の記述には`@always_comb`を使用してください。     |
| `initial begin ... end`      | `@testcase`                      | テストベンチのシーケンスを記述します。                                                                 |

## 3. 実践：カウンタを設計してみる

シンプルな4ビット同期カウンタを例に、HDLprotoとVerilogのコードを比較しながら見ていきましょう。

### Step 1: モジュールの定義

**HDLproto :**

```python
from hdlproto import *

class Counter(Module):
    def __init__(self, rst, en, q_out):
        self.rst = Input(rst)
        self.en = Input(en)
        self.q_out = Output(q_out)

        self.count = Reg(width=4, init=0)
        self.count_next = Wire(width=4)
        super().__init__()
```

- *注: HDLprotoでは clk の定義は不要です*
- *注: HDLprotoは clk, reset ともに posedgeイベントのみサポートしています*

**Verilog :**

```verilog
module Counter (
    input wire clk,
    input wire rst,
    input wire en,
    output wire [3:0] q_out
);
    reg [3:0] count;
    wire [3:0] count_next;
```

### Step 2: 組み合わせ回路

**HDLproto :**

```python
    # (Counterクラス内)
    @always_comb
    def comb_logic(self):
        if self.en.w:
            self.count_next.w = self.count.r + 1
        else:
            self.count_next.w = self.count.r
        
        self.q_out.w = self.count.r
```

**Verilog :**

```verilog
    // (Counterモジュール内)
    always @(*) begin
        if (en) begin
            count_next = count + 1;
        end else begin
            count_next = count;
        end
        q_out = count;
    end
```

### Step 3: 順序回路

**HDLproto :**

```python
    # (Counterクラス内)
    @always_ff
    def seq_logic(self, reset):
        if reset or self.rst.w:
            self.count.r = 0
        else:
            self.count.r = self.count_next.w
```

- *注: `@always_ff`の`reset`引数はシミュレータから与えられます*

**Verilog :**

```verilog
    // (Counterモジュール内)
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            count <= 4'b0;
        end else begin
            count <= count_next;
        end
    end
```

### Step 4: テストベンチとシミュレーション

ここがHDLprotoの大きな利点です。
Verilogの定型的なテストベンチと比較して、Pythonでいかに直感的にテストが書けるかを示します。

**HDLproto :**

```python
class TestCounter(TestBench):
    def __init__(self):
        self.rst = Wire(init=0)
        self.en = Wire(init=0)
        self.q_out = Wire(width=4)
        self.dut = Counter(self.rst, self.en, self.q_out)
        super().__init__()

    @testcase
    def run(self, sim):
        # リセット解除
        self.rst.w = 1
        sim.clock()
        self.rst.w = 0

        # イネーブルを有効にして10サイクル実行
        self.en.w = 1
        for i in range(10):
            print(f"Cycle {i}: q_out = {self.q_out.w}")
            assert self.q_out.w == i
            sim.clock()

if __name__ == "__main__":
    sim = Simulator(SimConfig(), TestCounter())
    sim.reset()
    sim.testcase("run")
```

**Verilog :**

```verilog
    // Verilogのテストベンチはより冗長になりがち
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    initial begin
        rst = 1; #10;
        rst = 0;
        en = 1;
        repeat (10) @(posedge clk);
        $finish;
    end
```

## 4. 次のステップ

基本を理解したら、次はより複雑な設計に挑戦してみましょう。
`example/ex_sap1.py` には、このライブラリを使って実装されたSAP-1（Simple-As-Possible）コンピュータの完全なモデルが含まれています。
階層化されたモジュール設計の良い参考例となるでしょう。