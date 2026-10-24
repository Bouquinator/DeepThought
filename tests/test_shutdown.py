"""However DeepThought ends (Ctrl-C, closed terminal, kill, kill -9), the tests
it started must end too: an infinite loop under test must never outlive it."""

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tests.helpers import ROOT, fresh_home, manager, write_suite

SUITE = """
[suite]
id = "spin"
name = "Spin"
version = "1.0.0"
project = "spin"
engine = ">=0.1"

[build]
command = "true"

[defaults]
timeout = 3600

[[group]]
name = "Spin"
category = "mandatory"
runner = "exec"
cases = "cases.toml"
"""


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_until(predicate, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


class Shutdown(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fresh_home()
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.pidfile = root / "spin.pid"
        spin = root / "spin.py"
        spin.write_text(f"import os\nopen({str(cls.pidfile)!r}, 'w').write(str(os.getpid()))\nwhile True:\n    pass\n")
        suite = write_suite(root / "suite", SUITE, {
            "cases.toml": f"[[case]]\nname = 'spin'\ncmd = [{sys.executable!r}, {str(spin)!r}]\n"})
        manager().registry.add(str(suite))
        cls.project = root / "project"
        cls.project.mkdir()
        (cls.project / "a.txt").write_text("a")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def start(self):
        self.pidfile.unlink(missing_ok=True)
        dt = subprocess.Popen([sys.executable, str(ROOT / "deepthought" / "__main__.py"), "run", "--no-update",
                               "--no-norm", "-s", "spin", str(self.project)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: dt.poll() is None and dt.kill())
        self.assertTrue(wait_until(lambda: self.pidfile.exists() and self.pidfile.read_text()), "test never started")
        pid = int(self.pidfile.read_text())
        self.addCleanup(lambda: alive(pid) and os.kill(pid, signal.SIGKILL))
        return dt, pid

    def check(self, sig):
        dt, pid = self.start()
        dt.send_signal(sig)
        try:
            dt.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.fail(f"DeepThought still running 10 s after {sig.name}")
        self.assertTrue(wait_until(lambda: not alive(pid)), f"the test kept running after {sig.name}")

    def test_ctrl_c(self):
        self.check(signal.SIGINT)

    def test_kill(self):
        self.check(signal.SIGTERM)

    def test_closed_terminal(self):
        self.check(signal.SIGHUP)

    def test_kill_9(self):
        self.check(signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
