
def module_manager_factory():
    from hdlproto.module import ModuleManager
    return ModuleManager()

def function_manager_factory():
    from hdlproto.function_manager import FunctionManager
    return FunctionManager()

def signal_manager_factory():
    from hdlproto.signal import SignalManager
    return SignalManager()

def event_manager_factory():
    from hdlproto.event import EventManager
    return EventManager()

def event_mediator_factory():
    from hdlproto.event import EventMediator
    return EventMediator()

def testcase_manager_factory():
    from .testcase_manager import TestcaseManager
    return TestcaseManager()

def simulation_exector_factory():
    from .simulator import SimulationExector
    return SimulationExector()
