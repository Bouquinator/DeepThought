#include "libft_test.h"

DT_TEST(ft_putendl_fd, basic, "Writes the string followed by a newline")
{
	t_dt_capture	cap;

	DT_CAPTURE_FD(1, cap, ft_putendl_fd("hello", 1));
	dt_check_bytes(cap.data, cap.len, "hello\n", 6, 0, "output", __FILE__, __LINE__);
	dt_capture_free(&cap);
}
