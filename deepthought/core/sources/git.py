"""Suites (and the tester itself) distributed as git repositories."""

import os
import re
import subprocess


class GitError(Exception):
    pass


def _git(args, cwd=None, timeout=120, batch=False):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    if batch and "GIT_SSH_COMMAND" not in env:
        env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o ConnectTimeout=5"  # never wait for a passphrase
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, env=env)
    except FileNotFoundError:
        raise GitError("git is not installed")
    except subprocess.TimeoutExpired:
        raise GitError(f"git {args[0]} timed out")
    if r.returncode != 0:
        raise GitError((r.stderr or r.stdout).strip() or f"git {args[0]} failed")
    return r.stdout.strip()


def clone(url, dest, ref=""):
    args = ["clone", "--quiet"]
    if not ref:
        args += ["--depth", "1"]
    _git(args + [url, str(dest)], timeout=300)
    if ref:
        _git(["checkout", "--quiet", ref], cwd=dest)
    return head(dest)


def head(path):
    return _git(["rev-parse", "HEAD"], cwd=path)


def update(path, ref=""):
    """Fetch and fast-forward. Returns (old_sha, new_sha)."""
    old = head(path)
    if ref:
        _git(["fetch", "--quiet", "--tags", "origin"], cwd=path, timeout=300)
        _git(["checkout", "--quiet", ref], cwd=path)
    else:
        _git(["pull", "--quiet", "--ff-only"], cwd=path, timeout=300)
    return old, head(path)


def is_repo(path):
    try:
        return _git(["rev-parse", "--is-inside-work-tree"], cwd=path) == "true"
    except (GitError, OSError):
        return False


def status(path, fetch=False):
    """Branch, ahead/behind upstream, local modifications."""
    info = {"is_git": is_repo(path), "branch": "", "behind": 0, "ahead": 0,
            "dirty": [], "head": "", "upstream": "", "error": ""}
    if not info["is_git"]:
        return info
    try:
        if fetch:
            _git(["fetch", "--quiet"], cwd=path, timeout=30)
        info["head"] = head(path)[:10]
        info["branch"] = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
        try:
            info["upstream"] = _git(["rev-parse", "--abbrev-ref", "@{u}"], cwd=path)
            counts = _git(["rev-list", "--left-right", "--count", "HEAD...@{u}"], cwd=path).split()
            info["ahead"], info["behind"] = int(counts[0]), int(counts[1])
        except GitError:
            pass
        porcelain = _git(["status", "--porcelain", "--untracked-files=no"], cwd=path)
        info["dirty"] = [line[3:] for line in porcelain.splitlines() if line.strip()]
    except GitError as e:
        info["error"] = str(e)
    return info


def log_between(path, old, new, limit=20):
    try:
        out = _git(["log", "--oneline", f"-{limit}", f"{old}..{new}"], cwd=path)
        return out.splitlines()
    except GitError:
        return []


def _is_sha(ref):
    return bool(re.fullmatch(r"[0-9a-f]{7,40}", ref or ""))


def ensure(url, ref, dest, refresh=False):
    """Make `dest` a checkout of url@ref. Returns a short human message.

    A commit ref is pinned: the network is used only when it is missing.
    A branch/tag ref is cloned once and only fetched again when `refresh`.
    """
    from pathlib import Path

    dest = Path(dest)
    if not (dest / ".git").exists():
        if dest.exists() and any(dest.iterdir()):
            raise GitError(f"{dest} exists and is not a git checkout")
        dest.parent.mkdir(parents=True, exist_ok=True)
        _git(["clone", "--quiet", url, str(dest)], timeout=300)
        if ref:
            _git(["checkout", "--quiet", ref], cwd=dest)
        return f"downloaded {url} @ {head(dest)[:10]}"
    current = head(dest)
    if _is_sha(ref) and current.startswith(ref):
        return f"up to date @ {current[:10]}"
    if not _is_sha(ref) and not refresh:
        return f"present @ {current[:10]}"
    _git(["fetch", "--quiet", "--tags", "origin"], cwd=dest, timeout=300)
    if ref:
        target = ref if _is_sha(ref) else f"origin/{ref}"
        try:
            _git(["checkout", "--quiet", target], cwd=dest)
        except GitError:
            _git(["checkout", "--quiet", ref], cwd=dest)
    else:
        _git(["pull", "--quiet", "--ff-only"], cwd=dest, timeout=300)
    return f"updated to {head(dest)[:10]}"
