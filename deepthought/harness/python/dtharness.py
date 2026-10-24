"""DeepThought Python harness.

Write tests in plain Python files:

    from dtharness import test, given, expect, expect_eq, expect_raises, capture_stdout, error
    import my_module                      # imported from the student's project

    @test("add() adds two numbers")
    def add_basic():
        expect_eq(my_module.add(1, 2), 3)

Run (the engine does this for you):

    python3 dtharness.py --list  tests/test_*.py
    python3 dtharness.py [--run ID ...] tests/test_*.py

Each test runs in its own forked process: exceptions, infinite loops
(timeouts) and sys.exit() are reported per test. Results are DTP JSON lines
on $DT_REPORT_FD, or readable text on stderr when it is unset.
Environment: DT_PROJECT (added to sys.path), DT_TIMEOUT, DT_FIXTURES.
"""

import contextlib
import importlib.util
import inspect
import io
import json
import os
import signal
import sys
import tempfile
import time
import traceback

PROTOCOL = 1
EXIT_PASS, EXIT_FAIL, EXIT_SKIP = 0, 1, 2
EXIT_REPORTED = 5  # the test reported its own end (error())

_tests = []
_state = {"failed": 0, "id": "", "out": None, "json": False, "input": ""}


class _Fatal(Exception):
    """Raised by require_*: stops the current test."""


class _Skip(Exception):
    pass


class _SuiteError(Exception):
    """Raised by error(): a problem in the test suite, not in the student's code."""


# ------------------------------------------------------------------ public API
def test(desc=None, *, name=None, timeout=None):
    """Decorator registering a test. Usable as @test or @test("description")."""

    def register(fn):
        module = os.path.splitext(os.path.basename(inspect.getsourcefile(fn) or "tests"))[0]
        _tests.append({
            "id": f"{module}/{name or fn.__name__}",
            "name": name or fn.__name__,
            "desc": (desc if isinstance(desc, str) else None) or (fn.__doc__ or "").strip().split("\n")[0],
            "file": os.path.abspath(inspect.getsourcefile(fn) or ""),
            "line": inspect.getsourcelines(fn)[1] if inspect.getsourcefile(fn) else 0,
            "fn": fn,
            "timeout": timeout,
        })
        return fn

    if callable(desc):
        fn, desc = desc, None
        return register(fn)
    return register


def _show(v):
    return v if isinstance(v, str) else repr(v)


def _caller():
    frame = inspect.stack()[2]
    return os.path.abspath(frame.filename), frame.lineno


def _check(ok, msg, expected, actual, fatal=False):
    if ok:
        return True
    _state["failed"] += 1
    file, line = _caller_outside()
    ev = {"t": "assert", "id": _state["id"], "ok": False, "msg": msg,
          "expected": _show(expected), "actual": _show(actual), "file": file, "line": line}
    if _state["input"]:
        ev["input"] = _state["input"]
    if isinstance(expected, str) and isinstance(actual, str):
        ev["cmp"] = "text"
    _emit(ev, human=f"    ✗ {os.path.basename(file)}:{line}  {msg}\n"
                    + (f"        input:    {_state['input']}\n" if _state["input"] else "")
                    + f"        expected: {_show(expected)!r}\n        actual:   {_show(actual)!r}\n")
    if fatal:
        raise _Fatal()
    return False


def _caller_outside():
    """First stack frame outside this module (the line in the test file)."""
    here = os.path.abspath(__file__)
    for frame in inspect.stack()[1:]:
        if os.path.abspath(frame.filename) != here:
            return os.path.abspath(frame.filename), frame.lineno
    return "", 0


def expect(cond, msg="expected a true value"):
    return _check(bool(cond), msg, True, cond)


def require(cond, msg="expected a true value"):
    return _check(bool(cond), msg, True, cond, fatal=True)


def expect_eq(actual, expected, msg=None):
    return _check(actual == expected, msg or "values differ", expected, actual)


def require_eq(actual, expected, msg=None):
    return _check(actual == expected, msg or "values differ", expected, actual, fatal=True)


def expect_ne(actual, unexpected, msg=None):
    return _check(actual != unexpected, msg or "values should differ", f"anything but {unexpected!r}", actual)


def expect_close(actual, expected, tol=1e-9, msg=None):
    ok = isinstance(actual, (int, float)) and abs(actual - expected) <= tol
    return _check(ok, msg or f"values differ by more than {tol}", expected, actual)


def expect_type(value, typ, msg=None):
    return _check(isinstance(value, typ), msg or f"expected an instance of {typ.__name__}",
                  typ.__name__, type(value).__name__)


def expect_raises(exc_type, fn, *args, msg=None, **kwargs):
    try:
        fn(*args, **kwargs)
    except exc_type:
        return True
    except Exception as e:  # wrong exception
        return _check(False, msg or f"{getattr(fn, '__name__', 'call')} raised the wrong exception",
                      exc_type.__name__, f"{type(e).__name__}: {e}")
    return _check(False, msg or f"{getattr(fn, '__name__', 'call')} did not raise", exc_type.__name__, "no exception")


@contextlib.contextmanager
def capture_stdout():
    """with capture_stdout() as out: ...; then out.text holds what was printed."""

    class Out:
        text = ""

    buf = io.StringIO()
    out = Out()
    with contextlib.redirect_stdout(buf):
        yield out
    out.text = buf.getvalue()


def expect_output(fn, expected, *args, msg=None, **kwargs):
    with capture_stdout() as out:
        fn(*args, **kwargs)
    return _check(out.text == expected, msg or f"output of {getattr(fn, '__name__', 'call')}()", expected, out.text)


def fixture(relpath):
    return os.path.join(os.environ.get("DT_FIXTURES", "fixtures"), relpath)


def given(*values, **named):
    """Describe the input being tested; shown with every failure (and crash) that follows.

    given("empty list")  ·  given([1, 2, 3])  ·  given(n=4, text="abc")
    """
    parts = [v if isinstance(v, str) else repr(v) for v in values]
    parts += [f"{k}={v!r}" for k, v in named.items()]
    _state["input"] = ", ".join(parts)
    _emit({"t": "input", "id": _state["id"], "value": _state["input"]})


def note(msg):
    _emit({"t": "log", "id": _state["id"], "msg": str(msg)}, human=f"    · {msg}\n")


def skip(reason=""):
    note(f"skipped: {reason}")
    raise _Skip(reason)


def fail(msg):
    return _check(False, msg, "", "")


def error(msg):
    """A problem in the test suite, not in the student's code (a missing fixture…):
    stops the test with the status "suite_error", which never counts against the student."""
    raise _SuiteError(str(msg))


# ------------------------------------------------------------------ plumbing
def _emit(ev, human=None):
    out = _state["out"]
    if _state["json"]:
        out.write(json.dumps(ev) + "\n")
    elif human:
        out.write(human)
    out.flush()


def _load(paths):
    project = os.environ.get("DT_PROJECT")
    if project and project not in sys.path:
        sys.path.insert(0, project)
    sys.modules.setdefault("dtharness", sys.modules[__name__])
    broken = []
    for path in paths:
        path = os.path.abspath(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        d = os.path.dirname(path)
        if d not in sys.path:
            sys.path.insert(1, d)
        try:
            spec = importlib.util.spec_from_file_location(f"dt_tests_{stem}", path)
            mod = importlib.util.module_from_spec(spec)
            with contextlib.redirect_stdout(io.StringIO()):
                spec.loader.exec_module(mod)
        except BaseException as e:  # import errors of the student's module land here
            broken.append({"id": f"{stem}/import", "name": "import", "file": path, "line": 1,
                           "desc": f"{os.path.basename(path)} could not be imported",
                           "error": "".join(traceback.format_exception(type(e), e, e.__traceback__))[-3000:]})
    return broken


def _run_one(t, default_timeout):
    _state["id"] = t["id"]
    _emit({"t": "start", "id": t["id"]})
    start = time.monotonic()
    if "error" in t:
        _emit({"t": "end", "id": t["id"], "status": "build_error", "ms": 0,
               "reason": "the test file could not be imported (syntax error or missing module in your project?)",
               "output": t["error"]},
              human=f"  ERROR   {t['id']}\n{t['error']}\n")
        return
    timeout = float(t.get("timeout") or default_timeout)
    tmp = tempfile.TemporaryFile()
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        code = EXIT_PASS
        try:
            os.dup2(tmp.fileno(), 1)
            os.dup2(tmp.fileno(), 2)
            signal.setitimer(signal.ITIMER_REAL, timeout)
            _state["failed"] = 0
            _state["input"] = ""
            t["fn"]()
            code = EXIT_FAIL if _state["failed"] else EXIT_PASS
        except _Fatal:
            code = EXIT_FAIL
        except _Skip:
            code = EXIT_SKIP
        except _SuiteError as e:
            sys.stdout.flush()
            sys.stderr.flush()
            tmp.seek(0)
            out = tmp.read(4096).decode("utf-8", "replace")
            ev = {"t": "end", "id": t["id"], "status": "suite_error", "reason": str(e),
                  "ms": int((time.monotonic() - start) * 1000)}
            if out:
                ev["output"] = out
            _emit(ev, human=f"  SUITE ERROR {t['id']}  {e}\n" + (f"    output:\n{out}\n" if out else ""))
            code = EXIT_REPORTED
        except SystemExit as e:
            _check(False, "the code called exit()", "no exit", f"exit({e.code})")
            code = EXIT_FAIL
        except BaseException as e:
            tb = traceback.extract_tb(e.__traceback__)
            where = next((f for f in reversed(tb) if not f.filename.endswith("dtharness.py")), tb[-1] if tb else None)
            reason = f"{type(e).__name__}: {e}"
            if where:
                reason += f"  (at {os.path.basename(where.filename)}:{where.lineno})"
            sys.stderr.write("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            _emit({"t": "log", "id": t["id"], "msg": reason})
            code = 4
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(code)
    _, status = os.waitpid(pid, 0)
    ms = int((time.monotonic() - start) * 1000)
    if os.WIFEXITED(status) and os.WEXITSTATUS(status) == EXIT_REPORTED:
        tmp.close()
        return
    tmp.seek(0)
    output = tmp.read(4096).decode("utf-8", "replace")
    tmp.close()
    ev = {"t": "end", "id": t["id"], "ms": ms}
    if os.WIFSIGNALED(status):
        sig = os.WTERMSIG(status)
        if sig == signal.SIGALRM:
            ev.update(status="timeout", reason=f"did not finish within {timeout:g}s (infinite loop?)")
        else:
            ev.update(status="crash", signal=signal.Signals(sig).name, reason=f"killed by {signal.Signals(sig).name}")
    else:
        code = os.WEXITSTATUS(status)
        ev["exit"] = code
        ev["status"] = {EXIT_PASS: "pass", EXIT_FAIL: "fail", EXIT_SKIP: "skip"}.get(code, "crash")
        if code == 4:
            last = [l for l in output.strip().splitlines() if l.strip()]
            ev["reason"] = "an exception was raised: " + (last[-1] if last else "?")
    if output:
        ev["output"] = output
    _emit(ev, human=f"  {ev['status'].upper():<8} {t['id']}  ({ms} ms) {ev.get('reason', '')}\n"
                    + (f"    output:\n{output}\n" if output and ev["status"] != "pass" else ""))


def main(argv):
    fd = os.environ.get("DT_REPORT_FD")
    if fd:
        _state["json"] = True
        _state["out"] = os.fdopen(os.dup(int(fd)), "w")
    else:
        _state["out"] = os.fdopen(os.dup(2), "w")
    listing = "--list" in argv
    selected, files, mode = [], [], None
    for a in argv:
        if a in ("--list", "--run"):
            mode = a
        elif mode == "--run" and not a.endswith(".py"):
            selected.append(a)
        else:
            files.append(a)
    broken = _load(files)
    tests = _tests + broken
    _emit({"t": "hello", "protocol": PROTOCOL, "harness": "python"})
    if listing:
        for t in tests:
            _emit({"t": "discover", "id": t["id"], "name": t["name"], "desc": t["desc"],
                   "file": t["file"], "line": t["line"]}, human=f"{t['id']:<40} {t['desc']}\n")
        return 0
    timeout = float(os.environ.get("DT_TIMEOUT") or 5)
    for t in tests:
        group = t["id"].split("/")[0]
        if not selected or t["id"] in selected or group in selected:
            _run_one(t, timeout)
    _emit({"t": "done"})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
