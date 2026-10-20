#include "sstyle.h"
#include <ctype.h>

DT_TEST(ft_tolower, basic, "ft_tolower: basic cases")
{
	DT_CHECK_CHAR("'A'", ft_tolower('A'), (char)tolower('A'));
	DT_CHECK_CHAR("'Z'", ft_tolower('Z'), (char)tolower('Z'));
	DT_CHECK_CHAR("'M'", ft_tolower('M'), (char)tolower('M'));
	DT_CHECK_CHAR("'a' (no change)", ft_tolower('a'), (char)tolower('a'));
	DT_CHECK_CHAR("'1' (no change)", ft_tolower('1'), (char)tolower('1'));
}

DT_TEST(ft_tolower, boundary, "boundary: chars just outside A-Z")
{
	DT_CHECK_CHAR("'@' (no change)", ft_tolower('@'), (char)tolower('@'));
	DT_CHECK_CHAR("'[' (no change)", ft_tolower('['), (char)tolower('['));
}
