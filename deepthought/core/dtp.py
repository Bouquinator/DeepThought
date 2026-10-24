"""DeepThought Test Protocol: JSON lines emitted by every harness/runner.

  {"t":"hello","protocol":1}
  {"t":"discover","id":"grp/name","name":"name","desc":"...","file":"...","line":3}
  {"t":"start","id":"grp/name"}
  {"t":"assert","id":"grp/name","ok":false,"msg":"...","expected":"...","actual":"...","file":"...","line":9,
   "input":"...", "cmp":"text"}     (optional: the input under test; "text" = the values are compared texts)
  {"t":"log","id":"grp/name","msg":"..."}
  {"t":"input","id":"grp/name","value":"src=\"abc\", n=2"}     (input under test from now on)
  {"t":"leak","id":"grp/name","bytes":12,"count":1}
  {"t":"end","id":"grp/name","status":"pass|fail|crash|timeout|leak|skip|error|suite_error","ms":3,
   "signal":"SIGSEGV","reason":"...","output":"..."}
  {"t":"done"}

Strings produced by the C harness map raw bytes to \\u00XX, so `latin-1`
re-encoding gives back the exact bytes.
"""

import json

from deepthought import PROTOCOL

TYPES = {"hello", "discover", "start", "assert", "log", "leak", "end", "done", "input"}
STATUSES = {"pass", "fail", "crash", "timeout", "leak", "skip", "error", "build_error", "suite_error"}


def parse(line):
    """Return an event dict, or None for blank/garbage lines."""
    if isinstance(line, bytes):
        line = line.decode("utf-8", "replace")
    line = line.strip()
    if not line.startswith("{"):
        return None
    try:
        ev = json.loads(line)
    except ValueError:
        return None
    if not isinstance(ev, dict) or ev.get("t") not in TYPES:
        return None
    if ev["t"] == "end" and ev.get("status") not in STATUSES:
        ev["status"] = "error"
    return ev


def compatible(hello):
    return int(hello.get("protocol", 0)) <= PROTOCOL


def emit(fp, **fields):
    """Helper for Python-side emitters."""
    fp.write(json.dumps(fields) + "\n")
    fp.flush()
