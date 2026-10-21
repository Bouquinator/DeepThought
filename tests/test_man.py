"""The reference manual (docs/reference.md, `dt man`) documents everything public."""

import ast
import re
import unittest

from deepthought.cli import man
from deepthought.cli.main import build_parser
from deepthought.core import config, dtp, manifest, paths


class ManualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections = man.load()
        cls.entries = [e for _, es in cls.sections for e in es]

    def assertEntry(self, name):
        self.assertTrue(man.find(self.sections, name) and any(
            n.lower() == name.lower() for e in man.find(self.sections, name) for n in e.names),
            f"docs/reference.md has no entry for {name}")

    def test_every_c_macro_and_function(self):
        header = (paths.HARNESS_C / "dt.h").read_text()
        macros = set(re.findall(r"#\s*define\s+(DT_[A-Z_]+)", header)) - {"DT_H", "DT__CHK"}
        internal = {"dt_alloc_start", "dt_alloc_stop", "dt_alloc_leaks"}  # used by dt_main.c only
        functions = set(re.findall(r"\b(dt_\w+)\(", header)) - internal
        self.assertGreater(len(macros), 30)
        for name in sorted(macros | functions):
            self.assertEntry(name)
        for name in ("DT_NO_ALLOC_HOOK", "DT_NO_FORK", "DT_OUTPUT_MAX", "t_dt_test", "t_dt_capture"):
            self.assertEntry(name)

    def test_every_python_harness_function(self):
        tree = ast.parse((paths.HARNESS_PY / "dtharness.py").read_text())
        public = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)
                  and not n.name.startswith("_") and n.name != "main"]
        for name in public:
            self.assertEntry("@test" if name == "test" else name)

    def test_every_command(self):
        commands = build_parser()._subparsers._group_actions[0].choices
        for name in commands:
            self.assertEntry(f"dt {name}")

    def test_every_manifest_key(self):
        tables = {"group": "[[group]]", "fetch": "[[fetch]]"}
        for key in manifest.SUITE_KEYS:
            self.assertEntry(tables.get(key, f"[{key}]"))
        group = next(e for e in self.entries if "[[group]]" in e.names).text
        for key in manifest.GROUP_KEYS:
            self.assertIn(f"`{key}`", group, f"[[group]] entry does not document '{key}'")
        for check in manifest.CHECKS:
            self.assertEntry(check)

    def test_protocol_settings_and_placeholders(self):
        for event in dtp.TYPES:
            self.assertEntry(event)
        statuses = next(e for e in self.entries if "statuses" in e.names).text
        for status in dtp.STATUSES:
            self.assertIn(f"`{status}`", statuses)
        for key in config.DEFAULTS:
            self.assertEntry(key)
        for ph in ("project", "build", "suite", "fixtures", "out", "harness", "harness_py", "cc",
                   "matrix.NAME", "fetch.NAME"):
            self.assertEntry("{" + ph + "}")

    def test_lookup_and_render(self):
        self.assertEqual([e.names for e in man.find(self.sections, "DT_CHECK_STR")], [["DT_CHECK_STR"]])
        self.assertEqual(man.find(self.sections, "dt_check_str")[0].names, ["dt_check_str"])
        self.assertGreater(len(man.find(self.sections, "malloc")), 3)
        self.assertTrue(man.find(self.sections, "infinite loop", search_text=True))
        for e in self.entries:
            self.assertTrue(man.render(e).strip(), e.heading)


if __name__ == "__main__":
    unittest.main()
