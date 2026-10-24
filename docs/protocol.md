# DeepThought Test Protocol (DTP) — version 1

DTP is the contract between the DeepThought engine and every program that runs tests: the C harness, the Python harness, the `exec` runner and your own `script` runners. A program that speaks DTP can be tested by DeepThought whatever its language: the engine never looks inside it, it only reads the events it writes.

This document is the complete specification. Every entry also exists in the [reference](reference.md) (`./dt man DTP`, `./dt man assert`…).

- [1. Vocabulary](#1-vocabulary)
- [2. Transport](#2-transport)
- [3. Invocation](#3-invocation)
- [4. Lifecycle of a run](#4-lifecycle-of-a-run)
- [5. Test identifiers](#5-test-identifiers)
- [6. Events](#6-events)
- [7. Statuses](#7-statuses)
- [8. Strings, bytes and encoding](#8-strings-bytes-and-encoding)
- [9. What the engine does with the events](#9-what-the-engine-does-with-the-events)
- [10. Timeouts, crashes and lost processes](#10-timeouts-crashes-and-lost-processes)
- [11. Human mode](#11-human-mode)
- [12. Reference implementations](#12-reference-implementations)
- [13. Compliance checklist](#13-compliance-checklist)
- [14. Versioning](#14-versioning)

---

## 1. Vocabulary

| term | meaning |
|---|---|
| **engine** | DeepThought itself (`deepthought/core/executor.py`): it starts test processes and reads their events. |
| **producer** | Any program that writes DTP: a C test binary, `dtharness.py`, a `script` runner. |
| **event** | One JSON object, on one line, with a `"t"` field naming its type. |
| **test** | The smallest unit that gets a status. It has a stable **id**. |
| **group** (DTP) | The part of a test id before the last `/`. Not the same thing as a suite's `[[group]]`, which is a whole block of tests in `suite.toml`. |
| **discovery** | Running the producer with `--list`: it announces its tests without running them. |
| **status** | The final verdict of one test, sent in its `end` event (`pass`, `fail`, `crash`…). |

## 2. Transport

- The engine creates a **pipe** and starts the producer with the environment variable **`DT_REPORT_FD`** set to the number of the pipe's write end (for example `DT_REPORT_FD=5`). That descriptor is inherited and already open: do not open anything, just write to it.
- The producer writes **one JSON object per line**, terminated by `\n`. Several events must never share a line, and one event must never be split across lines (JSON strings escape their newlines, so this is natural).
- **stdout and stderr stay free** for the code under test. A student's `printf` can never break the protocol, which is the whole point of using a separate descriptor.
- Write each event with a **single `write()`** when you can. When tests run in child processes (fork), several processes may write to the same pipe; writes of up to `PIPE_BUF` bytes (at least 512, usually 4096) are atomic. The C harness builds the whole line in memory and writes it in one call.
- **Flush after every event.** The UI is live: an event sitting in a buffer is an event the user does not see, and it is lost if the process then crashes.
- Lines that are not a JSON object with a known `"t"` are **ignored**. A producer can't corrupt a run by printing garbage to the descriptor, but it also gets no error: use `./dt suite validate` and the human mode to debug.
- The engine reads until the descriptor is closed (all producer processes have exited).

### Environment of a producer

| variable | value |
|---|---|
| `DT_REPORT_FD` | the descriptor to write events to. **Unset** means a human launched the program: see [§11](#11-human-mode). |
| `DT_PROJECT` | absolute path of the isolated copy of the student's project. Never the student's real folder. |
| `DT_SUITE` | absolute path of the suite folder. |
| `DT_FIXTURES` | absolute path of the group's fixtures folder (`fixtures` by default). |
| `DT_TIMEOUT` | the per-test timeout in seconds, as a float (`"5.0"`). The producer is expected to enforce it per test (§10). |
| `DT_MATRIX_<NAME>` | the current value of each matrix variable, e.g. `DT_MATRIX_BUFFER_SIZE=42`. |
| anything in `env` | the group's `env` table from `suite.toml`. |

The current directory is the group's **output folder** (`{out}`): a scratch folder owned by this group and this matrix variant, where the producer may create files.

## 3. Invocation

| arguments | expected behaviour |
|---|---|
| `--list` | Emit `hello`, then one `discover` per test, then exit **without running anything**. |
| `--run ID [ID…]` | Run only the given tests, in the order they were discovered. An argument may also be a **DTP group** (the part before the `/`), which selects every test of that group. |
| *(no argument)* | Run every test. |

Rules:

- `--list` must be **fast** (the engine waits at most 30 seconds) and **deterministic**: the same ids, in the same order, every time. Ids that appear at run time but were not discovered are ignored.
- `--list` must not depend on the student's code working. If the student's code is needed to know the tests, the producer has a design problem.
- `--run` ids the producer does not know are silently ignored.
- The engine **splits** the discovered ids into chunks and runs several `--run` processes **in parallel**, each with a different subset. Tests must therefore be **independent**: no shared files, no order dependency. A group that can't support this sets `[defaults] sequential = true` in `suite.toml`, which keeps a suite's groups from running at the same time (tests of one chunk still run in order).
- Extra arguments: the `script` runner passes nothing else. `command` in `suite.toml` may contain your own fixed arguments; the engine appends `--list` or `--run …` after them.
- The exit code of the producer is not a verdict. It's only used to explain a failure when no events arrived (for example, a discovery that crashed).

## 4. Lifecycle of a run

```
engine                                         producer
  │  DT_REPORT_FD=5 ./tests --list                │
  │ ────────────────────────────────────────────▶ │
  │ ◀── hello                                     │
  │ ◀── discover  a/one                           │
  │ ◀── discover  a/two                           │
  │ ◀── discover  b/one                           │   exits
  │                                               │
  │  UI shows 3 pending tests                     │
  │                                               │
  │  DT_REPORT_FD=5 ./tests --run a/one a/two     │   (and in parallel, another
  │ ────────────────────────────────────────────▶ │    process with --run b/one)
  │ ◀── hello                                     │
  │ ◀── start   a/one                             │
  │ ◀── input   a/one   "s=\"\""                  │
  │ ◀── assert  a/one   ok:false …                │
  │ ◀── end     a/one   status:"fail"             │
  │ ◀── start   a/two                             │
  │ ◀── leak    a/two   12 bytes                  │
  │ ◀── end     a/two   status:"leak"             │
  │ ◀── done                                      │   exits
```

Per test, the order is always:

```
start ─▶ (input | assert | log | leak)* ─▶ end
```

- `start` must come before any other event of that test.
- `end` must come **exactly once** and last. Don't send events for a test after its `end`: what the engine does with them is undefined.
- Tests may interleave between processes, never inside one process (a test is finished before the next one starts).
- `hello` comes first in every process; `done` may close a `--run`.

## 5. Test identifiers

- Format: **`group/name`**, e.g. `ft_strlen/empty`. The part before the last `/` is the DTP group, used by `--run GROUP`.
- Allowed characters: anything except a newline is accepted, but stick to letters, digits, `_`, `-`, `.` and one `/`. Ids appear in command lines (the **Reproduce** button) and in file names of reports.
- Unique within one producer. Two different groups of a suite (two `[[group]]` blocks, or two matrix variants) may reuse the same ids: the engine prefixes them with the group internally.
- **Stable across runs.** History, regressions ("was passing last run") and *Retest failed* match tests by id. Renaming a test loses its history.

## 6. Events

Every event is a JSON object with `"t"`. Fields marked ✓ are required. Unknown fields are ignored, so producers may add their own.

### `hello`

The first event of every process.

```json
{"t":"hello","protocol":1,"harness":"c","alloc_hooks":true}
```

| field | | type | meaning |
|---|---|---|---|
| `protocol` | ✓ | int | The DTP version spoken. The engine warns ("update the tester") when it is newer than its own. |
| `harness` | | string | Name of the producer (`c`, `python`, `my-runner`). Informational. |
| `alloc_hooks` | | bool | Sent by the C harness: `false` when malloc tracking is compiled out (sanitizer mode). Informational. |

### `discover`

One per test, only in `--list` mode.

```json
{"t":"discover","id":"ft_strlen/empty","group":"ft_strlen","name":"empty",
 "desc":"The empty string has length 0","file":"/abs/tests/ft_strlen.c","line":12}
```

| field | | type | meaning |
|---|---|---|---|
| `id` | ✓ | string | The test id (§5). |
| `name` | | string | Short display name. Default: the part of the id after the last `/`. |
| `group` | | string | The DTP group. Informational (the engine derives it from the id). |
| `desc` | | string | One sentence for the student, written as the rule being checked. |
| `file` | | string | **Absolute** path of the file defining the test. The UI then shows the test's source code. |
| `line` | | int | Line of the test in `file` (1-based). The UI extracts the test's body from there. |

### `start`

```json
{"t":"start","id":"ft_strlen/empty"}
```

The test is running. The UI switches it to *running*. Required before any other event of the test.

### `input`

```json
{"t":"input","id":"ft_strlcpy/truncates","value":"src=\"hello\", size=3"}
```

| field | | type | meaning |
|---|---|---|---|
| `id` | ✓ | string | The test. |
| `value` | ✓ | string | A description of the input under test **from now on**. |

Each `input` replaces the previous one. The engine keeps the last value and shows it with a crash or timeout ("while testing: …"), which is how the student learns which input broke their code. Send it before calling the code under test, and again whenever the input changes (once per loop iteration). An empty `value` clears it.

### `assert`

A failed check.

```json
{"t":"assert","id":"ft_substr/basic","ok":false,"msg":"ft_substr(\"hello\", 1, 3)",
 "input":"s=\"hello\", start=1, len=3","expected":"ell","actual":"el","cmp":"text",
 "file":"/abs/tests/ft_substr.c","line":20}
```

| field | | type | meaning |
|---|---|---|---|
| `id` | ✓ | string | The test. |
| `ok` | ✓ | bool | `false` for a failure. `true` asserts are allowed but ignored (don't send them: they cost pipe bandwidth). |
| `msg` | ✓ | string | What was checked: a C expression, a call, a label. It's the title of the failure card. |
| `expected` | | string | The expected value, already formatted as text. |
| `actual` | | string | The value obtained. Shown as **Got**. |
| `input` | | string | The input of *this* check. Default: the test's current `input` event value. |
| `cmp` | | string | `"text"`: `expected` and `actual` are compared texts or byte strings, and the UI explains where they differ (first different character, length difference, invisible characters, line diff). Leave it out for numbers, booleans and pointers. |
| `file` | | string | Absolute path of the failing check. |
| `line` | | int | Line of the failing check. When it is outside the test's own body (a helper function), the UI shows a few lines around it, next to the test that called it. |

- An `assert` does not end the test: send as many as you need, then `end`. A test with at least one failed assert must end with `fail` (or worse).
- The engine keeps the **first 30** failed asserts of a test, so a broken loop can't flood the UI. Stop sending after a few dozen.
- An assert with no `expected` and no `actual` is a plain failure message (`DT_FAIL`).

### `log`

```json
{"t":"log","id":"ft_split/many","msg":"first difference at word 3"}
```

| field | | type | meaning |
|---|---|---|---|
| `id` | ✓ | string | The test. `""` is accepted for messages about the whole process; they are not shown on a test. |
| `msg` | ✓ | string | Free text shown in the test's details, in order. |

### `leak`

```json
{"t":"leak","id":"ft_strdup/basic","bytes":3,"count":1}
```

| field | | type | meaning |
|---|---|---|---|
| `id` | ✓ | string | The test. |
| `bytes` | ✓ | int | Total size of the memory still allocated when the test ended. |
| `count` | ✓ | int | Number of blocks. |

Informational: the status is decided by `end`. Producers that detect leaks send `leak`, then end the test with `leak` if no assert failed (a failure is more important than a leak).

### `end`

```json
{"t":"end","id":"ft_split/null","status":"crash","ms":3,"signal":"SIGSEGV",
 "reason":"segmentation fault: invalid memory access (NULL or freed pointer, out of bounds)",
 "output":"…"}
```

| field | | type | meaning |
|---|---|---|---|
| `id` | ✓ | string | The test. |
| `status` | ✓ | string | One of the statuses of [§7](#7-statuses). An unknown value becomes `error`. |
| `ms` | | int | Duration in milliseconds. |
| `exit` | | int | Exit code of the process that ran the test, when there was one. |
| `signal` | | string | Name of the signal that killed it (`SIGSEGV`, `SIGBUS`, `SIGABRT`, `SIGFPE`, `SIGKILL`…), for `crash`. |
| `reason` | | string | **One human sentence** explaining the status: "segmentation fault: invalid memory access…", "did not finish within 5s". |
| `output` | | string | What the test printed on stdout and stderr, truncated by the producer (4 KB is plenty). Shown under the failure. |

### `done`

```json
{"t":"done"}
```

Optional. The process ran everything it was asked to. The engine doesn't need it (the closed pipe is the real end), but it makes logs easier to read.

## 7. Statuses

| status | meaning | counts as |
|---|---|---|
| `pass` | every check passed | passed |
| `fail` | at least one check failed | failed |
| `crash` | killed by a signal, an uncaught exception, or the process died during the test | failed |
| `timeout` | exceeded the per-test timeout | failed |
| `leak` | all checks passed, but memory was still allocated at the end | failed (passed when the user turned leak checks off) |
| `skip` | not run on purpose (`dt_skip`, missing prerequisite) | not counted |
| `suite_error` | a problem in the **test suite**, not in the student's code: a fixture that can't be opened, a reference that's missing (`dt_error`, `error()`) | not counted; the verdict becomes `incomplete` |
| `error` | the producer itself failed (internal problem, unknown status) | failed |
| `build_error` | the test could not be compiled or loaded against the student's code | failed |

Precedence, when several things go wrong in one test: `crash` / `timeout` > `fail` > `leak` > `pass`. A `suite_error` stops the test where it happens, so its earlier failed asserts are still shown but the status is `suite_error`: the test couldn't do its job.

**Use `suite_error` only for the suite's own problems.** It tells the student "this is not about your code" and keeps the test out of the grade, so a producer that sends it for a student's mistake hides that mistake. Engines older than this status read it as `error`.

## 8. Strings, bytes and encoding

DTP lines are JSON, so strings are Unicode. Two kinds of string are treated differently.

**Descriptive strings**: `desc`, `msg`, `reason`, `value`, `input`, `name`. Send normal UTF-8 text. The C harness can't know whether a `char *` is UTF-8, so it sends every byte ≥ 0x80 as a separate `\u00XX` escape; the engine recognises that case and decodes the bytes back as UTF-8, so `"Ã©"` displays as `é`. If they don't form valid UTF-8, they are shown as they are.

**Compared values**: `expected`, `actual`, `output`. They are **byte strings**: what matters is exactly which bytes the student's code produced. Encode every byte outside printable ASCII (`< 0x20`, `≥ 0x7f`) as `\u00XX` with XX the byte's value: `"aÿb"` means the bytes `61 FF 62`, and `"\u0000"` is a NUL byte. The engine maps each code point U+0000–U+00FF back to one byte (latin-1), so the round trip is lossless, and the UI makes the bytes visible: `\0`, `↵` for newlines, `·` for trailing spaces, `\xff`… Producers written in high-level languages may send ordinary UTF-8 text instead when they compare text, not bytes.

Size: keep each event under a few hundred KB. Truncate `output` yourself (4 KB is plenty); the UI shortens long values anyway.

## 9. What the engine does with the events

This is how the reference engine interprets the stream, so you can predict what the student sees.

1. **Discovery.** Every `discover` creates a test in the *pending* state, with its source code extracted from `file`/`line`, and a **Reproduce** command (`cd {out} && DT_… ./producer --run ID`). Tests not selected by a *Retest failed* keep their previous result and are marked as carried over.
2. **Events of unknown ids are dropped.** An id must have been discovered by the same group.
3. **`start`** sets the test to *running* and pushes it to the UI.
4. **`assert`** with `ok:false` is stored (first 30). Its `msg` and `input` are decoded as text; when `line` is outside the test's body, a few lines of `file` around `line` are attached for context.
5. **`input`** replaces the test's current input. **`log`** appends a note. **`leak`** records bytes/count.
6. **`end`** sets the final status, then the engine refines it:
   - if `output` contains an AddressSanitizer, LeakSanitizer or UBSan report, `reason` becomes its one-line summary with the location;
   - `timeout` with no `reason` gets "did not finish within Ns (infinite loop? blocking read?)";
   - `leak` becomes `pass` (with a note) when leak checks are off, for the run or for the group (`leaks = false`);
   - `fail` without any assert gets a reason: the unusual exit code (exit() called?), or "failed without an assertion message".
   - `suite_error` is kept apart: listed under *Problems in the test suite*, left out of the grade and of regressions, and re-run by *Retest failed*.
7. **The process exits.** Every test of the chunk that is still *pending* or *running* is resolved:
   - *running* (started, never ended) → `crash`, "the test process died unexpectedly", with the end of its stderr;
   - *pending* (never started) → `error`;
   - if the whole chunk exceeded its time budget → `timeout`;
   - if the user cancelled → `skip`.
8. **Scoring** uses the final statuses (see `./dt man grade`).

## 10. Timeouts, crashes and lost processes

There are two levels of protection, and a good producer uses both.

- **Per test** (the producer's job). Each test must stop after `DT_TIMEOUT` seconds and be reported as `timeout`. The C and Python harnesses fork one child per test, arm a timer (`setitimer`) in the child, and report `timeout` when it is killed by `SIGALRM`. A crash of the child (segfault, abort) becomes `crash` with the signal name, and the parent carries on with the next test. The `end` of a test may be written by the parent or by the child itself: the C harness lets the child report a `suite_error` with its reason (`dt_error`), then exit with a code (5) that tells the parent not to send another `end`. The engine doesn't care which process writes an event.
- **Per process** (the engine's job). A `--run` process gets a budget of `DT_TIMEOUT × number of tests + 10` seconds. Past that, its whole process group is killed, and its unfinished tests become `timeout`. This catches producers that don't fork.

A producer that doesn't fork (a simple shell script) still works: a crash kills the process, the engine sees a started test that never ended and reports it as `crash`. The remaining tests of that chunk become `error`, so forking per test is strongly recommended for anything that runs student code.

The engine also starts every producer in its **own process group** and kills that whole group when the user cancels, so children and grandchildren never outlive a run.

## 11. Human mode

When `DT_REPORT_FD` is unset, a person launched the producer by hand, usually by pasting the **Reproduce** command. Print readable text on stderr (or stdout) instead of JSON: one line per test with its status, and expected/actual for failures. The C harness prints:

```
    ✗ tests/ft_substr.c:20  ft_substr("hello", 1, 3)
        input:    s="hello", start=1, len=3
        expected: ell
        actual:   el
  FAIL    ft_substr/basic (0 ms)
```

`--list` and `--run` must work the same way in both modes. The C harness also supports `DT_NO_FORK=1` (run tests in-process, for `lldb`/`gdb`); a failed `DT_ASSERT`, `dt_skip` or `dt_error` still stops only the current test.

## 12. Reference implementations

The real producers are worth reading: [`deepthought/harness/c/dt_main.c`](../deepthought/harness/c/dt_main.c) (C, fork per test, byte-exact encoding) and [`deepthought/harness/python/dtharness.py`](../deepthought/harness/python/dtharness.py) (Python). Here are minimal ones.

### POSIX sh

```sh
#!/bin/sh
# run.sh — two checks on the project. Usage: run.sh --list | --run ID...
out() { [ -n "$DT_REPORT_FD" ] && printf '%s\n' "$1" >&"$DT_REPORT_FD" || printf '%s\n' "$1" >&2; }

out '{"t":"hello","protocol":1,"harness":"sh"}'
if [ "$1" = "--list" ]; then
  out '{"t":"discover","id":"basic/makefile","desc":"The project has a Makefile"}'
  out '{"t":"discover","id":"basic/readme","desc":"The project has a README.md"}'
  exit 0
fi
[ "$1" = "--run" ] && shift
[ $# -eq 0 ] && set -- basic/makefile basic/readme

for id in "$@"; do
  case "$id" in
    basic/makefile) file=Makefile ;;
    basic/readme)   file=README.md ;;
    *) continue ;;
  esac
  out "{\"t\":\"start\",\"id\":\"$id\"}"
  if [ -f "$DT_PROJECT/$file" ]; then
    out "{\"t\":\"end\",\"id\":\"$id\",\"status\":\"pass\"}"
  else
    out "{\"t\":\"assert\",\"id\":\"$id\",\"ok\":false,\"msg\":\"$file exists\",\"expected\":\"present\",\"actual\":\"missing\"}"
    out "{\"t\":\"end\",\"id\":\"$id\",\"status\":\"fail\",\"reason\":\"$file is missing\"}"
  fi
done
out '{"t":"done"}'
```

### Python, with one process per test

```python
#!/usr/bin/env python3
import json, os, subprocess, sys

TESTS = {
    "cli/no_args": ("Without arguments, prints usage and exits 1", [], "", 1),
    "cli/hello":   ("Prints its argument",                        ["hi"], "hi\n", 0),
}
fd = os.environ.get("DT_REPORT_FD")
out = os.fdopen(int(fd), "w") if fd else sys.stderr

def emit(**ev):
    out.write(json.dumps(ev) + "\n")
    out.flush()

emit(t="hello", protocol=1, harness="example")
args = sys.argv[1:]
if args[:1] == ["--list"]:
    for tid, (desc, *_ ) in TESTS.items():
        emit(t="discover", id=tid, desc=desc, file=os.path.abspath(__file__), line=4)
    sys.exit(0)
wanted = args[1:] if args[:1] == ["--run"] else list(TESTS)
timeout = float(os.environ.get("DT_TIMEOUT", "5"))
program = os.path.join(os.environ["DT_PROJECT"], "my_program")

for tid in [t for t in TESTS if t in wanted or t.split("/")[0] in wanted]:
    desc, argv, want_out, want_code = TESTS[tid]
    emit(t="start", id=tid)
    emit(t="input", id=tid, value="my_program " + " ".join(argv))
    try:
        p = subprocess.run([program, *argv], capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        emit(t="end", id=tid, status="timeout", reason=f"did not finish within {timeout}s")
        continue
    if p.returncode < 0:
        emit(t="end", id=tid, status="crash", signal=f"signal {-p.returncode}",
             reason="the program was killed by a signal")
        continue
    got = p.stdout.decode("latin-1")
    failed = False
    if got != want_out:
        emit(t="assert", id=tid, ok=False, msg="stdout", expected=want_out, actual=got, cmp="text")
        failed = True
    if p.returncode != want_code:
        emit(t="assert", id=tid, ok=False, msg="exit code", expected=str(want_code), actual=str(p.returncode))
        failed = True
    emit(t="end", id=tid, status="fail" if failed else "pass", exit=p.returncode,
         output=(p.stdout + p.stderr)[:4096].decode("latin-1"))
emit(t="done")
```

Hook either of them up with:

```toml
[[group]]
name = "Scripted"
runner = "script"
command = "run.py"         # relative to the suite folder, must be executable
```

## 13. Compliance checklist

- [ ] `hello` with `protocol: 1` is the first line of every process.
- [ ] `--list` emits every test, runs none, finishes in well under 30 s, and gives the same ids every time.
- [ ] `--run` accepts several ids and DTP groups, and ignores unknown ones.
- [ ] Every `start` is followed by exactly one `end`, with a known status.
- [ ] One event per line, written in one `write()` and flushed.
- [ ] Nothing but DTP on `DT_REPORT_FD`; the program under test keeps stdout/stderr.
- [ ] Each test enforces `DT_TIMEOUT` itself, and a crash only affects its own test (fork or subprocess).
- [ ] Failures carry `expected`/`actual` (and `cmp:"text"` for texts), and the input when it isn't obvious.
- [ ] Problems of the suite itself (missing fixture…) end with `suite_error` and a reason, never with `fail`.
- [ ] Tests are independent: they can run in any subset, in parallel processes.
- [ ] Readable output when `DT_REPORT_FD` is unset.
- [ ] `./dt suite validate path/to/suite --project path/to/a/correct/project` passes.

## 14. Versioning

- The protocol version (`hello.protocol`, currently **1**) changes only for **incompatible** changes: a renamed event, a field that changes meaning.
- New event types and new optional fields may be added at any time without changing the version. Consumers must ignore what they don't know, and producers must not rely on new fields being understood by older engines.
- A producer speaking a newer protocol than the engine still runs; the engine logs "harness speaks a newer protocol: update the tester".
- Suites declare the engine they need with `[suite] engine = ">=0.1"`. An incompatible suite is flagged instead of being run with surprises.

History of additions within version 1: `input` event; `input` and `cmp` on `assert`; `alloc_hooks` and `group` informational fields; the `suite_error` status.
