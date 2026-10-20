"""exec: declarative command cases — works for any language.

The group's `cases` file is TOML:

  [[case]]
  name = "three sorted numbers"
  desc = "Already sorted input prints nothing"
  cmd = "{project}/push_swap 1 2 3"     # string (split like a shell) or list
  shell = false                         # true: run through /bin/sh -c
  stdin = "..."                         # or stdin_file = "fixtures/in.txt"
  timeout = 3
  reference = "printf 'x'"              # optional: compare against this command
  compare = ["stdout", "exit"]          # what to compare with the reference
  check = "{suite}/check.sh"            # optional: gets stdout on stdin, exit 0 = ok
  [case.expect]
  stdout = ""                           # exact match
  stdout_contains = ["..."]
  stdout_regex = "^ok$"
  stderr = "", stderr_contains = [...], stderr_regex = "..."
  exit = 0                              # or "nonzero"
"""

import re
from pathlib import Path

from deepthought.core import proc, toml
from deepthought.core.template import as_argv, expand, quote_cmd
from deepthought.runners.base import Runner


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _latin(b):
    return b.decode("latin-1")


class ExecRunner(Runner):
    def _cases(self):
        path = Path(self.suite.path) / self.x(self.group.cases)
        data = toml.load_file(path)
        cases = data.get("case", [])
        out, seen = {}, set()
        for i, c in enumerate(cases):
            name = c.get("name") or f"case {i + 1}"
            cid = c.get("id") or _slug(name) or f"case-{i + 1}"
            while cid in seen:
                cid += "_"
            seen.add(cid)
            out[cid] = c
        return out, path

    def prepare(self):
        try:
            self._loaded, self._path = self._cases()
        except (OSError, toml.TOMLDecodeError) as e:
            self.build_log = f"cannot read cases file: {e}"
            return False
        self.build_cmd = f"(cases from {self._path})"
        return True

    def discover(self):
        cases, path = self._cases()
        lines = path.read_text().splitlines()
        out = []
        for cid, c in cases.items():
            name = c.get("name", cid)
            line = next((i + 1 for i, l in enumerate(lines) if f'"{name}"' in l), 0)
            out.append({"t": "discover", "id": cid, "name": name, "desc": c.get("desc", ""),
                        "file": str(path), "line": line})
        return out

    def _argv(self, cmd, shell):
        if shell or (isinstance(cmd, str) and cmd.startswith("sh ")):
            return [expand(cmd, self.vars)], True
        return as_argv(cmd, self.vars), False

    def _stdin(self, c):
        if "stdin_file" in c:
            p = Path(self.suite.path) / self.x(c["stdin_file"])
            return p.read_bytes()
        if "stdin" in c:
            return self.x(c["stdin"]).encode()
        return None

    def run_case(self, cid, c, on_event):
        on_event({"t": "start", "id": cid})
        timeout = float(c.get("timeout", self.timeout))
        shell = bool(c.get("shell", False))
        argv, use_shell = self._argv(c["cmd"], shell)
        stdin = self._stdin(c)
        shown = (argv[0] if use_shell else quote_cmd(argv)).replace(str(self.ctx.ws.src), "<project>")
        if stdin:
            preview = stdin[:200].decode("utf-8", "replace")
            shown += f"   with stdin: {preview!r}" + ("…" if len(stdin) > 200 else "")
        on_event({"t": "input", "id": cid, "value": c.get("input") or shown})
        env = self.env()
        env.update({k: str(self.x(v)) for k, v in c.get("env", {}).items()})
        with self.ctx.slots:
            res = proc.run(argv[0] if use_shell else argv, cwd=str(self.outdir), env=env,
                           timeout=timeout, stdin=stdin, tracker=self.ctx.tracker, shell=use_shell)
        fails = []

        def check(ok, msg, expected, actual):
            if not ok:
                fails.append((msg, expected, actual))

        exp = dict(c.get("expect", {}))
        if "reference" in c:
            rargv, rshell = self._argv(c["reference"], c.get("shell", False))
            ref = proc.run(rargv[0] if rshell else rargv, cwd=str(self.outdir), env=env,
                           timeout=timeout, stdin=stdin, tracker=self.ctx.tracker, shell=rshell)
            for field in c.get("compare", ["stdout", "exit"]):
                if field == "stdout":
                    check(res.stdout == ref.stdout, "stdout (vs reference)", _latin(ref.stdout), _latin(res.stdout))
                elif field == "stderr":
                    check(res.stderr == ref.stderr, "stderr (vs reference)", _latin(ref.stderr), _latin(res.stderr))
                elif field == "exit":
                    check(res.code == ref.code, "exit code (vs reference)", str(ref.code), str(res.code))
        for stream in ("stdout", "stderr"):
            data = _latin(getattr(res, stream))
            if stream in exp:
                want = self.x(exp[stream])
                check(data == want, stream, want, data)
            contains = exp.get(f"{stream}_contains", [])
            for needle in [contains] if isinstance(contains, str) else contains:
                check(self.x(needle) in data, f"{stream} contains", needle, data)
            if f"{stream}_regex" in exp:
                rx = exp[f"{stream}_regex"]
                check(re.search(rx, data, re.M) is not None, f"{stream} matches /{rx}/", rx, data)
        if "exit" in exp and not res.timed_out and res.code >= 0:
            want = exp["exit"]
            if want == "nonzero":
                check(res.code != 0, "exit code", "non-zero", str(res.code))
            else:
                check(res.code == int(want), "exit code", str(want), str(res.code))
        if "check" in c and not res.timed_out:
            cargv, cshell = self._argv(c["check"], c.get("shell", False))
            chk = proc.run(cargv[0] if cshell else cargv, cwd=str(self.outdir), env=env,
                           timeout=timeout, stdin=res.stdout, tracker=self.ctx.tracker, shell=cshell)
            check(chk.ok, f"checker: {expand(c['check'], self.vars)}", "exit 0", f"exit {chk.code}: {chk.text()[:500]}")

        for msg, e, a in fails:
            on_event({"t": "assert", "id": cid, "ok": False, "msg": msg, "expected": e, "actual": a,
                      "input": c.get("input") or shown,
                      "cmp": "text" if msg.startswith(("stdout", "stderr")) else ""})
        end = {"t": "end", "id": cid, "ms": res.ms, "exit": res.code,
               "output": _latin(res.stdout[:2048] + res.stderr[:2048])}
        if res.timed_out:
            end.update(status="timeout", reason=f"did not finish within {timeout}s")
        elif res.signal:
            import signal as _signal
            try:
                name = _signal.Signals(res.signal).name
            except ValueError:
                name = f"signal {res.signal}"
            end.update(status="crash", signal=name, reason=f"the program was killed by {name}")
        else:
            end["status"] = "fail" if fails else "pass"
        on_event(end)

    def run(self, ids, on_event):
        cases, _ = self._cases()
        for cid in ids:
            if self.ctx.tracker.cancelled:
                break
            if cid in cases:
                self.run_case(cid, cases[cid], on_event)

    def repro(self, test_id):
        try:
            c = self._cases()[0][test_id]
        except (KeyError, OSError):
            return ""
        argv, shell = self._argv(c["cmd"], c.get("shell", False))
        cmd = argv[0] if shell else quote_cmd(argv)
        if "stdin_file" in c:
            cmd += f" < {Path(self.suite.path) / self.x(c['stdin_file'])}"
        elif "stdin" in c:
            cmd = f"printf %s {quote_cmd([self.x(c['stdin'])])} | {cmd}"
        return f"cd {self.outdir} && {cmd}"
