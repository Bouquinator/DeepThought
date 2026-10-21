# DeepThought — a tester for 42 projects

> *“The answer to the ultimate question of life, the universe and everything is… 42.”* DeepThought computes whether your project deserves it.

One tester for every 42 project. It compiles your project in an isolated folder, runs every matching test suite and **explains each failure**: a diff with visible invisible characters, the test's code, the exact crash reason, leaks, and the command to reproduce it. Use it in your browser, your terminal, or CI.

- **Zero install**: Python 3.10+ standard library only, no pip, no npm, no sudo. Clone and run.
- **Browser UI** with live results, watch mode (re-runs on save), re-test failed only, history and regressions. A **terminal UI** and a **CI reporter** are included.
- **Any number of suites, for any project** — even projects DeepThought doesn't know: bundled ones, your own, your friends' (git URL, zip or folder), linked to the projects you choose.
- **Writing tests is easy**: a `suite.toml` plus test files in C, Python, declarative command cases, or any language through a tiny protocol.
- **Serious C testing**: one process per test (crashes and infinite loops are isolated), leak detection and **malloc-failure injection without valgrind**, output capture, a `BUFFER_SIZE` matrix, sanitizer mode (ASan/UBSan pinpoints the faulty line), norminette, forbidden functions (`nm`), Makefile rules and relink checks.
- **Self-updating**: every launch pulls the latest version automatically (skipped offline or if you edited the tester), and `./dt update` / one click does it on demand.

## Quick start

```sh
git clone <this repository> ~/deepthought
cd ~/deepthought
./dt                      # opens the web UI; add your project folder and press Run
```

In the terminal:

```sh
./dt run ~/libft          # build + test, readable report, exit code 0/1
./dt run ~/libft -w       # watch mode: re-run every time you save
./dt run ~/libft -f       # re-run only what failed last time
./dt tui ~/libft          # interactive terminal UI
./dt run . --junit report.xml --json result.json     # CI
```

Tip: `alias dt=~/deepthought/dt` in your shell rc.

## How your project is built

Every **Test** / **Retest** (including *Retest failed* and watch-mode runs) first syncs your folder into an isolated copy, then builds it there:

- **C projects**: the suite's build command, usually `make -C <project>` (incremental, so a retest after a small edit is fast). Suites add their own steps when needed, like `make bonus` before the bonus tests. Projects without a Makefile (get_next_line) are compiled by the tests themselves, once per `BUFFER_SIZE`.
- **Python projects**: every `.py` file is syntax-checked first (`calc.py:27: invalid syntax` stops the run with a clear message). Then the tests import your modules.
- **Your own build options** (remembered per project): **⚙ Build** in the run view, or from the terminal:

```sh
./dt run ~/libft --make-args "bonus"                    # this run only: make -C … bonus
./dt run ~/libft --make-args "CFLAGS=-O2 CC=gcc" --save-build   # remember it for this project
./dt run ~/so_long --build-cmd "make -C {project} re" --env DISPLAY=:0 --save-build
./dt run ~/py_proj --build-cmd "python3 -m compileall -q {project}" --save-build   # any command works
./dt run ~/libft --save-build                            # back to the defaults
```

| option | effect |
|---|---|
| build command | replaces the suite's command (`{project}` = the isolated copy) |
| extra make arguments | appended to the make command: targets (`bonus`) and variables (`CFLAGS=-O2`). Variables also apply to the suites' extra make steps. |
| environment | `KEY=VALUE` variables for every build command |
| always clean | `make fclean` before building (same as the *Clean build* button) |

## Suites included

| project | suite | what is tested |
|---|---|---|
| **libft** | **Sstyle suite** (community) | SStyles93's tests, ported to DeepThought: all 43 functions, one test per case, plus a Memory group (no leak, NULL without leaking when any malloc fails) for every allocating function. DeepThought adds Makefile rules, relink, norminette and forbidden-function checks. |
| **ft_printf** | **Sstyle suite** (community) | SStyles93's printf tests: every case compared with the system's `printf` (bytes and return value), behaviour (no buffering, -1 on write errors, malloc failures), subject requirements (Makefile, relink, `nm`), bonus flags, plus the original printf's undefined behaviours (informational, not graded). |
| **get_next_line** | official | Every test with `BUFFER_SIZE` = 1, 42, 9999 and 10000000: empty file, no final newline, only newlines, 10 000-char lines, 75 KB file, stdin, pipes, invalid/closed fds, read errors, malloc failure, leaks after EOF. Bonus: interleaved fds. |

Community suites live in [`community/`](community). Run `./dt suite list` to see what's installed.

## Your own projects

DeepThought isn't limited to the projects it knows. Add any folder, give it a type, and choose the suites that test it: your own, a friend's, or any installed suite, whatever project it was written for.

```sh
./dt project add ~/pipex pipex                              # a folder, with your own type name
./dt suite new pipex-tests --project pipex --runner exec --link ~/pipex   # create a suite for it
./dt suite add https://github.com/someone/pipex-tests.git --link ~/pipex  # or link someone's suite
./dt project link ~/pipex other-suite                       # attach any installed suite
./dt project list                                           # types and suites of your projects
./dt project auto ~/pipex                                   # back to automatic detection
```

In the web UI: add the folder (optionally with a type), then use **☰ Suites** on the project. You can also pick a project in **Link it to a project** when importing or creating a suite on the Suites page.

## Commands

| command | |
|---|---|
| `./dt` / `./dt ui [project]` | web UI (127.0.0.1, protected by a token) |
| `./dt run [path] [-s suite] [-f] [-w] [-v] [--sanitize] [--no-leaks] [--no-norm] [--clean] [--make-args A] [--build-cmd C] [--env K=V] [--save-build] [--timeout s] [-j n] [--json f] [--junit f]` | test in the terminal |
| `./dt tui [path]` | interactive terminal UI |
| `./dt suite list \| info ID \| add <git-url\|folder\|file.zip> [--link PROJECT] \| remove ID \| update [ID] \| enable ID \| disable ID` | manage suites |
| `./dt suite new NAME --project TYPE [--runner c-unit\|exec\|python-unit\|script] [--link PROJECT]` | create a suite from a template |
| `./dt suite validate PATH [--project PROJECT]` | check a suite (and run it against a project) |
| `./dt suite pack ID` | export a suite as a zip |
| `./dt update [--check]` | update the tester and git suites (also done automatically at every launch; `--no-update` or `DT_NO_UPDATE=1` to skip) |
| `./dt project list \| add PATH [TYPE] \| kind PATH TYPE\|auto \| link PATH SUITE… \| unlink PATH SUITE… \| auto PATH` | your projects: type and linked suites |
| `./dt history [path]` | past runs and grades |
| `./dt doctor` | check your environment (compiler, norminette, nm, git, cache dir) |
| `./dt man [topic]` | the manual: `./dt man` opens it in your browser (search, cross-links, every doc); `./dt man DT_CHECK_STR` prints one entry in the terminal |

## Write your own tests

```sh
./dt suite new my-tests --project libft
```

Then read **[docs/writing-suites.md](docs/writing-suites.md)**. It covers everything from a five-minute tutorial to the full reference (C harness, exec cases, Python, the protocol for other languages), how to test your suite, and how to share it.

Every macro, function, key and protocol event has its own page in **[docs/reference.md](docs/reference.md)**, also available offline: `./dt man` opens it in your browser, `./dt man NAME` prints one entry in the terminal.

Example of a C test:

```c
DT_TEST(ft_split, malloc_fail_middle, "A malloc fails midway: returns NULL and frees everything")
{
	dt_malloc_fail_at(3);
	DT_EXPECT_NULL(ft_split("a b c d", ' '));
}
```

Example of a program test (`exec` runner, no code):

```toml
[[case]]
name = "duplicates are an error"
cmd = ["{project}/push_swap", "1", "2", "1"]
[case.expect]
stderr = "Error\n"
exit = "nonzero"
```

## Documentation

- [docs/writing-suites.md](docs/writing-suites.md): writing, testing and sharing suites
- [docs/reference.md](docs/reference.md): the reference manual — every command, setting, `suite.toml` key, macro, function and protocol element (`./dt man`)
- [docs/architecture.md](docs/architecture.md): how the system works, and how to extend it
- [docs/protocol.md](docs/protocol.md): the DeepThought Test Protocol, in full: transport, lifecycle, every event and field, encoding, timeouts, example producers

## Where things go

DeepThought never writes into your project folder. Builds happen in `/tmp/dt-$USER` (or `~/goinfre` when present), and settings, installed suites and history live in `~/.deepthought`. The repository itself stays clean, so updates never conflict.

## Developing DeepThought

```sh
python3 -m unittest discover -s tests -t .     # engine tests, including end-to-end runs
```

The web UI has no build step: edit `deepthought/web/` and reload. Vendored dependencies: [Preact + htm](https://github.com/developit/htm) (MIT) in `deepthought/web/vendor/`, and [tomli](https://github.com/hukkin/tomli) (MIT, used only on Python 3.10) in `deepthought/_vendor/`.
