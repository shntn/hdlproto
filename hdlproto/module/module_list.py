from dataclasses import dataclass
from .module import Module
from hdlproto.testbench import TestBench
from hdlproto.state import _ModuleType

@dataclass
class _ModuleContainer:
    _module: (Module | TestBench)
    _info: dict

class _ModuleList:
    def __init__(self, _modules: list[_ModuleContainer] | None=None):
        if _modules:
            self._modules = _modules
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

    def _filtered(self, _filters: dict):
        result = []
        for container in self._modules:
            match = True
            for key, value in _filters.items():
                val = container._info.get(key)
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
        return _ModuleList(result)

    def _of_type(self, _module_type: _ModuleType | tuple[_ModuleType, ...]):
        return self._filtered({"module_type": _module_type})

    def _get_modules(self):
        modules = []
        for container in self._modules:
            modules.append(container._module)
        return modules
