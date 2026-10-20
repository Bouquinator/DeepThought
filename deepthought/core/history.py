"""Past runs, saved as JSON under ~/.deepthought/history/<project-key>/."""

import json
import time
from pathlib import Path

from deepthought.core import paths
from deepthought.core.models import FAILED_STATUSES, PASS
from deepthought.core.workspace import project_key

KEEP = 50


def _dir(project_path):
    d = paths.data_dir() / "history" / project_key(project_path)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(run_dict):
    d = _dir(run_dict["project"]["path"])
    (d / f"{run_dict['id']}.json").write_text(json.dumps(run_dict))
    files = sorted(d.glob("*.json"))
    for old in files[:-KEEP]:
        old.unlink(missing_ok=True)


def list_runs(project_path):
    out = []
    for f in sorted(_dir(project_path).glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        out.append({k: data.get(k) for k in ("id", "status", "started", "finished", "score", "suites", "options")})
    return out


def load(run_id):
    for f in (paths.data_dir() / "history").glob(f"*/{run_id}.json"):
        try:
            return json.loads(f.read_text())
        except (OSError, ValueError):
            return None
    return None


def previous(project_path, before_id, sanitize=False):
    """The latest finished run before `before_id` made with the same build flavour."""
    for f in sorted(_dir(project_path).glob("*.json"), reverse=True):
        if f.stem < before_id:
            try:
                data = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            if bool(data.get("options", {}).get("sanitize")) == sanitize and data.get("status") == "done":
                return data
    return None


def mark_changes(run, prev):
    """Flag tests that regressed (passed last time) or got fixed."""
    if not prev:
        return 0, 0
    old = {t["tid"]: t["status"] for g in prev.get("groups", []) for t in g.get("tests", [])}
    reg = fix = 0
    for t in run.all_tests():
        before = old.get(t.tid)
        if before == PASS and t.status in FAILED_STATUSES:
            t.regression = True
            reg += 1
        elif before in FAILED_STATUSES and t.status == PASS:
            t.fixed = True
            fix += 1
    return reg, fix


def new_run_id():
    return time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
