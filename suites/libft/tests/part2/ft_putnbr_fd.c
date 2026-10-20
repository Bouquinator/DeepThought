#include "libft_test.h"

static void	check(int n, const char *want)
{
	t_dt_capture	cap;

	DT_CAPTURE_FD(1, cap, ft_putnbr_fd(n, 1));
	dt_check_bytes(cap.data, cap.len, want, strlen(want), 0, "output", __FILE__, __LINE__);
	dt_capture_free(&cap);
}

DT_TEST(ft_putnbr_fd, basic, "Positive, negative, zero")
{
	check(42, "42");
	check(-42, "-42");
	check(0, "0");
}

DT_TEST(ft_putnbr_fd, limits, "INT_MAX and INT_MIN")
{
	check(INT_MAX, "2147483647");
	check(INT_MIN, "-2147483648");
}
