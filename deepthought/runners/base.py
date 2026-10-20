"""Runner interface and the shared machinery for DTP-speaking test processes."""

import glob
import math
import os
import shlex
import threading
from pathlib import Path

from deepthought.core import dtp, proc
from deepthought.core.template import expand, quote_cmd


class Runner:
    """One instance per (group, matrix variant) per run.

    prepare()  -> bool        compile / set up; False = build error (set self.build_log)
    discover() -> [dict]      DTP 'discover' events (id, name, desc, file, line)
    run(ids, on_event)        run tests, report DTP events through on_event
    repro(test_id) -> str     shell command reproducing one test
    """

    def __init__(self, ctx, suite, group, variant, outdir):
        self.ctx = ctx
        self.suite = suite
        self.group = group
        self.variant = variant
        self.outdir = Path(outdir)
        self.build_log = ""
        self.build_cmd = ""
        self.vars = ctx.template_vars(suite, group, variant, outdir)

    # helpers
    def x(self, value):
        return expand(value, self.vars)

    def globs(self, patterns, base=None):
        """Expand placeholders then globs; relative paths are relative to the suite."""
        base = Path(base or self.suite.path)
        out = []
        for pat in patterns:
            pat = self.x(pat)
            full = pat if os.path.isabs(pat) else str(base / pat)
            matches = sorted(glob.glob(full))
            if not matches and not any(c in pat for c in "*?["):
                matches = [full]  # keep explicit paths so the error says which is missing
            out.extend(matches)
        return out

    @property
    def timeout(self):
        t = self.ctx.options.get("timeout") or self.group.timeout or self.ctx.config["timeout"]
        return float(t)

    @property
    def fixtures(self):
        return str(Path(self.suite.path) / self.x(self.group.fixtures or "fixtures"))

    def env(self):
        env = {"DT_FIXTURES": self.fixtures, "DT_PROJECT": str(self.ctx.ws.src),
               "DT_SUITE": str(self.suite.path), "DT_TIMEOUT": str(self.timeout)}
        for k, v in self.variant.items():
            env[f"DT_MATRIX_{k}"] = str(v)
        for k, v in self.group.get("env").items():
            env[k] = str(self.x(v))
        return env

    def prepare(self):
        return True

    def discover(self):
        raise NotImplementedError

    def run(self, ids, on_event):
        raise NotImplementedError

    def repro(self, test_id):
        return ""


class DTPProcessRunner(Runner):
    """A runner whose tests live in a process supporting --list / --run ids."""

    def command(self):
        raise NotImplementedError

    def cwd(self):
        return str(self.outdir)

    def _exec(self, args, timeout, on_event, argv=None):
        argv = argv or self.command()
        r, w = os.pipe()
        events = []

        def reader():
            with os.fdopen(r, "rb") as f:
                for line in f:
                    ev = dtp.parse(line)
                    if ev is None:
                        continue
                    if ev["t"] == "hello" and not dtp.compatible(ev):
                        on_event({"t": "log", "id": "", "msg": "harness speaks a newer protocol: update the tester"})
                    events.append(ev)
                    on_event(ev)

        t = threading.Thread(target=reader, daemon=True)
        t.start()
        env = self.env()
        env["DT_REPORT_FD"] = str(w)
        closed = []

        def close_w(_p=None):
            if not closed:
                closed.append(True)
                os.close(w)

        with self.ctx.slots:
            res = proc.run(list(argv) + list(args), cwd=self.cwd(), env=env, timeout=timeout,
                           tracker=self.ctx.tracker, pass_fds=(w,), on_start=close_w)
        close_w()  # spawn failed: on_start never ran
        t.join(timeout=5)
        return res, events

    def discover(self):
        res, events = self._exec(["--list"], 30, lambda ev: None)
        found = [e for e in events if e["t"] == "discover"]
        if not found and not res.ok:
            raise RuntimeError(f"test discovery failed (exit {res.code}):\n{res.text()[-2000:]}")
        return found

    def run(self, ids, on_event):
        budget = self.timeout * max(1, len(ids)) + 10
        res, _ = self._exec(["--run", *ids], budget, on_event)
        return res

    def repro(self, test_id):
        env = {k: v for k, v in self.env().items() if k in ("DT_FIXTURES", "DT_TIMEOUT", "DT_PROJECT") or k.startswith("DT_MATRIX_")}
        envs = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
        return f"cd {shlex.quote(self.cwd())} && {envs} {quote_cmd(self.command())} --run {shlex.quote(test_id)}"


def shard(ids, jobs):
    """Split test ids into roughly balanced chunks for parallel processes."""
    if not ids:
        return []
    k = max(1, min(jobs, math.ceil(len(ids) / 6)))
    size = math.ceil(len(ids) / k)
    return [ids[i:i + size] for i in range(0, len(ids), size)]
