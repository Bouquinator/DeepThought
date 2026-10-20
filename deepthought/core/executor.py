"""Runs: plan → workspace → build → checks → tests → score → history.

RunManager is the single entry point used by the CLI, the TUI and the web
server. Every state change is published on the EventBus as:

  {"type": "run",   "run_id", "run": <summary>}           status / score changes
  {"type": "snapshot", "run_id", "run": <full run>}       a new run was created
  {"type": "stage", "run_id", "stage": {...}}
  {"type": "group", "run_id", "group": {... without tests}}
  {"type": "tests", "run_id", "gid", "tests": [...]}      discovery
  {"type": "test",  "run_id", "gid", "test": {...}}
  {"type": "watch", "project", "enabled"}
"""

import dataclasses
import itertools
import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from deepthought.checks import CHECKS, TITLES
from deepthought.checks import make as make_check
from deepthought.core import history, paths, proc
from deepthought.core.events import EventBus
from deepthought.core.models import (BUILD_ERROR, DONE_STATUSES, ERROR, FAILED_STATUSES, LEAK, PASS,
                                     PENDING, RUNNING, SKIP, GroupState, RunState, StageState, TestState)
from deepthought.core.project import ProjectStore, detect
from deepthought.core.template import as_argv, expand
from deepthought.core.workspace import Workspace, fingerprint
from deepthought.runners import get_runner
from deepthought.runners.base import shard

MAX_ASSERTS = 30
_ids = itertools.count()
_FETCH_LOCK = threading.Lock()  # one download per dependency at a time, across runs


class RunError(Exception):
    pass


def extract_source(file, line, max_lines=60):
    """The test's code, from its declaration line to the end of its body."""
    try:
        lines = Path(file).read_text(errors="replace").splitlines()
    except OSError:
        return ""
    if not 0 < line <= len(lines):
        return ""
    start = line - 1
    if file.endswith(".py"):
        while start > 0 and lines[start - 1].lstrip().startswith("@"):
            start -= 1
        body = [lines[start]]
        i = start + 1
        while i < len(lines) and not lines[i].lstrip().startswith("def "):
            body.append(lines[i])
            i += 1
        while i < len(lines) and len(body) < max_lines:
            body.append(lines[i])
            i += 1
            if i < len(lines) and lines[i] and not lines[i][0].isspace():
                break
        return "\n".join(body).rstrip()
    out, depth, opened = [], 0, False
    for text in lines[start:start + max_lines]:
        out.append(text)
        depth += text.count("{") - text.count("}")
        opened = opened or "{" in text
        if opened and depth <= 0:
            break
    return "\n".join(out)


def context_lines(file, line, radius=3):
    """A few lines around file:line, for asserts that live in helper functions."""
    try:
        lines = Path(file).read_text(errors="replace").splitlines()
    except OSError:
        return None
    if not 0 < line <= len(lines):
        return None
    start = max(1, line - radius)
    return {"start": start, "code": "\n".join(lines[start - 1:line + radius])}


def _asan_reason(output):
    """One readable line from AddressSanitizer / UBSan output, with the location."""
    m = re.search(r"SUMMARY: (AddressSanitizer|LeakSanitizer): (.+)", output)
    if m:
        return f"{m.group(1)}: {m.group(2).strip()}"
    m = re.search(r"ERROR: (AddressSanitizer|LeakSanitizer): (.+)", output)
    if m:
        return f"{m.group(1)}: {m.group(2).strip()}"
    m = re.search(r"(\S+:\d+:\d+): runtime error: (.+)", output)
    if m:
        return f"undefined behaviour at {Path(m.group(1)).name}: {m.group(2).strip()}"
    return ""


class RunContext:
    def __init__(self, manager, run, ws, options):
        self.manager = manager
        self.run = run
        self.ws = ws
        self.config = manager.config
        self.options = options
        self.bus = manager.bus
        self.tracker = proc.ProcTracker()
        jobs = int(options.get("jobs") or self.config["jobs"])
        self.jobs = max(1, jobs)
        self.slots = threading.BoundedSemaphore(self.jobs)
        self.lock = threading.RLock()
        self._once = {}
        self._once_lock = threading.Lock()

    def template_vars(self, suite, group=None, variant=None, outdir=None):
        v = {
            "project": str(self.ws.src), "build": str(self.ws.src), "suite": str(suite.path),
            "harness": str(paths.HARNESS_C), "harness_py": str(paths.HARNESS_PY),
            "fixtures": str(Path(suite.path) / "fixtures"), "cc": self.config["cc"],
        }
        if outdir:
            v["out"] = str(outdir)
        for k, val in (variant or {}).items():
            v[f"matrix.{k}"] = val
        for f in getattr(suite, "fetch", []):
            v[f"fetch.{f['name']}"] = f["path"]
        return v

    def x(self, value, suite):
        return expand(value, self.template_vars(suite))

    def run_once(self, argv, cwd, timeout=300):
        """Run a project command once per run (make, make bonus…), serialised."""
        key = (tuple(argv), cwd)
        with self._once_lock:
            if key not in self._once:
                self._once[key] = proc.run(argv, cwd=cwd, timeout=timeout, tracker=self.tracker,
                                           env=make_check.build_env(self))
            return self._once[key]

    def emit(self, type_, **payload):
        self.bus.publish({"type": type_, "run_id": self.run.id, **payload})


class RunManager:
    def __init__(self, config, registry, bus=None):
        self.config = config
        self.registry = registry
        self.bus = bus or EventBus()
        self.projects = ProjectStore()
        self.runs = {}
        self.contexts = {}
        self.watchers = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ queries
    def get(self, run_id):
        run = self.runs.get(run_id)
        if run:
            ctx = self.contexts.get(run_id)
            if ctx:
                with ctx.lock:
                    return run.to_dict()
            return run.to_dict()
        return history.load(run_id)

    def active_run(self, project_path):
        path = str(Path(project_path).resolve())
        for rid, run in reversed(list(self.runs.items())):
            if run.project["path"] == path and run.status in (PENDING, RUNNING):
                return run
        return None

    def suites_for(self, project_path):
        """(mode, kind, suites) that would run for a project, without raising.

        mode is "linked" (the user chose the suites), "kind" (the user set the
        project type: every enabled suite of that type) or "auto" (detection).
        """
        entry = self.projects.get(str(Path(project_path).expanduser().resolve()))
        linked = [self.registry.suites[u] for u in entry.get("suites") or [] if u in self.registry.suites]
        if linked:
            kind = entry.get("kind") if entry.get("kind_manual") else linked[0].project
            return "linked", kind or linked[0].project, linked
        if entry.get("kind_manual") and entry.get("kind"):
            kind = entry["kind"]
            return "kind", kind, [s for s in self.registry.enabled() if s.project == kind]
        kind, suites = detect(project_path, self.registry.enabled())
        return "auto", kind, suites

    def resolve_suites(self, project_path, suite_uids=None):
        if suite_uids:
            return [self.registry.get(u) for u in suite_uids]
        mode, kind, suites = self.suites_for(project_path)
        if not suites:
            if mode == "kind":
                raise RunError(f"no enabled suite targets the project type '{kind}'. Link suites to this "
                               "project (`dt project link`, or Suites in the UI) or create one (`dt suite new`).")
            raise RunError(
                f"no installed suite recognises {project_path}. Link suites to it (`dt project link PATH SUITE`, "
                "or the Suites button in the UI), set its type (`dt project kind PATH TYPE`), "
                "or pick suites explicitly (--suite ID)."
            )
        return suites

    # ------------------------------------------------------------ starting
    def start(self, project_path, suite_uids=None, options=None, only=None, base_run=None, wait=False):
        project_path = Path(project_path).expanduser().resolve()
        if not project_path.is_dir():
            raise RunError(f"{project_path} is not a directory")
        suites = self.resolve_suites(project_path, suite_uids)
        options = dict(options or {})
        # the project's saved build options, overridden by this run's options
        saved = self.projects.get(str(project_path)).get("build") or {}
        build = {**saved, **{k: v for k, v in (options.get("build") or {}).items() if v not in (None, "")}}
        build = {k: v for k, v in build.items() if v not in (None, "", {}, False)}
        if build:
            options["build"] = build
        else:
            options.pop("build", None)
        options["clean"] = bool(options.get("clean") or build.get("clean"))
        options.setdefault("sanitize", self.config["sanitize"])
        options.setdefault("leaks", self.config["leaks"])
        entry = self.projects.get(str(project_path))
        if entry.get("kind_manual") and entry.get("kind"):
            kind = entry["kind"]  # the user's own project type
        elif suite_uids:
            kind = suites[0].project
        else:
            kind = self.suites_for(project_path)[1] or suites[0].project
        rid = f"{history.new_run_id()}{next(_ids) % 100:02d}"
        run = RunState(
            id=rid,
            project={"path": str(project_path), "name": project_path.name, "kind": kind},
            suites=[{"uid": s.uid, "name": s.name, "version": s.version, "source": s.source} for s in suites],
            options={**options, "suites": [s.uid for s in suites]},
            base_run=(base_run or {}).get("id", "") if base_run else "",
        )
        ws = Workspace(paths.cache_dir(self.config["cache_dir"]), project_path,
                       flavor="asan" if options.get("sanitize") else "")
        ctx = RunContext(self, run, ws, options)
        self._plan(ctx, suites, only, base_run)
        with self._lock:
            self.runs[rid] = run
            self.contexts[rid] = ctx
            while len(self.runs) > 30:
                old = next(iter(self.runs))
                if self.runs[old].status in DONE_STATUSES | {"done", "cancelled", "error"}:
                    self.runs.pop(old)
                    self.contexts.pop(old, None)
                else:
                    break
        self.projects.add(str(project_path), kind)
        ctx.emit("snapshot", run=run.to_dict())
        t = threading.Thread(target=self._execute, args=(ctx, suites), daemon=True, name=f"run-{rid}")
        t.start()
        if wait:
            t.join()
        return run

    def rerun(self, run_id, failed_only=True, options=None, tids=None):
        base = self.get(run_id)
        if not base:
            raise RunError(f"unknown run {run_id}")
        opts = {k: v for k, v in base.get("options", {}).items() if k != "suites"}
        opts.update(options or {})
        only = None
        if tids:
            only = set(tids)
        elif failed_only:
            only = {t["tid"] for g in base["groups"] for t in g["tests"] if t["status"] in FAILED_STATUSES}
            only |= {g["gid"] + "::*" for g in base["groups"] if g["status"] in (BUILD_ERROR, ERROR) and not g["tests"]}
            if not only:
                only = None
        return self.start(base["project"]["path"], base["options"].get("suites"), opts, only=only,
                          base_run=base if only else None)

    def cancel(self, run_id):
        ctx = self.contexts.get(run_id)
        if ctx and ctx.run.status in (PENDING, RUNNING):
            ctx.tracker.cancel()
            return True
        return False

    # ------------------------------------------------------------ planning
    def _plan(self, ctx, suites, only, base_run):
        run = ctx.run
        base_groups = {g["gid"]: g for g in (base_run or {}).get("groups", [])}
        ctx.only = only
        ctx.plan = []
        run.stages.append(StageState("workspace", "Workspace"))
        ctx.fetches = {}
        for s in suites:
            for f in s.fetch:
                ctx.fetches.setdefault(f["path"], (f, []))[1].append(s)
        if ctx.fetches:
            run.stages.append(StageState("fetch", "Test sources"))
        builds = {}
        for s in suites:
            argv = make_check.build_argv(ctx, s)
            if argv:
                builds.setdefault(tuple(argv), []).append(s)
            elif make_check.wants_python_check(s):
                builds.setdefault(("<python syntax check>",), []).append(s)
        ctx.builds = []
        for i, (argv, ss) in enumerate(builds.items()):
            name = "Syntax check" if argv == ("<python syntax check>",) else "Build"
            st = StageState(f"build:{i}", name, message=" ".join(argv).replace(str(ctx.ws.src), "<project>"))
            run.stages.append(st)
            ctx.builds.append((st, ss))
        ctx.checks = []
        seen = {}
        for s in suites:
            for check in s.checks:
                if check not in CHECKS:
                    continue
                cfg_key = (check, repr(getattr(s, check, None) if check in ("forbidden", "norminette", "files")
                                       else s.build.get("rules") if check == "rules" else s.build.get("command")))
                if cfg_key in seen:
                    continue
                sid = f"{check}:{s.uid}" if any(k[0] == check for k in seen) else check
                seen[cfg_key] = True
                st = StageState(sid, TITLES[check])
                run.stages.append(st)
                ctx.checks.append((check, s, st))
        for s in suites:
            for group in s.groups:
                for variant in group.variants():
                    vtag = ",".join(f"{k}={v}" for k, v in variant.items())
                    gid = f"{s.uid}/{group.slug}" + (f"[{vtag}]" if vtag else "")
                    name = group.name + (f"  [{vtag}]" if vtag else "")
                    gs = GroupState(gid=gid, suite=s.uid, name=name, category=group.category,
                                    runner=group.runner, variant=variant)
                    carry = None
                    if only is not None:
                        wanted = {t.split("::", 1)[1] for t in only if t.split("::", 1)[0] == gid}
                        if not wanted and gid in base_groups:
                            carry = base_groups[gid]
                    if carry:
                        for k in ("status", "message", "build_log", "build_cmd", "cwd"):
                            setattr(gs, k, carry.get(k, getattr(gs, k)))
                        for t in carry.get("tests", []):
                            ts = TestState(**{f.name: t.get(f.name) for f in dataclasses.fields(TestState)
                                              if f.name in t})
                            ts.carried = True
                            gs.tests[ts.id] = ts
                    run.groups.append(gs)
                    ctx.plan.append((gs, s, group, variant, carry is not None))

    # ------------------------------------------------------------ executing
    def _execute(self, ctx, suites):
        run = ctx.run
        run.status = RUNNING
        run.started = time.time()
        ctx.emit("run", run=run.summary())
        try:
            self._stage_workspace(ctx)
            failed_suites = set()
            self._stage_fetch(ctx, failed_suites)
            for st, ss in ctx.builds:
                self._set_stage(ctx, st, RUNNING)
                ok = make_check.build(ctx, ss[0], st)
                if not ok:
                    failed_suites.update(s.uid for s in ss)
                ctx.emit("stage", stage=st.to_dict())
            if ctx.tracker.cancelled:
                raise _Cancelled()
            # Makefile checks touch the build products: run them before tests.
            parallel_checks = []
            for check, s, st in ctx.checks:
                if s.uid in failed_suites and check in ("relink", "forbidden"):
                    st.status, st.message = SKIP, "the build failed"
                    ctx.emit("stage", stage=st.to_dict())
                elif check in ("norminette",):
                    parallel_checks.append((check, s, st))
                else:
                    self._run_check(ctx, check, s, st)
            # Groups' `before` steps (e.g. `make bonus`) rewrite build products that other
            # groups link against: run them all first, serially, before any group compiles.
            for gs, suite, group, variant, carried in ctx.plan:
                if carried or suite.uid in failed_suites or not group.before:
                    continue
                if self._when_ok(ctx, group)[0]:
                    for argv in self._before_argvs(ctx, suite, group, variant):
                        ctx.run_once(argv, cwd=str(ctx.ws.src))
            with ThreadPoolExecutor(max_workers=max(2, ctx.jobs)) as pool:
                futures = [pool.submit(self._run_check, ctx, c, s, st) for c, s, st in parallel_checks]
                todo = [(gs, s, g, v) for gs, s, g, v, carried in ctx.plan if not carried]
                # suites with [defaults] sequential = true run their groups one after another
                serial = {}
                for item in todo:
                    if item[1].defaults.get("sequential"):
                        serial.setdefault(item[1].uid, []).append(item)
                    else:
                        futures.append(pool.submit(self._run_group, ctx, *item, failed_suites))
                for items in serial.values():
                    futures.append(pool.submit(
                        lambda its: [self._run_group(ctx, *it, failed_suites) for it in its], items))
                for f in futures:
                    f.result()
            if ctx.tracker.cancelled:
                raise _Cancelled()
            run.status = "done"
        except _Cancelled:
            run.status = "cancelled"
            for t in run.all_tests():
                if t.status in (PENDING, RUNNING):
                    t.status, t.reason = SKIP, "run cancelled"
            for g in run.groups:
                if g.status in (PENDING, RUNNING):
                    g.status = SKIP
        except Exception as e:  # engine bug: report it instead of dying silently
            run.status = "error"
            run.error = f"{e}\n{traceback.format_exc()}"
        finally:
            run.finished = time.time()
            self._finalize(ctx)

    def _set_stage(self, ctx, st, status):
        st.status = status
        ctx.emit("stage", stage=st.to_dict())

    def _stage_workspace(self, ctx):
        st = ctx.run.stages[0]
        self._set_stage(ctx, st, RUNNING)
        t0 = time.monotonic()
        changes = ctx.ws.sync()
        st.ms = int((time.monotonic() - t0) * 1000)
        st.status = PASS
        st.message = f"{changes} file(s) synced to the isolated build folder"
        st.log = str(ctx.ws.root)
        ctx.emit("stage", stage=st.to_dict())

    def _stage_fetch(self, ctx, failed_suites):
        """Download the suites' [[fetch]] dependencies (pinned git checkouts)."""
        if not ctx.fetches:
            return
        from deepthought.core.sources import git

        st = next(x for x in ctx.run.stages if x.id == "fetch")
        self._set_stage(ctx, st, RUNNING)
        t0 = time.monotonic()
        logs, bad = [], []
        for path, (f, suites) in ctx.fetches.items():
            try:
                with _FETCH_LOCK:
                    msg = git.ensure(f["git"], f["ref"], path)
                logs.append(f"{f['name']}: {msg}")
            except git.GitError as e:
                logs.append(f"{f['name']}: FAILED — {e}")
                bad.append(f["name"])
                failed_suites.update(s.uid for s in suites)
                ctx.fetch_failed = getattr(ctx, "fetch_failed", set()) | {s.uid for s in suites}
        st.ms = int((time.monotonic() - t0) * 1000)
        st.log = "\n".join(logs)
        st.items = [{"label": f"{f['name']}  {f['git']}" + (f" @ {f['ref'][:10]}" if f["ref"] else ""),
                     "ok": f["name"] not in bad} for f, _ in ctx.fetches.values()]
        if bad:
            st.status = "fail"
            st.message = f"could not download {', '.join(bad)} (offline? see the log)"
        else:
            st.status = PASS
            st.message = "; ".join(logs)
        ctx.emit("stage", stage=st.to_dict())

    def _run_check(self, ctx, check, suite, st):
        self._set_stage(ctx, st, RUNNING)
        t0 = time.monotonic()
        try:
            CHECKS[check](ctx, suite, st)
        except Exception as e:
            st.status, st.message = ERROR, f"check crashed: {e}"
            st.log += traceback.format_exc()
        st.ms = st.ms or int((time.monotonic() - t0) * 1000)
        ctx.emit("stage", stage=st.to_dict())

    def _when_ok(self, ctx, group):
        when = group.when or {}
        src = ctx.ws.src
        missing = [f for f in when.get("files", []) if not any(src.glob(f))]
        if missing:
            return False, f"not present: {', '.join(missing)}"
        anyf = when.get("any_files", [])
        if anyf and not any(any(src.glob(f)) for f in anyf):
            return False, f"none of: {', '.join(anyf)}"
        rule = when.get("make_rule")
        if rule:
            mk = src / "Makefile"
            if not mk.exists() or not re.search(rf"^{re.escape(rule)}\s*:", mk.read_text(errors='replace'), re.M):
                return False, f"the Makefile has no '{rule}' rule"
        return True, ""

    def _before_argvs(self, ctx, suite, group, variant):
        out = []
        for cmd in group.before:
            argv = as_argv(cmd, ctx.template_vars(suite, group, variant))
            if make_check.is_make(argv):  # same variables (CFLAGS…) as the main build
                argv += make_check.make_args(ctx, suite, variables_only=True)
            out.append(argv)
        return out

    def _run_group(self, ctx, gs, suite, group, variant, failed_suites):
        try:
            self._run_group_inner(ctx, gs, suite, group, variant, failed_suites)
        except Exception as e:
            gs.status = ERROR
            gs.message = f"runner error: {e}"
            gs.build_log += "\n" + traceback.format_exc()
            for t in gs.tests.values():
                if t.status in (PENDING, RUNNING):
                    t.status, t.reason = ERROR, "runner error"
        ctx.emit("group", group=gs.to_dict(with_tests=False))

    def _run_group_inner(self, ctx, gs, suite, group, variant, failed_suites):
        if ctx.tracker.cancelled:
            return
        if suite.uid in getattr(ctx, "fetch_failed", set()):
            gs.status, gs.message = BUILD_ERROR, "the suite's test sources could not be downloaded"
            return
        if suite.uid in failed_suites:
            gs.status, gs.message = BUILD_ERROR, "the project failed to build"
            return
        ok, why = self._when_ok(ctx, group)
        if not ok:
            gs.status, gs.message = SKIP, f"skipped: {why}"
            return
        slug = group.slug + ("-" + "-".join(f"{k}{v}" for k, v in variant.items()) if variant else "")
        outdir = ctx.ws.group_dir(suite.uid, slug)
        gs.cwd = str(outdir)
        runner = get_runner(group.runner)(ctx, suite, group, variant, outdir)
        gs.status, gs.message = RUNNING, "compiling…"
        ctx.emit("group", group=gs.to_dict(with_tests=False))
        logs = []
        for argv in self._before_argvs(ctx, suite, group, variant):
            res = ctx.run_once(argv, cwd=str(ctx.ws.src))  # already run (cached) before the groups
            logs.append(f"$ {' '.join(argv)}\n{res.text()}")
            if not res.ok:
                gs.status, gs.message = BUILD_ERROR, f"`{' '.join(argv)}` failed"
                gs.build_log = "\n".join(logs)
                return
        ok = runner.prepare()
        gs.build_cmd = runner.build_cmd
        gs.build_log = "\n".join(logs + [runner.build_log]).strip()
        if not ok:
            gs.status, gs.message = BUILD_ERROR, "the tests did not compile against your code"
            return
        found = runner.discover()
        only = ctx.only
        wanted = None
        if only is not None:
            wanted = {t.split("::", 1)[1] for t in only if t.split("::", 1)[0] == gs.gid}
            if "*" in wanted:
                wanted = None
        to_run = []
        with ctx.lock:
            for ev in found:
                tid = ev["id"]
                ts = TestState(tid=f"{gs.gid}::{tid}", id=tid, name=ev.get("name") or tid.split("/")[-1],
                               gid=gs.gid, desc=ev.get("desc", ""), file=ev.get("file", ""),
                               line=int(ev.get("line") or 0))
                ts.source = extract_source(ts.file, ts.line) if ts.file else ""
                ts.repro = runner.repro(tid)
                if wanted is not None and tid not in wanted:
                    ts.status, ts.carried = SKIP, True
                    ts.reason = "not selected in this re-run"
                else:
                    to_run.append(tid)
                gs.tests[tid] = ts
            gs.message = f"{len(to_run)} test(s)"
        ctx.emit("tests", gid=gs.gid, tests=[t.to_dict() for t in gs.tests.values()])
        ctx.emit("group", group=gs.to_dict(with_tests=False))

        leaks_on = ctx.options.get("leaks", True) and group.leaks is not False

        def on_event(ev):
            t = ev.get("t")
            ts = gs.tests.get(ev.get("id", ""))
            if ts is None:
                return
            with ctx.lock:
                if t == "start":
                    ts.status = RUNNING
                    ctx.emit("test", gid=gs.gid, test=ts.to_dict())
                elif t == "assert" and not ev.get("ok", False):
                    if len(ts.asserts) < MAX_ASSERTS:
                        a = {k: ev.get(k) for k in ("msg", "expected", "actual", "file", "line", "input", "cmp")}
                        body_end = ts.line + ts.source.count("\n")
                        if a["file"] and a["line"] and not (a["file"] == ts.file and ts.line <= a["line"] <= body_end):
                            a["context"] = context_lines(a["file"], int(a["line"]))
                        ts.asserts.append(a)
                elif t == "log":
                    ts.logs.append(str(ev.get("msg", "")))
                elif t == "input":
                    ts.input = str(ev.get("value", ""))
                elif t == "leak":
                    ts.leaks = {"bytes": ev.get("bytes", 0), "count": ev.get("count", 0)}
                elif t == "end":
                    ts.status = ev.get("status", ERROR)
                    ts.ms = int(ev.get("ms") or 0)
                    ts.signal = ev.get("signal", "")
                    ts.reason = ev.get("reason", "")
                    ts.output = ev.get("output", "")
                    ts.exit = ev.get("exit")
                    sanitizer = _asan_reason(ts.output) if ts.output else ""
                    if sanitizer:  # far more precise than "killed by SIGABRT"
                        ts.reason = sanitizer
                    if ts.status == "timeout" and not ts.reason:
                        ts.reason = f"did not finish within {runner.timeout:g}s (infinite loop? blocking read?)"
                    if ts.status == LEAK and not leaks_on:
                        ts.status = PASS
                        ts.logs.append("leak ignored (leak checks are off)")
                    if ts.status == "fail" and not ts.asserts and ts.exit not in (None, 0, 1):
                        ts.reason = ts.reason or f"the test process exited with code {ts.exit} (exit() called?)"
                    elif ts.status == "fail" and not ts.asserts and not ts.reason:
                        ts.reason = "failed without an assertion message"
                    ctx.emit("test", gid=gs.gid, test=ts.to_dict())

        chunks = shard(to_run, ctx.jobs)

        def run_chunk(chunk):
            res = runner.run(chunk, on_event)
            with ctx.lock:
                for tid in chunk:
                    ts = gs.tests[tid]
                    if ts.status in (PENDING, RUNNING):
                        if ctx.tracker.cancelled:
                            ts.status, ts.reason = SKIP, "run cancelled"
                        elif res is not None and res.timed_out:
                            ts.status, ts.reason = "timeout", "the test process exceeded its total time budget"
                        else:
                            ts.status = "crash" if ts.status == RUNNING else ERROR
                            tail = res.text()[-1500:] if res is not None else ""
                            ts.reason = "the test process died unexpectedly" + (f":\n{tail}" if tail else "")
                        ctx.emit("test", gid=gs.gid, test=ts.to_dict())

        if len(chunks) <= 1:
            for c in chunks:
                run_chunk(c)
        else:
            with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
                list(pool.map(run_chunk, chunks))
        gs.message = ""
        gs.status = PENDING
        gs.refresh_status()
        if gs.status == PENDING:
            gs.status = PASS

    def _finalize(self, ctx):
        run = ctx.run
        from deepthought.core.scoring import score_run
        with ctx.lock:
            for g in run.groups:
                if g.status == RUNNING:
                    g.refresh_status()
            run.score = score_run(run)
            prev = history.previous(run.project["path"], run.id, bool(run.options.get("sanitize")))
            reg, fix = history.mark_changes(run, prev)
            run.score["regressions"] = reg
            run.score["fixed"] = fix
            data = run.to_dict()
        try:
            history.save(data)
            self.projects.record_run(run.project["path"], run.id, run.score.get("grade"))
        except OSError as e:
            run.error = run.error or f"could not save history: {e}"
        ctx.emit("snapshot", run=data)
        ctx.emit("run", run=run.summary())

    # ------------------------------------------------------------ watch mode
    def watch(self, project_path, enabled, options=None, suite_uids=None):
        path = str(Path(project_path).expanduser().resolve())
        old = self.watchers.pop(path, None)
        if old:
            old.stop()
        if enabled:
            from deepthought.core.watch import Watcher

            def on_change():
                active = self.active_run(path)
                if active:
                    self.cancel(active.id)
                    time.sleep(0.3)
                try:
                    self.start(path, suite_uids, options)
                except RunError as e:
                    self.bus.publish({"type": "watch", "project": path, "enabled": True, "error": str(e)})

            w = Watcher(path, on_change)
            w.start()
            self.watchers[path] = w
        self.bus.publish({"type": "watch", "project": path, "enabled": enabled})
        return enabled


class _Cancelled(Exception):
    pass


def project_fingerprint(path):
    return fingerprint(path)
