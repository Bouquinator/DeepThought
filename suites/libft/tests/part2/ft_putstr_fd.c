#include "libft_test.h"

DT_TEST(ft_putstr_fd, basic, "Writes the string, without a newline")
{
	t_dt_capture	cap;

	DT_CAPTURE_FD(1, cap, ft_putstr_fd("hello 42", 1));
	dt_check_bytes(cap.data, cap.len, "hello 42", 8, 0, "output", __FILE__, __LINE__);
	dt_capture_free(&cap);
}

DT_TEST(ft_putstr_fd, empty, "Empty string writes nothing")
{
	t_dt_capture	cap;

	DT_CAPTURE_FD(1, cap, ft_putstr_fd("", 1));
	DT_EXPECT_EQ_SIZE(cap.len, 0);
	dt_capture_free(&cap);
}
