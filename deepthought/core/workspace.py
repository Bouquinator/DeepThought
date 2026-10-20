"""Isolated copy of the student's project. Builds never touch the original folder.

The copy is synchronised incrementally (mtime + size) so `make` stays
incremental between runs and watch mode is fast.
"""

import fnmatch
import hashlib
import os
import shutil
from pathlib import Path

IGNORE_DIRS = {".git", ".svn", ".hg", "__pycache__", "node_modules", ".vscode", ".idea", ".dt", ".cache"}
IGNORE_FILES = ["*.o", "*.a", "*.so", "*.dylib", "*.d", ".DS_Store", "a.out", "*.pyc", "*.swp", "*~"]
BINARY_MAGIC = (b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe")
MAX_FILE = 50 << 20


def project_key(path):
    path = str(Path(path).resolve())
    return hashlib.sha1(path.encode()).hexdigest()[:12]


def _ignored_file(name):
    return any(fnmatch.fnmatch(name, pat) for pat in IGNORE_FILES)


def _is_binary_exe(path):
    try:
        if not os.access(path, os.X_OK):
            return False
        with open(path, "rb") as f:
            return f.read(4) in BINARY_MAGIC
    except OSError:
        return False


def iter_source_files(root):
    """Yield (relpath, abspath) of the project files we care about."""
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".dt"))
        for name in sorted(filenames):
            if _ignored_file(name):
                continue
            full = Path(dirpath) / name
            if full.is_symlink() or not full.is_file():
                continue
            if full.stat().st_size > MAX_FILE or _is_binary_exe(full):
                continue
            yield str(full.relative_to(root)), full


def fingerprint(root):
    """Cheap change detector for watch mode: (relpath, mtime_ns, size) set."""
    h = hashlib.sha1()
    for rel, full in iter_source_files(root):
        st = full.stat()
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
    for rel, full in iter_source_files(src):
        wanted.add(rel)
        target = dst / rel
        st = full.stat()
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
