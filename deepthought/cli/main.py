"""Command line entry point: ./dt <command>."""

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

from deepthought import PROTOCOL, __version__


def _manager():
    from deepthought.core.config import Config
    from deepthought.core.executor import RunManager
    from deepthought.core.registry import Registry

    config = Config()
    registry = Registry(config)
    return config, registry, RunManager(config, registry)


def _print_update_banner():
    from deepthought.core import selfupdate
    from deepthought.cli.reporter_plain import c

    st = selfupdate.cached_status()
    if st.get("available"):
        print(c(f"⬆  a DeepThought update is available ({st.get('behind')} commit(s)): ./dt update", "yellow"))


# ------------------------------------------------------------------ run
def cmd_run(args):
    from deepthought.cli.reporter_plain import PlainReporter, c, exit_code, junit
    from deepthought.core import history
    from deepthought.core.executor import RunError

    config, registry, manager = _manager()
    reporter = PlainReporter(verbose=args.verbose, quiet=args.quiet)
    manager.bus.on(reporter)
    options = {"sanitize": args.sanitize, "leaks": not args.no_leaks, "clean": args.clean}
    if args.timeout:
        options["timeout"] = args.timeout
    if args.jobs:
        options["jobs"] = args.jobs
    if args.no_norm:
        options["norminette"] = False
    project = Path(args.path).expanduser().resolve()
    build = {}
    if args.build_cmd:
        build["command"] = args.build_cmd
    if args.make_args:
        build["make_args"] = args.make_args
    if args.env:
        build["env"] = dict(e.split("=", 1) for e in args.env if "=" in e)
    if args.save_build:
        saved = manager.projects.set_build(str(project), {**build, "clean": args.clean})
        print(c(f"build options saved for {project.name}: {saved or '(defaults)'}", "cyan"))
    elif build:
        options["build"] = build
    saved = manager.projects.get(str(project)).get("build")
    if saved and not args.quiet:
        print(c(f"build options: {saved}  (change: --save-build, or the ⚙ Build options button in the UI)", "dim"))

    def one_run():
        try:
            if args.failed:
                runs = history.list_runs(project)
                if not runs:
                    print(c("no previous run for this project: running everything", "yellow"))
                    run = manager.start(project, args.suite or None, options, wait=True)
                else:
                    run = manager.rerun(runs[0]["id"], failed_only=True, options=options)
                    _wait(manager, run.id)
            else:
                run = manager.start(project, args.suite or None, options, wait=True)
        except RunError as e:
            print(c(f"error: {e}", "red"))
            return 2
        data = manager.get(run.id)
        reporter.summary(data)
        if args.json:
            Path(args.json).write_text(json.dumps(data, indent=2))
        if args.junit:
            Path(args.junit).write_text(junit(data))
        return exit_code(data)

    code = one_run()
    if not args.watch:
        _print_update_banner()
        return code
    from deepthought.core.watch import Watcher
    import threading

    trigger = threading.Event()
    w = Watcher(str(project), trigger.set)
    w.start()
    print(c(f"\n👀 watching {project} — save a file to re-run (Ctrl-C to quit)", "cyan"))
    try:
        while True:
            trigger.wait()
            trigger.clear()
            reporter.__init__(verbose=args.verbose, quiet=args.quiet)
            print("\x1b[2J\x1b[H" if sys.stdout.isatty() else "\n" + "=" * 60)
            one_run()
            print(c(f"\n👀 watching {project} — save a file to re-run (Ctrl-C to quit)", "cyan"))
    except KeyboardInterrupt:
        w.stop()
        return 0


def _wait(manager, run_id):
    while manager.runs[run_id].status in ("pending", "running"):
        time.sleep(0.05)


# ------------------------------------------------------------------ ui / tui
def cmd_ui(args):
    from deepthought.server.app import serve

    return serve(port=args.port, open_browser=not args.no_open, project=args.path, host=args.host)


def cmd_tui(args):
    from deepthought.cli.tui import run_tui

    return run_tui(args.path, args.suite or None)


# ------------------------------------------------------------------ suites
def cmd_suite(args):
    from deepthought.cli.reporter_plain import c
    from deepthought.core.manifest import ManifestError, load_suite
    from deepthought.core.registry import RegistryError

    config, registry, manager = _manager()
    try:
        if args.action == "list":
            items = registry.to_list()
            if not items:
                print("no suites installed")
            for s in items:
                state = c("enabled", "green") if s["enabled"] else c("disabled", "dim")
                print(f"  {c(s['uid'], 'bold'):<32} {s['name']}  v{s['version']}  "
                      f"{c('project=' + s['project'], 'cyan')}  [{s['source']}] {state}")
                for w in s["warnings"]:
                    print(c(f"      ⚠ {w}", "yellow"))
            for e in registry.errors:
                print(c(f"  ✗ {e['path']} [{e['source']}]", "red"))
                for msg in e["errors"]:
                    print(c(f"      {msg}", "red"))
        elif args.action == "info":
            s = registry.get(args.target).to_dict()
            print(json.dumps(s, indent=2))
        elif args.action == "add":
            spec = args.target
            try:
                preview = load_suite(spec) if Path(spec).is_dir() else None
            except ManifestError:
                preview = None
            if not args.yes and not Path(spec).is_dir():
                print(c("⚠  Test suites contain code that will be compiled and run on your machine.", "yellow"))
                print(c("   Only add suites from people you trust.", "yellow"))
                if input("   Continue? [y/N] ").strip().lower() not in ("y", "yes"):
                    return 1
            s = registry.add(spec, args.ref or "")
            print(c(f"✓ added {s.name} ({s.id} v{s.version}, project={s.project})", "green"))
            if args.link:
                _link(manager, args.link, s.uid)
            del preview
        elif args.action == "remove":
            s = registry.remove(args.target)
            print(c(f"✓ removed {s.uid}", "green"))
        elif args.action == "update":
            msgs = [registry.update(args.target)] if args.target else registry.update_all()
            for m in msgs or ["no git suites to update"]:
                print(m)
        elif args.action == "new":
            dest = registry.create(args.target, args.project or "libft", args.runner, args.dir)
            print(c(f"✓ created {dest}", "green"))
            if args.link:
                registry.reload()
                created = next(x for x in registry.all() if Path(x.path).resolve() == Path(dest).resolve())
                _link(manager, args.link, created.uid)
            print(f"  edit {dest / 'suite.toml'} and the files in {dest}")
            if not args.link:
                print(f"  then link it to your project: ./dt project link <your project> {Path(dest).name}")
        elif args.action == "pack":
            dest = registry.pack(args.target, args.out or ".")
            print(c(f"✓ wrote {dest}", "green"))
        elif args.action in ("enable", "disable"):
            s = registry.get(args.target)
            registry.set_enabled(s.uid, args.action == "enable")
            print(f"{s.uid}: {args.action}d")
        elif args.action == "validate":
            return validate_suite(args.target, args.project, manager)
    except (RegistryError, ManifestError) as e:
        print(c(f"error: {e}", "red"))
        return 1
    return 0


def _link(manager, project, uid):
    from deepthought.cli.reporter_plain import c

    path = str(Path(project).expanduser().resolve())
    _, _, current = manager.suites_for(path)
    manager.projects.link(path, uid, current=[s.uid for s in current])
    print(c(f"✓ linked {uid} to {Path(path).name}", "green"))


def validate_suite(path, project, manager):
    from deepthought.cli.reporter_plain import PlainReporter, c, exit_code
    from deepthought.core.manifest import ManifestError, load_suite

    try:
        s = load_suite(path)
    except ManifestError as e:
        print(c(f"✗ {e.path}", "red"))
        for msg in e.errors:
            print(c(f"   - {msg}", "red"))
        return 1
    print(c(f"✓ suite.toml is valid: {s.name} ({s.id} v{s.version}) for project '{s.project}'", "green"))
    for w in s.warnings:
        print(c(f"  ⚠ {w}", "yellow"))
    for g in s.groups:
        print(f"  · {g.name} [{g.category}] runner={g.runner} variants={len(g.variants())}")
    if not project:
        print(c("  (pass --project PATH to also compile and run it against a project)", "dim"))
        return 0
    # temporarily register it so the run can find it
    manager.registry.reload()
    if s.id not in manager.registry.suites:
        s.source, s.uid = "folder", s.id
        manager.registry.suites[s.id] = s
    reporter = PlainReporter()
    manager.bus.on(reporter)
    run = manager.start(project, [s.uid], {}, wait=True)
    data = manager.get(run.id)
    reporter.summary(data)
    return exit_code(data)


# ------------------------------------------------------------------ projects
def cmd_project(args):
    from deepthought.cli.reporter_plain import c
    from deepthought.core.registry import RegistryError

    config, registry, manager = _manager()
    store = manager.projects
    try:
        if args.action == "list":
            items = store.all()
            if not items:
                print("no project yet: ./dt project add PATH")
            for p in items:
                mode, kind, suites = manager.suites_for(p["path"])
                label = {"linked": "linked suites", "kind": "own type", "auto": "detected"}[mode]
                print(f"  {c(p['name'], 'bold'):<30} {c(kind or '?', 'cyan')}  [{label}]  {c(p['path'], 'dim')}")
                print(c(f"      suites: {', '.join(s.uid for s in suites) or 'none: link one with `dt project link`'}", "dim"))
            return 0
        if not args.path:
            print(c("error: a project path is required", "red"))
            return 2
        path = str(Path(args.path).expanduser().resolve())
        if not Path(path).is_dir():
            print(c(f"error: {path} is not a directory", "red"))
            return 2
        if args.action == "add":
            store.add(path, args.values[0] if args.values else "", manual=bool(args.values))
        elif args.action == "kind":
            if not args.values:
                print(c("usage: dt project kind PATH TYPE   (TYPE 'auto' = detect again)", "red"))
                return 2
            store.configure(path, kind="" if args.values[0] == "auto" else args.values[0])
        elif args.action == "link":
            _, _, current = manager.suites_for(path)
            for uid in args.values:
                store.link(path, registry.get(uid).uid, current=[s.uid for s in current])
                current = []
        elif args.action == "unlink":
            for uid in args.values:
                store.unlink(path, registry.get(uid).uid)
        elif args.action == "auto":
            store.configure(path, kind="", suites=[])
        mode, kind, suites = manager.suites_for(path)
        print(c(f"✓ {Path(path).name}: type {kind or '?'} ({mode}), suites: "
                f"{', '.join(s.uid for s in suites) or 'none'}", "green"))
    except RegistryError as e:
        print(c(f"error: {e}", "red"))
        return 1
    return 0


# ------------------------------------------------------------------ misc
def cmd_update(args):
    from deepthought.cli.reporter_plain import c
    from deepthought.core import selfupdate

    if args.check:
        st = selfupdate.check(fetch=True)
        if not st["is_git"]:
            print("not a git clone")
        elif st["available"]:
            print(c(f"update available: {st['behind']} commit(s) behind {st['upstream']}", "yellow"))
            for line in st.get("changes", []):
                print(f"  {line}")
        else:
            print(c("up to date", "green"))
        return 0
    ok, msg, changes = selfupdate.update()
    print(c(msg, "green" if ok else "red"))
    for line in changes:
        print(f"  {line}")
    if ok:
        config, registry, _ = _manager()
        for m in registry.update_all():
            print(f"  {m}")
    return 0 if ok else 1


def cmd_doctor(args):
    from deepthought.cli.reporter_plain import c
    from deepthought.core import paths, proc, selfupdate
    from deepthought.core.config import Config

    config = Config()
    ok = True

    def line(good, label, detail="", hint=""):
        nonlocal ok
        mark = c("✓", "green") if good is True else c("–", "yellow") if good is None else c("✗", "red")
        if good is False:
            ok = False
        print(f"  {mark} {label:<20} {c(detail, 'dim')}" + (c(f"  → {hint}", "yellow") if hint else ""))

    print(c(f"DeepThought {__version__} (protocol {PROTOCOL})", "bold"))
    line(sys.version_info >= (3, 10), "python", f"{platform.python_version()} at {sys.executable}",
         "" if sys.version_info >= (3, 10) else "Python 3.10+ is required")
    for tool, required, hint in (("cc", True, "install a C compiler"), ("make", True, ""),
                                 ("nm", True, "needed for the forbidden-functions check"),
                                 ("git", True, "needed for updates and git suites"),
                                 ("norminette", False, "python3 -m pip install --user norminette"),
                                 ("valgrind", False, ""), ("leaks", False, "")):
        found = proc.which(tool)
        line(True if found else (False if required else None), tool, found or "not found", "" if found else hint)
    cache = paths.cache_dir(config["cache_dir"])
    line(os.access(cache, os.W_OK), "cache dir", str(cache))
    line(True, "data dir", str(paths.data_dir()))
    st = selfupdate.check(fetch=False)
    if st["is_git"]:
        detail = f"{st['branch']} @ {st['head']}" + (f" (behind {st['behind']})" if st["behind"] else "")
        line(True if not st["dirty"] else None, "tester repo", detail,
             "local modifications will block `dt update`" if st["dirty"] else "")
    else:
        line(None, "tester repo", "not a git clone (self-update disabled)")
    return 0 if ok else 1


def cmd_history(args):
    from deepthought.cli.reporter_plain import c
    from deepthought.core import history

    runs = history.list_runs(Path(args.path).resolve())
    for r in runs[: args.limit]:
        score = r.get("score") or {}
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("started") or 0))
        print(f"  {r['id']}  {when}  {r['status']:<9} grade {score.get('grade', '-'):>3}"
              + (c(f"  {score.get('regressions')} regression(s)", "magenta") if score.get("regressions") else ""))
    if not runs:
        print("no runs yet")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="dt", description="DeepThought — test your 42 projects.")
    p.add_argument("--version", action="version", version=f"DeepThought {__version__}")
    sub = p.add_subparsers(dest="command")

    ui = sub.add_parser("ui", help="start the web interface (default)")
    ui.add_argument("path", nargs="?", help="project to open")
    ui.add_argument("--port", type=int, default=0)
    ui.add_argument("--host", default="127.0.0.1")
    ui.add_argument("--no-open", action="store_true", help="do not open a browser")
    ui.set_defaults(func=cmd_ui)

    run = sub.add_parser("run", help="test a project in the terminal")
    run.add_argument("path", nargs="?", default=".")
    run.add_argument("-s", "--suite", action="append", help="suite id (repeatable); default: auto-detect")
    run.add_argument("-f", "--failed", action="store_true", help="re-run only what failed last time")
    run.add_argument("-w", "--watch", action="store_true", help="re-run when files change")
    run.add_argument("-v", "--verbose", action="store_true")
    run.add_argument("-q", "--quiet", action="store_true")
    run.add_argument("--sanitize", action="store_true", help="build with AddressSanitizer + UBSan")
    run.add_argument("--no-leaks", action="store_true", help="do not fail tests on leaks")
    run.add_argument("--no-norm", action="store_true", help="skip norminette")
    run.add_argument("--clean", action="store_true", help="make fclean before building")
    run.add_argument("--make-args", metavar="ARGS", help="extra make arguments, e.g. \"bonus CFLAGS=-O2\"")
    run.add_argument("--build-cmd", metavar="CMD", help="replace the build command, e.g. \"make -C {project} re\"")
    run.add_argument("--env", metavar="K=V", action="append", help="environment variable for the build (repeatable)")
    run.add_argument("--save-build", action="store_true",
                     help="remember --build-cmd/--make-args/--env/--clean for this project (no flags: reset)")
    run.add_argument("--timeout", type=float, help="per-test timeout (s)")
    run.add_argument("-j", "--jobs", type=int)
    run.add_argument("--json", metavar="FILE", help="write the full result as JSON")
    run.add_argument("--junit", metavar="FILE", help="write a JUnit XML report")
    run.set_defaults(func=cmd_run)

    tui = sub.add_parser("tui", help="interactive terminal interface")
    tui.add_argument("path", nargs="?", default=".")
    tui.add_argument("-s", "--suite", action="append")
    tui.set_defaults(func=cmd_tui)

    s = sub.add_parser("suite", help="manage test suites")
    s.add_argument("action", choices=["list", "info", "add", "remove", "update", "new", "pack",
                                      "validate", "enable", "disable"])
    s.add_argument("target", nargs="?", help="suite id, git URL, folder, .zip or name")
    s.add_argument("--ref", help="git branch/tag/commit (add)")
    s.add_argument("--project", help="project kind (new) or project path (validate)")
    s.add_argument("--runner", default="c-unit", choices=["c-unit", "python-unit", "exec", "script"])
    s.add_argument("--dir", help="create the suite in this folder instead of ~/.deepthought (new)")
    s.add_argument("-o", "--out", help="output folder (pack)")
    s.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    s.add_argument("--link", metavar="PROJECT", help="also link the suite to this project folder (add, new)")
    s.set_defaults(func=cmd_suite)

    pr = sub.add_parser("project", help="your projects: type and linked suites")
    pr.add_argument("action", choices=["list", "add", "kind", "link", "unlink", "auto"])
    pr.add_argument("path", nargs="?", help="project folder")
    pr.add_argument("values", nargs="*", help="add: [TYPE] · kind: TYPE|auto · link/unlink: SUITE…")
    pr.set_defaults(func=cmd_project)

    up = sub.add_parser("update", help="update the tester (git pull) and git suites")
    up.add_argument("--check", action="store_true", help="only check")
    up.set_defaults(func=cmd_update)

    doc = sub.add_parser("doctor", help="check your environment")
    doc.set_defaults(func=cmd_doctor)

    hist = sub.add_parser("history", help="past runs of a project")
    hist.add_argument("path", nargs="?", default=".")
    hist.add_argument("-n", "--limit", type=int, default=20)
    hist.set_defaults(func=cmd_history)
    return p


def _auto_update(argv):
    """Pull the latest tester before running anything, then restart on it."""
    import os

    from deepthought.cli.reporter_plain import c
    from deepthought.core import selfupdate
    from deepthought.core.config import Config

    if not Config()["auto_update"]:
        return
    updated, message = selfupdate.auto_update()
    if message:
        print(c(f"⬆  DeepThought {message}", "cyan" if updated else "yellow"), file=sys.stderr)
    if updated:
        os.environ["DT_NO_UPDATE"] = "1"  # the restarted process must not loop
        sys.stdout.flush()
        from deepthought.core import paths

        os.execv(sys.executable, [sys.executable, str(paths.PKG_DIR / "__main__.py"), *argv])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--no-update" in argv:
        argv.remove("--no-update")
    elif not set(argv) & {"-h", "--help", "--version", "update"}:
        _auto_update(argv)
    parser = build_parser()
    if not argv or (argv[0] not in parser._subparsers._group_actions[0].choices and not argv[0].startswith("-")):
        argv = ["ui", *argv]
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    if args.command in ("suite",) and args.action not in ("list",) and not args.target:
        parser.error(f"suite {args.action} needs a target")
    if args.command != "ui":
        import signal

        signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # `dt run | head` exits quietly
    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        return 130
