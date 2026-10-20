"""Suites shared as .zip files: safe extraction and packing."""

import io
import shutil
import tempfile
import zipfile
from pathlib import Path

MAX_TOTAL = 200 << 20


class ArchiveError(Exception):
    pass


def find_suite_root(path):
    """The shallowest directory containing a suite.toml."""
    path = Path(path)
    candidates = sorted(path.rglob("suite.toml"), key=lambda p: len(p.parts))
    if not candidates:
        raise ArchiveError("no suite.toml found in the archive")
    return candidates[0].parent


def extract(data_or_path, dest_parent, name_hint="suite"):
    """Extract a zip into a temp dir, locate the suite, move it under dest_parent.

    Returns the temporary directory holding the suite root; the caller moves it.
    """
    source = io.BytesIO(data_or_path) if isinstance(data_or_path, (bytes, bytearray)) else data_or_path
    try:
        zf = zipfile.ZipFile(source)
    except zipfile.BadZipFile:
        raise ArchiveError("not a valid zip file")
    total = 0
    tmp = Path(tempfile.mkdtemp(prefix="dt-zip-", dir=dest_parent))
    with zf:
        for info in zf.infolist():
            name = info.filename
            target = (tmp / name).resolve()
            if not str(target).startswith(str(tmp.resolve())) or name.startswith("/"):
                shutil.rmtree(tmp, ignore_errors=True)
                raise ArchiveError(f"unsafe path in archive: {name}")
            if name.startswith("__MACOSX/"):
                continue
            total += info.file_size
            if total > MAX_TOTAL:
                shutil.rmtree(tmp, ignore_errors=True)
                raise ArchiveError("archive is too large (>200MB)")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            mode = (info.external_attr >> 16) & 0o777
            if mode & 0o100:
                target.chmod(0o755)
    return tmp


def pack(suite_dir, dest_zip):
    suite_dir = Path(suite_dir)
    dest_zip = Path(dest_zip)
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(suite_dir.rglob("*")):
            rel = f.relative_to(suite_dir)
            if any(part in (".git", "__pycache__", ".DS_Store") for part in rel.parts):
                continue
            arc = Path(suite_dir.name) / rel
            if f.is_file():
                info = zipfile.ZipInfo(str(arc))
                info.external_attr = (f.stat().st_mode & 0o777) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, f.read_bytes())
    return dest_zip
