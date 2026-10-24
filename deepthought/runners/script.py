"""script: any executable that speaks DTP (--list / --run ids) — any language.

[[group]] keys used: command (string or list, placeholders allowed), env.
"""

import os
from pathlib import Path

from deepthought.core.template import as_argv, quote_cmd
from deepthought.runners.base import DTPProcessRunner


class ScriptRunner(DTPProcessRunner):
    def command(self):
        argv = as_argv(self.group.command, self.vars)
        first = argv[0]
        if not os.path.isabs(first) and (Path(self.suite.path) / first).exists():
            argv[0] = str(Path(self.suite.path) / first)
        return argv

    def prepare(self):
        argv = self.command()
        self.build_cmd = quote_cmd(argv)
        exe = Path(argv[0])
        if exe.is_absolute() and exe.exists() and not os.access(exe, os.X_OK):
            self.build_log = f"{exe} is not executable (chmod +x it)"
            self.suite_problem = f"its command {exe.name} is not executable (chmod +x it)"
            return False
        if exe.is_absolute() and not exe.exists():
            self.build_log = f"{exe} does not exist"
            self.suite_problem = f"its command {exe} does not exist"
            return False
        return True
