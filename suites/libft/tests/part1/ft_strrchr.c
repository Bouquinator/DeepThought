#include "libft_test.h"

static const char	*g_s = "Hello, 42 school!";

DT_TEST(ft_strrchr, found, "Finds the last occurrence")
{
	DT_EXPECT_EQ_PTR(ft_strrchr(g_s, 'o'), strrchr(g_s, 'o'));
}

DT_TEST(ft_strrchr, not_found, "Returns NULL when absent")
{
	DT_EXPECT_NULL(ft_strrchr(g_s, 'z'));
}

DT_TEST(ft_strrchr, terminator, "c = '\\0' returns a pointer to the terminator")
{
	DT_EXPECT_EQ_PTR(ft_strrchr(g_s, '\0'), g_s + strlen(g_s));
}

DT_TEST(ft_strrchr, first_char, "Match on the very first character")
{
	DT_EXPECT_EQ_STR(ft_strrchr("abc", 'a'), "abc");
}

DT_TEST(ft_strrchr, int_conversion, "c is converted to char ('l' + 256)")
{
	DT_EXPECT_EQ_PTR(ft_strrchr(g_s, 'l' + 256), strrchr(g_s, 'l' + 256));
}
