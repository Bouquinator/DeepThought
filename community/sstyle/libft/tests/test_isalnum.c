#include "sstyle.h"
#include <ctype.h>

DT_TEST(ft_isalnum, basic, "ft_isalnum: basic cases")
{
	DT_CHECK_BOOL("'a'", ft_isalnum('a'), isalnum('a'));
	DT_CHECK_BOOL("'Z'", ft_isalnum('Z'), isalnum('Z'));
	DT_CHECK_BOOL("'5'", ft_isalnum('5'), isalnum('5'));
	DT_CHECK_BOOL("0 (NUL)", ft_isalnum(0), isalnum(0));
}

DT_TEST(ft_isalnum, boundary, "boundary: chars just outside alpha/digit ranges")
{
	DT_CHECK_BOOL("'/' (47, before 0)", ft_isalnum('/'), isalnum('/'));
	DT_CHECK_BOOL("':' (58, after 9)", ft_isalnum(':'), isalnum(':'));
	DT_CHECK_BOOL("'@' (64, before A)", ft_isalnum('@'), isalnum('@'));
	DT_CHECK_BOOL("'[' (91, after Z)", ft_isalnum('['), isalnum('['));
	DT_CHECK_BOOL("'`' (96, before a)", ft_isalnum('`'), isalnum('`'));
	DT_CHECK_BOOL("'{' (123, after z)", ft_isalnum('{'), isalnum('{'));
}

DT_TEST(ft_isalnum, high_bytes_and_negative, "high bytes and negative")
{
	DT_CHECK_BOOL("200 (>127)", ft_isalnum(200), isalnum(200));
	DT_CHECK_BOOL("-1 (EOF-like)", ft_isalnum(-1), isalnum(-1));
}
