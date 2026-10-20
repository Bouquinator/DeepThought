/*
** Sstyle suite — ft_printf. Tests by SStyles93 (CodeTester,
** https://github.com/SStyles93/42_CodeTester), ported to DeepThought.
**
** Every case is checked against the host libc: the expected output and
** return value come from snprintf() called with the same arguments, so the
** reference is whatever the real printf prints on this machine (glibc on
** Linux, libSystem on macOS).
**
**   PF(format, args...)                 the label is the call's source text
**   PF_L(label, format, args...)        explicit label
**   PF_L_ALT(label, alt, format, ...)   also accepts `alt` as the output
**                                       (e.g. "%p" of NULL: "(nil)" / "0x0")
*/
#ifndef PF_H
# define PF_H
# include "dt.h"
# include "ft_printf.h"
# include <limits.h>
# include <stdio.h>
# include <stdlib.h>
# include <string.h>
# include <unistd.h>

/* some cases deliberately use undefined flag/specifier combinations */
# pragma GCC diagnostic ignored "-Wformat"
# pragma GCC diagnostic ignored "-Wformat-extra-args"
# pragma GCC diagnostic ignored "-Wformat-zero-length"
# pragma GCC diagnostic ignored "-Wformat-security"
# ifndef __clang__
#  pragma GCC diagnostic ignored "-Wformat-truncation"
#  pragma GCC diagnostic ignored "-Wformat-overflow"
# endif

# define PF_BUF_SIZE 262144

typedef struct s_pfcap
{
	FILE	*file;
	int		saved_fd;
}	t_pfcap;

typedef struct s_pfcase
{
	t_pfcap	cap;
	int		cap_ok;
	int		exp_ret;
	int		got_ret;
	int		got_len;
}	t_pfcase;

static char	g_pf_exp[PF_BUF_SIZE];
static char	g_pf_got[PF_BUF_SIZE];

/* Redirect fd 1 into a temp file / restore it and read what was written. */
static inline int	pf_capture_begin(t_pfcap *cap)
{
	fflush(stdout);
	cap->saved_fd = -1;
	cap->file = tmpfile();
	if (!cap->file)
		return (-1);
	cap->saved_fd = dup(STDOUT_FILENO);
	if (cap->saved_fd < 0 || dup2(fileno(cap->file), STDOUT_FILENO) < 0)
	{
		if (cap->saved_fd >= 0)
			close(cap->saved_fd);
		cap->saved_fd = -1;
		fclose(cap->file);
		cap->file = NULL;
		return (-1);
	}
	return (0);
}

static inline int	pf_capture_end(t_pfcap *cap, char *buf, size_t size)
{
	size_t	n;

	buf[0] = '\0';
	if (!cap->file)
		return (0);
	dup2(cap->saved_fd, STDOUT_FILENO);
	close(cap->saved_fd);
	rewind(cap->file);
	n = fread(buf, 1, size - 1, cap->file);
	buf[n] = '\0';
	fclose(cap->file);
	cap->file = NULL;
	return ((int)n);
}

/* Same verdict as the CodeTester: same bytes and same return value. */
static inline void	pf_report_at(const char *label, const t_pfcase *c,
	const char *alt_exp, const char *file, int line)
{
	char	call[600];
	int		exp_len;
	int		alt_len;
	int		ok;

	exp_len = c->exp_ret;
	if (exp_len >= PF_BUF_SIZE)
		exp_len = PF_BUF_SIZE - 1;
	alt_len = alt_exp ? (int)strlen(alt_exp) : -1;
	if (!c->cap_ok)
		ok = 0;
	else if (c->exp_ret < 0)
		ok = (c->got_ret == c->exp_ret);
	else
		ok = (c->got_ret == c->exp_ret && c->got_len == exp_len
				&& memcmp(g_pf_exp, g_pf_got, exp_len) == 0);
	if (!ok && alt_exp && c->got_ret == alt_len && c->got_len == alt_len
		&& memcmp(alt_exp, g_pf_got, alt_len) == 0)
		ok = 1;
	if (ok)
		return ;
	snprintf(call, sizeof(call), "ft_printf(%s)", label);
	if (!c->cap_ok)
	{
		dt_check(0, 0, call, "the output", "stdout could not be captured", file, line);
		return ;
	}
	if (alt_exp)
		dt_note("\"%s\" is also accepted for %s", alt_exp, call);
	if (c->exp_ret >= 0)
		dt_check_bytes(g_pf_got, c->got_len, g_pf_exp, exp_len, 0, call, file, line);
	snprintf(call, sizeof(call), "return value of ft_printf(%s)", label);
	dt_check_int(c->got_ret, c->exp_ret, 0, call, file, line);
}

# define PF_RUN_(label, alt, ...) do { \
	t_pfcase	pf_c_; \
	pf_c_.exp_ret = snprintf(g_pf_exp, PF_BUF_SIZE, __VA_ARGS__); \
	pf_c_.cap_ok = (pf_capture_begin(&pf_c_.cap) == 0); \
	pf_c_.got_ret = -1; \
	if (pf_c_.cap_ok) \
		pf_c_.got_ret = ft_printf(__VA_ARGS__); \
	pf_c_.got_len = pf_capture_end(&pf_c_.cap, g_pf_got, PF_BUF_SIZE); \
	pf_report_at((label), &pf_c_, (alt), __FILE__, __LINE__); \
} while (0)

# define PF_L(label, ...) PF_RUN_(label, NULL, __VA_ARGS__)
# define PF_L_ALT(label, alt_exp, ...) PF_RUN_(label, alt_exp, __VA_ARGS__)
# define PF(...) PF_L(#__VA_ARGS__, __VA_ARGS__)

#endif
