import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from tests.helpers import FIXTURES

from deepthought.core import dtp, template, workspace
from deepthought.core.models import GroupState, RunState, StageState, TestState
from deepthought.core.project import detect, match_score
from deepthought.core.scoring import score_run


class TemplateTests(unittest.TestCase):
    def test_expand(self):
        ctx = {"project": "/p", "matrix.N": 3}
        self.assertEqual(template.expand("{project}/x -DN={matrix.N} {unknown}", ctx), "/p/x -DN=3 {unknown}")
        self.assertEqual(template.as_argv("make -C {project} 'a b'", ctx), ["make", "-C", "/p", "a b"])


class DtpTests(unittest.TestCase):
    def test_parse(self):
        self.assertIsNone(dtp.parse(b"garbage"))
        self.assertIsNone(dtp.parse('{"t":"unknown"}'))
        ev = dtp.parse('{"t":"end","id":"a","status":"weird"}')
        self.assertEqual(ev["status"], "error")
        ev = dtp.parse('{"t":"assert","id":"a","ok":false,"actual":"a\\u00ffb"}')
        self.assertEqual(ev["actual"].encode("latin-1"), b"a\xffb")


class WorkspaceTests(unittest.TestCase):
    def test_sync_keeps_build_products(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as root:
            dst = Path(root) / "project"
            Path(src, "a.c").write_text("int a;")
            Path(src, "a.o").write_text("object")          # ignored
            Path(src, "sub").mkdir()
            Path(src, "sub", "b.h").write_text("x")
            self.assertEqual(workspace.sync(src, dst), 2)
            self.assertFalse((dst / "a.o").exists())
            (dst / "marker").write_text("made by make")   # build product in the copy
            Path(src, "sub", "b.h").unlink()
            time.sleep(0.01)
            Path(src, "a.c").write_text("int a = 1;")
            self.assertEqual(workspace.sync(src, dst), 2)
            self.assertTrue((dst / "marker").exists())
            self.assertFalse((dst / "sub").exists())
            self.assertEqual((dst / "a.c").read_text(), "int a = 1;")
            self.assertEqual(workspace.sync(src, dst), 0)

    def test_fingerprint_changes(self):
        with tempfile.TemporaryDirectory() as src:
            Path(src, "a.c").write_text("1")
            f1 = workspace.fingerprint(src)
            Path(src, "a.c").write_text("22")
            self.assertNotEqual(f1, workspace.fingerprint(src))


class DetectTests(unittest.TestCase):
    def test_builtin_suites_detect_fixtures(self):
        from deepthought.core.manifest import load_suite
        from deepthought.core import paths

        suites = [load_suite(p) for p in sorted(paths.BUILTIN_SUITES.iterdir()) if (p / "suite.toml").exists()]
        self.assertEqual(detect(FIXTURES / "libft_good", suites)[0], "libft")
        self.assertEqual(detect(FIXTURES / "gnl_good", suites)[0], "get_next_line")
        self.assertEqual(detect(FIXTURES / "printf_good", suites)[0], "ft_printf")
        libft = next(s for s in suites if s.id == "libft")
        self.assertEqual(match_score(libft, FIXTURES / "gnl_good"), 0)


def _run_with(tests_by_group, stages=()):
    run = RunState(id="r", project={"path": "/p", "name": "p", "kind": "k"}, suites=[], options={})
    for i, (cat, statuses) in enumerate(tests_by_group):
        g = GroupState(gid=f"s/g{i}", suite="s", name=f"g{i}", category=cat, runner="c-unit")
        for j, st in enumerate(statuses):
            g.tests[f"t{j}"] = TestState(tid=f"s/g{i}::t{j}", id=f"t{j}", name="t", gid=g.gid, status=st)
        run.groups.append(g)
    for sid, status in stages:
        run.stages.append(StageState(sid, sid, status=status))
    return run


class ScoringTests(unittest.TestCase):
    def test_perfect_with_bonus(self):
        s = score_run(_run_with([("mandatory", ["pass"] * 4), ("bonus", ["pass", "fail"])]))
        self.assertEqual(s["grade"], 112)
        self.assertEqual(s["verdict"], "ok")

    def test_bonus_ignored_when_mandatory_fails(self):
        s = score_run(_run_with([("mandatory", ["pass", "fail"]), ("bonus", ["pass"])]))
        self.assertEqual(s["grade"], 50)

    def test_skips_do_not_count(self):
        s = score_run(_run_with([("mandatory", ["pass", "skip"])]))
        self.assertEqual(s["grade"], 100)

    def test_build_failure_is_zero(self):
        s = score_run(_run_with([("mandatory", ["pass"])], stages=[("build:0", "fail")]))
        self.assertEqual(s["grade"], 0)
        self.assertIn("build", s["flags"])

    def test_norm_flag_makes_ko(self):
        s = score_run(_run_with([("mandatory", ["pass"])], stages=[("norminette", "fail")]))
        self.assertEqual(s["verdict"], "ko")


if __name__ == "__main__":
    unittest.main()
