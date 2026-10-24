"""Isolated copy of the student's project. Builds never touch the original folder.

The copy is synchronised incrementally (mtime + size) so `make` stays
incremental between runs and watch mode is fast.
"""

import fnmatch
import hashlib
import os
import re
import shutil
from pathlib import Path

IGNORE_DIRS = {".git", ".svn", ".hg", "__pycache__", "node_modules", ".vscode", ".idea", ".dt", ".cache"}
IGNORE_FILES = ["*.o", "*.a", "*.so", "*.dylib", "*.d", ".DS_Store", "a.out", "*.pyc", "*.swp", "*~"]
BINARY_MAGIC = (b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe")
MAX_FILE = 50 << 20


def project_key(path):
    path = str(Path(path).resolve())
    return hashlib.sha1(path.encode()).hexdigest()[:12]


_IGNORED = re.compile("|".join(fnmatch.translate(pat) for pat in IGNORE_FILES))
_binary_cache = {}  # path -> (mtime_ns, size, is a compiled executable): watch mode asks every second


def _ignored_file(name):
    return _IGNORED.match(name) is not None


def _is_binary_exe(path, st):
    if not st.st_mode & 0o111:
        return False
    key = (st.st_mtime_ns, st.st_size)
    cached = _binary_cache.get(path)
    if cached and cached[:2] == key:
        return cached[2]
    try:
        with open(path, "rb") as f:
            binary = f.read(4) in BINARY_MAGIC
    except OSError:
        binary = False
    if len(_binary_cache) > 10000:
        _binary_cache.clear()
    _binary_cache[path] = (*key, binary)
    return binary


def _scan(root, rel=""):
    """Yield (relpath, abspath, stat) of the project files we care about, in a
    stable order, with a single stat per file. Unreadable entries are skipped."""
    try:
        with os.scandir(os.path.join(root, rel)) as it:
            entries = sorted(it, key=lambda e: e.name)
    except OSError:
        return
    subdirs = []
    for e in entries:
        try:
            if e.is_dir(follow_symlinks=False):
                if e.name not in IGNORE_DIRS and not e.name.startswith(".dt"):
                    subdirs.append(e.name)
                continue
            if _ignored_file(e.name) or not e.is_file(follow_symlinks=False):
                continue  # symlinks, sockets, fifos...
            st = e.stat(follow_symlinks=False)
        except OSError:  # vanished while we looked
            continue
        if st.st_size > MAX_FILE or _is_binary_exe(e.path, st):
            continue
        yield rel + e.name, e.path, st
    for d in subdirs:
        yield from _scan(root, f"{rel}{d}/")


def iter_source_files(root):
    """Yield (relpath, abspath) of the project files we care about."""
    for rel, full, _ in _scan(str(root)):
        yield rel, Path(full)


def fingerprint(root):
    """Cheap change detector for watch mode: (relpath, mtime_ns, size) set."""
    h = hashlib.sha1()
    for rel, _, st in _scan(str(root)):
        h.update(f"{rel}\0{st.st_mtime_ns}\0{st.st_size}\n".encode())
    return h.hexdigest()


def sync(src, dst, manifest=None):
    """Mirror src into dst. Returns the number of files copied or removed.

    Only files copied by a previous sync (listed in `manifest`) are deleted
    when they disappear from src: build products (objects, markers, binaries)
    created inside dst by the project's Makefile are left alone.
    """
    src, dst = Path(src), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    manifest = Path(manifest) if manifest else dst.parent / ".dt_synced"
    try:
        previous = set(manifest.read_text().splitlines())
    except OSError:
        previous = set()
    wanted = set()
    changes = 0
    for rel, full, st in _scan(str(src)):
        wanted.add(rel)
        target = dst / rel
        try:
            tst = target.stat()
            if tst.st_size == st.st_size and tst.st_mtime_ns == st.st_mtime_ns:
                continue
        except FileNotFoundError:
            pass
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(full, target)
        changes += 1
    for rel in previous - wanted:
        target = dst / rel
        if target.is_file():
            target.unlink()
            changes += 1
            parent = target.parent
            while parent != dst and parent.is_dir() and not os.listdir(parent):
                parent.rmdir()
                parent = parent.parent
    manifest.write_text("\n".join(sorted(wanted)))
    return changes


class Workspace:
    def __init__(self, cache_root, project_path, flavor=""):
        self.project_path = Path(project_path).resolve()
        self.key = project_key(self.project_path)
        self.root = Path(cache_root) / "ws" / f"{self.key}{'-' + flavor if flavor else ''}"
        self.src = self.root / "project"
        self.out = self.root / "out"

    def sync(self):
        self.out.mkdir(parents=True, exist_ok=True)
        return sync(self.project_path, self.src)

    def group_dir(self, suite_uid, gid_slug):
        d = self.out / suite_uid / gid_slug
        d.mkdir(parents=True, exist_ok=True)
        return d
