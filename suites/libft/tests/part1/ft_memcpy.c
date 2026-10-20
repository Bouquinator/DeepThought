#include "libft_test.h"

DT_TEST(ft_memcpy, basic, "Copies n bytes and returns dst")
{
	char	src[] = "copy me\0with a null inside";
	char	dst[sizeof(src)];

	memset(dst, 0, sizeof(dst));
	DT_EXPECT_EQ_PTR(ft_memcpy(dst, src, sizeof(src)), dst);
	DT_EXPECT_EQ_MEM(dst, src, sizeof(src));
}

DT_TEST(ft_memcpy, zero_length, "n = 0 copies nothing")
{
	char	dst[4] = "abc";

	ft_memcpy(dst, "xyz", 0);
	DT_EXPECT_EQ_STR(dst, "abc");
}

DT_TEST(ft_memcpy, both_null, "memcpy(NULL, NULL, 3) returns NULL without crashing (like libc)")
{
	DT_EXPECT_NULL(ft_memcpy(NULL, NULL, 3));
}
