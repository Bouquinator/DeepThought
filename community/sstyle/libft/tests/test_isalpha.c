#include "sstyle.h"
#include <ctype.h>

DT_TEST(ft_isalpha, basic, "ft_isalpha: basic cases")
{
	DT_CHECK_BOOL("'a'", ft_isalpha('a'), isalpha('a'));
	DT_CHECK_BOOL("'z'", ft_isalpha('z'), isalpha('z'));
	DT_CHECK_BOOL("'A'", ft_isalpha('A'), isalpha('A'));
	DT_CHECK_BOOL("'Z'", ft_isalpha('Z'), isalpha('Z'));
	DT_CHECK_BOOL("'5'", ft_isalpha('5'), isalpha('5'));
	DT_CHECK_BOOL("0 (NUL)", ft_isalpha(0), isalpha(0));
}

DT_TEST(ft_isalpha, boundary, "boundary: chars just outside alpha ranges")
{
	DT_CHECK_BOOL("'@' (64, before A)", ft_isalpha('@'), isalpha('@'));
	DT_CHECK_BOOL("'[' (91, after Z)", ft_isalpha('['), isalpha('['));
	DT_CHECK_BOOL("'`' (96, before a)", ft_isalpha('`'), isalpha('`'));
	DT_CHECK_BOOL("'{' (123, after z)", ft_isalpha('{'), isalpha('{'));
}

DT_TEST(ft_isalpha, high_bytes_and_negative_passed_as, "high bytes and negative (passed as int)")
{
	DT_CHECK_BOOL("200 (>127)", ft_isalpha(200), isalpha(200));
	DT_CHECK_BOOL("-1 (EOF-like)", ft_isalpha(-1), isalpha(-1));
}
