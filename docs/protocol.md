# DeepThought Test Protocol (DTP) — version 1

DTP is the contract between the engine and anything that runs tests: the C harness, the Python harness, and your own `script` runners. Implement it and DeepThought can test any language.

## Transport

- The engine starts the test process with the environment variable **`DT_REPORT_FD`** set to the number of an open, writable file descriptor (a pipe).
- The process writes **one JSON object per line** (UTF-8) to that descriptor. Its stdout/stderr are free for the program under test.
- Lines that are not valid DTP JSON are ignored, so you can't corrupt a run by accident.
- When `DT_REPORT_FD` is unset (a human running the command), print readable text instead. That's what the “Reproduce” commands rely on.

Other environment variables given to test processes:

| variable | meaning |
|---|---|
| `DT_PROJECT` | isolated copy of the student's project |
| `DT_SUITE` | the suite folder |
| `DT_FIXTURES` | the fixtures folder |
| `DT_TIMEOUT` | per-test timeout, seconds (float) |
| `DT_MATRIX_<NAME>` | current matrix value(s) |

## Invocation

| arguments | expected behaviour |
|---|---|
| `--list` | emit `hello`, then one `discover` per test, then exit |
| `--run ID [ID…]` | run only those tests (an ID may also be a group prefix) |
| *(none)* | run every test |

The engine runs `--list` first (so the UI can show every test as *pending*), then runs subsets with `--run`, possibly in several processes in parallel. Tests must therefore be independent.

## Events

Every event has `"t"` (type). Test events carry `"id"`, a stable string `group/name`.

```json
{"t":"hello","protocol":1,"harness":"c"}
{"t":"discover","id":"ft_strlen/basic","name":"basic","desc":"Length of a regular string","file":"/abs/tests/ft_strlen.c","line":3}
{"t":"start","id":"ft_strlen/basic"}
{"t":"assert","id":"ft_strlen/basic","ok":false,"msg":"ft_strlen(\"\")","expected":"0","actual":"1","file":"/abs/tests/ft_strlen.c","line":9}
{"t":"log","id":"ft_strlen/basic","msg":"any note for the student"}
{"t":"leak","id":"ft_strlen/basic","bytes":12,"count":1}
{"t":"end","id":"ft_strlen/basic","status":"fail","ms":2,"exit":1,"signal":"SIGSEGV","reason":"…","output":"…"}
{"t":"done"}
```

| type | fields | notes |
|---|---|---|
| `hello` | `protocol` (int), `harness` | first line. A newer protocol than the engine knows produces a warning. |
| `discover` | `id`, `name`, `desc`, `file`, `line` | `file`/`line` let the UI show the test's source code. |
| `start` | `id` | the test is running |
| `assert` | `id`, `ok`, `msg`, `expected`, `actual`, `file`, `line` | send failed checks (`ok:false`); passing ones may be omitted. |
| `log` | `id`, `msg` | free text shown with the test |
| `leak` | `id`, `bytes`, `count` | memory still allocated at the end |
| `end` | `id`, `status`, `ms`, optional `exit`, `signal`, `reason`, `output` | **required** for every started test |
| `done` | | optional, end of the run |

`status` is one of: `pass`, `fail`, `crash`, `timeout`, `leak`, `skip`, `error`, `build_error`.

- `reason`: one human sentence (“segmentation fault: invalid memory access…”).
- `output`: what the test printed (truncated by you; ~4 KB is plenty).
- A test that was started but never ended (the process died) is reported by the engine as `crash`. One that never started is reported as `error`.

### Bytes in strings

`expected`, `actual` and `output` may contain arbitrary bytes. The C harness encodes every byte outside printable ASCII as `\u00XX`, so `"aÿb"` means the bytes `61 FF 62`, and the UI shows such characters visibly (`\xff`, `↵`, `·`…). Other producers may send normal UTF-8 text.

## Minimal implementation (sh)

```sh
out() { printf '%s\n' "$1" >&"$DT_REPORT_FD"; }
out '{"t":"hello","protocol":1}'
if [ "$1" = "--list" ]; then
  out '{"t":"discover","id":"basic/has_makefile","desc":"The project has a Makefile"}'
  exit 0
fi
out '{"t":"start","id":"basic/has_makefile"}'
if [ -f "$DT_PROJECT/Makefile" ]; then
  out '{"t":"end","id":"basic/has_makefile","status":"pass"}'
else
  out '{"t":"assert","id":"basic/has_makefile","ok":false,"msg":"Makefile","expected":"present","actual":"missing"}'
  out '{"t":"end","id":"basic/has_makefile","status":"fail"}'
fi
```

## Versioning

The protocol version only changes for incompatible changes. New optional fields may be added at any time, and consumers must ignore unknown fields.
