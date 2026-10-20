#include "libft_test.h"

DT_TEST(ft_memchr, found, "Finds a byte")
{
	const char	s[] = "find\0the byte";

	DT_EXPECT_EQ_PTR(ft_memchr(s, 'b', sizeof(s)), memchr(s, 'b', sizeof(s)));
}

DT_TEST(ft_memchr, past_null, "Does not stop at NUL bytes")
{
	const char	s[] = "a\0bc";

	DT_EXPECT_EQ_PTR(ft_memchr(s, 'c', 4), s + 3);
}

DT_TEST(ft_memchr, not_found, "Returns NULL when absent within n")
{
	DT_EXPECT_NULL(ft_memchr("abcdef", 'f', 5));
}

DT_TEST(ft_memchr, unsigned_conversion, "Searches (unsigned char)c: 0x1ff finds 0xff")
{
	const unsigned char	s[] = {1, 2, 0xff, 4};

	DT_EXPECT_EQ_PTR(ft_memchr(s, 0x1ff, 4), (void *)(s + 2));
}
