"""Subprocess helper: timeouts, process-group kill, output caps, cancellation."""

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass

MAX_OUTPUT = 1 << 20


@dataclass
class ProcResult:
    code: int
    stdout: bytes
    stderr: bytes
    ms: int
    timed_out: bool = False
    cancelled: bool = False
    truncated: bool = False

    @property
    def ok(self):
        return self.code == 0 and not self.timed_out and not self.cancelled

    @property
    def signal(self):
        return -self.code if self.code < 0 else 0

    def text(self):
        out = self.stdout.decode("utf-8", "replace")
        err = self.stderr.decode("utf-8", "replace")
        return (out + ("\n" if out and err and not out.endswith("\n") else "") + err).rstrip()


class ProcTracker:
    """Remembers live process groups of a run so they can be killed on cancel."""

    def __init__(self):
        self._lock = threading.Lock()
        self._procs = set()
        self.cancelled = False

    def add(self, p):
        with self._lock:
            if self.cancelled:
                _killpg(p)
            self._procs.add(p)

    def remove(self, p):
        with self._lock:
            self._procs.discard(p)

    def cancel(self):
        with self._lock:
            self.cancelled = True
            procs = list(self._procs)
        for p in procs:
            _killpg(p)


def _killpg(p):
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            p.kill()
        except OSError:
            pass


def _reader(stream, sink, cap, flags):
    total = 0
    while True:
        chunk = stream.read1(65536) if hasattr(stream, "read1") else stream.read(65536)
        if not chunk:
            break
        if total < cap:
            sink.append(chunk[: cap - total])
        else:
            flags["truncated"] = True
        total += len(chunk)


def run(argv, cwd=None, env=None, timeout=60.0, stdin=None, tracker=None,
        max_output=MAX_OUTPUT, pass_fds=(), shell=False, on_start=None):
    """Run a command to completion. Never raises for process failures."""
    start = time.monotonic()
    full_env = dict(os.environ)
    if env:
        full_env.update({k: str(v) for k, v in env.items()})
    try:
        p = subprocess.Popen(
            argv, cwd=cwd, env=full_env, shell=shell,
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True, pass_fds=pass_fds,
        )
    except (OSError, ValueError) as e:
        return ProcResult(127, b"", str(e).encode(), 0)
    if on_start:
        on_start(p)
    if tracker:
        tracker.add(p)
    out, err, flags = [], [], {"truncated": False}
    threads = [
        threading.Thread(target=_reader, args=(p.stdout, out, max_output, flags), daemon=True),
        threading.Thread(target=_reader, args=(p.stderr, err, max_output, flags), daemon=True),
    ]
    for t in threads:
        t.start()
    if stdin is not None:
        try:
            p.stdin.write(stdin if isinstance(stdin, bytes) else stdin.encode())
        except (BrokenPipeError, OSError):
            pass
        finally:
            try:
                p.stdin.close()
            except OSError:
                pass
    timed_out = False
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _killpg(p)
        p.wait()
    # kill leftovers in the group (e.g. a test's grandchild stuck forever)
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    for t in threads:
        t.join(timeout=2)
    for stream in (p.stdout, p.stderr, p.stdin):
        if stream:
            try:
                stream.close()
            except OSError:
                pass
    if tracker:
        tracker.remove(p)
    return ProcResult(
        code=p.returncode,
        stdout=b"".join(out),
        stderr=b"".join(err),
        ms=int((time.monotonic() - start) * 1000),
        timed_out=timed_out,
        cancelled=bool(tracker and tracker.cancelled),
        truncated=flags["truncated"],
    )


def which(name):
    from shutil import which as _which
    return _which(name)
