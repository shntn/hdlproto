from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .simulator import Simulator

class TestcaseManager:
    def __init__(self, simulator: "Simulator | None" = None):
        self.simulator = simulator
        self.testcase_functions = []

    def run_testcase(self, testcase: str=None):
        if testcase is not None:
            for name, func in self.testcase_functions:
                if name == testcase:
                    self.simulator.tb.log_testcase_start(name)
                    func(simulator=self.simulator)
                    self.simulator.tb.log_testcase_end(name)
                    return
        else:
            for name, func in self.testcase_functions:
                self.simulator.tb.log_testcase_start(name)
                func(simulator=self.simulator)
                self.simulator.tb.log_testcase_end(name)

