#include "libft_test.h"

DT_TEST(ft_putchar_fd, basic, "Writes one character to the fd")
{
	t_dt_capture	cap;

	DT_CAPTURE_FD(1, cap, ft_putchar_fd('x', 1));
	DT_EXPECT_EQ_MEM(cap.data, "x", 1);
	DT_EXPECT_EQ_SIZE(cap.len, 1);
	dt_capture_free(&cap);
}

DT_TEST(ft_putchar_fd, other_fd, "Respects the fd (writes to 2, not 1)")
{
	t_dt_capture	out;
	t_dt_capture	err;

	DT_CAPTURE_FD(1, out, DT_CAPTURE_FD(2, err, ft_putchar_fd('e', 2)));
	DT_EXPECT_EQ_SIZE(out.len, 0);
	DT_EXPECT_EQ_SIZE(err.len, 1);
	dt_capture_free(&out);
	dt_capture_free(&err);
}
