# Sstyle suite

DeepThought community suites wrapping **[SStyles93's CodeTester](https://github.com/SStyles93/42_CodeTester)**, an interactive C tester for 42's libft and ft_printf.

| suite | project | what it runs |
|---|---|---|
| `sstyle-libft` | libft | the CodeTester's 43 function suites (lists as bonus) + its `memory` suite (malloc failures, Linux only) |
| `sstyle-ft_printf` | ft_printf | `Printf_mandatory` (conversions, behaviour, subject requirements), `Printf_bonus` (flags), `Printf_original` (informational: not graded) |

## How it works

- **The tests are the CodeTester's, unmodified.** On first use DeepThought downloads the repository, pinned to a commit (`[[fetch]]` in each `suite.toml`), into `upstream/` (git-ignored).
- The CodeTester's own sources are compiled with your library: `src/utils.c`, `src/runner.c`, `src/memcheck.c`, and every file of `tests/`. Only its command-line entry point (`src/main.c`, `src/menu.c`) is replaced by [`adapter/dt_sstyle.c`](adapter/dt_sstyle.c).
- The adapter registers **each CodeTester suite as one DeepThought test** and runs it with the CodeTester's own `run_suite()` in verbose mode. Each `✗` line of its report becomes a failure with expected / actual values. The full report is the test's output, and the test's source is the CodeTester function.
- Link flags follow the CodeTester's Makefile: the whole `libft.a` (`-all_load` / `--whole-archive`) and `-u ft_printf`. On Linux, `--wrap=malloc` enables its memory suites.
- `ft_printf`'s groups run one after another (`sequential = true`), because `printf_project` runs `make` inside the project.

## Updating

To follow a newer CodeTester, change `ref` in both `suite.toml` files (a commit hash) and run `./dt suite update sstyle-libft`. The tests belong to their author: report missing cases or bugs [upstream](https://github.com/SStyles93/42_CodeTester).
