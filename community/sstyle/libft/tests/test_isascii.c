#include "sstyle.h"
#include <ctype.h>

DT_TEST(ft_isascii, cases, "ft_isascii")
{
	DT_CHECK_BOOL("0", ft_isascii(0), isascii(0));
	DT_CHECK_BOOL("'A'", ft_isascii('A'), isascii('A'));
	DT_CHECK_BOOL("127", ft_isascii(127), isascii(127));
	DT_CHECK_BOOL("128", ft_isascii(128), isascii(128));
	DT_CHECK_BOOL("-1", ft_isascii(-1), isascii(-1));
}
