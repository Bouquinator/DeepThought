import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import fresh_home

from deepthought.core import paths, selfupdate


def git(*args, cwd):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True, capture_output=True)


class SelfUpdateTests(unittest.TestCase):
    def test_pull_and_dirty_protection(self):
        fresh_home()
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            upstream = d / "upstream"
            upstream.mkdir()
            git("init", "-q", "-b", "main", cwd=upstream)
            (upstream / "f.txt").write_text("v1")
            git("add", ".", cwd=upstream)
            git("commit", "-qm", "v1", cwd=upstream)
            git("clone", "-q", str(upstream), str(d / "clone"), cwd=d)
            clone = d / "clone"
            (upstream / "f.txt").write_text("v2")
            git("commit", "-qam", "v2: better tests", cwd=upstream)
            with mock.patch.object(paths, "REPO_ROOT", clone):
                st = selfupdate.check(fetch=True)
                self.assertTrue(st["available"])
                self.assertEqual(st["behind"], 1)
                (clone / "f.txt").write_text("local edit")
                ok, msg, _ = selfupdate.update()
                self.assertFalse(ok)
                self.assertIn("local modifications", msg)
                git("checkout", "f.txt", cwd=clone)
                ok, msg, changes = selfupdate.update()
                self.assertTrue(ok, msg)
                self.assertEqual((clone / "f.txt").read_text(), "v2")
                self.assertTrue(any("better tests" in c for c in changes))
                self.assertFalse(selfupdate.check(fetch=False)["available"])

    def test_auto_update_at_launch(self):
        import os

        fresh_home()
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            git("init", "-q", "-b", "main", str(d / "up"), cwd=d)
            (d / "up" / "f.txt").write_text("v1")
            git("add", ".", cwd=d / "up")
            git("commit", "-qm", "v1", cwd=d / "up")
            git("clone", "-q", str(d / "up"), str(d / "clone"), cwd=d)
            clone = d / "clone"
            with mock.patch.object(paths, "REPO_ROOT", clone):
                self.assertEqual(selfupdate.auto_update(), (False, ""))        # nothing new
                (d / "up" / "f.txt").write_text("v2")
                git("commit", "-qam", "v2", cwd=d / "up")
                (clone / "f.txt").write_text("mine")                              # local edit: never overwritten
                updated, msg = selfupdate.auto_update()
                self.assertFalse(updated)
                self.assertIn("local changes", msg)
                git("checkout", "f.txt", cwd=clone)
                with mock.patch.dict(os.environ, {"DT_NO_UPDATE": "1"}):
                    self.assertEqual(selfupdate.auto_update(), (False, ""))    # opt-out
                updated, msg = selfupdate.auto_update()
                self.assertTrue(updated, msg)
                self.assertEqual((clone / "f.txt").read_text(), "v2")
                git("remote", "set-url", "origin", str(d / "missing"), cwd=clone)
                self.assertEqual(selfupdate.auto_update()[0], False)              # offline: skipped


if __name__ == "__main__":
    unittest.main()
