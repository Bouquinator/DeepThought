"""python-unit: Python test files using deepthought/harness/python/dtharness.py.

[[group]] keys used: tests (globs of test files), env.
"""

import shlex
import sys

from deepthought.core import paths
from deepthought.runners.base import DTPProcessRunner


class PythonUnitRunner(DTPProcessRunner):
    def command(self):
        files = self.globs(self.group.tests)
        python = self.ctx.config.get("python") or sys.executable
        return [python, str(paths.HARNESS_PY / "dtharness.py"), *files]

    def prepare(self):
        missing = [f for f in self.globs(self.group.tests) if not f.endswith(".py")]
        if missing:
            self.build_log = "not python files:\n" + "\n".join(missing)
            return False
        self.build_cmd = " ".join(shlex.quote(c) for c in self.command())
        return True

    def env(self):
        env = super().env()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env
