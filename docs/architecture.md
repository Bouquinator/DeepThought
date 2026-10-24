# How DeepThought works

## Goals and constraints

- **Zero install** on 42 machines (no sudo, small home quota): the engine is Python ≥ 3.10 **standard library only**, and the web UI is plain ES modules with **no build step** (Preact + htm vendored as one file). `git clone` + `./dt` is the whole installation.
- **Any number of suites, for any project, from anywhere**: built-in, your own, a friend's git repo, a zip.
- **Never touch the student's folder**: everything is built in an isolated copy.
- **Explain failures**: every result carries the test's code, a diff with visible characters, the reason (signal, timeout, leak, sanitizer report) and a command to reproduce it.
- **Self-updating**: the tester is a git clone and updates itself with `git pull --ff-only`.

## Layout

```
dt                         launcher (sh): finds Python ≥ 3.10, runs `python3 -m deepthought`
deepthought/
  cli/        main.py (commands) · reporter_plain.py (terminal/CI output) · tui.py (curses UI)
  core/       the engine
    executor.py    RunManager: plans and executes runs, publishes events
    manifest.py    suite.toml parsing and validation (the authoring contract)
    registry.py    installed suites from every source + suites.lock.json
    sources/       git.py (clone/pull/status) · archive.py (safe zip extract/pack)
    project.py     project detection ([detect] scoring) + remembered projects
    workspace.py   isolated, incremental copy of the project
    proc.py        subprocesses: timeouts, process-group kill, output caps, cancellation
    dtp.py         DeepThought Test Protocol parsing
    scoring.py     moulinette-like grade (suite errors are left out: verdict "incomplete")
    history.py     run history, regressions/fixes vs the previous run
    watch.py       file watcher (polling, debounced)
    selfupdate.py  git fetch / pull --ff-only of the tester itself
    config.py      ~/.deepthought/config.toml · paths.py · toml.py (tomllib or vendored tomli)
  runners/    c_unit.py · exec_cases.py · python_unit.py · script.py  (base.py: interface + DTP process runner)
  checks/     make.py (build, rules, relink) · norminette.py · forbidden.py · files.py
  harness/    c/ (dt.h, dt_main.c, dt_alloc.c) · python/dtharness.py
  server/     app.py (HTTP + auth) · api.py (JSON routes) · sse.py (live events)
  web/        index.html · app.js (store, router, SSE) · components/*.js · styles/app.css · vendor/
  manual/     `dt man` web manual: markdown.py (docs → HTML) · build.py · page.html (standalone page, no server)
suites/       official suites (get_next_line)
community/    bundled community suites (sstyle: SStyles93's libft and ft_printf tests, ported)
templates/    scaffolds for `dt suite new` (one per runner)
examples/     complete example projects + suites (python-unit, exec)
tests/        the engine's own tests + fixture projects (reference and deliberately broken)
```

User data lives **outside the repo**, so `git pull` never conflicts:

```
~/.deepthought/            (override with $DT_HOME)
  config.toml              settings changed from the defaults
  suites.lock.json         installed git / zip / folder suites (source, origin, sha…)
  suites/local|git|zip/    suites created or installed by the user
  projects.json            your projects: own type, linked suites, build options, last grade
  history/<project>/       one JSON file per run (last 50)
  update.json              cached update check
/tmp/dt-$USER/ or ~/goinfre/.deepthought-cache   (override with $DT_CACHE)
  ws/<project-hash>/project/   the isolated copy (builds happen here)
  ws/<project-hash>/out/       compiled test binaries, one folder per group
```

## A run, step by step

```
RunManager.start(project, suites?, options)
 1. resolve suites   explicit ids › suites the user linked to the project › every enabled suite of the
                     user's project type › detect(): best-scoring project kind → all its enabled suites
 1b. fetch           [[fetch]] dependencies of the suites (pinned git checkouts, downloaded once)
 2. plan             stages (workspace, build per distinct command, checks) and groups
                     (matrix expanded; carried-over results for "retest failed")
 3. workspace        incremental mirror of the project (mtime+size), ignores .git, *.o, *.a, binaries;
                     only deletes files it copied itself, so make's products survive → incremental builds
 4. build            the project's build override, else [build].command, plus extra make args
                     and env from the project's build options (projects.json), once per distinct
                     command; Python suites without a command get an ast-based syntax check
                     (failure → every group build_error)
 5. checks           rules, relink, files, forbidden (sequential: they touch build products),
                     norminette in parallel with the tests
 6. groups           in a thread pool; per group:
                       when → skip?   before commands (once per run)   runner.prepare()  (compile, cached by
                       content hash)   runner.discover() (--list)   runner.run(ids) in parallel shards
 7. score            per suite + overall; flags (norminette, forbidden, relink…)
 8. history          compare with the previous run of the same flavour → regression / fixed marks; save
```

Concurrency is bounded by a semaphore (`jobs`, default = CPU count) around every subprocess. Cancelling a run kills every live process group.

## Isolation of a single test

C and Python harnesses fork **one process per test**, with a timer (`setitimer` → `SIGALRM` = timeout). The parent reads the child's exit status: a signal means `crash`, `SIGALRM` means `timeout`, and exit codes mean pass/fail/skip/leak. A test that stops itself with `dt_error` reports its own `end` (status `suite_error`, with its reason) and exits with code 5, so the parent adds nothing. Test stdout/stderr go to a temp file that is attached to the result. The engine adds a global time budget per process group as a safety net. With `DT_NO_FORK=1` the tests run in-process, and a stopped test (`DT_ASSERT`, `dt_skip`, `dt_error`) jumps back to the runner with `longjmp`.

**Leak detection and malloc-failure injection** without valgrind: `dt_alloc.c` defines `malloc`/`calloc`/`realloc`/`free` in the test binary.
- On macOS (two-level namespaces) only code linked into the binary reaches them, and they forward to libc through `dlsym(RTLD_NEXT)`.
- On glibc they interpose process-wide and forward to `__libc_malloc`, so only callers inside the executable's text segment are tracked (libc's own allocations, like stdio buffers, are ignored).

Allocations are kept in a static hash table. Whatever is still allocated when the test function returns is a leak.

**Sanitizer mode** rebuilds both the project (`make CFLAGS=…`) and the tests with `-fsanitize=address,undefined` in a separate workspace (`<hash>-asan`), disables the malloc hooks, and turns the sanitizer report into the test's reason (`undefined behaviour at part2.c:67:17: negation of -2147483648…`).

## Events and interfaces

Every state change is published on an in-process `EventBus`:

| event | payload |
|---|---|
| `snapshot` | full run (created / finished) |
| `run` | summary (status, score) |
| `stage` | one stage |
| `group` | one group (without tests) |
| `tests` | discovered tests of a group |
| `test` | one test result |
| `watch`, `update` | watch mode toggled, update status |

Three consumers use the same events:
- **Web UI**: the server streams them over Server-Sent Events (`/api/events`), and the browser store applies them as patches.
- **Terminal reporter** (`dt run`): progress bar, group lines, failure details, exit code for CI, `--json`/`--junit` export.
- **TUI** (`dt tui`): curses tree + details.

## Web server and security

`ThreadingHTTPServer` bound to `127.0.0.1`:
- A random token is printed in the startup URL and stored in an HttpOnly, SameSite=Strict cookie. Every `/api/*` request needs it.
- Requests whose `Host` header is not local are rejected (DNS-rebinding protection).
- Static files are served only from `deepthought/web/`.

The API is listed in `deepthought/server/api.py` (≈25 routes: projects, runs, re-run, cancel, suites import/update/export, config, self-update, folder browser, open-in-editor).

Foreign suites run arbitrary code, by design (they are tests). The UI and CLI show a trust prompt before installing one, git suites are pinned by commit in the lockfile, and zip extraction rejects path traversal.

## Self-update

**At every launch** (`auto_update` setting, on by default), `./dt` runs a quick non-interactive `git fetch` (6 s timeout, SSH in batch mode). If the tester is behind and the clone is clean (no local changes, no local commits), it runs `git pull --ff-only` and re-executes itself on the new code (`DT_NO_UPDATE=1` prevents a loop). Offline, diverged or modified clones are left alone with a one-line note. `--no-update` or `DT_NO_UPDATE=1` skip it.

`./dt update` (or the banner in the UI):
1. `git fetch`.
2. Refuse when tracked files were modified locally. User suites belong in `~/.deepthought`, never in the repo.
3. `git pull --ff-only`.
4. Update every git suite.

A background check runs at most once a day (`check_updates` setting), and the result is cached in `update.json` to drive the banners. Suites declare `engine = ">=x.y"`: incompatible suites are flagged instead of failing mysteriously.

## Extending DeepThought

- **A new suite**: no code change. See [writing-suites.md](writing-suites.md).
- **An existing tester**: port its tests (labelled checks make this mostly mechanical, see [`community/sstyle`](../community/sstyle)), or wrap it untouched with `[[fetch]]` and an adapter or a `script` runner.
- **A new language with function-level tests**: write a harness that speaks [DTP](protocol.md) and a runner subclassing `DTPProcessRunner` (implement `command()` and optionally `prepare()`), then register it in `runners/__init__.py` and `manifest.RUNNERS`. `python_unit.py` is a 30-line example.
- **A new project check**: a function `(ctx, suite, stage)` that fills the `StageState`, registered in `checks/__init__.py` and `manifest.CHECKS`.
- **The UI**: edit the files in `deepthought/web/`. There is no build step, so reload the page.

## Tests

```sh
python3 -m unittest discover -s tests -t .
```

This covers manifest validation, workspace sync, scoring, the registry (folder/zip/git, zip-slip), self-update against a local upstream, the HTTP API and its security checks, and end-to-end runs. The end-to-end runs check that every planted bug in `tests/fixtures/libft_broken` gets exactly the expected status (using `tests/fixtures/engine-suite`, a test-only libft subset), that the reference get_next_line passes 100%, that custom project types and linked suites resolve correctly, that the Sstyle suites give the expected verdicts on the reference libft and ft_printf, and that suite problems (`dt_error`, `error()`, a missing `stdin_file`, a group without tests, a missing gnl fixture) are reported apart and never graded, with or without fork.
