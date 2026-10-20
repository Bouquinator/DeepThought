"""The tester updates itself with git (fetch + pull --ff-only)."""

import json
import threading
import time

from deepthought.core import paths
from deepthought.core.sources import git

CHECK_EVERY = 24 * 3600


def _state_file():
    return paths.data_dir() / "update.json"


def cached_status():
    try:
        return json.loads(_state_file().read_text())
    except (OSError, ValueError):
        return {}


def check(fetch=True):
    """Status of the tester repo against its upstream. Fetches by default."""
    st = git.status(paths.REPO_ROOT, fetch=fetch)
    st["checked"] = time.time()
    st["available"] = st.get("behind", 0) > 0
    if st["available"] and st.get("head"):
        st["changes"] = git.log_between(paths.REPO_ROOT, "HEAD", "@{u}")
    try:
        _state_file().write_text(json.dumps(st))
    except OSError:
        pass
    return st


def check_in_background(callback=None, force=False):
    """Fetch at most once a day (or when forced), off the main thread."""
    st = cached_status()
    if not force and time.time() - st.get("checked", 0) < CHECK_EVERY:
        if callback:
            callback(st)
        return

    def work():
        result = check(fetch=True)
        if callback:
            callback(result)

    threading.Thread(target=work, daemon=True, name="update-check").start()


def update():
    """git pull --ff-only. Returns (ok, message, changes)."""
    st = git.status(paths.REPO_ROOT, fetch=True)
    if not st["is_git"]:
        return False, "this copy of the tester is not a git clone: download a fresh copy instead", []
    if st["dirty"]:
        files = ", ".join(st["dirty"][:5])
        return False, (f"local modifications in the tester repo ({files}). Your own suites belong in "
                       "~/.deepthought/suites (`dt suite new`); stash or revert these changes first."), []
    if not st["upstream"]:
        return False, "no upstream branch configured (git branch --set-upstream-to=origin/main)", []
    if st["behind"] == 0:
        check(fetch=False)
        return True, "already up to date", []
    try:
        old, new = git.update(paths.REPO_ROOT)
    except git.GitError as e:
        return False, f"update failed: {e}", []
    changes = git.log_between(paths.REPO_ROOT, old, new)
    check(fetch=False)
    return True, f"updated {old[:7]} → {new[:7]} — restart dt to load the new version", changes
