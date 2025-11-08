from .module import Module

def testcase(func):
    func.type = 'testcase'
    return func


class TestBench(Module):
    @property
    def is_testbench(self):
        return True

    def log_sim_start(self, config):
        pass

    def log_testcase_start(self, name):
        pass

    def log_clock_start(self, clock_cycle):
        pass

    def log_testcase_end(self, name):
        pass

    def log_sim_end(self):
        pass