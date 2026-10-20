"""End to end: the official suites against reference and deliberately broken projects."""

import unittest

from tests.helpers import FIXTURES, ROOT, fresh_home, manager, statuses


ENGINE = ["engine-libft"]  # tests/fixtures/engine-suite: a libft subset used to test the engine


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fresh_home()
        cls.m = manager()
        cls.m.registry.add(str(FIXTURES / "engine-suite"))

    def run_project(self, path, suites=None, **options):
        self.m.projects.add(str(path))
        run = self.m.start(path, suites, options, wait=True)
        return self.m.get(run.id)

    def test_libft_good_is_perfect(self):
        run = self.run_project(FIXTURES / "libft_good", ENGINE)
        self.assertEqual(run["status"], "done", run.get("error"))
        bad = {k: v for k, v in statuses(run).items() if v != "pass"}
        self.assertEqual(bad, {})
        self.assertEqual(run["score"]["grade"], 125)

    def test_libft_broken_is_classified(self):
        st = statuses(self.run_project(FIXTURES / "libft_broken", ENGINE))
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
        run = self.run_project(FIXTURES / "libft_broken", ENGINE)
        stages = {s["id"]: s["status"] for s in run["stages"]}
        self.assertEqual(stages["relink"], "fail")
        self.assertEqual(stages["forbidden"], "fail")
        self.assertIn("printf", next(s for s in run["stages"] if s["id"] == "forbidden")["message"])
        self.assertIn("forbidden", run["score"]["flags"])

    def test_rerun_failed_only(self):
        run = self.run_project(FIXTURES / "libft_broken", ENGINE)
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

    def test_sstyle_community_suites(self):
        """The Sstyle suites download SStyles93's CodeTester (network) and run it unmodified."""
        run = self.run_project(FIXTURES / "libft_good")
        fetch = next((x for x in run["stages"] if x["id"] == "fetch"), None)
        if fetch is None or fetch["status"] != "pass":
            self.skipTest("CodeTester could not be downloaded (offline?)")
        self.assertEqual(run["suites"][0]["uid"], "sstyle-libft")
        st = statuses(run)
        self.assertEqual(st["Libft/ft_split"], "pass")
        self.assertEqual(st["Libft/ft_lstmap"], "pass")
        self.assertEqual(st["Libft/ft_strdup"], "fail")   # the CodeTester requires ft_strdup(NULL) protection
        strdup = next(t for g in run["groups"] for t in g["tests"] if t["id"] == "Libft/ft_strdup")
        self.assertIn("CRASH", strdup["asserts"][0]["msg"])
        self.assertTrue(strdup["file"].endswith("tests/libft/test_strdup.c"))
        run = self.run_project(FIXTURES / "printf_good")
        st = statuses(run)
        self.assertEqual(st["Printf_mandatory/printf_p"], "pass")
        self.assertEqual(st["Printf_mandatory/printf_project"], "pass")
        extra = [g for g in run["groups"] if g["category"] == "extra"]
        self.assertTrue(extra and all(t["id"].startswith("Printf_original/") for g in extra for t in g["tests"]))

    def test_project_build_options(self):
        path = FIXTURES / "libft_good"
        self.m.projects.set_build(str(path), {
            "command": "sh -c 'test \"$DT_FLAG\" = on && make -C {project}'",
            "make_args": "ignored-without-make", "env": "DT_FLAG=on"})
        try:
            run = self.run_project(path, ENGINE)
            build = next(s for s in run["stages"] if s["id"].startswith("build"))
            self.assertEqual(build["status"], "pass", build["log"])
            self.assertEqual(run["options"]["build"]["env"], {"DT_FLAG": "on"})
            # per-run options override the saved ones
            run = self.run_project(path, ENGINE, build={"command": "make -C {project}", "make_args": "bonus"})
            build = next(s for s in run["stages"] if s["id"].startswith("build"))
            self.assertTrue(build["log"].splitlines()[0].endswith("bonus"), build["log"])
        finally:
            self.m.projects.set_build(str(path), {})
        self.assertNotIn("build", self.m.projects.get(str(path)))

    def test_custom_project_type_and_links(self):
        import tempfile
        from pathlib import Path

        reg = self.m.registry
        reg.add(str(ROOT / "examples" / "suites" / "mini-echo"))
        with tempfile.TemporaryDirectory() as d:
            # an unknown project: nothing runs until the user decides
            Path(d, "notes.txt").write_text("hello")
            self.assertEqual(self.m.suites_for(d)[2], [])
            # own type: suites whose `project` is that type run
            self.m.projects.configure(d, kind="mini_echo")
            mode, kind, suites = self.m.suites_for(d)
            self.assertEqual((mode, kind, [s.uid for s in suites]), ("kind", "mini_echo", ["mini-echo"]))
            # linked suites: any suite, whatever project it targets
            self.m.projects.link(d, "engine-libft", current=["mini-echo"])
            mode, kind, suites = self.m.suites_for(d)
            self.assertEqual(mode, "linked")
            self.assertEqual({s.uid for s in suites}, {"mini-echo", "engine-libft"})
            self.m.projects.unlink(d, "mini-echo")
            self.assertEqual([s.uid for s in self.m.suites_for(d)[2]], ["engine-libft"])
            # back to automatic
            self.m.projects.configure(d, kind="", suites=[])
            self.assertEqual(self.m.suites_for(d)[0], "auto")
            self.assertEqual(self.m.suites_for(d)[2], [])
        # the run is labelled with the user's type
        proj = ROOT / "examples" / "projects" / "mini_echo"
        self.m.projects.configure(str(proj), kind="my_echo", suites=["mini-echo"])
        try:
            run = self.run_project(proj)
            self.assertEqual(run["project"]["kind"], "my_echo")
            self.assertEqual([s["uid"] for s in run["suites"]], ["mini-echo"])
        finally:
            self.m.projects.configure(str(proj), kind="", suites=[])

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
