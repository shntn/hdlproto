from hdlproto import *

class ProgramCounter(Module):
    def __init__(self, clk, n_clr, cp, ep, pc_out):
        self.clk = InputWire(clk)
        self.n_clr = InputWire(n_clr)
        self.cp = InputWire(cp)
        self.ep = InputWire(ep)
        self.pc_out = OutputWire(pc_out)
        self.pc = Reg(init=0, width=4)
        self.pc_next = Wire(init=0, width=4)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def sequential_circuit(self):
        if not self.n_clr.w:
            self.pc.r = 0
        else:
            self.pc.r = self.pc_next.w

    @always_comb
    def combinational_circuit(self):
        self.pc_next.w = self.pc.r

        # リセット
        if not self.n_clr.w:
            self.pc_next.w = 0

        # PC 更新
        if self.n_clr.w and self.cp.w:
            self.pc_next.w = self.pc.r + 1

        # PC 出力
        if self.ep.w:
            self.pc_out[3:0] = self.pc.r


class InputAndMemoryAddressRegister(Module):
    def __init__(self, clk, n_lm, ain, a):
        self.clk = InputWire(clk)
        self.n_lm = InputWire(n_lm)
        self.ain = InputWire(ain)
        self.a = OutputWire(a)
        self.a_reg = Reg(init=0, width=4)
        self.a_reg_next = Wire(init=0, width=4)
        self.select_a = Wire(init=0, width=4)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def sequential_circuit(self):
        self.a_reg.r = self.a_reg_next.w

    @always_comb
    def combinational_circuit(self):
        self.a_reg_next.w = self.a_reg.r

        # アドレスを選択
        if self.n_lm.w:
            self.select_a.w = self.a_reg.r
        else:
            self.select_a.w = self.ain[3:0]

        # 選択した A をラッチ
        self.a_reg_next.w = self.select_a.w

        # アドレス出力
        self.a.w = self.a_reg.r


class Ram(Module):
    def __init__(self, clk, a, n_ce, d):
        self.clk = InputWire(clk)
        self.a = InputWire(a)
        self.n_ce = InputWire(n_ce)
        self.d = OutputWire(d)
        self.memory = RegArray(count=16, width=8, init=[
                   # addr  inst        Acc     B-Reg   Out-Reg
            0x09,  # 0x0   LDA  0x9    0x02    0x00    0x00
            0x1A,  # 0x1   ADD  0xA    0x05    0x03    0x00
            0x1B,  # 0x2   ADD  0xB    0x0A    0x05    0x00
            0x2C,  # 0x3   SUB  0xC    0x06    0x04    0x00
            0xE0,  # 0x4   OUT         0x06    0x04    0x06
            0xF0,  # 0x5   HALT
            0x00,  # 0x6
            0x00,  # 0x7
            0x00,  # 0x8
            0x02,  # 0x9
            0x03,  # 0xA
            0x05,  # 0xB
            0x04,  # 0xC
            0x00,  # 0xD
            0x00,  # 0xE
            0x00  # 0xF
        ])
        super().__init__()

    @always_comb
    def combinational_circuit(self):
        if not self.n_ce.w:
            self.d.w = self.memory[self.a[3:0]].r


class InstructionRegister(Module):
    def __init__(self, clk, clr, d, n_li, n_ei, inst, imm):
        self.clk = InputWire(clk)
        self.clr = InputWire(clr)
        self.d = InputWire(d)
        self.n_li = InputWire(n_li)
        self.n_ei = InputWire(n_ei)
        self.inst = OutputWire(inst)
        self.imm = OutputWire(imm)
        self.inst_latch = Reg(init=0, width=4)
        self.imm_latch = Reg(init=0, width=4)
        self.data = Wire(init=0, width=8)
        self.inst_next = Wire(init=0, width=4)
        self.imm_next = Wire(init=0, width=4)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def sequential_circuit(self):
        if self.clr.w:
            self.inst_latch.r = 0
            self.imm_latch.r = 0
        else:
            self.inst_latch.r = self.inst_next.w
            self.imm_latch.r = self.imm_next.w

    @always_comb
    def combinational_circuit(self):
        self.inst_next.w = self.inst_latch.r
        self.imm_next.w = self.imm_latch.r

        # リセット
        if self.clr.w:
            self.inst_next.w = 0
            self.imm_next.w = 0

        # ラッチするデータを選択
        if self.n_li.w:
            self.data[7:4] = self.inst_latch.r
            self.data[3:0] =self.imm_latch.r
        else:
            self.data.w = self.d.w

        # ラッチ
        if not self.clr.w:
            self.inst_next.w = self.data[7:4]
            self.imm_next.w = self.data[3:0]

        # ラッチしたデータを出力
        if not self.n_ei.w:
            self.inst.w = self.inst_latch.r
            self.imm.w = (self.imm.w & 0xF0) | self.imm_latch.r


class ControllerSequencer(Module):
    def __init__(self, clk, n_clr, inst, cp, ep, n_lm, n_ce, n_li, n_ei, n_la, ea, su, eu, n_lb, n_lo, n_halt):
        self.clk = InputWire(clk)
        self.n_clr = InputWire(n_clr)
        self.inst = InputWire(inst)
        self.cp = OutputWire(cp)
        self.ep = OutputWire(ep)
        self.n_lm = OutputWire(n_lm)
        self.n_ce = OutputWire(n_ce)
        self.n_li = OutputWire(n_li)
        self.n_ei = OutputWire(n_ei)
        self.n_la = OutputWire(n_la)
        self.ea = OutputWire(ea)
        self.su = OutputWire(su)
        self.eu = OutputWire(eu)
        self.n_lb = OutputWire(n_lb)
        self.n_lo = OutputWire(n_lo)
        self.n_halt = OutputWire(n_halt)
        self.t = Reg(init=0, width=4)  # 0 = T1, ..., 5 = T6
        self.t_next = Wire(init=0, width=4)
        self.inst_lda = Wire(init=0, width=1)
        self.inst_add = Wire(init=0, width=1)
        self.inst_sub = Wire(init=0, width=1)
        self.inst_out = Wire(init=0, width=1)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def sequential_circuit(self):
        if not self.n_clr.w:
            self.t.r = 0
        else:
            self.t.r = self.t_next.w

    @always_comb
    def combinational_circuit(self):
        self.t_next.w = self.t.r

        # Tステートを更新
        if self.n_clr.w:
            if self.t.r == 5:
                self.t_next.w = 0
            else:
                self.t_next.w = self.t.r + 1
        else:
            self.t_next.w = 0

        # inst から命令をデコード
        self.inst_lda.w = self.inst.w == 0x0
        self.inst_add.w = self.inst.w == 0x1
        self.inst_sub.w = self.inst.w == 0x2
        self.inst_out.w = self.inst.w == 0xE
        self.n_halt.w = not (self.inst.w == 0xF)

        # 制御信号
        self.cp.w = self.t.r== 1
        self.ep.w = self.t.r == 0
        self.n_lm.w = not ((self.t.r == 0)
                            or (self.t.r == 3 and self.inst_lda.w)
                            or (self.t.r == 3 and self.inst_add.w)
                            or (self.t.r == 3 and self.inst_sub.w))
        self.n_ce.w = not ((self.t.r == 2)
                            or (self.t.r == 4 and self.inst_lda.w)
                            or (self.t.r == 4 and self.inst_add.w)
                            or (self.t.r == 4 and self.inst_sub.w))
        self.n_li.w = not self.t.r == 2
        self.n_ei.w = not ((self.t.r == 3 and self.inst_lda.w)
                            or (self.t.r == 3 and self.inst_add.w)
                            or (self.t.r == 3 and self.inst_sub.w))
        self.n_la.w = not ((self.t.r == 4 and self.inst_lda.w)
                            or (self.t.r == 5 and self.inst_add.w)
                            or (self.t.r == 5 and self.inst_sub.w))
        self.ea.w = self.t.r == 3 and self.inst_out.w
        self.su.w = self.t.r == 5 and self.inst_sub.w
        self.eu.w = ((self.t.r == 5 and self.inst_add.w)
                      or (self.t.r == 5 and self.inst_sub.w))
        self.n_lb.w = not ((self.t.r == 4 and self.inst_add.w)
                            or (self.t.r == 4 and self.inst_sub.w))
        self.n_lo.w = not (self.t.r == 3 and self.inst_out.w)



class Accumulator(Module):
    def __init__(self, clk, din, n_la, ea, dout_to_bus, dout_to_alu):
        self.clk = InputWire(clk)
        self.din = InputWire(din)
        self.n_la = InputWire(n_la)
        self.ea = InputWire(ea)
        self.dout_to_bus = OutputWire(dout_to_bus)
        self.dout_to_alu = OutputWire(dout_to_alu)
        self.data = Reg(init=0, width=8)
        self.data_next = Wire(init=0, width=8)
        self.data_in = Wire(init=0, width=8)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def sequential_circuit(self):
        self.data.r = self.data_next.w

    @always_comb
    def combinational_circuit(self):
        self.data_next.w = self.data.r

        # 入力データ選択
        if self.n_la.w:
            self.data_in.w = self.data.r
        else:
            self.data_in.w = self.din.w

        # ラッチ
        self.data_next.w = self.data_in.w

        # 出力選択
        self.dout_to_alu.w = self.data.r
        if self.ea.w:
            self.dout_to_bus.w = self.data.r


class AdderSubtractor(Module):
    def __init__(self, clk, din1, din2, su, eu, data_out):
        self.clk = InputWire(clk)
        self.din1 = InputWire(din1)
        self.din2 = InputWire(din2)
        self.su = InputWire(su)
        self.eu = InputWire(eu)
        self.data_out = OutputWire(data_out)
        self.op2 = Wire(init=0, width=8)
        super().__init__()

    @always_comb
    def combinational_circuit(self):
        # Bレジスタから入力する値の選択
        if self.su.w:
            self.op2.w = -self.din2.w
        else:
            self.op2.w = self.din2.w

        # 加算
        result = self.din1.w + self.op2.w

        # 出力選択
        if self.eu.w:
            self.data_out.w = result


class BRegister(Module):
    def __init__(self, clk, din, n_lb, dout):
        self.clk = InputWire(clk)
        self.din = InputWire(din)
        self.n_lb = InputWire(n_lb)
        self.dout = OutputWire(dout)
        self.data = Reg(init=0, width=8)
        self.data_next = Wire(init=0, width=8)
        self.data_in = Wire(init=0, width=8)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def sequential_circuit(self):
        self.data.r = self.data_next.w

    @always_comb
    def combinational_circuit(self):
        self.data_next.w = self.data.r

        # 入力データ選択
        if self.n_lb.w:
            self.data_in.w = self.data.r
        else:
            self.data_in.w = self.din.w

        # ラッチ
        self.data_next.w = self.data_in.w

        # 出力選択
        self.dout.w = self.data.r


class OutputRegister(Module):
    def __init__(self, clk, din, n_lo, dout):
        self.clk = InputWire(clk)
        self.din = InputWire(din)
        self.n_lo = InputWire(n_lo)
        self.dout = OutputWire(dout)
        self.data = Reg(init=0, width=8)
        self.data_next = Wire(init=0, width=8)
        self.data_in = Wire(init=0, width=8)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def sequential_circuit(self):
        self.data.r = self.data_next.w

    @always_comb
    def combinational_circuit(self):
        self.data_next.w = self.data.r

        # 入力データ選択
        if self.n_lo.w:
            self.data_in.w = self.data.r
        else:
            self.data_in.w = self.din.w

        # ラッチ
        self.data_next.w = self.data_in.w

        # 出力選択
        self.dout.w = self.data.r


class BinaryDisplay(Module):
    def __init__(self, clk, din):
        self.clk = InputWire(clk)
        self.din = InputWire(din)
        self.data = Reg(init=0, width=8)
        self.data_next = Wire(init=0, width=8)
        super().__init__()

    @always_ff((Edge.POS, 'clk'))
    def sequential_circuit(self):
        self.data.r = self.data_next.w

    @always_comb
    def combinational_circuit(self):
            self.data_next.w = self.din.w


class Sap1(Module):
    def __init__(self, clk, clr):
        self.clk = InputWire(clk)
        self.clr = InputWire(clr)

        # 生成信号
        self.n_clr = Wire(init=1)
        self.mar_out = Wire(init=0, width=4)
        self.inst = Wire(init=0, width=4)
        self.n_halt = Wire(init=1)
        self.acc_out = Wire(init=0, width=8)
        self.breg_out = Wire(init=0, width=8)
        self.or_out = Wire(init=0, width=8)

        # bus
        self.bus = Wire(init=0, width=8)

        # control signals
        self.cp = Wire(init=0)
        self.ep = Wire(init=0)
        self.n_lm = Wire(init=1)
        self.n_ce = Wire(init=1)
        self.n_li = Wire(init=1)
        self.n_ei = Wire(init=1)
        self.n_la = Wire(init=0)
        self.ea = Wire(init=0)
        self.su = Wire(init=0)
        self.eu = Wire(init=0)
        self.n_lb = Wire(init=1)
        self.n_lo = Wire(init=1)

        # モジュール
        self.m_pc = None
        self.m_mar = None
        self.m_ram = None
        self.m_ir = None
        self.m_cs = None
        self.m_acc = None
        self.m_alu = None
        self.m_breg = None
        self.m_or = None
        self.m_bd = None

        # Program Counter
        self.m_pc = ProgramCounter(self.clk, self.n_clr, self.cp, self.ep, self.bus)

        self.m_mar = InputAndMemoryAddressRegister(self.clk, self.n_lm, self.bus, self.mar_out)

        self.m_ram = Ram(self.clk, self.mar_out, self.n_ce, self.bus)

        self.m_ir = InstructionRegister(self.clk, self.clr, self.bus, self.n_li, self.n_ei, self.inst,self.bus)

        self.m_cs = ControllerSequencer(
                        self.clk,
                        self.n_clr, self.inst,
                        self.cp, self.ep, self.n_lm, self.n_ce, self.n_li,
                        self.n_ei, self.n_la, self.ea, self.su, self.eu,
                        self.n_lb, self.n_lo, self.n_halt)

        self.m_acc = Accumulator(self.clk, self.bus, self.n_la, self.ea, self.bus, self.acc_out)

        self.m_alu = AdderSubtractor(self.clk, self.acc_out, self.breg_out, self.su, self.eu, self.bus)

        self.m_breg = BRegister(self.clk, self.bus, self.n_lb, self.breg_out)

        self.m_or = OutputRegister(self.clk, self.bus, self.n_lo, self.or_out)

        self.m_bd = BinaryDisplay(self.clk, self.or_out)

        super().__init__()

    @always_comb
    def combinational_circuit(self):
        self.n_clr.w = not self.clr.w


class tbSAP1(TestBench):
    def __init__(self):
        self.clk = Wire()
        self.clr = Wire(init=1)
        self.sap1 = Sap1(self.clk, self.clr)
        super().__init__()

    def run(self, simulator):

        for i in range(6*6):
            self.clr.w = 0
            simulator.clock()


if __name__ == "__main__":
    tb = tbSAP1()
    vcd = VCDWriter()
    sim = Simulator(testbench=tb, clock=tb.clk, vcd=vcd)
    vcd.open("sap1.vcd")
    tb.run(sim)
    vcd.close()
