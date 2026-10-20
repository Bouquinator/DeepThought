#include "sstyle.h"
#include <stdlib.h>

DT_TEST(ft_atoi, basic, "ft_atoi: basic cases")
{
	DT_CHECK_INT("\"42\"", ft_atoi("42"), atoi("42"));
	DT_CHECK_INT("\"-42\"", ft_atoi("-42"), atoi("-42"));
	DT_CHECK_INT("\"+42\"", ft_atoi("+42"), atoi("+42"));
	DT_CHECK_INT("\"0\"", ft_atoi("0"), atoi("0"));
}

DT_TEST(ft_atoi, every_whitespace_type_before_a_sign, "every whitespace type before a sign: ' ' \\t \\n \\v \\f \\r")
{
	DT_CHECK_INT("\" \\t\\n\\v\\f\\r-42\"", ft_atoi(" \t\n\v\f\r-42"), atoi(" \t\n\v\f\r-42"));
	DT_CHECK_INT("\"42abc\"", ft_atoi("42abc"), atoi("42abc"));
	DT_CHECK_INT("\"abc\"", ft_atoi("abc"), atoi("abc"));
	DT_CHECK_INT("\"\"", ft_atoi(""), atoi(""));
	DT_CHECK_INT("\"   \"", ft_atoi("   "), atoi("   "));
	DT_CHECK_INT("\"2147483647\"", ft_atoi("2147483647"), atoi("2147483647"));
	DT_CHECK_INT("\"-2147483648\"", ft_atoi("-2147483648"), atoi("-2147483648"));
	DT_CHECK_INT("\"0042\"", ft_atoi("0042"), atoi("0042"));
}

DT_TEST(ft_atoi, just_a_sign_character_to_0, "just a sign character → 0")
{
	DT_CHECK_INT("\"-\"", ft_atoi("-"), atoi("-"));
}

DT_TEST(ft_atoi, double_sign, "double sign: second sign is not a digit, stops immediately → 0")
{
	DT_CHECK_INT("\"+-42\"", ft_atoi("+-42"), atoi("+-42"));
}
