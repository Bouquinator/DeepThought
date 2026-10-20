#include "libft_test.h"

static const char	*g_s = "Hello, 42 school!";

DT_TEST(ft_strchr, found, "Finds the first occurrence")
{
	DT_EXPECT_EQ_PTR(ft_strchr(g_s, 'o'), strchr(g_s, 'o'));
}

DT_TEST(ft_strchr, not_found, "Returns NULL when absent")
{
	DT_EXPECT_NULL(ft_strchr(g_s, 'z'));
}

DT_TEST(ft_strchr, terminator, "c = '\\0' returns a pointer to the terminator")
{
	DT_EXPECT_EQ_PTR(ft_strchr(g_s, '\0'), g_s + strlen(g_s));
}

DT_TEST(ft_strchr, int_conversion, "c is converted to char: 'H' + 256 finds 'H'")
{
	DT_EXPECT_EQ_PTR(ft_strchr(g_s, 'H' + 256), strchr(g_s, 'H' + 256));
}
