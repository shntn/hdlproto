from typing import TYPE_CHECKING

from .module_list import _ModuleList
from hdlproto.state import _ModuleType

if TYPE_CHECKING:
    from .module_list import _ModuleList

class _ModuleManager:
    def __init__(self, _module_list: "_ModuleList | None" = None):
        self.module_list = _module_list

    def _get_modules(self):
        return self.module_list

    def _log_clock_start(self, clock_cycle):
        for module in self.module_list._of_type(_module_type=_ModuleType.MODULE)._get_modules():
            module.log_clock_start(clock_cycle)

    def _log_clock_end(self, clock_cycle):
        for module in self.module_list._get_modules():
            module.log_clock_end(clock_cycle)
