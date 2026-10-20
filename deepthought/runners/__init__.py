"""Runners turn a suite [[group]] into tests. See base.Runner."""


def get_runner(name):
    from deepthought.runners.c_unit import CUnitRunner
    from deepthought.runners.exec_cases import ExecRunner
    from deepthought.runners.python_unit import PythonUnitRunner
    from deepthought.runners.script import ScriptRunner

    return {
        "c-unit": CUnitRunner,
        "python-unit": PythonUnitRunner,
        "exec": ExecRunner,
        "script": ScriptRunner,
    }[name]
