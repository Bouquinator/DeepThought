import tempfile
import unittest
from pathlib import Path

from tests.helpers import write_suite

from deepthought.core.manifest import ManifestError, engine_compatible, load_suite

GOOD = """
[suite]
id = "demo"
name = "Demo"
project = "demo"
[[group]]
name = "G1"
runner = "c-unit"
sources = ["tests/*.c"]
matrix = { N = [1, 2], M = ["a", "b", "c"] }
[[group]]
name = "G2"
category = "bonus"
runner = "exec"
cases = "cases.toml"
"""


class ManifestTests(unittest.TestCase):
    def test_valid_suite(self):
        with tempfile.TemporaryDirectory() as d:
            write_suite(d, GOOD, {"cases.toml": "[[case]]\nname='x'\ncmd='true'\n"})
            s = load_suite(d)
            self.assertEqual(s.id, "demo")
            self.assertEqual([g.name for g in s.groups], ["G1", "G2"])
            self.assertEqual(len(s.groups[0].variants()), 6)
            self.assertEqual(s.groups[1].category, "bonus")
            self.assertEqual(s.groups[0].slug, "g1")

    def test_errors_are_collected(self):
        with tempfile.TemporaryDirectory() as d:
            write_suite(d, """
[suite]
name = "x"
[[group]]
name = "a"
runner = "nope"
[[group]]
name = "b"
runner = "exec"
cases = "missing.toml"
""")
            with self.assertRaises(ManifestError) as cm:
                load_suite(d)
            msg = " ".join(cm.exception.errors)
            self.assertIn("'id' is required", msg)
            self.assertIn("'project' is required", msg)
            self.assertIn("unknown runner 'nope'", msg)
            self.assertIn("missing.toml", msg)

    def test_invalid_toml(self):
        with tempfile.TemporaryDirectory() as d:
            write_suite(d, "[suite\nid=")
            with self.assertRaises(ManifestError) as cm:
                load_suite(d)
            self.assertIn("invalid TOML", str(cm.exception))

    def test_unknown_keys_warn(self):
        with tempfile.TemporaryDirectory() as d:
            write_suite(d, GOOD.replace('runner = "c-unit"', 'runner = "c-unit"\nsorces = []'),
                        {"cases.toml": ""})
            s = load_suite(d)
            self.assertTrue(any("sorces" in w for w in s.warnings))

    def test_fetch_and_platform_tables(self):
        with tempfile.TemporaryDirectory() as d:
            write_suite(d + "/s", GOOD.replace('[[group]]\nname = "G2"', '''[group.darwin]
ldflags = ["-Wl,-all_load"]
[group.linux]
ldflags = ["-ldl"]
env = { A = "1" }
[[group]]
name = "G2"''') + '''
[[fetch]]
name = "dep"
git = "https://example.com/x.git"
ref = "abc1234"
into = "../shared"
''', {"cases.toml": ""})
            s = load_suite(d + "/s")
            self.assertEqual(s.fetch[0]["path"], str((Path(d) / "shared").resolve()))
            import platform
            expected = {"Darwin": ["-Wl,-all_load"], "Linux": ["-ldl"]}.get(platform.system(), [])
            self.assertEqual(s.groups[0].get("ldflags"), expected)
            write_suite(d + "/bad", GOOD + '''
[[fetch]]
git = "https://example.com/x.git"
into = "../../escape"
''', {"cases.toml": ""})
            with self.assertRaises(ManifestError) as cm:
                load_suite(d + "/bad")
            self.assertIn("'into' must stay inside", str(cm.exception))

    def test_engine_ranges(self):
        self.assertTrue(engine_compatible("", "0.1.0"))
        self.assertTrue(engine_compatible(">=0.1", "0.1.0"))
        self.assertFalse(engine_compatible(">=0.2", "0.1.5"))
        self.assertTrue(engine_compatible(">=0.1,<1.0", "0.9.9"))
        self.assertFalse(engine_compatible("<1", "1.0.0"))


class VendoredTomliTests(unittest.TestCase):
    """Python 3.10 has no tomllib: every shipped TOML file must parse with the vendored tomli."""

    def test_all_toml_files(self):
        from pathlib import Path

        from deepthought._vendor import tomli

        root = Path(__file__).resolve().parents[1]
        files = [p for p in root.rglob("*.toml") if "fixtures" not in p.parts or p.name == "suite.toml"]
        self.assertGreater(len(files), 5)
        for f in files:
            with open(f, "rb") as fh:
                tomli.load(fh)


if __name__ == "__main__":
    unittest.main()
