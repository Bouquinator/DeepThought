/*
** dt_main.c — test registry and runner for the DeepThought C harness.
**
**   ./tests --list                 print discovered tests
**   ./tests [--run ID|GROUP ...]   run all tests or a selection
**
** Environment:
**   DT_REPORT_FD   write DTP JSON lines to this fd (else readable text)
**   DT_TIMEOUT     per-test timeout in seconds (float, default 5)
**   DT_NO_FORK=1   run tests in-process (for debuggers)
**   DT_FIXTURES    directory used by dt_fixture()
**   DT_OUTPUT_MAX  bytes of test stdout/stderr to keep (default 4096)
*/

#ifndef _GNU_SOURCE
# define _GNU_SOURCE
#endif
#include "dt.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <sys/time.h>
#include <sys/wait.h>

#define DT_MAX_TESTS 4096
#define EXIT_PASS 0
#define EXIT_FAIL 1
#define EXIT_SKIP 2
#define EXIT_LEAK 3

static t_dt_test	g_tests[DT_MAX_TESTS];
static int			g_count = 0;
static int			g_json = 0;
static int			g_out = 2;
static int			g_failed = 0;
static int			g_in_child = 0;
static int			g_nofork = 0;
static const char	*g_current = "";
static char			g_input[1024];

/* ------------------------------------------------------------ output */

static void	out_raw(const char *s, size_t n)
{
	ssize_t	w;

	while (n > 0)
	{
		w = write(g_out, s, n);
		if (w < 0 && errno == EINTR)
			continue ;
		if (w <= 0)
			return ;
		s += w;
		n -= (size_t)w;
	}
}

/* growable buffer built with the raw allocator so it is never tracked */
typedef struct s_buf
{
	char	*d;
	size_t	len;
	size_t	cap;
}	t_buf;

static void	buf_put(t_buf *b, const char *s, size_t n)
{
	char	*nd;

	if (b->len + n + 1 > b->cap)
	{
		b->cap = (b->len + n + 1) * 2;
		nd = dt_raw_malloc(b->cap);
		if (!nd)
			return ;
		if (b->d)
			memcpy(nd, b->d, b->len);
		dt_raw_free(b->d);
		b->d = nd;
	}
	memcpy(b->d + b->len, s, n);
	b->len += n;
	b->d[b->len] = 0;
}

static void	buf_str(t_buf *b, const char *s)
{
	buf_put(b, s, strlen(s));
}

/* JSON string; bytes outside printable ASCII become \u00XX (lossless) */
static void	buf_json(t_buf *b, const char *s, size_t n)
{
	static const char	hex[] = "0123456789abcdef";
	char				esc[7];
	size_t				i;
	unsigned char		c;

	buf_put(b, "\"", 1);
	i = 0;
	while (s && i < n)
	{
		c = (unsigned char)s[i++];
		if (c == '"' || c == '\\')
		{
			esc[0] = '\\';
			esc[1] = (char)c;
			buf_put(b, esc, 2);
		}
		else if (c < 0x20 || c >= 0x7f)
		{
			memcpy(esc, "\\u00", 4);
			esc[4] = hex[c >> 4];
			esc[5] = hex[c & 15];
			buf_put(b, esc, 6);
		}
		else
			buf_put(b, (char *)&c, 1);
	}
	buf_put(b, "\"", 1);
}

static void	buf_kv(t_buf *b, const char *key, const char *val)
{
	buf_str(b, ",\"");
	buf_str(b, key);
	buf_str(b, "\":");
	buf_json(b, val, val ? strlen(val) : 0);
}

static void	buf_kvn(t_buf *b, const char *key, long long val)
{
	char	num[32];

	snprintf(num, sizeof(num), ",\"%s\":%lld", key, val);
	buf_str(b, num);
}

static void	emit(t_buf *b)
{
	buf_str(b, "}\n");
	out_raw(b->d, b->len);
	dt_raw_free(b->d);
	b->d = NULL;
}

static void	begin(t_buf *b, const char *type)
{
	b->d = NULL;
	b->len = 0;
	b->cap = 0;
	buf_str(b, "{\"t\":");
	buf_json(b, type, strlen(type));
}

static void	human(const char *fmt, ...)
{
	char	line[2048];
	va_list	ap;
	int		n;

	va_start(ap, fmt);
	n = vsnprintf(line, sizeof(line), fmt, ap);
	va_end(ap);
	if (n > (int)sizeof(line) - 1)
		n = sizeof(line) - 1;
	if (n > 0)
		out_raw(line, (size_t)n);
}

/* ------------------------------------------------------------ registry */

void	dt_register(t_dt_test test)
{
	if (g_count < DT_MAX_TESTS)
		g_tests[g_count++] = test;
}

static void	test_id(const t_dt_test *t, char *dst, size_t n)
{
	snprintf(dst, n, "%s/%s", t->group, t->name);
}

const char	*dt_fixture(const char *relpath)
{
	static char	path[4096];
	const char	*dir;

	dir = getenv("DT_FIXTURES");
	if (!dir || relpath[0] == '/')
		return (relpath);
	snprintf(path, sizeof(path), "%s/%s", dir, relpath);
	return (path);
}

/* ------------------------------------------------------------ checks */

static void	child_end(int code)
{
	fflush(stdout);
	fflush(stderr);
	if (g_nofork)
		return ;
	_exit(code);
}

static int	g_textual;	/* the values being reported are compared texts / bytes */

static void	report_assert(int ok, const char *expr, const char *exp,
	size_t elen, const char *act, size_t alen, const char *file, int line)
{
	t_buf	b;

	if (!g_json)
	{
		if (!ok)
			human("    \x1b[31m✗\x1b[0m %s:%d  %s\n%s%s%s        expected: %.*s\n"
				"        actual:   %.*s\n", file, line, expr,
				g_input[0] ? "        input:    " : "", g_input, g_input[0] ? "\n" : "",
				(int)elen, exp ? exp : "(null)", (int)alen,
				act ? act : "(null)");
		return ;
	}
	begin(&b, "assert");
	buf_kv(&b, "id", g_current);
	buf_str(&b, ok ? ",\"ok\":true" : ",\"ok\":false");
	buf_kv(&b, "msg", expr);
	if (g_input[0])
		buf_kv(&b, "input", g_input);
	if (g_textual)
		buf_str(&b, ",\"cmp\":\"text\"");
	buf_str(&b, ",\"expected\":");
	buf_json(&b, exp, exp ? elen : 0);
	buf_str(&b, ",\"actual\":");
	buf_json(&b, act, act ? alen : 0);
	buf_kv(&b, "file", file);
	buf_kvn(&b, "line", line);
	emit(&b);
}

static int	finish_check(int ok, int fatal)
{
	if (!ok)
	{
		g_failed++;
		if (fatal && g_in_child)
			child_end(EXIT_FAIL);
	}
	return (ok);
}

int	dt_check(int ok, int fatal, const char *expr, const char *expected,
	const char *actual, const char *file, int line)
{
	if (!ok)
		report_assert(0, expr, expected, strlen(expected), actual,
			strlen(actual), file, line);
	return (finish_check(ok, fatal));
}

int	dt_check_int(long long actual, long long expected, int fatal,
	const char *expr, const char *file, int line)
{
	char	a[32];
	char	e[32];

	if (actual != expected)
	{
		snprintf(a, sizeof(a), "%lld", actual);
		snprintf(e, sizeof(e), "%lld", expected);
		report_assert(0, expr, e, strlen(e), a, strlen(a), file, line);
	}
	return (finish_check(actual == expected, fatal));
}

int	dt_check_uint(unsigned long long actual, unsigned long long expected,
	int fatal, const char *expr, const char *file, int line)
{
	char	a[32];
	char	e[32];

	if (actual != expected)
	{
		snprintf(a, sizeof(a), "%llu", actual);
		snprintf(e, sizeof(e), "%llu", expected);
		report_assert(0, expr, e, strlen(e), a, strlen(a), file, line);
	}
	return (finish_check(actual == expected, fatal));
}

int	dt_check_sign(long long actual, long long expected, int fatal,
	const char *expr, const char *file, int line)
{
	int		sa;
	int		se;
	char	a[64];
	char	e[64];

	sa = (actual > 0) - (actual < 0);
	se = (expected > 0) - (expected < 0);
	if (sa != se)
	{
		snprintf(a, sizeof(a), "%lld (sign %+d)", actual, sa);
		snprintf(e, sizeof(e), "%lld (sign %+d)", expected, se);
		report_assert(0, expr, e, strlen(e), a, strlen(a), file, line);
	}
	return (finish_check(sa == se, fatal));
}

int	dt_check_bool(long long actual, long long expected, int fatal,
	const char *expr, const char *file, int line)
{
	int	ok;

	ok = (!actual == !expected);
	if (!ok)
		report_assert(0, expr, expected ? "true" : "false", strlen(expected ? "true" : "false"),
			actual ? "true" : "false", strlen(actual ? "true" : "false"), file, line);
	return (finish_check(ok, fatal));
}

int	dt_check_char(char actual, char expected, int fatal,
	const char *expr, const char *file, int line)
{
	return (dt_check_bytes(&actual, 1, &expected, 1, fatal, expr, file, line));
}

void	dt_failf_at(const char *file, int line, const char *fmt, ...)
{
	char	msg[1024];
	va_list	ap;

	va_start(ap, fmt);
	vsnprintf(msg, sizeof(msg), fmt, ap);
	va_end(ap);
	dt_check(0, 0, msg, "", "", file, line);
}

int	dt_check_ptr(const void *actual, const void *expected, int fatal,
	const char *expr, const char *file, int line)
{
	char	a[32];
	char	e[32];

	if (actual != expected)
	{
		snprintf(a, sizeof(a), "%p", actual);
		snprintf(e, sizeof(e), "%p", expected);
		report_assert(0, expr, e, strlen(e), a, strlen(a), file, line);
	}
	return (finish_check(actual == expected, fatal));
}

int	dt_check_str(const char *actual, const char *expected, int fatal,
	const char *expr, const char *file, int line)
{
	int	ok;

	if (!actual || !expected)
		ok = (actual == expected);
	else
		ok = (strcmp(actual, expected) == 0);
	if (!ok)
	{
		g_textual = (actual && expected);
		report_assert(0, expr,
			expected ? expected : "(null)", strlen(expected ? expected : "(null)"),
			actual ? actual : "(null)", strlen(actual ? actual : "(null)"),
			file, line);
		g_textual = 0;
	}
	return (finish_check(ok, fatal));
}

int	dt_check_bytes(const void *actual, size_t alen, const void *expected,
	size_t elen, int fatal, const char *expr, const char *file, int line)
{
	int	ok;

	ok = (alen == elen && (alen == 0 || memcmp(actual, expected, alen) == 0));
	if (!ok)
	{
		g_textual = 1;
		report_assert(0, expr, expected, elen, actual, alen, file, line);
		g_textual = 0;
	}
	return (finish_check(ok, fatal));
}

int	dt_check_mem(const void *actual, const void *expected, size_t n,
	int fatal, const char *expr, const char *file, int line)
{
	if (!actual || !expected)
		return (dt_check(actual == expected, fatal, expr,
				expected ? "memory" : "NULL", actual ? "memory" : "NULL",
				file, line));
	return (dt_check_bytes(actual, n, expected, n, fatal, expr, file, line));
}

void	dt_fail(const char *msg, const char *file, int line)
{
	dt_check(0, 0, msg, "", "", file, line);
}

void	dt_note(const char *fmt, ...)
{
	char	msg[1024];
	va_list	ap;
	t_buf	b;

	va_start(ap, fmt);
	vsnprintf(msg, sizeof(msg), fmt, ap);
	va_end(ap);
	if (!g_json)
	{
		human("    · %s\n", msg);
		return ;
	}
	begin(&b, "log");
	buf_kv(&b, "id", g_current);
	buf_kv(&b, "msg", msg);
	emit(&b);
}

void	dt_input(const char *fmt, ...)
{
	va_list	ap;
	t_buf	b;

	va_start(ap, fmt);
	vsnprintf(g_input, sizeof(g_input), fmt, ap);
	va_end(ap);
	if (!g_json)
		return ;
	begin(&b, "input");
	buf_kv(&b, "id", g_current);
	buf_kv(&b, "value", g_input);
	emit(&b);
}

void	dt_skip(const char *reason)
{
	dt_note("skipped: %s", reason);
	if (g_in_child)
		child_end(EXIT_SKIP);
}

/* ------------------------------------------------------------ capture */

int	dt_capture_begin(int fd)
{
	char	tmpl[] = "/tmp/dt_capture_XXXXXX";
	int		saved;
	int		tmp;

	if (fd == 1)
		fflush(stdout);
	if (fd == 2)
		fflush(stderr);
	saved = dup(fd);
	tmp = mkstemp(tmpl);
	if (tmp < 0)
		return (saved);
	unlink(tmpl);
	dup2(tmp, fd);
	close(tmp);
	return (saved);
}

void	dt_capture_end(int fd, int token, t_dt_capture *out)
{
	off_t	size;
	ssize_t	r;
	size_t	got;

	if (fd == 1)
		fflush(stdout);
	if (fd == 2)
		fflush(stderr);
	out->data = NULL;
	out->len = 0;
	size = lseek(fd, 0, SEEK_END);
	if (size > 0 && lseek(fd, 0, SEEK_SET) == 0)
	{
		out->data = dt_raw_malloc((size_t)size + 1);
		got = 0;
		while (out->data && got < (size_t)size)
		{
			r = read(fd, out->data + got, (size_t)size - got);
			if (r <= 0)
				break ;
			got += (size_t)r;
		}
		out->len = got;
		if (out->data)
			out->data[got] = 0;
	}
	dup2(token, fd);
	close(token);
}

void	dt_capture_free(t_dt_capture *cap)
{
	dt_raw_free(cap->data);
	cap->data = NULL;
	cap->len = 0;
}

/* ------------------------------------------------------------ running */

static const char	*signame(int sig)
{
	if (sig == SIGSEGV)
		return ("SIGSEGV");
	if (sig == SIGBUS)
		return ("SIGBUS");
	if (sig == SIGABRT)
		return ("SIGABRT");
	if (sig == SIGFPE)
		return ("SIGFPE");
	if (sig == SIGILL)
		return ("SIGILL");
	if (sig == SIGKILL)
		return ("SIGKILL");
	if (sig == SIGPIPE)
		return ("SIGPIPE");
	if (sig == SIGTRAP)
		return ("SIGTRAP");
	return ("SIGNAL");
}

static const char	*sigexplain(int sig)
{
	if (sig == SIGSEGV)
		return ("segmentation fault: invalid memory access (NULL or freed pointer, out of bounds)");
	if (sig == SIGBUS)
		return ("bus error: invalid or misaligned memory access");
	if (sig == SIGABRT)
		return ("abort: often a double free or a corrupted heap");
	if (sig == SIGFPE)
		return ("arithmetic error (e.g. division by zero)");
	return ("killed by a signal");
}

static double	now_ms(void)
{
	struct timeval	tv;

	gettimeofday(&tv, NULL);
	return (tv.tv_sec * 1000.0 + tv.tv_usec / 1000.0);
}

static void	set_timer(double seconds)
{
	struct itimerval	it;

	memset(&it, 0, sizeof(it));
	it.it_value.tv_sec = (time_t)seconds;
	it.it_value.tv_usec = (suseconds_t)((seconds - (double)(time_t)seconds) * 1e6);
	setitimer(ITIMER_REAL, &it, NULL);
}

static int	child_run(const t_dt_test *t, int outfd)
{
	size_t	bytes;
	size_t	count;
	t_buf	b;

	g_in_child = 1;
	if (outfd >= 0)
	{
		dup2(outfd, 1);
		dup2(outfd, 2);
		close(outfd);
	}
	g_failed = 0;
	g_input[0] = 0;
	dt_alloc_start();
	t->fn();
	dt_alloc_stop();
	if (dt_alloc_leaks(&bytes, &count))
	{
		if (g_json)
		{
			begin(&b, "leak");
			buf_kv(&b, "id", g_current);
			buf_kvn(&b, "bytes", (long long)bytes);
			buf_kvn(&b, "count", (long long)count);
			emit(&b);
		}
		else
			human("    \x1b[33m⚠\x1b[0m leaked %zu bytes in %zu allocation(s)\n",
				bytes, count);
		if (!g_failed)
			return (EXIT_LEAK);
	}
	return (g_failed ? EXIT_FAIL : EXIT_PASS);
}

static void	read_output(int fd, char **data, size_t *len)
{
	char	*max_env;
	size_t	max;
	off_t	size;
	ssize_t	r;

	*data = NULL;
	*len = 0;
	max_env = getenv("DT_OUTPUT_MAX");
	max = max_env ? (size_t)atol(max_env) : 4096;
	size = lseek(fd, 0, SEEK_END);
	if (size <= 0 || lseek(fd, 0, SEEK_SET) != 0)
		return ;
	if ((size_t)size < max)
		max = (size_t)size;
	*data = dt_raw_malloc(max + 1);
	if (!*data)
		return ;
	r = read(fd, *data, max);
	*len = r > 0 ? (size_t)r : 0;
	(*data)[*len] = 0;
}

static void	report_end(const char *status, double ms, int sig, int code,
	const char *output, size_t outlen)
{
	t_buf	b;

	if (!g_json)
	{
		human("  %s %s \x1b[2m(%.0f ms)\x1b[0m%s%s\n",
			!strcmp(status, "pass") ? "\x1b[32mPASS   \x1b[0m"
			: !strcmp(status, "skip") ? "\x1b[2mSKIP   \x1b[0m"
			: !strcmp(status, "leak") ? "\x1b[33mLEAK   \x1b[0m"
			: !strcmp(status, "timeout") ? "\x1b[35mTIMEOUT\x1b[0m"
			: !strcmp(status, "crash") ? "\x1b[31mCRASH  \x1b[0m"
			: "\x1b[31mFAIL   \x1b[0m", g_current, ms,
			sig ? "  " : "", sig ? sigexplain(sig) : "");
		if (outlen)
			human("    output:\n%.*s\n", (int)outlen, output);
		return ;
	}
	begin(&b, "end");
	buf_kv(&b, "id", g_current);
	buf_kv(&b, "status", status);
	buf_kvn(&b, "ms", (long long)ms);
	if (sig)
	{
		buf_kv(&b, "signal", signame(sig));
		buf_kv(&b, "reason", sigexplain(sig));
	}
	if (code >= 0)
		buf_kvn(&b, "exit", code);
	if (outlen)
	{
		buf_str(&b, ",\"output\":");
		buf_json(&b, output, outlen);
	}
	emit(&b);
}

static void	run_one(const t_dt_test *t, double timeout)
{
	char		id[512];
	char		tmpl[] = "/tmp/dt_out_XXXXXX";
	t_buf		b;
	pid_t		pid;
	int			status;
	int			outfd;
	double		start;
	char		*output;
	size_t		outlen;
	int			code;

	test_id(t, id, sizeof(id));
	g_current = id;
	if (g_json)
	{
		begin(&b, "start");
		buf_kv(&b, "id", id);
		emit(&b);
	}
	start = now_ms();
	if (g_nofork)
	{
		code = child_run(t, -1);
		report_end(code == EXIT_PASS ? "pass" : code == EXIT_LEAK ? "leak"
			: "fail", now_ms() - start, 0, -1, NULL, 0);
		return ;
	}
	outfd = mkstemp(tmpl);
	if (outfd >= 0)
		unlink(tmpl);
	fflush(stdout);
	fflush(stderr);
	pid = fork();
	if (pid == 0)
	{
		set_timer(timeout);
		child_end(child_run(t, outfd));
	}
	while (waitpid(pid, &status, 0) < 0 && errno == EINTR)
		;
	read_output(outfd, &output, &outlen);
	if (outfd >= 0)
		close(outfd);
	if (WIFSIGNALED(status) && WTERMSIG(status) == SIGALRM)
	{
		g_current = id;
		report_end("timeout", now_ms() - start, 0, -1, output, outlen);
	}
	else if (WIFSIGNALED(status))
		report_end("crash", now_ms() - start, WTERMSIG(status), -1, output, outlen);
	else
	{
		code = WEXITSTATUS(status);
		report_end(code == EXIT_PASS ? "pass" : code == EXIT_FAIL ? "fail"
			: code == EXIT_SKIP ? "skip" : code == EXIT_LEAK ? "leak" : "error",
			now_ms() - start, 0, code, output, outlen);
	}
	dt_raw_free(output);
}

static int	selected(const t_dt_test *t, int argc, char **argv, int first)
{
	char	id[512];
	int		i;

	if (first >= argc)
		return (1);
	test_id(t, id, sizeof(id));
	i = first;
	while (i < argc)
	{
		if (!strcmp(argv[i], id) || !strcmp(argv[i], t->group))
			return (1);
		i++;
	}
	return (0);
}

static void	list_tests(void)
{
	char	id[512];
	t_buf	b;
	int		i;

	i = 0;
	while (i < g_count)
	{
		test_id(&g_tests[i], id, sizeof(id));
		if (g_json)
		{
			begin(&b, "discover");
			buf_kv(&b, "id", id);
			buf_kv(&b, "group", g_tests[i].group);
			buf_kv(&b, "name", g_tests[i].name);
			buf_kv(&b, "desc", g_tests[i].desc);
			buf_kv(&b, "file", g_tests[i].file);
			buf_kvn(&b, "line", g_tests[i].line);
			emit(&b);
		}
		else
			human("%-40s %s\n", id, g_tests[i].desc);
		i++;
	}
}

int	main(int argc, char **argv)
{
	const char	*fd_env;
	const char	*to_env;
	double		timeout;
	t_buf		b;
	int			first;
	int			i;

	fd_env = getenv("DT_REPORT_FD");
	to_env = getenv("DT_TIMEOUT");
	g_nofork = getenv("DT_NO_FORK") && getenv("DT_NO_FORK")[0] == '1';
	timeout = to_env ? atof(to_env) : 5.0;
	if (timeout <= 0)
		timeout = 5.0;
	if (fd_env && *fd_env)
	{
		g_json = 1;
		g_out = dup(atoi(fd_env));
	}
	else
		g_out = dup(2);
	signal(SIGPIPE, SIG_IGN);
	if (g_json)
	{
		begin(&b, "hello");
		buf_kvn(&b, "protocol", DT_PROTOCOL);
		buf_kv(&b, "harness", "c");
		buf_str(&b, dt_alloc_hooked() ? ",\"alloc_hooks\":true" : ",\"alloc_hooks\":false");
		emit(&b);
	}
	if (argc > 1 && !strcmp(argv[1], "--list"))
	{
		list_tests();
		return (0);
	}
	first = (argc > 1 && !strcmp(argv[1], "--run")) ? 2 : 1;
	i = 0;
	while (i < g_count)
	{
		if (selected(&g_tests[i], argc, argv, first))
			run_one(&g_tests[i], timeout);
		i++;
	}
	if (g_json)
	{
		begin(&b, "done");
		emit(&b);
	}
	return (0);
}
