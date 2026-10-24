"""Suite errors: problems of the test suite itself (dt_error, error(), a missing
stdin_file, a group with no tests) are reported apart and never counted
against the student."""

import io
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tests.helpers import FIXTURES, ROOT, fresh_home, manager, statuses, write_suite

from deepthought.cli.reporter_plain import PlainReporter, exit_code, junit
from deepthought.core import dtp, paths

SUITE = """
[suite]
id = "probe"
name = "Probe"
project = "probe"

[[group]]
name = "C"
runner = "c-unit"
sources = ["{project}/answer.c", "tests/*.c"]

[[group]]
name = "Python"
runner = "python-unit"
tests = ["py/test_*.py"]

[[group]]
name = "Exec"
runner = "exec"
cases = "cases.toml"

[[group]]
name = "Nothing"
runner = "c-unit"
sources = ["nothing/*.c"]
"""

C_TESTS = r"""
#include "dt.h"
#include <errno.h>
#include <fcntl.h>

int	answer(void);

DT_TEST(fx, fixture, "Reads a fixture of the suite")
{
	int	fd = open(dt_fixture("data.txt"), O_RDONLY);

	if (fd < 0)
		dt_error("fixture data.txt cannot be opened: %s", strerror(errno));
	close(fd);
}

DT_TEST(fx, answer, "answer() is 42")
{
	DT_CHECK_INT("answer()", answer(), 42);
}

DT_TEST(fx, ok, "Always passes")
{
	DT_EXPECT(1);
}
"""

PY_TESTS = """
from dtharness import test, error, expect_eq

@test("A suite problem in Python")
def broken():
    print("some output first")
    error("the reference data is missing")

@test("A normal Python test")
def fine():
    expect_eq(1 + 1, 2)
"""

CASES = """
[[case]]
name = "missing stdin"
cmd = "cat"
stdin_file = "fixtures/not-there.txt"

[[case]]
name = "echo"
cmd = ["echo", "hi"]
[case.expect]
stdout = "hi\\n"
"""


def wait(m, run_id):
    while m.runs[run_id].status in ("pending", "running"):
        time.sleep(0.05)
    return m.get(run_id)


class SuiteErrors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fresh_home()
        cls.tmp = Path(tempfile.mkdtemp(prefix="dt-suite-error-"))
        cls.suite = write_suite(cls.tmp / "probe", SUITE, {
            "tests/probe.c": C_TESTS, "py/test_probe.py": PY_TESTS, "cases.toml": CASES,
            "fixtures/data.txt": "data\n"})
        cls.m = manager()
        cls.m.registry.add(str(cls.suite))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def project(self, value):
        p = self.tmp / f"project-{value}"
        p.mkdir(exist_ok=True)
        (p / "answer.c").write_text(f"int answer(void) {{ return {value}; }}\n")
        return p

    def run_probe(self, value, fixture=False):
        data = self.suite / "fixtures" / "data.txt"
        if fixture:
            data.write_text("data\n")
        elif data.exists():
            data.unlink()
        path = self.project(value)
        self.m.projects.add(str(path))
        run = self.m.start(path, ["probe"], {}, wait=True)
        return self.m.get(run.id)

    def test_statuses_and_reasons(self):
        run = self.run_probe(41)
        st = statuses(run)
        self.assertEqual(st["fx/fixture"], "suite_error")
        self.assertEqual(st["fx/answer"], "fail")                 # the student's real mistake
        self.assertEqual(st["fx/ok"], "pass")
        self.assertEqual(st["test_probe/broken"], "suite_error")
        self.assertEqual(st["test_probe/fine"], "pass")
        self.assertEqual(st["missing-stdin"], "suite_error")
        self.assertEqual(st["echo"], "pass")
        tests = {t["id"]: t for g in run["groups"] for t in g["tests"]}
        self.assertEqual(tests["fx/fixture"]["reason"], "fixture data.txt cannot be opened: No such file or directory")
        self.assertEqual(tests["fx/fixture"]["leaks"], None)
        self.assertEqual(tests["test_probe/broken"]["reason"], "the reference data is missing")
        self.assertIn("some output first", tests["test_probe/broken"]["output"])
        self.assertIn("not-there.txt", tests["missing-stdin"]["reason"])
        groups = {g["name"]: g for g in run["groups"]}
        self.assertEqual(groups["Nothing"]["status"], "suite_error")
        self.assertIn("no test file matches", groups["Nothing"]["message"])
        self.assertEqual(groups["C"]["status"], "fail")           # a real failure wins
        self.assertEqual(groups["Python"]["status"], "suite_error")

    def test_grade_ignores_suite_errors(self):
        run = self.run_probe(41)
        score = run["score"]
        self.assertEqual(score["suite_errors"], 4)                # 3 tests + the empty group
        self.assertEqual(score["mandatory"]["total"], 4)          # answer, ok, fine, echo
        self.assertEqual(score["mandatory"]["passed"], 3)
        self.assertEqual((score["grade"], score["verdict"]), (75, "ko"))
        self.assertEqual(exit_code(run), 1)                       # the student has a failure

    def test_only_suite_problems_is_incomplete(self):
        run = self.run_probe(42)
        score = run["score"]
        self.assertEqual((score["grade"], score["verdict"]), (100, "incomplete"))
        self.assertEqual(exit_code(run), 3)
        out = io.StringIO()
        PlainReporter(stream=out).summary(run)
        text = out.getvalue()
        self.assertIn("problem(s) in the test suite, not in your code", text)
        self.assertIn("fixture data.txt cannot be opened", text)
        self.assertIn("incomplete: 4 suite problem(s)", text)
        self.assertIn('<error type="suite_error" message="the reference data is missing"/>', junit(run))

    def test_nothing_to_grade(self):
        tmp = self.tmp / "only-errors"
        write_suite(tmp, """
[suite]
id = "only-errors"
name = "Only errors"
project = "probe"
[[group]]
name = "C"
runner = "c-unit"
sources = ["tests/*.c"]
""", {"tests/t.c": '#include "dt.h"\nDT_TEST(a, b, "x") { dt_error("broken on purpose"); }\n'})
        self.m.registry.add(str(tmp))
        path = self.project(1)
        run = self.m.get(self.m.start(path, ["only-errors"], {}, wait=True).id)
        self.assertEqual((run["score"]["grade"], run["score"]["verdict"]), (None, "incomplete"))
        self.assertEqual(exit_code(run), 3)
        out = io.StringIO()
        PlainReporter(stream=out).summary(run)                    # no crash on a None grade
        self.assertIn("grade —", out.getvalue())
        from argparse import Namespace

        from deepthought.cli.main import cmd_history  # not main(): it shuts DeepThought down when done
        with redirect_stdout(io.StringIO()) as hist:
            self.assertEqual(cmd_history(Namespace(path=str(path), limit=5)), 0)
        self.assertIn("grade   —", hist.getvalue())

    def test_retest_failed_runs_suite_errors_again(self):
        first = self.run_probe(42)
        (self.suite / "fixtures" / "data.txt").write_text("data\n")  # the author fixes the suite
        data = wait(self.m, self.m.rerun(first["id"], failed_only=True).id)
        tests = {t["id"]: t for g in data["groups"] for t in g["tests"]}
        self.assertEqual(tests["fx/fixture"]["status"], "pass")
        self.assertFalse(tests["fx/fixture"]["carried"])
        self.assertTrue(tests["fx/ok"]["carried"])               # passed: not re-run
        self.assertFalse(tests["fx/fixture"]["fixed"])            # it was never the student's failure

    def test_suite_error_is_not_a_regression(self):
        self.run_probe(42, fixture=True)
        run = self.run_probe(42)
        tests = {t["id"]: t for g in run["groups"] for t in g["tests"]}
        self.assertEqual(tests["fx/fixture"]["status"], "suite_error")
        self.assertFalse(tests["fx/fixture"]["regression"])
        self.assertEqual(run["score"]["regressions"], 0)

    def test_protocol_accepts_the_status(self):
        ev = dtp.parse('{"t":"end","id":"a/b","status":"suite_error","reason":"x"}')
        self.assertEqual(ev["status"], "suite_error")

    def test_c_harness_without_fork(self):
        """DT_NO_FORK (debugger mode): dt_error, DT_ASSERT and dt_skip still stop the test."""
        src = self.tmp / "nofork.c"
        src.write_text(r"""
#include "dt.h"
DT_TEST(n, error, "e") { dt_error("stop %d", 1); DT_FAIL("after dt_error"); }
DT_TEST(n, assert, "a") { DT_ASSERT(0); DT_FAIL("after DT_ASSERT"); }
DT_TEST(n, skip, "s") { dt_skip("why"); DT_FAIL("after dt_skip"); }
DT_TEST(n, ok, "o") { DT_EXPECT(1); }
""")
        exe = self.tmp / "nofork"
        h = paths.HARNESS_C
        subprocess.run(["cc", "-I", str(h), str(src), str(h / "dt_main.c"), str(h / "dt_alloc.c"), "-o", str(exe)]
                       + (["-ldl"] if os.uname().sysname == "Linux" else []), check=True)
        for nofork in ("0", "1"):
            r, w = os.pipe()
            subprocess.run([str(exe)], env={**os.environ, "DT_NO_FORK": nofork, "DT_REPORT_FD": str(w)},
                           pass_fds=(w,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            os.close(w)
            with os.fdopen(r) as f:
                events = [json.loads(line) for line in f]
            ends = {e["id"]: e for e in events if e["t"] == "end"}
            self.assertEqual({k: v["status"] for k, v in ends.items()},
                             {"n/error": "suite_error", "n/assert": "fail", "n/skip": "skip", "n/ok": "pass"}, nofork)
            self.assertEqual(ends["n/error"]["reason"], "stop 1")
            msgs = [e["msg"] for e in events if e["t"] == "assert"]
            self.assertEqual(msgs, ["0"], nofork)                 # nothing ran after a stop

    def test_gnl_suite_missing_fixture(self):
        """The official suite reports its own missing fixture as a suite problem."""
        copy = self.tmp / "gnl-copy"
        shutil.copytree(ROOT / "suites" / "get_next_line", copy)
        text = (copy / "suite.toml").read_text().replace('id = "get_next_line"', 'id = "gnl-copy"')
        (copy / "suite.toml").write_text(text)
        (copy / "fixtures" / "multi.txt").unlink()
        self.m.registry.add(str(copy))
        run = self.m.get(self.m.start(FIXTURES / "gnl_good", ["gnl-copy"], {}, wait=True).id)
        st = statuses(run)
        bad = {k: v for k, v in st.items() if v not in ("pass", "skip")}
        self.assertTrue(bad)
        self.assertEqual(set(bad.values()), {"suite_error"}, bad)
        self.assertEqual(run["score"]["verdict"], "incomplete")


if __name__ == "__main__":
    unittest.main()
