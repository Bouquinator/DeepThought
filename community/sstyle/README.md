# Sstyle suite

Tests written by **SStyles93** for the [CodeTester](https://github.com/SStyles93/42_CodeTester), ported to DeepThought with the author's permission.

| suite | project | contents |
|---|---|---|
| `sstyle-libft` | libft | every function of Part 1 and 2 (one test per case), a **Memory** group (each allocating function: no leak, and NULL without leaking when any of its mallocs fails), bonus lists |
| `sstyle-ft_printf` | ft_printf | **Mandatory**: each conversion compared with the system's `printf` (bytes and return value), behaviour (no buffering, -1 on write errors, malloc failures), the subject's requirements (files, Makefile, relink, `nm`). **Bonus**: flags and the bonus rule. **Original printf behaviour**: undefined-behaviour cases, informational (not graded) |

## How it was ported

The CodeTester's cases, inputs, expected values and labels are unchanged. Only the plumbing changed:

- each `test_ft_x(t_ctx *)` suite became `DT_TEST`s, split along the author's case comments (`/* truncation: size smaller than src */` → `ft_strlcpy/truncation`). Labelled helper calls became one test per call. Suites whose cases build on each other (the list functions) stay one test, run in order;
- `check_*(ctx, label, expected, got)` became DeepThought's labelled checks `DT_CHECK_*(label, got, expected)`, so every failure shows the author's label with expected and got;
- the memory checks (Linux-only `--wrap=malloc` in the CodeTester) use DeepThought's allocation hooks and now also run on macOS;
- crash-prone cases (`ft_printf(NULL)`, trailing `%`) are their own tests, since every DeepThought test is its own process;
- one test file per function (`split = true`): a missing function only fails its own tests.

Missing cases or a wrong expectation? Tell the author [upstream](https://github.com/SStyles93/42_CodeTester) and update the port here.
