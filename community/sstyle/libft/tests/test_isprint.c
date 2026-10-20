#include "sstyle.h"
#include <ctype.h>

DT_TEST(ft_isprint, cases, "ft_isprint")
{
	DT_CHECK_BOOL("' ' (32)", ft_isprint(' '), isprint(' '));
	DT_CHECK_BOOL("'~' (126)", ft_isprint('~'), isprint('~'));
	DT_CHECK_BOOL("'A'", ft_isprint('A'), isprint('A'));
	DT_CHECK_BOOL("31", ft_isprint(31), isprint(31));
	DT_CHECK_BOOL("127 (DEL)", ft_isprint(127), isprint(127));
	DT_CHECK_BOOL("0 (NUL)", ft_isprint(0), isprint(0));
	DT_CHECK_BOOL("'\\t' (9)", ft_isprint('\t'), isprint('\t'));
	DT_CHECK_BOOL("200 (>127)", ft_isprint(200), isprint(200));
}
