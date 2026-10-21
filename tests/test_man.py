"""The reference manual (docs/reference.md, `dt man`) documents everything public."""

import ast
import json
import re
import tempfile
import unittest

from deepthought.cli import man
from deepthought.cli.main import build_parser
from deepthought.core import config, dtp, manifest, paths
from deepthought.manual import build as web
from deepthought.manual.markdown import Renderer, code_block


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


class WebManualTests(unittest.TestCase):
    def test_markdown(self):
        r = Renderer(code=lambda c: "#/ref/x" if c == "DT_X" else None)
        out = r.render("# T\n\nA *b* **c** `<i>` [l](http://x)\n\n| a | b |\n|---|---|\n| `DT_X` | x \\| y |\n\n"
                       "- one\n  - two\n- [ ] task\n\n> note\n\n```c\nint x = \"</script>\";\n```\n")
        self.assertIn('<h1 id="t">T</h1>', out)
        self.assertIn("<em>b</em> <strong>c</strong> <code>&lt;i&gt;</code>", out)
        self.assertIn('<a href="http://x" target="_blank" rel="noopener">l</a>', out)
        self.assertIn('<a class="xref" href="#/ref/x"><code>DT_X</code></a>', out)
        self.assertIn("<td>x | y</td>", out)
        self.assertIn("<ul><li>one<ul><li>two</li></ul></li>", out)
        self.assertIn('class="task"', out)
        self.assertIn("<blockquote>", out)
        self.assertNotIn("</script>", out)
        self.assertIn('<span class="t-kw">int</span>', code_block("int x;", "c"))
        linked = Renderer(link=lambda u: "/" + u).render("see [`suites/x`](x.md) and [`[[group]]`](y)")
        self.assertIn('<a href="/x.md"><code>suites/x</code></a>', linked)
        self.assertIn('<a href="/y"><code>[[group]]</code></a>', linked)

    def test_build(self):
        with tempfile.TemporaryDirectory() as d:
            page = web.build(d, initial="#/ref/DT_TEST", theme="dark")
            html = page.read_text()
        self.assertEqual(html.count("</script>"), 1, "the data must not close the script element")
        blob = html.split("const DATA = ", 1)[1].split("\nconst $ =", 1)[0].strip().rstrip(";")
        data = json.loads(blob)
        self.assertEqual(data["initial"], "#/ref/DT_TEST")
        names = {n for s in data["reference"]["sections"] for e in s["entries"] for n in e["names"]}
        self.assertEqual(len(names), len({n for _, es in man.load() for e in es for n in e.names}))
        pages = {p["id"]: p for p in data["pages"]}
        self.assertEqual(set(pages), {"protocol", "writing-suites", "architecture"})
        # every internal link of every page leads somewhere
        everything = json.dumps(data)
        for kind, target in re.findall(r'href=\\"#/(ref|doc)/([^"\\]*)', everything):
            if kind == "doc":
                page_id, _, anchor = target.partition("/")
                self.assertIn(page_id, pages, target)
                if anchor:
                    self.assertIn(anchor, {h["id"] for h in pages[page_id]["toc"]} | set(
                        re.findall(r'id="([^"]+)"', pages[page_id]["html"])), target)
            elif target:
                anchors = {s["anchor"] for s in data["reference"]["sections"]}
                self.assertTrue(target in names or target in anchors, f"#/ref/{target}")


if __name__ == "__main__":
    unittest.main()
