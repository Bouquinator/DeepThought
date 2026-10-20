#include "libft_test.h"

DT_TEST(ft_strlen, basic, "Length of a regular string")
{
	DT_EXPECT_EQ_SIZE(ft_strlen("Hello 42"), 8);
}

DT_TEST(ft_strlen, empty, "The empty string has length 0")
{
	DT_EXPECT_EQ_SIZE(ft_strlen(""), 0);
}

DT_TEST(ft_strlen, long_string, "A 10000 character string")
{
	char	*s = malloc(10001);

	memset(s, 'x', 10000);
	s[10000] = 0;
	DT_EXPECT_EQ_SIZE(ft_strlen(s), 10000);
	free(s);
}

DT_TEST(ft_strlen, high_bytes, "Bytes above 127 are counted like any other")
{
	DT_EXPECT_EQ_SIZE(ft_strlen("\xff\x80\xc3\xa9"), 4);
}
