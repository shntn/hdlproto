from typing import Any, Type, Union

from .module import Module
from .signal import InputWire, OutputWire, OutputReg
from .signal_array import InputWireArray, OutputWireArray, OutputRegArray


class Interface(Module):
    """Base class equivalent to SystemVerilog's interface.

    It defines a bundle of signals and provides views with different directions
    (Input/Output) via Modport.
    """
    pass


class Modport:
    """Class equivalent to SystemVerilog's modport.

    It defines a group of ports with specific directions (Input/Output) for
    signals within an Interface.
    """

    def __init__(self,
                 parent_interface: Interface,
                 **port_directions: Union[Type[InputWire], Type[OutputWire], Type[OutputReg], Type[InputWireArray], Type[OutputWireArray], Type[OutputRegArray]]):
        """
        Parameters
        ----------
        parent_interface : Interface
            The Interface instance to which this Modport belongs.
        **port_directions : dict
            Pairs of signal names and direction classes (InputWire/OutputWire).
            Example: clk=InputWire, data=OutputWire
        """
        self._parent = parent_interface
        self._ports = {}

        for name, direction_cls in port_directions.items():
            if not hasattr(parent_interface, name):
                raise AttributeError(f"Interface '{type(parent_interface).__name__}' has no signal named '{name}'")

            target_signal = getattr(parent_interface, name)
            valid_classes = (
                InputWire, OutputWire, OutputReg,
                InputWireArray, OutputWireArray, OutputRegArray
            )

            if direction_cls not in valid_classes:
                raise TypeError(f"Modport direction must be Input or Output, got {direction_cls}")

            # Dynamically create Input/Output objects here.
            # Note: _set_context is not called at this point.
            # The context is set when the EnvironmentBuilder processes the module.
            port_instance = direction_cls(target_signal)

            # Set attributes to allow access via self.clk, self.data, etc.
            setattr(self, name, port_instance)

            # Keep for management purposes
            self._ports[name] = port_instance

    def __getattr__(self, name: str) -> Any:
        # Magic method to suppress warnings from static analysis tools (IDEs).
        #
        # Attributes set via setattr in __init__ are accessible normally,
        # so execution does not reach here for them.
        # Execution reaches here only when accessing 'non-existent attributes'.
        #
        # While it raises AttributeError as usual at runtime, the existence of
        # this method makes IDEs recognize the class has dynamic attributes,
        # suppressing unresolved attribute warnings (treated as Any type).
        raise AttributeError(f"'Modport' object has no attribute '{name}'")