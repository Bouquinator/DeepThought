"""Subprocess helper: timeouts, process-group kill, output caps, cancellation."""

import atexit
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import weakref
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
        _trackers.add(self)

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


# ---------------------------------------------------------------- exiting cleanly
# Test processes run in their own session, so a Ctrl-C or a closed terminal
# never reaches them: only we can kill them. shutdown() does it when we exit
# normally; the guardian does it when we die without a chance to clean up
# (SIGKILL, crash). Without both, an infinite loop under test spins forever.
_trackers = weakref.WeakSet()
_live = set()
_live_lock = threading.Lock()
_closing = threading.Event()

_GUARDIAN = r"""# DeepThought guardian: stops the tests left running when DeepThought exits
import os, signal, sys
for s in (signal.SIGINT, signal.SIGHUP, signal.SIGTERM):
    signal.signal(s, signal.SIG_IGN)
os.chdir("/")
groups = set()
for line in sys.stdin.buffer:
    if line[:1] == b"+":
        groups.add(int(line[1:]))
    elif line[:1] == b"-":
        groups.discard(int(line[1:]))
for g in groups:
    try:
        os.killpg(g, signal.SIGKILL)
    except OSError:
        pass
"""


class _Guardian:
    """A tiny process told about every process group we start. When DeepThought
    dies, however it dies, its socket closes and the guardian kills the groups
    still running."""

    def __init__(self):
        self._lock = threading.Lock()
        self._sock = None
        self._failed = False

    def _spawn(self):
        # a socket, not a pipe: if the guardian was killed, writing to it must not
        # SIGPIPE us (`dt run` restores the default SIGPIPE action)
        ours, theirs = socket.socketpair()  # non-inheritable: test processes never hold it open
        try:
            if sys.platform == "darwin" and not hasattr(socket, "MSG_NOSIGNAL"):
                ours.setsockopt(socket.SOL_SOCKET, 0x1022, 1)  # SO_NOSIGPIPE
            # posix_spawn, not Popen: it outlives us by design, so no "still running" warning
            os.posix_spawn(sys.executable, [sys.executable, "-I", "-S", "-c", _GUARDIAN], os.environ,
                           file_actions=[(os.POSIX_SPAWN_DUP2, theirs.fileno(), 0),
                                         (os.POSIX_SPAWN_OPEN, 1, os.devnull, os.O_WRONLY, 0),
                                         (os.POSIX_SPAWN_DUP2, 1, 2)],
                           setpgroup=0)
        except (OSError, ValueError, AttributeError):
            ours.close()
            self._failed = True
        else:
            self._sock = ours
        finally:
            theirs.close()

    def send(self, msg):
        if self._sock is None:
            with self._lock:
                if self._sock is None and not self._failed:
                    self._spawn()
        if self._sock is not None:
            try:
                self._sock.send(msg.encode(), getattr(socket, "MSG_NOSIGNAL", 0))
            except OSError:
                pass

    def close(self):
        with self._lock:
            self._failed = True
            if self._sock is not None:
                self._sock.close()


_guardian = _Guardian()
atexit.register(_guardian.close)  # the guardian then stops whatever is left


def shutdown():
    """DeepThought is exiting: cancel every run, kill every test process, start no new one."""
    _closing.set()
    for t in list(_trackers):
        t.cancel()
    with _live_lock:
        procs = list(_live)
    for p in procs:
        _killpg(p)
    _guardian.close()


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
    if _closing.is_set():
        return ProcResult(-signal.SIGKILL, b"", b"DeepThought is exiting", 0, cancelled=True)
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
    _guardian.send(f"+{p.pid}\n")
    with _live_lock:
        _live.add(p)
    if _closing.is_set():
        _killpg(p)
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
    with _live_lock:
        _live.discard(p)
    _guardian.send(f"-{p.pid}\n")
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
