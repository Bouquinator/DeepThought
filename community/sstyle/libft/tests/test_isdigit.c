#include "sstyle.h"
#include <ctype.h>

DT_TEST(ft_isdigit, basic, "ft_isdigit: basic cases")
{
	DT_CHECK_BOOL("'0'", ft_isdigit('0'), isdigit('0'));
	DT_CHECK_BOOL("'5'", ft_isdigit('5'), isdigit('5'));
	DT_CHECK_BOOL("'9'", ft_isdigit('9'), isdigit('9'));
	DT_CHECK_BOOL("'a'", ft_isdigit('a'), isdigit('a'));
	DT_CHECK_BOOL("0 (NUL)", ft_isdigit(0), isdigit(0));
}

DT_TEST(ft_isdigit, boundary, "boundary: chars just outside the digit range")
{
	DT_CHECK_BOOL("'/' (47, before 0)", ft_isdigit('/'), isdigit('/'));
	DT_CHECK_BOOL("':' (58, after 9)", ft_isdigit(':'), isdigit(':'));
}

DT_TEST(ft_isdigit, high_bytes_and_negative, "high bytes and negative")
{
	DT_CHECK_BOOL("200 (>127)", ft_isdigit(200), isdigit(200));
	DT_CHECK_BOOL("-1 (EOF-like)", ft_isdigit(-1), isdigit(-1));
}
