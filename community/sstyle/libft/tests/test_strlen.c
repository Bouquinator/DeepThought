#include "sstyle.h"
#include <string.h>

DT_TEST(ft_strlen, basic, "ft_strlen: basic cases")
{
	DT_CHECK_SIZE("\"\"", ft_strlen(""), strlen(""));
	DT_CHECK_SIZE("\"a\"", ft_strlen("a"), strlen("a"));
	DT_CHECK_SIZE("\"Hello, World!\"", ft_strlen("Hello, World!"), strlen("Hello, World!"));
}

DT_TEST(ft_strlen, string_containing_high_bytes_gt_127, "string containing high bytes (>127) — must stop only at NUL")
{
	DT_CHECK_SIZE("high bytes \\x80\\xff\\x7f",
		ft_strlen("\x80\xff\x7f"), strlen("\x80\xff\x7f"));
}

DT_TEST(ft_strlen, stress, "stress: 1000-char string")
{
	{
		char	big[1001];
		memset(big, 'a', 1000);
		big[1000] = '\0';
		DT_CHECK_SIZE("1000 'a' chars", ft_strlen(big), 1000);
	}
}
