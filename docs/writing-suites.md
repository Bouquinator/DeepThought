# Writing test suites

This guide explains how to write a suite that plugs into DeepThought. Anyone can write one: for your own project, for a project that has no tester yet, or to share with your cohort.

- [1. Five-minute tutorial](#1-five-minute-tutorial)
- [2. How a suite is used](#2-how-a-suite-is-used)
- [3. `suite.toml` reference](#3-suitetoml-reference)
- [4. Writing C tests (`c-unit`)](#4-writing-c-tests-c-unit)
- [5. Testing programs (`exec`)](#5-testing-programs-exec)
- [6. Writing Python tests (`python-unit`)](#6-writing-python-tests-python-unit)
- [7. Any language (`script`)](#7-any-language-script)
- [8. Testing your suite](#8-testing-your-suite)
- [9. Sharing your suite](#9-sharing-your-suite)
- [10. Checklist and good practices](#10-checklist-and-good-practices)
- [11. Troubleshooting](#11-troubleshooting)

Real-world examples to read alongside this guide: the official [`suites/get_next_line`](../suites/get_next_line) (C, matrix, fixtures), the [examples](../examples/suites) (Python, exec), and [`community/sstyle`](../community/sstyle) (an existing tester wrapped without changing its tests).

---

## 1. Five-minute tutorial

Say you want extra tests for **libft**.

```sh
./dt suite new my-libft --project libft          # scaffold ~/.deepthought/suites/local/my-libft
```

You get:

```
my-libft/
├── suite.toml        what the suite tests and how
├── tests/
│   └── example.c     example tests (compile and pass out of the box)
└── fixtures/         data files your tests can read (optional)
```

Edit `suite.toml`:

```toml
[suite]
id = "my-libft"
name = "My libft tests"
version = "0.1.0"
project = "libft"              # same type as the other libft suites: they run together
authors = ["your-login"]

[detect]
any_files = ["libft.h", "*/libft.h"]
makefile_name = "libft.a"

[build]
command = "make -C {project}"
artifacts = ["libft.a"]

[[group]]
name = "Edge cases"
runner = "c-unit"
split = true
sources = ["tests/*.c"]
include = ["{project}"]
link = ["{project}/libft.a"]
```

Replace `tests/example.c` with `tests/ft_strlen.c`:

```c
#include "dt.h"
#include "libft.h"
#include <string.h>

DT_TEST(ft_strlen, empty, "The empty string has length 0")
{
	DT_EXPECT_EQ_SIZE(ft_strlen(""), 0);
}

DT_TEST(ft_strlen, like_libc, "Same result as strlen on a long string")
{
	char	buf[1000];

	memset(buf, 'a', 999);
	buf[999] = 0;
	DT_EXPECT_EQ_SIZE(ft_strlen(buf), strlen(buf));
}
```

Run it:

```sh
./dt run ~/libft                      # every enabled libft suite runs, yours included
./dt run ~/libft --suite my-libft     # only yours
./dt suite validate ~/.deepthought/suites/local/my-libft --project ~/libft
```

Or open the web UI (`./dt`): the suite shows up in **Suites** and in every libft run. You never reinstall anything: edit a test, then click **Retest**.

---

## 2. How a suite is used

Understanding the pipeline makes everything else obvious:

```
your project ──copy──▶ isolated workspace ──[build] command──▶ artifacts (libft.a…)
                                   │
                                   ├── checks: rules, relink, norminette, forbidden, files
                                   │
                                   └── for every [[group]] (× every matrix value):
                                         runner prepares (c-unit compiles your tests + harness)
                                         runner discovers the tests (--list)
                                         runner runs them (in parallel, each test in its own process)
                                         results stream to the UI as DTP events
```

- The student's folder is **never modified**. Everything happens in a copy (`/tmp/dt-$USER/ws/…` or goinfre), so `{project}` always points to that copy.
- A suite is **matched to a project** through `[suite].project` and `[detect]`. When the user runs a folder, DeepThought finds the best-matching project kind and runs **every enabled suite of that kind**. Your suite therefore runs next to the other suites of that type.
- **Users can also attach any suite to any project themselves** (`./dt project link PATH SUITE`, `--link PATH`, or ☰ Suites in the UI), and give their own projects a type. A suite without `[detect]` only runs where it is linked, which suits personal or very specific suites.
- Each test gets a **status**: `pass`, `fail` (an expectation failed), `crash` (signal: segfault, abort…), `timeout`, `leak` (memory still allocated at the end), `build_error` (your test file did not compile against their code), `skip` or `error` (harness problem).
- **Grade**: like the moulinette. The mandatory pass rate gives 0–100, and bonus tests add up to +25, but only when mandatory is at 100%.

---

## 3. `suite.toml` reference

### `[suite]` (required)

| key | required | meaning |
|---|---|---|
| `id` | ✓ | Unique identifier: letters, digits, `.`, `_`, `-`. Used on the command line (`--suite id`). |
| `name` | ✓ | Display name. |
| `project` | ✓ | The project kind (`libft`, `get_next_line`, `ft_printf`, `push_swap`, `minishell`, …). Suites with the same `project` run together. Reuse the existing names when they exist (`libft`, `ft_printf`, `get_next_line`…); any name works for other projects. |
| `version` | | Your suite's version (`"1.2.0"`). Shown in the UI; used when re-importing zips. |
| `engine` | | Required DeepThought version range, e.g. `">=0.1"`, `">=0.1,<1.0"`. Incompatible suites are flagged, not run. |
| `authors` | | List of logins/names. |
| `description` | | One sentence, shown in the Suites page. |
| `homepage` | | Link to your repository. |

### `[detect]`: recognising a project folder

All conditions given must hold. The more specific the match, the higher the score, and the best-scoring project kind wins.

| key | meaning |
|---|---|
| `files` | All of these must exist (glob patterns allowed: `"src/*.c"`). Exact names score higher than globs. |
| `any_files` | At least one must exist (e.g. a header at the root *or* in `includes/`). |
| `makefile_name` | The Makefile's `NAME =` must be exactly this (strongest signal: +3). |

Without `[detect]` the suite never auto-runs; users can still pick it explicitly (`--suite id`, or the buttons on an unrecognised project).

### `[build]`: building the project

| key | meaning |
|---|---|
| `command` | Shell-like command run in the workspace, e.g. `"make -C {project}"`. Omit it when your tests compile the sources themselves (get_next_line does this). If it fails, every group of the suite is marked `build_error` and the grade is 0. |
| `artifacts` | Files the build must produce (relative to the project), e.g. `["libft.a"]`. Used by `relink` and `forbidden`. |
| `checks` | Project-level checks to run: `files`, `rules`, `relink`, `norminette`, `forbidden`. |
| `rules` | Makefile rules the `rules` check requires. Default: `["all", "clean", "fclean", "re", "$(NAME)"]`. |
| `clean` | Command used by “Clean build” (default `make fclean`). |
| `syntax_check` | `"python"`: when there is no `command`, parse every `.py` file of the project first (a syntax error fails the build with file:line). This is the default for suites with a `python-unit` group; set `"none"` to disable it. |
| `timeout` | Build timeout in seconds (default 300). |

Users can override the build per project (**⚙ Build** in the UI, `--build-cmd` / `--make-args` / `--env` on the command line): a replacement command, extra make arguments (`bonus`, `CFLAGS=-O2`) and environment variables. Your suite doesn't need to handle these, but don't hard-code assumptions that break when someone adds a make target. The make *variables* they set are also added to your `before` make commands.

In **Sanitizer mode** a `make` build gets `CFLAGS="-Wall -Wextra -Werror -g -fsanitize=address,undefined"` appended, so the student's own code is instrumented too.

### The checks

| check | configuration | what it does |
|---|---|---|
| `files` | `[files] required = ["Makefile", "**/libft.h"]` | Each pattern must match a file. |
| `rules` | `[build] rules = [...]` | The Makefile defines those rules (and uses -Wall -Wextra -Werror: a warning otherwise). |
| `relink` | `[build] artifacts` | Runs the build twice. The second run must not rebuild anything. Also checks `make bonus` when that rule exists. |
| `norminette` | `[norminette] paths = ["."]` | Runs `norminette` if installed, and lists errors with file:line. |
| `forbidden` | `[forbidden] allowed = ["malloc", "free", "write"]`, optional `allowed_regex`, `sources`, `cflags`, `artifacts` | Lists the external functions used by the artifacts (`nm`). Anything not allowed fails. Toolchain symbols are ignored, and `memset`/`memcpy` emitted by the compiler only give a warning. With `sources = ["get_next_line*.c"]` the files are compiled to objects first (for projects without a Makefile). |

### `[defaults]`

| key | meaning |
|---|---|
| `timeout` | Per-test timeout in seconds (default from the user's settings, 5). |
| `leaks` | `false` disables leak failures for the whole suite. |
| `cflags` | Extra flags for every c-unit compilation, e.g. `["-Wno-format"]`. |
| `fixtures` | Fixtures folder (default `fixtures`). |

### `[[group]]`: one block of tests

A suite has one or more groups. Each group appears as a folder in the test tree.

| key | runners | meaning |
|---|---|---|
| `name` | all | **Required**, unique within the suite. |
| `description` | all | Shown in the UI. |
| `category` | all | `mandatory` (default), `bonus` or `extra` (extra does not count in the grade). |
| `runner` | all | `c-unit` (default), `exec`, `python-unit`, `script`. |
| `when` | all | Run only if: `files = [...]` (all exist), `any_files = [...]`, `make_rule = "bonus"`. Otherwise the group is **skipped** (not failed): perfect for bonus parts. |
| `before` | all | Commands run in the project before this group, e.g. `["make -C {project} bonus"]`. Each distinct command runs once per run. If one fails, the group is a build error. |
| `matrix` | all | `{ BUFFER_SIZE = [1, 42, 10000000] }`: the group runs once per value (or combination of values). Use `{matrix.BUFFER_SIZE}` in other keys. |
| `timeout` | all | Per-test timeout for this group. |
| `leaks` | all | `false`: leaks do not fail tests of this group. |
| `env` | all | Extra environment variables for the test processes. |
| `fixtures` | all | Fixtures folder for this group. |
| `sources` | c-unit | Globs of C files to compile. Relative paths are relative to the suite. May include project files: `"{project}/get_next_line.c"`. |
| `include` | c-unit | `-I` folders. `{project}` automatically adds every project sub-folder containing headers (`includes/`, `inc/`…). |
| `link` | c-unit | Libraries / objects to link (`"{project}/libft.a"`). |
| `cflags`, `ldflags` | c-unit | Extra compiler / linker flags (`["-D", "BUFFER_SIZE={matrix.BUFFER_SIZE}"]`). |
| `split` | c-unit | `true`: each test file of the suite becomes its own binary. A file that does not compile (missing function, wrong prototype) then only breaks *its* tests (shown as `<file>/compile`), not the whole group. Recommended for libraries. |
| `cases` | exec | TOML file with the `[[case]]` list. |
| `tests` | python-unit | Globs of Python test files. |
| `command` | script | Executable (relative to the suite or absolute) speaking DTP. |

### `[[fetch]]`: test sources from another repository

A suite can depend on a git repository, for example an existing tester whose tests you reuse. It is downloaded before the first run (stage *Test sources*), pinned to `ref`:

```toml
[[fetch]]
name = "codetester"                                   # → {fetch.codetester}
git = "https://github.com/SStyles93/42_CodeTester.git"
ref = "473a2dc997f68a4047ca36f073c1f84097e5471b"      # a commit (pinned) or a branch/tag
into = "../upstream"                                  # inside the suite folder or its parent (shared)
```

With a commit `ref`, the network is used only once. With a branch, the checkout is refreshed by `./dt suite update ID`. If the download fails (offline), the suite's groups are reported as build errors with that reason, and other suites still run.

### Platform-specific settings

Any group can add settings for one platform, appended to the common ones:

```toml
[[group]]
name = "Libft"
ldflags = ["-lm"]
[group.darwin]                       # macOS
ldflags = ["-Wl,-all_load", "{project}/libft.a"]
[group.linux]
cflags = ["-DMEMCHECK_WRAP"]
ldflags = ["-Wl,--whole-archive", "{project}/libft.a", "-Wl,--no-whole-archive"]
```

Accepted keys: `sources`, `include`, `link`, `cflags`, `ldflags`, `env`.

### Other `[defaults]`

| key | meaning |
|---|---|
| `sequential` | `true`: the suite's groups run one after another instead of in parallel (when tests run `make` in the project, for example). |

### Placeholders

Usable in commands, paths and flags:

| placeholder | value |
|---|---|
| `{project}` | the isolated copy of the student's project (same as `{build}`) |
| `{suite}` | your suite's folder |
| `{fixtures}` | `{suite}/fixtures` |
| `{out}` | the group's working folder (where test binaries live and run) |
| `{harness}` | DeepThought's C harness folder (`dt.h`) |
| `{cc}` | the configured C compiler |
| `{matrix.NAME}` | the current matrix value |
| `{fetch.NAME}` | absolute path of a `[[fetch]]` dependency |

---

## 4. Writing C tests (`c-unit`)

Your test files are compiled together with the DeepThought harness ([`deepthought/harness/c`](../deepthought/harness/c)), linked against the student's code, and executed. You never write a `main()`.

### Anatomy of a test

```c
#include "dt.h"          // always first
#include "libft.h"       // the student's header (found through `include`)

DT_TEST(ft_substr, start_too_big, "start beyond the end gives an empty string")
{
	char	*r = ft_substr("lorem", 10, 3);

	DT_ASSERT_NOT_NULL(r);          // stops the test here if NULL
	DT_EXPECT_EQ_STR(r, "");        // records a failure, continues
	free(r);                        // free what you get: leaks are detected!
}
```

- `DT_TEST(group, name, "description")`: `group/name` is the test's id (shown in the tree and used by `--run`). Both must be valid C identifiers. The description is what the student reads, so write it as the rule being checked ("Returns NULL when malloc fails").
- Every test runs in its **own forked process** with a timer. A segfault, an abort or an infinite loop is reported for that test only, and the remaining tests keep running.
- `EXPECT_*` records the failure and continues. `ASSERT_*` stops the test (use it before dereferencing a pointer).

### Checks

| macro | passes when | shows |
|---|---|---|
| `DT_EXPECT(cond)` / `DT_ASSERT(cond)` | `cond` is true | the expression |
| `DT_EXPECT_EQ_INT(actual, expected)` | equal as `long long` | both numbers |
| `DT_EXPECT_EQ_SIZE(a, e)` | equal as `unsigned long long` | |
| `DT_EXPECT_EQ_PTR(a, e)` | same pointer | addresses |
| `DT_EXPECT_EQ_STR(a, e)` | same string (NULL-safe: both NULL is equal) | diff of the strings |
| `DT_EXPECT_EQ_MEM(a, e, n)` | same `n` bytes | byte diff |
| `DT_EXPECT_SAME_SIGN(a, e)` | same sign (`<0`, `0`, `>0`): for `strcmp`-like results | values and signs |
| `DT_EXPECT_NULL(p)` / `DT_EXPECT_NOT_NULL(p)` | | |
| `DT_EXPECT_ALLOC_SIZE(p, n)` | `p` was allocated with exactly `n` bytes (skipped in sanitizer mode) | |
| `DT_COMPARE_OUTPUT(ft_call, ref_call)` | both calls write the same bytes on stdout **and** return the same value | output diff + return values |
| `DT_FAIL("message")` | never: explicit failure | |

All `DT_ASSERT_*` variants exist for the `EQ_*` macros. Every check returns 1 if it passed, so you can write `if (!DT_EXPECT_EQ_STR(...)) return ;`.

Lower-level functions, handy in helpers: `dt_check_bytes(actual, alen, expected, elen, fatal, "label", __FILE__, __LINE__)` compares two byte buffers (used for captured output), and `dt_check_int(...)`, `dt_check_str(...)` and others are the functions behind the macros.

> **Helpers report the right line.** When a check fails inside a helper (`static void check(...)`), the UI shows the helper's code around the failing line *and* the test that called it. Helpers are the best way to write many similar cases. See `tests/fixtures/engine-suite/tests/part1/ft_strlcpy.c`.

### Comparing with the real function

The most convincing test compares the student's function with libc on the same input:

```c
static void	check(const char *s, int c)
{
	DT_EXPECT_EQ_PTR(ft_strchr(s, c), strchr(s, c));
}

DT_TEST(ft_strchr, int_conversion, "c is converted to char: 'H' + 256 finds 'H'")
{
	check("Hello", 'H' + 256);
}
```

When the reference is not portable (`strlcpy` is not in every libc), ship your own reference in a header next to the tests (see `tests/fixtures/engine-suite/tests/libft_test.h`) and add `"tests"` to `include`.

### Output (`write`, `printf`, `ft_putstr_fd`…)

```c
t_dt_capture	out;

DT_CAPTURE_STDOUT(out, ft_putendl_fd("hello", 1));
dt_check_bytes(out.data, out.len, "hello\n", 6, 0, "output", __FILE__, __LINE__);
dt_capture_free(&out);

DT_CAPTURE_FD(2, out, ft_putstr_fd("err", 2));   // any fd
```

`DT_COMPARE_OUTPUT(ft_printf("%5d|", 42), printf("%5d|", 42));` does all of that for you: captures both, compares bytes and return values, and flushes `printf`'s buffer. This is how the whole ft_printf suite is written.

Invisible characters (`\n`, `\0`, trailing spaces, tabs, bytes ≥ 0x80) are made visible in the UI diff, so you can compare raw bytes without worrying about how they display.

### malloc failures and leaks

DeepThought replaces `malloc`/`free` inside the test binary (no valgrind needed, works on macOS and Linux):

```c
DT_TEST(ft_split, malloc_fail_middle, "A malloc fails midway: returns NULL and frees everything")
{
	dt_malloc_fail_at(3);                 // the 3rd malloc from now returns NULL
	DT_EXPECT_NULL(ft_split("a b c d", ' '));
}                                         // anything still allocated now = LEAK status
```

| function | effect |
|---|---|
| `dt_malloc_fail_at(n)` | the n-th allocation (counted from now) returns NULL |
| `dt_malloc_fail_all()` | every allocation returns NULL |
| `dt_malloc_reset()` | back to normal |
| `dt_malloc_calls()` | allocations made since the last reset |
| `dt_leaks_ignore()` | don't report leaks for this test (e.g. get_next_line's static buffer when you stop before EOF) |
| `dt_alloc_size(p)` | size of a tracked allocation (prefer `DT_EXPECT_ALLOC_SIZE`) |

Only allocations made by code in the test binary (the student's code and yours) are tracked. libc's internal allocations (`printf` buffers, `fopen`…) are ignored. **Free everything your test allocates**, including results returned by the student's functions, otherwise the test is reported as leaking. If you need memory that should never be tracked, use `dt_raw_malloc` / `dt_raw_free`.

In **sanitizer mode** (a toggle in the UI, or `--sanitize`), the hooks are disabled and tests using `dt_malloc_fail_*` are skipped. In exchange, AddressSanitizer and UBSan report the exact faulty line in the student's code.

### Fixtures, files and stdin

Put data files in `fixtures/` and get their absolute path with `dt_fixture("name.txt")`:

```c
int	fd = open(dt_fixture("multi.txt"), O_RDONLY);

dup2(fd, 0);              // make it stdin: each test is its own process, so this is safe
```

Tests run in a scratch folder (`{out}`), so they may create files freely.

### Notes and skipping

- `dt_note("first difference at c = %d", c)` adds a line to the test's details.
- `dt_skip("needs a terminal")` marks the test as skipped and stops it.

### A matrix: get_next_line

```toml
[[group]]
name = "Mandatory"
runner = "c-unit"
matrix = { BUFFER_SIZE = [1, 42, 9999, 10000000] }
cflags = ["-D", "BUFFER_SIZE={matrix.BUFFER_SIZE}"]
sources = ["{project}/get_next_line.c", "{project}/get_next_line_utils.c", "tests/mandatory/*.c"]
include = ["{project}", "tests"]
```

The group is compiled and run 4 times, and appears 4 times in the tree (`Mandatory [BUFFER_SIZE=1]`, …). Inside the tests, the value is the `BUFFER_SIZE` macro (and `$DT_MATRIX_BUFFER_SIZE` in the environment).

### Bonus parts

```toml
[[group]]
name = "Bonus — linked lists"
category = "bonus"
when = { make_rule = "bonus" }            # no bonus rule → skipped, not failed
before = ["make -C {project} bonus"]
split = true
sources = ["tests/bonus/*.c"]
include = ["{project}"]
link = ["{project}/libft.a"]
```

### Running one test by hand

Every test in the UI has a **Reproduce** command such as:

```sh
cd /tmp/dt-you/ws/…/out/libft/part-1-libc-functions && DT_FIXTURES=… ./dt_ft_strlcpy --run ft_strlcpy/truncates
```

Without `DT_REPORT_FD` the binary prints readable results. `./dt_ft_strlcpy --list` lists its tests. `DT_NO_FORK=1` runs tests in-process, so you can use `lldb`/`gdb`:

```sh
DT_NO_FORK=1 lldb ./dt_ft_strlcpy -- --run ft_strlcpy/truncates
```

---

## 5. Testing programs (`exec`)

For projects that produce an executable (push_swap, pipex, so_long's parser, minishell, any language), describe cases in TOML. No code needed.

```toml
# suite.toml
[[group]]
name = "Error handling"
runner = "exec"
cases = "cases/errors.toml"
```

```toml
# cases/errors.toml — one [[case]] per test
[[case]]
name = "duplicate numbers"
desc = "push_swap prints Error on stderr for duplicates"
cmd = ["{project}/push_swap", "1", "2", "1"]
[case.expect]
stderr = "Error\n"
stdout = ""
exit = "nonzero"

[[case]]
name = "same output as bash"
cmd = "{project}/pipex infile 'ls -l' 'wc -l' outfile && cat outfile"
reference = "< infile ls -l | wc -l"
shell = true
compare = ["stdout"]

[[case]]
name = "sorts 5 numbers"
cmd = ["{project}/push_swap", "3", "2", "5", "1", "4"]
check = "{suite}/check_sorted.sh 3 2 5 1 4"     # receives the program's stdout on stdin
```

| key | meaning |
|---|---|
| `name` | **required**, unique; the test id is derived from it |
| `id` | explicit id (optional) |
| `desc` | description shown in the UI |
| `cmd` | list (no shell: safest) or string (split like a shell). With `shell = true` the string runs through `/bin/sh -c` (pipes, redirections). |
| `stdin` / `stdin_file` | input text / file (relative to the suite) |
| `timeout` | seconds |
| `env` | extra environment variables |
| `expect.stdout` / `expect.stderr` | exact match |
| `expect.stdout_contains` / `stderr_contains` | string or list of strings that must appear |
| `expect.stdout_regex` / `stderr_regex` | Python regex (multiline) |
| `expect.exit` | exact code, or `"nonzero"` |
| `reference` | command whose output is the expected one (same stdin/env) |
| `compare` | what to compare with the reference: `stdout`, `stderr`, `exit` (default `["stdout", "exit"]`) |
| `check` | command that receives the program's stdout on stdin; exit 0 means success (great for push_swap checkers) |

Crashes (signals) and timeouts are detected automatically. A complete example lives in [`examples/suites/mini-echo`](../examples/suites/mini-echo).

---

## 6. Writing Python tests (`python-unit`)

```toml
[[group]]
name = "ex00"
runner = "python-unit"
tests = ["tests/test_*.py"]
```

```python
from dtharness import test, expect, expect_eq, expect_raises, expect_output, capture_stdout, fixture

import calc            # the student's module: their project folder is on sys.path


@test("mean() of an empty list raises ValueError")
def mean_empty():
    expect_raises(ValueError, calc.mean, [])


@test("shout() prints in upper case")
def shout():
    expect_output(calc.shout, "HELLO!\n", "hello")
```

| function | meaning |
|---|---|
| `@test("description")` | registers a test (id `file_stem/function_name`); `@test(timeout=10)` changes the timeout |
| `expect(cond, msg)` / `require(cond, msg)` | `require*` stops the test |
| `expect_eq(actual, expected, msg=None)` / `require_eq` | equality |
| `expect_ne`, `expect_close(a, b, tol)`, `expect_type(v, T)` | |
| `expect_raises(Exc, fn, *args)` | `fn(*args)` must raise `Exc` |
| `expect_output(fn, expected, *args)` | what `fn(*args)` prints |
| `capture_stdout()` | `with capture_stdout() as out: …` then `out.text` |
| `fixture("name")`, `note(msg)`, `skip(reason)`, `fail(msg)` | |

Each test runs in its own forked process. Uncaught exceptions are reported as `crash` with the exception and the line, infinite loops as `timeout`, and `sys.exit()` as a failure. If the student's module does not even import (syntax error), the file shows a `build_error` test containing the traceback. Example: [`examples/suites/py-calc`](../examples/suites/py-calc).

---

## 7. Any language (`script`)

If none of the above fits, write your own runner in any language. It only has to speak the **DeepThought Test Protocol** ([protocol.md](protocol.md)):

```toml
[[group]]
name = "Scripted tests"
runner = "script"
command = "run.sh"          # relative to the suite folder
```

- `run.sh --list` prints a `discover` event per test.
- `run.sh --run ID...` runs those tests and prints `start`, `assert`, `end`.
- Events are JSON lines written to the file descriptor number in `$DT_REPORT_FD`. `$DT_PROJECT` is the project copy, `$DT_FIXTURES` your fixtures, `$DT_TIMEOUT` the per-test timeout.

`./dt suite new my-suite --runner script` generates a working example written in plain `sh`.

---

## 7b. Wrapping an existing tester

Many 42 testers already exist. You can bring one into DeepThought **without modifying its tests**:

1. `[[fetch]]` its repository, pinned to a commit.
2. Compile its test files with a small adapter instead of its `main()`. The adapter registers each of its tests with `dt_register()` and turns its report into DeepThought checks (`dt_check`, `dt_check_bytes`, `dt_note`).
3. Reproduce its build flags (per platform if needed) in the groups.

[`community/sstyle`](../community/sstyle) does exactly this for SStyles93's CodeTester (one ~430-line adapter, none of their files changed). For testers that are programs, the `script` runner is even simpler: a script that runs the tester and prints DTP events.

## 8. Testing your suite

1. **Validate the manifest**: errors name the exact key.
   ```sh
   ./dt suite validate path/to/my-suite
   ```
2. **Run it against a correct project**: everything must pass. A test that fails on a correct implementation is a bug in the test (it happens, even to well-tested suites).
   ```sh
   ./dt suite validate path/to/my-suite --project ~/a-correct-libft
   ```
3. **Run it against broken projects**: break one thing at a time (wrong return value, missing NULL check, infinite loop, leak) and check that the right test catches it with a clear message.
4. **Run in sanitizer mode** (`--sanitize`): tests must not depend on undefined behaviour.
5. Try **`BUFFER_SIZE=1` and huge values**, empty inputs, `NULL`… whatever the evaluators try.

DeepThought tests its own suites this way: see `tests/fixtures/` (reference and broken projects) and `tests/test_e2e.py`.

---

## 9. Sharing your suite

A suite is just a folder, so any of these work:

| how | the user runs | updates |
|---|---|---|
| **Git repository** (suite.toml at the root) | `./dt suite add https://github.com/you/libft-extra-tests.git` (or the Suites page) | `./dt suite update` / Update button |
| **Zip file** | `./dt suite add libft-extra-tests-1.0.0.zip` or drag & drop in the UI | re-import a newer version |
| **Folder** | `./dt suite add /path/to/folder` | edits are live |

`./dt suite pack my-suite` (or **Export .zip** in the UI) creates the zip.

To appear in **Suites › Discover**, open a pull request adding your repository to [`index.json`](../index.json):

```json
{ "name": "Libft extra edge cases", "project": "libft", "url": "https://github.com/you/libft-extra-tests.git",
  "author": "you", "description": "Tricky inputs for ft_split, ft_itoa and ft_strtrim." }
```

Users see a **trust warning** before adding a suite, because a suite contains code that is compiled and run on their machine. Keep yours readable.

---

## 10. Checklist and good practices

- [ ] `id` is unique and stable (renaming it loses users' history matching).
- [ ] `project` uses the usual name when one exists (`libft`…), so your suite runs next to the others.
- [ ] Every test has a **description written as the rule** ("Returns NULL when malloc fails"), not as the input.
- [ ] One behaviour per test: a failing test should tell the student *what* is wrong without reading the code.
- [ ] Prefer comparing with the real function over hard-coded values.
- [ ] Free everything (or call `dt_leaks_ignore()` with a comment explaining why).
- [ ] Bonus groups use `category = "bonus"` and a `when` condition.
- [ ] Libraries use `split = true`.
- [ ] No reliance on undefined behaviour (passes in sanitizer mode on a correct project).
- [ ] Platform differences (e.g. `printf("%p", NULL)` is `0x0` on macOS and `(nil)` on Linux): compare with the system's function instead of hard-coding.
- [ ] Bump `version` when you change tests; set `engine` when you use a newer feature.

---

## 11. Troubleshooting

| symptom | cause / fix |
|---|---|
| "no installed suite recognises …" | `[detect]` doesn't match. Check `files`/`makefile_name`, or run with `--suite your-id`. |
| My suite is not in the list | `./dt suite list` shows suites with errors and why. In the UI: Suites › "Suites with errors". |
| Every test is `build_error` | Open the group (click its name): the compile command and log are there. Usually a header path (`include`) or a missing library in `link`. |
| `<file>/compile` build error (split mode) | That test file uses a function the project doesn't have, or a wrong prototype. Expected for unfinished projects. |
| A test leaks but the code is correct | You forgot to free something in the test, or the project legitimately keeps memory (gnl static buffer): `dt_leaks_ignore()`. |
| Output comparison fails with "identical" text | Check the diff for `↵`, `·` (trailing space), `\0`: the UI shows invisible characters. |
| `printf` output missing in a capture | Use `DT_CAPTURE_*`/`DT_COMPARE_OUTPUT`: they flush stdio buffers. |
| Timeout on a big BUFFER_SIZE | Raise `timeout` for that group. |
| Works by hand, fails in DeepThought | Tests run in `{out}`, not the project folder: use `{project}`, `dt_fixture()` or `$DT_PROJECT`. |
