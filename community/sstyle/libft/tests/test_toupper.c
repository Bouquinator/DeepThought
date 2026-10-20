#include "sstyle.h"
#include <ctype.h>

DT_TEST(ft_toupper, basic, "ft_toupper: basic cases")
{
	DT_CHECK_CHAR("'a'", ft_toupper('a'), (char)toupper('a'));
	DT_CHECK_CHAR("'z'", ft_toupper('z'), (char)toupper('z'));
	DT_CHECK_CHAR("'m'", ft_toupper('m'), (char)toupper('m'));
	DT_CHECK_CHAR("'A' (no change)", ft_toupper('A'), (char)toupper('A'));
	DT_CHECK_CHAR("'1' (no change)", ft_toupper('1'), (char)toupper('1'));
}

DT_TEST(ft_toupper, boundary, "boundary: chars just outside a-z")
{
	DT_CHECK_CHAR("'`' (no change)", ft_toupper('`'), (char)toupper('`'));
	DT_CHECK_CHAR("'{' (no change)", ft_toupper('{'), (char)toupper('{'));
}
