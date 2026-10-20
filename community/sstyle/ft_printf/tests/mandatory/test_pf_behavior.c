#include "pf.h"
/*
** Behaviour that is not about formatting:
**   - output goes straight to fd 1, in order with raw write() calls
**     (no buffering inside ft_printf);
**   - return value is -1 when write() fails, and a failure does not leak
**     into the next call (return values on success are checked by every
**     PF() case);
**   - no state carried over between calls;
**   - no leaks (and correct behaviour if malloc fails).
*/

/* Run ft_printf with fd 1 replaced by fd (or closed when fd < 0). */
#define PF_ON_FD(ret, fd, ...) do { \
	int	pf_saved_; \
	fflush(stdout); \
	pf_saved_ = dup(STDOUT_FILENO); \
	if ((fd) < 0) \
		close(STDOUT_FILENO); \
	else \
		dup2((fd), STDOUT_FILENO); \
	(ret) = ft_printf(__VA_ARGS__); \
	dup2(pf_saved_, STDOUT_FILENO); \
	close(pf_saved_); \
} while (0)

DT_TEST(printf_behavior, unbuffered, "output goes straight to fd 1, in order with raw write() calls (no buffering)")
{
	t_pfcap	cap;
	int		len;

	if (pf_capture_begin(&cap) != 0)
	{
		DT_FAILF("could not capture stdout");
		return ;
	}
	write(STDOUT_FILENO, "A", 1);
	ft_printf("B%dC", 1);
	write(STDOUT_FILENO, "D", 1);
	ft_printf("%s", "E");
	ft_printf("");
	write(STDOUT_FILENO, "F", 1);
	ft_printf("%c%%", 'G');
	len = pf_capture_end(&cap, g_pf_got, PF_BUF_SIZE);
	DT_CHECK_INT("interleaved write()/ft_printf: length", len, 9);
	DT_CHECK_STR("interleaved write()/ft_printf: order", g_pf_got, "AB1CDEFG%");
}

DT_TEST(printf_behavior, no_state_between_calls, "no state carried over between calls")
{
	PF("%s", "long string first");
	PF("%s", "x");
	PF("%d", INT_MIN);
	PF("%d", 1);
	PF("%X", 0xABCu);
	PF("%x", 0xabcu);
}

#ifndef _WIN32

DT_TEST(printf_behavior, write_errors, "returns -1 when write() fails, and the next call works again")
{
	int		r;

	PF_ON_FD(r, -1, "abc");
	DT_CHECK_INT("stdout closed: \"abc\" returns -1", r, -1);
	PF_ON_FD(r, -1, "%c", 'c');
	DT_CHECK_INT("stdout closed: \"%c\" returns -1", r, -1);
	PF_ON_FD(r, -1, "%s", "str");
	DT_CHECK_INT("stdout closed: \"%s\" returns -1", r, -1);
	PF_ON_FD(r, -1, "%d", 42);
	DT_CHECK_INT("stdout closed: \"%d\" returns -1", r, -1);
	PF_ON_FD(r, -1, "%x", 1u);
	DT_CHECK_INT("stdout closed: \"%x\" returns -1", r, -1);
	PF_ON_FD(r, -1, "%p", (void *)&r);
	DT_CHECK_INT("stdout closed: \"%p\" returns -1", r, -1);

	/* a failed call must not affect the next one */
	PF_ON_FD(r, -1, "fail");
	PF("works again %d", 42);
}

#endif

/* The same call as in memory(), with the fail_at-th allocation failing. */
static int	pf_failing_call(int fail_at, int *leaks)
{
	t_pfcap	cap;
	size_t	before;
	int		r;

	*leaks = 0;
	if (pf_capture_begin(&cap) != 0)
		return (-2);
	before = dt_alloc_live();
	dt_malloc_fail_at(fail_at);
	r = ft_printf("%c|%s|%p|%d|%i|%u|%x|%X|%%|%s|%p",
			'c', "str", (void *)&cap, INT_MIN, INT_MAX, UINT_MAX, 0xabcu,
			0xabcu, NULL, NULL);
	dt_malloc_reset();
	*leaks = (int)(dt_alloc_live() - before);
	pf_capture_end(&cap, g_pf_got, PF_BUF_SIZE);
	return (r);
}

DT_TEST(printf_behavior, memory, "no leak, and -1 or a normal result when any malloc fails")
{
	t_pfcap	cap;
	size_t	before;
	int		leaks;
	int		allocs;
	int		expected;
	int		i;
	int		r;
	char	label[64];

	if (pf_capture_begin(&cap) != 0)
	{
		DT_FAILF("could not capture stdout");
		return ;
	}
	before = dt_alloc_live();
	dt_malloc_reset();
	expected = ft_printf("%c|%s|%p|%d|%i|%u|%x|%X|%%|%s|%p",
			'c', "str", (void *)&cap, INT_MIN, INT_MAX, UINT_MAX, 0xabcu,
			0xabcu, NULL, NULL);
	ft_printf("%s", (char *)NULL);
	ft_printf("%c%c", '\0', 'x');
	allocs = dt_malloc_calls();
	leaks = (int)(dt_alloc_live() - before);
	pf_capture_end(&cap, g_pf_got, PF_BUF_SIZE);
	DT_CHECK_INT("no leaked allocation", leaks, 0);
	i = 1;
	while (i <= allocs)
	{
		r = pf_failing_call(i, &leaks);
		snprintf(label, sizeof(label), "malloc #%d fails: returns -1 or ok", i);
		DT_CHECK_BOOL(label, r == -1 || r == expected, 1);
		snprintf(label, sizeof(label), "malloc #%d fails: no leak", i);
		DT_CHECK_INT(label, leaks, 0);
		i++;
	}
	dt_leaks_ignore();	/* reported step by step above */
}

