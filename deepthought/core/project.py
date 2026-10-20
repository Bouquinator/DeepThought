"""Project detection and the list of remembered projects."""

import json
import re
import threading
import time
from pathlib import Path

from deepthought.core import paths

_NAME_RE = re.compile(r"^\s*NAME\s*[:+?]?=\s*(\S+)", re.M)


def makefile_name(project):
    mk = Path(project) / "Makefile"
    if not mk.exists():
        return ""
    try:
        m = _NAME_RE.search(mk.read_text(errors="replace"))
    except OSError:
        return ""
    return m.group(1) if m else ""


def _glob_any(project, pattern):
    return any(Path(project).glob(pattern))


def match_score(suite, project):
    """0 = not for this project; higher = better match."""
    detect = suite.detect
    if not detect:
        return 0
    project = Path(project)
    score = 0
    # exact file names are stronger evidence than glob patterns
    weight = lambda pattern: 1 if any(c in pattern for c in "*?[") else 2  # noqa: E731
    for f in detect.get("files", []):
        if not _glob_any(project, f):
            return 0
        score += weight(f)
    anyf = detect.get("any_files", [])
    if anyf:
        hits = [f for f in anyf if _glob_any(project, f)]
        if not hits:
            return 0
        score += max(weight(f) for f in hits)
    want = detect.get("makefile_name")
    if want:
        if makefile_name(project) != want:
            return 0
        score += 3
    return score


def detect(project, suites):
    """Return (kind, [matching suites best first])."""
    scored = [(match_score(s, project), s) for s in suites]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return "", []
    kind = scored[0][1].project
    return kind, [s for _, s in scored if s.project == kind]


class ProjectStore:
    """~/.deepthought/projects.json: projects the user added, with their last score."""

    def __init__(self):
        self.path = paths.data_dir() / "projects.json"
        self._lock = threading.Lock()

    def _load(self):
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return []

    def _save(self, items):
        self.path.write_text(json.dumps(items, indent=2))

    def all(self):
        with self._lock:
            return [p for p in self._load() if Path(p["path"]).is_dir()]

    def add(self, path, kind="", manual=False):
        """Remember a project. A manual kind (chosen by the user) is never
        overwritten by detection."""
        path = str(Path(path).expanduser().resolve())
        with self._lock:
            items = self._load()
            for p in items:
                if p["path"] == path:
                    if kind and (manual or not p.get("kind_manual")):
                        p["kind"] = kind
                        p["kind_manual"] = bool(manual or p.get("kind_manual"))
                    self._save(items)
                    return p
            entry = {"path": path, "name": Path(path).name, "kind": kind, "kind_manual": bool(manual and kind),
                     "added": time.time(), "last_run": None, "last_grade": None}
            items.append(entry)
            self._save(items)
            return entry

    def configure(self, path, kind=None, suites=None):
        """Set the project's own type and/or the suites linked to it.

        kind:   a project type (any name, e.g. "pipex" or "my_project");
                "" goes back to automatic detection; None keeps it.
        suites: a list of suite uids that will run for this project
                (instead of the detected ones); [] goes back to automatic;
                None keeps it.
        """
        entry = self.add(path)
        with self._lock:
            items = self._load()
            for p in items:
                if p["path"] != entry["path"]:
                    continue
                if kind is not None:
                    p["kind"] = kind.strip()
                    p["kind_manual"] = bool(kind.strip())
                if suites is not None:
                    if suites:
                        p["suites"] = list(dict.fromkeys(suites))
                    else:
                        p.pop("suites", None)
                entry = p
            self._save(items)
        return entry

    def link(self, path, uid, current=None):
        """Add a suite to the project. When the project still runs its detected
        suites, they stay linked too (`current`)."""
        entry = self.get(path) or self.add(path)
        suites = list(entry.get("suites") or current or [])
        if uid not in suites:
            suites.append(uid)
        return self.configure(path, suites=suites)

    def unlink(self, path, uid):
        entry = self.get(path)
        suites = [u for u in (entry.get("suites") or []) if u != uid]
        return self.configure(path, suites=suites)

    def get(self, path):
        path = str(Path(path).expanduser().resolve())
        with self._lock:
            return next((p for p in self._load() if p["path"] == path), {})

    def set_build(self, path, build):
        """Save build options: command, make_args, env (dict), clean (bool)."""
        clean = {}
        for key in ("command", "make_args"):
            if str(build.get(key) or "").strip():
                clean[key] = str(build[key]).strip()
        env = build.get("env") or {}
        if isinstance(env, str):
            env = dict(l.split("=", 1) for l in env.splitlines() if "=" in l)
        env = {k.strip(): v.strip() for k, v in env.items() if k.strip()}
        if env:
            clean["env"] = env
        if build.get("clean"):
            clean["clean"] = True
        entry = self.add(path)
        with self._lock:
            items = self._load()
            for p in items:
                if p["path"] == entry["path"]:
                    if clean:
                        p["build"] = clean
                    else:
                        p.pop("build", None)
            self._save(items)
        return clean

    def remove(self, path):
        with self._lock:
            items = [p for p in self._load() if p["path"] != path]
            self._save(items)

    def record_run(self, path, run_id, grade):
        with self._lock:
            items = self._load()
            for p in items:
                if p["path"] == path:
                    p["last_run"] = run_id
                    p["last_grade"] = grade
                    p["last_time"] = time.time()
            self._save(items)
