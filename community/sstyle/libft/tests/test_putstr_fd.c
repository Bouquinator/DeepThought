#include "sstyle.h"
#include <string.h>

static void	t_putstr(const char *label, const char *s,
	const char *expected)
{
	int		pfd[2];
	char	buf[256];
	int		n;

	if (pipe(pfd) < 0)
	{
		DT_FAILF("check failed");
		return ;
	}
	ft_putstr_fd((char *)s, pfd[1]);
	close(pfd[1]);
	n = (int)read(pfd[0], buf, (int)sizeof(buf) - 1);
	buf[n < 0 ? 0 : n] = '\0';
	close(pfd[0]);
	DT_CHECK_STR(label, buf, expected);
}

DT_TEST(ft_putstr_fd, basic, "ft_putstr_fd: basic cases")
{
	t_putstr("putstr_fd \"hello\"", "hello", "hello");
}

DT_TEST(ft_putstr_fd, empty_string, "empty string")
{
	t_putstr("putstr_fd \"\"", "", "");
}
