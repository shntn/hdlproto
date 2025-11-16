from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .simulator import Simulator

class _TestcaseManager:
    def __init__(self, _simulator: "Simulator | None" = None):
        self._simulator = _simulator
        self._testcase_functions = []

    def _run_testcase(self, _testcase: str=None):
        if _testcase is not None:
            for name, func in self._testcase_functions:
                if name == _testcase:
                    self._simulator._tb.log_testcase_start(name)
                    func(simulator=self._simulator)
                    self._simulator._tb.log_testcase_end(name)
                    return
        else:
            for name, func in self._testcase_functions:
                self._simulator._tb.log_testcase_start(name)
                func(simulator=self._simulator)
                self._simulator._tb.log_testcase_end(name)

