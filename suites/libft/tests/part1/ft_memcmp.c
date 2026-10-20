#include "libft_test.h"

DT_TEST(ft_memcmp, equal, "Equal buffers give 0")
{
	DT_EXPECT_EQ_INT(ft_memcmp("ab\0cd", "ab\0cd", 5), 0);
}

DT_TEST(ft_memcmp, past_null, "Does not stop at NUL bytes")
{
	DT_EXPECT_SAME_SIGN(ft_memcmp("ab\0cd", "ab\0ce", 5), memcmp("ab\0cd", "ab\0ce", 5));
}

DT_TEST(ft_memcmp, unsigned_bytes, "Compares as unsigned char")
{
	DT_EXPECT_SAME_SIGN(ft_memcmp("\xff", "\x01", 1), memcmp("\xff", "\x01", 1));
}

DT_TEST(ft_memcmp, n_zero, "n = 0 gives 0")
{
	DT_EXPECT_EQ_INT(ft_memcmp("a", "b", 0), 0);
}
