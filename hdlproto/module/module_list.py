from dataclasses import dataclass
from .module import Module
from hdlproto.testbench import TestBench
from hdlproto.state import ModuleType

@dataclass
class ModuleContainer:
    module: (Module | TestBench)
    info: dict

class ModuleList:
    def __init__(self, modules: list[ModuleContainer]|None=None):
        if modules:
            self._modules = modules
        else:
            self._modules = []
        self._index = 0

    def __iter__(self):
        self._index = 0
        return self

    def __next__(self):
        if self._index < len(self._modules):
            result = self._modules[self._index]
            self._index += 1
            return result
        raise StopIteration

    def filtered(self, filters: dict):
        result = []
        for container in self._modules:
            match = True
            for key, value in filters.items():
                val = container.info.get(key)
                if isinstance(value, (list, tuple)):
                    if val not in value:
                        match = False
                        break
                else:
                    if val != value:
                        match = False
                        break
            if match:
                result.append(container)
        return ModuleList(result)

    def of_type(self, module_type: ModuleType | tuple[ModuleType, ...]):
        return self.filtered({"module_type": module_type})

    def get_modules(self):
        modules = []
        for container in self._modules:
            modules.append(container.module)
        return modules
