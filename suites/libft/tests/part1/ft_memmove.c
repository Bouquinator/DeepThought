#include "libft_test.h"

DT_TEST(ft_memmove, no_overlap, "Behaves like memcpy without overlap")
{
	char	dst[16] = {0};

	DT_EXPECT_EQ_PTR(ft_memmove(dst, "hello", 6), dst);
	DT_EXPECT_EQ_STR(dst, "hello");
}

DT_TEST(ft_memmove, overlap_forward, "dst after src (overlapping): must copy backwards")
{
	char	a[] = "0123456789";
	char	b[] = "0123456789";

	ft_memmove(a + 2, a, 6);
	memmove(b + 2, b, 6);
	DT_EXPECT_EQ_STR(a, b);
}

DT_TEST(ft_memmove, overlap_backward, "dst before src (overlapping)")
{
	char	a[] = "0123456789";
	char	b[] = "0123456789";

	ft_memmove(a, a + 3, 7);
	memmove(b, b + 3, 7);
	DT_EXPECT_EQ_STR(a, b);
}

DT_TEST(ft_memmove, both_null, "memmove(NULL, NULL, 5) returns NULL without crashing")
{
	DT_EXPECT_NULL(ft_memmove(NULL, NULL, 5));
}
