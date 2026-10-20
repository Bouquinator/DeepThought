#include "sstyle.h"
#include <string.h>
#include <limits.h>

static void	t_putnbr(const char *label, int n, const char *expected)
{
	int		pfd[2];
	char	buf[32];
	int		r;

	if (pipe(pfd) < 0)
	{
		DT_FAILF("check failed");
		return ;
	}
	ft_putnbr_fd(n, pfd[1]);
	close(pfd[1]);
	r = (int)read(pfd[0], buf, (int)sizeof(buf) - 1);
	buf[r < 0 ? 0 : r] = '\0';
	close(pfd[0]);
	DT_CHECK_STR(label, buf, expected);
}

DT_TEST(ft_putnbr_fd, putnbr_fd_0, "putnbr_fd 0")
{
	t_putnbr("putnbr_fd 0",          0,           "0");
}

DT_TEST(ft_putnbr_fd, putnbr_fd_9, "putnbr_fd 9")
{
	t_putnbr("putnbr_fd 9",          9,           "9");
}

DT_TEST(ft_putnbr_fd, putnbr_fd_minus_9, "putnbr_fd -9")
{
	t_putnbr("putnbr_fd -9",         -9,          "-9");
}

DT_TEST(ft_putnbr_fd, putnbr_fd_10, "putnbr_fd 10")
{
	/* digit-count transitions */
	t_putnbr("putnbr_fd 10",         10,          "10");
}

DT_TEST(ft_putnbr_fd, putnbr_fd_minus_10, "putnbr_fd -10")
{
	/* digit-count transitions */
	t_putnbr("putnbr_fd -10",        -10,         "-10");
}

DT_TEST(ft_putnbr_fd, putnbr_fd_1000, "putnbr_fd 1000")
{
	/* digit-count transitions */
	t_putnbr("putnbr_fd 1000",       1000,        "1000");
}

DT_TEST(ft_putnbr_fd, putnbr_fd_2147483647, "putnbr_fd 2147483647")
{
	/* digit-count transitions */
	t_putnbr("putnbr_fd 2147483647", 2147483647,  "2147483647");
}

DT_TEST(ft_putnbr_fd, putnbr_fd_int_min, "putnbr_fd INT_MIN")
{
	/* digit-count transitions */
	t_putnbr("putnbr_fd INT_MIN",    -2147483648, "-2147483648");
}
