import io
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from tests.helpers import fresh_home, write_suite

from deepthought.core.registry import Registry, RegistryError

SUITE = """
[suite]
id = "{id}"
name = "My suite"
version = "{version}"
project = "demo"
[detect]
files = ["demo.txt"]
[[group]]
name = "cases"
runner = "exec"
cases = "cases.toml"
"""
CASES = {"cases.toml": "[[case]]\nname = 'ok'\ncmd = 'true'\n"}


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        fresh_home()
        self.reg = Registry()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_shipped_suites_present(self):
        by_id = {s.id: s for s in self.reg.all()}
        self.assertEqual(by_id["get_next_line"].source, "builtin")
        self.assertEqual(by_id["sstyle-libft"].source, "community")
        self.assertEqual(by_id["sstyle-ft_printf"].source, "community")
        with self.assertRaises(RegistryError):
            self.reg.remove("sstyle-libft")

    def test_folder_link_and_remove_keeps_folder(self):
        src = write_suite(self.dir / "mine", SUITE.format(id="mine", version="1.0"), CASES)
        self.reg.add(str(src))
        self.assertEqual(self.reg.get("mine").source, "folder")
        self.reg.remove("mine")
        self.assertTrue(src.exists())
        self.assertNotIn("mine", self.reg.suites)

    def test_zip_roundtrip_and_replace(self):
        src = write_suite(self.dir / "zipped", SUITE.format(id="zipped", version="1.0"), CASES)
        self.reg.add(str(src))
        archive = self.reg.pack("zipped", self.dir)
        self.reg.remove("zipped")
        s = self.reg.add(str(archive))
        self.assertEqual(self.reg.get("zipped").source, "zip")
        self.assertTrue((s.path / "cases.toml").exists())
        with self.assertRaises(RegistryError):
            self.reg.add_zip(archive.read_bytes(), "again.zip")
        self.reg.add_zip(archive.read_bytes(), "again.zip", replace=True)

    def test_zip_slip_is_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../../evil/suite.toml", "x")
        with self.assertRaises(RegistryError):
            self.reg.add_zip(buf.getvalue(), "evil.zip")

    def test_git_add_and_update(self):
        origin = write_suite(self.dir / "origin", SUITE.format(id="gitsuite", version="1.0"), CASES)
        git("init", "-q", "-b", "main", cwd=origin)
        git("add", ".", cwd=origin)
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v1", cwd=origin)
        s = self.reg.add(f"file://{origin}")
        self.assertEqual(s.source, "git")
        self.assertEqual(self.reg.get("gitsuite").version, "1.0")
        (origin / "suite.toml").write_text(SUITE.format(id="gitsuite", version="2.0"))
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "v2", cwd=origin)
        msg = self.reg.update("gitsuite")
        self.assertIn("updated", msg)
        self.assertEqual(self.reg.get("gitsuite").version, "2.0")

    def test_invalid_suite_is_reported_not_fatal(self):
        bad = self.dir / "bad"
        write_suite(bad, "[suite]\nid='bad'\n")
        with self.assertRaises(RegistryError):
            self.reg.add(str(bad))

    def test_scaffold_every_runner(self):
        for runner in ("c-unit", "exec", "python-unit", "script"):
            dest = self.reg.create(f"new-{runner}", "demo", runner)
            self.assertIn(f"new-{runner}", self.reg.suites, runner)
            self.assertIn('project = "demo"', (dest / "suite.toml").read_text())


if __name__ == "__main__":
    unittest.main()
