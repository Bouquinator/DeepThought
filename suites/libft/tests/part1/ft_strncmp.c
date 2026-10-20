#include "libft_test.h"

DT_TEST(ft_strncmp, equal, "Equal strings give 0")
{
	DT_EXPECT_EQ_INT(ft_strncmp("abc", "abc", 3), 0);
}

DT_TEST(ft_strncmp, differ, "Different strings: same sign as strncmp")
{
	DT_EXPECT_SAME_SIGN(ft_strncmp("abc", "abd", 3), strncmp("abc", "abd", 3));
	DT_EXPECT_SAME_SIGN(ft_strncmp("abd", "abc", 3), strncmp("abd", "abc", 3));
}

DT_TEST(ft_strncmp, n_limit, "Stops after n characters")
{
	DT_EXPECT_EQ_INT(ft_strncmp("abcX", "abcY", 3), 0);
}

DT_TEST(ft_strncmp, n_zero, "n = 0 gives 0")
{
	DT_EXPECT_EQ_INT(ft_strncmp("a", "b", 0), 0);
}

DT_TEST(ft_strncmp, prefix, "A prefix is smaller")
{
	DT_EXPECT_SAME_SIGN(ft_strncmp("abc", "abcdef", 6), strncmp("abc", "abcdef", 6));
}

DT_TEST(ft_strncmp, unsigned_chars, "Compares as unsigned char: '\\200' > 'a'")
{
	DT_EXPECT_SAME_SIGN(ft_strncmp("\200", "a", 1), strncmp("\200", "a", 1));
}
