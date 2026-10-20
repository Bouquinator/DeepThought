"""Shared test helpers: an isolated DT_HOME / cache per test run."""

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_HOME = tempfile.mkdtemp(prefix="dt-test-home-")
os.environ["DT_HOME"] = _HOME
os.environ["DT_CACHE"] = os.path.join(_HOME, "cache")


def fresh_home():
    """Empty the shared DT_HOME (keeps the build cache for speed)."""
    for p in Path(_HOME).iterdir():
        if p.name != "cache":
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    return Path(_HOME)


def manager(config_overrides=None):
    from deepthought.core.config import Config
    from deepthought.core.executor import RunManager
    from deepthought.core.registry import Registry

    config = Config()
    config.values.update({"norminette": False, **(config_overrides or {})})
    return RunManager(config, Registry(config))


def statuses(run):
    """{test id: status} for a finished run dict."""
    return {t["id"]: t["status"] for g in run["groups"] for t in g["tests"]}


def write_suite(root, toml, files=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "suite.toml").write_text(toml)
    for rel, content in (files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return root
