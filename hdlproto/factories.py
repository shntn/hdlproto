
def _module_manager_factory():
    from .module.module_manager import _ModuleManager
    return _ModuleManager()

def _function_manager_factory():
    from hdlproto.function_manager import _FunctionManager
    return _FunctionManager()

def _signal_manager_factory():
    from .signal.signal_manager import _SignalManager
    return _SignalManager()

def _event_manager_factory():
    from .event.event_manager import _EventManager
    return _EventManager()

def _event_mediator_factory():
    from .event.event_mediator import _EventMediator
    return _EventMediator()

def _testcase_manager_factory():
    from .testcase_manager import _TestcaseManager
    return _TestcaseManager()

def _simulation_exector_factory():
    from .simulator import _SimulationExector
    return _SimulationExector()
