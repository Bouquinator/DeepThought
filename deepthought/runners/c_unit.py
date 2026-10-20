"""c-unit: compile C test files with the DeepThought harness, then run them.

[[group]] keys used: sources, include, link, cflags, ldflags, before, matrix, split.

split = false  all sources are linked into one test binary (default)
split = true   every test file of the suite gets its own binary, so one
               missing/broken function only affects its own tests. Sources
               outside the suite folder (e.g. {project}/get_next_line.c) are
               linked into every binary.
"""

import hashlib
import os
import platform
import shlex
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from deepthought.core import paths, proc
from deepthought.core.template import quote_cmd
from deepthought.runners.base import DTPProcessRunner

SANITIZE_FLAGS = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g", "-DDT_NO_ALLOC_HOOK"]


def header_dirs(root, max_depth=3):
    """Directories of the project that contain headers (auto -I)."""
    root = Path(root)
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and depth < max_depth)
        if any(f.endswith(".h") for f in filenames):
            out.append(dirpath)
    return out


class Unit:
    def __init__(self, name, sources, binary):
        self.name = name
        self.sources = sources
        self.binary = binary
        self.cmd = []
        self.ok = False
        self.log = ""


class CUnitRunner(DTPProcessRunner):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.units = []
        self.test_unit = {}

    @property
    def binary(self):
        return self.outdir / "dt_tests"

    def command(self):
        return [str(self.binary)]

    def _include_dirs(self):
        dirs = [str(paths.HARNESS_C)]
        for inc in self.group.include:
            inc = self.x(inc)
            p = inc if os.path.isabs(inc) else str(Path(self.suite.path) / inc)
            dirs.append(p)
            if Path(p).resolve() == Path(self.ctx.ws.src).resolve():
                dirs.extend(header_dirs(p))
        return list(dict.fromkeys(dirs))

    def _flags(self):
        cfg = self.ctx.config
        cflags = list(cfg["cflags"]) + list(self.suite.defaults.get("cflags", []))
        cflags += [str(self.x(f)) for f in self.group.cflags]
        if self.ctx.options.get("sanitize"):
            cflags += SANITIZE_FLAGS
        includes = [arg for d in self._include_dirs() for arg in ("-I", d)]
        links = self.globs(self.group.link)
        ldflags = [str(self.x(f)) for f in self.group.ldflags]
        if platform.system() == "Linux":
            ldflags.append("-ldl")
        if self.ctx.options.get("sanitize"):
            ldflags.append("-fsanitize=address,undefined")
        return cflags, includes, links, ldflags

    def _plan_units(self):
        sources = self.globs(self.group.sources)
        if not self.group.split:
            return [Unit("", sources, self.binary)]
        suite_root = str(Path(self.suite.path).resolve())
        own = [s for s in sources if str(Path(s).resolve()).startswith(suite_root)]
        common = [s for s in sources if s not in own]
        return [Unit(Path(s).stem, [*common, s], self.outdir / f"dt_{Path(s).stem}") for s in own]

    def _fingerprint(self, cmd, files):
        h = hashlib.sha1(quote_cmd(cmd).encode())
        files = list(files) + [str(p) for p in paths.HARNESS_C.iterdir()]
        for d in self._include_dirs():
            try:
                files += [str(p) for p in Path(d).glob("*.h")]
            except OSError:
                pass
        for f in sorted(set(files)):
            try:
                st = os.stat(f)
                h.update(f"{f}\0{st.st_mtime_ns}\0{st.st_size}\n".encode())
            except OSError:
                h.update(f"{f}\0missing\n".encode())
        return h.hexdigest()

    def _compile(self, unit, cflags, includes, harness, links, ldflags):
        unit.cmd = [self.ctx.config["cc"], *cflags, *includes, *unit.sources, *harness, *links, *ldflags,
                    "-o", str(unit.binary)]
        missing = [s for s in unit.sources + links if not os.path.exists(s)]
        if missing:
            unit.log = "missing files:\n" + "\n".join(f"  {m}" for m in missing)
            if any(str(self.ctx.ws.src) in m for m in missing):
                unit.log += "\n\nYour project does not contain a file these tests need (did the build produce it?)."
            return unit
        stamp = Path(str(unit.binary) + ".stamp")
        fp = self._fingerprint(unit.cmd, unit.sources + links)
        if unit.binary.exists() and stamp.exists() and stamp.read_text() == fp:
            unit.ok, unit.log = True, "(cached: nothing changed)"
            return unit
        with self.ctx.slots:
            res = proc.run(unit.cmd, cwd=str(self.outdir), timeout=180, tracker=self.ctx.tracker)
        unit.log = res.text().replace(str(self.ctx.ws.src), str(self.ctx.ws.project_path))
        unit.ok = res.ok
        if res.ok:
            stamp.write_text(fp)
        else:
            stamp.unlink(missing_ok=True)
            if res.timed_out:
                unit.log += "\n(compilation timed out)"
        return unit

    def _harness_objects(self, cflags, includes):
        """Compile the harness once per group (split mode links it many times)."""
        hdir = self.outdir / "_harness"
        hdir.mkdir(exist_ok=True)
        objs = []
        for src in ("dt_main.c", "dt_alloc.c"):
            obj = hdir / src.replace(".c", ".o")
            cmd = [self.ctx.config["cc"], *cflags, *includes, "-c", str(paths.HARNESS_C / src), "-o", str(obj)]
            stamp = Path(str(obj) + ".stamp")
            fp = self._fingerprint(cmd, [])
            if not (obj.exists() and stamp.exists() and stamp.read_text() == fp):
                res = proc.run(cmd, cwd=str(self.outdir), timeout=120, tracker=self.ctx.tracker)
                if not res.ok:
                    raise RuntimeError(f"harness failed to compile:\n{res.text()}")
                stamp.write_text(fp)
            objs.append(str(obj))
        return objs

    def prepare(self):
        cflags, includes, links, ldflags = self._flags()
        self.units = self._plan_units()
        if not self.units:
            self.build_log = "no test sources matched: " + ", ".join(self.group.sources)
            return False
        if self.group.split:
            harness = self._harness_objects(cflags, includes)
            with ThreadPoolExecutor(max_workers=self.ctx.jobs) as pool:
                list(pool.map(lambda u: self._compile(u, cflags, includes, harness, links, ldflags), self.units))
        else:
            harness = [str(paths.HARNESS_C / "dt_main.c"), str(paths.HARNESS_C / "dt_alloc.c")]
            self._compile(self.units[0], cflags, includes, harness, links, ldflags)
        self.build_cmd = quote_cmd(self.units[0].cmd)
        logs = []
        for u in self.units:
            if u.log and u.log != "(cached: nothing changed)" or not u.ok:
                logs.append((f"── {u.name} ──\n" if u.name else "") + (u.log or "(no output)"))
        self.build_log = "\n".join(logs) or "(cached: nothing changed)"
        if not self.group.split:
            return self.units[0].ok
        return any(u.ok for u in self.units) or not self.units

    def discover(self):
        found = []
        for u in self.units:
            if not u.ok:
                tid = f"{u.name}/compile"
                found.append({"t": "discover", "id": tid, "name": "compile",
                              "desc": f"{Path(u.sources[-1]).name} did not compile or link against your code",
                              "file": u.sources[-1], "line": 1})
                self.test_unit[tid] = u
                continue
            res, events = self._exec(["--list"], 30, lambda ev: None, argv=[str(u.binary)])
            ds = [e for e in events if e["t"] == "discover"]
            if not ds and not res.ok:
                raise RuntimeError(f"test discovery failed for {u.binary.name} (exit {res.code}):\n{res.text()[-2000:]}")
            for d in ds:
                self.test_unit[d["id"]] = u
            found.extend(ds)
        return found

    def run(self, ids, on_event):
        by_unit = {}
        for tid in ids:
            by_unit.setdefault(self.test_unit[tid].binary, []).append(tid)
        res = None
        for binary, tids in by_unit.items():
            unit = self.test_unit[tids[0]]
            if not unit.ok:
                for tid in tids:
                    on_event({"t": "start", "id": tid})
                    on_event({"t": "end", "id": tid, "status": "build_error",
                              "reason": "this test file did not compile against your code (missing function? wrong prototype?)",
                              "output": unit.log[-3000:]})
                continue
            budget = self.timeout * max(1, len(tids)) + 10
            res, _ = self._exec(["--run", *tids], budget, on_event, argv=[str(binary)])
        return res

    def repro(self, test_id):
        unit = self.test_unit.get(test_id)
        if unit and not unit.ok:
            return f"cd {shlex.quote(str(self.outdir))} && {quote_cmd(unit.cmd)}"
        env = {k: v for k, v in self.env().items() if k in ("DT_FIXTURES", "DT_TIMEOUT") or k.startswith("DT_MATRIX_")}
        envs = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
        binary = unit.binary if unit else self.binary
        return f"cd {shlex.quote(str(self.outdir))} && {envs} ./{binary.name} --run {shlex.quote(test_id)}"

    def env(self):
        env = super().env()
        if self.ctx.options.get("sanitize"):
            env["ASAN_OPTIONS"] = "abort_on_error=1:detect_leaks=0:print_summary=1"
            env["UBSAN_OPTIONS"] = "print_stacktrace=1:halt_on_error=1"
        return env
