# DeepThought reference manual

Every command, setting, file, key, macro, function and protocol element of DeepThought, one entry each, like a `man` page. For explanations and tutorials, read [writing-suites.md](writing-suites.md) (how to write tests), [protocol.md](protocol.md) (the DTP in depth) and [architecture.md](architecture.md) (how the engine works).

From the terminal, every `###` entry of this page is a man page:

```sh
./dt man                       # list every entry, by section
./dt man DT_CHECK_STR          # one entry (case-insensitive)
./dt man malloc                # every entry whose name contains "malloc"
./dt man -k leak               # every entry whose text mentions "leak"
```

**Sections**

1. [Concepts](#1-concepts)
2. [Command line](#2-command-line)
3. [suite.toml](#3-suitetoml)
4. [Placeholders](#4-placeholders)
5. [exec cases](#5-exec-cases)
6. [C harness: writing tests](#6-c-harness-writing-tests)
7. [C harness: checks](#7-c-harness-checks)
8. [C harness: input, output and control](#8-c-harness-input-output-and-control)
9. [C harness: memory](#9-c-harness-memory)
10. [C harness: test binaries](#10-c-harness-test-binaries)
11. [Python harness](#11-python-harness)
12. [Protocol (DTP)](#12-protocol-dtp)
13. [Statuses and grading](#13-statuses-and-grading)
14. [Project checks](#14-project-checks)
15. [Environment variables](#15-environment-variables)
16. [Files and folders](#16-files-and-folders)
17. [Settings (config.toml)](#17-settings-configtoml)
18. [Web server and API](#18-web-server-and-api)

Conventions: `UPPER_CASE` are C macros, `lower_case()` are functions, `[table]` and `key` are TOML, `{name}` is a placeholder, and *italics* are values you choose.

---

## 1. Concepts

### project

The student's code folder (`~/libft`). DeepThought never modifies it: every run works on a copy (see **workspace**). A project has a **project kind**, found by detection, chosen by the user, or implied by the suites linked to it.
See also: project kind, dt project, workspace.

### project kind

The type of a project, as a free-form name: `libft`, `get_next_line`, `ft_printf`, `push_swap`, `my_project`… Every suite declares the kind it targets in `[suite] project`. All enabled suites of the same kind run together on a project of that kind.

How the kind of a project is decided, in order:

1. **linked** — the user linked suites to the project (`dt project link`): exactly those suites run, whatever their kind.
2. **kind** — the user set a type (`dt project kind PATH TYPE`): every enabled suite of that type runs.
3. **auto** — detection: every enabled suite with a `[detect]` table is scored against the folder; the best-scoring suite gives the kind, and every suite of that kind that matches runs.

See also: [detect], dt project.

### suite

A folder containing a `suite.toml` plus tests, fixtures and anything else it needs. It targets one project kind and contains one or more **groups**. Suites come from a **source**: builtin, community, local, folder, git or zip.
See also: suite.toml, suite uid, suite source, dt suite.

### suite uid

The unique name of an installed suite. Usually its `[suite] id`; when two installed suites share an id, the later ones get a suffix with their source (`libft-extra@git`, then `@git2`…). Commands that take a suite (`--suite`, `dt suite update`, `dt project link`) accept the uid.

### suite source

Where an installed suite comes from:

| source | location | updated by |
|---|---|---|
| `builtin` | `suites/` in the tester repo | `dt update` |
| `community` | `community/` in the tester repo (e.g. the Sstyle suites) | `dt update` |
| `local` | `~/.deepthought/suites/local/` (created by `dt suite new`) | you: edits are live |
| `folder` | anywhere on disk, added with `dt suite add /path` | you: edits are live (linked, not copied) |
| `git` | `~/.deepthought/suites/git/<id>/` | `dt suite update` |
| `zip` | `~/.deepthought/suites/zip/<id>/` | re-import a newer zip |

### group

One `[[group]]` block of a suite: a set of tests run by one **runner**, with one category (`mandatory`, `bonus`, `extra`). It appears as a folder in the test tree. With a **matrix**, a group runs once per variant.
See also: [[group]], runner, matrix.

### runner

The adapter that builds, discovers and runs the tests of a group:

| runner | tests are | see |
|---|---|---|
| `c-unit` | C files using `dt.h` | sections 6–10 |
| `exec` | a TOML list of command lines with expected output | section 5 |
| `python-unit` | Python files using `dtharness` | section 11 |
| `script` | any executable speaking DTP | section 12 |

### matrix

A table of lists in a group (`matrix = { BUFFER_SIZE = [1, 42] }`). The group is built and run once per value, or per combination of values when there are several variables. Each run is a **variant**, shown as `Group [BUFFER_SIZE=1]`. The current value is available as `{matrix.NAME}` and `$DT_MATRIX_NAME`.

### test

The smallest unit with a status. It has an **id** `group/name` (in C, `DT_TEST(group, name, …)`), a description, and the location of its source code.
See also: test id, statuses.

### test id

`group/name`, unique within a producer and stable across runs. History, regressions and *Retest failed* match tests by id. The *group* part of the id (before the `/`) is unrelated to the suite's `[[group]]`.

### workspace

The isolated copy of the project, under the cache folder (`/tmp/dt-$USER/ws/<project-key>/project` or goinfre). Synced incrementally: files you change are copied again; files the build produced are kept, so `make` doesn't rebuild everything every run. `{project}` and `$DT_PROJECT` point to it.
See also: cache folder.

### run

One execution: plan → workspace sync → fetch → build → checks → groups (compile, discover, test) → grade → history. A run streams events to the web UI, the terminal reporter and the TUI, and is saved in the history.

### stage

A step of a run shown above the tests: *Test sources* (fetch), *Build*, and the project checks (*Makefile rules*, *No relink*, *Norminette*, *Forbidden functions*, *Required files*). A stage has a status `pass`, `warn`, `fail` or `skip`, a message and a log.

### harness

The code DeepThought links into, or imports from, test files: the C harness (`deepthought/harness/c/`: `dt.h`, `dt_main.c`, `dt_alloc.c`) and the Python harness (`deepthought/harness/python/dtharness.py`). Harnesses register tests, run each one in its own process, and report results in DTP.

### DTP

The *DeepThought Test Protocol*: JSON lines written by every test process to the descriptor `$DT_REPORT_FD`. Section 12 lists its elements; [protocol.md](protocol.md) is the full specification.

### fixture

A data file shipped with a suite, in its `fixtures/` folder (or the folder named by `fixtures`). Tests get its absolute path with `dt_fixture()` (C), `fixture()` (Python), `$DT_FIXTURES` or `{fixtures}`.

### regression

A test that passed in the previous comparable run of the same project and fails now. Shown with a marker in the UI and counted in the run's score (`regressions`). The opposite is **fixed**. Runs in sanitizer mode are compared only with sanitizer runs.

### linked suites

Suites the user attached to one project by hand (`dt project link`, `--link`, ☰ Suites in the UI). When a project has linked suites, exactly those run. Any suite can be linked to any project, whatever its `project` kind.

### sanitizer mode

A run option (`--sanitize`, UI toggle): the project and the tests are compiled with `-fsanitize=address,undefined -g`. Crashes then report the exact faulty line. DeepThought's malloc hooks are disabled in this mode, so tests using `dt_malloc_fail_*` are skipped.

### watch mode

`dt run --watch` or the *Watch* toggle: the project folder is polled, and saving a file re-runs the tests.

### self-update

The tester is a git clone and updates itself: on every launch (`auto_update`), it fetches and fast-forwards, then restarts on the new code. `dt update` does it by hand. It refuses when tracked files were modified locally.

---

## 2. Command line

### dt

```
./dt [--no-update] [COMMAND] [ARGS…]
```

The launcher: a POSIX sh script that finds Python 3.10 or newer (`$DT_PYTHON`, then `python3`, `python3.14` … `python3.10`, `python`) and runs the tester. Without a command, `dt` starts the web interface (`dt ui`). A first argument that is not a command is taken as a project path for `dt ui`.

Before any command except `--help`, `--version` and `update`, DeepThought **updates itself** when `auto_update` is on (see **self-update**), then restarts.

| option | |
|---|---|
| `--no-update` | skip the automatic update for this launch |
| `--version` | print the version |
| `-h`, `--help` | help for `dt` or for a command (`dt run -h`) |

### dt ui

```
./dt ui [PATH] [--port N] [--host ADDR] [--no-open]
```

Start the web interface on `127.0.0.1:4242` (the next free port if taken; `port` setting) and open the browser on it. `PATH` opens that project directly. `--no-open` doesn't open a browser (useful over SSH). The page is protected by a random token in its URL; keep the URL to yourself.

### dt run

```
./dt run [PATH] [OPTIONS]
```

Test a project (default: the current folder) in the terminal and print a coloured report.

| option | meaning |
|---|---|
| `-s ID`, `--suite ID` | run this suite (repeatable). Default: the project's linked suites, type, or detection. |
| `-f`, `--failed` | re-run only the tests that did not pass in the last run |
| `-w`, `--watch` | re-run every time a file of the project changes |
| `-v`, `--verbose` | also print passing tests and logs |
| `-q`, `--quiet` | only the summary |
| `--sanitize` | sanitizer mode (ASan + UBSan) |
| `--no-leaks` | leaks do not fail tests |
| `--no-norm` | skip norminette |
| `--clean` | run the clean command (`make fclean`) before building |
| `--make-args ARGS` | extra arguments for every `make` of the run: targets and variables, `"bonus CFLAGS=-O2"` |
| `--build-cmd CMD` | replace the suite's build command, e.g. `"make -C {project} re"` |
| `--env K=V` | environment variable for the build (repeatable) |
| `--save-build` | remember `--build-cmd`, `--make-args`, `--env` and `--clean` for this project (empty: forget them) |
| `--timeout S` | per-test timeout in seconds, for every group |
| `-j N`, `--jobs N` | parallel jobs (default: number of CPUs) |
| `--json FILE` | write the complete result as JSON |
| `--junit FILE` | write a JUnit XML report (for CI) |

Exit status: `0` everything passed, `1` a graded test failed, a build failed, or a check flagged the project (norminette, forbidden, relink, rules, files), `2` the run could not start (no suite for this project…). Groups with category `extra` don't affect it.

### dt tui

```
./dt tui [PATH] [-s ID]…
```

The interactive terminal interface (curses). Keys: arrows or `j` `k` move, `enter`/`space` fold a group, `PgUp`/`PgDn` scroll the details, `r` run again, `R` re-run failed tests, `f` show only failures, `s` toggle sanitizer mode for the next run, `w` watch, `q`/`Esc` quit.

### dt suite

```
./dt suite ACTION [TARGET] [OPTIONS]
```

Manage test suites. Actions:

| action | target | does |
|---|---|---|
| `list` | | every installed suite with uid, version, kind, source, enabled state and warnings; then suites that failed to load, with the reason |
| `info` | uid | the suite's details as JSON |
| `add` | git URL, folder, or `.zip` | install a suite. Asks for confirmation (foreign suites run code on your machine) unless `-y`. `--ref` pins a git branch, tag or commit. `--link PROJECT` also links it to that project. |
| `remove` | uid | uninstall. Git, zip and local suites are deleted; folders added with `add` are only forgotten. Builtin and community suites can't be removed: disable them. |
| `update` | [uid] | `git pull` one git suite, or all of them, and refresh `[[fetch]]` dependencies on branches |
| `new` | name | scaffold a new suite in `~/.deepthought/suites/local/NAME` (or `--dir`). `--project KIND`, `--runner c-unit\|exec\|python-unit\|script`, `--link PROJECT`. New suites have no `[detect]`: they run where they are linked. |
| `pack` | uid | write `ID-VERSION.zip` (in `-o DIR`, default the current folder) |
| `validate` | path | check a `suite.toml` and list its groups; with `--project PATH`, also run it against that project |
| `enable`, `disable` | uid | include or exclude a suite from automatic runs |

### dt project

```
./dt project ACTION [PATH] [VALUES…]
```

Your projects, their type and their suites (stored in `projects.json`).

| action | values | does |
|---|---|---|
| `list` | | every project with its type, mode (`detected`, `own type`, `linked suites`) and the suites that would run |
| `add` | [TYPE] | remember a project; with TYPE, also set its type |
| `kind` | TYPE \| `auto` | set the project's type (any name); `auto` goes back to detection |
| `link` | SUITE… | link suites to the project. The first link keeps the suites that were running already. |
| `unlink` | SUITE… | remove suites from the project's links |
| `auto` | | forget the type and the links: back to detection |

### dt update

```
./dt update [--check]
```

Update the tester: `git fetch`, then `git pull --ff-only`, then update every git suite. `--check` only says whether an update is available and lists the new commits. Refuses (with the reason) when the clone has local modifications.

### dt doctor

```
./dt doctor
```

Check the environment: Python version, `cc`, `make`, `nm`, `git` (required), `norminette`, `valgrind`, `leaks` (optional), the cache and data folders, and the state of the tester's git clone. Exit status 1 when something required is missing.

### dt history

```
./dt history [PATH] [-n N]
```

The last N (default 20) runs of a project: id, date, status, grade and regressions. The web UI's History page also compares two runs.

### dt man

```
./dt man [-k] [TOPIC]
```

This manual in the terminal. Without TOPIC, lists every entry by section. With TOPIC, prints the entry with that name (case-insensitive), or the list of entries whose name contains it. `-k` searches the text of the entries instead of their names. The pages are read from `docs/reference.md`, so they update with the tester.

---

## 3. suite.toml

### suite.toml

The manifest of a suite, in TOML, at the root of the suite folder. Tables: `[suite]` (required), `[detect]`, `[build]`, `[forbidden]`, `[norminette]`, `[files]`, `[defaults]`, `[[group]]` (at least one), `[[fetch]]`. Unknown tables and keys produce a warning, not an error. Check a manifest with `./dt suite validate PATH`.

### [suite]

Identity of the suite. Required.

| key | type | | meaning |
|---|---|---|---|
| `id` | string | ✓ | unique identifier: letters, digits, `.`, `_`, `-`, starting with a letter or digit. Keep it stable: history is matched by it. |
| `name` | string | ✓ | display name |
| `project` | string | ✓ | the project kind it targets. Reuse existing names (`libft`, `get_next_line`, `ft_printf`) when they apply. |
| `version` | string | | `"1.2.0"`, shown in the UI, compared when re-importing zips. Default `0.0.0`. |
| `engine` | string | | required DeepThought version: `">=0.1"`, `">=0.1,<1.0"`, `"==0.3"`. Operators `>=`, `>`, `<=`, `<`, `==`, comma = and. Incompatible suites are flagged and not run. |
| `authors` | list | | logins or names |
| `description` | string | | one sentence for the Suites page |
| `homepage` | string | | link to the suite's repository |

### [detect]

How to recognise a project of this kind. Optional: without it, the suite runs only when linked, chosen with `--suite`, or when the project's type is set to its kind. All conditions given must hold.

| key | type | meaning | score |
|---|---|---|---|
| `files` | list of globs | every pattern matches at least one file | +2 per exact name, +1 per glob |
| `any_files` | list of globs | at least one pattern matches | +2 or +1 for the best hit |
| `makefile_name` | string | the Makefile's `NAME =` value is exactly this | +3 |

The kind of the best-scoring suite wins; ties keep the first suite found.

### [build]

How to build the project, and which project checks run.

| key | type | meaning |
|---|---|---|
| `command` | string or list | build command run in the workspace, e.g. `"make -C {project}"`. Omit it when the tests compile the sources themselves. A failed build marks every group of the suite `build_error`, and the grade is 0. |
| `artifacts` | list | files the build must produce, relative to the project (`["libft.a"]`). Missing ones fail the build. Used by `relink` and `forbidden`. |
| `checks` | list | project checks to run: `files`, `rules`, `relink`, `norminette`, `forbidden` (section 14) |
| `rules` | list | Makefile rules required by the `rules` check. Default `["all", "clean", "fclean", "re", "$(NAME)"]`. |
| `clean` | string | command of *Clean build* / `--clean`. Default `make fclean`. |
| `syntax_check` | string | `"python"`: without `command`, parse every `.py` file of the project (default for suites with a `python-unit` group); `"none"` disables it |
| `timeout` | number | build timeout, seconds. Default 300. |

The user can override the command, add make arguments and environment variables per project (`--build-cmd`, `--make-args`, `--env`, ⚙ Build in the UI). Make variables from `--make-args` (`CFLAGS=…`) are also added to `before` make commands. In sanitizer mode, `make` gets `CFLAGS="-Wall -Wextra -Werror -g -fsanitize=address,undefined -fno-omit-frame-pointer"`.

### [defaults]

Defaults for every group of the suite.

| key | type | meaning |
|---|---|---|
| `timeout` | number | per-test timeout in seconds (otherwise the user's `timeout` setting, 5) |
| `leaks` | bool | `false`: leaks never fail tests of this suite |
| `cflags` | list | extra compiler flags for every `c-unit` compilation, placeholders allowed |
| `fixtures` | string | fixtures folder, relative to the suite. Default `fixtures`. |
| `sequential` | bool | `true`: the suite's groups run one after the other instead of in parallel (tests that run `make` in the project, shared files) |

### [[group]]

One block of tests. Keys by runner:

| key | runners | type | meaning |
|---|---|---|---|
| `name` | all | string | **required**, unique in the suite |
| `description` | all | string | shown in the UI |
| `category` | all | string | `mandatory` (default), `bonus`, or `extra` (shown, never graded) |
| `runner` | all | string | `c-unit` (default), `exec`, `python-unit`, `script` |
| `when` | all | table | conditions to run the group, else it is *skipped* (see **when**) |
| `before` | all | list | commands run in the project first (see **before**) |
| `matrix` | all | table of lists | run once per value / combination (see **matrix**) |
| `timeout` | all | number | per-test timeout for this group |
| `leaks` | all | bool | `false`: leaks don't fail this group's tests |
| `env` | all | table | environment variables for the test processes (placeholders allowed) |
| `fixtures` | all | string | fixtures folder of this group |
| `sources` | c-unit | list of globs | C files to compile: the tests, and project files when there is no library (`"{project}/get_next_line.c"`). Relative to the suite. **Required** for c-unit. |
| `include` | c-unit | list | `-I` folders. `"{project}"` also adds every project sub-folder (3 levels) that contains a header. |
| `link` | c-unit | list of globs | libraries and objects to link (`"{project}/libft.a"`) |
| `cflags` | c-unit | list | extra compiler flags (`["-D", "BUFFER_SIZE={matrix.BUFFER_SIZE}"]`) |
| `ldflags` | c-unit | list | extra linker flags (`["-lm"]`) |
| `split` | c-unit | bool | `true`: one test binary per test file (see **split**) |
| `cases` | exec | string | the TOML file listing the `[[case]]`s, relative to the suite. **Required** for exec. |
| `tests` | python-unit | list of globs | Python test files. **Required** for python-unit. |
| `command` | script | string or list | the DTP-speaking executable, relative to the suite or absolute, with fixed arguments. **Required** for script. |
| `darwin`, `linux` | all | table | platform additions (see **[group.darwin]**) |

Lists may be given as a single string.

### when

```toml
when = { files = ["ft_lstnew.c"], any_files = ["*_bonus.c", "bonus/*.c"], make_rule = "bonus" }
```

The group runs only if every condition holds; otherwise it is reported as *skipped* with the reason, not failed. `files`: every glob matches in the project. `any_files`: at least one matches. `make_rule`: the Makefile defines this rule. Typical use: bonus parts.

### before

```toml
before = ["make -C {project} bonus"]
```

Commands run in the project before the group's tests are compiled. All `before` commands of the run are executed up front, before any group compiles, and each distinct command runs only once per run, even if several groups list it. A failing command makes the group a `build_error` with its output.

### split

`split = true` in a `c-unit` group: every test file *of the suite* (from `sources`) becomes its own binary, linked with the project files listed in `sources` and with `link`. A file that doesn't compile against the student's code (missing function, wrong prototype) then breaks only its own tests, shown as one `FILE/compile` test with status `build_error` and the compiler output. Recommended for libraries, where students test unfinished projects.

### [group.darwin] · [group.linux]

```toml
[group.linux]
ldflags = ["-Wl,--whole-archive", "{project}/libft.a", "-Wl,--no-whole-archive"]
```

Settings appended to the group's own on that platform only (`darwin` = macOS). Accepted keys: `sources`, `include`, `link`, `cflags`, `ldflags` (lists, appended) and `env` (merged).

### [[fetch]]

```toml
[[fetch]]
name = "codetester"
git = "https://github.com/someone/tester.git"
ref = "473a2dc997f68a4047ca36f073c1f84097e5471b"
into = "../upstream"
```

A git repository the suite needs, downloaded before the first run (stage *Test sources*).

| key | | meaning |
|---|---|---|
| `git` | ✓ | repository URL |
| `name` | | letters, digits, `_`, `-`; gives the placeholder `{fetch.NAME}`. Default `depN`. |
| `ref` | | commit (fetched once, then offline), branch or tag (refreshed by `dt suite update`). Default: the default branch. |
| `into` | | where to clone, relative to the suite. It must stay inside the suite folder or its parent, so sibling suites can share one checkout. Default: NAME. |

If the download fails, the suite's groups are `build_error` with the reason; other suites still run.

### [forbidden]

Configuration of the `forbidden` check.

| key | meaning |
|---|---|
| `allowed` | external functions the project may use (`["malloc", "free", "write"]`) |
| `allowed_regex` | Python regexes of allowed names (`["ft_.*"]`) |
| `artifacts` | files to inspect with `nm`. Default: `[build] artifacts`. |
| `sources` | globs of project files to compile into objects first, for projects without a Makefile (`["get_next_line*.c"]`) |
| `cflags` | flags for that compilation (`["-D", "BUFFER_SIZE=42"]`) |

### [norminette]

| key | meaning |
|---|---|
| `paths` | files or folders to check, relative to the project. Default: the whole project. |

### [files]

| key | meaning |
|---|---|
| `required` | globs that must each match a file of the project (`["Makefile", "**/libft.h"]`) |

---

## 4. Placeholders

Strings in `suite.toml` (commands, paths, flags, `env` values) and in exec cases may contain placeholders. Unknown placeholders are left as they are.

### {project}

Absolute path of the workspace copy of the student's project. Same as `{build}`.

### {build}

Alias of `{project}` (the project is built in place, in the workspace).

### {suite}

Absolute path of the suite folder.

### {fixtures}

`{suite}/fixtures`. A group with its own `fixtures` key gets its folder through `$DT_FIXTURES` / `dt_fixture()`, not this placeholder.

### {out}

The group's output folder: where test binaries are built and where tests run (their current directory). One per group and matrix variant. Only defined inside groups.

### {harness}

The C harness folder (`dt.h`, `dt_main.c`, `dt_alloc.c`).

### {harness_py}

The Python harness folder (`dtharness.py`).

### {cc}

The configured C compiler (`cc` setting).

### {matrix.NAME}

The current value of the matrix variable NAME, in a group with a `matrix`.

### {fetch.NAME}

Absolute path of the `[[fetch]]` dependency called NAME.

---

## 5. exec cases

### [[case]]

One test of an `exec` group, in the file named by the group's `cases`. The program is run, then its output and exit code are checked.

| key | type | meaning |
|---|---|---|
| `name` | string | display name, unique in the file. The test id is derived from it (lowercase, dashes). |
| `id` | string | explicit test id instead |
| `desc` | string | description shown in the UI |
| `cmd` | list or string | the command. A list runs without a shell (safest). A string is split like a shell would. |
| `shell` | bool | `true`: run the `cmd` string through `/bin/sh -c` (pipes, redirections, `&&`). A string starting with `sh ` also does. |
| `stdin` | string | text given on stdin (placeholders allowed) |
| `stdin_file` | string | file given on stdin, relative to the suite |
| `timeout` | number | seconds (default: the group's) |
| `env` | table | extra environment variables |
| `input` | string | how the input is described in failures. Default: the command line (with `<project>` for the project path) and the start of stdin. |
| `reference` | string or list | a command whose result is the expected one, run with the same stdin and env |
| `compare` | list | what to compare with `reference`: `stdout`, `stderr`, `exit`. Default `["stdout", "exit"]`. |
| `check` | string or list | a command that receives the program's stdout on its stdin; exit 0 means pass (checkers) |
| `[case.expect]` | table | the expectations (see **[case.expect]**) |

All commands run in the group's output folder (`{out}`). A signal is reported as `crash`, a timeout as `timeout`.

### [case.expect]

| key | meaning |
|---|---|
| `stdout`, `stderr` | exact content (placeholders allowed) |
| `stdout_contains`, `stderr_contains` | a string or a list of strings that must all appear |
| `stdout_regex`, `stderr_regex` | Python regular expression that must match (multiline mode) |
| `exit` | exact exit code, or `"nonzero"` |

Output is compared byte for byte (decoded as latin-1, so any byte survives).

---

## 6. C harness: writing tests

Test files include `dt.h` and are compiled with `dt_main.c` and `dt_alloc.c` by the `c-unit` runner. Never write a `main()`.

### dt.h

```c
#include "dt.h"
```

The C harness header. Include it first in every test file: it declares every macro and function of sections 6 to 10, and includes `<stddef.h>`, `<stdlib.h>`, `<string.h>`, `<stdio.h>` and `<unistd.h>`. The `c-unit` runner adds its folder to the include path.

### DT_TEST

```c
DT_TEST(group, name, "description")
{
	/* test body */
}
```

Define and register a test with id `group/name`. `group` and `name` must be valid C identifiers, and the pair must be unique in the binary. The description is a string literal shown to the student: write the rule being checked ("Returns NULL when malloc fails").

The test registers itself before `main()` (a constructor function), so no list needs to be maintained. At run time the body runs in its own forked process, with a timer of `DT_TIMEOUT` seconds and malloc tracking on. Returning from the body ends the test; its status is then `pass`, `fail` (a check failed) or `leak`.

```c
DT_TEST(ft_strlen, empty, "The empty string has length 0")
{
	DT_EXPECT_EQ_SIZE(ft_strlen(""), 0);
}
```

See also: t_dt_test, dt_register, DT_EXPECT, DT_CHECK_STR.

### t_dt_test

```c
typedef struct s_dt_test {
	const char *group; const char *name; const char *desc;
	const char *file;  int line;         t_dt_fn fn;
} t_dt_test;
typedef void (*t_dt_fn)(void);
```

A registered test. Built by `DT_TEST`; only needed with `dt_register`.

### dt_register

```c
void dt_register(t_dt_test test);
```

Register a test by hand, for generated tests or adapters around another tester. Must be called before `main()` runs, i.e. from a function with `__attribute__((constructor))`. The strings must stay valid for the whole program. At most 4096 tests per binary.

```c
static void my_case(void) { DT_CHECK_INT("answer", answer(), 42); }
__attribute__((constructor)) static void reg(void)
{
	dt_register((t_dt_test){"adapter", "answer", "answer() is 42", __FILE__, __LINE__, my_case});
}
```

### DT_PROTOCOL

```c
#define DT_PROTOCOL 1
```

The DTP version the harness speaks, sent in `hello`.

### expect and assert

Every check exists in two flavours. **`DT_EXPECT_*`** (and every `DT_CHECK_*`) records the failure and lets the test continue. **`DT_ASSERT_*`** records the failure and **stops the test** immediately (its process exits with status `fail`): use it when continuing makes no sense, typically before dereferencing a pointer that may be NULL.

Every check evaluates its arguments exactly once and returns `1` if it passed, `0` otherwise:

```c
if (!DT_EXPECT_NOT_NULL(r))
	return ;
```

A failure is reported as an `assert` event with a message (the C expression, or your label), expected and actual values, and the file and line of the check.

---

## 7. C harness: checks

### DT_EXPECT · DT_ASSERT

```c
int DT_EXPECT(cond);
int DT_ASSERT(cond);
```

Pass when `cond` is true (non-zero). On failure, the message is the text of `cond`, expected `true`, got `false`.

### DT_EXPECT_EQ_INT · DT_ASSERT_EQ_INT

```c
int DT_EXPECT_EQ_INT(actual, expected);
```

Compare two integers as `long long`. Shows both numbers. Use for `int`, `long`, `char` codes, return values of `atoi`, `printf`…

### DT_EXPECT_EQ_SIZE · DT_ASSERT_EQ_SIZE

```c
int DT_EXPECT_EQ_SIZE(actual, expected);
```

Compare as `unsigned long long`: for `size_t` (`strlen`, `strlcpy`) and other unsigned values.

### DT_EXPECT_EQ_PTR · DT_ASSERT_EQ_PTR

```c
int DT_EXPECT_EQ_PTR(actual, expected);
```

Pass when both pointers are the same address. Shows the addresses (`%p`). Typical use: `ft_strchr(s, c)` against `strchr(s, c)`.

### DT_EXPECT_EQ_STR · DT_ASSERT_EQ_STR

```c
int DT_EXPECT_EQ_STR(actual, expected);
```

Compare two C strings with `strcmp`. NULL-safe: two NULLs are equal, NULL and a string are different (shown as `(null)`). The failure is a text comparison (`cmp: "text"`): the UI points at the first different character.

### DT_EXPECT_EQ_MEM · DT_ASSERT_EQ_MEM

```c
int DT_EXPECT_EQ_MEM(actual, expected, n);
```

Compare `n` bytes. NULL-safe. The failure shows both byte strings with invisible bytes made visible. For `memcpy`, `memset`, `bzero`, buffers containing `\0`.

### DT_EXPECT_SAME_SIGN

```c
int DT_EXPECT_SAME_SIGN(actual, expected);
```

Pass when both values have the same sign: both negative, both zero, or both positive. For `strcmp`, `strncmp`, `memcmp`, whose exact value is not specified. Shows the values and their signs.

### DT_EXPECT_NULL · DT_ASSERT_NULL · DT_EXPECT_NOT_NULL · DT_ASSERT_NOT_NULL

```c
int DT_EXPECT_NULL(ptr);
int DT_ASSERT_NOT_NULL(ptr);
```

Pass when `ptr` is (or isn't) `NULL`. Shows `NULL` / `non-NULL pointer`.

### DT_EXPECT_ALLOC_SIZE

```c
DT_EXPECT_ALLOC_SIZE(ptr, n);
```

Pass when `ptr` was allocated (by `malloc`, `calloc` or `realloc` in the test binary) with exactly `n` bytes. Checks that `ft_strdup("abc")` allocates 4 bytes, `ft_calloc(3, 4)` 12… Does nothing in sanitizer mode. Not an expression: it doesn't return a value.

### DT_FAIL

```c
void DT_FAIL(msg);
```

An explicit failure with a fixed message. The test continues.

### DT_FAILF

```c
void DT_FAILF(fmt, ...);
```

An explicit failure with a printf-like message (up to 1023 characters): `DT_FAILF("word %d is \"%s\", expected \"%s\"", i, got[i], want[i])`.

### labelled checks

```c
DT_CHECK_STR("ft_substr(\"hello\", 1, 3)", got, "ell");
```

The `DT_CHECK_*` family shows **your label** instead of the C expression as the failure's title: the call, the input, or the original label of a ported test. Arguments are always *(label, actual, expected)*. They never stop the test (no assert flavour), and they return 1 when they pass. The label may be a string built at run time.

| macro | compares |
|---|---|
| `DT_CHECK(label, cond)` | `cond` is true |
| `DT_CHECK_BOOL(label, actual, expected)` | truthiness: both zero or both non-zero (shows `true`/`false`) |
| `DT_CHECK_INT(label, actual, expected)` | `long long` |
| `DT_CHECK_UINT(label, actual, expected)` | `unsigned long long` |
| `DT_CHECK_SIZE(label, actual, expected)` | `size_t` (same as UINT) |
| `DT_CHECK_CHAR(label, actual, expected)` | one `char`, shown as a character |
| `DT_CHECK_PTR(label, actual, expected)` | addresses |
| `DT_CHECK_STR(label, actual, expected)` | C strings, NULL-safe, text diff |
| `DT_CHECK_MEM(label, actual, expected, n)` | n bytes, NULL-safe |
| `DT_CHECK_NULL(label, ptr)` | `ptr == NULL` |
| `DT_CHECK_NOT_NULL(label, ptr)` | `ptr != NULL` |

### DT_CHECK

```c
int DT_CHECK(label, cond);
```

Labelled `DT_EXPECT`. See **labelled checks**.

### DT_CHECK_BOOL

```c
int DT_CHECK_BOOL(label, actual, expected);
```

Pass when `actual` and `expected` are both zero or both non-zero. For `ft_isalpha` & co., whose exact non-zero value is free: `DT_CHECK_BOOL("ft_isalpha('a')", ft_isalpha('a'), isalpha('a'))`.

### DT_CHECK_INT · DT_CHECK_UINT · DT_CHECK_SIZE

```c
int DT_CHECK_INT(label, actual, expected);
```

Labelled integer comparisons (`long long`, `unsigned long long`, `size_t`).

### DT_CHECK_CHAR

```c
int DT_CHECK_CHAR(label, actual, expected);
```

Compare one `char`. Shown as a character, with invisible ones made visible (`\0`, `↵`). For `ft_toupper`, `ft_strmapi` callbacks…

### DT_CHECK_PTR

```c
int DT_CHECK_PTR(label, actual, expected);
```

Labelled pointer comparison.

### DT_CHECK_STR

```c
int DT_CHECK_STR(label, actual, expected);
```

Labelled, NULL-safe string comparison with a text diff.

### DT_CHECK_MEM

```c
int DT_CHECK_MEM(label, actual, expected, n);
```

Labelled comparison of `n` bytes.

### DT_CHECK_NULL · DT_CHECK_NOT_NULL

```c
int DT_CHECK_NULL(label, ptr);
int DT_CHECK_NOT_NULL(label, ptr);
```

Labelled NULL checks.

### dt_check

```c
int dt_check(int ok, int fatal, const char *msg, const char *expected,
             const char *actual, const char *file, int line);
```

The function behind every check. Reports a failure when `ok` is 0, with your own expected/actual texts; `fatal` non-zero stops the test. Use it in helpers that format values themselves; pass `__FILE__, __LINE__` (or the caller's location). Returns `ok`.

### dt_check_int · dt_check_uint · dt_check_ptr · dt_check_sign · dt_check_bool · dt_check_char

```c
int dt_check_int(long long actual, long long expected, int fatal,
                 const char *msg, const char *file, int line);
int dt_check_uint(unsigned long long actual, unsigned long long expected, int fatal, …);
int dt_check_ptr(const void *actual, const void *expected, int fatal, …);
int dt_check_sign(long long actual, long long expected, int fatal, …);
int dt_check_bool(long long actual, long long expected, int fatal, …);
int dt_check_char(char actual, char expected, int fatal, …);
```

The functions behind the typed macros. `msg` is the failure's title. Return 1 when the check passes.

### dt_check_str

```c
int dt_check_str(const char *actual, const char *expected, int fatal,
                 const char *msg, const char *file, int line);
```

String comparison, NULL-safe, reported as text.

### dt_check_mem

```c
int dt_check_mem(const void *actual, const void *expected, size_t n, int fatal,
                 const char *msg, const char *file, int line);
```

Compare `n` bytes, NULL-safe.

### dt_check_bytes

```c
int dt_check_bytes(const void *actual, size_t alen, const void *expected, size_t elen,
                   int fatal, const char *msg, const char *file, int line);
```

Compare two byte buffers **of possibly different lengths**: equal when the lengths and every byte are equal. The tool for captured output, where the length matters as much as the content (`printf` returning 5 but writing 4 bytes):

```c
dt_check_bytes(out.data, out.len, "hello\n", 6, 0, "output", __FILE__, __LINE__);
```

### dt_fail

```c
void dt_fail(const char *msg, const char *file, int line);
```

The function behind `DT_FAIL`.

### dt_failf_at

```c
void dt_failf_at(const char *file, int line, const char *fmt, ...);
```

The function behind `DT_FAILF`, for helpers that report the caller's location.

---

## 8. C harness: input, output and control

### dt_input

```c
void dt_input(const char *fmt, ...);
```

Describe the input being tested, printf-like (up to 1023 characters). Every failure that follows shows it as **Input**, and a crash or timeout shows "while testing: …". It stays until the next `dt_input` or the end of the test; `dt_input("")` clears it. Call it before calling the student's code, once per input:

```c
static void check(const char *s, char c)
{
	dt_input("s=\"%s\", c='%c'", s, c);
	...
}
```

Sends a DTP `input` event.

### dt_note

```c
void dt_note(const char *fmt, ...);
```

Add a line of text to the test's details (DTP `log`), printf-like, up to 1023 characters. Doesn't change the status.

### dt_skip

```c
void dt_skip(const char *reason);
```

Stop the test and mark it `skip` with the reason (as a note). For tests that can't run in this environment. Skipped tests don't count in the grade.

### t_dt_capture

```c
typedef struct s_dt_capture { char *data; size_t len; } t_dt_capture;
```

Bytes captured from a file descriptor. `data` is NUL-terminated for convenience but may contain NUL bytes: always use `len`. `data` is NULL when nothing was written. Free it with `dt_capture_free`.

### DT_CAPTURE_STDOUT

```c
DT_CAPTURE_STDOUT(cap, statement);
```

Run `statement` with everything written to stdout (fd 1) captured into the `t_dt_capture` named `cap`, instead of being printed. stdio buffers are flushed before and after, so `printf` output is included. Works with any amount of output (it goes through a temporary file).

```c
t_dt_capture out;
int          ret;

DT_CAPTURE_STDOUT(out, ret = ft_printf("%d|", 42));
dt_check_bytes(out.data, out.len, "42|", 3, 0, "output", __FILE__, __LINE__);
DT_EXPECT_EQ_INT(ret, 3);
dt_capture_free(&out);
```

### DT_CAPTURE_FD

```c
DT_CAPTURE_FD(fd, cap, statement);
```

Same as `DT_CAPTURE_STDOUT` for any descriptor: `DT_CAPTURE_FD(2, err, ft_putstr_fd("x", 2))`.

### DT_COMPARE_OUTPUT

```c
DT_COMPARE_OUTPUT(ft_call, ref_call);
```

Run `ft_call` and `ref_call`, capture what each writes on stdout, and check that the bytes **and** the return values (as `long long`) are the same. Two failures may be reported: `output of ft_call` (with a byte diff) and `return value of ft_call`. Captures are freed for you.

```c
DT_COMPARE_OUTPUT(ft_printf("%5.2s|", "abc"), printf("%5.2s|", "abc"));
```

### dt_capture_begin · dt_capture_end · dt_capture_free

```c
int  dt_capture_begin(int fd);
void dt_capture_end(int fd, int token, t_dt_capture *out);
void dt_capture_free(t_dt_capture *cap);
```

The functions behind the capture macros. `dt_capture_begin` redirects `fd` to a temporary file and returns a token (the saved descriptor); `dt_capture_end` restores `fd` and fills `out`. `dt_capture_free` releases the data and resets the structure. Captured data is allocated outside malloc tracking, so it never counts as a leak.

### dt_fixture

```c
const char *dt_fixture(const char *relpath);
```

Absolute path of a file in the group's fixtures folder (`$DT_FIXTURES/relpath`). An absolute `relpath` is returned unchanged. The result is a static buffer, overwritten by the next call: copy it if you need two at once.

```c
int fd = open(dt_fixture("lines/empty.txt"), O_RDONLY);
```

---

## 9. C harness: memory

`dt_alloc.c` replaces `malloc`, `calloc`, `realloc` and `free` in the test binary. While a test runs, allocations made by code in the binary (the student's library and your tests) are recorded; at the end of the test, whatever is still allocated is a leak. No valgrind needed, on macOS and Linux. On Linux, only calls coming from the test executable are tracked, so libc's internal allocations (`printf` buffers, `fopen`) never count. Tracking is off in sanitizer mode (`DT_NO_ALLOC_HOOK`).

### leaks

At the end of every test, the harness counts the blocks still allocated. If any, it sends a DTP `leak` event (bytes, count), and the test ends with status `leak` unless a check already failed. Free everything your test receives from the student's functions. Turn it off per test (`dt_leaks_ignore`), per group (`leaks = false`), per suite (`[defaults] leaks = false`) or per run (`--no-leaks`). Up to 65536 live blocks are tracked; beyond, leak reports are disabled for that test.

### dt_malloc_fail_at

```c
void dt_malloc_fail_at(int nth);
```

Make the `nth` allocation from now (1 = the next one) return `NULL`; the others succeed. Counts `malloc`, `calloc` and `realloc`. The way to test that a function returns NULL **and frees what it already allocated** when malloc fails midway:

```c
DT_TEST(ft_split, fail_3rd, "When the 3rd malloc fails, returns NULL without leaking")
{
	dt_malloc_fail_at(3);
	DT_EXPECT_NULL(ft_split("a b c", ' '));
}
```

In sanitizer mode the test is skipped.

### dt_malloc_fail_all

```c
void dt_malloc_fail_all(void);
```

Every allocation from now returns NULL, until `dt_malloc_reset`. Skipped in sanitizer mode.

### dt_malloc_reset

```c
void dt_malloc_reset(void);
```

Stop injecting failures and reset the allocation counter. Allocations already tracked stay tracked.

### dt_malloc_calls

```c
int dt_malloc_calls(void);
```

Number of allocations made since the last `dt_malloc_reset` or `dt_malloc_fail_*` (or since the test started). Use it to loop over every allocation of a function: call it once to count, then `dt_malloc_fail_at(i)` for each `i`. Returns -1 when hooks are disabled.

### dt_leaks_ignore

```c
void dt_leaks_ignore(void);
```

Don't report leaks for the current test. For memory the project legitimately keeps (get_next_line's static buffer when a test stops before EOF). Leave a comment saying why.

### dt_alloc_size

```c
size_t dt_alloc_size(const void *ptr);
```

The size requested for a tracked allocation, 0 if `ptr` is not tracked or hooks are disabled. Prefer `DT_EXPECT_ALLOC_SIZE`.

### dt_alloc_live

```c
size_t dt_alloc_live(void);
```

Number of tracked blocks currently allocated. Compare before and after one call to check that a single step frees what it should (`ft_lstdelone`, `ft_lstclear`), instead of waiting for the end of the test. Returns 0 when hooks are disabled.

### dt_raw_malloc · dt_raw_free

```c
void *dt_raw_malloc(size_t size);
void  dt_raw_free(void *ptr);
```

Allocate and free memory that is **never tracked**: never a leak, never failed by injection. For test infrastructure (reference results, big buffers) that must survive `dt_malloc_fail_all`.

### dt_alloc_hooked

```c
int dt_alloc_hooked(void);
```

1 when malloc tracking is compiled in, 0 in sanitizer mode. Test with it before relying on leak detection or failure injection.

### DT_NO_ALLOC_HOOK

Compile-time macro. When defined (`-DDT_NO_ALLOC_HOOK`, done automatically in sanitizer mode), the harness doesn't replace `malloc`/`free`: leaks aren't detected by the harness, `dt_malloc_fail_*` skip the test, and `dt_alloc_*` return 0. AddressSanitizer then detects memory errors instead.

---

## 10. C harness: test binaries

### test binary

The executable built by the `c-unit` runner from your sources and the harness: `{out}/dt_tests`, or `{out}/dt_FILE` per test file with `split = true`. It speaks DTP when `DT_REPORT_FD` is set and prints readable text otherwise, so you can run it by hand (the **Reproduce** button gives the exact command).

```
./dt_tests --list               # list the tests: id and description
./dt_tests                      # run every test
./dt_tests --run ID|GROUP …     # run some tests (a GROUP selects all its tests)
```

Each test runs in a forked child with a timer; a crash or timeout only ends that test. Captured stdout/stderr of the test (first 4096 bytes, `DT_OUTPUT_MAX`) is sent with its result.

### exit codes

Exit codes of a test's child process, read by the parent harness:

| code | status |
|---|---|
| 0 | `pass` |
| 1 | `fail` (a check failed, or a `DT_ASSERT_*` stopped the test) |
| 2 | `skip` |
| 3 | `leak` |
| other | `error` |
| killed by `SIGALRM` | `timeout` |
| killed by another signal | `crash`, with the signal name and an explanation |

The test binary itself exits 0 once it has run its tests.

### DT_NO_FORK

Environment variable. `DT_NO_FORK=1` runs tests in the binary's own process, without fork or timer, so a debugger sees the crash:

```sh
DT_NO_FORK=1 lldb ./dt_tests -- --run ft_split/empty
```

A crash then stops the whole binary.

### DT_OUTPUT_MAX

Environment variable. Bytes of a test's stdout/stderr kept and sent in its `end` event. Default 4096.

### limits

| limit | value |
|---|---|
| tests per binary | 4096 |
| `dt_input`, `dt_note`, `DT_FAILF` text | 1023 characters |
| tracked live allocations per test | 65536 |
| failed asserts shown per test | 30 (engine side) |
| captured output kept per test | `DT_OUTPUT_MAX`, 4096 bytes |

---

## 11. Python harness

Test files of a `python-unit` group import `dtharness`. The project's folder is first on `sys.path`, so the student's modules import directly. Each test runs in a forked process with a timeout.

```python
from dtharness import test, given, expect_eq
import calc

@test("add() adds two numbers")
def add_basic():
    given(1, 2)
    expect_eq(calc.add(1, 2), 3)
```

### dtharness

The Python harness module (`deepthought/harness/python/dtharness.py`), run by the `python-unit` runner as `python3 dtharness.py [--list | --run ID…] FILES…`. Test files may also be run by hand that way.

- A file whose import fails (the student's module has a syntax error, a missing name…) becomes one test `FILE/import` with status `build_error` and the traceback.
- An uncaught exception in a test ends it with status `crash` and the reason "an exception was raised: …" (type, message, file and line).
- `sys.exit()` in the student's code is a failure ("the code called exit()").
- An infinite loop is a `timeout`.
- Output printed while importing test files is discarded.

### @test

```python
@test
@test("description")
@test("description", name="id_part", timeout=10)
```

Register a test. Its id is `FILE_STEM/NAME`, NAME defaulting to the function's name. The description defaults to the first line of the docstring. `timeout` (seconds) overrides `DT_TIMEOUT` for this test.

### given

```python
given(*values, **named)
```

Describe the input under test, shown with every failure and crash that follows (DTP `input`). Strings are shown as they are, other values with `repr`: `given([3, 1, 2])`, `given(n=4, text="abc")`, `given("empty file")`.

### expect · require

```python
expect(cond, msg="expected a true value") -> bool
require(cond, msg="expected a true value") -> bool
```

Pass when `cond` is truthy. `require*` functions stop the test on failure; `expect*` functions continue. All return True when they pass.

### expect_eq · require_eq

```python
expect_eq(actual, expected, msg=None) -> bool
require_eq(actual, expected, msg=None) -> bool
```

Pass when `actual == expected`. Strings are compared as text (`cmp: "text"`, with a diff in the UI); other values are shown with `repr`.

### expect_ne

```python
expect_ne(actual, unexpected, msg=None) -> bool
```

Pass when `actual != unexpected`.

### expect_close

```python
expect_close(actual, expected, tol=1e-9, msg=None) -> bool
```

Pass when `actual` is a number within `tol` of `expected`. For floats.

### expect_type

```python
expect_type(value, typ, msg=None) -> bool
```

Pass when `isinstance(value, typ)`. Shows the type names.

### expect_raises

```python
expect_raises(exc_type, fn, *args, msg=None, **kwargs) -> bool
```

Call `fn(*args, **kwargs)` and pass if it raises `exc_type` (or a subclass). Reports "did not raise" or "raised the wrong exception".

### expect_output

```python
expect_output(fn, expected, *args, msg=None, **kwargs) -> bool
```

Call `fn(*args, **kwargs)` and compare what it prints on stdout with `expected` (text diff).

### capture_stdout

```python
with capture_stdout() as out:
    program.main()
out.text   # what was printed
```

Context manager capturing `sys.stdout`. `out.text` is filled when the block ends.

### fixture

```python
fixture(relpath) -> str
```

Path of a file in the group's fixtures folder.

### note

```python
note(msg)
```

Add a line to the test's details (DTP `log`).

### skip

```python
skip(reason="")
```

Stop the test and mark it `skip`.

### fail

```python
fail(msg) -> bool
```

Record an explicit failure; the test continues.

---

## 12. Protocol (DTP)

Summary of every element. The specification, with ordering rules, encoding and examples, is [protocol.md](protocol.md).

### DT_REPORT_FD

Environment variable set by the engine: the number of an open descriptor (a pipe) where the test process writes its DTP events, one JSON object per line. Unset when a person runs the program: print readable text instead.

### --list

Producer argument: emit `hello` and one `discover` per test, run nothing, exit. Must be fast (30 s maximum) and give the same ids every time.

### --run

Producer argument: `--run ID [ID…]` runs only those tests; an argument may be a DTP group (the id part before `/`). Unknown ids are ignored. Without arguments, a producer runs every test. The engine runs several `--run` processes in parallel with different subsets.

### hello

```json
{"t":"hello","protocol":1,"harness":"c"}
```

First event of every process. `protocol` (required): DTP version. `harness`: producer name.

### discover

```json
{"t":"discover","id":"ft_strlen/empty","name":"empty","desc":"…","file":"/abs/path.c","line":12}
```

A test exists (`--list` only). `id` required; `name`, `desc`, `file` (absolute), `line` optional. `file` and `line` let the UI show the test's code.

### start

```json
{"t":"start","id":"ft_strlen/empty"}
```

The test starts running. Must precede its other events.

### input

```json
{"t":"input","id":"ft_strlen/empty","value":"s=\"\""}
```

The input under test from now on, shown with failures, crashes and timeouts. Replaces the previous value.

### assert

```json
{"t":"assert","id":"…","ok":false,"msg":"…","expected":"…","actual":"…","input":"…","cmp":"text","file":"…","line":9}
```

A failed check. `id`, `ok`, `msg` required. `expected`/`actual`: the values, as text or bytes. `input`: this check's input (default: the current one). `cmp: "text"`: the values are texts to diff. `file`/`line`: where the check is. The engine keeps 30 per test.

### log

```json
{"t":"log","id":"…","msg":"…"}
```

A free note shown with the test.

### leak

```json
{"t":"leak","id":"…","bytes":12,"count":1}
```

Memory still allocated at the end of the test. Informational: the status comes with `end`.

### end

```json
{"t":"end","id":"…","status":"crash","ms":3,"exit":1,"signal":"SIGSEGV","reason":"…","output":"…"}
```

The test's result, exactly once per started test. `status` required (section 13). `ms` duration, `exit` exit code, `signal` signal name, `reason` one explanatory sentence, `output` what the test printed (truncated).

### done

```json
{"t":"done"}
```

Optional last event of a `--run`.

### cmp

Field of `assert`. `"text"` tells the UI that `expected` and `actual` are texts or byte strings: it shows where they first differ, the length difference, and invisible characters. Omit it for numbers, booleans and pointers.

### byte encoding

In `expected`, `actual` and `output`, each code point from U+0000 to U+00FF stands for one byte: `"aÿb"` is the bytes `61 FF 62`. The C harness escapes every byte outside printable ASCII that way, so any output round-trips exactly. Descriptive fields (`msg`, `desc`, `input`, `reason`) are UTF-8 text.

---

## 13. Statuses and grading

### statuses

| status | meaning | in the grade |
|---|---|---|
| `pass` | every check passed | passed |
| `fail` | a check failed | failed |
| `crash` | killed by a signal (segfault, abort, bus error…), an uncaught exception, or the process died mid-test | failed |
| `timeout` | took longer than the per-test timeout (infinite loop, blocking read) | failed |
| `leak` | all checks passed, memory left allocated | failed (passed with leak checks off) |
| `build_error` | the tests couldn't compile or load against the project, or the build failed | failed |
| `error` | the harness or runner failed | failed |
| `skip` | not run on purpose (condition, `dt_skip`, not selected in a re-run) | not counted |

### grade

Moulinette-style, per suite and for the whole run:

- The **mandatory** pass rate gives the grade, 0 to 100 (rounded down). Skipped tests don't count.
- **Bonus** tests add up to +25 (`25 × passed / total`), **only when mandatory is at 100**.
- `extra` groups are shown with their own pass rate but never graded.
- A failed **build** gives 0.
- A suite with only bonus tests gets 125 if they all pass, 0 otherwise.

### verdict

`ok` when the grade is at least 100 and neither norminette nor forbidden functions failed; `ko` otherwise. It's what the moulinette would say, roughly.

### flags

Problems an evaluator would object to, listed with the grade: `build`, `norminette`, `forbidden`, `relink`, `rules`, `files` (a check that failed). Any flag makes `dt run` exit with status 1.

---

## 14. Project checks

Listed in `[build] checks`. Each one is a stage of the run.

### rules

Check that the Makefile defines the rules in `[build] rules` (default `all`, `clean`, `fclean`, `re`, `$(NAME)`). Warns when the Makefile doesn't mention `-Wall -Wextra -Werror`.

### relink

Run the build a second time: it must not recompile or relink anything (artifacts unchanged, no `cc`/`ar` line in the output). If the Makefile has a `bonus` rule, `make bonus` twice is checked too (a warning when it relinks).

### norminette

Run `norminette` on the project (or `[norminette] paths`) when it is installed, and list each error with file, line, column and code. Skipped with an install hint when it's missing, or when disabled (`--no-norm`, `norminette` setting). Failing it makes the verdict `ko`.

### forbidden

List the external functions used by the project's artifacts (`nm -g`) and fail on any not in `[forbidden] allowed` / `allowed_regex`. Symbols inserted by the toolchain and sanitizers are ignored; `memset`, `memcpy`, `memmove` and `bzero` (often emitted by the compiler for struct copies) only give a warning. Without artifacts, `[forbidden] sources` are compiled to objects first. Failing it makes the verdict `ko`.

### files

Check that every glob of `[files] required` matches a file of the project.

---

## 15. Environment variables

### DT_HOME

Folder of the user's data (settings, installed suites, history). Default `~/.deepthought`.

### DT_CACHE

Folder for build artifacts and workspaces. Default, the first writable of: the `cache_dir` setting, `~/goinfre/.deepthought-cache` (on 42 machines), `/tmp/dt-$USER`, `~/.deepthought/cache`.

### DT_PYTHON

Python interpreter used by `./dt`, when the default one is too old.

### DT_NO_UPDATE

`1`: skip the automatic update at launch. Set by DeepThought itself when it restarts after updating.

### NO_COLOR

Set (to anything): the terminal reporter prints without colours.

### DT_PROJECT

Given to test processes: the workspace copy of the project. Python tests have it on `sys.path`.

### DT_SUITE

Given to test processes: the suite folder.

### DT_FIXTURES

Given to test processes: the group's fixtures folder. Used by `dt_fixture()` and `fixture()`.

### DT_TIMEOUT

Given to test processes: the per-test timeout in seconds (a float). The C and Python harnesses enforce it per test.

### DT_MATRIX_NAME

Given to test processes in a matrix group: `DT_MATRIX_BUFFER_SIZE=42`, one per matrix variable.

### test process variables

Also set by the engine: `PYTHONDONTWRITEBYTECODE=1` for Python tests (no `__pycache__` in the project), and in sanitizer mode `ASAN_OPTIONS=abort_on_error=1:detect_leaks=0:print_summary=1` and `UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1`. `DT_REPORT_FD`, `DT_NO_FORK` and `DT_OUTPUT_MAX` have their own entries.

---

## 16. Files and folders

### ~/.deepthought

The user's data folder (`$DT_HOME`). Never inside the repository, so updates never conflict with it.

```
~/.deepthought/
├── config.toml          settings that differ from the defaults
├── projects.json        your projects: type, linked suites, build options, last grade
├── suites.lock.json     installed git / zip / folder suites
├── suites/local/        suites created with `dt suite new`
├── suites/git/          cloned git suites
├── suites/zip/          extracted zip suites
├── history/<project>/   the last 50 runs of each project, as JSON
└── update.json          result of the last update check
```

### projects.json

The list of your projects. Each entry: `path`, `name`, `kind`, `kind_manual` (the user chose the type), `suites` (linked suite uids), `build` (saved build options: `command`, `make_args`, `env`, `clean`), `last_run`, `last_grade`. Edited through `dt project`, `dt run --save-build` and the UI.

### suites.lock.json

Every installed suite that isn't builtin, community or local: `id`, `source` (`git`, `zip`, `folder`), `origin` (URL or path), `path`, `version`, `installed` (timestamp) and, for git, the `ref` asked for. `dt suite update` uses it.

### history

`~/.deepthought/history/<project-key>/<run-id>.json`: the complete result of a run (every test, assert, stage, score). The last 50 runs per project are kept. Used for regressions, *Retest failed*, `dt history` and the History page.

### cache folder

Build artifacts, outside your home (42 home quotas are small): see `DT_CACHE`. Contains `ws/<project-key>/project` (the workspace copy of the project) and `ws/<project-key>/out/<suite>/<group>` (test binaries, one folder per group and matrix variant). Sanitizer runs use a separate `ws/<project-key>-…` folder. Safe to delete at any time; it's rebuilt on the next run.

### repository layout

```
dt                  launcher
deepthought/        the engine (Python, stdlib only)
  cli/  core/  runners/  checks/  server/  web/
  harness/c/        dt.h, dt_main.c, dt_alloc.c
  harness/python/   dtharness.py
suites/             official suites (get_next_line)
community/          community suites shipped with the tester (Sstyle: libft, ft_printf)
templates/suite/    scaffolds used by `dt suite new`
examples/           example projects and suites (Python, exec)
index.json          suites listed in Suites › Discover
docs/               this manual, writing-suites.md, protocol.md, architecture.md
tests/              the engine's own tests
```

### index.json

The list of suites shown in **Suites › Discover**. Each entry: `name`, `project`, `url` (git), `author`, `description`. Add yours with a pull request.

---

## 17. Settings (config.toml)

`~/.deepthought/config.toml`, edited in the UI's Settings page or by hand. Only values different from the defaults are written.

### cc

C compiler for test binaries. Default `cc`.

### cflags

Compiler flags for every test binary, before the suite's. Default `["-Wall", "-Wextra", "-g"]`.

### timeout

Default per-test timeout in seconds, when neither the group nor the suite sets one. Default `5.0`.

### jobs

Parallel jobs (compilations and test processes). Default: number of CPUs (at least 2).

### sanitize

Sanitizer mode by default. Default `false`.

### leaks

Leaks fail tests. Default `true`.

### norminette

Run norminette when a suite asks for it. Default `true`.

### cache_dir

Cache folder (see **DT_CACHE**). Default empty: automatic.

### theme

Web UI theme: `dark` or `light`. Default `dark`.

### port

Web UI port (the next free one is used if taken). Default `4242`.

### open_browser

`dt ui` opens the browser. Default `true`.

### check_updates

Check daily for updates and show a banner. Default `true`.

### auto_update

Update the tester at every launch. Default `true`.

### editor

Preferred editor for *Open in editor* links. Default `vscode`. The server opens files with VS Code's `code -g FILE:LINE` when it's installed, else with `open` (macOS) or `xdg-open` (Linux).

### disabled_suites

Uids of suites excluded from automatic runs (`dt suite disable`).

### python

Interpreter for Python tests. Default: the one running DeepThought. Set it by editing the file.

---

## 18. Web server and API

### web server

`dt ui` serves the interface and a JSON API on `127.0.0.1` only. Every API request needs the session token (in the URL printed in the terminal, then in the `dt_token` cookie or an `X-DT-Token` header); requests with a foreign `Host` header are refused (DNS rebinding protection). Run events are pushed with Server-Sent Events.

### API

| method | path | does |
|---|---|---|
| GET | `/api/state` | settings, projects, suites, runs, update status |
| POST | `/api/config` | change settings |
| POST, DELETE | `/api/projects` | add, remove a project |
| POST | `/api/projects/config` | set a project's type and linked suites |
| POST | `/api/projects/link` | link or unlink one suite |
| POST | `/api/projects/build` | save a project's build options |
| GET | `/api/projects/detect` | what would run for a folder |
| GET | `/api/history` | past runs of a project |
| POST | `/api/watch` | start or stop watching a project |
| POST | `/api/runs` | start a run |
| GET | `/api/runs/ID` | a run's complete state |
| POST | `/api/runs/ID/cancel` | cancel |
| POST | `/api/runs/ID/rerun` | re-run (all, failed, or chosen tests) |
| GET | `/api/suites` | installed suites and suites with errors |
| POST | `/api/suites/add`, `/upload`, `/inspect`, `/new`, `/reload` | install from git / folder, from a zip, preview, scaffold, reload |
| POST | `/api/suites/UID/update`, `/enable` | update, enable or disable |
| DELETE | `/api/suites/UID` | remove |
| GET | `/api/suites/UID/pack` | download as zip |
| GET | `/api/index` | the Discover list |
| POST | `/api/self/check`, `/api/self/update` | check for and apply a tester update |
| GET | `/api/fs/browse` | folder picker (unreadable entries are marked `locked`) |
| POST | `/api/open` | open a file in the editor |
| GET | `/api/events` | the SSE stream |

### run events

Events on the SSE stream, all with `type` and `run_id`:

| type | payload |
|---|---|
| `run` | a summary of the run when it starts running and when it ends (status, score) |
| `stage` | a stage (build, check, fetch) started or finished |
| `group` | a group's status changed (compiling, running, done, skipped, build error) |
| `tests` | a group discovered its tests: all of them, pending |
| `test` | one test changed (running, finished with its status, asserts, logs, output) |
| `snapshot` | the complete state of a run: when it is created (every test pending) and when it ends (final result) |

The terminal reporter and the TUI consume the same events.
