"""Where things live: the repo (code, built-in suites) and the user's data/cache dirs."""

import getpass
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG_DIR = REPO_ROOT / "deepthought"
HARNESS_C = PKG_DIR / "harness" / "c"
HARNESS_PY = PKG_DIR / "harness" / "python"
WEB_DIR = PKG_DIR / "web"
BUILTIN_SUITES = REPO_ROOT / "suites"
COMMUNITY_SUITES = REPO_ROOT / "community"
TEMPLATES = REPO_ROOT / "templates"
INDEX_FILE = REPO_ROOT / "index.json"


def _user():
    try:
        return getpass.getuser()
    except Exception:
        return str(os.getuid())


def data_dir():
    """User data (config, installed suites, history). Never inside the repo."""
    path = Path(os.environ.get("DT_HOME") or Path.home() / ".deepthought")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _writable(path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        return os.access(path, os.W_OK)
    except OSError:
        return False


def cache_dir(configured=""):
    """Build artifacts. Kept out of $HOME by default: 42 home quotas are small."""
    candidates = [os.environ.get("DT_CACHE"), configured]
    goinfre = Path.home() / "goinfre"
    if goinfre.is_dir():
        candidates.append(str(goinfre / ".deepthought-cache"))
    candidates.append(os.path.join("/tmp", f"dt-{_user()}"))
    for c in candidates:
        if c and _writable(Path(c).expanduser()):
            return Path(c).expanduser()
    fallback = data_dir() / "cache"
    fallback.mkdir(exist_ok=True)
    return fallback


def user_suites_dir():
    path = data_dir() / "suites"
    for sub in ("local", "git", "zip"):
        (path / sub).mkdir(parents=True, exist_ok=True)
    return path
