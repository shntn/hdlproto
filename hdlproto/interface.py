from .module import Module
from .signal import Wire, Reg, Input, Output


class Interface(Module):
    """SystemVerilogのinterfaceに相当する基底クラス。
    信号の束を定義し、Modportを通じて異なる方向(Input/Output)のビューを提供します。
    """
    pass


class Modport:
    """SystemVerilogのmodportに相当するクラス。
    Interface内の信号に対して、特定の方向(Input/Output)を持つポート群を定義します。
    """

    def __init__(self, parent_interface: Interface, **port_directions):
        """
        Parameters
        ----------
        parent_interface : Interface
            このModportが属するInterfaceのインスタンス
        **port_directions : dict
            信号名と方向クラス(Input/Output)のペア
            例: clk=Input, data=Output
        """
        self._parent = parent_interface
        self._ports = {}

        for name, direction_cls in port_directions.items():
            if not hasattr(parent_interface, name):
                raise AttributeError(f"Interface '{type(parent_interface).__name__}' has no signal named '{name}'")

            target_signal = getattr(parent_interface, name)

            if direction_cls not in (Input, Output):
                raise TypeError(f"Modport direction must be Input or Output, got {direction_cls}")

            # ここで動的に Input/Output オブジェクトを生成
            # 注意: この時点では _set_context は呼ばれません。
            # EnvironmentBuilder がモジュールに取り込まれた時点でコンテキストが設定されます。
            port_instance = direction_cls(target_signal)

            # self.clk, self.data などでアクセスできるように属性セット
            setattr(self, name, port_instance)

            # 管理用に保持
            self._ports[name] = port_instance