"""Installed suites, from every source.

Sources:
  builtin  suites/ in the tester repo (updated with the tester itself)
  local    ~/.deepthought/suites/local/<id>  (created by `dt suite new`)
  folder   any folder on disk, linked (not copied): edit and rerun in place
  git      cloned into ~/.deepthought/suites/git/<id>, updatable
  zip      extracted into ~/.deepthought/suites/zip/<id>

Everything except builtin/local is recorded in ~/.deepthought/suites.lock.json.
"""

import json
import re
import shutil
import tempfile
import threading
import time
from pathlib import Path

from deepthought.core import paths
from deepthought.core.manifest import ManifestError, load_suite
from deepthought.core.sources import archive, git


class RegistryError(Exception):
    pass


class Registry:
    def __init__(self, config=None):
        self.config = config
        self.lock_path = paths.data_dir() / "suites.lock.json"
        self.root = paths.user_suites_dir()
        self._lock = threading.RLock()
        self.suites = {}
        self.errors = []
        self.reload()

    # ------------------------------------------------------------ lockfile
    def _read_lock(self):
        try:
            return json.loads(self.lock_path.read_text())
        except (OSError, ValueError):
            return []

    def _write_lock(self, entries):
        self.lock_path.write_text(json.dumps(entries, indent=2))

    # ------------------------------------------------------------ loading
    def reload(self):
        with self._lock:
            found, errors = [], []

            def try_load(path, source, origin="", entry=None):
                try:
                    s = load_suite(path)
                except ManifestError as e:
                    errors.append({"path": str(e.path), "source": source, "errors": e.errors})
                    return
                s.source = source
                s.origin = origin or str(path)
                if entry:
                    s.origin = entry.get("origin", s.origin)
                found.append(s)

            if paths.BUILTIN_SUITES.is_dir():
                for d in sorted(paths.BUILTIN_SUITES.iterdir()):
                    if (d / "suite.toml").exists():
                        try_load(d, "builtin")
            for d in sorted((self.root / "local").iterdir()):
                if (d / "suite.toml").exists():
                    try_load(d, "local")
            for entry in self._read_lock():
                p = Path(entry["path"])
                if not (p / "suite.toml").exists():
                    errors.append({"path": str(p), "source": entry["source"],
                                   "errors": ["suite folder is missing (moved or deleted?)"]})
                    continue
                try_load(p, entry["source"], entry=entry)

            # unique ids: the first one keeps its id, duplicates get @source
            suites, seen = {}, set()
            for s in found:
                uid = s.id
                if uid in seen:
                    uid = f"{s.id}@{s.source}"
                    n = 2
                    while uid in seen:
                        uid, n = f"{s.id}@{s.source}{n}", n + 1
                seen.add(uid)
                s.uid = uid
                suites[uid] = s
            self.suites = suites
            self.errors = errors

    def all(self):
        return list(self.suites.values())

    def enabled(self):
        disabled = set(self.config["disabled_suites"]) if self.config else set()
        return [s for s in self.suites.values() if s.uid not in disabled and s.compatible]

    def get(self, uid):
        s = self.suites.get(uid)
        if not s:
            matches = [x for x in self.suites.values() if x.id == uid]
            if len(matches) == 1:
                return matches[0]
            raise RegistryError(f"unknown suite '{uid}'")
        return s

    def set_enabled(self, uid, enabled):
        if not self.config:
            return
        disabled = [x for x in self.config["disabled_suites"] if x != uid]
        if not enabled:
            disabled.append(uid)
        self.config.update({"disabled_suites": disabled})

    def to_list(self):
        disabled = set(self.config["disabled_suites"]) if self.config else set()
        out = []
        for s in self.suites.values():
            d = s.to_dict()
            d["enabled"] = s.uid not in disabled
            out.append(d)
        return out

    # ------------------------------------------------------------ adding
    def _record(self, suite, source, origin, path, **extra):
        entries = [e for e in self._read_lock() if Path(e["path"]) != Path(path)]
        entries.append({"id": suite.id, "source": source, "origin": origin, "path": str(path),
                        "version": suite.version, "installed": time.time(), **extra})
        self._write_lock(entries)

    @staticmethod
    def _slug(text):
        return re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-") or "suite"

    def _registered(self, path):
        path = Path(path).resolve()
        for s in self.suites.values():
            if Path(s.path).resolve() == path:
                return s
        raise RegistryError(f"the suite at {path} could not be loaded")

    def inspect(self, path):
        """Load a suite without installing it (used for the trust prompt)."""
        return load_suite(path)

    def add_folder(self, path):
        path = Path(path).expanduser().resolve()
        try:
            suite = load_suite(path)
        except ManifestError as e:
            raise RegistryError(str(e))
        with self._lock:
            self._record(suite, "folder", str(path), path)
            self.reload()
        return self._registered(path)

    def add_git(self, url, ref=""):
        name = self._slug(url.rstrip("/").split("/")[-1].removesuffix(".git"))
        dest = self.root / "git" / name
        if dest.exists():
            raise RegistryError(f"a git suite named '{name}' is already installed: use update")
        tmp = Path(tempfile.mkdtemp(prefix="dt-git-", dir=self.root / "git"))
        try:
            git.clone(url, tmp / "repo", ref)
            # the suite may live in a sub-folder of the repo
            suite_root = archive.find_suite_root(tmp / "repo")
            if suite_root != tmp / "repo":
                raise RegistryError("suite.toml must be at the root of the repository")
            suite = load_suite(suite_root)
            shutil.move(str(tmp / "repo"), dest)
        except (git.GitError, archive.ArchiveError, ManifestError) as e:
            raise RegistryError(str(e))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        with self._lock:
            self._record(suite, "git", url, dest, ref=ref, sha=git.head(dest))
            self.reload()
        return self._registered(dest)

    def add_zip(self, data_or_path, filename="suite.zip", replace=False):
        try:
            tmp = archive.extract(data_or_path, self.root / "zip")
        except archive.ArchiveError as e:
            raise RegistryError(str(e))
        try:
            suite_root = archive.find_suite_root(tmp)
            suite = load_suite(suite_root)
            dest = self.root / "zip" / self._slug(suite.id)
            if dest.exists():
                if not replace:
                    raise RegistryError(f"suite '{suite.id}' is already installed from a zip "
                                        "(re-import with replace to overwrite)")
                shutil.rmtree(dest)
            shutil.move(str(suite_root), dest)
        except (archive.ArchiveError, ManifestError) as e:
            raise RegistryError(str(e))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        with self._lock:
            self._record(load_suite(dest), "zip", filename, dest)
            self.reload()
        return self._registered(dest)

    def add(self, spec, ref=""):
        """Add from a git URL, a folder path or a .zip path."""
        p = Path(spec).expanduser()
        if p.is_dir():
            return self.add_folder(p)
        if p.is_file() and p.suffix == ".zip":
            return self.add_zip(str(p), p.name)
        if re.match(r"^(https?://|git@|ssh://|file://)", spec) or spec.endswith(".git"):
            return self.add_git(spec, ref)
        raise RegistryError(f"'{spec}' is not a folder, a .zip file or a git URL")

    # ------------------------------------------------------------ managing
    def remove(self, uid):
        suite = self.get(uid)
        if suite.source == "builtin":
            raise RegistryError("built-in suites cannot be removed (disable them instead)")
        with self._lock:
            entries = self._read_lock()
            self._write_lock([e for e in entries if Path(e["path"]) != suite.path])
            # only delete what we own: never a linked folder
            if suite.source in ("git", "zip", "local"):
                shutil.rmtree(suite.path, ignore_errors=True)
            self.reload()
        return suite

    def update(self, uid):
        """git pull for git suites. Returns a message."""
        suite = self.get(uid)
        if suite.source == "builtin":
            return "built-in suites are updated with the tester (`dt update`)"
        if suite.source != "git":
            return f"{suite.source} suites have nothing to update"
        entries = self._read_lock()
        entry = next((e for e in entries if Path(e["path"]) == suite.path), {})
        try:
            old, new = git.update(suite.path, entry.get("ref", ""))
        except git.GitError as e:
            raise RegistryError(str(e))
        with self._lock:
            entry["sha"] = new
            self._write_lock(entries)
            self.reload()
        if old == new:
            return f"{uid} is up to date"
        return f"{uid} updated {old[:7]} → {new[:7]}"

    def update_all(self):
        msgs = []
        for s in self.all():
            if s.source == "git":
                try:
                    msgs.append(self.update(s.uid))
                except RegistryError as e:
                    msgs.append(f"{s.uid}: {e}")
        return msgs

    def pack(self, uid, dest_dir="."):
        suite = self.get(uid)
        dest = Path(dest_dir).expanduser() / f"{self._slug(suite.id)}-{suite.version}.zip"
        return archive.pack(suite.path, dest)

    def create(self, name, project, runner="c-unit", folder=None):
        """Scaffold a new suite from templates/suite."""
        slug = self._slug(name)
        dest = Path(folder).expanduser().resolve() if folder else self.root / "local" / slug
        if dest.exists() and any(dest.iterdir()):
            raise RegistryError(f"{dest} already exists and is not empty")
        template = paths.TEMPLATES / "suite" / runner
        if not template.is_dir():
            raise RegistryError(f"no template for runner '{runner}'")
        shutil.copytree(template, dest, dirs_exist_ok=True)
        for f in dest.rglob("*"):
            if f.is_file() and f.suffix in (".toml", ".c", ".py", ".md", ".sh"):
                text = f.read_text()
                text = text.replace("__ID__", slug).replace("__NAME__", name).replace("__PROJECT__", project)
                f.write_text(text)
        if folder:
            self.add_folder(dest)
        self.reload()
        return dest
