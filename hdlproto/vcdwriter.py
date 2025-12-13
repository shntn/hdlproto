import itertools
from abc import ABC, abstractmethod
from typing import List


class _IVCDSignal(ABC):
    """Minimal interface required for recording signal transitions in a VCD file.

    This abstract base class defines the contract that any signal-like object
    must adhere to in order to be registered with the `VCDWriter`. This decouples
    the VCD writer from the internal implementation of hdlproto signals.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """str: The simple name of the signal (e.g., 'data')."""
        ...

    @property
    @abstractmethod
    def width(self) -> int:
        """int: The bit width of the signal."""
        ...

    @property
    @abstractmethod
    def is_reg(self) -> bool:
        """bool: Whether the adapted signal is a register."""
        ...

    @property
    @abstractmethod
    def value(self) -> int:
        """int: The current integer value of the signal."""
        ...

    @property
    @abstractmethod
    def scope(self) -> List[str]:
        """list of str: The hierarchical path to the signal (e.g., ['tb', 'dut'])."""
        ...


class VCDWriter:
    """A writer for producing Value Change Dump (VCD) files.

    This class generates a VCD file to log the signal transitions during a
    simulation. It supports hierarchical scopes and is decoupled from the
    hdlproto simulator internals, relying only on the `_IVCDSignal` interface.

    Attributes
    ----------
    filename : str or None
        The path to the output VCD file.
    f : file object or None
        The file handle for the VCD file.
    signals : list of tuple(_IVCDSignal, str)
        A list of registered signals, where each element is a tuple containing
        the signal object and its unique VCD identifier.

    Examples
    --------
    >>> vcd = VCDWriter()
    >>> vcd.open("dump.vcd")
    >>> # Simulator registers signals and calls vcd._dump()
    >>> vcd.close()
    """

    _id_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$"
    _id_iter = itertools.count()

    def __init__(self):
        """Initialize a VCDWriter instance."""
        self.filename = None
        self.f = None

        # list of (_IVCDSignal, vid)
        self.signals: List[tuple[_IVCDSignal, str]] = []
        self._last_values = {}

        self._scopes_finalized = False
        self._real_cycle = 0

    # ---------------------------------------------------------
    # Open file
    # ---------------------------------------------------------
    def open(self, filename: str):
        """Open a new VCD file and emit the header and initial values.

        Parameters
        ----------
        filename : str
            The name of the VCD file to create.
        """
        self.filename = filename
        self.f = open(filename, "w")
        self._write_header()
        self._dump_initial()

    # ---------------------------------------------------------
    # Close file
    # ---------------------------------------------------------
    def close(self):
        """Close the VCD file handle if it was opened."""
        if not self.f:
            return
        self.f.close()

    # ---------------------------------------------------------
    # Header
    # ---------------------------------------------------------
    def _write_header(self):
        """Write the static VCD header with metadata and timescale."""
        if not self.f:
            return
        f = self.f
        f.write("$date\n\tHDLproto Simulation\n$end\n")
        f.write("$version\n\tHDLproto\n$end\n")
        f.write("$timescale 1ns $end\n")

    # ---------------------------------------------------------
    # Register signal (IVCDSignal)
    # ---------------------------------------------------------
    def _register(self, sig: _IVCDSignal):
        """Add a signal to the dump list and allocate a unique VCD identifier.

        This method is called by the simulator for each signal that needs to be
        traced.

        Parameters
        ----------
        sig : _IVCDSignal
            The signal object to be registered for tracing.
        """
        vid = self._new_vcd_id()
        self.signals.append((sig, vid))
        self._last_values[vid] = None

    # ---------------------------------------------------------
    # Scope helpers
    # ---------------------------------------------------------
    def _enter_scope(self, name: str):
        """Emit a $scope directive for hierarchical grouping.

        Parameters
        ----------
        name : str
            The name of the scope to enter.
        """
        if not self.f:
            return
        self.f.write(f"$scope module {name} $end\n")

    def _exit_scope(self):
        """Emit a $upscope directive to close the current scope."""
        if not self.f:
            return
        self.f.write("$upscope $end\n")

    # ---------------------------------------------------------
    # Emit scopes + $var
    # ---------------------------------------------------------
    def _finalize_scopes(self):
        """Sort signals by scope and emit $var declarations once before dumping.

        This crucial step is performed after all signals have been registered
        but before any values are dumped. It sorts the signals by their
        hierarchical scope, then walks the scope tree to emit the `$scope` and
        `$var` declarations in the correct order.
        """
        if not self.f:
            return
        if self._scopes_finalized:
            return
        self._scopes_finalized = True

        # Build sortable table: (scope_path, signal, vid)
        table = []
        for sig, vid in self.signals:
            table.append((sig.scope, sig, vid))

        table.sort(key=lambda x: x[0])

        prev_path: List[str] = []
        for path, sig, vid in table:
            # Find a common prefix
            common = 0
            for a, b in zip(prev_path, path):
                if a == b:
                    common += 1
                else:
                    break

            # Exit scopes
            for _ in range(len(prev_path) - common):
                self._exit_scope()

            # Enter scopes
            for p in path[common:]:
                self._enter_scope(p)

            # Write variable declaration
            stype = "reg" if sig.is_reg else "wire"
            self.f.write(f"$var {stype} {sig.width} {vid} {sig.name} $end\n")

            prev_path = path

        # Close all scopes
        for _ in range(len(prev_path)):
            self._exit_scope()

        self.f.write("$enddefinitions $end\n")

    # ---------------------------------------------------------
    # VCD ID generator
    # ---------------------------------------------------------
    @classmethod
    def _new_vcd_id(cls) -> str:
        """Generate a short unique ID composed of legal VCD characters.

        VCD identifiers are used to compactly represent signals in the value
        dump section. This method generates a sequence of identifiers like
        'a', 'b', ..., 'a$', 'b$', ...

        Returns
        -------
        str
            A new, unique VCD identifier string.
        """
        n = next(cls._id_iter)
        chars = cls._id_chars
        base = len(chars)
        s = ""
        while True:
            s = chars[n % base] + s
            if n < base:
                break
            n //= base
        return s

    # ---------------------------------------------------------
    # Initial dump
    # ---------------------------------------------------------
    def _dump_initial(self):
        """Emit $dumpvars section with initial signal values."""
        if not self.f:
            return
        self._finalize_scopes()
        self.f.write("$dumpvars\n")

        for sig, vid in self.signals:
            val = sig.value & ((1 << sig.width) - 1)
            self._last_values[vid] = val

            if sig.width == 1:
                self.f.write(f"{val}{vid}\n")
            else:
                bits = format(val, f"0{sig.width}b")
                self.f.write(f"b{bits} {vid}\n")

        self.f.write("$end\n")

    # ---------------------------------------------------------
    # Value-change dump
    # ---------------------------------------------------------
    def _dump(self, timestamp: int = None):
        """Append a timestamped delta of signal changes since the last dump.

        This method is called by the simulator at each time step where values
        should be recorded. It compares the current signal values with the last
        recorded values and writes out only the changes.

        Parameters
        ----------
        timestamp : int, optional
            The simulation time for this dump. If None, an internal counter
            is used. Defaults to None.
        """
        if not self.f:
            return
        self._real_cycle += 1
        if timestamp is None:
            timestamp = self._real_cycle

        self.f.write(f"#{timestamp}\n")

        for sig, vid in self.signals:
            val = sig.value & ((1 << sig.width) - 1)
            prev = self._last_values[vid]

            if prev == val:
                continue

            if sig.width == 1:
                self.f.write(f"{val}{vid}\n")
            else:
                bits = format(val, f"0{sig.width}b")
                self.f.write(f"b{bits} {vid}\n")

            self._last_values[vid] = val