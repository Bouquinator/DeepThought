"""Building the project, and the classic Makefile checks.

What runs, in order of priority:
  1. the project's own build override (UI "Build options", `dt run --build-cmd`)
  2. the suite's [build] command (usually `make -C {project}`)
  3. for Python suites without a command: an automatic syntax check
Extra make arguments (targets like `bonus`, variables like `CFLAGS=-O2`) and
environment variables from the project's build options are applied to every
make invocation of the run.
"""

import ast
import os
import re
import shlex
from pathlib import Path

from deepthought.core import proc
from deepthought.core.template import as_argv, expand, quote_cmd

SANITIZE_CFLAGS = "-Wall -Wextra -Werror -g -fsanitize=address,undefined -fno-omit-frame-pointer"
PY_SKIP_DIRS = {"venv", ".venv", "env", "site-packages", "__pycache__", "node_modules", ".git"}


def build_options(ctx):
    return ctx.options.get("build") or {}


def is_make(argv):
    return bool(argv) and Path(argv[0]).name in ("make", "gmake")


def make_args(ctx, suite, variables_only=False):
    """Extra arguments for make: the project's make_args (+ sanitizer CFLAGS)."""
    raw = build_options(ctx).get("make_args") or ""
    try:
        args = [expand(a, ctx.template_vars(suite)) for a in shlex.split(raw)]
    except ValueError:
        args = raw.split()
    if variables_only:
        args = [a for a in args if "=" in a]
    if ctx.options.get("sanitize"):
        args.append(f"CFLAGS={SANITIZE_CFLAGS}")
    return args


def build_env(ctx):
    env = build_options(ctx).get("env") or {}
    if isinstance(env, str):
        env = dict(line.split("=", 1) for line in env.splitlines() if "=" in line)
    return {k.strip(): str(v) for k, v in env.items() if k.strip()}


def build_argv(ctx, suite):
    cmd = build_options(ctx).get("command") or suite.build.get("command")
    if not cmd:
        return None
    argv = as_argv(cmd, ctx.template_vars(suite))
    if is_make(argv):
        argv += make_args(ctx, suite)
    return argv


def wants_python_check(suite):
    mode = suite.build.get("syntax_check")
    if mode is not None:
        return mode == "python"
    return any(g.runner == "python-unit" for g in suite.groups)


def build(ctx, suite, stage):
    """Run the build. Returns True on success."""
    argv = build_argv(ctx, suite)
    if argv is None:
        if wants_python_check(suite):
            return python_syntax(ctx, suite, stage)
        stage.status = "skip"
        stage.message = "no build step (tests compile the sources directly)"
        return True
    if ctx.options.get("clean"):
        clean = as_argv(suite.build.get("clean", "make fclean"), ctx.template_vars(suite))
        if is_make(clean):
            clean += make_args(ctx, suite, variables_only=True)
        res = ctx.run_once(clean, cwd=str(ctx.ws.src))
        stage.log = f"$ {quote_cmd(clean)}\n{res.text()}\n"
    res = ctx.run_once(argv, cwd=str(ctx.ws.src), timeout=suite.build.get("timeout", 300))
    stage.ms = res.ms
    env = build_env(ctx)
    envs = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
    stage.log += f"$ {envs + ' ' if envs else ''}{quote_cmd(argv)}\n{res.text()}"
    if not res.ok:
        stage.status = "fail"
        stage.message = "timed out" if res.timed_out else f"build failed (exit {res.code})"
        return False
    missing = [a for a in suite.build.get("artifacts", []) if not (ctx.ws.src / ctx.x(a, suite)).exists()]
    if missing:
        stage.status = "fail"
        stage.message = f"build succeeded but did not produce: {', '.join(missing)}"
        return False
    stage.status = "pass"
    warnings = [l for l in res.text().splitlines() if "warning:" in l]
    stage.message = f"built in {res.ms} ms" + (f", {len(warnings)} warning(s)" if warnings else "")
    return True


def python_syntax(ctx, suite, stage):
    """Python 'build': every .py file of the project must parse (no bytecode is written)."""
    stage.name = "Syntax check"
    root = ctx.ws.src
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in PY_SKIP_DIRS]
        files += [Path(dirpath) / f for f in sorted(filenames) if f.endswith(".py")]
    errors = []
    for f in files:
        rel = str(f.relative_to(root))
        try:
            ast.parse(f.read_bytes(), filename=rel)
        except SyntaxError as e:
            errors.append({"file": rel, "line": e.lineno or 0, "col": e.offset or 0,
                           "code": type(e).__name__, "msg": e.msg})
        except (ValueError, OSError) as e:
            errors.append({"file": rel, "line": 0, "col": 0, "code": "Error", "msg": str(e)})
    stage.items = [{"label": f"{e['file']}:{e['line']}: {e['msg']}", "ok": False} for e in errors]
    stage.log = "\n".join(f"{e['file']}:{e['line']}:{e['col']}: {e['code']}: {e['msg']}" for e in errors) \
        or f"{len(files)} Python file(s) parsed"
    if errors:
        stage.status = "fail"
        stage.message = f"{len(errors)} file(s) with a syntax error: {errors[0]['file']}:{errors[0]['line']}"
        return False
    if not files:
        stage.status = "warn"
        stage.message = "no Python file found in the project"
        return True
    stage.status = "pass"
    stage.message = f"{len(files)} Python file(s) parse correctly"
    return True


def _targets(text):
    text = re.sub(r"\\\n", " ", text)
    targets = set()
    for line in text.splitlines():
        if line.startswith(("\t", "#")) or ":" not in line or "=" in line.split(":")[0]:
            continue
        head = line.split(":")[0]
        targets.update(head.split())
    return targets


def rules(ctx, suite, stage):
    mk = ctx.ws.src / "Makefile"
    if not mk.exists():
        stage.status = "fail"
        stage.message = "no Makefile"
        return
    text = mk.read_text(errors="replace")
    targets = _targets(text)
    required = suite.build.get("rules", ["all", "clean", "fclean", "re", "$(NAME)"])
    missing = [r for r in required if r not in targets and not (r == "$(NAME)" and "${NAME}" in targets)]
    stage.items = [{"label": r, "ok": r not in missing} for r in required]
    if missing:
        stage.status = "fail"
        stage.message = f"missing rule(s): {', '.join(missing)}"
    else:
        stage.status = "pass"
        stage.message = "all required rules are present"
    if "-Wall" not in text or "-Wextra" not in text or "-Werror" not in text:
        stage.items.append({"label": "-Wall -Wextra -Werror", "ok": False})
        if stage.status == "pass":
            stage.status = "warn"
            stage.message = "the Makefile does not seem to use -Wall -Wextra -Werror"


def relink(ctx, suite, stage):
    argv = build_argv(ctx, suite)
    if argv is None:
        stage.status = "skip"
        return
    artifacts = [ctx.ws.src / ctx.x(a, suite) for a in suite.build.get("artifacts", [])]
    before = {a: a.stat().st_mtime_ns for a in artifacts if a.exists()}
    env = build_env(ctx)
    with ctx.slots:
        res = proc.run(argv, cwd=str(ctx.ws.src), timeout=120, tracker=ctx.tracker, env=env)
    stage.ms = res.ms
    stage.log = f"$ {quote_cmd(argv)}   (second time)\n{res.text()}"
    changed = [a.name for a in artifacts if a.exists() and before.get(a) != a.stat().st_mtime_ns]
    compiled = [l for l in res.text().splitlines()
                if re.search(r"\b(cc|gcc|clang|ar)\s", l) and not l.startswith("make")]
    if changed or compiled:
        stage.status = "fail"
        stage.message = "running make twice rebuilds: " + (", ".join(changed) or "objects recompiled")
    else:
        stage.status = "pass"
        stage.message = "second make did nothing"
    # bonus relink: a very common evaluation point
    mk = ctx.ws.src / "Makefile"
    if mk.exists() and "bonus" in _targets(mk.read_text(errors="replace")):
        b1 = proc.run(argv + ["bonus"], cwd=str(ctx.ws.src), timeout=120, tracker=ctx.tracker, env=env)
        before = {a: a.stat().st_mtime_ns for a in artifacts if a.exists()}
        b2 = proc.run(argv + ["bonus"], cwd=str(ctx.ws.src), timeout=120, tracker=ctx.tracker, env=env)
        changed = [a.name for a in artifacts if a.exists() and before.get(a) != a.stat().st_mtime_ns]
        stage.log += f"\n$ make bonus   (twice)\n{b2.text()}"
        stage.items = [{"label": "make", "ok": stage.status == "pass"},
                       {"label": "make bonus", "ok": b1.ok and not changed}]
        if changed and stage.status == "pass":
            stage.status = "warn"
            stage.message = "`make bonus` relinks every time"
