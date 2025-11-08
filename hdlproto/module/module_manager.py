from typing import TYPE_CHECKING

from .module_list import ModuleList
from hdlproto.state import ModuleType

if TYPE_CHECKING:
    from .module_list import ModuleList

class ModuleManager:
    def __init__(self, module_list: "ModuleList | None" = None):
        self.module_list = module_list

    def get_modules(self):
        return self.module_list

    def log_clock_start(self, clock_cycle):
        for module in self.module_list.of_type(module_type=ModuleType.MODULE).get_modules():
            module.log_clock_start(clock_cycle)

    def log_clock_end(self, clock_cycle):
        for module in self.module_list.get_modules():
            module.log_clock_end(clock_cycle)
