"""End to end: the official suites against reference and deliberately broken projects."""

import unittest

from tests.helpers import FIXTURES, ROOT, fresh_home, manager, statuses


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fresh_home()
        cls.m = manager()

    def run_project(self, path, suites=None, **options):
        self.m.projects.add(str(path))
        run = self.m.start(path, suites, options, wait=True)
        return self.m.get(run.id)

    def test_libft_good_is_perfect(self):
        run = self.run_project(FIXTURES / "libft_good")
        self.assertEqual(run["status"], "done", run.get("error"))
        bad = {k: v for k, v in statuses(run).items() if v != "pass"}
        self.assertEqual(bad, {})
        self.assertEqual(run["score"]["grade"], 125)

    def test_libft_broken_is_classified(self):
        st = statuses(self.run_project(FIXTURES / "libft_broken"))
        expected = {
            "ft_strlcpy/truncates": "fail",          # wrong return value
            "ft_atoi/basic": "fail",                 # sign ignored
            "ft_strdup/malloc_fail": "crash",        # no malloc protection
            "ft_strchr/not_found": "timeout",        # infinite loop
            "ft_split/malloc_fail_middle": "leak",   # no cleanup on failure
            "ft_itoa/limits": "fail",                # INT_MIN overflow
            "ft_strnstr/compile": "build_error",     # missing function
            "ft_calloc/overflow": "fail",            # no overflow check
            "ft_strlen/basic": "pass",
        }
        for tid, status in expected.items():
            self.assertEqual(st.get(tid), status, tid)

    def test_libft_broken_checks(self):
        run = self.run_project(FIXTURES / "libft_broken")
        stages = {s["id"]: s["status"] for s in run["stages"]}
        self.assertEqual(stages["relink"], "fail")
        self.assertEqual(stages["forbidden"], "fail")
        self.assertIn("printf", next(s for s in run["stages"] if s["id"] == "forbidden")["message"])
        self.assertIn("forbidden", run["score"]["flags"])

    def test_rerun_failed_only(self):
        run = self.run_project(FIXTURES / "libft_broken")
        again = self.m.rerun(run["id"], failed_only=True)
        while self.m.runs[again.id].status in ("pending", "running"):
            import time
            time.sleep(0.05)
        data = self.m.get(again.id)
        carried = [t for g in data["groups"] for t in g["tests"] if t["carried"]]
        rerun = [t for g in data["groups"] for t in g["tests"] if not t["carried"]]
        self.assertTrue(carried)
        self.assertTrue(all(t["status"] != "pass" for t in rerun))

    def test_gnl_matrix(self):
        run = self.run_project(FIXTURES / "gnl_good")
        self.assertEqual({k: v for k, v in statuses(run).items() if v != "pass"}, {})
        variants = {g["name"] for g in run["groups"]}
        self.assertIn("Mandatory  [BUFFER_SIZE=1]", variants)
        self.assertIn("Mandatory  [BUFFER_SIZE=10000000]", variants)

    def test_printf(self):
        run = self.run_project(FIXTURES / "printf_good")
        self.assertEqual({k: v for k, v in statuses(run).items() if v != "pass"}, {})

    def test_project_build_options(self):
        path = FIXTURES / "libft_good"
        self.m.projects.set_build(str(path), {
            "command": "sh -c 'test \"$DT_FLAG\" = on && make -C {project}'",
            "make_args": "ignored-without-make", "env": "DT_FLAG=on"})
        try:
            run = self.run_project(path)
            build = next(s for s in run["stages"] if s["id"].startswith("build"))
            self.assertEqual(build["status"], "pass", build["log"])
            self.assertEqual(run["options"]["build"]["env"], {"DT_FLAG": "on"})
            # per-run options override the saved ones
            run = self.run_project(path, build={"command": "make -C {project}", "make_args": "bonus"})
            build = next(s for s in run["stages"] if s["id"].startswith("build"))
            self.assertTrue(build["log"].splitlines()[0].endswith("bonus"), build["log"])
        finally:
            self.m.projects.set_build(str(path), {})
        self.assertNotIn("build", self.m.projects.get(str(path)))

    def test_python_syntax_check(self):
        import shutil
        import tempfile
        from pathlib import Path

        self.m.registry.add(str(ROOT / "examples" / "suites" / "py-calc"))
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(ROOT / "examples" / "projects" / "py_calc" / "calc.py", d)
            with open(Path(d) / "calc.py", "a") as f:
                f.write("\ndef broken(:\n    pass\n")
            run = self.run_project(d)
        stage = next(s for s in run["stages"] if s["id"].startswith("build"))
        self.assertEqual((stage["name"], stage["status"]), ("Syntax check", "fail"))
        self.assertIn("calc.py:", stage["message"])
        self.assertEqual(run["score"]["grade"], 0)

    def test_python_and_exec_examples(self):
        reg = self.m.registry
        reg.add(str(ROOT / "examples" / "suites" / "py-calc"))
        reg.add(str(ROOT / "examples" / "suites" / "mini-echo"))
        st = statuses(self.run_project(ROOT / "examples" / "projects" / "py_calc"))
        self.assertEqual(st["test_calc/add_numbers"], "pass")
        self.assertEqual(st["test_calc/mean_empty"], "fail")
        self.assertEqual(st["test_calc/big_number"], "timeout")
        self.assertEqual(st["test_calc/percent"], "crash")
        st = statuses(self.run_project(ROOT / "examples" / "projects" / "mini_echo"))
        self.assertEqual(st["empty-argument-in-the-middle"], "fail")
        self.assertEqual(st["multi-line-output"], "pass")


if __name__ == "__main__":
    unittest.main()
