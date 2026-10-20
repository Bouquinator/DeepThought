#include "sstyle.h"
/* Write c to a fresh pipe and read back what arrived. */
static void	t_putchar(const char *label, char c,
	const char *expected)
{
	int		pfd[2];
	char	buf[16];
	int		n;

	if (pipe(pfd) < 0)
	{
		DT_FAILF("check failed");
		return ;
	}
	ft_putchar_fd(c, pfd[1]);
	close(pfd[1]);
	n = (int)read(pfd[0], buf, (int)sizeof(buf) - 1);
	buf[n < 0 ? 0 : n] = '\0';
	close(pfd[0]);
	DT_CHECK_STR(label, buf, expected);
}

DT_TEST(ft_putchar_fd, putchar_fd_a, "putchar_fd 'A'")
{
	t_putchar("putchar_fd 'A'",  'A',  "A");
}

DT_TEST(ft_putchar_fd, putchar_fd_n, "putchar_fd '\\n'")
{
	t_putchar("putchar_fd '\\n'", '\n', "\n");
}
