"""JSON API routes. Each handler gets (h, match, query) and returns JSON-able data."""

import json
import re
import shutil
import subprocess
from pathlib import Path

from deepthought import PROTOCOL, __version__
from deepthought.core import history, paths, selfupdate
from deepthought.core.executor import RunError
from deepthought.core.manifest import ManifestError
from deepthought.core.project import detect
from deepthought.core.registry import RegistryError
from deepthought.core.sources import archive


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


ROUTES = []


def _route(method, pattern):
    def deco(fn):
        ROUTES.append((method, re.compile(f"^{pattern}$"), fn))
        return fn
    return deco


def route(h, method, path, query):
    """Dispatch an /api request (called by server.app.Handler)."""
    for m, rx, fn in ROUTES:
        if m == method:
            match = rx.match(path)
            if match:
                try:
                    return fn(h, match, query)
                except (RegistryError, ManifestError, RunError, KeyError, ValueError) as e:
                    raise ApiError(str(e).strip("'\""))
    raise ApiError("not found", 404)


def _python_check(suite):
    from deepthought.checks.make import wants_python_check
    return wants_python_check(suite)


def _project_info(app, entry):
    p = entry["path"]
    kind, suites = detect(p, app.registry.enabled())
    entry = dict(entry)
    entry["kind"] = kind or entry.get("kind", "")
    entry["suites"] = [s.uid for s in suites]
    entry["watching"] = p in app.manager.watchers
    defaults = [s.build.get("command") for s in suites if s.build.get("command")]
    python = any(not s.build.get("command") and _python_check(s) for s in suites)
    entry["default_build"] = defaults[0] if defaults else ("python syntax check" if python else "")
    entry.setdefault("build", {})
    active = app.manager.active_run(p)
    entry["active_run"] = active.id if active else None
    return entry


# ------------------------------------------------------------------ state
@_route("GET", "/api/state")
def state(h, m, q):
    app = h.app
    return {
        "version": __version__,
        "protocol": PROTOCOL,
        "config": app.config.to_dict(),
        "projects": [_project_info(app, p) for p in app.manager.projects.all()],
        "suites": app.registry.to_list(),
        "suite_errors": app.registry.errors,
        "update": app.update_status,
        "runs": [r.summary() for r in list(app.manager.runs.values())[-20:]],
        "home": str(Path.home()),
        "repo": str(paths.REPO_ROOT),
    }


@_route("POST", "/api/config")
def set_config(h, m, q):
    h.app.config.update(h.read_json())
    return h.app.config.to_dict()


# ------------------------------------------------------------------ projects
@_route("POST", "/api/projects")
def add_project(h, m, q):
    path = Path(h.read_json().get("path", "")).expanduser()
    if not path.is_dir():
        raise ApiError(f"{path} is not a directory")
    kind, suites = detect(path, h.app.registry.enabled())
    entry = h.app.manager.projects.add(str(path), kind)
    return _project_info(h.app, entry)


@_route("DELETE", "/api/projects")
def remove_project(h, m, q):
    h.app.manager.projects.remove(q.get("path", ""))
    h.app.manager.watch(q.get("path", ""), False) if q.get("path") in h.app.manager.watchers else None
    return {"ok": True}


@_route("POST", "/api/projects/build")
def project_build(h, m, q):
    """Save a project's build options: {path, build: {command, make_args, env, clean}}."""
    body = h.read_json()
    path = Path(body.get("path", "")).expanduser()
    if not path.is_dir():
        raise ApiError(f"{path} is not a directory")
    saved = h.app.manager.projects.set_build(str(path), body.get("build") or {})
    return {"path": str(path.resolve()), "build": saved}


@_route("GET", "/api/projects/detect")
def detect_project(h, m, q):
    path = Path(q.get("path", "")).expanduser()
    if not path.is_dir():
        raise ApiError("not a directory")
    kind, suites = detect(path, h.app.registry.enabled())
    return {"path": str(path.resolve()), "kind": kind, "suites": [s.uid for s in suites]}


@_route("GET", "/api/history")
def project_history(h, m, q):
    return history.list_runs(q.get("project", ""))


@_route("POST", "/api/watch")
def watch(h, m, q):
    body = h.read_json()
    enabled = h.app.manager.watch(body["project"], bool(body.get("enabled")), body.get("options") or {},
                                  body.get("suites") or None)
    return {"project": body["project"], "enabled": enabled}


# ------------------------------------------------------------------ runs
@_route("POST", "/api/runs")
def start_run(h, m, q):
    body = h.read_json()
    run = h.app.manager.start(body["project"], body.get("suites") or None, body.get("options") or {})
    return run.summary()


@_route("GET", r"/api/runs/(?P<id>[\w.-]+)")
def get_run(h, m, q):
    data = h.app.manager.get(m["id"])
    if not data:
        raise ApiError("unknown run", 404)
    return data


@_route("POST", r"/api/runs/(?P<id>[\w.-]+)/cancel")
def cancel_run(h, m, q):
    return {"cancelled": h.app.manager.cancel(m["id"])}


@_route("POST", r"/api/runs/(?P<id>[\w.-]+)/rerun")
def rerun(h, m, q):
    body = h.read_json()
    run = h.app.manager.rerun(m["id"], failed_only=body.get("failed_only", True),
                              options=body.get("options") or None, tids=body.get("tids") or None)
    return run.summary()


# ------------------------------------------------------------------ suites
@_route("GET", "/api/suites")
def list_suites(h, m, q):
    return {"suites": h.app.registry.to_list(), "errors": h.app.registry.errors}


@_route("POST", "/api/suites/add")
def add_suite(h, m, q):
    body = h.read_json()
    s = h.app.registry.add(body["spec"].strip(), body.get("ref", ""))
    return s.to_dict()


@_route("POST", "/api/suites/upload")
def upload_suite(h, m, q):
    data = h.read_body()
    s = h.app.registry.add_zip(data, q.get("filename", "suite.zip"), replace=q.get("replace") == "1")
    return s.to_dict()


@_route("POST", "/api/suites/inspect")
def inspect_suite(h, m, q):
    """Preview a local folder before adding it (trust prompt)."""
    body = h.read_json()
    p = Path(body.get("spec", "")).expanduser()
    if p.is_dir():
        root = archive.find_suite_root(p)
        return h.app.registry.inspect(root).to_dict()
    return {"spec": body.get("spec"), "remote": True}


@_route("POST", "/api/suites/new")
def new_suite(h, m, q):
    body = h.read_json()
    dest = h.app.registry.create(body["name"], body.get("project", "libft"), body.get("runner", "c-unit"),
                                 body.get("dir") or None)
    return {"path": str(dest)}


@_route("POST", r"/api/suites/(?P<uid>[^/]+)/update")
def update_suite(h, m, q):
    return {"message": h.app.registry.update(m["uid"])}


@_route("POST", r"/api/suites/(?P<uid>[^/]+)/enable")
def enable_suite(h, m, q):
    h.app.registry.set_enabled(m["uid"], bool(h.read_json().get("enabled", True)))
    return {"ok": True}


@_route("DELETE", r"/api/suites/(?P<uid>[^/]+)")
def remove_suite(h, m, q):
    s = h.app.registry.remove(m["uid"])
    return {"removed": s.uid}


@_route("GET", r"/api/suites/(?P<uid>[^/]+)/pack")
def pack_suite(h, m, q):
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        dest = h.app.registry.pack(m["uid"], tmp)
        data = Path(dest).read_bytes()
        h.send_bytes(data, "application/zip",
                     headers={"Content-Disposition": f'attachment; filename="{Path(dest).name}"'})
    return None


@_route("POST", "/api/suites/reload")
def reload_suites(h, m, q):
    h.app.registry.reload()
    return {"suites": h.app.registry.to_list(), "errors": h.app.registry.errors}


@_route("GET", "/api/index")
def community_index(h, m, q):
    try:
        data = json.loads(paths.INDEX_FILE.read_text())
    except (OSError, ValueError):
        data = {"suites": []}
    installed = {s.origin for s in h.app.registry.all()}
    for s in data.get("suites", []):
        s["installed"] = s.get("url") in installed
    return data


# ------------------------------------------------------------------ self update
@_route("POST", "/api/self/check")
def check_update(h, m, q):
    h.app.update_status = selfupdate.check(fetch=True)
    return h.app.update_status


@_route("POST", "/api/self/update")
def do_update(h, m, q):
    ok, msg, changes = selfupdate.update()
    if ok:
        h.app.registry.update_all()
        h.app.registry.reload()
    h.app.update_status = selfupdate.cached_status()
    return {"ok": ok, "message": msg, "changes": changes, "status": h.app.update_status}


# ------------------------------------------------------------------ filesystem
@_route("GET", "/api/fs/browse")
def browse(h, m, q):
    path = Path(q.get("path") or Path.home()).expanduser()
    try:
        path = path.resolve()
        entries = sorted(path.iterdir(), key=lambda p: p.name.lower())
    except (OSError, PermissionError) as e:
        raise ApiError(f"cannot open {path}: {e}")
    dirs = []
    for p in entries:
        if p.name.startswith(".") and q.get("hidden") != "1":
            continue
        try:
            if p.is_dir():
                dirs.append({"name": p.name, "path": str(p),
                             "has_makefile": (p / "Makefile").exists(),
                             "has_suite": (p / "suite.toml").exists()})
        except OSError:
            continue
    files = [p.name for p in entries if p.is_file() and not p.name.startswith(".")][:200]
    kind, _ = detect(path, h.app.registry.enabled()) if files else ("", [])
    return {"path": str(path), "parent": str(path.parent) if path.parent != path else None,
            "dirs": dirs, "files": files, "kind": kind, "home": str(Path.home())}


@_route("POST", "/api/open")
def open_in_editor(h, m, q):
    """Open file:line in the user's editor (VS Code if available)."""
    body = h.read_json()
    path = Path(body.get("path", ""))
    if not path.is_file():
        raise ApiError("file not found")
    line = int(body.get("line") or 1)
    code = shutil.which("code")
    if code:
        subprocess.Popen([code, "-g", f"{path}:{line}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif shutil.which("open"):
        subprocess.Popen(["open", str(path)])
    elif shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", str(path)])
    else:
        raise ApiError("no editor found")
    return {"ok": True}
